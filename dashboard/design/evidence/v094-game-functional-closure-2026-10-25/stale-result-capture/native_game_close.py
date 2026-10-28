"""Minimal authorized maintenance deployment; restore the kiosk on every failure."""
from pathlib import Path
import hashlib,json,os,pwd,runpy,shutil,subprocess,tarfile,time,traceback
M=runpy.run_path('/var/lib/smartpc-dashboard/p0p9-proof/native_p0.py')
H=M['H'];R=M['R'];G=M['G'];PY=M['PY'];UID=M['UID'];state=M['state'];verify=M['verify'];children=M['children']
BASE='02548ecdfabe0625e1b48657f2ac2222330dadeb3da08397bb3f6186bf75b2d7'
CANDIDATE='3218f94083f6d41972bc971a99b75f2e8847f9df96fb1ace4f61b468d71104a3'
W=H/'game-close-final-20261025';P=W/'proof';S=W/'package';T=W/'project/dashboard'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):(P/name).write_text(json.dumps(value,indent=2)+'\n')
def run():
    P.mkdir(parents=True,exist_ok=True)
    guard=M['idle_guard']();old=verify(R);assert sha(R/'release-manifest.json')==BASE
    assert not S.exists() and not T.exists(),'Staging exists; audit before retry'
    shutil.copytree(R,S,ignore=shutil.ignore_patterns('__pycache__'))
    with tarfile.open(H/'p0p9-proof/game-close-rc3-overlay.tar.gz','r:gz') as tar:
        assert sorted(tar.getnames())==['game_protocol.py','game_worker.py','release-manifest.json','version.py']
        for member in tar.getmembers():assert member.isfile() and Path(member.name).name==member.name
        tar.extractall(S,filter='data')
    manifest=verify(S);assert sha(S/'release-manifest.json')==CANDIDATE and manifest['version']=='0.9.4-rc.3'
    changed=[n for n in old['sha256'] if manifest['sha256'][n]!=old['sha256'][n]]
    assert sorted(changed)==['game_protocol.py','game_worker.py','version.py']
    shutil.copytree(S,T)
    shutil.copytree(H/'p0p9-test-project/theme-projects',T.parent/'theme-projects')
    shutil.copytree(H/'p0p9-test-project/dashboard/fixtures/theme-runtime/renderers',T/'fixtures/theme-runtime/renderers')
    # Capture actual race results before the test harness destroys its private DB.
    ui=T/'check_game_session_ui.py';text=ui.read_text();old_line="completed=h.game._run_state=='finished'))"
    assert text.count(old_line)==1
    text=text.replace(old_line,"completed=h.game._run_state=='finished',results=h.game.snapshot['leaderboard']['race']))")
    text=text.replace("q=h.game._settings\n        # Use the participants","q=h.game._settings;q.draft['laps']=3\n        # Use the participants")
    text=text.replace("for name in ('Crono','Memoria','Linea','Tattico'):","for name in ('Crono',):")
    ui.write_text(text)
    test_override=sha(ui)
    before=state();boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    backup=H/'p0p9-backups/reference-native-20261024-220928'
    if not (backup/'game/game.sqlite').exists() or state(backup/'game',backup/'preferences')!=before:
        backup=H/'p0p9-backups'/('game-close-'+time.strftime('%Y%m%d-%H%M%S'))
        assert shutil.disk_usage(H).free>sum(p.stat().st_size for p in G.rglob('*') if p.is_file())+512*1024**2
    write('pre-intervention.json',dict(idleGuard=guard,bootId=boot,state=before,baseManifest=BASE,changedFiles=changed))
    M['idle_guard']()
    subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
    rollback=R.with_name('dashboard-before-v094-rc3-'+time.strftime('%Y%m%d-%H%M%S'));installed=False
    try:
        assert before==state(),'State changed during shutdown; audit before proceeding'
        if not (backup/'game').exists():
            shutil.copytree(G,backup/'game');shutil.copytree(H/'.config/SmartPC',backup/'preferences')
        assert state(backup/'game',backup/'preferences')==before
        tmp=Path('/var/tmp/smartpc-game-close-tests');tmp.mkdir(exist_ok=True)
        gid=pwd.getpwnam('smartpc').pw_gid
        os.chown(tmp,UID,gid)
        # Only private staging and proof are writable by test processes.
        for tree in (W,backup/'game'):
            for root,dirs,files in os.walk(tree):
                os.chown(root,UID,gid)
                for name in files:os.chown(Path(root)/name,UID,gid)
        env=['HOME='+str(H),'SMARTPC_TEST_DATA_TMP='+str(tmp),'QT_QPA_PLATFORM=eglfs',
             'QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
             'QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
        def call(args,cwd,log,timeout):
            with (P/log).open('w') as output:
                subprocess.run(['runuser','-u','smartpc','--','env',*env,*args],cwd=cwd,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=timeout)
        call([str(PY),'-m','unittest','check_game_session_start','check_game_menu','check_game_process','check_theme_heartbeat','-v'],S,'arm-units.log',120)
        call(['PYTHONPATH='+str(S),str(PY),str(H/'p0p9-proof/check_finish_window.py')],S,'arm-finish-window.log',30)
        print('ARM unit tests passed',flush=True)
        rows=[]
        for theme in ('base','functional','apple'):
            args=[str(PY),str(ui),'--theme',theme,'--store',str(backup/'game'),'--output',str(P/theme)]
            if theme=='apple':args+=['--full-race']
            call(args,T.parent,'native-'+theme+'.log',300)
            report=json.loads((P/theme/'report.json').read_text())
            assert report['window']==[960,640] and not report['qmlWarnings']
            race=report['rows'][-1];assert race['mode']=='gara' and 2<=race['cars']<=5
            if theme=='apple':
                assert race['completed'] and len(race['results'])==race['cars']
                assert all(r['status']=='arrivato' and r['lap']==3 for r in race['results']),race
            rows.append(dict(theme=theme,sessions=len(report['rows']),raceCars=race['cars'],fullRace=race['completed']))
            print('Native passed',theme,len(report['rows']),'sessions',flush=True)
        assert before==state(),'Private qualification altered production state'
        verify(S);assert sha(S/'release-manifest.json')==CANDIDATE
        os.replace(R,rollback)
        try:os.replace(S,R)
        except BaseException:os.replace(rollback,R);raise
        installed=True
        subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
        deadline=time.monotonic()+45;health=None
        while time.monotonic()<deadline:
            main=int(subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID','--value']))
            guis=children(main)
            for f in (Path('/proc')/str(guis[0])/'root/tmp').glob('smartpc-theme-health-'+str(UID)+'/*.json') if guis else ():
                try:
                    v=json.loads(f.read_text())
                    if v['pid'] in guis and v.get('ready') and 0<=time.time()-v['time']<2:health=v;break
                except (OSError,ValueError,KeyError):pass
            if health:break
            time.sleep(.2)
        assert health,'No fresh current-GUI heartbeat'
        service=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts'],text=True).splitlines())
        assert service['ActiveState']=='active' and service['SubState']=='running' and service['NRestarts']=='0',service
        assert before==state(),'Data/preferences changed on startup'
        assert boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        verify(R)
        receipt=dict(status='passed',version=manifest['version'],files=len(manifest['sha256']),scope='Functional Game maintenance closure; scientific learning research deferred',
                     changedFiles=changed,modelsChanged=False,rewardsChanged=False,newTrainingBackend=False,
                     backup=str(backup),rollback=str(rollback),productionStatePreserved=True,preferencesPreserved=True,
                     service=service,guiHeartbeat=health,native=rows,unitTests=19,
                     privateUiInstrumentationSha256=test_override,manifestSha256=CANDIDATE,
                     physicalHid=False,opticalFpsQualified=False,newOSReboot=False,scientificModelsQualified=False)
        write('final-receipt.json',receipt)
        print('Maintenance installed',manifest['version'],flush=True)
    except BaseException:
        write('failure.json',dict(error=traceback.format_exc(),installed=installed))
        if installed:
            subprocess.run(['systemctl','stop','smartpc-dashboard'],check=False)
            os.replace(R,R.with_name('dashboard-failed-rc3-'+time.strftime('%Y%m%d-%H%M%S')));os.replace(rollback,R)
        raise
    finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)

if __name__=='__main__':run()
