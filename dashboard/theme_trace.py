"""Private, bounded theme diagnostic recorder (no Qt, I/O or hot-path JSON).

The byte budget is a conservative estimate of JSON payload, not Python heap or
GPU memory.  Timestamps observe Python callback entry; they do not claim the
instant a C++ signal was emitted.  Callers must guard ``enabled`` before building
metadata.  Trace IDs and correlation maps never change functional application
state.  Export only after the measured work has finished.
"""
from collections import OrderedDict
from contextlib import contextmanager
from functools import wraps
import json
import math
import threading
import time
import uuid

TRACE_VERSION = 1
OUTCOMES = frozenset(("coherentSubmission", "noVisualChange", "rejected",
                      "superseded", "cancelled", "failed", "timeout",
                      "recoveryFallback", "unobservedFrame"))
_SENSITIVE_KEYS = frozenset(("title", "body", "text", "payload", "tokens",
                            "resolvedtokens", "preferences", "password",
                            "secret", "credentials", "configuration", "config"))


class TracePayloadError(ValueError):
    """A diagnostic field is unsafe, unbounded or not primitive."""


def _string_cost(value):
    # ensure_ascii=False JSON: UTF-8 plus escaping quotes, backslashes, controls.
    # Six bytes per ordinary ASCII character grossly overestimated real traces.
    extra = value.count('"') + value.count('\\')
    if not value.isprintable():
        extra += sum(5 for character in value if ord(character) < 32)
    return 2 + len(value.encode('utf-8')) + extra


def _string(value, label, maximum=256):
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise TracePayloadError(f"{label} must be a nonempty string of at most {maximum} characters")
    return value


def _primitive(value):
    if value is None or type(value) in (bool, int):
        if type(value) is int and value.bit_length() > 64:
            raise TracePayloadError("integer exceeds 64 bits")
        return value, 32
    if type(value) is float and math.isfinite(value):
        return value, 32
    if isinstance(value, str) and len(value) <= 256:
        return value, _string_cost(value)
    if type(value) in (list, tuple) and len(value) <= 64:
        values, size = [], 2
        for item in value:
            if type(item) in (list, tuple, dict):
                raise TracePayloadError("metadata lists must contain only scalars")
            frozen, cost = _primitive(item)
            values.append(frozen)
            size += cost + 1
        return tuple(values), size
    raise TracePayloadError("metadata must contain bounded primitive values; no objects or snapshots")


def _metadata(values):
    if len(values) > 32:
        raise TracePayloadError("at most 32 metadata fields are permitted")
    result, size = {}, 2
    for key, value in values.items():
        _string(key, "metadata key", 64)
        if key.lower().replace("_", "") in _SENSITIVE_KEYS:
            raise TracePayloadError(f"sensitive diagnostic field is forbidden: {key}")
        frozen, cost = _primitive(value)
        result[key] = frozen
        size += _string_cost(key) + cost + 4
    return result, size


