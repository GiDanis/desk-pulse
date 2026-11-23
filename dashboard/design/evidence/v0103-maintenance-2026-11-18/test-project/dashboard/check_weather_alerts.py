"""Offline checks for bulletin caching, validation and network reuse."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from weather_alerts import BULLETIN_PAGE, RAW_FILES, BulletinProvider

NOW = datetime(2026, 9, 30, 12, tzinfo=ZoneInfo("Europe/Rome")).timestamp()


def bulletin_fixture(now: float, *, key: str | None = None, colour: str = "ALLERTA GIALLA") -> dict[str, bytes]:
    key = key or datetime.fromtimestamp(now, ZoneInfo("Europe/Rome")).strftime("%Y%m%d_%H%M")
    quiet = "NESSUNA ALLERTA"
    properties = {"Comuni": ["Angri", "Altro comune"], "Nome zona": "Monti di Sarno",
                  "Rappresentata nella mappa": colour, "Per rischio idraulico": quiet,
                  "Per rischio temporali": quiet, "Per rischio idrogeologico": colour}
    topology = {"objects": {"zone": {"geometries": [{"properties": properties}]}}}
    wrapper = {"date": datetime.fromtimestamp(now, ZoneInfo("UTC")).isoformat()}
    responses = {BULLETIN_PAGE: f"files/xml/{key}.zip".encode()}
    for day in ("today", "tomorrow"):
        url = f"{RAW_FILES}topojson/{key}_{day}.json"
        wrapper[day] = {"topo_json": url}
        responses[url] = json.dumps(topology).encode()
    responses[f"{RAW_FILES}{key}.json"] = json.dumps(wrapper).encode()
    return responses


class BulletinCacheChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "dpc-bulletin.json"
        self.responses = bulletin_fixture(NOW)

    def fetch(self, provider: BulletinProvider, *, now: float = NOW, responses: dict | None = None):
        fixtures = self.responses if responses is None else responses
        with patch("weather_alerts._read", side_effect=lambda url, _: fixtures[url]) as read:
            return provider.refresh(now), read.call_count

    def test_same_key_skips_metadata_and_maps_after_restart(self) -> None:
        snapshot, calls = self.fetch(BulletinProvider(self.path))
        self.assertEqual(calls, 4)
        self.assertEqual(len(snapshot.events), 2)
        original_issued = snapshot.events[0]["issuedAt"]
        reused, calls = self.fetch(BulletinProvider(self.path), now=NOW + 60)
        self.assertEqual(calls, 1)
        self.assertTrue(reused.unchanged)
        self.assertEqual(reused.fetched_at, NOW)
        self.assertEqual(reused.checked_at, NOW + 60)
        self.assertEqual(reused.events[0]["issuedAt"], original_issued)
        self.assertEqual(list(self.path.parent.glob("dpc-*.json")), [self.path])

    def test_offline_restart_keeps_only_unexpired_alerts(self) -> None:
        self.fetch(BulletinProvider(self.path))
        with patch("weather_alerts._read", side_effect=OSError("offline")) as read:
            restarted = BulletinProvider(self.path)
            self.assertEqual(len(restarted.load(NOW).events), 2)
            read.assert_not_called()
            with self.assertRaises(OSError):
                restarted.refresh(NOW + 60)
            cached = restarted.load(NOW + 25 * 3600)
            self.assertEqual(len(cached.events), 1)
            self.assertFalse(cached.events[0]["startsAt"] > NOW + 25 * 3600)
            self.assertTrue(cached.from_cache)
            self.assertIsNone(restarted.load(NOW + 49 * 3600))

    def test_invalid_new_bulletin_preserves_previous_file(self) -> None:
        self.fetch(BulletinProvider(self.path))
        previous = self.path.read_bytes()
        invalid = bulletin_fixture(NOW + 60, colour="LIVELLO SCONOSCIUTO")
        with self.assertRaises(ValueError):
            self.fetch(BulletinProvider(self.path), now=NOW + 60, responses=invalid)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(len(BulletinProvider(self.path).load(NOW + 60).events), 2)

    def test_atomic_write_failure_preserves_old_cache_and_live_result(self) -> None:
        provider = BulletinProvider(self.path)
        self.fetch(provider)
        previous = self.path.read_bytes()
        newer = bulletin_fixture(NOW + 60, colour="ALLERTA ARANCIONE")
        with patch("weather_alerts.os.replace", side_effect=OSError("disco non scrivibile")):
            snapshot, _ = self.fetch(provider, now=NOW + 60, responses=newer)
        self.assertTrue(snapshot.cache_error)
        self.assertEqual(snapshot.events[0]["priority"], 3)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.glob("dpc-*.json")), [self.path])
        self.assertEqual(provider.load(NOW + 60).key, snapshot.key)

    def test_valid_empty_bulletin_and_corrupt_cache(self) -> None:
        empty = bulletin_fixture(NOW, colour="NESSUNA ALLERTA")
        snapshot, _ = self.fetch(BulletinProvider(self.path), responses=empty)
        self.assertEqual(snapshot.events, [])
        self.assertIsNotNone(BulletinProvider(self.path).load(NOW))
        self.path.write_text("{incomplete", encoding="utf-8")
        self.assertIsNone(BulletinProvider(self.path).load(NOW))
        snapshot, calls = self.fetch(BulletinProvider(self.path))
        self.assertEqual(calls, 4)
        self.assertEqual(len(snapshot.events), 2)

    def test_older_announced_key_cannot_replace_newer_cache(self) -> None:
        provider = BulletinProvider(self.path)
        self.fetch(provider, now=NOW + 60, responses=bulletin_fixture(NOW + 60))
        previous = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.fetch(provider, now=NOW + 120)
        self.assertEqual(self.path.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
