# Agent Architecture Guide

This document provides in-depth technical documentation of Memory Movie Maker's multi-agent architecture, agent responsibilities, and communication patterns.

## Architecture Overview

Memory Movie Maker implements a **sequential multi-agent architecture** using Google's Agent Development Kit (ADK). Unlike traditional LLM-based orchestration, the system uses deterministic control flow for reliability and predictability.

### Design Principles

1. **Single Responsibility**: Each agent has a clearly defined, focused purpose
2. **Sequential Processing**: Agents run in a predetermined order, not concurrently
3. **Deterministic Orchestration**: RootAgent uses logic-based routing, not LLM decisions
4. **Stateful Communication**: Agents communicate through shared ProjectState
5. **Self-Correction**: Built-in quality feedback loop with autonomous refinement

### Agent Interaction Flow

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User      │    │   RootAgent     │    │ AnalysisAgent   │
│  Request    │───▶│  (Orchestrator) │───▶│   (Content)     │
└─────────────┘    └─────────────────┘    └─────────────────┘
                           │                        │
                           ▼                        ▼
                   ┌─────────────────┐    ┌─────────────────┐
                   │CompositionAgent │◀───┤   ProjectState  │
                   │   (Creation)    │    │   (Shared)      │
                   └─────────────────┘    └─────────────────┘
                           │                        ▲
                           ▼                        │
                   ┌─────────────────┐              │
                   │EvaluationAgent  │              │
                   │   (Quality)     │              │
                   └─────────────────┘              │
                           │                        │
                           ▼                        │
                   ┌─────────────────┐              │
                   │RefinementAgent  │──────────────┘
                   │  (Improvement)  │
                   └─────────────────┘
```

## Agent Specifications

### 1. RootAgent 🎯

**File**: `src/memory_movie_maker/agents/root_agent.py`

#### Purpose
Central orchestrator that manages the entire video creation workflow. Provides the main user interface and coordinates agent execution.

#### Key Characteristics
- **No LLM**: Uses deterministic logic for reliable orchestration
- **Stateful**: Maintains ProjectState throughout the workflow
- **User Interface**: Primary API for external interactions
- **Error Handling**: Comprehensive error recovery and user feedback

#### Core Responsibilities

```python
class RootAgent:
    """Root agent orchestrating video creation workflow."""
    
    async def create_memory_movie(self, ...):
        """Main entry point for video creation."""
        # 1. Initialize project state
        # 2. Validate inputs and setup storage
        # 3. Run analysis phase
        # 4. Run composition phase  
        # 5. Run evaluation phase
        # 6. Run refinement phase (if needed)
        # 7. Return final results
    
    async def refine_video(self, project_id: str, feedback: str):
        """Apply user feedback to existing video."""
        # 1. Load existing project state
        # 2. Parse feedback with RefinementAgent
        # 3. Re-run composition with modifications
        # 4. Re-evaluate and potentially refine again
```

#### Decision Logic

The RootAgent uses **explicit decision trees** rather than LLM reasoning:

```python
# Phase transition logic
if project_state.status.phase == "analysis":
    if all_media_analyzed(project_state):
        project_state.status.phase = "composition"
    else:
        await run_analysis_agent()

elif project_state.status.phase == "composition":
    result = await run_composition_agent()
    if result["success"]:
        project_state.status.phase = "evaluation"
    else:
        raise CompositionError("Failed to create video")

elif project_state.status.phase == "evaluation":
    evaluation = await run_evaluation_agent()
    if evaluation.overall_score >= 7.0 or iteration_count >= 3:
        project_state.status.phase = "completed"
    else:
        project_state.status.phase = "refinement"
```

#### State Management

```python
class ProjectState(BaseModel):
    """Shared state across all agents."""
    
    # Workflow tracking
    status: ProjectStatus
    iteration_count: int = 0
    max_iterations: int = 3
    
    # Input data
    user_inputs: UserInputs
    
    # Analysis results
    analyzed_media: List[MediaAsset]
    
    # Composition outputs
    current_timeline: Optional[Timeline]
    current_video_path: Optional[str]
    
    # Evaluation results
    current_evaluation: Optional[VideoEvaluation]
    
    # Settings and preferences
    settings: ProjectSettings
