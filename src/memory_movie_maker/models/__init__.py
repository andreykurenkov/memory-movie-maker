"""
Data models for Memory Movie Maker.

This module provides Pydantic models for type safety and validation
throughout the application.
"""

from .project_state import (
    ProjectState,
    UserInputs,
    AnalysisResults,
    Timeline,
    ProjectHistory,
    ProjectStatus,
)
from .media_asset import (
    MediaAsset,
    MediaType,
    VideoSegment,
    GeminiAnalysis,
    AudioAnalysisProfile,
    AudioVibe,
)
from .timeline import (
    TimelineSegment,
    TransitionType,
    RenderSettings,
)
from .analysis import (
    MediaCluster,
    MediaScore,
    ContentTag,
    QualityMetrics,
)

__all__ = [
    # Project State
    "ProjectState",
    "UserInputs",
    "AnalysisResults",
    "Timeline",
    "ProjectHistory",
    "ProjectStatus",
    # Media Assets
    "MediaAsset",
    "MediaType",
    "VideoSegment",
    "GeminiAnalysis",
    "AudioAnalysisProfile",
    "AudioVibe",
    # Timeline
    "TimelineSegment",
    "TransitionType",
    "RenderSettings",
    # Analysis
    "MediaCluster",
    "MediaScore",
    "ContentTag",
    "QualityMetrics",
]