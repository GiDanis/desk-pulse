"""Editorial source, match identity, player joins and vote/cache semantics."""

import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from fantacalcio_core import (
    parse_page,
    presentation,
    grade,
    eligible,
    page_key,
    save_cache,
    read_cache,
)
from sport_core import fotmob_detail

FIXTURES = Path(__file__).with_name("fixtures")
HTML = (FIXTURES / "fantacalcio-2026-27-5-roma-inter.html").read_text()
SNAPSHOT = json.loads((FIXTURES / "sport-normalized-sample.json").read_text())
ORIGINAL = next(m for m in SNAPSHOT["fixtures"] if m["providerMatchId"] == "5749681")
DETAIL = json.loads((FIXTURES / "fantacalcio-fotmob-roma-inter.json").read_text())


class FantasyTests(unittest.TestCase):
    def page(self):
        return parse_page(HTML, "2026-27/5", time.time())

    def match(self):
        return fotmob_detail(DETAIL, ORIGINAL)

    def test_real_editorial_votes_and_full_rosters(self):
        data = presentation(self.page(), self.match())
        self.assertTrue(data["matched"])
        self.assertTrue(data["published"])
        self.assertEqual(data["warning"], "")
        self.assertEqual([len(t["players"]) for t in data["teams"]], [23, 23])
        for t in data["teams"]:
            self.assertEqual(sum(p["group"] == "Titolari" for p in t["players"]), 11)
            self.assertEqual(sum(p["group"] == "Subentrati" for p in t["players"]), 5)
            self.assertEqual(sum(p["group"] == "Panchina" for p in t["players"]), 7)
        josep = data["teams"][1]["players"][0]
        self.assertEqual(josep["name"], "Josep Martínez")
        self.assertEqual(josep["vote"], 6.5)
        self.assertEqual(josep["fantavote"], 4.5)
        self.assertTrue(
            all(
                p["vote"] is None
                for t in data["teams"]
                for p in t["players"]
                if p["group"] == "Panchina"
            )
        )
        self.assertNotEqual(
            josep["vote"],
            DETAIL["content"]["lineup"]["awayTeam"]["starters"][0]["performance"][
                "rating"
            ],
        )

    def test_editorial_column_is_identified_not_other_sources(self):
        # The provider changes labels without moving its columns: take the
        # identified column, whose real Josep Martinez statistical vote is 6.
        switched = (
            HTML.replace('title="Redazione Fantacalcio"', 'title="TEMP"')
            .replace('title="Voto Statistico"', 'title="Redazione Fantacalcio"')
            .replace('title="TEMP"', 'title="Voto Statistico"')
        )
        p = parse_page(switched, "2026-27/5", time.time())
        j = next(t for t in p["teams"] if t["teamId"] == "inter")["players"][0]
        self.assertEqual(j["vote"], 6)
        self.assertEqual(j["fantavote"], 4)
        with self.assertRaises(ValueError):
            parse_page(
                HTML.replace('title="Redazione Fantacalcio"', 'title="Unknown"'),
                "2026-27/5",
                time.time(),
            )

    def test_only_serie_a_and_correct_round_season(self):
        m = self.match()
        self.assertTrue(eligible(m))
        self.assertEqual(page_key(m), "2026-27/5")
        for league in (42, 141, 489):
            other = dict(
                m, competitionId="football:" + str(league), providerLeagueId=league
            )
            self.assertFalse(eligible(other))
            self.assertFalse(presentation(self.page(), other)["teams"])
        with self.assertRaises(ValueError):
            parse_page(HTML, "2025-26/5", time.time())
        with self.assertRaises(ValueError):
            parse_page(HTML, "2026-27/6", time.time())
        favourite = dict(m, competitionId="football:55", providerLeagueId=55, round="")
        favourite = fotmob_detail(DETAIL, favourite)
        self.assertEqual(page_key(favourite), "2026-27/5")

    def test_no_votes_for_different_fixture_or_kickoff(self):
        p = self.page()
        m = self.match()
        for wrong in [
            dict(m, awayTeamId="milan"),
            dict(m, kickoffUtc=m["kickoffUtc"] + 86400),
            dict(m, round="4"),
        ]:
            d = presentation(p, wrong)
            self.assertFalse(d["published"])
            self.assertFalse(d["matched"])
            self.assertTrue(
                all(row["vote"] is None for t in d["teams"] for row in t["players"])
            )

    def test_missing_sv_placeholder_and_invalid_numeric_votes(self):
        for token in ("", "—", "55", "56"):
            self.assertEqual(grade(token), (None, "—"))
        self.assertEqual(grade("s.v."), (None, "SV"))
        self.assertEqual(grade("6,5", base=True), (6.5, "6,5"))
        self.assertEqual(grade("-1"), (-1.0, "-1"))
        for token in ("nan", "inf", "999", "ab"):
            self.assertRaises(ValueError, grade, token)

    def test_ambiguous_names_never_get_another_players_vote(self):
        m = self.match()
        p = self.page()
        roster = m["lineups"][1]["squad"]
        roster.append(dict(roster[0], id="new-player", name="Josep Martinez 2"))
        d = presentation(p, m)
        self.assertTrue(d["warning"])
        joseps = [
            r for r in d["teams"][1]["players"] if r["id"] in ("772168", "new-player")
        ]
        self.assertTrue(all(r["vote"] is None for r in joseps))
        self.assertTrue(
            any(
                r["name"] == "Martinez Jo."
                and r["vote"] == 6.5
                and r["group"] == "Voti fonte"
                for r in d["teams"][1]["players"]
            )
        )

    def test_atomic_cache_and_reject_wrong_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "voti.json"
            p = self.page()
            save_cache(path, p)
            self.assertEqual(read_cache(path, "2026-27/5"), p)
            self.assertIsNone(read_cache(path, "2026-27/6"))
            with patch("fantacalcio_core.os.replace", side_effect=OSError("disk")):
                self.assertRaises(OSError, save_cache, path, p)
            self.assertEqual(read_cache(path, "2026-27/5"), p)
            self.assertFalse(list(Path(directory).glob("*.tmp")))
            raw = json.loads(path.read_text())
            raw["page"]["source"] = "FotMob"
            path.write_text(json.dumps(raw))
            self.assertIsNone(read_cache(path, "2026-27/5"))


if __name__ == "__main__":
    unittest.main()
