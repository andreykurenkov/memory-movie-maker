"""
Example: Gemini API Prompts for Memory Movie Maker

This file contains example prompts and structured outputs for various
Gemini API calls used throughout the system.
"""

import json
from typing import Dict, Any, List

# =============================================================================
# Visual Analysis Prompts
# =============================================================================

VISUAL_ANALYSIS_PROMPT = """
Analyze this media file and provide a structured JSON response with the following information:

{
    "description": "A brief, descriptive summary of what's shown (max 100 words)",
    "aesthetic_score": 0.0,  // Float between 0.0-1.0 rating visual appeal
    "quality_issues": [],    // Array of strings: ["blur", "overexposed", "underexposed", "noise", "artifacts"]
    "main_subjects": [],     // Array of identified subjects: ["person", "landscape", "animal", "building", etc.]
    "tags": [],             // Descriptive tags: ["sunset", "beach", "family", "celebration", etc.]
    "best_moment_timestamp": null,  // For videos: float timestamp in seconds of the most visually appealing moment
    "motion_level": null,    // For videos: "static", "slow", "medium", "fast"
    "composition": {
        "rule_of_thirds": true/false,
        "leading_lines": true/false,
        "symmetry": true/false,
        "framing": "good"/"average"/"poor"
    },
    "colors": {
        "dominant_colors": ["blue", "orange", "green"],  // Top 3 dominant colors
        "mood": "vibrant"/"muted"/"monochrome"/"warm"/"cool"
    },
    "suggested_use": "opening"/"highlight"/"transition"/"closing"  // Suggestion for video placement
}

Important guidelines:
- Be objective and descriptive
- Focus on visual elements that would matter for video editing
- For videos, identify the single best moment that could work as a still frame
- Consider how this media would fit into a larger video narrative
"""

# Example response for a beach photo
EXAMPLE_VISUAL_ANALYSIS_RESPONSE = {
    "description": "Stunning tropical beach scene during golden hour with palm trees silhouetted against a vibrant orange and pink sunset sky. Crystal clear turquoise water gently laps at pristine white sand.",
    "aesthetic_score": 0.92,
    "quality_issues": [],
    "main_subjects": ["beach", "ocean", "palm trees", "sunset", "sky"],
    "tags": ["tropical", "vacation", "paradise", "golden hour", "scenic", "relaxing"],
    "best_moment_timestamp": None,
    "motion_level": None,
    "composition": {
        "rule_of_thirds": True,
        "leading_lines": True,
        "symmetry": False,
        "framing": "good"
    },
    "colors": {
        "dominant_colors": ["orange", "blue", "pink"],
        "mood": "warm"
    },
    "suggested_use": "highlight"
}

# =============================================================================
# Video Critique Prompts
# =============================================================================

VIDEO_CRITIQUE_PROMPT = """
You are a professional video editor reviewing a generated video. The user requested: "{user_prompt}"

Watch the video and provide constructive feedback in the following JSON format:

{
    "overall_assessment": {
        "matches_user_intent": 0.0,  // 0.0-1.0 how well it matches the request
        "technical_quality": 0.0,     // 0.0-1.0 technical execution
        "emotional_impact": 0.0,      // 0.0-1.0 emotional resonance
        "pacing_score": 0.0          // 0.0-1.0 rhythm and flow
    },
    "strengths": [
        "Clear description of what works well",
        "Another positive aspect"
    ],
    "areas_for_improvement": [
        {
            "issue": "Description of the problem",
            "severity": "high"/"medium"/"low",
            "suggestion": "Specific actionable improvement",
            "time_range": [start_seconds, end_seconds]  // Optional: specific time range
        }
    ],
    "specific_recommendations": [
        "Add more dynamic shots in the opening 10 seconds",
        "Align the sunset sequence with the music climax at 1:45",
        "Include more close-up shots of people"
    ],
    "music_sync_analysis": {
        "beat_alignment": 0.0,  // 0.0-1.0 how well cuts align with beats
        "energy_matching": 0.0,  // 0.0-1.0 visual energy matches audio energy
        "suggestions": ["Specific timing adjustments"]
    }
}

Focus on actionable feedback that can be translated into editing commands.
Be specific about timing and content issues.
"""

