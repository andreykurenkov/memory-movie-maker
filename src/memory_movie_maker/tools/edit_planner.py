"""Edit planning tool using Gemini for intelligent timeline creation."""

import json
import logging
from typing import Dict, Any, List, Optional

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from google.adk.tools import FunctionTool
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

from ..config import settings
from ..models.media_asset import MediaAsset, MediaType, AudioAnalysisProfile
from ..models.project_state import ProjectState
from ..models.edit_plan import EditPlan, PlannedSegment
from ..utils.simple_logger import log_start, log_update, log_complete
from ..utils.ai_output_logger import ai_logger


logger = logging.getLogger(__name__)


class EditPlanner:
    """Plans video edits using Gemini's intelligence."""
    
    def __init__(self):
        """Initialize the edit planner."""
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai package not available")
        
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model_name = settings.get_gemini_model_name()
        
    async def plan_edit(
        self,
        media_assets: List[MediaAsset],
        music_profile: Optional[AudioAnalysisProfile],
        target_duration: int,
        user_prompt: str,
        style_preferences: Dict[str, Any],
        music_asset: Optional[MediaAsset] = None
    ) -> EditPlan:
        """Create an intelligent edit plan using Gemini.
        
        Args:
            media_assets: All analyzed media assets
            music_profile: Music analysis (beats, tempo, energy)
            target_duration: Target video duration in seconds
            user_prompt: User's original request
            style_preferences: Style settings (smooth, dynamic, etc.)
            
        Returns:
            Complete edit plan with segments and creative reasoning
        """
        log_start(logger, f"Planning {target_duration}s edit with Gemini")
        
        # Build the prompt
        prompt = self._build_edit_prompt(
            media_assets, music_profile, target_duration, user_prompt, style_preferences, music_asset
        )
        
        # Call Gemini
        log_update(logger, "Asking Gemini to plan the edit...")
        response = await self._call_gemini(prompt)
        
        # Parse the response
        log_update(logger, "Parsing edit plan...")
        edit_plan = self._parse_edit_plan(response)
        
        # Log to AI output logger
        ai_logger.log_edit_plan(
            plan=edit_plan.dict() if hasattr(edit_plan, 'dict') else vars(edit_plan),
            prompt=prompt,  # Log full prompt
            raw_response=response
        )
        
        log_complete(logger, f"Edit plan created with {len(edit_plan.segments)} segments")
        return edit_plan
    
    def _build_edit_prompt(
        self,
        media_assets: List[MediaAsset],
        music_profile: Optional[AudioAnalysisProfile],
        target_duration: int,
        user_prompt: str,
        style_preferences: Dict[str, Any],
        music_asset: Optional[MediaAsset] = None
    ) -> str:
        """Build a detailed prompt for Gemini."""
        
        # Format media information (already sorted chronologically)
        media_info = []
        prev_timestamp = None
        
        for i, asset in enumerate(media_assets):
            info = {
                "id": asset.id,
                "type": asset.type,
                "file": asset.file_path.split('/')[-1],
                "file_path": asset.file_path,  # Full path for context
                "chronological_index": i,  # Position in chronological order
            }
            
            # Check if this is likely part of the same event as previous
            if i > 0 and asset.metadata and media_assets[i-1].metadata:
                curr_time = asset.metadata.get("chronological_order") or asset.metadata.get("recorded_at")
                prev_time = media_assets[i-1].metadata.get("chronological_order") or media_assets[i-1].metadata.get("recorded_at")
                
                if curr_time and prev_time:
                    # If timestamps are numeric (chronological_order)
                    if isinstance(curr_time, (int, float)) and isinstance(prev_time, (int, float)):
                        time_diff = curr_time - prev_time
                        # If less than 5 minutes apart, likely same event
                        if time_diff < 300:
                            info["likely_same_event_as_previous"] = True
                            info["seconds_after_previous"] = time_diff
            
            # Add important metadata
            if asset.metadata:
                if "duration" in asset.metadata:
                    info["duration"] = asset.metadata["duration"]
                if "width" in asset.metadata and "height" in asset.metadata:
                    info["resolution"] = f"{asset.metadata['width']}x{asset.metadata['height']}"
                if "recorded_at" in asset.metadata:
                    info["recorded_at"] = asset.metadata["recorded_at"]
                elif "modified_time" in asset.metadata:
                    info["recorded_at"] = asset.metadata["modified_time"]  # Fallback
                if "fps" in asset.metadata:
                    info["fps"] = asset.metadata["fps"]
            
            # For videos, explicitly note the duration
            if asset.type == "video" and asset.duration:
                info["duration"] = asset.duration
            
            if asset.gemini_analysis:
                info["description"] = asset.gemini_analysis.description
                info["aesthetic_score"] = asset.gemini_analysis.aesthetic_score
                info["subjects"] = asset.gemini_analysis.main_subjects
                info["tags"] = asset.gemini_analysis.tags
                
                if hasattr(asset.gemini_analysis, 'notable_segments') and asset.gemini_analysis.notable_segments:
                    info["notable_segments"] = [
                        {
                            "start": seg.start_time,
                            "end": seg.end_time,
                            "description": seg.description,
                            "visual_content": seg.visual_content,
                            "audio_content": seg.audio_content,
                            "audio_type": seg.audio_type,
                            "speaker": seg.speaker,
                            "speech_content": seg.speech_content,
                            "music_description": seg.music_description,
                            "emotional_tone": seg.emotional_tone,
                            "importance": seg.importance,
                            "sync_priority": seg.sync_priority,
                            "recommended_action": seg.recommended_action,
                            "tags": seg.tags
                        }
                        for seg in asset.gemini_analysis.notable_segments
                    ]
                
                # Include audio summary if available
                if hasattr(asset.gemini_analysis, 'audio_summary') and asset.gemini_analysis.audio_summary:
                    audio_summary = asset.gemini_analysis.audio_summary
                    info["audio_summary"] = {
                        "has_speech": audio_summary.has_speech,
                        "has_music": audio_summary.has_music,
                        "dominant_audio": audio_summary.dominant_audio,
                        "overall_mood": audio_summary.overall_audio_mood,
                        "audio_quality": audio_summary.audio_quality,
                        "key_moments": audio_summary.key_audio_moments
                    }
            
            if asset.audio_analysis:
                info["audio_mood"] = asset.audio_analysis.vibe.mood
                info["tempo"] = asset.audio_analysis.tempo_bpm
            
            if asset.semantic_audio_analysis:
                info["audio_content"] = asset.semantic_audio_analysis.get("summary", "")
                # Include musical segments if available
                if asset.semantic_audio_analysis.get("segments"):
                    info["audio_segments"] = [
                        {
                            "start": seg.get("start_time", 0),
                            "end": seg.get("end_time", 0),
                            "type": seg.get("type", ""),
                            "musical_structure": seg.get("musical_structure"),
                            "energy_transition": seg.get("energy_transition"),
                            "sync_priority": seg.get("sync_priority", 0.5)
                        }
                        for seg in asset.semantic_audio_analysis.get("segments", [])
                        if seg.get("type") in ["music", "intro", "verse", "chorus", "bridge", "outro", "drop", "buildup"]
                    ]
                
            media_info.append(info)
        
        # Format music information
        music_info = None
        if music_profile:
            music_info = {
                "tempo": music_profile.tempo_bpm,
                "duration": music_profile.duration,
                "mood": music_profile.vibe.mood,
                "energy_level": music_profile.vibe.energy,
                "beat_count": len(music_profile.beat_timestamps),
                "energy_curve_summary": self._summarize_energy_curve(music_profile.energy_curve)
            }
            
            # Add detailed musical segmentation if available
            if music_asset and music_asset.semantic_audio_analysis:
                semantic = music_asset.semantic_audio_analysis
                music_info["musical_structure"] = semantic.get("musical_structure_summary", "")
                music_info["energy_peaks"] = semantic.get("energy_peaks", [])
                music_info["recommended_cut_points"] = semantic.get("recommended_cut_points", [])
                music_info["key_moments"] = semantic.get("key_moments", [])
                
                # Include musical segments
                if semantic.get("segments"):
                    music_info["detailed_segments"] = [
                        {
                            "start": seg.get("start_time", 0),
                            "end": seg.get("end_time", 0),
                            "type": seg.get("type", ""),
                            "content": seg.get("content", ""),
                            "musical_structure": seg.get("musical_structure"),
                            "energy_transition": seg.get("energy_transition"),
                            "sync_priority": seg.get("sync_priority", 0.5)
                        }
                        for seg in semantic.get("segments", [])
                        if seg.get("type") in ["music", "intro", "verse", "chorus", "bridge", "outro", "drop", "buildup"]
                    ]
        
        # Build the prompt with artistic direction
        prompt = f"""You are a professional video editor creating a cohesive video from a collection of photos and videos. 
The user has provided media from an event, trip, party, or personal collection that they want edited together into 
a single video that captures and preserves the memories from this experience.

USER REQUEST: {user_prompt}
TARGET DURATION: {target_duration} seconds
EDITING STYLE: {style_preferences.get('style', 'balanced')}

AVAILABLE MEDIA:
{json.dumps(media_info, indent=2)}

{'MUSIC TRACK:' + json.dumps(music_info, indent=2) if music_info else 'NO MUSIC TRACK'}

CREATIVE GUIDELINES:

1. STORY STRUCTURE:
   - Create a clear narrative arc with beginning, middle, and end
   - Use story beats: Establishing shot → Development → Climax → Resolution
   - Each segment should advance the story or emotional journey

2. PROFESSIONAL PACING & COMPOSITION:
   - CRITICAL: Never repeat the same clip - each media_id should appear ONLY ONCE in the edit
   - IMPORTANT: Use trim_start and trim_end to select DIFFERENT portions of long videos
   - For videos: Always specify trim_start/trim_end to extract the EXACT segment needed
   - Maintain NATURAL playback speed - clips should play at 1x speed (duration = trim_end - trim_start)
   
   PROFESSIONAL SHOT LENGTHS:
   - Quick cuts: 0.5-2s (for energy, montages, beat syncs)
   - Standard shots: 2-4s (for most content, allows viewer comprehension)
   - Breathing shots: 4-6s (for emotional moments, establishing shots)
   - Hero shots: 6-8s MAX (only for truly exceptional moments)
   - AVOID: Shots under 0.5s (too jarring) or over 8s (loses engagement)
   
   RULE OF THIRDS TIMING:
   - Place visual peaks at 1/3 and 2/3 points in the timeline
   - Build energy in waves, not a straight line
   - Use the 3-act structure even in short videos

3. EMOTIONAL IMPACT:
   - Build emotional intensity gradually
   - Place the most impactful moments at key points (1/3 and 2/3 marks)
   - Use quieter moments for emotional breathing room
   - End with a memorable, satisfying conclusion

4. PROFESSIONAL QUALITY STANDARDS:
   - MINIMUM aesthetic score: 0.7 (reject anything below unless it's narratively essential)
   - Prioritize clips with scores > 0.8 for key moments
   - For videos, use the notable_moments identified in analysis
   - Match visual energy to musical energy when possible
   
   AVOID AMATEUR MISTAKES:
   - Never use blurry, shaky, or poorly lit clips unless absolutely necessary
   - Don't put similar shots back-to-back (vary composition)
   - Avoid jarring aspect ratio changes
   - Never cut mid-action unless intentional
   - Don't overuse any single type of shot
   - IMPORTANT: Use each clip ONLY ONCE - no repetition
   - For chronological events (concerts, festivals), maintain temporal flow
   - It's fine NOT to use every video/image provided - quality over quantity
   - If multiple clips show the same moment/event, pick the BEST ONE only
   
   CHRONOLOGICAL AWARENESS & REDUNDANCY HANDLING:
   - Media files are sorted chronologically (see chronological_index)
   - Files with similar timestamps likely show the SAME event/performance from different angles
   - When you have multiple videos of the same moment:
     * Understand they're showing the SAME thing (e.g., same band performance, same speech)
     * Choose ONLY the BEST angle/quality - don't use both
     * Look for clues: similar subjects, matching audio, close timestamps
     * If unsure, check the descriptions and tags for matches
   - It's PERFECTLY FINE to skip redundant media - better to have a tight edit than use everything
   - Respect the natural flow of events unless artistic reasons dictate otherwise
   
5. PROFESSIONAL TRANSITION DISCIPLINE:
   - DEFAULT TO CRASH CUTS: Use "cut" (instant transition) as your primary transition
   - Crash cuts create energy, maintain pace, and feel modern/professional
   - ONLY use special transitions when there's a specific reason:
     * "fade": Major scene changes, time jumps, beginning/ending only
     * "crossfade": Dreamy sequences, flashbacks (use sparingly - max 2-3 per video)
     * "cut": Everything else (90-95% of transitions should be cuts)
   
   PROFESSIONAL TRANSITION RULES:
   - Cut on action (mid-movement) for seamless flow
   - Cut on beat for musical videos
   - Match cut when possible (similar shapes/movements between shots)
   - J-cuts and L-cuts for dialogue (audio leads or follows video)
   - NEVER use cheesy transitions (star wipes, spirals, etc.)

6. PROFESSIONAL MUSIC SYNCHRONIZATION:
   - BEAT PRECISION: Cuts should land EXACTLY on beat, not "near" the beat
   - Place key visual moments on strong beats and musical transitions
   - Match cutting rhythm to tempo: Fast music = shorter clips
   - Use energy curve: High energy → dynamic cuts, Low energy → longer takes
   - Leave space for the music to breathe
   
   PROFESSIONAL SYNC TECHNIQUES:
   - Hit the downbeat (1st beat of measure) for major changes
   - Use snare hits for impact cuts
   - Sync visual peaks with musical crescendos
   - Create visual "drops" that match musical drops
   - Pull back during musical bridges for contrast
   
   IMPORTANT: If detailed musical segments are provided:
   - Sync major visual transitions with musical structure changes (verse→chorus, buildup→drop)
   - Use "sync_priority" scores to identify must-sync moments
   - Align emotional peaks in visuals with "energy_peaks" in music
   - Cut on "recommended_cut_points" for natural flow
   - Match visual energy to "energy_transition" states (building, dropping, peak, valley)

7. VIDEO AUDIO INTEGRATION:
   - If video contains speech, preserve complete sentences/phrases when possible
   - Use "video_audio.recommended_cuts" for natural audio break points
   - Match emotional tone of video speech with overall mood
   - For videos with music, consider layering or transitioning between video and background music
   - Respect "sync_priority" in video segments for important audio-visual moments
   - If video has dialogue, ensure important speech is not cut mid-sentence
   - Use sound effects timing to enhance transitions (e.g., door closing as transition point)

8. INTELLIGENT AUDIO MIXING DECISIONS:
   - For each video segment, decide whether to preserve its original audio
   - Consider preserving original audio when:
     * Video contains important dialogue or narration
     * Ambient sounds enhance the atmosphere (waves, laughter, etc.)
     * Sound effects add impact (door closing, applause, etc.)
     * Video has its own music that complements the background track
   - Set original_audio_volume DECISIVELY (avoid muddy 50/50 mixing):
     * 0.8-1.0: Important dialogue, speeches, live performances (original DOMINATES)
     * 0.1-0.2: Ambient crowd noise, background sounds (music DOMINATES)
     * 0.0: Mute original audio completely (music only)
     * NEVER USE 0.3-0.7: This creates dissonant mixing - be decisive!
   - The system will automatically mix at 80/20 ratio based on your choice
   - Provide audio_reasoning to explain which track should dominate

Return a complete edit plan as JSON:
{{
  "segments": [
    {{
      "media_id": "asset_id",
      "start_time": 0.0,
      "duration": 3.0,
      "trim_start": 0.0,
      "trim_end": 3.0,
      "transition_type": "cut",  // Options: "cut" (instant), "fade", "crossfade" - use cut by default
      "preserve_original_audio": true/false,
      "original_audio_volume": 0.5,
      "audio_reasoning": "Preserving dialogue at 50% to layer with music...",
      "reasoning": "Establishes setting with wide shot...",
      "story_beat": "introduction",
      "energy_match": 0.7
    }}
  ],
  "total_duration": {target_duration},
  "narrative_structure": "The edit follows a journey from...",
  "pacing_strategy": "Starts slow to establish mood, builds energy...",
  "music_sync_notes": "Key moments hit on downbeats at...",
  "variety_score": 0.85,
  "story_coherence": 0.9,
  "technical_quality": 0.8,
  "reasoning_summary": "This edit emphasizes the journey aspect..."
}}

PROFESSIONAL EDITING PRINCIPLES:
- Every frame matters - no filler content
- Hook viewers in the first 3 seconds
- Create a video that feels expensive and polished
- Balance technical precision with emotional authenticity
- The whole should be greater than the sum of its parts

QUALITY CHECKLIST:
✓ Opening shot grabs attention immediately
✓ Each shot advances the story or emotion
✓ Transitions are invisible (cuts) or purposeful (fades)
✓ Music and visuals are perfectly synchronized
✓ Pacing creates and releases tension appropriately
✓ Ending provides satisfying closure
✓ Overall feels broadcast/commercial quality"""

        return prompt
    
    def _summarize_energy_curve(self, energy_curve: List[float]) -> str:
        """Summarize the energy curve for the prompt."""
        if not energy_curve:
            return "No energy data"
        
        # Find peaks and valleys
        avg_energy = sum(energy_curve) / len(energy_curve)
        high_energy_times = []
        low_energy_times = []
        
        samples_per_second = len(energy_curve) / 60  # Rough estimate
        
        for i, energy in enumerate(energy_curve):
            time = i / samples_per_second
            if energy > avg_energy * 1.3:
                high_energy_times.append(f"{time:.1f}s")
            elif energy < avg_energy * 0.7:
                low_energy_times.append(f"{time:.1f}s")
        
        return f"High energy at: {', '.join(high_energy_times[:5])}... Low energy at: {', '.join(low_energy_times[:5])}..."
    
    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API with the edit planning prompt."""
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    def _parse_edit_plan(self, response: str) -> EditPlan:
        """Parse Gemini's response into EditPlan object."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = response[json_start:json_end]
            plan_data = json.loads(json_str)
            
            # Convert segments to PlannedSegment objects
            segments = []
            for i, seg_data in enumerate(plan_data.get("segments", [])):
                segment = PlannedSegment(
                    media_id=seg_data["media_id"],
                    start_time=float(seg_data["start_time"]),
                    duration=float(seg_data["duration"]),
                    trim_start=float(seg_data.get("trim_start", 0.0)),
                    trim_end=float(seg_data.get("trim_end")) if seg_data.get("trim_end") else None,
                    transition_type=seg_data.get("transition_type", "cut"),  # Default to cut, not crossfade
                    reasoning=seg_data.get("reasoning", ""),
                    story_beat=seg_data.get("story_beat"),
                    energy_match=float(seg_data["energy_match"]) if seg_data.get("energy_match") else None,
                    # Audio mixing fields
                    preserve_original_audio=seg_data.get("preserve_original_audio", False),
                    original_audio_volume=float(seg_data.get("original_audio_volume", 0.3)),
                    audio_reasoning=seg_data.get("audio_reasoning")
                )
                segments.append(segment)
                
                # Log the reasoning
                if segment.reasoning:
                    log_update(logger, f"Segment {i+1}: {segment.reasoning[:60]}...")
            
            # Calculate actual total duration from segments
            actual_duration = sum(s.duration for s in segments)
            
            # Create EditPlan
            edit_plan = EditPlan(
                segments=segments,
                total_duration=actual_duration,  # Use calculated duration to avoid validation errors
                narrative_structure=plan_data.get("narrative_structure", "No structure provided"),
                pacing_strategy=plan_data.get("pacing_strategy", "Standard pacing"),
                music_sync_notes=plan_data.get("music_sync_notes"),
                variety_score=float(plan_data.get("variety_score", 0.5)),
                story_coherence=float(plan_data.get("story_coherence", 0.5)),
                technical_quality=float(plan_data.get("technical_quality", 0.5)),
                reasoning_summary=plan_data.get("reasoning_summary", "No summary provided")
            )
            
            # Log the creative overview
            log_update(logger, f"Narrative: {edit_plan.narrative_structure[:80]}...")
            log_update(logger, f"Variety score: {edit_plan.variety_score:.2f}, Coherence: {edit_plan.story_coherence:.2f}")
            
            return edit_plan
            
        except Exception as e:
            logger.error(f"Failed to parse edit plan: {e}")
            logger.debug(f"Response: {response}")
            raise ValueError(f"Could not parse edit plan: {e}")


