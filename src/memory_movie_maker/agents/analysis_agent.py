"""Analysis agent for processing media files."""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
import tempfile
import os

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

from ..tools.visual_analysis import visual_analysis_tool
from ..tools.audio_analysis import audio_analysis_tool
from ..tools.semantic_audio_analysis import semantic_audio_analysis_tool
from ..models.project_state import ProjectState
from ..models.media_asset import MediaAsset, MediaType
from ..storage.interface import StorageInterface
from ..storage.filesystem import FilesystemStorage


logger = logging.getLogger(__name__)


class AnalysisAgent(Agent):
    """Agent responsible for analyzing all media files in a project."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
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
        self.storage = storage or FilesystemStorage()
    
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
        
        # Create batches for concurrent processing
        visual_tasks = []
        audio_tasks = []
        
        for media_asset in media_files:
            # Skip if already analyzed and caching is enabled
            if self._is_fully_analyzed(media_asset) and project_state.analysis_cache_enabled:
                logger.info(f"Skipping {media_asset.file_path} - already analyzed")
                continue
            
            # Determine file type and create appropriate tasks
            if media_asset.type in [MediaType.IMAGE, MediaType.VIDEO]:
                if not media_asset.gemini_analysis:
                    visual_tasks.append(self._analyze_visual(media_asset))
            
            # For videos, also extract and analyze audio if needed
            if media_asset.type == MediaType.VIDEO:
                if not media_asset.audio_analysis:
                    audio_tasks.append(self._analyze_video_audio(media_asset))
            
            # For audio files, analyze both technical and semantic
            if media_asset.type == MediaType.AUDIO:
                if not media_asset.audio_analysis:
                    audio_tasks.append(self._analyze_audio_technical(media_asset))
                if not media_asset.semantic_audio_analysis:
                    audio_tasks.append(self._analyze_audio_semantic(media_asset))
        
        # Process all analyses concurrently
        if visual_tasks or audio_tasks:
            logger.info(f"Running {len(visual_tasks)} visual and {len(audio_tasks)} audio analyses")
            
            all_tasks = visual_tasks + audio_tasks
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            # Log any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Analysis task {i} failed: {result}")
        
        # Update project phase
        if project_state.project_status.phase == "analyzing":
            project_state.project_status.phase = "composing"
            logger.info("Analysis complete, moving to composing phase")
        
        return project_state
    
    def _is_fully_analyzed(self, media_asset: MediaAsset) -> bool:
        """Check if a media asset has been fully analyzed."""
        if media_asset.type in [MediaType.IMAGE, MediaType.VIDEO]:
            if not media_asset.gemini_analysis:
                return False
        
        if media_asset.type in [MediaType.VIDEO, MediaType.AUDIO]:
            if not media_asset.audio_analysis:
                return False
        
        if media_asset.type == MediaType.AUDIO and not media_asset.semantic_audio_analysis:
            return False
        
        return True
    
    async def _analyze_visual(self, media_asset: MediaAsset) -> MediaAsset:
        """Analyze visual content of an image or video."""
        try:
            logger.info(f"Analyzing visual content: {media_asset.file_path}")
            
            # Call the visual analysis tool
            from ..tools.visual_analysis import analyze_visual_media
            result = await analyze_visual_media(media_asset.file_path)
            
            if result["status"] == "success":
                # Update media asset with analysis
                media_asset.gemini_analysis = result["analysis"]
                logger.info(f"Visual analysis complete for {media_asset.file_path}")
            else:
                logger.error(f"Visual analysis failed: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Failed to analyze visual content {media_asset.file_path}: {e}")
        
        return media_asset
    
    async def _analyze_audio_technical(self, media_asset: MediaAsset) -> MediaAsset:
        """Analyze technical audio features."""
        try:
            logger.info(f"Analyzing audio features: {media_asset.file_path}")
            
            # Call the audio analysis tool
            from ..tools.audio_analysis import analyze_audio_media
            result = await analyze_audio_media(media_asset.file_path)
            
            if result["status"] == "success":
                # Update media asset with analysis
                media_asset.audio_analysis = result["analysis"]
                logger.info(f"Audio analysis complete for {media_asset.file_path}")
            else:
                logger.error(f"Audio analysis failed: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Failed to analyze audio {media_asset.file_path}: {e}")
        
        return media_asset
    
    async def _analyze_audio_semantic(self, media_asset: MediaAsset) -> MediaAsset:
        """Analyze semantic audio content."""
        try:
            logger.info(f"Analyzing audio semantics: {media_asset.file_path}")
            
            # Call the semantic audio analysis tool
            from ..tools.semantic_audio_analysis import analyze_audio_semantics
            result = await analyze_audio_semantics(media_asset.file_path)
            
            if result["status"] == "success":
                # Update media asset with analysis
                media_asset.semantic_audio_analysis = result["analysis"]
                logger.info(f"Semantic audio analysis complete for {media_asset.file_path}")
            else:
                logger.error(f"Semantic audio analysis failed: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Failed to analyze audio semantics {media_asset.file_path}: {e}")
        
        return media_asset
    
    async def _analyze_video_audio(self, media_asset: MediaAsset) -> MediaAsset:
        """Extract and analyze audio from video file."""
        audio_path = None
        try:
            logger.info(f"Extracting audio from video: {media_asset.file_path}")
            
            # Extract audio track
            audio_path = await self._extract_audio_from_video(media_asset.file_path)
            
            if audio_path:
                # Analyze the extracted audio
                await self._analyze_audio_technical(media_asset)
                
                # Also run semantic analysis if the video might have speech
                if media_asset.gemini_analysis and any(
                    tag in media_asset.gemini_analysis.tags 
                    for tag in ["speech", "people", "conversation", "interview"]
                ):
                    await self._analyze_audio_semantic(media_asset)
            
        except Exception as e:
            logger.error(f"Failed to extract/analyze video audio {media_asset.file_path}: {e}")
        finally:
            # Clean up temporary audio file
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)
        
        return media_asset
    
    async def _extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """Extract audio track from video file."""
        try:
            from moviepy.editor import VideoFileClip
            
            # Create temporary audio file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                audio_path = tmp.name
            
            # Extract audio using MoviePy
            video = VideoFileClip(video_path)
            if video.audio is not None:
                video.audio.write_audiofile(audio_path, logger=None)
                video.close()
                return audio_path
            else:
                logger.warning(f"Video has no audio track: {video_path}")
                video.close()
                return None
            
        except Exception as e:
            logger.error(f"Failed to extract audio from {video_path}: {e}")
            return None


# Standalone function for testing
async def test_analysis_agent():
    """Test the analysis agent with sample data."""
    from ..models.project_state import ProjectState, UserInputs, ProjectStatus
    from ..models.media_asset import MediaAsset
    import uuid
    
    # Create test project state
    test_media = [
        MediaAsset(
            id=str(uuid.uuid4()),
            file_path="data/test_inputs/test_video.mp4",
            type=MediaType.VIDEO
        ),
        MediaAsset(
            id=str(uuid.uuid4()),
            file_path="data/test_inputs/test_song.mp3",
            type=MediaType.AUDIO
        )
    ]
    
    project_state = ProjectState(
        user_inputs=UserInputs(
            media=test_media,
            initial_prompt="Create a test video"
        ),
        project_status=ProjectStatus(phase="analyzing")
    )
    
    # Create and run agent
    agent = AnalysisAgent()
    updated_state = await agent.analyze_project(project_state)
    
    # Print results
    for media in updated_state.user_inputs.media:
        print(f"\nMedia: {media.file_path}")
        print(f"Type: {media.type}")
        if media.gemini_analysis:
            print(f"Visual: {media.gemini_analysis.description}")
        if media.audio_analysis:
            print(f"Audio: {media.audio_analysis.tempo_bpm} BPM, {len(media.audio_analysis.beat_timestamps)} beats")
        if media.semantic_audio_analysis:
            print(f"Semantic: {media.semantic_audio_analysis.get('summary', 'N/A')}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analysis_agent())