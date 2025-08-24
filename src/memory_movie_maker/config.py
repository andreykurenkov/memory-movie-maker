"""Configuration management for Memory Movie Maker."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Cloud / Gemini API
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = True
    gemini_api_key: Optional[str] = None
    
    # Storage configuration (simplified - filesystem only)
    storage_path: str = "./data"
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    max_project_size: int = 5 * 1024 * 1024 * 1024  # 5GB
    
    # Processing configuration
    batch_size: int = 10
    analysis_cache_enabled: bool = True
    analysis_cache_ttl: int = 86400  # 24 hours in seconds
    
    # Video rendering
    default_video_resolution: str = "1920x1080"
    default_video_fps: int = 30
    default_video_codec: str = "libx264"
    default_audio_codec: str = "aac"
    
    # Development
    debug: bool = False
    log_level: str = "INFO"
    
    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env file
    )
    
    def get_gemini_model_name(self) -> str:
        """Get the Gemini model name based on configuration."""
        return "gemini-2.0-flash"
    
    def validate_api_keys(self) -> bool:
        """Check if required API keys are configured."""
        if self.google_genai_use_vertexai:
            return bool(self.google_cloud_project)
        else:
            return bool(self.gemini_api_key)


# Global settings instance
settings = Settings()