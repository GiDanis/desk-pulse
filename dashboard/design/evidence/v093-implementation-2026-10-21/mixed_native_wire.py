"""Private full-system UI repetition under the selected CPU policy."""
from pathlib import Path
import argparse
import json
import sys
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=600)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(args.source))
    from theme_fixture_support import isolate_process,LegacyHarness,read_corpus
    private,base=isolate_process()
    from PySide6.QtCore import QCoreApplication,QEvent,QEventLoop,QTimer,Qt,qVersion
    from theme_bundle import BundleManager,validate_project
    bundle=args.source.parent/'theme-projects/apple-calm/bundle'
    checked=validate_project(bundle)
    cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
    assert checked['digest']==cache['digest'] and cache['result']['qt']==qVersion()
    BundleManager(base,app_root=args.source).import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    _,cases,_=read_corpus()
    h=None
    rows=[]
    urgents=[]
    memory_samples=[]
    started=time.monotonic()
    args.output.mkdir(parents=True,exist_ok=True)
    def memory():
        result={}
        for line in Path('/proc/self/smaps_rollup').read_text().splitlines():
            if line.startswith(('Pss:','Rss:')):
                key,value=line.split(':',1)
                result[key]=int(value.split()[0])
        return result
    try:
        h=LegacyHarness(base,dict(theme='base',variant='day',motion='normal',game=True))
        def native_pump(ms=30):
            loop=QEventLoop()
            timer=QTimer()
            timer.setSingleShot(True)
            timer.setTimerType(Qt.TimerType.PreciseTimer)
            timer.timeout.connect(loop.quit)
            timer.start(round(ms))
            loop.exec()
        h.pump=native_pump
        assert h.service.selectDraft('studio.applecalm')
        h.wait_ready()
        initial=memory()
        cycle=0
        while time.monotonic()-started<args.seconds or len({r['surfaceId'] for r in rows})<68:
            h.profile['variant']='night' if cycle%2 else 'day'
            h.profile['motion']=('normal','reduced','off')[cycle%3]
            for case in cases:
                before=time.monotonic()
                result=h.run_case(case)
                assert result['status']=='passed'
                rows.append(dict(id=case['id'],surfaceId=case['surfaceId'],family=case['family'],
                                 cycle=cycle,variant=h.profile['variant'],motion=h.profile['motion'],
                                 wallMs=(time.monotonic()-before)*1000))
                # A production app.exec drains DeferredDelete. processEvents
                # alone in a long fixture loop would accumulate retired objects.
                QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
                if len(rows)%30==0 and not h.value('urgentEvent').get('id'):
                    identity='qa-mixed:'+str(len(rows))
                    event=dict(version=1,id=identity,source='qa-mixed',sourceLabel='Verifica isolata',
                        category='test',priority=3,title='Verifica prestazioni',detail='Evento sintetico locale',
                        issuedAt=h.now,startsAt=h.now,expiresAt=h.now+60,showOnHome=False)
                    before=time.monotonic()
                    h.events.publish_snapshot('qa-mixed',[event])
                    h.wait_ready()
                    h.window.update()
                    h.pump(60)
                    assert h.value('urgentEvent').get('id')==identity
                    urgents.append(dict(eventVisible=True,readyAndPumpMs=(time.monotonic()-before)*1000))
                    h.events.dismiss(identity)
                    h.events.publish_snapshot('qa-mixed',[])
                    h.wait_ready()
                if len(rows)%20==0:
                    progress=dict(status='in-progress',elapsedSeconds=time.monotonic()-started,
                                  cases=len(rows),surfaces=len({r['surfaceId'] for r in rows}),
                                  current=case['id'],memoryKiB=memory(),contexts=len(h.service.apiFactory._contexts),leases=len(h.service._leases))
                    memory_samples.append(progress)
                    (args.output/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
                if time.monotonic()-started>=args.seconds and len({r['surfaceId'] for r in rows})>=68:break
            cycle+=1
        assert not h.messages and not h.transport
        assert h.game._process is None,'Implicit learner started'
        report=dict(status='passed',elapsedSeconds=time.monotonic()-started,rows=rows,
            uniqueSurfaces=len({r['surfaceId'] for r in rows}),cycles=cycle,
            urgentChecks=urgents,memorySamples=memory_samples,initialMemoryKiB=initial,finalMemoryKiB=memory(),
            finalContexts=len(h.service.apiFactory._contexts),finalLeases=len(h.service._leases),
            qmlWarnings=h.messages,networkAttempts=h.transport,noImplicitLearner=True,
            scope='EGLFS UI repetition with private frozen-clock providers and synthetic urgent events; no live/optical claim',
            resourcePolicy=Path('/sys/devices/system/cpu/cpufreq/policy6/scaling_governor').read_text().strip())
        assert h.window.grabWindow().save(str(args.output/'final.png'))
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
    finally:
        if h:h.close()
        private.cleanup()


if __name__=='__main__':main()
