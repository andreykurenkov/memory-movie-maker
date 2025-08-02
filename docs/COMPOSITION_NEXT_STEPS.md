# Next Steps: Composition Algorithm & Video Rendering

## Current Status (As of 2025-08-02)

✅ **Completed:**
- All analysis tools (visual, audio technical, audio semantic)
- AnalysisAgent that coordinates all media analysis
- Comprehensive data models for project state and media

🚧 **Next Task: Implement Composition Algorithm and Video Rendering**

## Overview

The composition algorithm is the brain of the video creation process. It takes analyzed media and creates an intelligent timeline that:
- Syncs cuts to music beats
- Groups related content together
- Creates smooth transitions
- Balances pacing and energy

## Key Components to Implement

### 1. Timeline Generation Algorithm

```python
# src/memory_movie_maker/tools/composition.py

class CompositionTool:
    """Creates video timelines from analyzed media."""
    
    def compose_timeline(
        self,
        media_pool: List[MediaAsset],
        music_profile: AudioAnalysisProfile,
        target_duration: int,
        style_preferences: Dict[str, Any]
    ) -> Timeline:
        """Generate optimal timeline from media and music."""
        # 1. Cluster media by visual similarity/time
        # 2. Map clusters to music sections
        # 3. Assign media to beats
        # 4. Apply transitions
        # 5. Validate timeline
```

### 2. Core Algorithms Needed

#### A. Media Clustering
- Group photos/videos by:
  - Timestamp proximity
  - Visual similarity (from Gemini tags)
  - Subject matter
  - Quality scores

#### B. Beat Mapping
- Align media cuts to musical beats
- Use energy curves for dynamic pacing
- Place impactful media at musical peaks

#### C. Transition Selection
- Choose transitions based on:
  - Music tempo
  - Media content
  - Emotional tone
  - Pacing requirements

### 3. Video Rendering with MoviePy

```python
# src/memory_movie_maker/tools/video_renderer.py

from moviepy.editor import (
    VideoFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips, AudioFileClip
)

class VideoRenderer:
    """Renders final video from timeline."""
    
    async def render_video(
        self,
        timeline: Timeline,
        output_path: str,
        resolution: Tuple[int, int] = (1920, 1080)
    ) -> str:
        """Render timeline to video file."""
        # 1. Load all media clips
        # 2. Apply effects and transitions
        # 3. Sync to audio
        # 4. Export final video
```

## Implementation Steps

### Step 1: Install MoviePy
```bash
pip install moviepy
```

### Step 2: Create Composition Algorithm
1. Start with simple chronological ordering
2. Add beat synchronization
3. Implement clustering
4. Add transition logic

### Step 3: Create Video Renderer
1. Basic concatenation of clips
2. Add crossfade transitions
3. Implement Ken Burns effect for photos
4. Add audio synchronization

### Step 4: Create ADK Tool Wrappers
- `compose_timeline_tool` - For timeline generation
- `render_video_tool` - For video rendering

## Testing Approach

### Unit Tests
- Test clustering algorithm
- Test beat mapping
- Test transition selection
- Mock MoviePy for rendering tests

### Integration Tests
```python
# scripts/test_composition.py
async def test_composition():
    # Load analyzed media
    # Create timeline
    # Render short test video
    # Verify output
```

## Common Challenges

### 1. Memory Management
- MoviePy can be memory-intensive
- Process clips in batches
- Use lower resolution for previews

### 2. Rendering Performance
- Use multiprocessing for parallel rendering
- Cache rendered segments
- Optimize clip loading

### 3. Audio Sync
- Ensure precise beat alignment
- Handle videos with existing audio
- Mix audio tracks properly

## Example Timeline Structure

```python
timeline = Timeline(
    segments=[
        Segment(
            media_id="photo1",
            start_time=0.0,
            duration=2.5,  # Matches 2 beats
            effects=["ken_burns"],
            transition_out="crossfade"
        ),
        Segment(
            media_id="video1",
            start_time=2.5,
            duration=5.0,
            trim_start=1.0,  # Skip first second
            transition_out="fade_to_black"
        )
    ],
    audio_track_id="music1",
    total_duration=120.0
)
```

## Success Criteria

1. ✅ Timeline syncs perfectly to music beats
2. ✅ Smooth transitions between clips
3. ✅ Intelligent media ordering
4. ✅ Renders without memory issues
5. ✅ Output video plays correctly

## Resources

- [MoviePy Documentation](https://zulko.github.io/moviepy/)
- [Video Editing Best Practices](https://github.com/Zulko/moviepy/blob/master/examples/)
- Timeline data model in `src/memory_movie_maker/models/timeline.py`