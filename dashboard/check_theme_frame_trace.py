"""Immutable identity, phase invalidation and conservative frame classification."""
import dataclasses
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from theme_frame_trace import (FrameSubmission, FrameTicket, MotionStopProof, ThemeFrameTracker,
                               _freeze, _thaw, classify_submission)


def snapshot(revision=1, request='one'):
    return {'revision': revision, 'requestId': request, 'candidatePending': False,
            'sceneGraphValid': True, 'motionRunning': False,
            'participants': [{'instanceId': 'page.live', 'revision': revision,
                'observedRevision': revision, 'exposed': True, 'mandatory': True,
                'committed': True, 'ready': True, 'geometryValid': True, 'opacity': 1.0}]}


def submission(value):
    return FrameSubmission(1, FrameTicket(1, 0, 10, 1, _freeze(value)), 20, 2, 30, 2)


class ClassifierTests(unittest.TestCase):
    def test_snapshot_frozen_before_mutation_and_aba_identity(self):
        current = snapshot()
        frozen = submission(current)
        current['revision'] = 2
        current['requestId'] = 'two'
        current['participants'][0]['observedRevision'] = 2
        first = classify_submission(frozen)
        self.assertEqual((first['revision'], first['requestId']), (1, 'one'))
        third = classify_submission(submission(snapshot(1, 'three')))
        self.assertNotEqual(first['requestId'], third['requestId'])
        self.assertEqual(first['outcome'], 'coherentSubmission')

    def test_ticket_not_mutable(self):
        ticket = submission(snapshot()).ticket
        with self.assertRaises(dataclasses.FrozenInstanceError):
            ticket.epoch = 4
        copy = _thaw(ticket.snapshot); copy['participants'].clear()
        self.assertEqual(len(_thaw(ticket.snapshot)['participants']), 1)

    def test_qobject_and_nonfinite_values_refused(self):
        from PySide6.QtCore import QObject
        for value in (QObject(), float('nan'), float('inf'), {'bad': QObject()}):
            with self.assertRaises(ValueError):
                _freeze(value)

    def test_missing_capture_never_classifies_current_revision(self):
        value = FrameSubmission(4, None, 0, 0, 20, 2, 'noSynchronizedTicket')
        self.assertEqual(classify_submission(value)['outcome'], 'unobservedFrame')
        self.assertNotIn('revision', classify_submission(value))

    def test_unready_mandatory_hidden_host_rejects(self):
        current = snapshot()
        current['participants'].append(dict(current['participants'][0], instanceId='notice.hidden', exposed=False, ready=False))
        self.assertEqual(classify_submission(submission(current))['reason'], 'mandatoryNotCommitted')

    def test_hidden_mandatory_revision_is_not_enough_ready(self):
        current = snapshot()
        current['participants'].append(dict(current['participants'][0], instanceId='notice.hidden', exposed=False, revision=0))
        self.assertEqual(classify_submission(submission(current))['reason'], 'mandatoryRevisionMismatch')

    def test_style_revision_mismatch_rejects_reused_renderer(self):
        current = snapshot()
        current['participants'][0]['observedRevision'] = 0
        self.assertEqual(classify_submission(submission(current))['outcome'], 'unobservedFrame')

    def test_frozen_exit_explicit_without_actions_and_strict_false(self):
        current = snapshot()
        current['participants'].append(dict(current['participants'][0], instanceId='exit', revision=0,
            observedRevision=0, mandatory=False, retainedExit=True, actionsEnabled=False))
        result = classify_submission(submission(current))
        self.assertEqual(result['outcome'], 'coherentSubmission')
        self.assertFalse(result['strictCoherence'])
        current['participants'][-1]['actionsEnabled'] = True
        self.assertEqual(classify_submission(submission(current))['reason'], 'revisionMismatch')

    def test_fallback_does_not_prove_requested_revision(self):
        current = snapshot()
        current['participants'].append(dict(current['participants'][0], instanceId='urgent.fallback',
            mandatory=False, revision=0, observedRevision=0, role='fallback'))
        self.assertEqual(classify_submission(submission(current))['reason'], 'revisionMismatch')

    def test_presence_and_identity(self):
        for mutate, reason in ((lambda p: p.update(opacity=0), 'participantNotPresent'),
                               (lambda p: p.update(geometryValid=False), 'participantNotPresent'),
                               (lambda p: p.update(instanceId=''), 'participantIdentity')):
            current = snapshot(); mutate(current['participants'][0])
            self.assertEqual(classify_submission(submission(current))['reason'], reason)
        current = snapshot(); current['participants'].append(dict(current['participants'][0]))
        self.assertEqual(classify_submission(submission(current))['reason'], 'participantIdentity')

    def test_pending_and_invalid_graph_and_no_exposure(self):
        for key, value, reason in [('candidatePending', True, 'candidatePending'),
                                   ('sceneGraphValid', False, 'sceneGraphInvalid')]:
            current = snapshot(); current[key] = value
            self.assertEqual(classify_submission(submission(current))['reason'], reason)
        current = snapshot(); current['participants'][0]['exposed'] = False
        self.assertEqual(classify_submission(submission(current))['reason'], 'noExposedParticipants')

    def test_invalidate_preserves_latched_scene_but_cancels_not_synced(self):
        tracker = ThemeFrameTracker()
        tracker._ticket = submission(snapshot()).ticket
        tracker.invalidate('afterPolishMutation')
        tracker._synchronize()
        self.assertIsNone(tracker._latch[1])
        tracker._ticket = FrameTicket(2, tracker._epoch, 10, threading.get_ident(), _freeze(snapshot()))
        tracker._synchronize(); latch = tracker._latch
        tracker.invalidate('publishedAfterSync')
        self.assertEqual(tracker._latch, latch)
        tracker.invalidate_scene('hidden')
        self.assertIsNone(tracker._latch)

    def test_refreeze_is_gui_only_before_sync_and_never_relabels_latch(self):
        tracker=ThemeFrameTracker()
        class Window:
            def isExposed(self):return True
        state=snapshot()
        state['motionRunning']=True
        tracker._window=Window();tracker._provider=lambda:state
        tracker._capture()
        state['motionRunning']=False
        tracker.invalidate('motion.stopped')
        self.assertTrue(tracker.refresh_gui_ticket())
        tracker._synchronize();latched=tracker._latch
        self.assertFalse(_thaw(latched[1].snapshot)['motionRunning'])
        state['revision']=2
        self.assertFalse(tracker.refresh_gui_ticket())
        self.assertEqual(tracker._latch,latched)
        tracker._window=None

    def test_snapshot_total_budget_and_bool_revision(self):
        with self.assertRaises(ValueError):
            _freeze([[i for i in range(256)] for j in range(256)])
        current = snapshot(0); current['participants'][0]['revision'] = False
        self.assertEqual(classify_submission(submission(current))['reason'], 'participantRevisionType')

    def test_old_attachment_delivery_rejected_after_reattach(self):
        tracker = ThemeFrameTracker()
        tracker._delivery_open = True; tracker._attachment_id = 2
        observed = []; tracker.captured.connect(observed.append)
        old = dataclasses.replace(submission(snapshot()), attachment_id=1)
        tracker._consume(old)
        self.assertEqual(observed, [])

    def test_mandatory_retained_exit_commits_new_revision_displays_old(self):
        current = snapshot()
        current['participants'].append(dict(current['participants'][0], instanceId='mandatory.exit',
            revision=0, observedRevision=0, committedRevision=1, retainedExit=True, actionsEnabled=False))
        result = classify_submission(submission(current))
        self.assertEqual(result['outcome'], 'coherentSubmission')
        self.assertFalse(result['strictCoherence'])
        current['participants'][-1]['retainedExit'] = False
        self.assertEqual(classify_submission(submission(current))['reason'], 'mandatoryRevisionMismatch')
        current['participants'][-1].update(retainedExit=True, committedRevision=0)
        self.assertEqual(classify_submission(submission(current))['reason'], 'mandatoryRevisionMismatch')

    def tracked_submission(self, tracker, observed, request='one'):
        tracker._delivery_open = True
        tracker._ticket = FrameTicket(1, tracker._epoch, 10, threading.get_ident(), _freeze(snapshot(request=request)))
        tracker._synchronize()
        tracker._submit()
        return observed[-1]

    def test_latch_to_queue_is_atomic_during_submission_construction(self):
        tracker = ThemeFrameTracker()
        observed = []; tracker._delivered.connect(observed.append, Qt.ConnectionType.DirectConnection)
        def during_construction(*args, **kwargs):
            self.assertTrue(tracker.has_pending_submission('one'))
            self.assertIsNone(tracker._latch)
            return FrameSubmission(*args, **kwargs)
        with patch('theme_frame_trace.FrameSubmission', side_effect=during_construction):
            value = self.tracked_submission(tracker, observed)
        self.assertTrue(tracker.has_pending_submission('one'))
        tracker._consume(value)
        self.assertFalse(tracker.has_pending_submission('one'))
        self.assertEqual(tracker._queued_requests, {})

    def test_detach_during_submission_construction_never_reinserts_identity(self):
        tracker = ThemeFrameTracker()
        observed = []; tracker._delivered.connect(observed.append, Qt.ConnectionType.DirectConnection)
        captured = []; tracker.captured.connect(captured.append)
        def during_construction(*args, **kwargs):
            self.assertTrue(tracker.has_pending_submission('one'))
            tracker.detach()
            self.assertFalse(tracker.has_pending_submission('one'))
            return FrameSubmission(*args, **kwargs)
        with patch('theme_frame_trace.FrameSubmission', side_effect=during_construction):
            value = self.tracked_submission(tracker, observed)
        self.assertEqual(tracker._queued_requests, {})
        tracker._delivery_open = True  # A new attachment opens delivery again.
        tracker._consume(value)
        self.assertEqual(captured, [])
        self.assertEqual(tracker._queued_requests, {})

    def test_multiple_queued_frames_decline_one_at_a_time(self):
        tracker = ThemeFrameTracker()
        observed = []; tracker._delivered.connect(observed.append, Qt.ConnectionType.DirectConnection)
        first = self.tracked_submission(tracker, observed)
        second = self.tracked_submission(tracker, observed)
        self.assertEqual(tracker._queued_requests, {'one': 2})
        tracker._consume(first)
        self.assertEqual(tracker._queued_requests, {'one': 1})
        self.assertTrue(tracker.has_pending_submission('one'))
        tracker._consume(second)
        self.assertFalse(tracker.has_pending_submission('one'))
        self.assertEqual(tracker._queued_requests, {})

    def test_all_previous_attachment_deliveries_are_discarded(self):
        tracker = ThemeFrameTracker()
        observed = []; tracker._delivered.connect(observed.append, Qt.ConnectionType.DirectConnection)
        captured = []; tracker.captured.connect(captured.append)
        previous = []
        for unused in range(3):
            previous.append(self.tracked_submission(tracker, observed))
            tracker.detach()
        current = self.tracked_submission(tracker, observed, request='current')
        for old in previous:
            tracker._consume(old)
        self.assertEqual(captured, [])
        self.assertEqual(tracker._queued_requests, {'current': 1})
        tracker._consume(current)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]['requestId'], 'current')
        self.assertEqual(tracker._queued_requests, {})


    def terminal_snapshot(self):
        state = snapshot()
        state['motionRunning'] = True
        state['participants'][0]['motionRunning'] = True
        state['participants'][0]['visualGeometry'] = {'corners':[0.0,0.0,100.0,100.0], 'scale':1.0, 'rotation':0.0, 'opacity':1.0}
        return state

    def test_terminal_stop_proof_preserves_original_history(self):
        state = self.terminal_snapshot(); original = submission(state)
        terminal = _thaw(original.ticket.snapshot)
        terminal['motionRunning'] = False; terminal['participants'][0]['motionRunning'] = False
        proof = MotionStopProof(0, 1, 0, 25, _freeze(terminal))
        final = dataclasses.replace(original, terminal_proof=proof)
        result = classify_submission(final)
        self.assertTrue(result['motionSettled'])
        self.assertTrue(result['snapshot']['motionRunning'])
        self.assertEqual(result['motionSettlementEvidence'], 'guiStopBeforeSubmissionWithUnchangedVisualState')
        self.assertFalse(classify_submission(original)['motionSettled'])

    def test_terminal_proof_rejects_postsubmit_old_identity_and_visual_change(self):
        original = submission(self.terminal_snapshot()); terminal = _thaw(original.ticket.snapshot)
        terminal['motionRunning'] = False; terminal['participants'][0]['motionRunning'] = False
        valid = MotionStopProof(0, 1, 0, 25, _freeze(terminal))
        for proof in [dataclasses.replace(valid, observed_ns=31), dataclasses.replace(valid, observed_ns=19),
                      dataclasses.replace(valid, attachment_id=1), dataclasses.replace(valid, capture_serial=2),
                      dataclasses.replace(valid, ticket_epoch=1)]:
            self.assertFalse(classify_submission(dataclasses.replace(original, terminal_proof=proof))['motionSettled'])
        for key,value in [('revision',2), ('requestId','other'), ('candidatePending',True)]:
            changed = dict(terminal, **{key:value})
            proof = dataclasses.replace(valid, snapshot=_freeze(changed))
            self.assertFalse(classify_submission(dataclasses.replace(original, terminal_proof=proof))['motionSettled'])
        terminal['participants'][0]['visualGeometry']['scale'] = .5
        proof = dataclasses.replace(valid, snapshot=_freeze(terminal))
        self.assertFalse(classify_submission(dataclasses.replace(original, terminal_proof=proof))['motionSettled'])

    def test_terminal_proof_requires_visual_geometry_not_boolean_presence(self):
        state = self.terminal_snapshot(); state['participants'][0].pop('visualGeometry')
        original = submission(state); terminal = _thaw(original.ticket.snapshot)
        terminal['motionRunning'] = False; terminal['participants'][0]['motionRunning'] = False
        proof = MotionStopProof(0, 1, 0, 25, _freeze(terminal))
        self.assertFalse(classify_submission(dataclasses.replace(original, terminal_proof=proof))['motionSettled'])

    def test_real_latch_proof_is_gui_only_and_never_uses_submitted_history(self):
        tracker = ThemeFrameTracker()
        class Window:
            def isExposed(self):return True
        state = self.terminal_snapshot(); tracker._window = Window(); tracker._provider = lambda:state
        tracker._capture(); tracker._synchronize(); original = tracker._latch[1]
        state['motionRunning'] = False; state['participants'][0]['motionRunning'] = False
        self.assertTrue(tracker.prove_motion_stopped_gui())
        self.assertIs(tracker._latch[1], original)
        observed = []; tracker._delivered.connect(observed.append, Qt.ConnectionType.DirectConnection)
        tracker._submit()
        self.assertFalse(tracker.prove_motion_stopped_gui())
        result = classify_submission(observed[-1])
        self.assertTrue(result['motionSettled'])
        self.assertTrue(_thaw(original.snapshot)['motionRunning'])
        tracker._window = None

    def test_motion_controller_direct_read_survives_qml_binding_signal_order(self):
        # Use the actual controller. At its own runningChanged notification,
        # another dependent readonly binding may still contain the previous value.
        from PySide6.QtCore import QObject, Slot, QMetaObject, QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlComponent, QQmlEngine
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        app = QGuiApplication.instance() or QGuiApplication([])
        type(self)._qml_app = app
        class Probe(QObject):
            def __init__(self):super().__init__();self.rows=[]
            @Slot(bool,bool,bool)
            def sample(self, controller, cached, direct):self.rows.append((controller,cached,direct))
        probe = Probe(); engine = QQmlEngine(); engine.rootContext().setContextProperty('probe',probe)
        component = QQmlComponent(engine)
        component.setData(b'''import QtQuick
import "components"
Item {
 id: root
 property QtObject aggregate: QtObject {readonly property bool running:controller.running}
 Component { id: factory; QtObject {property bool running:true; function settle() {running=false} } }
 MotionController { id: controller; property bool testEnabled:false
  onRunningChanged: if (testEnabled) probe.sample(running,root.aggregate.running,traceRunningNow())
 }
 Component.onCompleted: {controller.currentRecipe=factory.createObject(controller);controller.testEnabled=true}
 function stopRecipe() {controller.currentRecipe.running=false}
 function cleanupRecipe() {controller.currentRecipe=null}
}''', QUrl.fromLocalFile(str(Path(__file__).with_name('frame-signal-order-test.qml'))))
        root = component.create()
        self.assertIsNotNone(root, [str(error) for error in component.errors()])
        self.assertTrue(QMetaObject.invokeMethod(root,'stopRecipe',Qt.ConnectionType.DirectConnection))
        self.assertEqual(len(probe.rows),1)
        self.assertEqual(probe.rows[0][0],False)
        self.assertEqual(probe.rows[0][2],False)
        QMetaObject.invokeMethod(root,'cleanupRecipe',Qt.ConnectionType.DirectConnection)
        root.deleteLater()


if __name__ == '__main__':
    unittest.main()
