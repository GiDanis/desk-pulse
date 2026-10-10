"""Transactional S0–S5 delivery; qualify EGLFS and preserve the selected theme."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

STAGE = Path('/var/lib/smartpc-dashboard/v086-source-staging')
PROJECT = STAGE / 'project'
RUNTIME = Path('/opt/smartpc/dashboard')
USER_HOME = Path('/var/lib/smartpc-dashboard')
PROOF = USER_HOME / 'v086-source-proof'
source = STAGE / 'runtime'
manifest = json.loads((source / 'release-manifest.json').read_text())
assert manifest['version'] == '0.8.6-rc.1'
for relative, digest in manifest['sha256'].items():
    assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == digest, relative
    assert hashlib.sha256((PROJECT / 'dashboard' / relative).read_bytes()).hexdigest() == digest, 'Qualification/runtime mismatch: ' + relative
assert not (source / 'fixtures/theme-runtime/renderers').exists()
cache = json.loads((PROOF / 'native-theme-preflight.json').read_text())
assert cache['result']['status'] == 'passed' and cache['result']['qt'] == '6.8.2'
assert cache['origin']['hostname'] == subprocess.check_output(['hostname'], text=True).strip()
sys.path.insert(0, str(PROJECT / 'dashboard'))
from theme_bundle import validate_project
assert cache['digest'] == validate_project(PROJECT / 'theme-projects/apple-calm/bundle')['digest']
environment = ['HOME=' + str(USER_HOME), 'XDG_CONFIG_HOME=' + str(USER_HOME / '.config'),
               'XDG_DATA_HOME=' + str(USER_HOME / '.local/share'), 'XDG_CACHE_HOME=/var/cache/smartpc-dashboard']
eglfs = ['QT_QPA_PLATFORM=eglfs', 'QT_QPA_EGLFS_INTEGRATION=eglfs_kms',
         'QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json', 'QT_QPA_EGLFS_HIDECURSOR=1', 'QSG_RHI_BACKEND=opengl']
software = ['QT_QPA_PLATFORM=offscreen', 'QT_QUICK_BACKEND=software']


def run_user(arguments, log, graphics, timeout=180):
    with (PROOF / log).open('w') as stream:
        subprocess.run(['runuser', '-u', 'smartpc', '--', 'env', *environment, *graphics, 'python3', *map(str, arguments)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=timeout)


run_user([PROOF / 'board-health.py', '--output', PROOF / 'transaction-baseline.json'], 'transaction-baseline.txt', software)
before = json.loads((PROOF / 'transaction-baseline.json').read_text())
assert before['version'] == '0.8.6-rc.1' and not before['manifestMismatches']
assert before['service']['ActiveState'] == 'active'
old_manifest=json.loads((RUNTIME/'release-manifest.json').read_text())
changed={name for name in set(old_manifest['sha256'])|set(manifest['sha256']) if old_manifest['sha256'].get(name)!=manifest['sha256'].get(name)}
assert changed=={'theme_api.py','check_dashboard_summary.py','check_dashboard_optimization_ui.py'},changed
(PROOF/'delta-scope.json').write_text(json.dumps({'changedFiles':sorted(changed),'scope':'Account detail source qualification; theme/QML/provider files unchanged'},indent=2)+'\n')
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup = Path('/var/backups') / ('smartpc-before-v086-source-' + stamp)
backup.mkdir(mode=0o700)
started = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
subprocess.run(['systemctl', 'stop', 'smartpc-dashboard'], check=True)
installed = False
backed_up = False
try:
    shutil.copytree(RUNTIME, backup / 'dashboard')
    shutil.copytree(USER_HOME / '.config', backup / 'config')
    shutil.copytree(USER_HOME / '.local', backup / 'local')
    shutil.copytree('/var/cache/smartpc-dashboard', backup / 'cache')
    backed_up = True
    for theme in ('base','apple'):
        name='optimization-'+theme
        run_user([PROJECT / 'dashboard/check_dashboard_optimization_ui.py','--theme',theme,'--palette','night',
                  '--capture-dir',PROOF / name],name+'.txt',eglfs)
    run_user([PROJECT / 'dashboard/check_dashboard_summary.py'],'summary-normalization.txt',software)
    run_user([PROJECT / 'dashboard/check_theme_api_adapters.py'],'public-adapters.txt',software)
    run_user([PROJECT / 'dashboard/check_theme_api_runtime.py'],'public-runtime.txt',software)
    qualification = {'coreManifestSha256': hashlib.sha256((source / 'release-manifest.json').read_bytes()).hexdigest(),
                     'themeDigest': cache['digest'], 'accountSourceDeltaProfiles': 2, 'previousDashboardQualification': '/var/lib/smartpc-dashboard/v086-dashboard-proof/qualification.json', 'status': 'passed'}
    (PROOF / 'qualification.json').write_text(json.dumps(qualification, indent=2) + '\n')
    new = RUNTIME.with_name('dashboard-v086.new-' + stamp)
    shutil.copytree(source, new)
    RUNTIME.rename(backup / 'replaced-runtime')
    try:
        new.rename(RUNTIME)
    except BaseException:
        (backup / 'replaced-runtime').rename(RUNTIME)
        raise
    installed = True
    # Importing a revision only makes it available; the activation journal and
    # appearance preferences remain those chosen by the user.
    importer = PROOF / 'import-production.py'
    importer.write_text('''import json,sys
from pathlib import Path
sys.path.insert(0,"/opt/smartpc/dashboard")
from theme_bundle import BundleManager
proof=Path("/var/lib/smartpc-dashboard/v086-source-proof")
cache=json.loads((proof/"native-theme-preflight.json").read_text())
revision=BundleManager(Path("/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC")).import_bundle(Path("/var/lib/smartpc-dashboard/v086-source-staging/smartpc-apple-calm-1.6.0.smartpc-theme"),preflight=lambda *_:cache["result"],require_preflight=True)
assert revision["digest"]==cache["digest"] and revision["version"]=="1.6.0"
(proof/"production-theme-import.json").write_text(json.dumps(revision,indent=2)+"\\n")
''')
    run_user([importer], 'theme-import.txt', software)
    subprocess.run(['systemctl', 'reset-failed', 'smartpc-dashboard'], check=True)
    subprocess.run(['systemctl', 'start', 'smartpc-dashboard'], check=True)
    deadline = time.monotonic() + 45
    while True:
        run_user([PROOF / 'board-health.py', '--output', PROOF / 'installed-health.json'], 'installed-health.txt', software)
        after = json.loads((PROOF / 'installed-health.json').read_text())
        heartbeat = after['guiHeartbeat']
        if heartbeat and heartbeat['ready'] and 0 <= heartbeat['ageSeconds'] < 15:
            break
        assert time.monotonic() < deadline, 'Fresh GUI readiness missing'
        time.sleep(2)
    assert after['version'] == manifest['version'] and not after['manifestMismatches']
    assert after['service']['ActiveState'] == 'active' and after['service']['NRestarts'] == '0'
    assert after['guiHeartbeat']['selection'] == after['activeTheme'] and after['guiHeartbeat']['pending'] is None
    assert after['preferenceHashes'] == before['preferenceHashes'], 'Nonappearance preferences changed'
    assert after['allPreferenceHashes'] == before['allPreferenceHashes'], 'Appearance or other preferences changed'
    assert after['activeTheme'] == before['activeTheme'], 'User theme selection changed'
    journal = subprocess.check_output(['journalctl', '-u', 'smartpc-dashboard', '--since', started, '--no-pager'], text=True)
    warnings = [line for line in journal.splitlines() if any(marker in line for marker in
                ('ReferenceError', 'TypeError', 'Binding loop', 'QQmlApplicationEngine failed', 'Traceback', 'Segmentation fault'))]
    assert not warnings, warnings
    (PROOF / 'installed-journal.txt').write_text(journal)
    receipt = {'status': 'passed', 'version': manifest['version'], 'files': len(manifest['sha256']),
               'backup': str(backup), 'preferencesPreserved': True, 'allPreferencesPreserved': True,
               'manifestVerified': True, 'selectedThemePreserved': True, 'activeTheme': after['activeTheme'],
               'availableAppleRevision': {'version': '1.6.0', 'digest': cache['digest']},
               'bootIdBefore': before['bootId'], 'installedAt': time.time(), 'qmlWarnings': warnings,
               'restartKind': 'service stop/start; reboot proof separate'}
    (PROOF / 'install-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)
except BaseException:
    subprocess.run(['systemctl', 'stop', 'smartpc-dashboard'], check=False)
    if installed:
        shutil.rmtree(RUNTIME)
        shutil.copytree(backup / 'dashboard', RUNTIME)
    if backed_up:
        newest_budgets = {p.name: p.read_bytes() for p in (USER_HOME / '.local/state/smartpc/casa').glob('*-budget.json')}
        for saved, target in (('config', USER_HOME / '.config'), ('local', USER_HOME / '.local'),
                              ('cache', Path('/var/cache/smartpc-dashboard'))):
            shutil.rmtree(target)
            shutil.copytree(backup / saved, target)
            subprocess.run(['chown', '-R', 'smartpc:smartpc', str(target)], check=True)
        for name, content in newest_budgets.items():
            destination = USER_HOME / '.local/state/smartpc/casa' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            subprocess.run(['chown', 'smartpc:smartpc', str(destination)], check=True)
    raise
finally:
    subprocess.run(['systemctl', 'start', 'smartpc-dashboard'], check=True)
