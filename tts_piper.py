#!/usr/bin/env python3
"""
Piper TTS provider implementation.
"""

import os
import subprocess
from typing import Optional, Dict, Any
from tts_interface import TTSProvider, TTSError


class PiperTTSProvider(TTSProvider):
    """Piper TTS provider using local ONNX models."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Default configuration
        self.script_dir = self.config.get('script_dir', 
                                          os.path.dirname(os.path.abspath(__file__)))
        self.piper_bin = self.config.get('piper_bin', 
                                         os.path.join(self.script_dir, "venv", "bin", "piper"))
        self.model_path = self.config.get('model_path',
                                          os.path.join(self.script_dir, "en_US-lessac-medium"))
        self.sample_rate = self.config.get('sample_rate', 22050)
    
    @property
    def name(self) -> str:
        return "Piper TTS"
    
    def validate_config(self) -> bool:
        """Check if piper binary and model exist."""
        if not os.path.exists(self.piper_bin):
            return False
        if not os.path.exists(f"{self.model_path}.onnx"):
            return False
        return True
    
    def speak(self, text: str) -> None:
        """Speak text using Piper and paplay."""
        try:
            # Create piper process
            piper_process = subprocess.Popen(
                [self.piper_bin, "--model", self.model_path, "--output_file", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Create paplay process
            paplay_process = subprocess.Popen(
                ["paplay", "--raw", f"--rate={self.sample_rate}", 
                 "--format=s16le", "--channels=1"],
                stdin=piper_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Send text to piper
            piper_process.stdin.write(text.encode('utf-8'))
            piper_process.stdin.close()
            
            # Allow piper's output to flow to paplay
            piper_process.stdout.close()
            
            # Wait for both processes to complete
            piper_process.wait()
            paplay_process.wait()
            
            # Check for errors
            if piper_process.returncode != 0:
                raise TTSError(f"Piper process failed with code {piper_process.returncode}")
            if paplay_process.returncode != 0:
                raise TTSError(f"Paplay process failed with code {paplay_process.returncode}")
                
        except subprocess.SubprocessError as e:
            raise TTSError(f"Subprocess error during speech: {e}")
        except Exception as e:
            raise TTSError(f"Error during speech: {e}")

