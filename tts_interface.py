#!/usr/bin/env python3
"""
Abstract interface for TTS (Text-to-Speech) providers.
Allows plugging in different TTS engines in the future.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the TTS provider with optional configuration.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config or {}
    
    @abstractmethod
    def speak(self, text: str) -> None:
        """
        Speak the given text. May be non-blocking depending on implementation.
        
        Args:
            text: The text to speak
            
        Raises:
            TTSError: If speech fails
        """
        pass
    
    def pause(self) -> None:
        """
        Pause the current speech playback.
        
        Raises:
            TTSError: If pause operation fails
        """
        pass
    
    def resume(self) -> None:
        """
        Resume paused speech playback.
        
        Raises:
            TTSError: If resume operation fails
        """
        pass
    
    def stop(self) -> None:
        """
        Stop the current speech playback.
        
        Raises:
            TTSError: If stop operation fails
        """
        pass
    
    def is_playing(self) -> bool:
        """
        Check if speech is currently playing.
        
        Returns:
            bool: True if playing, False otherwise
        """
        return False
    
    def is_paused(self) -> bool:
        """
        Check if speech is currently paused.
        
        Returns:
            bool: True if paused, False otherwise
        """
        return False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this TTS provider."""
        pass
    
    def validate_config(self) -> bool:
        """
        Validate that the provider is properly configured and available.
        
        Returns:
            bool: True if provider is ready to use, False otherwise
        """
        return True


class TTSError(Exception):
    """Exception raised when TTS operations fail."""
    pass

