"""Run locally; source identity and location inventory, not a performance test."""
import datetime
import hashlib
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[4]
patterns = {
    'game.py': r'def snapshot|def _refresh|def _poll|def stop|Queue\(maxsize|setInterval|context.Process',
    'game_worker.py': r'os.setpriority|OPENBLAS_NUM_THREADS|def save|def publish|capture_ms|time.sleep',
    'game_checkpoint_writer.py': r'def submit|def persist_snapshot|deepcopy|np.ndarray|subprocess.Popen',
    'game_presentation.py': r'1 / 30|SMARTPC_GAME_PRESENTER|def _timeout',
    'state.py': r'_dashboard_cache|_invalidate_dashboards',
    'theme_api.py': r'def updateLegacy|def bindGameScene|def normalize_legacy|def _cached',
    'theme_contexts.py': r'def snapshot_equal|def _update',
    'components/PublicContextAdapter.qml': r'streamGameScene|c.active === false|modelDomains|function scheduleRefresh|Qt.callLater',
    'components/ViewHost.qml': r'retainedLoaders|asynchronous:|function rendererKey',
    'presentations/GameVisual.qml': r'GamePresentationClock|FrameAnimation|currentFrame%2|Canvas|Shape \{',
    'game_native.py': r'ctypes.CDLL|def rays|class SparsePopulation',
    'game_native.c': r'void smartpc_|double',
    'game_store.py': r'def drivers|def driver_events|def sessions|def history|def total_seconds',
    'game_dossier.py': r'def dossier|store.sessions|driver_events',
    'game_results.py': r'def exercise',
    'game_residual_learning.py': r'def checkpoint|def encode_replay|_replaySnapshot',
    'game_residual_trainer.py': r'def checkpoint|def frame|evaluations.*\[-20:',
    'game_academy_trainer.py': r'evaluations.*\[-40:|def checkpoint',
    'theme_models.py': r'def _replace|dataChanged|beginInsertRows',
    'Main.qml': r'clockTimer|themeService.heartbeat|function publicSurfacePayload',
    'verify_performance_ui.py': r'def stats|ordered\[|frame_protocol',
    'weather.py': r'QThreadPool.globalInstance|def _on_finished',
    'sport.py': r'QThreadPool.globalInstance|def _finished',
    'network.py': r'QThreadPool.globalInstance|def _finished',
    'theme_lifecycle.py': r'health_root=|def heartbeat',
    'run.sh': r'QSG_RHI_BACKEND|QT_QPA_PLATFORM|QT_QPA_EGLFS',
}
paths = {f'dashboard/{name}': expression for name, expression in patterns.items()}
paths.update({
    'os/system/smartpc-dashboard.service': r'ExecStart|CacheDirectory|Memory|Nice|CPU',
    'scripts/build-game-native.sh': r'-O3|-ffp-contract',
    'theme-projects/apple-calm/bundle/qml/MiniHistory.qml': r'!visible|requestPaint|onPaint',
    'theme-projects/apple-calm/bundle/qml/NetworkHistoryChart.qml': r'!visible|requestPaint|onPaint',
    'theme-projects/apple-calm/bundle/qml/OutlineIcon.qml': r'Image|icon-atlas|cache:',
})
result = {'capturedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'scope': 'Local source inspection only; candidates are not measured bottlenecks',
          'files': []}
for name, expression in paths.items():
    path = root/name
    text = path.read_text()
    result['files'].append({'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'lines': len(text.splitlines()),
        'locations': [{'line': index, 'text': line.strip()[:220]}
                      for index, line in enumerate(text.splitlines(), 1) if re.search(expression, line)][:35]})
qml = list((root/'theme-projects/apple-calm/bundle/qml').rglob('*.qml'))
result['appleQmlFiles'] = len(qml)
result['appleCanvasDeclarations'] = [{'path': str(path.relative_to(root)), 'line': index}
    for path in qml for index, line in enumerate(path.read_text().splitlines(), 1)
    if re.search(r'\bCanvas\s*\{', line)]
print(json.dumps(result, indent=2))
