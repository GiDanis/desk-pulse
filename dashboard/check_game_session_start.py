"""Regression of keypad editing, real child startup and responsive teardown."""
from copy import deepcopy
from pathlib import Path
import tempfile,time,unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication,QTimer
from game import GameService
from check_game_menu import menu_prepare


class SessionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])

    def wait(self,condition,seconds=25):
        deadline=time.monotonic()+seconds
        while not condition() and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.005)
        self.assertTrue(condition())

    def test_up_and_down_commit_draft_without_writing_or_trapping_focus(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameService(root)
            try:
                s.openSettings();q=s._settings
                original=deepcopy(s._store.drivers())
                self.assertTrue(s.settingsAction('mode',1));s.settingsKey(6)
                self.assertTrue(q.edit);s.settingsKey(8)
                self.assertIsNone(q.edit);self.assertEqual(q.selected,'driver')
                self.assertEqual(q.draft['mode'],'qualifica')
                for mode in ('impara','qualifica','gara','impara_infinito','impara_sorpasso'):
                    q.draft['mode']=mode
                    for _ in range(3):
                        for key in [8]*(len(q.rows())+2)+[2]*(len(q.rows())+2):s.settingsKey(key)
                        self.assertEqual(q.selected,'mode')
                self.assertEqual(s._store.drivers(),original)
                self.assertIsNone(s._process)
            finally:s.close()

    def test_start_from_bottom_never_reads_large_store_in_key_handler(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameService(root)
            try:
                menu_prepare(s,'Crono','qualifica');q=s._settings
                for _ in range(len(q.rows())+2):s.settingsKey(8)
                self.assertEqual(q.selected,'start')
                pulse=[];timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:pulse.append(time.monotonic()));timer.start()
                with patch.object(s._store,'driver',side_effect=AssertionError('GUI projection read')):
                    start=time.monotonic();s.settingsKey(5)
                    self.assertLess(time.monotonic()-start,.25)
                    process=s._process;self.assertIsNotNone(process)
                    self.assertFalse(s.start())
                    self.wait(lambda:s._run_state in ('running','error'))
                self.assertEqual(s._run_state,'running',s._message)
                self.assertGreater(len(pulse),2)
                self.assertTrue(s.pause());self.wait(lambda:s._run_state=='paused')
                self.assertTrue(s.start());self.wait(lambda:s._run_state=='running')
                self.assertIs(s._process,process)
                before=len(pulse);start=time.monotonic();s.stop()
                self.assertLess(time.monotonic()-start,.1)
                self.wait(lambda:s._process is None)
                self.assertGreaterEqual(len(pulse),before)
                timer.stop()
            finally:s.close()

    def test_collector_pause_ack_does_not_hit_old_two_second_deadline(self):
        from unittest.mock import Mock
        import queue
        with tempfile.TemporaryDirectory() as root:
            s=GameService(root)
            try:
                process=Mock();process.is_alive.return_value=True
                pipe=Mock();pipe.poll.side_effect=[True,False]
                pipe.recv.return_value={'type':'pause_pending','session':s._epoch}
                s._process=process;s._command=pipe;s._frames=queue.Queue()
                s._run_state='pausing';s._pause_started=time.monotonic()-3
                s._poll()
                self.assertEqual(s._run_state,'pausing');self.assertEqual(s._save_state,'saving')
                process.terminate.assert_not_called()
                s._pause_ack_started=time.monotonic()-6
                pipe.poll.side_effect=[False];s._poll();process.terminate.assert_not_called()
                s._pause_ack_started=time.monotonic()-11
                pipe.poll.side_effect=[False];s._poll()
                process.terminate.assert_called_once();self.assertEqual(s._run_state,'error')
            finally:
                s._process=s._command=s._frames=None;s.close()

    def test_automatic_save_cannot_acknowledge_a_pending_pause(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameService(root);events=[];s.operationFinished.connect(lambda *args:events.append(args))
            try:
                s._run_state='pausing';s._save_state='saving'
                s._ack_save({'automatic':True})
                self.assertEqual(s._save_state,'saving');self.assertFalse(events)
                s._ack_save({'automatic':False})
                self.assertEqual(s._save_state,'saved');self.assertEqual(events,[('save',True,'')])
            finally:s.close()

    def test_child_errors_stay_in_game_and_leave_previous_artifacts(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameService(root)
            try:
                d=s._settings.current();d['driver']='nonexistent'
                original=sorted(p.name for p in (Path(root)/'policies').iterdir())
                self.assertTrue(s.startSetup(d));self.wait(lambda:s._run_state=='error')
                self.assertIn('Pilota sconosciuto',s._message)
                self.assertEqual(sorted(p.name for p in (Path(root)/'policies').iterdir()),original)
            finally:s.close()

    def test_changed_setup_after_pause_waits_for_old_worker_and_keeps_draft(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameService(root)
            try:
                menu_prepare(s,'Crono','qualifica');self.assertTrue(s._settings.apply('start'))
                self.wait(lambda:s._run_state in ('running','error'));self.assertEqual(s._run_state,'running',s._message)
                self.assertTrue(s.pause());self.wait(lambda:s._run_state=='paused' and s._save_state=='saved')
                old_pid=s._process.pid
                menu_prepare(s,'Memoria','qualifica');target=s._settings.draft['driver']
                self.assertTrue(s._settings.apply('start'));self.assertTrue(s._closing)
                self.wait(lambda:s._run_state in ('running','error'))
                self.assertEqual(s._run_state,'running',s._message)
                self.assertEqual(s._selected,target);self.assertNotEqual(s._process.pid,old_pid)
                self.assertTrue(s.pause());self.wait(lambda:s._run_state=='paused')
                self.assertTrue(s.setMode('impara_infinito'))
                self.wait(lambda:s._process is None)
                self.assertEqual(s._mode,'impara_infinito')
            finally:s.close()


if __name__=='__main__':unittest.main()
