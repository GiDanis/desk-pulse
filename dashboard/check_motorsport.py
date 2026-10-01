"""Motorsport regressions using captured provider payloads, never network."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from motorsport_core import (
    f1_calendar,
    f1_standings,
    apply_f1_results,
    moto_calendar,
    moto_programme,
    moto_sessions,
    moto_result_rows,
    read_cache,
    save_cache,
    present,
    stamp,
    MotorClient,
    JOLPICA,
    load_event,
)
from racing_timing import TimingState, deep_merge, moto_timing, f1_date
from sport_core import timestamp, ProviderError
from racing_details import open_results, open_session, load_driver, OPENF1

FIXTURES = Path(__file__).with_name("fixtures")


def fixture(name):
    return json.loads((FIXTURES / ("racing-" + name + ".json")).read_text())


def snapshot(kind):
    return fixture(kind + "-normalized")["snapshot"]


class Checks(unittest.TestCase):
    def test_additional_metadata_and_cold_cache(self):
        raw = fixture("f1-results")
        data = snapshot("f1")
        apply_f1_results(data, raw, "RAC", "15")
        event = next(e for e in data["events"] if e["round"] == "15")
        row = next(s for s in event["sessions"] if s["kind"] == "RAC")["results"][1]
        self.assertEqual(row["grid"], 8)
        self.assertEqual(row["gridChange"], 6)
        self.assertTrue(row["fastestLap"])
        moto = next(
            e
            for e in moto_calendar(fixture("moto-events"), 2026)
            if e["shortName"] == "JPN"
        )
        moto_programme(fixture("moto-japan-broadcast"), moto, 2026)
        self.assertEqual(moto["circuitData"]["length"], 4801)
        self.assertEqual(moto["circuitData"]["raceLaps"], 24)
        classification = moto_result_rows(fixture("moto-last-results"))
        self.assertEqual(classification[0]["bike"], "Ducati")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "f1.json"
            save_cache(path, data)
            view = present(read_cache(path, "f1"), time.time(), from_cache=True)
            event = next(e for e in view["events"] if e["round"] == "15")
            row = next(s for s in event["sessions"] if s["kind"] == "RAC")["results"][1]
            self.assertTrue(
                any(
                    r["label"] == "Variazione griglia → arrivo"
                    for r in row["detailRows"]
                )
            )

    def test_openf1_identity_encoding_results_and_stints(self):
        responses = fixture("openf1-details")
        event = f1_calendar(fixture("f1-2025-last-calendar"), 2025)[0]
        session = next(s for s in event["sessions"] if s["kind"] == "FP1")
        data = {"kind": "f1", "year": 2025, "events": [event]}

        class Replay:
            def get(self, url):
                if url not in responses:
                    raise ProviderError("URL inatteso: " + url)
                return deepcopy(responses[url])

        client = Replay()
        open_results(client, data, event, session)
        self.assertEqual(session["resultSource"], "OpenF1")
        self.assertEqual(len(session["results"]), 20)
        # A recorded standings winner is not used as the practice driver name.
        self.assertEqual(session["results"][0]["number"], 4)
        load_driver(
            client, data, event["id"], session["id"], session["results"][0]["id"]
        )
        self.assertTrue(session["results"][0]["stints"])
        wrong = deepcopy(event)
        wrong["circuitData"]["country"] = "Japan"
        with self.assertRaises(ValueError):
            open_session(client, data, wrong, session)
        session["start"] = time.time() - 10
        self.assertIsNone(open_session(client, data, event, session))

    def test_extra_failure_keeps_results_and_openf1_budget(self):
        data = snapshot("f1")
        event = present(data, time.time())["lastEvent"]
        session = next(s for s in event["sessions"] if s["kind"] == "RAC")
        before = deepcopy(session["results"])

        class Broken:
            def get(self, url):
                raise ProviderError("offline")

        load_driver(Broken(), data, event["id"], session["id"], before[0]["id"])
        row = next(e for e in data["events"] if e["id"] == event["id"])["sessions"]
        row = next(s for s in row if s["kind"] == "RAC")["results"][0]
        self.assertEqual(row["value"], before[0]["value"])
        self.assertTrue(row["extraError"])
        client = MotorClient()
        client._open_times = [time.time()] * 25
        with self.assertRaises(ProviderError):
            client.get(OPENF1 + "sessions?year=2025")
        self.assertFalse(client.request_count)

    def test_calendar_identity_timezone_missing_time(self):
        raw = fixture("f1-calendar")
        events = f1_calendar(raw, 2026)
        self.assertEqual(len(events), 23)
        japan = next(
            e
            for e in moto_calendar(fixture("moto-events"), 2026)
            if e["shortName"] == "JPN"
        )
        moto_programme(fixture("moto-japan-broadcast"), japan, 2026)
        self.assertEqual(
            [s["kind"] for s in japan["sessions"]],
            ["FP1", "PR", "FP2", "Q1", "Q2", "SPR", "WUP", "RAC"],
        )
        self.assertEqual(stamp(japan["sessions"][0]["start"]), "Ven 02/10 · 03:45")
        self.assertEqual(stamp(japan["sessions"][-1]["start"]), "Dom 04/10 · 07:00")
        self.assertFalse(any(s["broadcastActive"] for s in japan["sessions"]))
        raw["MRData"]["RaceTable"]["Races"][0].pop("time", None)
        self.assertIsNone(f1_calendar(raw, 2026)[0]["start"])
        with self.assertRaises(ValueError):
            f1_calendar(raw, 2025)
        with self.assertRaises(ValueError):
            moto_programme(fixture("moto-japan-broadcast"), japan, 2025)

    def test_standings_results_no_invented_zero(self):
        pilots, round_id = f1_standings(fixture("f1-drivers"), 2026)
        self.assertGreater(len(pilots), 20)
        self.assertEqual(round_id, "15")
        teams, _ = f1_standings(fixture("f1-constructors"), 2026, True)
        self.assertGreater(len(teams), 9)
        data = snapshot("f1")
        apply_f1_results(data, fixture("f1-results"), "RAC", "15")
        self.assertTrue(
            any(s["results"] for e in data["events"] for s in e["sessions"])
        )
        with self.assertRaises(ValueError):
            apply_f1_results(data, fixture("f1-results"), "RAC", "14")
        race = moto_result_rows(fixture("moto-last-results"))
        laps = moto_result_rows(fixture("moto-last-results"), "FP1")
        self.assertNotEqual(race[0]["value"], laps[0]["value"])
        self.assertTrue(race[0]["name"])
        self.assertTrue(race[0]["value"])

    def test_programme_results_merge_keeps_timing_identity(self):
        rows = fixture("moto-last-sessions")
        event_id = rows[0]["event"]["id"]
        category = rows[0]["category"]["id"]
        event = {
            "id": "motogp:2026:" + event_id,
            "providerId": event_id,
            "sessions": [],
        }
        kind = (
            rows[0]["type"] + str(rows[0]["number"])
            if rows[0]["type"] in ("FP", "Q")
            else rows[0]["type"]
        )
        event["sessions"] = [
            {
                "id": event["id"] + ":" + kind,
                "timingId": 7,
                "broadcastActive": True,
                "broadcastState": "IN_PROGRESS",
                "end": time.time() + 100,
            }
        ]
        moto_sessions(rows, event, category)
        target = next(s for s in event["sessions"] if s["kind"] == kind)
        self.assertTrue(target["broadcastActive"])
        self.assertEqual(target["timingId"], 7)
        with self.assertRaises(ValueError):
            moto_sessions(rows, event, "Moto3")

    def test_cache_atomic_failure_and_wrong_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "motor.json"
            data = snapshot("motogp")
            save_cache(path, data)
            self.assertEqual(read_cache(path, "motogp"), data)
            self.assertIsNone(read_cache(path, "f1"))
            original = path.read_bytes()
            bad = deepcopy(data)
            bad["events"][0]["sessions"] = [None]
            with self.assertRaises((ValueError, AttributeError)):
                save_cache(path, bad)
            self.assertEqual(path.read_bytes(), original)
            bad = deepcopy(data)
            bad["events"][0]["sessions"] = [
                {
                    "id": "bad",
                    "name": "GP",
                    "kind": "RAC",
                    "state": "scheduled",
                    "start": "oops",
                    "results": [],
                }
            ]
            with self.assertRaises(ValueError):
                save_cache(path, bad)
            bad = deepcopy(data)
            bad["events"][0]["start"] = "oops"
            with self.assertRaises(ValueError):
                save_cache(path, bad)
            path.write_text('{"schemaVersion":2}')
            self.assertIsNone(read_cache(path, "motogp"))

    def test_detail_failure_keeps_results_scoped_and_calendar_age(self):
        data = snapshot("f1")
        past = present(data, time.time())["lastEvent"]
        old = deepcopy(
            next(e for e in data["events"] if e["id"] == past["id"])["sessions"]
        )

        class Broken:
            def get(self, url):
                raise ProviderError("offline")

        result = load_event(Broken(), data, past["id"])
        self.assertEqual(result["detailErrorEventId"], past["id"])
        self.assertTrue(result["detailError"])
        self.assertEqual(result["fetchedAt"], data["fetchedAt"])
        self.assertEqual(
            next(e for e in result["events"] if e["id"] == past["id"])["sessions"], old
        )
        self.assertFalse(
            present(result, time.time(), from_cache=True).get("isLive", False)
        )

    def test_signalr_partial_merge_session_reset_and_stale(self):
        now = time.time()
        state = TimingState()
        start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 600))
        state.apply("SessionInfo", {"Key": 1, "Name": "Race", "StartDate": start}, now)
        state.apply(
            "DriverList", {"1": {"FullName": "Driver", "TeamName": "Team"}}, now
        )
        state.apply(
            "TimingData",
            {
                "Lines": {
                    "1": {
                        "Position": "1",
                        "BestLapTime": {"Value": "1:20.000"},
                        "Sectors": [{"Value": "a"}, {"Value": "b"}],
                    }
                }
            },
            now,
        )
        state.apply("SessionStatus", {"Status": "Started"}, now)
        state.connected = True
        year = time.gmtime(now).tm_year
        self.assertTrue(state.present(now, year)["active"])
        self.assertFalse(state.present(now, year)["isLive"])
        self.assertTrue(state.present(now, year, True)["isLive"])
        state.apply(
            "TimingData", {"Lines": {"1": {"Sectors": {"1": {"Value": "c"}}}}}, now + 1
        )
        self.assertEqual(
            state.topics["TimingData"]["Lines"]["1"]["Sectors"]["0"]["Value"], "a"
        )
        self.assertEqual(
            state.topics["TimingData"]["Lines"]["1"]["BestLapTime"]["Value"], "1:20.000"
        )
        state.apply("Heartbeat", {}, now + 100)
        self.assertFalse(state.present(now + 100, year, True)["active"])
        state.apply("SessionInfo", {"Key": 2}, now + 101)
        self.assertNotIn("TimingData", state.topics)
        self.assertIsNone(f1_date("2026-10-04T10:00:00", None))
        self.assertEqual(
            f1_date("2026-10-04T10:00:00", "+09:00"), timestamp("2026-10-04T01:00:00Z")
        )

    def test_gateway_category_status_identity_age_and_empty_rows(self):
        raw = fixture("moto-lite")
        data = snapshot("motogp")
        now = time.time()
        self.assertFalse(
            moto_timing(raw, data, now, now, True)["active"]
        )  # Real Moto3/N payload.
        head = raw["head"]
        head.update(
            category="MotoGP",
            session_status_id="A",
            event_shortname="TST",
            datet=int(time.strftime("%Y%m%d", time.gmtime(now))),
            session_id="1",
        )
        data["events"] = [
            {
                "shortName": "TST",
                "sessions": [
                    {
                        "start": now - 60,
                        "timingId": 1,
                        "broadcastActive": True,
                        "broadcastState": "IN_PROGRESS",
                    }
                ],
            }
        ]
        row = next(iter(raw["rider"].values()))
        row.update(pos=1)
        data["events"][0]["sessions"][0]["broadcastState"] = "unknown"
        self.assertFalse(moto_timing(raw, data, now, now, True)["active"])
        data["events"][0]["sessions"][0]["broadcastState"] = "IN_PROGRESS"
        self.assertTrue(moto_timing(raw, data, now, now, True)["isLive"])
        self.assertEqual(moto_timing(raw, data, now, now)["rows"][0]["value"], "—")
        self.assertFalse(moto_timing(raw, data, now - 100, now, True)["active"])
        head["session_id"] = "9"
        self.assertFalse(moto_timing(raw, data, now, now, True)["active"])
        head["session_id"] = "1"
        head["session_status_id"] = "N"
        self.assertFalse(moto_timing(raw, data, now, now, True)["active"])
        head["session_status_id"] = "A"
        raw["rider"] = {}
        self.assertFalse(moto_timing(raw, data, now, now, True)["active"])

    def test_budget_no_request_after_exhaustion(self):
        client = MotorClient()
        client._jolpica_times = [time.time()] * 400
        with self.assertRaises(ProviderError) as caught:
            client.get(JOLPICA + "2026.json?limit=100")
        self.assertGreater(caught.exception.retry_after, 3500)
        self.assertEqual(client.request_count, {})


if __name__ == "__main__":
    unittest.main()
