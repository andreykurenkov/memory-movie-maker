# Memory Movie Maker: Technical Design Document (TDD)

## Project Structure

```
memory-movie-maker/
├── .env.example                    # Example environment variables
├── .gitignore                      # Git ignore patterns
├── .github/                        # GitHub specific files
│   └── workflows/                  # CI/CD workflows
│       └── tests.yml              # Automated testing workflow
├── pyproject.toml                  # Project configuration and dependencies
├── README.md                       # Project overview and setup instructions
├── CLAUDE.md                       # Development context for AI assistants
├── Makefile                        # Common development tasks
│
├── docs/                           # Project documentation
│   ├── TDD.md                     # Technical Design Document (this file)
│   ├── roadmap.md                 # Development roadmap and task tracking
│   ├── ROOT_AGENT_GUIDE.md        # RootAgent workflow documentation
│   ├── API_REFERENCE.md           # Comprehensive API documentation
│   ├── AGENT_ARCHITECTURE.md      # Multi-agent system architecture
│   └── adr/                       # Architecture Decision Records
│       ├── 001-use-google-adk.md
│       └── 002-data-model-design.md
│
├── src/                            # Source code
│   ├── __init__.py
│   ├── memory_movie_maker/         # Main package
│   │   ├── __init__.py
│   │   ├── __main__.py            # CLI entry point
│   │   ├── config.py              # Configuration management
│   │   ├── constants.py           # Project constants
│   │   │
│   │   ├── agents/                # ADK Agent implementations
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Base agent classes
│   │   │   ├── root_agent.py      # Main orchestrator agent
│   │   │   ├── analysis_agent.py  # Media analysis agent
│   │   │   ├── composition_agent.py # Video composition agent
│   │   │   ├── evaluation_agent.py  # Quality evaluation agent
│   │   │   └── refinement_agent.py  # Feedback refinement agent
│   │   │
│   │   ├── tools/                 # Agent tools
│   │   │   ├── __init__.py
│   │   │   ├── visual_analysis.py # Gemini visual analysis
│   │   │   ├── audio_analysis.py  # Librosa audio analysis
│   │   │   ├── video_rendering.py # MoviePy rendering
│   │   │   ├── critique.py        # Video critique tool
│   │   │   ├── nlp_parser.py      # Natural language parsing
│   │   │   ├── semantic_audio_analysis.py # Gemini audio understanding
│   │   │   └── edit_planner.py    # AI-powered edit planning
│   │   │
│   │   ├── models/                # Data models
│   │   │   ├── __init__.py
│   │   │   ├── project_state.py   # Main project state model
│   │   │   ├── media_asset.py     # Media file models
│   │   │   ├── timeline.py        # Timeline and segment models
│   │   │   └── analysis.py        # Analysis result models
│   │   │
│   │   ├── storage/               # Storage abstraction
│   │   │   ├── __init__.py
│   │   │   ├── interface.py       # Abstract storage interface
│   │   │   ├── filesystem.py      # Local filesystem implementation
│   │   │   ├── s3.py             # S3 storage (future)
│   │   │   └── utils.py          # Storage utilities
│   │ 
│   │   ├── utils/                 # Utility functions
│   │   │   ├── __init__.py
│   │   │   ├── logging.py        # Structured logging setup
│   │   │   ├── validation.py     # Input validation utilities
│   │   │   ├── media.py          # Media file utilities
│   │   │   └── cache.py          # Caching utilities
│   │   │
│   │   └── web/                   # Web interface
│   │       ├── __init__.py
│   │       ├── app.py            # Gradio application
│   │       ├── components.py     # UI components
│   │       └── handlers.py       # Request handlers
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration and fixtures
│   │
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_algorithms.py
│   │   ├── test_tools.py
│   │   └── test_utils.py
│   │
│   ├── integration/              # Integration tests
│   │   ├── __init__.py
│   │   ├── test_agents.py
│   │   ├── test_storage.py
│   │   ├── test_workflow.py
│   │   └── test_web.py
│   │
│   ├── e2e/                      # End-to-end tests
│   │   ├── __init__.py
│   │   └── test_full_workflow.py
│   │
│   └── fixtures/                 # Test data
│       ├── __init__.py
│       ├── media/               # Sample media files
│       │   ├── images/
│       │   ├── videos/
│       │   └── audio/
│       └── configs/             # Test configurations
│
├── scripts/                      # Development and deployment scripts
│   ├── setup_dev.sh            # Development environment setup
│   ├── run_tests.sh            # Test runner script
│   └── deploy.sh               # Deployment script (future)
│
├── data/                        # Local data storage (gitignored)
│   ├── projects/               # Project files
│   ├── cache/                  # Analysis cache
│   └── temp/                   # Temporary files
│
└── logs/                        # Application logs (gitignored)
    ├── app.log                 # Main application log
    ├── agents.log              # Agent-specific logs
    └── performance.log         # Performance metrics
```

