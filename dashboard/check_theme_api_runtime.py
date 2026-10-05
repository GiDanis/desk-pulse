"""Public API runtime, isolated external QML import, models and broker checks."""
from copy import deepcopy
import os
from pathlib import Path
from unittest.mock import patch
import subprocess
import shutil
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')

from PySide6.QtCore import QObject, QUrl, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
import PySide6

from theme_api import (IMPORT_ROOT, PublicContextFactory, bootstrap_theme_api,
                       normalize_legacy, normalize_dto, runtime_typeinfo, weather_snapshot)
from theme_contexts import CONTRACT, PUBLIC_TYPES, default_snapshot, complete_snapshot


class PublicApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def setUp(self):
        self.factory = PublicContextFactory()
        self.errors = []
        self.factory.diagnostic.connect(lambda *args: self.errors.append(args))

    def test_every_surface_has_real_readonly_context(self):
        for surface_id, surface in CONTRACT.surfaces.items():
            with self.subTest(surface=surface_id):
                context = self.factory.create(surface_id)
                self.assertIsInstance(context, PUBLIC_TYPES[surface['context']])
                for name in CONTRACT.fields(surface['context']):
                    prop = context.metaObject().property(context.metaObject().indexOfProperty(name))
                    self.assertTrue(prop.isValid(), name)
                    self.assertFalse(prop.isWritable(), name)
                self.assertNotIn('controller', context._snapshot())
                self.assertNotIn('model', context._snapshot())
                self.assertEqual(context.contentId, surface_id)
                self.assertTrue(self.factory.updateLegacy(context, {'active': True, 'interactive': True,
                    'clockText': '12:34', 'dateText': '5 ottobre', 'epoch': 1791196440.0,
                    'viewportWidth': 960, 'viewportHeight': 640, 'motionMode': 'off'}), self.errors)
        self.assertEqual(self.errors, [])

    def test_primitive_properties_native_nested_objects_owned(self):
        context = self.factory.create('home.now')
        style = context.style
        for name, native in [('surface', 'QColor'), ('font24', 'int'), ('textScale', 'double'), ('uiFamily', 'QString')]:
            prop = style.metaObject().property(style.metaObject().indexOfProperty(name))
            self.assertEqual(prop.typeName(), native)
        self.assertEqual(context.metaObject().property(context.metaObject().indexOfProperty('style')).typeName(), 'QObject*')
        self.assertIs(style.parent(), context)
        self.assertIs(context.clock.parent(), context)

    def test_no_change_no_signals_and_identity_preserved(self):
        context = self.factory.create('home.now')
        clock = context.clock
        notices = []
        context.clock.timeTextChanged.connect(lambda: notices.append('time'))
        self.assertTrue(self.factory.update(context, {'clock': {'timeText': '08:00'}}))
        self.assertTrue(self.factory.update(context, {'clock': {'timeText': '08:00'}}))
        self.assertIs(context.clock, clock)
        self.assertEqual(notices, ['time'])

    def test_bad_snapshot_retains_previous_complete_data(self):
        context = self.factory.create('home.now')
        before = context._snapshot()
        self.assertFalse(self.factory.update(context, {'clock': {'epoch': float('nan')}}))
        self.assertEqual(context._snapshot(), before)
        self.assertFalse(self.factory.update(context, {'controller': {}}))
        self.assertFalse(self.factory.update(context, {'contentId': 'home.day'}))

    def test_numeric_zero_missing_and_false_preserved(self):
        weather = weather_snapshot({'status': 'active', 'data': {'temperature': '0°',
            'numeric': {'temperature': 0, 'humidity': None}}})
        self.assertEqual(weather['temperature']['value'], 0)
        self.assertTrue(weather['temperature']['available'])
        self.assertIsNone(weather['humidity']['value'])
        self.assertFalse(weather['humidity']['available'])
        legacy = weather_snapshot({'status': 'offline', 'data': {'temperature': '18°'}})
        self.assertFalse(legacy['temperature']['available'])
        self.assertEqual(legacy['temperature']['displayText'], '18°')
        self.assertEqual(legacy['source']['status'], 'offline')
        self.assertTrue(legacy['source']['isStale'])

    def test_match_score_zero_and_absence_do_not_coalesce(self):
        match = normalize_dto('MatchData', {'canonicalMatchId': 'match.1', 'homeScore': 0,
            'awayScore': None, 'pendingVAR': False, 'homeTeamId': 'a', 'homeTeam': 'A'})
        self.assertEqual(match['id'], 'match.1')
        self.assertEqual(match['homeScore']['value'], 0)
        self.assertFalse(match['awayScore']['available'])
        self.assertIsNone(match['awayScore']['value'])
        self.assertFalse(match['pendingVAR'])
        self.assertEqual(match['home']['id'], 'a')

    def test_model_moves_keep_row_and_model_objects(self):
        context = self.factory.create('overlay.menu')
        rows = [complete_snapshot('MenuRow', {'id': key, 'title': key, 'enabled': True}) for key in ('a', 'b', 'c')]
        self.assertTrue(self.factory.update(context, {'rows': rows}))
        model = context.rows
        a, b, c = [model.get(i) for i in range(3)]
        resets, moves, changes = [], [], []
        model.modelReset.connect(lambda: resets.append(True))
        model.rowsMoved.connect(lambda *args: moves.append(args))
        model.dataChanged.connect(lambda *args: changes.append(args))
        reordered = deepcopy([rows[2], rows[0], rows[1]])
        reordered[1]['title'] = 'A changed'
        self.assertTrue(self.factory.update(context, {'rows': reordered}))
        self.assertIs(context.rows, model)
        self.assertIs(model.get(0), c)
        self.assertIs(model.get(1), a)
        self.assertIs(model.get(2), b)
        self.assertEqual(a.title, 'A changed')
        self.assertEqual(model.indexOf('a'), 1)
        self.assertTrue(moves)
        self.assertTrue(changes)
        self.assertFalse(resets)
        self.assertIsNone(model.get(-1))

    def test_duplicate_row_rejected_before_mutation(self):
        context = self.factory.create('overlay.menu')
        row = complete_snapshot('MenuRow', {'id': 'a', 'title': 'A'})
        self.assertTrue(self.factory.update(context, {'rows': [row]}))
        self.assertFalse(self.factory.update(context, {'rows': [row, row]}))
        self.assertEqual(context.rows.count, 1)

    def active(self, surface='home.now'):
        context = self.factory.create(surface)
        self.assertTrue(self.factory.updateLegacy(context, {'active': True, 'interactive': True}))
        return context

    def test_action_lifecycle_generation_and_allowlist(self):
        calls = []
        self.factory._dispatch = lambda *args: calls.append(args) or True
        context = self.factory.create('home.now')
        self.assertFalse(context.requestAction('navigation.home', '', {}).accepted)
        self.factory.updateLegacy(context, {'active': True, 'interactive': True})
        self.assertFalse(context.requestAction('settings.activate', 'appearance.theme', {}).accepted)
        self.assertFalse(context.requestAction('navigation.view.step', '', {'direction': 0}).accepted)
        self.assertFalse(context.requestAction('navigation.home', '', {'unexpected': 1}).accepted)
        result = context.requestAction('navigation.home', '', {})
        self.assertTrue(result.accepted)
        self.assertEqual(result.status, 'completed')
        self.assertEqual(len(calls), 1)
        self.factory.release(context)
        self.assertFalse(context.requestAction('navigation.home', '', {}).accepted)
        self.assertEqual(len(calls), 1)

    def test_preview_suspended_and_backend_unavailable_deny_effects(self):
        calls = []
        self.factory._dispatch = lambda *args: calls.append(args) or True
        context = self.active()
        self.factory.updateLegacy(context, {'active': True, 'interactive': True, 'preview': True})
        self.assertFalse(context.requestAction('navigation.home', '', {}).accepted)
        self.factory.update(context, {'lifecycle': {'state': 'suspended', 'active': True, 'interactive': True}})
        self.assertFalse(context.requestAction('navigation.home', '', {}).accepted)
        self.factory.updateLegacy(context, {'active': True, 'interactive': True})
        self.factory._availability = lambda *_args: 'priority.urgent'
        self.assertEqual(context.requestAction('navigation.home', '', {}).errorCode, 'priority.urgent')
        self.assertFalse(calls)

    def test_no_router_does_not_falsely_accept(self):
        context = self.active()
        result = context.requestAction('navigation.home', '', {})
        self.assertFalse(result.accepted)
        self.assertEqual(result.errorCode, 'api.action.noRouter')

    def test_signal_dispatch_reports_synchronous_success_or_failure(self):
        context = self.active()
        self.factory.actionRequested.connect(lambda ctx, _a, _t, _p, request_id:
            self.factory.completeAction(ctx, request_id, False, 'provider.offline'))
        result = context.requestAction('navigation.home', '', {})
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.errorCode, 'provider.offline')

    def test_async_completion_updates_result_and_releases_pending_capacity(self):
        context = self.active()
        self.factory.actionRequested.connect(lambda *_args: None)
        result = context.requestAction('navigation.home', '', {'requestId': 'async.1'})
        self.assertTrue(result.accepted)
        self.assertEqual(result.status, 'pending')
        changes = []
        result.statusChanged.connect(lambda: changes.append(result.status))
        self.assertTrue(self.factory.completeAction(context, 'async.1', True, ''))
        self.assertEqual(result.status, 'completed')
        self.assertEqual(changes, ['completed'])
        self.assertNotIn('async.1', self.factory._pending)
        self.assertFalse(self.factory.completeAction(context, 'async.1', True, ''))

    def test_duplicate_request_id_does_not_dispatch_twice(self):
        calls = []
        self.factory._dispatch = lambda *_args: calls.append(True) or True
        context = self.active()
        first = context.requestAction('navigation.home', '', {'requestId': 'same.1'})
        second = context.requestAction('navigation.home', '', {'requestId': 'same.1'})
        self.assertTrue(first.accepted)
        self.assertTrue(second.accepted)
        self.assertEqual(calls, [True])
        different = context.requestAction('navigation.back', '', {'requestId': 'same.1'})
        self.assertFalse(different.accepted)
        self.assertEqual(different.errorCode, 'api.action.duplicate')

    def test_release_revokes_pending_result_and_stale_completion(self):
        context = self.active()
        self.factory.actionRequested.connect(lambda *_args: None)
        result = context.requestAction('navigation.home', '', {'requestId': 'stale.1'})
        self.factory.release(context)
        self.assertEqual(result.status, 'rejected')
        self.assertEqual(result.errorCode, 'api.action.generation')
        self.assertFalse(self.factory.completeAction(context, 'stale.1', True, ''))
        self.assertFalse(self.factory._pending)

    def test_clock_change_reuses_domain_normalization_until_provider_data_changes(self):
        context = self.factory.create('home.now')
        payload = {'clockText': '12:00', 'model': {'weather': {'status': 'active',
            'data': {'temperature': '0°', 'numeric': {'temperature': 0}}}}}
        import theme_api
        with patch.object(theme_api, 'weather_snapshot', wraps=theme_api.weather_snapshot) as normalizer:
            self.assertTrue(self.factory.updateLegacy(context, payload))
            self.assertEqual(normalizer.call_count, 1)
            payload['clockText'] = '12:01'
            self.assertTrue(self.factory.updateLegacy(context, payload))
            self.assertEqual(normalizer.call_count, 1)
            payload['model']['weather']['data']['numeric']['temperature'] = 1
            self.assertTrue(self.factory.updateLegacy(context, payload))
            self.assertEqual(normalizer.call_count, 2)
            self.assertEqual(context.weather.temperature.value, 1)

    def test_runtime_schema_and_default_cache_are_immutable_or_independent(self):
        fields = CONTRACT.fields('ThemeStyle')
        self.assertIs(fields, CONTRACT.fields('ThemeStyle'))
        with self.assertRaises(TypeError):
            fields['surface']['type'] = 'string'
        first = default_snapshot('PageContext')
        first['style']['surface'] = '#123456'
        self.assertEqual(default_snapshot('PageContext')['style']['surface'], '#000000')

    def test_completion_validates_one_full_tree_and_rejects_duplicate_rows(self):
        row = normalize_dto('MatchData', {'canonicalMatchId': 'match.same', 'homeScore': 0})
        with patch.object(CONTRACT, 'validate_snapshot', wraps=CONTRACT.validate_snapshot) as validator:
            result = complete_snapshot('SportData', {'matches': [row]})
            self.assertEqual(validator.call_count, 1)
            self.assertEqual(result['matches'][0]['homeScore']['value'], 0)
        with self.assertRaises(ValueError):
            complete_snapshot('SportData', {'matches': [row, row]})

    def test_all_model_counts_are_native_readonly_properties(self):
        for name in CONTRACT.models:
            model = PUBLIC_TYPES[name]()
            prop = model.metaObject().property(model.metaObject().indexOfProperty('count'))
            self.assertEqual(prop.typeName(), 'int', name)
            self.assertFalse(prop.isWritable(), name)
            with self.assertRaises(AttributeError):
                model.count = 3

    def test_nested_equality_preserves_types_and_mapping_order(self):
        from theme_contexts import snapshot_equal
        self.assertTrue(snapshot_equal({'a': [0, False, {'n': None}], 'b': 1.0},
                                       {'b': 1.0, 'a': [0, False, {'n': None}]}))
        self.assertFalse(snapshot_equal({'a': [False]}, {'a': [0]}))
        self.assertFalse(snapshot_equal({'a': [1]}, {'a': [1.0]}))
        self.assertFalse(snapshot_equal({'a': (1,)}, {'a': [1]}))
        self.assertFalse(snapshot_equal({'a': [None]}, {'a': []}))

    def test_cached_snapshot_never_treats_false_as_numeric_zero(self):
        context = self.factory.create('home.now')
        before = context._snapshot()
        self.assertFalse(self.factory.update(context, {'interactive': 0}))
        self.assertFalse(self.factory.update(context, {'clock': {'epoch': False}}))
        self.assertEqual(context._snapshot(), before)
        payload = {'model': {'weather': {'status': 'active',
            'data': {'numeric': {'temperature': 0}}}}}
        self.assertTrue(self.factory.updateLegacy(context, payload))
        self.assertTrue(context.weather.temperature.available)
        payload['model']['weather']['data']['numeric']['temperature'] = False
        self.assertTrue(self.factory.updateLegacy(context, payload))
        self.assertFalse(context.weather.temperature.available)
        self.assertIsNone(context.weather.temperature.value)

    def test_warm_clock_update_does_not_recomplete_validated_provider_tree(self):
        context = self.factory.create('home.now')
        payload = {'clockText': '12:00', 'model': {'weather': {'status': 'active',
            'data': {'numeric': {'temperature': 0}, 'forecast': []}}}}
        self.assertTrue(self.factory.updateLegacy(context, payload))
        weather = context.weather
        import theme_api
        with patch.object(theme_api, 'complete_field', wraps=theme_api.complete_field) as completer:
            payload['clockText'] = '12:01'
            self.assertTrue(self.factory.updateLegacy(context, payload))
            self.assertEqual([call.args[2] for call in completer.call_args_list], ['PageContext/clock'])
        self.assertIs(context.weather, weather)
        self.assertEqual(context.weather.temperature.value, 0)

    def test_changed_fields_validate_atomically_before_publishing_signals(self):
        context = self.factory.create('home.now')
        before = context._snapshot()
        signals = []
        context.clock.timeTextChanged.connect(lambda: signals.append('clock'))
        self.assertFalse(self.factory.update(context, {'clock': {'timeText': '12:01'}, 'interactive': 0}))
        self.assertEqual(context._snapshot(), before)
        self.assertEqual(signals, [])

    def test_qt_geometry_and_actor_snapshot_are_normalized_readonly(self):
        from PySide6.QtCore import QPointF, QRectF, Property
        class Actor(QObject):
            actorId = Property(str, lambda self: 'companion', constant=True)
            anchor = Property(QPointF, lambda self: QPointF(10, 20), constant=True)
        actor = Actor()
        context = self.factory.create('scene.main')
        self.assertTrue(self.factory.updateLegacy(context, {'actorState': actor,
            'occupiedRegions': [QRectF(2, 3, 20, 30)], 'active': True}))
        self.assertEqual(context.actor.actorId, 'companion')
        self.assertEqual(context.actor.anchor.x, 10)
        self.assertEqual(context.occupiedRegions[0]['height'], 30)
        self.assertIsNot(context.actor, actor)

    def test_completed_action_results_do_not_accumulate_surface_children(self):
        context = self.active()
        self.factory._dispatch = lambda *_args: True
        count = len(context.children())
        for _ in range(300):
            result = context.requestAction('navigation.home', '', {})
            self.assertTrue(result.accepted)
            self.assertIsNone(result.parent())
        self.assertEqual(len(context.children()), count)
        self.assertLessEqual(len(self.factory._history), 256)

    def test_legacy_notification_maps_retained_with_typed_sidecars(self):
        context = self.active('alerts.banner.small')
        event = {'id': 'event.1', 'revision': 'r1', 'rank': 0, 'title': 'Test',
                 'source': 'Synthetic', 'detail': 'Body from the live legacy event schema',
                 'notificationRank': 3, 'seen': False, 'expires_at': 1791196440.0}
        self.assertTrue(self.factory.updateLegacy(context, {'event': event, 'items': [event], 'mode': 'small',
            'active': True, 'interactive': True, 'actions': ['openInbox']}), self.errors)
        self.assertEqual(context.event, event)
        self.assertEqual(context.items, [event])
        self.assertEqual(context.eventData.id, 'event.1')
        self.assertEqual(context.eventData.body, event['detail'])
        self.assertEqual(context.eventData.sourceId, 'Synthetic')
        self.assertEqual(context.eventData.expiresAt, 1791196440.0)
        self.assertEqual(context.itemModel.get(0).id, 'event.1')
        self.assertIsNone(context.sourceMetadata)

    def test_external_qml_import_binding_and_readonly_failure(self):
        engine = QQmlEngine()
        bootstrap_theme_api(engine)
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(str(e) for e in errors))
        context = self.active()
        self.factory.update(context, {'clock': {'timeText': '12:34'}, 'style': {'surface': '#123456'}})
        with tempfile.TemporaryDirectory(prefix='smartpc-api-external-') as directory:
            source = Path(directory) / 'Independent.qml'
            source.write_text('''import QtQuick
import SmartPC.ThemeApi 2.0
Item {
    required property PageContext context
    readonly property string clockText: context.clock.timeText
    readonly property color surface: context.style.surface
    readonly property string motionMode: context.motionPolicy.mode
    function tryMutation() { try { context.style.surface = "red"; return true } catch(error) { return false } }
    function goHome() { return context.requestAction("navigation.home", "", {}).accepted }
}''')
            component = QQmlComponent(engine, QUrl.fromLocalFile(str(source)))
            self.assertEqual(component.errors(), [])
            root = component.createWithInitialProperties({'context': context})
            self.assertIsNotNone(root, component.errors())
            self.assertEqual(root.property('clockText'), '12:34')
            self.assertEqual(root.property('surface').name(), '#123456')
            expression = QQmlExpression(engine.rootContext(), root, 'tryMutation()')
            result = expression.evaluate()
            self.assertFalse(expression.hasError(), expression.error())
            self.assertEqual(result[0] if isinstance(result, tuple) else result, False)
            root.deleteLater()
        self.assertEqual(warnings, [])

    def test_private_adapter_does_not_read_payload_until_public_renderer_enabled(self):
        class Probe(QObject):
            def __init__(self):
                super().__init__()
                self.calls = []

            @Slot(str)
            def requested(self, surface):
                self.calls.append(surface)

        probe = Probe()
        engine = QQmlEngine()
        bootstrap_theme_api(engine)
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(str(error) for error in errors))
        component = QQmlComponent(engine)
        source = '''import QtQuick
import "components"
Item {
    id: root
    required property var factory
    required property var probe
    property bool adapterEnabled: false
    property string clockText: "12:00"
    QtObject {
        id: app
        property date now: new Date()
        property string familyId: "oggi"
        property string overlay: ""
        property var urgentEvent: ({})
        function publicSurfacePayload(surface) {
            root.probe.requested(surface)
            return {clockText:root.clockText}
        }
    }
    QtObject {
        id: privateContext
        property bool active: true
        property bool interactive: true
        property var style: null
        property int viewportWidth: 960
        property int viewportHeight: 640
        property var controller: app
        property string clockText: root.clockText
    }
    PublicContextAdapter {
        objectName: "adapterProbe"
        factory: root.factory
        legacy: privateContext
        surfaceId: "home.now"
        publicEnabled: root.adapterEnabled
    }
}'''
        component.setData(source.encode(), QUrl.fromLocalFile(str(IMPORT_ROOT.parent / 'PublicAdapterLaziness.qml')))
        self.assertEqual(component.errors(), [])
        root = component.createWithInitialProperties({'factory': self.factory, 'probe': probe})
        self.assertIsNotNone(root, component.errors())
        adapter = root.findChild(QObject, 'adapterProbe')
        root.setProperty('clockText', '12:01')
        self.app.processEvents()
        self.assertEqual(probe.calls, [])
        self.assertIsNone(adapter.property('publicContext'))
        root.setProperty('adapterEnabled', True)
        self.app.processEvents()
        context = adapter.property('publicContext')
        context = context.toVariant() if hasattr(context, 'toVariant') else context
        self.assertIsInstance(context, PUBLIC_TYPES['PageContext'])
        self.assertTrue(adapter.property('valid'), self.errors)
        self.assertEqual(context.clock.timeText, '12:01')
        self.assertTrue(probe.calls)
        root.setProperty('adapterEnabled', False)
        self.app.processEvents()
        calls = list(probe.calls)
        root.setProperty('clockText', '12:02')
        self.app.processEvents()
        self.assertEqual(probe.calls, calls)
        self.assertEqual(warnings, [])
        root.deleteLater()

    def test_runtime_typeinfo_matches_generated_native_metadata(self):
        typeinfo = IMPORT_ROOT / 'SmartPC/ThemeApi/runtime.qmltypes'
        self.assertEqual(typeinfo.read_text(), runtime_typeinfo())

    def test_lint_typo_rejected_with_real_qmllint(self):
        bundled = Path(PySide6.__file__).parent / 'qmllint'
        executable = str(bundled) if bundled.is_file() else shutil.which('qmllint') or shutil.which('pyside6-qmllint')
        if not executable and os.environ.get('SMARTPC_TEST_OPTIONAL_LINT') == '1':
            self.skipTest('notVerified: real qmllint unavailable on this target; native metadata/runtime gates remain required')
        self.assertTrue(executable, 'qmllint is required for this runtime gate')
        with tempfile.TemporaryDirectory(prefix='smartpc-api-lint-') as directory:
            source = Path(directory) / 'Independent.qml'
            valid = 'import QtQuick\nimport SmartPC.ThemeApi 2.0\nItem {required property PageContext context; readonly property color surface: context.style.surface; readonly property string timeText: context.clock.timeText; readonly property string motionMode: context.motionPolicy.mode}\n'
            for body, expected in [(valid, 0), (valid.replace('style.surface', 'style.surfaec'), 1)]:
                source.write_text(body)
                result = subprocess.run([str(executable), '--ignore-settings', '--unresolved-type', 'error', '-W', '0', '-I', str(IMPORT_ROOT), str(source)], text=True, capture_output=True)
                if expected == 0:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('surfaec', result.stderr)


if __name__ == '__main__':
    unittest.main()
