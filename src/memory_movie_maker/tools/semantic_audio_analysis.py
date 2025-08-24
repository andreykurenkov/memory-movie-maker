"""Semantic audio analysis tool using Gemini API for content understanding."""

import logging
from typing import Dict, Any, List, Optional
import asyncio
import json

from pydantic import BaseModel, Field
from google import genai
from ..config import settings
from ..storage.interface import StorageInterface
from ..utils.ai_output_logger import ai_logger


logger = logging.getLogger(__name__)


class AudioSegment(BaseModel):
    """Represents a notable segment in audio content."""
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    content: str = Field(..., description="What is said or happens in this segment")
    type: str = Field(..., description="Type: speech, music, sound_effect, silence, intro, verse, chorus, bridge, outro, drop, buildup")
    speaker: Optional[str] = Field(None, description="Speaker identification if speech")
    importance: float = Field(..., ge=0, le=1, description="Importance for video timeline")
    
    # Musical structure fields
    musical_structure: Optional[str] = Field(None, description="Musical section type: intro, verse, chorus, bridge, outro, drop, buildup, break")
    energy_transition: Optional[str] = Field(None, description="Energy change: building, dropping, steady, peak, valley")
    musical_elements: Optional[List[str]] = Field(None, description="Active elements: vocals, drums, bass, melody, harmony, effects")
    tempo_change: Optional[str] = Field(None, description="Tempo change if any: accelerating, decelerating, steady")
    sync_priority: Optional[float] = Field(None, ge=0, le=1, description="Priority for video sync (1.0 = must sync here)")


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
    
    # Musical structure overview (for music files)
    musical_structure_summary: Optional[str] = Field(None, description="Overview of song structure")
    energy_peaks: Optional[List[float]] = Field(None, description="Timestamps of energy peaks for impact moments")
    recommended_cut_points: Optional[List[float]] = Field(None, description="Best timestamps for video cuts")
    
    # LLM prompt used (excluded from serialization for LLM inputs)
    llm_prompt: Optional[str] = Field(None, exclude=True, description="Prompt sent to LLM")


class SemanticAudioAnalysisTool:
    """Tool for semantic analysis of audio content using Gemini."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
        """Initialize the semantic audio analysis tool.
        
        Args:
            storage: Optional storage interface for accessing audio files
        """
        self.storage = storage
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model_name = settings.get_gemini_model_name()
        
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
            
            # Wait for processing with timeout
            max_retries = 60  # Max 60 seconds wait
            retry_count = 0
            wait_time = 1  # Start with 1 second
            
            while audio_file.state == "PROCESSING" and retry_count < max_retries:
                await asyncio.sleep(wait_time)
                retry_count += 1
                
                # Exponential backoff up to 5 seconds
                wait_time = min(wait_time * 1.2, 5)
                
                if audio_file and hasattr(audio_file, 'name'):
                    audio_file = await loop.run_in_executor(
                        None,
                        lambda: self._client.files.get(name=audio_file.name)
                    )
            
            if retry_count >= max_retries:
                raise Exception(f"Audio upload timed out after {max_retries} seconds")
            
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
        
        prompt = """Analyze this audio file comprehensively for video editing purposes. Pay special attention to musical structure and transitions for synchronization.

Please provide:

1. **Transcript**: Full transcript if speech is present (null if no speech)

2. **Summary**: Brief 2-3 sentence summary of the content

3. **Segments**: List of ALL notable segments with precise timing:
   - start_time and end_time (in seconds, be very precise)
   - content: what is said or happens in this segment
   - type: "speech", "music", "sound_effect", "silence", "intro", "verse", "chorus", "bridge", "outro", "drop", "buildup"
   - speaker: identified speaker if speech (null otherwise)
   - importance: 0-1 score for inclusion in final video
   
   For MUSIC segments, also include:
   - musical_structure: "intro", "verse", "chorus", "bridge", "outro", "drop", "buildup", "break", etc.
   - energy_transition: "building", "dropping", "steady", "peak", "valley"
   - musical_elements: ["vocals", "drums", "bass", "melody", "harmony", "effects"] (active elements)
   - tempo_change: "accelerating", "decelerating", "steady" (if tempo changes)
   - sync_priority: 0-1 score for how important this moment is for video sync (1.0 = must sync)

4. **Speakers**: List of identified speakers (empty if no speech)

5. **Topics**: Main topics or themes (for speech) OR musical themes/moods (for music)

