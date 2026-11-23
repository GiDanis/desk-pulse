#!/usr/bin/env python3
"""Run the isolated real-Main aquarium benchmark; never installs or stops a service."""
from pathlib import Path
import runpy
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"dashboard"))
runpy.run_path(str(Path(__file__).resolve().parents[1]/'dashboard/check_aquarium_ui.py'),run_name='__main__')
