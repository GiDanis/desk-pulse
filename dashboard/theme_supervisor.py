"""External GUI health watchdog and theme rollback launcher.

A separate process can recover a QML GUI that no longer handles its timers.
Run with: theme_supervisor.py --data-root DIR -- COMMAND [ARGS...].
The application must publish LifecycleManager.heartbeat from its GUI event loop.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from theme_core import ThemeError, read_json
from theme_lifecycle import BASE, LifecycleManager, process_token


def _stop(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def supervise(command, data_root, *, startup_timeout=30.0, heartbeat_timeout=15.0):
    if startup_timeout <= 0 or heartbeat_timeout <= 0:
        raise ValueError('timeout positivo richiesto')
    lifecycle = LifecycleManager(data_root)
    # An interrupted activation never executes its bundle at the next boot.
    try:
        recovery = lifecycle.recover('attivazione interrotta prima del riavvio')
    except (OSError, ThemeError) as error:
        print(json.dumps({'supervisor': 'journalError', 'error': str(error)}), file=sys.stderr, flush=True)
        # Do not launch potentially broken code if the authoritative record cannot
        # be read/recovered. systemd restarts the supervisor; no provider data reset.
        return 78
    process = subprocess.Popen(command, start_new_session=True)
    started = time.monotonic()
    stopped = False
    def requested_stop(signum, frame):
        nonlocal stopped
        stopped = True
        if process.poll() is None:
            try:
                os.killpg(process.pid, signum)
            except ProcessLookupError:
                pass
    previous_handlers = {s: signal.signal(s, requested_stop) for s in (signal.SIGTERM, signal.SIGINT)}
    seen_health = False
    last_health_timestamp = None
    last_health_at = None
    failure = None
    try:
        while process.poll() is None:
            if stopped:
                _stop(process)
                break
            now = time.monotonic()
            try:
                health = read_json(lifecycle.health_path)
                current_pid = health.get('pid') == process.pid
                same_process = health.get('processStart') == process_token(process.pid)
                timestamp = health.get('time')
                if current_pid and same_process and type(timestamp) in (int, float):
                    age = time.time() - timestamp
                    if health.get('ready') is True and age >= 0 and age < heartbeat_timeout:
                        seen_health = True
                        if timestamp != last_health_timestamp:
                            last_health_timestamp, last_health_at = timestamp, now
                    if seen_health and last_health_at is not None and now - last_health_at > heartbeat_timeout:
                        failure = 'GUI heartbeat scaduto/readiness persa'
                        break
            except (OSError, ThemeError):
                pass
            if seen_health and last_health_at is not None and now - last_health_at > heartbeat_timeout:
                failure = 'GUI heartbeat assente'
                break
            if not seen_health and now - started > startup_timeout:
                failure = 'GUI startup/readiness timeout'
                break
            time.sleep(0.25)
        code = process.poll()
        if failure:
            _stop(process)
            code = process.returncode
        if not stopped:
            # systemd/operator shutdown is signalled to this supervisor. Any
            # unsolicited GUI exit, even Qt.quit() with code 0, can loop a theme.
            result = lifecycle.recover(failure or 'processo GUI terminato con codice ' + str(code), failed_active=True)
            print(json.dumps({'supervisor': 'recovered', **result}), file=sys.stderr, flush=True)
            # Restart remains the responsibility of systemd, avoiding a tight loop.
            return 75
        return 0 if stopped else code or 0
    finally:
        _stop(process)
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--startup-timeout', type=float, default=30)
    parser.add_argument('--heartbeat-timeout', type=float, default=15)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('comando GUI richiesto dopo --')
    return supervise(command, args.data_root, startup_timeout=args.startup_timeout,
                     heartbeat_timeout=args.heartbeat_timeout)


if __name__ == '__main__':
    raise SystemExit(main())
