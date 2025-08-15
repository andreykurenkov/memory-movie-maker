# API Reference

This document provides comprehensive documentation for Memory Movie Maker's key interfaces, data models, and agent APIs.

## Core Data Models

All data models use Pydantic for validation and serialization. They are defined in `src/memory_movie_maker/models/`.

### MediaAsset (`media_asset.py`)

Represents a single media file (photo, video, or audio) with analysis results.

```python
class MediaAsset(BaseModel):
    """Represents a media file with analysis metadata."""
    
    # Core attributes
    id: str = Field(..., description="Unique identifier (UUID)")
    path: str = Field(..., description="File path")
    type: MediaType = Field(..., description="image/video/audio")
    size: int = Field(..., ge=0, description="File size in bytes")
    duration: Optional[float] = Field(None, description="Duration in seconds (video/audio)")
    
    # Analysis results
    geminiAnalysis: Optional[GeminiAnalysis] = Field(None, description="AI visual analysis")
    audioAnalysis: Optional[AudioAnalysisProfile] = Field(None, description="Technical audio analysis")
    semanticAudioAnalysis: Optional[SemanticAudioAnalysis] = Field(None, description="AI audio understanding")
```

#### GeminiAnalysis

AI-powered visual analysis from Gemini.

```python
class GeminiAnalysis(BaseModel):
    """Visual analysis results from Gemini API."""
    
    description: str = Field(..., description="Overall content description")
    aesthetic_score: float = Field(..., ge=0, le=1, description="Visual quality score")
    notable_segments: List[VideoSegment] = Field(default=[], description="Key moments in video")
    
    # Content classification
    dominant_colors: List[str] = Field(default=[], description="Primary colors present")
    subjects: List[str] = Field(default=[], description="People, objects, or scenes")
    setting: Optional[str] = Field(None, description="Location or environment")
    
    # Technical quality
    lighting_quality: Optional[str] = Field(None, description="good/fair/poor")
    composition_score: Optional[float] = Field(None, ge=0, le=1)
    blur_detected: Optional[bool] = Field(None, description="Whether image is blurry")
```

#### AudioAnalysisProfile

Technical audio analysis using Librosa.

```python
class AudioAnalysisProfile(BaseModel):
    """Technical audio analysis results."""
    
    # Basic properties
    duration: float = Field(..., ge=0, description="Duration in seconds")
    sample_rate: int = Field(..., gt=0, description="Sample rate in Hz")
    
    # Musical structure
    tempo: float = Field(..., gt=0, description="Beats per minute")
    beats: List[float] = Field(..., description="Beat timestamps in seconds")
    musical_segments: List[MusicalSegment] = Field(..., description="Song structure")
    
    # Energy and dynamics
    energy_curve: List[float] = Field(..., description="Energy levels over time")
    rms_energy: List[float] = Field(..., description="RMS energy curve")
    
    # Musical characteristics
    danceability: float = Field(..., ge=0, le=1, description="How suitable for dancing")
    valence: float = Field(..., ge=0, le=1, description="Musical positivity")
    energy: float = Field(..., ge=0, le=1, description="Overall energy level")
```

#### MusicalSegment

Represents a structural section of music (intro, verse, chorus, etc.).

```python
class MusicalSegment(BaseModel):
    """A structural segment of music."""
    
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., ge=0, description="End time in seconds")
    segment_type: str = Field(..., description="intro/verse/chorus/bridge/outro")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    characteristics: Dict[str, Any] = Field(default={}, description="Additional properties")
```

### Timeline (`timeline.py`)

Represents the final video timeline with synchronized segments.