### Key Files Explanation

#### Configuration Files
- **`.env.example`**: Template for environment variables (API keys, settings)
- **`pyproject.toml`**: Project metadata, dependencies, and tool configurations
- **`Makefile`**: Common commands (install, test, lint, run)

#### Source Code Organization
- **`agents/`**: Each agent is a separate module implementing ADK patterns
- **`tools/`**: Reusable tools that agents can use, following ADK tool interface
- **`models/`**: Pydantic models for type safety and validation
- **`storage/`**: Abstract interface allows easy migration from filesystem to cloud
- **`utils/`**: Shared utilities to avoid code duplication
- **`web/`**: All web interface code isolated for easy replacement

#### Testing Structure
- **`unit/`**: Fast, isolated tests for individual components
- **`integration/`**: Tests for component interactions
- **`e2e/`**: Full workflow tests simulating real usage
- **`fixtures/`**: Shared test data and configurations

#### Runtime Directories
- **`data/`**: Persistent storage for projects and cache
- **`logs/`**: Structured logs for debugging and monitoring

## 1. System Architecture Overview

### 1.1 High-Level Architecture

Memory Movie Maker is designed as a **Multi-Agent System (MAS)** using Google's Agent Development Kit (ADK). This architecture promotes modularity, scalability, and maintainability through specialized agents that collaborate to achieve complex video editing tasks.

```
┌─────────────────────────────────────────────────────────────┐
│                        Web Interface                         │
│                         (Gradio)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                       RootAgent                              │
│                    (Orchestrator)                            │
└──────┬──────────┬──────────┬──────────┬──────────┬─────────┘
       │          │          │          │          │
┌──────▼────┐ ┌──▼────┐ ┌──▼─────┐ ┌──▼──────┐ ┌─▼────────┐
│ Analysis  │ │Compo- │ │Evalua- │ │Refine-  │ │Project   │
│  Agent    │ │sition │ │tion    │ │ment     │ │State     │
│           │ │Agent  │ │Agent   │ │Agent    │ │Manager   │
└─────┬─────┘ └───┬───┘ └───┬────┘ └────┬────┘ └──────────┘
      │           │         │            │
┌─────▼─────────────────────▼────────────▼────────────────────┐
│                         Tools Layer                          │
│  Visual Analysis │ Audio Analysis │ Rendering │ Critique    │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Core Components

#### Agents
1. **RootAgent**: Central orchestrator managing workflow and state
2. **AnalysisAgent**: Media content analysis specialist
3. **CompositionAgent**: AI-powered edit planning and video rendering
4. **EvaluationAgent**: Output quality assessment
5. **RefinementAgent**: Natural language to command translation

#### Support Systems
- **Storage Layer**: Abstracted storage interface
- **State Management**: Centralized project state
- **Tools**: Specialized functions for agents
- **Web Interface**: User interaction layer

## 2. Detailed Component Design

### 2.1 Agent Specifications

#### RootAgent
```python
class RootAgent(SequentialAgent):
    """
    Orchestrates the entire video creation workflow.
    Manages project state and coordinates sub-agents.
    """
    
    name = "root_agent"
    model = "gemini-2.0-flash"
    description = "Main orchestrator for memory movie creation"
    
    sub_agents = [
        AnalysisAgent,
        CompositionAgent,
        EvaluationAgent,
        RefinementAgent
    ]
    
    autonomous_iterations = 3  # Self-correction cycles
