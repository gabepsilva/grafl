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

# Import TTS interface
from tts_interface import TTSProvider, TTSError
from tts_piper import PiperTTSProvider

class SpeakingWindow(Gtk.ApplicationWindow):
    def __init__(self, app, text, tts_provider: TTSProvider):
        super().__init__(application=app)
        self.text = text
        self.tts_provider = tts_provider
        self._playback_started = False
        
        # Connect close handler
        self.connect("close-request", self.on_close_request)
        
        # Window configuration - minimal floating style
        self.set_title("Speaking...")
        self.set_resizable(False)
        
        # Make it borderless and float on top
        self.set_decorated(False)
        
        # Apply CSS for semi-transparent background
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background-color: rgba(0, 0, 0, 0.85);
                border-radius: 12px;
            }
            label {
                color: white;
                font-size: 16px;
            }
            button {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                padding: 8px 16px;
            }
            button:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Create UI - centered label and control buttons
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(30)
        box.set_margin_end(30)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        
        # Status label - simple and clean
        self.label = Gtk.Label()
        self.label.set_markup("<span size='large'>🔊 Speaking...</span>")
        self.label.set_halign(Gtk.Align.CENTER)
        box.append(self.label)
        
        # Control buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        
        # Skip backward button
        self.skip_backward_button = Gtk.Button(label="⏪ -5s")
        self.skip_backward_button.connect("clicked", self.on_skip_backward_clicked)
        button_box.append(self.skip_backward_button)
        
        # Pause button
        self.pause_button = Gtk.Button(label="⏸ Pause")
        self.pause_button.connect("clicked", self.on_pause_clicked)
        button_box.append(self.pause_button)
        
        # Resume button (initially hidden)
        self.resume_button = Gtk.Button(label="▶ Resume")
        self.resume_button.connect("clicked", self.on_resume_clicked)
        self.resume_button.set_visible(False)
        button_box.append(self.resume_button)
        
        # Skip forward button
        self.skip_forward_button = Gtk.Button(label="⏩ +5s")
        self.skip_forward_button.connect("clicked", self.on_skip_forward_clicked)
        button_box.append(self.skip_forward_button)
        
        # Stop button
        self.stop_button = Gtk.Button(label="⏹ Stop")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        button_box.append(self.stop_button)
        
        box.append(button_box)
        self.set_child(box)
        
        # Update window size for buttons (wider to accommodate skip buttons)
        self.set_default_size(400, 120)
        
        # Start status update timer
        GLib.timeout_add(100, self.update_status)
        
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
        """Handle pause button click."""
        self._handle_tts_action("pausing", self.tts_provider.pause)
    
    def on_resume_clicked(self, button):
        """Handle resume button click."""
        self._handle_tts_action("resuming", self.tts_provider.resume)
    
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
            self.label.set_markup("<span size='large'>🔊 Speaking...</span>")
            self.pause_button.set_visible(True)
            self.resume_button.set_visible(False)
            return True
        
        if is_paused:
            self.label.set_markup("<span size='large'>⏸ Paused</span>")
            self.pause_button.set_visible(False)
            self.resume_button.set_visible(True)
            return True
        
        # Not playing and not paused
        if self._playback_started:
            # Playback has started and now finished - close window
            GLib.idle_add(self.close_window)
            return False  # Stop timer
        
        # Playback hasn't started yet - keep waiting
        self.label.set_markup("<span size='large'>🔊 Preparing...</span>")
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

