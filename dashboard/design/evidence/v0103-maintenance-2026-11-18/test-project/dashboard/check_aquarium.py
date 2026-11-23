"""Meaningful controller/catalogue regressions; isolated, without network or GUI."""
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from copy import deepcopy
from PySide6.QtCore import QCoreApplication
from aquarium import AquariumService
from aquarium_catalog import ROOT,load_catalog


class AquariumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):self.service=AquariumService()
    def tearDown(self):self.service.close();self.app.processEvents()
    def open(self):
        self.service.setLifecycle(True,False,False,False,'normal',False)
        end=time.monotonic()+5
        while self.service.snapshot['status']=='loading' and time.monotonic()<end:self.app.processEvents();time.sleep(.002)
        self.assertEqual(self.service.snapshot['status'],'ready')
        self.service.setLifecycle(True,True,False,False,'normal',False)
    def test_lazy_constructor_does_not_load_assets(self):
        self.assertIsNone(self.service._executor);self.assertEqual(self.service.snapshot['status'],'idle')
    def test_actual_catalog_and_two_species_six_actors(self):
        self.open();s=self.service.snapshot
        self.assertEqual(len(s['species']),2);self.assertEqual(len(s['instances']),6)
        self.assertEqual([r['speciesId'] for r in s['instances']],['teal']*4+['gold']*2)
        self.assertEqual(s['effectivePlayback'],'running')
    def test_pause_survives_overlay_and_is_idempotent(self):
        self.open();self.assertTrue(self.service.pause());before=deepcopy(self.service.snapshot)
        self.assertTrue(self.service.pause());self.assertEqual(before,self.service.snapshot)
        self.service.setLifecycle(True,True,True,False,'normal',False)
        self.service.setLifecycle(True,True,False,False,'normal',False)
        self.assertEqual(self.service.snapshot['requestedPlayback'],'paused')
        self.assertTrue(self.service.resume());self.assertEqual(self.service.snapshot['effectivePlayback'],'running')
    def test_urgent_requires_explicit_resume_and_blocks_commands(self):
        self.open();self.service.setLifecycle(True,True,False,True,'normal',False)
        self.assertFalse(self.service.resume());self.assertFalse(self.service.pause())
        self.service.setLifecycle(True,True,False,False,'normal',False)
        self.assertEqual(self.service.snapshot['requestedPlayback'],'paused');self.assertTrue(self.service.resume())
    def test_reduced_off_do_not_change_global_policy(self):
        self.open()
        for mode in ('reduced','off'):
            self.service.setLifecycle(True,True,False,False,mode,False)
            self.assertEqual(self.service.snapshot['effectivePlayback'],'static');self.assertFalse(self.service.resume())
        self.service.setLifecycle(True,True,False,False,'normal',False)
        self.assertEqual(self.service.snapshot['effectivePlayback'],'running')
    def test_entering_during_existing_urgent_also_requires_resume(self):
        self.service.setLifecycle(False,False,False,True,'normal',False)
        self.service.setLifecycle(True,False,False,True,'normal',False)
        self.service.setLifecycle(True,True,False,False,'normal',False)
        self.assertEqual(self.service.snapshot['requestedPlayback'],'paused')
    def test_snapshot_revision_stable_without_lifecycle_change(self):
        self.open();changes=[];self.service.changed.connect(lambda:changes.append(1));before=self.service.snapshot
        for _ in range(300):self.service.setLifecycle(True,True,False,False,'normal',False)
        self.assertIs(before,self.service.snapshot);self.assertEqual(changes,[])
    def test_hidden_theme_and_new_visit(self):
        self.open();old=self.service.snapshot['sessionId'];self.service.pause()
        self.service.setLifecycle(False,False,False,False,'normal',True)
        self.assertIn('hidden',self.service.snapshot['suspendReasons'])
        self.service.setLifecycle(True,True,False,False,'normal',False)
        self.assertNotEqual(old,self.service.snapshot['sessionId']);self.assertEqual(self.service.snapshot['effectivePlayback'],'running')
    def test_stale_asset_callback_does_not_replace_current_session(self):
        self.open();before=deepcopy(self.service.snapshot)
        self.service._accept_catalog(-1,None,'stale failure');self.service.reportAssetError('old','wrong')
        self.assertEqual(before,self.service.snapshot)
        self.service.reportAssetError(before['sessionId'],'Missing texture')
        self.assertEqual(self.service.snapshot['effectivePlayback'],'error')
    def test_close_discards_completed_work(self):
        self.open();before=deepcopy(self.service.snapshot);self.service.close();self.service._accept_catalog(self.service._epoch,None,'stale')
        self.assertEqual(before,self.service.snapshot);self.assertFalse(self.service.resume())
    def invalid(self,mutate):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp);shutil.copytree(ROOT,target,dirs_exist_ok=True)
            data=json.loads((target/'catalog.json').read_text());mutate(data,target);(target/'catalog.json').write_text(json.dumps(data))
            with self.assertRaises((ValueError,KeyError)):load_catalog(target)
    def test_legacy_bundle_uses_additive_fallback_without_mutation(self):
        from theme_bundle import effective_manifest
        value={'coverage':{'mode':'complete','surfaces':['shell.main'],'fallbacks':[]}}
        before=deepcopy(value)
        result=effective_manifest(value,{'shell.main','aquarium.main'})
        self.assertEqual(value,before);self.assertEqual(result['coverage']['fallbacks'],['aquarium.main'])
        broken=effective_manifest(value,{'shell.main','unknown.new'})
        self.assertEqual(broken,value)

    def test_rejects_duplicate_species(self):self.invalid(lambda d,p:d['species'].append(deepcopy(d['species'][0])))
    def test_rejects_corrupt_file(self):self.invalid(lambda d,p:(p/'background.png').write_bytes(b'broken'))
    def test_rejects_escape(self):self.invalid(lambda d,p:d['files'].update({'../escape.png':'0'*64}))
    def test_rejects_nonfinite_and_outside_sheet(self):
        self.invalid(lambda d,p:d['species'][0].update(speed=float('nan')))
        self.invalid(lambda d,p:d['species'][0]['bodyRect'].update(width=9999))
    def test_rejects_false_schema_version(self):self.invalid(lambda d,p:d.update(schemaVersion=True))
    def test_rejects_wrong_real_dimensions(self):self.invalid(lambda d,p:d['species'][0].update(atlasWidth=1280))
    def test_rejects_unlisted_texture_before_opening_it(self):
        self.invalid(lambda d,p:d['species'][0].update(file='../private.png'))

if __name__=='__main__':unittest.main()
