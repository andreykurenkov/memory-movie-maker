# Memory Movie Maker - Project Context

## Project Overview

Memory Movie Maker is an intelligent, conversational video editing tool that transforms raw photos and videos into polished "memory movies" using Google's Agent Development Kit (ADK) and advanced AI capabilities.

### Key Technologies
- **Google ADK**: Multi-agent orchestration framework
- **Gemini API**: Visual analysis and natural language processing (using new google-genai SDK v1.28.0)
- **Librosa**: Audio analysis and beat detection
- **MoviePy/FFmpeg**: Video rendering
- **Gradio**: Web interface

## Architecture Overview

The system uses a Multi-Agent System (MAS) architecture with five specialized agents:

1. **RootAgent**: Orchestrates the entire workflow
2. **AnalysisAgent**: Analyzes media files (visual and audio)
3. **CompositionAgent**: Creates video timelines and renders output
4. **EvaluationAgent**: Critiques generated videos
5. **RefinementAgent**: Translates feedback into editing commands

### Self-Correction Loop
The system autonomously generates, evaluates, and refines videos 2-3 times before presenting to the user, ensuring higher quality output.

## Developer Quick Start

### Prerequisites Checklist

Before starting development, ensure you have:

- [ ] Python 3.10+ installed (`python --version`)
- [ ] FFmpeg installed (see installation guide below)
- [ ] Git configured
- [ ] Google Cloud account or Gemini API key
- [ ] 8GB+ RAM recommended for video processing
- [ ] 10GB+ free disk space

### FFmpeg Installation

FFmpeg is required for video processing:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Extract to C:\ffmpeg
3. Add C:\ffmpeg\bin to PATH environment variable

**Verify installation:**
```bash
ffmpeg -version
```

### Installing Librosa

Librosa is much easier to install than Essentia:

**All platforms:**
```bash
pip install librosa
```

**Optional dependencies for better performance:**
```bash
# For faster audio loading
pip install soundfile

# For MP3 support
pip install audioread
```

**Verify Installation:**
```python
import librosa
print(f"Librosa version: {librosa.__version__}")

# Test loading audio
y, sr = librosa.load(librosa.example('trumpet'))
print(f"Sample rate: {sr}, Duration: {len(y)/sr:.2f}s")
```

### Audio Analysis Architecture

The system uses **two complementary audio analysis approaches**:

1. **Technical Analysis (Librosa)**
   - Beat detection and tempo extraction
   - Energy curves for dynamic video cuts
   - Musical characteristics (danceability, valence)
   - Perfect for rhythm-synced editing

2. **Semantic Analysis (Gemini)**
   - Speech transcription and speaker identification
   - Emotional tone and topic extraction
   - Audio segmentation (speech, music, effects)
   - Content-aware video composition

Both tools work together to enable intelligent video editing that syncs with both the rhythm AND meaning of audio content.

### Setting Up API Access

#### Gemini API Setup
1. **Option A: Google Cloud Vertex AI**
   ```bash
   # Install gcloud CLI: https://cloud.google.com/sdk/docs/install
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   gcloud services enable aiplatform.googleapis.com
   ```

2. **Option B: Direct Gemini API (Recommended)**
   - Visit https://makersuite.google.com/app/apikey
   - Create new API key
   - Add to .env: `GEMINI_API_KEY=your-key-here`

#### Important: New Google GenAI SDK
As of 2025, we use the new `google-genai` SDK (v1.28.0) instead of the deprecated `google-generativeai` package. The new SDK provides:
- Better performance and reliability
- Unified API across different Google AI services
- Improved file handling for large media uploads
- Native async support

Example usage:
```python
from google import genai

# Initialize client
client = genai.Client(api_key=settings.gemini_api_key)

# Upload and analyze media
file = client.files.upload(file="video.mp4")
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[file, "Analyze this video"]
)
```

### Your First Agent Implementation

Here's a minimal example of creating a custom agent:

```python
# src/memory_movie_maker/agents/example_agent.py
from google.adk.agents import LlmAgent
from google.adk.tools import tool

# Define a tool for the agent
@tool
def count_media_files(project_state: dict) -> dict:
    """Count media files in the project.
    
    Args:
        project_state: Current project state
        
    Returns:
        Count of media files by type
    """
    media_count = {
        "images": 0,
        "videos": 0
    }
    
    for media in project_state.get("user_inputs", {}).get("media", []):
        if media["type"] == "image":
            media_count["images"] += 1
        elif media["type"] == "video":
            media_count["videos"] += 1
    
    return {
        "status": "success",
        "result": media_count
    }

# Create the agent
class ExampleAgent(LlmAgent):
    def __init__(self):
        super().__init__(
            name="example_agent",
            model="gemini-2.0-flash",
            description="Example agent for counting media files",
            instruction="""You are a helpful agent that counts media files.
            When asked, use the count_media_files tool to provide statistics.""",
            tools=[count_media_files]
        )

# Test the agent
if __name__ == "__main__":
    from google.adk.runners import InMemoryRunner
    
    agent = ExampleAgent()
    runner = InMemoryRunner(agent)
    
    # Sample project state
    test_state = {
        "user_inputs": {
            "media": [
                {"type": "image", "path": "photo1.jpg"},
                {"type": "video", "path": "video1.mp4"},
                {"type": "image", "path": "photo2.jpg"}
            ]
        }
    }
    
    response = runner.run("How many media files do we have?", state=test_state)
    print(response)
```

