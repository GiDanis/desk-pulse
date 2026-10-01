"""Persistent, UI-independent event policy for SmartPC.

Providers submit complete snapshots. The engine owns identity, expiry, ordering,
and delivery state so an unchanged provider refresh never reopens a notice.
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Any


HISTORY_SECONDS = 7 * 86400


def validate_event(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("Unsupported event format")
    event = dict(value)
    for key, limit in (("id", 160), ("source", 60), ("category", 40),
                       ("title", 100), ("detail", 240)):
        field = event.get(key)
        if not isinstance(field, str) or not field or len(field) > limit:
            raise ValueError(f"Invalid event {key}")
    if type(event.get("priority")) is not int or event["priority"] not in (1, 2, 3):
        raise ValueError("Invalid event priority")
    event["bannerSize"] = event.get("bannerSize", "small")
    if event["bannerSize"] not in ("small", "large"):
        raise ValueError("Invalid event banner size")
    event["notificationRank"] = event.get("notificationRank", event["priority"])
    if type(event["notificationRank"]) is not int or not 1 <= event["notificationRank"] <= 100:
        raise ValueError("Invalid event notification rank")
    for key in ("issuedAt", "startsAt", "expiresAt"):
        if type(event.get(key)) not in (int, float) or not math.isfinite(event[key]) or event[key] < 0:
            raise ValueError(f"Invalid event {key}")
    if event["expiresAt"] <= event["startsAt"]:
        raise ValueError("Event validity is empty")
    url = event.get("sourceUrl", "")
    if not isinstance(url, str) or len(url) > 500 or (url and not url.startswith("https://")):
        raise ValueError("Invalid event source URL")
    event["sourceUrl"] = url
    event["sourceLabel"] = event.get("sourceLabel", event["source"])
    if not isinstance(event["sourceLabel"], str) or not event["sourceLabel"] or len(event["sourceLabel"]) > 60:
        raise ValueError("Invalid event source label")
    event["revision"] = str(event.get("revision", ""))[:100]
    event["showOnHome"] = event.get("showOnHome") is True
    return event


class EventEngine:
    def __init__(self, path: Path | str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.is_closed = False
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        if path != ":memory:":
            self.db.execute("PRAGMA journal_mode = WAL")
            self.db.execute("PRAGMA synchronous = NORMAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            priority INTEGER NOT NULL,
            rank INTEGER NOT NULL DEFAULT 0,
            starts_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            payload TEXT NOT NULL,
            notified_level INTEGER NOT NULL DEFAULT 0,
            dismissed_level INTEGER NOT NULL DEFAULT 0,
            seen INTEGER NOT NULL DEFAULT 0,
            cancelled INTEGER NOT NULL DEFAULT 0
        )""")
        columns = {row["name"] for row in self.db.execute("PRAGMA table_info(events)")}
        if "rank" not in columns:
            self.db.execute("ALTER TABLE events ADD COLUMN rank INTEGER NOT NULL DEFAULT 0")
        self.db.execute("UPDATE events SET rank=priority WHERE rank=0")
        self.db.execute("CREATE INDEX IF NOT EXISTS events_expires ON events(expires_at)")
        self.db.execute("CREATE TABLE IF NOT EXISTS source_revisions (source TEXT PRIMARY KEY, revision TEXT NOT NULL)")
        self.db.commit()

    def source_revision(self, source: str) -> str:
        row = self.db.execute("SELECT revision FROM source_revisions WHERE source=?", (source,)).fetchone()
        if row is not None:
            return row["revision"]
        return max((str(json.loads(row["payload"]).get("revision", "")) for row in
                    self.db.execute("SELECT payload FROM events WHERE source=?", (source,))), default="")

    def replace_source(self, source: str, values: list[dict[str, Any]], *, revision: str | None = None) -> bool:
        """Apply one *valid* provider snapshot atomically, including cancellations."""
        if self.is_closed:
            return False
        if revision is not None and (not isinstance(revision, str) or not revision or len(revision) > 100):
            raise ValueError("Invalid source revision")
        events = [validate_event(value) for value in values]
        if any(value["source"] != source for value in events):
            raise ValueError("Mixed event sources")
        ids = [value["id"] for value in events]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate ids in provider snapshot")
        changed = False
        with self.db:
            for event in events:
                payload = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                old = self.db.execute("SELECT payload, source, cancelled FROM events WHERE id=?", (event["id"],)).fetchone()
                if old is not None and old["source"] != source:
                    raise ValueError("Event id already belongs to another source")
                if old is None:
                    self.db.execute("""INSERT INTO events
                        (id, source, priority, rank, starts_at, expires_at, payload)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (event["id"], source, event["priority"], event["notificationRank"], event["startsAt"], event["expiresAt"], payload))
                    changed = True
                elif old["payload"] != payload or old["cancelled"]:
                    self.db.execute("""UPDATE events SET priority=?, rank=?, starts_at=?, expires_at=?,
                        payload=?, cancelled=0 WHERE id=?""",
                        (event["priority"], event["notificationRank"], event["startsAt"], event["expiresAt"], payload, event["id"]))
                    if old["cancelled"]:
                        self.db.execute("""UPDATE events SET notified_level=0, dismissed_level=0,
                            seen=0 WHERE id=?""", (event["id"],))
                    changed = True
            active = self.db.execute("SELECT id FROM events WHERE source=? AND cancelled=0", (source,)).fetchall()
            for row in active:
                if row["id"] not in ids:
                    self.db.execute("UPDATE events SET cancelled=1 WHERE id=?", (row["id"],))
                    changed = True
            if revision is not None:
                self.db.execute("INSERT INTO source_revisions VALUES (?, ?) ON CONFLICT(source) DO UPDATE SET revision=excluded.revision",
                                (source, revision))
        return changed

    def _rows(self, now: float) -> list[sqlite3.Row]:
        return self.db.execute("""SELECT * FROM events WHERE cancelled=0 AND expires_at>?
            ORDER BY priority DESC, rank DESC, starts_at ASC, id ASC""", (now,)).fetchall()

    @staticmethod
    def _display(row: sqlite3.Row, now: float) -> dict[str, Any]:
        event = json.loads(row["payload"])
        event.setdefault("bannerSize", "small")
        event["seen"] = bool(row["seen"])
        event["upcoming"] = row["starts_at"] > now
        return event

    def snapshot(self, *, now: float | None = None, quiet: bool = False,
                 silenced_categories: frozenset[str] = frozenset()) -> dict[str, Any]:
        current = time.time() if now is None else now
        rows = self._rows(current)
        urgent = next((self._display(row, current) for row in rows
                       if row["starts_at"] <= current and row["priority"] == 3
                       and json.loads(row["payload"])["category"] not in silenced_categories
                       and row["dismissed_level"] < row["rank"]), {})
        banner = next((self._display(row, current) for row in rows
                       if not quiet and row["starts_at"] <= current and row["priority"] == 2
                       and json.loads(row["payload"])["category"] not in silenced_categories
                       and row["notified_level"] < row["rank"]), {})
        future = sorted((row for row in rows if row["starts_at"] > current
                         and json.loads(row["payload"]).get("showOnHome")),
                        key=lambda row: (row["starts_at"], -row["priority"]))
        next_event = self._display(future[0], current) if future else {}
        inbox = [self._display(row, current) for row in rows[:20]]
        return {"urgent": urgent, "banner": banner, "inbox": inbox,
                "unreadCount": sum(not row["seen"] for row in rows[:20]),
                "nextRelevantEvent": next_event}

    def mark_notified(self, event_id: str) -> None:
        with self.db:
            self.db.execute("""UPDATE events SET notified_level=MAX(notified_level, rank)
                WHERE id=?""", (event_id,))

    def dismiss(self, event_id: str) -> None:
        with self.db:
            self.db.execute("""UPDATE events SET dismissed_level=MAX(dismissed_level, rank),
                notified_level=MAX(notified_level, rank), seen=1 WHERE id=?""", (event_id,))

    def mark_seen(self, event_id: str) -> None:
        with self.db:
            self.db.execute("UPDATE events SET seen=1 WHERE id=?", (event_id,))

    def prune(self, now: float | None = None) -> None:
        current = time.time() if now is None else now
        with self.db:
            self.db.execute("DELETE FROM events WHERE expires_at<?", (current - HISTORY_SECONDS,))

    def close(self) -> None:
        self.is_closed = True
        self.db.close()
