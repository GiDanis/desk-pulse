"""Bundle adjustments and truthful catalog coverage, with private preferences.

Unit readiness/frame acknowledgements are explicit simulations; the final test
uses real Main/QML settings rows and no provider or production data.
"""
from copy import deepcopy
import json
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from theme_fixture_support import isolate_process
PRIVATE, BASE = isolate_process()
from PySide6.QtCore import QSettings, QThreadPool
from PySide6.QtGui import QGuiApplication
from theme_core import ROOT
from theme_api_contract import ThemeApiContract
from theme_service import ThemeService

APP = None if '--main-proof' in sys.argv else QGuiApplication([])
if APP:
    APP.setOrganizationName('SmartPC'); APP.setApplicationName('Dashboard')


class AdjustmentTests(unittest.TestCase):
    def setUp(self):
        QSettings('SmartPC', 'Dashboard').clear()
        self.store=BASE/self.id().split('.')[-1]/'themes'
        self.service=ThemeService(store=self.store)

    def tearDown(self):
        self.service.cancel(); QThreadPool.globalInstance().waitForDone(5000)

    def project(self, version='1.0.0', adjustments=()):
        destination=self.store.parent/('project-'+version)
        shutil.copytree(ROOT/'examples/bundles/studio-ambient',destination)
        for filename in ('bundle.json','theme.json'):
            value=json.loads((destination/filename).read_text());value['version']=version
            if filename=='bundle.json': value['adjustments']=list(adjustments)
            (destination/filename).write_text(json.dumps(value))
        # Test-only bypass isolates adjustment semantics, not renderer import proof.
        return self.service.bundles.import_bundle(destination,preflight=lambda *_:{'status':'passed','testOnly':True})

    def settle(self):
        candidate=self.service.candidateAppearance
        for content in candidate.get('requiredContents',[]):
            self.service.reportCandidate(candidate['generation'],content,True,'')
        self.service.acknowledgeThemeFrame(self.service.revision,True)

    def test_disallowed_controls_cannot_modify_bundle_and_inherited_scale_removed(self):
        s=self.service; revision=self.project(); self.assertTrue(s.reloadCatalog())
        s.beginEdit(); self.assertTrue(s.setToken('typography.textScale',1.05));self.assertTrue(s.setSection('paletteMode','night'))
        self.assertTrue(s.selectDraft(revision['id']),s.lastError);self.settle()
        self.assertEqual(s.draft['paletteMode'],'auto')
        self.assertNotIn('typography.textScale',s.draft['overrides'].get('tokens',{}))
        before=deepcopy(s.draft)
        self.assertFalse(s.setToken('typography.textScale',1.1))
        self.assertFalse(s.setTokens({'typography.textScale':1.1,'shape.radiusCard':7}))
        self.assertFalse(s.setSection('paletteMode','day'))
        self.assertEqual(s.draft,before,'rejected controls must be atomic')
        self.assertTrue(s.setSection('motionMode','off'),'Off remains global policy')
        self.assertTrue(s.setSection('motionMode','reduced'),'Reduced remains global policy')
        self.assertTrue(s.setToken('shape.radiusCard',7),'compatibility editor remains available')
        metadata=s.selectedTheme
        fallback_count = len(ThemeApiContract().surfaces) - 5
        self.assertEqual((metadata['coverageMode'],metadata['ownCount'],metadata['fallbackCount']),('partial',5,fallback_count))
        self.assertEqual(metadata['adjustments'],['motionMode'])
        self.assertIn('Parziale',metadata['coverageSummary'])
        with patch.object(s.bundles,'verify_revision',side_effect=AssertionError('QML getter must not read files')):
            self.assertEqual(s.selectedTheme,metadata)
            self.assertEqual(next(row for row in s.themes if row['id']==revision['id'])['coverageMode'],'partial')

    def test_revision_specific_capabilities_and_stale_profiles(self):
        s=self.service; first=self.project(adjustments=('paletteMode','textScale'))
        second=self.project('1.0.1'); self.assertTrue(s.reloadCatalog());s.beginEdit()
        self.assertTrue(s.selectDraft(first['id']));self.settle()
        # A previously stored adaptation must not override the current contract.
        key=s._profile_key(s.draft);s._draft_profiles[key]={'tokens':{'typography.textScale':1.1}}
        self.assertTrue(s.stepRevision(-1));self.settle()
        self.assertEqual(s.selectedTheme['version'],'1.0.0')
        self.assertIn('textScale',s.selectedTheme['adjustments'])
        self.assertTrue(s.setToken('typography.textScale',1.05))
        self.assertTrue(s.setSection('paletteMode','night'))
        self.assertTrue(s.stepRevision(1));self.settle()
        self.assertEqual(s.selectedTheme['version'],'1.0.1')
        self.assertNotIn('textScale',s.selectedTheme['adjustments'])
        self.assertNotIn('typography.textScale',s.draft['overrides'].get('tokens',{}))
        self.assertEqual(s.draft['paletteMode'],'auto')
        self.assertFalse(s.setToken('typography.textScale',1.1))
        self.assertEqual(s.draft['bundleRevision']['digest'],second['digest'])

    def test_legacy_editor_and_motion_policy_remain_available(self):
        s=self.service;s.beginEdit()
        self.assertTrue(s.selectDraft('functional'))
        self.assertTrue(s.setSection('paletteMode','night'))
        self.assertTrue(s.setTokens({'typography.textScale':1.05,'shape.radiusCard':9}))
        self.assertEqual(set(s.selectedTheme['adjustments']),{'paletteMode','textScale','motionMode'})
        self.assertEqual(s.selectedTheme['coverageMode'],'builtin')
        self.assertNotIn('Completo',s.selectedTheme['coverageSummary'])

    def test_real_main_rows_report_disallowed_controls_and_partial_coverage(self):
        child=subprocess.run([sys.executable,__file__,'--main-proof'],capture_output=True,text=True,timeout=45)
        self.assertEqual(child.returncode,0,child.stdout+child.stderr)
        self.assertIn('main-settings-adjustments-passed',child.stdout)


