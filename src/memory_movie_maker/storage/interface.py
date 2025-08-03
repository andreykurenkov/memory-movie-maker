"""Abstract storage interface for Memory Movie Maker."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageInterface(ABC):
    """Abstract storage interface for media and project files.
    
    This interface defines the contract for all storage implementations.
    It supports both synchronous and asynchronous operations for flexibility.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def delete(self, storage_path: str) -> bool:
        """Delete file from storage.
        
        Args:
            storage_path: Path to file to delete
            
        Returns:
            True if file was deleted, False if it didn't exist
            
        Raises:
            StorageError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Check if file exists.
        
        Args:
            storage_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def list_files(self, prefix: str) -> list[str]:
        """List files with given prefix.
        
        Args:
            prefix: Path prefix to filter files
            
        Returns:
            List of storage paths matching the prefix
            
        Raises:
            StorageError: If listing fails
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass


class StorageError(Exception):
    """Base exception for storage operations."""
    pass