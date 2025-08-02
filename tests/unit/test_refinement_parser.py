"""Tests for refinement parser tool."""

import pytest
from memory_movie_maker.tools.refinement_parser import (
    RefinementParser, parse_refinements, parse_user_request
)
from memory_movie_maker.models.timeline import TransitionType


class TestRefinementParser:
    """Test refinement parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return RefinementParser()
    
    @pytest.fixture
    def sample_evaluation(self):
        """Create sample evaluation results."""
        return {
            "overall_score": 7.0,
            "recommendation": "minor_adjustments",
            "specific_edits": [
                {
                    "timestamp": "0:15",
                    "issue": "Clip too short",
                    "suggestion": "Extend clip by 2 seconds"
                },
                {
                    "timestamp": "0:30",
                    "issue": "Abrupt transition",
                    "suggestion": "Use crossfade transition"
                },
                {
                    "timestamp": "1:00-1:05",
                    "issue": "Clip too long",
                    "suggestion": "Shorten by 3 seconds"
                }
            ],
            "creative_suggestions": [
                "Add more dynamic transitions during high-energy sections",
                "Consider longer clips for emotional moments"
            ]
        }
    
    def test_parse_specific_edit_duration_extend(self, parser):
        """Test parsing duration extension edit."""
        edit = {
            "timestamp": "0:15",
            "issue": "too short",
            "suggestion": "extend by 2 seconds"
        }
        commands = {}
        
        parser._parse_specific_edit(edit, commands)
        
        assert "adjust_durations" in commands
        assert commands["adjust_durations"]["segment_15"] == 2.0
    
    def test_parse_specific_edit_duration_shorten(self, parser):
        """Test parsing duration shortening edit."""
        edit = {
            "timestamp": "1:00",
            "issue": "too long",
            "suggestion": "shorten by 3 seconds"
        }
        commands = {}
        
        parser._parse_specific_edit(edit, commands)
        
        assert "adjust_durations" in commands
        assert commands["adjust_durations"]["segment_60"] == -3.0
    
    def test_parse_specific_edit_transition(self, parser):
        """Test parsing transition change edit."""
        edit = {
            "timestamp": "0:30",
            "issue": "abrupt",
            "suggestion": "use crossfade transition"
        }
        commands = {}
        
        parser._parse_specific_edit(edit, commands)
        
        assert "change_transitions" in commands
        assert commands["change_transitions"]["segment_30"] == TransitionType.CROSSFADE
    
    def test_parse_specific_edit_effect(self, parser):
        """Test parsing effect addition edit."""
        edit = {
            "timestamp": "0:45",
            "issue": "static",
            "suggestion": "add ken burns effect"
        }
        commands = {}
        
        parser._parse_specific_edit(edit, commands)
        
        assert "add_effects" in commands
        assert "ken_burns" in commands["add_effects"]["segment_45"]
    
    def test_parse_user_feedback_duration(self, parser):
        """Test parsing user duration feedback."""
        feedback = "Make the clip at 0:15 5 seconds long"
        commands = {}
        
        parser._parse_user_feedback(feedback, commands)
        
        assert "adjust_durations" in commands
        assert commands["adjust_durations"]["segment_15"] == 5.0
    
    def test_parse_user_feedback_transition(self, parser):
        """Test parsing user transition feedback."""
        feedback = "Use fade to black transition at 1:30"
        commands = {}
        
        parser._parse_user_feedback(feedback, commands)
        
        assert "change_transitions" in commands
        assert commands["change_transitions"]["segment_90"] == TransitionType.FADE_TO_BLACK
    
    def test_parse_user_feedback_removal(self, parser):
        """Test parsing user removal feedback."""
        feedback = "Remove the clip at 0:45"
        commands = {}
        
        parser._parse_user_feedback(feedback, commands)
        
        assert "remove_segments" in commands
        assert "segment_45" in commands["remove_segments"]
    
    def test_timestamp_to_segment_id(self, parser):
        """Test timestamp to segment ID conversion."""
        # Test MM:SS format
        assert parser._timestamp_to_segment_id("1:30") == "segment_90"
        
        # Test seconds format
        assert parser._timestamp_to_segment_id("45") == "segment_45"
        
        # Test range format
        assert parser._timestamp_to_segment_id("1:00-1:30") == "segment_60"
        
        # Test invalid format
        assert parser._timestamp_to_segment_id("invalid") is None
    
    def test_parse_feedback_to_commands_complete(
        self, parser, sample_evaluation
    ):
        """Test complete feedback parsing."""
        user_feedback = "Also make the music louder and remove the last clip"
        
        commands = parser.parse_feedback_to_commands(
            evaluation=sample_evaluation,
            user_feedback=user_feedback
        )
        
        # Should have multiple command types
        assert len(commands) > 0
        assert any(k in commands for k in ["adjust_durations", "change_transitions"])


class TestParseRefinementsTool:
    """Test parse refinements tool function."""
    
    @pytest.mark.asyncio
    async def test_parse_refinements_success(self):
        """Test successful refinement parsing."""
        evaluation = {
            "specific_edits": [
                {
                    "timestamp": "0:15",
                    "issue": "Too short",
                    "suggestion": "Extend by 2 seconds"
                }
            ]
        }
        
        result = await parse_refinements(
            evaluation_results=evaluation,
            user_feedback="Make it smoother"
        )
        
        assert result["status"] == "success"
        assert "edit_commands" in result
        assert result["command_count"] > 0
    
    @pytest.mark.asyncio
    async def test_parse_refinements_error(self):
        """Test refinement parsing error handling."""
        # Invalid evaluation structure
        result = await parse_refinements(
            evaluation_results=None,
            user_feedback=""
        )
        
        assert result["status"] == "error"


class TestParseUserRequestTool:
    """Test parse user request tool function."""
    
    @pytest.mark.asyncio
    async def test_parse_create_request(self):
        """Test parsing create request."""
        result = await parse_user_request(
            user_request="Create a 30 second dynamic video"
        )
        
        assert result["status"] == "success"
        assert result["intent"] == "create"
        assert result["parameters"]["duration"] == 30
        assert result["parameters"]["style"] == "dynamic"
    
    @pytest.mark.asyncio
    async def test_parse_edit_request(self):
        """Test parsing edit request."""
        result = await parse_user_request(
            user_request="Make the transitions smoother"
        )
        
        assert result["status"] == "success"
        assert result["intent"] == "edit"
        assert result["parameters"]["style"] == "smooth"
    
    @pytest.mark.asyncio
    async def test_parse_evaluate_request(self):
        """Test parsing evaluate request."""
        result = await parse_user_request(
            user_request="Check the video quality"
        )
        
        assert result["status"] == "success"
        assert result["intent"] == "evaluate"
    
    @pytest.mark.asyncio
    async def test_parse_quality_parameter(self):
        """Test parsing quality parameter."""
        result = await parse_user_request(
            user_request="Create a quick preview"
        )
        
        assert result["parameters"]["quality"] == "preview"
        
        result = await parse_user_request(
            user_request="Export final high quality version"
        )
        
        assert result["intent"] == "export"
        assert result["parameters"]["quality"] == "final"