#!/usr/bin/env python3
"""
GTK4 floating window that displays while text is being spoken.
Uses pluggable TTS interface.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk
import sys
import threading
import time
import math

# Import TTS interface and providers
from grafl.providers.base import TTSProvider, TTSError
from grafl.providers.piper import PiperTTSProvider
from grafl.providers.polly import PollyTTSProvider
from grafl.utils.config import get_voice_provider, set_voice_provider, get_log_level, set_log_level
from grafl.utils.logging import setup_logging, reconfigure_logging, get_logger

# Logger for this module
logger = get_logger(__name__)


def create_provider(provider_name: str) -> TTSProvider:
    """Create a TTS provider instance by name.
    
    Args:
        provider_name: Either "piper" or "polly"
        
    Returns:
        TTSProvider instance
    """
    if provider_name == "polly":
        return PollyTTSProvider()
    return PiperTTSProvider()


def create_validated_provider() -> tuple[TTSProvider, str | None]:
    """Create and validate a TTS provider from config, with fallback to Piper.
    
    Returns:
        Tuple of (provider, error_message).
        If error_message is not None, provider creation failed entirely.
    """
    provider_name = get_voice_provider()
    logger.debug(f"Voice provider from config: {provider_name}")
    provider = create_provider(provider_name)
    
    if provider.validate_config():
        return provider, None
    
    # Provider validation failed
    if provider_name == "piper":
        return provider, f"TTS provider '{provider.name}' is not properly configured"
    
    # Non-piper provider failed - show error and try fallback
    error_msg = getattr(provider, 'get_config_error', lambda: "")()
    if error_msg:
        print(f"{provider.name} not available:\n{error_msg}", file=sys.stderr)
    print("Falling back to Piper...", file=sys.stderr)
    
    fallback = PiperTTSProvider()
    if fallback.validate_config():
        return fallback, None
    
    return fallback, f"TTS provider '{fallback.name}' is not properly configured"

class SpeakingWindow(Gtk.ApplicationWindow):
    def __init__(self, app, text, tts_provider: TTSProvider):
        super().__init__(application=app)
        self.text = text
        self.tts_provider = tts_provider
        self._playback_started = False
        self._wave_offset = 0  # For waveform animation
        self._current_progress = 0.0  # Current displayed progress (for smoothing)
        
        # Connect close handler
        self.connect("close-request", self.on_close_request)
        
        # Window configuration - minimal floating style
        self.set_title("Speaking...")
        self.set_resizable(False)
        
        # Make it borderless and float on top
        self.set_decorated(False)
        
        # Apply CSS for compact bar design
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background-color: rgba(0, 0, 0, 1.0);
                border-radius: 5px;
                border: 1px solid rgba(255, 255, 255, 1.0);
            }
            .icon-label {
                color: white;
                font-size: 24px;
            }
            .wave-bar {
                background-color: rgba(255, 255, 255, 0.6);
                border-radius: 2px;
                min-width: 3px;
            }
            progressbar {
                min-height: 1px;
                background-color: rgba(255, 255, 255, 0.2);
            }
            progressbar trough {
                min-height: 1px;
                background-color: rgba(255, 255, 255, 0.2);
            }
            progressbar progress {
                min-height: 1px;
                background-color: rgba(255, 255, 255, 0.8);
            }
            button {
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
                border: none;
                border-radius: 50%;
                min-width: 36px;
                min-height: 36px;
                padding: 0;
                font-size: 14px;
                font-weight: 600;
            }
            button:hover {
                background-color: rgba(255, 255, 255, 0.25);
            }
            .menu-button {
                background-color: transparent;
                border-radius: 4px;
                min-width: 28px;
                min-height: 28px;
                padding: 2px;
                font-size: 16px;
            }
            .menu-button:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            .menu-popover {
                background-color: rgba(30, 30, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
            .menu-popover label {
                color: white;
                font-size: 12px;
                margin-bottom: 4px;
            }
            .menu-popover dropdown {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                min-height: 28px;
            }
            .menu-popover dropdown:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Create main vertical container
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Create UI - compact horizontal bar layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_halign(Gtk.Align.CENTER)
        main_box.set_valign(Gtk.Align.CENTER)
        
        # Speaker icon
        icon_label = Gtk.Label(label="🔊")
        icon_label.add_css_class("icon-label")
        main_box.append(icon_label)
        
        # Waveform visualization (10 bars)
        waveform_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        waveform_box.set_halign(Gtk.Align.CENTER)
        waveform_box.set_valign(Gtk.Align.CENTER)
        waveform_box.set_size_request(80, 32)
        
        # Create 10 wave bars with varying initial heights
        wave_heights = [8, 16, 24, 20, 12, 18, 14, 22, 10, 16]
        self.wave_bars = []
        for height in wave_heights:
            bar = Gtk.Box()
            bar.add_css_class("wave-bar")
            bar.set_size_request(3, height)
            bar.set_valign(Gtk.Align.CENTER)
            waveform_box.append(bar)
            self.wave_bars.append((bar, height))
        
        main_box.append(waveform_box)
        
        # Control buttons (circular)
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls_box.set_halign(Gtk.Align.CENTER)
        
        # Skip backward button
        self.skip_backward_button = Gtk.Button(label="-5s")
        self.skip_backward_button.connect("clicked", self.on_skip_backward_clicked)
        controls_box.append(self.skip_backward_button)
        
        # Skip forward button
        self.skip_forward_button = Gtk.Button(label="+5s")
        self.skip_forward_button.connect("clicked", self.on_skip_forward_clicked)
        controls_box.append(self.skip_forward_button)
        
        # Pause/Resume button (toggle)
        self.pause_button = Gtk.Button(label="⏸")
        self.pause_button.connect("clicked", self.on_pause_clicked)
        controls_box.append(self.pause_button)
        
        # Stop button
        self.stop_button = Gtk.Button(label="⏹")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        controls_box.append(self.stop_button)
        
        main_box.append(controls_box)
        
        # Hamburger menu button
        self.menu_button = Gtk.Button(label="☰")
        self.menu_button.add_css_class("menu-button")
        
        # Create popover for menu
        self.menu_popover = Gtk.Popover()
        self.menu_popover.add_css_class("menu-popover")
        self.menu_popover.set_parent(self.menu_button)
        
        # Popover content
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        popover_box.set_margin_top(4)
        popover_box.set_margin_bottom(4)
        popover_box.set_margin_start(4)
        popover_box.set_margin_end(4)
        
        # Voice provider label
        provider_label = Gtk.Label(label="Voice Provider")
        provider_label.set_halign(Gtk.Align.START)
        popover_box.append(provider_label)
        
        # Provider dropdown
        provider_options = Gtk.StringList.new(["Piper", "AWS Polly"])
        self.provider_dropdown = Gtk.DropDown(model=provider_options)
        
        # Set current provider selection
        current_provider = get_voice_provider()
        self.provider_dropdown.set_selected(0 if current_provider == "piper" else 1)
        
        self.provider_dropdown.connect("notify::selected", self.on_provider_changed)
        popover_box.append(self.provider_dropdown)
        
        # Log level label
        log_level_label = Gtk.Label(label="Log Level")
        log_level_label.set_halign(Gtk.Align.START)
        log_level_label.set_margin_top(8)
        popover_box.append(log_level_label)
        
        # Log level dropdown with numeric levels
        log_level_options = Gtk.StringList.new([
            "10 - DEBUG",
            "20 - INFO",
            "30 - WARNING",
            "40 - ERROR",
            "50 - CRITICAL"
        ])
        self.log_level_dropdown = Gtk.DropDown(model=log_level_options)
        
        # Set current log level selection
        log_level_map = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
        current_log_level = get_log_level()
        self.log_level_dropdown.set_selected(log_level_map.get(current_log_level, 1))
        
        self.log_level_dropdown.connect("notify::selected", self.on_log_level_changed)
        popover_box.append(self.log_level_dropdown)
        
        self.menu_popover.set_child(popover_box)
        self.menu_button.connect("clicked", self.on_menu_clicked)
        
        main_box.append(self.menu_button)
        main_container.append(main_box)
        
        # Progress bar (1 pixel tall) - aligned with logo start and button end
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_size_request(1, 0)  # 1 pixel height
        self.progress_bar.set_show_text(False)  # No text on progress bar
        self.progress_bar.set_margin_start(39)  # Align with logo start
        self.progress_bar.set_margin_end(39)  # Align with button end
        self.progress_bar.set_margin_top(-5)  # Move up a bit from bottom
        self.progress_bar.set_margin_bottom(5)  # Small bottom margin
        main_container.append(self.progress_bar)
        
        self.set_child(main_container)
        
        # Compact window size for bar design
        self.set_default_size(380, 60)
        
        # Start status update timer
        GLib.timeout_add(100, self.update_status)
        
        # Start waveform animation timer
        GLib.timeout_add(75, self.animate_waveform)
        
        # Start smooth progress bar update timer (30fps for smooth animation)
        GLib.timeout_add(33, self.update_progress_smooth)
        
        # Start speaking in a separate thread
        threading.Thread(target=self.speak_text, daemon=True).start()
    
    def speak_text(self):
        """Use the configured TTS provider to speak the text."""
        try:
            self.tts_provider.speak(self.text)
            time.sleep(0.2)  # Brief delay for playback initialization
            
            # Wait for playback to complete
            while self.tts_provider.is_playing() or self.tts_provider.is_paused():
                time.sleep(0.1)
        except TTSError as e:
            print(f"TTS Error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error during speech: {e}", file=sys.stderr)
        # Window closing is handled by update_status when playback finishes
    
    def _handle_tts_action(self, action_name: str, action_func):
        """Execute TTS action with error handling."""
        try:
            action_func()
        except TTSError as e:
            print(f"Error {action_name}: {e}", file=sys.stderr)
    
    def on_pause_clicked(self, button):
        """Toggle pause/resume."""
        action = self.tts_provider.resume if self.tts_provider.is_paused() else self.tts_provider.pause
        action_name = "resuming" if self.tts_provider.is_paused() else "pausing"
        self._handle_tts_action(action_name, action)
    
    def on_skip_backward_clicked(self, button):
        """Skip backward 5 seconds."""
        self._handle_tts_action("skipping backward", lambda: self.tts_provider.skip_backward(5.0))
    
    def on_skip_forward_clicked(self, button):
        """Skip forward 5 seconds."""
        self._handle_tts_action("skipping forward", lambda: self.tts_provider.skip_forward(5.0))
    
    def on_stop_clicked(self, button):
        """Stop playback and close window."""
        self._handle_tts_action("stopping", self.tts_provider.stop)
        self.close()
    
    def on_menu_clicked(self, button):
        """Toggle the menu popover."""
        if self.menu_popover.get_visible():
            self.menu_popover.popdown()
        else:
            self.menu_popover.popup()
    
    def on_provider_changed(self, dropdown, param):
        """Handle provider selection change."""
        selected = dropdown.get_selected()
        new_provider = "piper" if selected == 0 else "polly"
        current_provider = get_voice_provider()
        
        if new_provider != current_provider:
            # Stop current playback first
            self._stop_audio_if_playing()
            
            # Switch provider
            self.tts_provider = create_provider(new_provider)
            
            if not self.tts_provider.validate_config():
                # Get detailed error message if available
                error_msg = getattr(self.tts_provider, 'get_config_error', lambda: "")()
                if error_msg:
                    print(f"Cannot use {self.tts_provider.name}:\n{error_msg}", file=sys.stderr)
                else:
                    print(f"TTS provider '{self.tts_provider.name}' is not properly configured", 
                          file=sys.stderr)
                
                # Revert to previous provider (don't save invalid choice)
                self.tts_provider = create_provider(current_provider)
                dropdown.set_selected(0 if current_provider == "piper" else 1)
                self.menu_popover.popdown()
                return
            
            # Save preference only after successful validation
            set_voice_provider(new_provider)
            
            # Reset playback state and restart
            self._playback_started = False
            self._current_progress = 0.0
            self.progress_bar.set_fraction(0.0)
            
            # Restart speech with new provider
            threading.Thread(target=self.speak_text, daemon=True).start()
            
            # Restart timers
            GLib.timeout_add(100, self.update_status)
            GLib.timeout_add(75, self.animate_waveform)
            GLib.timeout_add(33, self.update_progress_smooth)
        
        # Close the popover
        self.menu_popover.popdown()
    
    def on_log_level_changed(self, dropdown, param):
        """Handle log level selection change."""
        selected = dropdown.get_selected()
        level_names = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        new_level = level_names[selected] if selected < len(level_names) else "INFO"
        
        current_level = get_log_level()
        if new_level != current_level:
            # Save and apply new log level
            set_log_level(new_level)
            reconfigure_logging(new_level)
            logger.info(f"Log level changed to {new_level}")
        
        # Close the popover
        self.menu_popover.popdown()
    
    def update_status(self):
        """Update UI based on playback status."""
        is_playing = self.tts_provider.is_playing()
        is_paused = self.tts_provider.is_paused()
        
        if is_playing or is_paused:
            self._playback_started = True
        
        if is_playing:
            self.pause_button.set_label("⏸")
        elif is_paused:
            self.pause_button.set_label("▶")
        elif self._playback_started:
            # Playback finished - close window
            GLib.idle_add(self.close_window)
            return False
        
        return True
    
    def update_progress_smooth(self):
        """Update progress bar smoothly with interpolation."""
        target_progress = self.tts_provider.get_progress()
        
        # Smooth interpolation (0.15 factor balances smoothness vs responsiveness)
        self._current_progress += (target_progress - self._current_progress) * 0.15
        self.progress_bar.set_fraction(self._current_progress)
        
        # Stop timer when playback is complete
        if self._playback_started and not self.tts_provider.is_playing() and not self.tts_provider.is_paused():
            return False
        
        return True
    
    def animate_waveform(self):
        """Animate the waveform bars using real-time frequency analysis."""
        # Stop animation if playback has finished
        if self._playback_started and not self.tts_provider.is_playing() and not self.tts_provider.is_paused():
            return False
        
        min_height = 8
        max_height = 24
        
        # Try real-time frequency analysis when playing
        if self.tts_provider.is_playing():
            bands = self.tts_provider.get_frequency_bands(10)
            
            # Use frequency data if available (provider supports it and has real audio data)
            if max(bands) > 0.01:
                for i, (bar, _) in enumerate(self.wave_bars):
                    animated_height = int(min_height + bands[i] * (max_height - min_height))
                    bar.set_size_request(3, animated_height)
                return True
        
        # Fall back to sine wave animation (when not playing or no frequency data)
        self._wave_offset = (self._wave_offset + 1) % 100
        
        for i, (bar, _) in enumerate(self.wave_bars):
            phase = (self._wave_offset + i * 10) / 100.0 * 2 * math.pi
            wave_factor = (math.sin(phase) + 1) / 2  # Normalize to 0-1
            animated_height = int(min_height + wave_factor * (max_height - min_height))
            bar.set_size_request(3, animated_height)
        
        return True
    
    def _stop_audio_if_playing(self):
        """Stop audio if currently playing or paused."""
        try:
            if self.tts_provider.is_playing() or self.tts_provider.is_paused():
                self.tts_provider.stop()
        except Exception:
            pass  # Ignore errors during cleanup
    
    def on_close_request(self, window):
        """Handle window close request."""
        self._stop_audio_if_playing()
        return False  # Allow window to close
    
    def close_window(self):
        """Close the window (called from main thread via GLib.idle_add)."""
        self._stop_audio_if_playing()
        self.close()
        return False  # Return False to ensure GLib.idle_add doesn't repeat


class SpeakingApp(Gtk.Application):
    def __init__(self, text, tts_provider: TTSProvider):
        super().__init__(application_id="com.grafl.speaking")
        self.text = text
        self.tts_provider = tts_provider
        self.window = None
    
    def do_activate(self):
        """Create and show the window (only once)."""
        if not self.window:
            self.window = SpeakingWindow(self, self.text, self.tts_provider)
            self.window.present()


def main():
    # Initialize logging from config
    log_level = get_log_level()
    setup_logging(log_level)
    logger.info("Starting grafl")
    logger.debug(f"Log level: {log_level}")
    
    # Text provided as argument or read from stdin
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    
    if not text.strip():
        logger.error("No text to speak")
        print("No text to speak", file=sys.stderr)
        sys.exit(1)
    
    # Create and validate TTS provider (with automatic fallback)
    tts_provider, error = create_validated_provider()
    if error:
        print(error, file=sys.stderr)
        sys.exit(1)
    
    app = SpeakingApp(text.strip(), tts_provider)
    app.run(None)


if __name__ == "__main__":
    main()

