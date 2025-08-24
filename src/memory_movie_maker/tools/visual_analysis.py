"""Visual analysis tool using Gemini API for image and video analysis."""

import logging
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio
import json

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, Image
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from google.adk.tools import FunctionTool
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

import cv2

from ..config import settings
from ..models.media_asset import GeminiAnalysis
from ..storage.interface import StorageInterface
from ..utils.simple_logger import log_start, log_update, log_complete
from ..utils.ai_output_logger import ai_logger


logger = logging.getLogger(__name__)

# Module-level analyzer instance for reuse
_analyzer_instance: Optional['VisualAnalysisTool'] = None


class VisualAnalysisTool:
    """Tool for analyzing visual content using Gemini API."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
        """Initialize the visual analysis tool.
        
        Args:
            storage: Storage interface for accessing media files
        """
        self.storage = storage
        self._client = None
        self._model_name = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client based on configuration."""
        if settings.google_genai_use_vertexai and VERTEX_AI_AVAILABLE:
            # Use Vertex AI
            if not settings.google_cloud_project:
                raise ValueError("GOOGLE_CLOUD_PROJECT must be set for Vertex AI")
            
            vertexai.init(
                project=settings.google_cloud_project,
                location=settings.google_cloud_location
            )
            self._model = GenerativeModel(settings.get_gemini_model_name())
            self._api_type = "vertex"
            log_complete(logger, f"Initialized Gemini via Vertex AI (project: {settings.google_cloud_project})")
        
        elif settings.gemini_api_key and GENAI_AVAILABLE:
            # Use direct Gemini API with new SDK
            self._client = genai.Client(api_key=settings.gemini_api_key)
            self._model_name = settings.get_gemini_model_name()
            self._api_type = "genai"
            log_complete(logger, f"Initialized Gemini via direct API using model: {self._model_name}")
        
        else:
            raise ValueError(
                "No valid Gemini configuration found. "
                "Set either GOOGLE_CLOUD_PROJECT or GEMINI_API_KEY"
            )
    
    async def analyze_image(self, image_path: str) -> GeminiAnalysis:
        """Analyze a single image using Gemini.
        
        Args:
            image_path: Path to the image file or storage path
            
        Returns:
            GeminiAnalysis object with structured analysis results
        """
        try:
            log_start(logger, f"Analyzing image: {Path(image_path).name}")
            
            # Load image data
            log_update(logger, "Loading image data...")
            image_data = await self._load_image(image_path)
            
            # Create the analysis prompt
            prompt = self._create_image_analysis_prompt()
            
            # Call Gemini API
            log_update(logger, "Sending to Gemini API...")
            response = await self._call_gemini(prompt, image_data, image_path)
            
            # Parse response into structured format
            log_update(logger, "Parsing analysis results...")
            analysis = self._parse_gemini_response(response)
            
            # Add prompt to analysis
            analysis.llm_prompt = prompt
            
            # Log to AI output logger
            ai_logger.log_visual_analysis(
                file_path=image_path,
                analysis=analysis.dict(exclude={'llm_prompt'}) if hasattr(analysis, 'dict') else vars(analysis),
                prompt=prompt,
                raw_response=response
            )
            
            log_complete(logger, f"Image analysis complete - {analysis.description[:50]}...")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze image {image_path}: {e}")
            raise
    
    async def analyze_video(self, video_path: str) -> GeminiAnalysis:
        """Analyze a complete video using Gemini's native video understanding.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            GeminiAnalysis object with video analysis including notable segments
        """
        try:
            log_start(logger, f"Analyzing video: {Path(video_path).name}")
            
            # Get video duration for the prompt
            log_update(logger, "Getting video metadata...")
            duration = await self._get_video_duration(video_path)
            log_update(logger, f"Video duration: {duration:.1f} seconds")
            
            # Create the analysis prompt
            prompt = self._create_video_analysis_prompt(duration)
            
            # Call Gemini API with the video
            log_update(logger, "Uploading video to Gemini API...")
            response = await self._call_gemini_video(prompt, video_path)
            
            # Parse response
            log_update(logger, "Parsing video analysis results...")
            analysis = self._parse_gemini_response(response)
            
            # Add prompt to analysis
            analysis.llm_prompt = prompt
            
            if analysis.notable_segments:
                log_update(logger, f"Found {len(analysis.notable_segments)} notable segments")
            
            # Log to AI output logger
            ai_logger.log_visual_analysis(
                file_path=video_path,
                analysis=analysis.dict(exclude={'llm_prompt'}) if hasattr(analysis, 'dict') else vars(analysis),
                prompt=prompt,
                raw_response=response
            )
            
            log_complete(logger, f"Video analysis complete - {analysis.description[:50]}...")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze video {video_path}: {e}")
            raise
    
    
    def _create_image_analysis_prompt(self) -> str:
        """Create the prompt for image analysis."""
        return """Analyze this image with PROFESSIONAL STANDARDS and provide a detailed JSON response:
{
  "description": "A clear, concise description of what's in the image",
  "aesthetic_score": 0.85,  // 0-1 score - BE STRICT: 0.9+ exceptional, 0.7-0.9 good, 0.5-0.7 acceptable, <0.5 poor
  "quality_issues": ["list", "of", "any", "quality", "problems"],
  "main_subjects": ["list", "of", "main", "subjects", "or", "people"],
  "tags": ["relevant", "tags", "for", "categorization"]
}

SCORING GUIDELINES (be critical):
- Deduct for: blur, noise, poor lighting, bad framing, distracting backgrounds
- Reward for: sharp focus, good composition, proper exposure, compelling subjects
- Most amateur photos should score 0.5-0.7
- Only truly excellent photos should score above 0.8"""
    
    def _create_video_analysis_prompt(self, video_duration: float) -> str:
        """Create the prompt for full video analysis including audio."""
        return f"""Analyze this video (duration: {video_duration:.1f} seconds) by examining both visual AND audio content together. Provide a comprehensive JSON response with the following structure:
{{
  "description": "Overall description of the video content including audio elements",
  "aesthetic_score": 0.75,  // 0-1 overall visual quality score
  "quality_issues": ["list", "of", "any", "quality", "problems"],
  "main_subjects": ["list", "of", "main", "subjects", "throughout", "video"],
  "tags": ["relevant", "tags", "for", "categorization"],
  "notable_segments": [
    {{
      "start_time": 0.0,
      "end_time": 3.5,
      "description": "Complete description of what happens in this segment (both visual and audio)",
      "visual_content": "What is shown visually",
      "audio_content": "What is heard (speech content, music description, sound effects)",
      "audio_type": "speech/music/sfx/ambient/mixed/silence",
      "speaker": "person1/narrator/unknown (if speech)",
      "speech_content": "Transcription or summary of speech (if any)",
      "music_description": "Genre, mood, tempo of music (if any)",
      "emotional_tone": "happy/sad/exciting/calm/tense/neutral",
      "importance": 0.8,  // 0-1 score for timeline inclusion
      "sync_priority": 0.7,  // 0-1 score for audio-visual sync importance
      "recommended_action": "cut_here/hold/transition/sync_to_beat",
      "tags": ["dialogue", "action", "music", "transition"]
    }}
  ],
  "overall_motion": "Description of overall motion/pacing in the video",
  "scene_changes": [1.5, 4.2, 7.8],  // Timestamps where major scene changes occur
  "audio_summary": {{
    "has_speech": true/false,
    "has_music": true/false,
    "dominant_audio": "speech/music/sfx/ambient",
    "overall_audio_mood": "Description of the overall audio atmosphere",
    "audio_quality": "clear/muffled/noisy/distorted",
    "key_audio_moments": ["loud sound at 2.3s", "music starts at 5.0s", "silence from 8-10s"]
  }}
}}

IMPORTANT: 
1. Create unified segments that describe BOTH visual and audio content together
2. Each segment should be a complete unit that makes sense for video editing
3. Identify natural cut points based on both audio and visual cues
4. Transcribe or summarize any important speech within each segment
5. Note any audio-visual synchronization opportunities (e.g., action matching sound)
6. Keep segments between 0.5 and 5 seconds unless there's a good reason for longer
7. Focus on creating segments that tell a story when put together"""
    
    async def _load_image(self, image_path: str) -> bytes:
        """Load image data from file or storage."""
        if self.storage and not Path(image_path).exists():
            # Load from storage
            image_io = await self.storage.download(image_path)
            return image_io.read()
        else:
            # Load from filesystem
            with open(image_path, 'rb') as f:
                return f.read()
    
    async def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_duration_sync, video_path)
    
    def _get_duration_sync(self, video_path: str) -> float:
        """Synchronously get video duration."""
        cap = cv2.VideoCapture(video_path)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            return frame_count / fps if fps > 0 else 0.0
        finally:
            cap.release()
    
    async def _call_gemini(self, prompt: str, image_data: bytes, image_path: str) -> str:
        """Call Gemini API with image and prompt."""
        try:
            if self._api_type == "vertex":
                # Vertex AI approach
                image_part = Part.from_data(image_data, mime_type="image/jpeg")
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.generate_content([prompt, image_part])
                )
                return response.text
            
            else:
                # New Gemini SDK approach
                # Upload the image file
                log_update(logger, "Uploading image file...")
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.files.upload(file=image_path)
                )
                
                # Wait for file to be processed
                while response.state.name == "PROCESSING":
                    await asyncio.sleep(1)
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.files.get(name=response.name)
                    )
                
                if response.state.name == "FAILED":
                    raise ValueError(f"Image processing failed: {response.state.name}")
                
                # Generate content
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.models.generate_content(
                        model=self._model_name,
                        contents=[prompt, response]
                    )
                )
                
                # Clean up uploaded file
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.files.delete(name=response.name)
                )
                
                return result.text
                
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    async def _call_gemini_video(self, prompt: str, video_path: str) -> str:
        """Call Gemini API with video and prompt."""
        try:
            if self._api_type == "vertex":
                # Vertex AI approach
                # Load video data
                with open(video_path, 'rb') as f:
                    video_data = f.read()
                
                mime_type, _ = mimetypes.guess_type(video_path)
                if not mime_type:
                    mime_type = "video/mp4"
                
                video_part = Part.from_data(video_data, mime_type=mime_type)
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.generate_content([prompt, video_part])
                )
                return response.text
            
            else:
                # New Gemini SDK approach
                # Upload the video file
                video_size_mb = Path(video_path).stat().st_size / (1024 * 1024)
                log_update(logger, f"Uploading video file ({video_size_mb:.1f} MB)...")
                video_file = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.files.upload(file=video_path)
                )
                
                # Wait for file to be processed
                log_update(logger, "Processing video file...")
                while video_file.state.name == "PROCESSING":
                    await asyncio.sleep(1)
                    video_file = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.files.get(name=video_file.name)
                    )
                
                if video_file.state.name == "FAILED":
                    raise ValueError(f"Video processing failed: {video_file.state.name}")
                
                # Generate content
                log_update(logger, "Analyzing video content...")
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.models.generate_content(
                        model=self._model_name,
                        contents=[prompt, video_file]
                    )
                )
                
                # Clean up uploaded file
                log_update(logger, "Cleaning up temporary files...")
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.files.delete(name=video_file.name)
                )
                
                return response.text
                
        except Exception as e:
            logger.error(f"Gemini video API call failed: {e}")
            raise
    
    def _parse_gemini_response(self, response_text: str) -> GeminiAnalysis:
        """Parse Gemini response into structured format."""
        try:
            # Extract JSON from response
            # Sometimes Gemini adds text before/after JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            # Convert to GeminiAnalysis
            analysis = GeminiAnalysis(
                description=data.get('description', ''),
                aesthetic_score=float(data.get('aesthetic_score', 0.5)),
                quality_issues=data.get('quality_issues', []),
                main_subjects=data.get('main_subjects', []),
                tags=data.get('tags', [])
            )
            
            # Add video-specific fields if present
            if 'notable_segments' in data:
                from ..models.media_asset import VideoSegment
                analysis.notable_segments = [
                    VideoSegment(**seg) for seg in data['notable_segments']
                ]
            
            if 'overall_motion' in data:
                analysis.overall_motion = data['overall_motion']
                
            if 'scene_changes' in data:
                analysis.scene_changes = data['scene_changes']
            
            # Add audio summary if present
            if 'audio_summary' in data:
                from ..models.media_asset import AudioSummary
                analysis.audio_summary = AudioSummary(**data['audio_summary'])
                
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.debug(f"Response text: {response_text}")
            
            # Return a basic analysis on parse failure
            return GeminiAnalysis(
                description="Analysis failed to parse",
                aesthetic_score=0.5,
                quality_issues=["parse_error"],
                main_subjects=[],
                tags=[]
            )


