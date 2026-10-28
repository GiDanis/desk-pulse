"""Presentation-only clock: absolute monotonic deadlines, no simulation work."""
import math
import time

from PySide6.QtCore import QObject, Property, QTimer, Qt, Signal
from PySide6.QtQml import qmlRegisterType


class GamePresentationClock(QObject):
    tick = Signal(float)
    runningChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._deadline = 0.
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._timeout)

    @Property(bool, notify=runningChanged)
    def running(self):
        return self._running

    @running.setter
    def running(self, value):
        if self._running == value:
            return
        self._running = value
        if value:
            self._deadline = time.monotonic() + 1 / 30
            self._arm()
        else:
            self._timer.stop()
        self.runningChanged.emit()

    def _arm(self):
        self._timer.start(max(1, math.ceil((self._deadline - time.monotonic()) * 1000)))

    def _timeout(self):
        if not self._running:
            return
        now = time.monotonic()
        self._deadline += 1 / 30
        if self._deadline <= now:
            self._deadline += (math.floor((now - self._deadline) * 30) + 1) / 30
        self.tick.emit(now * 1000)
        if self._running:
            self._arm()


_registered = False


def register_presentation_clock():
    global _registered
    if not _registered:
        qmlRegisterType(GamePresentationClock, 'SmartPC.Game', 1, 0, 'GamePresentationClock')
        _registered = True
