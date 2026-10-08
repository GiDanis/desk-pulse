"""Read-only installed manifest, service and preference fingerprint evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = Path("/opt/smartpc/dashboard")
manifest = json.loads((root / "release-manifest.json").read_text())
mismatches = [relative for relative, digest in manifest["sha256"].items()
              if not (root / relative).exists() or hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest]
properties = dict(line.split("=", 1) for line in subprocess.check_output(
    ["systemctl", "show", "smartpc-dashboard", "--property=ActiveState,SubState,NRestarts,MainPID"], text=True).splitlines())
from PySide6.QtCore import QSettings, qVersion
settings = QSettings("SmartPC", "Dashboard")
settings.sync()
nonappearance = {key: settings.value(key) for key in settings.allKeys()
                 if not key.startswith("appearance/") and key not in ("animationsEnabled", "nightMode")}
preference = hashlib.sha256(json.dumps(nonappearance, sort_keys=True, default=str).encode()).hexdigest()
pid = int(properties["MainPID"])
children = []
if pid:
    children = [int(child) for child, parent in (line.split() for line in subprocess.check_output(
        ["ps", "-eo", "pid=,ppid="], text=True).splitlines()) if int(parent) == pid]
runtime_pid = next((child for child in children if b"/app.py" in Path(f"/proc/{child}/cmdline").read_bytes()), pid)
memory = {}
if runtime_pid:
    for line in Path(f"/proc/{runtime_pid}/status").read_text().splitlines():
        if line.startswith(("VmRSS:", "VmSize:", "Threads:")):
            key, value = line.split(":", 1)
            memory[key] = value.strip()
report = {"time": time.time(), "hostname": subprocess.check_output(["hostname"], text=True).strip(),
          "version": manifest["version"], "qt": qVersion(), "files": len(manifest["sha256"]),
          "manifestMismatches": mismatches, "service": properties, "runtimePid": runtime_pid, "memory": memory,
          "nonAppearancePreferenceSha256": preference, "nonAppearancePreferenceCount": len(nonappearance),
          "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
          "scope": "Installed bytes and current health; not a physical usability/live source qualification"}
data = Path("/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC")
report["activeTheme"] = json.loads((data / "theme-activation.json").read_text())["active"]
health_hash = hashlib.sha256(os.fsencode(str(data))).hexdigest()
health_path = f"/proc/{pid}/root/tmp/smartpc-theme-health-{os.getuid()}/{health_hash}.json"
try:
    health = json.loads(subprocess.check_output(["sudo", "-n", "cat", health_path], stderr=subprocess.DEVNULL))
    report["guiHeartbeat"] = {"ready": health["ready"], "ageSeconds": time.time() - health["time"],
                              "pid": health["pid"], "selection": health["selection"], "pending": health["pending"]}
except (subprocess.CalledProcessError, ValueError, KeyError):
    report["guiHeartbeat"] = None
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
