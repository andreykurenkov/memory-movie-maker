"""Centralized logging configuration for Memory Movie Maker."""

import logging
import sys
from typing import Optional


def configure_logging(
    level: str = "INFO",
    format: Optional[str] = None,
    suppress_external: bool = True
) -> None:
    """Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format: Custom format string, or None for default
        suppress_external: If True, suppress noisy external library logs
    """
    # Default format: levelname | time | filename:lineno | message
    if format is None:
        format = "%(levelname)-5s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format,
        datefmt="%H:%M:%S",  # Just time, no date
        stream=sys.stdout,
        force=True  # Reconfigure if already configured
    )
    
    if suppress_external:
        # Suppress noisy external libraries
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("google.genai").setLevel(logging.WARNING)
        logging.getLogger("google_genai").setLevel(logging.WARNING)
        logging.getLogger("google.genai.models").setLevel(logging.WARNING)
        logging.getLogger("google.auth").setLevel(logging.WARNING)
        logging.getLogger("google.auth.transport").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("moviepy").setLevel(logging.WARNING)
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("vertexai").setLevel(logging.WARNING)
        
        # Suppress all google.* loggers except our own
        for name in logging.root.manager.loggerDict:
            if name.startswith("google.") and not name.startswith("google.adk"):
                logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class ProgressLogger:
    """Helper class for logging progress updates in a user-friendly way."""
    
    def __init__(self, name: str):
        # Create a custom logger with the module name
        self.logger = logging.getLogger(name)
        self._current_task = None
        self.name = name.split('.')[-1] if '.' in name else name
        
    def _log(self, level: int, message: str) -> None:
        """Log with custom formatting to show the actual module name."""
        # Get the actual caller's frame info
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            filename = caller_frame.f_code.co_filename.split('/')[-1]
            lineno = caller_frame.f_lineno
        else:
            filename = self.name + ".py"
            lineno = 0
            
        # Create a custom log record
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            filename,
            lineno,
            message,
            args=(),
            exc_info=None
        )
        self.logger.handle(record)
        
    def start_task(self, task: str) -> None:
        """Log the start of a new task."""
        self._current_task = task
        self._log(logging.INFO, f"🚀 Starting: {task}")
        
    def update(self, message: str) -> None:
        """Log a progress update."""
        if self._current_task:
            self._log(logging.INFO, f"   ▶ {message}")
        else:
            self._log(logging.INFO, f"▶ {message}")
            
    def complete(self, message: Optional[str] = None) -> None:
        """Log task completion."""
        if message:
            self._log(logging.INFO, f"✅ {message}")
        elif self._current_task:
            self._log(logging.INFO, f"✅ Completed: {self._current_task}")
        self._current_task = None
        
    def error(self, message: str) -> None:
        """Log an error."""
        self._log(logging.ERROR, f"❌ {message}")
        
    def warning(self, message: str) -> None:
        """Log a warning."""
        self._log(logging.WARNING, f"⚠️  {message}")