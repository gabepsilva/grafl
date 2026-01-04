#!/usr/bin/env python3
"""
GTK4 floating window that displays while text is being spoken.
Integrates with piper TTS to show reading status.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import sys
import threading
import os

class SpeakingWindow(Gtk.ApplicationWindow):
    def __init__(self, app, text):
        super().__init__(application=app)
        self.text = text
        self.speaking_process = None
        
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
        """Run piper to speak the text."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        piper_bin = os.path.join(script_dir, "venv", "bin", "piper")
        model_path = os.path.join(script_dir, "en_US-lessac-medium")
        
        try:
            # Create piper process
            piper_process = subprocess.Popen(
                [piper_bin, "--model", model_path, "--output_file", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Create paplay process
            paplay_process = subprocess.Popen(
                ["paplay", "--raw", "--rate=22050", "--format=s16le", "--channels=1"],
                stdin=piper_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Send text to piper
            piper_process.stdin.write(self.text.encode('utf-8'))
            piper_process.stdin.close()
            
            # Allow piper's output to flow to paplay
            piper_process.stdout.close()
            
            # Wait for both processes to complete
            piper_process.wait()
            paplay_process.wait()
            
        except Exception as e:
            print(f"Error during speech: {e}", file=sys.stderr)
        finally:
            # Close the window when done
            GLib.idle_add(self.close_window)
    
    def close_window(self):
        """Close the window (called from main thread)."""
        self.close()
        return False


class SpeakingApp(Gtk.Application):
    def __init__(self, text):
        super().__init__(application_id="com.grafl.speaking")
        self.text = text
        self.window = None
    
    def do_activate(self):
        """Create and show the window."""
        if not self.window:
            self.window = SpeakingWindow(self, self.text)
            self.window.present()


def main():
    if len(sys.argv) > 1:
        # Text provided as argument
        text = " ".join(sys.argv[1:])
    else:
        # Read from stdin
        text = sys.stdin.read()
    
    if not text or not text.strip():
        print("No text to speak", file=sys.stderr)
        sys.exit(1)
    
    app = SpeakingApp(text.strip())
    app.run(None)


if __name__ == "__main__":
    main()

