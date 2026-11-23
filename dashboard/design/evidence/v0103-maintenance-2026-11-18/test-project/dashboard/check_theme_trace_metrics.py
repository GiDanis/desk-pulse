import unittest
from theme_trace_metrics import build_trace_metrics, percentile


class MetricsTests(unittest.TestCase):
    def test_noop_keeps_denominator_without_fake_latency(self):
        raw={'requests':[{'requestId':'a','operation':'selectDraft','startedNs':0,'endedNs':1,'outcome':'noVisualChange'},
                         {'requestId':'b','operation':'selectDraft','startedNs':0,'endedNs':100,'outcome':'coherentSubmission'}],
             'events':[], 'incompleteReasons':[], 'recordingCostNsByRequest':{'a':10,'b':20},
             'frameSummaries':[{'requestId':'b','revision':1,'submittedSessionNs':100,'queuedDeliveryLagNs':0,
                'firstCoherent':True,'firstSettled':True,'participants':[]}]}
        r=build_trace_metrics(raw)
        self.assertTrue(r['complete']);self.assertEqual(r['requestedCount'],2)
        self.assertEqual(r['requestToCoherentSubmissionMs']['count'],1)
        self.assertEqual(r['outcomes']['noVisualChange'],1)
        raw['requests'][0]['outcome']='timeout'
        self.assertFalse(build_trace_metrics(raw)['complete'])

    def test_supplementary_scenarios_do_not_inflate_requirements(self):
        from check_theme_runtime_fixtures import coverage_summary
        rows=[{'id':'required','covers':['r1'],'status':'passed'},
              {'id':'supplementary','covers':[],'status':'passed'}]
        result=coverage_summary([{'coverage':rows}],rows)
        self.assertEqual(result['uniqueCanonicalRequirementsPassed'],1)
        self.assertEqual(result['uniqueScenariosPassed'],2)
        self.assertEqual(result['missingRequirements'],[])

    def test_historical_percentile_floor(self):
        self.assertEqual(percentile(list(range(100)),.95),94)
        self.assertIsNone(percentile([],.95))

    def test_preempted_coherent_request_has_diagnostic_but_no_fake_settlement(self):
        raw={'requests':[
            {'requestId':'a','operation':'selectDraft','startedNs':0,'endedNs':100,'outcome':'coherentSubmission','terminalMetadata':{'revision':1}},
            {'requestId':'b','operation':'selectDraft','startedNs':120,'endedNs':250,'outcome':'coherentSubmission','terminalMetadata':{'revision':2}}],
            'events':[
                {'event':'frame.submission','requestId':'a','timestampNs':105,'metadata':{'frameSerial':1,'revision':1,'motionSettled':False,'submittedNs':100}},
                {'event':'motion.stopped','requestId':'a','timestampNs':160,'metadata':{'instanceId':'home','revision':1,'motionEvent':'layout.swap'}},
                {'event':'appearance.published','requestId':'b','timestampNs':180,'metadata':{'revision':2}}],
            'incompleteReasons':[], 'recordingCostNsByRequest':{'a':10,'b':20},
            'frameSummaries':[
                {'requestId':'a','revision':1,'submittedSessionNs':100,'queuedDeliveryLagNs':5,'firstCoherent':True,'firstSettled':False,'participants':[]},
                {'requestId':'b','revision':2,'submittedSessionNs':250,'queuedDeliveryLagNs':0,'firstCoherent':True,'firstSettled':True,'participants':[]}]}
        result=build_trace_metrics(raw)
        self.assertFalse(result['complete'])
        self.assertEqual(result['incompleteReasons'],['missingOrDuplicateMotionSettledSummary'])
        self.assertEqual(result['requestedCount'],2)
        self.assertEqual(result['requestToCoherentSubmissionMs']['count'],2)
        self.assertEqual(result['requestToMotionSettledFrameMs']['count'],1)
        self.assertEqual(result['settledFramesMissing'],1)
        missing=result['missingSettledFrames'][0]
        self.assertEqual(missing['requestId'],'a')
        self.assertEqual(missing['revision'],1)
        self.assertEqual(missing['lastRecordedSubmission']['motionSettled'],False)
        self.assertEqual(missing['nextRequest']['requestId'],'b')
        self.assertEqual(missing['nextPublication']['revision'],2)
        self.assertEqual(len(missing['guiStopObservations']),1)
        self.assertEqual(missing['observation'],'nextRevisionPublishedWithoutObservedSettledFrame')


if __name__=='__main__':unittest.main()
