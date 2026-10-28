"""Native isolated tests; always restart the production kiosk afterwards."""
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import subprocess

H = Path('/var/lib/smartpc-dashboard')
P = H / 'v094-proof'
S = H / 'v094-project/dashboard'
G = H / '.local/share/SmartPC/SmartPC/game'
PY = H / 'game-runtime/bin/python'


def preserved():
    with sqlite3.connect((G / 'game.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not db.execute("SELECT 1 FROM sessions WHERE status='running'").fetchall()
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        data = {name: db.execute('SELECT * FROM "' + name + '" ORDER BY rowid').fetchall() for name in tables}
    return dict(database=hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(),
                artifacts={str(p.relative_to(G)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in G.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')},
                preferences={str(p.relative_to(H / '.config/SmartPC')): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (H / '.config/SmartPC').rglob('*') if p.is_file()})


if __name__ == '__main__':
    before = preserved()
    subprocess.run(['systemctl', 'stop', 'smartpc-dashboard'], check=True)
    try:
        rows = []
        env = ['HOME=' + str(H), 'QT_QPA_PLATFORM=eglfs', 'QT_QPA_EGLFS_INTEGRATION=eglfs_kms',
               'QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json', 'QT_QPA_EGLFS_HIDECURSOR=1',
               'QSG_RHI_BACKEND=opengl', 'OPENBLAS_NUM_THREADS=1', 'OMP_NUM_THREADS=1']
        for theme in ('base', 'functional', 'apple'):
            with (P / ('native-' + theme + '.txt')).open('w') as log:
                subprocess.run(['runuser', '-u', 'smartpc', '--', 'env', *env, str(PY),
                                str(S / 'check_header_clock_ui.py'), '--theme', theme,
                                '--output', str(P / theme)], cwd=S.parent, stdout=log,
                               stderr=subprocess.STDOUT, check=True, timeout=150)
            report = json.loads((P / theme / 'report.json').read_text())
            assert report['status'] == 'passed' and report['window'] == [960, 640] and not report['qmlWarnings']
            rows.append(dict(theme=theme, views=len(report['navigation'])))
            print('EGLFS passed: ' + theme, flush=True)
        assert before == preserved(), 'Native fixtures altered production state'
        manifest = json.loads((S / 'release-manifest.json').read_text())
        (P / 'native-checks.json').write_text(json.dumps(dict(status='passed', cases=rows,
            productionStatePreserved=True, sourceHashes=manifest['sha256']), indent=2) + '\n')
    finally:
        subprocess.run(['systemctl', 'start', 'smartpc-dashboard'], check=True)