```

#### AnalysisAgent
```python
class AnalysisAgent(LlmAgent):
    """
    Analyzes media files for content, quality, and characteristics.
    """
    
    name = "analysis_agent"
    model = "gemini-2.0-flash"
    
    tools = [
        visual_analysis_tool,
        audio_analysis_tool,
        batch_process_tool
    ]
```

### 2.2 Data Models

#### ProjectState
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class MediaAsset(BaseModel):
    """Individual media file representation"""
    id: str = Field(..., description="Unique identifier")
    file_path: str
    type: Literal["image", "video"]
    upload_timestamp: datetime
    metadata: Dict[str, Any] = {}
    gemini_analysis: Optional[GeminiAnalysis] = None
    required: bool = False

class GeminiAnalysis(BaseModel):
    """Structured output from Gemini visual analysis"""
    description: str
    aesthetic_score: float = Field(..., ge=0, le=1)
    quality_issues: List[str] = []
    main_subjects: List[str] = []
    tags: List[str] = []
    best_moment_timestamp: Optional[float] = None
    motion_level: Optional[str] = None

class AudioAnalysisProfile(BaseModel):
    """Audio track analysis results"""
    file_path: str
    beat_timestamps: List[float]
    tempo_bpm: float
    energy_curve: List[float]
    duration: float
    vibe: AudioVibe

class AudioVibe(BaseModel):
    """Musical characteristics"""
    danceability: float = Field(..., ge=0, le=1)
    energy: float = Field(..., ge=0, le=1)
    mood: str
    genre: Optional[str] = None

class AudioSegment(BaseModel):
    """Semantic audio segment with musical structure"""
    start_time: float
    end_time: float
    content: str
    type: str  # speech, music, silence, effects
    importance: float = 0.5
    musical_structure: Optional[str] = None  # intro, verse, chorus, etc.
    energy_transition: Optional[str] = None  # building, peak, dropping
    musical_elements: List[str] = []  # instruments detected
    sync_priority: float = 0.5  # How important to sync cuts here

class TimelineSegment(BaseModel):
    """Single clip in the timeline"""
    media_asset_id: str
    start_time: float
    end_time: float
    duration: float
    in_point: float = 0.0
    out_point: Optional[float] = None
    transition: Optional[str] = None

class ProjectState(BaseModel):
    """Complete project state"""
    project_id: str
    created_at: datetime
    updated_at: datetime
    
    # User inputs
    user_inputs: UserInputs
    
    # Analysis results
    analysis: AnalysisResults
    
    # Timeline
    timeline: Timeline
    
    # History
    history: ProjectHistory
    
    # Current status
    status: ProjectStatus

class UserInputs(BaseModel):
    """User-provided inputs"""
    media: List[MediaAsset] = []
    music: List[MediaAsset] = []
    initial_prompt: str
    target_duration: int  # seconds
    aspect_ratio: str = "16:9"
    style_preferences: Dict[str, Any] = {}

class AnalysisResults(BaseModel):
    """Analysis outputs"""
    music_profiles: List[AudioAnalysisProfile] = []
    media_pool: List[MediaAsset] = []
    analysis_timestamp: Optional[datetime] = None

class Timeline(BaseModel):
    """Video timeline"""
    segments: List[TimelineSegment] = []
    total_duration: float = 0.0
    render_settings: Dict[str, Any] = {}

class ProjectHistory(BaseModel):
    """Interaction history"""
    prompts: List[Dict[str, Any]] = []
    versions: List[Dict[str, Any]] = []
    feedback: List[Dict[str, Any]] = []

class ProjectStatus(BaseModel):
    """Current project status"""
    phase: str = "initialized"
    progress: float = 0.0
    current_version: int = 0
    error: Optional[str] = None
```

### 2.3 Tools Implementation

