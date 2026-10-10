#!/usr/bin/env python3
"""Dashboard geometry, content parity and real navigation with isolated providers."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from theme_fixture_support import isolate_process, LegacyHarness, read_corpus

parser = argparse.ArgumentParser()
parser.add_argument('--theme', choices=['base', 'functional', 'apple'], default='base')
parser.add_argument('--palette', choices=['day', 'night'], default='night')
parser.add_argument('--capture-dir', type=Path)
args = parser.parse_args()
private, data = isolate_process()
h = None
checks = []
try:
    from PySide6.QtCore import QObject, QPointF, QCoreApplication, QEvent, qVersion
    from theme_test_support import as_value
    from theme_bundle import BundleManager, validate_project
    from theme_api import normalize_dto
    project = Path(__file__).resolve().parents[1] / 'theme-projects/apple-calm/bundle'
    if args.theme == 'apple':
        valid = validate_project(project)
        cache = json.loads((project.parent / 'evidence/preflight-cache.json').read_text())
        assert cache['digest'] == valid['digest'] and cache['result']['status'] == 'passed'
        assert cache['result']['qt'] == qVersion()
        BundleManager(data).import_bundle(project, preflight=lambda *_: cache['result'], require_preflight=True)
    h = LegacyHarness(data, {'theme':args.theme if args.theme != 'apple' else 'base', 'variant':args.palette, 'motion':'off'})
    if args.theme == 'apple':
        assert h.service.selectDraft('studio.applecalm')
    _, cases, _ = read_corpus()
    output = args.capture_dir or Path(private.name) / 'captures'
    output.mkdir(parents=True, exist_ok=True)
    names = {'home.now':'homeNow', 'home.day':'homeDay', 'weather.now':'weatherNow',
             'weather.forecast':'weatherForecast', 'account.usage':'accountPanel',
             'casa.overview':'casaOverview', 'casa.devices':'casaDevices',
             'network.overview':'networkOverview', 'sport.hub':'sportHub'}
    def setup(sid):
        h.setup(next(c for c in cases if c['surfaceId'] == sid))
        h.wait_ready()
        h.pump(120)
        host = h.root.findChild(QObject, names[sid])
        return as_value(host.property('currentItem'))
    def tree(item):
        yield item
        for child in item.childItems():
            yield from tree(child)
    def box(item):
        p = item.mapToScene(QPointF(0, 0))
        return [round(v, 2) for v in (p.x(), p.y(), item.width(), item.height())]
    def cards(item):
        return [c for c in tree(item) if c.isVisible() and c.opacity() > 0 and
                c.property('radius') is not None and float(c.property('radius')) > 0 and c.width() > 100 and c.height() > 55]
    def texts(item):
        return [c.property('text') for c in tree(item) if c.isVisible() and c.property('text')]
    def capture(name):
        h.pump(80)
        assert h.window.grabWindow().save(str(output / (name + '.png')))
    geometry = []
    for sid in names:
        item = setup(sid)
        assert box(item) == [24.0, 72.0, 912.0, 552.0], (sid, box(item))
        visible = cards(item)
        for c in visible:
            x, y, w, ht = box(c)
            assert x >= 23.5 and x+w <= 936.5 and y >= 71.5 and y+ht <= 624.5, (sid, box(c))
        if visible:
            last = max(box(c)[1] + c.height() for c in visible)
            # Apple PageCanvas includes a source line; other grids reach the margin.
            assert 624-last <= 44, (sid, last)
        geometry.append({'surface':sid,'bounds':box(item),'cards':len(visible)})
        capture(sid)
    for scale in (1.1, 1.0):
        assert h.service.setToken('typography.textScale', scale)
        item = setup('casa.overview')
        tiles = [c for c in tree(item) if c.objectName().startswith('dashboardCard')]
        assert len(tiles) == 4
        for c in tiles:
            x, y, w, ht = box(c)
            assert y+ht <= 624.5
            for child in tree(c):
                if child.property('text') and child.isVisible():
                    xx, yy, ww, hh = box(child)
                    assert xx >= x-0.5 and xx+ww <= x+w+0.5 and yy >= y-0.5 and yy+hh <= y+ht+0.5, (child.property('text'), box(child), box(c))
        capture('casa-scale-'+str(scale))
        checks.append('four-favourites-contained-scale-'+str(scale))
    item = setup('casa.overview')
    h.expression('activateKey(8)');h.expression('activateKey(8)');h.wait_ready()
    assert h.value('activeContentId') == 'casa.devices'
    h.expression('activateKey(5)');h.wait_ready()
    assert h.value('overlay') == 'casaList'
    h.expression('activateKey(8)');h.expression('activateKey(5)');h.wait_ready()
    assert h.value('overlay') == 'casaDetail'
    selected = h.value('casaSelectedId')
    h.expression('activateKey(7)');h.wait_ready()
    assert h.value('overlay') == 'casaList' and h.value('casaSelectedId') == selected
    h.expression('activateKey(7)');h.wait_ready()
    assert h.value('dashboardViewId') == 'casa-dispositivi'
    checks.append('casa-dashboard-inventory-details-return-preserves-selection')
    item = setup('network.overview')
    assert any('Mbit/s' in t for t in texts(item)), texts(item)
    h.expression('activateKey(8)');h.wait_ready()
    host=h.root.findChild(QObject,'networkOverview');item=as_value(host.property('currentItem'))
    assert any('51' in t and '°C' in t for t in texts(item)), texts(item)
    assert any('radio' in t for t in texts(item)), texts(item)
    assert any('porte' in t for t in texts(item)), texts(item)
    original_caps = deepcopy(h.network._caps)
    for cap in h.network._caps.values(): cap['at'] = h.now-3600
    h.network.metricsChanged.emit();h.pump(150)
    assert sum('Precedente' in t for t in texts(item)) >= 2, texts(item)
    capture('network-previous')
    h.network._caps = {};h.network.metricsChanged.emit();h.pump(150)
    assert sum(t == '—' for t in texts(item)) >= 2, texts(item)
    assert not any('0 radio' in t or '0 porte' in t for t in texts(item))
    h.network._caps = original_caps;h.network.metricsChanged.emit();h.pump(150)
    checks.append('cached-catalogs-do-not-invent-zero-or-current-data')
    h.expression('activateKey(5)');h.wait_ready()
    assert h.value('overlay') == 'networkRouter'
    h.expression('activateKey(7)');h.wait_ready()
    assert h.value('dashboardViewId') == 'rete-iliadbox' and h.value('overlay') == ''
    checks.append('WAN-temperature-dashboard-and-detail-return')
    item = setup('account.usage')
    h.account.value['data'] = {'plan':'Fixture', 'windows':[
        {'label':'5 ore','usedPercent':24,'windowDurationMins':300,'resetsAt':h.now+3600},
        {'label':'7 giorni','usedPercent':62,'windowDurationMins':10080,'resetsAt':h.now+86400}],
        'credits':{'unlimited':False,'balance':'12'}, 'resetCredits':None}
    h.account.changed.emit()
    h.wait_ready()
    h.pump(150)
    assert any(t == '12' for t in texts(item)), texts(item)
    assert not any('undefined' in t for t in texts(item))
    capture('account-normalized')
    assert not any('5 ore · 5 ore' in t for t in texts(item))
    for value, available in [('',False),('0',True),(0,True),('12',True)]:
        credits = normalize_dto('AccountCredits', {'unlimited':False,'balance':value})
        assert credits['balance']['available'] == available
        if available: assert str(credits['balance']['value']) == str(value)
    h.account.value['data']['credits'] = {'unlimited':True,'balance':''}
    h.account.changed.emit()
    h.pump(120)
    assert any('illimitati' in t.lower() for t in texts(item))
    h.account.value['data']['windows'] = [{'label':'Utilizzo a zero','usedPercent':0,'windowDurationMins':300,'resetsAt':None}]
    h.account.value['data']['credits'] = {'unlimited':False,'balance':0}
    h.account.changed.emit()
    h.pump(150)
    assert any(t == '0' for t in texts(item)) and any(t == '0%' for t in texts(item)), texts(item)
    capture('account-zero-single-window')
    h.account.value['data']['windows'] = []
    h.account.value['data']['credits'] = {'unlimited':False,'balance':''}
    h.account.changed.emit()
    h.pump(150)
    assert not any(t == '0' or t == '0%' for t in texts(item)), texts(item)
    capture('account-missing')
    checks.append('credits-present-zero-unavailable-and-unlimited-distinct')
    h.account.value['status']='offline'
    h.account.value['data']['windows']=[{'label':'5 ore','usedPercent':0,'windowDurationMins':300,'resetsAt':h.now+3600}]
    h.account.value['data']['credits']={'unlimited':False,'balance':0}
    h.account.changed.emit();h.pump(120)
    h.expression('activateKey(5)');h.wait_ready();h.pump(100)
    detail=as_value(h.root.findChild(QObject,'overlayHost').property('currentItem'))
    assert any('Dato precedente' in t for t in texts(detail)),texts(detail)
    assert any(t=='0%' for t in texts(detail)),texts(detail)
    capture('account-previous-details')
    h.expression('activateKey(7)');h.wait_ready()
    checks.append('account-details-retain-source-age-and-real-zero')
    assert h.window.activeFocusItem().objectName() == 'inputOwner'
    assert not h.messages, h.messages
    assert not h.transport, h.transport
    assert not any(h.effects.values()), h.effects
    report = {'status':'passed','theme':args.theme,'palette':args.palette,'qt':qVersion(),
              'platform':h.app.platformName(),'windowSize':[960,640],'geometry':geometry,'checks':checks,
              'qmlWarnings':h.messages,'transportCalls':len(h.transport),
              'scope':'Real Main with offline fixtures; not live provider or physical readability proof'}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
finally:
    if h:
        h.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QCoreApplication.processEvents()
    private.cleanup()
