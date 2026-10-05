"""AI SDK boundary proofs: standalone use, diagnostics, packaging and coverage."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from theme_bundle import build_bundle, validate_project
from theme_bundle_tools import EXAMPLE, ROOT, initialize, inspect_archive, lint_project, write_full_kit


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory(prefix='smartpc-kit-tests-')
        self.base = Path(self.private.name)

    def tearDown(self):
        self.private.cleanup()

    def test_project_id_and_explicit_fallbacks(self):
        project = self.base / 'project'
        initialize(project, 'test.newtheme', 'Tema nuovo')
        report = validate_project(project)
        self.assertEqual(report['status'], 'valid')
        owned = set(report['manifest']['coverage']['surfaces'])
        fallback = set(report['manifest']['coverage']['fallbacks'])
        self.assertEqual(len(owned), 4)
        self.assertEqual(len(fallback), 40)
        self.assertFalse(owned & fallback)
        for row in report['registry']['presentations']:
            self.assertTrue(row['id'].startswith('test.newtheme.'))
        for path in (project / 'qml').glob('*.qml'):
            source = path.read_text()
            if path.name not in ('Icon.qml', 'Motion.qml'):
                self.assertIn('import SmartPC.ThemeApi 2.0', source)
            self.assertNotIn('controller', source)
            self.assertNotIn('import "..', source)

    def test_bad_id_and_existing_destination_preserved(self):
        path = self.base / 'project'
        with self.assertRaises(ValueError): initialize(path, '../escape')
        path.mkdir(); (path / 'keep.txt').write_text('keep')
        with self.assertRaises(ValueError): initialize(path)
        self.assertEqual((path / 'keep.txt').read_text(), 'keep')

    def test_offline_standalone_kit_validation_and_build(self):
        destination = self.base / 'kit'
        report = write_full_kit(destination)
        self.assertFalse(report['privateStateIncluded'])
        sdk = destination / 'sdk'
        self.assertTrue((sdk / 'smartpc-theme').is_file())
        self.assertTrue((sdk / 'theme-api/contexts.json').is_file())
        self.assertTrue((sdk / 'fixtures/theme-runtime/catalog.json').is_file())
        self.assertFalse((sdk / 'design').exists())
        self.assertFalse((sdk / '__pycache__').exists())
        cmd = [sys.executable, str(sdk / 'theme_bundle_tools.py')]
        project = self.base / 'standalone'
        for args in [('init', str(project), '--id', 'independent.newtheme'), ('validate', str(project)), ('pack', str(project), str(self.base / 'theme.smartpc-theme'))]:
            value = subprocess.run(cmd + list(args), cwd=self.base, capture_output=True, text=True, timeout=30)
            self.assertEqual(value.returncode, 0, value.stdout + value.stderr)
            self.assertNotIn('notVerified', json.loads(value.stdout).get('status', ''))
        manifest = json.loads((destination / 'kit-manifest.json').read_text())
        self.assertTrue(manifest['sdkSha256'])
        self.assertTrue((destination / 'PROMPT.md').is_file())

    def test_missing_linter_not_fake_pass(self):
        from unittest.mock import patch
        with patch('theme_bundle_tools.find_qmllint', return_value=None): result = lint_project(EXAMPLE)
        self.assertEqual(result['status'], 'notVerified')

    def test_import_requires_real_preflight_and_does_not_apply(self):
        data_root=self.base/'device-data'
        result=subprocess.run([sys.executable,str(ROOT/'theme_bundle_tools.py'),'import',str(EXAMPLE),'--store',str(data_root)],capture_output=True,text=True,timeout=100)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['status'],'imported')
        self.assertFalse(report['applied'])
        self.assertEqual(report['verification']['preflight'],'passed')
        self.assertFalse((data_root/'theme-activation.json').exists())

    def test_administration_respects_live_resource_leases(self):
        from theme_bundle import BundleManager
        from theme_lifecycle import LifecycleManager
        data_root=self.base/'administration';manager=BundleManager(data_root)
        revision=manager.import_bundle(EXAMPLE)
        identity=revision['id']+'@'+revision['version']+'#'+revision['digest']
        lifecycle=LifecycleManager(data_root);lease=lifecycle.acquire(revision,'cli-test')
        command=[sys.executable,str(ROOT/'theme_bundle_tools.py')]
        def run(arguments):
            result=subprocess.run(command+arguments+['--store',str(data_root)],capture_output=True,text=True,timeout=15)
            return result,json.loads(result.stdout)
        result,report=run(['list'])
        self.assertEqual(result.returncode,0)
        self.assertEqual(report['revisions'][0]['digest'],revision['digest'])
        result,report=run(['remove',identity])
        self.assertEqual(result.returncode,1)
        self.assertEqual(report['status'],'invalid')
        self.assertTrue(Path(revision['path']).exists())
        lifecycle.release(lease)
        result,report=run(['remove',identity])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(report['removed']['digest'],revision['digest'])
        self.assertFalse(Path(revision['path']).exists())
        result,report=run(['gc','--keep','2'])
        self.assertEqual(result.returncode,0)
        self.assertEqual(report['removed'],[])

    def test_deterministic_archive_and_source_preserved(self):
        before = {str(path.relative_to(EXAMPLE)): path.read_bytes() for path in EXAMPLE.rglob('*') if path.is_file()}
        first = self.base / 'first.smartpc-theme'; second = self.base / 'second.smartpc-theme'
        report1 = build_bundle(EXAMPLE, first); report2 = build_bundle(EXAMPLE, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(report1['digest'], report2['digest'])
        self.assertEqual(before, {str(path.relative_to(EXAMPLE)): path.read_bytes() for path in EXAMPLE.rglob('*') if path.is_file()})
        info = inspect_archive(first)
        self.assertEqual(info['integrity']['digest'], report1['digest'])
        self.assertEqual(info['verification']['runtime'], 'notVerified')

    def test_export_exact_installed_revision(self):
        from theme_bundle import BundleManager
        archive = self.base / 'original.smartpc-theme'; build_bundle(EXAMPLE, archive)
        manager = BundleManager(self.base / 'store')
        revision = manager.import_bundle(archive)
        exported = self.base / 'export.smartpc-theme'
        value = subprocess.run([sys.executable, str(ROOT / 'theme_bundle_tools.py'), 'export', revision['key'], str(exported), '--store', str(self.base / 'store')], capture_output=True, text=True, timeout=30)
        self.assertEqual(value.returncode, 0, value.stdout + value.stderr)
        self.assertEqual(archive.read_bytes(), exported.read_bytes())

    def test_diagnostics_json_for_missing_resource(self):
        project = self.base / 'bad'; initialize(project)
        (project / 'qml/Small.qml').unlink()
        value = subprocess.run([sys.executable, str(ROOT / 'theme_bundle_tools.py'), 'validate', str(project)], capture_output=True, text=True, timeout=20)
        self.assertEqual(value.returncode, 1)
        result = json.loads(value.stdout)
        self.assertEqual(result['status'], 'invalid')
        self.assertTrue(result['issues'])


if __name__ == '__main__':
    unittest.main()
