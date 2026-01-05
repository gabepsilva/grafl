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

# Import TTS interface
from grafl.providers.base import TTSProvider, TTSError
from grafl.providers.piper import PiperTTSProvider

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
    # Text provided as argument or read from stdin
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    
    if not text.strip():
        print("No text to speak", file=sys.stderr)
        sys.exit(1)
    
    # Create and validate TTS provider (currently only Piper)
    tts_provider = PiperTTSProvider()
    if not tts_provider.validate_config():
        print(f"TTS provider '{tts_provider.name}' is not properly configured", 
              file=sys.stderr)
        sys.exit(1)
    
    app = SpeakingApp(text.strip(), tts_provider)
    app.run(None)


if __name__ == "__main__":
    main()

