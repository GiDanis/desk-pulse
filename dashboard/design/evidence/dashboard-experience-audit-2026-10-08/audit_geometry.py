"""Analysis-only: current theme geometry and screenshots, offline fixtures."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'dashboard'))
from theme_fixture_support import isolate_process, LegacyHarness, read_corpus

parser = argparse.ArgumentParser()
parser.add_argument('--palette', choices=['day', 'night'], default='night')
parser.add_argument('--theme', choices=['apple', 'base', 'functional'], default='apple')
parser.add_argument('--account-normalized-only', action='store_true')
args = parser.parse_args()
output = Path(__file__).parent / (args.theme + '-' + args.palette)
output.mkdir(parents=True, exist_ok=True)
private, data = isolate_process()
h = None
try:
    from PySide6.QtCore import QObject, QPointF, qVersion
    from PySide6.QtQuick import QQuickItem
    from theme_bundle import BundleManager, validate_project
    from theme_test_support import as_value
    bundle = ROOT / 'theme-projects/apple-calm/bundle'
    validation = validate_project(bundle)
    cache = json.loads((bundle.parent / 'evidence/preflight-cache.json').read_text())
    assert cache['digest'] == validation['digest'] and cache['result']['status'] == 'passed'
    assert cache['result']['qt'] == qVersion()
    if args.theme == 'apple':
        BundleManager(data, app_root=ROOT / 'dashboard').import_bundle(
            bundle, preflight=lambda *_: cache['result'], require_preflight=True)
    h = LegacyHarness(data, {'theme': args.theme if args.theme != 'apple' else 'base', 'variant': args.palette, 'motion': 'off'})
    if args.theme == 'apple':
        assert h.service.selectDraft('studio.applecalm')
    h.wait_ready()
    _, cases, contract = read_corpus()
    presentations = json.loads((bundle / 'theme.json').read_text())['presentations']
    names = {'home.now': 'homeNow', 'home.clock': 'homeClock', 'home.day': 'homeDay',
             'weather.now': 'weatherNow', 'weather.forecast': 'weatherForecast', 'account.usage': 'accountPanel',
             'sport.hub': 'sportHub', 'sport.overview': 'sportPanel', 'sport.team': 'sportTeamPanel',
             'racing.overview': 'racingPanel', 'casa.overview': 'casaOverview', 'casa.devices': 'casaDevices',
             'network.overview': 'networkOverview', 'network.devices': 'networkDevices',
             'alerts.badge': 'unreadAlertsBadge', 'alerts.banner.small': 'eventBanner',
             'alerts.banner.large': 'eventLargeBanner', 'alerts.urgent': 'eventUrgent',
             'alerts.inbox': 'alertsInbox', 'alerts.detail': 'alertDetail', 'shell.main': 'shellHost'}

    def bounds(item):
        point = item.mapToScene(QPointF(0, 0))
        x, y, w, ht = point.x(), point.y(), item.width(), item.height()
        return [round(v, 2) for v in (x, y, w, ht)]

    def effective_bounds(item):
        x, y, w, ht = bounds(item)
        left, top, right, bottom = max(0, x), max(0, y), min(960, x+w), min(640, y+ht)
        current = item
        while current:
            if not current.isVisible() or current.opacity() <= 0:
                return None
            if current.clip():
                xx, yy, ww, hh = bounds(current)
                left, top, right, bottom = max(left, xx), max(top, yy), min(right, xx+ww), min(bottom, yy+hh)
            current = current.parentItem()
        return [left, top, right-left, bottom-top] if right > left and bottom > top else None

    def collect(item):
        cards, labels, lists = [], [], []
        # Repeater/ListView delegates are in the visual tree, not necessarily the
        # QObject ownership tree. Walk childItems so geometry includes them.
        def visual_tree(node):
            yield node
            for child in node.childItems():
                yield from visual_tree(child)
        for child in visual_tree(item):
            box = effective_bounds(child)
            if box is None:
                continue
            class_name = child.metaObject().className()
            radius = child.property('radius')
            text = child.property('text')
            original = bounds(child)
            if radius is not None and float(radius) > 0 and original[2] >= 100 and original[3] >= 55:
                cards.append({'type': class_name, 'bounds': bounds(child), 'visibleBounds': box})
            if text and isinstance(text, str):
                labels.append({'text': text, 'bounds': bounds(child), 'visibleBounds': box})
            if child.property('contentHeight') is not None and child.property('contentY') is not None:
                lists.append({'type': class_name, 'bounds': bounds(child),
                              'contentHeight': child.property('contentHeight'), 'contentY': child.property('contentY')})
        return cards, labels, lists

    records, seen = [], set()
    for case in cases:
        sid = case['surfaceId']
        if args.account_normalized_only and sid != 'account.usage':
            continue
        if sid not in presentations or sid in seen:
            continue
        seen.add(sid)
        h.setup(case)
        if args.account_normalized_only:
            h.account.value['data'] = {'plan':'Fixture', 'windows':[
                {'label':'5 ore', 'usedPercent':24, 'remainingPercent':76, 'windowDurationMins':300, 'resetsAt':h.now+3600},
                {'label':'7 giorni', 'usedPercent':62, 'remainingPercent':38, 'windowDurationMins':10080, 'resetsAt':h.now+86400}],
                'credits':{'unlimited':False, 'balance':'12'}, 'resetCredits':None}
            h.account.changed.emit()
        h.wait_ready()
        h.pump(150)
        for expression in case['expectedExpressions']:
            assert h.expression(expression), (case['id'], expression)
        host = h.root.findChild(QObject, names.get(sid, 'overlayHost'))
        assert host is not None, sid
        item = as_value(host.property('currentItem'))
        legacy = item is None
        if legacy:
            assert args.theme != 'apple', sid
            item = h.window.contentItem()
        elif args.theme == 'apple':
            assert item.property('contentReady') is True, sid
        else:
            assert host.property('currentReady') is True, sid
        cards, labels, lists = collect(item)
        last = max((c['visibleBounds'][1]+c['visibleBounds'][3] for c in cards), default=None)
        root_box = bounds(item)
        status = [l for l in labels if l['bounds'][1] >= root_box[1]+root_box[3]-55]
        next_status = min((l['bounds'][1] for l in status if last is not None and l['bounds'][1] >= last), default=None)
        record = {'surface': sid, 'case': case['id'], 'renderer': 'legacy core' if legacy else str(host.property('loadedPresentationId')),
                  'legacyWholeWindowMeasurement': legacy,
                  'rootBounds': root_box, 'cards': cards, 'labels': labels, 'scrollContainers': lists,
                  'lastVisibleCardBottom': last, 'gapToRootBottom': None if last is None else round(root_box[1]+root_box[3]-last,2),
                  'gapBeforeBottomStatus': None if next_status is None else round(next_status-last,2),
                  'providerEffects': dict(h.effects)}
        suffix = '-normalized' if args.account_normalized_only else ''
        assert h.window.grabWindow().save(str(output / (sid + suffix + '.png')))
        records.append(record)
        print(sid, record['gapToRootBottom'], record['gapBeforeBottomStatus'], flush=True)
    assert not h.messages and not h.transport
    report = {'status': 'passed', 'scope': 'Unmodified current renderers; one canonical fixture per owned surface; analysis only',
              'qt': qVersion(), 'platform': h.app.platformName(), 'windowSize': [h.window.width(),h.window.height()],
              'palette': args.palette, 'theme': args.theme, 'themeDigest': validation['digest'] if args.theme == 'apple' else None, 'apiFingerprint': contract.fingerprint,
              'records': records, 'qmlWarnings': h.messages, 'transportCalls': len(h.transport),
              'measurementLimit': 'Card bounds, not all semantic content or optical coverage; sparse/alert states need separate interpretation'}
    report['accountNormalizedFixture'] = args.account_normalized_only
    report_name = 'audit-account-normalized.json' if args.account_normalized_only else 'audit.json'
    (output / report_name).write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print('DONE', len(records), flush=True)
finally:
    if h:
        h.close()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QCoreApplication.processEvents()
    private.cleanup()
