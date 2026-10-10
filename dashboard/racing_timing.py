"""Small SignalR Core client and conservative MotoGP timing normalization."""

from copy import deepcopy
from datetime import datetime
import json
import time
from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkRequest, QAbstractSocket
from PySide6.QtWebSockets import QWebSocket
from sport_core import mapping, items, number, text, timestamp, ROME
from racing_details import metrics

TOPICS = [
    "Heartbeat",
    "SessionInfo",
    "SessionStatus",
    "TrackStatus",
    "DriverList",
    "TimingData",
    "LapCount",
    "RaceControlMessages",
    "TimingAppData",
    "TimingStats",
    "WeatherData",
]
BASE_TOPICS = TOPICS[:8]


def _merge_owned(old, new):
    if isinstance(new, dict):
        result = (
            old
            if isinstance(old, dict)
            else (
                {str(i): deepcopy(v) for i, v in enumerate(old)}
                if isinstance(old, list)
                else {}
            )
        )
        for key, value in new.items():
            result[key] = _merge_owned(result.get(key), value)
        return result
    return deepcopy(new)


def deep_merge(old, new):
    """Pure merge for callers; only the initial tree needs copying."""
    return _merge_owned(deepcopy(old), new)


def f1_date(value, offset):
    if not isinstance(value, str):
        return None
    if timestamp(value):
        return timestamp(value)
    if isinstance(offset, str):
        # SignalR uses unsigned offsets such as "08:00:00" as well as +08:00.
        offset = offset if offset.startswith(("+", "-")) else "+" + offset
        return timestamp(value + offset[:6])
    return None