### Running and Debugging Agents

1. **Run a single agent:**
   ```bash
   python -m memory_movie_maker.agents.example_agent
   ```

2. **Debug with logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # In your agent
   logger = logging.getLogger(__name__)
   logger.debug("Agent state: %s", state)
   ```

3. **Use ADK's development UI:**
   ```bash
   adk web --agent memory_movie_maker.agents.example_agent
   ```

### Common Pitfalls and Solutions

1. **Import Errors with ADK**
   - Ensure `google-adk` is installed: `pip install google-adk`
   - Check virtual environment is activated

2. **Gemini API Rate Limits**
   - Implement exponential backoff
   - Cache analysis results
   - Use batch processing

3. **Memory Issues with Video Processing**
   - Process videos in chunks
   - Clear temporary files regularly
   - Monitor memory usage

4. **Agent Communication Issues**
   - Always return proper status format: `{"status": "success/error", "result": ...}`
   - Validate ProjectState schema
   - Use structured logging for debugging

## Development Guidelines

### Code Standards
- Python 3.10+ with type hints
- Follow PEP 8 style guide
- Use Pydantic for data validation
- Implement comprehensive error handling
- Write docstrings for all public functions

### Testing Requirements
- Minimum 80% code coverage
- Unit tests for all components
- Integration tests for agent interactions
- End-to-end tests for complete workflows
- Use pytest with fixtures and mocks

### Project Structure
```
src/
├── agents/      # ADK agent implementations
├── tools/       # Agent tools (analysis, rendering, etc.)
├── models/      # Pydantic data models
├── storage/     # Storage abstraction layer
└── web/         # Gradio web interface
```

### Environment Configuration
```bash
# Required environment variables (.env file)
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"
GOOGLE_GENAI_USE_VERTEXAI="True"
GEMINI_API_KEY="your-api-key"  # Alternative to Vertex AI

# Storage configuration
STORAGE_TYPE="filesystem"  # or "s3" in future
STORAGE_PATH="./data"
```

### API Key Management
- Never commit API keys to the repository
- Use environment variables for all credentials
- Provide .env.example with dummy values
- Document required permissions for each service

## Development Workflow

### 1. Feature Development
- Create feature branch from main
- Implement with tests
- Ensure all tests pass
- Update documentation

### 2. Testing Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test category
pytest tests/unit/
pytest tests/integration/
```

### 3. Code Quality
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

## Agent Development Guidelines

### Creating New Agents
1. Inherit from appropriate ADK base class (Agent, LlmAgent, etc.)
2. Define clear agent description and instructions
3. Specify required tools
4. Implement error handling
5. Write comprehensive tests

### Tool Development
```python
from google.adk.tools import tool

@tool
def my_tool(param: str) -> dict:
    """Tool description for LLM.
    
    Args:
        param: Parameter description
        
    Returns:
        Dictionary with 'status' and 'result' keys
    """
    try:
        # Tool implementation
        return {"status": "success", "result": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### Agent Communication
- Use ProjectState as the single source of truth
- Pass state between agents via RootAgent
- Maintain immutable state updates
- Log all state transitions

## Performance Considerations

### Media Processing
- Batch process media files when possible
- Cache analysis results in MediaAsset.geminiAnalysis
- Use async operations for I/O-bound tasks
- Implement progress tracking for long operations

### Memory Management
- Stream large video files instead of loading entirely
- Clean up temporary files after processing
- Implement file size limits
- Use efficient data structures

## Security Guidelines

### Input Validation
- Validate all file uploads (type, size, content)
- Sanitize user input in prompts
- Implement rate limiting for API calls
- Use secure file paths (no directory traversal)

### API Security
- Use least-privilege API permissions
- Rotate API keys regularly
- Monitor API usage and costs
- Implement request timeouts

## Debugging Tips

### Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.info("Processing media file: %s", filename)
logger.error("Analysis failed", exc_info=True)
```

### Agent Debugging
- Use ADK's built-in logging
- Enable verbose mode for development
- Inspect ProjectState at each step
- Use breakpoints in tool functions

### Common Issues
1. **Gemini API errors**: Check quotas and rate limits
2. **Memory issues**: Reduce batch sizes, use streaming
3. **Rendering failures**: Verify media codec compatibility
4. **Agent timeouts**: Increase timeout values for long operations

## Future Considerations

### Cloud Migration
- Storage interface designed for S3 compatibility
- Stateless agents for horizontal scaling
- Queue-based processing for large workloads
- CDN integration for media delivery

### Feature Extensions
- Multi-language support
- Custom music generation
- Advanced effects and transitions
- Collaborative editing features

## Resources

### Documentation
- [Google ADK Docs](https://google.github.io/adk-docs/)
- [Gemini API Reference](https://ai.google.dev/gemini-api/docs)
- [Librosa Documentation](https://librosa.org/doc/latest/)
- [MoviePy Guide](https://zulko.github.io/moviepy/)

### Support
- GitHub Issues for bug reports
- Pull requests for contributions
- Code reviews required for all changes
- Maintain changelog for releases