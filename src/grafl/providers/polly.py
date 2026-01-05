#!/usr/bin/env python3
"""
AWS Polly TTS provider implementation.
"""

import os
import threading
import configparser
from pathlib import Path
import numpy as np
import sounddevice as sd
from typing import Optional, Dict, Any, Tuple
from grafl.providers.base import TTSProvider, TTSError
from grafl.utils.logging import get_logger

# Logger for this module
logger = get_logger(__name__)


class PollyTTSProvider(TTSProvider):
    """AWS Polly TTS provider using boto3."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        logger.debug("Initializing AWS Polly TTS provider")
        
        # Load AWS credentials following AWS CLI priority
        self.aws_access_key, self.aws_secret_key, self._credentials_source = self._load_credentials()
        self.aws_region = self._get_region()
        logger.debug(f"AWS region: {self.aws_region}")
        
        # Voice configuration
        self.voice_id = self.config.get('voice_id', 'Matthew')
        self.engine = self.config.get('engine', 'neural')
        # Neural engine supports: 16000 Hz for PCM
        self.sample_rate = self.config.get('sample_rate', 16000)
        
        # Polly client (lazy initialization)
        self._client = None
        
        # Playback state
        self._lock = threading.Lock()
        self._audio_data: Optional[np.ndarray] = None
        self._playback_position = 0
        self._is_playing = False
        self._is_paused = False
        self._stream: Optional[sd.OutputStream] = None
        self._finished_event = threading.Event()
        self._current_chunk: Optional[np.ndarray] = None  # For visualization
    
    @property
    def name(self) -> str:
        return "AWS Polly"
    
    def _load_credentials(self) -> Tuple[Optional[str], Optional[str], str]:
        """Load AWS credentials following AWS CLI priority.
        
        Priority order:
        1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        2. Shared credentials file (~/.aws/credentials)
        
        Returns:
            Tuple of (access_key, secret_key, source_description)
        """
        logger.debug("Loading AWS credentials...")
        
        # 1. Check environment variables first
        access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        if access_key and secret_key:
            logger.info("AWS credentials loaded from environment variables")
            return access_key, secret_key, "environment variables"
        
        logger.debug("Environment variables not set, checking credentials file...")
        
        # 2. Check shared credentials file (~/.aws/credentials)
        credentials_file = Path.home() / ".aws" / "credentials"
        if credentials_file.exists():
            logger.debug(f"Found credentials file: {credentials_file}")
            try:
                config = configparser.ConfigParser()
                config.read(credentials_file)
                
                # Try default profile first
                profile = os.environ.get('AWS_PROFILE', 'default')
                logger.debug(f"Using AWS profile: {profile}")
                
                if profile in config:
                    access_key = config[profile].get('aws_access_key_id')
                    secret_key = config[profile].get('aws_secret_access_key')
                    
                    if access_key and secret_key:
                        logger.info(f"AWS credentials loaded from ~/.aws/credentials [{profile}]")
                        return access_key, secret_key, f"~/.aws/credentials [{profile}]"
                else:
                    logger.debug(f"Profile '{profile}' not found in credentials file")
            except Exception as e:
                logger.warning(f"Error reading credentials file: {e}")
        else:
            logger.debug("No credentials file found at ~/.aws/credentials")
        
        logger.warning("AWS credentials not found")
        return None, None, "not found"
    
    def _get_region(self) -> str:
        """Get AWS region from environment or config file."""
        # Check environment variable first
        region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
        if region:
            return region
        
        # Check config file
        config_file = Path.home() / ".aws" / "config"
        if config_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(config_file)
                
                profile = os.environ.get('AWS_PROFILE', 'default')
                section = f"profile {profile}" if profile != 'default' else 'default'
                
                if section in config:
                    region = config[section].get('region')
                    if region:
                        return region
            except Exception:
                pass
        
        return 'us-east-1'  # Default region
    
    def _get_client(self):
        """Get or create the boto3 Polly client."""
        if self._client is None:
            logger.debug("Creating boto3 Polly client...")
            try:
                import boto3
                self._client = boto3.client(
                    'polly',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                logger.debug(f"Polly client created for region: {self.aws_region}")
            except ImportError:
                logger.error("boto3 is not installed")
                raise TTSError("boto3 is not installed. Please install it with: pip install boto3")
            except Exception as e:
                logger.error(f"Failed to create Polly client: {e}")
                raise TTSError(f"Failed to create Polly client: {e}") from e
        return self._client
    
    def validate_config(self) -> bool:
        """Check if AWS credentials are available."""
        if not self.aws_access_key or not self.aws_secret_key:
            return False
        
        # Try to import boto3
        try:
            import boto3
        except ImportError:
            return False
        
        return True
    
    def get_config_error(self) -> str:
        """Get a descriptive error message if configuration is invalid.
        
        Returns:
            str: Error message describing what's missing
        """
        try:
            import boto3
        except ImportError:
            return "boto3 is not installed. Run: pip install boto3"
        
        if not self.aws_access_key or not self.aws_secret_key:
            return (
                "AWS credentials not found. Please configure them using one of:\n"
                "  1. Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY\n"
                "  2. AWS credentials file: ~/.aws/credentials"
            )
        
        return ""
    
    def speak(self, text: str) -> None:
        """Speak text using AWS Polly and sounddevice (non-blocking)."""
        logger.debug(f"Speaking text (length: {len(text)} chars)")
        self.stop()  # Stop any current playback
        
        try:
            client = self._get_client()
            
            # Synthesize speech with Polly
            logger.debug(f"Requesting synthesis: voice={self.voice_id}, engine={self.engine}, sample_rate={self.sample_rate}")
            response = client.synthesize_speech(
                Text=text,
                OutputFormat='pcm',
                VoiceId=self.voice_id,
                Engine=self.engine,
                SampleRate=str(self.sample_rate)
            )
            
            # Read audio stream
            audio_stream = response.get('AudioStream')
            if not audio_stream:
                logger.error("No audio stream returned from AWS Polly")
                raise TTSError("No audio stream returned from AWS Polly")
            
            audio_bytes = audio_stream.read()
            audio_stream.close()
            
            if not audio_bytes:
                logger.error("No audio data generated by AWS Polly")
                raise TTSError("No audio data generated by AWS Polly")
            
            logger.debug(f"Received audio data: {len(audio_bytes)} bytes")
            
            # Convert to normalized float32 audio [-1.0, 1.0]
            # Polly PCM output is 16-bit signed little-endian, mono
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            self._audio_data = audio_int16.astype(np.float32) / 32768.0
            
            duration_sec = len(self._audio_data) / self.sample_rate
            logger.info(f"AWS Polly synthesis complete: {duration_sec:.1f}s audio")
            
            # Reset playback state
            with self._lock:
                self._playback_position = 0
                self._is_playing = False
                self._is_paused = False
                self._finished_event.clear()
            
            self._start_stream()
            logger.debug("Audio playback started")
                
        except TTSError:
            raise
        except Exception as e:
            logger.error(f"Error during speech synthesis: {e}")
            raise TTSError(f"Error during speech synthesis: {e}") from e
    
    def _audio_callback(self, outdata, frames, time_info, status):
        """Callback for OutputStream - feeds audio data continuously."""
        if self._audio_data is None:
            outdata.fill(0)
            return
        
        with self._lock:
            start = self._playback_position
            
            if start >= len(self._audio_data):
                outdata.fill(0)
                self._finished_event.set()
                raise sd.CallbackStop()
            
            # Copy available audio data to output buffer
            available = len(self._audio_data) - start
            to_copy = min(frames, available)
            outdata[:to_copy, 0] = self._audio_data[start:start + to_copy]
            
            # Store current chunk for frequency visualization
            self._current_chunk = self._audio_data[start:start + to_copy].copy()
            
            # Zero-fill remaining frames and stop if we've reached the end
            if to_copy < frames:
                outdata[to_copy:] = 0
                self._finished_event.set()
                raise sd.CallbackStop()
            
            self._playback_position = start + frames
    
    def _start_stream(self) -> None:
        """Start the audio output stream."""
        if self._audio_data is None:
            return
        
        with self._lock:
            self._is_playing = True
            self._is_paused = False
        
        try:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=self._audio_callback,
                finished_callback=self._on_stream_finished
            )
            self._stream.start()
        except Exception as e:
            with self._lock:
                self._is_playing = False
            raise TTSError(f"Failed to start audio stream: {e}") from e
    
    def _on_stream_finished(self) -> None:
        """Called when the stream finishes playing."""
        with self._lock:
            # Only reset state if not paused (paused means intentional stop)
            if not self._is_paused:
                self._is_playing = False
    
    def pause(self) -> None:
        """Pause the current speech playback."""
        with self._lock:
            if not self._is_playing or self._is_paused:
                return
            self._is_paused = True
        
        try:
            if self._stream and self._stream.active:
                self._stream.stop()
        except Exception as e:
            raise TTSError(f"Error pausing playback: {e}") from e
    
    def resume(self) -> None:
        """Resume paused speech playback from current position."""
        with self._lock:
            if not self._is_paused or self._audio_data is None:
                return
            self._is_paused = False
        
        try:
            self._start_stream()
        except Exception as e:
            raise TTSError(f"Error resuming playback: {e}") from e
    
    def _stop_stream(self) -> None:
        """Stop and close the audio stream. Ignores errors."""
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
        except Exception:
            pass  # Ignore errors when stopping
    
    def stop(self) -> None:
        """Stop the current speech playback."""
        self._stop_stream()
        
        with self._lock:
            self._is_playing = False
            self._is_paused = False
            self._playback_position = 0
    
    def is_playing(self) -> bool:
        """Check if speech is currently playing."""
        with self._lock:
            return self._is_playing and not self._is_paused
    
    def is_paused(self) -> bool:
        """Check if speech is currently paused."""
        with self._lock:
            return self._is_paused
    
    def skip_forward(self, seconds: float) -> None:
        """Skip forward in the current speech playback."""
        if self._audio_data is None:
            return
        
        with self._lock:
            samples_to_skip = int(seconds * self.sample_rate)
            new_position = self._playback_position + samples_to_skip
            
            # Clamp to end of audio
            self._playback_position = min(new_position, len(self._audio_data))
            
            if new_position >= len(self._audio_data):
                # If we've reached the end, stop playback
                self._is_playing = False
                self._is_paused = False
                self._stop_stream()
    
    def skip_backward(self, seconds: float) -> None:
        """Skip backward in the current speech playback."""
        if self._audio_data is None:
            return
        
        with self._lock:
            samples_to_skip = int(seconds * self.sample_rate)
            new_position = self._playback_position - samples_to_skip
            # Clamp to start of audio
            self._playback_position = max(0, new_position)
    
    def get_frequency_bands(self, num_bands: int = 10) -> list[float]:
        """Get frequency band amplitudes for visualization using FFT."""
        with self._lock:
            if self._current_chunk is None or len(self._current_chunk) < 128:
                return [0.0] * num_bands
            chunk = self._current_chunk.copy()
        
        # Apply Hanning window to reduce spectral leakage, then perform FFT
        window = np.hanning(len(chunk))
        fft_data = np.fft.rfft(chunk * window)
        fft_magnitude = np.abs(fft_data)
        
        # Split into logarithmic frequency bands for more natural audio visualization
        if len(fft_magnitude) > num_bands:
            band_edges = np.logspace(0, np.log10(len(fft_magnitude)), num_bands + 1).astype(int)
            
            bands = []
            for i in range(num_bands):
                start = band_edges[i]
                end = min(band_edges[i + 1], len(fft_magnitude))
                
                if end > start:
                    # Use RMS for better energy representation
                    band_energy = np.sqrt(np.mean(fft_magnitude[start:end] ** 2))
                    bands.append(float(band_energy))
                else:
                    bands.append(0.0)
        else:
            # Fallback for very small FFT results
            bands = [float(x) for x in fft_magnitude[:num_bands]]
            bands.extend([0.0] * (num_bands - len(bands)))
        
        # Normalize and apply power curve for better dynamic range visualization
        max_val = max(bands) if bands else 0
        if max_val > 0:
            bands = [(b / max_val) ** 0.7 for b in bands]
        
        return bands
    
    def get_progress(self) -> float:
        """Get playback progress as a value between 0.0 and 1.0."""
        with self._lock:
            if self._audio_data is None or len(self._audio_data) == 0:
                return 0.0
            return min(1.0, self._playback_position / len(self._audio_data))

