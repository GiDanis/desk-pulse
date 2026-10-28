"""Preserving installation with an actual runtime rollback/reinstall rehearsal."""
from contextlib import closing
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

STATE_ROOT=Path('/var/lib/smartpc-dashboard')
PROOF=STATE_ROOT/'v093-proof'
SOURCE=STATE_ROOT/'v093-runtime/dashboard'
TARGET=Path('/opt/smartpc/dashboard')
DATA=STATE_ROOT/'.local/share/SmartPC/SmartPC'
GAME=DATA/'game'
PY=STATE_ROOT/'game-runtime/bin/python'
MANIFEST=json.loads((SOURCE/'release-manifest.json').read_text())
assert MANIFEST['version']=='0.9.3-rc.1'
assert MANIFEST['distributionKind']=='runtime'
assert all(hashlib.sha256((SOURCE/n).read_bytes()).hexdigest()==v for n,v in MANIFEST['sha256'].items())
assert not (SOURCE/'fixtures/theme-runtime/renderers').exists()
native=json.loads((PROOF/'native-wire-final/receipt.json').read_text())
assert native['status']=='passed'
# The only native/package difference is diagnostics; compare every shipped file.
pc=json.loads((PROOF/'final-pc-gates.json').read_text())
assert pc['status']=='passed'
arm=json.loads((PROOF/'arm-final/receipt.json').read_text())
assert arm['status']=='passed' and arm['sourceManifest']==native['sourceManifest']
assert all(native['sourceManifest']['sha256'].get(n)==v and
           pc['productSourceHashes'].get(n)==v
           for n,v in MANIFEST['sha256'].items()),'Qualified product bytes differ'
assert (SOURCE/'libsmartpc_game_native.so').read_bytes()[18:20]==b'\xb7\x00','Expected unchanged AArch64 native library'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)):digest(p) for p in root.rglob('*') if p.is_file()}


