"""Multi-competition identity, nullability, calendar and durable cache checks."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from sport_core import fotmob_detail, ProviderError
from sport_team_core import parse_team, present, save_cache, read_cache, refresh

FIXTURES = Path(__file__).with_name("fixtures")
RAW = json.loads((FIXTURES / "sport-team-inter.json").read_text())
NOW = 1790868107.0


class TeamTests(unittest.TestCase):
    def profile(self):
        return parse_team(deepcopy(RAW), "8636", "inter", time.time())

    def test_background_polling_reaches_next_kickoff(self):
        from sport_team_core import profile_interval

        now = 1790868107
        self.assertEqual(profile_interval([], now), 21600)
        self.assertEqual(
            profile_interval(
                [{"status": "scheduled", "kickoffUtc": now + 4 * 3600}], now
            ),
            3 * 3600,
        )
        self.assertEqual(
            profile_interval([{"status": "scheduled", "kickoffUtc": now + 1800}], now),
            120,
        )
        self.assertEqual(
            profile_interval([{"status": "live", "kickoffUtc": now - 1800}], now), 60
        )
        self.assertEqual(
            profile_interval([{"status": "live", "kickoffUtc": now - 86400}], now),
            21600,
        )
        self.assertEqual(
            profile_interval([{"status": "scheduled", "kickoffUtc": None}], now), 21600
        )

    def test_real_profile_and_all_published_competitions(self):
        d = self.profile()
        p = present(d, NOW, "inter")
        self.assertEqual(len(d["fixtures"]), 53)
        self.assertEqual(
            {m["providerLeagueId"] for m in d["fixtures"]}, {42, 55, 141, 489}
        )
        self.assertEqual(len(d["squad"]), 25)
        self.assertEqual(d["coach"], "Cristian Chivu")
        self.assertEqual(d["standing"]["points"], 13)
        self.assertEqual(d["capacity"], 75817)
        self.assertEqual(len(p["upcoming"]), 42)
        self.assertEqual(p["upcoming"][0]["providerMatchId"], "6367342")
        self.assertEqual(p["results"][0]["providerMatchId"], "5749681")

    def test_unconfirmed_dates_and_missing_scores(self):
        d = self.profile()
        p = present(d, NOW, "inter")
        tentative = [m for m in p["upcoming"] if m["dateTentative"]]
        self.assertTrue(tentative)
        self.assertTrue(
            all(
                m["kickoffUtc"] is None and "confermare" in m["when"] for m in tentative
            )
        )
        self.assertTrue(
            all(m["homeScore"] is None and m["scoreText"] == "—" for m in p["upcoming"])
        )
        self.assertFalse(any(m["isLive"] for m in p["fixtures"]))

    def test_nullable_and_empty_profile_sections(self):
        r = deepcopy(RAW)
        r["squad"] = None
        r["overview"]["venue"] = None
        r["table"] = None
        r["fixtures"]["allFixtures"]["fixtures"] = []
        d = parse_team(r, "8636", "inter", time.time())
        self.assertEqual(d["squad"], [])
        self.assertEqual(d["fixtures"], [])
        self.assertIsNone(d["capacity"])
        self.assertEqual(d["standing"], {})

    def test_wrong_club_rejected(self):
        with self.assertRaises(ValueError):
            parse_team(RAW, "999", "inter", time.time())
        r = deepcopy(RAW)
        r["fixtures"]["allFixtures"]["fixtures"][0]["home"]["id"] = 1
        r["fixtures"]["allFixtures"]["fixtures"][0]["away"]["id"] = 2
        with self.assertRaises(ValueError):
            parse_team(r, "8636", "inter", time.time())

    def test_future_details_use_parent_competition_and_provider_ids(self):
        d = self.profile()
        for mid in ("6106251", "6367342"):
            m = next(m for m in d["fixtures"] if m["providerMatchId"] == mid)
            raw = json.loads(
                (FIXTURES / ("sport-team-detail-" + mid + ".json")).read_text()
            )
            result = fotmob_detail(raw, m)
            self.assertEqual(result["status"], "scheduled")
            self.assertIsNone(result["homeScore"])
            self.assertTrue(result["venue"])
            self.assertEqual(result["stats"], [])
            pending = deepcopy(m)
            pending["rawStatus"]["matchDateTbd"] = True
            pending["dateTentative"] = True
            pending["kickoffUtc"] = None
            unconfirmed = fotmob_detail(raw, pending)
            self.assertIsNone(unconfirmed["kickoffUtc"])
            self.assertEqual(unconfirmed["dateLabel"], "")
            wrong = deepcopy(raw)
            wrong["general"]["parentLeagueId"] = 99
            with self.assertRaises(ValueError):
                fotmob_detail(wrong, m)
            wrong = deepcopy(raw)
            wrong["header"]["teams"][0]["id"] = 99
            with self.assertRaises(ValueError):
                fotmob_detail(wrong, m)

    def test_atomic_cache_and_wrong_club_cache_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "team.json"
            d = self.profile()
            save_cache(path, d)
            self.assertEqual(read_cache(path, "8636", "inter"), d)
            self.assertIsNone(read_cache(path, "999", "inter"))
            with patch("sport_team_core.os.replace", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    save_cache(path, d)
            self.assertEqual(read_cache(path, "8636", "inter"), d)
            self.assertFalse(list(Path(directory).glob("*.tmp")))
            path.write_text("{")
            self.assertIsNone(read_cache(path, "8636", "inter"))

    def test_failed_detail_preserves_profile_and_error_is_scoped(self):
        d = self.profile()
        m = next(m for m in d["fixtures"] if m["providerMatchId"] == "6106251")

        class Client:
            def get(self, url):
                raise ProviderError("offline")

        result = refresh(Client(), "8636", "inter", d, m["canonicalMatchId"], True)
        self.assertEqual(result["fixtures"], d["fixtures"])
        self.assertEqual(result["detailErrorMatchId"], m["canonicalMatchId"])
        self.assertTrue(result["detailError"])


if __name__ == "__main__":
    unittest.main()
