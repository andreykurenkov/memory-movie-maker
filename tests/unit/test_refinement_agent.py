"""Tests for RefinementAgent."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from memory_movie_maker.agents.refinement_agent import RefinementAgent
from memory_movie_maker.models.project_state import ProjectState, UserInputs, ProjectStatus
from memory_movie_maker.models.timeline import Timeline, Segment


class TestRefinementAgent:
    """Test RefinementAgent functionality."""
    
    @pytest.fixture
    def agent(self):
        """Create refinement agent instance."""
        return RefinementAgent()
    
    @pytest.fixture
    def sample_project_state(self):
        """Create sample project state with timeline."""
        return ProjectState(
            user_inputs=UserInputs(
                media=[],
                initial_prompt="Create test video"
            ),
            project_status=ProjectStatus(phase="refining"),
            timeline=Timeline(
                segments=[
                    Segment(media_id="1", start_time=0, duration=3),
                    Segment(media_id="2", start_time=3, duration=2),
                    Segment(media_id="3", start_time=5, duration=4)
                ],
                total_duration=9
            )
        )
    
    @pytest.fixture
    def sample_evaluation(self):
        """Create sample evaluation results."""
        return {
            "overall_score": 7.0,
            "recommendation": "minor_adjustments",
            "specific_edits": [
                {
                    "timestamp": "0:03",
                    "issue": "Clip too short",
                    "suggestion": "Extend by 2 seconds"
                },
                {
                    "timestamp": "0:05",
                    "issue": "Abrupt transition",
                    "suggestion": "Use crossfade"
                }
            ]
        }
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.agents.refinement_agent.parse_refinements_tool')
    async def test_process_evaluation_feedback_success(
        self, mock_parse_tool, agent, sample_project_state, sample_evaluation
    ):
        """Test successful evaluation feedback processing."""
        mock_parse_tool.run = AsyncMock(return_value={
            "status": "success",
            "edit_commands": {
                "adjust_durations": {"1": 2},
                "change_transitions": {"2": "crossfade"}
            },
            "command_count": 2
        })
        
        result = await agent.process_evaluation_feedback(
            project_state=sample_project_state,
            evaluation_results=sample_evaluation,
            user_feedback="Make it smoother"
        )
        
        assert result["status"] == "success"
        assert "edit_commands" in result
        assert result["command_count"] == 2
        assert "summary" in result
        assert "recommendation" in result
        
        # Verify timeline info was extracted
        call_args = mock_parse_tool.run.call_args[1]
        assert "timeline_info" in call_args
        assert call_args["timeline_info"]["segments"] == 3
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.agents.refinement_agent.parse_refinements_tool')
    async def test_process_evaluation_feedback_failure(
        self, mock_parse_tool, agent, sample_project_state, sample_evaluation
    ):
        """Test handling of parsing failure."""
        mock_parse_tool.run = AsyncMock(return_value={
            "status": "error",
            "error": "Parsing failed"
        })
        
        result = await agent.process_evaluation_feedback(
            project_state=sample_project_state,
            evaluation_results=sample_evaluation
        )
        
        assert result["status"] == "error"
        assert "Parsing failed" in result["error"]
    
    def test_create_edit_summary(self, agent):
        """Test edit summary creation."""
        edit_commands = {
            "reorder_segments": ["3", "1", "2"],
            "adjust_durations": {"1": 2, "2": -1},
            "change_transitions": {"1": "crossfade"},
            "add_effects": {"2": ["ken_burns", "zoom"]},
            "remove_segments": ["4"]
        }
        
        summary = agent._create_edit_summary(edit_commands)
        
        assert "Reorder 3 segments" in summary
        assert "Adjust 2 clip durations (+1.0s total)" in summary
        assert "Change 1 transitions" in summary
        assert "Add 2 effects" in summary
        assert "Remove 1 segments" in summary
    
    def test_create_edit_summary_empty(self, agent):
        """Test edit summary with no commands."""
        summary = agent._create_edit_summary({})
        assert summary == "No edits needed"
    
    def test_get_edit_recommendation_minor(self, agent):
        """Test edit recommendation - minor edits."""
        evaluation = {"overall_score": 8.5}
        edit_commands = {"adjust_durations": {"1": 1}}
        
        recommendation = agent._get_edit_recommendation(
            evaluation, edit_commands
        )
        
        assert recommendation == "apply_minor_edits"
    
    def test_get_edit_recommendation_normal(self, agent):
        """Test edit recommendation - normal edits."""
        evaluation = {"overall_score": 7.0}
        edit_commands = {
            "adjust_durations": {"1": 2, "2": 3},
            "change_transitions": {"1": "crossfade"}
        }
        
        recommendation = agent._get_edit_recommendation(
            evaluation, edit_commands
        )
        
        assert recommendation == "apply_edits"
    
    def test_get_edit_recommendation_major(self, agent):
        """Test edit recommendation - consider regeneration."""
        evaluation = {"overall_score": 5.0}
        edit_commands = {
            f"edit_{i}": {"data": i} for i in range(20)
        }
        
        recommendation = agent._get_edit_recommendation(
            evaluation, edit_commands
        )
        
        assert recommendation == "consider_regeneration"
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.agents.refinement_agent.parse_user_request_tool')
    async def test_parse_user_edit_request_success(
        self, mock_parse_tool, agent, sample_project_state
    ):
        """Test successful user request parsing."""
        mock_parse_tool.run = AsyncMock(return_value={
            "status": "success",
            "intent": "edit",
            "parameters": {"duration": 30, "style": "smooth"}
        })
        
        result = await agent.parse_user_edit_request(
            user_request="Make it 30 seconds with smooth transitions",
            project_state=sample_project_state
        )
        
        assert result["status"] == "success"
        assert result["intent"] == "edit"
        assert result["parameters"]["duration"] == 30
        assert "suggestions" in result
        assert "ready_to_execute" in result
    
    def test_get_contextual_suggestions(self, agent):
        """Test contextual suggestion generation."""
        # Test create without timeline
        suggestions = agent._get_contextual_suggestions(
            intent="create",
            parameters={},
            project_state=ProjectState(
                user_inputs=UserInputs(media=[], initial_prompt="Test")
            )
        )
        assert "Need to run composition first" in suggestions
        
        # Test large duration change
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            timeline=Timeline(segments=[], total_duration=60)
        )
        suggestions = agent._get_contextual_suggestions(
            intent="edit",
            parameters={"duration": 120},
            project_state=project_state
        )
        assert any("Large duration change" in s for s in suggestions)
    
    def test_can_execute(self, agent):
        """Test execution readiness check."""
        # Test create - needs media
        state_no_media = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test")
        )
        assert not agent._can_execute("create", state_no_media)
        
        state_with_media = ProjectState(
            user_inputs=UserInputs(media=[Mock()], initial_prompt="Test")
        )
        assert agent._can_execute("create", state_with_media)
        
        # Test edit - needs timeline
        assert not agent._can_execute("edit", state_with_media)
        
        state_with_timeline = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            timeline=Timeline(segments=[], total_duration=0)
        )
        assert agent._can_execute("edit", state_with_timeline)
        
        # Test evaluate - needs renders
        assert not agent._can_execute("evaluate", state_with_timeline)
        
        state_with_render = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            rendered_outputs=["video.mp4"]
        )
        assert agent._can_execute("evaluate", state_with_render)