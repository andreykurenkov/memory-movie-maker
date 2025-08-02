"""Root agent orchestrator for the Memory Movie Maker system."""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
import uuid

from ..models.project_state import ProjectState, UserInputs, ProjectStatus
from ..models.media_asset import MediaAsset, MediaType
from ..storage.interface import StorageInterface
from ..storage.filesystem import FilesystemStorage

# Import all agents
from .analysis_agent import AnalysisAgent
from .composition_agent import CompositionAgent
from .evaluation_agent import EvaluationAgent
from .refinement_agent import RefinementAgent


logger = logging.getLogger(__name__)


class RootAgent:
    """Orchestrates the entire Memory Movie Maker workflow."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
        """Initialize root agent with all sub-agents.
        
        Args:
            storage: Storage interface for file management
        """
        self.storage = storage or FilesystemStorage(base_path="./data")
        
        # Initialize all agents
        self.analysis_agent = AnalysisAgent(storage=self.storage)
        self.composition_agent = CompositionAgent(storage=self.storage)
        self.evaluation_agent = EvaluationAgent()
        self.refinement_agent = RefinementAgent()
        
        # Configuration
        self.max_refinement_iterations = 3
        self.min_acceptable_score = 7.0
    
    async def create_memory_movie(
        self,
        media_paths: List[str],
        user_prompt: str,
        music_path: Optional[str] = None,
        target_duration: int = 60,
        style: str = "auto",
        auto_refine: bool = True
    ) -> Dict[str, Any]:
        """Create a complete memory movie from raw media files.
        
        Args:
            media_paths: List of paths to media files
            user_prompt: User's description of desired video
            music_path: Optional path to music file
            target_duration: Target video duration in seconds
            style: Video style (auto, smooth, dynamic, fast)
            auto_refine: If True, automatically refine based on evaluation
            
        Returns:
            Result dictionary with final video path and project state
        """
        try:
            logger.info("Starting Memory Movie Maker workflow")
            
            # Phase 1: Initialize project state
            project_state = await self._initialize_project(
                media_paths, user_prompt, music_path, target_duration, style
            )
            
            # Phase 2: Analysis
            logger.info("Phase 2: Analyzing media files...")
            project_state = await self.analysis_agent.analyze_project(project_state)
            
            # Phase 3: Composition
            logger.info("Phase 3: Creating initial composition...")
            project_state = await self.composition_agent.create_memory_movie(
                project_state=project_state,
                target_duration=target_duration,
                style=style,
                preview_only=True
            )
            
            if not auto_refine:
                # Return after first composition if auto-refine is disabled
                return {
                    "status": "success",
                    "video_path": project_state.rendered_outputs[-1],
                    "project_state": project_state,
                    "message": "Initial video created. Auto-refinement disabled."
                }
            
            # Phase 4: Self-correction loop
            refinement_count = 0
            while refinement_count < self.max_refinement_iterations:
                logger.info(f"Phase 4: Self-correction iteration {refinement_count + 1}")
                
                # Evaluate current video
                evaluation_result = await self.evaluation_agent.evaluate_memory_movie(
                    project_state=project_state
                )
                
                if evaluation_result["status"] != "success":
                    logger.warning("Evaluation failed, skipping refinement")
                    break
                
                evaluation = evaluation_result["evaluation"]
                project_state = evaluation_result["updated_state"]
                
                # Check if video is acceptable
                score = evaluation.get("overall_score", 0)
                recommendation = evaluation.get("recommendation", "")
                
                logger.info(f"Evaluation score: {score}/10, recommendation: {recommendation}")
                
                if score >= self.min_acceptable_score and recommendation == "accept":
                    logger.info("Video meets acceptance criteria!")
                    break
                
                if recommendation == "major_rework":
                    logger.warning("Major rework recommended, recreating from scratch...")
                    # Reset timeline and recreate
                    project_state.timeline = None
                    project_state = await self.composition_agent.create_memory_movie(
                        project_state=project_state,
                        target_duration=target_duration,
                        style=style,
                        preview_only=True
                    )
                else:
                    # Parse refinements
                    refinement_result = await self.refinement_agent.process_evaluation_feedback(
                        project_state=project_state,
                        evaluation_results=evaluation
                    )
                    
                    if refinement_result["status"] == "success" and refinement_result["edit_commands"]:
                        # Apply edits
                        logger.info(f"Applying edits: {refinement_result['summary']}")
                        project_state = await self.composition_agent.apply_edit_commands(
                            project_state=project_state,
                            edit_commands=refinement_result["edit_commands"]
                        )
                        
                        # Re-render with edits
                        project_state = await self.composition_agent.create_memory_movie(
                            project_state=project_state,
                            target_duration=target_duration,
                            style=style,
                            preview_only=True
                        )
                
                refinement_count += 1
            
            # Phase 5: Final render in full quality
            logger.info("Phase 5: Creating final high-quality render...")
            project_state = await self.composition_agent.create_memory_movie(
                project_state=project_state,
                target_duration=target_duration,
                style=style,
                preview_only=False
            )
            
            # Save project state
            await self._save_project_state(project_state)
            
            return {
                "status": "success",
                "video_path": project_state.rendered_outputs[-1],
                "project_state": project_state,
                "refinement_iterations": refinement_count,
                "final_score": project_state.evaluation_results.get("overall_score", "N/A")
            }
            
        except Exception as e:
            logger.error(f"Memory movie creation failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def process_user_feedback(
        self,
        project_state: ProjectState,
        user_feedback: str
    ) -> Dict[str, Any]:
        """Process user feedback and apply requested changes.
        
        Args:
            project_state: Current project state
            user_feedback: User's feedback or edit request
            
        Returns:
            Result with updated video and project state
        """
        try:
            logger.info("Processing user feedback...")
            
            # Parse user request
            request_result = await self.refinement_agent.parse_user_edit_request(
                user_request=user_feedback,
                project_state=project_state
            )
            
            if request_result["status"] != "success":
                return request_result
            
            intent = request_result["intent"]
            parameters = request_result["parameters"]
            
            if intent == "evaluate":
                # Run evaluation
                return await self.evaluation_agent.evaluate_memory_movie(project_state)
            
            elif intent == "edit":
                # Parse into edit commands
                if project_state.evaluation_results:
                    refinement_result = await self.refinement_agent.process_evaluation_feedback(
                        project_state=project_state,
                        evaluation_results=project_state.evaluation_results,
                        user_feedback=user_feedback
                    )
                    
                    if refinement_result["status"] == "success":
                        # Apply edits
                        project_state = await self.composition_agent.apply_edit_commands(
                            project_state=project_state,
                            edit_commands=refinement_result["edit_commands"]
                        )
                        
                        # Re-render
                        project_state = await self.composition_agent.create_memory_movie(
                            project_state=project_state,
                            target_duration=parameters.get("duration", project_state.user_inputs.target_duration),
                            style=parameters.get("style", "auto"),
                            preview_only=parameters.get("quality", "preview") == "preview"
                        )
                
                return {
                    "status": "success",
                    "video_path": project_state.rendered_outputs[-1],
                    "project_state": project_state
                }
            
            elif intent == "create":
                # Create new video with parameters
                return await self.create_memory_movie(
                    media_paths=[m.file_path for m in project_state.user_inputs.media],
                    user_prompt=user_feedback,
                    target_duration=parameters.get("duration", 60),
                    style=parameters.get("style", "auto")
                )
            
            else:
                return {
                    "status": "error",
                    "error": f"Unknown intent: {intent}"
                }
                
        except Exception as e:
            logger.error(f"User feedback processing failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _initialize_project(
        self,
        media_paths: List[str],
        user_prompt: str,
        music_path: Optional[str],
        target_duration: int,
        style: str
    ) -> ProjectState:
        """Initialize project state with media files."""
        media_assets = []
        
        # Process media files
        for path in media_paths:
            media_type = self._detect_media_type(path)
            if media_type:
                asset = MediaAsset(
                    id=str(uuid.uuid4()),
                    file_path=path,
                    type=media_type
                )
                media_assets.append(asset)
        
        # Add music if provided
        if music_path:
            music_asset = MediaAsset(
                id=str(uuid.uuid4()),
                file_path=music_path,
                type=MediaType.AUDIO
            )
            media_assets.append(music_asset)
        
        # Create project state
        project_state = ProjectState(
            user_inputs=UserInputs(
                media=media_assets,
                initial_prompt=user_prompt,
                target_duration=target_duration,
                style_preferences={"style": style}
            ),
            project_status=ProjectStatus(phase="analyzing")
        )
        
        logger.info(f"Initialized project with {len(media_assets)} media files")
        return project_state
    
    def _detect_media_type(self, file_path: str) -> Optional[MediaType]:
        """Detect media type from file extension."""
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            return MediaType.IMAGE
        elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']:
            return MediaType.VIDEO
        elif ext in ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']:
            return MediaType.AUDIO
        else:
            logger.warning(f"Unknown file type: {ext}")
            return None
    
    async def _save_project_state(self, project_state: ProjectState):
        """Save project state to storage."""
        try:
            project_id = project_state.project_id or str(uuid.uuid4())
            await self.storage.save_project(project_id, project_state.model_dump())
            logger.info(f"Project state saved: {project_id}")
        except Exception as e:
            logger.error(f"Failed to save project state: {e}")


# Standalone function for testing
async def test_root_agent():
    """Test the root agent with sample media."""
    import os
    
    # Check if test files exist
    test_files = [
        "data/test_inputs/test_video.mp4",
        "data/test_inputs/test_song.mp3"
    ]
    
    existing_files = [f for f in test_files if os.path.exists(f)]
    
    if not existing_files:
        print("No test files found. Please add media files to data/test_inputs/")
        return
    
    # Create root agent
    root_agent = RootAgent()
    
    # Test complete workflow
    result = await root_agent.create_memory_movie(
        media_paths=existing_files[:1],  # Just use first file
        user_prompt="Create a dynamic test video with smooth transitions",
        music_path=existing_files[1] if len(existing_files) > 1 else None,
        target_duration=10,
        style="dynamic",
        auto_refine=True
    )
    
    if result["status"] == "success":
        print(f"\n Memory movie created successfully!")
        print(f"Video path: {result['video_path']}")
        print(f"Refinement iterations: {result['refinement_iterations']}")
        print(f"Final score: {result['final_score']}")
        
        # Test user feedback
        print("\n=Ý Testing user feedback...")
        feedback_result = await root_agent.process_user_feedback(
            project_state=result["project_state"],
            user_feedback="Make it 15 seconds long with smoother transitions"
        )
        
        if feedback_result["status"] == "success":
            print(f" Feedback applied! New video: {feedback_result['video_path']}")
    else:
        print(f"\nL Failed: {result['error']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_root_agent())