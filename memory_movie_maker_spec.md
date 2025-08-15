# Memory Movie Maker: Complete Technical Specification

## Overview

Memory Movie Maker is an intelligent, conversational video editing tool that transforms raw photos and videos into polished "memory movies" using Google's Agent Development Kit (ADK) and advanced AI capabilities. The system uses a multi-agent architecture where AI agents collaborate to analyze media, plan edits, and render videos autonomously.

**Key Innovation**: The system uses **Gemini AI for intelligent edit planning** - instead of traditional algorithmic video editing, an LLM analyzes the media content and creates sophisticated edit plans with story structure, emotional pacing, and music synchronization.

## Architecture Overview

### Multi-Agent System (MAS)

The system comprises five specialized agents orchestrated by Google's ADK:

1. **RootAgent**: Orchestrates the entire workflow and manages project state
2. **AnalysisAgent**: Analyzes media files using Gemini for visual content and Librosa for audio features
3. **CompositionAgent**: Uses AI-powered edit planning to create video timelines and render output
4. **EvaluationAgent**: Critiques generated videos for quality and adherence to user intent
5. **RefinementAgent**: Translates natural language feedback into structured editing commands

### Self-Correction Loop

The system autonomously generates, evaluates, and refines videos 2-3 times before presenting to users:
1. Initial AI creation based on user prompt
2. AI evaluation and feedback generation
3. AI refinement based on feedback
4. Final video presentation to user

## Core Components

### 1. Analysis System

#### Visual Analysis (Gemini)
- **Images**: Analyzes aesthetic quality, subjects, tags, and visual composition
- **Videos**: Provides unified visual + audio analysis including:
  - Notable segments with both visual and audio descriptions
  - Speech transcription and speaker identification
  - Music/sound effect detection and timing
  - Audio-visual synchronization recommendations
  - Emotional tone tracking across segments

#### Audio Analysis (Librosa)
- **Beat Detection**: Precise beat timestamps using onset detection
- **Tempo Extraction**: BPM calculation for rhythm synchronization
- **Energy Curves**: Frame-by-frame RMS energy for dynamic pacing
- **Musical Structure**: Analysis of energy transitions and musical sections

#### Semantic Audio Analysis (Gemini)
- **Speech Recognition**: Transcription and speaker identification
- **Musical Segmentation**: Detection of intro/verse/chorus/bridge/outro
- **Emotional Analysis**: Mood and energy transition detection
- **Sync Priority**: Identification of critical audio-visual sync points

### 2. AI-Powered Edit Planning

**Core Innovation**: Instead of algorithmic video editing, the system uses **Gemini LLM to create intelligent edit plans**.

#### Edit Planner Process
1. **Content Analysis**: Aggregates all media analysis (visual, audio, semantic)
2. **Musical Structure**: Maps music segments (intro/verse/chorus) to video pacing
3. **LLM Planning**: Gemini creates detailed edit plan with:
   - Segment selection based on content quality and relevance
   - Story structure (introduction → development → climax → resolution)
   - Pacing matched to musical energy and emotional flow
   - Transition recommendations and sync points

#### Edit Plan Structure
```python
class EditPlan:
    segments: List[PlannedSegment]  # Ordered sequence of video segments
    total_duration: float           # Calculated total duration
    narrative_arc: str             # AI's story description
    variety_score: float           # Content diversity measure
    story_coherence: float         # Narrative consistency score
```

#### PlannedSegment Details
```python
class PlannedSegment:
    media_id: str                  # Source media asset
    start_time: float              # Timeline position
    duration: float                # Segment duration
    trim_start/trim_end: float     # Source media trimming
    transition_type: str           # Crossfade, cut, etc.
    reasoning: str                 # AI explanation for selection
    story_beat: str               # Narrative purpose
    energy_match: float           # Music synchronization score
```

### 3. Video Rendering Pipeline

#### Timeline Creation
- Converts AI edit plans into executable video timelines
- Handles media asset resolution and path management
- Applies transitions and effects as specified

