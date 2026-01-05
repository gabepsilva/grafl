#!/usr/bin/env python3
"""
Command-line interface for grafl TTS application.
"""

import sys
import os
from pathlib import Path

from grafl.utils.clipboard import run_clipboard_command
from grafl.ui.window import SpeakingApp, main as window_main, create_validated_provider
from grafl.utils.config import get_log_level
from grafl.utils.logging import setup_logging, get_logger


def speak_selection():
    """
    Speak selected text using TTS with GTK4 window.
    This can be called directly or via keybindings.
    """
    # Initialize logging from config
    log_level = get_log_level()
    setup_logging(log_level)
    logger = get_logger(__name__)
    logger.info("Starting grafl speak-selection")
    logger.debug(f"Log level: {log_level}")
    
    # Prefer Wayland for proper CSS transparency (must be set before GTK imports)
    if os.environ.get('WAYLAND_DISPLAY'):
        os.environ['GDK_BACKEND'] = 'wayland'
        logger.debug("Using Wayland backend")
    elif os.environ.get('DISPLAY') and not os.environ.get('GDK_BACKEND'):
        logger.warning("Running on X11. Window transparency may not work correctly.")
        print("Warning: Running on X11. Window transparency may not work correctly.", 
              file=sys.stderr)
    
    # Try multiple clipboard/selection tools to get selected text
    methods = [
        ['xsel', '-p', '-o'],           # xsel primary
        ['xsel', '-b', '-o'],           # xsel clipboard
        ['xclip', '-selection', 'primary', '-o'],
        ['xclip', '-selection', 'clipboard', '-o'],
        ['wl-paste', '-p'],             # Wayland primary
        ['wl-paste'],                   # Wayland clipboard
    ]
    
    text = None
    for command in methods:
        text = run_clipboard_command(command)
        if text:
            break
    
    if not text or not text.strip():
        print("No selected text found. Make sure xsel, xclip, or wl-paste is installed.", 
              file=sys.stderr)
        return 1
    
    # Create and validate TTS provider (with automatic fallback)
    tts_provider, error = create_validated_provider()
    if error:
        print(error, file=sys.stderr)
        return 1
    
    # Run GTK app with selected text
    app = SpeakingApp(text.strip(), tts_provider)
    app.run(None)
    return 0


def speak_text():
    """
    Speak text from stdin or command-line arguments.
    """
    # Text provided as argument or read from stdin
    text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else sys.stdin.read()
    
    if not text.strip():
        print("No text to speak", file=sys.stderr)
        return 1
    
    # Call the main window function with the text
    sys.argv = [sys.argv[0], text.strip()]  # Simulate original argv
    return window_main() or 0


def get_clipboard():
    """
    Get and print selected text from clipboard.
    """
    from grafl.utils.clipboard import main as clipboard_main
    return clipboard_main()


def print_help():
    """Print usage information."""
    print("""
grafl - Text-to-Speech application

Usage:
    grafl speak-selection    Speak currently selected text
    grafl speak [TEXT]       Speak text from arguments or stdin
    grafl get-clipboard      Get selected text and print to stdout
    grafl help               Show this help message

Examples:
    grafl speak-selection
    grafl speak "Hello, world!"
    echo "Hello, world!" | grafl speak
    grafl get-clipboard
""")
    return 0


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Error: No command specified", file=sys.stderr)
        print_help()
        return 1
    
    command = sys.argv[1]
    
    if command == "speak-selection":
        return speak_selection()
    elif command == "speak":
        return speak_text()
    elif command == "get-clipboard":
        return get_clipboard()
    elif command in ("help", "--help", "-h"):
        return print_help()
    else:
        print(f"Error: Unknown command '{command}'", file=sys.stderr)
        print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

