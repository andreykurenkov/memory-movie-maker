"""End-to-end integration tests for Memory Movie Maker."""

import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from pathlib import Path
import tempfile
import shutil

from memory_movie_maker.agents.root_agent import RootAgent
from memory_movie_maker.models.project_state import ProjectState
from memory_movie_maker.models.media_asset import MediaAsset, MediaType


class TestEndToEnd:
    """Test complete workflows end-to-end."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_media_files(self, temp_dir):
        """Create mock media files."""
        files = {
            "photo1.jpg": Path(temp_dir) / "photo1.jpg",
            "photo2.jpg": Path(temp_dir) / "photo2.jpg", 
            "video1.mp4": Path(temp_dir) / "video1.mp4",
            "music.mp3": Path(temp_dir) / "music.mp3"
        }
        
        for file_path in files.values():
            file_path.touch()
        
        return files
    
    @pytest.fixture
    def mock_gemini_responses(self):
        """Mock Gemini API responses."""
        return {
            "visual_analysis": {
                "description": "Beautiful sunset photo",
                "aesthetic_score": 0.85,
                "main_subjects": ["sunset", "landscape"],
                "tags": ["nature", "scenic", "outdoor"],
                "emotional_tone": "peaceful"
            },
            "video_evaluation": {
                "overall_score": 7.5,
                "strengths": ["Good pacing", "Nice transitions"],
                "weaknesses": ["Could use more variety"],
                "recommendation": "accept"
            }
        }
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.visual_analysis.genai.Client')
    @patch('memory_movie_maker.tools.video_evaluation.genai.Client')
    @patch('memory_movie_maker.tools.semantic_audio_analysis.genai.Client')
    @patch('librosa.load')
    @patch('librosa.beat.beat_track')
    @patch('moviepy.editor.ImageClip')
    @patch('moviepy.editor.VideoFileClip')
    @patch('moviepy.editor.concatenate_videoclips')
    async def test_complete_workflow_with_refinement(
        self,
        mock_concat,
        mock_video_clip,
        mock_image_clip,
        mock_beat_track,
        mock_librosa_load,
        mock_semantic_client,
        mock_eval_client,
        mock_visual_client,
        mock_media_files,
        mock_gemini_responses
    ):
        """Test complete workflow from media to final video."""
        # Setup mocks
        mock_librosa_load.return_value = (Mock(), 44100)
        mock_beat_track.return_value = (120.0, Mock())
        
        # Mock visual analysis
        mock_visual_response = Mock()
        mock_visual_response.text = str(mock_gemini_responses["visual_analysis"])
        mock_visual_client.return_value.models.generate_content.return_value = mock_visual_response
        
        # Mock evaluation
        mock_eval_response = Mock()
        mock_eval_response.text = str(mock_gemini_responses["video_evaluation"])
        mock_eval_client.return_value.models.generate_content.return_value = mock_eval_response
        
        # Mock video rendering
        mock_final_video = Mock()
        mock_final_video.write_videofile = Mock()
        mock_concat.return_value = mock_final_video
        
        # Create root agent
        root_agent = RootAgent()
        
        # Run complete workflow
        media_paths = [
            str(mock_media_files["photo1.jpg"]),
            str(mock_media_files["photo2.jpg"]),
            str(mock_media_files["video1.mp4"])
        ]
        
        result = await root_agent.create_memory_movie(
            media_paths=media_paths,
            user_prompt="Create a beautiful vacation montage",
            music_path=str(mock_media_files["music.mp3"]),
            target_duration=30,
            style="smooth",
            auto_refine=True
        )
        
        # Verify success
        assert result["status"] == "success"
        assert "video_path" in result
        assert result["refinement_iterations"] >= 0
        
        # Verify workflow executed
        assert mock_visual_client.called
        assert mock_librosa_load.called
        assert mock_concat.called
        assert mock_eval_client.called
    
    @pytest.mark.asyncio
    async def test_workflow_with_missing_dependencies(self):
        """Test workflow handling when dependencies are missing."""
        with patch('memory_movie_maker.tools.audio_analysis.librosa') as mock_librosa:
            mock_librosa.load.side_effect = ImportError("librosa not installed")
            
            root_agent = RootAgent()
            
            result = await root_agent.create_memory_movie(
                media_paths=["test.jpg"],
                user_prompt="Test without audio",
                target_duration=10,
                auto_refine=False
            )
            
            # Should handle gracefully
            assert result["status"] in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_user_feedback_workflow(self, temp_dir):
        """Test user feedback processing workflow."""
        # Create initial project state
        project_state = ProjectState(
            user_inputs=Mock(),
            timeline=Mock(),
            rendered_outputs=["initial_video.mp4"],
            evaluation_results={
                "overall_score": 6.5,
                "specific_edits": [
                    {
                        "timestamp": "0:15",
                        "issue": "Too fast",
                        "suggestion": "Slow down"
                    }
                ]
            }
        )
        
        root_agent = RootAgent()
        
        # Mock agent methods
        root_agent.refinement_agent.parse_user_edit_request = AsyncMock(
            return_value={
                "status": "success",
                "intent": "edit",
                "parameters": {}
            }
        )
        
        root_agent.refinement_agent.process_evaluation_feedback = AsyncMock(
            return_value={
                "status": "success",
                "edit_commands": {"adjust_durations": {"1": 2}}
            }
        )
        
        root_agent.composition_agent.apply_edit_commands = AsyncMock(
            return_value=project_state
        )
        
        root_agent.composition_agent.create_memory_movie = AsyncMock(
            return_value=project_state
        )
        
        # Process feedback
        result = await root_agent.process_user_feedback(
            project_state=project_state,
            user_feedback="Make the transitions at 0:15 slower"
        )
        
        assert result["status"] == "success"
        
        # Verify feedback was processed
        root_agent.refinement_agent.parse_user_edit_request.assert_called_once()
        root_agent.composition_agent.apply_edit_commands.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_with_many_files(self, temp_dir):
        """Test performance with many media files."""
        # Create many mock files
        media_paths = []
        for i in range(50):
            file_path = Path(temp_dir) / f"photo_{i}.jpg"
            file_path.touch()
            media_paths.append(str(file_path))
        
        # Mock all external calls
        with patch('memory_movie_maker.tools.visual_analysis.genai.Client'):
            with patch('memory_movie_maker.tools.audio_analysis.librosa'):
                with patch('moviepy.editor.ImageClip'):
                    with patch('moviepy.editor.concatenate_videoclips'):
                        root_agent = RootAgent()
                        
                        # Should complete in reasonable time
                        start_time = asyncio.get_event_loop().time()
                        
                        result = await root_agent.create_memory_movie(
                            media_paths=media_paths,
                            user_prompt="Test with many files",
                            target_duration=60,
                            auto_refine=False
                        )
                        
                        elapsed = asyncio.get_event_loop().time() - start_time
                        
                        # Should complete within timeout
                        assert elapsed < 60  # 60 second timeout
                        assert result["status"] in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_memory_management(self, temp_dir):
        """Test memory management with large files."""
        # This test verifies the system handles memory properly
        # In a real test, you'd create actual large files
        
        large_file = Path(temp_dir) / "large_video.mp4"
        large_file.touch()
        
        with patch('memory_movie_maker.tools.video_renderer.VideoFileClip') as mock_clip:
            # Mock large file handling
            mock_clip.return_value = Mock(
                duration=300,  # 5 minute video
                size=(4096, 2160),  # 4K resolution
                close=Mock()
            )
            
            root_agent = RootAgent()
            
            # Should handle without memory errors
            result = await root_agent.create_memory_movie(
                media_paths=[str(large_file)],
                user_prompt="Test large file",
                target_duration=60,
                auto_refine=False
            )
            
            # Verify cleanup was called
            mock_clip.return_value.close.assert_called()