"""Analysis agent for processing media files."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from google.adk.agents import Agent

from ..tools.visual_analysis import visual_analysis_tool
from ..tools.audio_analysis import audio_analysis_tool
from ..tools.semantic_audio_analysis import semantic_audio_analysis_tool
from ..models.project_state import ProjectState
from ..models.media_asset import MediaAsset, MediaType
from ..storage.interface import StorageInterface
from ..config import settings
from ..storage.filesystem import FilesystemStorage
from ..utils.simple_logger import log_start, log_update, log_complete


logger = logging.getLogger(__name__)

# Module-level storage for the agent
_agent_storage: Optional[StorageInterface] = None


class AnalysisAgent(Agent):
    """Agent responsible for analyzing all media files in a project."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
        """Initialize the analysis agent.
        
        Args:
            storage: Storage interface for accessing files
        """
        global _agent_storage
        _agent_storage = storage or FilesystemStorage(base_path="./data")
        
        super().__init__(
            name="AnalysisAgent",
            model=settings.get_gemini_model_name(),
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
    
    @property
    def storage(self) -> StorageInterface:
        """Get the storage interface."""
        return _agent_storage
    
    async def analyze_project(self, project_state: ProjectState) -> ProjectState:
        """Analyze all media files in the project.
        
        Args:
            project_state: Current project state
            
        Returns:
            Updated project state with analysis results
        """
        # Get all media files
        media_files = project_state.user_inputs.media
        music_files = project_state.user_inputs.music
        
        # Combine all files for analysis
        all_files = media_files + music_files
        
        log_start(logger, f"Analyzing {len(media_files)} media files and {len(music_files)} music tracks")
        
        # Create batches for concurrent processing
        visual_tasks = []
        audio_tasks = []
        
        for media_asset in all_files:
            # Skip if already analyzed and caching is enabled
            if self._is_fully_analyzed(media_asset) and project_state.analysis_cache_enabled:
                log_update(logger, f"Skipping {Path(media_asset.file_path).name} - already analyzed")
                continue
            
            # Determine file type and create appropriate tasks
            if media_asset.type in [MediaType.IMAGE, MediaType.VIDEO]:
                if not media_asset.gemini_analysis:
                    visual_tasks.append(self._analyze_visual(media_asset))
            
            # Note: For videos, audio is now analyzed as part of Gemini's video analysis
            # No need for separate audio extraction and analysis
            
            # For audio files, analyze both technical and semantic
            if media_asset.type == MediaType.AUDIO:
                if not media_asset.audio_analysis:
                    audio_tasks.append(self._analyze_audio_technical(media_asset))
                if not media_asset.semantic_audio_analysis:
                    audio_tasks.append(self._analyze_audio_semantic(media_asset))
        
        # Process all analyses with limited concurrency to avoid memory issues
        if visual_tasks or audio_tasks:
            log_update(logger, f"Running {len(visual_tasks)} visual and {len(audio_tasks)} audio analyses...")
            
            all_tasks = visual_tasks + audio_tasks
            
            # Limit concurrent uploads to avoid bus errors with large files
            # Use semaphore to limit to 4 concurrent uploads (balanced speed/stability)
            MAX_CONCURRENT_UPLOADS = 4
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)
            completed_count = 0
            
            async def run_with_semaphore(task_idx, task):
                nonlocal completed_count
                async with semaphore:
                    # Add small delay to avoid overwhelming the system
                    await asyncio.sleep(0.1)
                    result = await task
                    completed_count += 1
                    log_update(logger, f"Analysis progress: {completed_count}/{len(all_tasks)} completed")
                    return result
            
            # Wrap tasks with semaphore
            limited_tasks = [run_with_semaphore(i, task) for i, task in enumerate(all_tasks)]
            
            # Run tasks and collect both results and exceptions
            errors = []
            successful = 0
            
            # Use gather without return_exceptions to properly propagate critical errors
            try:
                results = await asyncio.gather(*limited_tasks)
                successful = len(results)
                log_update(logger, f"All {len(all_tasks)} analysis tasks completed successfully")
            except Exception as e:
                # If gather fails, try to complete remaining tasks individually
                logger.error(f"Batch analysis failed: {e}")
                
                # Run tasks individually to identify which ones fail
                for i, task in enumerate(all_tasks):
                    try:
                        await task
                        successful += 1
                    except Exception as task_error:
                        errors.append((i, task_error))
                        logger.error(f"Analysis task {i} failed: {task_error}")
                
                if errors:
                    logger.warning(f"{len(errors)} out of {len(all_tasks)} tasks failed")
                    # Don't fail completely if some analyses succeed
                    if successful == 0:
                        raise Exception(f"All {len(all_tasks)} analysis tasks failed")
        
        # Update project phase
        if project_state.status.phase == "analyzing":
            project_state.status.phase = "composing"
            log_complete(logger, "Analysis phase complete, ready for composition")
        
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
            # No need to log here as visual_analysis tool will log
            
            # Call the visual analysis tool
            from ..tools.visual_analysis import analyze_visual_media
            result = await analyze_visual_media(media_asset.file_path)
            
            if result["status"] == "success":
                # Update media asset with analysis
                from ..models.media_asset import GeminiAnalysis
                media_asset.gemini_analysis = GeminiAnalysis(**result["analysis"])
                
                # Store video duration in metadata if it's a video
                if media_asset.type == MediaType.VIDEO and "duration" in result:
                    if media_asset.metadata is None:
                        media_asset.metadata = {}
                    media_asset.metadata["duration"] = result["duration"]
            else:
                logger.error(f"Visual analysis failed for {Path(media_asset.file_path).name}: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Failed to analyze visual content {Path(media_asset.file_path).name}: {e}")
        
        return media_asset
    
    async def _analyze_audio_technical(self, media_asset: MediaAsset) -> MediaAsset:
        """Analyze technical audio features."""
        try:
            log_update(logger, f"Analyzing audio features: {Path(media_asset.file_path).name}")
            
            # Call the audio analysis tool
            from ..tools.audio_analysis import analyze_audio_media
            result = await analyze_audio_media(media_asset.file_path)
            
            if result["status"] == "success":
                # Update media asset with analysis
                from ..models.media_asset import AudioAnalysisProfile
                media_asset.audio_analysis = AudioAnalysisProfile(**result["analysis"])
                log_update(logger, f"Audio analysis complete: {result['analysis']['tempo_bpm']:.0f} BPM, {len(result['analysis']['beat_timestamps'])} beats")
            else:
                logger.error(f"Audio analysis failed: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Failed to analyze audio {Path(media_asset.file_path).name}: {e}")
        
        return media_asset
    
    async def _analyze_audio_semantic(self, media_asset: MediaAsset) -> MediaAsset:
        """Analyze semantic audio content."""
        try:
            log_update(logger, f"Analyzing audio semantics: {Path(media_asset.file_path).name}")
            
            # Call the semantic audio analysis tool
            from ..tools.semantic_audio_analysis import analyze_audio_semantics
            result = await analyze_audio_semantics(media_asset.file_path)
            
            if result["status"] == "success":
                # Update media asset with analysis
                media_asset.semantic_audio_analysis = result["analysis"]
                if result['analysis'].get('summary'):
                    log_update(logger, f"Semantic analysis complete: {result['analysis']['summary'][:50]}...")
            else:
                logger.error(f"Semantic audio analysis failed: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Failed to analyze audio semantics {Path(media_asset.file_path).name}: {e}")
        
        return media_asset
    # Note: _analyze_video_audio and _extract_audio_from_video methods removed
    # Video audio is now analyzed as part of Gemini's comprehensive video analysis
    # which provides speech transcription, sound effect detection, and audio segmentation


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
        status=ProjectStatus(phase="analyzing")
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