"""Isolated PC/offscreen diagnostic using real Main and synthetic providers.
No production display, preferences, provider requests or board runtime changes.
Software CPU attribution/lifetime only; not GPU or physical input latency.
"""
import argparse
import cProfile
import pstats
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import platform
import statistics
import threading
import time
from unittest.mock import patch

from theme_fixture_support import isolate_process, LegacyHarness

parser = argparse.ArgumentParser()
parser.add_argument('--theme', choices=['base', 'functional', 'apple'], default='apple')
parser.add_argument('--motion', choices=['off', 'reduced', 'normal'], default='off')
parser.add_argument('--palette', choices=['day', 'night'], default='day')
parser.add_argument('--bundle-project', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--extra-lists', action='store_true')
args = parser.parse_args()
private, base = isolate_process()
import PySide6
from PySide6.QtCore import QObject, Signal, Qt, qVersion
from theme_bundle import BundleManager, validate_project
import theme_api

counts = Counter()
original_cached = theme_api._cached
def cached(cache, key, raw, build):
    label = str(key)
    counts[label + ':lookup'] += 1
    def constructed():
        counts[label + ':build'] += 1
        return build()
    return original_cached(cache, key, raw, constructed)

def stats(rows):
    ordered = sorted(rows)
    return {'n': len(rows), 'median_ms': statistics.median(ordered),
            'p95_ms': ordered[int((len(ordered)-1)*.95)], 'max_ms': max(ordered)} if rows else None

class Keypad(QObject):
    keyPressed = Signal(int)

class FrameClock:
    def __init__(self):
        self.lock = threading.Lock()
        self.armed = self.synced = 0
        self.completed = {}
    def synchronize(self):
        # Render callbacks read only a primitive action ticket, never QML.
        with self.lock:
            self.synced = self.armed
    def submitted(self):
        with self.lock:
            if self.synced:
                self.completed.setdefault(self.synced, time.perf_counter_ns())

h = None
report = None
try:
    if args.theme == 'apple':
        project = args.bundle_project or Path(__file__).resolve().parents[1] / 'theme-projects/apple-calm/bundle'
        valid = validate_project(project)
        preflight = json.loads((project.parent / 'evidence/preflight-cache.json').read_text())
        assert preflight['digest'] == valid['digest'], 'stale preflight cache'
        BundleManager(base).import_bundle(project, preflight=lambda *_: preflight['result'], require_preflight=True)
    with patch('theme_api._cached', cached):
        h = LegacyHarness(base, {'theme': 'base' if args.theme == 'apple' else args.theme,
                                'variant': args.palette, 'motion': args.motion})
        if args.theme == 'apple':
            assert h.service.selectDraft('studio.applecalm')
            h.wait_ready()
        keypad = Keypad()
        h.root.setProperty('keypad', keypad)
        sample = deepcopy(h.sport._snapshot['fixtures'][0])
        fixtures = []
        for i in range(380):
            row = deepcopy(sample)
            row.update(canonicalMatchId='performance-'+str(i), round=str(i//10+1),
                       kickoffUtc=h.now+3600+i*7200, status='scheduled', homeScore=None, awayScore=None)
            fixtures.append(row)
        h.sport._snapshot['fixtures'] = fixtures
        h.sport.changed.emit()
        h.wait_ready()
        h.pump(50)
        clock = FrameClock()
        h.window.beforeSynchronizing.connect(clock.synchronize, Qt.ConnectionType.DirectConnection)
        h.window.frameSwapped.connect(clock.submitted, Qt.ConnectionType.DirectConnection)
        records = []
        serial = 0
        def key(position, category, cycle):
            global serial
            serial += 1
            profiler = cProfile.Profile() if category in ('open','back','topic') else None
            if profiler: profiler.enable()
            started = time.perf_counter_ns()
            keypad.keyPressed.emit(position)
            handled = time.perf_counter_ns()
            h.wait_ready()
            h.app.processEvents()
            h.wait_ready()
            ready = time.perf_counter_ns()
            with clock.lock:
                clock.armed = serial
            # Ask for a frame only after the destination/context is committed.
            # The next synchronization latches this action's immutable ticket.
            h.window.update()
            deadline = time.monotonic()+5
            while serial not in clock.completed and time.monotonic() < deadline:
                h.app.processEvents()
                time.sleep(.001)
            assert serial in clock.completed, ('frame timeout', category, h.messages)
            if profiler:
                profiler.disable()
                data=pstats.Stats(profiler)
                rows=[{'file':Path(f).name,'line':line,'function':name,'calls':nc,'selfSeconds':tt,'cumulativeSeconds':ct} for (f,line,name),(cc,nc,tt,ct,callers) in data.stats.items()]
                phase_profiles.append({'serial':serial,'category':category,'cycle':cycle,'totalSeconds':data.total_tt,'topCumulative':sorted(rows,key=lambda r:r['cumulativeSeconds'],reverse=True)[:30],'topSelf':sorted(rows,key=lambda r:r['selfSeconds'],reverse=True)[:30]})
            records.append({'serial': serial, 'key': position, 'category': category, 'cycle': cycle,
                            'handler_ms': (handled-started)/1e6, 'ready_ms': (ready-started)/1e6,
                            'submitted_ms': (clock.completed[serial]-started)/1e6})
        phase_profiles = []
        counts.clear()
        for cycle in range(3):
            h.root.setProperty('overlay', '')
            h.root.setProperty('overlayStack', [])
            h.root.setProperty('familyId', 'oggi')
            h.root.setProperty('viewIndex', [0]*8)
            h.root.setProperty('sportHubSelectedId', 'sport')
            h.wait_ready()
            for family in ['meteo', 'account', 'sports', 'casa', 'network', 'oggi']:
                key(6, 'topic', cycle)
                assert h.value('familyId') == family
                if len(h.value('currentFamily')['views']) > 1:
                    before = h.value('dashboardViewId') or h.value('activeContentId')
                    key(8, 'dashboard', cycle)
                    assert (h.value('dashboardViewId') or h.value('activeContentId')) != before
                    key(2, 'dashboard', cycle)
                    assert (h.value('dashboardViewId') or h.value('activeContentId')) == before
            h.root.setProperty('familyId', 'sports')
            h.root.setProperty('sportHubSelectedId', 'sport')
            h.wait_ready()
            key(5, 'open', cycle)
            assert h.value('overlay') == 'sportList'
            h.root.setProperty('sportIndex', 0)
            h.wait_ready()
            for i in range(24):
                before = h.value('sportIndex')
                key(8 if i % 2 == 0 else 2, 'list', cycle)
                assert h.value('sportIndex') != before
            key(7, 'back', cycle)
        if args.extra_lists:
            for family, route in [('casa', 'casaList'), ('network', 'networkList'), ('oggi', 'settings')]:
                h.root.setProperty('overlay', '')
                h.root.setProperty('overlayStack', [])
                h.root.setProperty('familyId', family)
                h.expression('pushOverlay('+json.dumps(route)+')')
                h.wait_ready()
                for i in range(16):
                    before = h.expression('publicSurfacePayload(overlayContentId).selection.selectedId')
                    key(8 if i % 2 == 0 else 2, route, 2)
                    after = h.expression('publicSurfacePayload(overlayContentId).selection.selectedId')
                    assert after != before, (route, 'selection did not move')
                key(7, 'back', 2)
        report = {'status': 'passed', 'theme': args.theme, 'palette': args.palette, 'motion': args.motion,
                  'platform': h.app.platformName(), 'runtime': {'python': platform.python_version(), 'qt': qVersion(), 'pyside': PySide6.__version__},
                  'frame_protocol': 'ready GUI destination; explicit update; action serial latched beforeSynchronizing and timestamped at frameSwapped',
                  'scope': 'software submission, synthetic input and data; no optical/GPU/physical USB claims; all outliers retained',
                  'records': records, 'phase_profiles': phase_profiles, 'profile_scope':'Per-action cProfile, CPU attribution only; profiled timestamps not performance baseline', 'statistics': {category: stats([r['submitted_ms'] for r in records if r['category'] == category])
                                                     for category in ['topic', 'dashboard', 'list', 'open', 'back', 'casaList', 'networkList', 'settings']},
                  'warm_statistics': {category: stats([r['submitted_ms'] for r in records if r['category'] == category and r['cycle'] > 0])
                                      for category in ['topic', 'dashboard', 'list']},
                  'cache_counters': dict(counts), 'network_attempts': h.transport, 'qml_messages': h.messages}
        assert not h.transport, h.transport
        print(json.dumps({'status': report['status'], 'platform': report['platform'], 'statistics': report['statistics']}))
finally:
    if h is not None:
        h.close()
    private.cleanup()
    if report is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
