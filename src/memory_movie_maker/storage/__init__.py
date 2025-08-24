"""Storage module for Memory Movie Maker.

This module provides filesystem storage for managing media files, 
project data, and temporary assets.
"""

from .interface import StorageInterface
from .filesystem import FilesystemStorage

__all__ = ["StorageInterface", "FilesystemStorage"]