#### Rendering (MoviePy + FFmpeg)
- **Video Composition**: Concatenates clips with transitions
- **Audio Integration**: Syncs background music with video content
- **Resolution Handling**: Scales content to target resolution (default 1920x1080)
- **Format Output**: Generates H.264/AAC MP4 files

### 4. Storage & Project Management

#### Supabase Backend Integration

The system uses **Supabase** as the backend for user authentication and project persistence.

**Database Schema (PostgreSQL)**
```sql
-- Users and Authentication (handled by Supabase Auth)
CREATE TABLE profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID REFERENCES profiles(id) NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT,
  target_duration INTEGER, -- seconds
  aspect_ratio VARCHAR(10) DEFAULT '16:9',
  style_preferences JSONB,
  status VARCHAR(20) DEFAULT 'draft', -- draft, processing, completed, error
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Media Assets
CREATE TABLE media_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL, -- Supabase Storage path
  file_name VARCHAR(255) NOT NULL,
  file_size BIGINT NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  media_type VARCHAR(10) NOT NULL, -- image, video, audio
  duration FLOAT, -- for video/audio files
  metadata JSONB, -- file metadata
  analysis_data JSONB, -- AI analysis results
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Project Versions (for edit history and iterations)
CREATE TABLE project_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  version_number INTEGER NOT NULL,
  timeline_data JSONB NOT NULL, -- complete timeline state
  edit_plan JSONB, -- AI-generated edit plan
  render_settings JSONB,
  output_file_path TEXT, -- rendered video path
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processing Jobs (for background AI processing)
CREATE TABLE processing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  job_type VARCHAR(50) NOT NULL, -- analysis, rendering, refinement
  status VARCHAR(20) DEFAULT 'queued', -- queued, processing, completed, failed
  progress FLOAT DEFAULT 0, -- 0-100
  result_data JSONB,
  error_message TEXT,
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Supabase Storage Configuration**
```typescript
// Supabase storage buckets
const storageBuckets = {
  'user-media': {
    public: false,
    allowedMimeTypes: ['image/*', 'video/*', 'audio/*'],
    fileSizeLimit: 500_000_000, // 500MB
    allowedTransformations: ['resize', 'thumbnail']
  },
  'rendered-videos': {
    public: true, // For easy sharing
    allowedMimeTypes: ['video/mp4'],
    fileSizeLimit: 1_000_000_000, // 1GB
  },
  'project-thumbnails': {
    public: true,
    allowedMimeTypes: ['image/jpeg', 'image/png'],
    fileSizeLimit: 10_000_000, // 10MB
  }
};
```

**Row Level Security (RLS) Policies**
```sql
-- Users can only access their own projects
CREATE POLICY "Users can view their own projects" ON projects
  FOR SELECT USING (owner_id = auth.uid());

CREATE POLICY "Users can update their own projects" ON projects
  FOR UPDATE USING (owner_id = auth.uid());

-- Users can only upload media to their own projects
CREATE POLICY "Users can manage their own media" ON media_assets
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM projects 
      WHERE id = project_id AND owner_id = auth.uid()
    )
  );

-- Users can only access their own project versions
CREATE POLICY "Users can access their own project versions" ON project_versions
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM projects 
      WHERE id = project_id AND owner_id = auth.uid()
    )
  );
```

#### Project State Model
```python
class ProjectState:
    project_id: str                    # Unique project identifier
    user_inputs: UserInputs           # Original media and preferences
    analysis: AnalysisResults         # All AI analysis data
    timeline: Timeline                # Current video timeline
    status: ProjectStatus             # Current processing phase
    output_path: str                  # Final video location
    version_history: List[Version]    # Edit iterations and refinements
