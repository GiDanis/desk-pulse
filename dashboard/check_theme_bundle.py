"""Adversarial pure tests for portable bundle identity and revision recovery."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

from theme_bundle import (ROOT, BundleManager, ThemeError, atomic_json, build_bundle,
                          canonical_bytes, revision_key, validate_project)
from theme_lifecycle import BASE, LifecycleManager, selection_key
from theme_resources import ResourceRef, ResourceResolver


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='smartpc-bundle-test-')
        self.root = Path(self.temporary.name)
        self.project = self.root / 'project'
        shutil.copytree(ROOT / 'examples/bundles/studio-ambient', self.project)
        self.manager = BundleManager(self.root / 'data')

    def tearDown(self):
        self.temporary.cleanup()

    def document(self, filename, mutation):
        path = self.project / filename
        value = json.loads(path.read_text())
        mutation(value)
        path.write_text(json.dumps(value, indent=2) + '\n')

    def installed(self, version=None):
        if version:
            self.document('bundle.json', lambda value: value.update(version=version))
            self.document('theme.json', lambda value: value.update(version=version))
        return self.manager.import_bundle(self.project, preflight=lambda *args: {'status': 'passed', 'testOnly': True})

    def test_reproducible_build_exact_payload_and_export(self):
        first, second = self.root / 'first.zip', self.root / 'second.zip'
        a = build_bundle(self.project, first)
        b = build_bundle(self.project, second)
        self.assertEqual(a['digest'], b['digest'])
        self.assertEqual(first.read_bytes(), second.read_bytes())
        revision = self.manager.import_bundle(first)
        exported = self.root / 'export.zip'
        self.manager.export_bundle(revision, exported)
        self.assertEqual(first.read_bytes(), exported.read_bytes())
        self.assertEqual(revision['preflight']['status'], 'unverified')

    def test_idempotence_and_same_version_conflict(self):
        first = self.installed()
        same = self.installed()
        self.assertTrue(same['idempotent'])
        self.assertEqual(first['key'], same['key'])
        path = self.project / 'qml/Home.qml'
        path.write_text(path.read_text() + '\n// changed revision\n')
        with self.assertRaises(ThemeError):
            self.installed()
        self.assertEqual(len(self.manager.list_revisions()), 1)

    def test_side_by_side_update_and_downgrade_identity(self):
        first = self.installed()
        second = self.installed('2.0.0')
        self.assertNotEqual(first['key'], second['key'])
        self.assertTrue(Path(first['payload']).is_dir())
        self.assertEqual(self.manager.verify_revision(first)['version'], '1.0.0')

    def test_modified_revision_rejected_before_use(self):
        revision = self.installed()
        path = Path(revision['payload']) / 'qml/Home.qml'
        path.write_text('import QtQuick\nItem {}\n')
        with self.assertRaises(ThemeError):
            self.manager.verify_revision(revision)
        self.assertEqual(self.manager.list_revisions(), [])

    def test_resources_revision_aware_and_tamper_guard(self):
        revision = self.installed()
        resolver = self.manager.resources
        relative = 'qml/Home.qml'
        reference = ResourceRef('bundle', revision['id'] + '.home', revision['key'], relative,
                                revision['files'][relative]['sha256'], 'page2')
        result = resolver.resolve(reference)
        self.assertTrue(result['url'].startswith('file:'))
        self.assertEqual(result['identity']['revision'], revision['key'])
        for path in ('../Home.qml', '/etc/passwd', 'qml/../Home.qml', 'qml\\Home.qml', 'https://bad/asset'):
            with self.assertRaises(ThemeError):
                resolver.resolve(ResourceRef('bundle', 'home', revision['key'], path))
        (Path(revision['payload']) / relative).write_text('broken')
        with self.assertRaises(ThemeError):
            resolver.resolve(reference)

    def test_runtime_preflight_not_invented(self):
        with self.assertRaises(ThemeError):
            self.manager.import_bundle(self.project, require_preflight=True)
        self.assertEqual(self.manager.list_revisions(), [])
        with self.assertRaises(ThemeError):
            self.manager.import_bundle(self.project, preflight=lambda *args: {'status': 'failed'})
        self.assertEqual(self.manager.list_revisions(), [])

    def test_all_surface_coverage_explicit(self):
        self.document('bundle.json', lambda value: value['coverage']['fallbacks'].pop())
        with self.assertRaises(ThemeError):
            validate_project(self.project)

    def test_no_builtin_namespace_override(self):
        self.document('visual-registry.json', lambda value: value['presentations'][0].update(id='builtin.home.left'))
        with self.assertRaises(ThemeError):
            validate_project(self.project)

    def test_no_legacy_controller_renderer(self):
        self.document('visual-registry.json', lambda value: value['presentations'][0].update(apiVersion=1))
        with self.assertRaises(ThemeError):
            validate_project(self.project)

    def test_manifest_unknown_version_api_and_noncanonical_semver(self):
        for field, value in [('engineApi', 3), ('surprise', True), ('version', '01.0.0')]:
            with self.subTest(field=field):
                original = (self.project / 'bundle.json').read_text()
                self.document('bundle.json', lambda document: document.update({field: value}))
                with self.assertRaises(ThemeError):
                    validate_project(self.project)
                (self.project / 'bundle.json').write_text(original)

    def test_symlink_hardlink_and_native_plugin_rejected(self):
        target = self.project / 'qml/Home.qml'
        link = self.project / 'qml/Bad.qml'
        link.symlink_to(target)
        with self.assertRaises(ThemeError):
            validate_project(self.project)
        link.unlink()
        os.link(target, link)
        with self.assertRaises(ThemeError):
            validate_project(self.project)
        link.unlink()
        (self.project / 'plugin.so').write_bytes(b'native')
        with self.assertRaises(ThemeError):
            validate_project(self.project)

    def test_archive_traversal_duplicate_symlink_and_hash_guards(self):
        valid = self.root / 'valid.zip'
        build_bundle(self.project, valid)
        with zipfile.ZipFile(valid) as archive:
            files = {entry.filename: archive.read(entry) for entry in archive.infolist()}
        for attack in ('traversal', 'duplicate', 'symlink', 'tampered', 'native'):
            with self.subTest(attack=attack):
                archive_path = self.root / (attack + '.zip')
                with zipfile.ZipFile(archive_path, 'w') as archive:
                    for filename, data in files.items():
                        archive.writestr(filename, b'tampered' if attack == 'tampered' and filename == 'qml/Home.qml' else data)
                    if attack == 'traversal':
                        archive.writestr('../escaped.txt', 'bad')
                    elif attack == 'duplicate':
                        archive.writestr('QML/home.qml', 'duplicate')
                    elif attack == 'symlink':
                        info = zipfile.ZipInfo('qml/linked.qml')
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(info, '../outside')
                    elif attack == 'native':
                        archive.writestr('plugin.so', 'bad')
                with self.assertRaises(ThemeError):
                    self.manager.import_bundle(archive_path)
                self.assertFalse((self.root / 'data/escaped.txt').exists())
                self.assertEqual(self.manager.list_revisions(), [])
                self.assertEqual(list((self.root / 'data/theme-staging').iterdir()), [])

    def test_visual_contract_lint(self):
        path = self.project / 'qml/Home.qml'
        path.write_text(path.read_text() + '\nWindow {}\n')
        with self.assertRaises(ThemeError):
            validate_project(self.project)

    def test_undeclared_asset_rejected(self):
        (self.project / 'assets').mkdir(exist_ok=True)
        (self.project / 'assets/secret.json').write_text('{}')
        with self.assertRaises(ThemeError):
            validate_project(self.project)

    def test_image_allocation_guard(self):
        import struct
        (self.project / 'assets').mkdir(exist_ok=True)
        (self.project / 'assets/giant.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'\0' * 8 + struct.pack('>II', 8192, 8192))
        self.document('bundle.json', lambda value: value['resources'].append({'id': 'giant', 'path': 'assets/giant.png', 'type': 'image'}))
        with self.assertRaises(ThemeError):
            validate_project(self.project)

    def test_catalog_identity_changes_across_same_renderer_id(self):
        from theme_core import ThemeCatalog
        first = self.installed()
        first_catalog = ThemeCatalog()
        self.manager.register_catalog(first_catalog, first)
        descriptor_a = first_catalog.presentations['studio.ambient.home']
        second = self.installed('2.0.0')
        second_catalog = ThemeCatalog()
        self.manager.register_catalog(second_catalog, second)
        descriptor_b = second_catalog.presentations['studio.ambient.home']
        self.assertNotEqual(descriptor_a['rendererKey'], descriptor_b['rendererKey'])
        self.assertNotEqual(descriptor_a['sourceUrl'], descriptor_b['sourceUrl'])
        self.assertEqual(first_catalog.resolve(first['id'])['themeVersion'], '1.0.0')

    def test_extended_roles_are_generated_and_reproducible(self):
        self.document('bundle.json', lambda value: value.update(extendedTokens={
            'studio.ambient.glow': {'type': 'color', 'default': '#12abef', 'alias': 'glowColor'},
            'studio.ambient.orbit': {'type': 'real', 'default': 0.25, 'minimum': 0, 'maximum': 1, 'alias': 'orbitFraction'}}))
        first, second = self.root / 'extended-first.zip', self.root / 'extended-second.zip'
        report = build_bundle(self.project, first)
        build_bundle(self.project, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(report['generated'], ['qml/ThemeRoles.qml', 'qml/ThemeRoles.qmltypes'])
        revision = self.manager.import_bundle(first)
        self.assertIn('qml/ThemeRoles.qml', revision['files'])
        source = (Path(revision['payload']) / 'qml/ThemeRoles.qml').read_text()
        self.assertIn('readonly property color glowColor', source)
        self.assertIn('base.tokenSnapshot["studio.ambient.glow"]', source)
        self.assertFalse((self.project / 'qml/ThemeRoles.qml').exists())
        exported = self.root / 'extended-export.zip'
        self.manager.export_bundle(revision, exported)
        self.assertEqual(exported.read_bytes(), first.read_bytes())

    def test_corrupt_visual_journal_recovers_base_without_provider_reset(self):
        lifecycle = LifecycleManager(self.root / 'data')
        lifecycle.path.write_text('{broken')
        private = self.root / 'data/events.sqlite'
        private.write_bytes(b'preserved')
        result = lifecycle.recover()
        self.assertTrue(result['recovered'])
        self.assertEqual(lifecycle.read()['active'], BASE)
        self.assertTrue(list((self.root / 'data/theme-quarantine').glob('journal-*.json')))
        self.assertEqual(private.read_bytes(), b'preserved')

    def test_supervisor_recovers_heartbeat_after_readiness_then_block(self):
        revision = self.installed()
        lifecycle = LifecycleManager(self.manager.root)
        ticket = lifecycle.begin(revision)['ticket']
        lifecycle.mark_ready(ticket)
        lifecycle.commit(ticket, {'key': revision['key'], 'coherent': True, 'presented': True})
        script = "import sys,time;sys.path.insert(0," + repr(str(ROOT)) + ");from theme_lifecycle import LifecycleManager;LifecycleManager(" + repr(str(self.manager.root)) + ");[ (LifecycleManager(" + repr(str(self.manager.root)) + ").heartbeat(ready=True),time.sleep(0.05)) for _ in range(12) ];time.sleep(10)"
        result = subprocess.run([sys.executable, str(ROOT / 'theme_supervisor.py'), '--data-root', str(self.manager.root),
                                 '--startup-timeout', '2', '--heartbeat-timeout', '0.2', '--', sys.executable, '-c', script],
                                capture_output=True, text=True, timeout=6)
        self.assertEqual(result.returncode, 75, result.stderr)
        self.assertIn('heartbeat', result.stderr)

    def test_heartbeat_is_private_ephemeral_ipc_and_preserves_journal(self):
        lifecycle=LifecycleManager(self.manager.root)
        ticket=lifecycle.begin(BASE)['ticket']
        before=lifecycle.path.read_bytes()
        record=lifecycle.heartbeat(ready=False)
        self.assertFalse(lifecycle.health_path.is_relative_to(self.manager.root))
        self.assertEqual(lifecycle.path.read_bytes(),before)
        self.assertFalse((self.manager.root/'theme-gui-health.json').exists())
        self.assertEqual(lifecycle.health_path.parent.stat().st_mode & 0o077,0)
        self.assertEqual(json.loads(lifecycle.health_path.read_text())['pid'],os.getpid())
        self.assertFalse(record['ready'])
        self.assertEqual(lifecycle.read()['pending']['ticket'],ticket)
        self.assertEqual(lifecycle.read()['active'], BASE)

    def test_activation_requires_ready_and_revision_frame(self):
        revision = self.installed()
        lifecycle = LifecycleManager(self.root / 'data')
        transaction = lifecycle.begin(revision, {'tokens': {'typography.textScale': 1.1}})
        ticket = transaction['ticket']
        ack = {'coherent': True, 'presented': True, 'key': revision['key']}
        with self.assertRaises(ThemeError):
            lifecycle.commit(ticket, ack)
        lifecycle.mark_ready(ticket)
        with self.assertRaises(ThemeError):
            lifecycle.commit(ticket, {**ack, 'key': 'another'})
        state = lifecycle.commit(ticket, ack)
        self.assertEqual(state['active']['digest'], revision['digest'])
        self.assertEqual(state['adaptations']['perRevision'][revision['key']]['tokens']['typography.textScale'], 1.1)

    def test_unverified_import_cannot_activate(self):
        revision = self.manager.import_bundle(self.project)
        lifecycle = LifecycleManager(self.root / 'data')
        with self.assertRaises(ThemeError):
            lifecycle.begin(revision)

    def test_interrupted_journal_recovery_quarantine_preserves_other_files(self):
        revision = self.installed()
        lifecycle = LifecycleManager(self.root / 'data')
        other = self.root / 'data/events.sqlite'
        other.write_bytes(b'private event data')
        preference = self.root / 'data/provider.json'
        preference.write_text('{"secret":"preserved"}')
        lifecycle.begin(revision)
        recovered = LifecycleManager(self.root / 'data').recover('power cut simulation')
        self.assertTrue(recovered['recovered'])
        self.assertEqual(recovered['selection'], BASE)
        self.assertEqual(self.manager.list_revisions(), [])
        self.assertEqual(other.read_bytes(), b'private event data')
        self.assertEqual(preference.read_text(), '{"secret":"preserved"}')
        with self.assertRaises(ThemeError):
            lifecycle.begin(revision)

    def test_lease_and_previous_block_remove_until_released(self):
        revision = self.installed()
        lifecycle = LifecycleManager(self.root / 'data')
        token = lifecycle.acquire(revision, 'font')
        with self.assertRaises(ThemeError):
            lifecycle.remove(revision)
        lifecycle.release(token)
        lifecycle.remove(revision)
        self.assertEqual(self.manager.list_revisions(), [])
        with self.assertRaises(ThemeError):
            lifecycle.remove(BASE)

    def test_gc_protects_active_previous_and_candidate(self):
        first, second, third = self.installed(), self.installed('2.0.0'), self.installed('3.0.0')
        lifecycle = LifecycleManager(self.root / 'data')
        for revision in (first, second):
            ticket = lifecycle.begin(revision)['ticket']
            lifecycle.mark_ready(ticket)
            lifecycle.commit(ticket, {'key': revision['key'], 'coherent': True, 'presented': True})
        lifecycle.begin(third)
        self.assertEqual(lifecycle.gc(keep_per_theme=1)['removed'], [])
        self.assertEqual(len(self.manager.list_revisions()), 3)

    def test_supervisor_recovers_crash_and_gui_block(self):
        for attack in ('crash', 'block'):
            with self.subTest(attack=attack):
                self.manager = BundleManager(self.root / ('supervisor-' + attack))
                revision = self.installed()
                lifecycle = LifecycleManager(self.manager.root)
                ticket = lifecycle.begin(revision)['ticket']
                lifecycle.mark_ready(ticket)
                lifecycle.commit(ticket, {'key': revision['key'], 'coherent': True, 'presented': True})
                script = 'import sys;sys.exit(3)' if attack == 'crash' else 'import time;time.sleep(10)'
                result = subprocess.run([sys.executable, str(ROOT / 'theme_supervisor.py'), '--data-root', str(self.manager.root),
                                         '--startup-timeout', '0.2', '--heartbeat-timeout', '0.2', '--', sys.executable, '-c', script],
                                        capture_output=True, text=True, timeout=6)
                self.assertEqual(result.returncode, 75, result.stderr)
                self.assertEqual(lifecycle.read()['active'], BASE)
                self.assertTrue((self.manager.root / 'theme-quarantine' / (revision['digest'] + '.json')).exists())


if __name__ == '__main__':
    unittest.main()
