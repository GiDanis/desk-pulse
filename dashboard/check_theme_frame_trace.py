"""Immutable identity, phase invalidation and conservative frame classification."""
import dataclasses
import threading
import unittest
from theme_frame_trace import (FrameSubmission, FrameTicket, ThemeFrameTracker,
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


if __name__ == '__main__':
    unittest.main()