```

## Technical Implementation Details

### Dependencies & Technologies

#### Core Framework
- **Google ADK**: Multi-agent orchestration and LLM integration
- **Google Gemini API**: Visual analysis, edit planning, and critique generation
- **New Google GenAI SDK** (v1.28.0): Modern API client with better performance

#### Media Processing
- **Librosa**: Audio analysis and music structure detection
- **MoviePy**: Video composition and rendering
- **FFmpeg**: Underlying video processing engine
- **OpenCV**: Video metadata extraction

#### Data & Storage
- **Pydantic**: Data validation and serialization
- **Supabase**: Backend-as-a-Service with PostgreSQL and real-time features
- **Asyncio**: Concurrent processing of analysis tasks

### Audio Analysis Architecture

The system uses **three complementary approaches**:

1. **Technical Analysis (Librosa)**
   - Beat detection and tempo extraction
   - Energy curves for dynamic video cuts
   - Musical characteristics (danceability, valence)
   - Perfect for rhythm-synced editing

2. **Semantic Audio Analysis (Gemini)**
   - Speech transcription and speaker identification
   - Emotional tone and topic extraction
   - Audio segmentation (speech, music, effects)
   - Content-aware video composition

3. **Integrated Video-Audio Analysis (Gemini)**
   - Unified segmentation of videos with both visual and audio content
   - Speech transcription within video context
   - Sound effect detection and importance scoring
   - Audio-visual synchronization recommendations
   - Emotional tone tracking across segments

### API Integration

#### Gemini API Usage
- **Model**: gemini-2.5-flash (latest high-performance model)
- **Authentication**: Direct API key or Vertex AI credentials
- **File Upload**: Large media files uploaded to Gemini storage
- **Structured Output**: JSON-formatted responses for consistent parsing

#### Configuration
```python
# Environment Variables
GEMINI_API_KEY=your_api_key_here
```

## Data Models

### Media Asset
```python
class MediaAsset:
    id: str                           # Unique identifier
    file_path: str                    # Storage location
    type: MediaType                   # IMAGE, VIDEO, AUDIO
    metadata: Dict[str, Any]          # File metadata (duration, etc.)
    gemini_analysis: GeminiAnalysis   # AI visual/audio analysis
    audio_analysis: AudioAnalysisProfile  # Technical audio data
    semantic_audio_analysis: Dict     # Speech/music structure
```

### Video Segment Analysis
```python
class VideoSegment:
    start_time: float                 # Segment start time
    end_time: float                   # Segment end time
    description: str                  # Complete segment description
    visual_content: str               # Visual elements
    audio_content: str                # Audio elements
    audio_type: str                   # speech/music/sfx/ambient/mixed
    speaker: str                      # Speaker ID (if speech)
    speech_content: str               # Transcribed speech
    music_description: str            # Music genre/mood/tempo
    emotional_tone: str               # happy/sad/exciting/calm/tense
    sync_priority: float              # Audio-visual sync importance
    recommended_action: str           # Editing recommendation
```

## User Interface

### Web Application Frontend

The system features a clean, responsive web application focused on the core goal: creating memory movies with AI.

#### Main Interface Components

**Project Dashboard**
- **Project Gallery**: Grid view of user's projects with thumbnails
- **Recent Projects**: Quick access to recently edited videos
- **Create New Project**: Simple button to start new project

**Project Creation Workflow**
1. **Media Upload**: Drag-and-drop interface for photos, videos, and music
   - Progress indicators for file uploads
   - File validation and format support
   - Automatic thumbnail generation

2. **Project Configuration**
   - **Prompt Input**: Text area for describing desired video
   - **Style Selection**: Simple dropdown (energetic, nostalgic, cinematic, etc.)
   - **Duration Settings**: Slider for target video length (30s - 5min)
   - **Aspect Ratio**: Selection for different platforms (16:9, 9:16, 1:1)

3. **AI Generation Interface**
   - **Progress Updates**: Status during analysis and rendering
   - **Preview**: Preview of generated video sections
   - **Processing Status**: Current AI agent activity

**Video Editor Interface**
- **Preview Player**: Video player with basic controls
- **Media Library**: List view of project assets
- **Version History**: Access to previous iterations

**Refinement Interface**
- **Natural Language Input**: Simple text input for editing requests
- **Quick Actions**: Buttons for common adjustments ("Make it faster", "More photos", etc.)
- **Iteration History**: Previous versions with ability to restore

#### Technology Stack

**Frontend Framework**
- **React 18**: Modern component-based UI with hooks and concurrent features
- **Next.js 14**: Full-stack framework with App Router and server components
- **TypeScript**: Type-safe development for better maintainability
- **Tailwind CSS**: Utility-first styling for consistent design

**UI Components**
- **Shadcn/ui**: High-quality, accessible component library
- **Radix UI**: Primitive components for complex interactions
- **Framer Motion**: Smooth animations and transitions
- **React Player**: Video playback with custom controls

**State Management**
- **Zustand**: Lightweight state management for client state
- **TanStack Query**: Server state management with caching
- **Supabase Client**: Direct database and auth integration

#### Command Line Interface (Development)
```bash
# Basic usage
python scripts/create_memory_movie.py photo1.jpg photo2.jpg video1.mp4 \
  -p "Create a 60-second upbeat vacation video" \
  -m background_music.mp3 \
  -d 60

