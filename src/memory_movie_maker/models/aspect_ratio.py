"""Aspect ratio enum and utilities."""

from enum import Enum
from typing import Tuple


class AspectRatio(str, Enum):
    """Supported video aspect ratios."""
    
    WIDESCREEN = "16:9"      # Standard widescreen (YouTube, TV, most videos)
    PORTRAIT = "9:16"        # Vertical video (Stories, Reels, TikTok, Shorts)
    CLASSIC = "4:3"          # Classic TV format, some older cameras
    SQUARE = "1:1"           # Square format (Instagram posts)
    ULTRAWIDE = "21:9"       # Ultrawide/Cinematic (movies, ultrawide monitors)
    
    @classmethod
    def from_string(cls, value: str) -> "AspectRatio":
        """Convert string to AspectRatio enum.
        
        Args:
            value: String representation of aspect ratio
            
        Returns:
            AspectRatio enum value
            
        Raises:
            ValueError: If value is not a valid aspect ratio
        """
        for ratio in cls:
            if ratio.value == value:
                return ratio
        raise ValueError(f"Invalid aspect ratio: {value}. Valid options: {[r.value for r in cls]}")
    
    @property
    def description(self) -> str:
        """Get human-readable description of aspect ratio."""
        descriptions = {
            AspectRatio.WIDESCREEN: "Widescreen (YouTube, TV, most videos)",
            AspectRatio.PORTRAIT: "Portrait/Vertical (Stories, Reels, TikTok)",
            AspectRatio.CLASSIC: "Classic (Old TV, some cameras)",
            AspectRatio.SQUARE: "Square (Instagram posts)",
            AspectRatio.ULTRAWIDE: "Ultrawide/Cinematic (Movies)",
        }
        return descriptions.get(self, "Custom aspect ratio")
    
    @property
    def resolution(self) -> Tuple[int, int]:
        """Get standard resolution for this aspect ratio."""
        resolutions = {
            AspectRatio.WIDESCREEN: (1920, 1080),  # Full HD
            AspectRatio.PORTRAIT: (1080, 1920),    # Vertical Full HD
            AspectRatio.CLASSIC: (1440, 1080),     # HD with 4:3 aspect
            AspectRatio.SQUARE: (1080, 1080),      # Square HD
            AspectRatio.ULTRAWIDE: (2560, 1080),   # Ultrawide HD
        }
        return resolutions[self]
    
    @property
    def preview_resolution(self) -> Tuple[int, int]:
        """Get preview resolution (roughly 1/3 size for faster rendering)."""
        width, height = self.resolution
        # Scale down and ensure even dimensions (required for codecs)
        preview_width = (width // 3) // 2 * 2
        preview_height = (height // 3) // 2 * 2
        return (preview_width, preview_height)
    
    @property
    def ratio_value(self) -> float:
        """Get aspect ratio as float value."""
        width, height = map(float, self.value.split(":"))
        return width / height
    
    @property
    def is_portrait(self) -> bool:
        """Check if this is a portrait/vertical aspect ratio."""
        return self == AspectRatio.PORTRAIT
    
    @property
    def is_landscape(self) -> bool:
        """Check if this is a landscape/horizontal aspect ratio."""
        return self in [AspectRatio.WIDESCREEN, AspectRatio.CLASSIC, AspectRatio.ULTRAWIDE]
    
    @property
    def is_square(self) -> bool:
        """Check if this is a square aspect ratio."""
        return self == AspectRatio.SQUARE
    
    def get_resolution_string(self, preview: bool = False) -> str:
        """Get resolution as a string (e.g., '1920x1080').
        
        Args:
            preview: If True, return preview resolution
            
        Returns:
            Resolution string in format 'WIDTHxHEIGHT'
        """
        width, height = self.preview_resolution if preview else self.resolution
        return f"{width}x{height}"