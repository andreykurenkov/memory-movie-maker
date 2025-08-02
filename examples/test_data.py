"""
Sample Test Data for Memory Movie Maker

This file provides sample data structures that can be used for testing
and development without requiring actual media files.
"""

from datetime import datetime, timedelta
import random

# Sample media metadata (without actual files)
SAMPLE_PHOTOS = [
    {
        "id": "photo_beach_01",
        "file_path": "/test/photos/beach_sunrise.jpg",
        "type": "image",
        "metadata": {
            "capture_time": "2025-07-15T06:30:00Z",
            "location": "Waikiki Beach, Hawaii",
            "camera": "iPhone 15 Pro",
            "resolution": "4032x3024"
        },
        "expected_analysis": {
            "description": "Stunning sunrise over Waikiki Beach with Diamond Head in background",
            "aesthetic_score": 0.92,
            "main_subjects": ["beach", "sunrise", "ocean", "mountain"],
            "tags": ["golden hour", "scenic", "tropical", "peaceful"],
            "suggested_use": "opening"
        }
    },
    {
        "id": "photo_family_01",
        "file_path": "/test/photos/family_beach_fun.jpg",
        "type": "image",
        "metadata": {
            "capture_time": "2025-07-15T10:15:00Z",
            "location": "Lanikai Beach, Hawaii",
            "faces_detected": 4
        },
        "expected_analysis": {
            "description": "Happy family playing in the sand at a tropical beach",
            "aesthetic_score": 0.85,
            "main_subjects": ["people", "family", "beach", "activity"],
            "tags": ["fun", "candid", "joyful", "vacation"],
            "suggested_use": "highlight"
        }
    },
    {
        "id": "photo_sunset_01",
        "file_path": "/test/photos/sunset_palms.jpg",
        "type": "image",
        "metadata": {
            "capture_time": "2025-07-15T18:45:00Z",
            "location": "Sunset Beach, Hawaii"
        },
        "expected_analysis": {
            "description": "Dramatic sunset with silhouetted palm trees",
            "aesthetic_score": 0.94,
            "main_subjects": ["sunset", "palm trees", "sky", "silhouette"],
            "tags": ["dramatic", "romantic", "tropical", "golden"],
            "suggested_use": "closing"
        }
    }
]

SAMPLE_VIDEOS = [
    {
        "id": "video_surf_01",
        "file_path": "/test/videos/surfing_action.mp4",
        "type": "video",
        "metadata": {
            "capture_time": "2025-07-15T14:30:00Z",
            "duration": 45.5,
            "fps": 60,
            "resolution": "1920x1080"
        },
        "expected_analysis": {
            "description": "Dynamic surfing footage with multiple riders catching waves",
            "aesthetic_score": 0.88,
            "main_subjects": ["surfing", "ocean", "waves", "action"],
            "tags": ["dynamic", "sports", "exciting", "blue"],
            "best_moment_timestamp": 23.5,
            "motion_level": "fast",
            "suggested_use": "highlight"
        }
    },
    {
        "id": "video_timelapse_01",
        "file_path": "/test/videos/sunset_timelapse.mp4",
        "type": "video",
        "metadata": {
            "capture_time": "2025-07-15T18:00:00Z",
            "duration": 30.0,
            "fps": 30,
            "resolution": "3840x2160"
        },
        "expected_analysis": {
            "description": "Breathtaking timelapse of sunset over ocean with cloud movement",
            "aesthetic_score": 0.96,
            "main_subjects": ["sunset", "clouds", "ocean", "sky"],
            "tags": ["timelapse", "cinematic", "colorful", "dramatic"],
            "best_moment_timestamp": 18.0,
            "motion_level": "medium",
            "suggested_use": "closing"
        }
    }
]

SAMPLE_MUSIC = [
    {
        "id": "music_upbeat_01",
        "file_path": "/test/music/tropical_upbeat.mp3",
        "type": "audio",
        "metadata": {
            "title": "Tropical Vacation",
            "artist": "Sample Artist",
            "duration": 180.0
        },
        "expected_analysis": {
            "tempo_bpm": 128.0,
            "key": "C major",
            "energy_profile": "high",
            "mood": {
                "happiness": 0.9,
                "energy": 0.85,
                "danceability": 0.8
            },
            "structure": [
                {"section": "intro", "start": 0, "end": 8},
                {"section": "verse", "start": 8, "end": 32},
                {"section": "chorus", "start": 32, "end": 48},
                {"section": "verse", "start": 48, "end": 72},
                {"section": "chorus", "start": 72, "end": 88},
                {"section": "bridge", "start": 88, "end": 104},
                {"section": "chorus", "start": 104, "end": 120},
                {"section": "outro", "start": 120, "end": 180}
            ]
        }
    }
]

