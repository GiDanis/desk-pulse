"""Manifest checked candidate installation with a persistent backup and rollback."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

H=Path('/var/lib/smartpc-dashboard');P=H/'v09-settings-circuits-install-proof'
SOURCE=H/'smartpc-v09-rc7-runtime';TARGET=Path('/opt/smartpc/dashboard')
DROP=Path('/etc/systemd/system/smartpc-dashboard.service.d/90-game-python.conf')
PY=H/'game-runtime/bin/python';HEALTH=H/'v086-source-proof/board-health.py'
P.mkdir(exist_ok=True);subprocess.run(['chown','smartpc:smartpc',str(P)],check=True)
manifest=json.loads((SOURCE/'release-manifest.json').read_text())
assert manifest['version']=='0.9.0-rc.7'
assert all(hashlib.sha256((SOURCE/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
     'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen']
def health(name):
    subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(HEALTH),'--output',str(P/(name+'.json'))],
                   check=True,stdout=subprocess.DEVNULL)
    return json.loads((P/(name+'.json')).read_text())

def pilots():
    result={}
    base=H/'.local/share/SmartPC'
    if not base.exists():return result
    for path in base.rglob('game.sqlite'):
        with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            cols=[r[1] for r in db.execute('PRAGMA table_info(drivers)')]
            values=[dict(r) for r in db.execute('SELECT '+','.join(cols)+' FROM drivers ORDER BY number')]
        result[str(path.relative_to(base))]=hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()
    return result
prior_pilots=pilots()

before=health('before');assert before['service']['ActiveState']=='active' and not before['manifestMismatches']
backup=Path('/var/backups')/time.strftime('smartpc-before-v09-%Y%m%d-%H%M%S')
backup.mkdir(mode=0o700)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    shutil.copytree(TARGET,backup/'runtime')
    private=[H/'.config/SmartPC',H/'.local/share/SmartPC']
    for i,path in enumerate(private):
        if path.exists():shutil.copytree(path,backup/('private-'+str(i)))
    if DROP.exists():shutil.copy2(DROP,backup/'python-dropin')
    shutil.rmtree(TARGET);shutil.copytree(SOURCE,TARGET)
    DROP.parent.mkdir(exist_ok=True)
    DROP.write_text('[Service]\nEnvironment=SMARTPC_PYTHON='+str(PY)+'\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','reset-failed','smartpc-dashboard'],check=True)
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    deadline=time.monotonic()+120
    while True:
        time.sleep(3);after=health('installed')
        gui=after.get('guiHeartbeat') or {}
        if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
        if time.monotonic()>deadline:raise RuntimeError('GUI non pronta entro 120 secondi')
    assert after['version']==manifest['version'] and not after['manifestMismatches']
    assert after['allPreferenceHashes']==before['allPreferenceHashes'],'Preferenze cambiate'
    assert after['activeTheme']==before['activeTheme'],'Tema cambiato'
    assert after['service']['NRestarts']=='0'
    assert pilots()==prior_pilots,'Piloti precedenti modificati'
    (P/'pilots-preserved.json').write_text(json.dumps({'preserved':True,'registryHashes':prior_pilots},indent=2)+'\n')
    (P/'install.json').write_text(json.dumps({'status':'passed','version':manifest['version'],
        'files':len(manifest['sha256']),'backup':str(backup),'beforeBootId':before['bootId'],
        'preferencesPreserved':True,'themePreserved':True,'python':str(PY)},indent=2)+'\n')
    print('Installazione verificata: '+manifest['version'],flush=True)
except BaseException:
    subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
    if (backup/'runtime').exists():
        shutil.rmtree(TARGET,ignore_errors=True);shutil.copytree(backup/'runtime',TARGET)
    for i,path in enumerate(private):
        shutil.rmtree(path,ignore_errors=True)
        if (backup/('private-'+str(i))).exists():
            shutil.copytree(backup/('private-'+str(i)),path)
            subprocess.run(['chown','-R','smartpc:smartpc',str(path)],check=True)
    if (backup/'python-dropin').exists():shutil.copy2(backup/'python-dropin',DROP)
    else:DROP.unlink(missing_ok=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    raise
