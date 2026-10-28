"""Static whole-system source/callback/timer/resource inventory, not a profiler."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import struct

root = Path(__file__).resolve().parents[4]
modules = ('app state dashboard_summary module_state weather weather_alerts account system_info keypad '
           'sport sport_core football football_free sport_team sport_team_core fantacalcio fantacalcio_live '
           'motorsport motorsport_core racing_details racing_timing racing_events '
           'casa casa_core tuya_core network network_core network_metrics network_history network_events iliadbox '
           'events event_core theme_api theme_contexts theme_models theme_service theme_lifecycle theme_supervisor '
           'theme_runtime theme_bundle theme_resources theme_pack').split()
rows = []
for name in modules:
    path = root/'dashboard'/(name+'.py')
    if not path.exists():
        continue
    text = path.read_text()
    tree = ast.parse(text)
    rows.append(dict(path=str(path.relative_to(root)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        lines=len(text.splitlines()), methods=[dict(name=n.name, line=n.lineno) for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and (n.name in ('__init__', 'refresh', '_finished', '_on_finished',
                '_tick', 'moduleState', 'snapshot', 'heartbeat', 'dashboardSummary', 'metricsView', 'publish_snapshot')
                or any(key in n.name for key in ('persist', 'save', 'cache')))],
        timerAndIoSites=[dict(line=i, text=line.strip()[:200]) for i, line in enumerate(text.splitlines(), 1)
            if any(key in line for key in ('setInterval(', 'timeout.connect', 'QThreadPool', 'sqlite3.connect',
                'fsync(', 'QProcess(', 'deepcopy(', 'json.loads(', 'read_text('))][:65]))
for name in ('dashboard/Main.qml', 'dashboard/components/ViewHost.qml', 'dashboard/components/PublicContextAdapter.qml',
             'dashboard/components/SceneHost.qml', 'os/system/smartpc-dashboard.service',
             'os/system/smartpc-display-level.service', 'os/system/smartpc-display-level.timer',
             'os/system/zz-smartpc-journal.conf', 'dashboard/run.sh'):
    p = root/name
    rows.append(dict(path=name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), lines=len(p.read_text().splitlines())))
bundle = root/'theme-projects/apple-calm/bundle'
assets = []
for p in bundle.rglob('*'):
    if p.is_file() and p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.ttf', '.otf', '.woff', '.woff2'):
        item = dict(path=str(p.relative_to(root)), bytes=p.stat().st_size)
        if p.suffix.lower() == '.png':
            with p.open('rb') as f:
                header = f.read(24)
            if header[:8] == b'\x89PNG\r\n\x1a\n':
                item['width'], item['height'] = struct.unpack('>II', header[16:24])
        assets.append(item)
r = dict(capturedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         scope='Whole-system source structure; sites are candidates, not measured time percentages',
         files=rows, appleQmlFiles=len(list(bundle.rglob('*.qml'))), appleAssets=assets)
print(json.dumps(r, indent=2))
