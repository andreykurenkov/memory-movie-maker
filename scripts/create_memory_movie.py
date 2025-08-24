#!/usr/bin/env python3
"""Command-line interface for creating memory movies."""

import argparse
import asyncio
import sys
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
  
  # Different aspect ratios
  %(prog)s media/*.* -p "Instagram story" --aspect-ratio 9:16
  %(prog)s media/*.* -p "Square social media post" --aspect-ratio 1:1
  %(prog)s media/*.* -p "Cinematic travel video" --aspect-ratio 21:9
  
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
        '--aspect-ratio',
        choices=['16:9', '9:16', '4:3', '1:1', '21:9'],
        default='16:9',
        help='Video aspect ratio (default: 16:9 widescreen)'
    )
    
    parser.add_argument(
        '--no-refine',
        action='store_true',
        help='Skip automatic refinement (faster but lower quality)'
    )
    
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Render in preview quality (640x360 @ 24fps) for faster processing'
    )
    
    parser.add_argument(
        '--no-original-audio',
        action='store_true',
        help='Remove original audio from video clips (use music only)'
    )
    
    parser.add_argument(
        '--audio-mix',
        type=float,
        default=0.3,
        help='Original audio volume when mixing with music (0.0-1.0, default: 0.3)'
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
    
    parser.add_argument(
        '--no-analysis',
        action='store_true',
        help='Skip saving AI analysis report'
    )
    
    return parser.parse_args()


def expand_media_files(file_patterns: List[str]) -> List[str]:
    """Expand file patterns and validate files exist."""
    from pathlib import Path
    from glob import glob
    
    expanded_files = []
    valid_extensions = {
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff',
        # Videos
        '.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.mpg', '.mpeg',
        # Audio
        '.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'
    }
    
    for pattern in file_patterns:
        # Check for path traversal attempts
        if '..' in pattern:
            print(f"Error: Path traversal not allowed: {pattern}")
            continue
        # Handle glob patterns
        if '*' in pattern or '?' in pattern:
            files = glob(pattern)
            for file_path in files:
                path = Path(file_path)
                # Skip directories
                if path.is_dir():
                    print(f"Warning: Skipping directory: {file_path}")
                    continue
                # Check extension
                if path.suffix.lower() not in valid_extensions:
                    print(f"Warning: Skipping unsupported file type: {file_path}")
                    continue
                # Check size (warn for files over 1GB)
                if path.stat().st_size > 1024 * 1024 * 1024:
                    print(f"Warning: Large file (>1GB): {file_path}")
                expanded_files.append(str(path.resolve()))
        else:
            # Single file
            path = Path(pattern)
            if path.exists():
                if path.is_dir():
                    print(f"Error: Path is a directory: {pattern}")
                    continue
                if path.suffix.lower() not in valid_extensions:
                    print(f"Error: Unsupported file type: {pattern}")
                    continue
                expanded_files.append(str(path.resolve()))
            else:
                print(f"Error: File not found: {pattern}")
    
    if not expanded_files:
        raise ValueError("No valid media files found after validation")
    
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
    print(f"Aspect Ratio: {args.aspect_ratio}")
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
            aspect_ratio=args.aspect_ratio,
            auto_refine=not args.no_refine,
            save_analysis=not args.no_analysis,
            preview_mode=args.preview
        )
        
        if result["status"] == "success":
            print(f"\n✅ Success! Your memory movie is ready:")
            
            # Show project directory
            project_state = result.get("project_state")
            if project_state and project_state.storage_path:
                print(f"\n📂 Project Directory: {project_state.storage_path}")
                print(f"   Contains: video, AI analysis, project state")
            
            print(f"\n📹 Video: {result['video_path']}")
            
            # Show AI analysis report if saved
            if result.get("ai_analysis_report") and not args.no_analysis:
                print(f"📝 AI Analysis: {Path(result['ai_analysis_report']).name}")
            
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