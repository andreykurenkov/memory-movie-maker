"""Refinement parsing tool for converting feedback to edit commands."""

import logging
from typing import Dict, Any, Optional
import re

from google.adk.tools import FunctionTool

from ..models.timeline import TransitionType


logger = logging.getLogger(__name__)


class RefinementParser:
    """Parses evaluation feedback and user requests into edit commands."""
    
    def __init__(self):
        """Initialize refinement parser."""
        self.transition_map = {
            "crossfade": TransitionType.CROSSFADE,
            "fade": TransitionType.FADE_TO_BLACK,
            "cut": TransitionType.CUT,
            "slide left": TransitionType.SLIDE_LEFT,
            "slide right": TransitionType.SLIDE_RIGHT,
            "zoom in": TransitionType.ZOOM_IN,
            "zoom out": TransitionType.ZOOM_OUT
        }
        
        self.effect_keywords = {
            # "ken burns": "ken_burns",  # Removed - not implemented
            "zoom": "zoom",
            "pan": "pan",
            "slow motion": "slow_motion",
            "speed up": "speed_up",
            "color": "color_correction",
            "brightness": "brightness_adjust"
        }
    
    def parse_feedback_to_commands(
        self,
        evaluation: Dict[str, Any],
        user_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parse evaluation and user feedback into edit commands.
        
        Args:
            evaluation: Video evaluation results
            user_feedback: Additional user feedback/requests
            
        Returns:
            Dictionary of edit commands
        """
        commands = {
            "reorder_segments": [],
            "adjust_durations": {},
            "change_transitions": {},
            "add_effects": {},
            "remove_segments": [],
            "replace_segments": {}
        }
        
        # Parse specific edits from evaluation
        if "specific_edits" in evaluation:
            for edit in evaluation["specific_edits"]:
                self._parse_specific_edit(edit, commands)
        
        # Parse creative suggestions
        if "creative_suggestions" in evaluation:
            for suggestion in evaluation["creative_suggestions"]:
                self._parse_suggestion(suggestion, commands)
        
        # Parse user feedback if provided
        if user_feedback:
            self._parse_user_feedback(user_feedback, commands)
        
        # Clean up empty command categories
        commands = {k: v for k, v in commands.items() if v}
        
        return commands
    
    def _parse_specific_edit(self, edit: Dict[str, Any], commands: Dict[str, Any]):
        """Parse a specific edit recommendation."""
        timestamp = edit.get("timestamp", "")
        issue = edit.get("issue", "").lower()
        suggestion = edit.get("suggestion", "").lower()
        
        # Extract segment ID from timestamp (simplified - real implementation would map this)
        segment_id = self._timestamp_to_segment_id(timestamp)
        
        if not segment_id:
            return
        
        # Duration adjustments
        if "too short" in issue or "extend" in suggestion:
            match = re.search(r'(\d+(?:\.\d+)?)\s*seconds?', suggestion)
            if match:
                duration_change = float(match.group(1))
                commands["adjust_durations"][segment_id] = duration_change
        
        elif "too long" in issue or "shorten" in suggestion:
            match = re.search(r'(\d+(?:\.\d+)?)\s*seconds?', suggestion)
            if match:
                duration_change = -float(match.group(1))
                commands["adjust_durations"][segment_id] = duration_change
        
        # Transition changes
        for transition_name, transition_type in self.transition_map.items():
            if transition_name in suggestion:
                commands["change_transitions"][segment_id] = transition_type
                break
        
        # Effect additions
        for effect_keyword, effect_name in self.effect_keywords.items():
            if effect_keyword in suggestion:
                if segment_id not in commands["add_effects"]:
                    commands["add_effects"][segment_id] = []
                commands["add_effects"][segment_id].append(effect_name)
    
    def _parse_suggestion(self, suggestion: str, commands: Dict[str, Any]):
        """Parse a creative suggestion."""
        suggestion_lower = suggestion.lower()
        
        # Look for general pacing suggestions
        if "longer clips" in suggestion_lower:
            # This would need timeline access to implement properly
            pass
        
        elif "dynamic transitions" in suggestion_lower:
            # This would apply to multiple segments
            pass
        
        # Look for effect suggestions
        for effect_keyword, effect_name in self.effect_keywords.items():
            if effect_keyword in suggestion_lower:
                # Would need to identify which segments to apply to
                pass
    
    def _parse_user_feedback(self, feedback: str, commands: Dict[str, Any]):
        """Parse user's natural language feedback."""
        feedback_lower = feedback.lower()
        
        # Duration commands
        duration_pattern = r'make\s+(?:the\s+)?(?:clip|segment)\s+at\s+([\d:]+)\s+(\d+(?:\.\d+)?)\s*seconds?'
        for match in re.finditer(duration_pattern, feedback_lower):
            timestamp = match.group(1)
            duration = float(match.group(2))
            segment_id = self._timestamp_to_segment_id(timestamp)
            if segment_id:
                commands["adjust_durations"][segment_id] = duration
        
        # Transition commands
        transition_pattern = r'use\s+(\w+(?:\s+\w+)?)\s+(?:transition\s+)?at\s+([\d:]+)'
        for match in re.finditer(transition_pattern, feedback_lower):
            transition_text = match.group(1)
            timestamp = match.group(2)
            segment_id = self._timestamp_to_segment_id(timestamp)
            
            if segment_id and transition_text in self.transition_map:
                commands["change_transitions"][segment_id] = self.transition_map[transition_text]
        
        # Removal commands
        if "remove" in feedback_lower or "delete" in feedback_lower:
            remove_pattern = r'(?:remove|delete)\s+(?:the\s+)?(?:clip|segment)\s+at\s+([\d:]+)'
            for match in re.finditer(remove_pattern, feedback_lower):
                timestamp = match.group(1)
                segment_id = self._timestamp_to_segment_id(timestamp)
                if segment_id and segment_id not in commands["remove_segments"]:
                    commands["remove_segments"].append(segment_id)
    
    def _timestamp_to_segment_id(self, timestamp: str) -> Optional[str]:
        """Convert timestamp to segment ID (placeholder implementation)."""
        # In real implementation, this would map timestamps to actual segment IDs
        # For now, return a mock ID
        if "-" in timestamp:
            start_time = timestamp.split("-")[0]
        else:
            start_time = timestamp
        
        # Convert MM:SS to seconds
        if ":" in start_time:
            parts = start_time.split(":")
            seconds = int(parts[0]) * 60 + int(parts[1])
        else:
            try:
                seconds = float(start_time)
            except ValueError:
                return None
        
        # Mock segment ID based on time
        return f"segment_{int(seconds)}"


# Create the refinement parsing tool function
async def parse_refinements(
    evaluation_results: Dict[str, Any],
    user_feedback: str = "",
    timeline_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Parse evaluation feedback into edit commands.
    
    Args:
        evaluation_results: Results from video evaluation
        user_feedback: Additional user feedback/requests
        timeline_info: Current timeline information for context
        
    Returns:
        Edit commands dictionary
    """
    try:
        parser = RefinementParser()
        
        # Parse feedback into commands
        commands = parser.parse_feedback_to_commands(
            evaluation=evaluation_results,
            user_feedback=user_feedback
        )
        
        # Add timeline context if provided
        if timeline_info:
            # This would enhance command generation with actual segment IDs
            pass
        
        logger.info(f"Parsed {len(commands)} command categories")
        
        return {
            "status": "success",
            "edit_commands": commands,
            "command_count": sum(
                len(v) if isinstance(v, (list, dict)) else 1 
                for v in commands.values()
            )
        }
        
    except Exception as e:
        logger.error(f"Refinement parsing failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Create natural language command parser
async def parse_user_request(
    user_request: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Parse natural language user request into structured commands.
    
    Args:
        user_request: Natural language request from user
        context: Additional context (timeline, evaluation, etc.)
        
    Returns:
        Parsed commands and intent
    """
    try:
        request_lower = user_request.lower()
        
        # Detect intent
        intent = "edit"  # default
        if any(word in request_lower for word in ["create", "make", "generate"]):
            intent = "create"
        elif any(word in request_lower for word in ["evaluate", "check", "review"]):
            intent = "evaluate"
        elif any(word in request_lower for word in ["export", "save", "finalize"]):
            intent = "export"
        
        # Parse parameters
        parameters = {}
        
        # Duration
        duration_match = re.search(r'(\d+)\s*(?:second|minute)s?', request_lower)
        if duration_match:
            value = int(duration_match.group(1))
            unit = "minutes" if "minute" in duration_match.group(0) else "seconds"
            parameters["duration"] = value * (60 if unit == "minutes" else 1)
        
        # Style
        for style in ["dynamic", "smooth", "fast", "slow", "energetic", "calm"]:
            if style in request_lower:
                parameters["style"] = style
                break
        
        # Quality
        if "preview" in request_lower or "quick" in request_lower:
            parameters["quality"] = "preview"
        elif "final" in request_lower or "high quality" in request_lower:
            parameters["quality"] = "final"
        
        return {
            "status": "success",
            "intent": intent,
            "parameters": parameters,
            "original_request": user_request
        }
        
    except Exception as e:
        logger.error(f"Request parsing failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Create ADK tools
parse_refinements_tool = FunctionTool(parse_refinements)

parse_user_request_tool = FunctionTool(parse_user_request)