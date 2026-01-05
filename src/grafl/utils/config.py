#!/usr/bin/env python3
"""
Configuration management for grafl.
Handles persistent storage of user preferences.
"""

import json
import logging
from pathlib import Path
from typing import Optional

# Default config location
CONFIG_DIR = Path.home() / ".config" / "grafl"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Valid voice providers
VALID_PROVIDERS = ["piper", "polly"]
DEFAULT_PROVIDER = "piper"

# Valid log levels
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
DEFAULT_LOG_LEVEL = "INFO"


def _get_logger():
    """Get logger for this module (lazy initialization to avoid circular imports)."""
    return logging.getLogger(__name__)


def _ensure_config_dir() -> None:
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """Load config from file, returning empty dict if not found."""
    logger = _get_logger()
    
    if not CONFIG_FILE.exists():
        logger.debug(f"Config file not found: {CONFIG_FILE}")
        return {}
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            logger.debug(f"Config loaded from {CONFIG_FILE}")
            return config
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error loading config file: {e}")
        return {}


def _save_config(config: dict) -> None:
    """Save config to file."""
    logger = _get_logger()
    _ensure_config_dir()
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"Config saved to {CONFIG_FILE}")


def get_voice_provider() -> str:
    """Get the configured voice provider.
    
    Returns:
        str: The voice provider name ("piper" or "polly").
             Defaults to "piper" if not configured.
    """
    config = _load_config()
    provider = config.get("voice_provider", DEFAULT_PROVIDER)
    
    # Validate provider
    if provider not in VALID_PROVIDERS:
        return DEFAULT_PROVIDER
    
    return provider


def set_voice_provider(provider: str) -> bool:
    """Set the voice provider preference.
    
    Args:
        provider: The provider name ("piper" or "polly")
        
    Returns:
        bool: True if successful, False if invalid provider
    """
    logger = _get_logger()
    
    if provider not in VALID_PROVIDERS:
        logger.warning(f"Invalid voice provider: {provider}")
        return False
    
    config = _load_config()
    config["voice_provider"] = provider
    _save_config(config)
    logger.info(f"Voice provider set to: {provider}")
    
    return True


def get_config_path() -> Path:
    """Get the path to the config file.
    
    Returns:
        Path: The config file path
    """
    return CONFIG_FILE


def get_log_level() -> str:
    """Get the configured log level.
    
    Returns:
        str: The log level name ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
             Defaults to "INFO" if not configured.
    """
    config = _load_config()
    level = config.get("log_level", DEFAULT_LOG_LEVEL)
    
    # Validate level
    if level.upper() not in VALID_LOG_LEVELS:
        return DEFAULT_LOG_LEVEL
    
    return level.upper()


def set_log_level(level: str) -> bool:
    """Set the log level preference.
    
    Args:
        level: The log level name ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        
    Returns:
        bool: True if successful, False if invalid level
    """
    logger = _get_logger()
    
    if level.upper() not in VALID_LOG_LEVELS:
        logger.warning(f"Invalid log level: {level}")
        return False
    
    config = _load_config()
    config["log_level"] = level.upper()
    _save_config(config)
    logger.info(f"Log level set to: {level.upper()}")
    
    return True

