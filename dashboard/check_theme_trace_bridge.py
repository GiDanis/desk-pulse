"""Meaningful bridge correlation/lifecycle tests without providers or user state."""
import unittest
import time
from types import SimpleNamespace
from pathlib import Path
from PySide6.QtCore import QCoreApplication
from theme_trace_bridge import ThemeTraceBridge


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.trace = ThemeTraceBridge()
        self.service = SimpleNamespace(_revision=1, _candidate=None, catalog=SimpleNamespace(root=Path('/tmp'),presentations={}),
            _snapshot={'revision': 1, 'tokens': {'surface': '#000000'}})
        self.trace.bind_service(self.service)

    def tearDown(self):
        self.trace.finish()

    def change(self, name='selectDraft'):
        with self.trace.operation(name) as request:
            self.service._revision += 1
            self.service._snapshot['tokens']['surface'] = '#ffffff'
            self.trace.published(self.service._revision)
        return request

    def test_no_visual_change_does_not_wait_or_force_frame(self):
        with self.trace.operation('setToken') as request:
            self.service._revision += 1
            self.trace.published(self.service._revision)
        row = self.trace.report()['requests'][0]
        self.assertEqual(row['outcome'], 'noVisualChange')
        self.assertFalse(self.trace._pending)
        self.assertIsNone(self.trace._tracker)

    def test_immutable_frame_keeps_original_request_after_new_publish(self):
        first = self.change()
        with self.trace.operation('setToken') as second:
            self.service._snapshot['tokens']['surface'] = '#123456'
            self.service._revision += 1
            self.trace.published(self.service._revision)
        self.trace._captured({'requestId': first, 'outcome': 'coherentSubmission',
            'revision': 2, 'frameSerial': 7, 'submittedNs': time.perf_counter_ns(),
            'motionSettled': False, 'strictCoherence': True,
            'snapshot': {'participants': []}})
        rows = {r['requestId']: r for r in self.trace.report()['requests']}
        self.assertEqual(rows[first]['outcome'], 'coherentSubmission')
        self.assertIsNone(rows[second]['outcome'])
        self.assertEqual(rows[first]['terminalMetadata']['revision'], 2)

    def test_terminal_is_once_and_ambiguous_frame_cannot_ack(self):
        request = self.change()
        self.trace._captured({'requestId': request, 'outcome': 'unobservedFrame'})
        self.assertIn(request, self.trace._pending)
        self.assertTrue(self.trace.finished(request, 'cancelled'))
        self.assertFalse(self.trace.finished(request, 'failed'))
        self.assertEqual(self.trace.report()['statistics']['duplicateTerminals'], 0)

    def test_generation_restart_preserves_identity_and_supersession(self):
        with self.trace.operation('selectDraft') as request:
            self.service._candidate = {'generation': 1}
            self.trace.candidate(1)
        with self.trace.correlate_generation(1):
            self.trace.cleared(1)
            self.trace.candidate(2)
        self.assertEqual(self.trace.recorder.request_for_generation(2), request)
        with self.trace.operation('cancel'):
            self.trace.cleared(2, 'cancelled')
            self.service._candidate = None
        self.assertEqual(self.trace.report()['requests'][0]['outcome'], 'cancelled')

    def test_apply_waits_for_worker_result_and_input_has_parent(self):
        identity = self.trace.beginInput('qtKey')
        with self.trace.operation('apply') as request:
            pass
        self.trace.endInput(identity)
        row = self.trace.report()['requests'][0]
        self.assertEqual(row['origin'], 'qtKey')
        self.assertEqual(row['metadata']['inputParent'], identity)
        self.assertIsNone(row['outcome'])
        self.trace.finished(request, 'noVisualChange', persisted=True)
        self.assertTrue(self.trace.report()['requests'][0]['terminalMetadata']['persisted'])

    def test_noop_never_receives_fake_motion_latency(self):
        with self.trace.operation('setToken') as request:
            self.trace.published(1)
        self.trace._captured({'requestId':request,'outcome':'coherentSubmission',
            'motionSettled':True,'strictCoherence':True,'submittedNs':time.perf_counter_ns(),
            'frameSerial':1,'revision':1,'snapshot':{'participants':[]}})
        self.assertEqual(self.trace.report()['frameSummaries'],[])

    def test_event_response_uses_ticket_identity_even_during_candidate(self):
        self.trace.traceEvent('notification.urgent', {'eventId':'e','eventRevision':'r','rank':3})
        result={'outcome':'unobservedFrame','reason':'candidatePending','frameSerial':1,
                'submittedNs':time.perf_counter_ns(),'snapshot':{'participants':[
                    {'surfaceId':'alerts.urgent','eventId':'e','eventRevision':'r','rank':3,
                     'exposed':True,'ready':True,'geometryValid':True,'opacity':1,
                     'rendererIdentity':'app.urgentFallback','role':'fallback'}]}}
        self.trace._captured(result);self.trace._captured(result)
        rows=self.trace.report()['notificationFrames']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['responseKind'],'fallback')

    def test_publish_supersedes_only_requests_without_latched_or_queued_frame(self):
        latched=set()
        self.trace._tracker=SimpleNamespace(invalidate=lambda reason:None,detach=lambda:None,
            has_pending_submission=lambda request:request in latched)
        first=self.change()
        latched.add(first)
        with self.trace.operation('setToken') as second:
            self.service._revision+=1;self.service._snapshot['tokens']['surface']='#222222'
            self.trace.published(self.service._revision)
        self.assertIn(first,self.trace._pending)
        latched.clear()
        self.trace._captured({'outcome':'unobservedFrame','reason':'noGuiTicket'})
        rows={r['requestId']:r for r in self.trace.report()['requests']}
        self.assertEqual(rows[first]['outcome'],'superseded')
        self.assertIsNone(rows[second]['outcome'])


if __name__ == '__main__':
    unittest.main()