#### Visual Analysis Tool
```python
from google.adk.tools import tool
from google.generativeai import GenerativeModel
import base64
from typing import Dict, Any

@tool
async def visual_analysis_tool(
    file_path: str,
    analysis_type: str = "comprehensive"
) -> Dict[str, Any]:
    """
    Analyzes visual content using Gemini API.
    
    Args:
        file_path: Path to image or video file
        analysis_type: Type of analysis to perform
        
    Returns:
        Structured analysis results
    """
    try:
        model = GenerativeModel('gemini-2.0-flash')
        
        # Read and encode file
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
        
        # Structured prompt for consistent output
        prompt = """
        Analyze this media file and provide a JSON response with:
        {
            "description": "Brief description of content",
            "aesthetic_score": 0.0-1.0,
            "quality_issues": ["blur", "overexposed", etc],
            "main_subjects": ["person", "landscape", etc],
            "tags": ["sunset", "beach", "family", etc],
            "best_moment_timestamp": null or seconds for videos,
            "motion_level": "static", "slow", "medium", "fast" for videos
        }
        """
        
        response = await model.generate_content_async([
            {"mime_type": "image/jpeg", "data": content},
            prompt
        ])
        
        return {
            "status": "success",
            "result": json.loads(response.text)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

#### Audio Analysis Tool
```python
import librosa
import numpy as np
from typing import Dict, List, Any

