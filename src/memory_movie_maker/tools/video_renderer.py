"""Video rendering tool using MoviePy."""

import logging
from typing import Dict, Any, List, Tuple, Optional
import tempfile
from pathlib import Path

from google.adk.tools import FunctionTool
from moviepy.editor import (
    VideoFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips, AudioFileClip, ColorClip
)
from moviepy.video.fx import resize
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout

from ..models.timeline import Timeline, TimelineSegment, TransitionType
from ..models.media_asset import MediaAsset, MediaType
from ..models.project_state import ProjectState
from ..storage.interface import StorageInterface
from ..storage.filesystem import FilesystemStorage


logger = logging.getLogger(__name__)

# Module-level storage
_renderer_storage: Optional[StorageInterface] = None


class VideoRenderer:
    """Renders final video from timeline."""
    
    def __init__(self, storage: Optional[StorageInterface] = None):
        """Initialize video renderer.
        
        Args:
            storage: Storage interface for accessing media files
        """
        global _renderer_storage
        _renderer_storage = storage or FilesystemStorage(base_path="./data")
        self.storage = _renderer_storage
        self.default_resolution = (1920, 1080)
        self.fps = 30
    
    async def render_video(
        self,
        timeline: Timeline,
        media_assets: Dict[str, MediaAsset],
        output_path: str,
        resolution: Tuple[int, int] = None,
        preview_mode: bool = False
    ) -> str:
        """Render timeline to video file.
        
        Args:
            timeline: Timeline with segments to render
            media_assets: Dictionary of media assets by ID
            output_path: Output video file path
            resolution: Video resolution (width, height)
            preview_mode: If True, render lower quality for speed
            
        Returns:
            Path to rendered video
        """
        resolution = resolution or self.default_resolution
        
        if preview_mode:
            # Lower resolution for faster preview
            resolution = (640, 360)
            self.fps = 15
        
        try:
            # Create clips for each segment
            clips = []
            for segment in timeline.segments:
                clip = await self._create_clip_from_segment(
                    segment, media_assets, resolution
                )
                if clip:
                    clips.append(clip)
            
            if not clips:
                raise ValueError("No valid clips created from timeline")
            
            # Apply transitions
            final_clips = self._apply_transitions(clips, timeline.segments)
            
            # Concatenate all clips
            video = concatenate_videoclips(final_clips, method="compose")
            
            # Add audio track if specified
            if timeline.music_track_id:
                video = self._add_audio_track(video, timeline.music_track_id)
            
            # Write output
            logger.info(f"Rendering video to {output_path}")
            video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=tempfile.mktemp('.m4a'),
                remove_temp=True,
                preset='fast' if preview_mode else 'medium'
            )
            
            # Clean up
            video.close()
            for clip in clips:
                clip.close()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Video rendering failed: {e}")
            raise
    
    async def _create_clip_from_segment(
        self,
        segment: TimelineSegment,
        media_assets: Dict[str, MediaAsset],
        resolution: Tuple[int, int]
    ) -> Optional[VideoFileClip]:
        """Create a MoviePy clip from a timeline segment."""
        media = media_assets.get(segment.media_asset_id)
        if not media:
            logger.warning(f"Media asset not found: {segment.media_asset_id}")
            return None
        
        try:
            if media.type == MediaType.IMAGE:
                logger.debug(f"Creating image clip for {media.file_path}")
                clip = self._create_image_clip(media, segment, resolution)
            elif media.type == MediaType.VIDEO:
                logger.debug(f"Creating video clip for {media.file_path}")
                clip = self._create_video_clip(media, segment, resolution)
            else:
                logger.warning(f"Unsupported media type: {media.type}")
                return None
            
            # Apply effects
            if "ken_burns" in segment.effects:
                clip = self._apply_ken_burns(clip, segment.duration)
            
            return clip
            
        except Exception as e:
            logger.error(f"Failed to create clip from {media.file_path}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _create_image_clip(
        self,
        media: MediaAsset,
        segment: TimelineSegment,
        resolution: Tuple[int, int]
    ) -> ImageClip:
        """Create clip from image file."""
        clip = ImageClip(media.file_path, duration=segment.duration)
        
        # Resize to fit resolution while maintaining aspect ratio
        clip = self._resize_clip(clip, resolution)
        
        return clip
    
    def _create_video_clip(
        self,
        media: MediaAsset,
        segment: TimelineSegment,
        resolution: Tuple[int, int]
    ) -> VideoFileClip:
        """Create clip from video file."""
        clip = VideoFileClip(media.file_path)
        original_duration = clip.duration
        
        logger.debug(f"Original video duration: {original_duration:.2f}s, segment needs {segment.duration:.2f}s")
        
        # Apply trimming if specified
        if segment.in_point > 0 or segment.out_point:
            # Ensure in_point is within bounds
            in_point = min(segment.in_point, max(0, clip.duration - 0.1))
            end_time = segment.out_point or clip.duration
            # Ensure end_time is within bounds and after in_point
            end_time = min(end_time, clip.duration)
            end_time = max(end_time, in_point + 0.1)  # At least 0.1s duration
            
            if in_point < clip.duration:
                clip = clip.subclip(in_point, end_time)
                logger.debug(f"Trimmed clip from {in_point:.2f}s to {end_time:.2f}s, new duration: {clip.duration:.2f}s")
            else:
                logger.warning(f"In point {in_point} exceeds video duration {clip.duration}, using full clip")
        
        # For very short clips that need to be extended
        if clip.duration < segment.duration:
            # Calculate how many loops we need
            loops_needed = int(segment.duration / clip.duration) + 1
            logger.debug(f"Looping clip {loops_needed} times to reach {segment.duration:.2f}s")
            
            # Loop the clip
            clip = clip.loop(n=loops_needed)
            
            # Trim to exact duration
            clip = clip.subclip(0, segment.duration)
        elif clip.duration > segment.duration:
            # Trim to exact duration
            clip = clip.subclip(0, segment.duration)
        
        # Resize to fit resolution
        clip = self._resize_clip(clip, resolution)
        
        return clip
    
    def _resize_clip(self, clip: VideoFileClip, resolution: Tuple[int, int]) -> VideoFileClip:
        """Resize clip to fit resolution while maintaining aspect ratio."""
        target_w, target_h = resolution
        clip_w, clip_h = clip.size
        
        # Calculate scale to fit
        scale = min(target_w / clip_w, target_h / clip_h)
        new_size = (int(clip_w * scale), int(clip_h * scale))
        
        # Resize
        clip = clip.resize(newsize=new_size)
        
        # Center on background if needed
        if new_size != resolution:
            # Create black background
            bg = ColorClip(size=resolution, color=(0, 0, 0), duration=clip.duration)
            # Center the clip
            x_pos = (target_w - new_size[0]) // 2
            y_pos = (target_h - new_size[1]) // 2
            clip = CompositeVideoClip([bg, clip.set_position((x_pos, y_pos))])
        
        return clip
    
    def _apply_ken_burns(self, clip: ImageClip, duration: float) -> ImageClip:
        """Apply Ken Burns effect (zoom/pan) to image."""
        # For now, just return the clip as-is
        # TODO: Implement proper Ken Burns effect with resize over time
        return clip
    
    def _apply_transitions(
        self,
        clips: List[VideoFileClip],
        segments: List[TimelineSegment]
    ) -> List[VideoFileClip]:
        """Apply transitions between clips."""
        if len(clips) <= 1:
            return clips
        
        final_clips = []
        transition_duration = 0.5
        
        for i, (clip, segment) in enumerate(zip(clips, segments)):
            if segment.transition_out == TransitionType.CROSSFADE and i < len(clips) - 1:
                # Apply fade out to current clip
                clip = fadeout(clip, transition_duration)
                # Apply fade in to next clip
                next_clip = clips[i + 1]
                next_clip = fadein(next_clip, transition_duration)
                
            elif segment.transition_out == TransitionType.FADE_TO_BLACK:
                clip = fadeout(clip, transition_duration)
                # Add black frame
                black = ColorClip(size=clip.size, color=(0, 0, 0), duration=0.5)
                final_clips.append(clip)
                final_clips.append(black)
                continue
            
            final_clips.append(clip)
        
        return final_clips
    
    def _add_audio_track(self, video: VideoFileClip, audio_path: str) -> VideoFileClip:
        """Add audio track to video."""
        try:
            audio = AudioFileClip(audio_path)
            
            # Trim audio to match video duration
            if audio.duration > video.duration:
                audio = audio.subclip(0, video.duration)
            
            # Set audio using set_audio method
            video = video.set_audio(audio)
            
            return video
            
        except Exception as e:
            logger.error(f"Failed to add audio track: {e}")
            return video


