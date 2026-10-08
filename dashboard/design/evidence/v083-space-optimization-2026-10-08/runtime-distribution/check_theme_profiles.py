"""T16: real resolver, journal and private QSettings; explicitly simulated host acks.

This checks state/persistence, not renderer readiness or physical frames. Bundle
preflight is marked testOnly, because the renderer path is covered separately.
"""
from copy import deepcopy
import json
import shutil
import unittest
from unittest.mock import patch

from theme_fixture_support import isolate_process
PRIVATE, BASE = isolate_process()
from PySide6.QtCore import QSettings, QThreadPool
from PySide6.QtGui import QGuiApplication
from theme_core import ROOT, ThemeError
from theme_service import ThemeService, SaveJob, SaveResult
from theme_test_support import wait_save

APP = QGuiApplication([])
APP.setOrganizationName('SmartPC'); APP.setApplicationName('Dashboard')


class ProfilesTests(unittest.TestCase):
    def setUp(self):
        QSettings('SmartPC', 'Dashboard').clear()
        self.store = BASE / self.id().split('.')[-1] / 'themes'
        self.service = ThemeService(store=self.store)
        self.settings = QSettings('SmartPC', 'Dashboard')
        self.settings.setValue('functional/sentinel', 'retained')
        self.settings.sync()

    def tearDown(self):
        self.service.cancel()
        QThreadPool.globalInstance().waitForDone(5000)

    def settle(self):
        snapshot = self.service.candidateAppearance
        if snapshot:
            for content in snapshot['requiredContents']:
                self.service.reportCandidate(snapshot['generation'], content, True, '')
        self.service.acknowledgeThemeFrame(self.service.revision, True)

    def save(self):
        self.settle()
        self.assertTrue(self.service.apply(), self.service.lastError)
        wait_save(APP, self.service)
        self.assertEqual(self.service.status, 'ready', self.service.lastError)

    def choose(self, identifier):
        self.assertTrue(self.service.selectDraft(identifier), self.service.lastError)
        self.settle()

    def radius(self):
        return self.service.resolvedAppearance['tokens']['shape.radiusCard']

    def test_schema1_A_B_return_cancel_and_process_reconstruction(self):
        s = self.service
        s.beginEdit(); self.assertTrue(s.setToken('shape.radiusCard', 7)); self.save()
        s.beginEdit(); self.choose('functional')
        self.assertEqual(self.radius(), s.catalog.resolve('functional')['tokens']['shape.radiusCard'])
        self.assertTrue(s.setToken('shape.radiusCard', 9)); self.save()
        s.beginEdit(); self.choose('base'); self.assertEqual(self.radius(), 7)
        self.assertTrue(s.setToken('shape.radiusCard', 3)); s.cancel()
        self.assertEqual(s.activeThemeId, 'functional'); self.assertEqual(self.radius(), 9)
        s.beginEdit(); self.choose('base'); self.assertEqual(self.radius(), 7); self.save()
        reconstructed = ThemeService(store=self.store)
        self.assertEqual(reconstructed.resolvedAppearance['tokens']['shape.radiusCard'], 7)
        reconstructed.beginEdit(); self.assertTrue(reconstructed.selectDraft('functional'))
        self.assertEqual(reconstructed.resolvedAppearance['tokens']['shape.radiusCard'], 9)
        reconstructed.cancel()
        self.assertEqual(self.settings.value('functional/sentinel'), 'retained')

    def test_bundle_revision_A_B_updated_return_has_separate_profiles(self):
        s = self.service
        project = self.store.parent / 'project'
        shutil.copytree(ROOT / 'examples/bundles/studio-ambient', project)
        first = s.bundles.import_bundle(project, preflight=lambda *_: {'status':'passed', 'testOnly':True})
        self.assertTrue(s.reloadCatalog())
        s.beginEdit(); self.choose(first['id'])
        self.assertTrue(s.setToken('shape.radiusCard', 7)); self.save()
        s.beginEdit(); self.choose('functional')
        self.assertTrue(s.setToken('shape.radiusCard', 9)); self.save()
        for name in ('bundle.json', 'theme.json'):
            document = json.loads((project / name).read_text())
            document['version'] = '1.0.1'; (project / name).write_text(json.dumps(document))
        updated = s.bundles.import_bundle(project, preflight=lambda *_: {'status':'passed', 'testOnly':True})
        self.assertTrue(s.reloadCatalog())
        s.beginEdit(); self.choose(first['id'])
        self.assertEqual(s.draft['bundleRevision']['digest'], updated['digest'])
        self.assertEqual(self.radius(), 13, 'new revision must not inherit old renderer/token adaptation implicitly')
        self.assertTrue(s.setToken('shape.radiusCard', 11)); self.save()
        s.beginEdit(); self.assertTrue(s.stepRevision(-1)); self.settle()
        self.assertEqual(s.draft['bundleRevision']['digest'], first['digest'])
        self.assertEqual(self.radius(), 7); self.save()
        s.beginEdit(); self.assertTrue(s.stepRevision(1)); self.settle()
        self.assertEqual(self.radius(), 11); s.cancel()
        self.assertEqual(self.radius(), 7)
        reconstructed = ThemeService(store=self.store)
        self.assertEqual(reconstructed.resolvedAppearance['bundleRevision']['digest'], first['digest'])
        reconstructed.beginEdit(); self.assertTrue(reconstructed.stepRevision(1))
        snapshot = reconstructed.candidateAppearance
        for content in snapshot.get('requiredContents', []):
            reconstructed.reportCandidate(snapshot['generation'], content, True, '')
        self.assertEqual(reconstructed.resolvedAppearance['tokens']['shape.radiusCard'], 11)
        reconstructed.cancel()
        self.assertEqual(self.settings.value('functional/sentinel'), 'retained')

    def test_save_failed_does_not_commit_profile_or_preferences(self):
        s = self.service
        s.beginEdit(); self.assertTrue(s.setToken('shape.radiusCard', 7)); self.save()
        previous = self.settings.value('appearance/config')
        previous_profiles = self.settings.value('appearance/themeOverrides')
        s.beginEdit(); self.choose('functional')
        self.assertTrue(s.setToken('shape.radiusCard', 9))
        jobs = []
        class CapturingPool:
            def start(self, job): jobs.append(job)
        with patch('theme_service.QThreadPool.globalInstance', return_value=CapturingPool()):
            self.assertTrue(s.apply())
        self.assertEqual(len(jobs), 1)
        s._saved(False, 'injected disk failure')
        self.assertEqual(s.activeThemeId, 'base'); self.assertEqual(self.radius(), 7)
        self.assertEqual(self.settings.value('appearance/config'), previous)
        self.assertEqual(self.settings.value('appearance/themeOverrides'), previous_profiles)
        self.assertNotIn('schema1:functional', s._profiles)
        self.assertEqual(s.draft['overrides']['tokens']['shape.radiusCard'], 9, 'failed draft remains available')
        s.cancel(); s.beginEdit(); self.choose('functional')
        self.assertEqual(self.radius(), s.catalog.resolve('functional')['tokens']['shape.radiusCard'])
        self.assertEqual(self.settings.value('functional/sentinel'), 'retained')

    def test_save_job_restores_all_visual_settings_after_sync_error(self):
        values = {'appearance/config':'old', 'appearance/themeOverrides':'old profiles',
                  'animationsEnabled':False, 'nightMode':'night', 'functional/sentinel':'retained'}
        original = deepcopy(values)
        class FailingSettings:
            Status = QSettings.Status
            def __init__(self, *_): pass
            def value(self, key): return values.get(key)
            def setValue(self, key, value): values[key] = value
            def remove(self, key): values.pop(key, None)
            def setAtomicSyncRequired(self, value): pass
            def sync(self): pass
            def status(self): return QSettings.Status.AccessError
        results = []; result = SaveResult(); result.finished.connect(lambda ok, message:results.append((ok, message)))
        with patch('theme_service.QSettings', FailingSettings):
            SaveJob({'schemaVersion':1,'themeId':'base','overrides':{},'motionMode':'normal','paletteMode':'day'},
                    result, profiles={'schema1:base':{}})._run()
        self.assertEqual(values, original)
        self.assertEqual(len(results), 1); self.assertFalse(results[0][0]); self.assertTrue(results[0][1])

    def test_journal_commit_failure_restores_settings_written_by_worker(self):
        s = self.service
        s.beginEdit(); self.assertTrue(s.setToken('shape.radiusCard',7)); self.save()
        previous = json.loads(self.settings.value('appearance/config'))
        profiles = json.loads(self.settings.value('appearance/themeOverrides'))
        project = self.store.parent/'project'
        shutil.copytree(ROOT/'examples/bundles/studio-ambient', project)
        revision = s.bundles.import_bundle(project, preflight=lambda *_:{'status':'passed','testOnly':True})
        self.assertTrue(s.reloadCatalog())
        s.beginEdit(); self.choose(revision['id']); self.assertTrue(s.setToken('shape.radiusCard',9)); self.settle()
        results=[]; s.saveFinished.connect(results.append)
        with patch.object(s.lifecycle, 'commit', side_effect=ThemeError('journal','injected commit failure')):
            self.assertTrue(s.apply()); wait_save(APP, s)
        self.settings.sync()
        self.assertEqual(results,[False]); self.assertEqual(s.activeThemeId,'base')
        self.assertEqual(self.radius(),7)
        self.assertEqual(json.loads(self.settings.value('appearance/config')),previous)
        self.assertEqual(json.loads(self.settings.value('appearance/themeOverrides')),profiles)
        self.assertEqual(s._profiles,profiles)
        self.assertIsNone(s.lifecycle.read()['pending'])
        self.assertEqual(self.settings.value('functional/sentinel'),'retained')


if __name__ == '__main__':
    try: unittest.main(verbosity=2)
    finally: PRIVATE.cleanup()
