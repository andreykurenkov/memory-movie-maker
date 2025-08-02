"""Tests for video renderer."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
from pathlib import Path

from memory_movie_maker.tools.video_renderer import VideoRenderer, render_video
from memory_movie_maker.models.timeline import Timeline, Segment, TransitionType
from memory_movie_maker.models.media_asset import MediaAsset, MediaType
from memory_movie_maker.models.project_state import ProjectState, UserInputs


class TestVideoRenderer:
    """Test video renderer functionality."""
    
    @pytest.fixture
    def renderer(self):
        """Create video renderer instance."""
        return VideoRenderer()
    
    @pytest.fixture
    def sample_timeline(self):
        """Create sample timeline."""
        return Timeline(
            segments=[
                Segment(
                    media_id="1",
                    start_time=0.0,
                    duration=2.0,
                    effects=["ken_burns"],
                    transition_out=TransitionType.CROSSFADE
                ),
                Segment(
                    media_id="2",
                    start_time=2.0,
                    duration=3.0,
                    trim_start=1.0,
                    trim_end=4.0,
                    transition_out=TransitionType.FADE_TO_BLACK
                )
            ],
            audio_track_id="music.mp3",
            total_duration=5.0
        )
    
    @pytest.fixture
    def media_assets(self):
        """Create media assets dictionary."""
        return {
            "1": MediaAsset(
                id="1",
                file_path="photo.jpg",
                type=MediaType.IMAGE
            ),
            "2": MediaAsset(
                id="2",
                file_path="video.mp4",
                type=MediaType.VIDEO,
                duration=10.0
            )
        }
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.video_renderer.ImageClip')
    @patch('memory_movie_maker.tools.video_renderer.VideoFileClip')
    @patch('memory_movie_maker.tools.video_renderer.concatenate_videoclips')
    async def test_render_video(
        self, mock_concat, mock_video_clip, mock_image_clip,
        renderer, sample_timeline, media_assets
    ):
        """Test basic video rendering."""
        # Mock clips
        mock_img_clip = MagicMock()
        mock_vid_clip = MagicMock()
        mock_image_clip.return_value = mock_img_clip
        mock_video_clip.return_value = mock_vid_clip
        
        # Mock concatenation
        mock_final_video = MagicMock()
        mock_concat.return_value = mock_final_video
        
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            output_path = await renderer.render_video(
                timeline=sample_timeline,
                media_assets=media_assets,
                output_path=tmp.name
            )
            
            assert output_path == tmp.name
            mock_image_clip.assert_called_once()
            mock_video_clip.assert_called_once()
            mock_concat.assert_called_once()
            mock_final_video.write_videofile.assert_called_once()
    
    @patch('memory_movie_maker.tools.video_renderer.ImageClip')
    def test_create_image_clip(self, mock_image_clip, renderer):
        """Test image clip creation."""
        media = MediaAsset(id="1", file_path="test.jpg", type=MediaType.IMAGE)
        segment = Segment(media_id="1", start_time=0, duration=3)
        
        mock_clip = MagicMock()
        mock_image_clip.return_value = mock_clip
        
        clip = renderer._create_image_clip(media, segment, (1920, 1080))
        
        mock_image_clip.assert_called_with("test.jpg", duration=3)
        assert clip is not None
    
    @patch('memory_movie_maker.tools.video_renderer.VideoFileClip')
    def test_create_video_clip_with_trim(self, mock_video_clip, renderer):
        """Test video clip creation with trimming."""
        media = MediaAsset(
            id="1", file_path="test.mp4", type=MediaType.VIDEO, duration=10
        )
        segment = Segment(
            media_id="1", start_time=0, duration=3,
            trim_start=2.0, trim_end=5.0
        )
        
        mock_clip = MagicMock()
        mock_clip.duration = 10.0
        mock_clip.subclipped = MagicMock(return_value=mock_clip)
        mock_video_clip.return_value = mock_clip
        
        clip = renderer._create_video_clip(media, segment, (1920, 1080))
        
        mock_clip.subclipped.assert_called()
        assert clip is not None
    
    def test_resize_clip(self, renderer):
        """Test clip resizing logic."""
        mock_clip = MagicMock()
        mock_clip.size = (1920, 1080)
        
        # Test no resize needed
        result = renderer._resize_clip(mock_clip, (1920, 1080))
        assert result == mock_clip
        
        # Test downscale
        mock_clip.size = (3840, 2160)
        with patch('memory_movie_maker.tools.video_renderer.resize') as mock_resize:
            mock_resize.return_value = mock_clip
            result = renderer._resize_clip(mock_clip, (1920, 1080))
            mock_resize.assert_called_once()
    
    def test_apply_ken_burns(self, renderer):
        """Test Ken Burns effect application."""
        mock_clip = MagicMock()
        mock_clip.zoom = MagicMock(return_value=mock_clip)
        mock_clip.size = (1920, 1080)
        
        with patch('memory_movie_maker.tools.video_renderer.resize'):
            result = renderer._apply_ken_burns(mock_clip, 3.0)
            mock_clip.zoom.assert_called_once()
    
    def test_apply_transitions(self, renderer):
        """Test transition application between clips."""
        clips = [MagicMock() for _ in range(3)]
        segments = [
            Segment(media_id="1", start_time=0, duration=2,
                   transition_out=TransitionType.CROSSFADE),
            Segment(media_id="2", start_time=2, duration=2,
                   transition_out=TransitionType.FADE_TO_BLACK),
            Segment(media_id="3", start_time=4, duration=2)
        ]
        
        with patch('memory_movie_maker.tools.video_renderer.fadeout') as mock_fadeout:
            with patch('memory_movie_maker.tools.video_renderer.fadein') as mock_fadein:
                mock_fadeout.return_value = clips[0]
                mock_fadein.return_value = clips[1]
                
                result = renderer._apply_transitions(clips, segments)
                
                # Should apply fade effects
                mock_fadeout.assert_called()
                mock_fadein.assert_called()
    
    @patch('memory_movie_maker.tools.video_renderer.AudioFileClip')
    def test_add_audio_track(self, mock_audio_clip, renderer):
        """Test adding audio track to video."""
        mock_video = MagicMock()
        mock_video.duration = 10.0
        mock_video.with_audio = MagicMock(return_value=mock_video)
        
        mock_audio = MagicMock()
        mock_audio.duration = 15.0
        mock_audio.subclipped = MagicMock(return_value=mock_audio)
        mock_audio_clip.return_value = mock_audio
        
        result = renderer._add_audio_track(mock_video, "music.mp3")
        
        mock_audio_clip.assert_called_with("music.mp3")
        mock_audio.subclipped.assert_called_with(0, 10.0)
        mock_video.with_audio.assert_called_with(mock_audio)


class TestRenderVideoTool:
    """Test render video tool function."""
    
    @pytest.mark.asyncio
    async def test_render_video_success(self):
        """Test successful video rendering."""
        timeline = Timeline(
            segments=[
                Segment(media_id="1", start_time=0, duration=2)
            ],
            total_duration=2
        )
        
        project_state = ProjectState(
            user_inputs=UserInputs(
                media=[
                    MediaAsset(id="1", file_path="test.jpg", type=MediaType.IMAGE)
                ],
                initial_prompt="Test"
            ),
            timeline=timeline
        )
        
        with patch('memory_movie_maker.tools.video_renderer.VideoRenderer') as mock_renderer:
            mock_instance = AsyncMock()
            mock_instance.render_video.return_value = "output.mp4"
            mock_renderer.return_value = mock_instance
            
            result = await render_video(
                project_state=project_state.model_dump(),
                output_filename="test.mp4"
            )
            
            assert result["status"] == "success"
            assert result["output_path"] == "output.mp4"
    
    @pytest.mark.asyncio
    async def test_render_video_no_timeline(self):
        """Test rendering without timeline."""
        project_state = ProjectState(
            user_inputs=UserInputs(media=[], initial_prompt="Test")
        )
        
        result = await render_video(
            project_state=project_state.model_dump()
        )
        
        assert result["status"] == "error"
        assert "No timeline found" in result["error"]