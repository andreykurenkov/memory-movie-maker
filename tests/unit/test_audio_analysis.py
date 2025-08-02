"""Unit tests for audio analysis tool."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

from memory_movie_maker.tools.audio_analysis import AudioAnalysisTool
from memory_movie_maker.models.media_asset import AudioAnalysisProfile, AudioVibe


class TestAudioAnalysisTool:
    """Test AudioAnalysisTool class."""
    
    @pytest.fixture
    def mock_audio_data(self):
        """Create mock audio data."""
        # 2 seconds of random audio at 22050 Hz
        y = np.random.randn(44100)
        sr = 22050
        return y, sr
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.audio_analysis.librosa')
    async def test_analyze_audio(self, mock_librosa, mock_audio_data):
        """Test basic audio analysis."""
        y, sr = mock_audio_data
        
        # Mock librosa functions
        mock_librosa.load.return_value = (y, sr)
        mock_librosa.beat.beat_track.return_value = (120.0, np.array([0, 22050, 44100]))
        mock_librosa.frames_to_time.return_value = np.array([0.0, 1.0, 2.0])
        mock_librosa.feature.rms.return_value = np.random.rand(1, 100) * 0.1
        mock_librosa.onset.onset_detect.return_value = np.array([10, 30, 50])
        mock_librosa.onset.onset_strength.return_value = np.random.rand(100)
        mock_librosa.feature.spectral_centroid.return_value = np.array([1000.0] * 100)
        mock_librosa.feature.spectral_rolloff.return_value = np.array([2000.0] * 100)
        mock_librosa.feature.zero_crossing_rate.return_value = np.array([0.1] * 100)
        
        tool = AudioAnalysisTool()
        result = await tool.analyze_audio("test.mp3")
        
        assert isinstance(result, AudioAnalysisProfile)
        assert result.file_path == "test.mp3"
        assert result.tempo_bpm == 120.0
        assert len(result.beat_timestamps) == 3
        assert result.duration == pytest.approx(2.0)
        assert len(result.energy_curve) > 0
        assert all(0 <= e <= 1 for e in result.energy_curve)
        assert isinstance(result.vibe, AudioVibe)
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.audio_analysis.librosa')
    async def test_vibe_analysis(self, mock_librosa, mock_audio_data):
        """Test vibe analysis produces valid values."""
        y, sr = mock_audio_data
        
        # Mock librosa functions
        mock_librosa.load.return_value = (y, sr)
        mock_librosa.beat.beat_track.return_value = (100.0, np.array([]))
        mock_librosa.frames_to_time.return_value = np.array([])
        mock_librosa.feature.rms.return_value = np.array([[0.05]])
        mock_librosa.onset.onset_detect.return_value = np.array([])
        mock_librosa.onset.onset_strength.return_value = np.array([0.5] * 100)
        mock_librosa.feature.spectral_centroid.return_value = np.array([3000.0])
        mock_librosa.feature.spectral_rolloff.return_value = np.array([4000.0])
        mock_librosa.feature.zero_crossing_rate.return_value = np.array([0.2])
        
        tool = AudioAnalysisTool()
        result = await tool.analyze_audio("test.mp3")
        
        vibe = result.vibe
        assert 0 <= vibe.danceability <= 1
        assert 0 <= vibe.energy <= 1
        assert 0 <= vibe.valence <= 1
        assert 0 <= vibe.arousal <= 1
        assert vibe.mood in ["energetic-happy", "calm-positive", "intense-dark", "melancholic", "balanced"]
        assert vibe.genre is not None
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.audio_analysis.librosa')
    async def test_energy_curve_normalization(self, mock_librosa, mock_audio_data):
        """Test that energy curve is properly normalized."""
        y, sr = mock_audio_data
        
        # Mock with high RMS values to test normalization
        mock_librosa.load.return_value = (y, sr)
        mock_librosa.beat.beat_track.return_value = (120.0, np.array([]))
        mock_librosa.frames_to_time.return_value = np.array([])
        mock_librosa.feature.rms.return_value = np.array([np.random.rand(100) * 10])  # High values
        mock_librosa.onset.onset_detect.return_value = np.array([])
        mock_librosa.onset.onset_strength.return_value = np.array([0.5])
        mock_librosa.feature.spectral_centroid.return_value = np.array([1000.0])
        mock_librosa.feature.spectral_rolloff.return_value = np.array([2000.0])
        mock_librosa.feature.zero_crossing_rate.return_value = np.array([0.1])
        
        tool = AudioAnalysisTool()
        result = await tool.analyze_audio("test.mp3")
        
        # All energy values should be between 0 and 1
        assert all(0 <= e <= 1 for e in result.energy_curve)
        assert max(result.energy_curve) <= 1.0
        assert min(result.energy_curve) >= 0.0
    
    @pytest.mark.asyncio
    async def test_storage_integration(self):
        """Test loading audio from storage."""
        # Mock storage
        mock_storage = AsyncMock()
        mock_io = Mock()
        mock_io.read.return_value = b"fake audio data"
        mock_storage.download.return_value = mock_io
        
        with patch('memory_movie_maker.tools.audio_analysis.librosa.load') as mock_load:
            mock_load.return_value = (np.random.randn(22050), 22050)
            
            with patch('memory_movie_maker.tools.audio_analysis.Path') as mock_path:
                mock_path.return_value.exists.return_value = False
                
                tool = AudioAnalysisTool(storage=mock_storage)
                
                # This should trigger storage download
                with patch('memory_movie_maker.tools.audio_analysis.tempfile.NamedTemporaryFile'):
                    await tool._load_audio("storage://audio.mp3")
                
                mock_storage.download.assert_called_once_with("storage://audio.mp3")
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in audio analysis."""
        with patch('memory_movie_maker.tools.audio_analysis.librosa.load') as mock_load:
            mock_load.side_effect = Exception("Failed to load audio")
            
            tool = AudioAnalysisTool()
            with pytest.raises(Exception) as exc_info:
                await tool.analyze_audio("bad_file.mp3")
            
            assert "Failed to load audio" in str(exc_info.value)


class TestAudioAnalysisADKTool:
    """Test the ADK tool wrapper."""
    
    @pytest.mark.asyncio
    async def test_analyze_audio_media_success(self):
        """Test successful audio analysis through ADK tool."""
        from memory_movie_maker.tools.audio_analysis import analyze_audio_media
        
        with patch('memory_movie_maker.tools.audio_analysis.AudioAnalysisTool') as mock_tool_class:
            mock_tool = mock_tool_class.return_value
            mock_profile = Mock()
            mock_profile.model_dump.return_value = {"test": "data"}
            mock_tool.analyze_audio = AsyncMock(return_value=mock_profile)
            
            result = await analyze_audio_media("test.mp3")
            
            assert result["status"] == "success"
            assert result["analysis"] == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_analyze_audio_media_error(self):
        """Test error handling in ADK tool."""
        from memory_movie_maker.tools.audio_analysis import analyze_audio_media
        
        with patch('memory_movie_maker.tools.audio_analysis.AudioAnalysisTool') as mock_tool_class:
            mock_tool = mock_tool_class.return_value
            mock_tool.analyze_audio = AsyncMock(side_effect=Exception("Analysis failed"))
            
            result = await analyze_audio_media("test.mp3")
            
            assert result["status"] == "error"
            assert "Analysis failed" in result["error"]