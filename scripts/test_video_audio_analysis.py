#!/usr/bin/env python3
"""Test script for enhanced video audio analysis."""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory_movie_maker.tools.visual_analysis import analyze_visual_media
from src.memory_movie_maker.config import settings


async def test_video_audio_analysis(video_path: str):
    """Test analyzing a video with audio content."""
    print(f"\n🎬 Testing video audio analysis on: {video_path}")
    print("=" * 60)
    
    # Check if file exists
    if not Path(video_path).exists():
        print(f"❌ Error: File not found: {video_path}")
        return
    
    # Analyze the video
    print("🔍 Analyzing video (this includes audio analysis)...")
    result = await analyze_visual_media(video_path)
    
    if result["status"] == "error":
        print(f"❌ Error: {result['error']}")
        return
    
    analysis = result["analysis"]
    
    # Display basic info
    print(f"\n📝 Description: {analysis['description']}")
    print(f"🎨 Aesthetic Score: {analysis['aesthetic_score']:.2f}")
    print(f"🏷️  Tags: {', '.join(analysis['tags'])}")
    
    # Display unified video segments with audio
    if analysis.get('notable_segments'):
        print(f"\n📹 Video Segments ({len(analysis['notable_segments'])}):")
        for i, seg in enumerate(analysis['notable_segments']):
            print(f"\n  Segment {i+1}: [{seg['start_time']:.1f}s - {seg['end_time']:.1f}s]")
            print(f"    📝 Description: {seg['description']}")
            
            # Visual content
            if seg.get('visual_content'):
                print(f"    👁️  Visual: {seg['visual_content']}")
            
            # Audio content
            if seg.get('audio_content'):
                print(f"    🔊 Audio: {seg['audio_content']}")
            
            # Audio type
            if seg.get('audio_type'):
                print(f"    🎵 Type: {seg['audio_type']}")
            
            # Speech content
            if seg.get('speech_content'):
                speaker = seg.get('speaker', 'unknown')
                print(f"    💬 Speech: \"{seg['speech_content']}\" ({speaker})")
            
            # Music description
            if seg.get('music_description'):
                print(f"    🎼 Music: {seg['music_description']}")
            
            # Emotional tone
            if seg.get('emotional_tone'):
                print(f"    😊 Tone: {seg['emotional_tone']}")
            
            # Importance and sync
            print(f"    ⭐ Importance: {seg['importance']:.2f}")
            if seg.get('sync_priority'):
                print(f"    🔄 Sync Priority: {seg['sync_priority']:.2f}")
            
            # Recommended action
            if seg.get('recommended_action'):
                print(f"    ✂️  Action: {seg['recommended_action']}")
            
            # Tags
            if seg.get('tags'):
                print(f"    🏷️  Tags: {', '.join(seg['tags'])}")
    
    # Display audio summary
    if analysis.get('audio_summary'):
        audio = analysis['audio_summary']
        print(f"\n🎵 Audio Summary:")
        print(f"  Has Speech: {audio.get('has_speech', False)}")
        print(f"  Has Music: {audio.get('has_music', False)}")
        if audio.get('dominant_audio'):
            print(f"  Dominant Audio: {audio['dominant_audio']}")
        print(f"  Audio Quality: {audio.get('audio_quality', 'unknown')}")
        if audio.get('overall_audio_mood'):
            print(f"  Overall Mood: {audio['overall_audio_mood']}")
        if audio.get('key_audio_moments'):
            print(f"  Key Moments: {', '.join(audio['key_audio_moments'])}")
    
    # Scene changes
    if analysis.get('scene_changes'):
        print(f"\n🎬 Scene Changes: {', '.join(f'{t:.1f}s' for t in analysis['scene_changes'])}")
    
    # Save full analysis
    output_file = Path(video_path).stem + "_audio_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"\n💾 Full analysis saved to: {output_file}")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_video_audio_analysis.py <video_path>")
        print("\nExample:")
        print("  python test_video_audio_analysis.py data/test_inputs/test_video.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    # Check API key
    if not settings.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not set in environment")
        sys.exit(1)
    
    await test_video_audio_analysis(video_path)


if __name__ == "__main__":
    asyncio.run(main())