```

### 2. AnalysisAgent 🔍

**File**: `src/memory_movie_maker/agents/analysis_agent.py`

#### Purpose
Extracts comprehensive content and technical metadata from all media files using multiple AI and signal processing approaches.

#### Architecture: Multi-Modal Analysis Pipeline

```
Media Input
    │
    ├─ Image ──┐
    │          ├──▶ Gemini Visual Analysis ──▶ GeminiAnalysis
    ├─ Video ──┤
    │          └──▶ Gemini Video+Audio Analysis ──▶ VideoSegments
    │
    └─ Audio ──┐
               ├──▶ Librosa Technical Analysis ──▶ AudioAnalysisProfile  
               └──▶ Gemini Semantic Analysis ──▶ SemanticAudioAnalysis
```

#### Core Tools Integration

The AnalysisAgent coordinates three specialized analysis tools:

```python
class AnalysisAgent(LlmAgent):
    """Agent for comprehensive media analysis."""
    
    def __init__(self):
        super().__init__(
            name="AnalysisAgent",
            model="gemini-2.0-flash",
            description="Analyzes media content for intelligent video composition",
            instruction=self._build_analysis_instruction(),
            tools=[
                visual_analysis_tool,           # Gemini-powered visual understanding
                audio_analysis_tool,            # Librosa technical audio analysis  
                semantic_audio_analysis_tool    # Gemini-powered audio understanding
            ]
        )
```

#### Analysis Workflow

```python
async def analyze_media_batch(self, media_assets: List[MediaAsset]) -> List[MediaAsset]:
    """Concurrent analysis of multiple media files."""
    
    # Group by analysis type for efficiency
    images = [m for m in media_assets if m.type == "image"]
    videos = [m for m in media_assets if m.type == "video"] 
    audio_files = [m for m in media_assets if m.type == "audio"]
    
    # Run analyses concurrently
    tasks = []
    
    # Visual analysis for images and videos
    for media in images + videos:
        tasks.append(self._analyze_visual_content(media))
    
    # Audio analysis for audio files and videos
    for media in audio_files + videos:
        tasks.append(self._analyze_audio_content(media))
    
    # Wait for all analyses to complete
    await asyncio.gather(*tasks)
    
    return media_assets
```

#### Quality Assurance

The AnalysisAgent includes built-in quality checks:

```python
def _validate_analysis_results(self, media_asset: MediaAsset) -> bool:
    """Ensure analysis results meet quality standards."""
    
    if media_asset.type in ["image", "video"]:
        if not media_asset.geminiAnalysis:
            return False
        if not media_asset.geminiAnalysis.description:
            return False
        if media_asset.geminiAnalysis.aesthetic_score < 0 or media_asset.geminiAnalysis.aesthetic_score > 1:
            return False
    
    if media_asset.type in ["audio", "video"]:
        if not media_asset.audioAnalysis:
            return False
        if not media_asset.audioAnalysis.beats:
            return False
        if media_asset.audioAnalysis.tempo <= 0:
            return False
    
    return True
```

### 3. CompositionAgent 🎬

**File**: `src/memory_movie_maker/agents/composition_agent.py`

#### Purpose
Creates videos using AI-powered edit planning combined with precise technical execution. This agent bridges creative AI decisions with technical video rendering.

#### Two-Phase Architecture

```
Phase 1: AI Edit Planning (Gemini)
    │
    ├─ Story Structure Analysis
    ├─ Content Selection Logic  
    ├─ Pacing Strategy
    └─ Music Synchronization Planning
    │
    ▼
Phase 2: Technical Execution (Deterministic)
    │
    ├─ Beat-Synchronized Timeline Building
    ├─ Precise Clip Trimming and Positioning
    ├─ Effect and Transition Application
    └─ Video Rendering with MoviePy
```

#### Edit Planning Engine

The CompositionAgent uses sophisticated AI planning:

```python
class EditPlanner:
    """AI-powered edit planning system."""
    
    async def plan_edit(
        self,
        media_assets: List[MediaAsset],
        music_profile: Optional[AudioAnalysisProfile],
        target_duration: int,
        user_prompt: str,
        style_preferences: Dict[str, Any]
    ) -> EditPlan:
        """Generate comprehensive edit plan using Gemini."""
        
        # Build context for AI planning
        context = self._build_planning_context(
            media_assets, music_profile, user_prompt
        )
        
        # AI generates structured edit plan
        plan = await self._generate_edit_plan_with_ai(context)
        
        # Validate and adjust plan
        validated_plan = self._validate_and_adjust_plan(plan, media_assets)
        
        return validated_plan
