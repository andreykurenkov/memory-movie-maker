"""
Analysis data models.

Defines structures for media analysis results,
clustering, scoring, and content categorization.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class ContentTag(BaseModel):
    """Content categorization tag with confidence."""
    name: str = Field(..., description="Tag name (e.g., 'sunset', 'family')")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    source: str = Field("gemini", description="Source of the tag (gemini, user, auto)")
    
    def __hash__(self):
        """Make tags hashable for set operations."""
        return hash((self.name, self.source))
    
    def __eq__(self, other):
        """Tags are equal if name and source match."""
        if isinstance(other, ContentTag):
            return self.name == other.name and self.source == other.source
        return False


class QualityMetrics(BaseModel):
    """Detailed quality assessment metrics."""
    sharpness: float = Field(0.5, ge=0, le=1, description="Image sharpness score")
    exposure: float = Field(0.5, ge=0, le=1, description="Exposure quality score")
    composition: float = Field(0.5, ge=0, le=1, description="Composition score")
    color_balance: float = Field(0.5, ge=0, le=1, description="Color balance score")
    noise_level: float = Field(0.5, ge=0, le=1, description="Noise level (lower is better)")
    
    # Video-specific metrics
    stability: Optional[float] = Field(None, ge=0, le=1, description="Video stability score")
    motion_blur: Optional[float] = Field(None, ge=0, le=1, description="Motion blur score")
    
    @property
    def overall_score(self) -> float:
        """Calculate overall quality score."""
        scores = [self.sharpness, self.exposure, self.composition, self.color_balance, 1 - self.noise_level]
        if self.stability is not None:
            scores.append(self.stability)
        if self.motion_blur is not None:
            scores.append(1 - self.motion_blur)
        return sum(scores) / len(scores)


class MediaScore(BaseModel):
    """Comprehensive scoring for media selection."""
    media_asset_id: str = Field(..., description="Reference to MediaAsset")
    
    # Individual scores
    aesthetic_score: float = Field(..., ge=0, le=1, description="Visual appeal score")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance to user intent")
    technical_score: float = Field(..., ge=0, le=1, description="Technical quality score")
    uniqueness_score: float = Field(..., ge=0, le=1, description="Uniqueness in media pool")
    
    # Contextual scores
    temporal_score: float = Field(0.5, ge=0, le=1, description="Temporal relevance (chronology)")
    emotional_score: float = Field(0.5, ge=0, le=1, description="Emotional impact score")
    
    # Computed weights
    weight: float = Field(1.0, gt=0, description="Final selection weight")
    
    @validator('weight')
    def calculate_weight(cls, v, values):
        """Calculate final weight from individual scores."""
        scores = [
            values.get('aesthetic_score', 0.5),
            values.get('relevance_score', 0.5),
            values.get('technical_score', 0.5),
            values.get('uniqueness_score', 0.5),
            values.get('temporal_score', 0.5),
            values.get('emotional_score', 0.5)
        ]
        # Weighted average with emphasis on aesthetic and relevance
        weights = [0.25, 0.25, 0.15, 0.15, 0.1, 0.1]
        return sum(s * w for s, w in zip(scores, weights))


class MediaCluster(BaseModel):
    """Group of related media assets."""
    id: str = Field(..., description="Cluster identifier")
    name: str = Field(..., description="Cluster name/description")
    media_asset_ids: List[str] = Field(..., description="IDs of media in cluster")
    
    # Cluster characteristics
    time_range: Optional[Dict[str, datetime]] = Field(None, description="Time span of media")
    dominant_tags: List[ContentTag] = Field(default_factory=list, description="Most common tags")
    dominant_subjects: List[str] = Field(default_factory=list, description="Main subjects")
    avg_quality_score: float = Field(0.5, ge=0, le=1, description="Average quality in cluster")
    
    # Cluster metadata
    cluster_type: str = Field("temporal", description="Type: temporal, thematic, quality")
    coherence_score: float = Field(0.5, ge=0, le=1, description="How well items fit together")
    
    def add_media(self, media_id: str) -> None:
        """Add media to cluster."""
        if media_id not in self.media_asset_ids:
            self.media_asset_ids.append(media_id)
    
    def remove_media(self, media_id: str) -> None:
        """Remove media from cluster."""
        if media_id in self.media_asset_ids:
            self.media_asset_ids.remove(media_id)
    
    @property
    def size(self) -> int:
        """Number of media items in cluster."""
        return len(self.media_asset_ids)


class AnalysisSession(BaseModel):
    """Track analysis batch operations."""
    session_id: str = Field(..., description="Analysis session identifier")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    
    # Progress tracking
    total_items: int = Field(..., ge=0, description="Total items to analyze")
    completed_items: int = Field(0, ge=0, description="Items analyzed so far")
    failed_items: int = Field(0, ge=0, description="Failed analysis attempts")
    
    # Results
    media_scores: Dict[str, MediaScore] = Field(default_factory=dict)
    clusters: List[MediaCluster] = Field(default_factory=list)
    quality_metrics: Dict[str, QualityMetrics] = Field(default_factory=dict)
    
    # Performance metrics
    avg_analysis_time: float = Field(0.0, ge=0, description="Average time per item (seconds)")
    total_api_calls: int = Field(0, ge=0, description="Total API calls made")
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def success_rate(self) -> float:
        """Calculate analysis success rate."""
        total_processed = self.completed_items + self.failed_items
        if total_processed == 0:
            return 0.0
        return (self.completed_items / total_processed) * 100
    
    def mark_completed(self) -> None:
        """Mark session as completed."""
        self.completed_at = datetime.utcnow()