# With options
python scripts/create_memory_movie.py *.jpg *.mp4 \
  --prompt "A nostalgic family gathering video" \
  --music wedding_song.mp3 \
  --duration 120 \
  --no-refine \
  --style sentimental
```

## API Architecture

### Backend API Design

#### FastAPI Application Structure
```python
# Main application
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Memory Movie Maker API")

# API Routes
@app.post("/api/projects")
async def create_project(project_data: ProjectCreate, user: User = Depends(get_current_user)):
    """Create a new video project"""

@app.post("/api/projects/{project_id}/media")
async def upload_media(project_id: str, files: List[UploadFile]):
    """Upload media files to project"""

@app.post("/api/projects/{project_id}/generate")
async def generate_video(project_id: str, generation_request: GenerationRequest):
    """Start AI video generation process"""

@app.post("/api/projects/{project_id}/refine")
async def refine_video(project_id: str, refinement_request: RefinementRequest):
    """Refine video based on user feedback"""

@app.get("/api/projects/{project_id}/status")
async def get_project_status(project_id: str):
    """Get current project processing status"""
```

#### Background Task Processing
```python
# Celery tasks for async processing
from celery import Celery

celery_app = Celery('memory_movie_maker')

@celery_app.task
def analyze_media_task(media_id: str):
    """Analyze uploaded media with AI"""
    
@celery_app.task
def generate_video_task(project_id: str, generation_params: dict):
    """Generate video using AI agents"""
    
@celery_app.task
def render_video_task(project_id: str, timeline_data: dict):
    """Render final video file"""
```

### Progress Tracking

#### Polling-based Status Updates
```typescript
// Frontend status polling
class ProjectStatusTracker {
  constructor(projectId: string) {
    this.projectId = projectId;
  }
  
  async pollStatus(): Promise<ProjectStatus> {
    const response = await fetch(`/api/projects/${this.projectId}/status`);
    return await response.json();
  }
  
  startPolling(callback: (status: ProjectStatus) => void) {
    const interval = setInterval(async () => {
      const status = await this.pollStatus();
      callback(status);
      
      if (status.phase === 'completed' || status.phase === 'error') {
        clearInterval(interval);
      }
    }, 2000); // Poll every 2 seconds
  }
}
```

## Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- FFmpeg installed and in PATH
- Gemini API key or Google Cloud credentials
- Supabase project setup
- 8GB+ RAM (for video processing)
- 10GB+ free disk space

### Installation

#### Backend Setup
```bash
# Clone repository
git clone <repository-url>
cd memory-movie-maker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your API keys and Supabase configuration

# Verify installation
python scripts/test_end_to_end.py
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit with Supabase URL and keys

# Start development server
npm run dev
```

#### Supabase Setup
```bash
# Install Supabase CLI
npm install -g supabase

# Initialize project
supabase init

# Start local development
supabase start

# Apply database migrations
supabase db push

