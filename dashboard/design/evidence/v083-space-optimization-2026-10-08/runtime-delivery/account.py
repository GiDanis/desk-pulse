"""Read the credential-free Account ChatGPT snapshot delivered by the PC."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QFileSystemWatcher, QObject, Property, QTimer, Signal

from module_state import module_state


MAX_AGE_SECONDS = 30 * 60
MAX_FILE_BYTES = 32 * 1024
DEFAULT_PATH = Path("/var/cache/smartpc-dashboard/account-chatgpt.json")


def read_account_state(path: Path, now: float | None = None) -> dict[str, Any]:
    if not path.exists():
        return module_state(status="unavailable", source="Codex App Server")
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("File account troppo grande")
        with path.open("rb") as stream:
            content = stream.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise ValueError("File account troppo grande")
        raw = json.loads(content)
        if not isinstance(raw, dict) or raw.get("version") != 1:
            raise ValueError("Formato account non valido")
        if raw.get("status") == "unavailable":
            return module_state(status="unavailable", source="Codex App Server",
                                 error=str(raw.get("error") or "Account non collegato")[:100])
        if raw.get("status") != "active" or not isinstance(raw.get("data"), dict):
            raise ValueError("Stato account non valido")
        updated_at = raw.get("updatedAt")
        if type(updated_at) not in (int, float) or not math.isfinite(updated_at) or updated_at <= 0:
            raise ValueError("Data account non valida")
        current = time.time() if now is None else now
        if updated_at > current + 300:
            raise ValueError("Orologio del PC non sincronizzato")
        status = "stale" if current - updated_at > MAX_AGE_SECONDS else "active"
        data = raw["data"]
        windows = data.get("windows")
        if not isinstance(windows, list):
            raise ValueError("Finestre account non valide")
        for window in windows:
            if not isinstance(window, dict):
                raise ValueError("Finestre account non valide")
            for key in ("usedPercent", "windowDurationMins", "resetsAt"):
                value = window.get(key)
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                    raise ValueError("Valori account non validi")
            used = window.get("usedPercent")
            if used is not None and not 0 <= used <= 100:
                raise ValueError("Percentuale account non valida")
        return module_state(status=status, source="Codex App Server", updated_at=updated_at,
                            data={"plan": data.get("plan") or "", "windows": windows,
                                  "credits": data.get("credits"), "resetCredits": data.get("resetCredits")})
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        msg = str(exc) if isinstance(exc, ValueError) and str(exc) else "Dati account non validi"
        return module_state(status="error", source="Codex App Server", error=msg)


class AccountService(QObject):
    changed = Signal()
    refreshFinished = Signal(bool, str)

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        super().__init__()
        self._path = path
        self._state = read_account_state(path)
        self._read_state = self._state
        self._file_signature = self._signature()
        self._closed = False

        self._watcher = QFileSystemWatcher(self)
        self._setup_watcher()
        self._watcher.fileChanged.connect(self._on_fs_changed)
        self._watcher.directoryChanged.connect(self._on_fs_changed)

        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(lambda: self.refresh(force=False))
        self._timer.start()

    def _setup_watcher(self) -> None:
        if self._path.exists() and str(self._path) not in self._watcher.files():
            self._watcher.addPath(str(self._path))
        if self._path.parent.exists() and str(self._path.parent) not in self._watcher.directories():
            self._watcher.addPath(str(self._path.parent))

    def _on_fs_changed(self, _path: str) -> None:
        if self._path.exists() and str(self._path) not in self._watcher.files():
            self._watcher.addPath(str(self._path))
        self.refresh(force=False)

    def _signature(self):
        try:
            stat = self._path.stat()
            return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        except OSError:
            return None

    @Property("QVariantMap", notify=changed)
    def moduleState(self) -> dict[str, Any]:
        return self._state

    def refresh(self, force: bool = True) -> bool:
        if self._closed:
            return False
        signature = self._signature()
        if force or signature != self._file_signature:
            self._read_state = read_account_state(self._path)
            self._file_signature = signature
            self._setup_watcher()
        state = self._read_state.copy()
        if state["status"] in ("active", "stale"):
            current = time.time()
            if state["updatedAt"] > current + 300:
                state["status"], state["error"] = "error", "Orologio del PC non sincronizzato"
            else:
                state["status"] = "stale" if current - state["updatedAt"] > MAX_AGE_SECONDS else "active"
        if state["status"] in ("error", "unavailable") and self._state["data"]:
            state = module_state(status=state["status"], source=state["source"],
                                 updated_at=self._state["updatedAt"], data=self._state["data"],
                                 error=state["error"] or "File dal PC assente · ultimi dati conservati")
        if state != self._state:
            self._state = state
            self.changed.emit()
        if force:
            ok = state["status"] in ("active", "stale")
            message = ("Cache riletta · dati precedenti dal PC" if state["status"] == "stale" else
                       "Cache riletta · gli aggiornamenti arrivano dal PC") if ok else state["error"] or "Account non collegato"
            self.refreshFinished.emit(ok, message)
        return True

    def close(self) -> None:
        self._closed = True
        self._timer.stop()
        self._watcher.blockSignals(True)
