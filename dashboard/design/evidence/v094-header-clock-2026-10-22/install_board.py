"""Verified runtime exchange and Apple update, with rollback on any failure."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

H = Path('/var/lib/smartpc-dashboard')
P = H / 'v094-proof'
R = H / 'v094-runtime/dashboard'
T = Path('/opt/smartpc/dashboard')
D = H / '.local/share/SmartPC/SmartPC'
G = D / 'game'
PY = H / 'game-runtime/bin/python'
env = ['HOME=' + str(H), 'XDG_CONFIG_HOME=' + str(H / '.config'),
       'XDG_DATA_HOME=' + str(H / '.local/share'), 'XDG_CACHE_HOME=/var/cache/smartpc-dashboard',
       'QT_QPA_PLATFORM=offscreen', 'QT_QUICK_BACKEND=software',
       'OPENBLAS_NUM_THREADS=1', 'OMP_NUM_THREADS=1']


def health(label):
    target = P / (label + '.json')
    subprocess.run(['runuser', '-u', 'smartpc', '--', 'env', *env, str(PY),
                    str(P / 'board-health.py'), '--output', str(target)], check=True,
                   stdout=subprocess.DEVNULL)
    return json.loads(target.read_text())


sys.path.insert(0, str(P))
from native_board import preserved
manifest = json.loads((R / 'release-manifest.json').read_text())
assert manifest['version'] == '0.9.4-rc.1'
assert all(hashlib.sha256((R / n).read_bytes()).hexdigest() == h for n, h in manifest['sha256'].items())
native = json.loads((P / 'native-checks.json').read_text())
assert native['status'] == 'passed' and native['productionStatePreserved']
assert all(native['sourceHashes'].get(n) == h for n, h in manifest['sha256'].items())
assert json.loads((P / 'pc-checks.json').read_text())['status'] == 'passed'
assert 'OK (skipped=1)' in (P / 'arm-runtime-with-tooling-limit.txt').read_text()
before = health('before-install')
assert before['version'] == '0.9.3-rc.2' and not before['manifestMismatches']
assert before['guiHeartbeat']['ready'] and before['activeTheme']['version'] == '1.6.3'
old_manifest = json.loads((T / 'release-manifest.json').read_text())
allowed = {'Main.qml', 'version.py', 'README.md', 'check_theme_api_adapters.py',
           'check_theme_api_runtime.py', 'fixtures/theme-runtime/catalog.json',
           'qml/SmartPC/ThemeApi/runtime.qmltypes'}
delta = [name for name in old_manifest['sha256'] if manifest['sha256'].get(name) != old_manifest['sha256'][name]]
assert all(name in allowed or name.startswith('theme-api/') for name in delta), delta
stamp = time.strftime('%Y%m%d-%H%M%S')
stage = T.with_name('dashboard-v094-stage-' + stamp)
old = T.with_name('dashboard-before-v094-' + stamp)
backup = H / 'v094-backups' / stamp
backup.mkdir(parents=True, mode=0o700)
shutil.copytree(R, stage)
subprocess.run(['systemctl', 'stop', 'smartpc-dashboard'], check=True)
switched = False
try:
    original = preserved()
    shutil.copytree(G, backup / 'game')
    shutil.copytree(H / '.config/SmartPC', backup / 'config')
    controls = backup / 'theme-control'
    controls.mkdir()
    for path in D.glob('theme-*.json'):
        shutil.copy2(path, controls / path.name)
    os.sync()
    T.rename(old)
    stage.rename(T)
    switched = True
    with (P / 'activation.txt').open('w') as log:
        subprocess.run(['runuser', '-u', 'smartpc', '--', 'env', *env, str(PY),
                        str(P / 'activate_theme.py'), str(P / 'apple-identity.json')],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
    subprocess.run(['systemctl', 'start', 'smartpc-dashboard'], check=True)
    deadline = time.monotonic() + 90
    while True:
        time.sleep(2)
        after = health('installed')
        beat = after.get('guiHeartbeat') or {}
        if (after['service']['ActiveState'] == 'active' and beat.get('ready') and
                beat.get('ageSeconds', 999) < 5 and beat.get('pid') == after['runtimePid'] and
                after['runtimePid'] != before['runtimePid'] and not beat.get('pending')):
            break
        assert time.monotonic() < deadline, 'Installed GUI not ready'
    assert after['version'] == manifest['version'] and not after['manifestMismatches']
    assert after['service']['NRestarts'] == '0' and before['bootId'] == after['bootId']
    assert before['preferenceHashes'] == after['preferenceHashes']
    identity = json.loads((P / 'apple-identity.json').read_text())
    assert after['activeTheme'] == identity == beat['selection']
    current = preserved()
    assert original['database'] == current['database'] and original['artifacts'] == current['artifacts']
    report = dict(status='passed', version=after['version'], files=len(manifest['sha256']),
                  activeTheme=identity, service=after['service'], guiHeartbeat=beat,
                  manifestMismatches=after['manifestMismatches'], runtimeRollback=str(old),
                  backup=str(backup), gameDatabasePreserved=True, policyArtifactsPreserved=True,
                  policyArtifactCount=len(original['artifacts']), nonAppearancePreferencesPreserved=True,
                  appearanceOptionsPreserved=True, newOSReboot=False, nativeThemes=native['cases'],
                  runtimeDelta=delta, manifestSha256=hashlib.sha256((T / 'release-manifest.json').read_bytes()).hexdigest())
    (P / 'final-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
except BaseException:
    subprocess.run(['systemctl', 'stop', 'smartpc-dashboard'], check=True)
    if switched:
        T.rename(T.with_name('dashboard-v094-failed-' + stamp))
        old.rename(T)
    if (backup / 'config').exists():
        for path in (backup / 'config').rglob('*'):
            if path.is_file():
                target = H / '.config/SmartPC' / path.relative_to(backup / 'config')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
        for path in (backup / 'theme-control').glob('*'):
            shutil.copy2(path, D / path.name)
        subprocess.run(['chown', '-R', 'smartpc:smartpc', str(H / '.config/SmartPC')], check=True)
        for path in D.glob('theme-*.json'):
            subprocess.run(['chown', 'smartpc:smartpc', str(path)], check=True)
    raise
finally:
    subprocess.run(['systemctl', 'start', 'smartpc-dashboard'], check=True)