# Set up storage buckets
supabase storage create user-media --public false
supabase storage create rendered-videos --public true
supabase storage create project-thumbnails --public true
```

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests

# Test with coverage
pytest --cov=src

# Test specific components
python scripts/test_video_audio_analysis.py data/sample_video.mp4

# Frontend tests
cd frontend && npm test
```

## API Reference

### Core Functions

#### Create Memory Movie
```python
from memory_movie_maker.agents.root_agent import RootAgent

agent = RootAgent()
result = await agent.create_memory_movie(
    media_paths=["photo1.jpg", "video1.mp4"],
    music_path="song.mp3",
    target_duration=60,
    user_prompt="Create an upbeat vacation video",
    style_preferences={"style": "energetic"},
    auto_refine=True
)
```

#### Refine Existing Video
```python
result = await agent.refine_memory_movie(
    project_state=existing_project,
    feedback="Make the beginning slower and add more nature shots"
)
```

### REST API Endpoints

#### Project Management
```typescript
// Create new project
POST /api/projects
{
  "title": "My Vacation Video",
  "description": "Summer trip to Hawaii",
  "target_duration": 60,
  "aspect_ratio": "16:9",
  "style_preferences": {"style": "energetic"}
}

// Upload media files
POST /api/projects/{project_id}/media
FormData: files[]

// Start video generation
POST /api/projects/{project_id}/generate
{
  "prompt": "Create an upbeat vacation video",
  "auto_refine": true
}

// Refine video
POST /api/projects/{project_id}/refine
{
  "feedback": "Make it more cinematic with slower pacing"
}
```

### Tool Usage

#### Visual Analysis
```python
from memory_movie_maker.tools.visual_analysis import analyze_visual_media

result = await analyze_visual_media("image.jpg")
# Returns: {"status": "success", "analysis": {...}, "duration": float}
```

#### Audio Analysis
```python
from memory_movie_maker.tools.audio_analysis import analyze_audio_media

result = await analyze_audio_media("music.mp3")
# Returns: {"status": "success", "analysis": AudioAnalysisProfile}
```

#### Edit Planning
```python
from memory_movie_maker.tools.edit_planner import plan_edit

edit_plan = await plan_edit(
    media_assets=analyzed_media,
    music_profile=music_analysis,
    target_duration=60,
    user_prompt="Create an upbeat video",
    style_preferences={"style": "energetic"}
)
```

## Performance Considerations

### Processing Times
- **Media Upload**: 5-30 seconds depending on file size and internet speed
- **Analysis Phase**: 30-60 seconds for 10 media files
- **Edit Planning**: 10-20 seconds (Gemini API call)
- **Video Rendering**: 1-3 minutes for 60-second output
- **Total Time**: 2-5 minutes for complete workflow

### Memory Usage
- **Analysis**: ~2GB RAM for concurrent processing
- **Rendering**: ~4GB RAM for HD video composition
- **Storage**: ~50MB per project (excluding source media)
- **Database**: ~1MB per project for metadata

### Optimization Strategies
- **Concurrent Analysis**: Process multiple media files simultaneously
- **Result Caching**: Cache analysis results to avoid reprocessing
- **Streaming Rendering**: Process video in chunks for large projects
- **Background Processing**: Queue long-running tasks
- **CDN Delivery**: Serve rendered videos from global CDN

## Error Handling & Logging

### Logging System
- **Structured Logging**: JSON-formatted logs with timestamps
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Component Tracking**: Agent and tool-specific log contexts
- **User Feedback**: Progress updates during long operations
- **Real-time Monitoring**: Live log streaming via WebSocket

### Common Error Scenarios
- **API Rate Limits**: Exponential backoff and retry logic
- **Media Format Issues**: Validation and conversion recommendations
- **Memory Constraints**: Graceful degradation and chunk processing
- **Network Failures**: Resilient API calling with fallbacks
- **Storage Limits**: Automatic cleanup and quota management

## Deployment Considerations

