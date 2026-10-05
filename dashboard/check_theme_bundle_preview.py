#!/usr/bin/env python3
"""Real Qt public-renderer, auxiliary fault and actual bundle-style proofs."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from theme_bundle_tools import initialize, ROOT


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory(prefix='smartpc-bundle-qt-check-')
        self.base = Path(self.private.name)
        self.project = self.base / 'project'
        initialize(self.project)

    def tearDown(self):
        self.private.cleanup()

    def preview(self, suffix, *, matrix=False):
        output = self.base / suffix
        command = [sys.executable, str(ROOT / 'theme_bundle_preview.py'), str(self.project), '--output', str(output)]
        if matrix: command.append('--matrix')
        value = subprocess.run(command, capture_output=True, text=True, timeout=90)
        return value.returncode, json.loads(value.stdout), output

    def test_all_four_registry_families_and_motion_matrix(self):
        code, result, output = self.preview('matrix', matrix=True)
        self.assertEqual(code, 0, result)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(len(result['renderers']), 72)
        self.assertEqual(len(result['auxiliaryRenderers']), 18)
        self.assertEqual({row['family'] for row in result['auxiliaryRenderers']}, {'sceneRenderers', 'iconRenderers', 'recipes'})
        self.assertFalse(result['qmlWarnings'])
        self.assertEqual(result['verification']['boardRuntime'], 'notVerified')
        self.assertEqual(len(list(output.glob('*.png'))), 72)

    def test_bundle_palette_is_used_in_actual_pixels(self):
        path = self.project / 'theme.json'; theme = json.loads(path.read_text())
        theme['tokens']['colors.background'] = '#171717'; path.write_text(json.dumps(theme))
        code, result, output = self.preview('actual-style')
        self.assertEqual(code, 0, result)
        from PySide6.QtGui import QImage
        image = QImage(str(output / 'home.now-day-off-normal.png'))
        self.assertEqual(image.pixelColor(10, 10).name(), '#171717', 'Preview silently rendered Base instead of the bundle')

    def test_auxiliary_component_errors_fail_runtime_preflight(self):
        for name in ('Scene', 'Icon', 'Motion'):
            with self.subTest(renderer=name):
                path = self.project / 'qml' / (name + '.qml'); previous = path.read_text()
                path.write_text('import QtQuick\nItem { unknownMandatoryProperty: true }\n')
                try:
                    code, result, output = self.preview('broken-' + name)
                    self.assertEqual(code, 1, result)
                    self.assertEqual(result['status'], 'failed')
                    self.assertIn('unknownMandatoryProperty', json.dumps(result))
                finally:
                    path.write_text(previous)

    def test_bad_declared_font_is_not_hidden_by_unused_status(self):
        asset = self.project / 'assets'; asset.mkdir(); (asset / 'broken.ttf').write_bytes(b'not a font')
        path = self.project / 'bundle.json'; manifest = json.loads(path.read_text())
        manifest['resources'].append({'id': 'bad.font', 'path': 'assets/broken.ttf', 'type': 'font'}); path.write_text(json.dumps(manifest))
        code, result, output = self.preview('broken-font')
        self.assertEqual(code, 1, result)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Font non decodificabile', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
