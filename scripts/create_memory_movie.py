#!/usr/bin/env python3
"""Command-line interface for creating memory movies."""

import argparse
import asyncio
import sys
import os
from pathlib import Path
from typing import List

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.memory_movie_maker.agents.root_agent import RootAgent


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create memory movies from your media files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with auto-detected music
  %(prog)s photo1.jpg photo2.jpg video1.mp4 -p "Create a family vacation video"
  
  # Specify music and duration
  %(prog)s *.jpg -m background_music.mp3 -d 60 -p "Dynamic travel montage"
  
  # Different styles
  %(prog)s media/*.* -p "Smooth romantic video" -s smooth
  %(prog)s media/*.* -p "Fast-paced action video" -s fast
  
  # Disable auto-refinement for faster processing
  %(prog)s photo*.jpg -p "Quick slideshow" --no-refine
        """
    )
    
    parser.add_argument(
        'media_files',
        nargs='+',
        help='Media files (images/videos) to include'
    )
    
    parser.add_argument(
        '-p', '--prompt',
        required=True,
        help='Description of the video you want to create'
    )
    
    parser.add_argument(
        '-m', '--music',
        help='Path to music/audio file (auto-detected if in media files)'
    )
    
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=60,
        help='Target video duration in seconds (default: 60)'
    )
    
    parser.add_argument(
        '-s', '--style',
        choices=['auto', 'smooth', 'dynamic', 'fast'],
        default='auto',
        help='Video style (default: auto)'
    )
    
    parser.add_argument(
        '--no-refine',
        action='store_true',
        help='Skip automatic refinement (faster but lower quality)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output directory (default: ./data/renders/)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def expand_media_files(file_patterns: List[str]) -> List[str]:
    """Expand file patterns and validate files exist."""
    expanded_files = []
    
    for pattern in file_patterns:
        # Handle glob patterns
        if '*' in pattern:
            from glob import glob
            files = glob(pattern)
            expanded_files.extend(files)
        else:
            # Single file
            if os.path.exists(pattern):
                expanded_files.append(pattern)
            else:
                print(f"Warning: File not found: {pattern}")
    
    return expanded_files


def separate_audio_files(media_files: List[str]) -> tuple[List[str], str]:
    """Separate audio files from other media."""
    audio_extensions = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'}
    
    audio_files = []
    other_files = []
    
    for file in media_files:
        ext = Path(file).suffix.lower()
        if ext in audio_extensions:
            audio_files.append(file)
        else:
            other_files.append(file)
    
    # Use first audio file as music if found
    music_path = audio_files[0] if audio_files else None
    
    return other_files, music_path


async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Expand and validate media files
    media_files = expand_media_files(args.media_files)
    
    if not media_files:
        print("Error: No valid media files found")
        return 1
    
    # Separate audio from other media
    visual_media, detected_music = separate_audio_files(media_files)
    
    # Determine music source
    music_path = args.music or detected_music
    
    if not visual_media:
        print("Error: No image or video files found")
        return 1
    
    print(f"\n🎬 Memory Movie Maker")
    print(f"{'='*50}")
    print(f"Media files: {len(visual_media)} visual files")
    print(f"Music: {Path(music_path).name if music_path else 'None'}")
    print(f"Duration: {args.duration} seconds")
    print(f"Style: {args.style}")
    print(f"Auto-refine: {not args.no_refine}")
    print(f"Prompt: {args.prompt}")
    print(f"{'='*50}\n")
    
    # Create root agent
    root_agent = RootAgent()
    
    # Create memory movie
    try:
        result = await root_agent.create_memory_movie(
            media_paths=visual_media,
            user_prompt=args.prompt,
            music_path=music_path,
            target_duration=args.duration,
            style=args.style,
            auto_refine=not args.no_refine
        )
        
        if result["status"] == "success":
            print(f"\n✅ Success! Your memory movie is ready:")
            print(f"📹 {result['video_path']}")
            
            if result.get("refinement_iterations", 0) > 0:
                print(f"\n📊 Quality improvements:")
                print(f"   - Refinement iterations: {result['refinement_iterations']}")
                print(f"   - Final score: {result.get('final_score', 'N/A')}/10")
            
            # Copy to output directory if specified
            if args.output:
                output_dir = Path(args.output)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                from shutil import copy2
                output_file = output_dir / Path(result['video_path']).name
                copy2(result['video_path'], output_file)
                print(f"\n📁 Copied to: {output_file}")
            
            print("\n💡 Tip: You can further refine your video by running:")
            print(f"   python scripts/refine_video.py {result['video_path']} -f 'your feedback here'")
            
            return 0
        else:
            print(f"\n❌ Error: {result['error']}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)