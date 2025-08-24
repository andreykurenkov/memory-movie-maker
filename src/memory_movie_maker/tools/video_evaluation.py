"""Video evaluation tool using Gemini for critique."""

import logging
from typing import Dict, Any
import json
import asyncio
from pathlib import Path

from google import genai
from google.adk.tools import FunctionTool

from ..config import settings
from ..models.project_state import ProjectState
from ..utils.ai_output_logger import ai_logger


logger = logging.getLogger(__name__)


class VideoEvaluator:
    """Evaluates rendered videos using Gemini's video understanding."""
    
    # Class-level cache for uploaded video files to avoid re-uploading
    _file_cache: Dict[str, Any] = {}
    _cache_timestamps: Dict[str, float] = {}
    
    def __init__(self, model_name: str = None):
        """Initialize video evaluator.
        
        Args:
            model_name: Gemini model to use (defaults to config)
        """
        self._model_name = model_name or settings.get_gemini_model_name()
        self._client = genai.Client(api_key=settings.gemini_api_key)
    
    async def evaluate_video(
        self,
        video_path: str,
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a rendered video for quality and improvements.
        
        Args:
            video_path: Path to rendered video
            project_context: Context about the project (prompt, style, etc.)
            
        Returns:
            Evaluation results with critique and suggestions
        """
        try:
            # Check if we have a cached upload for this video
            import os
            file_stat = os.stat(video_path)
            cache_key = f"{video_path}:{file_stat.st_mtime}:{file_stat.st_size}"
            
            if cache_key in VideoEvaluator._file_cache:
                logger.info(f"Using cached upload for: {video_path}")
                video_file = VideoEvaluator._file_cache[cache_key]
                
                # Check if the cached file is still active
                try:
                    file_info = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.files.get(name=video_file.name)
                    )
                    if file_info.state != "ACTIVE":
                        logger.warning(f"Cached file no longer active, re-uploading")
                        del VideoEvaluator._file_cache[cache_key]
                        video_file = None
                except Exception as e:
                    logger.warning(f"Cached file check failed, re-uploading: {e}")
                    del VideoEvaluator._file_cache[cache_key]
                    video_file = None
            else:
                video_file = None
            
            # Upload if not cached or cache invalid
            if video_file is None:
                logger.info(f"Uploading video for evaluation: {video_path}")
                video_file = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.files.upload(file=video_path)
                )
                
                # Cache the upload
                VideoEvaluator._file_cache[cache_key] = video_file
                VideoEvaluator._cache_timestamps[cache_key] = asyncio.get_event_loop().time()
                
                # Wait for processing
                await asyncio.sleep(2)
                
                # Check file status
                file_info = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.files.get(name=video_file.name)
                )
                
                if file_info.state != "ACTIVE":
                    logger.warning(f"File not ready: {file_info.state}")
            
            # Create evaluation prompt
            prompt = self._create_evaluation_prompt(project_context)
            
            # Generate critique
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self._model_name,
                    contents=[prompt, video_file]
                )
            )
            
            # Parse response
            critique = self._parse_evaluation_response(response.text)
            
            # Log to AI output logger
            ai_logger.log_evaluation(
                video_path=video_path,
                evaluation=critique,
                iteration=0,  # Will be updated by caller if needed
                prompt=prompt,  # Include the prompt
                raw_response=response.text
            )
            
            # Don't delete the file - keep it cached for potential re-evaluation
            # Files will be cleaned up when session ends or after timeout
            logger.debug(f"Keeping uploaded file cached: {video_file.name}")
            
            return {
                "status": "success",
                "evaluation": critique
            }
            
        except Exception as e:
            logger.error(f"Video evaluation failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _create_evaluation_prompt(self, context: Dict[str, Any]) -> str:
        """Create evaluation prompt for Gemini."""
        user_prompt = context.get("user_prompt", "Create a memory movie")
        style = context.get("style", "auto")
        target_duration = context.get("target_duration", 60)
        
        return f"""You are an expert video editor evaluating a video that was automatically generated from a collection of photos and videos.

Original Request: "{user_prompt}"
Style: {style}
Target Duration: {target_duration} seconds

Please evaluate this video and provide a detailed critique in the following JSON format:

{{
    "overall_score": 7.5,  // Score out of 10
    "strengths": [
        "Good pacing and rhythm",
        "Smooth transitions between clips"
    ],
    "weaknesses": [
        "Some clips feel too short",
        "Energy doesn't match music in middle section"
    ],
    "technical_issues": [
        "Slight pixelation at 0:15",
        "Audio sync issue at 0:32"
    ],
    "creative_suggestions": [
        "Consider longer clips for emotional moments",
        "Add more dynamic transitions during high-energy sections"
    ],
    "specific_edits": [
        {{
            "timestamp": "0:15-0:18",
            "issue": "Clip too short",
            "suggestion": "Extend clip duration by 2 seconds"
        }},
        {{
            "timestamp": "0:32",
            "issue": "Abrupt transition",
            "suggestion": "Use crossfade instead of cut"
        }}
    ],
    "recommendation": "minor_adjustments"  // "accept", "minor_adjustments", "major_rework"
}}

Be specific and constructive in your critique. Apply PROFESSIONAL BROADCAST STANDARDS:

SCORING RUBRIC (be strict):
- 9-10: Broadcast/commercial quality, could air on TV
- 7-8: Very good, minor issues only
- 5-6: Acceptable but needs work
- 3-4: Amateur, significant issues
- 1-2: Poor quality, major rework needed

EVALUATION CRITERIA:
1. PACING (20%): Rhythm, tempo changes, breathing room
2. MUSIC SYNC (20%): Cuts on beat, visual peaks match audio
3. VISUAL FLOW (20%): Story progression, shot variety, composition
4. TECHNICAL (20%): Resolution, color, transitions, stability
5. EMOTIONAL IMPACT (20%): Engagement, mood, satisfying conclusion

COMMON ISSUES TO CHECK:
- Cuts not on beat
- Shots too long/short for content
- Poor quality clips used
- Jarring transitions
- Weak opening or ending
- Mismatched energy between audio and video"""
    
    def _parse_evaluation_response(self, response_text: str) -> Dict[str, Any]:
        """Parse evaluation response from Gemini."""
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback parsing
                return {
                    "overall_score": 6.0,
                    "strengths": ["Video generated successfully"],
                    "weaknesses": ["Could not parse detailed evaluation"],
                    "technical_issues": [],
                    "creative_suggestions": ["Re-run evaluation for detailed feedback"],
                    "specific_edits": [],
                    "recommendation": "minor_adjustments"
                }
        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            return {
                "overall_score": 5.0,
                "strengths": [],
                "weaknesses": ["Evaluation parsing failed"],
                "technical_issues": [],
                "creative_suggestions": [],
                "specific_edits": [],
                "recommendation": "major_rework"
            }


# Create the evaluation tool function
async def evaluate_video(
    project_state: Dict[str, Any],
    video_path: str = None
) -> Dict[str, Any]:
    """Evaluate a rendered video for quality and improvements.
    
    Args:
        project_state: Current project state
        video_path: Path to video (uses latest render if not specified)
        
    Returns:
        Evaluation results with critique and suggestions
    """
    try:
        # Parse project state
        state = ProjectState(**project_state)
        
        # Get video path
        if not video_path and state.rendered_outputs:
            video_path = state.rendered_outputs[-1]  # Use latest render
        
        if not video_path:
            return {
                "status": "error",
                "error": "No video found to evaluate"
            }
        
        # Check if file exists
        if not Path(video_path).exists():
            return {
                "status": "error",
                "error": f"Video file not found: {video_path}"
            }
        
        # Create evaluation context
        context = {
            "user_prompt": state.user_inputs.initial_prompt,
            "style": state.user_inputs.style_preferences.get("style", "auto"),
            "target_duration": state.user_inputs.target_duration
        }
        
        # Evaluate video
        evaluator = VideoEvaluator()
        result = await evaluator.evaluate_video(video_path, context)
        
        if result["status"] == "success":
            # Store evaluation in project state
            state.evaluation_results = result["evaluation"]
            
            logger.info(f"Video evaluation complete: Score {result['evaluation']['overall_score']}/10")
            
            return {
                "status": "success",
                "evaluation": result["evaluation"],
                "updated_state": state.model_dump()
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Video evaluation failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def cleanup_video_cache():
    """Clean up cached video uploads. Call this at session end."""
    if VideoEvaluator._file_cache:
        logger.info(f"Cleaning up {len(VideoEvaluator._file_cache)} cached video uploads")
        client = genai.Client(api_key=settings.gemini_api_key)
        for cache_key, video_file in VideoEvaluator._file_cache.items():
            try:
                client.files.delete(name=video_file.name)
                logger.debug(f"Deleted cached file: {video_file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete cached file {video_file.name}: {e}")
        VideoEvaluator._file_cache.clear()
        VideoEvaluator._cache_timestamps.clear()


# Create ADK tool
evaluate_video_tool = FunctionTool(evaluate_video)