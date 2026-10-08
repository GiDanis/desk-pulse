"""Observe the installed kiosk for 30 minutes without sending input."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


def service_pid() -> int:
    result = subprocess.check_output(
        ["systemctl", "show", "smartpc-dashboard", "-p", "MainPID", "--value"], text=True
    ).strip()
    return int(result)


def read_temp() -> float | None:
    values = []
    for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
        try:
            if (zone / "type").read_text().strip().lower().startswith("cpu"):
                values.append(int((zone / "temp").read_text()) / 1000)
        except (OSError, ValueError):
            pass
    return max(values) if values else None


def read_rss(pid: int) -> int:
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    raise RuntimeError("VmRSS unavailable")


def main() -> int:
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
    start = time.monotonic()
    initial_pid = service_pid()
    samples = []
    errors = []
    while time.monotonic() - start < duration:
        try:
            pid = service_pid()
            if pid != initial_pid:
                errors.append(f"PID changed from {initial_pid} to {pid}")
            if pid <= 0:
                errors.append("service inactive")
            else:
                samples.append((read_rss(pid), read_temp()))
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            errors.append(str(exc))
        time.sleep(min(10, max(0, duration - (time.monotonic() - start))))
    memories = [sample[0] for sample in samples]
    temperatures = [sample[1] for sample in samples if sample[1] is not None]
    print(json.dumps({
        "elapsed_s": round(time.monotonic() - start, 1),
        "samples": len(samples),
        "pid_initial": initial_pid,
        "pid_final": service_pid(),
        "rss_min_kib": min(memories) if memories else None,
        "rss_max_kib": max(memories) if memories else None,
        "temperature_min_c": min(temperatures) if temperatures else None,
        "temperature_max_c": max(temperatures) if temperatures else None,
        "errors": list(dict.fromkeys(errors)),
    }))
    return 0 if samples and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