class TimingState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.topics = {}
        self.receivedAt = 0
        self.dataAt = 0
        self.connected = False
        self.revision = getattr(self, "revision", 0) + 1
        self._render_revision = -1
        self._rendered = None

    def apply(self, topic, payload, now):
        if topic not in TOPICS or not isinstance(payload, (dict, list)):
            return
        if topic == "SessionInfo":
            old = mapping(self.topics.get(topic))
            new = mapping(payload)
            if old and any(
                new.get(k) is not None and old.get(k) is not None and new[k] != old[k]
                for k in ("Key", "StartDate", "Path")
            ):
                connected = self.connected
                self.reset()
                self.connected = connected
        self.topics[topic] = _merge_owned(self.topics.get(topic), payload)
        if topic != "Heartbeat":
            self.revision += 1
        self.receivedAt = now
        if topic == "TimingData":
            self.dataAt = now

    def present(self, now, year, verified=False):
        info = mapping(self.topics.get("SessionInfo"))
        offset = info.get("GmtOffset")
        start = f1_date(info.get("StartDate"), offset)
        end = f1_date(info.get("EndDate"), offset)
        raw_status = text(mapping(self.topics.get("SessionStatus")).get("Status"))
        active = (
            self.connected
            and raw_status == "Started"
            and start is not None
            and datetime.fromtimestamp(start, ROME).year == year
            and -900 <= now - start <= 6 * 3600
            and (end is None or now <= end + 3600)
            and 0 <= now - self.receivedAt <= 30
            and self.dataAt > 0
            and 0 <= now - self.dataAt <= 90
        )
        if self._rendered is not None and self._render_revision == self.revision:
            result = self._rendered.copy()
            result.update(
                active=bool(active and result["rows"]),
                isLive=bool(active and result["rows"] and verified),
                fetchedAt=self.receivedAt,
                dataAt=self.dataAt,
            )
            return result
        drivers = mapping(self.topics.get("DriverList"))
        rows = []
        for ident, line in mapping(
            mapping(self.topics.get("TimingData")).get("Lines")
        ).items():
            line = mapping(line)
            driver = mapping(drivers.get(ident))
            pos = number(line.get("Position"))
            if not pos or not driver:
                continue
            gap = text(line.get("GapToLeader"))
            best = text(mapping(line.get("BestLapTime")).get("Value"))
            app_line = mapping(
                mapping(mapping(self.topics.get("TimingAppData")).get("Lines")).get(
                    ident
                )
            )
            stints = mapping(app_line.get("Stints"))
            if isinstance(app_line.get("Stints"), list):
                stints = {str(i): s for i, s in enumerate(app_line["Stints"])}
            stint = (
                mapping(stints[max(stints, key=lambda k: number(k) or 0)])
                if stints
                else {}
            )
            sectors = line.get("Sectors")
            if isinstance(sectors, list):
                sectors = {str(i): s for i, s in enumerate(sectors)}
            interval = text(mapping(line.get("IntervalToPositionAhead")).get("Value"))
            detail = metrics(
                ("Posizione", pos),
                ("Team", driver.get("TeamName")),
                ("Distacco dal leader", gap),
                ("Distacco dal precedente", interval),
                ("Ultimo giro", mapping(line.get("LastLapTime")).get("Value")),
                ("Giro migliore", best),
                ("Giri completati", number(line.get("NumberOfLaps"))),
                ("Soste", number(line.get("NumberOfPitStops"))),
                ("Gomme", stint.get("Compound")),
                ("Giri sulle gomme", number(stint.get("TotalLaps"))),
                (
                    "Stato",
                    (
                        "Ai box"
                        if line.get("InPit")
                        else "Uscita box" if line.get("PitOut") else None
                    ),
                ),
                *[
                    (
                        "Settore " + str(i + 1),
                        mapping(mapping(sectors).get(str(i))).get("Value"),
                    )
                    for i in range(3)
                ],
            )
            rows.append(
                {
                    "id": str(ident),
                    "position": pos,
                    "name": text(driver.get("FullName") or driver.get("LastName")),
                    "team": text(driver.get("TeamName")),
                    "value": gap or best or "—",
                    "laps": number(line.get("NumberOfLaps")),
                    "status": "Ai box" if line.get("InPit") else "",
                    "points": None,
                    "detailRows": detail,
                }
            )
        rows.sort(key=lambda r: r["position"])
        weather = mapping(self.topics.get("WeatherData"))
        messages = mapping(self.topics.get("RaceControlMessages")).get("Messages")
        if isinstance(messages, dict):
            messages = [
                messages[k] for k in sorted(messages, key=lambda k: number(k) or 0)
            ]
        result = {
            "active": bool(active and rows),
            "isLive": bool(active and rows and verified),
            "name": text(info.get("Name")),
            "meeting": text(mapping(info.get("Meeting")).get("Name")),
            "start": start,
            "end": end,
            "status": raw_status or "unknown",
            "source": "F1 SignalR Core",
            "fetchedAt": self.receivedAt,
            "dataAt": self.dataAt,
            "rows": rows,
            "lap": number(mapping(self.topics.get("LapCount")).get("CurrentLap")),
            "totalLaps": number(mapping(self.topics.get("LapCount")).get("TotalLaps")),
            "trackStatus": text(mapping(self.topics.get("TrackStatus")).get("Message")),
            "infoRows": metrics(
                ("Stato pista", mapping(self.topics.get("TrackStatus")).get("Message")),
                (
                    "Temperatura aria",
                    (
                        str(weather["AirTemp"]) + " °C"
                        if weather.get("AirTemp") is not None
                        else None
                    ),
                ),
                (
                    "Temperatura asfalto",
                    (
                        str(weather["TrackTemp"]) + " °C"
                        if weather.get("TrackTemp") is not None
                        else None
                    ),
                ),
            ),
            "messages": [
                text(m.get("Message")) for m in items(messages)[-8:] if m.get("Message")
            ],
        }
        self._render_revision = self.revision
        self._rendered = result
        return result.copy()


