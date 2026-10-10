"""Replay observed provider data in real Main; no network or production settings."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--dashboard', type=Path, default=Path(__file__).resolve().parents[3])
parser.add_argument('--theme', choices=['base', 'functional', 'apple'], default='base')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.dashboard))
from theme_fixture_support import isolate_process, LegacyHarness

private, data = isolate_process()
h = None
try:
    from PySide6.QtCore import QDateTime
    from theme_bundle import BundleManager, validate_project
    source = Path(__file__).resolve().parent
    if args.theme == 'apple':
        project = args.dashboard.parent / 'theme-projects/apple-calm/bundle'
        valid = validate_project(project)
        cache = json.loads((project.parent / 'evidence/preflight-cache.json').read_text())
        assert cache['digest'] == valid['digest'] and cache['result']['status'] == 'passed'
        BundleManager(data).import_bundle(project, preflight=lambda *_: cache['result'], require_preflight=True)
    h = LegacyHarness(data, {'theme': 'base' if args.theme == 'apple' else args.theme, 'variant': 'day', 'motion': 'off'})
    if args.theme == 'apple':
        assert h.service.selectDraft('studio.applecalm')
        h.wait_ready()
    args.output.mkdir(parents=True, exist_ok=True)
    observed = json.loads((source / 'observed-sport-cache.json').read_text())['snapshot']
    h.now = max(m.get('fetchedAt', 0) for m in observed['fixtures']) + 2
    h.root.setProperty('now', QDateTime.fromSecsSinceEpoch(int(h.now)))
    h.sport._snapshot = deepcopy(observed)
    h.sport._from_cache = False
    h.sport._error = ''
    h.sport.changed.emit()
    h.root.setProperty('familyId', 'sports')
    h.root.setProperty('sportHubSelectedId', 'sport')
    h.wait_ready()
    summary = h.state.dashboardSummary('sport-sport', h.now)
    assert summary['cards'][0]['title'] == 'In corso', summary
    assert summary['cards'][0]['value'] == '2 – 1', summary
    assert 'Genoa' in summary['cards'][0]['subtitle']
    assert h.window.grabWindow().save(str(args.output / 'serie-a-in-progress.png'))
    h.expression('activateKey(5)'); h.wait_ready()
    assert h.value('overlay') == 'sportList' and h.value('sportView') == 'IN CORSO'
    assert h.value('sportRows')[0]['canonicalMatchId'] == summary['eventId']
    h.expression('activateKey(7)'); h.wait_ready()
    assert h.value('familyId') == 'sports' and h.value('overlay') == ''
    h.sport._from_cache = True; h.sport.changed.emit()
    saved = h.state.dashboardSummary('sport-sport', h.now)
    assert saved['cards'][0]['title'] != 'In corso'
    h.sport._from_cache = False; h.sport.changed.emit()

    clock = json.loads((source / 'observed-timing.json').read_text())
    f1 = h.racing['f1']
    f1._snapshot = json.loads((source / 'observed-f1-cache.json').read_text())['snapshot']
    f1._from_cache = False; f1._offline = False; f1._error = ''
    h.root.setProperty('sportHubSelectedId', 'f1')
    timing = f1._timing.state
    timing.reset(); timing.connected = True
    for topic, value in clock['topics'].items():
        timing.apply(topic, value, h.now)
    f1.changed.emit(); h.wait_ready()
    ended = h.state.dashboardSummary('sport-f1', h.now)
    assert ended['sessionId'] == 'f1:2026:17:Q' and ended['mode'] == 'timing', ended
    assert ended['cards'][0]['value'] == 'Terminata' and len(f1.moduleState['data']['live']['rows']) == 22
    assert h.window.grabWindow().save(str(args.output / 'f1-qualifying-finished.png'))
    h.expression('activateKey(5)'); h.wait_ready()
    assert h.value('overlay') == 'racingTiming' and h.value('racingSessionId') == ended['sessionId']
    assert h.window.grabWindow().save(str(args.output / 'f1-qualifying-timing-detail.png'))
    h.expression('activateKey(7)'); h.wait_ready()
    assert h.value('familyId') == 'sports'

    # Active-session routing uses observed rows and simulated status/time.
    # This qualifies routing, not a live session or feed latency.
    h.now = clock['observedAt'] - 1800
    h.root.setProperty('now', QDateTime.fromSecsSinceEpoch(int(h.now)))
    timing.reset(); timing.connected = True
    for topic, value in clock['topics'].items():
        timing.apply(topic, value, h.now)
    timing.apply('SessionStatus', {'Status': 'Started'}, h.now)
    f1.changed.emit(); h.wait_ready()
    active = h.state.dashboardSummary('sport-f1', h.now)
    assert active['mode'] == 'timing' and active['cards'][0]['value'] == 'In corso', active
    h.expression('activateKey(5)'); h.wait_ready()
    assert h.value('overlay') == 'racingTiming'
    h.expression('activateKey(7)'); h.wait_ready()
    h.now += 100
    f1.changed.emit()
    stale = h.state.dashboardSummary('sport-f1', h.now)
    assert stale['cards'][0]['value'] not in ('In corso', 'In diretta')
    assert not h.transport, h.transport
    assert not h.messages, h.messages
    report = {'status': 'passed', 'theme': args.theme, 'source': 'observed Serie A and concluded Singapore qualifying; active F1 status/time simulated',
              'serieA': summary, 'concludedF1': ended, 'simulatedActiveF1': active, 'networkAttempts': h.transport, 'qmlMessages': h.messages}
    (args.output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'theme': args.theme, 'networkAttempts': h.transport, 'qmlMessages': h.messages}))
finally:
    if h:
        h.close()
    private.cleanup()
