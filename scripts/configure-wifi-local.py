#!/usr/bin/env python3
"""Collect Wi-Fi credentials locally, without including them in tool output."""
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

# SSID can be passed as argument or queried interactively
ssid = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('WIFI_SSID', '')

if not ssid:
    if shutil.which('zenity') and os.environ.get('DISPLAY'):
        res = subprocess.run(['zenity', '--entry', '--title=Wi-Fi Orange Pi',
            '--text=Inserisci il nome della rete Wi-Fi (SSID):', '--width=460'],
            capture_output=True, text=True)
        if res.returncode or not res.stdout.strip():
            raise SystemExit('Configurazione annullata; nessun SSID specificato.')
        ssid = res.stdout.strip()
    else:
        ssid = input('Nome rete Wi-Fi (SSID): ').strip()

if not ssid:
    raise SystemExit('SSID non valido.')

password = ''
if shutil.which('zenity') and os.environ.get('DISPLAY'):
    result = subprocess.run(['zenity', '--entry', '--hide-text', '--title=Wi-Fi Orange Pi',
        f'--text=Password per {ssid}\nLa password resta sul PC e sulla SD.',
        '--width=460'], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit('Configurazione annullata; nessuna credenziale salvata.')
    password = result.stdout.rstrip('\n')
else:
    password = getpass.getpass(f'Password per {ssid}: ')

if not 1 <= len(ssid.encode()) <= 32 or not 8 <= len(password) <= 63:
    raise SystemExit('Nome rete o lunghezza password non conformi agli standard Wi-Fi WPA2 (8-63 caratteri).')

fd, name = tempfile.mkstemp(prefix='deskpulse-wifi-', suffix='.json', dir=os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
try:
    with os.fdopen(fd, 'w') as f:
        json.dump({'ssid': ssid, 'password': password}, f)
    prepare_script = Path(__file__).resolve().parent / 'prepare-headless.py'
    target_root = sys.argv[2] if len(sys.argv) > 2 else ''
    cmd = ['sudo', sys.executable, str(prepare_script), name]
    if target_root:
        cmd.append(target_root)
    result = subprocess.run(cmd)
    raise SystemExit(result.returncode)
finally:
    Path(name).unlink(missing_ok=True)