def _json_copy(value):
    if isinstance(value, dict):
        return {key: _json_copy(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_copy(item) for item in value]
    return value


def _recording_cost(kind):
    """Observe bookkeeping cost with the real performance clock, never span work."""
    def decorate(function):
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            if not self.enabled:
                return function(self, *args, **kwargs)
            started = time.perf_counter_ns()
            request = self.current_request
            if kind == 'record':
                request = kwargs.get('request_id', args[1] if len(args) > 1 else None) or request
            elif kind == 'end':
                request = args[0] if args else kwargs.get('request_id')
            elif kind == 'bind':
                request = args[2] if len(args) > 2 else kwargs.get('request_id')
            try:
                result = function(self, *args, **kwargs)
                if kind == 'begin':
                    request = result
                return result
            finally:
                self._add_recording_cost(request, started)
        return wrapped
    return decorate


class TraceRecorder:
    """A recorder owned by the app/harness, disabled in ordinary operation.

    Event order and timestamp assignment are serialized by one lock.  Terminal
    outcomes survive event-buffer overflow, but the report is then incomplete.
    ``begin_request`` returns None when disabled or the bounded request budget is
    exhausted.  It never silently evicts a request or an event. Correlation maps
    retain old IDs, with bounded, explicitly counted eviction; they never infer
    a request from the latest operation.
    """
    def __init__(self, enabled=True, clock=time.perf_counter_ns, max_events=16384,
                 max_payload_bytes=8 * 1024 * 1024, max_open_requests=16):
        if type(enabled) is not bool:
            raise ValueError("enabled must be bool")
        for name, value in (("max_events", max_events), ("max_payload_bytes", max_payload_bytes),
                            ("max_open_requests", max_open_requests)):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self._enabled = enabled
        self._clock = clock
        self._lock = threading.RLock()
        self._local = threading.local()
        self._max_events = max_events
        self._max_payload = max_payload_bytes
        self._max_open = max_open_requests
        self._events = []
        self._strings = {}  # bounded, recorder-local sharing; no global intern leak
        self._metadata_keys = {}  # validated keys and serialized cost, <=256 entries
        self._event_costs = {}  # event name cost, <=256 entries
        self._requests = OrderedDict()
        self._generations = OrderedDict()
        self._revisions = OrderedDict()
        self._sequence = 0
        self._request_serial = 0
        self._span_serial = 0
        self._open = 0
        self._bytes = 0
        self._summary_bytes = 0
        self._recording_cost_unattributed = 0
        self._dropped = 0
        self._request_drops = 0
        self._duplicate_terminals = 0
        self._unknown_terminals = 0
        self._correlation_evictions = 0
        self._correlation_conflicts = 0
        self._clock_regressions = 0
        self._last_timestamp = 0
        self.session_id = uuid.uuid4().hex if enabled else None
        self._base = clock() if enabled else None

    def _add_recording_cost(self, request_id, started):
        with self._lock:
            elapsed = time.perf_counter_ns() - started
            if request_id in self._requests:
                self._requests[request_id]['recordingCostNs'] += elapsed
            else:
                self._recording_cost_unattributed += elapsed

    @property
    def enabled(self):
        return self._enabled

    @property
    def clock_origin_ns(self):
        """Exact process perf-counter origin; custom clocks cannot correlate Qt frames."""
        return self._base if self._clock is time.perf_counter_ns else None

    @property
    def current_request(self):
        return getattr(self._local, "request_id", None) if self.enabled else None

    def _timestamp_locked(self):
        timestamp = self._clock() - self._base
        if timestamp < self._last_timestamp:
            self._clock_regressions += 1
            # Keep original observed time, and invalidate the report explicitly.
        self._last_timestamp = timestamp
        return timestamp

    @_recording_cost("clock")
    def timestamp_ns(self):
        """Sample the same session-offset clock, including on the render thread."""
        if not self.enabled:
            return None
        with self._lock:
            return self._timestamp_locked()

    @contextmanager
    def scope(self, request_id):
        if not self.enabled:
            yield
            return
        previous = self.current_request
        self._local.request_id = request_id
        try:
            yield
        finally:
            self._local.request_id = previous

    def _resolve_request(self, request_id):
        return self.current_request if request_id is None else request_id

    def _append_locked(self, event, request_id, metadata, cost, timestamp=None):
        timestamp = self._timestamp_locked() if timestamp is None else timestamp
        self._sequence += 1
        sequence = self._sequence
        event_cost = self._event_costs.get(event)
        if event_cost is None:
            event_cost = _string_cost(event)
            if len(self._event_costs) < 256:
                self._event_costs[event] = event_cost
        cost += 256 + event_cost
        if len(self._events) >= self._max_events or self._bytes + self._summary_bytes + cost > self._max_payload:
            self._dropped += 1
            if request_id in self._requests:
                self._requests[request_id]["recordsDropped"] += 1
            return timestamp, None
        if isinstance(metadata, tuple):
            flat = metadata
        else:
            flat = []
            for key, value in metadata.items():
                flat.extend((self._share_string(key), self._share_string(value)))
        # Compact immutable storage. Dicts and JSON are constructed at export,
        # outside the measured work, while retaining every accepted raw record.
        self._events.append((sequence, timestamp, threading.get_ident(),
                             self._share_string(event), self._share_string(request_id), tuple(flat)))
        self._bytes += cost
        return timestamp, sequence

    def _share_string(self, value):
        if not isinstance(value, str):
            return value
        existing = self._strings.get(value)
        if existing is not None:
            return existing
        if len(self._strings) < 1024:
            self._strings[value] = value
        return value

    def _key_info(self, key):
        info = self._metadata_keys.get(key) if isinstance(key, str) else None
        if info is None:
            _string(key, "metadata key", 64)
            if key.lower().replace("_", "") in _SENSITIVE_KEYS:
                raise TracePayloadError(f"sensitive diagnostic field is forbidden: {key}")
            info = (key, _string_cost(key) + 4)
            if len(self._metadata_keys) < 256:
                self._metadata_keys[key] = info
        return info

    def _record_fields(self, values):
        # Single traversal: validation remains identical to _metadata, while
        # avoiding a transient dictionary and a second per-field sharing pass.
        if len(values) > 32:
            raise TracePayloadError("at most 32 metadata fields are permitted")
        flat, size = [], 2
        for key, value in values.items():
            canonical_key, key_cost = self._key_info(key)
            frozen, value_cost = _primitive(value)
            flat.extend((canonical_key, self._share_string(frozen)))
            size += key_cost + value_cost
        return tuple(flat), size

    @_recording_cost("record")
    def record(self, event, request_id=None, **metadata):
        """Append one record; return its sequence, or None if disabled/dropped."""
        if not self.enabled:
            return None
        _string(event, "event", 96)
        request_id = self._resolve_request(request_id)
        if request_id is not None:
            _string(request_id, "request ID", 96)
        with self._lock:
            copied, cost = self._record_fields(metadata)
            return self._append_locked(event, request_id, copied, cost)[1]

    @_recording_cost("begin")
    def begin_request(self, operation, origin="programmatic", **metadata):
        if not self.enabled:
            return None
        _string(operation, "operation", 96)
        _string(origin, "origin", 64)
        copied, cost = _metadata(metadata)
        with self._lock:
            # Total summaries are also bounded, not only simultaneously open ones.
            summary_cost = cost + 768
            if (self._open >= self._max_open or len(self._requests) >= self._max_events
                    or self._bytes + self._summary_bytes + summary_cost > self._max_payload):
                self._request_drops += 1
                return None
            self._summary_bytes += summary_cost
            self._request_serial += 1
            request_id = f"{self.session_id}:{self._request_serial}"
            timestamp = self._timestamp_locked()
            self._requests[request_id] = {"requestId": request_id, "operation": operation,
                "origin": origin, "startedNs": timestamp, "endedNs": None,
                "outcome": None, "metadata": copied, "terminalMetadata": None,
                "recordsDropped": 0, "recordingCostNs": 0}
            self._open += 1
            self._append_locked("request.begin", request_id,
                                {"operation": operation, "origin": origin, **copied}, cost + 512, timestamp)
            return request_id

    @_recording_cost("end")
    def end_request(self, request_id, outcome, **metadata):
        if not self.enabled:
            return False
        if outcome not in OUTCOMES:
            raise TracePayloadError(f"unknown request outcome: {outcome}")
        copied, cost = _metadata(metadata)
        with self._lock:
            request = self._requests.get(request_id)
            if request is None:
                self._unknown_terminals += 1
                return False
            if request["outcome"] is not None:
                self._duplicate_terminals += 1
                return False
            timestamp = self._timestamp_locked()
            request["endedNs"] = timestamp
            request["outcome"] = outcome
            if self._bytes + self._summary_bytes + cost + 128 <= self._max_payload:
                request["terminalMetadata"] = copied
                self._summary_bytes += cost + 128
            else:
                request["recordsDropped"] += 1
                self._dropped += 1
            self._open -= 1
            self._append_locked("request.end", request_id,
                                {"outcome": outcome, **copied}, cost + 256, timestamp)
            return True

    @contextmanager
    def span(self, event, request_id=None, **metadata):
        if not self.enabled:
            yield
            return
        recording_started = time.perf_counter_ns()
        _string(event, "span event", 90)
        copied, cost = _metadata(metadata)
        request_id = self._resolve_request(request_id)
        if request_id is not None:
            _string(request_id, "request ID", 96)
        stack = getattr(self._local, "spans", ())
        with self._lock:
            self._span_serial += 1
            span_id = self._span_serial
            parent = stack[-1] if stack else None
            started, _ = self._append_locked(event + ".begin", request_id,
                {**copied, "spanId": span_id, "parentSpanId": parent}, cost + 128)
        self._local.spans = (*stack, span_id)
        self._add_recording_cost(request_id, recording_started)
        failure = None
        try:
            yield
        except BaseException as error:
            failure = type(error).__name__
            raise
        finally:
            recording_started = time.perf_counter_ns()
            self._local.spans = stack
            with self._lock:
                ended = self._timestamp_locked()
                self._append_locked(event + ".end", request_id,
                    {"spanId": span_id, "parentSpanId": parent,
                     "durationNs": ended - started, "failed": failure is not None,
                     "errorType": failure}, 256, ended)
            self._add_recording_cost(request_id, recording_started)

    @_recording_cost("bind")
    def _bind(self, mapping, key, request_id):
        if not self.enabled:
            return False
        if type(key) not in (str, int) or (isinstance(key, str) and len(key) > 128):
            raise TracePayloadError("correlation key must be a bounded string or integer")
        if type(key) is int and key.bit_length() > 64:
            raise TracePayloadError("correlation key exceeds 64 bits")
        with self._lock:
            if request_id not in self._requests:
                return False
            if key in mapping:
                if mapping[key] != request_id:
                    self._correlation_conflicts += 1
                    return False
                return True
            if len(mapping) >= self._max_events:
                mapping.popitem(last=False)
                self._correlation_evictions += 1
            mapping[key] = request_id
            return True

    def bind_generation(self, generation, request_id):
        return self._bind(self._generations, generation, request_id)

    def bind_revision(self, revision, request_id):
        return self._bind(self._revisions, revision, request_id)

    def _lookup(self, mapping, key):
        if not self.enabled:
            return None
        with self._lock:
            return mapping.get(key)

    def request_for_generation(self, generation):
        return self._lookup(self._generations, generation)

    def request_for_revision(self, revision):
        return self._lookup(self._revisions, revision)

    def snapshot(self):
        """Copy a report outside measurement. This method performs no file I/O."""
        with self._lock:
            requests = [dict(request) for request in self._requests.values()]
            events = [{'sequence':sequence,'timestampNs':timestamp,'thread':thread,
                       'event':event,'requestId':request,'metadata':dict(zip(fields[::2],fields[1::2]))}
                      for sequence,timestamp,thread,event,request,fields in self._events]
            stats = {"recordsDropped": self._dropped, "requestsDropped": self._request_drops,
                     "openRequests": self._open, "duplicateTerminals": self._duplicate_terminals,
                     "unknownTerminals": self._unknown_terminals,
                     "correlationEvictions": self._correlation_evictions,
                     "correlationConflicts": self._correlation_conflicts,
                     "clockRegressions": self._clock_regressions,
                     "estimatedPayloadBytes": self._bytes + self._summary_bytes}
            recording_costs = {row["requestId"]: row["recordingCostNs"] for row in requests}
            unattributed_cost = self._recording_cost_unattributed
            maps = {"generations": list(self._generations.items()),
                    "revisions": list(self._revisions.items())}
        reasons = []
        for key in ("recordsDropped", "requestsDropped", "openRequests", "correlationEvictions",
                    "correlationConflicts", "clockRegressions"):
            if stats[key]:
                reasons.append(key)
        for request in requests:
            request["incomplete"] = bool(request["recordsDropped"] or request["outcome"] is None
                                         or stats["clockRegressions"])
        return _json_copy({"traceVersion": TRACE_VERSION, "enabled": self.enabled,
            "sessionId": self.session_id, "clock": ("perf_counter_ns/sessionOffset" if self._clock is time.perf_counter_ns
                      else "injectedMonotonicNanoseconds/sessionOffset"),
            "timestampQuality": "PythonCallbackEntryMayWaitForGIL",
            "limits": {"maxEvents": self._max_events, "maxPayloadBytes": self._max_payload,
                       "maxOpenRequests": self._max_open, "maxRequestSummaries": self._max_events},
            "payloadBudgetMeasures": "conservativeSerializedEstimateNotPythonHeap",
            "complete": self.enabled and not reasons, "incompleteReasons": reasons,
            "recordingCostNsByRequest": recording_costs,
            "recordingCostNsUnattributed": unattributed_cost,
            "recordingCostMethod": "perf_counter_ns/bookkeepingOnly/excludesSpanApplicationWork",
            "statistics": stats, "requests": requests, "events": events, "correlations": maps})

    def export(self, *, indent=2):
        """Serialize a snapshot after recording; caller owns publication/I/O."""
        return json.dumps(self.snapshot(), ensure_ascii=False, allow_nan=False, indent=indent)
