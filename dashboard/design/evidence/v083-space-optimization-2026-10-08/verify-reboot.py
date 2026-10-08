"""Read-only post-reboot verification of installed bytes, preferences and GUI."""
import json
from pathlib import Path
import subprocess
import time

proof = Path('/var/lib/smartpc-dashboard/v083-space-proof')
before = json.loads((proof / 'pre-reboot-health.json').read_text())
baseline = json.loads((proof / 'baseline-health.json').read_text())
native = json.loads((proof / 'native-theme-preflight.json').read_text())
deadline = time.monotonic() + 40
while True:
    result = subprocess.run(['python3', '/var/lib/smartpc-dashboard/v083-space-staging/board-health.py',
                             '--output', str(proof / 'post-reboot-health.json')], capture_output=True, text=True)
    (proof / 'post-reboot-health.txt').write_text(result.stdout + result.stderr)
    if result.returncode == 0:
        after = json.loads((proof / 'post-reboot-health.json').read_text())
        heartbeat = after['guiHeartbeat']
        if heartbeat and heartbeat['ready'] and 0 <= heartbeat['ageSeconds'] < 15:
            break
    assert time.monotonic() < deadline, 'Fresh GUI heartbeat missing after bounded startup wait'
    time.sleep(2)
assert after['bootId'] != before['bootId'], 'No system reboot observed'
assert after['version'] == '0.8.3-rc.2' and after['files'] == 499
assert not after['manifestMismatches']
assert after['service']['ActiveState'] == 'active' and after['service']['SubState'] == 'running'
assert after['service']['NRestarts'] == '0'
assert after['activeTheme']['version'] == '1.3.1' and after['activeTheme']['digest'] == native['digest']
assert heartbeat['selection'] == after['activeTheme'] and heartbeat['pending'] is None
assert after['preferenceHashes'] == baseline['preferenceHashes']
assert after['allPreferenceHashes'] == before['allPreferenceHashes']
journal = subprocess.check_output(['sudo', '-n', 'journalctl', '--boot', '-u', 'smartpc-dashboard', '--no-pager'], text=True)
(proof / 'post-reboot-journal.txt').write_text(journal)
warnings = [line for line in journal.splitlines() if any(marker in line for marker in
            ('ReferenceError', 'TypeError', 'Binding loop', 'QQmlApplicationEngine failed', 'Traceback', 'Segmentation fault'))]
assert not warnings, warnings
report = {'status': 'passed', 'bootIdBefore': before['bootId'], 'bootIdAfter': after['bootId'],
          'version': after['version'], 'files': after['files'], 'theme': after['activeTheme'],
          'service': after['service'], 'guiHeartbeat': heartbeat,
          'preferencesPreserved': True, 'allPreferenceHashesEqualToPreReboot': True,
          'manifestVerified': True, 'qmlWarnings': warnings,
          'scope': 'Orderly board reboot; physical readability and power-cut acceptance remain separate'}
(proof / 'reboot-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
