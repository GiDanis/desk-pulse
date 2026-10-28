"""Regression: mixed qualifying pace must not retire a valid slower finisher."""
import math,unittest
from game_protocol import finish_window,race_budget

class FinishWindowChecks(unittest.TestCase):
    def test_slower_three_lap_finisher_gets_a_full_lap_of_margin(self):
        fastest,slowest,laps=23.5,35.7,3
        winner=fastest*laps;last=slowest*laps
        self.assertGreater(last,winner+30.)
        deadline=min(race_budget('oval-1',laps),winner+finish_window([fastest,slowest],laps))
        self.assertGreaterEqual(deadline,last+slowest-1e-9)
    def test_longer_races_account_for_accumulated_pace_gap(self):
        for laps in (3,5,10):
            times=[22.,24.,25.,30.,36.]
            window=finish_window(times,laps)
            self.assertGreaterEqual(min(times)*laps+window,max(times)*(laps+1))
    def test_empty_or_missing_qualifying_data_keeps_legacy_floor(self):
        self.assertEqual(finish_window([],3),30.)
        self.assertEqual(finish_window([None,None],3),30.)
        self.assertEqual(finish_window([23.,23.],3),30.)
    def test_invalid_pace_is_rejected(self):
        for pace in (0.,-1.,float('nan'),float('inf')):
            with self.assertRaises(ValueError):finish_window([23.,pace],3)
    def test_invalid_race_target_is_rejected(self):
        for laps in (0,-1,3.,True):
            with self.assertRaises(ValueError):finish_window([23.,36.],laps)
    def test_existing_overall_budget_still_bounds_extreme_pace(self):
        window=finish_window([20.,600.],10)
        global_limit=race_budget('oval-1',10)
        self.assertEqual(min(global_limit,200.+window),global_limit)

if __name__=='__main__':unittest.main(verbosity=2)
