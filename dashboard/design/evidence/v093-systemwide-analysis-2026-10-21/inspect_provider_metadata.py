"""Read-only event-store aggregates; no user content or provider requests."""
import datetime
import json
from pathlib import Path
import sqlite3
import subprocess
import time

r = dict(capturedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(), sqliteVersion=sqlite3.sqlite_version)
path = Path('/var/lib/smartpc-dashboard/events.sqlite3')
try:
    with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=3) as db:
        db.execute('BEGIN')
        now = time.time()
        r['eventStore'] = dict(bytes=path.stat().st_size,
            rows=db.execute('SELECT count(*) FROM events').fetchone()[0],
            activeRows=db.execute('SELECT count(*) FROM events WHERE cancelled=0 AND expires_at>?', (now,)).fetchone()[0],
            payloadBytes=db.execute('SELECT coalesce(sum(length(payload)),0) FROM events').fetchone()[0],
            sources=db.execute('SELECT count(DISTINCT source) FROM events').fetchone()[0],
            journalMode=db.execute('PRAGMA journal_mode').fetchone()[0])
        db.rollback()
except (OSError, sqlite3.Error) as error:
    r['eventStore'] = {'unavailable': str(error)}
r['service'] = subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard.service', '-p', 'MainPID',
    '-p', 'ActiveState', '-p', 'NRestarts']).decode()
print(json.dumps(r, indent=2))
