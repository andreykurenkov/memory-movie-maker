# Memory Movie Maker

An intelligent, conversational video editing tool that transforms raw photos and videos into polished "memory movies" using AI.

## Overview

Memory Movie Maker leverages Google's Agent Development Kit (ADK) and advanced AI capabilities to automate video creation while maintaining creative control through natural language feedback.

## Features

- 🎬 **Automated Video Creation**: Upload photos/videos and music, get a professionally edited video
- 🤖 **Multi-Agent AI System**: Specialized agents for analysis, composition, evaluation, and refinement
- 🎵 **Music Synchronization**: Automatic beat detection and rhythmic video pacing
- 💬 **Natural Language Control**: Refine videos with simple commands like "make it more upbeat"
- 🔄 **Self-Improving**: AI autonomously reviews and improves videos before showing them
- 🌐 **Web Interface**: Simple drag-and-drop interface built with Gradio

## Quick Start

### Prerequisites

- Python 3.10+
- FFmpeg (for video processing)
- Gemini API key (get one at https://makersuite.google.com/app/apikey)
- 8GB+ RAM recommended
- 10GB+ free disk space

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/memory-movie-maker.git
cd memory-movie-maker
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

4. Set up your API key:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Usage

#### Option 1: Web Interface (Recommended)

```bash
python scripts/launch_web_app.py
# Open http://localhost:7860 in your browser
```

#### Option 2: Command Line

```bash
# Basic usage
python scripts/create_memory_movie.py photo1.jpg photo2.jpg video1.mp4 \
    -p "Create a beautiful vacation montage" \
    -m background_music.mp3 \
    -d 60

# With specific style
python scripts/create_memory_movie.py media/*.* \
    -p "Dynamic sports highlights with fast cuts" \
    -s fast \
    -d 30

# Quick mode (no auto-refinement)
python scripts/create_memory_movie.py *.jpg \
    -p "Simple photo slideshow" \
    --no-refine
```

#### Option 3: Python API

```python
from memory_movie_maker.agents.root_agent import RootAgent
import asyncio

async def create_video():
    agent = RootAgent()
    result = await agent.create_memory_movie(
        media_paths=["photo1.jpg", "photo2.jpg", "video1.mp4"],
        user_prompt="Create a romantic anniversary video",
        music_path="love_song.mp3",
        target_duration=60,
        style="smooth",
        auto_refine=True
    )
    print(f"Video created: {result['video_path']}")

asyncio.run(create_video())
```

## Architecture

Memory Movie Maker uses a multi-agent architecture with a self-correction loop:

```
User Input → RootAgent → AnalysisAgent → CompositionAgent → EvaluationAgent
                              ↑                                      ↓
                              ←──── RefinementAgent ←────────────────
```

### Agents

- **RootAgent**: Orchestrates the workflow sequentially (no LLM decision-making needed)
- **AnalysisAgent**: Analyzes media files using:
  - Gemini for visual understanding (native video analysis)
  - Librosa for technical audio features (beats, tempo, energy)
  - Gemini for semantic audio analysis (speech, emotions)
- **CompositionAgent**: Creates beat-synced timelines and renders videos
- **EvaluationAgent**: Scores videos (1-10) and suggests specific improvements
- **RefinementAgent**: Parses feedback into actionable edit commands

### Self-Correction Loop

The system automatically refines videos up to 3 times:
1. Create initial video
2. Evaluate quality (target: 7.0+ score)
3. If needed, apply refinements and re-render
4. Repeat until acceptable or max iterations reached

## Troubleshooting

### Installation Issues

**FFmpeg not found**:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian  
sudo apt update && sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Add to PATH environment variable
```

**Gemini API errors**:
- "API key not valid": Check GEMINI_API_KEY in .env
- "Quota exceeded": Wait or upgrade at https://console.cloud.google.com
- Set `GOOGLE_GENAI_USE_VERTEXAI=False` for direct API usage

**Memory errors with large videos**:
- Use `--no-refine` flag for faster processing
- Reduce video resolution in settings
- Process fewer files at once

### Performance Tips

- **Faster processing**: Use `--no-refine` to skip quality improvements
- **Better quality**: Keep auto-refine enabled (default)
- **Batch processing**: The system processes media files concurrently
- **Caching**: Analysis results are cached to avoid re-processing

## Development

### Quick Start for New Developers

1. **Read the docs**:
   - [CLAUDE.md](CLAUDE.md) - Complete developer guide
   - [ROOT_AGENT_GUIDE.md](docs/ROOT_AGENT_GUIDE.md) - Orchestration details
   - [TDD.md](docs/TDD.md) - Technical design and architecture

2. **Run example scripts**:
   ```bash
   # Test individual components
   python scripts/test_visual_analysis.py
   python scripts/test_audio_with_real_file.py
   python scripts/test_composition.py
   
   # Test complete workflow
   python scripts/test_root_agent.py
   ```

3. **Debug with enhanced logging**:
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   python scripts/create_memory_movie.py ...
   ```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only

# Run tests for specific component
pytest tests/unit/test_composition.py
pytest -k "test_root_agent"
```

### Key Features Explained

**🎵 Beat Synchronization**: Videos automatically sync cuts to music beats using Librosa's tempo detection

**🤖 Self-Correction**: The system evaluates its own output and makes improvements before showing you

**💬 Natural Language**: Just describe what you want - no need to learn complex editing tools

**📊 Quality Scoring**: Each video gets a quality score (1-10) with specific improvement suggestions

**🔄 Iterative Refinement**: Make changes with simple commands like "make it slower" or "add more transitions"

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports  
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Documentation

- [CLAUDE.md](CLAUDE.md) - Complete developer guide and project context
- [Product Requirements](docs/PRD.md) - What we're building and why
- [Technical Design](docs/TDD.md) - How it's built
- [Development Roadmap](docs/roadmap.md) - Progress and next steps
- [RootAgent Guide](docs/ROOT_AGENT_GUIDE.md) - Orchestration details

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [Google ADK](https://google.github.io/adk-docs/) - Agent Development Kit
- [Gemini API](https://ai.google.dev/) - Visual and language understanding
- [Librosa](https://librosa.org/) - Audio analysis
- [MoviePy](https://zulko.github.io/moviepy/) - Video editing
- [Gradio](https://gradio.app/) - Web interface