"""Tests for EvaluationAgent."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from memory_movie_maker.agents.evaluation_agent import EvaluationAgent
from memory_movie_maker.models.project_state import ProjectState, UserInputs, ProjectStatus


class TestEvaluationAgent:
    """Test EvaluationAgent functionality."""
    
    @pytest.fixture
    def agent(self):
        """Create evaluation agent instance."""
        return EvaluationAgent()
    
    @pytest.fixture
    def sample_project_state(self):
        """Create sample project state with rendered video."""
        return ProjectState(
            user_inputs=UserInputs(
                media=[],
                initial_prompt="Create test video"
            ),
            project_status=ProjectStatus(phase="evaluating"),
            rendered_outputs=["test_video.mp4"]
        )
    
    @pytest.fixture
    def sample_evaluation(self):
        """Create sample evaluation results."""
        return {
            "overall_score": 7.5,
            "strengths": ["Good pacing", "Smooth transitions"],
            "weaknesses": ["Some clips too short", "Music sync could be better"],
            "technical_issues": ["Slight pixelation at 0:15"],
            "creative_suggestions": ["Add more variety in transitions"],
            "specific_edits": [
                {
                    "timestamp": "0:15",
                    "issue": "Clip too short",
                    "suggestion": "Extend by 2 seconds"
                },
                {
                    "timestamp": "0:30",
                    "issue": "Abrupt transition",
                    "suggestion": "Use crossfade"
                }
            ],
            "recommendation": "minor_adjustments"
        }
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.agents.evaluation_agent.evaluate_video_tool')
    async def test_evaluate_memory_movie_success(
        self, mock_eval_tool, agent, sample_project_state, sample_evaluation
    ):
        """Test successful video evaluation."""
        mock_eval_tool.run = AsyncMock(return_value={
            "status": "success",
            "evaluation": sample_evaluation,
            "updated_state": sample_project_state.model_dump()
        })
        
        result = await agent.evaluate_memory_movie(sample_project_state)
        
        assert result["status"] == "success"
        assert result["evaluation"] == sample_evaluation
        assert "feedback_summary" in result
        assert "updated_state" in result
        
        # Check feedback summary content
        summary = result["feedback_summary"]
        assert "7.5/10" in summary
        assert "Minor Adjustments" in summary
        assert "Good pacing" in summary
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.agents.evaluation_agent.evaluate_video_tool')
    async def test_evaluate_memory_movie_failure(
        self, mock_eval_tool, agent, sample_project_state
    ):
        """Test handling evaluation failure."""
        mock_eval_tool.run = AsyncMock(return_value={
            "status": "error",
            "error": "Video file not found"
        })
        
        result = await agent.evaluate_memory_movie(sample_project_state)
        
        assert result["status"] == "error"
        assert "Video file not found" in result["error"]
    
    def test_create_feedback_summary(self, agent, sample_evaluation):
        """Test feedback summary creation."""
        summary = agent._create_feedback_summary(sample_evaluation)
        
        # Check structure
        assert "Overall Score: 7.5/10" in summary
        assert "Recommendation: Minor Adjustments" in summary
        
        # Check strengths
        assert "Strengths:" in summary
        assert "✓ Good pacing" in summary
        
        # Check issues
        assert "Key Issues:" in summary
        assert "• Some clips too short" in summary
        
        # Check suggestions
        assert "Top Suggestions:" in summary
        
        # Check edit count
        assert "2 specific edits recommended" in summary
    
    def test_create_feedback_summary_minimal(self, agent):
        """Test feedback summary with minimal data."""
        minimal_eval = {
            "overall_score": 5.0,
            "recommendation": "major_rework"
        }
        
        summary = agent._create_feedback_summary(minimal_eval)
        
        assert "5.0/10" in summary
        assert "Major Rework" in summary
    
    def test_extract_priority_edits(self, agent, sample_evaluation):
        """Test priority edit extraction."""
        # Add more edits with priority keywords
        sample_evaluation["specific_edits"].extend([
            {
                "timestamp": "1:00",
                "issue": "Audio sync error",
                "suggestion": "Adjust timing"
            },
            {
                "timestamp": "1:15",
                "issue": "Color mismatch",
                "suggestion": "Color correction"
            },
            {
                "timestamp": "1:30",
                "issue": "Quality degradation",
                "suggestion": "Re-render segment"
            }
        ])
        
        priority_edits = agent.extract_priority_edits(
            sample_evaluation, max_edits=3
        )
        
        assert len(priority_edits) == 3
        # Sync and quality issues should be prioritized
        assert any("sync" in edit["issue"].lower() for edit in priority_edits)
        assert any("quality" in edit["issue"].lower() for edit in priority_edits)
    
    def test_extract_priority_edits_limited(self, agent):
        """Test priority edit extraction with limit."""
        large_eval = {
            "specific_edits": [
                {"timestamp": f"{i}:00", "issue": f"Issue {i}", "suggestion": f"Fix {i}"}
                for i in range(10)
            ]
        }
        
        priority_edits = agent.extract_priority_edits(large_eval, max_edits=5)
        
        assert len(priority_edits) == 5
    
    def test_should_accept_video_accepted(self, agent):
        """Test video acceptance criteria - accepted."""
        evaluation = {
            "overall_score": 8.5,
            "recommendation": "accept"
        }
        
        assert agent.should_accept_video(evaluation) is True
    
    def test_should_accept_video_minor_adjustments(self, agent):
        """Test video acceptance criteria - minor adjustments."""
        evaluation = {
            "overall_score": 7.5,
            "recommendation": "minor_adjustments"
        }
        
        assert agent.should_accept_video(evaluation) is True
    
    def test_should_accept_video_rejected_low_score(self, agent):
        """Test video acceptance criteria - low score."""
        evaluation = {
            "overall_score": 6.5,
            "recommendation": "minor_adjustments"
        }
        
        assert agent.should_accept_video(evaluation) is False
    
    def test_should_accept_video_rejected_major_rework(self, agent):
        """Test video acceptance criteria - major rework."""
        evaluation = {
            "overall_score": 7.5,
            "recommendation": "major_rework"
        }
        
        assert agent.should_accept_video(evaluation) is False
    
    @pytest.mark.asyncio
    async def test_evaluate_with_specific_video_path(
        self, agent, sample_project_state, sample_evaluation
    ):
        """Test evaluation with specific video path."""
        with patch('memory_movie_maker.agents.evaluation_agent.evaluate_video_tool') as mock_tool:
            mock_tool.run = AsyncMock(return_value={
                "status": "success",
                "evaluation": sample_evaluation,
                "updated_state": sample_project_state.model_dump()
            })
            
            result = await agent.evaluate_memory_movie(
                sample_project_state,
                video_path="specific_video.mp4"
            )
            
            # Verify video path was passed
            mock_tool.run.assert_called_once()
            call_args = mock_tool.run.call_args[1]
            assert call_args["video_path"] == "specific_video.mp4"