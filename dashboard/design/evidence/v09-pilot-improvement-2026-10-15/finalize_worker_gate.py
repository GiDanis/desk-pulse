"""Atomic worker-only patch. Game.start spawns a fresh interpreter; no GUI restart."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-pilot-improvement-proof'
S=H/'smartpc-rc18-worker-gate';T=Path('/opt/smartpc/dashboard')
assert 'OK' in (P/'arm-continuous-gate.txt').read_text()
old=json.loads((T/'release-manifest.json').read_text());new=json.loads((S/'release-manifest.json').read_text())
assert old['version']==new['version']=='0.9.0-rc.18'
changed={k for k,v in new['sha256'].items() if old['sha256'].get(k)!=v}
assert changed=={'game_academy_trainer.py','check_game_pilot_improvement.py'}
assert all(hashlib.sha256((T/k).read_bytes()).hexdigest()==v for k,v in old['sha256'].items())
assert all(hashlib.sha256((S/k).read_bytes()).hexdigest()==new['sha256'][k] for k in changed)
before=subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID'],text=True).strip()
backup=T.with_name('rc18-before-continuous-worker-gate');backup.mkdir()
for name in (*changed,'release-manifest.json'):shutil.copy2(T/name,backup/name)
try:
    for name in (*sorted(changed),'release-manifest.json'):
        temporary=T/(name+'.worker-stage');shutil.copy2(S/name,temporary);os.replace(temporary,T/name)
    os.sync()
    assert all(hashlib.sha256((T/k).read_bytes()).hexdigest()==v for k,v in new['sha256'].items())
    assert subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID'],text=True).strip()==before
    output=P/'installed-worker-final.json';output.touch()
    subprocess.run(['chown','smartpc:smartpc',str(output)],check=True)
    subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),
        'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',
        str(H/'game-runtime/bin/python'),str(H/'v086-source-proof/board-health.py'),'--output',str(output)],check=True,stdout=subprocess.DEVNULL)
    health=json.loads(output.read_text());assert not health['manifestMismatches']
    assert health['service']['ActiveState']=='active' and health['service']['NRestarts']=='0'
    assert health['guiHeartbeat']['ready']
    receipt=json.loads((P/'final-receipt.json').read_text())
    shutil.copy2(P/'final-receipt.json',P/'before-worker-gate-receipt.json')
    receipt.update(finalManifestSha256=hashlib.sha256((T/'release-manifest.json').read_bytes()).hexdigest(),
        service=health['service'],guiHeartbeat=health['guiHeartbeat'],workerGateFix=dict(
            tests=11,backup=str(backup),appliesOnNextWorkerStart=True,guiPidPreserved=True,
            gameStoreConstructed=False,gameDataWrites=False))
    (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
    for name in (*changed,'release-manifest.json'):
        temporary=T/(name+'.worker-rollback');shutil.copy2(backup/name,temporary);os.replace(temporary,T/name)
    os.sync();raise
