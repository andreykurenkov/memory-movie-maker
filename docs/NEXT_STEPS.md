# Next Steps: AnalysisAgent Implementation Guide

## Current Status (As of 2025-08-02)

✅ **Completed:**
- Project structure and configuration
- All documentation (PRD, TDD, roadmap)
- Data models with full validation
- Storage layer with filesystem backend
- Visual analysis tool with Gemini API
- Updated dependencies (using Librosa instead of Essentia)
- **NEW: Migrated to new google-genai SDK (v1.28.0)**
- **NEW: Audio analysis tool with Librosa**
- **NEW: Semantic audio analysis tool with Gemini**

🚧 **Next Task: Implement AnalysisAgent**

## What Was Just Completed

### Audio Analysis Tools (Two Complementary Approaches)

#### 1. Technical Audio Analysis (Librosa)
- Extracts tempo, beats, energy curves from audio files
- Analyzes musical characteristics (danceability, energy, valence, arousal)
- Detects mood and genre hints
- Provides timestamps for beats and energy peaks
- Fully tested with both unit tests and real MP3 files

#### 2. Semantic Audio Analysis (Gemini)
- Generates transcripts for speech content
- Identifies speakers and conversation topics
- Detects emotional tone and key moments
- Segments audio into meaningful parts (speech, music, sound effects)
- Provides sync suggestions for video editing

### Key Features:
- **Technical (Librosa)**: Beat detection, tempo sync, energy-based cuts
- **Semantic (Gemini)**: Content understanding, speech timing, emotional arcs
- **Combined Power**: Both tools work together for intelligent video composition
- ADK tool wrappers ready for agent integration

## Quick Start for AnalysisAgent

### 1. Understanding the AnalysisAgent Role

The AnalysisAgent is responsible for:
- Coordinating visual and audio analysis of all media files
- Managing batch processing of multiple files
- Caching analysis results to avoid re-processing
- Updating the ProjectState with analysis results

### 2. Prerequisites

```bash
# Verify all analysis tools work
python scripts/test_visual_analysis.py
python scripts/test_audio_with_real_file.py
python scripts/test_semantic_audio.py

# All should analyze test files successfully
```

### 3. AnalysisAgent Implementation Guide

Create `src/memory_movie_maker/agents/analysis_agent.py`:

```python
"""Analysis agent for processing media files."""

import logging
from typing import Dict, Any, List
from pathlib import Path

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

from ..tools.visual_analysis import visual_analysis_tool
from ..tools.audio_analysis import audio_analysis_tool
from ..tools.semantic_audio_analysis import semantic_audio_analysis_tool
from ..models.project_state import ProjectState, MediaAsset
from ..storage.interface import StorageInterface

logger = logging.getLogger(__name__)


class AnalysisAgent(Agent):
    """Agent responsible for analyzing all media files in a project."""
    
    def __init__(self, storage: StorageInterface):
        """Initialize the analysis agent.
        
        Args:
            storage: Storage interface for accessing files
        """
        super().__init__(
            name="AnalysisAgent",
            model="gemini-2.0-flash",
            description="Analyzes media files for visual and audio content",
            instruction="""You are an expert media analyst. Your job is to:
            1. Analyze all media files provided
            2. Use visual_analysis for images and videos
            3. Use audio_analysis for technical audio features (beats, tempo, energy)
            4. Use semantic_audio_analysis for content understanding (speech, emotions)
            5. Extract meaningful features for video composition
            6. Update the project state with analysis results
            
            Be thorough but efficient. Cache results when possible.""",
            tools=[visual_analysis_tool, audio_analysis_tool, semantic_audio_analysis_tool]
        )
        self.storage = storage
    
    async def analyze_project(self, project_state: ProjectState) -> ProjectState:
        """Analyze all media files in the project.
        
        Args:
            project_state: Current project state
            
        Returns:
            Updated project state with analysis results
        """
        # Get all media files
        media_files = project_state.user_inputs.media
        
        logger.info(f"Analyzing {len(media_files)} media files")
        
        for media_asset in media_files:
            # Skip if already analyzed
            if media_asset.geminiAnalysis and project_state.analysis_cache_enabled:
                logger.info(f"Skipping {media_asset.path} - already analyzed")
                continue
            
            # Determine file type and analyze
            if media_asset.type in ["image", "video"]:
                await self._analyze_visual(media_asset)
            
            # For videos, also extract audio if needed
            if media_asset.type == "video" and not media_asset.audioAnalysis:
                await self._extract_and_analyze_audio(media_asset)
        
        # Update project phase
        project_state.project_status.phase = "composition"
        
        return project_state
```