@tool
def audio_analysis_tool(
    file_path: str,
    detailed: bool = True
) -> Dict[str, Any]:
    """
    Analyzes audio using Librosa library.
    
    Args:
        file_path: Path to audio file
        detailed: Whether to include detailed analysis
        
    Returns:
        Audio analysis profile
    """
    try:
        # Load audio
        y, sr = librosa.load(file_path)
        
        # Beat tracking
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        
        # Energy analysis using RMS
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        
        # Normalize energy curve
        energy = (rms - rms.min()) / (rms.max() - rms.min() + 1e-6)
        
        # High-level descriptors (if detailed)
        vibe = {}
        if detailed:
            # Spectral features for mood analysis
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            zero_crossings = librosa.feature.zero_crossing_rate(y)[0]
            
            # Simple energy-based danceability estimate
            danceability = float(np.mean(energy) * (tempo / 140.0))  # Normalize around 140 BPM
            danceability = min(1.0, max(0.0, danceability))
            
            # Simple mood estimation based on spectral features
            brightness = np.mean(spectral_centroids) / (sr / 2)
            if brightness > 0.6:
                mood = "happy"
            elif brightness > 0.4:
                mood = "neutral"
            else:
                mood = "calm"
            
            vibe = {
                "danceability": danceability,
                "energy": float(np.mean(energy)),
                "mood": mood
            }
        
        return {
            "status": "success",
            "result": {
                "beat_timestamps": beat_times.tolist(),
                "tempo_bpm": float(tempo),
                "energy_curve": energy.tolist(),
                "duration": len(y) / sr,
                "vibe": vibe
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### 2.4 Algorithms

#### Chronological Clustering Algorithm
```python
def cluster_media_chronologically(
    media_assets: List[MediaAsset],
    cluster_threshold: int = 3600  # 1 hour in seconds
) -> List[List[MediaAsset]]:
    """
    Groups media by capture time for narrative flow.
    """
    # Sort by timestamp
    sorted_media = sorted(
        media_assets,
        key=lambda x: x.metadata.get('capture_time', x.upload_timestamp)
    )
    
    clusters = []
    current_cluster = [sorted_media[0]]
    
    for i in range(1, len(sorted_media)):
        prev_time = sorted_media[i-1].metadata.get('capture_time')
        curr_time = sorted_media[i].metadata.get('capture_time')
        
        if (curr_time - prev_time).seconds > cluster_threshold:
            clusters.append(current_cluster)
            current_cluster = [sorted_media[i]]
        else:
            current_cluster.append(sorted_media[i])
    
    clusters.append(current_cluster)
    return clusters
```

#### Rhythmic Pacing Algorithm
```python
def generate_timeline_segments(
    media_pool: List[MediaAsset],
    music_profile: AudioAnalysisProfile,
    target_duration: int
) -> List[TimelineSegment]:
    """
    Creates timeline synchronized to music rhythm.
    """
    segments = []
    current_time = 0.0
    beat_index = 0
    
    # Calculate average clip duration based on tempo
    base_clip_duration = 60.0 / music_profile.tempo_bpm * 4  # 4 beats
    
    while current_time < target_duration and beat_index < len(music_profile.beat_timestamps):
        # Get current energy level
        energy_index = int(current_time / music_profile.duration * len(music_profile.energy_curve))
        current_energy = music_profile.energy_curve[min(energy_index, len(music_profile.energy_curve)-1)]
        
        # Adjust clip duration based on energy
        duration_multiplier = 1.5 - current_energy  # High energy = shorter clips
        clip_duration = base_clip_duration * duration_multiplier
        
        # Select media based on score
        selected_media = select_best_media(media_pool, current_energy)
        
        # Create segment
        segment = TimelineSegment(
            media_asset_id=selected_media.id,
            start_time=current_time,
            end_time=current_time + clip_duration,
            duration=clip_duration,
            in_point=0.0,
            out_point=clip_duration if selected_media.type == "video" else None
        )
        
        segments.append(segment)
        current_time += clip_duration
        
        # Advance to next beat marker
        while beat_index < len(music_profile.beat_timestamps) and \
              music_profile.beat_timestamps[beat_index] < current_time:
            beat_index += 1
    
    return segments
```

### 2.5 AI-Powered Edit Planning

The system now uses Gemini LLM to create intelligent edit plans before composition, enabling:
- Story-driven sequencing based on content understanding
- Musical structure awareness (intro/verse/chorus alignment)
- Energy-based pacing that matches visual content to audio dynamics
- Smooth transitions selected based on context

#### Edit Plan Models
```python
class PlannedSegment(BaseModel):
    """AI-planned segment with reasoning"""
    media_id: str
    start_time: float
    duration: float
    trim_start: float = 0.0
    trim_end: Optional[float] = None
    transition_type: str
    reasoning: str  # Why this clip was chosen
    story_beat: str  # e.g., "introduction", "climax"
    energy_match: float  # How well it matches music energy

class EditPlan(BaseModel):
    """Complete edit plan created by AI"""
    segments: List[PlannedSegment]
    total_duration: float
    narrative_structure: str
    pacing_strategy: str
    music_sync_notes: str
    variety_score: float
    story_coherence: float
    technical_quality: float
    reasoning_summary: str
```

#### Two-Phase Composition Process
1. **Planning Phase**: AI analyzes all media and music to create a detailed edit plan
2. **Execution Phase**: Convert the plan into a timeline with precise timing

This approach ensures videos have both technical precision (beat sync, smooth transitions) and creative coherence (story flow, emotional arc).

### 2.6 Storage Architecture

#### Storage Interface
```python
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

class StorageInterface(ABC):
    """Abstract storage interface for future cloud migration"""
    
    @abstractmethod
    async def upload(self, file_path: str, content: BinaryIO) -> str:
        """Upload file and return storage path"""
        pass
    
    @abstractmethod
    async def download(self, storage_path: str) -> BinaryIO:
        """Download file from storage"""
        pass
    
    @abstractmethod
    async def delete(self, storage_path: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Check if file exists"""
        pass

class FilesystemStorage(StorageInterface):
    """Local filesystem implementation"""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    async def upload(self, file_path: str, content: BinaryIO) -> str:
        target_path = self.base_path / file_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_path, 'wb') as f:
            f.write(content.read())
        
        return str(target_path)

class S3Storage(StorageInterface):
    """S3-compatible storage (future implementation)"""
    
    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix
    
    # Implementation for S3 operations
```

## 3. API Design

### 3.1 Agent Communication Protocol

All agents communicate through standardized message formats:

```python
class AgentMessage(BaseModel):
    """Standard message format between agents"""
    sender: str
    receiver: str
    action: str
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: str

class AgentResponse(BaseModel):
    """Standard response format"""
    status: Literal["success", "error", "pending"]
    result: Optional[Any]
    error: Optional[str]
    metadata: Dict[str, Any] = {}
```

### 3.2 Web API Endpoints

```python
from fastapi import FastAPI, UploadFile, BackgroundTasks
from typing import List

app = FastAPI()

@app.post("/projects/create")
async def create_project(
    media_files: List[UploadFile],
    music_file: UploadFile,
    prompt: str,
    settings: Dict[str, Any]
) -> ProjectResponse:
    """Create new video project"""
    pass

@app.get("/projects/{project_id}/status")
async def get_project_status(project_id: str) -> StatusResponse:
    """Get current project status"""
    pass

@app.post("/projects/{project_id}/refine")
async def refine_video(
    project_id: str,
    feedback: str
) -> RefinementResponse:
    """Submit refinement feedback"""
    pass

@app.get("/projects/{project_id}/download")
async def download_video(
    project_id: str,
    version: Optional[int] = None
) -> FileResponse:
    """Download generated video"""
    pass
```

## 4. Security Design

### 4.1 Input Validation

```python
class MediaValidator:
    """Validates uploaded media files"""
    
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/heic']
    ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/quicktime', 'video/x-msvideo']
    ALLOWED_AUDIO_TYPES = ['audio/mpeg', 'audio/mp4', 'audio/wav']
    
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_PROJECT_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
    
    @staticmethod
    def validate_file(file: UploadFile) -> ValidationResult:
        # Check file type
        if file.content_type not in (
            MediaValidator.ALLOWED_IMAGE_TYPES +
            MediaValidator.ALLOWED_VIDEO_TYPES +
            MediaValidator.ALLOWED_AUDIO_TYPES
        ):
            return ValidationResult(
                valid=False,
                error="Unsupported file type"
            )
        
        # Check file size
        if file.size > MediaValidator.MAX_FILE_SIZE:
            return ValidationResult(
                valid=False,
                error="File too large"
            )
        
        # Additional security checks
        # - Scan for malicious content
        # - Verify file headers match content type
        # - Check for path traversal attempts
        
        return ValidationResult(valid=True)
```

### 4.2 API Security

```python
from functools import wraps
import jwt

def require_api_key(f):
    """API key validation decorator"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or not validate_api_key(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")
        return await f(*args, **kwargs)
    return decorated_function

class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False
        
        self.requests[client_id].append(now)
        return True
```

## 5. Performance Optimization

### 5.1 Caching Strategy

```python
from functools import lru_cache
import hashlib

class AnalysisCache:
    """Caches expensive analysis results"""
    
    def __init__(self, storage: StorageInterface):
        self.storage = storage
        self.memory_cache = {}
    
    def get_cache_key(self, file_path: str, analysis_type: str) -> str:
        """Generate cache key based on file content"""
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        return f"{file_hash}_{analysis_type}"
    
    async def get(self, file_path: str, analysis_type: str) -> Optional[Any]:
        cache_key = self.get_cache_key(file_path, analysis_type)
        
        # Check memory cache
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        # Check persistent cache
        cache_path = f"cache/{cache_key}.json"
        if await self.storage.exists(cache_path):
            data = await self.storage.download(cache_path)
            result = json.loads(data.read())
            self.memory_cache[cache_key] = result
            return result
        
        return None
```

### 5.2 Parallel Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class BatchProcessor:
    """Processes multiple files in parallel"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_batch(
        self,
        files: List[str],
        process_func: Callable
    ) -> List[Any]:
        """Process files in parallel"""
        tasks = []
        
        for file in files:
            task = asyncio.create_task(
                self.process_single(file, process_func)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Processing failed: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
```

## 6. Testing Strategy

### 6.1 Unit Testing

```python
import pytest
from unittest.mock import Mock, patch

class TestAnalysisAgent:
    """Unit tests for AnalysisAgent"""
    
    @pytest.fixture
    def agent(self):
        return AnalysisAgent()
    
    @pytest.fixture
    def mock_gemini(self):
        with patch('google.generativeai.GenerativeModel') as mock:
            yield mock
    
    async def test_visual_analysis(self, agent, mock_gemini):
        # Setup mock
        mock_response = Mock()
        mock_response.text = json.dumps({
            "description": "Test image",
            "aesthetic_score": 0.8
        })
        mock_gemini.return_value.generate_content_async.return_value = mock_response
        
        # Test
        result = await agent.analyze_visual("test.jpg")
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["aesthetic_score"] == 0.8
```

### 6.2 Integration Testing

```python
class TestVideoCreationWorkflow:
    """End-to-end workflow tests"""
    
    @pytest.fixture
    def test_media(self):
        """Fixture providing test media files"""
        return {
            "images": ["tests/fixtures/image1.jpg", "tests/fixtures/image2.jpg"],
            "videos": ["tests/fixtures/video1.mp4"],
            "music": "tests/fixtures/music.mp3"
        }
    
    async def test_complete_workflow(self, test_media):
        # Create project
        project = await create_project(
            media_files=test_media["images"] + test_media["videos"],
            music_file=test_media["music"],
            prompt="Create a 1-minute upbeat video"
        )
        
        # Wait for processing
        while project.status.phase != "completed":
            await asyncio.sleep(1)
            project = await get_project(project.project_id)
        
        # Verify output
        assert project.timeline.total_duration == pytest.approx(60.0, rel=0.1)
        assert len(project.timeline.segments) > 0
        assert project.status.error is None
```

## 7. Deployment Architecture

### 7.1 Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
      - STORAGE_TYPE=filesystem
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### 7.2 Cloud Deployment (Future)

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memory-movie-maker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: memory-movie-maker
  template:
    metadata:
      labels:
        app: memory-movie-maker
    spec:
      containers:
      - name: app
        image: gcr.io/project/memory-movie-maker:latest
        env:
        - name: STORAGE_TYPE
          value: "s3"
        - name: S3_BUCKET
          value: "memory-movie-media"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

## 8. Monitoring and Observability

### 8.1 Logging

```python
import structlog

logger = structlog.get_logger()

class StructuredLogger:
    """Structured logging for better observability"""
    
    @staticmethod
    def log_agent_action(
        agent_name: str,
        action: str,
        project_id: str,
        **kwargs
    ):
        logger.info(
            "agent_action",
            agent=agent_name,
            action=action,
            project_id=project_id,
            **kwargs
        )
    
    @staticmethod
    def log_performance(
        operation: str,
        duration: float,
        **kwargs
    ):
        logger.info(
            "performance",
            operation=operation,
            duration_ms=duration * 1000,
            **kwargs
        )
```

### 8.2 Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
video_generation_counter = Counter(
    'video_generations_total',
    'Total number of videos generated'
)

generation_duration_histogram = Histogram(
    'video_generation_duration_seconds',
    'Time taken to generate videos'
)

active_projects_gauge = Gauge(
    'active_projects',
    'Number of currently active projects'
)
```

## 9. Error Handling

### 9.1 Agent Error Recovery

```python
class AgentErrorHandler:
    """Handles agent failures gracefully"""
    
    @staticmethod
    async def with_retry(
        func: Callable,
        max_attempts: int = 3,
        backoff_factor: float = 2.0
    ):
        """Retry failed operations with exponential backoff"""
        for attempt in range(max_attempts):
            try:
                return await func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                
                wait_time = backoff_factor ** attempt
                logger.warning(
                    "Operation failed, retrying",
                    attempt=attempt + 1,
                    wait_time=wait_time,
                    error=str(e)
                )
                await asyncio.sleep(wait_time)
```

## 10. Cost Estimation and Optimization

### 10.1 API Cost Estimates

#### Gemini API Costs (as of 2025)
```
Visual Analysis:
- Image analysis: ~$0.0001 per image
- Video analysis: ~$0.001 per minute of video
- Text generation: ~$0.00001 per 1K characters

Typical Project (2-minute video):
- 50 photos analyzed: $0.005
- 10 video clips (30s each): $0.005
- Multiple critique/refinement cycles: $0.002
- Total estimated cost: ~$0.01-0.02 per video
```

#### Cost Optimization Strategies

1. **Caching**
   - Cache all analysis results by file hash
   - Reuse analysis for duplicate media
   - Cache validity: 30 days

2. **Batch Processing**
   - Group API calls to reduce overhead
   - Use batch endpoints where available

3. **Progressive Analysis**
   - Analyze only visible timeline segments first
   - Defer analysis of unused media

4. **Quality Tiers**
   - Use faster/cheaper models for initial drafts
   - Reserve premium models for final output

### 10.2 Performance Benchmarks

```
Target Performance Metrics:
- Media analysis: 1-2 seconds per file
- Music analysis: 3-5 seconds per track
- Timeline generation: <10 seconds
- Video rendering: 1-2x real-time
- Total initial generation: <5 minutes for 2-minute video
```

## 11. Future Considerations

### 10.1 Scalability Enhancements
- Implement distributed task queue (Celery/RabbitMQ)
- Add horizontal scaling for agents
- Implement result caching with Redis
- Use CDN for media delivery

### 10.2 Feature Extensions
- Multi-language support with i18n
- Real-time collaboration with WebSockets
- Advanced effects engine
- AI-generated music integration

### 10.3 Performance Optimizations
- GPU acceleration for rendering
- Streaming video processing
- Predictive caching
- Edge deployment for global users