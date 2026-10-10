"""Read-only post-reboot acceptance; require changed boot and fresh GUI proof."""
import json
import os
from pathlib import Path
import subprocess
import time

proof = Path('/var/lib/smartpc-dashboard/v086-dashboard-proof')
before = json.loads((proof / 'transaction-baseline.json').read_text())
after = json.loads((proof / 'reboot-health.json').read_text())
receipt = json.loads((proof / 'install-receipt.json').read_text())
assert after['bootId'] != before['bootId'], 'No actual system reboot'
assert after['version'] == '0.8.6-rc.1' and after['files'] == receipt['files'] and not after['manifestMismatches']
assert after['service']['ActiveState'] == 'active' and after['service']['SubState'] == 'running'
assert after['service']['NRestarts'] == '0'
assert 0 <= time.time()-after['time'] < 15, 'Health measurement is not fresh'
heartbeat = after['guiHeartbeat']
assert heartbeat and heartbeat['ready'] and 0 <= heartbeat['ageSeconds'] < 15
assert heartbeat['pending'] is None and heartbeat['selection'] == after['activeTheme']
assert after['activeTheme'] == before['activeTheme']
assert after['allPreferenceHashes'] == before['allPreferenceHashes']
assert after['preferenceHashes'] == before['preferenceHashes']
env = dict(os.environ, XDG_CONFIG_HOME='/var/lib/smartpc-dashboard/.config',
           XDG_DATA_HOME='/var/lib/smartpc-dashboard/.local/share', XDG_CACHE_HOME='/var/cache/smartpc-dashboard')
journal = subprocess.check_output(['sudo', '-n', 'journalctl', '-b', '-u', 'smartpc-dashboard', '--no-pager'], text=True, env=env)
warnings = [line for line in journal.splitlines() if any(marker in line for marker in
            ('ReferenceError', 'TypeError', 'Binding loop', 'QQmlApplicationEngine failed', 'Traceback', 'Segmentation fault'))]
assert not warnings, warnings
(proof / 'reboot-journal.txt').write_text(journal)
report = {'status': 'passed', 'version': after['version'], 'files': after['files'],
          'bootIdBefore': before['bootId'], 'bootIdAfter': after['bootId'],
          'service': after['service'], 'guiHeartbeat': heartbeat, 'allPreferencesPreserved': True,
          'activeTheme': after['activeTheme'], 'backup': receipt['backup'], 'qmlWarnings': warnings,
          'verifiedAt': time.time(), 'scope': 'Actual reboot/runtime health; physical readability and long soak separate'}
(proof / 'reboot-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
