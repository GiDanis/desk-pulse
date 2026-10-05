"""Service-level save/recovery faults with private Qt settings and real bundles.

Bundle import uses a declared test-only preflight; this file tests journal and
service transitions, not renderer compatibility or board performance.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

_private=tempfile.TemporaryDirectory(prefix='smartpc-service-recovery-')
os.environ['XDG_CONFIG_HOME']=str(Path(_private.name)/'config')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')

from PySide6.QtCore import QSettings
from PySide6.QtGui import QGuiApplication
from theme_bundle import ROOT, BundleManager, atomic_json
from theme_core import ThemeError
from theme_lifecycle import BASE, LifecycleManager, selection_key
from theme_service import ThemeService, SaveJob

app=QGuiApplication.instance() or QGuiApplication([])


class ServiceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.private=tempfile.TemporaryDirectory(prefix='smartpc-service-case-')
        self.data=Path(self.private.name)
        self.store=self.data/'themes'
        self.settings=QSettings('SmartPC','Dashboard')
        self.settings.clear(); self.settings.setValue('weather/location','provider-preserved');self.settings.sync()
        self.manager=BundleManager(self.data)

    def tearDown(self):
        self.private.cleanup()

    def installed(self):
        return self.manager.import_bundle(ROOT/'examples/bundles/studio-ambient',
                    preflight=lambda *args:{'status':'passed','testOnly':True})

    def service(self):
        return ThemeService(store=self.store)

    def preview(self,service):
        service.beginEdit()
        self.assertTrue(service.selectDraft('studio.ambient'),service.lastError)
        candidate=service.candidateAppearance
        for content in candidate.get('requiredContents',[]):
            service.reportCandidate(candidate['generation'],content,True,'')
        service.acknowledgeThemeFrame(service.revision,True)
        self.assertTrue(service.readyToApply,service.lastError)

    def committed_bundle(self):
        self.installed();service=self.service();self.preview(service)
        with patch('theme_service.QThreadPool'):
            self.assertTrue(service.apply(),service.lastError)
        # The real persistence callback contract; write the same values the worker
        # owns so the next service instance tests startup rather than an invented UI.
        self.settings.setValue('appearance/config',json.dumps(service._pending));self.settings.sync()
        self.assertTrue(service._saved_state(True,''))
        return service

    def ready(self,service):
        candidate=service.candidateAppearance
        for content in candidate.get('requiredContents',[]):
            service.reportCandidate(candidate['generation'],content,True,'')
        service.acknowledgeThemeFrame(service.revision,True)

    def save(self,service):
        self.ready(service)
        with patch('theme_service.QThreadPool'):
            self.assertTrue(service.apply(),service.lastError)
        SaveJob(service._pending,service._save_result,profiles=service._pending_profiles)._run()
        self.assertEqual(service.status,'ready',service.lastError)

    def test_first_preview_crash_recovers_without_saved_appearance(self):
        revision=self.installed();life=LifecycleManager(self.data)
        life.begin(revision)
        service=self.service()
        self.assertEqual(service.activeThemeId,'base')
        self.assertIsNone(life.read()['pending'])
        self.assertTrue((self.data/'theme-quarantine'/(revision['digest']+'.json')).is_file())
        self.assertEqual(self.settings.value('weather/location'),'provider-preserved')

    def test_corrupt_advisory_backup_does_not_abort_visual_recovery(self):
        self.installed();service=self.service();self.preview(service)
        (self.data/'theme-previous-configuration.json').write_text('{broken')
        service.recoverScene('renderer failed')
        self.assertEqual(service.activeThemeId,'base')
        self.assertEqual(service.status,'recovery')
        self.assertIsNone(service.lifecycle.read()['pending'])
        self.assertEqual(self.settings.value('weather/location'),'provider-preserved')

    def test_corrupt_visual_journal_can_be_recovered_from_running_service(self):
        self.installed();service=self.service();self.preview(service)
        service.lifecycle.path.write_text('{broken')
        service.recoverScene('journal and renderer fault')
        self.assertEqual(service.activeThemeId,'base')
        self.assertEqual(service.lifecycle.read()['active'],BASE)
        self.assertEqual(service.status,'recovery')
        self.assertEqual(self.settings.value('weather/location'),'provider-preserved')

    def test_retry_after_failed_save_waits_for_its_new_coherent_frame(self):
        service=self.committed_bundle();service.beginEdit()
        radius=service.resolvedAppearance['tokens']['shape.radiusCard']
        self.assertTrue(service.setToken('shape.radiusCard',radius+1))
        service.acknowledgeThemeFrame(service.revision,True)
        with patch('theme_service.QThreadPool'):
            self.assertTrue(service.apply())
        service._saved_state(False,'test worker write failure')
        self.assertTrue(service.editing)
        self.assertEqual(service.resolvedAppearance['tokens']['shape.radiusCard'],radius)
        with patch('theme_service.QThreadPool') as pool:
            self.assertFalse(service.apply())
            pool.globalInstance.return_value.start.assert_not_called()
        self.assertIsNone(service._pending)
        self.assertTrue(service.needsFrameAcknowledgement)
        service.acknowledgeThemeFrame(service.revision,True)
        with patch('theme_service.QThreadPool'):
            self.assertTrue(service.apply(),service.lastError)
        service._saved_state(True,'')
        self.assertEqual(service.resolvedAppearance['tokens']['shape.radiusCard'],radius+1)

    def test_journal_begin_failure_completes_async_save_as_failed(self):
        service=self.service();service.beginEdit();service.setToken('shape.radiusCard',5)
        state=service.lifecycle.read()
        state['lastRecovery']={'failed':{'kind':'corruptJournal'},'selected':BASE,'reason':'test'}
        atomic_json(service.lifecycle.path,state)
        service._pending=deepcopy(service.draft)
        results=[];service.saveFinished.connect(results.append)
        with patch.object(service.lifecycle,'begin',side_effect=ThemeError('activation','disk fault')):
            self.assertFalse(service._saved_state(True,''))
        self.assertEqual(results,[False]);self.assertIsNone(service._pending)
        self.assertEqual(service.status,'error')
        self.assertEqual(json.loads(self.settings.value('appearance/config'))['themeId'],'base')
        self.assertEqual(self.settings.value('weather/location'),'provider-preserved')

    def test_pending_save_rejects_reset_preview_and_cancel(self):
        service=self.service();service.beginEdit();service.setToken('shape.radiusCard',5)
        with patch('theme_service.QThreadPool'):
            self.assertTrue(service.apply())
        pending=deepcopy(service._pending);revision=service.revision
        self.assertFalse(service.resetDraft());self.assertFalse(service.preview());self.assertFalse(service.cancel())
        self.assertEqual(service._pending,pending);self.assertEqual(service.revision,revision)
        service._saved_state(False,'test cleanup')

    def test_commit_and_cancel_io_failure_do_not_leave_editor_saving(self):
        self.installed();service=self.service();self.preview(service)
        with patch('theme_service.QThreadPool'):
            self.assertTrue(service.apply())
        results=[];service.saveFinished.connect(results.append)
        with patch.object(service.lifecycle,'commit',side_effect=OSError('commit fault')), \
             patch.object(service.lifecycle,'cancel',side_effect=OSError('cancel fault')):
            self.assertFalse(service._saved_state(True,''))
        self.assertEqual(results,[False]);self.assertIsNone(service._pending)
        self.assertEqual(service.activeThemeId,'base');self.assertEqual(service.status,'error')
        self.assertIsNotNone(service.lifecycle.read()['pending'],'boot recovery must retain interrupted transaction')

    def test_failed_font_resolution_releases_acquired_revision_lease(self):
        revision=self.installed();service=self.service();service.reloadCatalog()
        identity={'origin':'bundle','revision':selection_key(revision),'digest':revision['digest']}
        with patch.object(service.catalog,'resolve',side_effect=ThemeError('font','test failure')):
            with self.assertRaises(ThemeError):service.acquireRevision(identity)
        self.assertEqual(list(service.lifecycle.leases_root.glob('*.json')),[])
        self.assertEqual(service._leases,{})

    def test_malformed_bundle_identity_is_a_validation_error(self):
        service=self.service()
        for value in ([],{},'bundle',{'id':'base'}):
            candidate=deepcopy(service.draft);candidate['bundleRevision']=value
            with self.subTest(value=value),self.assertRaises(ThemeError):service._validate_config(candidate)

    def test_damaged_profile_values_are_ignored_before_switching(self):
        self.settings.setValue('appearance/themeOverrides',json.dumps({
            'schema1:functional':{'tokens':[]},'schema1:base':[], 'valid':{'tokens':{'shape.radiusCard':4}}}))
        self.settings.sync();service=self.service()
        self.assertEqual(service._profiles,{'valid':{'tokens':{'shape.radiusCard':4}}})
        service.beginEdit();self.assertTrue(service.selectDraft('functional'),service.lastError)

    def test_per_theme_profiles_persist_and_cancel_discards_draft_changes(self):
        service=self.service();service.beginEdit()
        self.assertTrue(service.setToken('shape.radiusCard',4))
        self.assertTrue(service.setToken('typography.textScale',1.05))
        self.assertTrue(service.selectDraft('functional'))
        self.assertTrue(service.setToken('shape.radiusCard',8))
        self.assertTrue(service.selectDraft('base'))
        self.assertEqual(service.draft['overrides']['tokens']['shape.radiusCard'],4)
        self.save(service)
        restarted=self.service();restarted.beginEdit()
        self.assertTrue(restarted.selectDraft('functional'))
        self.assertEqual(restarted.draft['overrides']['tokens']['shape.radiusCard'],8)
        self.assertEqual(restarted.draft['overrides']['tokens']['typography.textScale'],1.05)
        self.assertTrue(restarted.setToken('shape.radiusCard',10))
        self.assertTrue(restarted.cancel())
        restarted.beginEdit();self.assertTrue(restarted.selectDraft('functional'))
        self.assertEqual(restarted.draft['overrides']['tokens']['shape.radiusCard'],8)

    def test_revision_switch_restores_own_overrides_and_retains_global_text_scale(self):
        service=self.committed_bundle()
        project=self.data/'update';shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
        for name in ('bundle.json','theme.json'):
            value=json.loads((project/name).read_text());value['version']='1.0.1'
            (project/name).write_text(json.dumps(value))
        self.manager.import_bundle(project,preflight=lambda *args:{'status':'passed','testOnly':True})
        self.assertTrue(service.reloadCatalog())
        with patch.object(service.bundles,'list_revisions',side_effect=AssertionError('QML revision read must not scan files')), \
             patch('theme_bundle.BundleManager.verify_revision',side_effect=AssertionError('QML revision read must not hash assets')):
            self.assertEqual([row['version'] for row in service.revisions],['1.0.0','1.0.1'])
        service.beginEdit();self.assertTrue(service.setToken('shape.radiusCard',4))
        self.assertTrue(service.setToken('typography.textScale',1.05))
        self.assertTrue(service.stepRevision(1))
        self.ready(service)
        self.assertEqual(service.draft['bundleRevision']['version'],'1.0.1')
        self.assertEqual(service.draft['overrides']['tokens']['typography.textScale'],1.05)
        self.assertNotIn('shape.radiusCard',service.draft['overrides']['tokens'])
        self.assertTrue(service.setToken('shape.radiusCard',8))
        self.assertTrue(service.stepRevision(-1));self.ready(service)
        self.assertEqual(service.draft['overrides']['tokens']['shape.radiusCard'],4)
        self.save(service)
        restarted=self.service();restarted.beginEdit();self.assertTrue(restarted.stepRevision(1))
        self.ready(restarted)
        self.assertEqual(restarted.draft['overrides']['tokens']['shape.radiusCard'],8)
        self.assertEqual(restarted.draft['overrides']['tokens']['typography.textScale'],1.05)

    def test_malformed_nested_journal_recovers_without_provider_reset(self):
        life=LifecycleManager(self.data)
        for field,value in [('adaptations',[]),('failureCounts',{'broken':-1}),
                            ('lastRecovery',{'failed':{},'selected':'bad','reason':'bad'})]:
            state=life._default();state[field]=value;atomic_json(life.path,state)
            with self.subTest(field=field):
                result=life.recover();self.assertTrue(result['recovered'])
                self.assertEqual(life.read()['active'],BASE)
        self.assertEqual(self.settings.value('weather/location'),'provider-preserved')


if __name__=='__main__':
    unittest.main()
