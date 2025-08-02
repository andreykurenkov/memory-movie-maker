"""Storage module for Memory Movie Maker.

This module provides abstract storage interfaces and implementations
for managing media files, project data, and temporary assets.
"""

from .interface import StorageInterface
from ..config import Settings

__all__ = ["StorageInterface", "get_storage"]


def get_storage(settings: Settings) -> StorageInterface:
    """Factory function to get storage implementation based on settings.
    
    Args:
        settings: Application settings containing storage configuration
        
    Returns:
        StorageInterface implementation
        
    Raises:
        ValueError: If storage type is not supported
    """
    from .filesystem import FilesystemStorage
    
    if settings.storage_type == "filesystem":
        return FilesystemStorage(settings.storage_path)
    else:
        raise ValueError(f"Unknown storage type: {settings.storage_type}")