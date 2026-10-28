"""Isolated real Main/ThemeApi aquarium checks and native frame measurements."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--theme',default='base',choices=['base','functional','apple'])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=3)
    p.add_argument('--warmup',type=float,default=2)
    p.add_argument('--population',type=int,default=6,choices=[1,4,6,8,16])
    p.add_argument('--sprite',action='store_true')
    p.add_argument('--benchmark-only',action='store_true')
    p.add_argument('--missing-assets',action='store_true')
    p.add_argument('--broken-image',action='store_true')
    p.add_argument('--bundle',type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    from theme_fixture_support import isolate_process,LegacyHarness
    private,base=isolate_process()
    from theme_bundle import BundleManager,validate_project
    from PySide6.QtCore import qVersion
    if a.theme=='apple':
        bundle=a.bundle or Path(__file__).resolve().parents[1]/'theme-projects/apple-calm/bundle'
        checked=validate_project(bundle,app_root=Path(__file__).parent)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==checked['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=Path(__file__).parent).import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,{'theme':'base' if a.theme=='apple' else a.theme,'variant':'day','motion':'normal'})
    from PySide6.QtCore import QObject,qVersion,QCoreApplication,QEvent,Qt
    from PySide6.QtGui import QKeyEvent
    if a.theme=="apple":
        assert h.service.selectDraft("studio.applecalm");h.wait_ready()
    checks=[];frames=[];reports=[]
    def wait(test,seconds=8):
        end=time.monotonic()+seconds
        while not test() and time.monotonic()<end:h.pump(5)
        assert test(),(h.aquarium.snapshot,h.messages,h.expression('aquariumPage.lastError'))
    def value(expr):return h.expression('aquariumPage.currentItem.'+expr)
    def check(name,condition):assert condition,name;checks.append(name)
    def capture(name):
        h.pump(20);assert h.window.grabWindow().save(str(a.output/(name+'.png')))
    expected_theme='studio.applecalm' if a.theme=='apple' else a.theme
    def commit_theme():
        # Home intentionally cancels an appearance preview. Persist the private
        # test selection so navigation really exercises the requested theme.
        from theme_test_support import wait_save
        h.wait_ready();wait(lambda:h.service.readyToApply)
        assert h.service.apply(),h.service.lastError
        wait_save(h.app,h.service,timeout=15);h.wait_ready()
        check('savedThemeForNavigation',h.service.activeThemeId==expected_theme)
    try:
        commit_theme()
        if a.missing_assets:
            h.aquarium._root=base/'missing-artwork'
        if a.broken_image:
            from aquarium_catalog import load_catalog
            h.aquarium._catalog=load_catalog()
            h.aquarium._catalog['backgroundUrl']=(base/'missing-image.png').as_uri()
            h.aquarium._publish()
        h.expression('familyId="aquarium"')
        if a.missing_assets or a.broken_image:
            wait(lambda:h.aquarium.snapshot['status']=='error' and h.value('presentedPageContentId')=='aquarium.main')
            check('errorFallbackCommitted',value('ready') and not value('moving'))
            capture('asset-error')
            h.expression('activateKey(9)');h.pump(150)
            check('errorMenuAccessible',h.value('overlay')=='menu')
            h.expression('activateKey(7)');h.pump(100);h.expression('activateKey(7)');h.pump(100)
            check('errorCanReturnHome',h.value('familyId')=='oggi')
            expected=[m for m in h.messages if a.broken_image and 'missing-image.png' in m]
            unexpected=[m for m in h.messages if m not in expected]
            assert not unexpected and not h.transport,(h.messages,h.transport)
            if a.broken_image:assert expected,'Image failure was not exercised'
            (a.output/'report.json').write_text(json.dumps({'status':'passed','checks':checks,'warnings':unexpected,'expectedAssetWarnings':expected,'networkAttempts':h.transport},indent=2)+'\n')
            # Preserve expected decode diagnostics in the report; the shared
            # harness teardown must still reject every unexpected Qt warning.
            h.messages[:]=unexpected
            return
        wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running')
        wait(lambda:value('tickCount')>2)
        check('firstCommitAfterAsyncAssets',h.value('presentedPageContentId')=='aquarium.main')
        check('nativeCanvasAndSafeArea',h.expression('aquariumPage.width === 960 && aquariumPage.height === 640 && aquariumPage.y+contentLayer.y === 0 && aquariumPage.context.viewportWidth === 960'))
        check('fishEnvelopesInsideSafeArea',h.expression('aquariumPage.currentItem.fishEnvelopeRadius >= .94 && aquariumPage.currentItem.actors.every(a => {const s=aquariumPage.currentItem.ctx.safeArea;return a.area.x-a.radius>=s.x-.000001 && a.area.y-a.radius>=s.y-.000001 && a.area.x+a.area.width+a.radius<=s.x+s.width+.000001 && a.area.y+a.area.height+a.radius<=s.y+s.height+.000001})'))
        check('hourPreserved',h.expression('publicSurfacePayload("shell.main").clockText === timeText() && timeText().length === 5'))
        if not a.benchmark_only:
            capture('running')
            QCoreApplication.sendEvent(h.window,QKeyEvent(QEvent.KeyPress,Qt.Key_5,Qt.NoModifier,'5',True,2));h.pump(100)
            check('qtAutoRepeatDoesNotToggle',h.aquarium.snapshot['requestedPlayback']=='playing')
            QCoreApplication.sendEvent(h.window,QKeyEvent(QEvent.KeyPress,Qt.Key_5,Qt.NoModifier,'5',False,1));h.pump(150);ticks=value('tickCount');h.pump(160)
            check('pauseStopsClock',value('tickCount')==ticks and h.aquarium.snapshot['requestedPlayback']=='paused')
            h.expression('activateKey(9)');h.pump(80);h.expression('activateKey(7)');h.pump(100)
            check('pausedSurvivesMenu',h.aquarium.snapshot['requestedPlayback']=='paused' and value('tickCount')==ticks)
            h.expression('activateKey(5)');wait(lambda:value('tickCount')>ticks)
            h.expression('activateKey(9)');h.pump(120);ticks=value('tickCount');h.pump(120)
            check('overlayStopsClock',value('tickCount')==ticks)
            h.expression('activateKey(7)');wait(lambda:value('tickCount')>ticks)
            h.events.set_demo_scenario('urgente');h.pump(160);ticks=value('tickCount');h.pump(160)
            check('urgentStopsAndOwnsInput',h.aquarium.snapshot['requestedPlayback']=='paused' and value('tickCount')==ticks and bool(h.value('urgentEvent').get('id')))
            capture('urgent')
            h.events.set_demo_scenario('nessuno');h.pump(150)
            check('urgentDoesNotAutoResume',h.aquarium.snapshot['requestedPlayback']=='paused')
            h.expression('activateKey(5)');wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running')
            h.service.beginEdit()
            for mode in ('reduced','off'):
                assert h.service.setSection('motionMode',mode);h.wait_ready();h.pump(120);ticks=value('tickCount');h.pump(120)
                check(mode+'Static',h.aquarium.snapshot['effectivePlayback']=='static' and value('tickCount')==ticks)
            assert h.service.setSection('motionMode','normal');h.wait_ready();wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running')
            assert h.service.setSection('paletteMode','night');h.wait_ready();capture('night')
            check('nightKeepsPlayback',h.aquarium.snapshot['effectivePlayback']=='running')
            assert h.service.setSection('paletteMode','day');h.wait_ready();commit_theme()
            for _ in range(20):
                h.expression('activateKey(1)');h.pump(80);check('hiddenStops',h.aquarium.snapshot['effectivePlayback']=='suspended')
                h.expression('familyId="aquarium"');wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running')
                check('requestedThemeSurvivesReentry',h.service.activeThemeId==expected_theme)
                h.pump(40);QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
                clocks=[o for o in h.root.findChildren(QObject) if 'FrameAnimation' in o.metaObject().className() and o.property('running')]
                check('singleClockAndSixActorsAfterReentry',len(clocks)==1 and value('actors.length')==6 and value('rows.length')==6)
            h.expression('activateKey(7)');h.pump(100);check('backFromAquariumHome',h.value('familyId')=='oggi')
            h.expression('familyId="aquarium"');wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running')
        h.expression('aquariumPage.currentItem.benchmarkPopulation='+str(a.population))
        h.expression('aquariumPage.currentItem.benchmarkSprite='+str(a.sprite).lower())
        wait(lambda:value('assetsReady'))
        # Keep the real shell clock alive during long native measurements.
        h.root.findChild(QObject,'clockTimer').setProperty('running',True)
        h.pump(int(a.warmup*1000))
        frames.clear()
        def frame():frames.append(time.monotonic_ns())
        h.window.frameSwapped.connect(frame)
        started=time.monotonic();start_ticks=value('tickCount');start_discarded=value('discardedFrames')
        samples=[];next_sample=started;last_cpu=None;last_sample=None
        def sample_resources():
            nonlocal last_cpu,last_sample
            now=time.monotonic()
            try:
                stat=Path('/proc/self/stat').read_text().split(') ',1)[1].split()
                cpu=(int(stat[11])+int(stat[12]))/os.sysconf('SC_CLK_TCK')
                status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
                temperatures={p.parent.name:int(p.read_text())/1000 for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}
                samples.append({'elapsed':now-started,'rssKiB':int(status['VmRSS'].split()[0]),'threads':int(status['Threads']),'fds':len(list(Path('/proc/self/fd').iterdir())),'cpuPercent':(cpu-last_cpu)/(now-last_sample)*100 if last_cpu is not None else None,'temperaturesC':temperatures})
                last_cpu,last_sample=cpu,now
            except (OSError,ValueError,KeyError):pass
        while time.monotonic()-started<a.seconds:
            h.pump(10)
            if time.monotonic()>=next_sample:
                sample_resources();next_sample=time.monotonic()+10
        sample_resources()
        ended=time.monotonic();h.window.frameSwapped.disconnect(frame)
        intervals=[(b-c)/1e6 for c,b in zip(frames,frames[1:])]
        ordered=sorted(intervals)
        def percentile(q):return ordered[max(0,math.ceil(len(ordered)*q)-1)] if ordered else None
        duration=ended-started
        missed=sum(max(0,round(dt/(1000/60))-1) for dt in intervals)
        slots=len(intervals)+missed
        rate=len(frames)/duration
        native=os.environ.get('QT_QPA_PLATFORM')=='eglfs' and os.environ.get('QT_QUICK_BACKEND')!='software'
        passed=bool(intervals) and rate>=59 and percentile(.95)<=18.5 and missed/max(1,slots)<=.01 and sum(dt>50 for dt in intervals)<2
        report={'status':'passed','theme':a.theme,'platform':os.environ.get('QT_QPA_PLATFORM'),'qt':qVersion(),'population':a.population,'renderer':'sprite' if a.sprite else 'rig','seconds':duration,'callbacks':len(frames),'callbacksPerSecond':rate,'p50Ms':percentile(.5),'p95Ms':percentile(.95),'p99Ms':percentile(.99),'maxMs':max(intervals,default=None),'stallsOver50Ms':sum(dt>50 for dt in intervals),'estimatedMissedSlots':missed,'estimatedMissedSlotRatio':missed/max(1,slots),'poseTicks':value('tickCount')-start_ticks,'discardedLongDeltas':value('discardedFrames')-start_discarded,'near60SoftwareGate':passed if native else None,'nativeGraphics':native,'physicalFramesQualified':False,'checks':checks,'warnings':h.messages,'networkAttempts':h.transport,'rawIntervalsMs':intervals,'assetRevision':h.aquarium.snapshot['assetRevision'],'scope':'Software queue/pose timing in isolated Main with fixture providers; not GPU or optical timing'}
        windows=[]
        for offset in range(0,len(intervals),600):
            window=intervals[offset:offset+600]
            if len(window)<300:continue
            ordered_window=sorted(window)
            windows.append({'fromCallback':offset,'count':len(window),'callbacksPerSecond':1000*len(window)/sum(window),'p95Ms':ordered_window[math.ceil(len(window)*.95)-1],'maxMs':max(window)})
        report.update(resourceSamples=samples,windows600=windows,shellClockRunning=True)
        assert not h.messages,h.messages;assert not h.transport,h.transport
        capture('final')
        (a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ('rawIntervalsMs','checks')},ensure_ascii=False))
    finally:
        h.close();private.cleanup()
if __name__=='__main__':main()
