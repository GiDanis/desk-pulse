"""Explicitly authorized full Game reset, using the installed runtime only.

No new learning recipe is installed. All previous Game data is removed from
active storage together, with a complete external recovery copy.
"""
from pathlib import Path
import hashlib,json,os,shutil,sqlite3,subprocess,sys,time
from contextlib import closing
H=Path('/var/lib/smartpc-dashboard');GAME=H/'.local/share/SmartPC/SmartPC/game';P=H/'v09-full-reset-proof';PY=H/'game-runtime/bin/python';R=Path('/opt/smartpc/dashboard')
P.mkdir(exist_ok=True);P.chmod(0o755)
sys.path.insert(0,str(R))
from game_store import GameStore
from game_residual_migration import exchange


def inventory(root):
    return {str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()}


def health(label):
    path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
    subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
    return json.loads(path.read_text())


def fresh_state(root):
    with closing(sqlite3.connect((root/'game.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        tables={r[0]:db.execute('SELECT COUNT(*) FROM '+r[0]).fetchone()[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        drivers=[dict(r) for r in db.execute('SELECT id,name,number,checkpoint,steps,seconds,candidate,curriculum FROM drivers ORDER BY number')]
        assert [d['name'] for d in drivers]==['Maestro','Crono','Memoria','Linea','Tattico']
        assert all(d['checkpoint'] is None and d['steps']==0 and d['seconds']==0 and d['candidate'] is None and d['curriculum'] is None for d in drivers)
        assert all(v==0 for k,v in tables.items() if k!='drivers'),tables
        policies=[r[0] for r in db.execute('SELECT policy FROM drivers')]
        assert len(set(policies))==5 and len(list((root/'policies').glob('*.json')))==5
        return dict(drivers=drivers,tables=tables,policyCount=5,integrity='ok',foreignKeysValid=True)


before=health('before');assert before['version']=='0.9.0-rc.24' and not before['manifestMismatches']
manifest_hash=hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest()
stamp=time.strftime('%Y%m%d-%H%M%S');stage=GAME.with_name('game-full-reset-stage-'+stamp);backup=H/'game-backups'/('before-full-reset-'+stamp)
assert not stage.exists() and not backup.exists()
GameStore(stage);expected=fresh_state(stage)
subprocess.run(['chown','-R','smartpc:smartpc',str(stage)],check=True);stage.chmod(0o700)
config_before=inventory(H/'.config/SmartPC');swapped=False
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    assert subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState','--value'],text=True).strip()=='inactive'
    original=inventory(GAME)
    shutil.copytree(H/'.config/SmartPC',backup.with_name(backup.name+'-config'))
    os.sync();exchange(GAME,stage);swapped=True;stage.rename(backup);backup.chmod(0o700);os.sync()
    assert inventory(backup)==original,'External recovery copy differs'
    assert fresh_state(GAME)==expected
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    deadline=time.monotonic()+90
    while True:
        time.sleep(3);after=health('after');gui=after.get('guiHeartbeat') or {}
        if (after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5
                and not gui.get('pending') and gui.get('pid')==after['runtimePid'] and after['runtimePid']!=before['runtimePid']):break
        assert time.monotonic()<deadline,'GUI not ready'
    assert after['version']==before['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
    assert after['allPreferenceHashes']==before['allPreferenceHashes'] and after['activeTheme']==before['activeTheme'] and after['bootId']==before['bootId']
    assert inventory(H/'.config/SmartPC')==config_before
    assert hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest()==manifest_hash
    final=fresh_state(GAME);assert final==expected
    receipt=dict(status='passed',operation='full-game-reset',authorization='User: Si puoi azzerare tutto erano solo prove',
        resetScope=['all pilots training weights/checkpoints','all tracks and objectives','qualifications','lap and speed records','races','sessions','history','personal driving memory'],
        version=after['version'],files=after['files'],runtimeChanged=False,directDrivingActivated=False,
        backup=str(backup),backupFiles=len(original),backupHashesPreserved=True,newGame=final,
        newPilotIds=True,oldCheckpointsAbsentFromActiveStore=True,activePolicies='Five freshly generated baseline policies only; no trained study/user artifact copied',allPreferenceHashesPreserved=True,preferenceFilesPreserved=True,
        activeTheme=after['activeTheme'],service=after['service'],guiHeartbeat=after['guiHeartbeat'],liveGuiPidVerified=True,
        newOSReboot=False,manifestMismatches=after['manifestMismatches'],manifestSha256=manifest_hash,
        nextStep='New direct-control path remains under qualification; no study model imported')
    (P/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
    if swapped:
        subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
        original_root=backup if backup.exists() else stage
        exchange(GAME,original_root);os.sync()
    raise
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
