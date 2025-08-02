"""
Unit tests for data models.

Tests Pydantic model validation, computed properties,
and business logic methods.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from memory_movie_maker.models import (
    # Media Assets
    MediaAsset,
    MediaType,
    GeminiAnalysis,
    AudioAnalysisProfile,
    AudioVibe,
    # Timeline
    TimelineSegment,
    TransitionType,
    RenderSettings,
    Timeline,
    # Analysis
    ContentTag,
    QualityMetrics,
    MediaScore,
    MediaCluster,
    # Project State
    ProjectState,
    UserInputs,
    AnalysisResults,
    ProjectHistory,
    ProjectStatus,
)


class TestMediaAsset:
    """Test MediaAsset model."""
    
    def test_create_image_asset(self):
        """Test creating an image media asset."""
        asset = MediaAsset(
            id="img_001",
            file_path="/path/to/image.jpg",
            type=MediaType.IMAGE,
            metadata={"width": 1920, "height": 1080}
        )
        
        assert asset.id == "img_001"
        assert asset.type == "image"
        assert not asset.is_analyzed
        assert asset.quality_score == 0.5  # Default
    
    def test_create_video_asset(self):
        """Test creating a video media asset."""
        asset = MediaAsset(
            id="vid_001",
            file_path="/path/to/video.mp4",
            type=MediaType.VIDEO,
            metadata={"duration": 30.5, "fps": 30}
        )
        
        assert asset.type == "video"
        assert asset.duration == 30.5
    
    def test_analyzed_asset(self):
        """Test asset with analysis results."""
        analysis = GeminiAnalysis(
            description="Beautiful sunset",
            aesthetic_score=0.9,
            tags=["sunset", "nature"],
            main_subjects=["sky", "sun"]
        )
        
        asset = MediaAsset(
            id="img_002",
            file_path="/path/to/sunset.jpg",
            type=MediaType.IMAGE,
            gemini_analysis=analysis
        )
        
        assert asset.is_analyzed
        assert asset.quality_score == 0.9
    
    def test_invalid_motion_level(self):
        """Test invalid motion level validation."""
        with pytest.raises(ValidationError):
            GeminiAnalysis(
                description="Test",
                aesthetic_score=0.5,
                motion_level="super-fast"  # Invalid
            )


class TestTimeline:
    """Test Timeline models."""
    
    def test_create_timeline_segment(self):
        """Test creating a timeline segment."""
        segment = TimelineSegment(
            media_asset_id="img_001",
            start_time=0.0,
            end_time=5.0,
            duration=5.0,
            transition_in=TransitionType.FADE
        )
        
        assert segment.duration == 5.0
        assert segment.transition_in == "fade"
    
    def test_invalid_segment_times(self):
        """Test segment time validation."""
        with pytest.raises(ValidationError):
            TimelineSegment(
                media_asset_id="img_001",
                start_time=5.0,
                end_time=3.0,  # End before start
                duration=2.0
            )
    
    def test_render_settings(self):
        """Test render settings validation."""
        settings = RenderSettings(
            resolution="1920x1080",
            fps=30.0,
            bitrate="10M"
        )
        
        assert settings.width == 1920
        assert settings.height == 1080
        assert settings.aspect_ratio == pytest.approx(16/9)
    
    def test_invalid_resolution(self):
        """Test invalid resolution format."""
        with pytest.raises(ValidationError):
            RenderSettings(resolution="1920p")  # Invalid format
    
    def test_timeline_continuity(self):
        """Test timeline continuity checking."""
        timeline = Timeline()
        
        # Add segments with gap
        timeline.add_segment(TimelineSegment(
            media_asset_id="img_001",
            start_time=0.0,
            end_time=5.0,
            duration=5.0
        ))
        
        timeline.add_segment(TimelineSegment(
            media_asset_id="img_002",
            start_time=6.0,  # Gap of 1 second
            end_time=10.0,
            duration=4.0
        ))
        
        issues = timeline.validate_continuity()
        assert len(issues) == 1
        assert "Gap of 1.000s" in issues[0]


class TestAnalysisModels:
    """Test analysis-related models."""
    
    def test_content_tag_hashing(self):
        """Test content tags can be used in sets."""
        tag1 = ContentTag(name="sunset", confidence=0.9)
        tag2 = ContentTag(name="sunset", confidence=0.8)  # Same name
        tag3 = ContentTag(name="beach", confidence=0.9)
        
        tag_set = {tag1, tag2, tag3}
        assert len(tag_set) == 2  # tag1 and tag2 are same
    
    def test_quality_metrics_score(self):
        """Test quality metrics overall score calculation."""
        metrics = QualityMetrics(
            sharpness=0.9,
            exposure=0.8,
            composition=0.85,
            color_balance=0.9,
            noise_level=0.1  # Low is good
        )
        
        score = metrics.overall_score
        assert 0.8 < score < 0.9
    
    def test_media_score_weighting(self):
        """Test media score weight calculation."""
        score = MediaScore(
            media_asset_id="img_001",
            aesthetic_score=0.9,
            relevance_score=0.8,
            technical_score=0.7,
            uniqueness_score=0.6
        )
        
        # Weight should be weighted average
        assert 0.6 < score.weight < 0.9
    
    def test_media_cluster_operations(self):
        """Test cluster add/remove operations."""
        cluster = MediaCluster(
            id="cluster_1",
            name="Beach photos",
            media_asset_ids=["img_001"]
        )
        
        assert cluster.size == 1
        
        cluster.add_media("img_002")
        assert cluster.size == 2
        
        cluster.add_media("img_002")  # Duplicate
        assert cluster.size == 2  # No change
        
        cluster.remove_media("img_001")
        assert cluster.size == 1


class TestProjectState:
    """Test ProjectState and related models."""
    
    def test_create_minimal_project(self):
        """Test creating project with minimal inputs."""
        inputs = UserInputs(
            initial_prompt="Create a vacation video",
            target_duration=60
        )
        
        project = ProjectState(user_inputs=inputs)
        
        assert len(project.project_id) == 36  # UUID
        assert project.status.phase == "initialized"
        assert project.user_inputs.target_duration == 60
    
    def test_invalid_aspect_ratio(self):
        """Test aspect ratio validation."""
        with pytest.raises(ValidationError):
            UserInputs(
                initial_prompt="Test",
                aspect_ratio="16:10"  # Not in valid list
            )
    
    def test_phase_transitions(self):
        """Test project phase updates."""
        inputs = UserInputs(initial_prompt="Test")
        project = ProjectState(user_inputs=inputs)
        
        # Update phase
        project.status.update_phase("analyzing", progress=25.0)
        
        assert project.status.phase == "analyzing"
        assert project.status.progress == 25.0
        assert len(project.status.phase_history) == 1
        assert project.status.is_processing
    
    def test_invalid_phase(self):
        """Test invalid phase validation."""
        status = ProjectStatus()
        
        with pytest.raises(ValueError):
            status.update_phase("processing")  # Not in valid phases
    
    def test_history_tracking(self):
        """Test project history methods."""
        inputs = UserInputs(initial_prompt="Test")
        project = ProjectState(user_inputs=inputs)
        
        # Add prompt
        project.history.add_prompt("Make it more upbeat")
        assert len(project.history.prompts) == 1
        
        # Add version
        timeline = Timeline()
        version_num = project.history.add_version(timeline, {"test": True})
        assert version_num == 1
        
        # Add feedback
        project.history.add_feedback("Looks great!", version=1, sentiment="positive")
        assert len(project.history.feedback) == 1
    
    def test_media_lookup(self):
        """Test finding media by ID."""
        media1 = MediaAsset(id="img_001", file_path="/test1.jpg", type=MediaType.IMAGE)
        media2 = MediaAsset(id="aud_001", file_path="/test.mp3", type=MediaType.AUDIO)
        
        inputs = UserInputs(
            initial_prompt="Test",
            media=[media1],
            music=[media2]
        )
        
        project = ProjectState(user_inputs=inputs)
        
        # Find existing media
        found = project.get_media_by_id("img_001")
        assert found is not None
        assert found.file_path == "/test1.jpg"
        
        # Find music
        found = project.get_media_by_id("aud_001")
        assert found is not None
        assert found.type == "audio"
        
        # Non-existent media
        assert project.get_media_by_id("xyz_999") is None
    
    def test_project_summary(self):
        """Test project summary generation."""
        inputs = UserInputs(
            initial_prompt="Test video",
            media=[
                MediaAsset(id="1", file_path="/1.jpg", type=MediaType.IMAGE),
                MediaAsset(id="2", file_path="/2.jpg", type=MediaType.IMAGE)
            ]
        )
        
        project = ProjectState(
            user_inputs=inputs,
            name="My Vacation"
        )
        
        summary = project.to_summary()
        
        assert summary["name"] == "My Vacation"
        assert summary["media_count"] == 2
        assert summary["status"]["phase"] == "initialized"
        assert not summary["has_output"]


class TestAudioModels:
    """Test audio-specific models."""
    
    def test_audio_vibe(self):
        """Test audio vibe validation."""
        vibe = AudioVibe(
            danceability=0.8,
            energy=0.9,
            mood="upbeat",
            genre="electronic"
        )
        
        assert vibe.danceability == 0.8
        assert vibe.mood == "upbeat"
    
    def test_audio_analysis_profile(self):
        """Test audio analysis profile."""
        vibe = AudioVibe(
            danceability=0.7,
            energy=0.6,
            mood="relaxed"
        )
        
        profile = AudioAnalysisProfile(
            file_path="/music.mp3",
            beat_timestamps=[0.0, 0.5, 1.0, 1.5],
            tempo_bpm=120.0,
            energy_curve=[0.5, 0.6, 0.7, 0.8],
            duration=30.0,
            vibe=vibe
        )
        
        assert profile.tempo_bpm == 120.0
        assert len(profile.beat_timestamps) == 4
    
    def test_invalid_energy_curve(self):
        """Test energy curve validation."""
        vibe = AudioVibe(danceability=0.5, energy=0.5, mood="test")
        
        with pytest.raises(ValidationError):
            AudioAnalysisProfile(
                file_path="/test.mp3",
                beat_timestamps=[],
                tempo_bpm=120,
                energy_curve=[0.5, 1.5],  # Invalid: > 1
                duration=10,
                vibe=vibe
            )