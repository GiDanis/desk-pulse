"""Quarantine inventory and guarded isolated readmission, without GUI execution."""
import json
from pathlib import Path
import tempfile
import shutil
import unittest

from theme_bundle import ROOT, BundleManager, atomic_json
from theme_core import ThemeError
from theme_lifecycle import BASE, LifecycleManager


class ReadmissionTests(unittest.TestCase):
    def setUp(self):
        self.private=tempfile.TemporaryDirectory(prefix='theme-readmit-test-')
        self.root=Path(self.private.name)
        self.manager=BundleManager(self.root)
        self.revision=self.manager.import_bundle(ROOT/'examples/bundles/studio-ambient',
                            preflight=lambda *_:{'status':'passed','testOnly':True})
        self.identity={k:self.revision[k] for k in ('id','version','digest')}
        self.lifecycle=LifecycleManager(self.root)
        self.marker=self.root/'theme-quarantine'/(self.identity['digest']+'.json')
        atomic_json(self.marker,{'revision':self.identity,'reason':'GUI exit -11','failures':1})

    def tearDown(self):
        self.private.cleanup()

    def test_inventory_blocked_legacy_date_and_executable_exclusion(self):
        row=self.manager.inventory()[0]
        self.assertEqual(row['state'],'blocked')
        self.assertFalse(row['selectable']);self.assertIsNone(row['failedAt'])
        self.assertEqual(self.manager.list_revisions(),[])
        self.assertEqual(len(self.manager.list_revisions(include_quarantined=True)),1)

    def test_success_uses_copy_preserves_selection_and_incident(self):
        initial=self.lifecycle.read()
        def check(payload,*_):
            self.assertNotEqual(str(payload),self.revision['payload'])
            self.assertTrue(self.marker.exists())
            return {'status':'passed','backend':'offscreen','boardEglfs':'notVerified'}
        result=self.lifecycle.verify_quarantined(self.identity,check)
        self.assertFalse(self.marker.exists());self.assertEqual(self.lifecycle.read(),initial)
        self.assertEqual(self.lifecycle.read()['active'],BASE)
        report=json.loads(Path(result['report']).read_text())
        self.assertEqual(report['incident']['reason'],'GUI exit -11')
        self.assertFalse(report['productionActivation'])
        self.assertEqual(self.manager.inventory()[0]['state'],'available')
        self.assertEqual(list(self.lifecycle.leases_root.glob('*.json')),[])

    def test_failed_check_keeps_block_and_releases_lease(self):
        with self.assertRaises(ThemeError):
            self.lifecycle.verify_quarantined(self.identity,lambda *_:{'status':'failed','error':'bad renderer'})
        self.assertTrue(self.marker.exists())
        self.assertEqual(list(self.lifecycle.leases_root.glob('*.json')),[])

    def test_new_incident_cannot_be_removed_by_old_check(self):
        def check(*_):
            atomic_json(self.marker,{'revision':self.identity,'reason':'new crash','failures':2})
            return {'status':'passed'}
        with self.assertRaises(ThemeError):self.lifecycle.verify_quarantined(self.identity,check)
        self.assertEqual(json.loads(self.marker.read_text())['reason'],'new crash')

    def test_changed_generation_cannot_readmit(self):
        def check(*_):
            self.lifecycle.begin(BASE)
            return {'status':'passed'}
        with self.assertRaises(ThemeError):self.lifecycle.verify_quarantined(self.identity,check)
        self.assertTrue(self.marker.exists())

    def test_changed_payload_is_detected_after_check(self):
        def check(*_):
            path=Path(self.revision['payload'])/'qml/Home.qml'
            path.write_text(path.read_text()+'\n// tampered\n')
            return {'status':'passed'}
        with self.assertRaises(ThemeError):self.lifecycle.verify_quarantined(self.identity,check)
        self.assertTrue(self.marker.exists());self.assertEqual(self.manager.inventory()[0]['state'],'invalid')

    def test_malformed_descriptor_visible(self):
        (Path(self.revision['path'])/'revision.json').write_text('{')
        rows=self.manager.inventory()
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['state'],'invalid')
        self.assertFalse(rows[0]['selectable']);self.assertTrue(rows[0]['reason'])

    def test_cancellation_after_pass_cannot_remove_marker(self):
        with self.assertRaises(ThemeError):
            self.lifecycle.verify_quarantined(self.identity,lambda *_:{'status':'passed'},cancelled=lambda:True)
        self.assertTrue(self.marker.exists())

    def test_malformed_incident_visible_without_breaking_catalog(self):
        atomic_json(self.marker,[])
        row=self.manager.inventory()[0]
        self.assertEqual(row['state'],'invalid');self.assertFalse(row['selectable'])

    def test_healthy_revision_remains_selectable_beside_blocked_one(self):
        project=self.root/'new-project';shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
        for name in ('bundle.json','theme.json'):
            path=project/name;value=json.loads(path.read_text());value['version']='2.0.0';atomic_json(path,value)
        healthy=self.manager.import_bundle(project,preflight=lambda *_:{'status':'passed','testOnly':True})
        self.assertEqual([r['digest'] for r in self.manager.list_revisions()],[healthy['digest']])
        self.assertEqual({r['state'] for r in self.manager.inventory()},{'available','blocked'})


if __name__=='__main__':unittest.main()
