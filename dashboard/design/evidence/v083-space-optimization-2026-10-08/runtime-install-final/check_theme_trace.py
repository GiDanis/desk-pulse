"""Tests for the private recorder; no Qt, providers, files or service state."""
import json
import importlib.util
import os
import tempfile
import time
import threading
import unittest
from unittest.mock import patch

from theme_trace import OUTCOMES, TracePayloadError, TraceRecorder


class Clock:
    def __init__(self):
        self.value = 1000
    def __call__(self):
        self.value += 10
        return self.value


class ThemeTraceTests(unittest.TestCase):
    def recorder(self, **options):
        return TraceRecorder(clock=Clock(), **options)

    def test_disabled_does_not_call_clock_or_validate_payload(self):
        def forbidden():
            raise AssertionError("disabled recorder called clock")
        trace = TraceRecorder(enabled=False, clock=forbidden)
        self.assertIsNone(trace.begin_request(object(), config=object()))
        self.assertIsNone(trace.record(object(), text=object()))
        self.assertIsNone(trace.timestamp_ns())
        with trace.scope("ignored"), trace.span(object(), payload=object()):
            self.assertIsNone(trace.current_request)
        self.assertFalse(trace.end_request("ignored", "invalid", secret=object()))
        self.assertFalse(trace.bind_generation([], "ignored"))
        self.assertEqual(trace.snapshot()["events"], [])
        self.assertFalse(trace.snapshot()["complete"])

    def test_monotonic_clock_order_and_distinct_terminal_outcome(self):
        trace = self.recorder()
        request = trace.begin_request("selectDraft", origin="Qt", fromRevision=0)
        trace.record("candidate", request, serviceGeneration=1)
        self.assertTrue(trace.end_request(request, "rejected", reason="contrast"))
        report = trace.snapshot()
        self.assertTrue(report["complete"])
        self.assertEqual([event["sequence"] for event in report["events"]], [1, 2, 3])
        self.assertEqual([event["timestampNs"] for event in report["events"]], [10, 20, 30])
        self.assertEqual(report["requests"][0]["outcome"], "rejected")
        self.assertEqual(report["requests"][0]["startedNs"], 10)
        self.assertEqual(report["requests"][0]["endedNs"], 30)
        self.assertIn("GIL", report["timestampQuality"])

    def test_terminal_exactly_once_and_unknown_never_becomes_current(self):
        trace = self.recorder()
        request = trace.begin_request("preview")
        self.assertTrue(trace.end_request(request, "cancelled"))
        self.assertFalse(trace.end_request(request, "coherentSubmission"))
        self.assertFalse(trace.end_request("old-unknown", "timeout"))
        report = trace.snapshot()
        self.assertEqual(report["requests"][0]["outcome"], "cancelled")
        self.assertEqual(report["statistics"]["duplicateTerminals"], 1)
        self.assertEqual(report["statistics"]["unknownTerminals"], 1)
        with self.assertRaises(TracePayloadError):
            trace.end_request(request, "successful-ish")

    def test_each_defined_outcome_is_preserved(self):
        trace = self.recorder(max_open_requests=1)
        for outcome in OUTCOMES:
            request = trace.begin_request("preview")
            self.assertTrue(trace.end_request(request, outcome))
        self.assertEqual({row["outcome"] for row in trace.snapshot()["requests"]}, OUTCOMES)

    def test_nested_scopes_and_spans_restore_parent_on_exception(self):
        trace = self.recorder()
        first = trace.begin_request("first")
        second = trace.begin_request("second")
        with trace.scope(first):
            with trace.span("resolve"):
                with trace.scope(second):
                    with self.assertRaises(RuntimeError), trace.span("validate"):
                        trace.record("cache.hit", available=False)
                        raise RuntimeError("must not export exception text")
                self.assertEqual(trace.current_request, first)
        self.assertIsNone(trace.current_request)
        trace.end_request(first, "failed")
        trace.end_request(second, "rejected")
        events = trace.snapshot()["events"]
        starts = [event for event in events if event["event"].endswith(".begin") and event["event"] != "request.begin"]
        self.assertIsNone(starts[0]["metadata"]["parentSpanId"])
        self.assertEqual(starts[1]["metadata"]["parentSpanId"], starts[0]["metadata"]["spanId"])
        failure = next(event for event in events if event["event"] == "validate.end")
        self.assertEqual(failure["requestId"], second)
        self.assertEqual(failure["metadata"]["errorType"], "RuntimeError")
        self.assertTrue(failure["metadata"]["failed"])
        self.assertNotIn("must not export", trace.export())

    def test_thread_local_context_and_total_record_order(self):
        trace = self.recorder()
        requests = [trace.begin_request("preview") for _ in range(4)]
        barrier = threading.Barrier(4)
        errors = []
        def producer(request):
            try:
                with trace.scope(request):
                    barrier.wait(timeout=5)
                    for index in range(100):
                        trace.record("worker.phase", index=index)
                    trace.end_request(request, "noVisualChange")
            except BaseException as error:
                errors.append(error)
        workers = [threading.Thread(target=producer, args=(request,)) for request in requests]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=10)
            self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertIsNone(trace.current_request)
        events = trace.snapshot()["events"]
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
        times = [event["timestampNs"] for event in events]
        self.assertEqual(times, sorted(times))
        for request in requests:
            self.assertEqual(sum(event["event"] == "worker.phase" and event["requestId"] == request for event in events), 100)

    def test_same_request_terminal_race_has_one_winner(self):
        trace = self.recorder()
        request = trace.begin_request("preview")
        barrier = threading.Barrier(8)
        results = []
        def finish():
            barrier.wait(timeout=5)
            results.append(trace.end_request(request, "cancelled"))
        workers = [threading.Thread(target=finish) for _ in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=10)
            self.assertFalse(worker.is_alive())
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 7)
        report = trace.snapshot()
        self.assertEqual(report["statistics"]["openRequests"], 0)
        self.assertEqual(sum(event["event"] == "request.end" for event in report["events"]), 1)

    def test_hot_path_never_serializes_json(self):
        trace = self.recorder()
        with patch("theme_trace.json.dumps", side_effect=AssertionError("hot JSON serialization")):
            request = trace.begin_request("preview", fromRevision=3)
            with trace.scope(request), trace.span("resolve"):
                trace.record("cache.hit", revision=4)
            trace.end_request(request, "coherentSubmission")
        self.assertTrue(trace.snapshot()["complete"])

    def test_stale_generation_revision_never_inherits_latest_request(self):
        trace = self.recorder()
        old = trace.begin_request("preview")
        trace.bind_generation(1, old)
        trace.bind_revision(4, old)
        trace.end_request(old, "superseded")
        new = trace.begin_request("preview")
        trace.bind_generation(2, new)
        self.assertFalse(trace.bind_generation(1, new))
        self.assertFalse(trace.bind_revision(4, new))
        self.assertEqual(trace.request_for_generation(1), old)
        self.assertEqual(trace.request_for_revision(4), old)
        self.assertIsNone(trace.request_for_generation(999))
        self.assertFalse(trace.bind_generation(3, "unknown"))
        trace.end_request(new, "coherentSubmission")
        self.assertIn("correlationConflicts", trace.snapshot()["incompleteReasons"])

    def test_event_overflow_does_not_replace_slow_records_or_lose_terminal(self):
        trace = self.recorder(max_events=2)
        request = trace.begin_request("preview")
        trace.record("slow.prepare", request, durationNs=100000)
        trace.record("late.frame", request)
        self.assertTrue(trace.end_request(request, "coherentSubmission"))
        report = trace.snapshot()
        self.assertEqual([event["event"] for event in report["events"]], ["request.begin", "slow.prepare"])
        self.assertEqual(report["statistics"]["recordsDropped"], 2)
        self.assertEqual(report["requests"][0]["outcome"], "coherentSubmission")
        self.assertTrue(report["requests"][0]["incomplete"])
        self.assertFalse(report["complete"])

    def test_payload_budget_bounds_events_and_request_summaries(self):
        trace = self.recorder(max_payload_bytes=1800)
        request = trace.begin_request("preview")
        self.assertIsNotNone(request)
        trace.record("large", request, ids=["x" * 256] * 64)
        trace.end_request(request, "unobservedFrame", reason="x" * 256)
        report = trace.snapshot()
        self.assertLessEqual(report["statistics"]["estimatedPayloadBytes"], 1800)
        self.assertGreater(report["statistics"]["recordsDropped"], 0)
        self.assertEqual(report["requests"][0]["outcome"], "unobservedFrame")
        self.assertTrue(report["requests"][0]["incomplete"])
        tiny = self.recorder(max_payload_bytes=1)
        self.assertIsNone(tiny.begin_request("preview"))
        self.assertEqual(tiny.snapshot()["statistics"]["requestsDropped"], 1)

    def test_open_request_and_total_summary_limits_are_explicit(self):
        trace = self.recorder(max_events=2, max_open_requests=1)
        first = trace.begin_request("preview")
        self.assertIsNone(trace.begin_request("preview"))
        self.assertIn("openRequests", trace.snapshot()["incompleteReasons"])
        trace.end_request(first, "cancelled")
        second = trace.begin_request("preview")
        trace.end_request(second, "cancelled")
        self.assertIsNone(trace.begin_request("preview"))
        self.assertEqual(len(trace.snapshot()["requests"]), 2)
        self.assertEqual(trace.snapshot()["statistics"]["requestsDropped"], 2)

    def test_correlation_maps_are_bounded_and_evictions_reported(self):
        trace = self.recorder(max_events=2)
        request = trace.begin_request("preview")
        for generation in range(3):
            self.assertTrue(trace.bind_generation(generation, request))
        self.assertIsNone(trace.request_for_generation(0))
        self.assertEqual(trace.request_for_generation(2), request)
        trace.end_request(request, "cancelled")
        self.assertEqual(trace.snapshot()["statistics"]["correlationEvictions"], 1)
        self.assertFalse(trace.snapshot()["complete"])

    def test_payload_is_primitive_private_and_immutable_after_record(self):
        trace = self.recorder()
        ids = ["one", "two"]
        trace.record("ack", ids=ids, available=False, value=0, missing=None)
        ids.append("three")
        exported = trace.snapshot()
        self.assertEqual(exported["events"][0]["metadata"]["ids"], ["one", "two"])
        exported["events"][0]["metadata"]["ids"].append("mutated report")
        self.assertEqual(trace.snapshot()["events"][0]["metadata"]["ids"], ["one", "two"])
        for unsafe in (object(), {}, [object()], float("inf"), float("nan"), 1 << 80, "x" * 257):
            with self.subTest(value=type(unsafe).__name__), self.assertRaises(TracePayloadError):
                trace.record("unsafe", value=unsafe)
        for key in ("title", "body", "resolved_tokens", "password", "preferences"):
            with self.subTest(key=key), self.assertRaises(TracePayloadError):
                trace.record("unsafe", **{key: "sensitive"})

    def test_clock_regression_invalidates_report_without_hiding_observation(self):
        values = iter((100, 120, 110, 130))
        trace = TraceRecorder(clock=lambda: next(values))
        request = trace.begin_request("preview")
        trace.record("frame", request)
        trace.end_request(request, "coherentSubmission")
        report = trace.snapshot()
        self.assertEqual([event["timestampNs"] for event in report["events"]], [20, 10, 30])
        self.assertEqual(report["statistics"]["clockRegressions"], 1)
        self.assertFalse(report["complete"])
        self.assertTrue(report["requests"][0]["incomplete"])

    def test_export_is_json_compatible_and_exposes_open_requests(self):
        trace = self.recorder()
        trace.begin_request("apply", configHash="abc")
        parsed = json.loads(trace.export(indent=None))
        self.assertEqual(parsed, trace.snapshot())
        self.assertEqual(parsed["requests"][0]["outcome"], None)
        self.assertIn("openRequests", parsed["incompleteReasons"])
        self.assertFalse(parsed["complete"])

    def test_recording_cost_excludes_work_inside_application_span(self):
        cost_clock = Clock()
        with patch("theme_trace.time.perf_counter_ns", cost_clock):
            trace = self.recorder()
            request = trace.begin_request("preview")
            with trace.scope(request), trace.span("resolve"):
                cost_clock.value += 1000000000
            trace.end_request(request, "coherentSubmission")
        report = trace.snapshot()
        self.assertEqual(report["recordingCostNsByRequest"][request], 40)
        self.assertEqual(report["recordingCostNsUnattributed"], 0)
        self.assertIn("excludesSpanApplicationWork", report["recordingCostMethod"])

    def test_disabled_does_not_sample_recording_cost_clock(self):
        trace = TraceRecorder(enabled=False)
        with patch("theme_trace.time.perf_counter_ns", side_effect=AssertionError("disabled cost clock")):
            trace.begin_request("preview")
            trace.record("noop")
            with trace.span("noop"):
                pass
            trace.end_request(None, "rejected")
        self.assertEqual(trace.snapshot()["recordingCostNsUnattributed"], 0)

    def test_resolver_trace_keeps_snapshot_and_schema_contract_unchanged(self):
        from theme_core import ThemeCatalog, ThemeError
        baseline = ThemeCatalog().resolve("functional")
        trace = self.recorder()
        catalog = ThemeCatalog(trace=trace)
        request = trace.begin_request("resolve")
        with trace.scope(request):
            actual = catalog.resolve("functional")
            with self.assertRaises(ThemeError):
                catalog.resolve("missing.theme")
        trace.end_request(request, "rejected")
        self.assertEqual(actual, baseline)
        events = trace.snapshot()["events"]
        scoped = [row for row in events if row["requestId"] == request]
        self.assertTrue(any(row["event"] == "catalog.contrast.begin" for row in scoped))
        failure = [row for row in scoped if row["event"] == "catalog.resolve.end" and row["metadata"]["failed"]]
        self.assertEqual(len(failure), 1)
        self.assertEqual(failure[0]["metadata"]["errorType"], "ThemeError")

    def test_disabled_hook_never_calls_bridge_operation_or_span(self):
        from theme_trace_hooks import trace_operation, trace_span, trace_generation
        class DisabledBridge:
            recorder = TraceRecorder(enabled=False)
            def operation(self, name):
                raise AssertionError("disabled bridge operation")
            def correlate_generation(self, generation):
                raise AssertionError("disabled generation")
        class Subject:
            _trace = DisabledBridge()
            @trace_operation("mutate")
            @trace_span("validate")
            def mutate(self):
                return False
            @trace_generation
            def ack(self, generation):
                return generation
        subject = Subject()
        self.assertFalse(subject.mutate())
        self.assertEqual(subject.ack(7), 7)

    @unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt integration requires PySide6")
    def test_private_qt_bridge_staging_stale_callbacks_and_persistence(self):
        from PySide6.QtGui import QGuiApplication
        from theme_service import ThemeService
        from theme_trace_bridge import ThemeTraceBridge
        with tempfile.TemporaryDirectory(prefix="smartpc-private-trace-") as directory:
            with patch.dict(os.environ, XDG_CONFIG_HOME=directory, SMARTPC_THEME_STORE=directory + "/themes", QT_QPA_PLATFORM="offscreen"):
                app = QGuiApplication.instance() or QGuiApplication([])
                type(self)._qt_app = app
                trace = ThemeTraceBridge()
                service = ThemeService(trace=trace)
                service.setActiveContent("home.now")
                service.beginEdit()
                self.assertTrue(service.selectDraft("functional"))
                first_generation = service._candidate["generation"]
                request = trace.recorder.request_for_generation(first_generation)
                service.setPreparedContents(["alerts.banner.small"])
                next_generation = service._candidate["generation"]
                self.assertNotEqual(next_generation, first_generation)
                self.assertEqual(trace.recorder.request_for_generation(next_generation), request)
                service.reportCandidate(first_generation, "home.now", True, "late callback")
                self.assertEqual(service._candidate["generation"], next_generation)
                service.reportCandidate(next_generation, "home.now", False, "private failure text")
                row = next(row for row in trace.recorder.snapshot()["requests"] if row["requestId"] == request)
                self.assertEqual(row["outcome"], "failed")
                self.assertNotIn("private failure text", trace.recorder.export())
                self.assertFalse(service.setToken("unknown.token", 7))
                service.setActiveContent("")
                service.setPreparedContents([])
                self.assertTrue(service.setToken("shape.radiusCard", 0))
                self.assertTrue(service.preview())
                self.assertTrue(service.apply())
                deadline = time.monotonic() + 5
                while service.status == "saving" and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.002)
                self.assertEqual(service.status, "ready")
                rows = trace.recorder.snapshot()["requests"]
                saved = next(row for row in rows if row["operation"] == "apply")
                self.assertEqual(saved["outcome"], "noVisualChange")
                self.assertTrue(saved["terminalMetadata"]["persisted"])
                self.assertTrue(any(row["outcome"] == "rejected" for row in rows))
                trace.finish()
                self.assertEqual(trace.recorder.snapshot()["statistics"]["duplicateTerminals"], 0)
                self.assertEqual(service.resolvedAppearance["tokens"]["shape.radiusCard"], 0)
                service.deleteLater()
                trace.deleteLater()
                app.processEvents()

    def test_invalid_limits_rejected_and_enabled_readonly(self):
        for option in ("max_events", "max_payload_bytes", "max_open_requests"):
            for value in (0, -1, True, 1.5):
                with self.subTest(option=option, value=value), self.assertRaises(ValueError):
                    TraceRecorder(**{option: value})
        with self.assertRaises(AttributeError):
            self.recorder().enabled = False


if __name__ == "__main__":
    unittest.main()
