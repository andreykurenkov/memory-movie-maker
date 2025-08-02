#!/usr/bin/env python3
"""Test script to verify audio analysis works with real audio files."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_movie_maker.tools.audio_analysis import AudioAnalysisTool


async def test_real_audio():
    """Test analyzing real audio files from test_inputs."""
    
    print("🎵 Memory Movie Maker - Audio Analysis Test")
    print("=" * 60)
    
    # Find test audio files
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    audio_files = list(test_dir.glob("*.mp3")) + list(test_dir.glob("*.wav")) + list(test_dir.glob("*.m4a"))
    
    if not audio_files:
        print(f"❌ No audio files found in {test_dir}")
        return
    
    print(f"✅ Found {len(audio_files)} audio file(s)")
    print("-" * 60)
    
    # Create audio analysis tool
    tool = AudioAnalysisTool()
    
    for audio_path in audio_files:
        print(f"\n📁 Analyzing: {audio_path.name}")
        print(f"   Size: {audio_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        try:
            # Analyze the audio
            print("   ⏳ Analyzing audio features...")
            result = await tool.analyze_audio(str(audio_path))
            
            print("\n   ✅ Analysis complete!")
            print(f"\n   📊 Basic Info:")
            print(f"      Duration: {result.duration:.1f} seconds")
            print(f"      Tempo: {result.tempo_bpm:.1f} BPM")
            print(f"      Total Beats: {len(result.beat_timestamps)}")
            
            print(f"\n   🎵 Musical Characteristics:")
            print(f"      Danceability: {result.vibe.danceability:.2%}")
            print(f"      Energy: {result.vibe.energy:.2%}")
            print(f"      Valence (positivity): {result.vibe.valence:.2%}")
            print(f"      Arousal (intensity): {result.vibe.arousal:.2%}")
            print(f"      Mood: {result.vibe.mood}")
            print(f"      Genre: {result.vibe.genre}")
            
            print(f"\n   📈 Energy Analysis:")
            print(f"      Energy samples: {len(result.energy_curve)}")
            if result.energy_curve:
                print(f"      Min energy: {min(result.energy_curve):.2f}")
                print(f"      Max energy: {max(result.energy_curve):.2f}")
                print(f"      Avg energy: {sum(result.energy_curve)/len(result.energy_curve):.2f}")
            
            # Show beat pattern
            if result.beat_timestamps:
                print(f"\n   🥁 Beat Pattern:")
                print(f"      First 10 beats at: {[f'{b:.2f}s' for b in result.beat_timestamps[:10]]}")
                if len(result.beat_timestamps) > 10:
                    print(f"      ... and {len(result.beat_timestamps) - 10} more beats")
            
            # Show energy peaks (for potential video cut points)
            if result.energy_curve:
                print(f"\n   ⚡ Energy Peaks (potential cut points):")
                # Find peaks in energy curve
                energy_threshold = 0.7
                peak_times = []
                for i, energy in enumerate(result.energy_curve):
                    if energy > energy_threshold:
                        time = i * result.duration / len(result.energy_curve)
                        peak_times.append(time)
                
                if peak_times:
                    # Group nearby peaks
                    grouped_peaks = []
                    last_peak = -5
                    for peak in peak_times:
                        if peak - last_peak > 2:  # At least 2 seconds apart
                            grouped_peaks.append(peak)
                            last_peak = peak
                    
                    print(f"      Found {len(grouped_peaks)} energy peaks:")
                    for i, peak in enumerate(grouped_peaks[:5], 1):
                        print(f"      {i}. {peak:.1f}s")
                    if len(grouped_peaks) > 5:
                        print(f"      ... and {len(grouped_peaks) - 5} more")
                else:
                    print("      No significant energy peaks found")
            
            # Key and time signature if available
            if result.key:
                print(f"\n   🎼 Music Theory:")
                print(f"      Key: {result.key}")
            if result.time_signature:
                print(f"      Time Signature: {result.time_signature}")
            
        except Exception as e:
            print(f"\n   ❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)


async def test_adk_tool():
    """Test the ADK tool wrapper."""
    print("\n🔧 Testing ADK Tool Wrapper")
    print("-" * 40)
    
    from memory_movie_maker.tools.audio_analysis import analyze_audio_media
    
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    audio_files = list(test_dir.glob("*.mp3"))
    
    if audio_files:
        audio_path = str(audio_files[0])
        print(f"Testing with: {Path(audio_path).name}")
        
        result = await analyze_audio_media(audio_path)
        
        if result["status"] == "success":
            print("✅ ADK tool wrapper works correctly")
            print(f"   Analysis keys: {list(result['analysis'].keys())}")
        else:
            print(f"❌ ADK tool wrapper failed: {result.get('error')}")
    else:
        print("No audio files to test ADK wrapper")


if __name__ == "__main__":
    asyncio.run(test_real_audio())
    asyncio.run(test_adk_tool())