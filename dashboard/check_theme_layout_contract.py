#!/usr/bin/env python3
"""Author shell layout validation, immutable revision and real Qt preview proofs."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from theme_bundle import (ROOT, BundleManager, ThemeError,
                          build_bundle, register_catalog, revision_key, validate_layout, validate_project)
from theme_core import ThemeCatalog

CUSTOM_LAYOUT = {
    'header': {'x': 0, 'y': 0, 'width': 960, 'height': 64},
    'content': {'x': 120, 'y': 64, 'width': 720, 'height': 520},
    'guide': {'x': 120, 'y': 590, 'width': 720, 'height': 40},
    'sceneSafeRegions': [{'x': 0, 'y': 64, 'width': 96, 'height': 520}],
}


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory(prefix='smartpc-layout-check-')
        self.base = Path(self.private.name)
        self.project = self.base / 'project'
        shutil.copytree(ROOT / 'examples/bundles/studio-ambient', self.project)
        self.manifest = json.loads((self.project / 'bundle.json').read_text())

    def tearDown(self):
        self.private.cleanup()

    def save(self):
        (self.project / 'bundle.json').write_text(json.dumps(self.manifest) + '\n')


class LayoutTests(ProjectTest):
    def test_optional_layout_keeps_existing_resolution_unchanged(self):
        valid = validate_project(self.project)
        catalog = ThemeCatalog()
        register_catalog(catalog, {**valid, 'payload': str(self.project)})
        self.assertNotIn('layout', catalog.resolve(valid['id']))

    def test_complete_custom_layout_and_full_canvas_are_valid(self):
        self.assertEqual(validate_layout(CUSTOM_LAYOUT), CUSTOM_LAYOUT)
        layout = deepcopy(CUSTOM_LAYOUT)
        layout.update(header={'x': 0, 'y': 0, 'width': 0, 'height': 0},
                      guide={'x': 0, 'y': 640, 'width': 0, 'height': 0},
                      content={'x': 0, 'y': 0, 'width': 960, 'height': 640},
                      sceneSafeRegions=[])
        validate_layout(layout)
        layout['content']['width'] = 959.5
        validate_layout(layout)

    def test_rejects_missing_and_unknown_layout_or_rectangle_fields(self):
        for mutation in (
            lambda v: v.pop('guide'), lambda v: v.update(z=5),
            lambda v: v['content'].pop('height'), lambda v: v['content'].update(clip=False),
            lambda v: v.update(sceneSafeRegions={}),
            lambda v: v.update(sceneSafeRegions=[deepcopy(v['header'])] * 65),
        ):
            layout = deepcopy(CUSTOM_LAYOUT); mutation(layout)
            with self.assertRaises(ThemeError): validate_layout(layout)

    def test_rejects_nonfinite_boolean_negative_and_empty_content(self):
        for value in (True, False, float('nan'), float('inf'), -1, '720', None, 10 ** 1000):
            with self.subTest(value=str(value)[:40]):
                layout = deepcopy(CUSTOM_LAYOUT); layout['content']['width'] = value
                with self.assertRaises(ThemeError): validate_layout(layout)
        for dimension in ('width', 'height'):
            layout = deepcopy(CUSTOM_LAYOUT); layout['content'][dimension] = 0
            with self.assertRaises(ThemeError): validate_layout(layout)

    def test_rejects_outside_viewport_for_every_region(self):
        for region in ('header', 'content', 'guide', 'sceneSafeRegions'):
            for dimension, value in (('x', 959), ('y', 639), ('width', 961), ('height', 641)):
                layout = deepcopy(CUSTOM_LAYOUT)
                rectangle = layout[region][0] if region == 'sceneSafeRegions' else layout[region]
                rectangle[dimension] = value
                with self.subTest(region=region, dimension=dimension):
                    with self.assertRaises(ThemeError): validate_layout(layout)

    def test_custom_layout_requires_author_owned_shell(self):
        self.manifest['layout'] = deepcopy(CUSTOM_LAYOUT)
        self.manifest['coverage']['surfaces'].remove('shell.main')
        self.manifest['coverage']['fallbacks'].append('shell.main'); self.save()
        with self.assertRaisesRegex(ThemeError, 'shell.main'): validate_project(self.project)

    def test_resolved_layout_is_isolated_and_revision_without_layout_clears_it(self):
        self.manifest['layout'] = deepcopy(CUSTOM_LAYOUT); self.save()
        valid = validate_project(self.project); catalog = ThemeCatalog()
        register_catalog(catalog, {**valid, 'payload': str(self.project)})
        identity = revision_key(valid)
        self.assertEqual(catalog.bundle_revision_metadata[identity]['layout'], CUSTOM_LAYOUT)
        valid['manifest']['layout']['content']['x'] = 1
        self.assertEqual(catalog.bundle_metadata[valid['id']]['layout'], CUSTOM_LAYOUT)
        resolved = catalog.resolve(valid['id']); resolved['layout']['content']['x'] = 0
        self.assertEqual(catalog.resolve(valid['id'])['layout'], CUSTOM_LAYOUT)
        self.manifest.pop('layout'); self.save(); valid = validate_project(self.project)
        register_catalog(catalog, {**valid, 'payload': str(self.project)})
        self.assertNotIn('layout', catalog.resolve(valid['id']))

    def test_pack_import_export_preserves_layout_and_payload_identity(self):
        self.manifest['layout'] = deepcopy(CUSTOM_LAYOUT); self.save()
        archive = self.base / 'theme.smartpc-theme'; built = build_bundle(self.project, archive)
        manager = BundleManager(self.base / 'store')
        revision = manager.import_bundle(archive)
        exported = self.base / 'export.smartpc-theme'; manager.export_bundle(revision, exported)
        self.assertEqual(archive.read_bytes(), exported.read_bytes())
        self.assertEqual(manager.verify_revision(revision)['manifest']['layout'], CUSTOM_LAYOUT)
        self.assertEqual(revision['digest'], built['digest'])


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'Real Qt preview requires PySide6')
class LayoutPreviewTests(ProjectTest):
    def preview(self, suffix):
        result = subprocess.run([sys.executable, str(ROOT / 'theme_bundle_preview.py'),
                                 str(self.project), '--output', str(self.base / suffix)],
                                capture_output=True, text=True, timeout=90)
        return result.returncode, json.loads(result.stdout)

    def test_custom_page_viewport_and_shell_rectangles_reach_real_contexts(self):
        self.manifest['layout'] = deepcopy(CUSTOM_LAYOUT)
        # Overlay surfaces retain the full display even with a custom page
        # content area. Their contexts and actual preview geometry must agree.
        self.manifest['coverage']['fallbacks'].remove('device.info')
        self.manifest['coverage']['surfaces'].append('device.info')
        self.manifest['resources'].append({'id': 'info', 'path': 'qml/Info.qml', 'type': 'qml'}); self.save()
        registry_path = self.project / 'visual-registry.json'
        registry = json.loads(registry_path.read_text())
        registry['presentations'].append({'id': 'studio.ambient.info', 'contentIds': ['device.info'],
            'file': 'qml/Info.qml', 'apiVersion': 2, 'contextApi': 'overlay1', 'name': 'Info'})
        registry_path.write_text(json.dumps(registry))
        theme_path = self.project / 'theme.json'; theme = json.loads(theme_path.read_text())
        theme['presentations']['device.info'] = 'studio.ambient.info'; theme_path.write_text(json.dumps(theme))
        (self.project / 'qml/Info.qml').write_text('import QtQuick\nimport SmartPC.ThemeApi 2.0\nItem {\n'
            'required property InfoContext context\nreadonly property bool ready: context.viewport.width === 960 && context.viewport.height === 640 && context.lifecycle.active\n'
            'function settleMotion() {}\n}\n')
        home = self.project / 'qml/Home.qml'
        home.write_text(home.read_text().replace('readonly property bool ready: ',
            'readonly property bool ready: context.viewport.width === 720 && context.viewport.height === 520 && '))
        shell = self.project / 'qml/Shell.qml'
        shell.write_text(shell.read_text().replace('readonly property bool ready: ',
            'readonly property bool ready: context.layout.content.x === 120 && context.layout.content.y === 64 && context.layout.sceneSafeRegions.length === 1 && '))
        code, report = self.preview('custom')
        self.assertEqual(code, 0, report); self.assertFalse(report['qmlWarnings'])
        pages = [row for row in report['renderers'] if row['contextType'] == 'PageContext']
        self.assertTrue(pages)
        self.assertTrue(all(row['geometry'] == [720, 520] and row['contentRect'] == CUSTOM_LAYOUT['content'] for row in pages))
        overlays = [row for row in report['renderers'] if row['contextType'] == 'InfoContext']
        self.assertTrue(overlays)
        self.assertTrue(all(row['geometry'] == [960, 640] for row in overlays))

    def test_presentations_without_ready_or_with_content_not_ready_are_rejected(self):
        for name in ('Home', 'Shell', 'Small'):
            path = self.project / 'qml' / (name + '.qml'); source = path.read_text()
            for defect in ('missing', 'content-false'):
                broken = source.replace('readonly property bool ready:', 'readonly property bool noReady:').replace('readonly property bool contentReady: ready', 'readonly property bool contentReady: noReady') if defect == 'missing' else source.replace('readonly property bool contentReady: ready', 'readonly property bool contentReady: false')
                path.write_text(broken)
                try:
                    code, report = self.preview(name + '-' + defect)
                    with self.subTest(name=name, defect=defect):
                        self.assertEqual(code, 1, report)
                        self.assertIn('senza ready' if defect == 'missing' else 'contentReady=false', json.dumps(report))
                finally:
                    path.write_text(source)

    def test_scene_without_ready_or_with_content_not_ready_is_rejected(self):
        path = self.project / 'qml/Scene.qml'; source = path.read_text()
        for defect in ('missing', 'content-false'):
            broken = source.replace('readonly property bool ready:', 'readonly property bool noReady:') if defect == 'missing' else source.replace('id: root', 'id: root\n    readonly property bool contentReady: false')
            path.write_text(broken)
            try:
                code, report = self.preview('scene-' + defect)
                with self.subTest(defect=defect):
                    self.assertEqual(code, 1, report)
                    self.assertIn('senza ready' if defect == 'missing' else 'contentReady=false', json.dumps(report))
            finally:
                path.write_text(source)

    def test_canvas_scene_preview_receives_full_viewport(self):
        path = self.project / 'visual-registry.json'; registry = json.loads(path.read_text())
        registry['sceneRenderers']['studio.ambient.scene']['sceneMode'] = 'canvas'
        path.write_text(json.dumps(registry))
        path = self.project / 'qml/Scene.qml'
        path.write_text(path.read_text().replace('readonly property bool ready: true',
            'readonly property bool ready: root.width === 960 && root.height === 640 && context.viewport.width === 960 && context.viewport.height === 640'))
        code, report = self.preview('canvas-scene')
        self.assertEqual(code, 0, report)
        scenes = [row for row in report['auxiliaryRenderers'] if row['family'] == 'sceneRenderers']
        self.assertTrue(scenes)
        self.assertTrue(all(row['geometry'] == [960, 640] for row in scenes))


if __name__ == '__main__':
    unittest.main()
