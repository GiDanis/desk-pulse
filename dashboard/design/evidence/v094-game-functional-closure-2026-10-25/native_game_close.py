"""Minimal authorized maintenance deployment; restore the kiosk on every failure."""
from pathlib import Path
import hashlib,json,os,pwd,runpy,shutil,subprocess,tarfile,time,traceback
M=runpy.run_path('/var/lib/smartpc-dashboard/p0p9-proof/native_p0.py')
H=M['H'];R=M['R'];G=M['G'];PY=M['PY'];UID=M['UID'];state=M['state'];verify=M['verify'];children=M['children']
BASE='02548ecdfabe0625e1b48657f2ac2222330dadeb3da08397bb3f6186bf75b2d7'
CANDIDATE='3218f94083f6d41972bc971a99b75f2e8847f9df96fb1ace4f61b468d71104a3'
W=H/'game-close-verified-20261025';P=W/'proof';S=W/'package';T=W/'project/dashboard'

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
    ui=T/'check_game_session_ui.py'
    shutil.copy2(H/'p0p9-proof/check_game_session_ui_fresh.py',ui)
    test_override=sha(ui)
    previous=H/'game-close-final-20261025/proof'
    prior_ui=H/'game-close-final-20261025/project/dashboard/check_game_session_ui.py'
    previous_override=sha(prior_ui)
    assert verify(H/'game-close-final-20261025/package')==manifest
    for name,digest in manifest['sha256'].items():
        if name!='check_game_session_ui.py':assert sha(prior_ui.parent/name)==digest,name
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
        for name in ('arm-units.log','arm-finish-window.log'):
            shutil.copy2(previous/name,P/name)
            assert (P/name).read_text().rstrip().endswith('OK')
        print('ARM 19 unit checks reused: identical runtime manifest',flush=True)
        rows=[]
        for theme in ('base','functional'):
            shutil.copytree(previous/theme,P/theme)
            shutil.copy2(previous/('native-'+theme+'.log'),P/('native-'+theme+'.log'))
            report=json.loads((P/theme/'report.json').read_text())
            assert len(report['rows'])==5 and report['window']==[960,640] and not report['qmlWarnings']
            assert all(r['state']=='passed' for r in report['rows'])
            rows.append(dict(theme=theme,sessions=5,raceCars=report['rows'][-1]['cars'],fullRace=False,reused=True))
        shutil.copytree(previous/'apple',P/'prior-apple-mode-checks')
        prior=json.loads((P/'prior-apple-mode-checks/report.json').read_text())
        assert len(prior['rows'])==5 and not prior['qmlWarnings']
        assert all(r['state']=='passed' for r in prior['rows'][:4])
        args=[str(PY),str(ui),'--theme','apple','--store',str(backup/'game'),'--output',str(P/'apple'),'--full-race','--race-only']
        call(args,T.parent,'native-apple.log',240)
        report=json.loads((P/'apple/report.json').read_text())
        assert report['window']==[960,640] and not report['qmlWarnings']
        race=report['rows'][-1]
        assert race['completed'] and 2<=race['cars']<=5 and len(race['results'])==race['cars']
        assert race['raceId'] and race['rules']['laps']==3
        assert all(r['status']=='arrivato' and r['lap']==3 for r in race['results'])
        rows.append(dict(theme='apple',sessions=5,previousModeSessions=4,freshRaceSessions=1,raceCars=race['cars'],fullRace=True,raceId=race['raceId'],laps=3))
        print('Native fresh race passed',race['cars'],'cars, 3 laps, matching race ID',flush=True)
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
                     privateUiInstrumentationSha256=test_override,reusedUiInstrumentationSha256=previous_override,staleResultCaptureExcluded=True,manifestSha256=CANDIDATE,
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