def database_state(root):
    with closing(sqlite3.connect((root/'game.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert not db.execute("SELECT 1 FROM sessions WHERE status IN ('running','paused')").fetchall(),'Production game is active'
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {name:dict(rows=db.execute('SELECT count(*) FROM "'+name+'"').fetchone()[0],
            sha256=hashlib.sha256(json.dumps(db.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall(),
                ensure_ascii=False,separators=(',',':')).encode()).hexdigest()) for name in tables}


def health(label):
    output=PROOF/(label+'.json')
    output.touch()
    subprocess.run(['chown','smartpc:smartpc',str(output)],check=True)
    subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(STATE_ROOT),
        'XDG_CONFIG_HOME='+str(STATE_ROOT/'.config'),'XDG_DATA_HOME='+str(STATE_ROOT/'.local/share'),
        'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',
        str(PY),str(STATE_ROOT/'v086-source-proof/board-health.py'),'--output',str(output)],
        check=True,stdout=subprocess.DEVNULL)
    return json.loads(output.read_text())


def ready(label,version,old_pid):
    deadline=time.monotonic()+90
    while True:
        time.sleep(2)
        current=health(label)
        beat=current.get('guiHeartbeat') or {}
        if (current['service']['ActiveState']=='active' and beat.get('ready')
            and beat.get('ageSeconds',999)<5 and beat.get('pid')==current['runtimePid']
            and not beat.get('pending') and current['runtimePid']!=old_pid):
            assert current['version']==version and not current['manifestMismatches']
            assert current['service']['NRestarts']=='0'
            assert current['allPreferenceHashes']==before['allPreferenceHashes']
            assert current['activeTheme']==before['activeTheme']
            return current
        assert time.monotonic()<deadline,'Current coherent GUI not ready'


def exchange(left,right):
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.renameat2(-100,os.fsencode(left),-100,os.fsencode(right),2):
        error=ctypes.get_errno()
        raise OSError(error,os.strerror(error))


before=health('before-install')
assert before['version']=='0.9.0-rc.28' and not before['manifestMismatches']
production_manifest=json.loads((TARGET/'release-manifest.json').read_text())['sha256']
source_changes=sorted(n for n,v in MANIFEST['sha256'].items() if production_manifest.get(n)!=v)
assert set(source_changes)==set(('Main.qml','app.py','check_game_fluidity_ui.py','check_sport_ui.py',
    'check_state_availability.py','check_system_performance.py','components/PublicContextAdapter.qml',
    'event_core.py','game.py','game_metadata.py','game_settings.py','game_store.py','run.sh','sport.py',
    'state.py','theme_fixture_support.py','verify_performance_ui.py','version.py'))
assert not set(production_manifest)-set(MANIFEST['sha256'])

assert digest(SOURCE/'game_native.c')==digest(TARGET/'game_native.c')
assert digest(SOURCE/'libsmartpc_game_native.so')==digest(TARGET/'libsmartpc_game_native.so')
assert (before.get('guiHeartbeat') or {}).get('ready')
database_state(GAME)
stamp=time.strftime('%Y%m%d-%H%M%S')
stage=TARGET.with_name('dashboard-before-v093-'+stamp)
backup=STATE_ROOT/'v093-backups'/stamp
backup.mkdir(parents=True,mode=0o700)
shutil.copytree(SOURCE,stage)
assert all(digest(stage/n)==v for n,v in MANIFEST['sha256'].items())
subprocess.run(['systemctl','stop','smartpc-dashboard.service'],check=True)
switched=False
backup_complete=False
candidate_started=False
try:
    original=inventory(GAME)
    rows=database_state(GAME)
    configuration=inventory(STATE_ROOT/'.config/SmartPC')
    subprocess.run(['cp','-a',str(DATA),str(backup/'application-data')],check=True)
    subprocess.run(['cp','-a',str(STATE_ROOT/'.config/SmartPC'),str(backup/'preferences')],check=True)
    assert inventory(backup/'application-data/game')==original
    assert database_state(backup/'application-data/game')==rows
    backup_complete=True
    if (STATE_ROOT/'events.sqlite3').exists():
        with closing(sqlite3.connect((STATE_ROOT/'events.sqlite3').as_uri()+'?mode=ro',uri=True)) as source:
            with closing(sqlite3.connect(backup/'events.sqlite3')) as destination:
                source.backup(destination)
                assert destination.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    os.sync()
    exchange(TARGET,stage)
    switched=True
    candidate_started=True
    subprocess.run(['systemctl','start','smartpc-dashboard.service'],check=True)
    installed=ready('installed-first','0.9.3-rc.1',before['runtimePid'])
    # Prove the saved runtime can still run, without touching durable user data.
    subprocess.run(['systemctl','stop','smartpc-dashboard.service'],check=True)
    exchange(TARGET,stage)
    switched=False
    subprocess.run(['systemctl','start','smartpc-dashboard.service'],check=True)
    restored=ready('rollback-rehearsal','0.9.0-rc.28',installed['runtimePid'])
    assert database_state(GAME)==rows
    subprocess.run(['systemctl','stop','smartpc-dashboard.service'],check=True)
    exchange(TARGET,stage)
    switched=True
    subprocess.run(['systemctl','start','smartpc-dashboard.service'],check=True)
    after=ready('installed-final','0.9.3-rc.1',restored['runtimePid'])
    assert database_state(GAME)==rows
    assert inventory(STATE_ROOT/'.config/SmartPC')==configuration
    current=inventory(GAME)
    assert all(current.get(n)==v for n,v in original.items() if not n.startswith('game.sqlite'))
    receipt=dict(status='passed',version=MANIFEST['version'],files=len(MANIFEST['sha256']),sourceChanges=source_changes,
        nativeQualification=str(PROOF/'native-wire-final/receipt.json'),nativeQualificationSha256=digest(PROOF/'native-wire-final/receipt.json'),
        pcQualificationSha256=digest(PROOF/'final-pc-gates.json'),armQualificationSha256=digest(PROOF/'arm-final/receipt.json'),
        manifestSha256=digest(TARGET/'release-manifest.json'),runtimeRollback=str(stage),
        dataBackup=str(backup),atomicExchange=True,runtimeRollbackActuallyRehearsed=True,
        allGameTablesPreserved=rows,originalArtifactFilesPreserved=True,preferencesPreserved=True,
        activeTheme=after['activeTheme'],allPreferenceHashes=after['allPreferenceHashes'],currentGuiHeartbeat=after['guiHeartbeat'],service=after['service'],
        bootId=after['bootId'],noProductionTrainingStarted=True,noRecipeMigration=True,
        themeApi='2.11',newOSReboot=False,scope='Installed candidate; extended/live/physical gates remain separate')
    (PROOF/'installation-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)
except BaseException:
    subprocess.run(['systemctl','stop','smartpc-dashboard.service'],check=True)
    if switched:exchange(TARGET,stage)
    # Only the failed activation journal/preferences can be restored here;
    # provider events and game writes are never rewound by a runtime rollback.
    if backup_complete and candidate_started:
        subprocess.run(['cp','-a',str(backup/'preferences')+'/.',str(STATE_ROOT/'.config/SmartPC')],check=True)
        for path in DATA.glob('theme*'):
            if path.is_dir():shutil.rmtree(path)
            else:path.unlink()
        for path in (backup/'application-data').glob('theme*'):
            subprocess.run(['cp','-a',str(path),str(DATA/path.name)],check=True)
    os.sync()
    raise
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard.service'],check=True)
