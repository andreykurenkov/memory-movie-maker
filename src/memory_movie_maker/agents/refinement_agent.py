"""Refinement agent for parsing and applying video edits."""

import logging
from typing import Dict, Any, Optional, List

from google.adk.agents import Agent

from ..tools.refinement_parser import parse_refinements_tool, parse_user_request_tool
from ..models.project_state import ProjectState


logger = logging.getLogger(__name__)


class RefinementAgent(Agent):
    """Agent responsible for parsing feedback and creating edit commands."""
    
    def __init__(self):
        """Initialize refinement agent."""
        super().__init__(
            name="RefinementAgent",
            model="gemini-2.0-flash",
            description="Parses feedback and creates actionable edit commands",
            instruction="""You are an expert at understanding video editing feedback and 
            translating it into specific, actionable commands. Your responsibilities:
            
            1. Parse evaluation results into edit commands
            2. Understand natural language user requests
            3. Create precise editing instructions
            4. Prioritize changes based on impact
            5. Ensure edits maintain video coherence
            
            When parsing feedback:
            - Extract specific timestamps and changes
            - Identify transition and effect requests
            - Understand duration and pacing adjustments
            - Recognize segment reordering needs
            - Detect quality and style preferences
            
            Command types you can generate:
            - reorder_segments: Change clip order
            - adjust_durations: Modify clip lengths
            - change_transitions: Update transition types
            - add_effects: Apply visual effects
            - remove_segments: Delete clips
            - replace_segments: Swap clips
            
            Always ensure commands are:
            - Specific and actionable
            - Technically feasible
            - Aligned with user intent
            - Prioritized by importance""",
            tools=[parse_refinements_tool, parse_user_request_tool]
        )
    
    async def process_evaluation_feedback(
        self,
        project_state: ProjectState,
        evaluation_results: Dict[str, Any],
        user_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process evaluation results into edit commands.
        
        Args:
            project_state: Current project state
            evaluation_results: Results from EvaluationAgent
            user_feedback: Additional user input
            
        Returns:
            Edit commands and recommendations
        """
        try:
            logger.info("Processing evaluation feedback...")
            
            # Extract timeline info for context
            timeline_info = None
            if project_state.timeline:
                timeline_info = {
                    "segments": len(project_state.timeline.segments),
                    "duration": project_state.timeline.total_duration,
                    "segment_details": [
                        {
                            "id": seg.media_id,
                            "start": seg.start_time,
                            "duration": seg.duration
                        }
                        for seg in project_state.timeline.segments
                    ]
                }
            
            # Parse refinements
            result = await parse_refinements_tool.run(
                evaluation_results=evaluation_results,
                user_feedback=user_feedback or "",
                timeline_info=timeline_info
            )
            
            if result["status"] != "success":
                raise RuntimeError(f"Refinement parsing failed: {result.get('error')}")
            
            edit_commands = result["edit_commands"]
            
            # Create summary
            summary = self._create_edit_summary(edit_commands)
            
            # Determine if changes are worth applying
            recommendation = self._get_edit_recommendation(
                evaluation_results,
                edit_commands
            )
            
            return {
                "status": "success",
                "edit_commands": edit_commands,
                "summary": summary,
                "recommendation": recommendation,
                "command_count": result["command_count"]
            }
            
        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def parse_user_edit_request(
        self,
        user_request: str,
        project_state: ProjectState
    ) -> Dict[str, Any]:
        """Parse user's natural language edit request.
        
        Args:
            user_request: User's request in natural language
            project_state: Current project state for context
            
        Returns:
            Parsed intent and parameters
        """
        try:
            logger.info(f"Parsing user request: {user_request[:50]}...")
            
            # Create context
            context = {
                "has_timeline": project_state.timeline is not None,
                "has_renders": len(project_state.rendered_outputs) > 0,
                "current_phase": project_state.project_status.phase,
                "media_count": len(project_state.user_inputs.media)
            }
            
            # Parse request
            result = await parse_user_request_tool.run(
                user_request=user_request,
                context=context
            )
            
            if result["status"] != "success":
                raise RuntimeError(f"Request parsing failed: {result.get('error')}")
            
            intent = result["intent"]
            parameters = result["parameters"]
            
            # Enhance with context-aware suggestions
            suggestions = self._get_contextual_suggestions(
                intent, parameters, project_state
            )
            
            return {
                "status": "success",
                "intent": intent,
                "parameters": parameters,
                "suggestions": suggestions,
                "ready_to_execute": self._can_execute(intent, project_state)
            }
            
        except Exception as e:
            logger.error(f"User request parsing failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _create_edit_summary(self, edit_commands: Dict[str, Any]) -> str:
        """Create human-readable summary of edit commands."""
        summary_parts = []
        
        if "reorder_segments" in edit_commands:
            count = len(edit_commands["reorder_segments"])
            summary_parts.append(f"Reorder {count} segments")
        
        if "adjust_durations" in edit_commands:
            count = len(edit_commands["adjust_durations"])
            total_change = sum(edit_commands["adjust_durations"].values())
            summary_parts.append(
                f"Adjust {count} clip durations ({total_change:+.1f}s total)"
            )
        
        if "change_transitions" in edit_commands:
            count = len(edit_commands["change_transitions"])
            summary_parts.append(f"Change {count} transitions")
        
        if "add_effects" in edit_commands:
            count = sum(len(effects) for effects in edit_commands["add_effects"].values())
            summary_parts.append(f"Add {count} effects")
        
        if "remove_segments" in edit_commands:
            count = len(edit_commands["remove_segments"])
            summary_parts.append(f"Remove {count} segments")
        
        return " | ".join(summary_parts) if summary_parts else "No edits needed"
    
    def _get_edit_recommendation(
        self,
        evaluation: Dict[str, Any],
        edit_commands: Dict[str, Any]
    ) -> str:
        """Determine recommendation based on evaluation and edits."""
        score = evaluation.get("overall_score", 0)
        eval_recommendation = evaluation.get("recommendation", "")
        command_count = sum(
            len(v) if isinstance(v, (list, dict)) else 1 
            for v in edit_commands.values()
        )
        
        if score >= 8.0 and command_count < 3:
            return "apply_minor_edits"
        elif score >= 6.0 and command_count < 10:
            return "apply_edits"
        elif command_count > 15:
            return "consider_regeneration"
        else:
            return "apply_edits"
    
    def _get_contextual_suggestions(
        self,
        intent: str,
        parameters: Dict[str, Any],
        project_state: ProjectState
    ) -> List[str]:
        """Get context-aware suggestions for user."""
        suggestions = []
        
        if intent == "create" and not project_state.timeline:
            suggestions.append("Need to run composition first")
        
        if intent == "edit" and not project_state.timeline:
            suggestions.append("No timeline to edit - create one first")
        
        if intent == "evaluate" and not project_state.rendered_outputs:
            suggestions.append("No video to evaluate - render one first")
        
        if "duration" in parameters and project_state.timeline:
            current_duration = project_state.timeline.total_duration
            target_duration = parameters["duration"]
            if abs(current_duration - target_duration) > 10:
                suggestions.append(
                    f"Large duration change ({current_duration:.0f}s ’ {target_duration}s)"
                )
        
        return suggestions
    
    def _can_execute(self, intent: str, project_state: ProjectState) -> bool:
        """Check if intent can be executed given current state."""
        if intent == "create":
            return len(project_state.user_inputs.media) > 0
        elif intent == "edit":
            return project_state.timeline is not None
        elif intent == "evaluate":
            return len(project_state.rendered_outputs) > 0
        elif intent == "export":
            return len(project_state.rendered_outputs) > 0
        
        return False


# Test function
async def test_refinement_agent():
    """Test the refinement agent."""
    from ..models.project_state import ProjectState, UserInputs, ProjectStatus
    from ..models.timeline import Timeline, Segment
    
    # Create test evaluation results
    evaluation_results = {
        "overall_score": 7.5,
        "recommendation": "minor_adjustments",
        "specific_edits": [
            {
                "timestamp": "0:15-0:18",
                "issue": "Clip too short",
                "suggestion": "Extend clip duration by 2 seconds"
            },
            {
                "timestamp": "0:32",
                "issue": "Abrupt transition",
                "suggestion": "Use crossfade transition instead"
            }
        ]
    }
    
    # Create test project state
    project_state = ProjectState(
        user_inputs=UserInputs(
            media=[],
            initial_prompt="Create test video"
        ),
        project_status=ProjectStatus(phase="refining"),
        timeline=Timeline(
            segments=[
                Segment(media_id="seg1", start_time=0, duration=3),
                Segment(media_id="seg2", start_time=3, duration=2)
            ],
            total_duration=5
        )
    )
    
    # Test agent
    agent = RefinementAgent()
    
    # Test evaluation processing
    print("Testing evaluation feedback processing...")
    result = await agent.process_evaluation_feedback(
        project_state=project_state,
        evaluation_results=evaluation_results,
        user_feedback="Also make the music louder at the end"
    )
    
    if result["status"] == "success":
        print(f"Edit Summary: {result['summary']}")
        print(f"Commands: {result['edit_commands']}")
        print(f"Recommendation: {result['recommendation']}")
    
    # Test user request parsing
    print("\nTesting user request parsing...")
    request_result = await agent.parse_user_edit_request(
        "Make the video 30 seconds long with smooth transitions",
        project_state
    )
    
    if request_result["status"] == "success":
        print(f"Intent: {request_result['intent']}")
        print(f"Parameters: {request_result['parameters']}")
        print(f"Can execute: {request_result['ready_to_execute']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_refinement_agent())