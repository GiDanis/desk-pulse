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
        normalization={}
        original_normalize=theme_api.normalize_legacy
        def observe_normalize(surface,*values,**kwargs):
            start=time.perf_counter_ns()
            result=original_normalize(surface,*values,**kwargs)
            item=normalization.setdefault(surface,{'calls':0,'milliseconds':0,'maxSportMatches':0})
            item['calls']+=1;item['milliseconds']+=(time.perf_counter_ns()-start)/1e6
            sport=result.get('sport') or {}
            item['maxSportMatches']=max(item['maxSportMatches'],len(sport.get('matches',[])))
            return result
        h.stack.enter_context(patch('theme_api.normalize_legacy',observe_normalize))
        routes=[('Serie A','sports','sport','key5'),('Squadra','sports','team','key5'),('Squadra con modo preparato','sports','team-prepared','key5'),('F1','sports','f1','key5'),('MotoGP','sports','motogp','key5'),('Casa','casa','','key5'),('Rete traffico','network','','key5'),('Rete dispositivi','network','','networkList'),('Impostazioni','oggi','','settings'),('Informazioni','oggi','','info')]
        for label,family,discipline,route in routes:
            h.root.setProperty('overlay','');h.root.setProperty('overlayStack',[])
            h.root.setProperty('familyId',family)
            if discipline:h.root.setProperty('sportHubSelectedId','team' if discipline=='team-prepared' else discipline)
            if discipline=='team-prepared':h.root.setProperty('sportView','LA MIA SQUADRA')
            elif discipline=='team':h.root.setProperty('sportView','PROSSIME')
            h.root.setProperty('viewIndex',[0]*8);h.wait_ready();h.pump(15)
            normalization={}
            before=h.service.apiFactory._generation
            profiler=cProfile.Profile();profiler.enable();start=time.perf_counter_ns()
            if route=='key5':keypad.keyPressed.emit(5)
            else:h.expression('pushOverlay('+json.dumps(route)+')')
            handled=time.perf_counter_ns();h.wait_ready();h.app.processEvents();h.wait_ready()
            end=time.monotonic()+5
            while not h.expression('overlayHost.currentReady && overlayHost.readiness === \"ready\"') and time.monotonic()<end:h.pump(5)
            profiler.disable();data=pstats.Stats(profiler)
            rows=[{'file':Path(f).name,'line':line,'function':name,'calls':nc,'selfSeconds':tt,'cumulativeSeconds':ct} for (f,line,name),(cc,nc,tt,ct,callers) in data.stats.items()]
            records.append({'label':label,'input':route,'overlay':h.value('overlay'),'surface':h.value('overlayContentId'),'newContexts':h.service.apiFactory._generation-before,'handler_ms_profiled':(handled-start)/1e6,'profileSeconds':data.total_tt,'normalizationBySurface':normalization,'topCumulative':sorted(rows,key=lambda r:r['cumulativeSeconds'],reverse=True)[:22],'topSelf':sorted(rows,key=lambda r:r['selfSeconds'],reverse=True)[:15]})
            assert h.value('overlay'),label
            assert h.expression('overlayHost.currentReady && overlayHost.readiness === "ready"'),(label,h.value('overlay'),h.expression('({active:overlayHost.active,readiness:overlayHost.readiness,surface:overlayHost.currentSurfaceId,contextReady:overlayHost.currentContextReady,itemReady:overlayHost.currentItem ? overlayHost.currentItem.ready : null,contentReady:overlayHost.currentItem ? overlayHost.currentItem.contentReady : null})'),h.messages)
        assert not h.transport,h.transport
        assert not h.messages,h.messages
        report={'status':'passed','scope':'CPU attribution per opening on PC offscreen; synthetic 380 matches and demo Casa/network; profiled timings not board performance; settings/info direct pushOverlay, other paths key5; team-prepared sets sportView before key5 as isolated navigation-order experiment','records':records,'network_attempts':h.transport,'qml_messages':h.messages}
        print(json.dumps({'status':'passed','routes':[(r['label'],r['surface']) for r in records]}))
finally:
    if h is not None:h.close()
    from PySide6.QtCore import QCoreApplication,QEvent
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    private.cleanup()
    if report is not None:args.output.write_text(json.dumps(report,indent=2)+'\n')
