"""RootAgent - Central orchestrator for Memory Movie Maker."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
import uuid
from pathlib import Path

try:
    from google.adk.agents import Agent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    
from ..models.project_state import ProjectState, UserInputs, ProjectStatus
from ..models.media_asset import MediaAsset, MediaType
from ..storage.filesystem import FilesystemStorage
from ..agents.analysis_agent import AnalysisAgent
from ..agents.composition_agent import CompositionAgent
from ..agents.evaluation_agent import EvaluationAgent  
from ..agents.refinement_agent import RefinementAgent
from ..utils.simple_logger import log_start, log_complete

logger = logging.getLogger(__name__)


class RootAgent:
    """Central orchestrator that manages the entire workflow."""
    
    def __init__(self, storage_path: str = "./data"):
        """Initialize root agent with sub-agents."""
        # Storage for saving project states
        self.storage = FilesystemStorage(storage_path)
        
        # Initialize sub-agents
        self.analysis_agent = AnalysisAgent()
        self.composition_agent = CompositionAgent()
        self.evaluation_agent = EvaluationAgent()
        self.refinement_agent = RefinementAgent()
        
        # Configuration
        self.max_refinement_iterations = 3
        self.min_acceptable_score = 7.0
        
        logger.info("RootAgent initialized with all sub-agents")
    
    async def create_memory_movie(
        self,
        media_paths: List[str],
        user_prompt: str,
        music_path: Optional[str] = None,
        target_duration: int = 60,
        style: str = "auto",
        auto_refine: bool = True
    ) -> Dict[str, Any]:
        """Main entry point for creating a memory movie.
        
        Args:
            media_paths: List of paths to media files
            user_prompt: User's description of desired video
            music_path: Optional path to background music
            target_duration: Target video duration in seconds
            style: Style preference (auto, smooth, dynamic, fast)
            auto_refine: Whether to auto-refine using evaluation
            
        Returns:
            Result dictionary with video path and metadata
        """
        try:
            log_start(logger, "Creating memory movie")
            
            # Phase 1: Initialize project
            logger.info("Phase 1: Initializing project")
            project_state = await self._initialize_project(
                media_paths, user_prompt, music_path, target_duration, style
            )
            
            # Save initial state
            await self._save_project_state(project_state)
            
            # Phase 2: Analyze media
            logger.info("Phase 2: Analyzing media")
            project_state = await self.analysis_agent.analyze_project(project_state)
            
            # Phase 3: Create initial video
            logger.info("Phase 3: Creating initial video")
            project_state = await self.composition_agent.create_memory_movie(
                project_state=project_state,
                style=style
            )
            
            if not auto_refine:
                # Return immediately without refinement
                log_complete(logger, "Initial video created without refinement")
                return {
                    "status": "success",
                    "video_path": project_state.rendered_outputs[-1] if project_state.rendered_outputs else None,
                    "project_state": project_state,
                    "message": "Initial video created (no auto-refinement)",
                    "refinement_iterations": 0
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
                    logger.error(f"Evaluation failed: {evaluation_result.get('error')}")
                    break
                
                # Update project state with evaluation
                project_state = evaluation_result["updated_state"]
                evaluation = evaluation_result["evaluation"]
                
                # Check if video is acceptable
                score = evaluation.get("overall_score", 0)
                recommendation = evaluation.get("recommendation", "")
                
                if score >= self.min_acceptable_score and recommendation == "accept":
                    logger.info("Video meets acceptance criteria!")
                    break
                
                if recommendation == "major_rework":
                    logger.info("Major rework needed - recreating from scratch")
                    # Clear timeline to force recreation
                    project_state.timeline = None
                    project_state = await self.composition_agent.create_memory_movie(
                        project_state=project_state,
                        style=style
                    )
                else:
                    # Apply refinements
                    logger.info("Applying refinements based on evaluation")
                    
                    # Get edit commands from evaluation feedback
                    refinement_result = await self.refinement_agent.process_evaluation_feedback(
                        evaluation_feedback=evaluation,
                        project_state=project_state
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
                            style=style,
                            skip_composition=True  # Keep existing timeline
                        )
                
                refinement_count += 1
            
            # Phase 5: Finalize and save
            logger.info("Phase 5: Finalizing project")
            project_state.project_status.phase = "completed"
            project_state.project_status.progress = 100
            
            # Save final state
            await self._save_project_state(project_state)
            
            final_video_path = project_state.rendered_outputs[-1] if project_state.rendered_outputs else None
            final_score = project_state.evaluation_results.get("overall_score", 0) if project_state.evaluation_results else 0
            
            log_complete(logger, f"Memory movie created: {final_video_path}")
            
            return {
                "status": "success",
                "video_path": final_video_path,
                "project_state": project_state,
                "refinement_iterations": refinement_count,
                "final_score": final_score,
                "message": f"Video created with {refinement_count} refinement iterations"
            }
            
        except Exception as e:
            logger.error(f"Failed to create memory movie: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def process_user_feedback(
        self,
        project_state: ProjectState,
        user_feedback: str
    ) -> Dict[str, Any]:
        """Process user feedback and apply changes.
        
        Args:
            project_state: Current project state
            user_feedback: User's feedback text
            
        Returns:
            Result with updated video path
        """
        try:
            log_start(logger, "Processing user feedback")
            
            # Parse user intent
            intent_result = await self.refinement_agent.parse_user_edit_request(
                user_feedback=user_feedback,
                project_state=project_state
            )
            
            if intent_result["status"] != "success":
                return intent_result
            
            intent = intent_result["intent"]
            
            if intent == "evaluate":
                # User wants evaluation
                evaluation_result = await self.evaluation_agent.evaluate_memory_movie(
                    project_state=project_state
                )
                return evaluation_result
            
            elif intent == "edit":
                # Convert feedback to edit commands
                refinement_result = await self.refinement_agent.process_evaluation_feedback(
                    evaluation_feedback={"user_feedback": user_feedback},
                    project_state=project_state
                )
                
                if refinement_result["status"] == "success":
                    # Apply edits
                    project_state = await self.composition_agent.apply_edit_commands(
                        project_state=project_state,
                        edit_commands=refinement_result["edit_commands"]
                    )
                    
                    # Re-render
                    style = project_state.user_inputs.style_preferences.get("style", "auto")
                    project_state = await self.composition_agent.create_memory_movie(
                        project_state=project_state,
                        style=style,
                        skip_composition=True
                    )
                    
                    # Save updated state
                    await self._save_project_state(project_state)
                    
                    return {
                        "status": "success",
                        "video_path": project_state.rendered_outputs[-1],
                        "project_state": project_state,
                        "message": "Feedback applied successfully"
                    }
            
            elif intent == "regenerate":
                # Full regeneration requested
                style = project_state.user_inputs.style_preferences.get("style", "auto")
                project_state = await self.composition_agent.create_memory_movie(
                    project_state=project_state,
                    style=style
                )
                
                await self._save_project_state(project_state)
                
                return {
                    "status": "success",
                    "video_path": project_state.rendered_outputs[-1],
                    "project_state": project_state,
                    "message": "Video regenerated"
                }
            
            return {
                "status": "error",
                "error": f"Unknown intent: {intent}"
            }
            
        except Exception as e:
            logger.error(f"Failed to process feedback: {e}")
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
        """Initialize project state from user inputs."""
        # Create media assets
        media_assets = []
        
        # Add main media files
        for path in media_paths:
            media_type = self._detect_media_type(path)
            if media_type:
                asset = MediaAsset(
                    id=str(uuid.uuid4()),
                    file_path=path,
                    type=media_type,
                    metadata={}
                )
                media_assets.append(asset)
        
        # Add music if provided
        if music_path:
            music_asset = MediaAsset(
                id=str(uuid.uuid4()),
                file_path=music_path,
                type=MediaType.AUDIO,
                metadata={"role": "background_music"}
            )
            media_assets.append(music_asset)
        
        # Create user inputs
        user_inputs = UserInputs(
            media=media_assets,
            initial_prompt=user_prompt,
            target_duration=target_duration,
            style_preferences={"style": style}
        )
        
        # Create project state
        project_state = ProjectState(
            project_id=str(uuid.uuid4()),
            user_inputs=user_inputs,
            project_status=ProjectStatus(
                phase="analyzing",
                progress=10,
                current_task="Initializing project"
            )
        )
        
        return project_state
    
    def _detect_media_type(self, file_path: str) -> Optional[MediaType]:
        """Detect media type from file extension."""
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return MediaType.IMAGE
        elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            return MediaType.VIDEO
        elif ext in ['.mp3', '.wav', '.aac', '.m4a', '.flac']:
            return MediaType.AUDIO
        
        return None
    
    async def _save_project_state(self, project_state: ProjectState):
        """Save project state to storage."""
        await self.storage.save_project(
            project_state.project_id,
            project_state.model_dump()
        )


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
        print("\n✅ Memory movie created successfully!")
        print(f"Video path: {result['video_path']}")
        print(f"Refinement iterations: {result['refinement_iterations']}")
        print(f"Final score: {result['final_score']}")
        
        # Test user feedback
        print("\n==> Testing user feedback...")
        feedback_result = await root_agent.process_user_feedback(
            project_state=result["project_state"],
            user_feedback="Make it 15 seconds long with smoother transitions"
        )
        
        if feedback_result["status"] == "success":
            print(f"✅ Feedback applied! New video: {feedback_result['video_path']}")
    else:
        print(f"\n❌ Failed: {result['error']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_root_agent())