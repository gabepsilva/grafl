#!/usr/bin/env python3
"""
grafl - Text-to-Speech application entry point.
"""

import sys
from pathlib import Path

# Add src to path so we can find the grafl package
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR / "src"))

from grafl.cli import main

if __name__ == "__main__":
    sys.exit(main())

