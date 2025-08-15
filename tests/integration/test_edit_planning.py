"""Integration tests for AI-powered edit planning workflow."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json

from memory_movie_maker.models.project_state import ProjectState, UserInputs
from memory_movie_maker.models.media_asset import (
    MediaAsset, MediaType, GeminiAnalysis, AudioAnalysisProfile, AudioVibe
)
from memory_movie_maker.models.edit_plan import EditPlan, PlannedSegment
from memory_movie_maker.tools.edit_planner import EditPlanner


class TestEditPlanningIntegration:
    """Test AI-powered edit planning workflow."""
    
    @pytest.fixture
    def sample_media_assets(self):
        """Create sample analyzed media assets."""
        return [
            MediaAsset(
                id="img_001",
                file_path="/media/sunset.jpg",
                type=MediaType.IMAGE,
                gemini_analysis=GeminiAnalysis(
                    description="Beautiful sunset over ocean with vibrant colors",
                    aesthetic_score=0.9,
                    main_subjects=["sunset", "ocean", "sky"],
                    tags=["landscape", "nature", "golden hour"]
                )
            ),
            MediaAsset(
                id="vid_001",
                file_path="/media/family_gathering.mp4",
                type=MediaType.VIDEO,
                duration=15.0,
                gemini_analysis=GeminiAnalysis(
                    description="Family members laughing and talking at dinner",
                    aesthetic_score=0.8,
                    main_subjects=["people", "family", "dinner"],
                    tags=["social", "indoors", "celebration"],
                    notable_segments=[{
                        "start_time": 2.0,
                        "end_time": 8.0,
                        "description": "Everyone laughing at joke",
                        "importance": 0.9
                    }]
                )
            ),
            MediaAsset(
                id="img_002",
                file_path="/media/group_photo.jpg",
                type=MediaType.IMAGE,
                gemini_analysis=GeminiAnalysis(
                    description="Group photo with everyone smiling",
                    aesthetic_score=0.85,
                    main_subjects=["people", "group", "smiles"],
                    tags=["portrait", "social", "happiness"]
                )
            )
        ]
    
    @pytest.fixture
    def sample_music_asset(self):
        """Create sample analyzed music asset."""
        return MediaAsset(
            id="music_001",
            file_path="/media/upbeat_song.mp3",
            type=MediaType.AUDIO,
            duration=120.0,
            audio_analysis=AudioAnalysisProfile(
                file_path="/media/upbeat_song.mp3",
                duration=120.0,
                tempo_bpm=128.0,
                beat_timestamps=[0.0, 0.469, 0.938, 1.406, 1.875, 2.344, 2.813],
                energy_curve=[0.3, 0.4, 0.5, 0.7, 0.8, 0.9, 0.8, 0.7],
                vibe=AudioVibe(
                    danceability=0.8,
                    energy=0.75,
                    mood="upbeat"
                )
            ),
            semantic_audio_analysis={
                "summary": "Upbeat instrumental track with building energy",
                "emotional_tone": "energetic",
                "musical_structure_summary": "Intro (0-15s) → Verse (15-45s) → Chorus (45-75s) → Bridge (75-90s) → Outro (90-120s)",
                "segments": [
                    {
                        "start_time": 0,
                        "end_time": 15,
                        "type": "intro",
                        "content": "Soft piano intro",
                        "musical_structure": "intro",
                        "energy_transition": "building",
                        "sync_priority": 0.7
                    },
                    {
                        "start_time": 15,
                        "end_time": 45,
                        "type": "music",
                        "content": "Main melody with drums",
                        "musical_structure": "verse",
                        "energy_transition": "steady",
                        "sync_priority": 0.5
                    },
                    {
                        "start_time": 45,
                        "end_time": 75,
                        "type": "music",
                        "content": "Full instrumentation",
                        "musical_structure": "chorus",
                        "energy_transition": "peak",
                        "sync_priority": 1.0
                    }
                ],
                "energy_peaks": [45.0, 60.0, 75.0],
                "recommended_cut_points": [15.0, 30.0, 45.0, 60.0, 75.0]
            }
        )
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.edit_planner.GENAI_AVAILABLE', True)
    async def test_edit_planning_with_music_sync(self, sample_media_assets, sample_music_asset):
        """Test edit planning with music synchronization."""
        # Mock Gemini response
        mock_gemini_response = {
            "segments": [
                {
                    "media_id": "img_001",
                    "start_time": 0.0,
                    "duration": 3.0,
                    "trim_start": 0.0,
                    "transition_type": "fade",
                    "reasoning": "Opening with beautiful sunset establishes mood",
                    "story_beat": "introduction",
                    "energy_match": 0.3
                },
                {
                    "media_id": "vid_001",
                    "start_time": 3.0,
                    "duration": 5.0,
                    "trim_start": 2.0,
                    "trim_end": 7.0,
                    "transition_type": "crossfade",
                    "reasoning": "Family laughter syncs with music energy buildup",
                    "story_beat": "development",
                    "energy_match": 0.7
                },
                {
                    "media_id": "img_002",
                    "start_time": 8.0,
                    "duration": 2.0,
                    "trim_start": 0.0,
                    "transition_type": "fade",
                    "reasoning": "Group photo as emotional peak",
                    "story_beat": "climax",
                    "energy_match": 0.9
                }
            ],
            "total_duration": 10.0,
            "narrative_structure": "Journey from serene nature to joyful human connection",
            "pacing_strategy": "Gradual energy build matching music progression",
            "music_sync_notes": "Key visual moments aligned with musical transitions at 3s and 8s",
            "variety_score": 0.85,
            "story_coherence": 0.9,
            "technical_quality": 0.87,
            "reasoning_summary": "Edit creates emotional arc from peaceful to joyful"
        }
        
        with patch('memory_movie_maker.tools.edit_planner.genai') as mock_genai:
            # Setup mock client
            mock_client = Mock()
            mock_genai.Client.return_value = mock_client
            
            # Setup mock response
            mock_response = Mock()
            mock_response.text = json.dumps(mock_gemini_response)
            mock_client.models.generate_content = AsyncMock(return_value=mock_response)
            
            # Create planner
            planner = EditPlanner()
            
            # Plan edit
            edit_plan = await planner.plan_edit(
                media_assets=sample_media_assets,
                music_profile=sample_music_asset.audio_analysis,
                target_duration=10,
                user_prompt="Create a heartwarming family memory",
                style_preferences={"style": "smooth"},
                music_asset=sample_music_asset
            )
            
            # Verify plan structure
            assert isinstance(edit_plan, EditPlan)
            assert len(edit_plan.segments) == 3
            assert edit_plan.total_duration == 10.0
            
            # Verify music synchronization
            assert edit_plan.music_sync_notes is not None
            assert "musical transitions" in edit_plan.music_sync_notes
            
            # Verify segment details
            first_segment = edit_plan.segments[0]
            assert first_segment.media_id == "img_001"
            assert first_segment.story_beat == "introduction"
            assert first_segment.energy_match == 0.3
            
            # Verify AI reasoning
            assert edit_plan.narrative_structure == "Journey from serene nature to joyful human connection"
            assert edit_plan.variety_score == 0.85
            assert edit_plan.story_coherence == 0.9
    
    @pytest.mark.asyncio
    async def test_edit_planning_prompt_construction(self, sample_media_assets, sample_music_asset):
        """Test that edit planning prompt includes all necessary information."""
        with patch('memory_movie_maker.tools.edit_planner.genai') as mock_genai:
            # Setup mock
            mock_client = Mock()
            mock_genai.Client.return_value = mock_client
            
            # Capture the prompt
            captured_prompt = None
            async def capture_prompt(model, contents):
                nonlocal captured_prompt
                captured_prompt = contents
                mock_response = Mock()
                mock_response.text = json.dumps({
                    "segments": [],
                    "total_duration": 0,
                    "narrative_structure": "",
                    "pacing_strategy": "",
                    "variety_score": 0,
                    "story_coherence": 0,
                    "technical_quality": 0,
                    "reasoning_summary": ""
                })
                return mock_response
            
            mock_client.models.generate_content = capture_prompt
            
            planner = EditPlanner()
            
            # Plan edit
            await planner.plan_edit(
                media_assets=sample_media_assets,
                music_profile=sample_music_asset.audio_analysis,
                target_duration=30,
                user_prompt="Create an energetic montage",
                style_preferences={"style": "dynamic"},
                music_asset=sample_music_asset
            )
            
            # Verify prompt contains key elements
            assert captured_prompt is not None
            assert "Create an energetic montage" in captured_prompt
            assert "TARGET DURATION: 30 seconds" in captured_prompt
            assert "STYLE: dynamic" in captured_prompt
            
            # Verify media information is included
            assert "sunset.jpg" in captured_prompt
            assert "Beautiful sunset over ocean" in captured_prompt
            assert "aesthetic_score" in captured_prompt
            
            # Verify music information is included
            assert "tempo\": 128" in captured_prompt
            assert "musical_structure" in captured_prompt
            assert "energy_peaks" in captured_prompt
            assert "recommended_cut_points" in captured_prompt
            
            # Verify creative guidelines
            assert "STORY STRUCTURE" in captured_prompt
            assert "VARIETY & PACING" in captured_prompt
            assert "MUSIC SYNCHRONIZATION" in captured_prompt
    
    @pytest.mark.asyncio
    async def test_edit_planning_without_music(self, sample_media_assets):
        """Test edit planning without background music."""
        with patch('memory_movie_maker.tools.edit_planner.genai') as mock_genai:
            # Setup mock
            mock_client = Mock()
            mock_genai.Client.return_value = mock_client
            
            mock_response = Mock()
            mock_response.text = json.dumps({
                "segments": [
                    {
                        "media_id": "img_001",
                        "start_time": 0.0,
                        "duration": 5.0,
                        "trim_start": 0.0,
                        "transition_type": "fade",
                        "reasoning": "Strong opening image",
                        "story_beat": "introduction"
                    }
                ],
                "total_duration": 5.0,
                "narrative_structure": "Visual story without music",
                "pacing_strategy": "Steady pacing based on content",
                "variety_score": 0.7,
                "story_coherence": 0.8,
                "technical_quality": 0.85,
                "reasoning_summary": "Content-driven edit"
            })
            mock_client.models.generate_content = AsyncMock(return_value=mock_response)
            
            planner = EditPlanner()
            
            # Plan edit without music
            edit_plan = await planner.plan_edit(
                media_assets=sample_media_assets,
                music_profile=None,
                target_duration=5,
                user_prompt="Create a simple slideshow",
                style_preferences={"style": "smooth"},
                music_asset=None
            )
            
            # Verify plan works without music
            assert isinstance(edit_plan, EditPlan)
            assert len(edit_plan.segments) == 1
            assert edit_plan.music_sync_notes is None
            assert edit_plan.segments[0].energy_match is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])