"""Semantic audio analysis tool using Gemini API for content understanding."""

import logging
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path
import json

from pydantic import BaseModel, Field
from google import genai
from ..models.media_asset import MediaAsset
from ..config import settings
from ..storage.interface import StorageInterface


logger = logging.getLogger(__name__)


class AudioSegment(BaseModel):
    """Represents a notable segment in audio content."""
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    content: str = Field(..., description="What is said or happens in this segment")
    type: str = Field(..., description="Type: speech, music, sound_effect, silence")
    speaker: Optional[str] = Field(None, description="Speaker identification if speech")
    importance: float = Field(..., ge=0, le=1, description="Importance for video timeline")


class SemanticAudioAnalysis(BaseModel):
    """Results from Gemini semantic audio analysis."""
    transcript: Optional[str] = Field(None, description="Full transcript if speech present")
    summary: str = Field(..., description="Brief summary of audio content")
    segments: List[AudioSegment] = Field(default_factory=list, description="Notable segments")
    speakers: List[str] = Field(default_factory=list, description="Identified speakers")
    topics: List[str] = Field(default_factory=list, description="Main topics discussed")
    emotional_tone: str = Field(..., description="Overall emotional tone")
    key_moments: List[Dict[str, Any]] = Field(default_factory=list, description="Key moments for video sync")
    sound_elements: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Non-speech sounds and their timestamps or ranges"
    )


class SemanticAudioAnalysisTool:
    """Tool for semantic analysis of audio content using Gemini."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
        """Initialize the semantic audio analysis tool.
        
        Args:
            storage: Optional storage interface for accessing audio files
        """
        self.storage = storage
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model_name = "gemini-2.0-flash"
        
    async def analyze_audio_semantics(self, audio_path: str) -> SemanticAudioAnalysis:
        """Analyze audio for semantic content and meaning.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            SemanticAudioAnalysis with transcript, segments, and semantic understanding
        """
        try:
            # Upload audio file
            logger.info(f"Uploading audio file: {audio_path}")
            audio_file = await self._upload_audio(audio_path)
            
            # Generate comprehensive analysis
            analysis = await self._analyze_content(audio_file)
            
            # Clean up
            await self._cleanup_file(audio_file)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze audio semantics for {audio_path}: {e}")
            raise
    
    async def _upload_audio(self, audio_path: str) -> Any:
        """Upload audio file to Gemini."""
        loop = asyncio.get_event_loop()
        
        try:
            # Upload using the Files API
            audio_file = await loop.run_in_executor(
                None,
                lambda: self._client.files.upload(file=audio_path)
            )
            
            # Wait for processing
            while audio_file.state == "PROCESSING":
                await asyncio.sleep(1)
                audio_file = await loop.run_in_executor(
                    None,
                    lambda: self._client.files.get(name=audio_file.name)
                )
            
            if audio_file.state == "FAILED":
                raise Exception(f"Audio upload failed: {audio_file.error}")
            
            logger.info(f"Audio uploaded successfully: {audio_file.name}")
            return audio_file
            
        except Exception as e:
            logger.error(f"Failed to upload audio: {e}")
            raise
    
    async def _analyze_content(self, audio_file: Any) -> SemanticAudioAnalysis:
        """Perform comprehensive semantic analysis."""
        loop = asyncio.get_event_loop()
        
        prompt = """Analyze this audio file comprehensively for video editing purposes.

Please provide:

1. **Transcript**: Full transcript if speech is present (null if no speech)

2. **Summary**: Brief 2-3 sentence summary of the content

3. **Segments**: List of notable segments with:
   - start_time and end_time (in seconds)
   - content: what is said or happens
   - type: "speech", "music", "sound_effect", or "silence"
   - speaker: identified speaker if speech (null otherwise)
   - importance: 0-1 score for inclusion in final video

4. **Speakers**: List of identified speakers (empty if no speech)

5. **Topics**: Main topics or themes discussed

6. **Emotional Tone**: Overall emotional tone (e.g., "upbeat", "serious", "nostalgic", "dramatic")

7. **Key Moments**: Important moments for video synchronization:
   - timestamp: when it occurs
   - description: what happens
   - sync_suggestion: how to sync with video (e.g., "cut to new scene", "emphasize with slow motion")

8. **Sound Elements**: Non-speech sounds with timestamps:
   - "laughter": [timestamps]
   - "applause": [timestamps]
   - "music": [start, end timestamps]
   - etc.

Return as JSON matching this structure:
{
    "transcript": "string or null",
    "summary": "string",
    "segments": [...],
    "speakers": [...],
    "topics": [...],
    "emotional_tone": "string",
    "key_moments": [...],
    "sound_elements": {...}
}

Focus on elements that would be useful for creating an engaging video."""
        
        try:
            # Generate analysis
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self._model_name,
                    contents=[prompt, audio_file]
                )
            )
            
            # Parse response
            result_text = response.text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            # Parse JSON response
            result_data = json.loads(result_text)
            
            # Convert to SemanticAudioAnalysis
            segments = []
            for seg in result_data.get("segments", []):
                segments.append(AudioSegment(
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    content=seg["content"],
                    type=seg["type"],
                    speaker=seg.get("speaker"),
                    importance=seg["importance"]
                ))
            
            return SemanticAudioAnalysis(
                transcript=result_data.get("transcript"),
                summary=result_data["summary"],
                segments=segments,
                speakers=result_data.get("speakers", []),
                topics=result_data.get("topics", []),
                emotional_tone=result_data["emotional_tone"],
                key_moments=result_data.get("key_moments", []),
                sound_elements=result_data.get("sound_elements", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze audio content: {e}")
            # Return a basic analysis on error
            return SemanticAudioAnalysis(
                summary="Audio analysis failed",
                emotional_tone="unknown",
                segments=[],
                speakers=[],
                topics=[]
            )
    
    async def _cleanup_file(self, file: Any):
        """Clean up uploaded file."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.files.delete(name=file.name)
            )
            logger.info(f"Cleaned up file: {file.name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file: {e}")


# ADK Tool wrapper
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field

async def analyze_audio_semantics(file_path: str, storage: Optional[StorageInterface] = None) -> Dict[str, Any]:
    """Analyze audio for semantic content, speech, and meaning.
    
    Args:
        file_path: Path to audio file
        storage: Optional storage interface
        
    Returns:
        Dictionary with semantic analysis results
    """
    try:
        analyzer = SemanticAudioAnalysisTool(storage)
        analysis = await analyzer.analyze_audio_semantics(file_path)
        
        return {
            "status": "success",
            "analysis": analysis.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Semantic audio analysis failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# Create the ADK tool
semantic_audio_analysis_tool = FunctionTool(func=analyze_audio_semantics)