#!/usr/bin/env python3
"""Test the complete Memory Movie Maker workflow with RootAgent."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.memory_movie_maker.agents.root_agent import RootAgent


async def test_complete_workflow():
    """Test the complete workflow from media to final video."""
    print("🎬 Memory Movie Maker - Complete Workflow Test")
    print("=" * 60)
    
    # Check for test files
    test_video = "data/test_inputs/test_video.mp4"
    test_audio = "data/test_inputs/test_song.mp3"
    
    media_files = []
    if Path(test_video).exists():
        media_files.append(test_video)
        print(f"✓ Found test video: {test_video}")
    else:
        print(f"✗ Test video not found: {test_video}")
    
    music_path = None
    if Path(test_audio).exists():
        music_path = test_audio
        print(f"✓ Found test audio: {test_audio}")
    else:
        print(f"✗ Test audio not found: {test_audio}")
    
    if not media_files:
        print("\n❌ No test media files found!")
        print("Please add test files to data/test_inputs/")
        return
    
    # Create RootAgent
    print("\n📊 Initializing RootAgent...")
    root_agent = RootAgent()
    
    # Test 1: Create video with auto-refinement
    print("\n" + "=" * 60)
    print("TEST 1: Create video with auto-refinement")
    print("=" * 60)
    
    result = await root_agent.create_memory_movie(
        media_paths=media_files,
        user_prompt="Create a dynamic test video showcasing the media with smooth transitions",
        music_path=music_path,
        target_duration=10,
        style="dynamic",
        auto_refine=True
    )
    
    if result["status"] == "success":
        print(f"\n✅ Video created successfully!")
        print(f"   - Output: {result['video_path']}")
        print(f"   - Refinements: {result['refinement_iterations']}")
        print(f"   - Final score: {result.get('final_score', 'N/A')}")
        
        project_state = result["project_state"]
        
        # Show evaluation details if available
        if project_state.evaluation_results:
            print("\n📋 Evaluation Details:")
            eval_results = project_state.evaluation_results
            print(f"   - Overall score: {eval_results.get('overall_score', 'N/A')}/10")
            
            if eval_results.get('strengths'):
                print("   - Strengths:")
                for strength in eval_results['strengths'][:2]:
                    print(f"     • {strength}")
            
            if eval_results.get('weaknesses'):
                print("   - Areas for improvement:")
                for weakness in eval_results['weaknesses'][:2]:
                    print(f"     • {weakness}")
        
        # Test 2: Process user feedback
        print("\n" + "=" * 60)
        print("TEST 2: Process user feedback")
        print("=" * 60)
        
        feedback = "Make the video 15 seconds long with smoother transitions"
        print(f"User feedback: '{feedback}'")
        
        feedback_result = await root_agent.process_user_feedback(
            project_state=project_state,
            user_feedback=feedback
        )
        
        if feedback_result["status"] == "success":
            print(f"✅ Feedback applied successfully!")
            print(f"   - New video: {feedback_result['video_path']}")
        else:
            print(f"❌ Feedback processing failed: {feedback_result.get('error')}")
    
    else:
        print(f"\n❌ Video creation failed: {result.get('error')}")
    
    # Test 3: Create video without auto-refinement
    print("\n" + "=" * 60)
    print("TEST 3: Create video without auto-refinement (fast mode)")
    print("=" * 60)
    
    fast_result = await root_agent.create_memory_movie(
        media_paths=media_files,
        user_prompt="Quick test video",
        music_path=music_path,
        target_duration=5,
        style="smooth",
        auto_refine=False
    )
    
    if fast_result["status"] == "success":
        print(f"✅ Fast video created: {fast_result['video_path']}")
        print(f"   - Message: {fast_result.get('message', '')}")
    else:
        print(f"❌ Fast video creation failed: {fast_result.get('error')}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


async def test_workflow_phases():
    """Test individual workflow phases."""
    print("\n🔍 Testing Individual Workflow Phases")
    print("=" * 60)
    
    # This would test each phase separately
    # Useful for debugging specific issues
    pass


if __name__ == "__main__":
    print("🚀 Starting Memory Movie Maker Tests\n")
    
    try:
        asyncio.run(test_complete_workflow())
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()