```

#### Music Synchronization Engine

Advanced beat-synchronization system:

```python
class BeatSynchronizer:
    """Synchronizes video cuts to music beats."""
    
    def synchronize_timeline_to_music(
        self,
        edit_plan: EditPlan,
        music_profile: AudioAnalysisProfile
    ) -> Timeline:
        """Create beat-synchronized timeline."""
        
        # Map edit plan segments to musical structure
        segment_mapping = self._map_segments_to_music_structure(
            edit_plan.selected_segments,
            music_profile.musical_segments
        )
        
        # Align cuts to beat grid
        beat_aligned_timeline = self._align_cuts_to_beats(
            segment_mapping,
            music_profile.beats
        )
        
        # Apply micro-timing adjustments
        final_timeline = self._apply_timing_refinements(beat_aligned_timeline)
        
        return final_timeline
```

#### Rendering Pipeline

```python
class VideoRenderer:
    """High-quality video rendering with MoviePy."""
    
    async def render_timeline(
        self,
        timeline: Timeline,
        media_assets: List[MediaAsset],
        output_path: str
    ) -> Dict[str, Any]:
        """Render final video from timeline."""
        
        # Load and prepare all media clips
        clips = await self._load_media_clips(timeline, media_assets)
        
        # Apply effects and transitions
        processed_clips = await self._apply_effects_and_transitions(clips, timeline)
        
        # Composite final video
        final_video = self._composite_video(processed_clips)
        
        # Add background music with sync
        if timeline.music_asset_id:
            final_video = await self._add_synchronized_music(final_video, timeline)
        
        # Render to file
        render_stats = await self._render_to_file(final_video, output_path)
        
        return render_stats
```

### 4. EvaluationAgent 📊

**File**: `src/memory_movie_maker/agents/evaluation_agent.py`

#### Purpose
Provides objective quality assessment and specific improvement recommendations for generated videos.

#### Multi-Dimensional Quality Model

```python
class QualityAssessmentFramework:
    """Comprehensive video quality evaluation."""
    
    EVALUATION_DIMENSIONS = {
        "story_coherence": {
            "weight": 0.25,
            "criteria": ["narrative_flow", "content_relevance", "emotional_arc"]
        },
        "pacing_quality": {
            "weight": 0.25, 
            "criteria": ["rhythm_variation", "energy_progression", "timing_precision"]
        },
        "music_sync": {
            "weight": 0.25,
            "criteria": ["beat_alignment", "energy_matching", "transition_timing"]
        },
        "technical_quality": {
            "weight": 0.25,
            "criteria": ["transition_smoothness", "effect_quality", "overall_polish"]
        }
    }
```

#### Evaluation Process

```python
async def evaluate_video(
    self,
    video_path: str,
    timeline: Timeline,
    edit_plan: EditPlan,
    user_prompt: str
) -> VideoEvaluation:
    """Comprehensive video quality evaluation."""
    
    # Technical analysis
    technical_metrics = await self._analyze_technical_quality(video_path, timeline)
    
    # Content analysis with AI
    content_assessment = await self._assess_content_quality(
        video_path, edit_plan, user_prompt
    )
    
    # Music synchronization analysis
    sync_quality = await self._evaluate_music_sync(video_path, timeline)
    
    # Aggregate scores and generate insights
    final_evaluation = self._synthesize_evaluation(
        technical_metrics, content_assessment, sync_quality
    )
    
    return final_evaluation
