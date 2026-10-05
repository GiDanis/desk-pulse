"""Storage optimizations preserve raw records, privacy and frozen ownership."""
import json
import sys
import threading
import unittest
from theme_trace import TraceRecorder, TracePayloadError, _metadata
from theme_frame_trace import _freeze, _thaw


class CompactTraceTests(unittest.TestCase):
    def test_flat_record_metadata_and_payload_cost_match_reference(self):
        recorder = TraceRecorder()
        fields = {'host': 'page.live', 'revision': 5, 'opacity': 1.0, 'active': False,
                  'missing': None, 'ids': ['small', 'large'], 'unicode': 'é\n"\\'}
        copied, expected_cost = _metadata(fields)
        with recorder._lock:
            flat, cost = recorder._record_fields(fields)
        self.assertEqual(cost, expected_cost)
        self.assertEqual(dict(zip(flat[::2], flat[1::2])), copied)
        recorder.record('host.ready', **fields)
        self.assertEqual(recorder.snapshot()['events'][0]['metadata'], json.loads(json.dumps(fields)))

    def test_bounded_key_cache_never_bypasses_sensitive_validation(self):
        recorder = TraceRecorder(max_events=1000)
        for index in range(400):
            recorder.record('event.' + str(index), **{'field' + str(index): index})
        self.assertLessEqual(len(recorder._metadata_keys), 256)
        self.assertLessEqual(len(recorder._event_costs), 256)
        for name in ('tokens', 'token_s', 'password', 'secret', 'body', 'resolved_tokens'):
            with self.subTest(name=name), self.assertRaises(TracePayloadError):
                recorder.record('unsafe', **{name: 'not recorded'})
        self.assertEqual(len(recorder.snapshot()['events']), 400)

    def test_threaded_metadata_cache_is_serialized(self):
        recorder = TraceRecorder(max_events=5000)
        threads = [threading.Thread(target=lambda: [recorder.record('host.ready', host='same', revision=i) for i in range(200)]) for _ in range(4)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        events = recorder.snapshot()['events']
        self.assertEqual(len(events), 800)
        self.assertEqual([event['sequence'] for event in events], list(range(1, 801)))

    def test_frozen_snapshot_string_sharing_retains_immutable_values(self):
        pool = {}
        first_key = (' ' + 'instanceId').strip()
        second_key = ('  ' + 'instanceId').strip()
        first = _freeze({first_key: 'page.live', 'revision': 1}, strings=pool)
        second = _freeze({second_key: 'page.live', 'revision': 2}, strings=pool)
        a, b = dict(zip(first[1][::2], first[1][1::2])), dict(zip(second[1][::2], second[1][1::2]))
        self.assertIs(next(key for key in first[1][::2] if key == 'instanceId'), next(key for key in second[1][::2] if key == 'instanceId'))
        self.assertIs(a['instanceId'], b['instanceId'])
        self.assertEqual(_thaw(first)['revision'], 1)
        self.assertEqual(_thaw(second)['revision'], 2)
        for index in range(3000):
            _freeze({'id': str(index)}, strings=pool)
        self.assertLessEqual(len(pool), 2048)


if __name__ == '__main__':
    unittest.main()
