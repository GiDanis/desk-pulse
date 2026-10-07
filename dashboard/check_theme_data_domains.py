"""Explicit PageContext subscriptions preserve flexibility without unused trees."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from theme_bundle import validate_project
from theme_core import ROOT, ThemeError

class DomainTests(unittest.TestCase):
    def setUp(self):
        self.private=tempfile.TemporaryDirectory();self.addCleanup(self.private.cleanup)
        self.project=Path(self.private.name)/'project';shutil.copytree(ROOT/'examples/bundles/studio-ambient',self.project)
    def change(self,value,index=0,remove=False):
        path=self.project/'visual-registry.json';doc=json.loads(path.read_text())
        if remove:doc['presentations'][index].pop('dataDomains',None)
        else:doc['presentations'][index]['dataDomains']=value
        path.write_text(json.dumps(doc)+'\n')
    def test_default_remains_full(self):
        self.change(None,remove=True);validate_project(self.project)
    def test_empty_and_all_subscriptions_valid(self):
        for values in [[],['weather','account','nextEvent','sport','team','fantasy','racing']]:
            self.change(values);validate_project(self.project)
    def test_unknown_duplicate_and_non_list_rejected(self):
        for values in [['unknown'],['weather','weather'],False,'weather',[0]]:
            self.change(values)
            with self.assertRaises(ThemeError):validate_project(self.project)
    def test_non_page_rejected(self):
        self.change(['weather'],index=1)
        with self.assertRaises(ThemeError):validate_project(self.project)


def main_proof():
    from theme_fixture_support import isolate_process,LegacyHarness
    private,base=isolate_process();harness=None
    try:
        from PySide6.QtCore import QObject,qVersion
        from theme_runtime import preflight
        from theme_test_support import as_value,wait_save
        import time
        harness=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
        service=harness.service;project=base/'project';shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
        revision=service.bundles.import_bundle(project,preflight=preflight)
        assert service.reloadCatalog();service.beginEdit();assert service.selectDraft(revision['id']);harness.wait_ready()
        deadline=time.monotonic()+5
        while not service.readyToApply and time.monotonic()<deadline:harness.pump(5)
        assert service.apply();wait_save(harness.app,service)
        home=harness.root.findChild(QObject,'homeNow');loader=as_value(home.property('currentLoader'))
        adapter=loader.findChild(QObject,'publicContextAdapter');context=as_value(adapter.property('publicContext'))
        assert as_value(adapter.property('modelDomains'))==['weather','nextEvent']
        payload=as_value(adapter.property('payload'));assert set(payload['model'])=={'weather','nextEvent'}
        assert context.weather.temperature.available and context.weather.temperature.value==0
        assert context.sport is None and context.racing is None and context.account is None
        assert harness.value('sport')['data']['fixtures'],'Opting out must not alter the provider'
        assert not harness.messages,harness.messages
        print(json.dumps({'status':'passed','qt':qVersion(),'checks':['real-manifest-subscription','bridge-model-projection',
            'unsubscribed-null','weather-zero-preserved','provider-unchanged'],'qmlWarnings':harness.messages}))
    finally:
        if harness:harness.close()
        private.cleanup()

if __name__=='__main__':
    import sys
    if '--main-proof' in sys.argv:main_proof()
    else:unittest.main()
