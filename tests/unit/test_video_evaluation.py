"""Tests for video evaluation tool."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from memory_movie_maker.tools.video_evaluation import VideoEvaluator, evaluate_video
from memory_movie_maker.models.project_state import ProjectState, UserInputs


class TestVideoEvaluator:
    """Test video evaluator functionality."""
    
    @pytest.fixture
    def evaluator(self):
        """Create video evaluator instance."""
        with patch('memory_movie_maker.tools.video_evaluation.genai.Client'):
            return VideoEvaluator()
    
    @pytest.fixture
    def mock_evaluation_response(self):
        """Create mock evaluation response."""
        return {
            "overall_score": 7.5,
            "strengths": ["Good pacing", "Smooth transitions"],
            "weaknesses": ["Some clips too short"],
            "technical_issues": [],
            "creative_suggestions": ["Add more variety"],
            "specific_edits": [
                {
                    "timestamp": "0:15",
                    "issue": "Clip too short",
                    "suggestion": "Extend by 2 seconds"
                }
            ],
            "recommendation": "minor_adjustments"
        }
    
    def test_create_evaluation_prompt(self, evaluator):
        """Test evaluation prompt creation."""
        context = {
            "user_prompt": "Create vacation video",
            "style": "dynamic",
            "target_duration": 60
        }
        
        prompt = evaluator._create_evaluation_prompt(context)
        
        assert "Create vacation video" in prompt
        assert "dynamic" in prompt
        assert "60 seconds" in prompt
        assert "JSON format" in prompt
    
    def test_parse_evaluation_response_valid_json(
        self, evaluator, mock_evaluation_response
    ):
        """Test parsing valid JSON response."""
        response_text = f"Here's my evaluation:\n{json.dumps(mock_evaluation_response)}"
        
        result = evaluator._parse_evaluation_response(response_text)
        
        assert result["overall_score"] == 7.5
        assert len(result["strengths"]) == 2
        assert result["recommendation"] == "minor_adjustments"
    
    def test_parse_evaluation_response_invalid_json(self, evaluator):
        """Test parsing invalid response."""
        response_text = "This is not valid JSON"
        
        result = evaluator._parse_evaluation_response(response_text)
        
        # Should return fallback
        assert result["overall_score"] == 6.0
        assert "Could not parse" in result["weaknesses"][0]
    
    @pytest.mark.asyncio
    async def test_evaluate_video(self, evaluator, mock_evaluation_response):
        """Test video evaluation."""
        # Mock Gemini client
        mock_file = Mock()
        mock_file.name = "test_file"
        mock_file.state = "ACTIVE"
        
        mock_response = Mock()
        mock_response.text = json.dumps(mock_evaluation_response)
        
        evaluator._client.files.upload = Mock(return_value=mock_file)
        evaluator._client.files.get = Mock(return_value=mock_file)
        evaluator._client.files.delete = Mock()
        evaluator._client.models.generate_content = Mock(return_value=mock_response)
        
        result = await evaluator.evaluate_video(
            video_path="test.mp4",
            project_context={"user_prompt": "Test video"}
        )
        
        assert result["status"] == "success"
        assert result["evaluation"]["overall_score"] == 7.5
        
        # Verify API calls
        evaluator._client.files.upload.assert_called_once()
        evaluator._client.models.generate_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_video_error_handling(self, evaluator):
        """Test error handling during evaluation."""
        evaluator._client.files.upload = Mock(side_effect=Exception("Upload failed"))
        
        result = await evaluator.evaluate_video(
            video_path="test.mp4",
            project_context={}
        )
        
        assert result["status"] == "error"
        assert "Upload failed" in result["error"]


class TestEvaluateVideoTool:
    """Test evaluate video tool function."""
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.video_evaluation.VideoEvaluator')
    async def test_evaluate_video_tool_success(self, mock_evaluator_class):
        """Test successful video evaluation."""
        # Mock evaluator
        mock_evaluator = AsyncMock()
        mock_evaluator.evaluate_video.return_value = {
            "status": "success",
            "evaluation": {
                "overall_score": 8.0,
                "recommendation": "accept"
            }
        }
        mock_evaluator_class.return_value = mock_evaluator
        
        project_state = ProjectState(
            user_inputs=UserInputs(
                media=[],
                initial_prompt="Test video",
                target_duration=60
            ),
            rendered_outputs=["test.mp4"]
        )
        
        result = await evaluate_video(
            project_state=project_state.model_dump()
        )
        
        assert result["status"] == "success"
        assert result["evaluation"]["overall_score"] == 8.0
        assert "updated_state" in result
    
    @pytest.mark.asyncio
    async def test_evaluate_video_tool_no_video(self):
        """Test evaluation without rendered video."""
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test")
        )
        
        result = await evaluate_video(
            project_state=project_state.model_dump()
        )
        
        assert result["status"] == "error"
        assert "No video found" in result["error"]
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.video_evaluation.Path')
    async def test_evaluate_video_tool_file_not_found(self, mock_path):
        """Test evaluation with missing video file."""
        mock_path.return_value.exists.return_value = False
        
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            rendered_outputs=["missing.mp4"]
        )
        
        result = await evaluate_video(
            project_state=project_state.model_dump(),
            video_path="missing.mp4"
        )
        
        assert result["status"] == "error"
        assert "not found" in result["error"]