def main_proof():
    from theme_fixture_support import LegacyHarness
    from theme_test_support import as_value
    from PySide6.QtCore import QObject
    harness=LegacyHarness(BASE/'main-proof',{'theme':'base','variant':'day','motion':'off'})
    try:
        s=harness.service
        project=BASE/'main-project';shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
        manifest=json.loads((project/'bundle.json').read_text());manifest['adjustments']=[]
        (project/'bundle.json').write_text(json.dumps(manifest))
        revision=s.bundles.import_bundle(project,preflight=lambda *_:{'status':'passed','testOnly':True})
        assert s.reloadCatalog();s.beginEdit();assert s.selectDraft(revision['id']),s.lastError
        harness.wait_ready()
        assert not s.candidateAppearance,s.lastError
        harness.root.setProperty('overlay','appearance');harness.pump(60)
        settings=harness.root.findChild(QObject,'settingsPanel')
        rows=as_value(settings.property('simpleAppearanceRows'))
        assert rows[0]['enabled'] is False,rows
        fallback_count = len(ThemeApiContract().surfaces) - 5
        assert 'Parziale' in rows[2]['detail'] and '5 propri' in rows[2]['detail'] and f'{fallback_count} Base' in rows[2]['detail'],rows[2]
        assert rows[1].get('enabled',True),'global motion policy must remain available'
        payload=harness.expression('publicSurfacePayload("settings.appearance")')
        by_id={row['id']:row for row in payload['rows']}
        assert by_id['appearance.palette']['enabled'] is False
        assert 'appearance.textScale' not in by_id
        harness.root.setProperty('overlay','system');harness.pump(40)
        display=harness.expression('publicSurfacePayload("settings.display")')
        assert next(row for row in display['rows'] if row['id']=='appearance.textScale')['enabled'] is False
        harness.root.setProperty('overlay','appearance');harness.pump(40)
        assert 'Parziale' in by_id['appearance.theme']['detail']
        assert by_id['appearance.motion']['enabled'] is True
        settings.setProperty('advancedAppearance',True);harness.pump(20)
        rows=as_value(settings.property('advancedAppearanceRows'))
        assert rows[0]['enabled'] is False and 'appearance.textScale' not in {row['id'] for row in rows}
        assert not harness.messages,harness.messages
        print('main-settings-adjustments-passed')
    finally: harness.close()


if __name__=='__main__':
    if '--main-proof' in sys.argv: main_proof()
    else: unittest.main()
