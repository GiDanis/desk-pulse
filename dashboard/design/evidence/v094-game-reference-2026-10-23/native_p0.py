"""Authorized P0 qualification/deployment. Always restore the kiosk on error."""
from pathlib import Path
import hashlib,json,os,pwd,shutil,sqlite3,subprocess,time

H=Path('/var/lib/smartpc-dashboard');P=H/'p0p9-proof';S=H/'p0p9-project/dashboard'
T=H/'p0p9-test-project/dashboard'
G=H/'.local/share/SmartPC/SmartPC/game';R=Path('/opt/smartpc/dashboard')
PY=H/'game-runtime/bin/python';UID=pwd.getpwnam('smartpc').pw_uid
TMP=Path('/var/tmp/smartpc-p0p9-tests')


def state(game=G,preferences=None):
    preferences=preferences or H/'.config/SmartPC'
    with sqlite3.connect((game/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        digest=hashlib.sha256()
        for table in tables:
            for row in db.execute('SELECT * FROM "'+table+'" ORDER BY rowid'):
                digest.update(json.dumps([table,row],sort_keys=True).encode())
    return dict(database=digest.hexdigest(),artifacts={str(f.relative_to(game)):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in game.rglob('*') if f.is_file() and not f.name.startswith('game.sqlite')},
        preferences={str(f.relative_to(preferences)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in preferences.rglob('*') if f.is_file()})


def children(pid):
    result=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if int((p/'stat').read_text().split()[3])==pid:result.append(int(p.name))
        except (OSError,ValueError,IndexError):pass
    return result


def idle_guard():
    supervisor=int(subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID','--value']))
    gui=children(supervisor);assert len(gui)==1,('GUI identity',gui)
    for pid in children(gui[0]):
        proc=Path('/proc')/str(pid)
        command=(proc/'cmdline').read_bytes()
        if b'resource_tracker' in command:continue
        if b'game_process.py' in command:
            assert b'--child\x00metadata\x00' in command,('Learning process active; pause before intervention',pid)
            continue
        has_db=any(str(f.resolve()).endswith('/game/game.sqlite') for f in (proc/'fd').iterdir())
        assert has_db,('Possible learner/other child active; pause before intervention',pid)
    assert len(children(gui[0]))<=2,'Possible learner active'
    return dict(supervisor=supervisor,gui=gui[0],children=children(gui[0]))


def verify(root):
    m=json.loads((root/'release-manifest.json').read_text())
    for name,digest in m['sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    return m


def run():
    guard=idle_guard();manifest=verify(S);assert manifest['version']=='0.9.4-rc.2'
    store_bytes=sum(p.stat().st_size for p in G.rglob('*') if p.is_file())
    required=3*store_bytes+512*1024**2
    assert shutil.disk_usage(H).free>required,'Insufficient space for backup, isolated copy and test growth'
    stamp=time.strftime('%Y%m%d-%H%M%S');backup=H/'p0p9-backups'/stamp
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    before=state();(P/'pre-intervention.json').write_text(json.dumps(dict(idleGuard=guard,state=before,bootId=boot),indent=2)+'\n')
    for candidate in sorted((H/'p0p9-backups').glob('*'),reverse=True):
        if (candidate/'game/game.sqlite').exists() and state(candidate/'game',candidate/'preferences')==before:
            backup=candidate;break
    backup.mkdir(parents=True,exist_ok=True)
    TMP.mkdir(exist_ok=True);os.chown(TMP,UID,pwd.getpwnam('smartpc').pw_gid)
    subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
    rollback=R.with_name('dashboard-before-v094-rc2-'+stamp);installed=False
    try:
        if not (backup/'game').exists():
            shutil.copytree(G,backup/'game');shutil.copytree(H/'.config/SmartPC',backup/'preferences')
        for f in (backup/'game').rglob('*'):os.chown(f,UID,pwd.getpwnam('smartpc').pw_gid)
        os.chown(backup/'game',UID,pwd.getpwnam('smartpc').pw_gid)
        assert before==state(),'State changed during shutdown; preserve backup and audit before continuing'
        env=['HOME='+str(H),'SMARTPC_TEST_DATA_TMP='+str(TMP),'QT_QPA_PLATFORM=eglfs',
            'QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
            'QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
        fingerprint=hashlib.sha256((S/'release-manifest.json').read_bytes()).hexdigest()
        unit_sources={k:v for k,v in manifest['sha256'].items() if k!='check_game_session_ui.py'}
        unit_receipt=P/'arm-unit-receipt.json'
        if not unit_receipt.exists() or json.loads(unit_receipt.read_text()).get('sourceHashes')!=unit_sources:
            with (P/'arm-unit.txt').open('w') as log:
                subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),'-m','unittest',
                    'check_game_session_start','check_game_menu','check_game_process','check_theme_heartbeat','-v'],cwd=S,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
            unit_receipt.write_text(json.dumps(dict(status='passed',tests=13,manifestSha256=fingerprint,sourceHashes=unit_sources),indent=2)+'\n')
        rows=[]
        # The fixture injects CanvasScene into its test catalog. Its diagnostic
        # renderer belongs only to the private test project, never the runtime.
        assert (T/'fixtures/theme-runtime/renderers/CanvasScene.qml').exists()
        for name,digest in manifest['sha256'].items():assert hashlib.sha256((T/name).read_bytes()).hexdigest()==digest,name
        for theme in ('base','functional','apple'):
            arguments=['--theme',theme,'--store',str(backup/'game'),'--output',str(P/theme)]
            if theme=='apple':arguments+=['--soak-seconds','1800']
            with (P/('native-'+theme+'.txt')).open('w') as log:
                subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(T/'check_game_session_ui.py'),*arguments],
                    cwd=T.parent,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=2400)
            report=json.loads((P/theme/'report.json').read_text())
            assert report['window']==[960,640] and not report['qmlWarnings']
            rows.append(dict(theme=theme,sessions=len(report['rows'])))
            print('Native passed',theme,flush=True)
        assert before==state(),'Private native test changed production state'
        verify(S)
        os.replace(R,rollback)
        try:os.replace(S,R)
        except Exception:os.replace(rollback,R);raise
        installed=True
        subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
        deadline=time.monotonic()+40;health=None
        while time.monotonic()<deadline:
            main=int(subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID','--value']))
            guis=children(main)
            for f in (Path('/proc')/str(guis[0])/'root/tmp').glob('smartpc-theme-health-'+str(UID)+'/*.json') if guis else ():
                try:
                    value=json.loads(f.read_text())
                    if value['pid'] in guis and value.get('ready') and 0<=time.time()-value['time']<2:health=value;break
                except (OSError,ValueError,KeyError):pass
            if health:break
            time.sleep(.2)
        assert health,'No fresh heartbeat from current GUI'
        service=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','smartpc-dashboard',
            '-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts'],text=True).splitlines())
        assert service['ActiveState']=='active' and service['SubState']=='running'
        assert before==state(),'Production data or preferences changed at boot'
        assert boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        receipt=dict(status='passed',version=manifest['version'],files=len(manifest['sha256']),scope='P0 only',
            newModels=False,newTrainingBackend=False,backup=str(backup),rollback=str(rollback),
            productionStatePreserved=True,service=service,guiHeartbeat=health,native=rows,
            physicalHid=False,newOSReboot=False,manifestSha256=hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest())
        (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('P0 installed and heartbeat verified',manifest['version'],flush=True)
    except Exception:
        if installed:
            subprocess.run(['systemctl','stop','smartpc-dashboard'],check=False)
            failed=R.with_name('dashboard-failed-p0-'+stamp);os.replace(R,failed);os.replace(rollback,R)
        raise
    finally:
        subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)


if __name__=='__main__':run()
