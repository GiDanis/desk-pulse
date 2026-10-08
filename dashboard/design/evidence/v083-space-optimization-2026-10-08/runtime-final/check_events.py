"""Focused lifecycle and official-bulletin checks without a Qt display."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from event_core import EventEngine
from weather_alerts import normalize_bulletin


NOW = datetime(2026, 9, 30, 12, tzinfo=ZoneInfo("Europe/Rome")).timestamp()


def event(*, priority: int = 2, starts: float = NOW - 10, expires: float = NOW + 3600) -> dict:
    return {"version": 1, "id": "test:1", "source": "test", "category": "test",
            "priority": priority, "title": "Avviso", "detail": "Dettaglio",
            "issuedAt": NOW, "startsAt": starts, "expiresAt": expires,
            "revision": "1", "sourceUrl": "", "showOnHome": True}


class EventChecks(unittest.TestCase):
    def test_notification_categories_apply_at_all_hours_without_hiding_inbox(self) -> None:
        for priority in (2, 3):
            for quiet in (False, True):
                for silenced in (False, True):
                    with self.subTest(priority=priority, quiet=quiet, silenced=silenced):
                        engine = EventEngine(":memory:")
                        engine.replace_source("test", [event(priority=priority)])
                        snapshot = engine.snapshot(now=NOW, quiet=quiet,
                            silenced_categories=frozenset({"test"} if silenced else {"other"}))
                        self.assertEqual(bool(snapshot["banner"]), priority == 2 and not quiet and not silenced)
                        self.assertEqual(bool(snapshot["urgent"]), priority == 3 and not silenced)
                        self.assertEqual(snapshot["inbox"][0]["id"], "test:1")
                        self.assertEqual(snapshot["unreadCount"], 1)
                        engine.close()

    def test_unread_count_survives_delivery_and_restart_but_not_reading_or_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.sqlite3"
            engine = EventEngine(path)
            engine.replace_source("test", [event()])
            engine.mark_notified("test:1")
            self.assertEqual(engine.snapshot(now=NOW)["unreadCount"], 1)
            engine.close()
            engine = EventEngine(path)
            self.assertEqual(engine.snapshot(now=NOW)["unreadCount"], 1)
            engine.mark_seen("test:1")
            self.assertEqual(engine.snapshot(now=NOW)["unreadCount"], 0)
            engine.close()
            engine = EventEngine(path)
            self.assertEqual(engine.snapshot(now=NOW)["unreadCount"], 0)
            engine.replace_source("test", [])
            engine.replace_source("test", [event()])
            self.assertEqual(engine.snapshot(now=NOW)["unreadCount"], 1)
            self.assertEqual(engine.snapshot(now=NOW + 3601)["unreadCount"], 0)
            engine.replace_source("test", [], revision="new-valid-empty-snapshot")
            self.assertEqual(engine.source_revision("test"), "new-valid-empty-snapshot")
            engine.close()
            engine = EventEngine(path)
            self.assertEqual(engine.source_revision("test"), "new-valid-empty-snapshot")
            engine.close()

    def test_banner_format_persists_without_repeating_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.sqlite3"
            engine = EventEngine(path)
            engine.replace_source("test", [event()])
            self.assertEqual(engine.snapshot(now=NOW)["banner"]["bannerSize"], "small")
            engine.mark_notified("test:1")
            large = dict(event(), bannerSize="large")
            engine.replace_source("test", [large])
            self.assertEqual(engine.snapshot(now=NOW)["banner"], {})
            with self.assertRaises(ValueError):
                engine.replace_source("test", [dict(large, bannerSize="unknown")])
            engine.close()
            engine = EventEngine(path)
            self.assertEqual(engine.snapshot(now=NOW)["inbox"][0]["bannerSize"], "large")
            self.assertFalse(engine.snapshot(now=NOW)["banner"])
            engine.replace_source("test", [])
            engine.replace_source("test", [large])
            self.assertEqual(engine.snapshot(now=NOW)["banner"]["bannerSize"], "large")
            self.assertFalse(engine.snapshot(now=NOW, quiet=True)["banner"])
            engine.close()

    def test_dedup_escalation_and_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.sqlite3"
            engine = EventEngine(path)
            self.assertTrue(engine.replace_source("test", [event()]))
            self.assertEqual(engine.snapshot(now=NOW)["banner"]["id"], "test:1")
            engine.mark_notified("test:1")
            self.assertFalse(engine.replace_source("test", [event()]))
            self.assertEqual(engine.snapshot(now=NOW)["banner"], {})
            engine.close()
            engine = EventEngine(path)
            self.assertEqual(engine.snapshot(now=NOW)["banner"], {})
            self.assertTrue(engine.replace_source("test", [event(priority=3)]))
            self.assertEqual(engine.snapshot(now=NOW)["urgent"]["id"], "test:1")
            engine.dismiss("test:1")
            self.assertEqual(engine.snapshot(now=NOW)["urgent"], {})
            engine.close()
            engine = EventEngine(path)
            self.assertEqual(engine.snapshot(now=NOW)["urgent"], {})
            red = dict(event(priority=3), notificationRank=4, title="Allerta rossa")
            engine.replace_source("test", [red])
            self.assertEqual(engine.snapshot(now=NOW)["urgent"]["title"], "Allerta rossa")
            engine.dismiss("test:1")
            engine.replace_source("test", [])
            engine.replace_source("test", [red])
            self.assertTrue(engine.snapshot(now=NOW)["urgent"], "a reactivated alert is a new occurrence")
            engine.close()

    def test_future_expiry_cancellation_and_quiet(self) -> None:
        engine = EventEngine(":memory:")
        future = event(starts=NOW + 600)
        engine.replace_source("test", [future])
        self.assertEqual(engine.snapshot(now=NOW)["nextRelevantEvent"]["id"], "test:1")
        self.assertEqual(engine.snapshot(now=NOW)["banner"], {})
        self.assertEqual(engine.snapshot(now=NOW + 700, quiet=True)["banner"], {})
        self.assertEqual(engine.snapshot(now=NOW + 700)["banner"]["id"], "test:1")
        self.assertEqual(engine.snapshot(now=NOW + 3700)["inbox"], [])
        engine.replace_source("test", [])
        self.assertEqual(engine.snapshot(now=NOW)["inbox"], [])
        engine.close()

    def test_provider_collision_and_invalid_clock_do_not_replace_valid_event(self) -> None:
        engine = EventEngine(":memory:")
        engine.replace_source("test", [event(priority=3)])
        with self.assertRaises(ValueError):
            engine.replace_source("other", [dict(event(), source="other")])
        with self.assertRaises(ValueError):
            engine.replace_source("test", [dict(event(), expiresAt=float("nan"))])
        self.assertEqual(engine.snapshot(now=NOW)["urgent"]["id"], "test:1")
        self.assertFalse(engine.snapshot(now=NOW, silenced_categories=frozenset({"test"}))["urgent"])
        self.assertTrue(engine.snapshot(now=NOW, quiet=True)["urgent"], "quiet hours preserve urgency")
        engine.close()

    def test_bulletin_selects_angri_and_preserves_day_precision(self) -> None:
        quiet = "Assenza di fenomeni significativi prevedibili / NESSUNA ALLERTA"
        orange = "Moderata / ALLERTA ARANCIONE"
        angri = {"Comuni": ["Angri"], "Nome zona": "Monti di Sarno",
                 "Rappresentata nella mappa": orange,
                 "Per rischio idraulico": quiet, "Per rischio temporali": quiet,
                 "Per rischio idrogeologico": orange}
        other = dict(angri, Comuni=["Altro comune"])
        maps = {}
        for name in ("today", "tomorrow"):
            local = angri if name == "tomorrow" else dict(
                angri, **{"Rappresentata nella mappa": quiet,
                          "Per rischio idrogeologico": quiet})
            maps[name] = {"objects": {"zone": {"geometries": [
                {"properties": other}, {"properties": local}]}}}
        wrapper = {"date": "2026-09-30T10:00:00Z"}
        result = normalize_bulletin(wrapper, maps, "20260930_1400", NOW)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["priority"], 3)
        self.assertEqual(result[0]["id"], "dpc:Angri:2026-10-01")
        self.assertEqual(datetime.fromtimestamp(result[0]["startsAt"], ZoneInfo("Europe/Rome")).hour, 0)


if __name__ == "__main__":
    unittest.main()
