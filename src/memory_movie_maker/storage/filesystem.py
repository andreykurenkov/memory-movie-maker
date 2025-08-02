"""Filesystem storage implementation."""

import asyncio
import shutil
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional
import aiofiles
import aiofiles.os
from contextlib import asynccontextmanager

from .interface import StorageInterface, StorageError
from .utils import (
    validate_file_path, validate_file_type, sanitize_filename,
    validate_file_size, get_content_type, is_media_file
)


class FilesystemStorage(StorageInterface):
    """Filesystem-based storage implementation.
    
    This implementation stores files on the local filesystem with
    a structured directory layout for projects, cache, and temporary files.
    """
    
    def __init__(self, base_path: str):
        """Initialize filesystem storage.
        
        Args:
            base_path: Base directory for all storage operations
        """
        self.base_path = Path(base_path).resolve()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directory structure exists."""
        directories = [
            self.base_path / "projects",
            self.base_path / "cache" / "analysis",
            self.base_path / "temp",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_absolute_path(self, storage_path: str) -> Path:
        """Convert storage path to absolute filesystem path.
        
        Args:
            storage_path: Relative storage path
            
        Returns:
            Absolute Path object
            
        Raises:
            StorageError: If path is invalid
        """
        if not validate_file_path(storage_path):
            raise StorageError(f"Invalid storage path: {storage_path}")
        
        abs_path = self.base_path / storage_path
        
        # Ensure path is within base directory
        try:
            abs_path.relative_to(self.base_path)
        except ValueError:
            raise StorageError(f"Path escapes storage directory: {storage_path}")
        
        return abs_path
    
    async def upload(self, file_path: str, content: BinaryIO) -> str:
        """Upload file and return storage path.
        
        Args:
            file_path: Relative path for the file in storage
            content: Binary file content to upload
            
        Returns:
            Storage path that can be used to retrieve the file
            
        Raises:
            StorageError: If upload fails
        """
        # Sanitize filename
        path_parts = Path(file_path).parts
        if path_parts:
            sanitized_parts = list(path_parts[:-1]) + [sanitize_filename(path_parts[-1])]
            file_path = str(Path(*sanitized_parts))
        
        # Validate path
        if not validate_file_path(file_path):
            raise StorageError(f"Invalid file path: {file_path}")
        
        abs_path = self._get_absolute_path(file_path)
        
        try:
            # Read content into memory for validation
            content.seek(0)
            file_content = content.read()
            
            # Validate file type
            if not validate_file_type(file_path, file_content[:8192]):
                raise StorageError(f"File type not allowed: {file_path}")
            
            # Validate file size
            if not validate_file_size(len(file_content)):
                raise StorageError(f"File too large: {len(file_content)} bytes")
            
            # Ensure parent directory exists
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first (atomic operation)
            temp_path = abs_path.with_suffix(abs_path.suffix + '.tmp')
            
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(file_content)
            
            # Move to final location
            await aiofiles.os.rename(temp_path, abs_path)
            
            # Return relative path
            return str(Path(file_path))
            
        except Exception as e:
            # Clean up temp file if it exists
            temp_path = abs_path.with_suffix(abs_path.suffix + '.tmp')
            if temp_path.exists():
                temp_path.unlink()
            
            if isinstance(e, StorageError):
                raise
            raise StorageError(f"Failed to upload file: {e}")
    
    async def download(self, storage_path: str) -> BinaryIO:
        """Download file from storage.
        
        Args:
            storage_path: Path returned from upload()
            
        Returns:
            Binary file content
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If download fails
        """
        abs_path = self._get_absolute_path(storage_path)
        
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        
        try:
            async with aiofiles.open(abs_path, 'rb') as f:
                content = await f.read()
            
            return BytesIO(content)
            
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise StorageError(f"Failed to download file: {e}")
    
    async def delete(self, storage_path: str) -> bool:
        """Delete file from storage.
        
        Args:
            storage_path: Path to file to delete
            
        Returns:
            True if file was deleted, False if it didn't exist
            
        Raises:
            StorageError: If deletion fails
        """
        abs_path = self._get_absolute_path(storage_path)
        
        try:
            if not abs_path.exists():
                return False
            
            await aiofiles.os.remove(abs_path)
            
            # Clean up empty parent directories
            parent = abs_path.parent
            while parent != self.base_path and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
            
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to delete file: {e}")
    
    async def exists(self, storage_path: str) -> bool:
        """Check if file exists.
        
        Args:
            storage_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            abs_path = self._get_absolute_path(storage_path)
            return abs_path.exists()
        except StorageError:
            return False
    
    async def list_files(self, prefix: str) -> list[str]:
        """List files with given prefix.
        
        Args:
            prefix: Path prefix to filter files
            
        Returns:
            List of storage paths matching the prefix
            
        Raises:
            StorageError: If listing fails
        """
        try:
            # Ensure prefix doesn't escape base directory
            if not validate_file_path(prefix):
                raise StorageError(f"Invalid prefix: {prefix}")
            
            prefix_path = self.base_path / prefix
            
            # Collect all files recursively
            files = []
            
            def collect_files(path: Path):
                if path.is_file():
                    try:
                        rel_path = path.relative_to(self.base_path)
                        files.append(str(rel_path))
                    except ValueError:
                        pass
                elif path.is_dir():
                    for child in path.iterdir():
                        collect_files(child)
            
            if prefix_path.exists():
                collect_files(prefix_path)
            
            return sorted(files)
            
        except Exception as e:
            if isinstance(e, StorageError):
                raise
            raise StorageError(f"Failed to list files: {e}")
    
    async def get_file_size(self, storage_path: str) -> int:
        """Get file size in bytes.
        
        Args:
            storage_path: Path to file
            
        Returns:
            File size in bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If operation fails
        """
        abs_path = self._get_absolute_path(storage_path)
        
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        
        try:
            stat = await aiofiles.os.stat(abs_path)
            return stat.st_size
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise StorageError(f"Failed to get file size: {e}")
    
    async def get_file_metadata(self, storage_path: str) -> dict:
        """Get file metadata.
        
        Args:
            storage_path: Path to file
            
        Returns:
            Dictionary with metadata (size, modified_time, content_type, etc)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If operation fails
        """
        abs_path = self._get_absolute_path(storage_path)
        
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {storage_path}")
        
        try:
            stat = await aiofiles.os.stat(abs_path)
            
            # Read first few bytes for content type detection
            async with aiofiles.open(abs_path, 'rb') as f:
                header = await f.read(8192)
            
            return {
                'size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'content_type': get_content_type(str(abs_path), header),
                'is_media': is_media_file(str(abs_path)),
            }
            
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise StorageError(f"Failed to get metadata: {e}")
    
    async def copy(self, source_path: str, dest_path: str) -> str:
        """Copy file within storage.
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            
        Returns:
            New storage path
            
        Raises:
            FileNotFoundError: If source doesn't exist
            StorageError: If copy fails
        """
        source_abs = self._get_absolute_path(source_path)
        
        if not source_abs.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Sanitize destination filename
        path_parts = Path(dest_path).parts
        if path_parts:
            sanitized_parts = list(path_parts[:-1]) + [sanitize_filename(path_parts[-1])]
            dest_path = str(Path(*sanitized_parts))
        
        dest_abs = self._get_absolute_path(dest_path)
        
        try:
            # Ensure destination directory exists
            dest_abs.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            await asyncio.to_thread(shutil.copy2, source_abs, dest_abs)
            
            return dest_path
            
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise StorageError(f"Failed to copy file: {e}")
    
    async def move(self, source_path: str, dest_path: str) -> str:
        """Move file within storage.
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            
        Returns:
            New storage path
            
        Raises:
            FileNotFoundError: If source doesn't exist
            StorageError: If move fails
        """
        source_abs = self._get_absolute_path(source_path)
        
        if not source_abs.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Sanitize destination filename
        path_parts = Path(dest_path).parts
        if path_parts:
            sanitized_parts = list(path_parts[:-1]) + [sanitize_filename(path_parts[-1])]
            dest_path = str(Path(*sanitized_parts))
        
        dest_abs = self._get_absolute_path(dest_path)
        
        try:
            # Ensure destination directory exists
            dest_abs.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            await aiofiles.os.rename(source_abs, dest_abs)
            
            # Clean up empty source directories
            parent = source_abs.parent
            while parent != self.base_path and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
            
            return dest_path
            
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise StorageError(f"Failed to move file: {e}")
    
    # Additional helper methods
    
    async def cleanup_temp_files(self, older_than_hours: int = 24):
        """Clean up old temporary files.
        
        Args:
            older_than_hours: Remove files older than this many hours
        """
        temp_dir = self.base_path / "temp"
        if not temp_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
        
        for file_path in temp_dir.rglob("*"):
            if file_path.is_file():
                stat = await aiofiles.os.stat(file_path)
                if stat.st_mtime < cutoff_time:
                    try:
                        await aiofiles.os.remove(file_path)
                    except Exception:
                        pass  # Ignore errors during cleanup
    
    async def get_project_size(self, project_id: str) -> int:
        """Get total size of a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Total size in bytes
        """
        project_path = self.base_path / "projects" / project_id
        if not project_path.exists():
            return 0
        
        total_size = 0
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                stat = await aiofiles.os.stat(file_path)
                total_size += stat.st_size
        
        return total_size