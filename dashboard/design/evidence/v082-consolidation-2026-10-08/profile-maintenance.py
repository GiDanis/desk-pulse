"""Isolated before/after Qt callback and unchanged-file workload, no network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
if len(sys.argv) == 1:
    rows = []
    for lane in ("before", "after"):
        completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), lane], check=True, capture_output=True, text=True, timeout=15)
        rows.append(json.loads(completed.stdout))
    report = {"scope": "Qt software callback gaps with injected 150 ms replace delay. Acquisition excluded before; controlled worker after. Not GPU/input-to-pixel latency.", "profiles": rows}
    (HERE / "profile-local.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    raise SystemExit(0)

lane = sys.argv[1]
sys.path.insert(0, str(ROOT / "dashboard"))
if lane == "before":
    sys.path.insert(0, str(HERE / "baseline-source"))
with tempfile.TemporaryDirectory(prefix="smartpc-maintenance-profile-") as private:
    os.environ["XDG_CACHE_HOME"] = private
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QEventLoop, QTimer, QThreadPool, qVersion
    from PySide6.QtGui import QGuiApplication
    import weather
    import account
    app = QGuiApplication([])
    raw = json.loads((ROOT / "dashboard/fixtures/theme-runtime/domains/weather-zero.json").read_text())["raw"]
    snapshot = weather.normalize_response(raw)
    service = weather.WeatherService(auto_refresh=False)
    service._cache_path = Path(private) / "weather.json"
    stamps = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: stamps.append(time.perf_counter()))
    replace = os.replace
    def slow_replace(source, target):
        if Path(target) == service._cache_path:
            time.sleep(.15)
        return replace(source, target)
    loop = QEventLoop()
    with patch.object(weather, "fetch_weather", return_value=snapshot), patch.object(weather.os, "replace", side_effect=slow_replace):
        timer.start()
        callback = (lambda: service._on_finished(snapshot, None)) if lane == "before" else (lambda: service.refresh())
        QTimer.singleShot(60, callback)
        QTimer.singleShot(380, loop.quit)
        loop.exec()
    timer.stop()
    assert service._snapshot == snapshot and not service._in_flight
    gaps = [(b-a)*1000 for a,b in zip(stamps, stamps[1:])]
    path = Path(private) / "account.json"
    path.write_text(json.dumps({"version":1,"status":"active","updatedAt":time.time(),"data":{"windows":[{"label":"Codex","usedPercent":0}]}}))
    reader = account.AccountService(path)
    with patch.object(account,"read_account_state",wraps=account.read_account_state) as read:
        started = time.perf_counter()
        for _ in range(100):
            reader.refresh(force=False) if lane == "after" else reader.refresh()
        elapsed = (time.perf_counter()-started)*1000
        reads = read.call_count
    result = {"label":lane,"qt":qVersion(),"maxQtCallbackGapMs":round(max(gaps),3),"timerCallbacks":len(stamps),"unchangedAccountChecks":100,"accountParses":reads,"accountCheckElapsedMs":round(elapsed,3)}
    service.close() if hasattr(service,"close") else service._timer.stop()
    reader.close() if hasattr(reader,"close") else reader._timer.stop()
    assert QThreadPool.globalInstance().waitForDone(3000)
    print(json.dumps(result))
