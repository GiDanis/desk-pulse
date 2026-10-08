"""Verify persistent reboot evidence and preservation without exposing private data."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

proof = Path('/var/lib/smartpc-dashboard/v083-proof')
before = json.loads((proof / 'pre-reboot-health.json').read_text())
after = json.loads((proof / 'post-reboot-health.json').read_text())
receipt = json.loads((proof / 'install-receipt.json').read_text())
assert after['bootId'] != before['bootId']
assert after['version'] == receipt['version'] == '0.8.3-rc.1'
assert after['files'] == receipt['files'] == 498 and not after['manifestMismatches']
assert after['service']['ActiveState'] == 'active' and after['service']['SubState'] == 'running'
assert after['service']['NRestarts'] == '0'
assert after['preferenceHashes'] == before['preferenceHashes']
legacy = json.loads((proof / 'baseline-health.json').read_text())
assert all(after['preferenceHashes'].get(key) == value for key,value in legacy['preferenceHashes'].items())
assert set(after['preferenceHashes']) - set(legacy['preferenceHashes']) == {'navigation/schemaVersion','navigation/sportVisible'}
assert after['activeTheme'] == before['activeTheme'] == receipt['theme']
health = after['guiHeartbeat']
assert health['ready'] and 0 <= health['ageSeconds'] < 15
assert health['pid'] == after['runtimePid'] and health['selection'] == after['activeTheme']
assert health['pending'] is None

backup = Path(receipt['backup'])
def budgets(root):
    return {p.name: {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'data':json.loads(p.read_text())}
            for p in (root / 'state/smartpc/casa').glob('*-budget.json')}
previous, current = budgets(backup / 'local'), budgets(Path('/var/lib/smartpc-dashboard/.local'))
assert previous and set(previous) <= set(current), 'Casa ledger missing'
deltas=[]
for key,record in previous.items():
    old,new=record['data'],current[key]['data']
    assert old['scope']==new['scope'] and old['periodStart']==new['periodStart'] and old['periodEnd']==new['periodEnd'], 'Casa period changed; investigate before qualifying preservation'
    assert new['requests']>=old['requests'] and new['highWater']>=old['highWater'], 'Casa ledger rolled back'
    deltas.append(new['requests']-old['requests'])
unchanged=all(record['sha256']==current[key]['sha256'] for key,record in previous.items())
journal = subprocess.check_output(['journalctl','-b','-u','smartpc-dashboard','--no-pager'],text=True)
markers = ('ReferenceError','TypeError','Binding loop','QQmlApplicationEngine failed','Traceback','Segmentation fault')
warnings = [line for line in journal.splitlines() if any(marker in line for marker in markers)]
assert not warnings, warnings
(proof / 'post-reboot-journal.txt').write_text(journal)
report = {'status':'passed','verifiedAt':time.time(),'version':after['version'],
          'bootIdBefore':before['bootId'],'bootIdAfter':after['bootId'],
          'manifestVerified':True,'files':after['files'],'preferencesPreserved':True,
          'nonAppearancePreferences':after['nonAppearancePreferenceCount'],
          'themePreservedAfterReboot':True,'guiReady':True,'heartbeatAgeSeconds':health['ageSeconds'],
          'NRestarts':int(after['service']['NRestarts']),'qmlWarnings':warnings,
          'casaLedgerPreserved':True,'casaLedgerUnchanged':unchanged,'casaLedgerFiles':len(current),'casaRequestsDuringDelivery':sum(deltas),'legacyPreferencesPreserved':len(legacy['preferenceHashes']),'navigationMigrationAddedKeys':['navigation/schemaVersion','navigation/sportVisible'],
          'scope':'Ordered reboot and current service health; physical keypad, network unplug, power cut and long soak not qualified'}
(proof / 'delivery-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
