"""Simple logging utilities for cleaner output."""

import logging
import sys


def setup_logging():
    """Set up logging with clean format and suppressed external libraries."""
    # Create a custom formatter
    class CleanFormatter(logging.Formatter):
        """Custom formatter that shows clean output."""
        
        def format(self, record):
            # Extract just the module name from the full path
            module = record.pathname.split('/')[-1].replace('.py', '')
            
            # Format based on level
            if record.levelname == 'INFO':
                if hasattr(record, 'progress_type'):
                    if record.progress_type == 'start':
                        return f"🚀 {module}: {record.getMessage()}"
                    elif record.progress_type == 'update':
                        return f"   ▶ {record.getMessage()}"
                    elif record.progress_type == 'complete':
                        return f"✅ {module}: {record.getMessage()}"
                return f"INFO  | {module}: {record.getMessage()}"
            elif record.levelname == 'ERROR':
                return f"❌ ERROR | {module}: {record.getMessage()}"
            elif record.levelname == 'WARNING':
                return f"⚠️  WARN | {module}: {record.getMessage()}"
            else:
                return f"{record.levelname:5s} | {module}: {record.getMessage()}"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with custom formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CleanFormatter())
    root_logger.addHandler(console_handler)
    
    # Suppress noisy libraries
    for lib in ['httpx', 'httpcore', 'google.genai', 'google_genai', 'google.auth', 
                'urllib3', 'moviepy', 'PIL', 'vertexai', 'google.auth.transport']:
        logging.getLogger(lib).setLevel(logging.WARNING)
    
    # Suppress all google.* loggers except our own
    for name in list(logging.root.manager.loggerDict.keys()):
        if name.startswith('google.') and not name.startswith('google.adk'):
            logging.getLogger(name).setLevel(logging.WARNING)


def log_start(logger: logging.Logger, message: str):
    """Log the start of a task."""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0, message, (), None
    )
    record.progress_type = 'start'
    logger.handle(record)


def log_update(logger: logging.Logger, message: str):
    """Log a progress update."""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0, message, (), None
    )
    record.progress_type = 'update'
    logger.handle(record)


def log_complete(logger: logging.Logger, message: str):
    """Log task completion."""
    record = logger.makeRecord(
        logger.name, logging.INFO, "", 0, message, (), None
    )
    record.progress_type = 'complete'
    logger.handle(record)