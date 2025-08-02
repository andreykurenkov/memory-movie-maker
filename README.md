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
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/memory-movie-maker.git
cd memory-movie-maker
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Usage

1. Start the web interface:
```bash
python -m memory_movie_maker
```

2. Open your browser to `http://localhost:7860`

3. Upload your media files and music

4. Describe your vision (e.g., "Create a 2-minute upbeat video of our Hawaii vacation")

5. Wait for AI to generate your video

6. Provide feedback to refine (e.g., "Add more sunset shots, make the beginning slower")

## Architecture

Memory Movie Maker uses a multi-agent architecture:

- **RootAgent**: Orchestrates the entire workflow
- **AnalysisAgent**: Analyzes media content and music
- **CompositionAgent**: Creates video timelines and renders output
- **EvaluationAgent**: Reviews quality and adherence to user intent
- **RefinementAgent**: Translates feedback into editing commands

## Troubleshooting

### Common Setup Issues

#### FFmpeg Installation
- **macOS**: If `brew install ffmpeg` fails, try `brew update` first
- **Ubuntu**: For codec issues, install with: `sudo apt install ffmpeg libavcodec-extra`
- **Windows**: Ensure FFmpeg bin directory is in PATH. Test with: `ffmpeg -version`

#### Python Environment
- **ImportError**: Ensure virtual environment is activated: `source venv/bin/activate`
- **Version Error**: Requires Python 3.10+. Check with: `python --version`
- **Package conflicts**: Try clean install: `pip install --force-reinstall -e .`

#### API Setup
- **Gemini API errors**: 
  - Check API key is set in `.env`
  - Verify quotas at: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com
  - For 429 errors, implement retry with exponential backoff

#### Memory Issues
- **Large video processing**: 
  - Reduce batch size in config
  - Increase swap space
  - Use lower resolution for testing

### Performance Optimization

- **Slow analysis**: Enable caching in `.env`: `ANALYSIS_CACHE_ENABLED=True`
- **Long render times**: Use lower quality settings for testing
- **API rate limits**: Batch requests and implement caching

## Development

### Quick Start for New Developers

1. **Understand the architecture**: Read [CLAUDE.md](CLAUDE.md) Section "Developer Quick Start"
2. **Explore examples**: Check `examples/` directory for implementation patterns
3. **Run a single agent**: See `examples/agents/sample_analysis_agent.py`
4. **Debug with logging**: Set `LOG_LEVEL=DEBUG` in `.env`

### Project Structure

See [docs/TDD.md](docs/TDD.md) for detailed project structure.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test suite
pytest tests/unit/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Documentation

- [Product Requirements](docs/PRD.md)
- [Technical Design](docs/TDD.md)
- [Development Roadmap](docs/roadmap.md)
- [AI Context](CLAUDE.md)

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [Google ADK](https://google.github.io/adk-docs/) - Agent Development Kit
- [Gemini API](https://ai.google.dev/) - Visual and language understanding
- [Essentia](https://essentia.upf.edu/) - Audio analysis
- [MoviePy](https://zulko.github.io/moviepy/) - Video editing
- [Gradio](https://gradio.app/) - Web interface