"""Qualify this exact Sport delta on EGLFS, then install with rollback."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

home = Path('/var/lib/smartpc-dashboard')
proof = home / 'v087-sport-live-proof'
source = home / 'v087-sport-live-staging/project/dashboard'
runtime = Path('/opt/smartpc/dashboard')
manifest = json.loads((source / 'release-manifest.json').read_text())
old = json.loads((runtime / 'release-manifest.json').read_text())
assert old == json.loads((proof / 'installed-manifest-before.json').read_text())
assert manifest['version'] == '0.8.7-rc.3' and old['version'] == '0.8.7-rc.2'
for root, entries in [(source, manifest), (runtime, old)]:
    for name, digest in entries['sha256'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, (root, name)
changed = [name for name in manifest['sha256'] if old['sha256'].get(name) != manifest['sha256'][name]]
assert set(changed) == {'Main.qml', 'dashboard_summary.py', 'motorsport.py', 'motorsport_core.py',
                       'racing_timing.py', 'MotorsportOverlay.qml', 'check_motorsport.py',
                       'check_motorsport_ui.py', 'check_dashboard_summary.py', 'version.py'}
env = ['HOME=' + str(home), 'XDG_CONFIG_HOME=' + str(home / '.config'),
       'XDG_DATA_HOME=' + str(home / '.local/share'), 'XDG_CACHE_HOME=/var/cache/smartpc-dashboard']
egl = ['QT_QPA_PLATFORM=eglfs', 'QT_QPA_EGLFS_INTEGRATION=eglfs_kms',
       'QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json', 'QT_QPA_EGLFS_HIDECURSOR=1', 'QSG_RHI_BACKEND=opengl']
health = home / 'v086-source-proof/board-health.py'

def run(arguments, name, graphics=()):
    with (proof / (name + '.txt')).open('w') as stream:
        subprocess.run(['runuser', '-u', 'smartpc', '--', 'env', *env, *graphics, 'python3', *map(str, arguments)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=120)

run([health, '--output', proof / 'baseline-health.json'], 'baseline-health')
before = json.loads((proof / 'baseline-health.json').read_text())
assert not before['manifestMismatches'] and before['service']['ActiveState'] == 'active'
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup = Path('/var/backups') / ('smartpc-before-v087-sport-live-' + stamp)
backup.mkdir(mode=0o700)
started = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
subprocess.run(['systemctl', 'stop', 'smartpc-dashboard'], check=True)
installed = False
try:
    shutil.copytree(runtime, backup / 'dashboard')
    shutil.copytree(home / '.config', backup / 'config')
    shutil.copytree(home / '.local', backup / 'local')
    for test in ['check_dashboard_summary.py', 'check_motorsport.py']:
        print('Native ' + test, flush=True)
        run([source / test], test.removesuffix('.py'), ['QT_QPA_PLATFORM=offscreen', 'QT_QUICK_BACKEND=software'])
    for theme in ['base', 'functional', 'apple']:
        print('EGLFS live priority ' + theme, flush=True)
        run([proof / 'qualify-priority-ui.py', '--dashboard', source, '--theme', theme, '--output', proof / ('eglfs-' + theme)],
            'eglfs-' + theme, egl)
    new = runtime.with_name('dashboard-v087-sport-live.new-' + stamp)
    shutil.copytree(source, new, ignore=lambda directory, names: ['renderers']
                    if Path(directory) == source / 'fixtures/theme-runtime' else [])
    assert not (new / 'fixtures/theme-runtime/renderers').exists()
    runtime.rename(backup / 'replaced-runtime')
    try:
        new.rename(runtime)
    except BaseException:
        (backup / 'replaced-runtime').rename(runtime)
        raise
    installed = True
    subprocess.run(['systemctl', 'start', 'smartpc-dashboard'], check=True)
    deadline = time.monotonic() + 45
    while True:
        run([health, '--output', proof / 'installed-health.json'], 'installed-health')
        after = json.loads((proof / 'installed-health.json').read_text())
        hb = after['guiHeartbeat']
        if hb and hb['ready'] and 0 <= hb['ageSeconds'] < 15:
            break
        assert time.monotonic() < deadline, 'Fresh GUI readiness absent'
        time.sleep(2)
    assert after['version'] == manifest['version'] and not after['manifestMismatches']
    assert after['service']['ActiveState'] == 'active' and after['service']['NRestarts'] == '0'
    assert after['activeTheme'] == before['activeTheme'] == hb['selection'] and hb['pending'] is None
    assert after['preferenceHashes'] == before['preferenceHashes']
    journal = subprocess.check_output(['journalctl', '-u', 'smartpc-dashboard', '--since', started, '--no-pager'], text=True)
    warnings = [line for line in journal.splitlines() if any(marker in line for marker in
                ['ReferenceError', 'TypeError', 'Binding loop', 'QQmlApplicationEngine failed', 'Traceback', 'Segmentation fault'])]
    assert not warnings, warnings
    (proof / 'installed-journal.txt').write_text(journal)
    report = {'status': 'passed', 'version': manifest['version'], 'files': len(manifest['sha256']), 'changedFiles': changed,
              'backup': str(backup), 'activeTheme': after['activeTheme'], 'preferencesPreserved': True,
              'guiHeartbeat': hb, 'qmlWarnings': warnings, 'service': after['service'],
              'scope': 'Native EGLFS replay of observed data and simulated active F1; service restart, no reboot; real active F1 latency unqualified'}
    (proof / 'install-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
except BaseException:
    subprocess.run(['systemctl', 'stop', 'smartpc-dashboard'], check=False)
    if installed:
        shutil.rmtree(runtime)
        shutil.copytree(backup / 'dashboard', runtime)
    raise
finally:
    subprocess.run(['systemctl', 'start', 'smartpc-dashboard'], check=True)
