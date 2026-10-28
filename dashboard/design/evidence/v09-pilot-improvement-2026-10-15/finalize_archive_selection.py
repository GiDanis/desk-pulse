"""Finalize the tested Clone-PPO qualification fallback, keeping original data."""
import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-pilot-improvement-proof'
R=H/'smartpc-v09-rc18-runtime-final';T=Path('/opt/smartpc/dashboard')
G=H/'.local/share/SmartPC/SmartPC/game';PY=H/'game-runtime/bin/python'
m=json.loads((R/'release-manifest.json').read_text())
assert m['version']=='0.9.0-rc.18' and all(hashlib.sha256((R/k).read_bytes()).hexdigest()==v for k,v in m['sha256'].items())
assert 'OK' in (P/'arm-archive-selection.txt').read_text()
receipt=json.loads((P/'final-receipt.json').read_text());shutil.copy2(P/'final-receipt.json',P/'initial-rc18-receipt.json')

def snapshot():
    with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        tables={r[0]:db.execute('SELECT * FROM '+r[0]+' ORDER BY rowid').fetchall() for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return dict(tables=tables,artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (G/'policies').glob('*.json')})

def health(label):
    p=P/(label+'.json');p.touch();subprocess.run(['chown','smartpc:smartpc',str(p)],check=True)
    subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),
        'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',
        str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(p)],check=True,stdout=subprocess.DEVNULL)
    return json.loads(p.read_text())

initial=health('before-archive-selection');before=snapshot()
assert not any(row[2]=='running' for row in before['tables']['sessions'])
assert initial['version']=='0.9.0-rc.18' and not initial['manifestMismatches']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
old=T.with_name('dashboard-rc18-before-archive-selection');stage=T.with_name('dashboard-rc18-archive-stage');switched=False
try:
    assert snapshot()==before
    assert not old.exists() and not stage.exists();shutil.copytree(R,stage)
    os.sync();T.rename(old);stage.rename(T);switched=True;os.sync()
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    end=time.monotonic()+90
    while True:
        time.sleep(3);after=health('installed-final');gui=after.get('guiHeartbeat') or {}
        if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending'):break
        assert time.monotonic()<end
    assert not after['manifestMismatches'] and after['version']==m['version']
    assert after['service']['NRestarts']=='0' and initial['allPreferenceHashes']==after['allPreferenceHashes']
    assert initial['activeTheme']==after['activeTheme'] and initial['bootId']==after['bootId']
    assert snapshot()==before
    receipt.update(service=after['service'],guiHeartbeat=after['guiHeartbeat'],
        finalManifestSha256=hashlib.sha256((T/'release-manifest.json').read_bytes()).hexdigest(),
        previousCandidateRuntime=str(old),archiveSelectionGate='10 ARM tests passed; no copied timed certificates',
        finalDataIdentical=True)
    (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
    if switched:
        subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
        T.rename(T.with_name('dashboard-rc18-failed-archive-selection'));old.rename(T)
    raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
