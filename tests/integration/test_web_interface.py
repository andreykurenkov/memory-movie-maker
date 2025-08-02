"""Integration tests for Gradio web interface."""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import tempfile
import gradio as gr

from memory_movie_maker.web.app import MemoryMovieMakerApp
from memory_movie_maker.models.project_state import ProjectState


class TestWebInterface:
    """Test Gradio web interface functionality."""
    
    @pytest.fixture
    def app(self):
        """Create app instance."""
        return MemoryMovieMakerApp()
    
    @pytest.fixture
    def mock_files(self):
        """Create mock file uploads."""
        return [
            {"name": "photo1.jpg", "data": b"fake_image_data"},
            {"name": "photo2.jpg", "data": b"fake_image_data2"}
        ]
    
    def test_interface_creation(self, app):
        """Test interface creation."""
        interface = app.create_interface()
        
        assert isinstance(interface, gr.Blocks)
        
        # Check main components exist
        components = {c.elem_id for c in interface.blocks.values() if hasattr(c, 'elem_id')}
        assert "media_upload" in components
        assert "music_upload" in components
        assert "output_video" in components
    
    @pytest.mark.asyncio
    async def test_create_video_async_success(self, app, mock_files):
        """Test async video creation."""
        # Mock root agent
        app.root_agent.create_memory_movie = AsyncMock(
            return_value={
                "status": "success",
                "video_path": "output.mp4",
                "project_state": Mock(
                    evaluation_results={"overall_score": 8.0}
                ),
                "refinement_iterations": 2,
                "final_score": 8.0
            }
        )
        
        video_path, log = await app.create_video_async(
            media_files=mock_files,
            music_file=None,
            prompt="Test video",
            duration=30,
            style="smooth",
            auto_refine=True
        )
        
        assert video_path == "output.mp4"
        assert "✅ Video created successfully!" in log
        assert "Final Score: 8.0/10" in log
    
    @pytest.mark.asyncio
    async def test_create_video_async_error(self, app, mock_files):
        """Test async video creation error handling."""
        app.root_agent.create_memory_movie = AsyncMock(
            return_value={
                "status": "error",
                "error": "Processing failed"
            }
        )
        
        video_path, log = await app.create_video_async(
            media_files=mock_files,
            music_file=None,
            prompt="Test video",
            duration=30,
            style="smooth",
            auto_refine=False
        )
        
        assert video_path is None
        assert "❌ Error: Processing failed" in log
    
    def test_create_video_validation(self, app):
        """Test video creation validation."""
        # No media files
        result = app.create_video(
            media_files=[],
            music_file=None,
            prompt="Test",
            duration=30,
            style="smooth",
            auto_refine=True
        )
        
        video, log, download_visible, refine_visible = result
        assert video is None
        assert "Please upload media files" in log
        assert not download_visible["visible"]
        
        # No prompt
        result = app.create_video(
            media_files=[{"name": "test.jpg"}],
            music_file=None,
            prompt="",
            duration=30,
            style="smooth",
            auto_refine=True
        )
        
        video, log, _, _ = result
        assert video is None
        assert "Please describe your video" in log
    
    def test_load_for_refinement(self, app):
        """Test loading video for refinement."""
        # Set current project state
        app.current_project_state = Mock(
            evaluation_results={
                "overall_score": 7.5,
                "recommendation": "minor_adjustments",
                "strengths": ["Good pacing"],
                "weaknesses": ["Some clips too short"],
                "specific_edits": [
                    {
                        "timestamp": "0:15",
                        "issue": "Clip too short",
                        "suggestion": "Extend by 2 seconds"
                    }
                ]
            }
        )
        
        video, eval_text = app.load_for_refinement("current_video.mp4")
        
        assert video == "current_video.mp4"
        assert "📊 Overall Score: 7.5/10" in eval_text
        assert "✓ Strengths:" in eval_text
        assert "Good pacing" in eval_text
        assert "⚠️ Issues:" in eval_text
        assert "[0:15] Clip too short" in eval_text
    
    def test_load_for_refinement_no_video(self, app):
        """Test loading for refinement without video."""
        app.current_project_state = None
        
        video, eval_text = app.load_for_refinement(None)
        
        assert video is None
        assert "No video to refine" in eval_text
    
    @pytest.mark.asyncio
    async def test_apply_feedback_async(self, app):
        """Test async feedback application."""
        app.current_project_state = Mock()
        
        app.root_agent.process_user_feedback = AsyncMock(
            return_value={
                "status": "success",
                "video_path": "refined_video.mp4",
                "project_state": Mock()
            }
        )
        
        video_path, log = await app.apply_feedback_async(
            "Make transitions smoother"
        )
        
        assert video_path == "refined_video.mp4"
        assert "✅ Feedback applied successfully!" in log
    
    def test_apply_feedback_validation(self, app):
        """Test feedback application validation."""
        # No feedback
        video, log = app.apply_feedback("")
        
        assert video is None
        assert "Please provide feedback" in log
        
        # No project loaded
        app.current_project_state = None
        video, log = app.apply_feedback("Some feedback")
        
        assert video is None
        assert "No project loaded" in log
    
    def test_cleanup(self, app):
        """Test cleanup functionality."""
        # Create temp directory
        temp_dir = app.temp_dir
        assert os.path.exists(temp_dir)
        
        # Cleanup
        app.cleanup()
        
        # Should remove temp directory
        assert not os.path.exists(temp_dir)
    
    @patch('gradio.Blocks.launch')
    def test_launch_app(self, mock_launch):
        """Test app launch."""
        from memory_movie_maker.web.app import launch_app
        
        launch_app(share=True, port=8080)
        
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args[1]
        assert call_args["share"] is True
        assert call_args["server_port"] == 8080
    
    def test_file_path_extraction(self, app):
        """Test file path extraction from Gradio file objects."""
        # Test dict format
        files = [
            {"name": "/tmp/gradio/file1.jpg"},
            {"name": "/tmp/gradio/file2.mp4"}
        ]
        
        paths = []
        for file in files:
            if isinstance(file, dict) and 'name' in file:
                paths.append(file['name'])
        
        assert len(paths) == 2
        assert paths[0].endswith("file1.jpg")
        assert paths[1].endswith("file2.mp4")
        
        # Test string format
        files = ["direct_path1.jpg", "direct_path2.mp4"]
        
        paths = []
        for file in files:
            if isinstance(file, str):
                paths.append(file)
        
        assert paths == files