### Architecture Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js App  │    │   Python API   │    │   Supabase      │
│   (Frontend)    │◄──►│   (AI Agents)   │◄──►│   (Database)    │
│   - React UI    │    │   - Video AI    │    │   - PostgreSQL  │
│   - Real-time   │    │   - Processing  │    │   - Storage     │
│   - Auth        │    │   - Rendering   │    │   - Auth        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Background    │
                    │   Workers       │
                    │   - Video Proc  │
                    │   - AI Analysis │
                    │   - Rendering   │
                    └─────────────────┘
```

#### Deployment Stack

**Frontend Hosting (Vercel)**
- **Next.js Application**: Deployed on Vercel for optimal performance
- **Edge Functions**: Server-side rendering and API routes
- **CDN**: Global content delivery for static assets
- **Custom Domain**: Professional branding with SSL

**Backend API (Railway/Render)**
- **Python FastAPI**: RESTful API for AI processing
- **Containerization**: Docker containers for consistent deployment
- **Auto-scaling**: Horizontal scaling based on demand
- **Health Monitoring**: Uptime and performance monitoring

**Database & Storage (Supabase)**
- **Managed PostgreSQL**: Fully managed database with backups
- **Object Storage**: Large file storage for media assets
- **Real-time Engine**: WebSocket connections for collaboration
- **Edge Functions**: Serverless functions for data processing

**Background Processing (Celery + Redis)**
- **Task Queue**: Asynchronous video processing jobs
- **Redis Cache**: Session storage and temporary data
- **Worker Scaling**: Auto-scale based on queue depth
- **Job Monitoring**: Track processing status and failures

**Media Processing Infrastructure**
- **FFmpeg Servers**: Dedicated instances for video rendering
- **GPU Acceleration**: NVIDIA instances for AI analysis
- **Content Delivery**: CloudFront/CloudFlare for video delivery
- **Storage Optimization**: Automatic compression and format conversion

#### Scalability Considerations
- **Stateless Agents**: AI agents designed for horizontal scaling
- **Database Sharding**: Partition data across multiple databases
- **Caching Strategy**: Multi-level caching (Redis, CDN, browser)
- **Load Balancing**: Distribute traffic across multiple instances

### Security
- **API Keys**: Environment-based credential management
- **File Validation**: Input sanitization and type checking
- **Rate Limiting**: Request throttling and quota management
- **Data Privacy**: Local processing option for sensitive content
- **Row Level Security**: Database-level access controls
- **JWT Authentication**: Secure user session management

## Future Enhancements

### Phase 1: Core Improvements (Q1)
- **Mobile Optimization**: Progressive Web App (PWA) for mobile editing
- **Batch Processing**: Upload and process multiple projects simultaneously
- **Advanced Templates**: Industry-specific templates (wedding, travel, business)
- **Export Variations**: Multiple aspect ratios and quality settings per project

### Phase 2: Collaboration Features (Q2)
- **Team Workspaces**: Organization-level project management
- **Review Workflows**: Approval processes for team projects
- **Asset Libraries**: Shared media libraries across projects
- **Brand Guidelines**: Consistent styling and branding enforcement

### Phase 3: Advanced AI (Q3)
- **Style Transfer**: Apply cinematic styles to any video content
- **Face Recognition**: Automatic subject identification and personalization
- **Voice Cloning**: AI-generated narration in user's voice
- **Scene Understanding**: Context-aware transitions and effects

### Phase 4: Enterprise Features (Q4)
- **API Access**: Full programmatic control for enterprise integrations
- **Custom Models**: Train AI on organization-specific content
- **Advanced Analytics**: Detailed insights on video performance
- **White-label Solutions**: Branded versions for enterprise clients

### Technical Roadmap

#### Performance Optimization
- **Edge Computing**: Deploy AI models closer to users globally
- **GPU Acceleration**: Utilize cloud GPUs for faster processing
- **Streaming Processing**: Real-time analysis during upload
- **Predictive Caching**: Pre-generate common video variations

#### AI Model Improvements
- **Multi-modal Understanding**: Better audio-visual correlation
- **Temporal Consistency**: Smoother transitions and pacing
- **User Preference Learning**: Personalized editing styles
- **Content-aware Effects**: Intelligent application of filters and effects

## Development Roadmap: From AI Engine to Full Web Application

### Current Status: Core AI Engine Complete ✅

The multi-agent AI system is fully implemented and functional:
- **AnalysisAgent**: Media content understanding with Gemini + Librosa
- **CompositionAgent**: AI-powered edit planning and video rendering  
- **EvaluationAgent**: Quality assessment and improvement suggestions
- **RefinementAgent**: Natural language feedback interpretation
- **RootAgent**: Workflow orchestration and state management

**Validation**: Run `python scripts/test_end_to_end.py` to verify complete AI workflow.

### Phase 1: Web API Development (4-6 weeks)

#### 1.1 FastAPI Backend Setup
**Status**: Not Started | **Priority**: High

```bash
# Implementation tasks:
mkdir backend
cd backend

