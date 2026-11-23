"""Liveness stays atomic without durable I/O; activation writes stay durable."""
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from theme_bundle import atomic_json
from theme_lifecycle import LifecycleManager


class HeartbeatChecks(unittest.TestCase):
    def test_heartbeat_never_fsyncs_the_gui_thread(self):
        with tempfile.TemporaryDirectory() as root:
            life=LifecycleManager(root)
            try:
                with patch('theme_bundle.os.fsync',side_effect=AssertionError('Liveness must not fsync')):
                    record=life.heartbeat(ready=True,context={'surfaceId':'game.menu'})
                self.assertEqual(json.loads(life.health_path.read_text()),record)
                self.assertTrue(record['ready']);self.assertTrue(record['processStart'])
                self.assertEqual(record['context']['surfaceId'],'game.menu')
            finally:life.health_path.unlink(missing_ok=True)

    def test_durable_settings_still_sync_file_and_directory(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('theme_bundle.os.fsync') as sync:
                atomic_json(Path(root)/'journal.json',{'generation':7})
            self.assertEqual(sync.call_count,2)
            self.assertEqual(json.loads((Path(root)/'journal.json').read_text()),{'generation':7})


if __name__=='__main__':unittest.main()
