"""Composition tool for creating video timelines from analyzed media."""

import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import random
from collections import defaultdict

from google.adk.tools import FunctionTool

from ..models.timeline import Timeline, Segment, TransitionType
from ..models.media_asset import MediaAsset, MediaType, AudioAnalysisProfile
from ..models.project_state import ProjectState


logger = logging.getLogger(__name__)


@dataclass
class MediaCluster:
    """Group of related media files."""
    media_items: List[MediaAsset]
    start_time: float
    duration: float
    theme: str
    energy_level: float


class CompositionAlgorithm:
    """Creates intelligent video timelines from analyzed media."""
    
    def __init__(self):
        """Initialize composition algorithm."""
        self.min_clip_duration = 1.0  # Minimum seconds per clip
        self.max_clip_duration = 5.0  # Maximum seconds per clip
        self.transition_duration = 0.5  # Default transition duration
    
    def compose_timeline(
        self,
        media_pool: List[MediaAsset],
        music_profile: Optional[AudioAnalysisProfile],
        target_duration: int,
        style_preferences: Dict[str, Any]
    ) -> Timeline:
        """Generate optimal timeline from media and music.
        
        Args:
            media_pool: List of analyzed media assets
            music_profile: Audio analysis of soundtrack (optional)
            target_duration: Target video duration in seconds
            style_preferences: User style preferences
            
        Returns:
            Timeline with arranged segments
        """
        # Filter out unusable media
        usable_media = self._filter_usable_media(media_pool)
        
        if not usable_media:
            raise ValueError("No usable media found for timeline creation")
        
        # Cluster media by similarity
        clusters = self._cluster_media(usable_media)
        
        # If we have music, sync to beats
        if music_profile and music_profile.beat_timestamps:
            segments = self._create_beat_synced_segments(
                clusters, music_profile, target_duration
            )
        else:
            # Create chronological timeline
            segments = self._create_chronological_segments(
                clusters, target_duration
            )
        
        # Apply transitions
        segments = self._apply_transitions(segments, style_preferences)
        
        # Create timeline
        timeline = Timeline(
            segments=segments,
            audio_track_id=music_profile.file_path if music_profile else None,
            total_duration=sum(s.duration for s in segments)
        )
        
        return timeline
    
    def _filter_usable_media(self, media_pool: List[MediaAsset]) -> List[MediaAsset]:
        """Filter media that can be used in timeline."""
        usable = []
        
        for media in media_pool:
            # Skip media without analysis
            if media.type in [MediaType.IMAGE, MediaType.VIDEO] and not media.gemini_analysis:
                logger.warning(f"Skipping {media.file_path} - no visual analysis")
                continue
            
            # Skip low quality media
            if media.gemini_analysis and media.gemini_analysis.aesthetic_score < 0.3:
                logger.info(f"Skipping {media.file_path} - low aesthetic score")
                continue
            
            usable.append(media)
        
        return usable
    
    def _cluster_media(self, media_items: List[MediaAsset]) -> List[MediaCluster]:
        """Group media by visual similarity and time."""
        clusters = []
        
        # Simple clustering by timestamp and tags
        time_groups = defaultdict(list)
        
        for media in media_items:
            # Use capture time if available, otherwise group all together
            timestamp = media.metadata.get("capture_time", "unknown") if media.metadata else "unknown"
            time_key = str(timestamp)[:10] if timestamp != "unknown" else "unknown"
            time_groups[time_key].append(media)
        
        # Create clusters from time groups
        for time_key, items in time_groups.items():
            # Further cluster by common tags
            tag_groups = self._group_by_tags(items)
            
            for tag_theme, tag_items in tag_groups.items():
                cluster = MediaCluster(
                    media_items=tag_items,
                    start_time=0,  # Will be set later
                    duration=len(tag_items) * 2.5,  # Rough estimate
                    theme=tag_theme,
                    energy_level=self._calculate_cluster_energy(tag_items)
                )
                clusters.append(cluster)
        
        return clusters
    
    def _group_by_tags(self, media_items: List[MediaAsset]) -> Dict[str, List[MediaAsset]]:
        """Group media by common tags."""
        tag_groups = defaultdict(list)
        
        for media in media_items:
            if media.gemini_analysis and media.gemini_analysis.tags:
                # Use most prominent tag as grouping key
                main_tag = media.gemini_analysis.tags[0] if media.gemini_analysis.tags else "misc"
                tag_groups[main_tag].append(media)
            else:
                tag_groups["misc"].append(media)
        
        return dict(tag_groups)
    
    def _calculate_cluster_energy(self, media_items: List[MediaAsset]) -> float:
        """Calculate average energy level of a cluster."""
        energy_scores = []
        
        for media in media_items:
            if media.gemini_analysis:
                # Use aesthetic score as proxy for energy
                energy_scores.append(media.gemini_analysis.aesthetic_score)
        
        return sum(energy_scores) / len(energy_scores) if energy_scores else 0.5
    
    def _create_beat_synced_segments(
        self,
        clusters: List[MediaCluster],
        music_profile: AudioAnalysisProfile,
        target_duration: int
    ) -> List[Segment]:
        """Create segments synchronized to music beats."""
        segments = []
        beat_times = music_profile.beat_timestamps[:target_duration * 2]  # Rough beat limit
        energy_curve = music_profile.energy_curve
        
        # Sort clusters by energy to match with music dynamics
        sorted_clusters = sorted(clusters, key=lambda c: c.energy_level, reverse=True)
        
        # Distribute media across beats
        media_queue = []
        for cluster in sorted_clusters:
            media_queue.extend(cluster.media_items)
        
        current_beat_idx = 0
        while media_queue and current_beat_idx < len(beat_times) - 1:
            media = media_queue.pop(0)
            
            # Calculate duration to next few beats
            beats_per_clip = self._calculate_beats_per_clip(
                current_beat_idx, beat_times, energy_curve
            )
            
            start_time = beat_times[current_beat_idx]
            end_beat_idx = min(current_beat_idx + beats_per_clip, len(beat_times) - 1)
            duration = beat_times[end_beat_idx] - start_time
            
            # Create segment
            segment = self._create_segment_from_media(
                media, start_time, duration
            )
            segments.append(segment)
            
            current_beat_idx = end_beat_idx
        
        return segments
    
    def _calculate_beats_per_clip(
        self,
        beat_idx: int,
        beat_times: List[float],
        energy_curve: List[float]
    ) -> int:
        """Calculate how many beats a clip should span."""
        # High energy = shorter clips (1-2 beats)
        # Low energy = longer clips (4-8 beats)
        
        if beat_idx < len(energy_curve):
            energy = energy_curve[beat_idx]
            if energy > 0.7:
                return random.randint(1, 2)
            elif energy > 0.4:
                return random.randint(2, 4)
            else:
                return random.randint(4, 6)
        
        return 4  # Default
    
    def _create_chronological_segments(
        self,
        clusters: List[MediaCluster],
        target_duration: int
    ) -> List[Segment]:
        """Create simple chronological timeline."""
        segments = []
        current_time = 0.0
        
        # Flatten all media
        all_media = []
        for cluster in clusters:
            all_media.extend(cluster.media_items)
        
        # Calculate duration per item
        duration_per_item = min(
            target_duration / len(all_media) if all_media else self.max_clip_duration,
            self.max_clip_duration
        )
        duration_per_item = max(duration_per_item, self.min_clip_duration)
        
        for media in all_media:
            if current_time >= target_duration:
                break
            
            segment = self._create_segment_from_media(
                media, current_time, duration_per_item
            )
            segments.append(segment)
            current_time += duration_per_item
        
        return segments
    
    def _create_segment_from_media(
        self,
        media: MediaAsset,
        start_time: float,
        duration: float
    ) -> Segment:
        """Create a timeline segment from a media asset."""
        effects = []
        
        # Add Ken Burns effect for photos
        if media.type == MediaType.IMAGE:
            effects.append("ken_burns")
        
        # Determine if we need to trim video
        trim_start = 0.0
        trim_end = None
        
        if media.type == MediaType.VIDEO and media.duration:
            # Use interesting parts of the video
            if media.gemini_analysis and hasattr(media.gemini_analysis, 'video_segments'):
                # Use the most important segment
                best_segment = max(
                    media.gemini_analysis.video_segments,
                    key=lambda s: s.importance,
                    default=None
                )
                if best_segment:
                    trim_start = best_segment.start_time
                    trim_end = best_segment.end_time
        
        return Segment(
            media_id=media.id,
            start_time=start_time,
            duration=duration,
            effects=effects,
            trim_start=trim_start,
            trim_end=trim_end
        )
    
    def _apply_transitions(
        self,
        segments: List[Segment],
        style_preferences: Dict[str, Any]
    ) -> List[Segment]:
        """Apply transitions between segments."""
        transition_style = style_preferences.get("transition_style", "smooth")
        
        for i, segment in enumerate(segments[:-1]):
            if transition_style == "smooth":
                segment.transition_out = TransitionType.CROSSFADE
            elif transition_style == "dynamic":
                # Alternate between different transitions
                transitions = [
                    TransitionType.CROSSFADE,
                    TransitionType.FADE_TO_BLACK,
                    TransitionType.SLIDE_LEFT,
                    TransitionType.SLIDE_RIGHT
                ]
                segment.transition_out = transitions[i % len(transitions)]
            else:
                segment.transition_out = TransitionType.CUT
        
        return segments


