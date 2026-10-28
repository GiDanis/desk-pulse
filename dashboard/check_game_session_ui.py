"""Real Main navigation/Start regression, saved models in a PRIVATE copy."""
from pathlib import Path
import argparse,json,os,shutil,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')
os.environ['SMARTPC_TEST_ASYNC_METADATA']='1'


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from check_game_menu import menu_prepare
    p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),required=True)
    p.add_argument('--store',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--race-only',action='store_true');p.add_argument('--full-race',action='store_true')
    p.add_argument('--soak-seconds',type=float,default=0.)
    p.add_argument('--backend',choices=('spawn','local'),default='spawn')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    private,base=isolate_process();project=Path(__file__).resolve().parents[1]
    def copy_private(source,target):
        # Policies are content-addressed immutable artifacts. Only the private
        # DB is copied; hard links avoid hundreds of MB of unrelated writeback.
        if Path(source).parent.name=='policies':
            try:os.link(source,target);return target
            except OSError:pass
        return shutil.copy2(source,target)
    shutil.copytree(a.store,base/'state/game',copy_function=copy_private)
    if a.theme=='apple':
        from theme_bundle import BundleManager,validate_project
        from PySide6.QtCore import qVersion
        bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=project/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    original_wait=LegacyHarness.wait_ready;original_init=LegacyHarness.__init__
    cold_started=time.monotonic()
    def cold_wait(harness):
        from theme_test_support import wait_ready
        try:
            wait_ready(harness.app,harness.root,timeout=15)
            original_wait(harness)
        except Exception:
            (a.output/'initialization-failure.json').write_text(json.dumps(dict(
                seconds=time.monotonic()-cold_started,qmlWarnings=harness.messages,
                themeStatus=harness.service.status,themeError=harness.service.lastError),indent=2)+'\n')
            raise
    LegacyHarness.wait_ready=cold_wait
    def observed_init(harness,*args,**kwargs):
        try:original_init(harness,*args,**kwargs)
        except Exception:
            service=getattr(harness,'game',None);reader=getattr(service,'_metadata_reader',None)
            (a.output/'constructor-failure.json').write_text(json.dumps(dict(
                seconds=time.monotonic()-cold_started,qmlWarnings=getattr(harness,'messages',[]),
                metadataError=getattr(service,'_storage_error',None),drivers=len(getattr(service,'_drivers',[])),
                ticket=getattr(service,'_metadata_ticket',None),readerStats=reader.last_stats if reader else {},
                pending=reader.pending if reader else None,inflight=reader.inflight if reader else None,
                processAlive=bool(reader and reader.process and reader.process.is_alive())),indent=2)+'\n')
            raise
    LegacyHarness.__init__=observed_init
    try:h=LegacyHarness(base,dict(theme=a.theme if a.theme!='apple' else 'base',variant='day',motion='normal',game=True,gameBackend=a.backend))
    finally:LegacyHarness.wait_ready=original_wait;LegacyHarness.__init__=original_init
    cold_seconds=time.monotonic()-cold_started
    def wait(condition,seconds=60):
        end=time.monotonic()+seconds
        while not condition() and time.monotonic()<end:
            h.pump(10)
            if h.game._run_state=='error':
                (a.output/'worker-failure.json').write_text(json.dumps(dict(message=h.game._message,
                    stages=list(getattr(h.game,'startup_diagnostics',[])),
                    pid=h.game._process.pid if h.game._process else None,
                    processAlive=bool(h.game._process and h.game._process.is_alive()),
                    exitCode=h.game._process.exitcode if h.game._process else None,
                    family=h.value('familyId'),overlay=h.value('overlay'),
                    themePreparing=h.value('themePreparing'),qmlWarnings=h.messages),indent=2)+'\n')
            assert h.game._run_state!='error',h.game._message
        assert condition(),h.game._message
    rows=[];latencies=[];started=time.monotonic()
    def key(value):
        start=time.monotonic();h.expression('activateKey('+str(value)+')')
        latencies.append((time.monotonic()-start)*1000);h.pump(20)
    try:
        if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        h.expression('familyId="game"');h.wait_ready()
        for mode in (() if a.race_only else ('impara','impara_infinito','impara_sorpasso','qualifica')):
            for name in ('Crono','Memoria','Linea','Tattico'):
                wait(lambda:h.game._process is None)
                if h.value('overlay')!='':h.expression('popOverlay()');h.wait_ready()
                key(9);h.wait_ready();menu_prepare(h.game,name,mode);h.pump(30)
                q=h.game._settings;count=len(q.rows())
                # Deliberately enter edit then leave with 8, without confirming 5.
                while q.selected!='mode':key(2)
                key(5);assert q.edit;key(8);assert q.edit is None
                for _ in range(count+2):key(8)
                assert q.selected=='start'
                for _ in range(count+2):key(2)
                assert q.selected=='mode'
                for _ in range(count+2):key(8)
                assert q.selected=='start'
                start=time.monotonic();key(5);wait(lambda:h.game._run_state=='running')
                assert h.value('overlay')==''
                wait(lambda:len(h.game.scene.get('cars',[]))>0)
                key(5);wait(lambda:h.game._run_state=='paused' and h.game._save_state=='saved')
                h.game.stop();wait(lambda:h.game._process is None)
                rows.append(dict(pilot=name,mode=mode,startSeconds=time.monotonic()-start,
                    saved=True,navigation='edit-down-bottom-top-bottom-Start',state='passed'))
                (a.output/'report.json').write_text(json.dumps(dict(theme=a.theme,window=[h.window.width(),h.window.height()],rows=rows,
                    inputCallMs=latencies,qmlWarnings=h.messages,physicalHid=False),indent=2)+'\n')
                assert not h.messages,h.messages
                print(name,mode,'navigation/start/save passed',flush=True)
        wait(lambda:h.game._process is None)
        if h.value('overlay')!='':h.expression('popOverlay()');h.wait_ready()
        key(9);h.wait_ready();menu_prepare(h.game,'Crono','gara');h.pump(40)
        q=h.game._settings
        # Use the participants picker and its enabled qualified versions.
        h.game.settingsAction('participants',1)
        for person in h.game._drivers:
            option=next(r for r in q.rows() if r['id']=='participant:'+person['id'])
            if option['enabled'] and person['id'] not in q.draft['participants']:
                h.game.settingsAction(option['id'],1)
        key(7)
        for _ in range(len(q.rows())+2):key(8)
        assert q.selected=='start'
        h.pump(100);assert h.window.grabWindow().save(str(a.output/'race-start-menu.png'))
        for _ in range(len(q.rows())+2):key(2)
        assert q.selected=='mode'
        for _ in range(len(q.rows())+2):key(8)
        key(5);wait(lambda:h.game._run_state=='running')
        expected=len(q.draft['participants']);wait(lambda:len(h.game.scene.get('cars',[]))==expected)
        deadline=time.monotonic()+(180 if a.full_race else 3)
        while h.game._run_state!='finished' and time.monotonic()<deadline:
            h.pump(20);assert len(h.game.scene.get('cars',[]))==expected
        if a.full_race:assert h.game._run_state=='finished'
        else:
            key(5);wait(lambda:h.game._run_state=='paused')
        rows.append(dict(mode='gara',state='passed',cars=expected,completed=h.game._run_state=='finished'))
        h.game.stop();wait(lambda:h.game._process is None)
        soak_round=0
        while time.monotonic()-started<a.soak_seconds:
            if h.value('overlay')!='':h.expression('popOverlay()');h.wait_ready()
            key(9);h.wait_ready()
            name=('Crono','Memoria','Linea','Tattico')[soak_round%4]
            mode=('qualifica','impara','impara_infinito','impara_sorpasso')[soak_round%4]
            menu_prepare(h.game,name,mode);h.pump(30);q=h.game._settings
            for value in [8]*(len(q.rows())+1)+[2]*(len(q.rows())+1)+[8]*(len(q.rows())+1):key(value)
            key(5);wait(lambda:h.game._run_state=='running')
            h.pump(1500);key(5);wait(lambda:h.game._run_state=='paused' and h.game._save_state=='saved')
            h.game.stop();wait(lambda:h.game._process is None)
            key(1);h.wait_ready();h.expression('familyId="game"');h.wait_ready()
            soak_round+=1
            (a.output/'soak-progress.json').write_text(json.dumps(dict(rounds=soak_round,seconds=time.monotonic()-started,
                maxInputCallMs=max(latencies),qmlWarnings=h.messages),indent=2)+'\n')
            assert not h.messages,h.messages
            if soak_round%5==0:print('mixed soak',soak_round,round(time.monotonic()-started),flush=True)
        if soak_round:rows.append(dict(mode='mixed-soak',rounds=soak_round,seconds=time.monotonic()-started))
        (a.output/'report.json').write_text(json.dumps(dict(theme=a.theme,coldHarnessSeconds=cold_seconds,window=[h.window.width(),h.window.height()],rows=rows,
            inputCallMs=latencies,qmlWarnings=h.messages,physicalHid=False),indent=2)+'\n')
        assert not h.messages,h.messages
        assert h.window.grabWindow().save(str(a.output/'final.png'))
    finally:h.close();private.cleanup()


if __name__=='__main__':main()
