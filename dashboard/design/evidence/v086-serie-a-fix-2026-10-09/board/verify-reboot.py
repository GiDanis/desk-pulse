"""Accept the correction only after changed boot, fresh GUI and preserved prefs."""
import hashlib,json,subprocess,time
from pathlib import Path
P=Path('/var/lib/smartpc-dashboard/v086-seriea-proof')
before=json.loads((P/'baseline.json').read_text());after=json.loads((P/'reboot-health.json').read_text());receipt=json.loads((P/'install-receipt.json').read_text())
name_delta=json.loads((P/'name-delta-receipt.json').read_text());assert name_delta['status']=='passed'
assert hashlib.sha256(Path('/opt/smartpc/dashboard/release-manifest.json').read_bytes()).hexdigest()==name_delta['manifestSha256']
assert before['bootId']!=after['bootId']
assert after['version']=='0.8.6-rc.2' and after['files']==receipt['files'] and not after['manifestMismatches']
assert after['service']['ActiveState']=='active' and after['service']['SubState']=='running' and after['service']['NRestarts']=='0'
assert 0<=time.time()-after['time']<15
hb=after['guiHeartbeat'];assert hb and hb['ready'] and 0<=hb['ageSeconds']<15 and hb['pending'] is None
assert hb['selection']==after['activeTheme']==before['activeTheme']
assert after['allPreferenceHashes']==before['allPreferenceHashes']
journal=subprocess.check_output(['sudo','-n','journalctl','-b','-u','smartpc-dashboard','--no-pager'],text=True)
warnings=[l for l in journal.splitlines() if any(x in l for x in ('ReferenceError','TypeError','Binding loop','QQmlApplicationEngine failed','Traceback','Segmentation fault'))];assert not warnings,warnings
(P/'reboot-journal.txt').write_text(journal)
report={'status':'passed','version':after['version'],'files':after['files'],'bootIdBefore':before['bootId'],'bootIdAfter':after['bootId'],'activeTheme':after['activeTheme'],'allPreferencesPreserved':True,'service':after['service'],'guiHeartbeat':hb,'backup':receipt['backup'],'nameDeltaBackup':name_delta['backup'],'manifestSha256':name_delta['manifestSha256'],'qmlWarnings':warnings,'verifiedAt':time.time()}
(P/'reboot-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