# Create the render tool function
async def render_video(
    project_state: Dict[str, Any],
    output_filename: str = "output.mp4",
    resolution: str = "1920x1080",
    preview: bool = False
) -> Dict[str, Any]:
    """Render video from timeline.
    
    Args:
        project_state: Current project state with timeline
        output_filename: Output video filename
        resolution: Video resolution (e.g., "1920x1080", "1280x720")
        preview: If True, render lower quality preview
        
    Returns:
        Result with output path or error
    """
    try:
        # Parse project state
        state = ProjectState(**project_state)
        
        if not state.timeline:
            return {
                "status": "error",
                "error": "No timeline found in project state"
            }
        
        # Parse resolution
        width, height = map(int, resolution.split('x'))
        
        # Create media asset dictionary
        media_dict = {asset.id: asset for asset in state.user_inputs.media}
        
        # Determine output path
        output_dir = Path("./data/renders")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / output_filename)
        
        # Initialize renderer
        renderer = VideoRenderer()
        
        # Render video
        rendered_path = await renderer.render_video(
            timeline=state.timeline,
            media_assets=media_dict,
            output_path=output_path,
            resolution=(width, height),
            preview_mode=preview
        )
        
        # Update project state
        state.output_path = rendered_path
        
        logger.info(f"Video rendered successfully: {rendered_path}")
        
        return {
            "status": "success",
            "output_path": rendered_path,
            "updated_state": state.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Video rendering failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Create ADK tool
render_video_tool = FunctionTool(render_video)