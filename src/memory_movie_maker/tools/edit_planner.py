"""Edit planning tool using Gemini for intelligent timeline creation."""

import json
import logging
from typing import Dict, Any, List, Optional

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    types = None

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
        self._model_name = settings.get_gemini_model_name(task="planning")

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

        # Convert simple IDs back to original IDs
        id_mapping = getattr(self, '_id_mapping', None)
        if id_mapping:
            for segment in edit_plan.segments:
                if segment.media_id in id_mapping:
                    segment.media_id = id_mapping[segment.media_id]

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

        # Simplify media information - only include what's essential for editing decisions
        media_info = []

        for i, asset in enumerate(media_assets):
            # Use simple sequential IDs for easier reference
            simple_id = f"m{i:03d}"  # m000, m001, etc.

            info = {
                "id": simple_id,
                "original_id": asset.id,  # Keep mapping for execution
                "type": asset.type,
                "index": i,  # Chronological position
            }

            # Essential metadata only
            if asset.type == "video":
                info["duration"] = asset.duration or asset.metadata.get("duration", 0)

            # Analysis results - only the most important fields
            if asset.gemini_analysis:
                info["description"] = asset.gemini_analysis.description[:100]  # Truncate long descriptions
                info["quality"] = round(asset.gemini_analysis.aesthetic_score, 2)
                info["subjects"] = asset.gemini_analysis.main_subjects[:3]  # Top 3 subjects only

                if hasattr(asset.gemini_analysis, 'notable_segments') and asset.gemini_analysis.notable_segments:
                    # Only include the top 3 most important segments
                    top_segments = sorted(
                        asset.gemini_analysis.notable_segments,
                        key=lambda s: s.importance,
                        reverse=True
                    )[:3]
                    info["key_moments"] = [
                        {
                            "start": seg.start_time,
                            "end": seg.end_time,
                            "description": seg.description[:50],  # Brief description
                            "importance": round(seg.importance, 2)
                        }
                        for seg in top_segments
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

        # Create ID mapping for converting back to original IDs
        id_mapping = {info["id"]: info["original_id"] for info in media_info}
        self._id_mapping = id_mapping  # Store for later use in parse

        # Build the prompt following Gemini best practices
        prompt = f"""## Context

You are a professional video editor. The user has provided a collection of media files (photos and videos) from an event, trip, or personal experience. Your task is to create a detailed edit plan that selects and arranges these media files into a cohesive video.

## Requirements

- **User Request**: {user_prompt}
- **Target Duration**: {target_duration} seconds (your edit must be within 5 seconds of this)

## Editing Guidelines

### Most Critical Rules
• **Never repeat clips** - each media_id appears only once
• **STRONGLY prefer videos over photos** - only use photos if no video coverage exists
• **Match cuts to music** beats/energy when music is present  
• **Prioritize quality** - use clips with quality score > 0.7

### Shot Duration
• Quick cuts: 0.5-2s (energy, montages)
• Standard: 2-4s (most content)
• Emotional: 4-6s (key moments)
• Maximum: 8s (avoid longer)

### Pacing Essentials
• Vary shot types and compositions
• Build energy in waves, not straight lines
• Place best moments at 1/3 and 2/3 points
• Create rhythm through variety

### Quality Standards
• Skip blurry/shaky/dark clips unless essential
• For videos: use trim_start/trim_end to extract best parts
• Match visual energy to music energy
• End with something memorable

### Handling Redundant Media
• Media files are sorted chronologically (see index field)
• Multiple files with similar timestamps often show the same moment from different angles
• When you have duplicate coverage:
  - Choose only the BEST angle/quality
  - **ALWAYS prefer video over photos** of the same moment
  - It's perfectly fine to skip redundant media
• Photos should only be used when there's NO video coverage of that part of the event
• Maintain temporal flow for events unless artistic reasons dictate otherwise

### Transition Discipline
• **Default to cuts** - Use "cut" for 90-95% of transitions
• Cuts create energy and maintain pace
• Only use special transitions with purpose:
  - "fade": Scene changes, time jumps, beginning/ending
  - "crossfade": Dreamy/emotional moments (use sparingly)
  - "cut": Everything else

• Cut on action (mid-movement) for seamless flow
• Cut on beat for musical videos
• Match cut when possible (similar shapes/movements between shots)
• Never use cheesy transitions (star wipes, spirals, etc.)

### Music Synchronization (when music is present)
• **Cuts must hit beats exactly** - not "near" the beat
• Match cutting rhythm to tempo: fast music = shorter clips
• Place key moments on strong beats and musical transitions
• Sync visual peaks with musical crescendos
• If musical segments are provided in analysis:
  - Use "sync_priority" scores for must-sync moments
  - Cut on "recommended_cut_points" for natural flow
  - Match visual energy to "energy_transition" states

### Audio Handling
• Preserve complete sentences/phrases when video contains speech
• Use "video_audio.recommended_cuts" for natural break points
• Match emotional tone of video speech with overall mood

### Audio Mixing Decisions
**Be decisive with audio mixing - avoid muddy 50/50 mixes:**
• **0.8-1.0**: Important dialogue, speeches, performances (original dominates)
• **0.1-0.2**: Ambient sounds, crowd noise (music dominates)  
• **0.0**: Mute original audio (music only)
• **Never use 0.3-0.7**: This creates muddy mixing

Consider preserving original audio when:
• Video contains important dialogue or narration
• Ambient sounds enhance atmosphere (waves, laughter)
• Sound effects add impact (applause, etc.)


## Available Media

The media files are already sorted chronologically. Each file has:
- **id**: Simple reference ID (m000, m001, etc.) 
- **type**: "image" or "video"
- **quality**: Aesthetic score from 0-1 (higher is better)
- **duration**: For videos, length in seconds
- **description**: Brief content description

**Important**: Videos are strongly preferred over photos. Only use photos when no suitable video exists for that moment.

```json
{json.dumps(media_info, indent=2)}
```

{('## Music Track' + chr(10) + chr(10) + '```json' + chr(10) + json.dumps(music_info, indent=2) + chr(10) + '```') if music_info else '## Note: No Music Track Provided'}

# Output Format

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
✓ Overall feels broadcast/commercial quality

## Your Task

Analyze the available media files and create a detailed edit plan that:
1. Selects the best clips (strongly preferring videos over photos)
2. Arranges them in an engaging sequence
3. Matches the user's request and target duration
4. Returns a valid JSON object with all required fields

Create the edit plan now."""

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
        """Call Gemini API with the edit planning prompt.
        
        Uses thinking config to allow the model to reason through the edit plan
        with up to 2000 tokens of internal thinking before generating the response.
        """
        try:
            # Create config with thinking enabled for better reasoning
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=10000  # Allow up to 2k tokens for thinking
                )
            ) if types else None
            
            # Call with thinking config if available
            if config:
                logger.info("Using thinking config with 2k token budget for edit planning")
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=config
                )
            else:
                # Fallback without thinking config
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
