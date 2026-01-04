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

# Import TTS interface
from tts_interface import TTSProvider, TTSError
from tts_piper import PiperTTSProvider

class SpeakingWindow(Gtk.ApplicationWindow):
    def __init__(self, app, text, tts_provider: TTSProvider):
        super().__init__(application=app)
        self.text = text
        self.tts_provider = tts_provider
        
        # Window configuration - minimal floating style
        self.set_title("Speaking...")
        self.set_default_size(250, 80)
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
        """)
        
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Create UI - simple centered label
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_top(25)
        box.set_margin_bottom(25)
        box.set_margin_start(30)
        box.set_margin_end(30)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        
        # Status label - simple and clean
        self.label = Gtk.Label()
        self.label.set_markup("<span size='large'>🔊 Speaking...</span>")
        self.label.set_halign(Gtk.Align.CENTER)
        box.append(self.label)
        
        self.set_child(box)
        
        # Start speaking in a separate thread
        threading.Thread(target=self.speak_text, daemon=True).start()
    
    def speak_text(self):
        """Use the configured TTS provider to speak the text."""
        try:
            self.tts_provider.speak(self.text)
        except TTSError as e:
            print(f"TTS Error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error during speech: {e}", file=sys.stderr)
        finally:
            GLib.idle_add(self.close_window)
    
    def close_window(self):
        """Close the window (called from main thread)."""
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

