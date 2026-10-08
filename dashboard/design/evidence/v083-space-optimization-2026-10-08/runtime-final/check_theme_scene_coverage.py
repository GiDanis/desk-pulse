"""Selected SceneContext capability and immutable bundle coverage must agree."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from theme_bundle import (_inventory, payload_digest, register_catalog,
                          validate_project)
from theme_core import ROOT, ThemeCatalog, ThemeError


class SceneCoverageTests(unittest.TestCase):
    def setUp(self):
        self.private = tempfile.TemporaryDirectory(prefix='smartpc-scene-coverage-')
        self.addCleanup(self.private.cleanup)
        self.project = Path(self.private.name) / 'project'
        shutil.copytree(ROOT / 'examples/bundles/studio-ambient', self.project)

    def document(self, filename, edit):
        path = self.project / filename
        value = json.loads(path.read_text())
        edit(value)
        path.write_text(json.dumps(value, indent=2) + '\n')

    def scene_fallback(self):
        def edit(value):
            value['coverage']['surfaces'].remove('scene.main')
            value['coverage']['fallbacks'].append('scene.main')
        self.document('bundle.json', edit)

    def catalog(self):
        validate_project(self.project)
        manifest = json.loads((self.project / 'bundle.json').read_text())
        registry = json.loads((self.project / 'visual-registry.json').read_text())
        inventory = _inventory(self.project)
        catalog = ThemeCatalog()
        register_catalog(catalog, {'id': manifest['id'], 'version': manifest['version'],
            'digest': payload_digest(inventory), 'payload': str(self.project),
            'manifest': manifest, 'registry': registry, 'files': inventory})
        return catalog

    def test_owned_selected_scene_can_start_disabled_and_enable(self):
        catalog = self.catalog()
        result = catalog.resolve('studio.ambient')
        self.assertFalse(result['scene']['enabled'])
        self.assertEqual(result['presentations']['scene.main'], 'studio.ambient.scene')
        self.assertEqual(result['sceneRegistry'][result['scene']['renderer']]['rendererKey'],
            result['presentationRegistry'][result['presentations']['scene.main']]['rendererKey'])
        enabled = catalog.resolve('studio.ambient', {'scene': {'enabled': True}})
        self.assertTrue(enabled['scene']['enabled'])

    def test_selected_external_cannot_claim_fallback_even_when_disabled(self):
        self.scene_fallback()
        with self.assertRaisesRegex(ThemeError, 'coverage.scene.main'):
            validate_project(self.project)
        self.document('theme.json', lambda value: value['scene'].update(enabled=True))
        with self.assertRaisesRegex(ThemeError, 'coverage.scene.main'):
            validate_project(self.project)

    def test_owned_scene_cannot_select_builtin(self):
        self.document('theme.json', lambda value: value['scene'].update(renderer='builtin.actor'))
        with self.assertRaisesRegex(ThemeError, 'coverage.scene.main'):
            validate_project(self.project)

    def test_auxiliary_renderer_can_exist_with_builtin_selected(self):
        self.scene_fallback()
        self.document('theme.json', lambda value: value['scene'].update(renderer='builtin.actor'))
        catalog = self.catalog()
        result = catalog.resolve('studio.ambient')
        self.assertEqual(result['scene']['renderer'], 'builtin.actor')
        self.assertIn('studio.ambient.scene', result['sceneRegistry'])
        self.assertNotEqual(result['presentations'].get('scene.main'), 'studio.ambient.scene')
        with self.assertRaisesRegex(ThemeError, 'coverage.scene.main'):
            catalog.resolve('studio.ambient', {'scene': {'renderer': 'studio.ambient.scene'}})

    def test_primary_scene_in_presentations_is_rejected(self):
        def edit(value):
            scene = deepcopy(value['sceneRenderers']['studio.ambient.scene'])
            scene.update(id='studio.ambient.primary-scene', contentIds=['scene.main'])
            value['presentations'].append(scene)
        self.document('visual-registry.json', edit)
        self.document('theme.json', lambda value: value['presentations'].update(
            {'scene.main': 'studio.ambient.primary-scene'}))
        with self.assertRaisesRegex(ThemeError, 'scene.main richiede sceneRenderers'):
            validate_project(self.project)

    def test_editor_override_cannot_replace_owned_scene_with_base(self):
        catalog = self.catalog()
        with self.assertRaisesRegex(ThemeError, 'coverage.scene.main'):
            catalog.resolve('studio.ambient', {'scene': {'renderer': 'builtin.actor'}})

    def test_scene_descriptor_must_belong_to_selected_immutable_revision(self):
        catalog = self.catalog()
        identity = catalog.scene_renderers['studio.ambient.scene']['rendererIdentity']
        identity['revision'] = 'studio.ambient@2.0.0#' + 'a' * 64
        with self.assertRaisesRegex(ThemeError, 'coverage.scene.main'):
            catalog.resolve('studio.ambient')


if __name__ == '__main__':
    unittest.main(verbosity=2)