def generate_sample_project_state(
    num_photos: int = 20,
    num_videos: int = 5,
    include_music: bool = True,
    project_id: str = None
) -> dict:
    """Generate a complete sample ProjectState for testing"""
    
    if project_id is None:
        project_id = f"test_proj_{random.randint(1000, 9999)}"
    
    # Select random samples
    photos = random.choices(SAMPLE_PHOTOS, k=min(num_photos, len(SAMPLE_PHOTOS)))
    videos = random.choices(SAMPLE_VIDEOS, k=min(num_videos, len(SAMPLE_VIDEOS)))
    
    # Extend with variations
    all_media = []
    for i, photo in enumerate(photos):
        photo_copy = photo.copy()
        photo_copy["id"] = f"{photo['id']}_{i}"
        photo_copy["upload_timestamp"] = datetime.utcnow().isoformat()
        all_media.append(photo_copy)
    
    for i, video in enumerate(videos):
        video_copy = video.copy()
        video_copy["id"] = f"{video['id']}_{i}"
        video_copy["upload_timestamp"] = datetime.utcnow().isoformat()
        all_media.append(video_copy)
    
    # Create project state
    state = {
        "project_id": project_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        
        "user_inputs": {
            "media": all_media,
            "music": SAMPLE_MUSIC[:1] if include_music else [],
            "initial_prompt": "Create a 2-minute upbeat video of our Hawaii vacation",
            "target_duration": 120,
            "aspect_ratio": "16:9",
            "style_preferences": {
                "vibe": "upbeat",
                "theme": "vacation",
                "transitions": "smooth"
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
            "prompts": [{
                "timestamp": datetime.utcnow().isoformat(),
                "type": "user",
                "content": "Create a 2-minute upbeat video of our Hawaii vacation"
            }],
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
    
    return state

def generate_analyzed_media(media_item: dict) -> dict:
    """Add simulated analysis results to a media item"""
    
    analyzed = media_item.copy()
    if "expected_analysis" in media_item:
        analyzed["gemini_analysis"] = media_item["expected_analysis"].copy()
        # Add some variation
        score = analyzed["gemini_analysis"]["aesthetic_score"]
        analyzed["gemini_analysis"]["aesthetic_score"] = max(0, min(1, 
            score + random.uniform(-0.05, 0.05)
        ))
    
    return analyzed

def generate_sample_timeline(
    media_pool: list,
    target_duration: float = 120.0,
    beats_per_minute: float = 128.0
) -> list:
    """Generate a sample timeline with rhythmic cuts"""
    
    beat_duration = 60.0 / beats_per_minute
    measure_duration = beat_duration * 4  # 4/4 time
    
    timeline = []
    current_time = 0.0
    media_index = 0
    
    while current_time < target_duration and media_index < len(media_pool):
        media = media_pool[media_index]
        
        # Vary clip duration based on content
        if media["type"] == "image":
            duration = measure_duration * random.choice([1, 2])  # 1-2 measures
        else:
            # For videos, use a portion
            available_duration = media["metadata"].get("duration", 30.0)
            duration = min(measure_duration * random.choice([2, 4]), available_duration)
        
        segment = {
            "media_asset_id": media["id"],
            "start_time": current_time,
            "end_time": current_time + duration,
            "duration": duration,
            "in_point": 0.0 if media["type"] == "image" else random.uniform(0, 5),
            "out_point": None if media["type"] == "image" else duration,
            "transition": random.choice(["cut", "fade", "crossfade"])
        }
        
        timeline.append(segment)
        current_time += duration
        media_index += 1
    
    return timeline

# Sample user feedback examples
SAMPLE_FEEDBACK = [
    {
        "text": "Make the beginning more exciting",
        "expected_commands": [{
            "intent": "REPLACE_CONTENT",
            "parameters": {
                "segment_indices": [0, 1],
                "content_filter": ["dynamic", "action", "exciting"]
            }
        }]
    },
    {
        "text": "It's too fast, make it more relaxing",
        "expected_commands": [{
            "intent": "ADJUST_PACING",
            "parameters": {
                "time_range": [0, 120],
                "speed_factor": 0.8
            }
        }]
    },
    {
        "text": "Add more sunset shots and remove the surfing",
        "expected_commands": [
            {
                "intent": "ADD_CONTENT",
                "parameters": {
                    "content_filter": ["sunset"],
                    "duration": 5.0
                }
            },
            {
                "intent": "REMOVE_CONTENT",
                "parameters": {
                    "content_filter": ["surfing"]
                }
            }
        ]
    }
]

if __name__ == "__main__":
    # Example usage
    print("Memory Movie Maker - Sample Test Data")
    print("=" * 60)
    
    # Generate a sample project
    project = generate_sample_project_state(num_photos=10, num_videos=3)
    print(f"\nGenerated project: {project['project_id']}")
    print(f"Media items: {len(project['user_inputs']['media'])}")
    print(f"Target duration: {project['user_inputs']['target_duration']}s")
    
    # Simulate analysis
    analyzed_media = [
        generate_analyzed_media(m) 
        for m in project['user_inputs']['media']
    ]
    
    # Generate timeline
    timeline = generate_sample_timeline(analyzed_media, project['user_inputs']['target_duration'])
    print(f"\nGenerated timeline with {len(timeline)} segments")
    print(f"Total duration: {timeline[-1]['end_time']:.1f}s")
    
    # Show sample feedback
    print("\nSample user feedback:")
    for feedback in SAMPLE_FEEDBACK[:2]:
        print(f"  '{feedback['text']}'")
        print(f"  -> {feedback['expected_commands'][0]['intent']}")