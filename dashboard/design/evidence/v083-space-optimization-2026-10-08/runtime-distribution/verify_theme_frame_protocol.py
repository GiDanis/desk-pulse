"""A0.3.0 isolated Qt window protocol probe; no providers or diagnostic animation.

The harness changes a real QML color as its test workload. The observer itself
never calls update/requestUpdate or produces timer/animation frames.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import threading
import time

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from theme_frame_trace import ThemeFrameTracker


class ProtocolHarness(QObject):
    mutateAfterSync = Signal()

    def __init__(self, window, app, directory):
        super().__init__()
        self.window, self.app, self.directory = window, app, directory
        self.records = []
        self.warnings = []
        self.gui_thread = threading.get_ident()
        self.phase = 'initial'
        self.gated = False
        self.hidden_started_ns = 0
        self.hidden_finished_ns = 0
        self.busy_ns = 80_000_000
        self.revision = 1
        self.request_id = 'request-A1'
        self.candidate_pending = False
        self.mutated_before_delivery = False
        self.timed_out = False
        self.started_ns = time.perf_counter_ns()
        self.tracker = ThemeFrameTracker().attach(window, self.snapshot)
        self.tracker.captured.connect(self.record)
        self.mutateAfterSync.connect(self.change_before_delivery, Qt.ConnectionType.QueuedConnection)
        window.afterSynchronizing.connect(self.sync_barrier, Qt.ConnectionType.DirectConnection)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(self.timeout)
        self.deadline.start(8000)

    def snapshot(self):
        return {'revision': self.revision, 'requestId': self.request_id,
            'candidatePending': self.candidate_pending, 'sceneGraphValid': True,
            'motionRunning': False, 'tokenSignature': str(self.window.property('surfaceColor')),
            'participants': [{'instanceId': 'probe.page.live', 'surfaceId': 'probe',
                'rendererIdentity': 'same-probe-renderer', 'revision': self.revision,
                'observedRevision': self.window.property('appearanceRevision'),
                'exposed': True, 'mandatory': True, 'ready': True, 'committed': True,
                'geometryValid': self.window.width() > 0 and self.window.height() > 0,
                'opacity': 1.0}]}

    @Slot()
    def sync_barrier(self):
        # Queue GUI mutation before _submit queues its immutable consumption.
        # This does not read any QML/GUI object from the render thread.
        if self.phase == 'initial' and not self.gated:
            self.gated = True
            self.mutateAfterSync.emit()
        elif self.phase == 'cancelPending' and not self.gated:
            self.gated = True
            self.mutateAfterSync.emit()

    def set_state(self, revision, request_id, color, pending=False):
        self.tracker.invalidate('probePublication')
        self.revision, self.request_id, self.candidate_pending = revision, request_id, pending
        self.window.setProperty('appearanceRevision', revision)
        self.window.setProperty('surfaceColor', color)

    @Slot()
    def change_before_delivery(self):
        if self.phase == 'initial':
            # GIL released while GUI is deliberately occupied; render signal can
            # enqueue. Then publish B before delivery of the frozen A record.
            time.sleep(self.busy_ns / 1e9)
            self.set_state(2, 'request-B', '#37556a')
            self.mutated_before_delivery = True
            self.phase = 'B'
        elif self.phase == 'cancelPending':
            self.set_state(4, 'request-after-cancel', '#725f35')
            self.phase = 'cancelled'

    @Slot(object)
    def record(self, value):
        self.records.append(value)
        outcome, request = value.get('outcome'), value.get('requestId')
        if outcome != 'coherentSubmission':
            return
        if request == 'request-B' and self.phase == 'B':
            self.set_state(1, 'request-A2', '#163c28')
            self.phase = 'ABA'
        elif request == 'request-A2' and self.phase == 'ABA':
            self.phase = 'hidden'
            self.window.hide()
            self.hidden_started_ns = time.perf_counter_ns()
            self.set_state(3, 'request-hidden-reopen', '#6a3755')
            QTimer.singleShot(150, self.reopen)
        elif request == 'request-hidden-reopen' and self.phase == 'reopened':
            self.phase = 'cancelPending'
            self.gated = False
            self.set_state(4, 'request-cancelled-candidate', '#483d6d', pending=True)
        elif request == 'request-after-cancel' and self.phase == 'cancelled':
            self.phase = 'finished'
            QTimer.singleShot(100, self.finish)

    @Slot()
    def reopen(self):
        self.hidden_finished_ns = time.perf_counter_ns()
        self.phase = 'reopened'
        self.window.show()

    @Slot()
    def timeout(self):
        self.timed_out = True
        self.finish()

    @Slot()
    def finish(self):
        self.deadline.stop()
        self.tracker.detach()
        try:
            self.window.afterSynchronizing.disconnect(self.sync_barrier)
        except RuntimeError:
            pass
        coherent = [r for r in self.records if r['outcome'] == 'coherentSubmission']
        requests = {r.get('requestId') for r in coherent}
        required = {'request-A1', 'request-B', 'request-A2', 'request-hidden-reopen', 'request-after-cancel'}
        first_a = next((r for r in coherent if r.get('requestId') == 'request-A1'), None)
        cancelled = [r for r in self.records if r.get('requestId') == 'request-cancelled-candidate']
        identity_pass = required.issubset(requests) and first_a is not None and first_a['revision'] == 1
        hidden_records = [r for r in coherent if self.hidden_started_ns < r['submittedNs'] < self.hidden_finished_ns]
        ordered = all(r['capturedNs'] <= r['synchronizedNs'] <= r['submittedNs'] <= r['consumedNs']
            for r in coherent)
        queued_aba = bool(first_a and first_a['queuedDeliveryLagNs'] >= self.busy_ns * .7 and self.mutated_before_delivery)
        sync_threads = sorted({r['syncThread'] for r in self.records})
        submit_threads = sorted({r['submissionThread'] for r in self.records})
        gui_threads = sorted({r['captureThread'] for r in self.records if r['captureThread'] is not None})
        report = {'reportVersion': 1, 'qt': qVersion(), 'pyside': pyside_version,
            'platformPlugin': self.app.platformName(), 'machine': platform.machine(),
            'graphicsApi': str(self.window.rendererInterface().graphicsApi()),
            'requestedRenderLoop': os.environ.get('QSG_RENDER_LOOP', 'unset'),
            'observedThreading': 'threaded' if any(t != self.gui_thread for t in sync_threads + submit_threads) else 'singleGuiThreadObserved',
            'guiThread': self.gui_thread, 'captureThreads': gui_threads,
            'syncThreads': sync_threads, 'submissionThreads': submit_threads,
            'timeout': self.timed_out, 'finalPhase': self.phase,
            'coherentRequests': sorted(requests), 'requiredRequests': sorted(required),
            'checks': {'requiredFrames': identity_pass, 'frozenAWhileGuiAlreadyB': queued_aba,
                'signalTimestampOrdering': ordered,
                'noCoherentSubmissionWhileHidden': not hidden_records,
                'cancelledCandidateNotCoherent': bool(cancelled) and all(r['outcome'] != 'coherentSubmission' for r in cancelled),
                'captureAndConsumerOnGui': all(r['captureThread'] == self.gui_thread and r['consumerThread'] == self.gui_thread for r in coherent)},
            'timestampQuality': 'PythonCallbackEntryIncludesUnknownGilDelay',
            'nativeSignalTimestampVerified': False,
            'gilDelayQuantified': False,
            'gilLimitation': 'Queued GUI delay is measured; no independent C++ emission clock is available to bound render Python GIL acquisition delay.',
            'proofScope': 'Real QML color changes, immutable Qt scene-sync tickets and frame submission identity; no pixel, GPU or optical timing assertion.',
            'observerForcedFrames': False,
            'observedPythonCallbackCostsNs': {key: {
                'count': len([r[key] for r in self.records if r.get(key) is not None]),
                'max': max([r[key] for r in self.records if r.get(key) is not None], default=None)}
                for key in ('captureCallbackCostNs', 'syncPreLatchCostNs', 'submissionPreQueueCostNs')},
            'callbackCostScope': 'Python capture body and direct callback pre-latch/pre-queue only; excludes native emission/GIL wait and signal emission tail.',
            'warnings': self.warnings,
            'records': self.records}
        report['verified'] = not self.timed_out and all(report['checks'].values()) and not self.warnings
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / 'report.json'
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(target)
        print(json.dumps({k: v for k, v in report.items() if k != 'records'}, ensure_ascii=False))
        self.app.exit(0 if report['verified'] else 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    app = QGuiApplication([])
    app.setOrganizationName('SmartPCTests'); app.setApplicationName('Theme frame protocol')
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(str(v) for v in values))
    engine.loadData(b'''import QtQuick\nimport QtQuick.Window\nWindow { width: 960; height: 640; visible: false\n property int appearanceRevision: 1\n property string surfaceColor: "#163c28"\n Rectangle { anchors.fill: parent; color: surfaceColor }\n}''')
    if not engine.rootObjects():
        raise RuntimeError('protocol QML window failed: ' + '; '.join(warnings))
    window = shiboken6.wrapInstance(shiboken6.getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    harness = ProtocolHarness(window, app, args.directory)
    harness.warnings = warnings
    window.show()
    status = app.exec()
    window.hide()
    del harness
    del engine
    return status


if __name__ == '__main__':
    raise SystemExit(main())
