"""Tests for composition tool and algorithm."""

import pytest
from unittest.mock import Mock, patch
import uuid

from memory_movie_maker.tools.composition import (
    CompositionAlgorithm, compose_timeline, MediaCluster
)
from memory_movie_maker.models.timeline import Timeline, Segment, TransitionType
from memory_movie_maker.models.media_asset import (
    MediaAsset, MediaType, AudioAnalysisProfile, GeminiAnalysis
)
from memory_movie_maker.models.project_state import ProjectState, UserInputs


class TestCompositionAlgorithm:
    """Test the composition algorithm."""
    
    @pytest.fixture
    def algorithm(self):
        """Create composition algorithm instance."""
        return CompositionAlgorithm()
    
    @pytest.fixture
    def sample_media(self):
        """Create sample media assets."""
        return [
            MediaAsset(
                id="1",
                file_path="photo1.jpg",
                type=MediaType.IMAGE,
                gemini_analysis=GeminiAnalysis(
                    description="Beach sunset",
                    aesthetic_score=0.8,
                    tags=["beach", "sunset", "landscape"]
                )
            ),
            MediaAsset(
                id="2",
                file_path="video1.mp4",
                type=MediaType.VIDEO,
                duration=10.0,
                gemini_analysis=GeminiAnalysis(
                    description="People playing",
                    aesthetic_score=0.7,
                    tags=["people", "activity", "fun"]
                )
            ),
            MediaAsset(
                id="3",
                file_path="photo2.jpg",
                type=MediaType.IMAGE,
                gemini_analysis=GeminiAnalysis(
                    description="Mountain view",
                    aesthetic_score=0.9,
                    tags=["mountain", "landscape", "nature"]
                )
            )
        ]
    
    @pytest.fixture
    def music_profile(self):
        """Create sample music profile."""
        return AudioAnalysisProfile(
            file_path="music.mp3",
            beat_timestamps=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            tempo_bpm=120.0,
            energy_curve=[0.5, 0.6, 0.7, 0.8, 0.7, 0.6, 0.5, 0.6],
            duration=30.0
        )
    
    def test_filter_usable_media(self, algorithm, sample_media):
        """Test filtering of usable media."""
        # Add low quality media
        sample_media.append(
            MediaAsset(
                id="4",
                file_path="bad.jpg",
                type=MediaType.IMAGE,
                gemini_analysis=GeminiAnalysis(
                    description="Blurry photo",
                    aesthetic_score=0.2
                )
            )
        )
        
        usable = algorithm._filter_usable_media(sample_media)
        
        assert len(usable) == 3  # Low quality filtered out
        assert all(m.id != "4" for m in usable)
    
    def test_cluster_media_by_tags(self, algorithm, sample_media):
        """Test media clustering by tags."""
        clusters = algorithm._cluster_media(sample_media)
        
        assert len(clusters) > 0
        # Should have landscape cluster
        landscape_cluster = next(
            (c for c in clusters if c.theme == "landscape"), None
        )
        assert landscape_cluster is not None
        assert len(landscape_cluster.media_items) >= 2
    
    def test_beat_synced_segments(self, algorithm, sample_media, music_profile):
        """Test beat-synchronized segment creation."""
        clusters = algorithm._cluster_media(sample_media)
        segments = algorithm._create_beat_synced_segments(
            clusters, music_profile, target_duration=4
        )
        
        assert len(segments) > 0
        # Check segments align with beats
        for segment in segments:
            assert segment.start_time in music_profile.beat_timestamps
    
    def test_chronological_segments(self, algorithm, sample_media):
        """Test chronological segment creation."""
        clusters = algorithm._cluster_media(sample_media)
        segments = algorithm._create_chronological_segments(
            clusters, target_duration=10
        )
        
        assert len(segments) == 3
        # Check segments are in order
        assert segments[0].start_time == 0.0
        assert segments[1].start_time > segments[0].start_time
        
        # Check total duration
        total_duration = sum(s.duration for s in segments)
        assert total_duration <= 10
    
    def test_apply_transitions(self, algorithm):
        """Test transition application."""
        segments = [
            Segment(media_id="1", start_time=0, duration=2),
            Segment(media_id="2", start_time=2, duration=2),
            Segment(media_id="3", start_time=4, duration=2)
        ]
        
        # Test smooth style
        result = algorithm._apply_transitions(
            segments, {"transition_style": "smooth"}
        )
        assert result[0].transition_out == TransitionType.CROSSFADE
        assert result[1].transition_out == TransitionType.CROSSFADE
        
        # Test dynamic style
        result = algorithm._apply_transitions(
            segments, {"transition_style": "dynamic"}
        )
        # Should have variety of transitions
        transitions = [s.transition_out for s in result[:-1]]
        assert len(set(transitions)) > 1
    
    def test_compose_timeline_integration(
        self, algorithm, sample_media, music_profile
    ):
        """Test complete timeline composition."""
        timeline = algorithm.compose_timeline(
            media_pool=sample_media,
            music_profile=music_profile,
            target_duration=10,
            style_preferences={"style": "dynamic"}
        )
        
        assert isinstance(timeline, Timeline)
        assert len(timeline.segments) > 0
        assert timeline.audio_track_id == music_profile.file_path
        assert timeline.total_duration > 0
        
        # Check all segments have valid media IDs
        media_ids = {m.id for m in sample_media}
        for segment in timeline.segments:
            assert segment.media_id in media_ids


class TestComposeTimelineTool:
    """Test the compose timeline tool function."""
    
    @pytest.mark.asyncio
    async def test_compose_timeline_success(self):
        """Test successful timeline composition."""
        # Create project state
        media = [
            MediaAsset(
                id=str(uuid.uuid4()),
                file_path="test.jpg",
                type=MediaType.IMAGE,
                gemini_analysis={"description": "Test", "aesthetic_score": 0.8}
            )
        ]
        
        project_state = ProjectState(
            user_inputs=UserInputs(media=media, initial_prompt="Test")
        )
        
        result = await compose_timeline(
            project_state=project_state.model_dump(),
            target_duration=10,
            style="smooth"
        )
        
        assert result["status"] == "success"
        assert "timeline" in result
        assert "updated_state" in result
    
    @pytest.mark.asyncio
    async def test_compose_timeline_no_media(self):
        """Test timeline composition with no media."""
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test")
        )
        
        result = await compose_timeline(
            project_state=project_state.model_dump(),
            target_duration=10
        )
        
        assert result["status"] == "error"
        assert "No usable media" in result["error"]