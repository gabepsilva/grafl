#!/usr/bin/env python3
"""
Script to get selected text from clipboard or X selection on Linux.
Prints the selected text to stdout.
"""

import subprocess
import sys
import os


def get_x_selection_xsel():
    """Get text from X PRIMARY selection using xsel."""
    try:
        result = subprocess.run(
            ['xsel', '-p', '-o'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_clipboard_xsel():
    """Get text from clipboard using xsel."""
    try:
        result = subprocess.run(
            ['xsel', '-b', '-o'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_x_selection_xclip():
    """Get text from X PRIMARY selection using xclip."""
    try:
        result = subprocess.run(
            ['xclip', '-selection', 'primary', '-o'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_clipboard_xclip():
    """Get text from clipboard using xclip."""
    try:
        result = subprocess.run(
            ['xclip', '-selection', 'clipboard', '-o'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_wayland_clipboard():
    """Get text from Wayland clipboard using wl-paste."""
    try:
        result = subprocess.run(
            ['wl-paste', '-p'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    try:
        result = subprocess.run(
            ['wl-paste'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def main():
    text = None
    method_used = None
    
    # Try different methods based on availability
    # Try xsel first (most lightweight)
    text = get_x_selection_xsel()
    if text:
        method_used = "xsel primary"
    
    if not text:
        text = get_clipboard_xsel()
        if text:
            method_used = "xsel clipboard"
    
    # Try xclip
    if not text:
        text = get_x_selection_xclip()
        if text:
            method_used = "xclip primary"
    
    if not text:
        text = get_clipboard_xclip()
        if text:
            method_used = "xclip clipboard"
    
    # Try Wayland
    if not text:
        text = get_wayland_clipboard()
        if text:
            method_used = "wl-paste"
    
    # Debug: write raw text to file
    try:
        with open('/tmp/readlog.txt', 'wb') as f:
            if text:
                f.write(f"Method: {method_used}\n".encode('utf-8'))
                f.write(f"Length: {len(text)} chars\n".encode('utf-8'))
                f.write(f"Repr: {repr(text)}\n".encode('utf-8'))
                f.write(b"Raw bytes:\n")
                f.write(text.encode('utf-8'))
            else:
                f.write(b"No text captured\n")
    except Exception as e:
        print(f"Debug write failed: {e}", file=sys.stderr)
    
    # Print the text
    if text:
        print(text, end='')
    else:
        print("No selected text found. Make sure xsel, xclip, or wl-paste is installed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