# ADK tool wrapper
async def plan_edit(
    project_state: Dict[str, Any],
    target_duration: int = 60,
    style: str = "auto"
) -> Dict[str, Any]:
    """Plan video edit using Gemini's intelligence.
    
    Args:
        project_state: Current project state with analyzed media
        target_duration: Target video duration in seconds
        style: Style preference (auto, smooth, dynamic, fast)
        
    Returns:
        Edit plan with segments and reasoning
    """
    try:
        # Parse project state
        state = ProjectState(**project_state)
        
        # Separate media types
        visual_media = []
        music_track = None
        music_asset = None
        
        # Get visual media from media field
        for asset in state.user_inputs.media:
            if asset.type in [MediaType.IMAGE, MediaType.VIDEO]:
                visual_media.append(asset)
        
        # Get music from music field
        if state.user_inputs.music and len(state.user_inputs.music) > 0:
            music_asset = state.user_inputs.music[0]  # Use first music track
            if music_asset.audio_analysis:
                music_track = music_asset.audio_analysis
        
        if not visual_media:
            return {
                "status": "error",
                "error": "No visual media found to create timeline"
            }
        
        # Get user prompt
        user_prompt = state.user_inputs.initial_prompt or "Create a cohesive video from these media files"
        
        # Style preferences
        style_prefs = {
            "style": style,
            "transition_style": "smooth" if style == "smooth" else "dynamic"
        }
        
        # Create planner and get edit plan
        planner = EditPlanner()
        edit_plan = await planner.plan_edit(
            media_assets=visual_media,
            music_profile=music_track,
            target_duration=target_duration,
            user_prompt=user_prompt,
            style_preferences=style_prefs,
            music_asset=music_asset
        )
        
        return {
            "status": "success",
            "edit_plan": edit_plan.model_dump(),
            "segment_count": len(edit_plan.segments),
            "total_duration": edit_plan.total_duration,
            "variety_score": edit_plan.variety_score,
            "story_coherence": edit_plan.story_coherence
        }
        
    except Exception as e:
        logger.error(f"Edit planning failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Create ADK tool
if ADK_AVAILABLE:
    plan_edit_tool = FunctionTool(plan_edit)
else:
    plan_edit_tool = None