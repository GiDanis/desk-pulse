#!/usr/bin/env python3
"""Portable declared opaque visual payloads without native executables or decoders."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from theme_bundle import (ROOT, MAX_FILE_BYTES, MAX_MANIFEST_BYTES, BundleManager, ThemeError, _extract_archive, build_bundle,
                          validate_project)


class OpaqueAssetTests(unittest.TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory(prefix='smartpc-opaque-check-')
        self.base = Path(self.private.name); self.project = self.base / 'project'
        shutil.copytree(ROOT / 'examples/bundles/studio-ambient', self.project)
        (self.project / 'assets').mkdir()
        self.manifest = json.loads((self.project / 'bundle.json').read_text())

    def tearDown(self):
        self.private.cleanup()

    def save(self):
        (self.project / 'bundle.json').write_text(json.dumps(self.manifest) + '\n')

    def asset(self, name, contents=b'visual fixture\x00\x01', *, declared=True, kind='data'):
        path = self.project / 'assets' / name; path.write_bytes(contents)
        if declared:
            self.manifest['resources'].append({'id': 'visual.' + str(len(self.manifest['resources'])),
                                               'path': 'assets/' + name, 'type': kind})
        self.save(); return path

    def raw_archive(self, archive):
        with zipfile.ZipFile(archive, 'w') as target:
            for path in self.project.rglob('*'):
                if path.is_file(): target.write(path, path.relative_to(self.project).as_posix())
            target.writestr('integrity.json', '{}')
        return archive

    def test_declared_shader_atlas_rig_binary_and_custom_format_roundtrip(self):
        names = ['filter.qsb', 'motion.atlas', 'companion.rig', 'poses.bin', 'model.customvisual', 'plainasset']
        assets = []
        for index, name in enumerate(names):
            path = self.asset(name, bytes([index, 0, 255]) + b'opaque visual fixture')
            assets.append({'id': 'visual.asset' + str(index), 'type': 'data', 'path': 'assets/' + name,
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        theme_path = self.project / 'theme.json'; theme = json.loads(theme_path.read_text())
        theme['assets'] = assets; theme_path.write_text(json.dumps(theme))
        checked = validate_project(self.project)
        for asset in assets:
            self.assertEqual(checked['files'][asset['path']]['sha256'], asset['sha256'])
        archive = self.base / 'visual.smartpc-theme'; build_bundle(self.project, archive)
        manager = BundleManager(self.base / 'store'); revision = manager.import_bundle(archive)
        self.assertEqual(revision['preflight']['status'], 'unverified', 'Opaque bytes cannot prove a decoder exists')
        exported = self.base / 'export.smartpc-theme'; manager.export_bundle(revision, exported)
        self.assertEqual(archive.read_bytes(), exported.read_bytes())
        verified = manager.verify_revision(revision)
        for asset in assets:
            self.assertEqual((Path(verified['payload']) / asset['path']).read_bytes(), (self.project / asset['path']).read_bytes())

    def test_unknown_extensions_require_explicit_data_declaration(self):
        self.asset('undeclared.qsb', declared=False)
        with self.assertRaisesRegex(ThemeError, 'dichiarazione data'): validate_project(self.project)
        archive = self.raw_archive(self.base / 'undeclared.zip')
        destination = self.base / 'extraction'; destination.mkdir()
        with self.assertRaisesRegex(ThemeError, 'dichiarazione data'): _extract_archive(archive, destination)
        self.assertFalse(any(destination.iterdir()), 'Undeclared payload must fail before extraction')

    def test_native_code_script_and_installer_suffixes_cannot_masquerade_as_data(self):
        for name in ('library.so', 'library.so.1', 'tool.EXE', 'plugin.dll', 'driver.dylib', 'script.py',
                     'script.sh', 'start.bat', 'start.cmd', 'shortcut.desktop', 'install.deb', 'shader.py.bin'):
            with self.subTest(name=name):
                path = self.asset(name)
                try:
                    with self.assertRaisesRegex(ThemeError, 'nativo/script/installatore'): validate_project(self.project)
                    archive = self.raw_archive(self.base / 'native.zip')
                    destination = self.base / 'native-extraction'; destination.mkdir(exist_ok=True)
                    with self.assertRaisesRegex(ThemeError, 'nativo/script/installatore'): _extract_archive(archive, destination)
                finally:
                    path.unlink(); self.manifest['resources'].pop(); self.save()

    def test_renamed_executables_are_rejected_by_header(self):
        for header in (b'\x7fELF', b'MZ', b'#!/bin/sh\n', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe'):
            with self.subTest(header=header):
                path = self.asset('renamed.bin', header + b'fixture')
                try:
                    with self.assertRaisesRegex(ThemeError, 'eseguibile rinominato'): validate_project(self.project)
                    archive = self.raw_archive(self.base / 'renamed.zip')
                    destination = self.base / ('renamed-' + header.hex()); destination.mkdir()
                    with self.assertRaisesRegex(ThemeError, 'eseguibile rinominato'): _extract_archive(archive, destination)
                finally:
                    path.unlink(); self.manifest['resources'].pop(); self.save()

    def test_data_type_cannot_bypass_qml_font_or_image_validation(self):
        for name in ('component.qml', 'code.js', 'font.ttf', 'picture.png'):
            with self.subTest(name=name):
                path = self.asset(name)
                try:
                    with self.assertRaises(ThemeError): validate_project(self.project)
                finally:
                    path.unlink(); self.manifest['resources'].pop(); self.save()
        for kind in ('qml', 'js', 'font', 'image'):
            with self.subTest(kind=kind):
                path = self.asset('wrongkind.qsb', kind=kind)
                try:
                    with self.assertRaises(ThemeError): validate_project(self.project)
                finally:
                    path.unlink(); self.manifest['resources'].pop(); self.save()

    def test_manifest_bound_link_and_duplicate_keys_are_rejected_before_inventory(self):
        path = self.project / 'bundle.json'; original = path.read_bytes()
        try:
            path.write_bytes(b' ' * (MAX_MANIFEST_BYTES + 1))
            with self.assertRaisesRegex(ThemeError, 'manifest troppo grande'): validate_project(self.project)
            archive = self.raw_archive(self.base / 'oversized.zip'); destination = self.base / 'big-extraction'; destination.mkdir()
            with self.assertRaisesRegex(ThemeError, 'manifest troppo grande'): _extract_archive(archive, destination)
            path.write_bytes(b'{"resources": [], "resources": []}')
            with self.assertRaisesRegex(ThemeError, 'JSON non valido'): validate_project(self.project)
            path.unlink(); elsewhere = self.base / 'manifest.json'; elsewhere.write_bytes(original); path.symlink_to(elsewhere)
            with self.assertRaisesRegex(ThemeError, 'senza link'): validate_project(self.project)
            path.unlink(); path.write_bytes(original); os.link(path, self.base / 'hardlinked.json')
            with self.assertRaisesRegex(ThemeError, 'senza link'): validate_project(self.project)
        finally:
            if path.exists() or path.is_symlink(): path.unlink()
            path.write_bytes(original)

    def test_opaque_size_payload_path_and_file_links_keep_existing_limits(self):
        path = self.asset('too-big.bin'); path.write_bytes(b'x' * (MAX_FILE_BYTES + 1))
        with self.assertRaisesRegex(ThemeError, 'file troppo grande'): validate_project(self.project)
        path.unlink(); self.manifest['resources'].pop(); self.save()
        for index in range(3): self.asset('large-' + str(index) + '.bin', b'x' * MAX_FILE_BYTES)
        with self.assertRaisesRegex(ThemeError, 'budget complessivo'): validate_project(self.project)
        for path in (self.project / 'assets').iterdir(): path.unlink()
        self.manifest['resources'] = self.manifest['resources'][:-3]
        self.manifest['resources'].append({'id': 'escape', 'path': '../escape.bin', 'type': 'data'}); self.save()
        with self.assertRaisesRegex(ThemeError, 'traversal'): validate_project(self.project)
        self.manifest['resources'].pop(); self.save()
        path = self.asset('link.bin'); path.unlink(); external = self.base / 'external.bin'; external.write_bytes(b'fixture'); path.symlink_to(external)
        with self.assertRaisesRegex(ThemeError, 'link/file speciale'): validate_project(self.project)


if __name__ == '__main__':
    unittest.main()
