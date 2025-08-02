#!/usr/bin/env python3
"""Test script to verify audio analysis works."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_movie_maker.tools.audio_analysis import AudioAnalysisTool


async def test_audio_analysis():
    """Test analyzing sample audio."""
    
    print("🎵 Testing Audio Analysis")
    print("-" * 40)
    
    # Use librosa example
    import librosa
    example_file = librosa.example('trumpet')
    
    print(f"📁 Using example: {Path(example_file).name}")
    
    tool = AudioAnalysisTool()
    
    try:
        result = await tool.analyze_audio(example_file)
        
        print(f"\n✅ Analysis complete!")
        print(f"   Duration: {result.duration:.1f} seconds")
        print(f"   Tempo: {result.tempo_bpm:.1f} BPM")
        print(f"   Beats: {len(result.beat_timestamps)} detected")
        print(f"   Energy: {len(result.energy_curve)} samples")
        print(f"\n   Vibe:")
        print(f"   - Danceability: {result.vibe.danceability:.2f}")
        print(f"   - Energy: {result.vibe.energy:.2f}")
        print(f"   - Valence: {result.vibe.valence:.2f}")
        print(f"   - Arousal: {result.vibe.arousal:.2f}")
        print(f"   - Mood: {result.vibe.mood}")
        print(f"   - Genre: {result.vibe.genre}")
        
        # Show beat pattern
        if result.beat_timestamps:
            print(f"\n   First 5 beats at: {[f'{b:.2f}s' for b in result.beat_timestamps[:5]]}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()


async def test_with_test_audio():
    """Test with audio files from test_inputs if available."""
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    audio_files = list(test_dir.glob("*.mp3")) + list(test_dir.glob("*.wav")) + list(test_dir.glob("*.m4a"))
    
    if audio_files:
        print(f"\n\n{'='*40}")
        print(f"📂 Found {len(audio_files)} audio files in test_inputs")
        
        tool = AudioAnalysisTool()
        
        for audio_path in audio_files[:2]:  # Test first 2 files
            print(f"\n🎵 Analyzing: {audio_path.name}")
            print(f"   Size: {audio_path.stat().st_size / 1024 / 1024:.1f} MB")
            
            try:
                result = await tool.analyze_audio(str(audio_path))
                print(f"   ✅ Success!")
                print(f"   - Tempo: {result.tempo_bpm:.1f} BPM")
                print(f"   - Vibe: {result.vibe.mood} (energy: {result.vibe.energy:.2f})")
                print(f"   - {len(result.beat_timestamps)} beats detected")
            except Exception as e:
                print(f"   ❌ Failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_audio_analysis())
    asyncio.run(test_with_test_audio())