6. **Emotional Tone**: Overall emotional tone (e.g., "upbeat", "melancholic", "energetic", "peaceful", "dramatic", "euphoric")

7. **Key Moments**: Important moments for video synchronization with EXACT timestamps:
   - timestamp: exact time in seconds when it occurs
   - description: what happens (e.g., "beat drops", "chorus starts", "energy peak", "tempo change")
   - sync_suggestion: specific video editing suggestion (e.g., "hard cut on beat", "start slow motion", "transition to new scene")

8. **Sound Elements**: Non-speech sounds with precise timestamps:
   - "laughter": [timestamps]
   - "applause": [timestamps]
   - "music": [start, end timestamps]
   - "silence": [start, end timestamps]
   - etc.

9. **Musical Structure Summary**: (for music files) Brief overview like "Intro (0-15s) → Verse 1 (15-45s) → Chorus (45-75s)..."

10. **Energy Peaks**: (for music files) List of exact timestamps where energy/intensity peaks for impact moments

11. **Recommended Cut Points**: (for music files) List of ideal timestamps for video cuts based on rhythm and structure

Return as JSON matching this structure:
{
    "transcript": "string or null",
    "summary": "string",
    "segments": [
        {
            "start_time": 0.0,
            "end_time": 15.5,
            "content": "Instrumental intro with building energy",
            "type": "intro",
            "speaker": null,
            "importance": 0.8,
            "musical_structure": "intro",
            "energy_transition": "building",
            "musical_elements": ["drums", "bass", "effects"],
            "tempo_change": "steady",
            "sync_priority": 0.9
        }
    ],
    "speakers": [...],
    "topics": [...],
    "emotional_tone": "string",
    "key_moments": [...],
    "sound_elements": {...},
    "musical_structure_summary": "string or null",
    "energy_peaks": [15.2, 45.7, 76.3] or null,
    "recommended_cut_points": [4.0, 8.0, 15.5, 30.0] or null
}

Be extremely precise with timestamps - video editors need exact frame-accurate timing. Identify EVERY musical transition, beat drop, chorus entry, and energy shift."""
        
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
            result_text = response.text if hasattr(response, 'text') else str(response)
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            # Parse JSON response
            result_data = json.loads(result_text)
            
            # Convert to SemanticAudioAnalysis
            segments = []
            for seg in result_data.get("segments", []):
                segment = AudioSegment(
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    content=seg["content"],
                    type=seg["type"],
                    speaker=seg.get("speaker"),
                    importance=seg["importance"],
                    # Musical structure fields
                    musical_structure=seg.get("musical_structure"),
                    energy_transition=seg.get("energy_transition"),
                    musical_elements=seg.get("musical_elements"),
                    tempo_change=seg.get("tempo_change"),
                    sync_priority=seg.get("sync_priority")
                )
                segments.append(segment)
            
            return SemanticAudioAnalysis(
                transcript=result_data.get("transcript"),
                summary=result_data["summary"],
                segments=segments,
                speakers=result_data.get("speakers", []),
                topics=result_data.get("topics", []),
                emotional_tone=result_data["emotional_tone"],
                key_moments=result_data.get("key_moments", []),
                sound_elements=result_data.get("sound_elements", {}),
                # Musical structure overview fields
                musical_structure_summary=result_data.get("musical_structure_summary"),
                energy_peaks=result_data.get("energy_peaks"),
                recommended_cut_points=result_data.get("recommended_cut_points"),
                # Include the prompt
                llm_prompt=prompt
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze audio content: {e}")
            # Return a basic analysis on error
            return SemanticAudioAnalysis(
                transcript=None,
                summary="Audio analysis failed",
                emotional_tone="unknown",
                segments=[],
                speakers=[],
                topics=[],
                key_moments=[],
                sound_elements={},
                musical_structure_summary=None,
                energy_peaks=None,
                recommended_cut_points=None,
                llm_prompt=prompt if 'prompt' in locals() else None
            )
    
    async def _cleanup_file(self, file: Any) -> None:
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
        
        # Log to AI output logger (extract prompt from analysis)
        ai_logger.log_audio_analysis(
            file_path=file_path,
            analysis_type="semantic",
            analysis=analysis.model_dump(exclude={'llm_prompt'}),  # Exclude prompt from the analysis dict
            prompt=analysis.llm_prompt,
            raw_response=None  # Could capture raw response if needed
        )
        
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
semantic_audio_analysis_tool = FunctionTool(analyze_audio_semantics)