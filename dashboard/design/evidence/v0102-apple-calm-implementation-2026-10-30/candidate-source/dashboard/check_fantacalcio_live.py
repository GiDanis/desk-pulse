"""Recorded real protobuf, seasonal persistence, history and live lifecycle checks."""

import base64
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication
from fantacalcio_core import parse_page, read_cache, save_cache
from fantacalcio_live import (
    LiveClient,
    FantasyClient,
    check_descriptor,
    decode_message,
    normalize_live,
    live_window,
    estimated_fantavote,
)
from fantacalcio import FantacalcioService, Worker
from sport_core import ProviderError

FIXTURES = Path(__file__).with_name("fixtures")
BINARY = base64.b64decode((FIXTURES / "fantacalcio-live-2023-24-4.base64").read_text())
SCHEMA = json.loads((FIXTURES / "fantacalcio-live-schema.json").read_text())
HISTORY = (FIXTURES / "fantacalcio-2023-24-4-fiorentina-atalanta.html").read_text()
APP = QCoreApplication.instance() or QCoreApplication([])


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.decoded = decode_message(BINARY)
        self.page = normalize_live(self.decoded, "2023-24/4", time.time())
        self.match = dict(
            competitionId="serie_a",
            season="2023/2024",
            round="4",
            homeTeamId="fiorentina",
            awayTeamId="atalanta",
            canonicalMatchId="fixture:recorded",
            homeTeam="Fiorentina",
            awayTeam="Atalanta",
            kickoffUtc=self.page["teams"][0]["kickoffUtc"],
            status="finished",
        )

    def test_recorded_binary_and_published_redaction_agree(self):
        self.assertEqual(len(self.decoded["protoData"]), 8)
        history = parse_page(HISTORY, "2023-24/4", time.time())
        live = self.page["teams"][0]["players"]
        published = next(t for t in history["teams"] if t["teamId"] == "fiorentina")[
            "players"
        ]
        for name, expected in {
            "Terracciano": (5.5, 3.5),
            "Duncan": (6.5, 7.5),
            "Bonaventura": (7, 10),
            "Barak": (None, None),
        }.items():
            left = next(p for p in live if p["name"] == name)
            right = next(p for p in published if p["name"] == name)
            self.assertEqual((left["vote"], left["fantavote"]), expected)
            self.assertEqual((right["vote"], right["fantavote"]), expected)
        self.assertFalse(
            any(p["role"] == "ALL" for t in self.page["teams"] for p in t["players"])
        )

    def test_season_discovery_once_across_days_and_restart_then_rollover(self):
        client = LiveClient(self.directory)
        html = HISTORY + '<a href="/api/v1/Excel/votes/18/4">Excel</a>'
        with patch.object(
            client, "_request", return_value=(html.encode(), time.time())
        ) as request:
            self.assertEqual(client.season_id("2023-24/4"), 18)
            self.assertEqual(client.season_id("2023-24/5"), 18)
            self.assertEqual(request.call_count, 1)
        restarted = LiveClient(self.directory)
        with patch.object(
            restarted, "_request", side_effect=AssertionError("repeat discovery")
        ):
            self.assertEqual(restarted.season_id("2023-24/38"), 18)
        html2 = html.replace("2023-24", "2024-25").replace("votes/18/4", "votes/19/4")
        with patch.object(
            restarted, "_request", return_value=(html2.encode(), time.time())
        ) as request:
            self.assertEqual(restarted.season_id("2024-25/4"), 19)
            self.assertEqual(request.call_count, 1)
        self.assertEqual(
            LiveClient(self.directory).seasons, {"2023-24": 18, "2024-25": 19}
        )

    def test_discovery_rejects_wrong_archive_and_corrupt_cache(self):
        (self.directory / "fantacalcio-seasons.json").write_text(
            '{"schemaVersion":1,"seasons":null}'
        )
        client = LiveClient(self.directory)
        with patch.object(
            client, "_request", return_value=(HISTORY.encode(), time.time())
        ):
            with self.assertRaises(ValueError):
                client.season_id("2024-25/4")
        self.assertEqual(client.seasons, {})

    def test_anonymous_signing_uuid_key_and_whole_day_cache(self):
        client = LiveClient(self.directory)
        client.seasons = {"2023-24": 18}
        client.descriptor_ok = True
        resource = "https://api.fantacalcio.it/v1/st/18/matches/live/4.dat"
        answer = json.dumps(
            {
                "uuid": {
                    "errors": [],
                    "resources": [{"signedUri": resource + "?token=private"}],
                }
            }
        ).encode()
        with patch.object(
            client,
            "_request",
            side_effect=[(answer, time.time()), (BINARY, time.time())],
        ) as request:
            first = client.get("2023-24/4")
            second = client.get("2023-24/4")
            self.assertEqual(first, second)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(
                request.call_args_list[0].args[1], {"resourcesUri": [resource]}
            )
        self.assertNotIn("token", json.dumps(first))

    def test_404_cooldown_and_published_fallback(self):
        client = FantasyClient(self.directory)
        client.live.seasons = {"2023-24": 18}
        response = json.dumps(
            {"uuid": {"errors": [{"statusCode": 404}], "resources": []}}
        ).encode()
        match = dict(self.match, status="live", kickoffUtc=time.time() - 60)
        with patch.object(
            client.live, "_request", return_value=(response, time.time())
        ) as request:
            with self.assertRaises(ProviderError) as error:
                client.live.get("2023-24/4")
            self.assertEqual(error.exception.http_status, 404)
            with self.assertRaises(ProviderError):
                client.live.get("2023-24/4")
            self.assertEqual(request.call_count, 1)
        history = parse_page(HISTORY, "2023-24/4", time.time())
        with patch.object(client, "get", return_value=history):
            page = client.get_for_match("2023-24/4", 30, match)
        self.assertIn("liveNotice", page)
        self.assertFalse(page.get("provisional", False))

    def test_finished_history_does_not_query_live(self):
        client = FantasyClient(self.directory)
        history = parse_page(HISTORY, "2023-24/4", time.time())
        with patch.object(
            client.live, "get", side_effect=AssertionError("historical live")
        ), patch.object(client, "get", return_value=history):
            self.assertEqual(
                client.get_for_match("2023-24/4", 21600, self.match), history
            )
        # Even within the live window, published grades take precedence.
        recent = dict(self.match, kickoffUtc=time.time() - 7200)
        for team in history["teams"]:
            team["kickoffUtc"] = recent["kickoffUtc"]
        with patch.object(
            client.live, "get", side_effect=AssertionError("published live")
        ), patch.object(client, "get", return_value=history):
            self.assertEqual(client.get_for_match("2023-24/4", 30, recent), history)

    def test_provisional_never_overwrites_published_cache(self):
        path = self.directory / "fantacalcio-2023-24-4.json"
        history = parse_page(HISTORY, "2023-24/4", time.time())
        save_cache(path, history)
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            save_cache(path, self.page)
        self.assertEqual(path.read_bytes(), before)

        class Fake:
            def get_for_match(inner, key, ttl, match):
                return deepcopy(self.page)

        Worker(Fake(), "2023-24/4", path, False, 30, self.match).run()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(read_cache(path, "2023-24/4"), history)

    def test_wire_corruption_size_and_unknown_fields(self):
        for body in (
            b"\x0a\x7f\x01",
            b"\x08\x01",
            b"\x00",
            b"\x0b",
            b"\x0a\x80",
            b"\x80" * 11,
            b"x" * 1_000_001,
        ):
            with self.assertRaises(ValueError):
                decode_message(body)
        # Unknown varint field 31 is skipped without changing known values.
        self.assertEqual(decode_message(BINARY + b"\xf8\x01\x02"), self.decoded)

    def test_descriptor_change_and_auth_failure_are_explicit(self):
        import math

        def encode(descriptor):
            seed, result = 98, []
            for char in json.dumps(descriptor):
                x = math.sin(seed) * 10000
                result.append(
                    chr(ord(char) + (math.floor((x - math.floor(x)) * 2) - 1))
                )
                seed += 1
            return "".join(result)

        check_descriptor(encode(SCHEMA))
        changed = deepcopy(SCHEMA)
        changed["nested"]["LiveMessage"]["nested"]["Player"]["fields"]["vote"][
            "type"
        ] = "string"
        with self.assertRaises(ValueError):
            check_descriptor(encode(changed))
        client = LiveClient(self.directory)
        client.seasons = {"2023-24": 18}
        response = json.dumps(
            {"uuid": {"errors": [{"statusCode": 401}], "resources": []}}
        ).encode()
        with patch.object(
            client, "_request", return_value=(response, time.time())
        ) as request:
            for _ in range(2):
                with self.assertRaises(ProviderError) as error:
                    client.get("2023-24/4")
                self.assertEqual(error.exception.http_status, 401)
            self.assertEqual(request.call_count, 1)

    def test_ambiguous_bonuses_never_invent_exact_fantavote(self):
        self.assertEqual(estimated_fantavote(6, [3, 22, 1, 14]), 9.5)
        self.assertEqual(estimated_fantavote(6, [7, 4]), 8)
        for events in ([3, 9], [1, 2], [16], [21], [23], [20], [999]):
            self.assertIsNone(estimated_fantavote(6, events))
        self.assertIsNone(estimated_fantavote(None, [3]))

    def test_selection_and_expiry_never_show_wrong_live_match(self):
        service = FantacalcioService(self.directory, auto_refresh=False)
        self.addCleanup(service.close)
        current = dict(self.match, status="live", kickoffUtc=time.time() - 60)
        service.set_match(current)
        self.page["teams"][0]["kickoffUtc"] = current["kickoffUtc"]
        self.page["teams"][1]["kickoffUtc"] = current["kickoffUtc"]
        service.live_page = self.page
        self.assertTrue(service.moduleState["data"]["provisional"])
        self.assertEqual(service.interval(), 30)
        service.set_match(dict(current, awayTeamId="inter"))
        self.assertFalse(service.moduleState["data"]["provisional"])
        service.set_match(current)
        self.page["fetchedAt"] = time.time() - 121
        self.assertFalse(service.moduleState["data"]["provisional"])
        self.assertFalse(live_window(self.match))
        self.assertFalse(
            live_window(dict(current, status="scheduled", kickoffUtc=time.time() + 901))
        )
        self.assertFalse(live_window(dict(current, competitionId="football:42")))
        self.assertTrue(
            live_window(dict(current, status="scheduled", kickoffUtc=time.time() + 899))
        )


if __name__ == "__main__":
    unittest.main()
