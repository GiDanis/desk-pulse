"""Actual isolated Main/Worker: fixed roster, all learners and five-car races."""
import argparse,json,os,time,statistics
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def qualify(store,driver):
    from game_learning import Policy
    from game_simulation import World
    from game_catalog import RACE_PHYSICS_VERSION
    policy_hash,profile=store.qualification_candidate(driver['id']);policy=Policy(store.load(policy_hash))
    run,payload=store.begin_session('qualifica',dict(profile=profile,participants=[dict(id=driver['id'],name=driver['name'],number=driver['number'],policy=policy_hash,profile=profile)]))
    w=World(1,71,laps=2,track_id=store.track_id,physics=RACE_PHYSICS_VERSION,telemetry=True);w.reset(varied=False);w.native_sensors=True
    for _ in range(18000):
        w.step(policy.act(None,world=w),return_observations=False)
        if not w.active.any():break
    assert not w.retired[0] and w.lap_count[0]==2,(driver['name'],w.rows())
    for lap in w.lap_times[0]:
        if not lap['standingStart']:store.record_qualification(driver['id'],policy_hash,profile,lap,run)
    payload['results']=w.rows([driver['id']]);store.finish_session(run,'complete',payload)
    return w.lap_times[0][-1]['time']


def qualify_roster(store):
    """Measure each qualifier in a separate world with no fictitious rivals."""
    from game_learning import Policy
    from game_simulation import World
    from game_control import frozen_actions
    from game_catalog import RACE_PHYSICS_VERSION
    drivers=store.drivers();controllers=[];runs=[]
    for driver in drivers:
        ph,profile=store.qualification_candidate(driver['id']);controllers.append(Policy(store.load(ph)))
        person=dict(id=driver['id'],name=driver['name'],number=driver['number'],policy=ph,profile=profile)
        run,payload=store.begin_session('qualifica',dict(profile=profile,participants=[person],origin='Qualifica iniziale · simulazioni indipendenti'))
        runs.append((run,payload,person))
    # Independent one-car worlds: the traffic follower must never see the
    # other qualifying pilots as rivals in a shared numerical array.
    times={}
    import numpy as np
    for controller,(run,payload,person) in zip(controllers,runs):
        w=World(1,71,shared=False,laps=2,track_id=store.track_id,physics=RACE_PHYSICS_VERSION,telemetry=True)
        w.reset(varied=False);w.native_sensors=True
        w.enable_timing('qualifica').bind(0,person['id'],person['policy'])
        for _ in range(18000):
            w.step(np.array([controller.act(None,world=w,index=0)]),return_observations=False)
            if not w.active.any():break
        assert not w.retired[0] and w.lap_count[0]==2,w.rows()
        for lap in w.lap_times[0]:
            if not lap['standingStart']:store.record_qualification(person['id'],person['policy'],person['profile'],lap,run)
        store.save_timing(run,w.timing.drain())
        payload['results']=w.rows([person['id']]);store.finish_session(run,'complete',payload)
        times[person['name']]=w.lap_times[0][-1]['time']
    return times


