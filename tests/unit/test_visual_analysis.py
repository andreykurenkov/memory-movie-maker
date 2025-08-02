"""Unit tests for visual analysis tool."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
import io
from PIL import Image
import numpy as np

from memory_movie_maker.tools.visual_analysis import VisualAnalysisTool, analyze_visual_media
from memory_movie_maker.models.media_asset import GeminiAnalysis


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch('memory_movie_maker.tools.visual_analysis.settings') as mock:
        mock.google_genai_use_vertexai = False
        mock.gemini_api_key = "test-api-key"
        mock.get_gemini_model_name.return_value = "gemini-2.0-flash"
        yield mock


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes."""
    # Create a simple red square image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()


@pytest.fixture
def sample_gemini_response():
    """Sample Gemini API response."""
    return json.dumps({
        "description": "A red square on white background",
        "aesthetic_score": 0.8,
        "quality_issues": [],
        "main_subjects": ["red square", "geometric shape"],
        "tags": ["abstract", "geometric", "simple"]
    })


class TestVisualAnalysisTool:
    """Test VisualAnalysisTool class."""
    
    @patch('memory_movie_maker.tools.visual_analysis.GENAI_AVAILABLE', True)
    @patch('memory_movie_maker.tools.visual_analysis.genai')
    def test_initialization_with_genai(self, mock_genai, mock_settings):
        """Test initialization with direct Gemini API."""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        tool = VisualAnalysisTool()
        
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")
        assert tool._model == mock_model
        assert tool._api_type == "genai"
    
    @patch('memory_movie_maker.tools.visual_analysis.VERTEX_AI_AVAILABLE', True)
    @patch('memory_movie_maker.tools.visual_analysis.vertexai')
    @patch('memory_movie_maker.tools.visual_analysis.GenerativeModel')
    def test_initialization_with_vertex(self, mock_genmodel, mock_vertexai, mock_settings):
        """Test initialization with Vertex AI."""
        mock_settings.google_genai_use_vertexai = True
        mock_settings.google_cloud_project = "test-project"
        mock_settings.google_cloud_location = "us-central1"
        
        mock_model = Mock()
        mock_genmodel.return_value = mock_model
        
        tool = VisualAnalysisTool()
        
        mock_vertexai.init.assert_called_once_with(
            project="test-project",
            location="us-central1"
        )
        mock_genmodel.assert_called_once_with("gemini-2.0-flash")
        assert tool._model == mock_model
        assert tool._api_type == "vertex"
    
    def test_initialization_no_config(self, mock_settings):
        """Test initialization fails without proper config."""
        mock_settings.gemini_api_key = None
        mock_settings.google_cloud_project = None
        
        with pytest.raises(ValueError, match="No valid Gemini configuration"):
            VisualAnalysisTool()
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.visual_analysis.GENAI_AVAILABLE', True)
    @patch('memory_movie_maker.tools.visual_analysis.genai')
    async def test_analyze_image(self, mock_genai, mock_settings, sample_image_bytes, sample_gemini_response):
        """Test image analysis."""
        # Setup mocks
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = sample_gemini_response
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Create tool and mock the _call_gemini method
        tool = VisualAnalysisTool()
        tool._call_gemini = AsyncMock(return_value=sample_gemini_response)
        
        # Mock file loading
        with patch('builtins.open', mock_open(read_data=sample_image_bytes)):
            result = await tool.analyze_image("test.jpg")
        
        # Verify result
        assert isinstance(result, GeminiAnalysis)
        assert result.description == "A red square on white background"
        assert result.main_subjects == ["red square", "geometric shape"]
        assert result.aesthetic_score == 0.8
        assert len(result.tags) == 3
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.visual_analysis.GENAI_AVAILABLE', True)
    @patch('memory_movie_maker.tools.visual_analysis.genai')
    @patch('memory_movie_maker.tools.visual_analysis.cv2')
    async def test_analyze_video(self, mock_cv2, mock_genai, mock_settings):
        """Test video analysis."""
        # Setup mocks
        mock_model = Mock()
        video_response = json.dumps({
            "description": "A video showing movement",
            "aesthetic_score": 0.75,
            "quality_issues": [],
            "main_subjects": ["person", "object"],
            "tags": ["action", "outdoor"],
            "notable_segments": [
                {
                    "start_time": 0.0,
                    "end_time": 3.0,
                    "description": "Opening scene",
                    "importance": 0.8,
                    "tags": ["intro"]
                }
            ],
            "overall_motion": "moderate movement throughout",
            "scene_changes": [1.5, 4.0]
        })
        mock_response = Mock()
        mock_response.text = video_response
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Mock video capture
        mock_cap = Mock()
        mock_cap.get.side_effect = lambda prop: 30.0 if prop == 5 else 150.0  # FPS=30, frames=150
        mock_cap.read.return_value = (True, np.zeros((100, 100, 3), dtype=np.uint8))
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        
        tool = VisualAnalysisTool()
        tool._call_gemini_video = AsyncMock(return_value=video_response)
        tool._load_video = AsyncMock(return_value=b"fake video data")
        
        result = await tool.analyze_video("test.mp4")
        
        # Verify result
        assert isinstance(result, GeminiAnalysis)
        assert result.description == "A video showing movement"
        assert len(result.notable_segments) == 1
        assert result.notable_segments[0].start_time == 0.0
        assert result.overall_motion == "moderate movement throughout"
        assert len(result.scene_changes) == 2
    
    
    @patch('memory_movie_maker.tools.visual_analysis.GENAI_AVAILABLE', True)
    @patch('memory_movie_maker.tools.visual_analysis.genai')
    def test_parse_gemini_response(self, mock_genai, mock_settings):
        """Test parsing Gemini response."""
        # Mock genai for initialization
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        tool = VisualAnalysisTool()
        
        # Test valid JSON for image
        response = """Here's the analysis:
{
    "description": "Test image",
    "aesthetic_score": 0.9,
    "quality_issues": [],
    "main_subjects": ["object1"],
    "tags": ["test"]
}
Some additional text."""
        
        result = tool._parse_gemini_response(response)
        assert result.description == "Test image"
        assert result.aesthetic_score == 0.9
        assert len(result.tags) == 1
        
        # Test invalid JSON
        bad_response = "This is not JSON"
        result = tool._parse_gemini_response(bad_response)
        assert result.description == "Analysis failed to parse"
        assert result.aesthetic_score == 0.5
        assert "parse_error" in result.quality_issues
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.visual_analysis.GENAI_AVAILABLE', True)
    @patch('memory_movie_maker.tools.visual_analysis.genai')
    async def test_analyze_with_storage(self, mock_genai, mock_settings, sample_image_bytes, sample_gemini_response):
        """Test analysis with storage interface."""
        # Mock genai for initialization
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Mock storage
        mock_storage = AsyncMock()
        mock_io = io.BytesIO(sample_image_bytes)
        mock_storage.download.return_value = mock_io
        
        # Mock Path.exists to return False
        with patch('memory_movie_maker.tools.visual_analysis.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            tool = VisualAnalysisTool(storage=mock_storage)
            tool._call_gemini = AsyncMock(return_value=sample_gemini_response)
            result = await tool.analyze_image("stored/image.jpg")
        
        # Verify storage was used
        mock_storage.download.assert_called_once_with("stored/image.jpg")
        assert isinstance(result, GeminiAnalysis)


class TestAnalyzeVisualMediaTool:
    """Test the ADK tool wrapper."""
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.visual_analysis.mimetypes')
    async def test_analyze_image_file(self, mock_mimetypes):
        """Test analyzing image file."""
        # Setup mocks
        mock_mimetypes.guess_type.return_value = ('image/jpeg', None)
        
        # Mock the tool initialization and methods
        with patch('memory_movie_maker.tools.visual_analysis.VisualAnalysisTool') as mock_tool_class:
            mock_tool = AsyncMock()
            mock_analysis = GeminiAnalysis(
                description="Test image",
                aesthetic_score=0.8,
                quality_issues=[],
                main_subjects=["test"],
                tags=["test"]
            )
            mock_tool.analyze_image.return_value = mock_analysis
            mock_tool_class.return_value = mock_tool
            
            # Call tool
            result = await analyze_visual_media("test.jpg")
        
        # Verify
        assert result["status"] == "success"
        assert result["type"] == "image"
        assert result["analysis"]["description"] == "Test image"
        assert result["analysis"]["aesthetic_score"] == 0.8
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.visual_analysis.mimetypes')
    async def test_analyze_video_file(self, mock_mimetypes):
        """Test analyzing video file."""
        # Setup mocks
        mock_mimetypes.guess_type.return_value = ('video/mp4', None)
        
        # Mock the tool initialization and methods
        with patch('memory_movie_maker.tools.visual_analysis.VisualAnalysisTool') as mock_tool_class:
            mock_tool = AsyncMock()
            from memory_movie_maker.models.media_asset import VideoSegment
            mock_analysis = GeminiAnalysis(
                description="Test video",
                aesthetic_score=0.75,
                quality_issues=[],
                main_subjects=["test"],
                tags=["test"],
                notable_segments=[
                    VideoSegment(
                        start_time=0.0,
                        end_time=2.0,
                        description="Test segment",
                        importance=0.8,
                        tags=["action"]
                    )
                ],
                overall_motion="moderate",
                scene_changes=[1.0, 3.0]
            )
            mock_tool.analyze_video.return_value = mock_analysis
            mock_tool_class.return_value = mock_tool
            
            # Call tool
            result = await analyze_visual_media("test.mp4")
        
        # Verify
        assert result["status"] == "success"
        assert result["type"] == "video"
        assert result["analysis"]["description"] == "Test video"
        assert len(result["analysis"]["notable_segments"]) == 1
        assert result["analysis"]["overall_motion"] == "moderate"
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.visual_analysis.mimetypes')
    async def test_analyze_unsupported_file(self, mock_mimetypes):
        """Test analyzing unsupported file type."""
        mock_mimetypes.guess_type.return_value = ('text/plain', None)
        
        # We don't need to create a tool for unsupported file types
        result = await analyze_visual_media("test.txt")
        
        assert result["status"] == "error"
        assert "Unsupported file type" in result["error"]
    
    @pytest.mark.asyncio
    @patch('memory_movie_maker.tools.visual_analysis.VisualAnalysisTool')
    @patch('memory_movie_maker.tools.visual_analysis.mimetypes')
    async def test_analyze_with_error(self, mock_mimetypes, mock_tool_class):
        """Test handling analysis errors."""
        mock_mimetypes.guess_type.return_value = ('image/jpeg', None)
        
        mock_tool = AsyncMock()
        mock_tool.analyze_image.side_effect = Exception("API error")
        mock_tool_class.return_value = mock_tool
        
        result = await analyze_visual_media("test.jpg")
        
        assert result["status"] == "error"
        assert "API error" in result["error"]


def mock_open(read_data=None):
    """Helper to create mock for open()."""
    m = MagicMock(spec=open)
    handle = MagicMock()
    handle.read.return_value = read_data
    handle.__enter__.return_value = handle
    m.return_value = handle
    return m