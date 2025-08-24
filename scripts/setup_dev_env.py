#!/usr/bin/env python3
"""
Development environment setup script for Memory Movie Maker.
Helps new developers get started quickly.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def check_python_version():
    """Ensure Python 3.10+ is installed."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Python 3.10+ is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✓ Python {version.major}.{version.minor} detected")
    return True


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    if run_command("ffmpeg -version", check=False):
        print("✓ FFmpeg is installed")
        return True
    else:
        print("❌ FFmpeg not found")
        print("\nTo install FFmpeg:")
        if platform.system() == "Darwin":
            print("  macOS: brew install ffmpeg")
        elif platform.system() == "Linux":
            print("  Linux: sudo apt install ffmpeg")
        else:
            print("  Windows: Download from https://ffmpeg.org/download.html")
        return False


def setup_virtual_env():
    """Create and activate virtual environment."""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✓ Virtual environment already exists")
    else:
        print("Creating virtual environment...")
        if not run_command(f"{sys.executable} -m venv venv"):
            return False
        print("✓ Virtual environment created")
    
    # Provide activation instructions
    print("\nTo activate the virtual environment:")
    if platform.system() == "Windows":
        print("  Windows: .\\venv\\Scripts\\activate")
    else:
        print("  macOS/Linux: source venv/bin/activate")
    
    return True


def install_dependencies():
    """Install project dependencies."""
    print("\nInstalling dependencies...")
    
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("⚠️  Warning: Not in a virtual environment!")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return False
    
    # Upgrade pip first
    print("Upgrading pip...")
    if not run_command(f"{sys.executable} -m pip install --upgrade pip"):
        return False
    
    # Install the package in development mode
    print("Installing Memory Movie Maker in development mode...")
    if not run_command(f"{sys.executable} -m pip install -e '.[dev]'"):
        print("\n⚠️  Some dependencies failed to install.")
        print("This might be due to system-specific requirements.")
        print("You can try installing core dependencies only:")
        print(f"  {sys.executable} -m pip install -e .")
        return False
    
    print("✓ Dependencies installed")
    return True


def setup_environment_file():
    """Create .env file from template."""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if env_path.exists():
        print("✓ .env file already exists")
    elif env_example_path.exists():
        print("Creating .env file from template...")
        env_path.write_text(env_example_path.read_text())
        print("✓ .env file created")
        print("  ⚠️  Remember to add your API keys to .env")
    else:
        print("⚠️  No .env.example found, creating basic .env...")
        env_content = """# Memory Movie Maker Configuration

# Google Cloud / Gemini API
GOOGLE_CLOUD_PROJECT=""
GEMINI_API_KEY=""

# Storage
STORAGE_TYPE="filesystem"
STORAGE_PATH="./data"

# Logging
LOG_LEVEL="INFO"

# Development
DEBUG=False
"""
        env_path.write_text(env_content)
        print("✓ Basic .env file created")
    
    return True


def create_data_directories():
    """Create required data directories."""
    directories = [
        "data/projects",
        "data/cache",
        "data/temp",
        "logs",
    ]
    
    print("\nCreating data directories...")
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✓ Data directories created")
    return True


def verify_installation():
    """Verify the installation worked."""
    print("\nVerifying installation...")
    
    # Test imports
    test_code = """
import memory_movie_maker
from memory_movie_maker.models import ProjectState, MediaAsset
print("✓ Core imports successful")

try:
    import librosa
    print("✓ Librosa available")
except ImportError:
    print("⚠️  Librosa not available (audio processing)")

try:
    import moviepy
    print("✓ MoviePy available")
except ImportError:
    print("⚠️  MoviePy not available (video processing)")

"""
    
    return run_command(f"{sys.executable} -c '{test_code}'")


def print_next_steps():
    """Print helpful next steps."""
    print("\n" + "="*60)
    print("🎉 Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Activate your virtual environment (see above)")
    print("2. Add your API keys to .env file")
    print("3. Read docs/NEXT_STEPS.md for implementation guide")
    print("4. Run tests: pytest tests/unit/test_models.py -v")
    print("\nUseful commands:")
    print("  make test     # Run all tests")
    print("  make lint     # Run code quality checks")
    print("  make format   # Format code")
    print("\nHappy coding! 🚀")


def main():
    """Run the setup process."""
    print("Memory Movie Maker - Development Setup")
    print("="*60)
    
    # Check prerequisites
    if not check_python_version():
        return 1
    
    if not check_ffmpeg():
        print("\n⚠️  FFmpeg is recommended but not required for setup")
        response = input("Continue without FFmpeg? (y/N): ")
        if response.lower() != 'y':
            return 1
    
    # Setup environment
    if not setup_virtual_env():
        return 1
    
    # Check if we should install dependencies
    if "--no-install" not in sys.argv:
        if not install_dependencies():
            print("\n⚠️  Dependency installation had issues")
            print("You may need to install some packages manually")
    
    # Setup configuration
    if not setup_environment_file():
        return 1
    
    if not create_data_directories():
        return 1
    
    # Verify if not skipping install
    if "--no-install" not in sys.argv:
        verify_installation()
    
    print_next_steps()
    return 0


if __name__ == "__main__":
    sys.exit(main())