# Example critique for a vacation video
EXAMPLE_VIDEO_CRITIQUE_RESPONSE = {
    "overall_assessment": {
        "matches_user_intent": 0.75,
        "technical_quality": 0.85,
        "emotional_impact": 0.70,
        "pacing_score": 0.65
    },
    "strengths": [
        "Beautiful sunset sequence perfectly captures the romantic mood",
        "Good variety of wide shots showing the scenic location",
        "Smooth transitions between scenes"
    ],
    "areas_for_improvement": [
        {
            "issue": "Opening feels too slow for an 'upbeat' video",
            "severity": "medium",
            "suggestion": "Start with more dynamic beach activity shots",
            "time_range": [0, 15]
        },
        {
            "issue": "Music climax at 1:30 doesn't align with visual highlight",
            "severity": "high",
            "suggestion": "Move sunset sequence to coincide with music peak",
            "time_range": [85, 95]
        }
    ],
    "specific_recommendations": [
        "Replace first clip with beach volleyball or water sports footage",
        "Add 2-3 quick cuts of people laughing between 0:20-0:30",
        "Extend the sunset sequence by 3 seconds for better music alignment"
    ],
    "music_sync_analysis": {
        "beat_alignment": 0.70,
        "energy_matching": 0.65,
        "suggestions": [
            "Adjust cut at 0:45 to land exactly on the beat",
            "Speed up transitions during high-energy chorus (1:00-1:30)"
        ]
    }
}

# =============================================================================
# Natural Language Command Parsing Prompts
# =============================================================================

NLP_COMMAND_PARSING_PROMPT = """
Parse the following user feedback into structured editing commands.

User feedback: "{user_feedback}"

Convert this into a JSON array of specific editing commands:

[
    {
        "intent": "REPLACE_CONTENT" | "ADJUST_PACING" | "REORDER_SEGMENTS" | "ADD_CONTENT" | "REMOVE_CONTENT" | "ADJUST_DURATION",
        "parameters": {
            // For REPLACE_CONTENT:
            "segment_indices": [0, 1],  // Which segments to replace
            "content_filter": ["dynamic", "people", "sunset"],  // What type of content to use
            
            // For ADJUST_PACING:
            "time_range": [start, end],  // In seconds
            "speed_factor": 1.5,  // 1.0 = normal, >1 = faster, <1 = slower
            
            // For REORDER_SEGMENTS:
            "from_index": 3,
            "to_index": 1,
            
            // For ADD_CONTENT:
            "position": "after_segment_2" | "at_time_45",
            "content_filter": ["beach", "activity"],
            "duration": 5.0,
            
            // For REMOVE_CONTENT:
            "segment_indices": [4, 5],
            
            // For ADJUST_DURATION:
            "segment_index": 2,
            "new_duration": 4.5
        },
        "reasoning": "Brief explanation of why this change addresses the feedback"
    }
]

Map natural language to specific, executable commands. Examples:
- "make it faster" -> ADJUST_PACING with speed_factor > 1
- "more sunset shots" -> REPLACE_CONTENT or ADD_CONTENT with content_filter: ["sunset"]
- "remove the boring part in the middle" -> REMOVE_CONTENT with appropriate segment_indices
- "start with something exciting" -> REPLACE_CONTENT for segment_indices: [0]
"""

