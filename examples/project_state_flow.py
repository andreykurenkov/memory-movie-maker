"""
Example: ProjectState Flow Through Agents

This example demonstrates how ProjectState flows through the multi-agent system
during video creation, showing the transformations at each step.
"""

from datetime import datetime
from typing import Dict, Any
import json

# Example 1: Initial ProjectState after user input
initial_state = {
    "project_id": "proj_12345",
    "created_at": "2025-08-02T10:00:00Z",
    "updated_at": "2025-08-02T10:00:00Z",
    
    "user_inputs": {
        "media": [
            {
                "id": "media_001",
                "file_path": "/data/uploads/hawaii_beach.jpg",
                "type": "image",
                "upload_timestamp": "2025-08-02T10:00:00Z",
                "metadata": {"capture_time": "2025-07-15T14:30:00Z"},
                "required": False
            },
            {
                "id": "media_002",
                "file_path": "/data/uploads/sunset_timelapse.mp4",
                "type": "video",
                "upload_timestamp": "2025-08-02T10:01:00Z",
                "metadata": {"capture_time": "2025-07-15T18:45:00Z", "duration": 30.5},
                "required": True  # User marked this as must-include
            }
        ],
        "music": [
            {
                "id": "music_001",
                "file_path": "/data/uploads/upbeat_summer.mp3",
                "type": "audio",
                "upload_timestamp": "2025-08-02T10:02:00Z"
            }
        ],
        "initial_prompt": "Create a 2-minute upbeat video of our Hawaii vacation",
        "target_duration": 120,  # seconds
        "aspect_ratio": "16:9",
        "style_preferences": {
            "vibe": "upbeat",
            "theme": "vacation"
        }
    },
    
    "analysis": {
        "music_profiles": [],
        "media_pool": [],
        "analysis_timestamp": None
    },
    
    "timeline": {
        "segments": [],
        "total_duration": 0.0,
        "render_settings": {}
    },
    
    "history": {
        "prompts": [
            {
                "timestamp": "2025-08-02T10:00:00Z",
                "type": "user",
                "content": "Create a 2-minute upbeat video of our Hawaii vacation"
            }
        ],
        "versions": [],
        "feedback": []
    },
    
    "status": {
        "phase": "initialized",
        "progress": 0.0,
        "current_version": 0,
        "error": None
    }
}

# Example 2: ProjectState after AnalysisAgent processes it
after_analysis_state = {
    **initial_state,
    "updated_at": "2025-08-02T10:05:00Z",
    
    "analysis": {
        "music_profiles": [
            {
                "file_path": "/data/uploads/upbeat_summer.mp3",
                "beat_timestamps": [0.5, 1.0, 1.5, 2.0, 2.5],  # ... truncated
                "tempo_bpm": 128.0,
                "energy_curve": [0.3, 0.4, 0.6, 0.8, 0.9],  # ... truncated
                "duration": 180.0,
                "vibe": {
                    "danceability": 0.85,
                    "energy": 0.9,
                    "mood": "happy",
                    "genre": "pop"
                }
            }
        ],
        "media_pool": [
            {
                "id": "media_001",
                "file_path": "/data/uploads/hawaii_beach.jpg",
                "type": "image",
                "upload_timestamp": "2025-08-02T10:00:00Z",
                "metadata": {"capture_time": "2025-07-15T14:30:00Z"},
                "required": False,
                "gemini_analysis": {
                    "description": "Beautiful beach scene with palm trees and clear blue water",
                    "aesthetic_score": 0.92,
                    "quality_issues": [],
                    "main_subjects": ["beach", "ocean", "palm trees", "sky"],
                    "tags": ["tropical", "vacation", "paradise", "sunny"],
                    "best_moment_timestamp": None,
                    "motion_level": None
                }
            },
            {
                "id": "media_002",
                "file_path": "/data/uploads/sunset_timelapse.mp4",
                "type": "video",
                "upload_timestamp": "2025-08-02T10:01:00Z",
                "metadata": {"capture_time": "2025-07-15T18:45:00Z", "duration": 30.5},
                "required": True,
                "gemini_analysis": {
                    "description": "Stunning timelapse of sunset over ocean with vibrant colors",
                    "aesthetic_score": 0.95,
                    "quality_issues": [],
                    "main_subjects": ["sunset", "ocean", "clouds", "sky"],
                    "tags": ["dramatic", "colorful", "timelapse", "scenic"],
                    "best_moment_timestamp": 15.2,  # Best moment at 15.2 seconds
                    "motion_level": "medium"
                }
            }
        ],
        "analysis_timestamp": "2025-08-02T10:05:00Z"
    },
    
    "status": {
        "phase": "analysis_complete",
        "progress": 25.0,
        "current_version": 0,
        "error": None
    }
}

# Example 3: ProjectState after CompositionAgent creates timeline
after_composition_state = {
    **after_analysis_state,
    "updated_at": "2025-08-02T10:10:00Z",
    
    "timeline": {
        "segments": [
            {
                "media_asset_id": "media_001",
                "start_time": 0.0,
                "end_time": 3.5,
                "duration": 3.5,
                "in_point": 0.0,
                "out_point": None,  # Image, so no out point
                "transition": "fade_in"
            },
            {
                "media_asset_id": "media_002",
                "start_time": 3.5,
                "end_time": 8.5,
                "duration": 5.0,
                "in_point": 10.0,  # Start from 10s into the video
                "out_point": 15.0,  # End at 15s (the best moment)
                "transition": "crossfade"
            }
            # ... more segments to reach 120 seconds
        ],
        "total_duration": 120.0,
        "render_settings": {
            "output_format": "mp4",
            "resolution": "1920x1080",
            "fps": 30,
            "codec": "h264",
            "bitrate": "8M"
        }
    },
    
    "history": {
        **after_analysis_state["history"],
        "versions": [
            {
                "version": 1,
                "timestamp": "2025-08-02T10:10:00Z",
                "output_path": "/data/projects/proj_12345/output_v1.mp4",
                "agent": "composition_agent"
            }
        ]
    },
    
    "status": {
        "phase": "composition_complete",
        "progress": 50.0,
        "current_version": 1,
        "error": None
    }
}

