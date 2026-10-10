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
        records=[]
        def inspect(label, handler_ms=None):
            snapshot=h.expression('({active:overlayHost.active,readiness:overlayHost.readiness,contentId:overlayHost.contentId,currentSurface:overlayHost.currentSurfaceId,rendererKey:overlayHost.loadedRendererKey,retainedKeys:overlayHost.retainedLoaders.map(x=>x.rendererKey),instance:overlayHost.currentLoader && overlayHost.currentLoader.usePublicApi ? overlayHost.currentLoader.publicAdapter.publicContext.surfaceInstanceId : ""})')
            records.append({'label':label,'overlay':h.value('overlay'),'factoryGeneration':h.service.apiFactory._generation,'liveContexts':len(h.service.apiFactory._contexts),'handler_ms':handler_ms,'host':snapshot})
        def act(key,label):
            start=time.perf_counter_ns();keypad.keyPressed.emit(key);duration=(time.perf_counter_ns()-start)/1e6
            h.wait_ready();h.pump(15);inspect(label,duration)
        h.root.setProperty('overlay','');h.root.setProperty('overlayStack',[])
        h.root.setProperty('familyId','sports');h.root.setProperty('sportHubSelectedId','sport');h.wait_ready()
        inspect('initial')
        for i in range(5):
            act(5,'same-list-open-'+str(i));assert h.value('overlay')=='sportList'
            act(7,'same-list-close-'+str(i));assert h.value('overlay')==''
        h.expression('pushOverlay("sportList")');h.wait_ready();inspect('list-direct')
        h.expression('pushOverlay("settings")');h.wait_ready();inspect('settings-switch')
        act(7,'settings-back-to-list');assert h.value('overlay')=='sportList'
        act(7,'list-close')
        h.expression('pushOverlay("settings")');h.wait_ready();inspect('settings-after-close')
        act(7,'settings-close')
        h.expression('pushOverlay("settings")');h.wait_ready();inspect('settings-reopen')
        report={'status':'passed','scope':'PC offscreen real Main; synthetic fixtures/input; loader identity and context lifetime, not board or optical timing','records':records,'network_attempts':h.transport,'qml_messages':h.messages}
        assert not h.transport,h.transport
        assert not h.messages,h.messages
        print(json.dumps(report,indent=2))
finally:
    if h is not None:h.close()
    from PySide6.QtCore import QCoreApplication,QEvent
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    private.cleanup()
    if report is not None:args.output.write_text(json.dumps(report,indent=2)+'\n')
