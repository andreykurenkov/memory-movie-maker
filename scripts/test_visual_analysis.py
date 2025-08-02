#!/usr/bin/env python3
"""Test script to verify visual analysis works with real videos."""

import asyncio
import os
import sys
from pathlib import Path
from pprint import pprint

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_movie_maker.utils.logging_config import configure_logging
from memory_movie_maker.tools.visual_analysis import VisualAnalysisTool
from memory_movie_maker.config import settings

# Configure logging to suppress external libraries
configure_logging(level="INFO", suppress_external=True)


async def test_video_analysis():
    """Test analyzing real videos from test_inputs."""
    
    # Check if API is configured
    if not settings.validate_api_keys():
        print("❌ Error: No Gemini API configured!")
        print("Please set either GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT in your .env file")
        return
    
    # Find test videos
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    video_files = list(test_dir.glob("*.mp4"))
    
    if not video_files:
        print(f"❌ No video files found in {test_dir}")
        return
    
    print(f"✅ Found {len(video_files)} test videos")
    print(f"✅ Using {'Vertex AI' if settings.google_genai_use_vertexai else 'Direct Gemini API'}")
    print("-" * 60)
    
    # Create visual analysis tool
    try:
        tool = VisualAnalysisTool()
        print("✅ Visual analysis tool initialized")
    except Exception as e:
        print(f"❌ Failed to initialize tool: {e}")
        return
    
    # Analyze first video
    video_path = video_files[0]
    print(f"\n📹 Analyzing video: {video_path.name}")
    print(f"   Size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    try:
        # Analyze the video
        print("   ⏳ Sending to Gemini API (this may take 10-30 seconds)...")
        result = await tool.analyze_video(str(video_path))
        
        print("\n✅ Analysis completed!")
        print("\n📊 Results:")
        print(f"   Description: {result.description}")
        print(f"   Aesthetic Score: {result.aesthetic_score:.2f}")
        print(f"   Main Subjects: {', '.join(result.main_subjects)}")
        print(f"   Tags: {', '.join(result.tags)}")
        
        if result.notable_segments:
            print(f"\n   🎬 Notable Segments ({len(result.notable_segments)}):")
            for i, segment in enumerate(result.notable_segments, 1):
                print(f"      {i}. [{segment.start_time:.1f}s - {segment.end_time:.1f}s] {segment.description}")
                print(f"         Importance: {segment.importance:.2f}, Tags: {', '.join(segment.tags)}")
        
        if result.overall_motion:
            print(f"\n   Motion: {result.overall_motion}")
        
        if result.scene_changes:
            print(f"   Scene Changes at: {', '.join(f'{t:.1f}s' for t in result.scene_changes)}")
        
        if result.quality_issues:
            print(f"\n   ⚠️  Quality Issues: {', '.join(result.quality_issues)}")
        
        # Optionally analyze more videos
        if len(video_files) > 1:
            print(f"\n\n{'='*60}")
            response = input("Analyze another video? (y/n): ")
            if response.lower() == 'y':
                for video_path in video_files[1:]:
                    print(f"\n📹 Analyzing: {video_path.name}")
                    try:
                        result = await tool.analyze_video(str(video_path))
                        print(f"   ✅ Success! Description: {result.description[:100]}...")
                        print(f"   Found {len(result.notable_segments)} notable segments")
                    except Exception as e:
                        print(f"   ❌ Failed: {e}")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API key is valid")
        print("2. Ensure you have API quota remaining")
        print("3. Check the video file is not corrupted")
        print("4. For Vertex AI, ensure APIs are enabled in your project")


async def test_image_analysis():
    """Quick test with an image if available."""
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    image_files = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))
    
    if image_files:
        print(f"\n\n{'='*60}")
        print("📷 Bonus: Found image files, testing image analysis...")
        
        tool = VisualAnalysisTool()
        image_path = image_files[0]
        
        try:
            result = await tool.analyze_image(str(image_path))
            print(f"✅ Image analysis successful!")
            print(f"   Description: {result.description}")
            print(f"   Aesthetic Score: {result.aesthetic_score:.2f}")
        except Exception as e:
            print(f"❌ Image analysis failed: {e}")


if __name__ == "__main__":
    print("🎬 Memory Movie Maker - Visual Analysis Test")
    print("=" * 60)
    
    # Run the async test
    asyncio.run(test_video_analysis())
    
    # Optionally test image analysis
    asyncio.run(test_image_analysis())
    
    print("\n✨ Test complete!")