"""Real Main/Worker walkthrough through the settings menu, using private stores."""
from pathlib import Path
import argparse,json,os,shutil,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    p=argparse.ArgumentParser()
    p.add_argument('--theme',choices=('base','functional','apple'),required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--saved-root',type=Path)
    p.add_argument('--all-modes',action='store_true');p.add_argument('--full-race',action='store_true')
    p.add_argument('--export-store',type=Path);p.add_argument('--restore-store',type=Path)
    args=p.parse_args();private,base=isolate_process();project=Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True,exist_ok=True)
    from game_store import GameStore,canonical
    if args.restore_store:
        shutil.copytree(args.restore_store,base/'state/game')
    elif args.saved_root:
        seed=GameStore(base/'state/game');profiles=json.loads((args.saved_root/'profiles.json').read_text())
        for d in seed.drivers()[1:]:
            method=d['profile']['algorithm'];c=json.loads((args.saved_root/(method+'.json')).read_text())
            with seed.connect() as db:db.execute('UPDATE drivers SET profile=? WHERE id=?',(canonical(profiles[method]).decode(),d['id']))
            source=seed.artifact(c);c['sourceCheckpoint']=source
            candidate=json.loads(json.dumps(c['curriculum']['champion']['policy']));candidate['weights']=c['learner']['actor']
            seed.save_training(d['id'],c,candidate,c['steps'],c.get('seconds',0),c.get('metric',{}),c['curriculum'])
    if args.theme=='apple':
        from theme_bundle import BundleManager,validate_project
        from PySide6.QtCore import qVersion
        bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,dict(theme=args.theme if args.theme!='apple' else 'base',variant='day',motion='normal',game=True))
    from check_game_menu import menu_prepare,menu_value
    def wait(condition,seconds=180):
        end=time.monotonic()+seconds
        while not condition() and time.monotonic()<end:
            h.pump(10)
            assert h.game.snapshot['runState']!='error',h.game.snapshot
            assert not h.messages,h.messages
        assert condition(),h.game.snapshot
    def capture(name):
        h.pump(60);assert h.window.grabWindow().save(str(args.output/(name+'.png')))
    def prepare(name,mode):
        h.game.stop()
        if h.value('overlay')!='':h.expression('popOverlay()');h.wait_ready()
        h.expression('activateKey(9)');h.wait_ready();assert h.value('overlay')=='gameMenu'
        driver=menu_prepare(h.game,name,mode);h.pump(50)
        assert h.game.snapshot['settings']['draft']['profile']==driver['profile']
        return driver
    def start():
        assert h.game.settingsAction('start',1),h.game.snapshot
        wait(lambda:h.game.snapshot['runState']=='running')
        assert h.value('overlay')==''
    def pause():
        if h.game.snapshot['runState']=='finished':
            # finished is sent only after timing flush and durable session commit.
            h.game.stop();return
        assert h.game.pause()
        wait(lambda:h.game.snapshot['saveState']=='saved' and not h.game.captured)
        h.game.stop()
    sessions=[];qualifying_starts=[];race=None;reopened=bool(args.restore_store)
    try:
        if args.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
        h.expression('familyId="game"');h.wait_ready()
        modes=('impara','impara_infinito','impara_sorpasso') if args.all_modes and not reopened else ('impara',)
        for name in ('Crono','Memoria','Linea','Tattico'):
            for mode in modes:
                d=prepare(name,mode);before=h.game._store.load(d['checkpoint'])
                old_steps=before['steps'];old_updates=before['learner']['update']
                if mode=='impara':capture(name.lower()+'-menu')
                start()
                budget=1200 if reopened else 4000
                wait(lambda:h.game.scene.get('meta',{}).get('steps',0)>=old_steps+budget)
                capture(name.lower()+'-'+mode)
                pause();after=h.game._store.driver(d['id']);c=h.game._store.load(after['checkpoint'])
                assert c['steps']>=old_steps+budget and c['learner']['update']>old_updates,(name,mode,c['learner']['update'],old_updates)
                assert c['objective']==mode and after['profile']==d['profile']
                sessions.append(dict(name=name,mode=mode,previousSteps=old_steps,steps=c['steps'],
                    previousUpdates=old_updates,updates=c['learner']['update'],saved=True,reopened=reopened,
                    checkpoint=after['checkpoint'],policy=after['policy'],menuUsed=True))
                print(name,mode,'menu/update/save passed',flush=True)
        if not reopened:
            for name in ('Crono','Memoria','Linea','Tattico'):
                d=prepare(name,'qualifica');start()
                wait(lambda:len(h.game.scene.get('cars',[]))==1 and h.game.scene.get('meta',{}).get('time',0)>1)
                qualifying_starts.append(dict(name=name,oneCar=True,menuUsed=True));pause()
            from check_game_residual_ui import qualify_roster
            measured=qualify_roster(h.game._store);h.game._refresh()
            d=prepare('Crono','gara')
            assert h.game.settingsAction('participants',1)
            for person in h.game._store.drivers():
                if person['id'] not in h.game._settings.draft['participants']:
                    assert h.game.settingsAction('participant:'+person['id'],1),person['name']
            h.game.settingsKey(7)
            menu_value(h.game,'grid','slowest_first');menu_value(h.game,'laps',3)
            capture('five-qualified-menu');start()
            wait(lambda:len(h.game.scene.get('cars',[]))==5 and h.game.scene.get('meta',{}).get('time',0)>1)
            ids={r['id'] for r in h.game.scene['cars']};started=time.monotonic()
            while h.game.snapshot['runState']!='finished' and time.monotonic()-started<(180 if args.full_race else 8):
                h.pump(10);assert {r['id'] for r in h.game.scene['cars']}==ids and len(ids)==5
                assert not h.messages,h.messages
            finished=h.game.snapshot['runState']=='finished';results=h.game.scene['cars']
            if args.full_race:assert finished and all(r['status']=='arrivato' and r['lap']==3 for r in results),results
            capture('five-racing');pause()
            race=dict(fiveCarsVisible=True,completed=finished,results=results,grid='slowest_first',laps=3,measuredQualifying=measured,menuUsed=True)
        report=dict(status='passed',theme=args.theme,window=[h.window.width(),h.window.height()],sessions=sessions,
            qualifyingMenuStarts=qualifying_starts,race=race,qmlWarnings=h.messages,reopened=reopened,
            scope='Isolated actual Main/Worker. Menu selectors and keypad edits; no production or optical FPS claim.')
        assert report['window']==[960,640] and not report['qmlWarnings']
        if args.export_store:
            h.game.close();assert not args.export_store.exists()
            shutil.copytree(base/'state/game',args.export_store);args.export_store.chmod(0o700)
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('Menu UI passed',args.theme,'sessions',len(sessions),'reopened',reopened,flush=True)
    finally:h.close();private.cleanup()


if __name__=='__main__':main()
