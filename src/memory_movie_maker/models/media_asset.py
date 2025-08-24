"""
Media asset data models.

Defines structures for representing media files (images, videos, audio)
and their associated metadata and analysis results.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class MediaType(str, Enum):
    """Supported media file types."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class VideoSegment(BaseModel):
    """Notable segment or event within a video."""
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    description: str = Field(..., description="Complete description of segment")
    importance: float = Field(..., ge=0, le=1, description="Importance score for timeline inclusion")
    tags: List[str] = Field(default_factory=list, description="Segment tags")
    
    # Detailed content breakdown
    visual_content: Optional[str] = Field(None, description="What is shown visually")
    audio_content: Optional[str] = Field(None, description="What is heard")
    audio_type: Optional[str] = Field(None, description="Type: speech/music/sfx/ambient/mixed/silence")
    
    # Speech-specific fields (if applicable)
    speaker: Optional[str] = Field(None, description="Speaker identifier if speech present")
    speech_content: Optional[str] = Field(None, description="Transcription or summary of speech")
    
    # Music-specific fields (if applicable)
    music_description: Optional[str] = Field(None, description="Music genre, mood, tempo if present")
    
    # Editing guidance
    emotional_tone: Optional[str] = Field(None, description="Emotional tone: happy/sad/exciting/calm/tense/neutral")
    sync_priority: Optional[float] = Field(None, ge=0, le=1, description="Audio-visual sync importance")
    recommended_action: Optional[str] = Field(None, description="Editing recommendation: cut_here/hold/transition/sync_to_beat")
    
    @validator('end_time')
    def validate_times(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class AudioSummary(BaseModel):
    """Summary of audio content in a video."""
    has_speech: bool = Field(False, description="Whether video contains speech")
    has_music: bool = Field(False, description="Whether video contains music")
    dominant_audio: Optional[str] = Field(None, description="Main audio type: speech/music/sfx/ambient")
    overall_audio_mood: Optional[str] = Field(None, description="Overall audio atmosphere")
    audio_quality: str = Field("clear", description="Audio quality: clear/muffled/noisy/distorted")
    key_audio_moments: List[str] = Field(default_factory=list, description="Notable audio events with timestamps")


class GeminiAnalysis(BaseModel):
    """Structured output from Gemini visual analysis."""
    description: str = Field(..., description="Brief description of content")
    aesthetic_score: float = Field(..., ge=0, le=1, description="Visual quality score")
    quality_issues: List[str] = Field(default_factory=list, description="Detected quality problems")
    main_subjects: List[str] = Field(default_factory=list, description="Primary subjects in frame")
    tags: List[str] = Field(default_factory=list, description="Content tags for categorization")
    
    # Video-specific fields
    notable_segments: List[VideoSegment] = Field(default_factory=list, description="Notable video segments")
    overall_motion: Optional[str] = Field(None, description="Overall motion characterization")
    scene_changes: List[float] = Field(default_factory=list, description="Timestamps of major scene changes")
    
    # Audio summary for videos
    audio_summary: Optional[AudioSummary] = Field(None, description="Summary of audio content in video")
    
    # LLM prompt used (excluded from serialization for LLM inputs)
    llm_prompt: Optional[str] = Field(None, exclude=True, description="Prompt sent to LLM")


class AudioVibe(BaseModel):
    """Musical characteristics and mood analysis."""
    danceability: float = Field(..., ge=0, le=1, description="How suitable for dancing")
    energy: float = Field(..., ge=0, le=1, description="Perceived energy level")
    valence: float = Field(0.5, ge=0, le=1, description="Musical positivity/happiness")
    arousal: float = Field(0.5, ge=0, le=1, description="Excitement/intensity level")
    mood: str = Field(..., description="Primary mood descriptor")
    genre: Optional[str] = Field(None, description="Detected music genre")


class AudioAnalysisProfile(BaseModel):
    """Audio track analysis results from Librosa."""
    file_path: str = Field(..., description="Path to audio file")
    beat_timestamps: List[float] = Field(..., description="Detected beat positions in seconds")
    tempo_bpm: float = Field(..., gt=0, description="Tempo in beats per minute")
    energy_curve: List[float] = Field(..., description="Energy levels over time (0-1)")
    duration: float = Field(..., gt=0, description="Total duration in seconds")
    vibe: AudioVibe = Field(..., description="Musical characteristics")
    key: Optional[str] = Field(None, description="Detected musical key")
    time_signature: Optional[str] = Field(None, description="Time signature (e.g., 4/4)")
    sections: List[Dict[str, Any]] = Field(default_factory=list, description="Song structure analysis")
    
    @validator('energy_curve')
    def validate_energy_curve(cls, v):
        if any(val < 0 or val > 1 for val in v):
            raise ValueError('All energy values must be between 0 and 1')
        return v


class MediaAsset(BaseModel):
    """Individual media file representation."""
    id: str = Field(..., description="Unique identifier")
    file_path: str = Field(..., description="Path to media file")
    type: MediaType = Field(..., description="Media file type")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When file was uploaded")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata (EXIF, etc.)")
    
    # Analysis results
    gemini_analysis: Optional[GeminiAnalysis] = Field(None, description="Visual analysis results")
    audio_analysis: Optional[AudioAnalysisProfile] = Field(None, description="Audio analysis results")
    semantic_audio_analysis: Optional[Dict[str, Any]] = Field(None, description="Semantic audio analysis results")
    
    # User preferences
    required: bool = Field(False, description="Must be included in final video")
    excluded: bool = Field(False, description="Should not be used")
    
    # Computed properties
    @property
    def is_analyzed(self) -> bool:
        """Check if media has been analyzed."""
        if self.type == MediaType.AUDIO:
            return self.audio_analysis is not None
        else:
            return self.gemini_analysis is not None
    
    @property
    def quality_score(self) -> float:
        """Get quality score from analysis."""
        if self.gemini_analysis:
            return self.gemini_analysis.aesthetic_score
        return 0.5  # Default neutral score
    
    @property
    def duration(self) -> Optional[float]:
        """Get media duration if available."""
        if self.type == MediaType.VIDEO:
            return self.metadata.get('duration')
        elif self.type == MediaType.AUDIO and self.audio_analysis:
            return self.audio_analysis.duration
        return None
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }