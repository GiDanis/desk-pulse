"""Read ChatGPT account usage from local Codex and publish a safe snapshot to SmartPC."""

from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REMOTE_PATH = "/var/cache/smartpc-dashboard/account-chatgpt.json"
SOURCE = "Codex App Server"


class AccountUnavailable(Exception):
    """The local Codex account needs attention rather than a retry."""


class AppServer:
    def __init__(self, executable: str) -> None:
        environment = os.environ.copy()
        environment["PATH"] = str(Path(executable).parent) + os.pathsep + environment.get("PATH", "")
        self.process = subprocess.Popen(
            [executable, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0, env=environment,
        )
        self._next_id = 0
        self._read_buffer = b""
        self._pending: list[dict[str, Any]] = []
        self.notifications: list[dict[str, Any]] = []
        try:
            self.call("initialize", {"clientInfo": {
                "name": "smartpc_account", "title": "SmartPC Account", "version": "0.4.0",
            }})
            self._send({"method": "initialized", "params": {}})
        except Exception:
            self.close()
            raise

    def _send(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write((json.dumps(message, separators=(",", ":")) + "\n").encode())
        self.process.stdin.flush()

    def _read_message(self, deadline: float) -> dict[str, Any]:
        assert self.process.stdout is not None
        while not self._pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Nessuna risposta da Codex")
            ready, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not ready:
                raise TimeoutError("Nessuna risposta da Codex")
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Codex App Server terminato")
            self._read_buffer += chunk
            while b"\n" in self._read_buffer:
                line, self._read_buffer = self._read_buffer.split(b"\n", 1)
                if line:
                    self._pending.append(json.loads(line))
        return self._pending.pop(0)

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        request_id = self._next_id
        message: dict[str, Any] = {"method": method, "id": request_id}
        if params is not None:
            message["params"] = params
        self._send(message)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            response = self._read_message(deadline)
            if response.get("id") != request_id:
                if response.get("method") == "account/rateLimits/updated":
                    self.notifications.append(response)
                    self.notifications = self.notifications[-100:]
                continue
            if "error" in response:
                # App-server error details can include account information. Do not log them.
                raise AccountUnavailable(f"Codex ha rifiutato {method}")
            return response.get("result") or {}
        raise TimeoutError(f"Nessuna risposta da Codex per {method}")

    def close(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)

    def notification(self, deadline: float) -> dict[str, Any]:
        if self.notifications:
            return self.notifications.pop(0)
        return self._read_message(deadline)


def merge_limits(previous: dict[str, Any], notification: dict[str, Any]) -> dict[str, Any]:
    """An update to one bucket is not a replacement of every account limit."""
    from copy import deepcopy
    result = deepcopy(previous)
    params = notification.get("params") or {}
    bucket = params.get("rateLimits")
    if not isinstance(bucket, dict):
        return result
    identity = bucket.get("limitId")
    if not isinstance(identity, str) or not identity:
        return result  # An unscoped delta requires a complete read.
    buckets = result.setdefault("rateLimitsByLimitId", {})
    if not isinstance(buckets, dict):
        return deepcopy(previous)
    existing = buckets.get(identity)
    buckets[identity] = dict(existing or {}, **bucket)
    return result


def watch(server: AppServer, account: dict[str, Any], limits: dict[str, Any], host: str, identity: Path) -> None:
    """Optional persistent helper; ten-minute reads recover missed notifications."""
    previous = None
    reconcile = time.monotonic()
    while True:
        now = time.monotonic()
        force = now >= reconcile
        if force:
            limits = server.call("account/rateLimits/read")
            reconcile = time.monotonic() + 600
        snapshot = normalize(account, limits, int(time.time()))
        if force or snapshot["data"] != previous:
            publish(snapshot, host, identity)
            previous = snapshot["data"]
        try:
            message = server.notification(min(reconcile, time.monotonic() + 30))
        except TimeoutError:
            continue
        if message.get("method") == "account/rateLimits/updated":
            merged = merge_limits(limits, message)
            if merged == limits:
                reconcile = time.monotonic()
            limits = merged


def normalize(account_result: dict[str, Any], limits_result: dict[str, Any], now: int) -> dict[str, Any]:
    account = account_result.get("account") or {}
    if account.get("type") != "chatgpt":
        raise AccountUnavailable("Account ChatGPT non collegato a Codex")

    buckets = limits_result.get("rateLimitsByLimitId")
    if not isinstance(buckets, dict) or not buckets:
        legacy = limits_result.get("rateLimits")
        buckets = {legacy.get("limitId", "codex"): legacy} if isinstance(legacy, dict) else {}
    windows: list[dict[str, Any]] = []
    credit_details = None
    for bucket_id, bucket in buckets.items():
        if not isinstance(bucket, dict):
            continue
        label = bucket.get("limitName") or ("Codex" if bucket_id == "codex" else str(bucket_id))
        for kind in ("primary", "secondary"):
            window = bucket.get(kind)
            if not isinstance(window, dict):
                continue
            used = window.get("usedPercent")
            duration = window.get("windowDurationMins")
            resets_at = window.get("resetsAt")
            if not isinstance(used, (int, float)) or isinstance(used, bool) or not 0 <= used <= 100:
                continue
            if not isinstance(duration, (int, float)) or duration <= 0:
                continue
            windows.append({
                "id": f"{bucket_id}:{kind}",
                "label": str(label)[:50], "usedPercent": round(float(used), 1),
                "windowDurationMins": int(duration),
                "resetsAt": int(resets_at) if isinstance(resets_at, (int, float)) and resets_at > 0 else 0,
            })
        if credit_details is None and isinstance(bucket.get("credits"), dict):
            credit_details = bucket["credits"]

    if not windows:
        raise RuntimeError("Codex non ha restituito finestre di utilizzo valide")
    credits = None
    if credit_details is not None:
        balance = credit_details.get("balance")
        credits = {
            "balance": str(balance) if balance is not None else "",
            "unlimited": credit_details.get("unlimited") is True,
        }
    reset_details = limits_result.get("rateLimitResetCredits")
    reset_count = reset_details.get("availableCount") if isinstance(reset_details, dict) else None
    reset_credits = reset_count if isinstance(reset_count, int) and reset_count >= 0 else None
    plan = account.get("planType") or next(
        (bucket.get("planType") for bucket in buckets.values() if isinstance(bucket, dict) and bucket.get("planType")), ""
    )
    return {
        "version": 1, "status": "active", "source": SOURCE, "updatedAt": now,
        "data": {
            "plan": str(plan)[:40], "windows": windows,
            "credits": credits, "resetCredits": reset_credits,
        },
        "error": "",
    }


def unavailable_snapshot(message: str) -> dict[str, Any]:
    return {"version": 1, "status": "unavailable", "source": SOURCE,
            "updatedAt": 0, "data": {}, "error": message}


def find_codex() -> str | None:
    found = shutil.which("codex")
    if found:
        return found
    # systemd user services do not necessarily inherit the interactive nvm PATH.
    candidates = (
        sorted((Path.home() / ".nvm/versions/node").glob("*/bin/codex")) +
        [Path.home() / ".local/bin/codex", Path.home() / ".npm-global/bin/codex"]
    )
    for c in reversed(candidates):
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)
    return None


def publish(snapshot: dict[str, Any], host: str, identity: Path) -> None:
    payload = (json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    remote = (
        "set -e; umask 077; "
        "mkdir -p /var/cache/smartpc-dashboard; "
        "tmp=$(mktemp /var/cache/smartpc-dashboard/account-chatgpt.XXXXXX); "
        "trap 'rm -f \"$tmp\"' EXIT; "
        f'cat > "$tmp"; mv "$tmp" {REMOTE_PATH}'
    )
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "-i", str(identity), host, remote],
        input=payload, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Invio del riepilogo alla Orange Pi non riuscito")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("SMARTPC_ACCOUNT_HOST", "smartpc@192.168.1.179"))
    parser.add_argument("--identity", type=Path, default=Path.home() / ".ssh/smartpc_ed25519")
    parser.add_argument("--codex-bin", default=os.environ.get("SMARTPC_CODEX_BIN") or find_codex())
    parser.add_argument("--watch", action="store_true", help="Ascolta aggiornamenti; riconcilia ogni 10 minuti")
    args = parser.parse_args()
    if not args.codex_bin:
        print("Codex CLI non trovato", file=sys.stderr)
        return 1
    server = None
    try:
        server = AppServer(args.codex_bin)
        account = server.call("account/read", {"refreshToken": False})
        if (account.get("account") or {}).get("type") != "chatgpt":
            snapshot = unavailable_snapshot("Account ChatGPT non collegato sul PC")
        else:
            limits = server.call("account/rateLimits/read")
            snapshot = normalize(account, limits, int(time.time()))
            if args.watch:
                watch(server, account, limits, args.host, args.identity)
    except AccountUnavailable:
        snapshot = unavailable_snapshot("Accesso ChatGPT da ripristinare sul PC")
    except (OSError, TimeoutError, ValueError, RuntimeError) as exc:
        print(f"Lettura account non riuscita: {type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        if server is not None:
            server.close()
    try:
        publish(snapshot, args.host, args.identity)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        print(f"Sincronizzazione non riuscita: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("Riepilogo Account ChatGPT sincronizzato")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
