"""Utility functions for storage operations."""

import os
import re
import mimetypes
from pathlib import Path
from typing import Optional

# File type constants
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/quicktime', 'video/webm', 'video/avi', 'video/x-matroska'}
ALLOWED_AUDIO_TYPES = {'audio/mpeg', 'audio/wav', 'audio/aac', 'audio/ogg', 'audio/flac'}

ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.gif',  # Images
    '.mp4', '.mov', '.webm', '.avi', '.mkv',  # Videos
    '.mp3', '.wav', '.aac', '.ogg', '.flac'   # Audio
}

# Size limits
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
MAX_PROJECT_SIZE = 5 * 1024 * 1024 * 1024  # 5GB

# Filename sanitization regex
UNSAFE_CHARS = re.compile(r'[^\w\s\-.]')
MULTIPLE_DOTS = re.compile(r'\.{2,}')
LEADING_DOTS = re.compile(r'^\.+')


def validate_file_path(path: str) -> bool:
    """Prevent directory traversal attacks.
    
    Args:
        path: File path to validate
        
    Returns:
        True if path is safe, False otherwise
    """
    # Convert to Path object for normalization
    try:
        p = Path(path)
        
        # Check for path traversal attempts
        if '..' in p.parts:
            return False
        
        # Check for absolute paths
        if p.is_absolute():
            return False
        
        # Check for suspicious patterns
        path_str = str(p)
        if any(pattern in path_str for pattern in ['../', '..\\', '~/', '~\\']):
            return False
        
        return True
    except Exception:
        return False


def validate_file_type(file_path: str, content: bytes, strict: bool = True) -> bool:
    """Verify file type matches content.
    
    For now, we'll use simple extension checking. In production,
    you'd want to use python-magic for content verification.
    
    Args:
        file_path: Path to file (for extension check)
        content: First few bytes of file content
        strict: If True, verify MIME type matches extension
        
    Returns:
        True if file type is allowed, False otherwise
    """
    # Check extension
    ext = Path(file_path).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    # Basic content validation (check file signatures)
    if len(content) >= 4:
        # Check common file signatures
        signatures = {
            b'\xff\xd8\xff': ['.jpg', '.jpeg'],  # JPEG
            b'\x89PNG': ['.png'],  # PNG
            b'GIF8': ['.gif'],  # GIF
            b'RIFF': ['.webp', '.wav'],  # WebP or WAV
            b'\x00\x00\x00\x18ftypmp4': ['.mp4'],  # MP4
            b'\x00\x00\x00\x14ftyp': ['.mov', '.mp4'],  # QuickTime/MP4
            b'ID3': ['.mp3'],  # MP3 with ID3
            b'\xff\xfb': ['.mp3'],  # MP3 without ID3
        }
        
        for signature, extensions in signatures.items():
            if content.startswith(signature) and ext in extensions:
                return True
    
    # If no signature matched but extension is allowed, accept it
    # (some formats have variable headers)
    return True


def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filename.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for storage
    """
    # Split name and extension
    name = Path(filename).stem
    ext = Path(filename).suffix
    
    # Remove unsafe characters
    name = UNSAFE_CHARS.sub('_', name)
    
    # Remove multiple dots
    name = MULTIPLE_DOTS.sub('_', name)
    
    # Remove leading dots
    name = LEADING_DOTS.sub('', name)
    
    # Limit length
    if len(name) > 200:
        name = name[:200]
    
    # Ensure name is not empty
    if not name:
        name = 'unnamed'
    
    # Reconstruct filename
    return f"{name}{ext}"


def validate_file_size(size: int, file_type: Optional[str] = None) -> bool:
    """Check if file size is within limits.
    
    Args:
        size: File size in bytes
        file_type: Optional MIME type for type-specific limits
        
    Returns:
        True if size is acceptable, False otherwise
    """
    if size <= 0:
        return False
    
    if size > MAX_FILE_SIZE:
        return False
    
    # Type-specific limits (future enhancement)
    type_limits = {
        'image/': 50 * 1024 * 1024,    # 50MB for images
        'video/': 500 * 1024 * 1024,   # 500MB for videos
        'audio/': 100 * 1024 * 1024,   # 100MB for audio
    }
    
    if file_type:
        for prefix, limit in type_limits.items():
            if file_type.startswith(prefix) and size > limit:
                return False
    
    return True


def get_content_type(file_path: str, content: Optional[bytes] = None) -> str:
    """Determine content type from file path and content.
    
    Args:
        file_path: Path to file
        content: Optional file content for magic detection
        
    Returns:
        MIME type string
    """
    # Use mimetypes module
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'


def is_media_file(file_path: str) -> bool:
    """Check if file is a supported media type.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file is image, video, or audio
    """
    ext = Path(file_path).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def get_media_type(file_path: str) -> Optional[str]:
    """Get media type category from file path.
    
    Args:
        file_path: Path to check
        
    Returns:
        'image', 'video', 'audio', or None
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        return None
    
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    
    return None