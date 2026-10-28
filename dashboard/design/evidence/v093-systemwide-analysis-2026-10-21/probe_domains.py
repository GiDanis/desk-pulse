"""All provider domains and event pipeline, fixtures only, private files, no network."""
import argparse
from copy import deepcopy
import datetime
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
a = p.parse_args()
source = a.source.resolve()
sys.path.insert(0, str(source))
os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                  SMARTPC_SPORT_OFFLINE='1', SMARTPC_RACING_OFFLINE='1',
                  OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
os.nice(10)
fixture_paths = dict(weather='fixtures/theme-runtime/domains/weather-zero.json',
                     sport='fixtures/sport-normalized-sample.json',
                     f1='fixtures/racing-f1-normalized.json', motogp='fixtures/racing-motogp-normalized.json')
fixtures = globals().get('_STUDY_FIXTURES') or {key: json.loads((source/path).read_text()) for key, path in fixture_paths.items()}
network = []


def denied(*a, **kw):
    network.append('denied')
    raise RuntimeError('System-wide study network denied')


def measure(fn, n=16):
    fn()
    samples = []
    for _ in range(n):
        before = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns()-before)/1e6)
    return dict(n=n, p50Ms=statistics.median(samples), maxMs=max(samples), samplesMs=samples)


r = dict(startedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         scope='Private fixture services, Python getters/callbacks/event engine; no QML GPU/optical claim',
         python=sys.version, sourceHashes={name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (
             'weather.py', 'account.py', 'sport.py', 'motorsport.py', 'network.py', 'casa.py', 'events.py', 'event_core.py', 'system_info.py')})
with tempfile.TemporaryDirectory(prefix='smartpc-v093-domains-') as tmp, \
        patch('socket.socket.connect', side_effect=denied), patch('socket.getaddrinfo', side_effect=denied):
    base = Path(tmp)
    for key in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME'):
        os.environ[key] = str(base/key)
        (base/key).mkdir()
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import QCoreApplication, QEvent, qVersion
    app = QGuiApplication([])
    app.setOrganizationName('SmartPCStudy')
    app.setApplicationName('V093Domains')
    from weather import WeatherService, normalize_response
    from account import AccountService
    from sport import SportService
    from motorsport import MotorsportService
    from casa import CasaService
    from network import NetworkService
    from events import EventService
    from system_info import SystemInfo
    now = time.time()
    account_path = base/'account.json'
    account_path.write_text(json.dumps(dict(version=1, status='active', updatedAt=now,
        data=dict(plan='Fixture', windows=[dict(usedPercent=0, windowDurationMins=300, resetsAt=now+3600)]))))
    seed = deepcopy(fixtures['sport'])
    seed['fetchedAt'] = seed['standingsFetchedAt'] = now
    services = {}
    started = time.perf_counter_ns()
    services['weather'] = WeatherService(auto_refresh=False)
    services['account'] = AccountService(account_path)
    services['sport'] = SportService(auto_refresh=False, initial=seed, cache_path=base/'sport.json', state_path=base/'goals.json', verified=False)
    for kind in ('f1', 'motogp'):
        services[kind] = MotorsportService(kind, auto_refresh=False, initial=deepcopy(fixtures[kind]['snapshot']), cache_directory=base)
    services['casa'] = CasaService(auto_refresh=False, demo=True)
    services['network'] = NetworkService(auto_refresh=False, demo=True)
    services['events'] = EventService(path=base/'events.sqlite3', auto_refresh=False)
    services['system'] = SystemInfo()
    r.update(constructorsTogetherMs=(time.perf_counter_ns()-started)/1e6, qt=qVersion())
    try:
        r['providerGetters'] = {}
        for name, service in services.items():
            prop = 'eventState' if name == 'events' else 'data' if name == 'system' else 'moduleState'
            r['providerGetters'][name] = dict(measurement=measure(lambda service=service, prop=prop: getattr(service, prop)),
                fixtureJsonBytes=len(json.dumps(getattr(service, prop), default=str).encode()))
        normalized = normalize_response(fixtures['weather']['raw'])
        r['weatherNormalize'] = measure(lambda: normalize_response(fixtures['weather']['raw']))
        r['weatherCompletionCallback'] = measure(lambda: services['weather']._on_finished(normalized, None))
        r['accountUnchangedRefresh'] = measure(lambda: services['account'].refresh(False))
        r['accountForcedFileRefresh'] = measure(lambda: services['account'].refresh(True))
        r['systemInfoRefresh'] = measure(services['system'].refresh)
        r['eventScaling'] = []
        event_service = services['events']
        for count in (0, 100, 1000):
            with event_service._engine.db:
                event_service._engine.db.execute('DELETE FROM events')
                for i in range(count):
                    event = dict(id=f'study:{i}', source='study', category='fixture', title='Fixture',
                                 detail='Offline event', priority=1, revision=1, issuedAt=now,
                                 startsAt=now-1, expiresAt=now+3600, showOnHome=False)
                    event_service._engine.db.execute('INSERT INTO events(id,source,payload,starts_at,expires_at,priority,rank) VALUES(?,?,?,?,?,?,?)',
                        (event['id'], 'study', json.dumps(event), now-1, now+3600, 1, 1))
            r['eventScaling'].append(dict(activeEvents=count, tick=measure(event_service._tick, n=8),
                engineSnapshot=measure(lambda: event_service._engine.snapshot(now=now), n=8)))
        r['networkAttempts'] = network
        assert not network, network
    finally:
        services['system'].setMonitoring(False)
        for service in reversed(list(services.values())):
            if hasattr(service, 'close'):
                service.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
r['finishedAtUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps(r, indent=2))
