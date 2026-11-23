"""No-op clearing must not invalidate every dashboard provider binding."""
import tempfile
import unittest
from PySide6.QtCore import QCoreApplication
from fantacalcio import FantacalcioService


class ProviderInvalidationTests(unittest.TestCase):
    def test_clear_is_idempotent_and_still_stops_timer(self):
        _app = QCoreApplication.instance() or QCoreApplication([])
        with tempfile.TemporaryDirectory() as directory:
            service = FantacalcioService(directory, auto_refresh=False)
            changes = []
            service.changed.connect(lambda: changes.append(True))
            service.timer.start(60000)
            service.clear()
            self.assertFalse(service.timer.isActive())
            self.assertEqual(changes, [])
            service.match = {'canonicalMatchId': 'fixture'}
            service.key = 'fixture'
            service.error = 'fixture error'
            service.clear()
            self.assertEqual(len(changes), 1)
            self.assertEqual(service.match, {})
            self.assertEqual(service.key, '')
            self.assertEqual(service.error, '')
            service.clear()
            self.assertEqual(len(changes), 1)
            service.close()


if __name__ == '__main__': unittest.main()