# ADK Tool wrapper
async def analyze_visual_media(file_path: str, storage: Optional[StorageInterface] = None) -> Dict[str, Any]:
    """Analyze image or video file using Gemini vision capabilities.
    
    Args:
        file_path: Path to the media file
        storage: Optional storage interface
        
    Returns:
        Dictionary with analysis results
    """
    try:
        # Determine file type first
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type or not (mime_type.startswith('image/') or mime_type.startswith('video/')):
            return {
                "status": "error",
                "error": f"Unsupported file type: {mime_type}"
            }
        
        # Reuse analyzer instance to avoid recreating clients
        global _analyzer_instance
        if _analyzer_instance is None:
            _analyzer_instance = VisualAnalysisTool(storage)
        analyzer = _analyzer_instance
        
        if mime_type.startswith('image/'):
            # Analyze as image
            analysis = await analyzer.analyze_image(file_path)
            return {
                "status": "success",
                "type": "image",
                "analysis": analysis.model_dump()
            }
        
        else:  # mime_type.startswith('video/')
            # Analyze complete video
            analysis = await analyzer.analyze_video(file_path)
            # Get video duration
            duration = await analyzer._get_video_duration(file_path)
            return {
                "status": "success",
                "type": "video",
                "analysis": analysis.model_dump(),
                "duration": duration
            }
            
    except Exception as e:
        logger.error(f"Visual analysis failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Create the ADK tool
if ADK_AVAILABLE:
    visual_analysis_tool = FunctionTool(analyze_visual_media)
else:
    visual_analysis_tool = None