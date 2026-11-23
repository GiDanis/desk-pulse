"""Offline probes of actual provider adapters and Apple Calm formatting.

Regression oracles for provider/DTO/theme semantics; no user state or providers.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
from theme_fixture_support import isolate_process

private, base = isolate_process()
try:
    from PySide6.QtCore import QUrl, qVersion
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlEngine, QQmlComponent, QQmlExpression
    from theme_api import numeric, normalize_dto, source_snapshot, weather_snapshot

    app = QGuiApplication([])
    engine = QQmlEngine()
    component = QQmlComponent(engine)
    format_path = ROOT / "theme-projects/apple-calm/bundle/qml/Format.js"
    qml = 'import QtQml\nimport "' + QUrl.fromLocalFile(str(format_path)).toString() + '" as Format\nQtObject {}'
    component.setData(qml.encode(), QUrl.fromLocalFile(str(base / "Probe.qml")))
    obj = component.create()
    assert obj is not None, [e.toString() for e in component.errors()]

    def run(expression):
        e = QQmlExpression(QQmlEngine.contextForObject(obj), obj, "JSON.stringify(" + expression + ")")
        value, undefined = e.evaluate()
        assert not e.hasError() and not undefined, e.error().toString()
        return json.loads(value)

    def arg(value):
        return json.dumps(value, ensure_ascii=False)

    rows = []

    def check(identifier, actual, expected, evidence, kind="control"):
        rows.append({"id": identifier, "kind": kind, "actual": actual, "expected": expected,
                     "matched": actual == expected, "evidence": evidence})

    check("zero-is-not-missing", run("Format.number(" + arg(numeric(0)) + ")"), "0", "theme_api.numeric → Format.number")
    check("missing-is-not-zero", run("Format.number(" + arg(numeric(None)) + ")"), "—", "theme_api.numeric → Format.number")
    window = normalize_dto("AccountWindow", {"id": "x", "usedPercent": 34,
                                              "windowDurationMins": 300, "resetsAt": 0})
    check("account-duration-alias", window["windowDurationMinutes"]["value"], 300,
          "account_sync output windowDurationMins → normalize_dto")
    check("account-used-is-not-remaining", window["usedPercent"]["value"], 34,
          "AccountPage currently labels this Utilizzato; residual candidate must derive 100-used")
    actual_reset = run("(" + arg(window) + ").resetsAt === null ? 'Reset non disponibile' : 'Reset ' + Format.stamp((" + arg(window) + ").resetsAt)")
    check("unknown-reset-zero", actual_reset, "Reset non disponibile",
          "account_sync uses 0 when reset unavailable; AccountPage checks null only", "finding")
    football = [normalize_dto("MatchData", {"canonicalMatchId": state, "status": state,
        "homeTeam": "A", "awayTeam": "B", "homeScore": 0, "awayScore": 1,
        "minute": "45", "rawStatus": ""}) for state in ("live", "half_time")]
    filtered = run("Format.matches(" + arg(football) + ", 'IN CORSO')")
    check("halftime-in-progress-filter", [r["id"] for r in filtered], ["live", "half_time"],
          "sport_core.LIVE_STATES includes half_time; Format.matches checks live only", "finding")
    check("halftime-italian-label", run("Format.matchStatus(" + arg(football[1]) + ")"), "Intervallo",
          "sport_core status normalized as half_time; Format.matchStatus lacks label", "finding")
    for kind in ("f1", "motogp"):
        fixture = ROOT / ("dashboard/fixtures/racing-" + kind + "-normalized.json")
        snapshot = json.loads(fixture.read_text())["snapshot"]
        raw = next(s["results"][0] for event in snapshot["events"] for s in event.get("sessions", []) if s.get("results"))
        dto = normalize_dto("RacingTiming", raw)
        formatted = run("Format.timing(" + arg([dto]) + ")")[0]
        check(kind + "-result-reaches-renderer", raw["value"] in formatted["value"], True,
              {"fixture": str(fixture.relative_to(ROOT)), "sourceValue": raw["value"],
               "dtoTime": dto["time"], "renderedValue": formatted["value"]}, "finding")
    match = normalize_dto("MatchData", {"canonicalMatchId": "partial", "status": "finished",
        "homeTeam": "A", "awayTeam": "B", "homeScore": 0, "awayScore": None})
    check("partial-score-consistency", run("Format.matches(" + arg([match]) + ")")[0]["value"], "0 – —",
          "dashboard_summary preserves 0–missing, list formatter currently hides the score", "presentation-decision")
    raw_weather = json.loads((ROOT / "dashboard/fixtures/theme-runtime/domains/weather-zero.json").read_text())["raw"]
    from weather import normalize_response
    normalized_weather = weather_snapshot({"status": "active", "source": "fixture",
        "updatedAt": 1790848800, "data": normalize_response(raw_weather)})
    check("weather-zero", normalized_weather["temperature"]["value"], 0,
          "real normalize_response → weather_snapshot")
    check("daily-not-hourly", len(normalized_weather["forecast"]), 3,
          {"dates": [x["date"] for x in normalized_weather["forecast"]],
           "hourlyForecastField": "absent; hourly request is precipitation_probability only"})
    check("offline-retains-source-age", source_snapshot({"status": "offline", "updatedAt": 1000,
        "checkedAt": 1100, "data": {"value": 0}})["isStale"], True, "source_snapshot offline retained data")
    check("invalid-numeric-display", run("Format.number(" + arg(numeric(False)) + ")"), "—",
          "numeric(False) is unavailable but carries displayText=False, currently preferred by Format.number",
          "boundary-hardening")
    from motorsport_core import f1_result_rows, moto_result_rows
    f1 = f1_result_rows({"Results":[{"position":"1","Driver":{"driverId":"a"},"Time":{"time":"1:20:00"}},{"position":"2","Driver":{"driverId":"b"},"Time":{"time":"+2.400"}}]}, "Results")
    check("race-winner-total", (f1[0]["resultKind"],f1[0]["timeKind"],f1[0]["time"]), ("time","total","1:20:00"), "actual F1 producer")
    check("race-other-gap", (f1[1]["resultKind"],f1[1]["gap"],f1[1]["time"]), ("gap","+2.400",None), "actual F1 producer")
    check("lap-alias", normalize_dto("RacingTiming", {"id":"a","laps":12})["lap"]["value"], 12, "laps → lap")
    for invalid in (False, True, float("nan"), float("inf")):
        check("invalid-"+str(invalid), run("Format.number("+arg(numeric(invalid))+")"), "—", "invalid input must not become a measure")
    check("display-only-time", run("Format.number("+arg(numeric("1:24.580"))+")"), "1:24.580", "trusted formatted timing retained")
    check("remaining-34", run("Format.remaining("+arg(numeric(34))+")"), 66, "bar and label share residual")
    for state, code in [("in attesa","pending"),("presentato","presented"),("revocato","revoked"),("scaduto","expired"),("solo elenco · fuori tempo","listed_late")]:
        check("delivery-"+code, normalize_dto("NotificationEvent", {"deliveryState":state})["deliveryState"], code, "stable public code")
    check("halftime-dto", football[1]["status"], "half_time", "enum preserves provider status")
    for source,category,icon in [("sport_f1","sport","race-car"),("sport_motogp","sport","motorcycle"),("weather-alert","meteo","cloud"),("football","sport","football")]:
        event = normalize_dto("NotificationEvent", {"source":source,"category":category})
        check("notice-icon-"+source, run("Format.noticeIcon("+arg(event)+")"), icon, "actual provider source/category vocabulary")
    source_files = [format_path, ROOT / "dashboard/theme_api.py", ROOT / "dashboard/weather.py",
        ROOT / "dashboard/account_sync.py", ROOT / "dashboard/sport_core.py",
        ROOT / "theme-projects/apple-calm/bundle/qml/AccountPage.qml"]
    report = {"scope": "offline provider/DTO/Apple Calm regression; no providers, no board",
        "qt": qVersion(), "python": sys.version.split()[0], "cases": rows,
        "matches": sum(r["matched"] for r in rows),
        "findings": [r["id"] for r in rows if not r["matched"]],
        "sourceHashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}}
    assert not report["findings"], report["findings"]
    print(json.dumps({"cases": len(rows), "controlsAndExpectationsMatched": report["matches"],
                      "findings": report["findings"], "qt": qVersion()}))
    obj.deleteLater()
    engine.deleteLater()
    app.processEvents()
finally:
    private.cleanup()
