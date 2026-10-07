#!/usr/bin/env python3
"""Offline real-Main navigation/renderer evidence; supports the preserved baseline.

Timings are software action → frameSwapped callback with coherent GUI state,
not optical input-to-pixel or GPU times. Production settings/providers are isolated.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser()
p.add_argument('--runtime-root',type=Path,default=ROOT/'dashboard')
p.add_argument('--project',type=Path,default=ROOT/'theme-projects/apple-calm/bundle')
p.add_argument('--sport-cache',type=Path)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--baseline',action='store_true')
p.add_argument('--existing-revision',type=Path)
p.add_argument('--palette',choices=['day','night'],default='night')
p.add_argument('--cycles',type=int,default=3)
args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(args.runtime_root))
from theme_fixture_support import isolate_process,LegacyHarness,read_corpus
private,base=isolate_process();h=None
try:
    from theme_bundle import BundleManager,validate_project
    from theme_test_support import as_value,wait_save
    from PySide6.QtCore import QObject,qVersion
    from theme_api import normalize_legacy
    manager=BundleManager(base,app_root=args.runtime_root)
    if args.existing_revision:
        descriptor=json.loads(args.existing_revision.read_text())
        directory=base/'theme-bundles'/descriptor['id']/(descriptor['version']+'-'+descriptor['digest'])
        directory.mkdir(parents=True)
        shutil.copytree(args.project,directory/'payload')
        shutil.copy2(args.existing_revision,directory/'revision.json')
        revision=manager.verify_revision(descriptor)
        assert revision['preflight']['status']=='passed'
    else:
        manifest=validate_project(args.project,app_root=args.runtime_root)
        cache_path=args.project.parent/'evidence/preflight-cache.json'
        cache=json.loads(cache_path.read_text()) if cache_path.is_file() else {}
        from theme_runtime import preflight
        def checked(payload,metadata,registry):
            if cache.get('digest')==manifest['digest'] and cache.get('result',{}).get('qt')==qVersion() and cache['result'].get('status')=='passed':return cache['result']
            result=preflight(payload,metadata,registry)
            cache_path.parent.mkdir(parents=True,exist_ok=True)
            cache_path.write_text(json.dumps({'digest':manifest['digest'],'result':result},indent=2)+'\n')
            return result
        revision=manager.import_bundle(args.project,preflight=checked,require_preflight=True)
    h=LegacyHarness(base,{'theme':'base','variant':args.palette,'motion':'normal'})
    assert h.service.selectDraft(revision['id']),h.service.lastError
    h.wait_ready()
    deadline=time.monotonic()+15
    while not h.service.readyToApply and time.monotonic()<deadline:h.pump(10)
    assert h.service.readyToApply,h.service.lastError
    assert h.service.apply(),h.service.lastError
    wait_save(h.app,h.service);h.pump(30)
    raw=json.loads(args.sport_cache.read_text()).get('snapshot') if args.sport_cache else deepcopy(h.seed)
    h.sport._snapshot=deepcopy(raw);h.sport.changed.emit();h.pump(40)
    timings=[];frame_stamps=[];current=None;dot_probe=None
    def swapped():
        now=time.perf_counter_ns()
        frame_stamps.append(now)
        if dot_probe is not None:dot_probe.append(now)
        if current is not None and h.expression('currentThemeRenderCoherent()'):
            if current['firstFrameMs'] is None:current['firstFrameMs']=(now-current['start'])/1e6
            if not h.expression('navigationMotion.running || tabMotion.running'):
                current['settledFrameMs']=(now-current['start'])/1e6
    h.window.frameSwapped.connect(swapped)
    actions=[
        ('home','familyId="oggi";viewIndex=[0,0,0,0,0,0,0];sportView="PROSSIME";overlay="";overlayStack=[]'),
        ('weather','navigateFamily(1)'),('forecast','navigateView(1)'),
        ('account','navigateFamily(1)'),('sport','navigateFamily(1)'),
        ('standing-overview','sportView="CLASSIFICA"'),
        ('standing-detail','openSportTable()'),('menu','pushOverlay("menu")'),
        ('standing-return','back()'),('back-to-sport','back()'),
        ('f1','navigateFamily(1)'),('f1-second-view','navigateView(1)'),
        ('motogp','navigateFamily(1)'),('casa','navigateFamily(1)'),
        ('casa-devices','navigateView(1)'),('home-return','home()')]
    for cycle in range(args.cycles):
        for label,code in actions:
            h.pump(20)
            current={'label':label,'cycle':cycle,'start':time.perf_counter_ns(),'firstFrameMs':None,'settledFrameMs':None}
            h.expression('(function(){'+code+';return true})()')
            elapsed=(time.perf_counter_ns()-current['start'])/1e6
            end=time.monotonic()+8
            while current['settledFrameMs'] is None and time.monotonic()<end:h.pump(2)
            # Repeating Home when already there need not manufacture a frame.
            if current['firstFrameMs'] is None and label=='home':
                current=None;continue
            assert current['settledFrameMs'] is not None,{'timeout':label,'warnings':h.messages}
            timings.append({k:v for k,v in current.items() if k!='start'}|{'actionMs':elapsed})
            print(json.dumps(timings[-1]),flush=True);current=None
    # Read the actual public names and identities through the loaded renderer.
    h.expression('(function(){familyId="sport";sportView="CLASSIFICA";openSportTable();return true})()')
    h.wait_ready();h.pump(20)
    host=h.root.findChild(QObject,'overlayHost');loader=as_value(host.property('currentLoader'))
    context=as_value(loader.findChild(QObject,'publicContextAdapter').property('publicContext'))
    names=[context.standings.get(i).name for i in range(context.standings.count)]
    ids=[context.standings.get(i).id for i in range(context.standings.count)]
    if not args.baseline:
        assert names==[row['team'] for row in raw['standings']]
        assert ids==[row['teamId'] for row in raw['standings']]
        identity=loader
        h.expression('(pushOverlay("menu"),true)');h.wait_ready();h.pump(20)
        h.expression('(back(),true)');h.wait_ready();h.pump(20)
        assert as_value(host.property('currentLoader')) is identity,'standing renderer not reused'
        shell=h.root.findChild(QObject,'shellHost');shell_item=as_value(shell.property('currentItem'))
        dots=shell_item.findChild(QObject,'viewDots')
        assert dots.property('count')==2 and dots.property('visible')
        assert host.property('y')==64 and shell.property('z')>host.property('z')
        h.window.grabWindow().save(str(args.output/'standing.png'))
        h.expression('(function(){home();viewIndex=[1,0,0,0,0,0,0];return true})()');h.wait_ready();h.pump(250)
        clock=h.root.findChild(QObject,'homeClock');item=as_value(clock.property('currentItem'))
        assert item.findChild(QObject,'dominantClock') is not None
        h.window.grabWindow().save(str(args.output/'clock.png'))
    # Observe dot animation without evaluating a whole-QML coherence expression
    # on every frame. Include every interval inside each probe, even >=100ms.
    dot_intervals=[]
    h.expression('(home(),true)');h.wait_ready();h.pump(300)
    for direction in (1,-1,1,-1):
        dot_probe=[]
        h.expression('(navigateFamily('+str(direction)+'),true)');h.pump(300)
        dot_intervals.extend((b-a)/1e6 for a,b in zip(dot_probe,dot_probe[1:]))
        dot_probe=None
    assert not h.messages,h.messages
    cache={};warm=[]
    for i in range(25):
        t=time.perf_counter_ns();normalize_legacy('sport.standings',{'model':{'sport':{'data':raw,'status':'offline'}},'epoch':i,'selection':{'index':i%20}},cache,validate=False)
        if i:warm.append((time.perf_counter_ns()-t)/1e6)
    def p95(values):return sorted(values)[max(0,int(len(values)*.95)-1)] if values else None
    intervals=[(b-a)/1e6 for a,b in zip(frame_stamps,frame_stamps[1:]) if (b-a)/1e6<100]
    report={'status':'passed','version':revision['version'],'digest':revision['digest'],'qt':qVersion(),'platform':h.app.platformName(),'windowSize':[h.window.width(),h.window.height()],
        'baseline':args.baseline,'palette':args.palette,'sportRecords':{'fixtures':len(raw['fixtures']),'standings':len(raw['standings'])},'standingsNamesPresent':sum(bool(x) for x in names),'timings':timings,
        'warmFirstFrameP95Ms':p95([x['firstFrameMs'] for x in timings if x['cycle']>0]),'warmSettledFrameP95Ms':p95([x['settledFrameMs'] for x in timings if x['cycle']>0]),
        'standingsAdapterWarmP95Ms':p95(warm),'standingsAdapterSamplesMs':warm,'shortFrameIntervalP95Ms':p95(intervals),'frameIntervalsUnder100Ms':intervals,
        'timingScope':'Software action to frameSwapped callback with observed coherent GUI state; content settlement excludes decorative dot motion, verified separately. No optical/GPU proof. Short intervals exclude gaps >=100ms and are not an all-transition FPS claim.',
        'dotAnimationFrameIntervalP95Ms':p95(dot_intervals),'dotAnimationFrameIntervalsMs':dot_intervals,'qmlWarnings':h.messages,'providerRequests':h.transport}
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['timings','standingsAdapterSamplesMs','frameIntervalsUnder100Ms','dotAnimationFrameIntervalsMs']}),flush=True)
finally:
    if h:h.close()
    private.cleanup()
