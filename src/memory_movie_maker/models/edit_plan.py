"""
Edit plan data models.

Defines structures for AI-generated edit plans including
segment selections, timing, and creative reasoning.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class PlannedSegment(BaseModel):
    """A single segment in an AI-planned edit."""
    media_id: str = Field(..., description="ID of the media asset to use")
    start_time: float = Field(..., ge=0, description="When this segment starts in timeline (seconds)")
    duration: float = Field(..., gt=0, le=30, description="How long to show this clip (seconds)")
    
    # Source media trimming
    trim_start: float = Field(0.0, ge=0, description="Start time within source media")
    trim_end: Optional[float] = Field(None, description="End time within source media")
    
    # Creative decisions
    transition_type: str = Field("crossfade", description="Transition from previous clip")
    effect_suggestions: List[str] = Field(default_factory=list, description="Suggested effects")
    
    # AI reasoning
    reasoning: str = Field(..., description="Why this clip was chosen for this moment")
    story_beat: Optional[str] = Field(None, description="Narrative purpose (intro, development, climax, etc.)")
    energy_match: Optional[float] = Field(None, ge=0, le=1, description="How well it matches music energy")
    
    @validator('trim_end')
    def validate_trim_end(cls, v, values):
        if v is not None and 'trim_start' in values and v <= values['trim_start']:
            raise ValueError('trim_end must be greater than trim_start')
        return v
    
    @validator('duration')
    def validate_duration_matches_trim(cls, v, values):
        if 'trim_start' in values and values.get('trim_end') is not None:
            trim_duration = values['trim_end'] - values['trim_start']
            if abs(v - trim_duration) > 0.1:  # Allow small difference
                raise ValueError(f'duration should match trim duration ({trim_duration:.1f}s)')
        return v


class EditPlan(BaseModel):
    """Complete AI-generated edit plan."""
    segments: List[PlannedSegment] = Field(..., description="Ordered list of planned segments")
    total_duration: float = Field(..., gt=0, description="Total planned duration")
    
    # Creative overview
    narrative_structure: str = Field(..., description="Overall story structure")
    pacing_strategy: str = Field(..., description="How pacing will work")
    music_sync_notes: Optional[str] = Field(None, description="How edit syncs with music")
    
    # Metrics
    variety_score: float = Field(..., ge=0, le=1, description="How varied the clip selection is")
    story_coherence: float = Field(..., ge=0, le=1, description="How well it tells a story")
    technical_quality: float = Field(..., ge=0, le=1, description="Average quality of selected clips")
    
    # Metadata
    created_by: str = Field("gemini-2.0-flash", description="Model that created the plan")
    reasoning_summary: str = Field(..., description="Overall reasoning for the edit")
    
    @validator('total_duration')
    def validate_total_duration(cls, v, values):
        if 'segments' in values and values['segments']:
            calculated = sum(seg.duration for seg in values['segments'])
            if abs(v - calculated) > 0.1:
                raise ValueError(f'total_duration should be {calculated:.1f}s based on segments')
        return v
    
    def get_segment_at_time(self, time: float) -> Optional[PlannedSegment]:
        """Find which segment is playing at a given time."""
        current_time = 0.0
        for segment in self.segments:
            if current_time <= time < current_time + segment.duration:
                return segment
            current_time += segment.duration
        return None
    
    def get_story_arc(self) -> Dict[str, List[PlannedSegment]]:
        """Group segments by story beat."""
        arc = {}
        for segment in self.segments:
            beat = segment.story_beat or "unspecified"
            if beat not in arc:
                arc[beat] = []
            arc[beat].append(segment)
        return arc
    
    def get_media_usage(self) -> Dict[str, float]:
        """Calculate total screen time per media asset."""
        usage = {}
        for segment in self.segments:
            if segment.media_id not in usage:
                usage[segment.media_id] = 0.0
            usage[segment.media_id] += segment.duration
        return usage