# Core API structure
- fastapi_app/
  ├── main.py              # FastAPI application
  ├── api/
  │   ├── routes/          # API endpoints
  │   ├── models/          # Request/response models
  │   └── middleware/      # CORS, auth, logging
  ├── services/
  │   ├── agent_service.py # AI agent integration
  │   ├── file_service.py  # Media upload handling
  │   └── project_service.py # Project management
  └── dependencies.py      # Dependency injection
```

**Key Implementation Steps**:
1. **Project API endpoints**: Create, list, update, delete projects
2. **Media upload handling**: Multipart file upload with validation
3. **AI processing endpoints**: Trigger agent workflows via background tasks
4. **Status polling**: Progress tracking endpoints
5. **Error handling**: Comprehensive error responses and logging

**Deliverables**:
- RESTful API with OpenAPI documentation
- Background task processing with Redis
- File upload and storage integration
- Authentication middleware for Supabase integration

#### 1.2 Supabase Integration
**Status**: Not Started | **Priority**: High

**Database Schema Implementation**:
```sql
-- Execute these migrations in Supabase
-- 1. Core tables (projects, media_assets, project_versions)
-- 2. Collaboration tables (project_collaborators, comments)
-- 3. Processing tables (processing_jobs)
-- 4. RLS policies for data security
```

**Storage Configuration**:
```bash
# Option 1: Supabase Storage
supabase storage create user-media --public false
supabase storage create rendered-videos --public true
supabase storage create project-thumbnails --public true

# Option 2: AWS S3 Setup
aws s3 mb s3://memory-movies-user-media
aws s3 mb s3://memory-movies-rendered-videos  
aws s3 mb s3://memory-movies-thumbnails
# Configure CORS and bucket policies as needed
```

**Python Integration**:
```python
# Backend services integration (flexible storage)
- database_client.py     # Database operations (Supabase or PostgreSQL)
- storage_service.py     # File storage (Supabase Storage or S3)
- auth_service.py        # User authentication  
- config_service.py      # Environment-based configuration
```

**Deliverables**:
- Complete database schema with migrations
- File storage integration (Supabase Storage or S3)
- User authentication system
- Row-level security policies implemented

### Phase 2: Frontend Development (6-8 weeks)

#### 2.1 Next.js Application Setup
**Status**: Not Started | **Priority**: High

```bash
# Create Next.js frontend
npx create-next-app@latest frontend --typescript --tailwind --app