```python
class Timeline(BaseModel):
    """Video timeline with synchronized segments."""
    
    segments: List[TimelineSegment] = Field(..., description="Ordered video segments")
    music_asset_id: Optional[str] = Field(None, description="Background music track")
    total_duration: float = Field(..., gt=0, description="Total video duration")
    target_duration: float = Field(..., gt=0, description="Requested duration")
    
class TimelineSegment(BaseModel):
    """Single segment in the video timeline."""
    
    # Media reference
    media_asset_id: str = Field(..., description="Reference to MediaAsset")
    
    # Timing
    start_time: float = Field(..., ge=0, description="Start in timeline")
    duration: float = Field(..., gt=0, description="Segment duration")
    
    # Media trimming (for videos)
    in_point: float = Field(default=0, ge=0, description="Start time in source media")
    out_point: Optional[float] = Field(None, description="End time in source media")
    
    # Effects and transitions
    effects: List[str] = Field(default=[], description="Applied effects")
    transition_in: Optional[str] = Field(None, description="Incoming transition")
    transition_out: Optional[str] = Field(None, description="Outgoing transition")
```

### EditPlan (`edit_plan.py`)

AI-generated plan for video composition.

```python
class EditPlan(BaseModel):
    """AI-generated plan for video composition."""
    
    # Story structure
    story_arc: str = Field(..., description="Overall narrative approach")
    pacing_style: str = Field(..., description="fast/medium/slow")
    emotional_journey: str = Field(..., description="Emotional progression")
    
    # Technical specifications
    target_duration: float = Field(..., gt=0)
    style_preferences: Dict[str, Any] = Field(default={})
    
    # Media selection and ordering
    selected_segments: List[SelectedSegment] = Field(..., description="Chosen media segments")
    variety_score: float = Field(..., ge=0, le=1, description="Content diversity measure")
    
    # Music synchronization
    sync_points: List[SyncPoint] = Field(default=[], description="Key synchronization moments")
    transition_style: str = Field(default="smooth", description="Transition approach")

class SelectedSegment(BaseModel):
    """A media segment selected for the final video."""
    
    media_asset_id: str = Field(..., description="Source media reference")
    reason: str = Field(..., description="Why this segment was chosen")
    priority: float = Field(..., ge=0, le=1, description="Importance score")
    
    # Timing within source media
    source_start: float = Field(default=0, ge=0)
    source_duration: float = Field(..., gt=0)
    
    # Planned position in timeline
    timeline_position: float = Field(..., ge=0)
    timeline_duration: float = Field(..., gt=0)
```

## Agent APIs

### RootAgent (`root_agent.py`)

Main orchestrator and user interface.

```python
class RootAgent:
    """Root agent that orchestrates the video creation workflow."""
    
    async def create_memory_movie(
        self,
        media_paths: List[str],
        user_prompt: str,
        music_path: Optional[str] = None,
        target_duration: int = 60,
        style: str = "balanced",
        auto_refine: bool = True
    ) -> Dict[str, Any]:
        """Create a memory movie from media files.
        
        Args:
            media_paths: List of photo/video file paths
            user_prompt: Natural language description of desired video
            music_path: Optional background music file
            target_duration: Desired video length in seconds
            style: Editing style (fast/balanced/slow/smooth/energetic)
            auto_refine: Whether to automatically improve video quality
            
        Returns:
            {
                "video_path": str,           # Path to generated video
                "timeline": Timeline,        # Final timeline used
                "quality_score": float,      # Final quality score (1-10)
                "iterations": int,           # Number of refinement cycles
                "analysis_results": dict     # Media analysis summary
            }
        """
    
    async def refine_video(
        self,
        project_id: str,
        feedback: str
    ) -> Dict[str, Any]:
        """Apply user feedback to improve an existing video.
        
        Args:
            project_id: ID of existing project
            feedback: Natural language feedback ("make it faster", etc.)
            
        Returns:
            Updated video with same structure as create_memory_movie()
        """
```

### AnalysisAgent (`analysis_agent.py`)

Media content analysis and understanding.

```python
class AnalysisAgent(LlmAgent):
    """Agent for analyzing media content."""
    
    async def analyze_media_batch(
        self,
        media_assets: List[MediaAsset]
    ) -> List[MediaAsset]:
        """Analyze multiple media files concurrently.
        
        Args:
            media_assets: List of media files to analyze
            
        Returns:
            Same list with analysis results populated
        """
    
    async def analyze_single_media(
        self,
        media_asset: MediaAsset
    ) -> MediaAsset:
        """Analyze a single media file.
        
        Automatically determines analysis type based on media type:
        - Images: Visual analysis with Gemini
        - Videos: Visual + audio analysis with Gemini + Librosa  
        - Audio: Technical + semantic analysis with Librosa + Gemini
        
        Args:
            media_asset: Media file to analyze
            
        Returns:
            Media asset with analysis results
        """
```

