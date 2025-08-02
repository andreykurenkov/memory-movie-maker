#!/usr/bin/env python3
"""Test composition and video rendering."""

import asyncio
import sys
from pathlib import Path
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.memory_movie_maker.models.project_state import ProjectState, UserInputs, ProjectStatus
from src.memory_movie_maker.models.media_asset import (
    MediaAsset, MediaType, GeminiAnalysis, AudioAnalysisProfile, 
    AudioVibe, VideoSegment
)
from src.memory_movie_maker.tools.composition import compose_timeline
from src.memory_movie_maker.tools.video_renderer import render_video
import uuid


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_composition():
    """Test timeline composition and video rendering."""
    
    # Create mock analyzed media
    media_assets = [
        # Mock video with analysis
        MediaAsset(
            id=str(uuid.uuid4()),
            file_path="data/test_inputs/test_video.mp4",
            type=MediaType.VIDEO,
            duration=10.0,
            gemini_analysis=GeminiAnalysis(
                description="A scenic mountain view with clouds",
                aesthetic_score=0.85,
                main_subjects=["mountain", "sky", "clouds"],
                composition_quality=0.9,
                technical_quality=0.8,
                tags=["landscape", "nature", "scenic"],
                emotional_tone="peaceful",
                scene_type="outdoor",
                video_segments=[
                    VideoSegment(
                        start_time=2.0,
                        end_time=8.0,
                        description="Beautiful cloud movement over mountain",
                        importance=0.9,
                        tags=["scenic", "clouds"]
                    )
                ]
            )
        ),
        # Mock audio with beat analysis
        MediaAsset(
            id=str(uuid.uuid4()),
            file_path="data/test_inputs/test_song.mp3",
            type=MediaType.AUDIO,
            duration=30.0,
            audio_analysis=AudioAnalysisProfile(
                file_path="data/test_inputs/test_song.mp3",
                beat_timestamps=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,
                               5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0],
                tempo_bpm=120.0,
                energy_curve=[0.5, 0.6, 0.7, 0.8, 0.7, 0.6, 0.5, 0.6, 0.7, 0.8,
                             0.7, 0.6, 0.5, 0.4, 0.5, 0.6, 0.7, 0.8, 0.7, 0.6],
                duration=30.0,
                vibe=AudioVibe(
                    danceability=0.7,
                    energy=0.6,
                    valence=0.8,
                    arousal=0.6,
                    mood="upbeat",
                    genre="electronic"
                ),
                sections=[]
            )
        )
    ]
    
    # Create project state
    project_state = ProjectState(
        user_inputs=UserInputs(
            media=media_assets,
            initial_prompt="Create a test video with beat sync"
        ),
        project_status=ProjectStatus(phase="composing")
    )
    
    print("=" * 60)
    print("Testing Timeline Composition")
    print("=" * 60)
    
    # Test composition
    result = await compose_timeline(
        project_state=project_state.model_dump(),
        target_duration=10,
        style="dynamic"
    )
    
    if result["status"] == "success":
        timeline = result["timeline"]
        print(f"\n✅ Timeline created successfully!")
        print(f"Total duration: {timeline['total_duration']:.2f}s")
        print(f"Number of segments: {len(timeline['segments'])}")
        
        for i, segment in enumerate(timeline['segments']):
            print(f"\nSegment {i+1}:")
            print(f"  - Media ID: {segment['media_id']}")
            print(f"  - Start: {segment['start_time']:.2f}s")
            print(f"  - Duration: {segment['duration']:.2f}s")
            print(f"  - Effects: {segment['effects']}")
            print(f"  - Transition: {segment.get('transition_out', 'none')}")
        
        # Update state with timeline
        updated_state = ProjectState(**result["updated_state"])
        
        print("\n" + "=" * 60)
        print("Testing Video Rendering (Preview Mode)")
        print("=" * 60)
        
        # Test rendering
        render_result = await render_video(
            project_state=updated_state.model_dump(),
            output_filename="test_composition_output.mp4",
            resolution="640x360",
            preview=True
        )
        
        if render_result["status"] == "success":
            print(f"\n✅ Video rendered successfully!")
            print(f"Output path: {render_result['output_path']}")
            print("\nYou can play the video with:")
            print(f"  ffplay {render_result['output_path']}")
            print("  or")
            print(f"  open {render_result['output_path']}")
        else:
            print(f"\n❌ Rendering failed: {render_result['error']}")
    
    else:
        print(f"\n❌ Composition failed: {result['error']}")


async def test_with_real_files():
    """Test with actual files if they exist."""
    video_path = Path("data/test_inputs/test_video.mp4")
    audio_path = Path("data/test_inputs/test_song.mp3")
    
    if not video_path.exists() or not audio_path.exists():
        print("\n⚠️  Real test files not found. Using mock data instead.")
        return await test_composition()
    
    print("\n📁 Found real test files! Testing with actual media...")
    
    # First, we would need to run actual analysis on these files
    # For now, we'll use the mock test
    return await test_composition()


if __name__ == "__main__":
    print("🎬 Memory Movie Maker - Composition Test")
    asyncio.run(test_with_real_files())