class F1Timing(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = TimingState()
        self.enabled = False
        self._topics = TOPICS[:]
        self._buffer = ""
        self._failures = 0
        self.socket = QWebSocket()
        self.socket.connected.connect(self._opened)
        self.socket.textMessageReceived.connect(self._message)
        self.socket.disconnected.connect(self._closed)
        self.socket.errorOccurred.connect(self._failed)
        self._retry = QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.timeout.connect(self._connect)
        self._deadline = QTimer(self)
        self._deadline.setSingleShot(True)
        self._deadline.timeout.connect(self._failed)
        self._ping = QTimer(self)
        self._ping.setInterval(15000)
        self._ping.timeout.connect(self._keepalive)
        self._ping.start()

    def ensure(self, enabled):
        self.enabled = enabled
        if not enabled:
            self._retry.stop()
            self._deadline.stop()
            self.socket.abort()
            self.state.connected = False
        elif (
            self.socket.state() == QAbstractSocket.SocketState.UnconnectedState
            and not self._retry.isActive()
        ):
            self._connect()

    def _connect(self):
        if not self.enabled:
            return
        self.state.reset()
        self._buffer = ""
        request = QNetworkRequest(QUrl("wss://livetiming.formula1.com/signalrcore"))
        request.setRawHeader(b"User-Agent", b"SmartPC-Dashboard/0.6")
        self.socket.open(request)
        self._deadline.start(20000)

    def _opened(self):
        self.socket.sendTextMessage(
            json.dumps({"protocol": "json", "version": 1}) + "\x1e"
        )

    def _message(self, value):
        if len(value) + len(self._buffer) > 1_000_000:
            self.socket.abort()
            return
        self._buffer += value
        records = self._buffer.split("\x1e")
        self._buffer = records.pop()
        try:
            for record in records:
                if not record:
                    continue
                message = json.loads(record)
                if message == {}:
                    self.socket.sendTextMessage(
                        json.dumps(
                            {
                                "type": 1,
                                "invocationId": "1",
                                "target": "Subscribe",
                                "arguments": [self._topics],
                            }
                        )
                        + "\x1e"
                    )
                elif message.get("type") == 3:
                    if message.get("error"):
                        # Optional topics must not take away the timing that
                        # was already verified without authentication.
                        self._topics = BASE_TOPICS[:]
                        self.socket.abort()
                        return
                    snapshot = mapping(message.get("result"))
                    if not snapshot:
                        continue
                    self.state.connected = True
                    self._deadline.stop()
                    self._failures = 0
                    for topic in ["SessionInfo"] + [
                        t for t in snapshot if t != "SessionInfo"
                    ]:
                        if topic in snapshot:
                            self.state.apply(topic, snapshot[topic], time.time())
                    self.state.connected = True
                    self.changed.emit()
                elif message.get("type") == 1:
                    args = items(message.get("arguments"))
                    if len(args) >= 2 and args[0] in TOPICS:
                        self.state.apply(args[0], args[1], time.time())
                        self.state.connected = True
                elif message.get("type") == 7:
                    self.socket.abort()
        except (ValueError, TypeError, AttributeError):
            self.socket.abort()

    def _failed(self, *_):
        self.socket.abort()
        self._closed()

    def _closed(self):
        self._deadline.stop()
        self.state.connected = False
        self.changed.emit()
        if self.enabled and not self._retry.isActive():
            self._failures += 1
            self._retry.start(min(300, 30 * 2 ** min(self._failures, 3)) * 1000)

    def _keepalive(self):
        if self.socket.state() == QAbstractSocket.SocketState.ConnectedState:
            self.socket.sendTextMessage('{"type":6}\x1e')
            if self.state.receivedAt and time.time() - self.state.receivedAt > 60:
                self.socket.abort()

    def close(self):
        self.ensure(False)


def moto_timing(raw, snapshot, acquired, now, verified=False):
    head = mapping(mapping(raw).get("head"))
    result = {
        "active": False,
        "isLive": False,
        "rows": [],
        "source": "PulseLive timing",
        "fetchedAt": acquired,
        "name": text(head.get("session_name")),
        "rawStatus": text(head.get("session_status_id")),
        "category": text(head.get("category")),
        "lap": None,
        "totalLaps": number(head.get("num_laps")),
    }
    if head.get("category") != "MotoGP":
        return result
    # Validate against a category-filtered broadcast session in the same GP/date.
    candidates = []
    session_events = {}
    for event in snapshot.get("events", []):
        if event.get("shortName") != head.get("event_shortname"):
            continue
        for s in event["sessions"]:
            # Date in the gateway is local to the track; compare session time +/- a day
            # plus strict session timing ID, rather than misreading it as Italy midnight.
            gateway = str(head.get("datet", ""))
            if (
                s.get("timingId") == number(head.get("session_id"))
                and s["start"]
                and -900 <= now - s["start"] <= 6 * 3600
                and gateway
                in [
                    datetime.fromtimestamp(s["start"] + d * 86400, ROME).strftime(
                        "%Y%m%d"
                    )
                    for d in (-1, 0, 1)
                ]
            ):
                candidates.append(s)
                session_events[s["id"]] = event
    # Unknown A/R codes are not guessed. A verified broadcast with explicit
    # STARTED/IN_PROGRESS can authorize activity independently of that code.
    active_session = next(
        (
            s
            for s in candidates
            if s.get("broadcastActive") is True
            and (
                s.get("broadcastState") in ("STARTED", "IN_PROGRESS", "LIVE")
                or head.get("session_status_name")
                in ("STARTED", "IN_PROGRESS", "RUNNING", "LIVE")
            )
        ),
        None,
    )
    result["active"] = bool(
        active_session
        and 0 <= now - acquired <= 90
        and head.get("session_status_id") not in ("N", "F")
    )
    result["isLive"] = bool(result["active"] and verified)
    if active_session:
        event = session_events[active_session["id"]]
        result.update(eventId=event["id"], sessionId=active_session["id"],
                      meeting=event["name"], start=active_session["start"])
    for ident, row in mapping(raw.get("rider")).items():
        row = mapping(row)
        pos = number(row.get("pos"))
        if not pos or pos < 1:
            continue
        name = (
            text(row.get("rider_name")) + " " + text(row.get("rider_surname"))
        ).strip()
        value = text(row.get("gap_first")) or text(row.get("last_lap_time")) or "—"
        if value in ("0.000", "0"):
            value = "—"
        result["rows"].append(
            {
                "id": text(ident),
                "position": pos,
                "name": name,
                "team": text(row.get("team_name")),
                "value": value,
                "laps": number(row.get("num_lap")),
                "status": "Ai box" if row.get("on_pit") else "",
                "points": None,
                "detailRows": metrics(
                    ("Posizione", pos),
                    ("Team", row.get("team_name")),
                    ("Moto", row.get("bike_name")),
                    (
                        "Distacco dal leader",
                        (
                            row.get("gap_first")
                            if row.get("gap_first") not in ("0.000", "0", 0)
                            else None
                        ),
                    ),
                    (
                        "Distacco dal precedente",
                        (
                            row.get("gap_prev")
                            if row.get("gap_prev") not in ("0.000", "0", 0)
                            else None
                        ),
                    ),
                    (
                        "Ultimo giro",
                        (
                            row.get("last_lap_time")
                            if row.get("last_lap_time") not in ("0.000", "0", 0)
                            else None
                        ),
                    ),
                    (
                        "Tempo di riferimento",
                        (
                            row.get("lap_time")
                            if row.get("lap_time") not in ("0.000", "0", 0)
                            else None
                        ),
                    ),
                    ("Giri completati", number(row.get("num_lap"))),
                    ("Stato", "Ai box" if row.get("on_pit") else None),
                ),
            }
        )
    result["rows"].sort(key=lambda row: row["position"])
    result["active"] = bool(result["active"] and result["rows"])
    result["isLive"] = bool(result["active"] and verified)
    return result
