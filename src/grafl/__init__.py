"""
Grafl - A text-to-speech application with GTK4 interface.
"""

__version__ = "0.1.0"

# Import main components for easy access
from grafl.providers.base import TTSProvider, TTSError
from grafl.providers.piper import PiperTTSProvider
from grafl.cli import main as cli_main

__all__ = [
    "TTSProvider",
    "TTSError",
    "PiperTTSProvider",
    "cli_main",
]