### CompositionAgent (`composition_agent.py`)

AI-powered video creation and rendering.

```python
class CompositionAgent(LlmAgent):
    """Agent for creating and rendering videos."""
    
    async def create_video(
        self,
        media_assets: List[MediaAsset],
        user_prompt: str,
        music_asset: Optional[MediaAsset] = None,
        target_duration: int = 60,
        style_preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a video from analyzed media.
        
        Process:
        1. Generate edit plan using AI
        2. Build beat-synchronized timeline
        3. Render video with MoviePy
        
        Args:
            media_assets: Analyzed media files
            user_prompt: User's creative direction
            music_asset: Optional background music
            target_duration: Desired video length
            style_preferences: Style settings (pacing, transitions, etc.)
            
        Returns:
            {
                "video_path": str,
                "timeline": Timeline,
                "edit_plan": EditPlan,
                "render_stats": dict
            }
        """
```

### EvaluationAgent (`evaluation_agent.py`)

Video quality assessment and improvement suggestions.

```python
class EvaluationAgent(LlmAgent):
    """Agent for evaluating video quality."""
    
    async def evaluate_video(
        self,
        video_path: str,
        timeline: Timeline,
        edit_plan: EditPlan,
        user_prompt: str
    ) -> VideoEvaluation:
        """Evaluate video quality and suggest improvements.
        
        Args:
            video_path: Path to rendered video
            timeline: Timeline used to create video
            edit_plan: Original edit plan
            user_prompt: User's original request
            
        Returns:
            VideoEvaluation with score and improvement suggestions
        """

class VideoEvaluation(BaseModel):
    """Video quality evaluation results."""
    
    overall_score: float = Field(..., ge=1, le=10, description="Overall quality score")
    
    # Component scores
    story_coherence: float = Field(..., ge=1, le=10)
    pacing_quality: float = Field(..., ge=1, le=10)
    music_sync: float = Field(..., ge=1, le=10)
    transition_smoothness: float = Field(..., ge=1, le=10)
    
    # Improvement suggestions
    strengths: List[str] = Field(..., description="What works well")
    areas_for_improvement: List[str] = Field(..., description="Specific issues to address")
    suggested_changes: List[str] = Field(..., description="Actionable improvement steps")
    
    # Decision support
    needs_refinement: bool = Field(..., description="Whether refinement is recommended")
    confidence: float = Field(..., ge=0, le=1, description="Evaluation confidence")
```

### RefinementAgent (`refinement_agent.py`)

Feedback interpretation and edit command generation.

```python
class RefinementAgent(LlmAgent):
    """Agent for interpreting feedback and generating refinements."""
    
    async def parse_feedback(
        self,
        feedback: str,
        current_timeline: Timeline,
        evaluation: VideoEvaluation
    ) -> RefinementCommands:
        """Parse natural language feedback into edit commands.
        
        Args:
            feedback: User feedback or evaluation suggestions
            current_timeline: Current video timeline
            evaluation: Current quality evaluation
            
        Returns:
            Structured commands for timeline modification
        """

class RefinementCommands(BaseModel):
    """Structured commands for video refinement."""
    
    # Global changes
    pacing_adjustment: Optional[float] = Field(None, description="Speed multiplier")
    style_changes: Dict[str, Any] = Field(default={}, description="Style modifications")
    
    # Segment-level changes
    segment_modifications: List[SegmentModification] = Field(default=[])
    
    # Content changes
    content_additions: List[str] = Field(default=[], description="Media to add")
    content_removals: List[str] = Field(default=[], description="Media to remove")
    
    # Technical adjustments
    transition_changes: Dict[str, str] = Field(default={}, description="Transition updates")
    effect_changes: Dict[str, List[str]] = Field(default={}, description="Effect modifications")
```

