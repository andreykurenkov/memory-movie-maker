"""Audio analysis tool using Librosa for music and sound analysis."""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import librosa
import asyncio
from pathlib import Path
import tempfile

from ..models.media_asset import AudioAnalysisProfile, AudioVibe
from ..storage.interface import StorageInterface


logger = logging.getLogger(__name__)


class AudioAnalysisTool:
    """Tool for analyzing audio content using Librosa."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
        """Initialize the audio analysis tool.
        
        Args:
            storage: Optional storage interface for accessing audio files
        """
        self.storage = storage
        
    async def analyze_audio(self, audio_path: str) -> AudioAnalysisProfile:
        """Analyze audio file and extract musical features.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            AudioAnalysisProfile with tempo, beats, energy, and vibe
        """
        try:
            # Load audio asynchronously
            y, sr = await self._load_audio(audio_path)
            
            # Get duration
            duration = len(y) / sr
            
            # Extract features in parallel
            tempo, beats = await self._extract_rhythm(y, sr)
            energy_curve = await self._extract_energy(y, sr)
            vibe = await self._analyze_vibe(y, sr)
            
            # Create profile
            return AudioAnalysisProfile(
                file_path=audio_path,
                beat_timestamps=beats.tolist(),
                tempo_bpm=tempo,
                energy_curve=energy_curve.tolist(),
                duration=duration,
                vibe=vibe,
                sections=[]  # Could be implemented later with segment analysis
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze audio {audio_path}: {e}")
            raise
    
    async def _load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file asynchronously."""
        loop = asyncio.get_event_loop()
        
        if self.storage and not Path(audio_path).exists():
            # Download from storage first
            audio_io = await self.storage.download(audio_path)
            # Save to temp file for librosa
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp.write(audio_io.read())
                tmp_path = tmp.name
            
            y, sr = await loop.run_in_executor(None, librosa.load, tmp_path)
            Path(tmp_path).unlink()  # Clean up
            return y, sr
        else:
            # Load from filesystem
            return await loop.run_in_executor(None, librosa.load, audio_path)
    
    async def _extract_rhythm(self, y: np.ndarray, sr: int) -> Tuple[float, np.ndarray]:
        """Extract tempo and beat positions."""
        loop = asyncio.get_event_loop()
        
        def extract():
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beats, sr=sr)
            return float(tempo), beat_times
        
        return await loop.run_in_executor(None, extract)
    
    async def _extract_energy(self, y: np.ndarray, sr: int, hop_length: int = 512) -> np.ndarray:
        """Extract energy envelope of the audio."""
        loop = asyncio.get_event_loop()
        
        def extract():
            # Use RMS energy
            rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
            
            # Smooth the energy curve
            from scipy.ndimage import gaussian_filter1d
            smoothed = gaussian_filter1d(rms, sigma=2)
            
            # Normalize to 0-1
            if smoothed.max() > 0:
                smoothed = smoothed / smoothed.max()
            
            # Resample to ~10 values per second for storage efficiency
            target_rate = 10  # Hz
            current_rate = sr / hop_length
            resample_factor = target_rate / current_rate
            
            from scipy.signal import resample
            target_length = int(len(smoothed) * resample_factor)
            if target_length < 1:
                target_length = 1
            
            if len(smoothed) > 1 and target_length > 1:
                resampled = resample(smoothed, target_length)
            else:
                # If array is too small, just use the original
                resampled = smoothed
            
            # Ensure all values are in 0-1 range
            resampled = np.clip(resampled, 0, 1)
            
            return resampled
        
        return await loop.run_in_executor(None, extract)
    
    async def _extract_onsets(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Detect onset times (when new sounds begin)."""
        loop = asyncio.get_event_loop()
        
        def extract():
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            return onset_times
        
        return await loop.run_in_executor(None, extract)
    
    async def _analyze_vibe(self, y: np.ndarray, sr: int) -> AudioVibe:
        """Analyze the overall vibe/mood of the audio."""
        loop = asyncio.get_event_loop()
        
        def analyze():
            # Extract various features
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
            
            # Calculate energy
            energy_rms = np.mean(librosa.feature.rms(y=y)[0])
            # Normalize energy to 0-1
            energy = min(1.0, energy_rms * 10)  # Scale appropriately
            
            # Calculate brightness (related to valence)
            brightness = np.mean(spectral_centroid) / sr  # Normalized
            valence = min(1.0, brightness * 3)  # Scale to 0-1
            
            # Calculate arousal based on spectral flux and tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            arousal = min(1.0, (tempo - 60) / 140)  # Normalize tempo to arousal
            
            # Calculate danceability based on rhythm strength and tempo
            onset_strength = librosa.onset.onset_strength(y=y, sr=sr)
            rhythm_strength = np.std(onset_strength)
            danceability = min(1.0, rhythm_strength * 2 * (0.5 + arousal * 0.5))
            
            # Determine mood based on valence and arousal
            if valence > 0.7 and arousal > 0.7:
                mood = "energetic-happy"
            elif valence > 0.7 and arousal < 0.3:
                mood = "calm-positive"
            elif valence < 0.3 and arousal > 0.7:
                mood = "intense-dark"
            elif valence < 0.3 and arousal < 0.3:
                mood = "melancholic"
            else:
                mood = "balanced"
            
            # Genre detection based on tempo and spectral features
            if tempo < 80:
                genre = "ambient"
            elif tempo < 120 and valence < 0.5:
                genre = "classical"
            elif tempo > 120 and danceability > 0.7:
                genre = "dance/electronic"
            elif rhythm_strength > 0.8:
                genre = "rhythmic"
            else:
                genre = "general"
            
            return AudioVibe(
                danceability=danceability,
                energy=energy,
                valence=valence,
                arousal=arousal,
                mood=mood,
                genre=genre
            )
        
        return await loop.run_in_executor(None, analyze)


# ADK Tool wrapper
from google.adk.tools import FunctionTool

async def analyze_audio_media(file_path: str, storage: Optional[StorageInterface] = None) -> Dict[str, Any]:
    """Analyze audio file for rhythm, energy, and mood.
    
    Args:
        file_path: Path to audio file
        storage: Optional storage interface
        
    Returns:
        Dictionary with analysis results
    """
    try:
        analyzer = AudioAnalysisTool(storage)
        profile = await analyzer.analyze_audio(file_path)
        
        return {
            "status": "success",
            "analysis": profile.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# Create the ADK tool
audio_analysis_tool = FunctionTool(func=analyze_audio_media)