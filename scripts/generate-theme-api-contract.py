#!/usr/bin/env python3
"""Generate/check public theme contracts, independently from runtime availability."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
from theme_api_tools import main

if __name__ == '__main__':
    sys.exit(main())
