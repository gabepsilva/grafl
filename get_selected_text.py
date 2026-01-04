#!/usr/bin/env python3
"""
Script to get selected text from clipboard or X selection on Linux.
Prints the selected text to stdout.
"""

import subprocess
import sys


def run_clipboard_command(command, timeout=2):
    """
    Run a clipboard command and return text if successful.
    
    Args:
        command: List of command arguments to execute
        timeout: Maximum seconds to wait for command completion
        
    Returns:
        str: Text from clipboard/selection, or None if unavailable
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def main():
    """
    Try multiple clipboard/selection tools in priority order.
    Exits with code 0 on success, 1 on failure.
    """
    # Try methods in priority order
    # Primary selections are preferred over clipboard for quick text selection
    methods = [
        ['xsel', '-p', '-o'],           # xsel primary selection
        ['xsel', '-b', '-o'],           # xsel clipboard
        ['xclip', '-selection', 'primary', '-o'],    # xclip primary
        ['xclip', '-selection', 'clipboard', '-o'],  # xclip clipboard
        ['wl-paste', '-p'],             # wl-paste primary (Wayland)
        ['wl-paste'],                   # wl-paste clipboard (Wayland)
    ]
    
    for command in methods:
        text = run_clipboard_command(command)
        if text:
            print(text, end='')
            return 0
    
    # No method succeeded
    print("No selected text found. Make sure xsel, xclip, or wl-paste is installed.", 
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

