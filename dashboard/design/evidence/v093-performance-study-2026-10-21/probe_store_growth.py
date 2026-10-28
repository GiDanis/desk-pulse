"""Headless synthetic DB growth and nominal progress sizes, always private."""
import argparse
from copy import deepcopy
import datetime
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.source.resolve()))
os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
os.nice(10)


def measure(fn):
    fn()
    values = []
    for _ in range(8):
        before = time.perf_counter_ns()
        fn()
        values.append((time.perf_counter_ns()-before)/1e6)
    return dict(n=8, p50Ms=statistics.median(values), maxMs=max(values), samplesMs=values)


r = dict(capturedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         scope='Synthetic private SQL rows; no real pilot, no learning/display/provider',
         source=str(a.source.resolve()), python=sys.version)
with tempfile.TemporaryDirectory(prefix='smartpc-v093-growth-') as temp:
    base = Path(temp)
    for key in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME'):
        os.environ[key] = str(base/key)
        (base/key).mkdir()
    os.environ['SMARTPC_GAME_STORE'] = str(base/'game')
    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication([])
    app.setOrganizationName('SmartPCStudy')
    app.setApplicationName('V093Growth')
    from game import GameService
    from game_dossier import dossier
    s = GameService(base/'game')
    driver = next(d for d in s._drivers if d['id'] == s._selected)
    proof = dict(round=1, phase='pace', rewardVersion='synthetic',
                 candidate=dict(valid=3, total=3, median=22., best=21.8,
                                results=[dict(reason='success', goalMeters=100.) for _ in range(3)]))
    r['nominalProgress'] = []
    for count in (0, 20, 40):
        driver['curriculum'] = dict(phase='pace', evaluations=[dict(deepcopy(proof), round=i+1) for i in range(count)])
        r['nominalProgress'].append(dict(evaluations=count, wholePythonSnapshot=measure(lambda: s.snapshot)))
    s._refresh()
    payload = json.dumps(dict(participants=[], diagnostics=[dict(i=i, values=list(range(12))) for i in range(16)]))
    r['syntheticSessionPayloadBytes'] = len(payload.encode())
    r['storeGrowth'] = []
    for count in (0, 100, 1000):
        with s._store.connect() as db:
            db.execute('DELETE FROM sessions')
            db.execute("DELETE FROM history WHERE kind='evaluation'")
            db.executemany('INSERT INTO sessions VALUES(?,?,?,?,?,?)',
                [(f'study-{i}', 'qualifica', 'complete', '2026-10-21T12:00:00+00:00',
                  '2026-10-21T12:00:00+00:00', payload) for i in range(count)])
            db.executemany('INSERT INTO history(driver,kind,created,payload,track_id) VALUES(?,?,?,?,?)',
                [(driver['id'], 'evaluation', '2026-10-21T12:00:00+00:00', json.dumps(proof), 'oval-1')
                 for _ in range(count)])
        r['storeGrowth'].append(dict(sessions=count, evaluationEvents=count,
            storeSessions=measure(lambda: s._store.sessions(complete=False)),
            dossier=measure(lambda: dossier(s._store, driver['id'], driver=driver)),
            wholeRefresh=measure(s._refresh)))
    s.close()
print(json.dumps(r, indent=2))
