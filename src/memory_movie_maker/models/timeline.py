"""
Timeline data models.

Defines structures for video timeline representation,
including segments, transitions, and render settings.
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator


class TransitionType(str, Enum):
    """Available transition effects between clips."""
    CUT = "cut"
    FADE = "fade"
    FADE_TO_BLACK = "fade_to_black"
    CROSSFADE = "crossfade"
    DISSOLVE = "dissolve"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


class TimelineSegment(BaseModel):
    """Single clip in the video timeline."""
    media_asset_id: str = Field(..., description="Reference to MediaAsset")
    start_time: float = Field(..., ge=0, description="Start time in timeline (seconds)")
    end_time: float = Field(..., gt=0, description="End time in timeline (seconds)")
    duration: float = Field(..., gt=0, description="Segment duration (seconds)")
    
    # Source media timing
    in_point: float = Field(0.0, ge=0, description="Start time within source media")
    out_point: Optional[float] = Field(None, description="End time within source media")
    
    # Visual effects
    transition_in: TransitionType = Field(TransitionType.CUT, description="Transition from previous clip")
    transition_out: TransitionType = Field(TransitionType.CUT, description="Transition to next clip")
    transition_duration: float = Field(0.5, ge=0, le=2.0, description="Transition duration (seconds)")
    
    # Effects and adjustments
    effects: List[str] = Field(default_factory=list, description="Applied effects")
    speed_factor: float = Field(1.0, gt=0, le=10.0, description="Playback speed multiplier")
    volume: float = Field(1.0, ge=0, le=2.0, description="Audio volume adjustment")
    
    # Layout (for multi-clip compositions)
    position: Optional[Dict[str, float]] = Field(None, description="Position override (x, y)")
    scale: float = Field(1.0, gt=0, le=10.0, description="Scale factor")
    rotation: float = Field(0.0, ge=-360, le=360, description="Rotation in degrees")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be greater than start_time')
        return v
    
    @validator('duration')
    def validate_duration(cls, v, values):
        if 'start_time' in values and 'end_time' in values:
            expected = values['end_time'] - values['start_time']
            if abs(v - expected) > 0.001:  # Allow small floating point differences
                raise ValueError(f'duration must equal end_time - start_time (expected {expected})')
        return v
    
    @validator('out_point')
    def validate_out_point(cls, v, values):
        if v is not None and 'in_point' in values and v <= values['in_point']:
            raise ValueError('out_point must be greater than in_point')
        return v


class RenderSettings(BaseModel):
    """Video rendering configuration."""
    resolution: str = Field("1920x1080", description="Output resolution (WxH)")
    fps: float = Field(30.0, gt=0, le=120, description="Frames per second")
    bitrate: str = Field("10M", description="Video bitrate (e.g., 10M, 5000k)")
    codec: str = Field("h264", description="Video codec")
    audio_codec: str = Field("aac", description="Audio codec")
    audio_bitrate: str = Field("192k", description="Audio bitrate")
    preset: str = Field("medium", description="Encoding preset (ultrafast/fast/medium/slow)")
    
    # Advanced settings
    pixel_format: str = Field("yuv420p", description="Pixel format")
    crf: Optional[int] = Field(23, ge=0, le=51, description="Constant Rate Factor (quality)")
    profile: Optional[str] = Field("high", description="Codec profile")
    level: Optional[str] = Field("4.0", description="Codec level")
    
    # Output format
    container: str = Field("mp4", description="Output container format")
    
    @validator('resolution')
    def validate_resolution(cls, v):
        try:
            width, height = v.split('x')
            int(width), int(height)
        except ValueError:
            raise ValueError('Resolution must be in format WIDTHxHEIGHT (e.g., 1920x1080)')
        return v
    
    @property
    def width(self) -> int:
        """Extract width from resolution."""
        return int(self.resolution.split('x')[0])
    
    @property
    def height(self) -> int:
        """Extract height from resolution."""
        return int(self.resolution.split('x')[1])
    
    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio."""
        return self.width / self.height


class Timeline(BaseModel):
    """Complete video timeline structure."""
    segments: List[TimelineSegment] = Field(default_factory=list, description="Ordered list of clips")
    total_duration: float = Field(0.0, ge=0, description="Total timeline duration (seconds)")
    render_settings: RenderSettings = Field(default_factory=RenderSettings, description="Rendering configuration")
    
    # Audio settings
    music_track_id: Optional[str] = Field(None, description="Background music MediaAsset ID")
    music_volume: float = Field(0.8, ge=0, le=1.0, description="Background music volume")
    ducking_enabled: bool = Field(True, description="Auto-duck music during dialogue")
    
    # Timeline metadata
    version: int = Field(1, ge=1, description="Timeline version number")
    created_at: Optional[str] = Field(None, description="When timeline was created")
    
    @validator('total_duration')
    def validate_total_duration(cls, v, values):
        if 'segments' in values and values['segments']:
            expected = max(seg.end_time for seg in values['segments'])
            if abs(v - expected) > 0.001:  # Allow small floating point differences
                raise ValueError(f'total_duration should match last segment end_time (expected {expected})')
        return v
    
    def add_segment(self, segment: TimelineSegment) -> None:
        """Add a segment and update total duration."""
        self.segments.append(segment)
        self.total_duration = max(self.total_duration, segment.end_time)
    
    def get_segment_at_time(self, time: float) -> Optional[TimelineSegment]:
        """Find segment at given time position."""
        for segment in self.segments:
            if segment.start_time <= time < segment.end_time:
                return segment
        return None
    
    def validate_continuity(self) -> List[str]:
        """Check for gaps or overlaps in timeline."""
        issues = []
        sorted_segments = sorted(self.segments, key=lambda s: s.start_time)
        
        for i in range(1, len(sorted_segments)):
            prev = sorted_segments[i-1]
            curr = sorted_segments[i]
            
            gap = curr.start_time - prev.end_time
            if gap > 0.001:  # Small gap
                issues.append(f"Gap of {gap:.3f}s between segments at {prev.end_time:.3f}s")
            elif gap < -0.001:  # Overlap
                issues.append(f"Overlap of {-gap:.3f}s between segments at {prev.end_time:.3f}s")
        
        return issues