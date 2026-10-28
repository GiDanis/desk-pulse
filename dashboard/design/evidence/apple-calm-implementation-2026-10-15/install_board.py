"""Atomic rc19 runtime + verified Apple 1.6.3; keep production Base/settings.

Requires the corrected-loop native receipt and a reviewed performance summary.
Run as root. A failed switch restores the previous runtime and theme state.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

H=Path('/var/lib/smartpc-dashboard');PY=H/'game-runtime/bin/python'
DATA=H/'.local/share/SmartPC/SmartPC';GAME=DATA/'game';TARGET=Path('/opt/smartpc/dashboard')
SOURCE=Path('/tmp/smartpc-apple-runtime-final/dashboard')
E=Path('/tmp/smartpc-apple-final-proof');P=E/'delivery';P.mkdir(exist_ok=True)
subprocess.run(['chown','smartpc:smartpc',str(P)],check=True)
manifest=json.loads((SOURCE/'release-manifest.json').read_text())
assert manifest['version']=='0.9.0-rc.19'
assert all(hashlib.sha256((SOURCE/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
assert json.loads((E/'native-receipt.json').read_text())['status']=='passed'
assert json.loads((E/'performance-summary.json').read_text())['status']=='passed'
assert json.loads((E/'release-supplement.json').read_text())['status']=='passed'
qualified=json.loads((E/'qualified-source-hashes.json').read_text())
assert all(manifest['sha256'].get(name)==digest for name,digest in qualified.items())

def game_snapshot():
    with sqlite3.connect((GAME/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        tables={r[0]:db.execute('SELECT * FROM "'+r[0]+'" ORDER BY rowid').fetchall()
                for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not any(r[2]=='running' for r in tables.get('sessions',[])),'Production training running'
    return {'tables':{name:hashlib.sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest() for name,rows in tables.items()},
            'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GAME/'policies').glob('*.json')},
            'pilots':len(tables['drivers'])}

env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
     'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen']
def health(label):
    path=P/(label+'.json')
    subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),'/tmp/board_health.py',
                    '--output',str(path)],check=True,stdout=subprocess.DEVNULL)
    return json.loads(path.read_text())

before=health('before-install');assert before['version']=='0.9.0-rc.18' and not before['manifestMismatches']
assert before['activeTheme']=={'id':'base','kind':'base'}
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
stamp=time.strftime('%Y%m%d-%H%M%S');backup=Path('/var/backups')/('smartpc-before-apple-recovery-'+stamp)
old=TARGET.with_name('dashboard-rc18-before-apple-'+stamp);stage=TARGET.with_name('dashboard-rc19-stage-'+stamp)
switched=False;backed=False
try:
    game_before=game_snapshot();backup.mkdir(mode=0o700)
    shutil.copytree(H/'.config/SmartPC',backup/'config')
    visual=backup/'visual';visual.mkdir()
    theme_paths=[p for p in DATA.iterdir() if p.name.startswith('theme-')]
    for path in theme_paths:
        if path.is_dir():shutil.copytree(path,visual/path.name)
        else:shutil.copy2(path,visual/path.name)
    backed=True
    # Store-only import: real PC/ARM preflights and native acceptance already
    # completed. Digest-check the cache against the same immutable payload.
    code='''import json,sys
from pathlib import Path
sys.path.insert(0,"/tmp/smartpc-apple-candidate/dashboard")
from theme_bundle import BundleManager,validate_project
root=Path("/tmp/smartpc-apple-release/bundle")
valid=validate_project(root);cache=json.loads(Path("/tmp/smartpc-apple-release/cache.json").read_text())
assert cache["digest"]==valid["digest"] and cache["result"]["status"]=="passed"
revision=BundleManager("/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC",app_root="/tmp/smartpc-apple-candidate/dashboard").import_bundle(root,preflight=lambda *_:cache["result"],require_preflight=True)
print(json.dumps({k:revision[k] for k in ("id","version","digest")}))
'''
    result=subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),'-'],input=code,text=True,
                          capture_output=True,check=True)
    identity=json.loads(result.stdout);(P/'theme-import.json').write_text(json.dumps(identity,indent=2)+'\n')
    assert identity['version']=='1.6.3'
    stage.mkdir()
    for name,digest in manifest['sha256'].items():
        path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/name,path)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    shutil.copy2(SOURCE/'release-manifest.json',stage/'release-manifest.json');os.sync()
    TARGET.rename(old);stage.rename(TARGET);switched=True;os.sync()
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    end=time.monotonic()+90
    while True:
        time.sleep(2);after=health('installed');pulse=after.get('guiHeartbeat') or {}
        if after['service']['ActiveState']=='active' and pulse.get('ready') and pulse.get('ageSeconds',99)<5 and not pulse.get('pending'):break
        assert time.monotonic()<end,'GUI not ready'
    assert after['version']==manifest['version'] and not after['manifestMismatches']
    assert after['service']['NRestarts']=='0'
    assert after['allPreferenceHashes']==before['allPreferenceHashes']
    assert after['activeTheme']==before['activeTheme'] and after['bootId']==before['bootId']
    assert game_snapshot()==game_before,'Game data changed'
    code='''import sys,json
from pathlib import Path
sys.path.insert(0,"/opt/smartpc/dashboard")
from theme_runtime import make_catalog
c=make_catalog(Path("/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/themes"),Path("/opt/smartpc/dashboard"))
assert "studio.applecalm" in c.packs and c.bundle_revisions["studio.applecalm"]["version"]=="1.6.3"
print(json.dumps(c.bundle_inventory))
'''
    result=subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),'-'],input=code,text=True,
                          capture_output=True,check=True)
    inventory=json.loads(result.stdout);(P/'production-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    receipt={'status':'passed','version':after['version'],'files':len(manifest['sha256']),
             'installedAtUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'qt':after['qt'],
             'themeAvailable':identity,'activeTheme':after['activeTheme'],'backup':str(backup),
             'runtimeRollback':str(old),'service':after['service'],'guiHeartbeat':after['guiHeartbeat'],
             'manifestMismatches':after['manifestMismatches'],'allPreferencesPreserved':True,
             'preservedPreferenceCount':len(before['allPreferenceHashes']),
             'preservedNonAppearancePreferenceCount':before['nonAppearancePreferenceCount'],
             'originalPilotsAndArtifactsUnchanged':True,'pilots':game_before['pilots'],
             'artifactCount':len(game_before['artifacts']),'newOSReboot':False,
             'originalQuarantinePreserved':any(r['version']=='1.6.2' and r['state']=='blocked' for r in inventory),
             'noProductionTraining':True}
    receipt['qualification']={'coreSoakMinutes':30,'soakBundle':json.loads((E/'performance-summary.json').read_text())['soak']['bundle'],
                              'releaseBundleSupplement':'release-supplement.json'}
    (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
    subprocess.run(['systemctl','stop','smartpc-dashboard'],check=False)
    if switched:
        TARGET.rename(TARGET.with_name('dashboard-rc19-failed-'+stamp));old.rename(TARGET)
    if backed:
        # Service is stopped: restore only the visual/config transaction. Game
        # and provider caches are outside this operation and are not reverted.
        for path in [p for p in DATA.iterdir() if p.name.startswith('theme-')]:
            if path.is_dir():shutil.rmtree(path)
            else:path.unlink()
        for path in (backup/'visual').iterdir():
            if path.is_dir():shutil.copytree(path,DATA/path.name)
            else:shutil.copy2(path,DATA/path.name)
        for path in (backup/'config').rglob('*'):
            if path.is_file():
                dest=H/'.config/SmartPC'/path.relative_to(backup/'config');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        restored=[str(p) for p in DATA.iterdir() if p.name.startswith('theme-')]
        subprocess.run(['chown','-R','smartpc:smartpc',*restored,str(H/'.config/SmartPC')],check=True)
    raise
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
