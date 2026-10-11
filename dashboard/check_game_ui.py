"""Real Main with real on-demand learning, isolated providers and driver state."""
import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    from theme_fixture_support import isolate_process, LegacyHarness
    from theme_bundle import BundleManager, validate_project
    from PySide6.QtCore import qVersion
    parser=argparse.ArgumentParser();parser.add_argument('--theme',choices=('base','functional','apple'),default='base')
    parser.add_argument('--capture-dir',type=Path)
    parser.add_argument('--palette',choices=('day','night'),default='day')
    parser.add_argument('--motion',choices=('normal','reduced','off'),default='normal')
    parser.add_argument('--text-scale',type=float,default=1.0)
    parser.add_argument('--soak-seconds',type=float,default=0)
    parser.add_argument('--method',choices=('evolution','ppo','neat'),default='evolution')
    parser.add_argument('--progress-fixture',type=Path,help='Actual isolated learning evidence for the Progressi render')
    args=parser.parse_args()
    private,base=isolate_process();root=Path(__file__).resolve().parents[1]
    if args.theme=='apple':
        bundle=root/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=root/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,{'theme':'functional' if args.theme=='functional' else 'base','variant':args.palette,'motion':args.motion,'game':True})
    frames=[];samples=[]
    def wait(predicate,seconds=15):
        deadline=time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:h.pump(5)
        assert predicate(),h.game.snapshot
    def capture(name):
        if args.capture_dir:
            args.capture_dir.mkdir(parents=True,exist_ok=True);h.pump(60)
            assert h.window.grabWindow().save(str(args.capture_dir/(name+'.png')))
    try:
        if args.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',args.text_scale);h.wait_ready()
        assert h.game.configure({'algorithm':args.method})
        assert not h.game._process
        h.expression('familyId="game"');h.wait_ready();capture('idle')
        assert h.value('activeContentId')=='game.track'
        h.expression('activateKey(9)');h.wait_ready();assert h.value('overlay')=='gameMenu';capture('menu')
        def visual_items(item):
            yield item
            for child in item.childItems():yield from visual_items(child)
        menu_rows=h.value('gameMenuRows')
        if hasattr(menu_rows,'toVariant'):menu_rows=menu_rows.toVariant()
        for index,row in enumerate(menu_rows):
            assert row['description'] and row['value'],row
            h.expression('gameMenuIndex='+str(index));h.pump(30)
            items=[item for item in visual_items(h.window.contentItem()) if item.objectName()=='gameSettingDescription'+str(index) and item.property('visible')]
            assert items,index
            for item in items:
                assert item.property('contentHeight')<=item.property('height')+.1,(row,item.property('contentHeight'),item.property('height'))
        h.expression('gameMenuIndex=4');h.pump(30);capture('menu-parameters')
        assert not any(item.property('text') and '2/8 scegli' in str(item.property('text')) for item in visual_items(h.window.contentItem())), 'Legenda ancora presente'
        h.expression('activateKey(7)');h.wait_ready();assert h.value('overlay')==''
        h.expression('activateKey(5)');wait(lambda:h.game.snapshot['runState']=='running')
        wait(lambda:bool(h.game.scene['cars']));capture('learning')
        if args.soak_seconds:
            import resource
            h.window.frameSwapped.connect(lambda:frames.append(time.monotonic()))
            started_soak=time.monotonic();next_sample=started_soak
            while time.monotonic()-started_soak<args.soak_seconds:
                h.pump(10)
                assert h.game.snapshot['runState']=='running',h.game.snapshot
                assert not h.messages,h.messages
                if time.monotonic()>=next_sample:
                    pid=h.game._process.pid
                    status=Path('/proc/'+str(pid)+'/status').read_text()
                    memory={line.split(':')[0]:line.split(':')[1].strip() for line in status.splitlines() if line.startswith(('VmRSS:','Threads:'))}
                    temperatures={}
                    for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
                        try:temperatures[(zone/'type').read_text().strip()]=float((zone/'temp').read_text())/1000
                        except (OSError,ValueError):pass
                    samples.append({'elapsed':time.monotonic()-started_soak,'worker':memory,'temperatures':temperatures,
                                    'guiMaxRssKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'meta':h.game.scene['meta']})
                    next_sample=time.monotonic()+30
                    if args.capture_dir:(args.capture_dir/'soak-progress.json').write_text(json.dumps(samples,indent=2)+'\n')
            capture('soak-end')
        view=h.value('viewIndex');family=h.value('familyId')
        h.expression('activateKey(6)');h.expression('activateKey(8)');h.pump(50)
        assert h.value('viewIndex')==view and h.value('familyId')==family
        assert h.game.snapshot['display']=='solo'
        started=time.monotonic();h.expression('activateKey(5)');wait(lambda:not h.game.captured)
        latency=time.monotonic()-started;assert latency<.25,latency
        wait(lambda:h.game.snapshot['saveState']=='saved')
        steps=h.game.snapshot['drivers'][0]['steps'];assert steps>0
        h.pump(80);assert h.game.snapshot['drivers'][0]['steps']==steps
        capture('paused')
        h.expression('activateKey(8)');h.wait_ready();assert h.value('activeContentId')=='game.leaderboard';capture('leaderboard')
        h.expression('activateKey(8)');h.wait_ready();assert h.value('activeContentId')=='game.progress';capture('progress')
        h.expression('activateKey(2)');h.expression('activateKey(2)');h.wait_ready()
        h.expression('activateKey(5)');wait(lambda:h.game.captured)
        h.expression('activateKey(1)');wait(lambda:not h.game.captured);wait(lambda:h.game.snapshot['saveState']=='saved')
        wait(lambda:h.game._process is None)
        assert h.value('familyId')=='oggi'
        if args.progress_fixture:
            data=json.loads(args.progress_fixture.read_text());state=data['state']
            assert args.method=='evolution' and state['champion']
            driver=h.game._store.driver(h.game.snapshot['selectedDriverId'])
            assert driver['profile']==data['profile']
            h.game._store.save_training(driver['id'],{'renderFixture':True},state['champion']['policy'],
                                       data['steps'],data['wallSeconds'],curriculum=state)
            h.game._refresh()
            h.service.beginEdit()
            assert h.service.selectDraft('studio.applecalm' if args.theme=='apple' else args.theme)
            assert h.service.setToken('typography.textScale',args.text_scale);h.wait_ready()
            h.expression('familyId="game";const v=viewIndex.slice();v[8]=2;viewIndex=v');h.wait_ready()
            assert h.game.snapshot['progress']['verified'];capture('progress-qualified')
        assert not h.messages,h.messages
        assert not h.transport,h.transport
        report={'status':'passed','theme':args.theme,'platform':os.environ['QT_QPA_PLATFORM'],
                'window':[h.window.width(),h.window.height()],'pauseAckSeconds':latency,
                'stepsSaved':steps,'qmlWarnings':h.messages,'transportCalls':len(h.transport),
                'method':args.method,'palette':args.palette,'motion':args.motion,'textScale':args.text_scale,
                'soakSeconds':args.soak_seconds,'samples':samples,
                'progressFixture':bool(args.progress_fixture),
                'softwareFrameTiming':{'frames':len(frames),'medianInterval':float(__import__('statistics').median([b-a for a,b in zip(frames,frames[1:])])) if len(frames)>1 else None,
                                       'scope':'Qt frameSwapped software timing; no optical or GPU claim'}}
        if args.capture_dir:(args.capture_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
    finally:h.close();private.cleanup()


if __name__=='__main__':main()
