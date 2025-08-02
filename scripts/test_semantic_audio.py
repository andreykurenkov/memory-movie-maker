#!/usr/bin/env python3
"""Test script to verify semantic audio analysis works with real audio files."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_movie_maker.tools.semantic_audio_analysis import SemanticAudioAnalysisTool


async def test_semantic_audio():
    """Test semantic analysis of audio files."""
    
    print("🎙️ Memory Movie Maker - Semantic Audio Analysis Test")
    print("=" * 60)
    
    # Find test audio files
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    audio_files = list(test_dir.glob("*.mp3")) + list(test_dir.glob("*.wav"))
    
    if not audio_files:
        print(f"❌ No audio files found in {test_dir}")
        return
    
    print(f"✅ Found {len(audio_files)} audio file(s)")
    print("-" * 60)
    
    # Create semantic audio analysis tool
    tool = SemanticAudioAnalysisTool()
    
    for audio_path in audio_files:
        print(f"\n📁 Analyzing: {audio_path.name}")
        print(f"   Size: {audio_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        try:
            # Analyze the audio
            print("   ⏳ Performing semantic analysis...")
            result = await tool.analyze_audio_semantics(str(audio_path))
            
            print("\n   ✅ Analysis complete!")
            
            # Display results
            print(f"\n   📝 Summary:")
            print(f"      {result.summary}")
            
            if result.transcript:
                print(f"\n   📜 Transcript Preview:")
                preview = result.transcript[:200] + "..." if len(result.transcript) > 200 else result.transcript
                print(f"      {preview}")
            
            print(f"\n   🎭 Emotional Tone: {result.emotional_tone}")
            
            if result.speakers:
                print(f"\n   👥 Speakers: {', '.join(result.speakers)}")
            
            if result.topics:
                print(f"\n   📌 Topics: {', '.join(result.topics)}")
            
            if result.segments:
                print(f"\n   🎬 Notable Segments ({len(result.segments)} total):")
                for i, seg in enumerate(result.segments[:5], 1):
                    print(f"      {i}. [{seg.start_time:.1f}s - {seg.end_time:.1f}s] {seg.type}")
                    print(f"         {seg.content[:100]}...")
                    if seg.speaker:
                        print(f"         Speaker: {seg.speaker}")
                    print(f"         Importance: {seg.importance:.2f}")
                if len(result.segments) > 5:
                    print(f"      ... and {len(result.segments) - 5} more segments")
            
            if result.key_moments:
                print(f"\n   ⭐ Key Moments for Video Sync:")
                for i, moment in enumerate(result.key_moments[:3], 1):
                    print(f"      {i}. {moment['timestamp']}s: {moment['description']}")
                    print(f"         Sync: {moment.get('sync_suggestion', 'No suggestion')}")
            
            if result.sound_elements:
                print(f"\n   🔊 Sound Elements:")
                for element, timestamps in result.sound_elements.items():
                    if timestamps:
                        print(f"      {element}: {len(timestamps)} occurrence(s)")
                        print(f"         First at: {timestamps[0]}s")
            
        except Exception as e:
            print(f"\n   ❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)


async def compare_analyses():
    """Compare Librosa and Gemini analyses."""
    print("\n\n📊 Comparing Audio Analysis Approaches")
    print("-" * 60)
    
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    audio_files = list(test_dir.glob("*.mp3"))
    
    if not audio_files:
        return
    
    audio_path = audio_files[0]
    
    # Run both analyses
    from memory_movie_maker.tools.audio_analysis import AudioAnalysisTool
    
    print(f"\n🎵 Librosa Analysis (Technical):")
    librosa_tool = AudioAnalysisTool()
    librosa_result = await librosa_tool.analyze_audio(str(audio_path))
    print(f"   - Tempo: {librosa_result.tempo_bpm:.1f} BPM")
    print(f"   - Beats: {len(librosa_result.beat_timestamps)}")
    print(f"   - Energy samples: {len(librosa_result.energy_curve)}")
    print(f"   - Mood: {librosa_result.vibe.mood}")
    
    print(f"\n🎙️ Gemini Analysis (Semantic):")
    semantic_tool = SemanticAudioAnalysisTool()
    try:
        semantic_result = await semantic_tool.analyze_audio_semantics(str(audio_path))
        print(f"   - Summary: {semantic_result.summary}")
        print(f"   - Emotional tone: {semantic_result.emotional_tone}")
        print(f"   - Segments: {len(semantic_result.segments)}")
        print(f"   - Has transcript: {'Yes' if semantic_result.transcript else 'No'}")
    except Exception as e:
        print(f"   - Failed: {e}")
    
    print("\n💡 Usage Recommendations:")
    print("   - Use Librosa for: Beat detection, tempo sync, energy-based cuts")
    print("   - Use Gemini for: Content understanding, speech timing, emotional arcs")
    print("   - Combine both for: Intelligent video composition with semantic awareness")


if __name__ == "__main__":
    asyncio.run(test_semantic_audio())
    asyncio.run(compare_analyses())