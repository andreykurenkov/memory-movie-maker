"""
Project state data model.

The central data structure that flows through all agents,
maintaining the complete state of a video creation project.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, ClassVar, Union
from pydantic import BaseModel, Field, validator
import uuid

from .media_asset import MediaAsset, AudioAnalysisProfile
from .timeline import Timeline
from .analysis import AnalysisSession
from .aspect_ratio import AspectRatio


class UserInputs(BaseModel):
    """User-provided inputs and preferences."""
    media: List[MediaAsset] = Field(default_factory=list, description="Uploaded media files")
    music: List[MediaAsset] = Field(default_factory=list, description="Music tracks")
    initial_prompt: str = Field(..., description="User's initial description")
    target_duration: int = Field(120, gt=0, le=600, description="Target video duration in seconds")
    aspect_ratio: Union[AspectRatio, str] = Field(AspectRatio.WIDESCREEN, description="Video aspect ratio")
    style_preferences: Dict[str, Any] = Field(default_factory=dict, description="Style preferences")
    
    @validator('aspect_ratio', pre=True)
    def validate_aspect_ratio(cls, v):
        """Convert string to AspectRatio enum if needed."""
        if isinstance(v, str):
            try:
                return AspectRatio.from_string(v)
            except ValueError as e:
                # List valid options in error message
                valid_options = [ratio.value for ratio in AspectRatio]
                raise ValueError(f'Aspect ratio must be one of: {", ".join(valid_options)}')
        return v
    
    @property
    def total_media_count(self) -> int:
        """Total number of media files."""
        return len(self.media) + len(self.music)


class AnalysisResults(BaseModel):
    """Results from media analysis phase."""
    music_profiles: List[AudioAnalysisProfile] = Field(default_factory=list, description="Analyzed music")
    media_pool: List[MediaAsset] = Field(default_factory=list, description="Analyzed media with scores")
    analysis_timestamp: Optional[datetime] = Field(None, description="When analysis completed")
    analysis_session: Optional[AnalysisSession] = Field(None, description="Analysis session details")
    
    # Derived insights
    dominant_mood: Optional[str] = Field(None, description="Overall mood from analysis")
    suggested_pacing: Optional[str] = Field(None, description="Suggested video pacing")
    quality_distribution: Dict[str, int] = Field(default_factory=dict, description="Quality score distribution")
    
    def mark_analyzed(self) -> None:
        """Mark analysis as complete."""
        self.analysis_timestamp = datetime.utcnow()
        if self.analysis_session:
            self.analysis_session.mark_completed()


class ProjectHistory(BaseModel):
    """Track all interactions and versions."""
    prompts: List[Dict[str, Any]] = Field(default_factory=list, description="User prompts history")
    versions: List[Dict[str, Any]] = Field(default_factory=list, description="Generated versions")
    feedback: List[Dict[str, Any]] = Field(default_factory=list, description="User feedback")
    
    def add_prompt(self, prompt: str, prompt_type: str = "user") -> None:
        """Add a new prompt to history."""
        self.prompts.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": prompt_type,
            "content": prompt
        })
    
    def add_version(self, timeline: Timeline, metadata: Dict[str, Any] = None) -> int:
        """Add a new version and return version number."""
        version_num = len(self.versions) + 1
        self.versions.append({
            "version": version_num,
            "timestamp": datetime.utcnow().isoformat(),
            "timeline": timeline.dict(),
            "metadata": metadata or {}
        })
        return version_num
    
    def add_feedback(self, feedback: str, version: int, sentiment: Optional[str] = None) -> None:
        """Add user feedback for a version."""
        self.feedback.append({
            "timestamp": datetime.utcnow().isoformat(),
            "version": version,
            "content": feedback,
            "sentiment": sentiment
        })


class ProjectStatus(BaseModel):
    """Current project processing status."""
    phase: str = Field("initialized", description="Current processing phase")
    progress: float = Field(0.0, ge=0, le=100, description="Progress percentage")
    current_version: int = Field(0, ge=0, description="Current video version")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    # Phase tracking
    phase_history: List[Dict[str, Any]] = Field(default_factory=list, description="Phase transition history")
    
    # Valid phases
    VALID_PHASES: ClassVar[List[str]] = [
        "initialized",
        "uploading",
        "analyzing",
        "composing",
        "rendering",
        "evaluating",
        "refining",
        "completed",
        "error"
    ]
    
    @validator('phase')
    def validate_phase(cls, v):
        if v not in cls.VALID_PHASES:
            raise ValueError(f'Phase must be one of: {", ".join(cls.VALID_PHASES)}')
        return v
    
    def update_phase(self, new_phase: str, progress: float = None) -> None:
        """Update phase and track history."""
        if new_phase not in self.VALID_PHASES:
            raise ValueError(f'Invalid phase: {new_phase}')
        
        # Track phase transition
        self.phase_history.append({
            "from_phase": self.phase,
            "to_phase": new_phase,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        self.phase = new_phase
        if progress is not None:
            self.progress = progress
    
    @property
    def is_processing(self) -> bool:
        """Check if currently processing."""
        return self.phase not in ["initialized", "completed", "error"]
    
    @property
    def is_complete(self) -> bool:
        """Check if processing is complete."""
        return self.phase == "completed"
    
    @property
    def has_error(self) -> bool:
        """Check if an error occurred."""
        return self.phase == "error" or self.error is not None


class ProjectState(BaseModel):
    """Complete project state - the source of truth."""
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique project ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Project creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    # Core components
    user_inputs: UserInputs = Field(..., description="User-provided inputs")
    analysis: AnalysisResults = Field(default_factory=AnalysisResults, description="Analysis results")
    timeline: Timeline = Field(default_factory=Timeline, description="Current timeline")
    history: ProjectHistory = Field(default_factory=ProjectHistory, description="Interaction history")
    status: ProjectStatus = Field(default_factory=ProjectStatus, description="Current status")
    
    # Project metadata
    name: Optional[str] = Field(None, description="User-friendly project name")
    description: Optional[str] = Field(None, description="Project description")
    tags: List[str] = Field(default_factory=list, description="Project tags")
    
    # Storage references
    storage_path: Optional[str] = Field(None, description="Base storage path")
    output_path: Optional[str] = Field(None, description="Final video output path")
    rendered_outputs: List[str] = Field(default_factory=list, description="List of rendered video paths")
    
    # Evaluation and refinement
    evaluation_results: Optional[Dict[str, Any]] = Field(None, description="Latest evaluation results")
    analysis_cache_enabled: bool = Field(True, description="Whether to use cached analysis results")
    ai_analysis_log_path: Optional[str] = Field(None, description="Path to AI analysis log file")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.utcnow()
    
    def get_current_timeline(self) -> Timeline:
        """Get the current timeline."""
        return self.timeline
    
    def validate_state(self) -> List[str]:
        """Validate the project state and return list of issues.
        
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check timeline references valid media
        if self.timeline and self.timeline.segments:
            media_ids = {m.id for m in self.user_inputs.media}
            for i, segment in enumerate(self.timeline.segments):
                if segment.media_asset_id not in media_ids:
                    errors.append(f"Timeline segment {i} references invalid media ID: {segment.media_asset_id}")
                
                # Check segment timing
                if segment.end_time <= segment.start_time:
                    errors.append(f"Timeline segment {i} has invalid timing: end <= start")
                
                # Check trim points are within media duration
                media = self.get_media_by_id(segment.media_asset_id)
                if media and media.duration:
                    if segment.in_point >= media.duration:
                        errors.append(f"Timeline segment {i} in_point exceeds media duration")
                    if segment.out_point and segment.out_point > media.duration:
                        errors.append(f"Timeline segment {i} out_point exceeds media duration")
        
        # Check evaluation results match current video
        if self.evaluation_results and self.rendered_outputs:
            # Just a basic check that we have outputs
            if not self.rendered_outputs:
                errors.append("Evaluation results exist but no rendered outputs")
        
        # Check status phase is valid
        if self.status and self.status.phase not in ProjectStatus.VALID_PHASES:
            errors.append(f"Invalid project phase: {self.status.phase}")
        
        return errors
    
    def get_media_by_id(self, media_id: str) -> Optional[MediaAsset]:
        """Find media asset by ID."""
        # Check user inputs
        for media in self.user_inputs.media + self.user_inputs.music:
            if media.id == media_id:
                return media
        
        # Check analyzed media pool
        for media in self.analysis.media_pool:
            if media.id == media_id:
                return media
        
        return None
    
    def get_latest_version(self) -> Optional[Dict[str, Any]]:
        """Get the latest generated version."""
        if self.history.versions:
            return self.history.versions[-1]
        return None
    
    def to_summary(self) -> Dict[str, Any]:
        """Create a summary view of the project."""
        return {
            "project_id": self.project_id,
            "name": self.name or f"Project {self.project_id[:8]}",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": {
                "phase": self.status.phase,
                "progress": self.status.progress,
                "is_complete": self.status.is_complete
            },
            "media_count": self.user_inputs.total_media_count,
            "target_duration": self.user_inputs.target_duration,
            "current_version": self.status.current_version,
            "has_output": self.output_path is not None
        }
    
    @validator('timeline')
    def validate_timeline_references(cls, v, values):
        """Ensure timeline references valid media assets."""
        # Only validate if we have a timeline with segments
        if not v or not v.segments:
            return v
        
        # Only validate if analysis is complete (has media_pool)
        # During initialization, we may not have all data yet
        if 'user_inputs' in values and 'analysis' in values:
            # Build list of valid media IDs
            valid_ids = set()
            
            # Add user input media
            if values['user_inputs'].media:
                valid_ids.update(m.id for m in values['user_inputs'].media)
            if values['user_inputs'].music:
                valid_ids.update(m.id for m in values['user_inputs'].music)
            
            # Add analyzed media if available
            if values['analysis'] and values['analysis'].media_pool:
                valid_ids.update(m.id for m in values['analysis'].media_pool)
            
            # Only validate if we have some valid IDs to check against
            if valid_ids:
                for segment in v.segments:
                    if segment.media_asset_id not in valid_ids:
                        # Log warning instead of raising during partial state
                        import logging
                        logging.warning(f'Timeline segment references media ID not yet in pool: {segment.media_asset_id}')
                        # Don't raise - allow partial states during processing
        
        return v