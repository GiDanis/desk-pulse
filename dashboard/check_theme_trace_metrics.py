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


if __name__=='__main__':unittest.main()