# Create the composition tool function
async def compose_timeline(
    project_state: Dict[str, Any],
    target_duration: int = 60,
    style: str = "auto"
) -> Dict[str, Any]:
    """Create video timeline from analyzed media.
    
    Args:
        project_state: Current project state
        target_duration: Target video duration in seconds
        style: Style preference (auto, smooth, dynamic, fast)
        
    Returns:
        Result with timeline or error
    """
    try:
        # Parse project state
        state = ProjectState(**project_state)
        
        # Get media assets
        media_pool = state.user_inputs.media
        
        # Find music track if available
        music_profile = None
        for media in media_pool:
            if media.type == MediaType.AUDIO and media.audio_analysis:
                music_profile = media.audio_analysis
                break
        
        # Style preferences
        style_prefs = {
            "transition_style": "smooth" if style == "smooth" else "dynamic",
            "pacing": "fast" if style == "fast" else "normal"
        }
        
        # Create timeline
        algorithm = CompositionAlgorithm()
        timeline = algorithm.compose_timeline(
            media_pool=media_pool,
            music_profile=music_profile,
            target_duration=target_duration,
            style_preferences=style_prefs
        )
        
        # Update project state
        state.timeline = timeline
        
        logger.info(f"Created timeline with {len(timeline.segments)} segments")
        
        return {
            "status": "success",
            "timeline": timeline.model_dump(),
            "updated_state": state.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Timeline composition failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Create ADK tool
compose_timeline_tool = FunctionTool(
    compose_timeline,
    name="compose_timeline",
    description="Create video timeline from analyzed media assets"
)