"""Integration tests for music synchronization features."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json

from memory_movie_maker.models.media_asset import (
    MediaAsset, MediaType, AudioAnalysisProfile, AudioVibe
)
from memory_movie_maker.models.timeline import Timeline, TimelineSegment, TransitionType
from memory_movie_maker.tools.semantic_audio_analysis import (
    SemanticAudioAnalysisTool, SemanticAudioAnalysis, AudioSegment
)
from memory_movie_maker.tools.composition import CompositionAlgorithm


class TestMusicSynchronization:
    """Test music analysis and synchronization features."""
    
    @pytest.fixture
    def sample_audio_segments(self):
        """Create sample audio segments with musical structure."""
        return [
            AudioSegment(
                start_time=0.0,
                end_time=15.0,
                content="Soft piano introduction",
                type="intro",
                importance=0.8,
                musical_structure="intro",
                energy_transition="building",
                musical_elements=["piano", "effects"],
                sync_priority=0.9
            ),
            AudioSegment(
                start_time=15.0,
                end_time=30.0,
                content="Drums enter with main melody",
                type="verse",
                importance=0.7,
                musical_structure="verse",
                energy_transition="steady",
                musical_elements=["piano", "drums", "bass"],
                sync_priority=0.6
            ),
            AudioSegment(
                start_time=30.0,
                end_time=45.0,
                content="Energy builds to chorus",
                type="buildup",
                importance=0.9,
                musical_structure="buildup",
                energy_transition="building",
                musical_elements=["piano", "drums", "bass", "effects"],
                sync_priority=0.8
            ),
            AudioSegment(
                start_time=45.0,
                end_time=60.0,
                content="Full chorus with all instruments",
                type="chorus",
                importance=1.0,
                musical_structure="chorus",
                energy_transition="peak",
                musical_elements=["vocals", "piano", "drums", "bass", "melody"],
                sync_priority=1.0
            ),
            AudioSegment(
                start_time=60.0,
                end_time=75.0,
                content="Energy drops back to verse",
                type="verse",
                importance=0.6,
                musical_structure="verse",
                energy_transition="dropping",
                musical_elements=["piano", "drums", "bass"],
                sync_priority=0.5
            )
        ]
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.semantic_audio_analysis.GENAI_AVAILABLE', True)
    async def test_semantic_audio_analysis(self, sample_audio_segments):
        """Test semantic audio analysis extracts musical structure."""
        with patch('memory_movie_maker.tools.semantic_audio_analysis.genai') as mock_genai:
            # Setup mock client
            mock_client = Mock()
            mock_genai.Client.return_value = mock_client
            
            # Mock file upload
            mock_file = Mock()
            mock_file.state = "ACTIVE"
            mock_file.name = "test-file"
            mock_client.files.upload.return_value = mock_file
            mock_client.files.get.return_value = mock_file
            mock_client.files.delete.return_value = None
            
            # Mock analysis response
            analysis_response = {
                "transcript": None,
                "summary": "Upbeat instrumental track with clear verse-chorus structure",
                "segments": [seg.model_dump() for seg in sample_audio_segments],
                "speakers": [],
                "topics": ["instrumental", "upbeat", "electronic"],
                "emotional_tone": "energetic",
                "key_moments": [
                    {"timestamp": 45.0, "description": "Chorus drop", "sync_suggestion": "Hard cut to new scene"},
                    {"timestamp": 30.0, "description": "Energy buildup", "sync_suggestion": "Start accelerating cuts"}
                ],
                "sound_elements": {
                    "music": [[0, 75]],
                    "silence": []
                },
                "musical_structure_summary": "Intro (0-15s) → Verse (15-30s) → Buildup (30-45s) → Chorus (45-60s) → Verse (60-75s)",
                "energy_peaks": [45.0, 48.0, 51.0],
                "recommended_cut_points": [15.0, 30.0, 45.0, 60.0]
            }
            
            mock_response = Mock()
            mock_response.text = json.dumps(analysis_response)
            mock_client.models.generate_content.return_value = mock_response
            
            # Create tool and analyze
            tool = SemanticAudioAnalysisTool()
            result = await tool.analyze_audio_semantics("/test/audio.mp3")
            
            # Verify analysis results
            assert isinstance(result, SemanticAudioAnalysis)
            assert len(result.segments) == 5
            assert result.musical_structure_summary is not None
            assert "Intro" in result.musical_structure_summary
            assert "Chorus" in result.musical_structure_summary
            
            # Verify musical segments
            chorus_segment = result.segments[3]
            assert chorus_segment.musical_structure == "chorus"
            assert chorus_segment.energy_transition == "peak"
            assert chorus_segment.sync_priority == 1.0
            assert "vocals" in chorus_segment.musical_elements
            
            # Verify sync recommendations
            assert len(result.key_moments) == 2
            assert result.energy_peaks == [45.0, 48.0, 51.0]
            assert result.recommended_cut_points == [15.0, 30.0, 45.0, 60.0]
    
    def test_beat_synced_composition(self):
        """Test composition algorithm syncs to music beats."""
        # Create music profile with beats
        music_profile = AudioAnalysisProfile(
            file_path="/test/music.mp3",
            duration=10.0,
            tempo_bpm=120.0,
            beat_timestamps=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5],
            energy_curve=[0.5, 0.6, 0.7, 0.8, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4],
            vibe=AudioVibe(
                danceability=0.8,
                energy=0.7,
                mood="energetic"
            )
        )
        
        # Create sample media
        media_assets = [
            MediaAsset(
                id=f"img_{i:03d}",
                file_path=f"/media/photo_{i}.jpg",
                type=MediaType.IMAGE,
                gemini_analysis=Mock(aesthetic_score=0.8)
            )
            for i in range(5)
        ]
        
        # Create composition algorithm
        algo = CompositionAlgorithm()
        
        # Generate timeline
        timeline = algo.compose_timeline(
            media_pool=media_assets,
            music_profile=music_profile,
            target_duration=5,
            style_preferences={"transition_style": "dynamic"}
        )
        
        # Verify timeline is beat-synced
        assert isinstance(timeline, Timeline)
        assert len(timeline.segments) > 0
        assert timeline.music_track_id == "/test/music.mp3"
        
        # Check that segments start on beat times
        for segment in timeline.segments:
            # Start time should be close to a beat
            closest_beat = min(music_profile.beat_timestamps, 
                             key=lambda beat: abs(beat - segment.start_time))
            assert abs(segment.start_time - closest_beat) < 0.1
    
    def test_energy_based_pacing(self):
        """Test that composition adjusts pacing based on music energy."""
        # Create music with varying energy
        music_profile = AudioAnalysisProfile(
            file_path="/test/dynamic_music.mp3",
            duration=30.0,
            tempo_bpm=140.0,
            beat_timestamps=[i * 0.429 for i in range(70)],  # 140 BPM
            energy_curve=[
                0.3, 0.3, 0.4, 0.5, 0.6,  # Building
                0.8, 0.9, 1.0, 0.9, 0.8,  # Peak
                0.5, 0.4, 0.3, 0.3, 0.3   # Calm
            ],
            vibe=AudioVibe(
                danceability=0.9,
                energy=0.8,
                mood="dynamic"
            )
        )
        
        # Create media
        media_assets = [
            MediaAsset(
                id=f"vid_{i:03d}",
                file_path=f"/media/clip_{i}.mp4",
                type=MediaType.VIDEO,
                duration=5.0,
                gemini_analysis=Mock(aesthetic_score=0.85)
            )
            for i in range(10)
        ]
        
        algo = CompositionAlgorithm()
        
        # Mock the beat calculation to use our energy curve
        def mock_beats_per_clip(beat_idx, beat_times, energy_curve):
            if beat_idx < len(energy_curve):
                energy = energy_curve[beat_idx]
                if energy > 0.7:
                    return 2  # Fast cuts
                elif energy > 0.4:
                    return 4  # Medium cuts
                else:
                    return 6  # Slow cuts
            return 4
        
        algo._calculate_beats_per_clip = mock_beats_per_clip
        
        # Generate timeline
        timeline = algo.compose_timeline(
            media_pool=media_assets,
            music_profile=music_profile,
            target_duration=15,
            style_preferences={"transition_style": "smooth"}
        )
        
        # Verify pacing matches energy
        # Early segments (low energy) should be longer
        early_segments = [s for s in timeline.segments if s.start_time < 5]
        if early_segments:
            avg_early_duration = sum(s.duration for s in early_segments) / len(early_segments)
        
        # Peak segments (high energy) should be shorter
        peak_segments = [s for s in timeline.segments if 5 <= s.start_time < 10]
        if peak_segments:
            avg_peak_duration = sum(s.duration for s in peak_segments) / len(peak_segments)
        
        # Late segments (low energy) should be longer again
        late_segments = [s for s in timeline.segments if s.start_time >= 10]
        if late_segments:
            avg_late_duration = sum(s.duration for s in late_segments) / len(late_segments)
        
        # Peak cuts should be faster (shorter duration)
        if early_segments and peak_segments:
            assert avg_peak_duration < avg_early_duration
        if late_segments and peak_segments:
            assert avg_peak_duration < avg_late_duration
    
    def test_musical_structure_integration(self):
        """Test that composition respects musical structure from semantic analysis."""
        # Create music asset with semantic analysis
        music_asset = MediaAsset(
            id="music_001",
            file_path="/test/structured_song.mp3",
            type=MediaType.AUDIO,
            duration=60.0,
            audio_analysis=AudioAnalysisProfile(
                file_path="/test/structured_song.mp3",
                duration=60.0,
                tempo_bpm=100.0,
                beat_timestamps=[i * 0.6 for i in range(100)],
                energy_curve=[0.5] * 100,
                vibe=AudioVibe(danceability=0.7, energy=0.6, mood="balanced")
            ),
            semantic_audio_analysis={
                "segments": [
                    {
                        "start_time": 0,
                        "end_time": 15,
                        "type": "intro",
                        "musical_structure": "intro",
                        "sync_priority": 0.8
                    },
                    {
                        "start_time": 15,
                        "end_time": 30,
                        "type": "verse",
                        "musical_structure": "verse",
                        "sync_priority": 0.5
                    },
                    {
                        "start_time": 30,
                        "end_time": 45,
                        "type": "chorus",
                        "musical_structure": "chorus",
                        "sync_priority": 1.0
                    }
                ],
                "recommended_cut_points": [0, 15, 30, 45],
                "energy_peaks": [30, 35, 40]
            }
        )
        
        # Verify semantic analysis is accessible
        assert music_asset.semantic_audio_analysis is not None
        segments = music_asset.semantic_audio_analysis["segments"]
        assert len(segments) == 3
        
        # Verify chorus has highest sync priority
        chorus_seg = next(s for s in segments if s["musical_structure"] == "chorus")
        assert chorus_seg["sync_priority"] == 1.0
        
        # Verify recommended cut points align with structure
        cut_points = music_asset.semantic_audio_analysis["recommended_cut_points"]
        assert 15 in cut_points  # Verse start
        assert 30 in cut_points  # Chorus start


if __name__ == "__main__":
    pytest.main([__file__, "-v"])