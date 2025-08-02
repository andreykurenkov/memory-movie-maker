"""Tests for RootAgent orchestrator."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid
from pathlib import Path

from memory_movie_maker.agents.root_agent import RootAgent
from memory_movie_maker.models.project_state import ProjectState, UserInputs, ProjectStatus
from memory_movie_maker.models.media_asset import MediaAsset, MediaType


class TestRootAgent:
    """Test RootAgent functionality."""
    
    @pytest.fixture
    def root_agent(self):
        """Create root agent instance."""
        with patch('memory_movie_maker.agents.root_agent.FilesystemStorage'):
            return RootAgent()
    
    @pytest.fixture
    def sample_media_paths(self, tmp_path):
        """Create sample media file paths."""
        # Create temporary files
        photo1 = tmp_path / "photo1.jpg"
        photo2 = tmp_path / "photo2.png"
        video1 = tmp_path / "video1.mp4"
        music1 = tmp_path / "music.mp3"
        
        for f in [photo1, photo2, video1, music1]:
            f.touch()
        
        return [str(photo1), str(photo2), str(video1)], str(music1)
    
    @pytest.mark.asyncio
    async def test_create_memory_movie_complete_workflow(
        self, root_agent, sample_media_paths
    ):
        """Test complete memory movie creation workflow."""
        media_paths, music_path = sample_media_paths
        
        # Mock all agent methods
        root_agent.analysis_agent.analyze_project = AsyncMock(
            side_effect=lambda ps: ps  # Return state unchanged
        )
        
        root_agent.composition_agent.create_memory_movie = AsyncMock(
            side_effect=lambda ps, **kwargs: ps  # Return state unchanged
        )
        
        # Mock evaluation to return good score
        root_agent.evaluation_agent.evaluate_memory_movie = AsyncMock(
            return_value={
                "status": "success",
                "evaluation": {
                    "overall_score": 8.0,
                    "recommendation": "accept"
                },
                "updated_state": Mock(
                    evaluation_results={"overall_score": 8.0}
                )
            }
        )
        
        # Mock save
        root_agent._save_project_state = AsyncMock()
        
        result = await root_agent.create_memory_movie(
            media_paths=media_paths,
            user_prompt="Create test video",
            music_path=music_path,
            target_duration=10,
            style="dynamic",
            auto_refine=True
        )
        
        assert result["status"] == "success"
        assert result["refinement_iterations"] == 1  # One evaluation pass
        assert result["final_score"] == 8.0
        
        # Verify workflow order
        root_agent.analysis_agent.analyze_project.assert_called_once()
        assert root_agent.composition_agent.create_memory_movie.call_count >= 2  # Initial + final
        root_agent.evaluation_agent.evaluate_memory_movie.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_memory_movie_no_auto_refine(
        self, root_agent, sample_media_paths
    ):
        """Test creation without auto-refinement."""
        media_paths, music_path = sample_media_paths
        
        # Mock agents
        root_agent.analysis_agent.analyze_project = AsyncMock(
            side_effect=lambda ps: ps
        )
        
        # Add rendered output to state
        def add_render(ps, **kwargs):
            ps.rendered_outputs.append("preview.mp4")
            return ps
        
        root_agent.composition_agent.create_memory_movie = AsyncMock(
            side_effect=add_render
        )
        
        result = await root_agent.create_memory_movie(
            media_paths=media_paths,
            user_prompt="Quick test",
            target_duration=5,
            auto_refine=False
        )
        
        assert result["status"] == "success"
        assert "Initial video created" in result["message"]
        assert result["video_path"] == "preview.mp4"
        
        # Should not call evaluation
        root_agent.evaluation_agent.evaluate_memory_movie.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_self_correction_loop_refinement(self, root_agent):
        """Test self-correction loop with refinements."""
        # Setup initial state
        root_agent.analysis_agent.analyze_project = AsyncMock(
            side_effect=lambda ps: ps
        )
        
        root_agent.composition_agent.create_memory_movie = AsyncMock(
            side_effect=lambda ps, **kwargs: ps
        )
        
        root_agent.composition_agent.apply_edit_commands = AsyncMock(
            side_effect=lambda ps, **kwargs: ps
        )
        
        # First evaluation: needs improvement
        # Second evaluation: acceptable
        eval_results = [
            {
                "status": "success",
                "evaluation": {
                    "overall_score": 6.5,
                    "recommendation": "minor_adjustments"
                },
                "updated_state": Mock(evaluation_results={"overall_score": 6.5})
            },
            {
                "status": "success",
                "evaluation": {
                    "overall_score": 7.5,
                    "recommendation": "accept"
                },
                "updated_state": Mock(evaluation_results={"overall_score": 7.5})
            }
        ]
        
        root_agent.evaluation_agent.evaluate_memory_movie = AsyncMock(
            side_effect=eval_results
        )
        
        root_agent.refinement_agent.process_evaluation_feedback = AsyncMock(
            return_value={
                "status": "success",
                "edit_commands": {"adjust_durations": {"1": 2}}
            }
        )
        
        root_agent._save_project_state = AsyncMock()
        
        result = await root_agent.create_memory_movie(
            media_paths=["test.jpg"],
            user_prompt="Test refinement",
            target_duration=10
        )
        
        assert result["status"] == "success"
        assert result["refinement_iterations"] == 2
        assert result["final_score"] == 7.5
        
        # Verify refinement was applied
        root_agent.refinement_agent.process_evaluation_feedback.assert_called_once()
        root_agent.composition_agent.apply_edit_commands.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_self_correction_loop_major_rework(self, root_agent):
        """Test self-correction with major rework recommendation."""
        root_agent.analysis_agent.analyze_project = AsyncMock(
            side_effect=lambda ps: ps
        )
        
        root_agent.composition_agent.create_memory_movie = AsyncMock(
            side_effect=lambda ps, **kwargs: ps
        )
        
        # Evaluation recommends major rework
        root_agent.evaluation_agent.evaluate_memory_movie = AsyncMock(
            return_value={
                "status": "success",
                "evaluation": {
                    "overall_score": 4.0,
                    "recommendation": "major_rework"
                },
                "updated_state": Mock(
                    evaluation_results={"overall_score": 4.0},
                    timeline=Mock()  # Has timeline
                )
            }
        )
        
        root_agent._save_project_state = AsyncMock()
        
        # Should only run once due to max iterations
        root_agent.max_refinement_iterations = 1
        
        result = await root_agent.create_memory_movie(
            media_paths=["test.jpg"],
            user_prompt="Test rework",
            target_duration=10
        )
        
        # Should recreate from scratch
        assert root_agent.composition_agent.create_memory_movie.call_count >= 3  # Initial + rework + final
    
    def test_detect_media_type(self, root_agent):
        """Test media type detection."""
        assert root_agent._detect_media_type("photo.jpg") == MediaType.IMAGE
        assert root_agent._detect_media_type("photo.JPEG") == MediaType.IMAGE
        assert root_agent._detect_media_type("video.mp4") == MediaType.VIDEO
        assert root_agent._detect_media_type("video.MOV") == MediaType.VIDEO
        assert root_agent._detect_media_type("song.mp3") == MediaType.AUDIO
        assert root_agent._detect_media_type("song.WAV") == MediaType.AUDIO
        assert root_agent._detect_media_type("document.pdf") is None
    
    @pytest.mark.asyncio
    async def test_initialize_project(self, root_agent, sample_media_paths):
        """Test project initialization."""
        media_paths, music_path = sample_media_paths
        
        project_state = await root_agent._initialize_project(
            media_paths=media_paths,
            user_prompt="Test prompt",
            music_path=music_path,
            target_duration=60,
            style="smooth"
        )
        
        assert isinstance(project_state, ProjectState)
        assert len(project_state.user_inputs.media) == 4  # 3 media + 1 music
        assert project_state.user_inputs.initial_prompt == "Test prompt"
        assert project_state.user_inputs.target_duration == 60
        assert project_state.user_inputs.style_preferences["style"] == "smooth"
        assert project_state.project_status.phase == "analyzing"
    
    @pytest.mark.asyncio
    async def test_process_user_feedback_edit(self, root_agent):
        """Test processing user feedback for edits."""
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            evaluation_results={"overall_score": 7.0},
            timeline=Mock()
        )
        
        root_agent.refinement_agent.parse_user_edit_request = AsyncMock(
            return_value={
                "status": "success",
                "intent": "edit",
                "parameters": {"duration": 30}
            }
        )
        
        root_agent.refinement_agent.process_evaluation_feedback = AsyncMock(
            return_value={
                "status": "success",
                "edit_commands": {"adjust_durations": {"1": 2}}
            }
        )
        
        root_agent.composition_agent.apply_edit_commands = AsyncMock(
            side_effect=lambda ps, **kwargs: ps
        )
        
        root_agent.composition_agent.create_memory_movie = AsyncMock(
            side_effect=lambda ps, **kwargs: ps
        )
        
        result = await root_agent.process_user_feedback(
            project_state=project_state,
            user_feedback="Make it 30 seconds"
        )
        
        assert result["status"] == "success"
        root_agent.composition_agent.apply_edit_commands.assert_called_once()
        root_agent.composition_agent.create_memory_movie.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_user_feedback_evaluate(self, root_agent):
        """Test processing user feedback for evaluation."""
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test")
        )
        
        root_agent.refinement_agent.parse_user_edit_request = AsyncMock(
            return_value={
                "status": "success",
                "intent": "evaluate",
                "parameters": {}
            }
        )
        
        root_agent.evaluation_agent.evaluate_memory_movie = AsyncMock(
            return_value={
                "status": "success",
                "evaluation": {"overall_score": 8.0}
            }
        )
        
        result = await root_agent.process_user_feedback(
            project_state=project_state,
            user_feedback="Check the video quality"
        )
        
        assert result["status"] == "success"
        root_agent.evaluation_agent.evaluate_memory_movie.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_project_state(self, root_agent):
        """Test project state saving."""
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test"),
            project_id="test-123"
        )
        
        root_agent.storage.save_project = AsyncMock()
        
        await root_agent._save_project_state(project_state)
        
        root_agent.storage.save_project.assert_called_once_with(
            "test-123",
            project_state.model_dump()
        )
    
    @pytest.mark.asyncio
    async def test_error_handling(self, root_agent):
        """Test error handling in main workflow."""
        root_agent.analysis_agent.analyze_project = AsyncMock(
            side_effect=Exception("Analysis failed")
        )
        
        result = await root_agent.create_memory_movie(
            media_paths=["test.jpg"],
            user_prompt="Test error",
            target_duration=10
        )
        
        assert result["status"] == "error"
        assert "Analysis failed" in result["error"]