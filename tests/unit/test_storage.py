"""Unit tests for storage layer."""

import asyncio
import pytest
import pytest_asyncio
from io import BytesIO
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from memory_movie_maker.storage import get_storage
from memory_movie_maker.storage.interface import StorageError
from memory_movie_maker.storage.filesystem import FilesystemStorage
from memory_movie_maker.config import Settings


@pytest_asyncio.fixture
async def temp_storage_dir():
    """Create a temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def storage(temp_storage_dir):
    """Create a filesystem storage instance."""
    return FilesystemStorage(temp_storage_dir)


@pytest.fixture
def sample_image():
    """Create a sample image file content."""
    # PNG header + minimal data
    return b'\x89PNG\r\n\x1a\n' + b'\x00' * 100


@pytest.fixture
def sample_video():
    """Create a sample video file content."""
    # MP4 header (simplified)
    return b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 1000


@pytest.fixture
def sample_audio():
    """Create a sample audio file content."""
    # MP3 ID3 header
    return b'ID3\x03\x00\x00\x00' + b'\x00' * 500


class TestStorageInterface:
    """Test the storage interface contract."""
    
    @pytest.mark.asyncio
    async def test_factory_function(self, temp_storage_dir):
        """Test storage factory function."""
        settings = Settings(storage_type="filesystem", storage_path=temp_storage_dir)
        storage = get_storage(settings)
        assert isinstance(storage, FilesystemStorage)
    
    @pytest.mark.asyncio
    async def test_factory_invalid_type(self):
        """Test factory with invalid storage type."""
        settings = Settings(storage_type="invalid")
        with pytest.raises(ValueError, match="Unknown storage type"):
            get_storage(settings)


class TestFilesystemStorage:
    """Test filesystem storage implementation."""
    
    @pytest.mark.asyncio
    async def test_upload_download_cycle(self, storage, sample_image):
        """Test basic upload and download."""
        # Upload
        content = BytesIO(sample_image)
        path = await storage.upload("test.png", content)
        assert path == "test.png"
        
        # Download
        downloaded = await storage.download(path)
        assert downloaded.read() == sample_image
    
    @pytest.mark.asyncio
    async def test_upload_with_subdirectory(self, storage, sample_image):
        """Test upload to subdirectory."""
        content = BytesIO(sample_image)
        path = await storage.upload("projects/proj1/media/test.png", content)
        assert path == "projects/proj1/media/test.png"
        
        # Verify file exists
        assert await storage.exists(path)
    
    @pytest.mark.asyncio
    async def test_upload_sanitizes_filename(self, storage, sample_image):
        """Test filename sanitization."""
        content = BytesIO(sample_image)
        dangerous_name = "../../../etc/passwd.png"
        # This should raise an error because the path contains ".."
        with pytest.raises(StorageError, match="Invalid file path"):
            await storage.upload(dangerous_name, content)
        
        # Test that a safe filename with special chars gets sanitized
        safe_but_weird = "test<>:|?.png"
        path = await storage.upload(safe_but_weird, BytesIO(sample_image))
        assert "<" not in path
        assert ">" not in path
        assert ":" not in path
        assert "|" not in path
        assert "?" not in path
    
    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, storage):
        """Test rejection of invalid file types."""
        content = BytesIO(b"#!/bin/sh\nrm -rf /")
        with pytest.raises(StorageError, match="File type not allowed"):
            await storage.upload("script.sh", content)
    
    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, storage):
        """Test rejection of oversized files."""
        # Create content larger than max size
        large_content = BytesIO(b'\x00' * (501 * 1024 * 1024))  # 501MB
        with pytest.raises(StorageError, match="File too large"):
            await storage.upload("large.png", large_content)
    
    @pytest.mark.asyncio
    async def test_download_nonexistent(self, storage):
        """Test downloading non-existent file."""
        with pytest.raises(FileNotFoundError):
            await storage.download("nonexistent.png")
    
    @pytest.mark.asyncio
    async def test_delete_existing(self, storage, sample_image):
        """Test deleting existing file."""
        # Upload first
        content = BytesIO(sample_image)
        path = await storage.upload("test.png", content)
        
        # Delete
        result = await storage.delete(path)
        assert result is True
        
        # Verify deleted
        assert not await storage.exists(path)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage):
        """Test deleting non-existent file."""
        result = await storage.delete("nonexistent.png")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_exists(self, storage, sample_image):
        """Test file existence check."""
        path = "test.png"
        
        # Check before upload
        assert not await storage.exists(path)
        
        # Upload
        content = BytesIO(sample_image)
        await storage.upload(path, content)
        
        # Check after upload
        assert await storage.exists(path)
    
    @pytest.mark.asyncio
    async def test_list_files(self, storage, sample_image, sample_video):
        """Test listing files with prefix."""
        # Upload multiple files
        await storage.upload("projects/proj1/img1.png", BytesIO(sample_image))
        await storage.upload("projects/proj1/img2.png", BytesIO(sample_image))
        await storage.upload("projects/proj2/video.mp4", BytesIO(sample_video))
        
        # List all project files
        files = await storage.list_files("projects")
        assert len(files) == 3
        assert "projects/proj1/img1.png" in files
        assert "projects/proj1/img2.png" in files
        assert "projects/proj2/video.mp4" in files
        
        # List specific project
        files = await storage.list_files("projects/proj1")
        assert len(files) == 2
        assert all("proj1" in f for f in files)
    
    @pytest.mark.asyncio
    async def test_get_file_size(self, storage, sample_image):
        """Test getting file size."""
        content = BytesIO(sample_image)
        path = await storage.upload("test.png", content)
        
        size = await storage.get_file_size(path)
        assert size == len(sample_image)
    
    @pytest.mark.asyncio
    async def test_get_file_metadata(self, storage, sample_image):
        """Test getting file metadata."""
        content = BytesIO(sample_image)
        path = await storage.upload("test.png", content)
        
        metadata = await storage.get_file_metadata(path)
        assert metadata['size'] == len(sample_image)
        assert metadata['content_type'] == 'image/png'
        assert metadata['is_media'] is True
        assert 'modified_time' in metadata
        assert 'created_time' in metadata
    
    @pytest.mark.asyncio
    async def test_copy_file(self, storage, sample_image):
        """Test copying files."""
        # Upload original
        content = BytesIO(sample_image)
        source = await storage.upload("original.png", content)
        
        # Copy
        dest = await storage.copy(source, "copy.png")
        assert dest == "copy.png"
        
        # Verify both exist
        assert await storage.exists(source)
        assert await storage.exists(dest)
        
        # Verify content is same
        original_content = await storage.download(source)
        copied_content = await storage.download(dest)
        assert original_content.read() == copied_content.read()
    
    @pytest.mark.asyncio
    async def test_move_file(self, storage, sample_image):
        """Test moving files."""
        # Upload original
        content = BytesIO(sample_image)
        source = await storage.upload("original.png", content)
        
        # Move
        dest = await storage.move(source, "moved.png")
        assert dest == "moved.png"
        
        # Verify source deleted and dest exists
        assert not await storage.exists(source)
        assert await storage.exists(dest)
    
    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, storage, sample_image):
        """Test concurrent file uploads."""
        async def upload_file(index):
            content = BytesIO(sample_image)
            return await storage.upload(f"concurrent_{index}.png", content)
        
        # Upload 10 files concurrently
        tasks = [upload_file(i) for i in range(10)]
        paths = await asyncio.gather(*tasks)
        
        # Verify all uploaded
        assert len(paths) == 10
        for path in paths:
            assert await storage.exists(path)
    
    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, storage, sample_image):
        """Test path traversal attack prevention."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "~/../../root/.ssh/id_rsa",
            "/etc/passwd",
            "C:\\Windows\\System32\\config",
        ]
        
        # Test that these paths are rejected during upload
        for path in malicious_paths:
            with pytest.raises(StorageError):
                await storage.upload(path, BytesIO(sample_image))
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_files(self, storage, sample_image):
        """Test temporary file cleanup."""
        # Create old temp file
        temp_path = "temp/old_file.png"
        await storage.upload(temp_path, BytesIO(sample_image))
        
        # Manually set old modification time
        abs_path = storage._get_absolute_path(temp_path)
        old_time = datetime.now().timestamp() - (25 * 3600)  # 25 hours ago
        import os
        os.utime(abs_path, (old_time, old_time))
        
        # Run cleanup
        await storage.cleanup_temp_files(older_than_hours=24)
        
        # Verify file deleted
        assert not await storage.exists(temp_path)
    
    @pytest.mark.asyncio
    async def test_get_project_size(self, storage, sample_image, sample_video):
        """Test calculating project size."""
        project_id = "test_project"
        
        # Upload files to project
        await storage.upload(f"projects/{project_id}/img1.png", BytesIO(sample_image))
        await storage.upload(f"projects/{project_id}/img2.png", BytesIO(sample_image))
        await storage.upload(f"projects/{project_id}/video.mp4", BytesIO(sample_video))
        
        # Get total size
        size = await storage.get_project_size(project_id)
        expected = len(sample_image) * 2 + len(sample_video)
        assert size == expected


