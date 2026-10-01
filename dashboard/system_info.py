"""Passive Linux diagnostics. QML reads snapshots; getters never perform I/O."""
from __future__ import annotations

import os
import platform
import shutil
import socket
import struct
import sys
import time
from pathlib import Path

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QObject, Property, QProcess, QProcessEnvironment, QTimer, Signal, Slot, qVersion
from PySide6.QtGui import QGuiApplication


def read_text(path: str) -> str:
    try:
        return Path(path).read_text().strip().strip("\0")
    except (OSError, UnicodeError):
        return ""


def duration(seconds: float) -> str:
    minutes = int(seconds) // 60
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    return f"{days} g {hours} h {minutes} min" if days else f"{hours} h {minutes} min"


def mib(kib: int) -> str:
    return f"{kib / 1024:.0f} MiB"


def wifi_quality(output: str) -> str:
    """NetworkManager reports quality, not RSSI; never convert it into dBm."""
    for line in output.splitlines():
        active, separator, signal = line.partition(":")
        if active == "yes" and separator and signal.isdigit() and 0 <= int(signal) <= 100:
            return signal + "%"
    return "N/D"


class SystemInfo(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._data: dict = {}
        self._updated_at = 0.0
        self._started = time.monotonic()
        self._cpu_sample = None
        self._monitoring = False
        self._wifi_interface = ""
        self._wifi_quality = "N/D"
        self._wifi_checked = 0.0
        self._nmcli = shutil.which("nmcli")
        self._wifi_process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("LC_ALL", "C")
        self._wifi_process.setProcessEnvironment(environment)
        self._wifi_process.finished.connect(self._wifi_finished)
        self._wifi_process.errorOccurred.connect(self._wifi_error)
        self._wifi_timeout = QTimer(self)
        self._wifi_timeout.setSingleShot(True)
        self._wifi_timeout.setInterval(2500)
        self._wifi_timeout.timeout.connect(self._wifi_process.kill)
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self.refresh)
        os_release = dict(line.split("=", 1) for line in read_text("/etc/os-release").splitlines() if "=" in line)
        board_release = {}
        for path in ("/etc/armbian-release", "/etc/orangepi-release"):
            board_release.update(line.split("=", 1) for line in read_text(path).splitlines() if "=" in line)
        self._static = {
            "version": "DeskPulse v0.6", "hostname": socket.gethostname(),
            "model": board_release.get("BOARD_NAME", "").strip('"') or read_text("/sys/firmware/devicetree/base/model") or platform.machine(),
            "os": os_release.get("PRETTY_NAME", platform.system()).strip('"'),
            "kernel": platform.release(), "python": platform.python_version(),
            "qt": qVersion(), "pyside": pyside_version, "cores": str(os.cpu_count() or "N/D"),
            "timezone": read_text("/etc/timezone") or time.tzname[0],
        }
        self.refresh()

    @Property("QVariantMap", notify=changed)
    def data(self) -> dict:
        return self._data.copy()

    @Property(float, notify=changed)
    def updatedAt(self) -> float:
        return self._updated_at

    @Property(str, notify=changed)
    def cpuTemperature(self) -> str:
        return self._data.get("cpuTemperature", "N/D")

    @Property(str, notify=changed)
    def memoryUsage(self) -> str:
        return self._data.get("memoryUsage", "N/D")

    @Property(str, notify=changed)
    def uptimeText(self) -> str:
        return self._data.get("uptime", "N/D")

    @Slot(bool)
    def setMonitoring(self, enabled: bool) -> None:
        self._monitoring = enabled
        if enabled:
            self.refresh()
            self._timer.start()
        else:
            self._timer.stop()
            self._wifi_timeout.stop()
            if self._wifi_process.state() != QProcess.ProcessState.NotRunning:
                self._wifi_checked = 0.0
                self._wifi_process.kill()

    def _wifi_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._wifi_finished(-1, QProcess.ExitStatus.CrashExit)

    def _request_wifi(self, interface: str) -> None:
        if not self._monitoring or not self._nmcli or self._wifi_process.state() != QProcess.ProcessState.NotRunning:
            return
        if interface == self._wifi_interface and time.monotonic() - self._wifi_checked < 30:
            return
        self._wifi_interface = interface
        self._wifi_checked = time.monotonic()
        self._wifi_process.start(self._nmcli, ["--wait", "2", "-t", "-f", "ACTIVE,SIGNAL",
                                             "device", "wifi", "list", "ifname", interface, "--rescan", "no"])
        self._wifi_timeout.start()

    def _wifi_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._wifi_timeout.stop()
        output = bytes(self._wifi_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._wifi_quality = (wifi_quality(output) if exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit else "N/D")
        if not self._monitoring or self._data.get("interface") != self._wifi_interface:
            return
        self._data = {**self._data, "wifiSignal": self._wifi_quality,
                      "wifiSignalDetail": "Qualità NetworkManager · rilevata " + time.strftime("%H:%M:%S")
                      if self._wifi_quality != "N/D" else "Qualità non disponibile da NetworkManager"}
        self.changed.emit()

    @Slot()
    def refresh(self) -> None:
        data = dict(self._static)
        temperatures = {}
        for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
            try:
                temperatures[read_text(str(zone / "type"))] = int(read_text(str(zone / "temp"))) / 1000
            except ValueError:
                pass
        cpu = [v for k, v in temperatures.items() if k.startswith("cpu")]
        gpu = [v for k, v in temperatures.items() if k.startswith("gpu")]
        data["cpuTemperature"] = f"{max(cpu):.0f} °C" if cpu else "N/D"
        data["gpuTemperature"] = f"{max(gpu):.0f} °C" if gpu else "N/D"
        try:
            memory = {line.split(":")[0]: int(line.split()[1]) for line in read_text("/proc/meminfo").splitlines()}
            total, available = memory["MemTotal"], memory["MemAvailable"]
            data["memoryUsage"] = f"{(total - available) / total * 100:.0f}% usata"
            data["memoryDetail"] = f"{mib(available)} liberi / {mib(total)}"
            data["swap"] = mib(memory["SwapTotal"] - memory["SwapFree"]) + " usati"
        except (ValueError, KeyError, ZeroDivisionError, IndexError):
            data.update(memoryUsage="N/D", memoryDetail="N/D", swap="N/D")
        try:
            status = dict(line.split(":", 1) for line in read_text("/proc/self/status").splitlines() if ":" in line)
            data["appMemory"] = mib(int(status["VmRSS"].split()[0])) + " RSS"
            data["appMemoryPeak"] = mib(int(status["VmHWM"].split()[0])) + " RSS"
            data["threads"] = status["Threads"].strip()
        except (KeyError, ValueError, IndexError):
            data.update(appMemory="N/D", appMemoryPeak="N/D", threads="N/D")
        try:
            ticks = read_text("/proc/self/stat").rsplit(")", 1)[1].split()
            cpu_seconds = (int(ticks[11]) + int(ticks[12])) / os.sysconf("SC_CLK_TCK")
            now = time.monotonic()
            previous = self._cpu_sample
            data["appCpu"] = (f"{max(0, (cpu_seconds - previous[1]) / (now - previous[0]) * 100):.1f}% di un core"
                              if previous and now - previous[0] >= 1 else self._data.get("appCpu", "In misurazione…"))
            if previous is None or now - previous[0] >= 1:
                self._cpu_sample = (now, cpu_seconds)
        except (ValueError, IndexError, OSError):
            data["appCpu"] = "N/D"
        try:
            data["uptime"] = duration(float(read_text("/proc/uptime").split()[0]))
        except (ValueError, IndexError):
            data["uptime"] = "N/D"
        data["appUptime"] = duration(time.monotonic() - self._started)
        data["load"] = " / ".join(read_text("/proc/loadavg").split()[:3]) or "N/D"
        try:
            fs = os.statvfs("/")
            data["storage"] = f"{fs.f_bavail * fs.f_frsize / 2**30:.1f} GiB liberi / {fs.f_blocks * fs.f_frsize / 2**30:.1f} GiB"
        except OSError:
            data["storage"] = "N/D"
        data.update(interface="N/D", ip="N/D", network="Non disponibile", wifiSignal="N/D",
                    wifiSignalDetail="Nessuna connessione Wi-Fi attiva")
        for line in read_text("/proc/net/route").splitlines()[1:]:
            fields = line.split()
            if len(fields) < 4 or fields[1] != "00000000" or not (int(fields[3], 16) & 1):
                continue
            interface = fields[0]
            data["interface"] = interface
            try:
                import fcntl
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
                    address = fcntl.ioctl(connection.fileno(), 0x8915, struct.pack("256s", interface.encode()[:15]))
                data["ip"] = socket.inet_ntoa(address[20:24])
                data["network"] = "Rete locale collegata"
            except (OSError, ImportError):
                pass
            for wireless in read_text("/proc/net/wireless").splitlines()[2:]:
                if wireless.strip().startswith(interface + ":"):
                    values = wireless.split()
                    if len(values) > 3:
                        data["wifiSignal"] = values[3].rstrip(".") + " dBm"
                        data["wifiSignalDetail"] = "Potenza rilevata dal driver"
            if data["wifiSignal"] == "N/D" and Path("/sys/class/net", interface, "wireless").is_dir():
                data["wifiSignal"] = self._wifi_quality if interface == self._wifi_interface else "N/D"
                data["wifiSignalDetail"] = (self._data.get("wifiSignalDetail", "Qualità NetworkManager")
                                             if data["wifiSignal"] != "N/D" else "Lettura qualità Wi-Fi…" if self._nmcli else "Misura non disponibile dal driver")
                self._request_wifi(interface)
            break
        screen = QGuiApplication.primaryScreen()
        data["display"] = (f"{screen.size().width()} × {screen.size().height()} · {screen.refreshRate():.0f} Hz" if screen else "N/D")
        data["graphics"] = "Qt Quick · " + QGuiApplication.platformName().upper()
        data["pid"] = str(os.getpid())
        data["mode"] = "Demo" if "--demo" in sys.argv else "Dashboard"
        self._data = data
        self._updated_at = time.time()
        self.changed.emit()
