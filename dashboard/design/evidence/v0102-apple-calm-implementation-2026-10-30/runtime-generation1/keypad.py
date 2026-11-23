"""Read the dedicated 3x3 USB keypad without intercepting other keyboards."""

from __future__ import annotations

import os
import struct
from pathlib import Path

from PySide6.QtCore import QObject, Property, QSocketNotifier, QTimer, Signal


VENDOR_ID = "413d"
PRODUCT_ID = "553a"
EVENT = struct.Struct("@llHHi")
CONTROL_KEYS = {29, 97}  # left and right Ctrl
SHIFT_KEYS = {42, 54}
# Positions are numbered from the top left, across each row. These are the
# current shortcuts observed on the actual device on 2026-09-29.
KEY_POSITIONS = {19: 1, 31: 2, 111: 3, 30: 4, 44: 5, 21: 6, 46: 7, 47: 8, 45: 9}


def find_keypad_event() -> Path | None:
    """Select the boot-keyboard interface, not the other HID interfaces."""
    for event in sorted(Path("/sys/class/input").glob("event*")):
        device = event / "device"
        try:
            vendor = (device / "id/vendor").read_text().strip().lower()
            product = (device / "id/product").read_text().strip().lower()
            phys = (device / "phys").read_text().strip()
        except OSError:
            continue
        if (vendor, product) == (VENDOR_ID, PRODUCT_ID) and phys.endswith("/input0"):
            path = Path("/dev/input") / event.name
            if path.exists():
                return path
    return None


class KeyDecoder:
    def __init__(self) -> None:
        self.modifiers: set[int] = set()

    def feed(self, event_type: int, code: int, value: int) -> int | None:
        if event_type != 1:  # EV_KEY
            return None
        if code in CONTROL_KEYS | SHIFT_KEYS:
            if value == 1:
                self.modifiers.add(code)
            elif value == 0:
                self.modifiers.discard(code)
            return None
        if value != 1:  # ignore release and auto-repeat
            return None
        position = KEY_POSITIONS.get(code)
        if position is None:
            return None
        if position == 3:  # Delete
            return position
        if not self.modifiers.intersection(CONTROL_KEYS):
            return None
        if position == 1 and not self.modifiers.intersection(SHIFT_KEYS):
            return None
        return position


class Keypad(QObject):
    changed = Signal()
    keyPressed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._fd: int | None = None
        self._path: Path | None = None
        self._notifier: QSocketNotifier | None = None
        self._buffer = b""
        self._decoder = KeyDecoder()
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._connect_if_present)
        self._timer.start()
        self._connect_if_present()

    @Property(bool, notify=changed)
    def connected(self) -> bool:
        return self._fd is not None

    def _connect_if_present(self) -> None:
        if self._fd is not None:
            return
        path = find_keypad_event()
        if path is None:
            return
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        except OSError:
            return
        self._fd = fd
        self._path = path
        self._buffer = b""
        self._decoder = KeyDecoder()
        self._notifier = QSocketNotifier(fd, QSocketNotifier.Type.Read, self)
        self._notifier.activated.connect(self._read_events)
        self.changed.emit()

    def _disconnect(self) -> None:
        if self._notifier is not None:
            self._notifier.setEnabled(False)
            self._notifier.deleteLater()
            self._notifier = None
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
            self._path = None
            self.changed.emit()

    def _read_events(self, *_args: object) -> None:
        if self._fd is None:
            return
        try:
            data = os.read(self._fd, EVENT.size * 64)
        except BlockingIOError:
            return
        except OSError:
            self._disconnect()
            return
        if not data:
            self._disconnect()
            return
        self._buffer += data
        length = len(self._buffer) // EVENT.size * EVENT.size
        for _, _, event_type, code, value in EVENT.iter_unpack(self._buffer[:length]):
            position = self._decoder.feed(event_type, code, value)
            if position is not None:
                self.keyPressed.emit(position)
        self._buffer = self._buffer[length:]
