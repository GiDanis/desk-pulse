"""Verify persistent reboot evidence and preservation without exposing private data."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

proof = Path('/var/lib/smartpc-dashboard/v082-proof')
before = json.loads((proof / 'pre-reboot-health.json').read_text())
after = json.loads((proof / 'post-reboot-health.json').read_text())
receipt = json.loads((proof / 'install-receipt.json').read_text())
assert after['bootId'] != before['bootId']
assert after['version'] == receipt['version'] == '0.8.2-rc.1'
assert after['files'] == 491 and not after['manifestMismatches']
assert after['service']['ActiveState'] == 'active' and after['service']['SubState'] == 'running'
assert after['service']['NRestarts'] == '0'
assert after['nonAppearancePreferenceSha256'] == before['nonAppearancePreferenceSha256']
assert after['activeTheme'] == before['activeTheme'] == receipt['theme']
health = after['guiHeartbeat']
assert health['ready'] and 0 <= health['ageSeconds'] < 15
assert health['pid'] == after['runtimePid'] and health['selection'] == after['activeTheme']
assert health['pending'] is None

backup = Path(receipt['backup'])
def budgets(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / 'state/smartpc/casa').glob('*-budget.json')}
previous, current = budgets(backup / 'local'), budgets(Path('/var/lib/smartpc-dashboard/.local'))
assert previous and previous == current, 'Casa consumption ledger changed; review actual requests before making a preservation claim'
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
          'casaLedgerUnchanged':True,'casaLedgerFiles':len(current),
          'scope':'Ordered reboot and current service health; physical keypad, network unplug, power cut and long soak not qualified'}
(proof / 'delivery-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
