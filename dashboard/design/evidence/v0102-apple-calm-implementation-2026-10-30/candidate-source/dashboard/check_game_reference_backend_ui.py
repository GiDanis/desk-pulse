"""Real Main/QML with the separate learner, private stores and unqualified weights.

This proves integration and layout only. It never manufactures release authority,
lap certificates or scientific results and never touches personal pilot data.
"""
from pathlib import Path
from copy import deepcopy
import argparse,json,os,time,sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),required=True)
    p.add_argument('--policy',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--single-case',action='store_true',help='Bounded native diagnostic: first Crono case only')
    p.add_argument('--races-only',action='store_true',help='Real timed private preparations, then complete 2/5-car GUI races')
    a=p.parse_args()
    if not os.environ.get('SMARTPC_GAME_LEARNER_PYTHON'):p.error('Explicit separate learner interpreter required')
    os.environ['SMARTPC_GAME_REFERENCE_EXPERIMENT']='1'
    from theme_fixture_support import isolate_process,LegacyHarness
    from game_store import GameStore,canonical
    from check_game_menu import menu_prepare
    private,base=isolate_process();project=Path(__file__).resolve().parents[1];a.output.mkdir(parents=True,exist_ok=True)
    store=GameStore(base/'state/game');policy=json.loads(a.policy.read_text())
    for d in store.drivers():
        if d['name']=='Maestro':continue
        fixture=deepcopy(policy);fixture['algorithm']=d['profile']['algorithm']
        fixture['origin']={**fixture['origin'],'backend':'sb3-skill-1'}
        with store.connect() as db:db.execute('UPDATE drivers SET profile=? WHERE id=?',
            (canonical({**d['profile'],'hidden':128,'learningBackend':'sb3-skill-1'}).decode(),d['id']))
        store.save_training(d['id'],{},fixture,0,0)
    measured_qualifying=[]
    if a.races_only:
        from game_lab.races import run
        for d in store.drivers():
            digest=d.get('candidate') or d['policy'];frozen=store.load(digest)
            measured=run([frozen],qualifying=True,laps=4)
            participant=dict(id=d['id'],policy=digest,profile=d['profile'])
            session,payload=store.begin_session('qualifica',dict(participants=[participant],profile=d['profile'],
                source='measured-headless-private-fixture',results=measured['results']))
            valid=[lap for lap in measured['results'][0]['lapTimes'] if lap['clean'] and not lap['standingStart']]
            assert valid,(d['name'],measured)
            for lap in valid:store.record_qualification(d['id'],digest,d['profile'],lap,session)
            store.finish_session(session,'complete',payload)
            measured_qualifying.append(dict(pilot=d['name'],policy=digest,bestLap=min(l['time'] for l in valid),
                laps=valid,method='actual frozen World simulation',scientificQualification=False))
    if a.theme=='apple':
        from theme_bundle import BundleManager,validate_project
        from PySide6.QtCore import qVersion
        bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    # A fresh native shader/QML cache can exceed the desktop's five-second
    # fixture allowance. Keep this separate from command/startup latency and
    # preserve diagnostics; production readiness/watchdog deadlines are intact.
    original_wait=LegacyHarness.wait_ready;cold_started=time.monotonic()
    def cold_wait(harness):
        from theme_test_support import wait_ready
        try:wait_ready(harness.app,harness.root,timeout=15);original_wait(harness)
        except Exception:
            (a.output/'initialization-failure.json').write_text(json.dumps(dict(seconds=time.monotonic()-cold_started,
                qmlWarnings=harness.messages,themeStatus=harness.service.status,themeError=harness.service.lastError),indent=2)+'\n')
            raise
    LegacyHarness.wait_ready=cold_wait
    try:h=LegacyHarness(base,dict(theme='base' if a.theme=='apple' else a.theme,variant='day',motion='normal',game=True))
    finally:LegacyHarness.wait_ready=original_wait
    cold_seconds=time.monotonic()-cold_started;rows=[]
    def wait(condition,seconds=40):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            h.pump(10);assert not h.messages,h.messages
            assert h.game.snapshot['runState']!='error',h.game.snapshot['message']
            if condition():return
        raise AssertionError(h.game.snapshot)
    def capture(name):
        h.pump(60);assert h.window.grabWindow().save(str(a.output/(name+'.png')))
    try:
        if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        h.expression('familyId="game"');h.wait_ready()
        cases=[('Crono','impara'),('Crono','impara_infinito'),('Crono','impara_sorpasso'),
               ('Memoria','impara_sorpasso'),('Linea','impara_sorpasso'),('Tattico','impara_sorpasso')]
        for name,mode in [] if a.races_only else cases[:1] if a.single_case else cases:
            if h.value('overlay')!='':h.expression('popOverlay()');h.wait_ready()
            h.expression('activateKey(9)');h.wait_ready();assert h.value('overlay')=='gameMenu'
            menu_prepare(h.game,name,mode);assert h.game.settingsAction('start',1)
            wait(lambda:h.game.snapshot['runState']=='running' and h.game.scene.get('meta',{}).get('backend')=='sb3-skill-1')
            wait(lambda:h.game.scene.get('meta',{}).get('learningStats',{}).get('decisions',0)>=128)
            assert len(h.game.scene['cars'])==(3 if mode=='impara_sorpasso' else 1)
            cameras=[]
            if name=='Crono' and mode=='impara_sorpasso':
                for _ in range(4):
                    h.expression('activateKey(8)');h.pump(100);cameras.append(h.game.snapshot['camera'])
                    capture(mode+'-'+h.game.snapshot['camera'])
                assert len(set(cameras))==4,cameras
                for _ in range(2):h.expression('activateKey(6)');h.pump(80)
            capture(name+'-'+mode)
            h.expression('activateKey(5)');wait(lambda:h.game.snapshot['runState']=='paused' and h.game.snapshot['saveState']=='saved')
            d=h.game._store.driver(h.game._selected);c=h.game._store.load(d['checkpoint'])
            assert c['backend']=='sb3-skill-1' and c['decisions']>=128
            rows.append(dict(pilot=name,mode=mode,decisions=c['decisions'],physicsSteps=c['steps'],cameras=cameras))
            h.game.stop();wait(lambda:h.game._process is None)
        races=[]
        if a.races_only:
            from check_game_menu import menu_value
            from PySide6.QtCore import QObject
            import math
            people=store.drivers()
            for count,order in ((2,'fastest_first'),(5,'slowest_first')):
                if h.value('overlay')!='':h.expression('popOverlay()');h.wait_ready()
                h.expression('activateKey(9)');h.wait_ready();menu_prepare(h.game,'Crono','gara')
                wanted={d['id'] for d in people[:count]};h.game.settingsAction('participants',1)
                for d in people:
                    if (d['id'] in h.game._settings.draft['participants'])!=(d['id'] in wanted):
                        assert h.game.settingsAction('participant:'+d['id'],1)
                h.game.settingsKey(7);menu_value(h.game,'laps',3);menu_value(h.game,'grid',order)
                assert h.game.settingsAction('start',1)
                wait(lambda:h.game.snapshot['runState']=='running' and len(h.game.scene.get('cars',[]))==count)
                started=time.monotonic();samples=0;last_camera=started;cameras=set()
                capture('race-'+str(count)+'-grid')
                while h.game.snapshot['runState']!='finished' and time.monotonic()-started<240:
                    h.pump(20);assert not h.messages,h.messages
                    assert h.game.snapshot['runState']!='error',h.game.snapshot['message']
                    assert {c['id'] for c in h.game.scene['cars']}==wanted
                    arenas=[v for v in h.root.findChildren(QObject,'gameArena') if v.property('visible')]
                    assert len(arenas)==1,len(arenas)
                    arena=arenas[0]
                    # Repeater delegates are visual children; their QObject
                    # ownership need not follow the QQuickItem parent chain.
                    items={c.objectName():c for c in arena.childItems()}
                    for i in range(count):
                        car=items.get('gameCar'+str(i));assert car and car.property('visible'),(i,list(items))
                        radius=math.hypot(car.property('width'),car.property('height'))/2
                        x=car.property('x')+car.property('width')/2;y=car.property('y')+car.property('height')/2
                        assert radius<=x<=arena.property('width')-radius,(i,x,arena.property('width'))
                        assert radius<=y<=arena.property('height')-radius,(i,y,arena.property('height'))
                    samples+=1;cameras.add(h.game.snapshot['camera'])
                    if time.monotonic()-last_camera>15:
                        h.expression('activateKey(8)');last_camera=time.monotonic();capture('race-'+str(count)+'-'+h.game.snapshot['camera'])
                assert h.game.snapshot['runState']=='finished',h.game.snapshot
                results=h.game.snapshot['leaderboard']['race'];assert len(results)==count
                races.append(dict(cars=count,laps=3,grid=order,sessionCompleted=True,
                    allArrived=all(r['status']=='arrivato' and r['lap']>=3 for r in results),
                    allCarsVisible=True,visibilitySamples=samples,cameras=sorted(cameras),results=results,
                    scientificQualification=False,sharedNeuralPreparation=True))
                capture('race-'+str(count)+'-finished');h.game.stop();wait(lambda:h.game._process is None)
        assert 'torch' not in sys.modules
        report=dict(status='passed',theme=a.theme,platform=os.environ['QT_QPA_PLATFORM'],coldHarnessSeconds=cold_seconds,window=[h.window.width(),h.window.height()],
            cases=rows,races=races,measuredQualifying=measured_qualifying,qmlWarnings=h.messages,torchInGui=False,scientificQualification=False,installed=False)
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    finally:h.close();private.cleanup()

if __name__=='__main__':main()