```

#### Improvement Suggestion Engine

```python
class ImprovementEngine:
    """Generates specific, actionable improvement suggestions."""
    
    def generate_improvement_suggestions(
        self,
        evaluation: VideoEvaluation,
        timeline: Timeline,
        edit_plan: EditPlan
    ) -> List[str]:
        """Create specific improvement recommendations."""
        
        suggestions = []
        
        # Story and pacing improvements
        if evaluation.story_coherence < 7.0:
            suggestions.extend(self._suggest_story_improvements(timeline, edit_plan))
        
        # Music sync improvements  
        if evaluation.music_sync < 7.0:
            suggestions.extend(self._suggest_sync_improvements(timeline))
        
        # Technical improvements
        if evaluation.transition_smoothness < 7.0:
            suggestions.extend(self._suggest_technical_improvements(timeline))
        
        return suggestions
```

### 5. RefinementAgent 🔧

**File**: `src/memory_movie_maker/agents/refinement_agent.py`

#### Purpose
Interprets quality feedback and user requests, translating them into specific, actionable edit commands for video improvement.

#### Natural Language Processing Pipeline

```python
class FeedbackParser:
    """Advanced natural language feedback interpretation."""
    
    FEEDBACK_CATEGORIES = {
        "pacing": ["faster", "slower", "speed up", "slow down", "rushed", "dragging"],
        "content": ["more", "less", "add", "remove", "include", "exclude"],
        "style": ["upbeat", "calm", "energetic", "smooth", "dramatic", "subtle"],
        "transitions": ["smoother", "sharper", "fade", "cut", "blend"],
        "music": ["sync", "beat", "rhythm", "volume", "timing"]
    }
    
    async def parse_feedback(
        self,
        feedback: str,
        current_state: ProjectState
    ) -> RefinementCommands:
        """Parse natural language feedback into structured commands."""
        
        # Extract intent and parameters
        intent_analysis = await self._analyze_user_intent(feedback)
        
        # Map to specific edit commands
        commands = self._translate_intent_to_commands(
            intent_analysis, current_state
        )
        
        # Validate commands against current timeline
        validated_commands = self._validate_commands(commands, current_state)
        
        return validated_commands
```

#### Command Generation System

```python
class CommandGenerator:
    """Generates specific edit commands from feedback analysis."""
    
    def generate_pacing_commands(
        self,
        feedback_analysis: dict,
        current_timeline: Timeline
    ) -> List[EditCommand]:
        """Generate pacing-related edit commands."""
        
        commands = []
        
        if "faster" in feedback_analysis["keywords"]:
            # Reduce segment durations by 15-25%
            commands.append(EditCommand(
                type="adjust_pacing",
                target="all_segments", 
                parameters={"speed_multiplier": 1.2}
            ))
            
            # Increase cut frequency
            commands.append(EditCommand(
                type="increase_cuts",
                parameters={"frequency_multiplier": 1.3}
            ))
        
        elif "slower" in feedback_analysis["keywords"]:
            # Extend segment durations
            commands.append(EditCommand(
                type="adjust_pacing",
                target="all_segments",
                parameters={"speed_multiplier": 0.8}
            ))
            
            # Add more gradual transitions
            commands.append(EditCommand(
                type="modify_transitions",
                parameters={"style": "gradual", "duration_multiplier": 1.4}
            ))
        
        return commands
```

#### Integration with CompositionAgent

```python
async def apply_refinements(
    self,
    commands: RefinementCommands,
    current_timeline: Timeline,
    media_assets: List[MediaAsset]
) -> Timeline:
    """Apply refinement commands to create improved timeline."""
    
    # Create modified timeline
    modified_timeline = self._apply_timeline_modifications(
        current_timeline, commands
    )
    
    # Re-run composition with modifications
    composition_agent = CompositionAgent()
    refined_timeline = await composition_agent.refine_existing_timeline(
        modified_timeline, commands.style_changes
    )
    
    return refined_timeline
```

## Inter-Agent Communication

### ProjectState: Shared Memory

All agents communicate through a shared `ProjectState` object that serves as the system's memory:

```python
# State progression through workflow
project_state.status.phase = "analysis"     # AnalysisAgent working
project_state.status.phase = "composition"  # CompositionAgent working  
project_state.status.phase = "evaluation"   # EvaluationAgent working
project_state.status.phase = "refinement"   # RefinementAgent working
project_state.status.phase = "completed"    # Workflow finished
```

### Data Flow Patterns

```python
# Analysis → Composition
analyzed_media = project_state.analyzed_media
timeline = composition_agent.create_timeline(analyzed_media)
project_state.current_timeline = timeline

