"""Qt controller -> GUI interpreter relay -> isolated learner on private data."""
from copy import deepcopy
from pathlib import Path
import json,os,tempfile,time,unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication
from game import GameService
from game_store import GameStore,canonical
from game_process import ProcessHandle
from check_game_menu import menu_prepare

@unittest.skipUnless(os.environ.get('SMARTPC_TEST_REFERENCE_POLICY') and os.environ.get('SMARTPC_GAME_LEARNER_PYTHON'),'Explicit private model and learner interpreter required')
class ReferenceRelayChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])

    def wait(self,condition,seconds=30):
        deadline=time.monotonic()+seconds
        while not condition() and time.monotonic()<deadline:self.app.processEvents();time.sleep(.005)
        self.assertTrue(condition())

    def test_real_qt_start_save_switch_and_resume_across_interpreters(self):
        import sys
        self.assertNotIn('torch',sys.modules)
        base=json.loads(Path(os.environ['SMARTPC_TEST_REFERENCE_POLICY']).read_text())
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,SMARTPC_GAME_REFERENCE_EXPERIMENT='1'):
            store=GameStore(root)
            for name in ('Crono','Memoria'):
                driver=next(d for d in store.drivers() if d['name']==name);policy=deepcopy(base)
                # Fixture metadata selects the backend; no synthetic driving
                # result or release authority is created.
                policy['algorithm']=driver['profile']['algorithm'];policy['origin']={**policy['origin'],'backend':'sb3-skill-1'}
                with store.connect() as db:db.execute('UPDATE drivers SET profile=? WHERE id=?',
                    (canonical({**driver['profile'],'hidden':128,'learningBackend':'sb3-skill-1'}).decode(),driver['id']))
                store.save_training(driver['id'],{},policy,0,0)
            s=GameService(root)
            try:
                for name,mode in (('Crono','impara'),('Memoria','impara_infinito')):
                    menu_prepare(s,name,mode);self.assertTrue(s._settings.apply('start'))
                    self.wait(lambda:s._run_state in ('running','error'));self.assertEqual(s._run_state,'running',s._message)
                    self.assertIsInstance(s._process,ProcessHandle)
                    self.wait(lambda:s._scene.get('meta',{}).get('learningStats',{}).get('decisions',0)>128 or s._run_state=='error')
                    self.assertEqual(s._run_state,'running',s._message)
                    self.assertTrue(s.pause());self.wait(lambda:(s._run_state=='paused' and s._save_state=='saved') or s._run_state=='error')
                    self.assertEqual(s._run_state,'paused',s._message)
                    self.assertNotIn('libtorch',(Path('/proc')/str(s._process.pid)/'maps').read_text())
                self.assertTrue(s.start());self.wait(lambda:s._run_state=='running')
                s.stop();self.wait(lambda:s._process is None);self.assertEqual(s._save_state,'saved')
                self.assertNotIn('torch',sys.modules)
            finally:s.close()

if __name__=='__main__':unittest.main()
