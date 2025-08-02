#!/usr/bin/env python3
"""Test script to verify AnalysisAgent works with real media files."""

import asyncio
import sys
from pathlib import Path
import uuid
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_movie_maker.agents.analysis_agent import AnalysisAgent
from memory_movie_maker.models.project_state import ProjectState, UserInputs, ProjectStatus
from memory_movie_maker.models.media_asset import MediaAsset, MediaType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


async def test_analysis_agent():
    """Test the AnalysisAgent with real media files."""
    
    print("🎬 Memory Movie Maker - AnalysisAgent Test")
    print("=" * 60)
    
    # Find test media files
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    
    # Collect different types of media
    test_media = []
    
    # Add video files
    for video_file in test_dir.glob("*.mp4"):
        test_media.append(MediaAsset(
            id=str(uuid.uuid4()),
            file_path=str(video_file),
            type=MediaType.VIDEO
        ))
        print(f"✅ Found video: {video_file.name}")
    
    # Add audio files
    for audio_file in list(test_dir.glob("*.mp3")) + list(test_dir.glob("*.wav")):
        test_media.append(MediaAsset(
            id=str(uuid.uuid4()),
            file_path=str(audio_file),
            type=MediaType.AUDIO
        ))
        print(f"✅ Found audio: {audio_file.name}")
    
    # Add image files
    for image_file in list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png")):
        test_media.append(MediaAsset(
            id=str(uuid.uuid4()),
            file_path=str(image_file),
            type=MediaType.IMAGE
        ))
        print(f"✅ Found image: {image_file.name}")
    
    if not test_media:
        print(f"❌ No media files found in {test_dir}")
        return
    
    print(f"\n📊 Total media files: {len(test_media)}")
    print("-" * 60)
    
    # Create project state
    project_state = ProjectState(
        user_inputs=UserInputs(
            media=test_media,
            initial_prompt="Create a memory movie from these files"
        ),
        project_status=ProjectStatus(phase="analyzing")
    )
    
    # Create and run AnalysisAgent
    print("\n🤖 Initializing AnalysisAgent...")
    agent = AnalysisAgent()
    
    print("⏳ Starting analysis (this may take a while)...")
    print("-" * 60)
    
    try:
        # Run the analysis
        updated_state = await agent.analyze_project(project_state)
        
        print("\n✅ Analysis complete!")
        print("=" * 60)
        
        # Display results for each media file
        for media in updated_state.user_inputs.media:
            print(f"\n📁 File: {Path(media.file_path).name}")
            print(f"   Type: {media.type}")
            
            # Visual analysis results
            if media.gemini_analysis:
                print(f"\n   👁️ Visual Analysis:")
                print(f"      Description: {media.gemini_analysis.description}")
                print(f"      Aesthetic Score: {media.gemini_analysis.aesthetic_score:.2f}")
                if media.gemini_analysis.main_subjects:
                    print(f"      Subjects: {', '.join(media.gemini_analysis.main_subjects)}")
                if media.gemini_analysis.tags:
                    print(f"      Tags: {', '.join(media.gemini_analysis.tags[:5])}")
                if media.gemini_analysis.notable_segments:
                    print(f"      Notable Segments: {len(media.gemini_analysis.notable_segments)}")
                    for seg in media.gemini_analysis.notable_segments[:2]:
                        print(f"        - [{seg.start_time:.1f}s-{seg.end_time:.1f}s]: {seg.description}")
            
            # Technical audio analysis results
            if media.audio_analysis:
                print(f"\n   🎵 Audio Analysis (Technical):")
                print(f"      Duration: {media.audio_analysis.duration:.1f}s")
                print(f"      Tempo: {media.audio_analysis.tempo_bpm:.1f} BPM")
                print(f"      Beats: {len(media.audio_analysis.beat_timestamps)}")
                print(f"      Energy Samples: {len(media.audio_analysis.energy_curve)}")
                print(f"      Mood: {media.audio_analysis.vibe.mood}")
                print(f"      Danceability: {media.audio_analysis.vibe.danceability:.2%}")
            
            # Semantic audio analysis results
            if media.semantic_audio_analysis:
                print(f"\n   🎙️ Audio Analysis (Semantic):")
                analysis = media.semantic_audio_analysis
                print(f"      Summary: {analysis.get('summary', 'N/A')}")
                print(f"      Emotional Tone: {analysis.get('emotional_tone', 'N/A')}")
                if analysis.get('speakers'):
                    print(f"      Speakers: {', '.join(analysis['speakers'])}")
                if analysis.get('topics'):
                    print(f"      Topics: {', '.join(analysis['topics'])}")
                if analysis.get('segments'):
                    print(f"      Segments: {len(analysis['segments'])}")
            
            print("-" * 60)
        
        # Summary statistics
        print(f"\n📈 Analysis Summary:")
        print(f"   Project Phase: {updated_state.project_status.phase}")
        
        visual_count = sum(1 for m in updated_state.user_inputs.media if m.gemini_analysis)
        audio_tech_count = sum(1 for m in updated_state.user_inputs.media if m.audio_analysis)
        audio_sem_count = sum(1 for m in updated_state.user_inputs.media if m.semantic_audio_analysis)
        
        print(f"   Visual Analyses: {visual_count}")
        print(f"   Audio Technical Analyses: {audio_tech_count}")
        print(f"   Audio Semantic Analyses: {audio_sem_count}")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()


async def test_caching():
    """Test that caching works correctly."""
    print("\n\n🔄 Testing Analysis Caching")
    print("=" * 60)
    
    test_dir = Path(__file__).parent.parent / "data" / "test_inputs"
    audio_files = list(test_dir.glob("*.mp3"))
    
    if not audio_files:
        print("No audio files to test caching")
        return
    
    # Create a single media asset
    test_media = [MediaAsset(
        id=str(uuid.uuid4()),
        file_path=str(audio_files[0]),
        type=MediaType.AUDIO
    )]
    
    project_state = ProjectState(
        user_inputs=UserInputs(media=test_media, initial_prompt="Test"),
        project_status=ProjectStatus(phase="analyzing"),
        analysis_cache_enabled=True
    )
    
    agent = AnalysisAgent()
    
    # First run
    print("⏳ First analysis run...")
    start_time = asyncio.get_event_loop().time()
    updated_state = await agent.analyze_project(project_state)
    first_duration = asyncio.get_event_loop().time() - start_time
    print(f"✅ First run took: {first_duration:.2f}s")
    
    # Second run (should use cache)
    print("\n⏳ Second analysis run (should use cache)...")
    start_time = asyncio.get_event_loop().time()
    updated_state = await agent.analyze_project(updated_state)
    second_duration = asyncio.get_event_loop().time() - start_time
    print(f"✅ Second run took: {second_duration:.2f}s")
    
    if second_duration < first_duration * 0.1:
        print("✅ Caching is working correctly!")
    else:
        print("⚠️ Caching might not be working as expected")


if __name__ == "__main__":
    asyncio.run(test_analysis_agent())
    asyncio.run(test_caching())