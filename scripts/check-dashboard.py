#!/usr/bin/env python3
"""Run dashboard regressions in isolated processes, with cloud probes excluded."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
SPECIAL = {
    "check_casa_live.py",
    "check_theme_bundle_acceptance.py",
    "check_theme_runtime_fixtures.py",
}
UI = {
    "check_dashboard.py",
    "check_settings.py",
    "check_notifications.py",
    "check_theme_semantic_residuals.py",
    "check_theme_semantic_palettes.py",
}
QUICK = {
    "check_settings.py",
    "check_aquarium.py",
    "check_game_menu.py",
    "check_game_session_start.py",
    "check_theme_core.py",
}


def cases(suite):
    for path in sorted(DASHBOARD.glob("check_*.py")):
        if path.name in SPECIAL:
            continue
        is_ui = path.stem.endswith("_ui") or path.name in UI
        if suite == "quick" and path.name not in QUICK:
            continue
        if suite not in ("all", "quick") and is_ui != (suite == "ui"):
            continue
        arguments = (
            ["--offline-only"]
            if path.name in ("check_sport_team_ui.py", "check_fantacalcio_ui.py")
            else []
        )
        yield path.stem, [str(path), *arguments]
    if suite in ("core", "all"):
        yield (
            "theme-corpus-contract",
            [
                str(DASHBOARD / "check_theme_runtime_fixtures.py"),
                "--track",
                "contractData",
            ],
        )
    if suite in ("ui", "all"):
        for case in (
            "notifications",
            "scene-error",
            "scene-neverready",
            "scene-frame",
            "overlay",
        ):
            yield (
                "theme-acceptance-" + case,
                [str(DASHBOARD / "check_theme_bundle_acceptance.py"), "--case", case],
            )
        yield (
            "casa-functional-night",
            [str(DASHBOARD / "check_casa_ui.py"), "--profile", "functional:night:off"],
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite", choices=("quick", "core", "ui", "all"), default="quick"
    )
    parser.add_argument(
        "--case",
        action="append",
        help="Run only this named case; repeat to select several.",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--list", action="store_true", help="List selected cases without running tests."
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print each case result as it completes."
    )
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    selected = list(cases("all" if args.case else args.suite))
    if args.case:
        unknown = set(args.case) - {name for name, _ in selected}
        if unknown:
            parser.error("Unknown cases: " + ", ".join(sorted(unknown)))
        selected = [(name, command) for name, command in selected if name in args.case]
    if not selected:
        parser.error("No cases selected")
    if args.list:
        print("\n".join(name for name, _ in selected))
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required when running tests")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    run_started = time.monotonic()
    for name, command in selected:
        if name == "check_header_clock_ui":
            command = [*command, "--theme", "base", "--output", str(args.output_dir.resolve() / "header-clock-base")]
        elif name == "check_aquarium_ui":
            command = [*command, "--output", str(args.output_dir.resolve() / "aquarium-ui")]
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="smartpc-regression-") as private:
            base = Path(private)
            environment = os.environ.copy()
            for key, directory in (
                ("XDG_CONFIG_HOME", "config"),
                ("XDG_DATA_HOME", "data"),
                ("XDG_CACHE_HOME", "cache"),
                ("XDG_STATE_HOME", "state"),
            ):
                location = base / directory
                location.mkdir()
                environment[key] = str(location)
            environment.update(
                QT_QPA_PLATFORM="offscreen",
                QT_QUICK_BACKEND="software",
                STATE_DIRECTORY=str(base / "state"),
                SMARTPC_THEME_STORE=str(base / "themes"),
            )
            for key in (
                "SMARTPC_ACCOUNT_PATH",
                "SMARTPC_ACCOUNT_SNAPSHOT",
                "SMARTPC_THEME_TRACE_OUTPUT",
                "SMARTPC_SPORT_OFFLINE",
                "SMARTPC_RACING_OFFLINE",
                "SMARTPC_FOOTBALL_CONFIG",
            ):
                environment.pop(key, None)
            try:
                completed = subprocess.run(
                    [sys.executable, *command],
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout,
                )
                output = completed.stdout + completed.stderr
                row = {
                    "case": name,
                    "exitCode": completed.returncode,
                    "status": "passed" if completed.returncode == 0 else "failed",
                }
            except subprocess.TimeoutExpired as error:
                output = (
                    "Test exceeded timeout.\n"
                    + str(error.stdout or "")
                    + str(error.stderr or "")
                )
                row = {"case": name, "status": "failed", "timeoutSeconds": args.timeout}
            row["elapsedSeconds"] = round(time.monotonic() - started, 3)
            (args.output_dir / (name + ".txt")).write_text(output)
            results.append(row)
            if args.verbose:
                print(json.dumps(row), flush=True)
            report = {
                "suite": "selected" if args.case else args.suite,
                "results": results,
                "status": "passed"
                if all(row["status"] == "passed" for row in results)
                else "failed",
                "scope": "Local regressions with isolated state and offscreen rendering; live Casa probe excluded.",
            }
            (args.output_dir / "checks.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(
        json.dumps(
            {
                "status": report["status"],
                "passed": sum(row["status"] == "passed" for row in results),
                "total": len(results),
                "failedCases": [
                    row["case"] for row in results if row["status"] != "passed"
                ],
                "elapsedSeconds": round(time.monotonic() - run_started, 3),
                "report": str(args.output_dir / "checks.json"),
            }
        ),
        flush=True,
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
