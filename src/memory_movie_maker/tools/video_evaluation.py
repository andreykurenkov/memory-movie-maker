"""Video evaluation tool using Gemini for critique."""

import logging
from typing import Dict, Any, List, Optional
import json
import asyncio
from pathlib import Path

from google import genai
from google.adk.tools import FunctionTool

from ..config import settings
from ..models.project_state import ProjectState


logger = logging.getLogger(__name__)


class VideoEvaluator:
    """Evaluates rendered videos using Gemini's video understanding."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """Initialize video evaluator.
        
        Args:
            model_name: Gemini model to use
        """
        self._model_name = model_name
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
            # Upload video
            logger.info(f"Uploading video for evaluation: {video_path}")
            video_file = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.files.upload(file=video_path)
            )
            
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
            
            # Clean up
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.files.delete(name=video_file.name)
                )
            except Exception as e:
                logger.warning(f"Failed to delete uploaded file: {e}")
            
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
        
        return f"""You are an expert video editor evaluating a generated memory movie.

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

Be specific and constructive in your critique. Focus on:
1. Pacing and rhythm synchronization
2. Visual storytelling and flow
3. Technical quality (resolution, transitions, effects)
4. Emotional impact and engagement
5. Adherence to the requested style"""
    
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


# Create ADK tool
evaluate_video_tool = FunctionTool(evaluate_video)