# Composition → Evaluation  
evaluation = evaluation_agent.evaluate(
    project_state.current_video_path,
    project_state.current_timeline
)
project_state.current_evaluation = evaluation

# Evaluation → Refinement
if evaluation.needs_refinement:
    commands = refinement_agent.generate_commands(evaluation)
    improved_timeline = composition_agent.apply_refinements(commands)
    project_state.current_timeline = improved_timeline
```

## Error Handling and Recovery

### Agent-Level Error Handling

Each agent implements robust error handling:

```python
class BaseAgent:
    """Base agent with standard error handling."""
    
    async def execute_with_recovery(self, operation):
        """Execute operation with automatic recovery."""
        
        for attempt in range(self.max_retries):
            try:
                return await operation()
            
            except RetryableError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    raise
            
            except NonRetryableError as e:
                # Log error and return graceful fallback
                logger.error(f"Non-retryable error in {self.name}: {e}")
                return self._generate_fallback_result(e)
```

### System-Level Recovery

```python
class ErrorRecoveryManager:
    """Manages system-wide error recovery."""
    
    async def handle_agent_failure(
        self,
        failed_agent: str,
        error: Exception,
        project_state: ProjectState
    ):
        """Implement recovery strategies for agent failures."""
        
        if failed_agent == "AnalysisAgent":
            # Use cached analysis or simplified analysis
            return await self._recover_analysis_failure(project_state)
        
        elif failed_agent == "CompositionAgent":
            # Fall back to template-based composition
            return await self._recover_composition_failure(project_state)
        
        elif failed_agent == "EvaluationAgent":
            # Skip evaluation, proceed with video
            return await self._skip_evaluation(project_state)
```

## Performance Optimization

### Concurrent Processing

Where possible, agents use concurrent processing:

```python
# AnalysisAgent: Concurrent media analysis
async def analyze_media_batch(self, media_assets):
    analysis_tasks = [
        self.analyze_single_media(asset) 
        for asset in media_assets
    ]
    return await asyncio.gather(*analysis_tasks)

# CompositionAgent: Parallel clip processing
async def process_clips_concurrently(self, timeline):
    clip_tasks = [
        self.process_timeline_segment(segment)
        for segment in timeline.segments
    ]
    return await asyncio.gather(*clip_tasks)
```

### Memory Management

```python
class MemoryManager:
    """Manages memory usage across agents."""
    
    def __init__(self):
        self.max_memory_mb = 4000  # 4GB limit
        self.current_usage = 0
    
    async def process_with_memory_limit(self, media_assets):
        """Process media in batches to stay within memory limits."""
        
        batch_size = self._calculate_optimal_batch_size(media_assets)
        
        for batch in self._create_batches(media_assets, batch_size):
            await self._process_batch(batch)
            
            # Force garbage collection between batches
            import gc
            gc.collect()
```

## Testing and Validation

### Agent Unit Testing

Each agent has comprehensive unit tests:

```python
class TestAnalysisAgent:
    """Unit tests for AnalysisAgent."""
    
    @pytest.mark.asyncio
    async def test_visual_analysis(self):
        """Test visual analysis functionality."""
        agent = AnalysisAgent()
        
        # Mock media asset
        media = create_test_media_asset("test_image.jpg")
        
        # Run analysis
        result = await agent.analyze_single_media(media)
        
        # Validate results
        assert result.geminiAnalysis is not None
        assert result.geminiAnalysis.aesthetic_score >= 0
        assert result.geminiAnalysis.aesthetic_score <= 1
        assert len(result.geminiAnalysis.description) > 10
```

### Integration Testing

```python
class TestAgentIntegration:
    """Integration tests for agent interactions."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete agent workflow."""
        
        # Setup test project
        project_state = create_test_project_state()
        
        # Run analysis
        analysis_agent = AnalysisAgent()
        project_state = await analysis_agent.run(project_state)
        
        # Run composition
        composition_agent = CompositionAgent()
        project_state = await composition_agent.run(project_state)
        
        # Validate results
        assert project_state.current_video_path is not None
        assert os.path.exists(project_state.current_video_path)
```

This architecture provides a robust, scalable foundation for intelligent video creation while maintaining clear separation of concerns and reliable error handling throughout the system.