def np_all(values):return bool(values.all())


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from theme_bundle import BundleManager,validate_project
    from PySide6.QtCore import qVersion
    p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),default='base');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--race-seconds',type=float,default=8);p.add_argument('--qualification',action='store_true')
    p.add_argument('--saved-root',type=Path);p.add_argument('--full-race',action='store_true');args=p.parse_args()
    private,base=isolate_process();project=Path(__file__).resolve().parents[1]
    if args.saved_root:
        from game_store import GameStore,canonical
        store=GameStore(base/'state/game');profiles=json.loads((args.saved_root/'profiles.json').read_text())
        for driver in store.drivers()[1:]:
            method=driver['profile']['algorithm'];c=json.loads((args.saved_root/(method+'.json')).read_text())
            with store.connect() as db:db.execute('UPDATE drivers SET profile=? WHERE id=?',(canonical(profiles[method]).decode(),driver['id']))
            original=store.artifact(c);c['sourceCheckpoint']=original
            candidate=json.loads(json.dumps(c['curriculum']['champion']['policy']));candidate['weights']=c['learner']['actor']
            store.save_training(driver['id'],c,candidate,c['steps'],c.get('seconds',0),c.get('metric',{}),c['curriculum'])
            with store.connect() as db:db.execute('UPDATE drivers SET profile=? WHERE id=?',(canonical(profiles[method]).decode(),driver['id']))
    if args.theme=='apple':
        bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text());assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,dict(theme=args.theme if args.theme!='apple' else 'base',variant='day',motion='normal',game=True));captures=[]
    args.output.mkdir(parents=True,exist_ok=True)
    def wait(f,seconds=45):
        end=time.monotonic()+seconds
        while not f() and time.monotonic()<end:h.pump(10)
        assert f(),h.game.snapshot
    def capture(name):
        h.pump(80);assert h.window.grabWindow().save(str(args.output/(name+'.png')));captures.append(name)
    try:
        if args.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
        assert [d['name'] for d in h.game.snapshot['drivers']]==['Maestro','Crono','Memoria','Linea','Tattico']
        h.expression('familyId="game"');h.wait_ready();capture('ready-oval-12m')
        learners=[]
        for name in ('Crono','Memoria','Linea','Tattico'):
            d=next(d for d in h.game._store.drivers() if d['name']==name)
            h.game.stop();assert h.game.selectDriver(d['id']);assert h.game.setMode('impara')
            start_steps=d['steps']
            assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and h.game.scene.get('meta',{}).get('steps',0)>start_steps+4000)
            capture(name.lower()+'-learning')
            if name=='Crono':
                from PySide6.QtCore import QObject
                assert h.game.snapshot['camera']=='circuito'
                h.expression('activateKey(8)');h.pump(80)
                assert h.game.snapshot['camera']=='segui'
                arena=next(x for x in h.window.findChildren(QObject,'gameArena') if x.property('visible'))
                assert arena.property('following');capture('crono-follow-oval')
                h.expression('activateKey(8)');h.pump(80)
                assert h.game.snapshot['camera']=='telemetria'
                panel=next(x for x in h.window.findChildren(QObject,'gameLearningPanel') if x.property('visible'))
                capture('crono-controls')
                h.expression('activateKey(6)');h.pump(80);assert h.game.snapshot['camera']=='premi';capture('crono-rewards')
                h.expression('activateKey(6)');h.pump(80);assert h.game.snapshot['camera']=='rete';capture('crono-network')
                h.expression('activateKey(8)');h.pump(80);assert h.game.snapshot['camera']=='sensori';capture('crono-sensors')
                h.expression('activateKey(8)');h.pump(80);assert h.game.snapshot['camera']=='circuito'
            assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved' and not h.game.captured)
            d=h.game._store.driver(d['id']);c=h.game._store.load(d['checkpoint'])
            assert c['protocol'] in ('race-residual-1','direct-driving-3') and c['decisions']>100
            if d['profile'].get('controlMode')=='direct':
                assert c['protocol']=='direct-driving-3' and c['curriculum']['execution']['teacherAtInference'] is False
                assert c['learner']['update']>0
            if args.saved_root:
                assert c['curriculum']['migration']['version']==('direct-racing-1' if d['profile'].get('controlMode')=='direct' else 'race-residual-4')
                assert c['curriculum']['recipeArchives'] and c['curriculum']['effectiveParameters']['criticInputs']==94
            learners.append(dict(name=name,method=d['profile']['algorithm'],control=d['profile'].get('controlMode','residual'),policyKind=h.game._store.load(d['policy'])['kind'],steps=d['steps'],decisions=c['decisions']))
        h.game.stop();h.expression('activateKey(9)');h.wait_ready();h.game.settingsAction('section:management',1)
        assert not any(r['id'] in ('create','transfer') for r in h.game.snapshot['settings']['rows']);capture('clean-roster-settings')
        h.expression('popOverlay()');h.wait_ready()
        gui_qualification=None
        if args.qualification:
            maestro=next(d for d in h.game._store.drivers() if d['name']=='Crono');h.game.stop()
            assert h.game.selectDriver(maestro['id']) and h.game.setMode('qualifica') and h.game.start()
            wait(lambda:any(q['id']==maestro['id'] for q in h.game.snapshot.get('leaderboard',{}).get('qualification',[])),130)
            capture('actual-flying-qualifying');gui_qualification=h.game.snapshot['leaderboard']['qualification']
            assert h.game.pause();wait(lambda:not h.game.captured);h.game.stop()
        timed=qualify_roster(h.game._store)
        h.game._refresh();assert h.game.setMode('gara')
        h.game._participants=[d['id'] for d in h.game._store.drivers()];h.game._race_laps=3;h.game._camera='circuito'
        assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and len(h.game.scene.get('cars',[]))==5)
        capture('five-grid')
        # Qt does not repaint unchanged stationary cars at 30 Hz during countdown.
        wait(lambda:h.game.scene.get('meta',{}).get('countdown',0)<=0 and h.game.scene.get('meta',{}).get('time',0)>1)
        frames=[];h.window.frameSwapped.connect(lambda:frames.append(time.monotonic()))
        started=time.monotonic();ids={d['id'] for d in h.game.scene['cars']}
        while time.monotonic()-started<args.race_seconds and h.game.snapshot['runState']!='finished':
            h.pump(10);assert len(h.game.scene['cars'])==5;assert {d['id'] for d in h.game.scene['cars']}==ids
            assert not h.messages,h.messages
        sampled_frames=frames[:]
        completed_race=h.game.snapshot['runState']=='finished'
        race_rows=h.game.scene['cars']
        if args.full_race:
            assert completed_race and all(r.get('status')=='arrivato' and r.get('lap')==3 for r in race_rows),race_rows
        capture('five-racing');h.game.pause();wait(lambda:not h.game.captured);h.game.stop()
        intervals=sorted(b-a for a,b in zip(sampled_frames,sampled_frames[1:]));timing=dict(samples=len(intervals),p95=intervals[int(len(intervals)*.95)] if intervals else None,maximum=max(intervals) if intervals else None)
        for d in h.game._store.drivers():
            h.expression('openPilotDetails('+json.dumps(d['id'])+')');h.wait_ready();h.expression('activateKey(6)');h.pump(40)
            assert not h.messages,h.messages
        capture('pilot-method')
        report=dict(status='passed',theme=args.theme,window=[h.window.width(),h.window.height()],roster=5,roadWidth=12,
            learners=learners,privateHeadlessQualifyingTimes=timed,actualGuiQualification=gui_qualification,fiveCarsVisible=True,completedRace=completed_race,raceResults=race_rows,frameTiming=timing,captures=captures,qmlWarnings=h.messages,
            scope='Isolated actual Main/Worker; headless physical qualifying per exact policy; no production changes or optical FPS claim')
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    finally:h.close();private.cleanup()


if __name__=='__main__':main()