class TestStorageUtils:
    """Test storage utility functions."""
    
    def test_validate_file_path(self):
        """Test path validation."""
        from memory_movie_maker.storage.utils import validate_file_path
        
        # Valid paths
        assert validate_file_path("file.png")
        assert validate_file_path("projects/123/media/file.mp4")
        assert validate_file_path("cache/analysis/result.json")
        
        # Invalid paths
        assert not validate_file_path("../etc/passwd")
        assert not validate_file_path("/etc/passwd")
        assert not validate_file_path("..\\windows\\system32")
        assert not validate_file_path("~/root/.ssh/id_rsa")
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from memory_movie_maker.storage.utils import sanitize_filename
        
        assert sanitize_filename("normal.png") == "normal.png"
        assert sanitize_filename("my file.png") == "my file.png"
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("file<>:|?.png") == "file_____.png"
        assert sanitize_filename("...hidden") == "_.hidden"
        assert sanitize_filename("a" * 250 + ".png") == "a" * 200 + ".png"
    
    def test_validate_file_type(self):
        """Test file type validation."""
        from memory_movie_maker.storage.utils import validate_file_type
        
        # Valid types
        assert validate_file_type("image.png", b'\x89PNG\r\n\x1a\n')
        assert validate_file_type("image.jpg", b'\xff\xd8\xff')
        assert validate_file_type("audio.mp3", b'ID3\x03\x00')
        
        # Invalid types
        assert not validate_file_type("script.sh", b'#!/bin/sh')
        assert not validate_file_type("executable.exe", b'MZ\x90\x00')
    
    def test_validate_file_size(self):
        """Test file size validation."""
        from memory_movie_maker.storage.utils import validate_file_size
        
        assert validate_file_size(1024)  # 1KB
        assert validate_file_size(100 * 1024 * 1024)  # 100MB
        assert not validate_file_size(0)
        assert not validate_file_size(-1)
        assert not validate_file_size(600 * 1024 * 1024)  # 600MB
    
    def test_get_media_type(self):
        """Test media type detection."""
        from memory_movie_maker.storage.utils import get_media_type
        
        assert get_media_type("photo.jpg") == "image"
        assert get_media_type("video.mp4") == "video"
        assert get_media_type("song.mp3") == "audio"
        assert get_media_type("document.pdf") is None