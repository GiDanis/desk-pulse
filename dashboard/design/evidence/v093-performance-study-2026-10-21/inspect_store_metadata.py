"""Read-only SQL metadata; no pilot payloads, weights, names or migrations."""
import datetime
import json
from pathlib import Path
import sqlite3
import subprocess

path = Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game/game.sqlite')
r = {'capturedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'scope': 'Consistent read-only metadata transaction; no checkpoint or application imports'}
try:
    with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=3) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        r['counts'] = {table: db.execute('SELECT count(*) FROM '+table).fetchone()[0]
                       for table in ('drivers', 'sessions', 'history', 'timed_qualifications', 'timing_laps')}
        r['sessionGroups'] = [dict(row) for row in db.execute(
            'SELECT mode,status,count(*) AS count,sum(length(payload)) AS payloadBytes FROM sessions GROUP BY mode,status')]
        r['eventGroups'] = [dict(row) for row in db.execute(
            'SELECT kind,count(*) AS count,sum(length(payload)) AS payloadBytes FROM history GROUP BY kind')]
        r['curricula'] = [dict(number=row['number'], bytes=len(row['curriculum'] or ''),
                                evaluations=len(json.loads(row['curriculum'] or '{}').get('evaluations', [])))
                            for row in db.execute('SELECT number,curriculum FROM drivers ORDER BY number')]
        r['plans'] = {'sessions': [tuple(row) for row in db.execute('EXPLAIN QUERY PLAN SELECT * FROM sessions ORDER BY created DESC')],
                      'events': [tuple(row) for row in db.execute("EXPLAIN QUERY PLAN SELECT * FROM history WHERE driver=? AND (? OR track_id=?) AND kind IN ('profile','reset','evaluation') ORDER BY id DESC", ('study', 1, 'oval-1'))]}
        db.rollback()
except (OSError, sqlite3.Error, ValueError) as error:
    r['unavailable'] = str(error)
r['service'] = subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard.service',
    '-p', 'MainPID', '-p', 'ActiveState', '-p', 'NRestarts']).decode()
print(json.dumps(r, indent=2))
