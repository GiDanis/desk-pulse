"""Private EGLFS qualification, preserved paused roster, atomic rc18 installation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

H=Path('/var/lib/smartpc-dashboard')
P=H/'v09-pilot-improvement-proof';P.mkdir(exist_ok=True)
subprocess.run(['chown','smartpc:smartpc',str(P)],check=True)
PROJECT=H/'smartpc-v09-rc18-project';SOURCE=PROJECT/'dashboard'
RUNTIME=H/'smartpc-v09-rc18-runtime';TARGET=Path('/opt/smartpc/dashboard')
PY=H/'game-runtime/bin/python';GAME=H/'.local/share/SmartPC/SmartPC/game'
manifest=json.loads((RUNTIME/'release-manifest.json').read_text())
assert manifest['version']=='0.9.0-rc.18'
assert all(hashlib.sha256((RUNTIME/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())


def snapshot():
    with sqlite3.connect((GAME/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        tables={r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall()
            for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GAME/'policies').glob('*.json')}
    return dict(tables=tables,artifacts=artifacts)


def health(label):
    path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
    subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),
        'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
        'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',
        str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],
        check=True,stdout=subprocess.DEVNULL)
    return json.loads(path.read_text())


before=snapshot();assert not any(r[2]=='running' for r in before['tables']['sessions']),'Training still running'
initial=health('before-install');assert initial['version']=='0.9.0-rc.17' and not initial['manifestMismatches']
assert 'OK' in (H/'rc18-arm-checks.txt').read_text()
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
old=TARGET.with_name('dashboard-rc17-before-pilot-improvement')
stage=TARGET.with_name('dashboard-rc18-pilot-stage');switched=False
backup=Path('/var/backups')/time.strftime('smartpc-before-pilot-improvement-%Y%m%d-%H%M%S')
try:
    stable=snapshot()
    assert stable['artifacts']==before['artifacts']
    assert all(stable['tables'][t]==v for t,v in before['tables'].items() if t!='sessions')
    backup.mkdir(mode=0o700)
    def copy(src,dst):
        if Path(src).parent==GAME/'policies':os.link(src,dst);return dst
        return shutil.copy2(src,dst)
    shutil.copytree(GAME,backup/'game',copy_function=copy)
    shutil.copytree(H/'.config/SmartPC',backup/'config');os.sync()
    env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
        'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs',
        'QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
        'QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
    cases=[]
    for theme in ('base','functional','apple'):
        cases.append((theme+'-recipes',SOURCE/'check_game_pilot_improvement_ui.py',
            ['--theme',theme,'--output',str(P/(theme+'-recipes'))]))
    cases.append(('apple-neural-qualification',SOURCE/'check_game_driving_integrity_ui.py',
        ['--theme','apple','--source-checkpoint',str(H/'v09-driving-integrity-proof/evo-source.json'),
         '--output',str(P/'apple-neural-qualification')]))
    cases.append(('apple-settings-regression',SOURCE/'check_game_settings_ui.py',
        ['--theme','apple','--capture-dir',str(P/'apple-settings-regression')]))
    for label,script,args in cases:
        print('EGLFS '+label,flush=True)
        with (P/(label+'.txt')).open('w') as out:
            subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(script),*args],
                cwd=PROJECT,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=360)
        report=json.loads((P/label/'report.json').read_text())
        assert report['status']=='passed' and not report['qmlWarnings']
        print('Passed '+label,flush=True)
    assert snapshot()==stable,'Private tests changed production game data'
    assert not old.exists() and not stage.exists();stage.mkdir()
    for name,digest in manifest['sha256'].items():
        dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(RUNTIME/name,dest)
        assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
    shutil.copy2(RUNTIME/'release-manifest.json',stage/'release-manifest.json');os.sync()
    TARGET.rename(old);stage.rename(TARGET);switched=True;os.sync()
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    deadline=time.monotonic()+90
    while True:
        time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
        if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
        assert time.monotonic()<deadline,'GUI not ready'
    assert after['version']==manifest['version'] and not after['manifestMismatches']
    assert after['service']['NRestarts']=='0'
    assert initial['allPreferenceHashes']==after['allPreferenceHashes']
    assert initial['activeTheme']==after['activeTheme'] and initial['bootId']==after['bootId']
    final=snapshot();assert final['artifacts']==stable['artifacts']
    for table,rows in stable['tables'].items():
        actual=final['tables'][table]
        if table=='sessions':
            assert len(actual)==len(rows)
            assert all(x==y or (x[:2]==y[:2] and x[2] in ('paused','running') and y[2]=='interrupted' and x[3:]==y[3:]) for x,y in zip(rows,actual))
        else:assert actual==rows,table
    receipt=dict(status='passed',version=after['version'],files=len(manifest['sha256']),
        backup=str(backup),runtimeRollback=str(old),pilots=len(stable['tables']['drivers']),
        artifactCount=len(stable['artifacts']),originalPilotsAndArtifactsUnchanged=True,
        preferencesPreserved=True,activeTheme=after['activeTheme'],newOSReboot=False,
        service=after['service'],guiHeartbeat=after['guiHeartbeat'],
        manifestMismatches=after['manifestMismatches'],nativeCases=[c[0] for c in cases],
        finalManifestSha256=hashlib.sha256((TARGET/'release-manifest.json').read_bytes()).hexdigest(),
        noProductionTrainingOrPilotCreation=True)
    (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)
except BaseException:
    if switched:
        subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
        TARGET.rename(TARGET.with_name('dashboard-rc18-failed-pilot-improvement'));old.rename(TARGET)
    raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