# Example 4: ProjectState after EvaluationAgent critiques
after_evaluation_state = {
    **after_composition_state,
    "updated_at": "2025-08-02T10:12:00Z",
    
    "history": {
        **after_composition_state["history"],
        "feedback": [
            {
                "timestamp": "2025-08-02T10:12:00Z",
                "source": "evaluation_agent",
                "version": 1,
                "content": "The video matches the upbeat theme well with good pacing. However, the beginning could use more energy to match the music's intro. Consider starting with a more dynamic shot.",
                "suggestions": [
                    "Replace first segment with more dynamic content",
                    "Add more beach activity shots in first 30 seconds",
                    "Ensure sunset sequence aligns with music climax"
                ]
            }
        ]
    },
    
    "status": {
        "phase": "evaluation_complete",
        "progress": 60.0,
        "current_version": 1,
        "error": None
    }
}

# Example 5: ProjectState after RefinementAgent processes feedback
after_refinement_state = {
    **after_evaluation_state,
    "updated_at": "2025-08-02T10:13:00Z",
    
    "history": {
        **after_evaluation_state["history"],
        "prompts": [
            *after_evaluation_state["history"]["prompts"],
            {
                "timestamp": "2025-08-02T10:13:00Z",
                "type": "system",
                "content": "REPLACE_CONTENT: segments[0], filter='dynamic|activity'",
                "parsed_command": {
                    "intent": "REPLACE_CONTENT",
                    "parameters": {
                        "segment_index": 0,
                        "content_filter": ["dynamic", "activity"]
                    }
                }
            }
        ]
    },
    
    "status": {
        "phase": "refinement_ready",
        "progress": 70.0,
        "current_version": 1,
        "error": None
    }
}

# Example 6: Final ProjectState after second composition
final_state = {
    **after_refinement_state,
    "updated_at": "2025-08-02T10:18:00Z",
    
    "timeline": {
        "segments": [
            {
                "media_asset_id": "media_003",  # Different, more dynamic shot
                "start_time": 0.0,
                "end_time": 3.5,
                "duration": 3.5,
                "in_point": 0.0,
                "out_point": 3.5,
                "transition": "fade_in"
            },
            # ... rest of refined timeline
        ],
        "total_duration": 120.0,
        "render_settings": after_composition_state["timeline"]["render_settings"]
    },
    
    "history": {
        **after_refinement_state["history"],
        "versions": [
            *after_refinement_state["history"]["versions"],
            {
                "version": 2,
                "timestamp": "2025-08-02T10:18:00Z",
                "output_path": "/data/projects/proj_12345/output_v2.mp4",
                "agent": "composition_agent",
                "changes": "Replaced opening segment with more dynamic content"
            }
        ]
    },
    
    "status": {
        "phase": "complete",
        "progress": 100.0,
        "current_version": 2,
        "error": None
    }
}

def print_state_summary(state: Dict[str, Any], title: str):
    """Helper function to print a summary of the project state"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Phase: {state['status']['phase']}")
    print(f"Progress: {state['status']['progress']}%")
    print(f"Current Version: {state['status']['current_version']}")
    print(f"Media Count: {len(state['user_inputs']['media'])}")
    print(f"Timeline Segments: {len(state['timeline']['segments'])}")
    print(f"Feedback Count: {len(state['history']['feedback'])}")
    
    if state['analysis']['media_pool']:
        print("\nAnalyzed Media:")
        for media in state['analysis']['media_pool'][:2]:  # Show first 2
            if 'gemini_analysis' in media:
                print(f"  - {media['id']}: {media['gemini_analysis']['description'][:50]}...")
                print(f"    Score: {media['gemini_analysis']['aesthetic_score']}")

if __name__ == "__main__":
    # Demonstrate the flow
    print("ProjectState Flow Through Memory Movie Maker Agents")
    
    print_state_summary(initial_state, "1. Initial State (User Input)")
    print_state_summary(after_analysis_state, "2. After Analysis Agent")
    print_state_summary(after_composition_state, "3. After Composition Agent")
    print_state_summary(after_evaluation_state, "4. After Evaluation Agent")
    print_state_summary(after_refinement_state, "5. After Refinement Agent")
    print_state_summary(final_state, "6. Final State (Complete)")
    
    # Show how to access specific data
    print("\n" + "="*60)
    print("Accessing Specific Data Examples:")
    print("="*60)
    
    # Get all required media
    required_media = [m for m in final_state['user_inputs']['media'] if m.get('required')]
    print(f"\nRequired Media: {[m['id'] for m in required_media]}")
    
    # Get music tempo
    if final_state['analysis']['music_profiles']:
        tempo = final_state['analysis']['music_profiles'][0]['tempo_bpm']
        print(f"Music Tempo: {tempo} BPM")
    
    # Get highest scoring media
    if final_state['analysis']['media_pool']:
        best_media = max(
            final_state['analysis']['media_pool'],
            key=lambda m: m.get('gemini_analysis', {}).get('aesthetic_score', 0)
        )
        print(f"Highest Scoring Media: {best_media['id']} "
              f"(score: {best_media['gemini_analysis']['aesthetic_score']})")