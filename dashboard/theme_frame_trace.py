"""Private, passive Qt frame correlation; never reads GUI objects on render threads.

A captured ticket proves only the supplied sampled Qt state at scene sync, not
arbitrary pixels, GPU time or optical panel response. Python callback timestamps
include any GIL acquisition delay. Providers must invalidate relevant mutations
between capture and scene sync (including changes made in polish).
"""
from dataclasses import dataclass
import math
import threading
import time

from PySide6.QtCore import QObject, Qt, Signal, Slot


def _freeze(value, depth=0, budget=None):
    if budget is None:
        budget = [4096]
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError('frame snapshot exceeds 4096 nodes')
    if depth > 16:
        raise ValueError('frame snapshot nesting exceeds 16')
    if value is None or type(value) in (bool, int, str):
        if isinstance(value, str) and len(value) > 1024:
            raise ValueError('frame snapshot string exceeds 1024')
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if isinstance(value, dict):
        if len(value) > 256 or any(type(k) is not str for k in value):
            raise ValueError('frame snapshot requires bounded string keys')
        return ('__map__', tuple((k, _freeze(v, depth + 1, budget)) for k, v in sorted(value.items())))
    if isinstance(value, (list, tuple)):
        if len(value) > 256:
            raise ValueError('frame snapshot list exceeds 256')
        return ('__list__', tuple(_freeze(v, depth + 1, budget) for v in value))
    raise ValueError('frame snapshot must contain JSON primitives, not QObject handles')


def _thaw(value):
    if isinstance(value, tuple):
        kind, items = value
        if kind == '__map__':
            return {k: _thaw(v) for k, v in items}
        return [_thaw(v) for v in items]
    return value


@dataclass(frozen=True)
class FrameTicket:
    capture_serial: int
    epoch: int
    captured_ns: int
    capture_thread: int
    snapshot: tuple
    reason: str = ''
    capture_cost_ns: int = 0


@dataclass(frozen=True)
class MotionStopProof:
    """GUI stop observed before submission with identical copied visual state."""
    attachment_id: int
    capture_serial: int
    ticket_epoch: int
    observed_ns: int
    snapshot: tuple


def _motion_independent(value):
    """Remove only motion liveness; every visual/identity field stays comparable."""
    if isinstance(value, dict):
        return {key: _motion_independent(item) for key,item in value.items() if key != 'motionRunning'}
    if isinstance(value, list):
        return [_motion_independent(item) for item in value]
    return value


def _matching_terminal_state(ticket, proof_snapshot):
    original = _thaw(ticket.snapshot)
    terminal = _thaw(proof_snapshot)
    if terminal.get('motionRunning') is not False:
        return False
    # Boolean geometryValid is insufficient: require the actual render signature.
    participants = original.get('participants', [])
    if not participants or any(not isinstance(p, dict) or not p.get('visualGeometry') for p in participants):
        return False
    return _motion_independent(original) == _motion_independent(terminal)


@dataclass(frozen=True)
class FrameSubmission:
    frame_serial: int
    ticket: FrameTicket | None
    synchronized_ns: int
    sync_thread: int
    submitted_ns: int
    submission_thread: int
    reason: str = ''
    sync_pre_latch_cost_ns: int = 0
    submission_pre_queue_cost_ns: int = 0
    attachment_id: int = 0
    terminal_proof: MotionStopProof | None = None