### 4. Key Implementation Points

1. **Batch Processing**:
   ```python
   # Process multiple files concurrently
   import asyncio
   
   tasks = []
   for media in media_files:
       if media.type == "video":
           tasks.append(self._analyze_visual(media))
   
   results = await asyncio.gather(*tasks)
   ```

2. **Caching Logic**:
   ```python
   # Check cache before analyzing
   if media_asset.geminiAnalysis:
       # Use cached analysis
       return media_asset
   
   # After analysis, update the asset
   media_asset.geminiAnalysis = analysis_result
   ```

3. **Audio Extraction from Video**:
   ```python
   # Extract audio track from video
   from moviepy.editor import VideoFileClip
   
   async def _extract_audio(self, video_path: str) -> str:
       """Extract audio from video file."""
       video = VideoFileClip(video_path)
       audio_path = video_path.replace('.mp4', '_audio.mp3')
       video.audio.write_audiofile(audio_path)
       return audio_path
   ```

### 5. Testing the AnalysisAgent

Create `tests/unit/test_analysis_agent.py`:

```python
"""Tests for AnalysisAgent."""

import pytest
from unittest.mock import Mock, AsyncMock

from memory_movie_maker.agents.analysis_agent import AnalysisAgent
from memory_movie_maker.models.project_state import ProjectState


class TestAnalysisAgent:
    """Test AnalysisAgent functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_project(self):
        """Test analyzing a project with mixed media."""
        # Create mock storage
        storage = Mock()
        
        # Create agent
        agent = AnalysisAgent(storage)
        
        # Create test project state
        project_state = create_test_project_state()
        
        # Run analysis
        result = await agent.analyze_project(project_state)
        
        # Verify all media was analyzed
        for media in result.user_inputs.media:
            if media.type in ["image", "video"]:
                assert media.geminiAnalysis is not None
            if media.type == "video":
                assert media.audioAnalysis is not None
```

### 6. Integration with RootAgent

The AnalysisAgent will be called by RootAgent:

```python
# In RootAgent
async def process_user_request(self, request: str, project_state: ProjectState):
    # ... other logic ...
    
    if project_state.project_status.phase == "analysis":
        # Run analysis
        analysis_agent = AnalysisAgent(self.storage)
        project_state = await analysis_agent.analyze_project(project_state)
```

## Common Challenges and Solutions

### 1. **Large Video Files**
- Problem: Videos take too long to upload/analyze
- Solution: Implement video chunking or sampling
- Consider: Analyze keyframes only for very long videos

### 2. **API Rate Limits**
- Problem: Hitting Gemini API limits with many files
- Solution: Implement rate limiting and exponential backoff
- Code:
  ```python
  from tenacity import retry, wait_exponential
  
  @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
  async def analyze_with_retry(self, file_path):
      return await self.visual_tool.analyze(file_path)
  ```

### 3. **Memory Issues**
- Problem: Loading many large files causes OOM
- Solution: Process files one at a time, clear memory between
- Use: `gc.collect()` after processing large files

### 4. **Mixed Media Handling**
- Problem: Projects may have images, videos, and separate audio
- Solution: Handle each type appropriately
- Consider: Creating a media type detector utility

## Testing Checklist

- [ ] Unit tests for AnalysisAgent class
- [ ] Integration tests with real media files
- [ ] Test batch processing performance
- [ ] Test caching behavior
- [ ] Test error handling (corrupted files, API failures)
- [ ] Test memory usage with large projects
- [ ] Test concurrent analysis
- [ ] Verify ProjectState updates correctly

## Next Steps After AnalysisAgent

Once the AnalysisAgent is complete:
1. Update roadmap.md to ~65% complete
2. Begin implementing the composition algorithm
3. Create timeline based on audio beats and visual segments
4. Implement video rendering with MoviePy

The composition algorithm should:
- Use beat timestamps for cut timing
- Use energy peaks for dramatic moments
- Match visual segments to audio rhythm
- Create smooth transitions

Good luck! The AnalysisAgent is crucial for extracting all the features needed for intelligent video composition.