# RootAgent Guide

## Overview

The RootAgent is the main orchestrator for the Memory Movie Maker system. It coordinates all other agents in a sequential workflow, implementing a self-correction loop that automatically improves video quality.

## Architecture

### Sequential Workflow (No LLM Decision-Making)

The RootAgent follows a deterministic, sequential workflow:

```
1. Initialize → 2. Analyze → 3. Compose → 4. Evaluate/Refine Loop → 5. Final Render
```

No LLM calls are needed to decide which agent to run - the flow is hardcoded based on the current phase.

### Self-Correction Loop

The system automatically refines videos up to 3 times:

```python
while refinement_count < 3:
    1. Evaluate video (EvaluationAgent)
    2. Check score and recommendation
    3. If score >= 7.0 and recommendation == "accept": 
       → Done!
    4. Else:
       → Parse feedback (RefinementAgent)
       → Apply edits (CompositionAgent)
       → Re-render preview
    5. refinement_count++
```

## Usage

### Python API

```python
from memory_movie_maker.agents.root_agent import RootAgent

# Create orchestrator
root_agent = RootAgent()

# Create memory movie
result = await root_agent.create_memory_movie(
    media_paths=["photo1.jpg", "photo2.jpg", "video1.mp4"],
    user_prompt="Create a family vacation video with upbeat music",
    music_path="background_music.mp3",
    target_duration=60,
    style="dynamic",
    auto_refine=True  # Enable self-correction
)

if result["status"] == "success":
    print(f"Video created: {result['video_path']}")
    print(f"Quality score: {result['final_score']}/10")
    print(f"Refinements: {result['refinement_iterations']}")
```

### Command Line

```bash
# Basic usage
python scripts/create_memory_movie.py photo*.jpg video*.mp4 \
    -p "Create a vacation montage" \
    -m music.mp3 \
    -d 60

# Fast mode (no refinement)
python scripts/create_memory_movie.py media/*.* \
    -p "Quick slideshow" \
    --no-refine

# Different styles
python scripts/create_memory_movie.py *.jpg \
    -p "Smooth romantic video" \
    -s smooth
```

## Workflow Phases

### Phase 1: Initialize
- Load media files
- Detect file types
- Create ProjectState
- Set initial parameters

### Phase 2: Analyze
- **AnalysisAgent** processes all media:
  - Visual analysis (Gemini)
  - Audio technical analysis (Librosa)
  - Audio semantic analysis (Gemini)
- Results cached in MediaAsset objects

### Phase 3: Compose
- **CompositionAgent** creates initial video:
  - Beat-synchronized timeline
  - Intelligent media clustering
  - Transition selection
  - Preview render (640x360)

### Phase 4: Evaluate & Refine
- **EvaluationAgent** critiques video:
  - Scores 1-10
  - Identifies issues
  - Suggests improvements
  
- **RefinementAgent** parses feedback:
  - Converts to edit commands
  - Prioritizes changes
  
- **CompositionAgent** applies edits:
  - Adjusts durations
  - Changes transitions
  - Re-renders preview

This loop continues until:
- Score >= 7.0 and recommendation == "accept"
- OR max iterations (3) reached

### Phase 5: Final Render
- Full quality render (1920x1080)
- Save project state
- Return final video path

## User Feedback Processing

After initial creation, users can provide feedback:

```python
feedback_result = await root_agent.process_user_feedback(
    project_state=project_state,
    user_feedback="Make it 30 seconds with slower pacing"
)
```

The system will:
1. Parse the natural language request
2. Determine intent (edit/evaluate/create)
3. Apply appropriate changes
4. Re-render as needed

## Configuration

### Refinement Settings

```python
root_agent.max_refinement_iterations = 3  # Max self-correction loops
root_agent.min_acceptable_score = 7.0     # Minimum quality threshold
```

### Storage

The RootAgent uses the storage interface for:
- Saving project states
- Managing temporary files
- Organizing rendered outputs

## Error Handling

The RootAgent handles errors gracefully:
- Failed evaluations skip refinement
- Missing analysis falls back to basic composition
- Each phase logs detailed progress

## Performance

Typical processing times:
- Analysis: 10-30s per media file
- Composition: 5-10s
- Evaluation: 10-15s
- Refinement: 5-10s
- Final render: 30-60s

Total time for a 60-second video with 10 media files:
- With refinement: 3-5 minutes
- Without refinement: 1-2 minutes

## Best Practices

1. **Media Selection**: Include diverse, high-quality media
2. **Clear Prompts**: Be specific about desired style and mood
3. **Music Choice**: Select music that matches intended energy
4. **Auto-Refine**: Enable for best quality, disable for speed
5. **Feedback**: Provide specific, actionable feedback

## Troubleshooting

### Common Issues

1. **Low evaluation scores**
   - Check media quality
   - Ensure sufficient media variety
   - Verify music-video sync

2. **Slow processing**
   - Reduce media file sizes
   - Use --no-refine for faster results
   - Check GPU availability for rendering

3. **Memory errors**
   - Process fewer files at once
   - Reduce target duration
   - Use preview mode for testing