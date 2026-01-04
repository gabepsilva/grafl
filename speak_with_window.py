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
from tts_interface import TTSProvider, TTSError
from tts_piper import PiperTTSProvider

class SpeakingWindow(Gtk.ApplicationWindow):
    def __init__(self, app, text, tts_provider: TTSProvider):
        super().__init__(application=app)
        self.text = text
        self.tts_provider = tts_provider
        self._playback_started = False
        self._wave_offset = 0  # For waveform animation
        
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
        self.wave_bars = []
        wave_heights = [8, 16, 24, 20, 12, 18, 14, 22, 10, 16]
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
        self.set_child(main_box)
        
        # Compact window size for bar design
        self.set_default_size(380, 60)
        
        # Start status update timer
        GLib.timeout_add(100, self.update_status)
        
        # Start waveform animation timer
        GLib.timeout_add(75, self.animate_waveform)
        
        # Start speaking in a separate thread
        threading.Thread(target=self.speak_text, daemon=True).start()
    
    def speak_text(self):
        """Use the configured TTS provider to speak the text."""
        try:
            self.tts_provider.speak(self.text)
            # Give playback time to start
            time.sleep(0.2)
            # Wait for playback to complete
            while self.tts_provider.is_playing() or self.tts_provider.is_paused():
                time.sleep(0.1)
        except TTSError as e:
            print(f"TTS Error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error during speech: {e}", file=sys.stderr)
        # Don't close here - let update_status handle it
    
    def _handle_tts_action(self, action_name: str, action_func):
        """Common error handling for TTS actions."""
        try:
            action_func()
        except TTSError as e:
            print(f"Error {action_name}: {e}", file=sys.stderr)
    
    def on_pause_clicked(self, button):
        """Handle pause/resume button click (toggle)."""
        if self.tts_provider.is_paused():
            self._handle_tts_action("resuming", self.tts_provider.resume)
        else:
            self._handle_tts_action("pausing", self.tts_provider.pause)
    
    def on_skip_backward_clicked(self, button):
        """Handle skip backward button click."""
        self._handle_tts_action("skipping backward", lambda: self.tts_provider.skip_backward(5.0))
    
    def on_skip_forward_clicked(self, button):
        """Handle skip forward button click."""
        self._handle_tts_action("skipping forward", lambda: self.tts_provider.skip_forward(5.0))
    
    def on_stop_clicked(self, button):
        """Handle stop button click."""
        self._handle_tts_action("stopping", self.tts_provider.stop)
        self.close()
    
    def update_status(self):
        """Update UI based on playback status."""
        is_playing = self.tts_provider.is_playing()
        is_paused = self.tts_provider.is_paused()
        
        # Track if playback has started
        if is_playing or is_paused:
            self._playback_started = True
        
        if is_playing:
            self.pause_button.set_label("⏸")
            return True
        
        if is_paused:
            self.pause_button.set_label("▶")
            return True
        
        # Not playing and not paused
        if self._playback_started:
            # Playback has started and now finished - close window
            GLib.idle_add(self.close_window)
            return False  # Stop timer
        
        # Playback hasn't started yet - keep waiting
        return True
    
    def animate_waveform(self):
        """Animate the waveform bars using real-time frequency analysis."""
        # Only stop animation if playback has finished
        if self._playback_started and not self.tts_provider.is_playing() and not self.tts_provider.is_paused():
            # Playback finished - stop animation
            return False
        
        # Try real-time frequency analysis when playing
        use_sine_fallback = True
        if self.tts_provider.is_playing():
            # Get frequency bands from audio (WinAmp-style spectrum analyzer!)
            bands = self.tts_provider.get_frequency_bands(10)
            
            # Check if provider actually supports frequency analysis
            # (if all bands are zero or very low, fall back to sine wave)
            if max(bands) > 0.01:  # Has real audio data
                use_sine_fallback = False
                for i, (bar, base_height) in enumerate(self.wave_bars):
                    # Map frequency band to bar height (8-24 px range)
                    min_height = 8
                    max_height = 24
                    animated_height = int(min_height + bands[i] * (max_height - min_height))
                    bar.set_size_request(3, animated_height)
        
        # Fall back to sine wave animation if:
        # - Not playing/paused, OR
        # - Provider doesn't support frequency analysis
        if use_sine_fallback:
            self._wave_offset = (self._wave_offset + 1) % 100
            
            for i, (bar, base_height) in enumerate(self.wave_bars):
                # Calculate animated height using sine wave
                phase = (self._wave_offset + i * 10) / 100.0 * 2 * math.pi
                wave_factor = (math.sin(phase) + 1) / 2  # 0 to 1
                min_height = 8
                max_height = 24
                animated_height = int(min_height + wave_factor * (max_height - min_height))
                bar.set_size_request(3, animated_height)
        
        return True
    
    def _stop_audio_if_playing(self):
        """Stop audio if currently playing or paused."""
        try:
            if self.tts_provider.is_playing() or self.tts_provider.is_paused():
                self.tts_provider.stop()
        except Exception:
            pass  # Ignore errors when stopping
    
    def on_close_request(self, window):
        """Handle window close request."""
        self._stop_audio_if_playing()
        return False  # Allow window to close
    
    def close_window(self):
        """Close the window (called from main thread)."""
        self._stop_audio_if_playing()
        self.close()
        return False


class SpeakingApp(Gtk.Application):
    def __init__(self, text, tts_provider: TTSProvider):
        super().__init__(application_id="com.grafl.speaking")
        self.text = text
        self.tts_provider = tts_provider
        self.window = None
    
    def do_activate(self):
        """Create and show the window."""
        if self.window:
            return
        self.window = SpeakingWindow(self, self.text, self.tts_provider)
        self.window.present()


def main():
    if len(sys.argv) > 1:
        # Text provided as argument
        text = " ".join(sys.argv[1:])
    else:
        # Read from stdin
        text = sys.stdin.read()
    
    if not text.strip():
        print("No text to speak", file=sys.stderr)
        sys.exit(1)
    
    # Create TTS provider (currently only Piper)
    # In the future, you can add logic to select different providers
    tts_provider = PiperTTSProvider()
    
    # Validate provider
    if not tts_provider.validate_config():
        print(f"TTS provider '{tts_provider.name}' is not properly configured", 
              file=sys.stderr)
        sys.exit(1)
    
    app = SpeakingApp(text.strip(), tts_provider)
    app.run(None)


if __name__ == "__main__":
    main()

