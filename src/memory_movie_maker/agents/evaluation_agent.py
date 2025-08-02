"""Evaluation agent for critiquing generated videos."""

import logging
from typing import Dict, Any, Optional, List

from google.adk.agents import Agent

from ..tools.video_evaluation import evaluate_video_tool
from ..models.project_state import ProjectState


logger = logging.getLogger(__name__)


class EvaluationAgent(Agent):
    """Agent responsible for evaluating and critiquing generated videos."""
    
    def __init__(self):
        """Initialize evaluation agent."""
        super().__init__(
            name="EvaluationAgent",
            model="gemini-2.0-flash",
            description="Evaluates video quality and provides improvement suggestions",
            instruction="""You are an expert video critic and editor. Your responsibilities:
            1. Evaluate rendered videos for quality and effectiveness
            2. Identify technical issues (sync, transitions, quality)
            3. Assess creative aspects (pacing, storytelling, emotion)
            4. Provide specific, actionable feedback
            5. Recommend whether to accept, adjust, or rework
            
            Evaluation criteria:
            - Music synchronization and rhythm
            - Visual flow and storytelling
            - Technical quality (resolution, smoothness)
            - Emotional impact and engagement
            - Adherence to user's original request
            
            Always provide:
            - Overall score (1-10)
            - Specific timestamps for issues
            - Clear improvement suggestions
            - Priority of changes needed
            
            Be constructive and specific in feedback.""",
            tools=[evaluate_video_tool]
        )
    
    async def evaluate_memory_movie(
        self,
        project_state: ProjectState,
        video_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate a generated memory movie.
        
        Args:
            project_state: Current project state
            video_path: Specific video to evaluate (uses latest if not provided)
            
        Returns:
            Evaluation results with recommendations
        """
        try:
            logger.info("Starting video evaluation...")
            
            # Run evaluation
            result = await evaluate_video_tool.run(
                project_state=project_state.model_dump(),
                video_path=video_path
            )
            
            if result["status"] != "success":
                raise RuntimeError(f"Evaluation failed: {result.get('error')}")
            
            evaluation = result["evaluation"]
            
            # Log summary
            logger.info(f"Evaluation complete: Score {evaluation['overall_score']}/10")
            logger.info(f"Recommendation: {evaluation['recommendation']}")
            
            # Update project state
            updated_state = ProjectState(**result["updated_state"])
            
            # Create detailed feedback
            feedback = self._create_feedback_summary(evaluation)
            
            return {
                "status": "success",
                "evaluation": evaluation,
                "feedback_summary": feedback,
                "updated_state": updated_state
            }
            
        except Exception as e:
            logger.error(f"Video evaluation failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _create_feedback_summary(self, evaluation: Dict[str, Any]) -> str:
        """Create human-readable feedback summary."""
        score = evaluation.get("overall_score", 0)
        recommendation = evaluation.get("recommendation", "unknown")
        
        summary_parts = [
            f"Overall Score: {score}/10",
            f"Recommendation: {recommendation.replace('_', ' ').title()}"
        ]
        
        # Strengths
        strengths = evaluation.get("strengths", [])
        if strengths:
            summary_parts.append("\nStrengths:")
            for strength in strengths[:3]:  # Top 3
                summary_parts.append(f"   {strength}")
        
        # Key issues
        weaknesses = evaluation.get("weaknesses", [])
        technical_issues = evaluation.get("technical_issues", [])
        all_issues = weaknesses + technical_issues
        
        if all_issues:
            summary_parts.append("\nKey Issues:")
            for issue in all_issues[:3]:  # Top 3
                summary_parts.append(f"  " {issue}")
        
        # Top suggestions
        suggestions = evaluation.get("creative_suggestions", [])
        if suggestions:
            summary_parts.append("\nTop Suggestions:")
            for suggestion in suggestions[:2]:  # Top 2
                summary_parts.append(f"  ’ {suggestion}")
        
        # Specific edits count
        specific_edits = evaluation.get("specific_edits", [])
        if specific_edits:
            summary_parts.append(f"\n{len(specific_edits)} specific edits recommended")
        
        return "\n".join(summary_parts)
    
    def extract_priority_edits(
        self,
        evaluation: Dict[str, Any],
        max_edits: int = 5
    ) -> List[Dict[str, Any]]:
        """Extract priority edits from evaluation.
        
        Args:
            evaluation: Full evaluation results
            max_edits: Maximum number of edits to return
            
        Returns:
            List of priority edits
        """
        specific_edits = evaluation.get("specific_edits", [])
        
        # Prioritize edits based on impact
        priority_keywords = ["sync", "abrupt", "quality", "missing", "error"]
        
        priority_edits = []
        other_edits = []
        
        for edit in specific_edits:
            issue = edit.get("issue", "").lower()
            if any(keyword in issue for keyword in priority_keywords):
                priority_edits.append(edit)
            else:
                other_edits.append(edit)
        
        # Combine and limit
        all_edits = priority_edits + other_edits
        return all_edits[:max_edits]
    
    def should_accept_video(self, evaluation: Dict[str, Any]) -> bool:
        """Determine if video should be accepted based on evaluation.
        
        Args:
            evaluation: Evaluation results
            
        Returns:
            True if video is acceptable
        """
        score = evaluation.get("overall_score", 0)
        recommendation = evaluation.get("recommendation", "")
        
        # Accept if score >= 7 and recommendation is "accept" or "minor_adjustments"
        return score >= 7.0 and recommendation in ["accept", "minor_adjustments"]


# Test function
async def test_evaluation_agent():
    """Test the evaluation agent."""
    from ..models.project_state import ProjectState, UserInputs, ProjectStatus
    import uuid
    
    # Create test project with rendered video
    project_state = ProjectState(
        user_inputs=UserInputs(
            media=[],
            initial_prompt="Create a dynamic travel video"
        ),
        project_status=ProjectStatus(phase="evaluating"),
        rendered_outputs=["data/renders/test_video.mp4"]
    )
    
    # Create and test agent
    agent = EvaluationAgent()
    result = await agent.evaluate_memory_movie(project_state)
    
    if result["status"] == "success":
        print("Evaluation Results:")
        print(result["feedback_summary"])
        
        # Check if we should accept
        should_accept = agent.should_accept_video(result["evaluation"])
        print(f"\nAccept video? {should_accept}")
        
        # Get priority edits
        priority_edits = agent.extract_priority_edits(result["evaluation"])
        if priority_edits:
            print(f"\nPriority edits ({len(priority_edits)}):")
            for edit in priority_edits:
                print(f"  - {edit['timestamp']}: {edit['issue']}")
    else:
        print(f"Evaluation failed: {result.get('error')}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_evaluation_agent())