def classify_submission(submission):
    """Pure classifier. Never consults current GUI/service/request state."""
    if submission.reason or submission.ticket is None:
        return {'outcome': 'unobservedFrame', 'reason': submission.reason or 'missingTicket'}
    ticket = submission.ticket
    if ticket.reason:
        return {'outcome': 'unobservedFrame', 'reason': ticket.reason}
    snapshot = _thaw(ticket.snapshot)
    revision = snapshot.get('revision')
    participants = snapshot.get('participants')
    common = {'revision': revision, 'requestId': snapshot.get('requestId'), 'snapshot': snapshot,
              'motionSettled': snapshot.get('motionRunning') is False}
    candidate_pending = snapshot.get('candidatePending') is True
    common['candidatePending'] = candidate_pending
    if snapshot.get('sceneGraphValid') is False:
        return dict(common, outcome='unobservedFrame', reason='sceneGraphInvalid')
    if type(revision) is not int or revision < 0 or not isinstance(participants, list) or not participants:
        return dict(common, outcome='unobservedFrame', reason='invalidSnapshot')
    identities = set()
    exposed_count = 0
    for participant in participants:
        identity = participant.get('instanceId') if isinstance(participant, dict) else None
        if not isinstance(identity, str) or not identity or identity in identities:
            return dict(common, outcome='unobservedFrame', reason='participantIdentity')
        identities.add(identity)
        if type(participant.get('revision')) is not int or type(participant.get('observedRevision', participant.get('revision'))) is not int:
            return dict(common, outcome='unobservedFrame', reason='participantRevisionType')
        front_required = candidate_pending and (participant.get('mandatory') is True or participant.get('exposed') is True)
        if front_required:
            if not (participant.get('frontCommitted') is True and participant.get('frontReady') is True):
                return dict(common, outcome='unobservedFrame', reason='mandatoryNotCommitted')
            renderer = participant.get('frontRendererIdentity')
            expected_renderer = participant.get('frontExpectedRendererIdentity')
            if not isinstance(renderer, str) or not renderer or renderer != expected_renderer:
                return dict(common, outcome='unobservedFrame', reason='frontRendererMismatch')
        elif participant.get('mandatory') and not (participant.get('committed') is True and participant.get('ready') is True):
            return dict(common, outcome='unobservedFrame', reason='mandatoryNotCommitted')
        retained = ((participant.get('participation') == 'retainedExit' or participant.get('retainedExit') is True)
                    and participant.get('actionsEnabled') is False)
        if participant.get('mandatory'):
            committed_revision = participant.get('frontCommittedRevision') if candidate_pending else participant.get('committedRevision', participant.get('revision'))
            if type(committed_revision) is not int or committed_revision != revision:
                return dict(common, outcome='unobservedFrame', reason='mandatoryRevisionMismatch')
            displayed_revision = participant.get('frontCommittedRevision') if candidate_pending else participant.get('revision')
            if not retained and (displayed_revision != revision or participant.get('observedRevision', participant.get('revision')) != revision):
                return dict(common, outcome='unobservedFrame', reason='mandatoryRevisionMismatch')
        if participant.get('exposed') is not True:
            continue
        exposed_count += 1
        opacity = participant.get('opacity')
        if participant.get('geometryValid') is not True or type(opacity) not in (int, float) or not math.isfinite(opacity) or opacity <= 0:
            return dict(common, outcome='unobservedFrame', reason='participantNotPresent')
        if (participant.get('frontReady') if candidate_pending else participant.get('ready')) is not True:
            return dict(common, outcome='unobservedFrame', reason='participantNotReady')
        observed = participant.get('observedRevision', participant.get('revision'))
        displayed_revision = participant.get('frontCommittedRevision') if candidate_pending else participant.get('revision')
        if type(displayed_revision) is not int or observed != revision or displayed_revision != revision:
            # An explicit retained exit is presentation history, not current live style.
            if not retained:
                return dict(common, outcome='unobservedFrame', reason='revisionMismatch')
    if not exposed_count:
        return dict(common, outcome='unobservedFrame', reason='noExposedParticipants')
    proof = submission.terminal_proof
    if (proof is not None and proof.attachment_id == submission.attachment_id
            and proof.capture_serial == ticket.capture_serial and proof.ticket_epoch == ticket.epoch
            and submission.synchronized_ns <= proof.observed_ns <= submission.submitted_ns
            and _matching_terminal_state(ticket, proof.snapshot)):
        common['motionSettled'] = True
        common['motionSettlementEvidence'] = 'guiStopBeforeSubmissionWithUnchangedVisualState'
        common['motionStopObservedNs'] = proof.observed_ns
    return dict(common, outcome='displayedRevisionCoherent' if candidate_pending else 'coherentSubmission', reason='', strictCoherence=all(
        (p.get('frontCommittedRevision') if candidate_pending else p.get('revision')) == revision and p.get('observedRevision', p.get('revision')) == revision
        for p in participants if p.get('exposed') is True))


