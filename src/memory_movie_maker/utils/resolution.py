"""Resolution and aspect ratio utilities.

This module provides backward-compatible utility functions that work with
the AspectRatio enum from models.aspect_ratio.
"""

from typing import Tuple, Union
from ..models.aspect_ratio import AspectRatio


def get_resolution_for_aspect_ratio(
    aspect_ratio: Union[str, AspectRatio], 
    preview: bool = False
) -> Tuple[int, int]:
    """Get the appropriate resolution for a given aspect ratio.
    
    Args:
        aspect_ratio: Aspect ratio string or enum
        preview: If True, return lower resolution for preview
        
    Returns:
        Tuple of (width, height) in pixels
    """
    # Convert string to enum if needed
    if isinstance(aspect_ratio, str):
        try:
            aspect_ratio = AspectRatio.from_string(aspect_ratio)
        except ValueError:
            # Default to widescreen if invalid
            aspect_ratio = AspectRatio.WIDESCREEN
    
    return aspect_ratio.preview_resolution if preview else aspect_ratio.resolution


def get_resolution_string(
    aspect_ratio: Union[str, AspectRatio], 
    preview: bool = False
) -> str:
    """Get resolution as a string (e.g., "1920x1080").
    
    Args:
        aspect_ratio: Aspect ratio string or enum
        preview: If True, return preview resolution
        
    Returns:
        Resolution string in format "WIDTHxHEIGHT"
    """
    # Convert string to enum if needed
    if isinstance(aspect_ratio, str):
        try:
            aspect_ratio = AspectRatio.from_string(aspect_ratio)
        except ValueError:
            aspect_ratio = AspectRatio.WIDESCREEN
    
    return aspect_ratio.get_resolution_string(preview)


def parse_aspect_ratio(ratio_str: Union[str, AspectRatio]) -> float:
    """Parse aspect ratio to float value.
    
    Args:
        ratio_str: Aspect ratio as string or enum
        
    Returns:
        Aspect ratio as float (e.g., 1.777...)
    """
    if isinstance(ratio_str, AspectRatio):
        return ratio_str.ratio_value
    
    if isinstance(ratio_str, str) and ":" in ratio_str:
        width, height = map(float, ratio_str.split(":"))
        return width / height
    
    return 16.0 / 9.0  # Default


def is_portrait(aspect_ratio: Union[str, AspectRatio]) -> bool:
    """Check if aspect ratio is portrait orientation.
    
    Args:
        aspect_ratio: Aspect ratio string or enum
        
    Returns:
        True if portrait (height > width), False otherwise
    """
    if isinstance(aspect_ratio, AspectRatio):
        return aspect_ratio.is_portrait
    return aspect_ratio == "9:16"


def is_square(aspect_ratio: Union[str, AspectRatio]) -> bool:
    """Check if aspect ratio is square.
    
    Args:
        aspect_ratio: Aspect ratio string or enum
        
    Returns:
        True if square (1:1), False otherwise
    """
    if isinstance(aspect_ratio, AspectRatio):
        return aspect_ratio.is_square
    return aspect_ratio == "1:1"


def get_aspect_ratio_description(aspect_ratio: Union[str, AspectRatio]) -> str:
    """Get human-readable description of aspect ratio.
    
    Args:
        aspect_ratio: Aspect ratio string or enum
        
    Returns:
        Description of the aspect ratio and its common uses
    """
    if isinstance(aspect_ratio, AspectRatio):
        return aspect_ratio.description
    
    # Fallback for strings
    try:
        enum_val = AspectRatio.from_string(aspect_ratio)
        return enum_val.description
    except ValueError:
        return "Custom aspect ratio"