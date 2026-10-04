"""Private opt-in diagnostics. No public ThemeApi, provider or render ownership.

All QML reads happen on the GUI thread. Frames retain their original ticket;
later service state is never used to repair an ambiguous submission.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
import hashlib
from pathlib import Path
import time

from PySide6.QtCore import QObject, Property, QMetaObject, Q_RETURN_ARG, QTimer, Qt, Slot
from PySide6.QtQml import QJSValue
from theme_trace import TraceRecorder
from theme_frame_trace import ThemeFrameTracker


class ThemeTraceBridge(QObject):
    def __init__(self, parent=None, recorder=None):
        super().__init__(parent)
        self.recorder = recorder or TraceRecorder()
        self._service = None
        self._window = None
        self._tracker = None
        self._pending = {}
        self._timers = {}
        self._instance_serial = 0
        self._frames = []
        self._settled = set()
        self._completed = {}
        self._summaries_dropped = 0
        self._notification_inputs = {}
        self._notification_frames = []
        self._origin = 'programmatic'
        self._input_serial = 0
        self._input_stack = []
        self._clock_origin = self.recorder.clock_origin_ns
        if self.enabled and self._clock_origin is None:
            raise ValueError('Qt frame tracing requires the process perf_counter_ns clock')
        surfaces = json.loads(Path(__file__).with_name('theme-api').joinpath('surfaces.json').read_text())['surfaces']
        self._routes = {row['legacyRoute']: row['id'] for row in surfaces if row['legacyRoute']}
        manifest = Path(__file__).with_name('release-manifest.json')
        self._manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.exists() else None
        self._api_fingerprint = json.loads(Path(__file__).with_name('theme-api').joinpath('generated/api-metadata.json').read_text())['apiFingerprint']
        self._renderer_sources = {}

    @Property(bool, constant=True)
    def enabled(self):
        return self.recorder.enabled

    def bind_service(self, service):
        self._service = service
        for identifier, descriptor in service.catalog.presentations.items():
            path = service.catalog.root / descriptor['file']
            self._renderer_sources[identifier] = {'origin':'app','sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}

    @Slot(str, result=int)
    def beginInput(self, origin):
        self._input_serial += 1
        self._input_stack.append((self._input_serial, self._origin))
        self._origin = origin
        self.recorder.record('input.begin', inputParent=self._input_serial, origin=origin)
        return self._input_serial

    @Slot(int)
    def endInput(self, identity):
        self.recorder.record('input.end', inputParent=identity)
        if self._input_stack and self._input_stack[-1][0] == identity:
            _, self._origin = self._input_stack.pop()

    @Slot(str, str, result=str)
    def allocateInstance(self, surface, role):
        self._instance_serial += 1
        return f'{surface}:{role}:{self._instance_serial}'

    @Slot(str, result=str)
    def surfaceForRoute(self, route):
        return self._routes.get(route, route if route else 'shell.root')

    @Slot(int, result=str)
    def requestForRevision(self, revision):
        return self.recorder.request_for_revision(revision) or ''

    @Slot(str)
    def invalidate(self, reason):
        if self._tracker:
            self._tracker.invalidate(reason)

    @Slot(str, 'QVariantMap')
    def traceEvent(self, name, fields):
        # Only primitive identity/timing metadata is accepted by the recorder.
        # QML maps are copied on GUI, never shared with the render callback.
        self.invalidate(name)
        generation = fields.get('serviceGeneration')
        revision = fields.get('revision')
        request = (self.recorder.request_for_generation(generation) if generation else None)
        request = request or self.recorder.current_request or self.recorder.request_for_revision(revision)
        self.recorder.record(name, request_id=request, **fields)
        if name == 'motion.stopped' and fields.get('running') is False and self._tracker:
            if not self._tracker.refresh_gui_ticket():
                self._tracker.prove_motion_stopped_gui()
        if name in ('notification.urgent', 'notification.banner') and fields.get('eventId'):
            key = (fields['eventId'], fields.get('eventRevision', ''), fields.get('rank', 0))
            if key not in self._notification_inputs and len(self._notification_inputs) < 512:
                self._notification_inputs[key] = self.recorder.timestamp_ns()

    @contextmanager
    def operation(self, name):
        if self.recorder.current_request:
            yield self.recorder.current_request
            return
        service = self._service
        before = self._visual_state(service)
        request = self.recorder.begin_request(name, self._origin,
            fromRevision=service._revision if service else 0,
            inputParent=self._input_stack[-1][0] if self._input_stack else None)
        if not request:
            yield None
            return
        self._pending[request] = {'operation': name, 'before': before}
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda r=request: self.finished(r, 'timeout', reason='noCoherentSubmission'))
        self._timers[request] = timer
        timer.start(5000)
        self.invalidate('request.begin')
        try:
            with self.recorder.scope(request):
                yield request
        except BaseException as error:
            self.finished(request, 'failed', errorType=type(error).__name__)
            raise
        finally:
            if request in self._pending and name != 'apply' and service is not None:
                if not service._candidate and before == self._visual_state(service):
                    outcome = 'recoveryFallback' if self._pending[request].get('recovery') else 'noVisualChange'
                    self.finished(request, outcome, proof='equalResolvedAppearance')

    @staticmethod
    def _visual_state(service):
        if service is None:
            return None
        # Compare actual resolved appearance, excluding bookkeeping identities.
        result = deepcopy(service._snapshot)
        for key in ('revision', 'generation', 'requiredContents'):
            result.pop(key, None)
        return result

    @contextmanager
    def correlate_generation(self, generation):
        with self.recorder.scope(self.recorder.request_for_generation(generation)):
            yield

    def candidate(self, generation):
        request = self.recorder.current_request
        if request:
            self.recorder.bind_generation(generation, request)
        self.invalidate('candidate.created')
        self.recorder.record('candidate.created', generation=generation)

    def published(self, revision):
        request = self.recorder.current_request
        if request:
            self.recorder.bind_revision(revision, request)
            if request in self._pending:
                self._pending[request]['revision'] = revision
        for previous, state in list(self._pending.items()):
            if previous!=request and state.get('revision') is not None and state['operation']!='apply':
                state['supersededByRevision'] = revision
                if self._tracker and not self._tracker.has_pending_submission(previous):
                    self.finished(previous,'superseded',byRevision=revision)
        self.invalidate('appearance.published')
        snapshot = self._service._snapshot if self._service else {}
        self.recorder.record('appearance.published', revision=revision,
            themeId=snapshot.get('themeId'), themeVersion=snapshot.get('themeVersion'))

    def recovery(self):
        request = self.recorder.current_request
        if request in self._pending:
            self._pending[request]['recovery'] = True
        self.recorder.record('appearance.recoveryFallback', request_id=request)

    def cleared(self, generation, outcome='superseded'):
        request = self.recorder.request_for_generation(generation)
        if request and request != self.recorder.current_request:
            self.finished(request, outcome, generation=generation)
        self.invalidate('candidate.cleared')
        self.recorder.record('candidate.cleared', request_id=request, generation=generation, reason=outcome)

    def finished(self, request, outcome, **metadata):
        if request not in self._pending:
            return False
        self._pending.pop(request)
        self._completed[request] = outcome
        timer = self._timers.pop(request, None)
        if timer:
            timer.stop()
            timer.deleteLater()
        return self.recorder.end_request(request, outcome, **metadata)

    def attach(self, window):
        self._window = window
        self._tracker = ThemeFrameTracker(self)
        self._tracker.captured.connect(self._captured)
        self._tracker.attach(window, self._snapshot, self.recorder)

    @contextmanager
    def suspend_observation(self, reason):
        """Blocking GUI grabWindow can hold the GIL while awaiting render signals.

        Screenshots are outside request latency windows. Disconnect direct Python
        render callbacks for this explicit diagnostic gap, then resume passively.
        """
        if self._tracker:
            self._tracker.detach()
        self.recorder.record('observer.suspended', reason=reason)
        try:
            yield
        finally:
            if self._tracker:
                self._tracker.attach(self._window, self._snapshot, self.recorder)
            self.recorder.record('observer.resumed', reason=reason)

    def _snapshot(self):
        result = QMetaObject.invokeMethod(self._window, 'themeTraceSnapshot',
            Qt.ConnectionType.DirectConnection, Q_RETURN_ARG('QVariant'))
        if isinstance(result, QJSValue):
            result = result.toVariant()
        return result

    @Slot(object)
    def _captured(self, result):
        self._capture_notifications(result)
        request = result.get('requestId')
        # Retire transactions after immutable classification, preserving an old
        # coherent frame already latched/queued before the next publish.
        if result.get('outcome')!='coherentSubmission':
            for previous,state in list(self._pending.items()):
                if state.get('supersededByRevision') and self._tracker and not self._tracker.has_pending_submission(previous):
                    self.finished(previous,'superseded',byRevision=state['supersededByRevision'])
        if not request or result['outcome'] != 'coherentSubmission':
            return
        first = request in self._pending
        if not first and self._completed.get(request) != 'coherentSubmission':
            return
        settled = (result.get('motionSettled') and result.get('strictCoherence')
                   and request not in self._settled)
        if not (first or settled):
            return
        if settled:
            self._settled.add(request)
        snapshot = result.get('snapshot', {})
        summary = {key: value for key, value in result.items() if key != 'snapshot'}
        summary['participants'] = snapshot.get('participants', [])
        summary['firstCoherent'] = first
        summary['firstSettled'] = bool(settled)
        summary['submittedSessionNs'] = result['submittedNs'] - self._clock_origin
        if len(self._frames) < 512:
            self._frames.append(summary)
        else:
            self._summaries_dropped += 1
            self.recorder.record('frame.summaryLimit', request_id=request)
        if first:
            outcome = 'recoveryFallback' if (self._pending[request].get('recovery')
                or self._pending[request]['operation'] == 'recoverVisual') else 'coherentSubmission'
            self.finished(request, outcome, revision=result.get('revision'),
                frameSerial=result['frameSerial'], submittedSessionNs=summary['submittedSessionNs'],
                strictCoherence=result.get('strictCoherence', False))

    def _capture_notifications(self, result):
        # A candidate elsewhere can block theme coherence while an independent
        # urgent fallback is already present. Its identity comes from this ticket.
        if result.get('reason') not in ('', 'candidatePending', 'mandatoryNotCommitted',
                'mandatoryRevisionMismatch', 'revisionMismatch'):
            return
        seen = {(r['eventId'], r['eventRevision'], r['rank']) for r in self._notification_frames}
        for participant in result.get('snapshot', {}).get('participants', []):
            if participant.get('surfaceId') not in ('alerts.banner.small','alerts.banner.large','alerts.urgent'):
                continue
            if not (participant.get('exposed') and participant.get('ready') and participant.get('geometryValid')
                    and participant.get('opacity', 0) > 0):
                continue
            key = (participant.get('eventId'), participant.get('eventRevision'), participant.get('rank'))
            if key not in self._notification_inputs or key in seen:
                continue
            submitted = result['submittedNs'] - self._clock_origin
            started = self._notification_inputs[key]
            if submitted < started:
                continue
            row = {'eventId':key[0], 'eventRevision':key[1], 'rank':key[2],
                   'startedSessionNs':started, 'submittedSessionNs':submitted,
                   'durationMs':(submitted-started)/1e6, 'frameSerial':result['frameSerial'],
                   'rendererIdentity':participant.get('rendererIdentity'),
                   'responseKind':'fallback' if participant.get('role')=='fallback' else 'selectedRenderer'}
            self._notification_frames.append(row)
            seen.add(key)
            self.recorder.record('notification.submission', request_id=result.get('requestId') or None,
                eventId=key[0], eventRevision=key[1], rank=key[2], frameSerial=result['frameSerial'],
                submittedSessionNs=submitted, responseKind=row['responseKind'])

    def finish(self):
        if self._tracker:
            self._tracker.detach()
        if self._window is not None:
            try:
                self._window.setProperty('traceRecorder', None)
            except RuntimeError:
                pass  # Qt may already have destroyed the diagnostic window.
        for request in list(self._pending):
            self.finished(request, 'unobservedFrame', reason='sessionEndedBeforeCoherentSubmission')

    def report(self):
        result = self.recorder.snapshot()
        result.update(frameProtocol='immutableGuiTicket/syncLatch/submissionSerial',
            frameSummaries=self._frames, frameSummariesDropped=self._summaries_dropped, nativeSignalTimestampVerified=False,
            gilDelayQuantified=False, newPublicThemeApiVerified=False)
        result['notificationFrames'] = self._notification_frames
        result['notificationInputsCount'] = len(self._notification_inputs)
        result['runtimeManifestSha256'] = self._manifest_hash
        result['apiFingerprint'] = self._api_fingerprint
        result['rendererSources'] = self._renderer_sources
        if self._summaries_dropped:
            result['complete'] = False
            result['incompleteReasons'].append('frameSummariesDropped')
        return result

    def write_report(self, path):
        self.finish()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_text(json.dumps(self.report(), ensure_ascii=False, indent=2) + '\n')
        temporary.replace(path)