class ThemeFrameTracker(QObject):
    """Optional observer. Construct/attach only when tracing is explicitly enabled.

    capture_provider executes on GUI afterAnimating and returns a small JSON map.
    `invalidate()` must be called for observed mutation after capture/before sync.
    It never changes an already latched scene/frame or queued immutable record.
    `invalidate_scene()` additionally invalidates the current scene latch.
    """
    captured = Signal(object)
    _delivered = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        self._window = None
        self._provider = None
        self._recorder = None
        self._ticket = None
        self._latch = None
        self._epoch = 0
        self._capture_serial = 0
        self._frame_serial = 0
        self._connections = []
        self._gui_thread = threading.get_ident()
        self._delivery_open = False
        self._attachment_id = 0
        self._capture_open = False
        self._queued_requests = {}
        self._delivered.connect(self._consume, Qt.ConnectionType.QueuedConnection)

    def attach(self, window, snapshot_provider, recorder=None):
        if threading.get_ident() != self._gui_thread:
            raise RuntimeError('frame tracker attach requires GUI thread')
        self.detach()
        self._window, self._provider, self._recorder = window, snapshot_provider, recorder
        self._delivery_open = True
        signals = [(window.afterAnimating, self._capture),
                   (window.afterSynchronizing, self._synchronize),
                   (window.frameSwapped, self._submit),
                   (window.sceneGraphInvalidated, self._scene_invalidated)]
        for signal, callback in signals:
            signal.connect(callback, Qt.ConnectionType.DirectConnection)
            self._connections.append((signal, callback))
        window.visibleChanged.connect(self._visibility_changed)
        self._connections.append((window.visibleChanged, self._visibility_changed))
        return self

    def detach(self):
        self._delivery_open = False
        self._attachment_id += 1
        for signal, callback in self._connections:
            try:
                signal.disconnect(callback)
            except (RuntimeError, TypeError):
                pass
        self._connections = []
        with self._lock:
            self._epoch += 1
            self._ticket = None
            self._latch = None
            self._capture_open = False
            self._queued_requests.clear()
        self._window = self._provider = self._recorder = None

    @Slot(str)
    def invalidate(self, reason='stateChanged'):
        """Invalidate only tickets not synchronized yet; preserve submitted history."""
        with self._lock:
            self._epoch += 1
            self._ticket = None

    def invalidate_scene(self, reason='sceneInvalidated'):
        with self._lock:
            self._epoch += 1
            self._ticket = None
            self._latch = None
            self._capture_open = False

    def refresh_gui_ticket(self):
        """Refreeze a changed non-render animation state before scene sync only.

        Qt can stop `running` after afterAnimating on its last drawable frame.
        No update/timer/frame is requested, and synchronized history is immutable.
        Subsequent geometry/style mutations still invalidate this fresh ticket.
        """
        if threading.get_ident() != self._gui_thread:
            return False
        with self._lock:
            opened = self._capture_open
        if not opened or self._window is None:
            return False
        self._capture()
        return True

    def prove_motion_stopped_gui(self):
        """Add a separate proof to an unsubmitted latch; never rewrite its ticket.

        A final animation can stop after sync without changing another pixel.
        The terminal GUI snapshot must match every identity/visual field, and
        must be observed before frameSwapped. A post-submit proof is rejected.
        """
        if threading.get_ident() != self._gui_thread or self._window is None:
            return False
        with self._lock:
            latch = self._latch
            attachment = self._attachment_id
        if latch is None or latch[1] is None or latch[1].reason:
            return False
        ticket = latch[1]
        try:
            value = self._provider()
            if not isinstance(value, dict):
                return False
            terminal = _freeze(value)
        except Exception:
            return False
        observed = time.perf_counter_ns()
        if not _matching_terminal_state(ticket, terminal):
            return False
        proof = MotionStopProof(attachment, ticket.capture_serial, ticket.epoch, observed, terminal)
        with self._lock:
            if self._attachment_id != attachment or self._latch is not latch:
                return False
            self._latch = (*latch[:5], proof)
        return True

    @staticmethod
    def _ticket_request(ticket):
        if ticket is None:
            return None
        value = next((value for key,value in ticket.snapshot[1] if key=='requestId'), None)
        return value if isinstance(value,str) and value else None

    def has_pending_submission(self, request):
        """Copied identities only; a latched/queued old frame can still win."""
        with self._lock:
            return (self._queued_requests.get(request,0)>0 or
                    bool(self._latch and self._ticket_request(self._latch[1])==request))

    @Slot()
    def _scene_invalidated(self):
        # Called directly on render thread: copied primitives only.
        self.invalidate_scene('sceneGraphInvalidated')

    @Slot()
    def _visibility_changed(self):
        self.invalidate_scene('windowVisibilityChanged')

    @Slot()
    def _capture(self):
        now = time.perf_counter_ns()
        producer = threading.get_ident()
        with self._lock:
            self._capture_open = True
            epoch = self._epoch
            self._capture_serial += 1
            serial = self._capture_serial
        reason, snapshot = '', _freeze({})
        if producer != self._gui_thread:
            reason = 'captureNotGuiThread'
        elif self._window is None or not self._window.isExposed():
            reason = 'windowNotExposed'
        else:
            try:
                value = self._provider()
                if not isinstance(value, dict):
                    raise ValueError('snapshot must be a map')
                snapshot = _freeze(value)
            except Exception as error:
                # Never serialize provider data or traceback/exception contents.
                reason = 'snapshotError:' + type(error).__name__
        ticket = FrameTicket(serial, epoch, now, producer, snapshot, reason, time.perf_counter_ns() - now)
        with self._lock:
            if epoch == self._epoch:
                self._ticket = ticket

    @Slot()
    def _synchronize(self):
        now = time.perf_counter_ns()
        with self._lock:
            self._capture_open = False
            self._frame_serial += 1
            ticket, self._ticket = self._ticket, None
            if ticket is not None and ticket.epoch != self._epoch:
                ticket = None
            self._latch = (self._frame_serial, ticket, now, threading.get_ident(), time.perf_counter_ns() - now, None)

    @Slot()
    def _submit(self):
        now = time.perf_counter_ns()
        producer = threading.get_ident()
        with self._lock:
            latch = self._latch
            serial = self._frame_serial
            attachment_id = self._attachment_id
            # Keep ownership observable continuously across scene -> GUI queue.
            # A GUI publish/detach can run while the frozen object is constructed.
            # It must see either this latch or its queued identity, never neither.
            request = self._ticket_request(latch[1]) if latch else None
            if request:
                self._queued_requests[request] = self._queued_requests.get(request,0)+1
            self._latch = None
        if latch is None:
            value = FrameSubmission(serial, None, 0, 0, now, producer, 'noSynchronizedTicket',
                                    submission_pre_queue_cost_ns=time.perf_counter_ns() - now, attachment_id=attachment_id)
        else:
            serial, ticket, synced_ns, synced_thread, sync_cost, proof = latch
            value = FrameSubmission(serial, ticket, synced_ns, synced_thread, now, producer,
                                    '' if ticket is not None else 'noGuiTicket', sync_cost, time.perf_counter_ns() - now, attachment_id, proof)
        self._delivered.emit(value)

    @Slot(object)
    def _consume(self, submission):
        if not self._delivery_open or submission.attachment_id != self._attachment_id:
            return
        request = self._ticket_request(submission.ticket)
        if request:
            with self._lock:
                remaining = self._queued_requests.get(request,0)-1
                if remaining>0:self._queued_requests[request]=remaining
                else:self._queued_requests.pop(request,None)
        now = time.perf_counter_ns()
        classification = classify_submission(submission)
        result = dict(classification, frameSerial=submission.frame_serial,
                      captureSerial=submission.ticket.capture_serial if submission.ticket else None,
                      capturedNs=submission.ticket.captured_ns if submission.ticket else None,
                      synchronizedNs=submission.synchronized_ns, submittedNs=submission.submitted_ns,
                      consumedNs=now, queuedDeliveryLagNs=now - submission.submitted_ns,
                      captureThread=submission.ticket.capture_thread if submission.ticket else None,
                      syncThread=submission.sync_thread, submissionThread=submission.submission_thread,
                      consumerThread=threading.get_ident(),
                      timestampQuality='PythonCallbackEntryIncludesUnknownGilDelay',
                      clock='processLocalPerfCounterNs',
                      captureCallbackCostNs=submission.ticket.capture_cost_ns if submission.ticket else None,
                      syncPreLatchCostNs=submission.sync_pre_latch_cost_ns,
                      submissionPreQueueCostNs=submission.submission_pre_queue_cost_ns)
        if self._recorder is not None:
            self._recorder.record('frame.submission', request_id=classification.get('requestId') or None,
                frameSerial=submission.frame_serial, revision=classification.get('revision'),
                outcome=classification['outcome'], reason=classification.get('reason', ''),
                synchronizedNs=submission.synchronized_ns, submittedNs=submission.submitted_ns,
                queuedDeliveryLagNs=result['queuedDeliveryLagNs'],
                captureThread=result['captureThread'], syncThread=submission.sync_thread,
                submissionThread=submission.submission_thread,
                timestampQuality=result['timestampQuality'],
                captureCallbackCostNs=result['captureCallbackCostNs'],
                syncPreLatchCostNs=submission.sync_pre_latch_cost_ns,
                submissionPreQueueCostNs=submission.submission_pre_queue_cost_ns,
                motionSettled=result.get('motionSettled', False),
                motionSettlementEvidence=result.get('motionSettlementEvidence', 'capturedGuiState'),
                motionStopObservedNs=result.get('motionStopObservedNs'))
        self.captured.emit(result)
