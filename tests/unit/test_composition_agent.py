"""Tests for CompositionAgent."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import uuid

from memory_movie_maker.agents.composition_agent import CompositionAgent
from memory_movie_maker.models.project_state import ProjectState, UserInputs, ProjectStatus
from memory_movie_maker.models.media_asset import MediaAsset, MediaType, GeminiAnalysis
from memory_movie_maker.models.timeline import Timeline, Segment, TransitionType


class TestCompositionAgent:
    """Test CompositionAgent functionality."""
    
    @pytest.fixture
    def agent(self):
        """Create composition agent instance."""
        return CompositionAgent()
    
    @pytest.fixture
    def sample_project_state(self):
        """Create sample project state with analyzed media."""
        return ProjectState(
            user_inputs=UserInputs(
                media=[
                    MediaAsset(
                        id=str(uuid.uuid4()),
                        file_path="test.jpg",
                        type=MediaType.IMAGE,
                        gemini_analysis=GeminiAnalysis(
                            description="Test image",
                            aesthetic_score=0.8
                        )
                    ),
                    MediaAsset(
                        id=str(uuid.uuid4()),
                        file_path="test.mp4",
                        type=MediaType.VIDEO,
                        gemini_analysis=GeminiAnalysis(
                            description="Test video",
                            aesthetic_score=0.7
                        )
                    )
                ],
                initial_prompt="Create test video"
            ),
            project_status=ProjectStatus(phase="composing")
        )
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.agents.composition_agent.compose_timeline_tool')
    @patch('memory_movie_maker.agents.composition_agent.render_video_tool')
    async def test_create_memory_movie_success(
        self, mock_render_tool, mock_compose_tool, agent, sample_project_state
    ):
        """Test successful memory movie creation."""
        # Mock timeline creation
        mock_compose_tool.run = AsyncMock(return_value={
            "status": "success",
            "timeline": {
                "segments": [{"media_id": "1", "duration": 2}],
                "total_duration": 2
            },
            "updated_state": sample_project_state.model_dump()
        })
        
        # Mock rendering
        mock_render_tool.run = AsyncMock(return_value={
            "status": "success",
            "output_path": "output.mp4",
            "updated_state": sample_project_state.model_dump()
        })
        
        result = await agent.create_memory_movie(
            project_state=sample_project_state,
            target_duration=10,
            style="smooth",
            preview_only=True
        )
        
        assert isinstance(result, ProjectState)
        assert result.project_status.phase == "evaluating"
        
        # Verify tool calls
        mock_compose_tool.run.assert_called_once()
        mock_render_tool.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_memory_movie_no_media(self, agent):
        """Test creation with no media files."""
        empty_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            project_status=ProjectStatus(phase="composing")
        )
        
        with pytest.raises(ValueError, match="No media files"):
            await agent.create_memory_movie(empty_state)
    
    @pytest.mark.asyncio
    async def test_create_memory_movie_no_analyzed_media(
        self, agent
    ):
        """Test creation with unanalyzed media."""
        unanalyzed_state = ProjectState(
            user_inputs=UserInputs(
                media=[
                    MediaAsset(
                        id=str(uuid.uuid4()),
                        file_path="test.jpg",
                        type=MediaType.IMAGE
                        # No analysis
                    )
                ],
                initial_prompt="Test"
            ),
            project_status=ProjectStatus(phase="composing")
        )
        
        with pytest.raises(ValueError, match="No analyzed media"):
            await agent.create_memory_movie(unanalyzed_state)
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.agents.composition_agent.compose_timeline_tool')
    async def test_create_memory_movie_timeline_failure(
        self, mock_compose_tool, agent, sample_project_state
    ):
        """Test handling of timeline creation failure."""
        mock_compose_tool.run = AsyncMock(return_value={
            "status": "error",
            "error": "Timeline creation failed"
        })
        
        with pytest.raises(RuntimeError, match="Timeline creation failed"):
            await agent.create_memory_movie(sample_project_state)
    
    @pytest.mark.asyncio
    async def test_apply_edit_commands(self, agent):
        """Test applying edit commands to timeline."""
        # Create project with timeline
        timeline = Timeline(
            segments=[
                Segment(media_id="1", start_time=0, duration=2),
                Segment(media_id="2", start_time=2, duration=3),
                Segment(media_id="3", start_time=5, duration=2)
            ],
            total_duration=7
        )
        
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            timeline=timeline
        )
        
        # Test duration adjustment
        edit_commands = {
            "adjust_durations": {"1": 3, "2": 2}
        }
        
        result = await agent.apply_edit_commands(project_state, edit_commands)
        
        assert result.timeline.segments[0].duration == 3
        assert result.timeline.segments[1].duration == 2
        assert result.timeline.total_duration == 7  # 3 + 2 + 2
    
    @pytest.mark.asyncio
    async def test_apply_edit_commands_reorder(self, agent):
        """Test reordering segments."""
        timeline = Timeline(
            segments=[
                Segment(media_id="1", start_time=0, duration=2),
                Segment(media_id="2", start_time=2, duration=2),
                Segment(media_id="3", start_time=4, duration=2)
            ],
            total_duration=6
        )
        
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            timeline=timeline
        )
        
        edit_commands = {
            "reorder_segments": ["3", "1", "2"]
        }
        
        result = await agent.apply_edit_commands(project_state, edit_commands)
        
        # Check new order
        assert result.timeline.segments[0].media_id == "3"
        assert result.timeline.segments[1].media_id == "1"
        assert result.timeline.segments[2].media_id == "2"
        
        # Check start times updated
        assert result.timeline.segments[0].start_time == 0
        assert result.timeline.segments[1].start_time == 2
        assert result.timeline.segments[2].start_time == 4
    
    @pytest.mark.asyncio
    async def test_apply_edit_commands_transitions(self, agent):
        """Test changing transitions."""
        timeline = Timeline(
            segments=[
                Segment(media_id="1", start_time=0, duration=2),
                Segment(media_id="2", start_time=2, duration=2)
            ],
            total_duration=4
        )
        
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            timeline=timeline
        )
        
        edit_commands = {
            "change_transitions": {
                "1": TransitionType.FADE_TO_BLACK,
                "2": TransitionType.CROSSFADE
            }
        }
        
        result = await agent.apply_edit_commands(project_state, edit_commands)
        
        assert result.timeline.segments[0].transition_out == TransitionType.FADE_TO_BLACK
        assert result.timeline.segments[1].transition_out == TransitionType.CROSSFADE
    
    @pytest.mark.asyncio
    async def test_apply_edit_commands_effects(self, agent):
        """Test adding effects."""
        timeline = Timeline(
            segments=[
                Segment(media_id="1", start_time=0, duration=2, effects=[])
            ],
            total_duration=2
        )
        
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            timeline=timeline
        )
        
        edit_commands = {
            "add_effects": {
                "1": ["ken_burns", "slow_motion"]
            }
        }
        
        result = await agent.apply_edit_commands(project_state, edit_commands)
        
        assert "ken_burns" in result.timeline.segments[0].effects
        assert "slow_motion" in result.timeline.segments[0].effects
    
    @pytest.mark.asyncio
    async def test_apply_edit_commands_no_timeline(self, agent):
        """Test applying edits without timeline."""
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test")
        )
        
        with pytest.raises(ValueError, match="No timeline found"):
            await agent.apply_edit_commands(project_state, {})
    
    def test_storage_property(self, agent):
        """Test storage property access."""
        assert agent.storage is not None
        assert hasattr(agent.storage, 'save_project')