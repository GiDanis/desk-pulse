"""Persistent, UI-independent event policy for SmartPC.

Providers submit complete snapshots. The engine owns identity, expiry, ordering,
and delivery state so an unchanged provider refresh never reopens a notice.
"""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Any


HISTORY_SECONDS = 7 * 86400
MAX_PENDING_BANNERS = 20


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
    severity = event.get("weatherSeverity", "")
    if severity not in ("", "gialla", "arancione", "rossa"):
        raise ValueError("Invalid weather severity")
    # Compatible with caches written before structured severity was introduced.
    if not severity and event["source"] == "weather-alert":
        severity = {2: "gialla", 3: "arancione", 4: "rossa"}.get(event["notificationRank"], "")
    event["weatherSeverity"] = severity
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
    until = event.get("bannerUntil", event["expiresAt"])
    if type(until) not in (int, float) or not math.isfinite(until) or until < event["startsAt"]:
        raise ValueError("Invalid banner deadline")
    event["bannerUntil"] = min(until, event["expiresAt"])
    notice_revision = event.get("noticeRevision", "")
    if not isinstance(notice_revision, str) or len(notice_revision) > 100:
        raise ValueError("Invalid notification revision")
    event["noticeRevision"] = notice_revision
    return event


@lru_cache(maxsize=2048)
def _payload(text):
    # Owned by the decoder cache; public display values always get their own tree.
    return json.loads(text)


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
        if "skipped_level" not in columns:
            self.db.execute("ALTER TABLE events ADD COLUMN skipped_level INTEGER NOT NULL DEFAULT 0")
        self.db.execute("UPDATE events SET rank=priority WHERE rank=0")
        self.db.execute("CREATE INDEX IF NOT EXISTS events_expires ON events(expires_at)")
        self.db.execute("CREATE TABLE IF NOT EXISTS source_revisions (source TEXT PRIMARY KEY, revision TEXT NOT NULL)")
        self.db.commit()
        self._row_cache = None
        self._deadline_cache = None

    def source_revision(self, source: str) -> str:
        row = self.db.execute("SELECT revision FROM source_revisions WHERE source=?", (source,)).fetchone()
        if row is not None:
            return row["revision"]
        return max((str(_payload(row["payload"]).get("revision", "")) for row in
                    self.db.execute("SELECT payload FROM events WHERE source=?", (source,))), default="")

    def migrate_identity(self, old_id: str, new_id: str, source: str) -> None:
        """Keep delivery/read state when a provider gains stable window IDs."""
        with self.db:
            if not self.db.execute("SELECT 1 FROM events WHERE id=?", (new_id,)).fetchone():
                self.db.execute("UPDATE events SET id=? WHERE id=? AND source=?", (new_id, old_id, source))

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
                    previous_revision = json.loads(old["payload"]).get("noticeRevision", "")
                    if old["cancelled"] or (previous_revision and event["noticeRevision"] and previous_revision != event["noticeRevision"]):
                        self.db.execute("""UPDATE events SET notified_level=0, dismissed_level=0,
                            skipped_level=0, seen=0 WHERE id=?""", (event["id"],))
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
        revision = (self.db.total_changes, self.db.execute('PRAGMA data_version').fetchone()[0])
        cached = self._row_cache
        if cached and cached[0] == revision and cached[1] <= now < cached[2]:
            return cached[3]
        rows = self.db.execute("""SELECT * FROM events WHERE cancelled=0 AND expires_at>?
            ORDER BY priority DESC, rank DESC, starts_at ASC, id ASC""", (now,)).fetchall()
        self._row_cache = (revision, now, min((row['expires_at'] for row in rows), default=math.inf), rows)
        return rows

    @staticmethod
    def _display(row: sqlite3.Row, now: float) -> dict[str, Any]:
        event = deepcopy(_payload(row["payload"]))
        event.setdefault("bannerSize", "small")
        event["seen"] = bool(row["seen"])
        event["upcoming"] = row["starts_at"] > now
        event["cancelled"] = bool(row["cancelled"])
        event["expired"] = row["expires_at"] <= now
        event["presented"] = row["notified_level"] >= row["rank"]
        event["deliveryState"] = ("revocato" if row["cancelled"] else "scaduto" if event["expired"]
                                  else "presentato" if event["presented"] else "solo elenco · coda piena" if row["skipped_level"] >= row["rank"]
                                  else "solo elenco · fuori tempo" if event.get("bannerUntil", row["expires_at"]) <= now
                                  else "in attesa")
        return event

    def snapshot(self, *, now: float | None = None, quiet: bool = False,
                 silenced_categories: frozenset[str] = frozenset(), history: bool = False) -> dict[str, Any]:
        current = time.time() if now is None else now
        rows = self._rows(current)
        urgent = next((self._display(row, current) for row in rows
                       if row["starts_at"] <= current and row["priority"] == 3
                       and _payload(row["payload"])["category"] not in silenced_categories
                       and row["dismissed_level"] < row["rank"]), {})
        pending = [row for row in rows
                       if not quiet and row["starts_at"] <= current and row["priority"] == 2
                       and _payload(row["payload"]).get("bannerUntil", row["expires_at"]) > current
                       and _payload(row["payload"])["category"] not in silenced_categories
                       and row["notified_level"] < row["rank"] and row["skipped_level"] < row["rank"]]
        pending.sort(key=lambda row: (-row["rank"], _payload(row["payload"])["issuedAt"], row["id"]))
        if len(pending) > MAX_PENDING_BANNERS:
            with self.db:
                self.db.executemany("UPDATE events SET skipped_level=MAX(skipped_level,rank) WHERE id=?",
                                    [(row["id"],) for row in pending[MAX_PENDING_BANNERS:]])
            pending = pending[:MAX_PENDING_BANNERS]
            rows = self._rows(current)
        banner = self._display(pending[0], current) if pending else {}
        future = sorted((row for row in rows if row["starts_at"] > current
                         and _payload(row["payload"]).get("showOnHome")),
                        key=lambda row: (row["starts_at"], -row["priority"]))
        next_event = self._display(future[0], current) if future else {}
        visible = self.db.execute("""SELECT * FROM events WHERE expires_at>=?
            ORDER BY starts_at DESC, id LIMIT 200""", (current - HISTORY_SECONDS,)).fetchall() if history else rows[:100]
        inbox = [self._display(row, current) for row in visible]
        return {"urgent": urgent, "banner": banner, "inbox": inbox,
                "unreadCount": sum(not row["seen"] for row in rows),
                "nextRelevantEvent": next_event, "historyMode": history,
                "queueCount": len(pending), "queuedEvents": [self._display(row, current) for row in pending[:20]],
                "interruptionStatus": "silenzio" if quiet else "attive"}

    def lookup(self, event_id: str, now: float) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM events WHERE id=? AND cancelled=0 AND expires_at>?",
                              (event_id, now)).fetchone()
        return self._display(row, now) if row else {}

    def next_deadline(self, now: float) -> float:
        rows = self._rows(now)
        cached = self._deadline_cache
        if cached and cached[0] is rows and cached[1] <= now < cached[2]:
            return min(now + 300, cached[2])
        deadlines = [math.inf]
        for row in rows:
            deadlines.extend(value for value in (row["starts_at"], row["expires_at"],
                             _payload(row["payload"]).get("bannerUntil", row["expires_at"])) if value > now)
        self._deadline_cache = (rows, now, min(deadlines))
        return min(now + 300, self._deadline_cache[2])  # Wall-clock recovery remains bounded.

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
