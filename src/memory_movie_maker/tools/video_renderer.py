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
from moviepy.video import fx as vfx

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
        # Professional video settings
        self.default_resolution = (1920, 1080)  # Full HD by default
        self.fps = 30  # Standard frame rate for smooth motion
        self.bitrate = "10M"  # High quality bitrate for crisp video
        self.preserve_original_audio = True  # Keep audio from video clips by default
        self.audio_mix_ratio = 0.8  # When mixing with music, original audio at 80% volume (dominant)
    
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
            resolution = (1280, 720)  # HD preview (better than 360p)
            self.fps = 24  # Use 24fps for preview (cinematic but faster than 30)
            bitrate = "4M"
        else:
            bitrate = self.bitrate  # Use high quality for final render
        
        clips = []
        final_clips = []
        video = None
        all_clips_to_cleanup = []  # Track ALL clips for cleanup
        
        try:
            # Create clips for each segment
            for segment in timeline.segments:
                clip = await self._create_clip_from_segment(
                    segment, media_assets, resolution
                )
                if clip:
                    clips.append(clip)
                    all_clips_to_cleanup.append(clip)
            
            if not clips:
                raise ValueError("No valid clips created from timeline")
            
            # Apply transitions (may create additional clips)
            final_clips = self._apply_transitions(clips, timeline.segments)
            
            # Track any new clips created by transitions
            for clip in final_clips:
                if clip not in all_clips_to_cleanup:
                    all_clips_to_cleanup.append(clip)
            
            # Concatenate all clips
            video = concatenate_videoclips(final_clips, method="compose")
            
            # Add audio track if specified
            if timeline.music_track_id:
                video = self._add_audio_track(video, timeline.music_track_id, timeline)
            else:
                # No background music, but we might have original audio from clips
                if video.audio is not None:
                    logger.info("No background music provided, using original audio from video clips")
                else:
                    logger.info("No background music or original audio, creating silent video")
            
            # Write output
            logger.info(f"Rendering video to {output_path}")
            video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                bitrate=bitrate if 'bitrate' in locals() else self.bitrate,
                preset='slow' if not preview_mode else 'medium',  # Better quality compression
                audio_bitrate="192k",  # High quality audio
                temp_audiofile=tempfile.mktemp('.m4a'),
                remove_temp=True
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Video rendering failed: {e}")
            raise
            
        finally:
            # Clean up ALL clips including video and any created during processing
            if video:
                video.close()
            # Clean up all tracked clips
            for clip in all_clips_to_cleanup:
                if clip:
                    try:
                        clip.close()
                    except Exception:
                        pass  # Ignore errors during cleanup
    
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
                
                # Handle audio mixing for this specific segment
                if clip.audio and segment.preserve_original_audio:
                    # Adjust the original audio volume for this segment
                    clip = clip.volumex(segment.original_audio_volume)
                    logger.debug(f"Preserving original audio at {segment.original_audio_volume*100:.0f}% volume")
                elif clip.audio and not segment.preserve_original_audio:
                    # Mute the original audio for this segment
                    clip = clip.without_audio()
                    logger.debug(f"Muting original audio from video clip")
            else:
                logger.warning(f"Unsupported media type: {media.type}")
                return None
            
            # Apply effects
            # Note: Ken Burns effect removed - not implemented
            
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
                # Note: The actual duration is now the trimmed duration, not the segment duration
            else:
                logger.warning(f"In point {in_point} exceeds video duration {clip.duration}, using full clip")
        else:
            # No trimming specified, use segment duration
            if clip.duration > segment.duration:
                # Trim to exact duration
                clip = clip.subclip(0, segment.duration)
                logger.debug(f"Trimmed clip to segment duration: {segment.duration:.2f}s")
            elif clip.duration < segment.duration:
                # Only pad if the original clip is shorter than needed (no trim points specified)
                logger.warning(f"Original clip ({clip.duration:.2f}s) shorter than segment ({segment.duration:.2f}s). Using available duration.")
                # Don't pad - just use what we have
        
        # Resize to fit resolution
        clip = self._resize_clip(clip, resolution)
        
        return clip
    
    def _resize_clip(self, clip: VideoFileClip, resolution: Tuple[int, int]) -> VideoFileClip:
        """Resize clip to fit resolution while maintaining aspect ratio with professional letterboxing."""
        target_w, target_h = resolution
        clip_w, clip_h = clip.size
        
        # Calculate aspect ratios
        target_aspect = target_w / target_h
        clip_aspect = clip_w / clip_h
        
        # Determine if we need letterboxing or pillarboxing
        if abs(clip_aspect - target_aspect) < 0.1:
            # Similar aspect ratio, just resize to fit exactly
            clip = clip.resize(newsize=resolution)
        else:
            # Calculate scale to fit while maintaining aspect ratio
            scale = min(target_w / clip_w, target_h / clip_h)
            new_size = (int(clip_w * scale), int(clip_h * scale))
            
            # Ensure dimensions are even (required for many codecs)
            new_size = (new_size[0] // 2 * 2, new_size[1] // 2 * 2)
            
            # Resize with high quality
            resized_clip = clip.resize(newsize=new_size)
            
            # Add professional letterboxing/pillarboxing
            if new_size != resolution:
                # Create subtle gradient background instead of pure black
                # This looks more professional than hard black bars
                bg = ColorClip(size=resolution, color=(16, 16, 16), duration=resized_clip.duration)
                
                # Center the clip
                x_pos = (target_w - new_size[0]) // 2
                y_pos = (target_h - new_size[1]) // 2
                # Note: CompositeVideoClip creates a new clip, bg is embedded
                clip = CompositeVideoClip([bg, resized_clip.set_position((x_pos, y_pos))])
            else:
                clip = resized_clip
        
        # Apply subtle color correction for more professional look
        # Slightly increase contrast and saturation
        try:
            from moviepy.video.fx.colorx import colorx
            clip = clip.fx(colorx, 1.1)  # Boost colors slightly
        except:
            # Skip color correction if not available
            pass
        
        return clip
    
    # Ken Burns effect removed - was not implemented
    
    def _apply_transitions(
        self,
        clips: List[VideoFileClip],
        segments: List[TimelineSegment]
    ) -> List[VideoFileClip]:
        """Apply transitions between clips.
        
        Returns list of clips INCLUDING any newly created transition clips.
        Caller is responsible for tracking these for cleanup.
        """
        if len(clips) <= 1:
            return clips
        
        final_clips = []
        # Professional transition timing
        transition_duration = 0.2  # Quick, barely noticeable fades (200ms)
        
        for i, (clip, segment) in enumerate(zip(clips, segments)):
            # Handle different transition types
            if segment.transition_out == TransitionType.CUT:
                # Crash cut - no transition effect, just append the clip
                final_clips.append(clip)
                
            elif segment.transition_out == TransitionType.FADE and i < len(clips) - 1:
                # Fade transition - fade out current, fade in next
                clip = fadeout(clip, transition_duration)
                if i + 1 < len(clips):
                    clips[i + 1] = fadein(clips[i + 1], transition_duration)
                final_clips.append(clip)
                
            elif segment.transition_out == TransitionType.CROSSFADE and i < len(clips) - 1:
                # Crossfade - overlapping fade
                clip = fadeout(clip, transition_duration)
                if i + 1 < len(clips):
                    clips[i + 1] = fadein(clips[i + 1], transition_duration)
                final_clips.append(clip)
                
            elif segment.transition_out == TransitionType.FADE_TO_BLACK:
                # Fade to black with a brief black pause
                clip = fadeout(clip, transition_duration)
                # Create black clip - this is a NEW clip that needs cleanup
                black = ColorClip(size=clip.size, color=(0, 0, 0), duration=0.2)
                final_clips.append(clip)
                final_clips.append(black)  # Track this for cleanup
                
            else:
                # Default to cut for any unhandled transition types
                final_clips.append(clip)
        
        return final_clips
    
    def _add_audio_track(self, video: VideoFileClip, audio_path: str, timeline: Timeline) -> VideoFileClip:
        """Add audio track to video, mixing with any preserved original audio."""
        try:
            # Load the background music
            music = AudioFileClip(audio_path)
            
            # Trim music to match video duration
            if music.duration > video.duration:
                music = music.subclip(0, video.duration)
            
            # Check if video has original audio from segments that preserved it
            if video.audio is not None:
                # We already have audio from clips that preserved it with proper volumes
                # Mix strategy: Either original audio dominates (80/20) or music dominates (20/80)
                from moviepy.audio.AudioClip import CompositeAudioClip
                
                # Determine dominant audio based on segment settings
                # If any segment has original_audio_volume > 0.5, original dominates
                # Otherwise, music dominates
                has_important_audio = any(
                    seg.preserve_original_audio and seg.original_audio_volume > 0.5 
                    for seg in timeline.segments
                )
                
                if has_important_audio:
                    # Original audio dominates (80%), music is subtle background (20%)
                    music = music.volumex(0.2)
                    logger.info("Original audio dominant mix (80/20)")
                else:
                    # Music dominates (80%), original audio is subtle (20%)
                    # Note: original audio volumes are already set per segment
                    music = music.volumex(0.8)
                    logger.info("Background music dominant mix (20/80)")
                
                # Composite the audio tracks
                mixed_audio = CompositeAudioClip([video.audio, music])
                
                # Set the mixed audio
                video = video.set_audio(mixed_audio)
            else:
                # No original audio preserved, just use the background music at full volume
                video = video.set_audio(music)
                logger.info("Added background music (no original audio preserved)")
            
            return video
            
        except Exception as e:
            logger.error(f"Failed to add audio track: {e}")
            return video


# Create the render tool function
async def render_video(
    project_state: Dict[str, Any],
    output_filename: str = "output.mp4",
    resolution: str = "1920x1080",
    preview: bool = False,
    preserve_original_audio: bool = True,
    audio_mix_ratio: float = 0.3
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
        
        # Determine output path - use project directory if available
        if state.storage_path:
            output_dir = Path(state.storage_path)
        else:
            # Fallback to project-specific directory
            output_dir = Path(f"./data/projects/{state.project_id}")
        
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
        # Add to rendered outputs list
        if rendered_path not in state.rendered_outputs:
            state.rendered_outputs.append(rendered_path)
        
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