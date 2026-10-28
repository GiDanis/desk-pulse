"""Current saved Sport data, private service/settings, offline, no exported content."""
import cProfile
import datetime
import io
import json
import os
from pathlib import Path
import pstats
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, '/opt/smartpc/dashboard')
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', SMARTPC_SPORT_OFFLINE='1',
                  SMARTPC_RACING_OFFLINE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
os.nice(10)
network = []
def denied(*a, **kw):
    network.append('denied')
    raise RuntimeError('Saved provider probe is offline')

path = Path('/var/cache/smartpc-dashboard/SmartPC/SmartPC/sport.json')
r = dict(capturedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         scope='Saved Sport snapshot, not fresh/live API evidence; private offline service, no QML/GPU',
         cacheBytes=path.stat().st_size)
with tempfile.TemporaryDirectory(prefix='smartpc-v093-sport-') as tmp, \
        patch('socket.socket.connect', side_effect=denied), patch('socket.getaddrinfo', side_effect=denied):
    base = Path(tmp)
    for key in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME'):
        os.environ[key] = str(base/key)
        (base/key).mkdir()
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import QSettings, QCoreApplication, QEvent
    app = QGuiApplication([])
    app.setOrganizationName('SmartPCStudy')
    app.setApplicationName('V093SavedSport')
    from sport_core import read_cache
    from sport import SportService
    seed = read_cache(path)
    assert seed
    QSettings('SmartPC', 'Dashboard').setValue('sport/season', seed['season'])
    service = SportService(auto_refresh=False, initial=seed, cache_path=base/'sport.json',
                           state_path=base/'goals.json', verified=False)
    service._offline = True
    service._from_cache = True
    try:
        service.moduleState
        samples = []
        for _ in range(20):
            before = time.perf_counter_ns()
            service.moduleState
            samples.append((time.perf_counter_ns()-before)/1e6)
        probe = cProfile.Profile()
        probe.runcall(lambda: service.moduleState)
        stream = io.StringIO()
        pstats.Stats(probe, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(16)
        r.update(samplesMs=samples, p50Ms=statistics.median(samples), maxMs=max(samples),
                 fixtures=len(seed.get('fixtures', [])), profile=stream.getvalue(),
                 networkAttempts=network, status=service.moduleState['status'])
        assert not network
    finally:
        service.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
print(json.dumps(r, indent=2))
