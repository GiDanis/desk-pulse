"""Public contract coherence, data/action boundaries and coverage regressions."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from theme_api_contract import ROOT, DOCUMENTS, ContractError, ThemeApiContract, api_metadata, read_document


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = ThemeApiContract()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='smartpc-api-contract-')
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def clone(self):
        for path in [*(ROOT / 'theme-api').glob('*.json'), *ROOT.rglob('*.qml'),
                     ROOT / 'themes/token-contract.json', ROOT / 'presentations/registry.json']:
            if 'design' in path.relative_to(ROOT).parts:
                continue
            target = self.root / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        return self.root

    def change(self, document, mutate):
        root = self.clone()
        path = root / 'theme-api' / document
        data = json.loads(path.read_text())
        mutate(data)
        path.write_text(json.dumps(data))
        return root

    def code(self, code, callback):
        with self.assertRaises(ContractError) as caught:
            callback()
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_coverage_and_not_runtime_availability(self):
        c = self.contract
        self.assertEqual(len(c.surfaces), 44)
        self.assertEqual(c.check_source_coverage()['routes'], 30)
        self.assertEqual(c.check_source_coverage()['registeredContents'], 14)
        self.assertFalse(c.metadata()['runtimeModuleVerified'])
        self.assertEqual(c.metadata()['availability'], 'contractOnly')

    def test_fingerprint_stable_across_root_and_json_formatting(self):
        root = self.clone()
        for name in DOCUMENTS:
            path = root / 'theme-api' / name
            path.write_text(json.dumps(json.loads(path.read_text()), sort_keys=True))
        self.assertEqual(self.contract.fingerprint, ThemeApiContract(root).fingerprint)

    def test_fingerprint_changes_with_public_contract(self):
        root = self.change('actions.json', lambda d: d['actions']['details.scroll']['arguments']['delta'].update(maximum=100))
        self.assertNotEqual(self.contract.fingerprint, ThemeApiContract(root).fingerprint)

    def test_minor_version_is_not_exact_fingerprint_compatibility(self):
        root = self.clone()
        for name in DOCUMENTS:
            path = root / 'theme-api' / name
            data = json.loads(path.read_text()); data['module']['minor'] = 1
            path.write_text(json.dumps(data))
        contract = ThemeApiContract(root)
        self.assertEqual(contract.metadata()['module']['minor'], 1)
        self.assertNotEqual(contract.fingerprint, self.contract.fingerprint)

    def test_descriptor_typo_rejected(self):
        root = self.change('contexts.json', lambda d: d['types']['NumericValue']['fields']['value'].update(minumum=0))
        self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_missing_variant_and_setting_section_rejected(self):
        for name, mutate in [('surfaces.json', lambda d: d['fixtureRequirements']['requiredCases'].pop()),
                             ('actions.json', lambda d: d['settingRows']['sections'].pop('settings.account'))]:
            root = self.change(name, mutate)
            self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_unknown_and_cyclic_type_rejected(self):
        for mutate in (lambda d: d['types']['NumericValue']['fields']['value'].update(type='InventedType'),
                       lambda d: d['types']['NumericValue'].update(extends='NumericValue')):
            root = self.change('contexts.json', mutate)
            self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_private_and_writable_properties_rejected(self):
        for mutate in (lambda d: d['contexts']['PageContext']['fields'].update(controller={'type': 'legacyMap', 'readOnly': True}),
                       lambda d: d['types']['ActorSnapshot']['fields']['pose'].update(readOnly=False)):
            root = self.change('contexts.json', mutate)
            self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_duplicate_surface_and_unknown_action_rejected(self):
        for mutate in (lambda d: d['surfaces'].append(deepcopy(d['surfaces'][0])),
                       lambda d: d['surfaces'][0]['actions'].append('imagined.action')):
            root = self.change('surfaces.json', mutate)
            self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_contract_version_and_model_identity(self):
        for name, mutate in [('actions.json', lambda d: d.update(contractVersion=True)),
                             ('contexts.json', lambda d: d['models']['MatchModel'].update(identityRole='notThere'))]:
            root = self.change(name, mutate)
            self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_notification_legacy_types_and_bool_return(self):
        fields = self.contract.fields('NotificationContext')
        self.assertEqual(fields['event']['type'], 'legacyMap')
        self.assertEqual(self.contract.contexts['NotificationContext']['signals'],
                         {'settleMotionRequested': {'parameters': []}})
        self.assertEqual(fields['items'], {'type': 'array', 'items': 'legacyMap', 'readOnly': True})
        self.assertEqual(self.contract.contexts['NotificationContext']['methods']['requestAction']['result'], 'bool')
        self.assertFalse(fields['itemModel']['required'])

    def test_unknown_signal_parameter_rejected(self):
        root = self.change('contexts.json', lambda d: d['contexts']['NotificationContext']['signals']
                           ['settleMotionRequested'].update(parameters=['InventedType']))
        self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_zero_false_and_null_remain_distinct(self):
        numeric = {'available': True, 'value': 0, 'unit': 'celsius', 'displayText': '0°', 'sourceRevision': ''}
        self.contract.validate_snapshot('NumericValue', numeric)
        self.contract.validate_snapshot('NumericValue', {**numeric, 'available': False, 'value': None})
        self.code('api.value.availability', lambda: self.contract.validate_snapshot('NumericValue', {**numeric, 'value': None}))
        self.code('api.value.type', lambda: self.contract.validate_snapshot('NumericValue', {**numeric, 'value': False}))
        self.contract.validate_snapshot('ScalarValue', {'available': True, 'value': False, 'unit': '', 'displayText': 'Disattivo'})

    def test_nonfinite_and_huge_numbers_rejected(self):
        for value in (float('nan'), float('inf'), 10 ** 1000):
            self.code('api.value.type', lambda: self.contract.validate_snapshot('NumericValue',
                       {'available': True, 'value': value, 'unit': '', 'displayText': '', 'sourceRevision': ''}))

    def test_extra_and_missing_fields_rejected(self):
        self.code('api.value.unknown', lambda: self.contract.validate_snapshot('Point', {'x': 0, 'y': 0, 'controller': {}}))
        self.code('api.value.required', lambda: self.contract.validate_snapshot('Point', {'x': 0}))

    def test_model_duplicates_and_empty_ids_rejected(self):
        row = {'id': 'summary', 'label': 'Riepilogo', 'enabled': True}
        self.contract.validate_snapshot('TabModel', [row])
        for rows in ([row, row], [{**row, 'id': ''}]):
            self.code('api.value.identity', lambda: self.contract.validate_snapshot('TabModel', rows))

    def test_invalid_date_not_just_regular_expression(self):
        row = {k: None for k in self.contract.fields('WeatherForecast')}
        row['date'] = '2026-02-31'
        # Validate a date field through the same descriptor used by snapshots.
        self.code('api.value.date', lambda: self.contract._value(self.contract.fields('WeatherForecast')['date'], row['date'], 'date'))

    def test_action_allowlists_and_bounded_arguments(self):
        self.assertFalse(self.contract.validate_request('home.now', 'navigation.family.step', arguments={'direction': 1})['runtimeDispatchVerified'])
        for direction in (0, 2, True, '1'):
            with self.assertRaises(ContractError):
                self.contract.validate_request('home.now', 'navigation.family.step', arguments={'direction': direction})
        self.code('api.request.action', lambda: self.contract.validate_request('alerts.urgent', 'appearance.apply'))
        self.code('api.request.action', lambda: self.contract.validate_request('scene.main', 'home'))
        self.code('api.value.range', lambda: self.contract.validate_request('alerts.urgent', 'dismiss'))
        self.code('api.value.unknown', lambda: self.contract.validate_request('settings.sources', 'sources.refresh', 'meteo', {'url': 'https://arbitrary'}))

    def test_request_metadata_does_not_add_actions(self):
        self.contract.validate_request('alerts.urgent', 'home', arguments={'requestId': 'user-17'})
        self.code('api.value.type', lambda: self.contract.validate_request('alerts.urgent', 'home', arguments={'requestId': False}))
        self.code('api.request.surface', lambda: self.contract.validate_request('unknown', 'home'))

    def test_new_route_in_single_quoted_call_detected(self):
        root = self.clone()
        with (root / 'Main.qml').open('a') as f:
            f.write("\nfunction newRoute() { pushOverlay('newDetail') }\n")
        self.code('api.coverage.routes', lambda: ThemeApiContract(root).check_source_coverage())

    def test_literal_route_assignment_detected(self):
        root = self.clone()
        with (root / 'Main.qml').open('a') as f:
            f.write("\nfunction newRoute() { overlay = 'newDetail' }\n")
        self.code('api.coverage.routes', lambda: ThemeApiContract(root).check_source_coverage())

    def test_comments_strings_do_not_create_routes(self):
        root = self.clone()
        with (root / 'Main.qml').open('a') as f:
            f.write("\n// pushOverlay('fake')\n/* overlay === 'fake' */\nproperty string explanation: \"pushOverlay('fake')\"\n")
        self.assertEqual(ThemeApiContract(root).check_source_coverage()['routes'], 30)

    def test_unknown_dynamic_route_requires_inventory(self):
        root = self.clone()
        with (root / 'Main.qml').open('a') as f:
            f.write('\nfunction newDynamic(id) { pushOverlay(id) }\n')
        self.code('api.coverage.dynamic', lambda: ThemeApiContract(root).check_source_coverage())

    def test_new_registry_content_detected(self):
        root = self.clone()
        path = root / 'presentations/registry.json'
        data = json.loads(path.read_text()); data['presentations'][0]['contentIds'].append('new.page')
        path.write_text(json.dumps(data))
        self.code('api.coverage.registry', lambda: ThemeApiContract(root).check_source_coverage())

    def test_new_qml_content_detected(self):
        root = self.clone()
        (root / 'AdditionalHost.qml').write_text('import QtQuick\nItem { property string contentId: "new.page" }')
        self.code('api.coverage.contents', lambda: ThemeApiContract(root).check_source_coverage())

    def test_semantic_text_cannot_use_focus_threshold(self):
        root = self.change('semantic-roles.json', lambda d: d['usages'][0].update(minimum=3))
        self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_semantic_unknown_background_and_light_claim_rejected(self):
        for mutate in (lambda d: d['usages'][0].update(backgroundToken='colors.imagined'),
                       lambda d: d['policy'].update(lightPaletteSupported=True)):
            root = self.change('semantic-roles.json', mutate)
            self.code('api.contract.invalid', lambda: ThemeApiContract(root))

    def test_bad_json_duplicate_keys_and_nonfinite(self):
        path = self.root / 'document.json'
        for body in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            path.write_text(body)
            self.code('api.json.invalid', lambda: read_document(path))

    def test_old_root_does_not_inherit_pc_fingerprint(self):
        self.assertEqual(api_metadata(self.root)['availability'], 'unavailable')
        self.assertIsNone(api_metadata(self.root)['apiFingerprint'])
        root = self.clone(); (root / 'theme-api/contexts.json').unlink()
        with self.assertRaises(FileNotFoundError):
            api_metadata(root)

    def test_generated_schema_matches_python_for_nullable_zero(self):
        schema = self.contract.json_schema()
        # JSON Schema is optional on the board; the canonical checker is stdlib.
        if importlib.util.find_spec('jsonschema') is None:
            self.skipTest('independent JSON Schema validator unavailable')
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(schema)
        selected = {**schema, '$ref': '#/$defs/NumericValue'}
        validator = Draft202012Validator(selected)
        row = {'available': True, 'value': 0, 'unit': '', 'displayText': '', 'sourceRevision': ''}
        validator.validate(row)
        self.assertTrue(list(validator.iter_errors({**row, 'value': None})))
        validator.validate({**row, 'available': False, 'value': None})

    def test_generator_stale_artifact_detected(self):
        script = ROOT / 'theme_api_tools.py'
        output = self.root / 'generated'
        command = [sys.executable, str(script), '--output', str(output)]
        for args in (command, [*command, '--check']):
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (output / 'reference.md').write_text('stale')
        result = subprocess.run([*command, '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['issues'][0]['code'], 'api.generated.stale')


if __name__ == '__main__':
    unittest.main()
