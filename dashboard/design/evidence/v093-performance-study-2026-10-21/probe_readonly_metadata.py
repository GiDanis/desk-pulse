"""Time current metadata readers through a read-only consistent SQLite snapshot.

No GameStore constructor on the real DB, no checkpoints loaded for residuals,
no public payloads in output, no training, display, or provider operations.
"""
import cProfile
from contextlib import contextmanager
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import pstats
import sqlite3
import statistics
import sys
import tempfile
import time

source = Path('/opt/smartpc/dashboard')
store_root = Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game')
sys.path.insert(0, str(source))
os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
os.nice(10)


def measure(fn):
    fn()
    values = []
    for _ in range(5):
        before = time.perf_counter_ns()
        fn()
        values.append((time.perf_counter_ns()-before)/1e6)
    return dict(n=5, p50Ms=statistics.median(values), maxMs=max(values), samplesMs=values)


r = dict(capturedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         scope='Current metadata readers headless through one SQLite mode=ro transaction; no GUI conversion or FPS',
         sourceHashes={name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (
             'game.py', 'game_store.py', 'game_dossier.py', 'game_results.py')})
with tempfile.TemporaryDirectory(prefix='smartpc-v093-readers-') as temp:
    base = Path(temp)
    for key in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME'):
        os.environ[key] = str(base/key)
        (base/key).mkdir()
    os.environ['SMARTPC_GAME_STORE'] = str(base/'game')
    from PySide6.QtCore import QCoreApplication, qVersion
    app = QCoreApplication([])
    app.setOrganizationName('SmartPCStudy')
    app.setApplicationName('V093ReadOnlyReaders')
    from game_store import GameStore
    from game import GameService
    from game_dossier import dossier
    from game_results import exercise
    db = sqlite3.connect((store_root/'game.sqlite').as_uri()+'?mode=ro', uri=True, timeout=3)
    db.row_factory = sqlite3.Row
    db.execute('BEGIN')
    class ReadOnlyStore(GameStore):
        def __init__(self):
            self.root = store_root
            self.policies = store_root/'policies'
            self.track_id = 'oval-1'
        @contextmanager
        def connect(self):
            yield db
    s = GameService(base/'game')
    try:
        store = ReadOnlyStore()
        s._store = store
        r['driversRead'] = measure(store.drivers)
        drivers = store.drivers()
        r['rows'] = []
        for driver in drivers:
            if driver['number'] == 1:
                continue
            s._selected = driver['id']
            s._refresh()
            r['rows'].append(dict(number=driver['number'],
                evaluationCount=len((driver.get('curriculum') or {}).get('evaluations', [])),
                metadataRefresh=measure(s._refresh),
                wholePythonSnapshot=measure(lambda: s.snapshot),
                selectedDossier=measure(lambda: dossier(store, driver['id'], driver=driver))))
        s._selected = drivers[1]['id']
        probe = cProfile.Profile()
        probe.runcall(s._refresh)
        stream = io.StringIO()
        pstats.Stats(probe, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(20)
        r['refreshProfile'] = stream.getvalue()
        r['qt'] = qVersion()
    finally:
        s.close()
        db.rollback()
        db.close()
r['finishedAtUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps(r, indent=2))
