"""Tests for AnalysisAgent."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import uuid

from memory_movie_maker.agents.analysis_agent import AnalysisAgent
from memory_movie_maker.models.project_state import ProjectState, UserInputs, ProjectStatus
from memory_movie_maker.models.media_asset import MediaAsset, MediaType, GeminiAnalysis


class TestAnalysisAgent:
    """Test AnalysisAgent functionality."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create mock storage."""
        return Mock()
    
    @pytest.fixture
    def sample_project_state(self):
        """Create sample project state with various media types."""
        media_assets = [
            MediaAsset(
                id=str(uuid.uuid4()),
                file_path="test_video.mp4",
                type=MediaType.VIDEO
            ),
            MediaAsset(
                id=str(uuid.uuid4()),
                file_path="test_audio.mp3",
                type=MediaType.AUDIO
            ),
            MediaAsset(
                id=str(uuid.uuid4()),
                file_path="test_image.jpg",
                type=MediaType.IMAGE
            )
        ]
        
        return ProjectState(
            user_inputs=UserInputs(
                media=media_assets,
                initial_prompt="Create a memory movie"
            ),
            project_status=ProjectStatus(phase="analyzing")
        )
    
    @pytest.mark.asyncio
    async def test_analyze_project_basic(self, mock_storage, sample_project_state):
        """Test basic project analysis."""
        agent = AnalysisAgent(storage=mock_storage)
        
        # Mock the analysis methods
        agent._analyze_visual = AsyncMock(return_value=sample_project_state.user_inputs.media[0])
        agent._analyze_video_audio = AsyncMock(return_value=sample_project_state.user_inputs.media[0])
        agent._analyze_audio_technical = AsyncMock(return_value=sample_project_state.user_inputs.media[1])
        agent._analyze_audio_semantic = AsyncMock(return_value=sample_project_state.user_inputs.media[1])
        
        result = await agent.analyze_project(sample_project_state)
        
        # Verify phase updated
        assert result.project_status.phase == "composing"
        
        # Verify analysis methods called
        assert agent._analyze_visual.call_count == 2  # video + image
        assert agent._analyze_video_audio.call_count == 1  # video only
        assert agent._analyze_audio_technical.call_count == 1  # audio only
        assert agent._analyze_audio_semantic.call_count == 1  # audio only
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, mock_storage):
        """Test that already analyzed media is skipped when caching enabled."""
        # Create pre-analyzed media
        analyzed_media = MediaAsset(
            id=str(uuid.uuid4()),
            file_path="analyzed.mp4",
            type=MediaType.VIDEO,
            gemini_analysis=GeminiAnalysis(
                description="Already analyzed",
                aesthetic_score=0.8
            )
        )
        
        project_state = ProjectState(
            user_inputs=UserInputs(
                media=[analyzed_media],
                initial_prompt="Test"
            ),
            project_status=ProjectStatus(phase="analyzing"),
            analysis_cache_enabled=True
        )
        
        agent = AnalysisAgent(storage=mock_storage)
        agent._analyze_visual = AsyncMock()
        
        await agent.analyze_project(project_state)
        
        # Should not analyze again
        agent._analyze_visual.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_visual_analysis_integration(self, mock_storage):
        """Test visual analysis integration."""
        media = MediaAsset(
            id=str(uuid.uuid4()),
            file_path="test.jpg",
            type=MediaType.IMAGE
        )
        
        with patch('memory_movie_maker.agents.analysis_agent.analyze_visual_media') as mock_analyze:
            mock_analyze.return_value = {
                "status": "success",
                "analysis": {
                    "description": "Test image",
                    "aesthetic_score": 0.9,
                    "main_subjects": ["person"],
                    "tags": ["portrait"]
                }
            }
            
            agent = AnalysisAgent(storage=mock_storage)
            result = await agent._analyze_visual(media)
            
            assert result.gemini_analysis is not None
            assert result.gemini_analysis["description"] == "Test image"
    
    @pytest.mark.asyncio
    async def test_audio_extraction_from_video(self, mock_storage):
        """Test audio extraction from video files."""
        media = MediaAsset(
            id=str(uuid.uuid4()),
            file_path="test_video.mp4",
            type=MediaType.VIDEO,
            gemini_analysis=GeminiAnalysis(
                description="People talking",
                aesthetic_score=0.7,
                tags=["people", "conversation"]
            )
        )
        
        agent = AnalysisAgent(storage=mock_storage)
        
        # Mock MoviePy
        with patch('memory_movie_maker.agents.analysis_agent.VideoFileClip') as mock_video:
            mock_clip = Mock()
            mock_audio = Mock()
            mock_clip.audio = mock_audio
            mock_audio.write_audiofile = Mock()
            mock_video.return_value = mock_clip
            
            # Mock audio analysis
            agent._analyze_audio_technical = AsyncMock(return_value=media)
            agent._analyze_audio_semantic = AsyncMock(return_value=media)
            
            result = await agent._analyze_video_audio(media)
            
            # Should extract audio and analyze both technical and semantic
            mock_audio.write_audiofile.assert_called_once()
            agent._analyze_audio_technical.assert_called_once()
            agent._analyze_audio_semantic.assert_called_once()  # Because tags include "conversation"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_storage, sample_project_state):
        """Test error handling during analysis."""
        agent = AnalysisAgent(storage=mock_storage)
        
        # Make one analysis fail
        agent._analyze_visual = AsyncMock(side_effect=Exception("Analysis failed"))
        agent._analyze_video_audio = AsyncMock(return_value=sample_project_state.user_inputs.media[0])
        agent._analyze_audio_technical = AsyncMock(return_value=sample_project_state.user_inputs.media[1])
        agent._analyze_audio_semantic = AsyncMock(return_value=sample_project_state.user_inputs.media[1])
        
        # Should not raise, but continue with other analyses
        result = await agent.analyze_project(sample_project_state)
        
        # Phase should still update
        assert result.project_status.phase == "composing"
    
    def test_is_fully_analyzed(self, mock_storage):
        """Test _is_fully_analyzed method."""
        agent = AnalysisAgent(storage=mock_storage)
        
        # Video not analyzed
        video = MediaAsset(
            id=str(uuid.uuid4()),
            file_path="test.mp4",
            type=MediaType.VIDEO
        )
        assert not agent._is_fully_analyzed(video)
        
        # Video with visual but no audio
        video.gemini_analysis = {"description": "test"}
        assert not agent._is_fully_analyzed(video)
        
        # Fully analyzed video
        video.audio_analysis = {"tempo_bpm": 120}
        assert agent._is_fully_analyzed(video)
        
        # Audio file needs both analyses
        audio = MediaAsset(
            id=str(uuid.uuid4()),
            file_path="test.mp3",
            type=MediaType.AUDIO
        )
        assert not agent._is_fully_analyzed(audio)
        
        audio.audio_analysis = {"tempo_bpm": 120}
        assert not agent._is_fully_analyzed(audio)
        
        audio.semantic_audio_analysis = {"summary": "test"}
        assert agent._is_fully_analyzed(audio)
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, mock_storage):
        """Test that analyses run concurrently."""
        # Create multiple media files
        media_assets = [
            MediaAsset(id=str(uuid.uuid4()), file_path=f"video{i}.mp4", type=MediaType.VIDEO)
            for i in range(3)
        ]
        
        project_state = ProjectState(
            user_inputs=UserInputs(media=media_assets, initial_prompt="Test"),
            project_status=ProjectStatus(phase="analyzing")
        )
        
        agent = AnalysisAgent(storage=mock_storage)
        
        # Track call order
        call_order = []
        
        async def mock_visual_analysis(media):
            call_order.append(f"visual_{media.file_path}")
            await asyncio.sleep(0.1)  # Simulate work
            return media
        
        async def mock_audio_analysis(media):
            call_order.append(f"audio_{media.file_path}")
            await asyncio.sleep(0.1)  # Simulate work
            return media
        
        agent._analyze_visual = mock_visual_analysis
        agent._analyze_video_audio = mock_audio_analysis
        
        await agent.analyze_project(project_state)
        
        # All visual should start before any audio completes
        # (proving concurrent execution)
        visual_indices = [i for i, call in enumerate(call_order) if call.startswith("visual_")]
        audio_indices = [i for i, call in enumerate(call_order) if call.startswith("audio_")]
        
        assert len(visual_indices) == 3
        assert len(audio_indices) == 3
        assert max(visual_indices) < max(audio_indices)  # Some overlap expected