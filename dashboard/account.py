"""Read the credential-free Account ChatGPT snapshot delivered by the PC."""

from __future__ import annotations

import json
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
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("version") != 1:
            raise ValueError("Formato account non valido")
        if raw.get("status") == "unavailable":
            return module_state(status="unavailable", source="Codex App Server",
                                 error=str(raw.get("error") or "Account non collegato")[:100])
        if raw.get("status") != "active" or not isinstance(raw.get("data"), dict):
            raise ValueError("Stato account non valido")
        updated_at = raw.get("updatedAt")
        if not isinstance(updated_at, (int, float)) or updated_at <= 0:
            raise ValueError("Data account non valida")
        current = time.time() if now is None else now
        if updated_at > current + 300:
            raise ValueError("Orologio del PC non sincronizzato")
        status = "stale" if current - updated_at > MAX_AGE_SECONDS else "active"
        data = raw["data"]
        windows = data.get("windows")
        if not isinstance(windows, list):
            raise ValueError("Finestre account non valide")
        return module_state(status=status, source="Codex App Server", updated_at=updated_at,
                            data={"plan": data.get("plan") or "", "windows": windows,
                                  "credits": data.get("credits"), "resetCredits": data.get("resetCredits")})
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        msg = str(exc) if isinstance(exc, ValueError) and str(exc) else "Dati account non validi"
        return module_state(status="error", source="Codex App Server", error=msg)


class AccountService(QObject):
    changed = Signal()

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        super().__init__()
        self._path = path
        self._state = read_account_state(path)

        self._watcher = QFileSystemWatcher(self)
        self._setup_watcher()
        self._watcher.fileChanged.connect(self._on_fs_changed)
        self._watcher.directoryChanged.connect(self._on_fs_changed)

        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def _setup_watcher(self) -> None:
        if self._path.exists():
            self._watcher.addPath(str(self._path))
        if self._path.parent.exists():
            self._watcher.addPath(str(self._path.parent))

    def _on_fs_changed(self, _path: str) -> None:
        if self._path.exists() and str(self._path) not in self._watcher.files():
            self._watcher.addPath(str(self._path))
        self.refresh()

    @Property("QVariantMap", notify=changed)
    def moduleState(self) -> dict[str, Any]:
        return self._state

    def refresh(self) -> None:
        state = read_account_state(self._path)
        if state != self._state:
            self._state = state
            self.changed.emit()
