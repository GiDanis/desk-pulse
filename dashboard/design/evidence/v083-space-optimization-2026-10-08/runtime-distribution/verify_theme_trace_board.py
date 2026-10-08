"""A0.3 compatibility lane: exact existing notification workload, optional trace.

Run fresh processes in three alternating off/on pairs for each font profile.
Report raw data and explicit residual targets; a p95 from successful requests
cannot hide a timeout/overflow. Use EGLFS exclusively while kiosk is stopped.
"""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('verify_notifications_board.py')), run_name='__main__')
