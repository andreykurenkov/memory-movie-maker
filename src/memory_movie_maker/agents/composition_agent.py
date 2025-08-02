"""Composition agent for creating and rendering videos."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from google.adk.agents import Agent

from ..tools.composition import compose_timeline_tool
from ..tools.video_renderer import render_video_tool
from ..models.project_state import ProjectState
from ..storage.interface import StorageInterface
from ..storage.filesystem import FilesystemStorage


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
            model="gemini-2.0-flash",
            description="Creates video timelines and renders final videos",
            instruction="""You are an expert video editor. Your responsibilities:
            1. Create compelling video timelines from analyzed media
            2. Sync video cuts to music beats when available
            3. Apply appropriate transitions and effects
            4. Render high-quality videos
            5. Create preview versions for quick feedback
            
            Guidelines:
            - Match video energy to music dynamics
            - Group similar content together
            - Use smooth transitions by default
            - Keep clips between 1-5 seconds
            - Prioritize high-quality media
            
            When creating timelines:
            - First use compose_timeline to create the edit
            - Then use render_video to create the output
            - Always create a preview first (preview=true, 640x360)
            - Only render full quality after approval""",
            tools=[compose_timeline_tool, render_video_tool]
        )
    
    @property
    def storage(self) -> StorageInterface:
        """Get storage interface."""
        return _agent_storage
    
    async def create_memory_movie(
        self,
        project_state: ProjectState,
        target_duration: int = 60,
        style: str = "auto",
        preview_only: bool = True
    ) -> ProjectState:
        """Create a memory movie from analyzed media.
        
        Args:
            project_state: Current project state with analyzed media
            target_duration: Target video duration in seconds
            style: Video style (auto, smooth, dynamic, fast)
            preview_only: If True, only render preview quality
            
        Returns:
            Updated project state with timeline and rendered output
        """
        try:
            logger.info(f"Creating memory movie: {target_duration}s, style={style}")
            
            # Validate we have analyzed media
            if not project_state.user_inputs.media:
                raise ValueError("No media files found in project")
            
            analyzed_count = sum(
                1 for m in project_state.user_inputs.media
                if m.gemini_analysis or m.audio_analysis
            )
            
            if analyzed_count == 0:
                raise ValueError("No analyzed media found. Run AnalysisAgent first.")
            
            # Create timeline
            logger.info("Creating timeline...")
            timeline_result = await compose_timeline_tool.run(
                project_state=project_state.model_dump(),
                target_duration=target_duration,
                style=style
            )
            
            if timeline_result["status"] != "success":
                raise RuntimeError(f"Timeline creation failed: {timeline_result.get('error')}")
            
            # Update state with timeline
            project_state = ProjectState(**timeline_result["updated_state"])
            logger.info(f"Timeline created with {len(project_state.timeline.segments)} segments")
            
            # Determine output filename
            output_name = f"memory_movie_{'preview' if preview_only else 'final'}.mp4"
            
            # Render video
            logger.info(f"Rendering {'preview' if preview_only else 'final'} video...")
            render_result = await render_video_tool.run(
                project_state=project_state.model_dump(),
                output_filename=output_name,
                resolution="640x360" if preview_only else "1920x1080",
                preview=preview_only
            )
            
            if render_result["status"] != "success":
                raise RuntimeError(f"Video rendering failed: {render_result.get('error')}")
            
            # Update state with rendered output
            project_state = ProjectState(**render_result["updated_state"])
            
            # Update project phase
            if project_state.project_status.phase == "composing":
                project_state.project_status.phase = "evaluating"
            
            logger.info(f"Video rendered successfully: {render_result['output_path']}")
            
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
                segments_dict = {s.media_id: s for s in timeline.segments}
                timeline.segments = [segments_dict[media_id] for media_id in new_order]
            
            if "adjust_durations" in edit_commands:
                # Adjust segment durations
                duration_changes = edit_commands["adjust_durations"]
                for segment in timeline.segments:
                    if segment.media_id in duration_changes:
                        segment.duration = duration_changes[segment.media_id]
            
            if "change_transitions" in edit_commands:
                # Change transition types
                transition_changes = edit_commands["change_transitions"]
                for segment in timeline.segments:
                    if segment.media_id in transition_changes:
                        segment.transition_out = transition_changes[segment.media_id]
            
            if "add_effects" in edit_commands:
                # Add effects to segments
                effect_changes = edit_commands["add_effects"]
                for segment in timeline.segments:
                    if segment.media_id in effect_changes:
                        segment.effects.extend(effect_changes[segment.media_id])
            
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
        project_status=ProjectStatus(phase="composing")
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