## Tool APIs

### Key Tools

Tools are functions that agents can call to perform specific tasks.

#### Visual Analysis Tool (`visual_analysis.py`)

```python
@tool
async def visual_analysis_tool(file_path: str) -> Dict[str, Any]:
    """Analyze visual content using Gemini API.
    
    Args:
        file_path: Path to image or video file
        
    Returns:
        Dictionary with analysis results matching GeminiAnalysis schema
    """
```

#### Audio Analysis Tool (`audio_analysis.py`)

```python
@tool
async def audio_analysis_tool(file_path: str) -> Dict[str, Any]:
    """Analyze audio technical features using Librosa.
    
    Args:
        file_path: Path to audio file (or video with audio)
        
    Returns:
        Dictionary with analysis results matching AudioAnalysisProfile schema
    """
```

#### Edit Planner Tool (`edit_planner.py`)

```python
@tool
async def plan_edit_tool(
    media_assets: List[MediaAsset],
    user_prompt: str,
    music_profile: Optional[AudioAnalysisProfile],
    target_duration: int,
    style_preferences: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate AI edit plan for video composition.
    
    Uses Gemini to create intelligent edit plan considering:
    - User creative intent
    - Media content and quality
    - Music structure and rhythm
    - Pacing and storytelling principles
    
    Returns:
        Dictionary matching EditPlan schema
    """
```

#### Video Renderer Tool (`video_renderer.py`)

```python
@tool
async def render_video_tool(
    timeline: Timeline,
    media_assets: List[MediaAsset],
    output_path: str,
    music_asset: Optional[MediaAsset] = None
) -> Dict[str, Any]:
    """Render final video using MoviePy.
    
    Args:
        timeline: Video timeline with segments and timing
        media_assets: Source media files
        output_path: Where to save rendered video
        music_asset: Optional background music
        
    Returns:
        {
            "success": bool,
            "output_path": str,
            "duration": float,
            "file_size": int,
            "render_time": float
        }
    """
```

## Error Handling

All APIs use consistent error handling patterns:

```python
class MemoryMovieMakerError(Exception):
    """Base exception for Memory Movie Maker."""
    pass

class MediaAnalysisError(MemoryMovieMakerError):
    """Error during media analysis."""
    pass

class CompositionError(MemoryMovieMakerError):
    """Error during video composition."""
    pass

class RenderingError(MemoryMovieMakerError):
    """Error during video rendering."""
    pass
```

## Usage Examples

### Basic Video Creation

```python
from memory_movie_maker.agents.root_agent import RootAgent

# Initialize agent
agent = RootAgent()

# Create video
result = await agent.create_memory_movie(
    media_paths=["photo1.jpg", "photo2.jpg", "video1.mp4"],
    user_prompt="Create a fun birthday party video",
    music_path="happy_song.mp3",
    target_duration=60,
    style="energetic"
)

print(f"Video created: {result['video_path']}")
print(f"Quality score: {result['quality_score']}")
```

### Manual Analysis

```python
from memory_movie_maker.agents.analysis_agent import AnalysisAgent
from memory_movie_maker.models.media_asset import MediaAsset

# Create media asset
media = MediaAsset(
    id="test-123",
    path="vacation_video.mp4",
    type="video",
    size=15000000
)

# Analyze
agent = AnalysisAgent()
analyzed_media = await agent.analyze_single_media(media)

print(f"Visual analysis: {analyzed_media.geminiAnalysis.description}")
print(f"Audio tempo: {analyzed_media.audioAnalysis.tempo} BPM")
```

### Custom Refinement

```python
# Get feedback and apply refinements
feedback = "Make the video faster and add more transitions"

refined_result = await agent.refine_video(
    project_id="my-project-123",
    feedback=feedback
)

print(f"Refined video: {refined_result['video_path']}")
print(f"New quality score: {refined_result['quality_score']}")
```

This API reference provides comprehensive documentation for integrating with and extending Memory Movie Maker's capabilities.