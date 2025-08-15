# Memory Movie Maker

An intelligent, conversational video editing tool that transforms raw photos and videos into polished "memory movies" using AI.

## Overview

Memory Movie Maker leverages Google's Agent Development Kit (ADK) and advanced AI capabilities to automate video creation while maintaining creative control through natural language feedback.

## Features

- 🎬 **Automated Video Creation**: Upload photos/videos and music, get a professionally edited video
- 🤖 **Multi-Agent AI System**: Specialized agents for analysis, composition, evaluation, and refinement
- 🧠 **AI-Powered Edit Planning**: Gemini creates intelligent edit plans with story structure and pacing
- 🎵 **Advanced Music Synchronization**: Detects musical structure (intro/verse/chorus) and syncs cuts to beats
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

Memory Movie Maker uses a **multi-agent architecture** powered by Google's Agent Development Kit (ADK) with a self-correction loop:

```
User Input → RootAgent → AnalysisAgent → CompositionAgent → EvaluationAgent
                              ↑                                      ↓
                              ←──── RefinementAgent ←────────────────
```

### Core Technologies

- **Google ADK**: Multi-agent orchestration framework
- **Gemini API**: Advanced AI for visual analysis and edit planning
- **Librosa**: Professional audio analysis (beats, tempo, musical structure)
- **MoviePy**: Video rendering and effects engine
- **Gradio**: Modern web interface framework

### Agents & Responsibilities

#### 🎯 **RootAgent** (`root_agent.py`)
- **Role**: Workflow orchestrator and user interface
- **Functions**: Manages agent lifecycle, handles user interactions, coordinates data flow
- **No LLM**: Uses deterministic logic for reliable orchestration

#### 🔍 **AnalysisAgent** (`analysis_agent.py`)
- **Role**: Media content understanding
- **Tools**:
  - **Visual Analysis**: Gemini extracts content descriptions, quality scores, notable segments
  - **Audio Technical**: Librosa detects beats, tempo, energy curves, musical structure (intro/verse/chorus)
  - **Audio Semantic**: Gemini provides speech transcription, emotional tone, sound effect detection
- **Output**: Rich media metadata for intelligent composition

#### 🎬 **CompositionAgent** (`composition_agent.py`)
- **Role**: AI-powered video creation
- **Process**:
  1. **Edit Planning**: Gemini creates story structure with pacing and transitions
  2. **Timeline Building**: Maps media to beats with precise timing
  3. **Video Rendering**: Uses MoviePy for effects, transitions, and final export
- **Key Feature**: Beat-synchronized cuts for professional-quality rhythm matching

#### 📊 **EvaluationAgent** (`evaluation_agent.py`)
- **Role**: Quality assessment and improvement identification
- **Functions**: 
  - Scores videos (1-10 scale) on story, pacing, sync, and transitions
  - Provides specific, actionable improvement suggestions
  - Determines if additional refinement is needed (target: ≥7.0 score)

#### 🔧 **RefinementAgent** (`refinement_agent.py`)
- **Role**: Feedback interpretation and edit command generation
- **Functions**:
  - Parses natural language feedback ("make it more upbeat", "slower pacing")
  - Translates to specific edit parameters (tempo changes, clip selection, transitions)
  - Applies user preferences to composition settings

### Self-Correction Loop

The system autonomously improves videos through **iterative refinement**:

1. **Initial Creation**: CompositionAgent generates first draft
2. **Quality Evaluation**: EvaluationAgent scores and critiques (target: 7.0+)
3. **Intelligent Refinement**: If score < 7.0, RefinementAgent applies improvements
4. **Re-rendering**: CompositionAgent creates improved version
5. **Repeat**: Up to 3 iterations or until quality target achieved

This ensures users receive high-quality videos without manual intervention.

### Data Flow Architecture

```
Media Files → Analysis → AI Planning → Timeline → Rendering → Evaluation → Refinement
     ↓            ↓           ↓           ↓           ↓            ↓            ↓
  Metadata    Quality    Edit Plan   Beat-Synced   MP4 Video   Quality     Enhanced
 Extraction    Scores     (Gemini)    Timeline     (MoviePy)   Score       Video
```

### Key Innovation: Hybrid AI Approach

The system combines **three complementary AI approaches**:

1. **Technical Analysis** (Librosa): Precise beat detection, tempo mapping, energy curves
2. **Semantic Understanding** (Gemini): Content comprehension, emotional analysis, story structure  
3. **Creative Synthesis** (Gemini): Intelligent edit planning that considers both technical and creative factors

This hybrid approach enables videos that are both **technically synchronized** and **creatively compelling**.

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

## Library Dependencies

### Core AI & Agent Framework
- **`google-adk==1.9.0`**: Google's Agent Development Kit for multi-agent orchestration
- **`google-genai>=1.0.0`**: New unified Google AI SDK for Gemini API access
- **`google-cloud-aiplatform==1.106.0`**: Google Cloud AI platform integration

### Audio & Video Processing
- **`librosa==0.11.0`**: Professional audio analysis library for beat detection and musical structure
- **`moviepy==2.2.1`**: Python video editing library for rendering and effects
- **`opencv-python==4.12.0.88`**: Computer vision library for advanced video processing
- **`pillow==11.3.0`**: Python Imaging Library for photo processing
- **`numpy>=1.25.0,<2.3.0`**: Numerical computing foundation

### Web Interface & API
- **`gradio==5.39.0`**: Modern web interface framework for AI applications
- **`fastapi==0.116.1`**: High-performance web framework for APIs
- **`uvicorn==0.35.0`**: ASGI web server for FastAPI

### Data Models & Validation
- **`pydantic==2.11.7`**: Data validation and serialization with type hints
- **`pydantic-settings==2.10.1`**: Settings management with Pydantic

### Development Tools
- **`pytest==8.4.1`**: Testing framework with async support
- **`black==25.1.0`**: Code formatter for consistent Python style
- **`mypy==1.17.1`**: Static type checker for Python
- **`isort==5.13.2`**: Import statement organizer

### Optional Dependencies
- **`monitoring`**: OpenTelemetry integration for production monitoring
- **`boto3==1.40.1`**: AWS SDK for future S3 storage support

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete developer guide and project context
- **[Technical Design](docs/TDD.md)** - Architecture deep dive and implementation details
- **[Development Roadmap](docs/roadmap.md)** - Project progress and next steps
- **[RootAgent Guide](docs/ROOT_AGENT_GUIDE.md)** - Orchestration and workflow details
- **[Architecture Decision Records](docs/adr/)** - Key technical decisions and rationale

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [Google ADK](https://google.github.io/adk-docs/) - Agent Development Kit
- [Gemini API](https://ai.google.dev/) - Visual and language understanding
- [Librosa](https://librosa.org/) - Audio analysis
- [MoviePy](https://zulko.github.io/moviepy/) - Video editing
- [Gradio](https://gradio.app/) - Web interface