# Example parsing of natural language feedback
EXAMPLE_NLP_PARSING = {
    "input": "Make the beginning more exciting and add more shots of people having fun. The middle part drags a bit.",
    "output": [
        {
            "intent": "REPLACE_CONTENT",
            "parameters": {
                "segment_indices": [0, 1],
                "content_filter": ["dynamic", "activity", "people", "excitement"]
            },
            "reasoning": "User wants a more exciting opening"
        },
        {
            "intent": "ADD_CONTENT",
            "parameters": {
                "position": "throughout",
                "content_filter": ["people", "fun", "laughing", "activity"],
                "duration": 3.0
            },
            "reasoning": "User requested more shots of people having fun"
        },
        {
            "intent": "ADJUST_PACING",
            "parameters": {
                "time_range": [60, 90],
                "speed_factor": 1.3
            },
            "reasoning": "User mentioned the middle part drags, suggesting faster pacing needed"
        }
    ]
}

# =============================================================================
# Helper Functions for Prompt Construction
# =============================================================================

def create_visual_analysis_prompt(media_type: str, context: Dict[str, Any]) -> str:
    """Create a customized visual analysis prompt based on media type and context."""
    
    base_prompt = VISUAL_ANALYSIS_PROMPT
    
    # Add context-specific instructions
    if context.get("style_preferences"):
        style = context["style_preferences"]
        base_prompt += f"\n\nAdditional context: The user wants a {style.get('vibe', 'general')} "
        base_prompt += f"{style.get('theme', 'video')}. Pay special attention to content that "
        base_prompt += f"matches this theme."
    
    if media_type == "video":
        base_prompt += "\n\nFor this video, pay special attention to:"
        base_prompt += "\n- Identify the most visually striking moment"
        base_prompt += "\n- Note any camera movement or stability issues"
        base_prompt += "\n- Assess the overall visual consistency"
    
    return base_prompt

def create_critique_prompt(user_prompt: str, video_duration: float, style: Dict[str, Any]) -> str:
    """Create a video critique prompt with specific context."""
    
    prompt = VIDEO_CRITIQUE_PROMPT.format(user_prompt=user_prompt)
    
    # Add duration context
    prompt += f"\n\nVideo duration: {video_duration} seconds"
    prompt += f"\nRequested duration: {style.get('target_duration', 'not specified')} seconds"
    
    # Add style context
    if style.get('vibe'):
        prompt += f"\nRequested vibe: {style['vibe']}"
    
    return prompt

def validate_gemini_response(response: str, expected_schema: str) -> Dict[str, Any]:
    """Validate and parse Gemini's JSON response."""
    
    try:
        # Parse JSON
        data = json.loads(response)
        
        # Basic validation based on expected schema
        if expected_schema == "visual_analysis":
            required_keys = ["description", "aesthetic_score", "quality_issues", "main_subjects", "tags"]
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Missing required key: {key}")
        
        return data
        
    except json.JSONDecodeError as e:
        # Try to extract JSON from response if it's wrapped in text
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError(f"Failed to parse Gemini response as JSON: {e}")

# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    print("Memory Movie Maker - Gemini Prompt Examples")
    print("=" * 60)
    
    # Example 1: Visual Analysis
    print("\n1. Visual Analysis Prompt:")
    print("-" * 40)
    print(VISUAL_ANALYSIS_PROMPT[:500] + "...")
    print("\nExample Response:")
    print(json.dumps(EXAMPLE_VISUAL_ANALYSIS_RESPONSE, indent=2)[:500] + "...")
    
    # Example 2: Video Critique
    print("\n\n2. Video Critique Prompt:")
    print("-" * 40)
    user_request = "Create a 2-minute upbeat video of our Hawaii vacation"
    critique_prompt = create_critique_prompt(user_request, 120.0, {"vibe": "upbeat"})
    print(critique_prompt[:500] + "...")
    
    # Example 3: NLP Command Parsing
    print("\n\n3. Natural Language Parsing:")
    print("-" * 40)
    print(f"User feedback: '{EXAMPLE_NLP_PARSING['input']}'")
    print("\nParsed commands:")
    for i, cmd in enumerate(EXAMPLE_NLP_PARSING['output']):
        print(f"\n  {i+1}. {cmd['intent']}")
        print(f"     Parameters: {cmd['parameters']}")
        print(f"     Reasoning: {cmd['reasoning']}")