"""Composition agent for creating and rendering videos."""

import logging
from typing import Dict, Any, Optional

from google.adk.agents import Agent

from ..tools.composition import compose_timeline_tool
from ..tools.edit_planner import plan_edit_tool
from ..tools.video_renderer import render_video_tool
from ..models.project_state import ProjectState
from ..models.aspect_ratio import AspectRatio
from ..storage.interface import StorageInterface
from ..storage.filesystem import FilesystemStorage
from ..config import settings
from ..utils.simple_logger import log_start, log_update, log_complete


logger = logging.getLogger(__name__)

# Module-level storage
_agent_storage: Optional[StorageInterface] = None


class CompositionAgent(Agent):
    """Agent responsible for composing timelines and rendering videos."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
        """Initialize composition agent.
        
        Args:
            storage: Storage interface for managing files
        """
        global _agent_storage
        _agent_storage = storage or FilesystemStorage(base_path="./data")
        
        super().__init__(
            name="CompositionAgent",
            model=settings.get_gemini_model_name(task="planning"),
            description="Creates intelligent video edits using AI planning and renders final videos",
            instruction="""You are an award-winning video editor using AI to create compelling memory movies.

            YOUR WORKFLOW:
            1. First, use plan_edit to create an intelligent edit plan with Gemini
            2. Then, use compose_timeline to execute the plan into a timeline
            3. Finally, use render_video to create the output video
            
            KEY RESPONSIBILITIES:
            - Create emotionally resonant videos that tell a story
            - Select clips that capture the essence of the memory
            - Sync key moments to music beats and energy
            - Apply smooth, professional transitions
            - Balance variety with coherence
            
            CREATIVE GUIDELINES:
            - NEVER repeat the same clip - use each media asset only ONCE
            - For long videos, use trim points to extract different segments
            - Maintain natural playback speed (1x) - no slow motion effects
            - Build narrative arcs with beginning, middle, and end
            - Match visual energy to musical dynamics
            - Use the highest quality and most relevant clips
            - Vary clip lengths: 1-6 seconds typically, 8 seconds maximum
            - Create videos people will want to watch multiple times
            
            TECHNICAL WORKFLOW:
            1. Always start with plan_edit to get an AI-generated edit plan
            2. Pass the edit_plan result to compose_timeline
            3. Create a preview first (preview=true, 640x360)
            4. Only render full quality after approval
            
            Remember: The AI planning step is crucial - it ensures intelligent
            clip selection and arrangement based on content understanding.""",
            tools=[plan_edit_tool, compose_timeline_tool, render_video_tool]
        )
    
    @property
    def storage(self) -> StorageInterface:
        """Get storage interface."""
        return _agent_storage
    
    async def create_memory_movie(
        self,
        project_state: ProjectState,
        target_duration: int = None,
        style: str = "auto",
        preview_only: bool = False
    ) -> ProjectState:
        """Create a memory movie from analyzed media.
        
        Args:
            project_state: Current project state with analyzed media
            target_duration: Target video duration in seconds (uses project state if not specified)
            style: Video style (auto, smooth, dynamic, fast)
            preview_only: If True, only render preview quality
            
        Returns:
            Updated project state with timeline and rendered output
        """
        try:
            # Use target duration from project state if not explicitly provided
            if target_duration is None:
                target_duration = project_state.user_inputs.target_duration
            
            log_start(logger, f"Creating memory movie: {target_duration}s, style={style}")
            
            # Validate we have analyzed media
            if not project_state.user_inputs.media:
                raise ValueError("No media files found in project")
            
            analyzed_count = sum(
                1 for m in project_state.user_inputs.media
                if m.gemini_analysis or m.audio_analysis
            )
            
            if analyzed_count == 0:
                raise ValueError("No analyzed media found. Run AnalysisAgent first.")
            
            # Step 1: Create AI edit plan
            log_update(logger, "Creating AI edit plan...")
            from ..tools.edit_planner import plan_edit
            plan_result = await plan_edit(
                project_state=project_state.model_dump(),
                target_duration=target_duration,
                style=style
            )
            
            if plan_result["status"] != "success":
                raise RuntimeError(f"Edit planning failed: {plan_result.get('error')}")
            
            log_update(logger, f"Edit plan created with {plan_result['segment_count']} segments")
            log_update(logger, f"Variety score: {plan_result.get('variety_score', 0):.2f}, Story coherence: {plan_result.get('story_coherence', 0):.2f}")
            
            # Step 2: Execute the edit plan into a timeline
            log_update(logger, "Executing edit plan into timeline...")
            from ..tools.composition import compose_timeline
            timeline_result = await compose_timeline(
                project_state=project_state.model_dump(),
                edit_plan=plan_result["edit_plan"],
                target_duration=target_duration,
                style=style
            )
            
            if timeline_result["status"] != "success":
                raise RuntimeError(f"Timeline creation failed: {timeline_result.get('error')}")
            
            # Update state with timeline
            project_state = ProjectState(**timeline_result["updated_state"])
            log_update(logger, f"Timeline created with {len(project_state.timeline.segments)} segments")
            
            # Determine output filename
            output_name = f"memory_movie_{'preview' if preview_only else 'final'}.mp4"
            
            # Get resolution based on aspect ratio
            aspect_ratio = project_state.user_inputs.aspect_ratio
            if isinstance(aspect_ratio, str):
                aspect_ratio = AspectRatio.from_string(aspect_ratio)
            resolution_str = aspect_ratio.get_resolution_string(preview=preview_only)
            
            # Render video
            log_update(logger, f"Rendering {'preview' if preview_only else 'final'} video at {resolution_str}...")
            from ..tools.video_renderer import render_video
            render_result = await render_video(
                project_state=project_state.model_dump(),
                output_filename=output_name,
                resolution=resolution_str,
                preview=preview_only
            )
            
            if render_result["status"] != "success":
                raise RuntimeError(f"Video rendering failed: {render_result.get('error')}")
            
            # Update state with rendered output
            project_state = ProjectState(**render_result["updated_state"])
            
            # Update project phase
            if project_state.status and project_state.status.phase == "composing":
                project_state.status.phase = "evaluating"
            
            log_complete(logger, f"Video rendered successfully: {render_result['output_path']}")
            
            return project_state
            
        except Exception as e:
            logger.error(f"Memory movie creation failed: {e}")
            raise
    
    async def apply_edit_commands(
        self,
        project_state: ProjectState,
        edit_commands: Dict[str, Any]
    ) -> ProjectState:
        """Apply edit commands to modify timeline.
        
        Args:
            project_state: Current project state with timeline
            edit_commands: Dictionary of edit commands
            
        Returns:
            Updated project state with modified timeline
        """
        try:
            logger.info(f"Applying edit commands: {edit_commands}")
            
            if not project_state.timeline:
                raise ValueError("No timeline found to edit")
            
            timeline = project_state.timeline
            
            # Process different edit commands
            if "reorder_segments" in edit_commands:
                # Reorder segments based on new order
                new_order = edit_commands["reorder_segments"]
                segments_dict = {s.media_asset_id: s for s in timeline.segments}
                timeline.segments = [segments_dict[media_id] for media_id in new_order]
            
            if "adjust_durations" in edit_commands:
                # Adjust segment durations
                duration_changes = edit_commands["adjust_durations"]
                for segment in timeline.segments:
                    if segment.media_asset_id in duration_changes:
                        segment.duration = duration_changes[segment.media_asset_id]
            
            if "change_transitions" in edit_commands:
                # Change transition types
                transition_changes = edit_commands["change_transitions"]
                for segment in timeline.segments:
                    if segment.media_asset_id in transition_changes:
                        segment.transition_out = transition_changes[segment.media_asset_id]
            
            if "add_effects" in edit_commands:
                # Add effects to segments
                effect_changes = edit_commands["add_effects"]
                for segment in timeline.segments:
                    if segment.media_asset_id in effect_changes:
                        segment.effects.extend(effect_changes[segment.media_asset_id])
            
            # Recalculate timeline duration and start times
            current_time = 0.0
            for segment in timeline.segments:
                segment.start_time = current_time
                current_time += segment.duration
            timeline.total_duration = current_time
            
            logger.info("Edit commands applied successfully")
            
            return project_state
            
        except Exception as e:
            logger.error(f"Failed to apply edit commands: {e}")
            raise


# Test function
async def test_composition_agent():
    """Test the composition agent."""
    from ..models.project_state import ProjectState, UserInputs, ProjectStatus
    from ..models.media_asset import MediaAsset, MediaType, GeminiAnalysis, AudioAnalysisProfile
    import uuid
    
    # Create test project with analyzed media
    test_media = [
        MediaAsset(
            id=str(uuid.uuid4()),
            file_path="data/test_inputs/test_video.mp4",
            type=MediaType.VIDEO,
            gemini_analysis=GeminiAnalysis(
                description="Test video",
                aesthetic_score=0.8
            )
        ),
        MediaAsset(
            id=str(uuid.uuid4()),
            file_path="data/test_inputs/test_song.mp3",
            type=MediaType.AUDIO,
            audio_analysis=AudioAnalysisProfile(
                file_path="data/test_inputs/test_song.mp3",
                beat_timestamps=[0.5, 1.0, 1.5, 2.0],
                tempo_bpm=120.0,
                energy_curve=[0.5, 0.6, 0.7, 0.6],
                duration=30.0
            )
        )
    ]
    
    project_state = ProjectState(
        user_inputs=UserInputs(
            media=test_media,
            initial_prompt="Create a test video"
        ),
        status=ProjectStatus(phase="composing")
    )
    
    # Create and test agent
    agent = CompositionAgent()
    updated_state = await agent.create_memory_movie(
        project_state=project_state,
        target_duration=10,
        style="dynamic",
        preview_only=True
    )
    
    print(f"Timeline segments: {len(updated_state.timeline.segments)}")
    print(f"Rendered outputs: {updated_state.rendered_outputs}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_composition_agent())