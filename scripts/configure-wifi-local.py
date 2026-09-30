#!/usr/bin/env python3
"""Collect Wi-Fi credentials locally, without including them in tool output."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ssid = 'iliadbox-2F063E-2.4GZz'
result = subprocess.run(['zenity', '--entry', '--hide-text', '--title=Wi-Fi Orange Pi',
    '--text=Password per '+ssid+'\nLa password resta sul PC e sulla SD, non viene inviata in chat.',
    '--width=460'], capture_output=True, text=True)
if result.returncode:
    raise SystemExit('Configurazione annullata; nessuna credenziale salvata.')
values = [ssid, result.stdout.rstrip('\n')]
if len(values) != 2 or not 1 <= len(values[0].encode()) <= 32 or not 8 <= len(values[1]) <= 63:
    raise SystemExit('Nome rete o lunghezza password non validi; configurazione non applicata.')
fd, name = tempfile.mkstemp(prefix='smartpc-wifi-', suffix='.json', dir=os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
try:
    with os.fdopen(fd, 'w') as f:
        json.dump({'ssid': values[0], 'password': values[1]}, f)
    result = subprocess.run(['sudo', '-n', '/usr/bin/python3',
        '/home/giuseppe/Documenti/Workspace/SmartPC/scripts/prepare-headless.py', name])
    raise SystemExit(result.returncode)
finally:
    Path(name).unlink(missing_ok=True)
