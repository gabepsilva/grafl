#!/usr/bin/env python3
"""
Logging configuration for grafl.
Follows XDG Base Directory specification for log files.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

# XDG Base Directory: ~/.local/share/grafl/logs/
LOG_DIR = Path.home() / ".local" / "share" / "grafl" / "logs"
LOG_FILE = LOG_DIR / "grafl.log"

# Maximum log file size (10MB)
MAX_LOG_SIZE = 10 * 1024 * 1024
# Keep 5 backup files
BACKUP_COUNT = 5

# Log level mapping
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,      # 10
    "INFO": logging.INFO,        # 20
    "WARNING": logging.WARNING,  # 30
    "ERROR": logging.ERROR,      # 40
    "CRITICAL": logging.CRITICAL # 50
}

DEFAULT_LOG_LEVEL = "INFO"

# Flag to track if logging has been set up
_logging_initialized = False


def setup_logging(level: str = DEFAULT_LOG_LEVEL) -> None:
    """Set up logging configuration.
    
    Args:
        level: Log level name ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    """
    global _logging_initialized
    
    # Convert level name to logging constant
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels, handlers filter
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # File handler with rotation - respects configured level
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)  # File respects configured level
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler (stderr) - respects configured level
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    _logging_initialized = True
    
    # Log that logging is initialized (only to file to avoid console noise)
    logger = get_logger(__name__)
    logger.debug(f"Logging initialized: level={level}, file={LOG_FILE}")


def reconfigure_logging(level: str) -> None:
    """Reconfigure logging with a new level.
    
    Args:
        level: New log level name
    """
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    
    # Update both console and file handler levels
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setLevel(log_level)
    
    logger = get_logger(__name__)
    logger.debug(f"Logging reconfigured: level={level}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_log_file_path() -> Path:
    """Get the path to the log file.
    
    Returns:
        Path: The log file path
    """
    return LOG_FILE

