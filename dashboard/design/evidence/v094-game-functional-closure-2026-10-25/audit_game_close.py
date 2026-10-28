"""Read back installed maintenance and reclaim only this delivery's test temp."""
from pathlib import Path
import hashlib,json,os,runpy,shutil,subprocess,time
m=runpy.run_path('/var/lib/smartpc-dashboard/p0p9-proof/native_p0.py')
h=m['H'];r=m['R'];w=h/'game-close-verified-20261025';p=w/'proof'
receipt=json.loads((p/'final-receipt.json').read_text());before=json.loads((p/'pre-intervention.json').read_text())
manifest=m['verify'](r);digest=hashlib.sha256((r/'release-manifest.json').read_bytes()).hexdigest()
assert digest==receipt['manifestSha256'] and manifest['version']=='0.9.4-rc.3'
assert m['state']()==before['state']
backup=Path(receipt['backup']);assert m['state'](backup/'game',backup/'preferences')==before['state']
service=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts'],text=True).splitlines())
assert service['ActiveState']=='active' and service['SubState']=='running' and service['NRestarts']=='0'
guis=m['children'](int(service['MainPID']));fresh=None
for f in (Path('/proc')/str(guis[0])/'root/tmp').glob('smartpc-theme-health-'+str(m['UID'])+'/*.json'):
    value=json.loads(f.read_text())
    if value['pid'] in guis and value.get('ready') and 0<=time.time()-value['time']<2:fresh=value;break
assert fresh,'No fresh ready heartbeat from current GUI'
assert before['bootId']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
tmp=Path('/var/tmp/smartpc-game-close-tests');handles=[]
if tmp.exists():
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        try:
            for fd in (process/'fd').iterdir():
                try:
                    if os.readlink(fd).startswith(str(tmp)+'/'):handles.append(str(fd))
                except OSError:pass
        except OSError:pass
removed=False
if tmp.exists() and not handles:shutil.rmtree(tmp);removed=True
result=dict(status='passed',version=manifest['version'],manifestSha256=digest,files=len(manifest['sha256']),
    dataAndPreferencesUnchanged=True,backupVerifiedAfterTests=True,service=service,guiHeartbeat=fresh,
    newOSReboot=False,ownTestTempRemoved=removed,testTempOpenHandles=handles,freeBytes=shutil.disk_usage(h).free)
(p/'post-delivery-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
