"""Real Main, isolated providers: input -> ready -> sync-tagged frame submission.

EGLFS needs exclusive display ownership: run while the kiosk is stopped and
always restart it in the caller's finally. No provider requests or preferences.
This measures software timing, not USB, optical latency, GPU time or idle FPS.
"""
import argparse
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
parser.add_argument('--samples',type=int,default=30)
args = parser.parse_args()
private, base = isolate_process()
import PySide6
from PySide6.QtCore import QObject, Signal, Qt, qVersion, QCoreApplication, QEvent
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
        # Hosts are application-owned and static. Observe those references, not
        # a repeated scan of every DTO/row QObject created by the destination.
        hosts=[o for o in h.root.findChildren(QObject) if o.metaObject().indexOfProperty('readiness')>=0]
        from PySide6.QtQml import QQmlExpression,QQmlEngine
        coherent=QQmlExpression(QQmlEngine.contextForObject(h.root),h.root,'currentThemeRenderCoherent')
        def wait_destination():
            end=time.monotonic()+30
            while time.monotonic()<end:
                h.app.processEvents()
                QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
                active=[o for o in hosts if o.property('active')]
                errors=[o.property('lastError') for o in active if o.property('readiness')=='error']
                assert not errors,errors
                settled=all(o.property('readiness')=='ready' and
                    (o.metaObject().indexOfProperty('currentContextReady')<0 or o.property('currentContextReady')) for o in active)
                value=coherent.evaluate()[0];assert not coherent.hasError(),coherent.error().toString()
                if active and settled and value and not h.service.candidateAppearance:return
                time.sleep(.001)
            raise AssertionError([(o.property('contentId'),o.property('readiness')) for o in active])
        h.wait_ready=wait_destination
        clock=FrameClock()
        h.window.beforeSynchronizing.connect(clock.synchronize,Qt.ConnectionType.DirectConnection)
        h.window.frameSwapped.connect(clock.submitted,Qt.ConnectionType.DirectConnection)
        records=[];serial=0
        def key(position,category,cycle):
            global serial
            serial+=1
            started=time.perf_counter_ns();keypad.keyPressed.emit(position);handled=time.perf_counter_ns()
            wait_destination();ready=time.perf_counter_ns()
            with clock.lock:clock.armed=serial
            h.window.update();end=time.monotonic()+5
            while serial not in clock.completed and time.monotonic()<end:h.app.processEvents();time.sleep(.001)
            assert serial in clock.completed,category
            instance=h.expression('overlayHost.currentLoader && overlayHost.currentLoader.usePublicApi ? overlayHost.currentLoader.publicAdapter.publicContext.surfaceInstanceId : ""')
            records.append({'serial':serial,'key':position,'category':category,'cycle':cycle,'handler_ms':(handled-started)/1e6,'ready_ms':(ready-started)/1e6,'submitted_ms':(clock.completed[serial]-started)/1e6,'instanceId':instance,'overlay':h.value('overlay')})
            if args.motion!='off':h.pump(130)
        for family in ['meteo','account','sports','casa','network','oggi']:
            h.root.setProperty('overlay','');h.root.setProperty('overlayStack',[])
            h.root.setProperty('familyId',family);wait_destination()
            for i in range(6):key(6 if i%2==0 else 4,'family',i)
        h.root.setProperty('familyId','sports');h.root.setProperty('sportHubSelectedId','sport');wait_destination()
        for i in range(30):key(8 if i%2==0 else 2,'sport-dashboard',i)
        for label,family,discipline,route in [('serieA','sports','sport','sportList'),('team','sports','team','sportTeamPicker'),('casa','casa','','casaList'),('network','network','','networkList'),('settings','oggi','','settings')]:
            h.root.setProperty('overlay','');h.root.setProperty('overlayStack',[])
            h.root.setProperty('familyId',family);h.root.setProperty('viewIndex',[0]*7+[2 if label=='network' else 0])
            if discipline:h.root.setProperty('sportHubSelectedId',discipline)
            wait_destination()
            print('Measuring '+label,flush=True)
            for i in range(args.samples):
                if label=='settings':
                    keypad.keyPressed.emit(9);wait_destination();h.root.setProperty('menuIndex',1)
                key(5,label+'-open',i);assert h.value('overlay')==route,(label,h.value('overlay'))
                key(7,label+'-back',i)
                if i%10==0:print(label+' '+str(i),flush=True)
                if label=='settings':keypad.keyPressed.emit(7);wait_destination()
            if label=='serieA':
                keypad.keyPressed.emit(5);wait_destination()
                for i in range(30):key(8 if i%2==0 else 2,'serieA-focus',i)
                keypad.keyPressed.emit(7);wait_destination()
        categories=sorted({r['category'] for r in records})
        report={'status':'passed','theme':args.theme,'motion':args.motion,'platform':h.app.platformName(),'runtime':{'python':platform.python_version(),'qt':qVersion(),'pyside':PySide6.__version__},
          'protocol':'synthetic signal input; static host readiness and currentThemeRenderCoherent; explicit frame update; action ticket latched beforeSynchronizing, timestamped at frameSwapped',
          'scope':'software coherent-frame submission, not first visible feedback, motion completion, GPU or physical USB/optical latency; identical verifier for baseline/candidate; 380 synthetic matches and small demo inventories',
          'deferredDeleteFlushed':True,'records':records,'statistics':{k:stats([r['submitted_ms'] for r in records if r['category']==k]) for k in categories},
          'warmStatistics':{k:stats([r['submitted_ms'] for r in records if r['category']==k and r['cycle']>0]) for k in categories},
          'handlerStatistics':{k:stats([r['handler_ms'] for r in records if r['category']==k]) for k in categories},'network_attempts':h.transport,'qml_messages':h.messages}
        assert not h.messages,h.messages
        assert not h.transport,h.transport
        print(json.dumps({'status':'passed','statistics':report['statistics']}))
finally:
    if h is not None:h.close()
    from PySide6.QtCore import QCoreApplication,QEvent
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    private.cleanup()
    if report is not None:args.output.write_text(json.dumps(report,indent=2)+'\n')