# Core frontend structure
frontend/
├── app/                 # App Router (Next.js 13+)
│   ├── (auth)/         # Authentication pages
│   ├── (dashboard)/    # Main application
│   └── api/            # API routes
├── components/
│   ├── ui/             # Reusable UI components
│   ├── project/        # Project-specific components
│   ├── editor/         # Video editor components
│   └── upload/         # File upload components
├── lib/
│   ├── supabase.ts     # Supabase client
│   ├── api.ts          # API client
│   └── stores/         # State management
└── types/              # TypeScript type definitions
```

**Key Components to Build**:
1. **Authentication system** with Supabase Auth
2. **Project dashboard** with grid layout
3. **File upload interface** with drag-and-drop and progress
4. **Video preview interface** with player controls
5. **Refinement interface** for AI feedback

#### 2.2 Core UI Components
**Status**: Not Started | **Priority**: Medium

**Project Dashboard**:
```typescript
// Key components to implement
- ProjectCard           # Project thumbnail and metadata
- ProjectGrid          # Responsive project gallery
- CreateProjectModal   # New project creation flow
- FilterSidebar        # Project filtering and search
- ShareDialog          # Project sharing controls
```

**Video Preview Interface**:
```typescript
// Preview components
- VideoPlayer          # Video player with basic controls
- MediaLibrary         # Asset browser with thumbnails
- VersionHistory       # Previous iterations
- ExportSettings       # Download options
```

**File Upload System**:
```typescript
// Upload components  
- DropZone             # Drag-and-drop file upload
- UploadProgress       # Progress indicators and queues
- FilePreview          # Media thumbnails and validation
- BatchUpload          # Multiple file handling
```

### Phase 3: Integration & Polish (4-6 weeks)

#### 3.1 AI Agent Integration
**Status**: Not Started | **Priority**: High

**Backend Service Layer**:
```python
# services/agent_service.py
class AgentService:
    async def analyze_media(self, project_id: str) -> AnalysisResult
    async def generate_video(self, project_id: str, prompt: str) -> GenerationResult  
    async def refine_video(self, project_id: str, feedback: str) -> RefinementResult
    async def get_processing_status(self, job_id: str) -> ProcessingStatus
```

**Frontend Integration**:
```typescript
// lib/agents.ts
export class AgentAPI {
  async startAnalysis(projectId: string): Promise<JobStatus>
  async generateVideo(projectId: string, prompt: string): Promise<JobStatus>
  async refineVideo(projectId: string, feedback: string): Promise<JobStatus>
  async subscribeToProgress(jobId: string, callback: ProgressCallback): void
}
```

#### 3.2 Polish & Optimization
**Status**: Not Started | **Priority**: Medium

**Performance Optimizations**:
- Component lazy loading for faster initial load
- Image optimization for thumbnails and previews
- Efficient video preview generation
- Background task status caching

**User Experience Improvements**:
- Loading states and skeleton screens
- Error handling with user-friendly messages
- Mobile-responsive design
- Keyboard shortcuts for common actions

### Phase 4: Production Deployment

**Implementation Goal**: Deploy a fully functional web application that allows users to create memory movies with AI assistance.

**Key Requirements**:
- Web-accessible interface for project creation and management
- File upload system supporting photos, videos, and audio
- Integration with the existing AI agent system for video generation
- User authentication and project persistence
- Responsive design for desktop and mobile use

### Implementation Requirements

**Core Features to Implement**:
1. **Backend API** - FastAPI server with endpoints for project management, file upload, and AI processing
2. **Frontend Application** - Next.js web app with authentication, project dashboard, and file upload
3. **Database Integration** - Supabase setup with the defined schema for user data and projects
4. **AI Agent Integration** - Connect the web interface to the existing agent system
5. **Deployment** - Production-ready deployment with proper environment configuration

### Success Criteria

**Functional Requirements**:
- [ ] Users can create accounts and log in
- [ ] Users can upload photos, videos, and music files
- [ ] Users can create projects with natural language prompts
- [ ] AI agents generate videos automatically using uploaded media
- [ ] Users can refine videos with natural language feedback
- [ ] Users can download completed videos
- [ ] Projects persist and users can return to edit them later

**Technical Requirements**:
- [ ] Responsive web interface (desktop and mobile)
- [ ] File upload handling for files up to 500MB
- [ ] Integration with existing AI agent system
- [ ] Supabase authentication and data persistence
- [ ] Production deployment with proper environment configuration

**User Experience Goals**:
- [ ] Intuitive interface requiring minimal learning
- [ ] Project creation to first video: <5 minutes
- [ ] Simple refinement process with natural language
- [ ] Clear progress indicators during AI processing

This specification guides the implementation of a web application that transforms the current AI engine into a user-friendly service for creating memory movies with AI assistance.