"""Integration tests for visual analysis workflow with Gemini."""

import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json
import base64

from memory_movie_maker.tools.visual_analysis import VisualAnalysisTool
from memory_movie_maker.models.media_asset import (
    MediaAsset, MediaType, GeminiAnalysis, VideoSegment
)


# Skip real API tests if no key is configured
real_api_skip = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set"
)


class TestVisualAnalysisIntegration:
    """Integration tests for visual analysis with mocked and real Gemini API."""
    
    @pytest.fixture
    def test_videos_dir(self):
        """Get path to test videos directory."""
        return Path(__file__).parent.parent.parent / "data" / "test_inputs"
    
    @pytest.fixture
    def visual_tool(self):
        """Create visual analysis tool with real API."""
        return VisualAnalysisTool()
    
    @pytest.mark.asyncio
    async def test_analyze_real_video(self, visual_tool, test_videos_dir):
        """Test analyzing a real video file."""
        # Find first video in test directory
        video_files = list(test_videos_dir.glob("*.mp4"))
        if not video_files:
            pytest.skip("No test videos found")
        
        video_path = str(video_files[0])
        
        # Analyze the video
        result = await visual_tool.analyze_video(video_path)
        
        # Verify the result
        assert isinstance(result, GeminiAnalysis)
        assert result.description
        assert 0 <= result.aesthetic_score <= 1
        assert isinstance(result.tags, list)
        
        # Check video-specific fields
        assert result.notable_segments is not None
        if result.notable_segments:
            segment = result.notable_segments[0]
            assert segment.start_time >= 0
            assert segment.end_time > segment.start_time
            assert segment.description
            assert 0 <= segment.importance <= 1
        
        if result.overall_motion:
            assert isinstance(result.overall_motion, str)
        
        if result.scene_changes:
            assert all(t >= 0 for t in result.scene_changes)
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_videos(self, visual_tool, test_videos_dir):
        """Test analyzing multiple videos to check consistency."""
        video_files = list(test_videos_dir.glob("*.mp4"))[:2]  # Test first 2 videos
        if len(video_files) < 2:
            pytest.skip("Need at least 2 test videos")
        
        results = []
        for video_path in video_files:
            result = await visual_tool.analyze_video(str(video_path))
            results.append(result)
        
        # All should be valid analyses
        assert all(isinstance(r, GeminiAnalysis) for r in results)
        assert all(r.description for r in results)
        assert all(0 <= r.aesthetic_score <= 1 for r in results)
    
    @pytest.mark.asyncio
    async def test_video_notable_segments(self, visual_tool, test_videos_dir):
        """Test that video analysis produces meaningful segments."""
        video_files = list(test_videos_dir.glob("*.mp4"))
        if not video_files:
            pytest.skip("No test videos found")
        
        video_path = str(video_files[0])
        result = await visual_tool.analyze_video(video_path)
        
        # Should have at least one notable segment
        assert len(result.notable_segments) >= 1
        
        # Segments should be chronological and non-overlapping
        for i in range(len(result.notable_segments) - 1):
            current = result.notable_segments[i]
            next_seg = result.notable_segments[i + 1]
            assert current.end_time <= next_seg.start_time
        
        # All segments should have meaningful descriptions
        for segment in result.notable_segments:
            assert len(segment.description) > 10  # Not just a few words
            assert segment.tags  # Should have at least one tag