#!/usr/bin/env python3
"""Launch the Memory Movie Maker web interface."""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.memory_movie_maker.web.app import launch_app


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Launch Memory Movie Maker web interface"
    )
    
    parser.add_argument(
        '--share',
        action='store_true',
        help='Create a public share link (requires internet)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=7860,
        help='Port to run the server on (default: 7860)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("""
    🎬 Memory Movie Maker - Web Interface
    ====================================
    
    Starting web server...
    """)
    
    if args.share:
        print("📡 Creating public share link...")
    else:
        print(f"🌐 Local URL: http://localhost:{args.port}")
    
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        launch_app(share=args.share, port=args.port)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())