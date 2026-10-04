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
    if snapshot.get('candidatePending') is True:
        return dict(common, outcome='unobservedFrame', reason='candidatePending')
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
        if participant.get('mandatory') and not (participant.get('committed') is True and participant.get('ready') is True):
            return dict(common, outcome='unobservedFrame', reason='mandatoryNotCommitted')
        retained = ((participant.get('participation') == 'retainedExit' or participant.get('retainedExit') is True)
                    and participant.get('actionsEnabled') is False)
        if participant.get('mandatory'):
            committed_revision = participant.get('committedRevision', participant.get('revision'))
            if type(committed_revision) is not int or committed_revision != revision:
                return dict(common, outcome='unobservedFrame', reason='mandatoryRevisionMismatch')
            if not retained and (participant.get('revision') != revision or participant.get('observedRevision', participant.get('revision')) != revision):
                return dict(common, outcome='unobservedFrame', reason='mandatoryRevisionMismatch')
        if participant.get('exposed') is not True:
            continue
        exposed_count += 1
        opacity = participant.get('opacity')
        if participant.get('geometryValid') is not True or type(opacity) not in (int, float) or not math.isfinite(opacity) or opacity <= 0:
            return dict(common, outcome='unobservedFrame', reason='participantNotPresent')
        if participant.get('ready') is not True:
            return dict(common, outcome='unobservedFrame', reason='participantNotReady')
        observed = participant.get('observedRevision', participant.get('revision'))
        if observed != revision or participant.get('revision') != revision:
            # An explicit retained exit is presentation history, not current live style.
            if not retained:
                return dict(common, outcome='unobservedFrame', reason='revisionMismatch')
    if not exposed_count:
        return dict(common, outcome='unobservedFrame', reason='noExposedParticipants')
    return dict(common, outcome='coherentSubmission', reason='', strictCoherence=all(
        p.get('revision') == revision and p.get('observedRevision', p.get('revision')) == revision
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
            self._frame_serial += 1
            ticket, self._ticket = self._ticket, None
            if ticket is not None and ticket.epoch != self._epoch:
                ticket = None
            self._latch = (self._frame_serial, ticket, now, threading.get_ident(), time.perf_counter_ns() - now)

    @Slot()
    def _submit(self):
        now = time.perf_counter_ns()
        producer = threading.get_ident()
        with self._lock:
            latch, self._latch = self._latch, None
            serial = self._frame_serial
            attachment_id = self._attachment_id
        if latch is None:
            value = FrameSubmission(serial, None, 0, 0, now, producer, 'noSynchronizedTicket',
                                    submission_pre_queue_cost_ns=time.perf_counter_ns() - now, attachment_id=attachment_id)
        else:
            serial, ticket, synced_ns, synced_thread, sync_cost = latch
            value = FrameSubmission(serial, ticket, synced_ns, synced_thread, now, producer,
                                    '' if ticket is not None else 'noGuiTicket', sync_cost, time.perf_counter_ns() - now, attachment_id)
        self._delivered.emit(value)

    @Slot(object)
    def _consume(self, submission):
        if not self._delivery_open or submission.attachment_id != self._attachment_id:
            return
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
                submissionPreQueueCostNs=submission.submission_pre_queue_cost_ns)
        self.captured.emit(result)
