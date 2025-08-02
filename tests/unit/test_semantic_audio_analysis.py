"""Unit tests for semantic audio analysis tool."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from memory_movie_maker.tools.semantic_audio_analysis import (
    SemanticAudioAnalysisTool, 
    SemanticAudioAnalysis,
    AudioSegment
)


class TestSemanticAudioAnalysisTool:
    """Test SemanticAudioAnalysisTool class."""
    
    @pytest.fixture
    def mock_gemini_response(self):
        """Create mock Gemini API response."""
        return {
            "transcript": "Hello, this is a test audio file.",
            "summary": "A brief test audio with greeting.",
            "segments": [
                {
                    "start_time": 0.0,
                    "end_time": 3.0,
                    "content": "Hello, this is a test audio file.",
                    "type": "speech",
                    "speaker": "Speaker 1",
                    "importance": 0.8
                }
            ],
            "speakers": ["Speaker 1"],
            "topics": ["greeting", "testing"],
            "emotional_tone": "friendly",
            "key_moments": [
                {
                    "timestamp": 0.5,
                    "description": "Greeting begins",
                    "sync_suggestion": "Fade in on speaker"
                }
            ],
            "sound_elements": {
                "speech": [0.0, 3.0]
            }
        }
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.semantic_audio_analysis.genai')
    async def test_analyze_audio_semantics(self, mock_genai, mock_gemini_response):
        """Test semantic audio analysis."""
        # Mock client
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        
        # Mock file upload
        mock_file = Mock()
        mock_file.name = "test_file"
        mock_file.state = "ACTIVE"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file
        
        # Mock model response
        mock_response = Mock()
        mock_response.text = json.dumps(mock_gemini_response)
        mock_client.models.generate_content.return_value = mock_response
        
        # Mock file deletion
        mock_client.files.delete.return_value = None
        
        tool = SemanticAudioAnalysisTool()
        result = await tool.analyze_audio_semantics("test.mp3")
        
        assert isinstance(result, SemanticAudioAnalysis)
        assert result.transcript == "Hello, this is a test audio file."
        assert result.summary == "A brief test audio with greeting."
        assert len(result.segments) == 1
        assert result.segments[0].type == "speech"
        assert result.emotional_tone == "friendly"
        assert len(result.speakers) == 1
        assert len(result.topics) == 2
        assert len(result.key_moments) == 1
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.semantic_audio_analysis.genai')
    async def test_audio_segments(self, mock_genai, mock_gemini_response):
        """Test audio segment parsing."""
        # Setup mocks
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        
        mock_file = Mock()
        mock_file.name = "test_file"
        mock_file.state = "ACTIVE"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file
        
        mock_response = Mock()
        mock_response.text = json.dumps(mock_gemini_response)
        mock_client.models.generate_content.return_value = mock_response
        mock_client.files.delete.return_value = None
        
        tool = SemanticAudioAnalysisTool()
        result = await tool.analyze_audio_semantics("test.mp3")
        
        segment = result.segments[0]
        assert isinstance(segment, AudioSegment)
        assert segment.start_time == 0.0
        assert segment.end_time == 3.0
        assert segment.content == "Hello, this is a test audio file."
        assert segment.speaker == "Speaker 1"
        assert segment.importance == 0.8
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.semantic_audio_analysis.genai')
    async def test_no_speech_audio(self, mock_genai):
        """Test analyzing audio without speech."""
        # Mock response for music-only audio
        music_response = {
            "transcript": None,
            "summary": "Instrumental music track with upbeat rhythm.",
            "segments": [
                {
                    "start_time": 0.0,
                    "end_time": 30.0,
                    "content": "Upbeat instrumental music",
                    "type": "music",
                    "speaker": None,
                    "importance": 0.7
                }
            ],
            "speakers": [],
            "topics": ["music", "instrumental"],
            "emotional_tone": "upbeat",
            "key_moments": [
                {
                    "timestamp": 15.0,
                    "description": "Music reaches crescendo",
                    "sync_suggestion": "Peak action moment"
                }
            ],
            "sound_elements": {
                "music": [0.0, 30.0]
            }
        }
        
        # Setup mocks
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        
        mock_file = Mock()
        mock_file.name = "test_file"
        mock_file.state = "ACTIVE"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file
        
        mock_response = Mock()
        mock_response.text = json.dumps(music_response)
        mock_client.models.generate_content.return_value = mock_response
        mock_client.files.delete.return_value = None
        
        tool = SemanticAudioAnalysisTool()
        result = await tool.analyze_audio_semantics("music.mp3")
        
        assert result.transcript is None
        assert len(result.speakers) == 0
        assert result.segments[0].type == "music"
        assert result.segments[0].speaker is None
        assert "music" in result.sound_elements
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.semantic_audio_analysis.genai')
    async def test_upload_failure(self, mock_genai):
        """Test handling of upload failure."""
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        
        # Mock failed upload
        mock_file = Mock()
        mock_file.state = "FAILED"
        mock_file.error = "Upload failed"
        mock_file.name = "test_file"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file
        
        tool = SemanticAudioAnalysisTool()
        with pytest.raises(Exception) as exc_info:
            await tool.analyze_audio_semantics("test.mp3")
        
        assert "Audio upload failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.semantic_audio_analysis.genai')
    async def test_analysis_error_handling(self, mock_genai):
        """Test graceful handling of analysis errors."""
        mock_client = Mock()
        mock_genai.Client.return_value = mock_client
        
        mock_file = Mock()
        mock_file.name = "test_file"
        mock_file.state = "ACTIVE"
        mock_client.files.upload.return_value = mock_file
        mock_client.files.get.return_value = mock_file
        
        # Mock analysis failure
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_client.files.delete.return_value = None
        
        tool = SemanticAudioAnalysisTool()
        result = await tool.analyze_audio_semantics("test.mp3")
        
        # Should return basic analysis on error
        assert result.summary == "Audio analysis failed"
        assert result.emotional_tone == "unknown"
        assert len(result.segments) == 0


class TestSemanticAudioADKTool:
    """Test the ADK tool wrapper."""
    
    @pytest.mark.asyncio
    async def test_analyze_audio_semantics_success(self):
        """Test successful semantic analysis through ADK tool."""
        from memory_movie_maker.tools.semantic_audio_analysis import analyze_audio_semantics
        
        with patch('memory_movie_maker.tools.semantic_audio_analysis.SemanticAudioAnalysisTool') as mock_tool_class:
            mock_tool = mock_tool_class.return_value
            mock_analysis = Mock()
            mock_analysis.model_dump.return_value = {"test": "data"}
            mock_tool.analyze_audio_semantics = AsyncMock(return_value=mock_analysis)
            
            result = await analyze_audio_semantics("test.mp3")
            
            assert result["status"] == "success"
            assert result["analysis"] == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_analyze_audio_semantics_error(self):
        """Test error handling in ADK tool."""
        from memory_movie_maker.tools.semantic_audio_analysis import analyze_audio_semantics
        
        with patch('memory_movie_maker.tools.semantic_audio_analysis.SemanticAudioAnalysisTool') as mock_tool_class:
            mock_tool = mock_tool_class.return_value
            mock_tool.analyze_audio_semantics = AsyncMock(side_effect=Exception("Analysis failed"))
            
            result = await analyze_audio_semantics("test.mp3")
            
            assert result["status"] == "error"
            assert "Analysis failed" in result["error"]