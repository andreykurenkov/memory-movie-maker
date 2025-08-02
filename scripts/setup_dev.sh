#!/bin/bash

# Setup script for Memory Movie Maker development environment

set -e  # Exit on error

echo "<¬ Setting up Memory Movie Maker development environment..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "L Error: Python 3.10+ is required (found $PYTHON_VERSION)"
    exit 1
fi

echo " Python version check passed: $PYTHON_VERSION"

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo "L Error: This script must be run from the project root directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "=æ Creating virtual environment..."
    python3 -m venv venv
else
    echo "=æ Virtual environment already exists"
fi

# Activate virtual environment
echo "= Activating virtual environment..."
source venv/bin/activate

# Upgrade pip and install build tools
echo " Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

# Install the package in editable mode with dev dependencies
echo "=Ú Installing project dependencies..."
pip install -e ".[dev,monitoring]"

# Check for FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "   Warning: FFmpeg not found. Please install FFmpeg for video processing:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu: sudo apt-get install ffmpeg"
    echo "   Windows: Download from https://ffmpeg.org/download.html"
else
    echo " FFmpeg is installed"
fi

# Create necessary directories
echo "=Á Creating project directories..."
mkdir -p data/{projects,cache,temp}
mkdir -p logs
mkdir -p tests/fixtures/media/{images,videos,audio}

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "= Creating .env file from template..."
    cp .env.example .env
    echo "   Please edit .env and add your API keys"
else
    echo "= .env file already exists"
fi

# Set up pre-commit hooks (if pre-commit is installed)
if command -v pre-commit &> /dev/null; then
    echo "> Setting up pre-commit hooks..."
    pre-commit install
else
    echo "9  Skipping pre-commit setup (not installed)"
fi

# Run initial tests to verify setup
echo ">ê Running quick test to verify setup..."
python -c "
import sys
print(f'Python: {sys.version}')
try:
    import memory_movie_maker
    print(' Package import successful')
except ImportError as e:
    print(f'L Package import failed: {e}')
    sys.exit(1)
"

# Display next steps
echo ""
echo "( Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Edit .env file with your API keys"
echo "3. Run tests: make test"
echo "4. Start development: make run"
echo ""
echo "Useful commands:"
echo "  make help      - Show all available make commands"
echo "  make test      - Run all tests"
echo "  make coverage  - Run tests with coverage report"
echo "  make format    - Format code with black and isort"
echo "  make lint      - Run linting checks"
echo ""