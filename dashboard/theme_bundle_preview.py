#!/usr/bin/env python3
"""Isolated real-QML renderer previews using public Theme API contexts.

These proofs concern renderer loading/geometry/readiness/lifecycle, not the
complete Main workflow, optical appearance, GPU latency or board performance.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def _snapshot_style(engine, contract, appearance):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent
    component = QQmlComponent(engine)
    component.setData(b'import QtQuick\nimport "themes"\nStyleFacade {}', QUrl.fromLocalFile(str(ROOT / 'PreviewStyle.qml')))
    style = component.createWithInitialProperties({'appearance': appearance})
    if style is None:
        raise ValueError('\n'.join(error.toString() for error in component.errors()))
    style.setParent(engine)
    from PySide6.QtQml import QQmlEngine
    QQmlEngine.setObjectOwnership(style, QQmlEngine.CppOwnership)
    def value(obj, name):
        result = obj.property(name)
        if hasattr(result, 'toVariant'): result = result.toVariant()
        if hasattr(result, 'name'): result = result.name()
        return result
    snapshot = {}
    for name, spec in contract.fields('ThemeStyle').items():
        if spec['type'] == 'SemanticPalette':
            semantic = value(style, name)
            snapshot[name] = {key: value(semantic, key) for key in contract.fields('SemanticPalette')}
        else:
            snapshot[name] = value(style, name)
    return style, snapshot


def render_project(project, output, matrix=False, visible=False):
    # Isolation precedes Qt and all service imports.
    from theme_fixture_support import isolate_process
    private, base = isolate_process()
    messages = []
    app = engine = window = None
    try:
        from PySide6.QtCore import QObject, QUrl, qInstallMessageHandler, qVersion, QMetaObject
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
        from PySide6.QtQuick import QQuickItem, QQuickWindow
        from theme_api import bootstrap_theme_api, PublicContextFactory
        from theme_contexts import default_snapshot
        from theme_api_contract import ThemeApiContract
        from theme_core import ThemeCatalog
        from theme_bundle import validate_project, register_catalog, DEFAULT_SHELL_LAYOUT
        project = Path(project).resolve(); output = Path(output).resolve()
        if output.exists() and any(output.iterdir()):
            raise ValueError('Cartella anteprime non vuota: scegliere una nuova destinazione')
        output.mkdir(parents=True, exist_ok=True)
        valid = validate_project(project, app_root=ROOT)
        if valid['status'] not in ('valid', 'passed', 'verified'):
            return {'reportVersion': 1, 'operation': 'preview', 'status': 'failed', 'validation': valid}
        registry = json.loads((project / 'visual-registry.json').read_text())
        layout = deepcopy(valid['manifest'].get('layout', DEFAULT_SHELL_LAYOUT))
        page_width, page_height = layout['content']['width'], layout['content']['height']
        app = QGuiApplication([])
        previous_handler = qInstallMessageHandler(lambda kind, context, message: messages.append(message))
        engine = QQmlApplicationEngine(); bootstrap_theme_api(engine)
        factory = PublicContextFactory()
        contract = ThemeApiContract()
        catalog = ThemeCatalog()
        register_catalog(catalog, {'id': valid['id'], 'version': valid['version'], 'digest': valid['digest'], 'payload': str(project), 'manifest': valid['manifest'], 'registry': registry, 'files': valid['files']})
        from PySide6.QtGui import QFontDatabase, QImageReader
        font_families = {}; registered_fonts = []; resource_checks = []
        for resource in valid['manifest']['resources']:
            path = project / resource['path']
            if resource['type'] == 'font':
                number = QFontDatabase.addApplicationFont(str(path))
                families = QFontDatabase.applicationFontFamilies(number) if number >= 0 else []
                assert families, 'Font non decodificabile: ' + resource['path']
                registered_fonts.append(number); font_families[resource['id']] = families[0]
                resource_checks.append({'id': resource['id'], 'type': 'font', 'status': 'passed', 'families': families})
            elif resource['type'] in ('image', 'preview'):
                reader = QImageReader(str(path)); image = reader.read()
                assert not image.isNull(), 'Immagine non decodificabile: ' + resource['path']
                resource_checks.append({'id': resource['id'], 'type': resource['type'], 'status': 'passed', 'decodedSize': [image.width(), image.height()]})
        imports = '\n'.join('import ' + module + (' 2.0' if module == 'SmartPC.ThemeApi' else '') for module in valid['manifest']['qtModules'])
        module_probe = QQmlComponent(engine); module_probe.setData((imports + '\nQtObject {}').encode(), QUrl.fromLocalFile(str(ROOT / 'PreviewModules.qml')))
        assert module_probe.status() == QQmlComponent.Ready, 'Import modulo fallito: ' + '\n'.join(error.toString() for error in module_probe.errors())
        module_object = module_probe.create(); module_object.setParent(engine)
        window = QQuickWindow(); window.resize(960, 640)
        if visible: window.show()
        else: window.show()  # The platform is offscreen unless explicitly overridden.
        def pump(duration=80):
            deadline = time.monotonic() + duration / 1000
            while time.monotonic() < deadline:
                app.processEvents(); time.sleep(.001)
        pairs = [(variant, mode) for variant in ('day', 'night') for mode in ('normal', 'reduced', 'off')] if matrix else [('day', 'off')]
        rows = []
        # Mandatory fields tested with Unicode, no-spaces and normal independent cases.
        cases = ['normal', 'longUnicode', 'noSpaces'] if matrix else ['normal']
        network = []
        def denied(*args, **kwargs):
            network.append('denied'); raise RuntimeError('Theme preview network denied')
        with patch('socket.socket.connect', side_effect=denied), patch('socket.getaddrinfo', side_effect=denied):
            import socket
            try: socket.socket().connect(('127.0.0.1', 1))
            except RuntimeError: pass
            assert network == ['denied']; network.clear()
            for renderer in registry.get('presentations', []):
                for surface in renderer['contentIds']:
                    type_name = contract.surfaces[surface]['context']
                    host_family = contract.surfaces[surface]['hostFamily']
                    for variant, mode in pairs:
                        appearance = catalog.resolve(valid['id'], variant=variant)
                        for token, value in appearance['tokens'].items():
                            if isinstance(value, str) and value.startswith('asset:'):
                                asset_id = value[6:]
                                if asset_id not in font_families:
                                    asset = next((a for a in appearance['assets'] if a['id'] == asset_id and a['type'] == 'font'), None)
                                    assert asset is not None, 'Asset font mancante: ' + asset_id
                                    number = QFontDatabase.addApplicationFont(asset['file']); families = QFontDatabase.applicationFontFamilies(number) if number >= 0 else []
                                    assert families, 'Font non caricabile: ' + asset_id
                                    registered_fonts.append(number); font_families[asset_id] = families[0]
                                appearance['tokens'][token] = font_families[asset_id]
                        appearance['motionMode'] = mode
                        style_object, style = _snapshot_style(engine, contract, appearance)
                        for case in cases:
                            snapshot = default_snapshot(type_name)
                            snapshot.update(contentId=surface, style=deepcopy(style), appearanceRevision=1)
                            if 'clock' in snapshot:
                                snapshot['clock'].update(timeText='23:59', dateText='DOMENICA 4 OTTOBRE 2026', timezone='Europe/Rome', locale='it_IT', night=variant=='night')
                            if 'motionPolicy' in contract.fields(type_name):
                                snapshot['motionPolicy'].update(mode=mode, suspended=False, urgent=surface == 'alerts.urgent')
                            if host_family in ('page', 'overlay'):
                                snapshot['lifecycle'].update(state='active', active=True, interactive=False, preview=True, generation=1)
                                snapshot['viewport'] = snapshot['safeArea'] = {'x': 0, 'y': 0, 'width': page_width if host_family == 'page' else 960, 'height': page_height if host_family == 'page' else 640}
                            if type_name == 'PageContext':
                                if case != 'normal':
                                    weather = default_snapshot('WeatherData')
                                    weather.update(location='Angri', description='Zero è un valore valido')
                                    weather['temperature'].update(available=True, value=0, displayText='0°', unit='°C')
                                    weather['source'].update(status='offline', hasData=True, isStale=True, sourceId='fixture', sourceLabel='Fixture offline')
                                    event = default_snapshot('NextEventData')
                                    event.update(id='fixture.future', title='Evento futuro' if case == 'longUnicode' else '界' * 100, whenText='Domani · 08:00')
                                    snapshot.update(weather=weather, nextEvent=event)
                            elif type_name == 'ShellContext':
                                snapshot['lifecycle'].update(state='active', active=True, interactive=False, preview=True, generation=1)
                                snapshot.update(currentFamilyId='oggi', currentViewId='ORA')
                                snapshot['viewport'] = snapshot['safeArea'] = {'x': 0, 'y': 0, 'width': 960, 'height': 640}
                                snapshot['layout'] = deepcopy(layout)
                            elif type_name == 'NotificationContext':
                                snapshot.update(active=True, preview=True, ready=True, viewportWidth=960, viewportHeight=640, mode='large' if surface.endswith('large') else 'small')
                                snapshot['visualStyle'].update(style)
                                snapshot['visualStyle'].update(surfaceColor=style['surface'], titleColor=style['textPrimary'], bodyColor=style['textSecondary'], sourceColor=style['textSecondary'], guideColor=style['textSecondary'], noticeAccent=style['accent'], noticeRadius=style['radiusCard'])
                                event = default_snapshot('NotificationEvent')
                                title = 'Evento sintetico · Àèìòù ° − %'
                                body = 'Informazioni dimostrative. Nessun evento reale o dato personale.'
                                if case == 'longUnicode': title = ('Àèìòù Ω — evento ' * 9)[:100]; body = ('Informazioni sintetiche — àèìòù ' * 12)[:240]
                                if case == 'noSpaces': title = 'Å' * 100; body = '界' * 240
                                event.update(id='fixture.event', revision='1', rank=1, category='system', severity='info', title=title, body=body, sourceId='fixture', sourceLabel='Fixture offline', bannerSize=snapshot['mode'])
                                snapshot.update(eventData=event, event={'id': event['id'], 'title': title, 'detail': body}, sourceText='Fixture offline', validityText='Dati sintetici', guideText='3 AVVISI · 1 HOME')
                            context = factory.create(surface)
                            snapshot.pop('surfaceInstanceId', None)
                            if type_name == 'PageContext' and 'dataDomains' in renderer:
                                for domain in ('weather', 'account', 'nextEvent', 'sport', 'team', 'fantasy', 'racing'):
                                    if domain not in renderer['dataDomains']:
                                        snapshot[domain] = None
                            assert factory.update(context, snapshot), 'Contesto fixture rifiutato: ' + type_name
                            component = QQmlComponent(engine, QUrl.fromLocalFile(str(project / renderer['file'])))
                            item = component.createWithInitialProperties({'context': context})
                            if not isinstance(item, QQuickItem):
                                raise ValueError(renderer['file'] + ': ' + '\n'.join(error.toString() for error in component.errors()))
                            item.setParentItem(window.contentItem()); item.setParent(window)
                            if host_family == 'page' and 'layout' in valid['manifest']:
                                item.setClip(True)
                            width, height = (page_width, page_height) if host_family == 'page' else (960, 640) if host_family in ('shell', 'overlay') else (860, 340 if surface.endswith('large') else 92)
                            item.setSize(__import__('PySide6.QtCore', fromlist=['QSizeF']).QSizeF(width, height))
                            pump(120)
                            assert item.metaObject().indexOfProperty('ready') >= 0, renderer['file'] + ' API2 senza ready'
                            assert item.property('ready') is True, renderer['file'] + ' non ready: ' + repr(messages)
                            assert item.property('contentReady') is not False, renderer['file'] + ' contentReady=false'
                            assert item.width() > 0 and item.height() > 0 and item.isVisible()
                            if item.metaObject().indexOfMethod('settleMotion()') >= 0:
                                QMetaObject.invokeMethod(item, 'settleMotion')
                            if 'lifecycle' in snapshot:
                                snapshot['lifecycle'].update(state='suspended', active=False)
                            if 'active' in snapshot: snapshot['active'] = False
                            if 'motionPolicy' in snapshot: snapshot['motionPolicy']['suspended'] = True
                            assert factory.update(context, snapshot), 'Suspension fixture rejected'; pump(30)
                            animations = [child for child in item.findChildren(QObject) if 'Animation' in child.metaObject().className() or 'Timer' in child.metaObject().className()]
                            assert all(not child.property('running') for child in animations), 'Lavoro decorativo attivo dopo sospensione'
                            image = window.grabWindow()
                            screenshot = f"{surface}-{variant}-{mode}-{case}.png"
                            if image.isNull() or not image.save(str(output / screenshot)):
                                raise ValueError('Screenshot Qt non acquisito')
                            rows.append({'surface': surface, 'renderer': renderer['id'], 'variant': variant, 'motion': mode, 'case': case, 'status': 'passed', 'screenshot': screenshot, 'contextType': type_name, 'geometry': [width, height], 'contentRect': deepcopy(layout['content']) if host_family == 'page' else None, 'suspendedDecorationsStopped': True})
                            item.setParentItem(None); item.deleteLater(); factory.release(context); context.deleteLater(); pump(10)
                        style_object.deleteLater(); pump(5)
            # All declared auxiliary renderers are executable payload too.
            auxiliary = []
            from PySide6.QtQml import QQmlExpression, QQmlEngine
            for family in ('sceneRenderers', 'iconRenderers', 'recipes'):
                for identifier, descriptor in registry.get(family, {}).items():
                    for variant, mode in pairs:
                        appearance = catalog.resolve(valid['id'], variant=variant); appearance['motionMode'] = mode
                        style_object, style = _snapshot_style(engine, contract, appearance)
                        context = None
                        properties = {}
                        if family == 'sceneRenderers':
                            context = factory.create('scene.main')
                            snapshot = default_snapshot('SceneContext'); snapshot.pop('surfaceInstanceId', None)
                            snapshot['clock'].update(timeText='23:59', dateText='DOMENICA 4 OTTOBRE 2026', night=variant=='night')
                            snapshot.update(contentId='scene.main', style=style, suspended=False)
                            snapshot['lifecycle'].update(state='active', active=True, preview=True)
                            snapshot['motionPolicy'].update(mode=mode, suspended=False, urgent=False)
                            snapshot['actor'].update(actorId='fixture.actor', pose='idle', locomotion='idle', paused=mode != 'normal', motionMode=mode)
                            snapshot['viewport'] = {'x': 0, 'y': 0, 'width': 960, 'height': 640}
                            snapshot['safeArea'] = deepcopy(layout['sceneSafeRegions'][0]) if descriptor.get('sceneMode') == 'actor' and layout['sceneSafeRegions'] else deepcopy(snapshot['viewport'])
                            assert factory.update(context, snapshot)
                            properties = {'context': context}
                        elif family == 'iconRenderers':
                            properties = {'tint': style['accent'], 'opticalSize': 36}
                        component = QQmlComponent(engine, QUrl.fromLocalFile(str(project / descriptor['file'])))
                        item = component.createWithInitialProperties(properties)
                        assert item is not None, '\n'.join(error.toString() for error in component.errors())
                        if family in ('sceneRenderers', 'iconRenderers'):
                            assert isinstance(item, QQuickItem), descriptor['file'] + ' richiede un elemento visuale QQuickItem'
                        item.setParent(window)
                        if isinstance(item, QQuickItem):
                            item.setParentItem(window.contentItem())
                            if family == 'sceneRenderers':
                                footprint = descriptor.get('footprint', {'width': 30, 'height': 30})
                                size = (footprint['width'], footprint['height']) if descriptor.get('sceneMode') == 'actor' else (960, 640)
                            else:
                                size = (36, 36)
                            item.setWidth(size[0]); item.setHeight(size[1])
                        if family == 'recipes':
                            target = QQuickItem(window.contentItem()); target.setParent(window); target.setOpacity(1)
                            engine.rootContext().setContextProperty('_themePreviewTarget', target)
                            expression = QQmlExpression(QQmlEngine.contextForObject(item), item,
                                'play(_themePreviewTarget, {motionMode:"' + mode + '",duration:60,exit:false,opacityFrom:0.6},1,false)')
                            expression.evaluate(); assert not expression.hasError(), expression.error().toString()
                        pump(100)
                        if family == 'sceneRenderers':
                            assert item.metaObject().indexOfProperty('ready') >= 0, descriptor['file'] + ' API2 senza ready'
                            assert item.property('ready') is True, descriptor['file'] + ' non ready'
                            assert item.property('contentReady') is not False, descriptor['file'] + ' contentReady=false'
                        elif item.metaObject().indexOfProperty('ready') >= 0:
                            assert item.property('ready') is True
                        expression = QQmlExpression(QQmlEngine.contextForObject(item), item, 'settle()' if family == 'recipes' else 'settleMotion()')
                        expression.evaluate(); assert not expression.hasError(), expression.error().toString()
                        if context:
                            snapshot['lifecycle'].update(state='suspended', active=False)
                            snapshot['motionPolicy']['suspended'] = True; snapshot['suspended'] = True
                            assert factory.update(context, snapshot)
                        pump(30)
                        animations = [child for child in item.findChildren(QObject) if 'Animation' in child.metaObject().className() or 'Timer' in child.metaObject().className()]
                        assert all(not child.property('running') for child in animations), 'Decorazione ausiliaria non assestata'
                        if family == 'recipes':
                            assert item.property('running') is False and abs(target.opacity() - 1) < .001
                            target.deleteLater()
                        auxiliary.append({'family': family, 'renderer': identifier, 'variant': variant, 'motion': mode, 'status': 'passed', 'settleVerified': True, 'geometry': [item.width(), item.height()] if isinstance(item, QQuickItem) else None})
                        if isinstance(item, QQuickItem): item.setParentItem(None)
                        item.deleteLater()
                        if context:
                            factory.release(context); context.deleteLater()
                        style_object.deleteLater(); pump(10)
            for number in registered_fonts: QFontDatabase.removeApplicationFont(number)
            assert not network, 'Il renderer ha tentato accesso alla rete'
        warnings = [message for message in messages if not message.startswith('QStandardPaths:')]
        result = {'reportVersion': 1, 'operation': 'preview', 'status': 'failed' if warnings else 'passed', 'qt': qVersion(), 'backend': os.environ.get('QT_QPA_PLATFORM'), 'apiFingerprint': contract.fingerprint, 'renderers': rows, 'auxiliaryRenderers': auxiliary, 'resourceChecks': resource_checks, 'qtModules': valid['manifest']['qtModules'], 'qmlWarnings': warnings, 'isolation': {'privateXdg': True, 'privateStore': True, 'networkDenied': True, 'networkPositiveControl': True}, 'verification': {'publicApiBinding': 'passed', 'rendererLoadAndReadiness': 'passed', 'screenshots': 'passed', 'mainWorkflows': 'notVerified', 'boardRuntime': 'notVerified', 'performance': 'notVerified'}, 'scope': 'Real public contexts and QML renderers, synthetic isolated fixtures. This is not full dashboard navigation or board acceptance.'}
        (output / 'preview-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        qInstallMessageHandler(previous_handler)
        return result
    finally:
        if window: window.close()
        if engine: engine.deleteLater()
        if app: app.processEvents()
        private.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path); parser.add_argument('--output', type=Path, required=True); parser.add_argument('--matrix', action='store_true'); parser.add_argument('--visible', action='store_true')
    args = parser.parse_args()
    try:
        report = render_project(args.project, args.output, args.matrix, args.visible)
    except ImportError as error:
        report = {'reportVersion': 1, 'operation': 'preview', 'status': 'notVerified', 'issues': [{'code': 'preview.runtimeUnavailable', 'message': str(error)}]}
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr)
        report = {'reportVersion': 1, 'operation': 'preview', 'status': 'failed', 'issues': [{'code': 'preview.failed', 'message': str(error)}]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'passed' else 2 if report['status'] == 'notVerified' else 1


if __name__ == '__main__':
    raise SystemExit(main())
