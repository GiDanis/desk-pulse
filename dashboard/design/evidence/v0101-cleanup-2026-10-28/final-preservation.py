"""Verify preserved live configuration and Game data against the install rollback."""

import hashlib, json, sqlite3
from pathlib import Path

H = Path("/var/lib/smartpc-dashboard")
G = H / ".local/share/SmartPC/SmartPC/game"
B = Path("/var/backups/smartpc-maintenance/rollback-0.10.0-rc.2-20261028-200231")


def hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def game():
    with sqlite3.connect((G / "game.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        names = [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        tables = {
            n: db.execute('SELECT * FROM "' + n + '" ORDER BY rowid').fetchall()
            for n in names
        }
    return {
        "logicalDatabaseSha256": hashlib.sha256(
            json.dumps(tables, sort_keys=True, default=str).encode()
        ).hexdigest(),
        "tableCounts": {n: len(v) for n, v in tables.items()},
        "artifacts": {
            str(p.relative_to(G)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in G.rglob("*")
            if p.is_file() and not p.name.startswith("game.sqlite")
        },
    }


saved = json.loads((B / "preservation.json").read_text())
current = game()
assert current == saved["game"], "Game content differs from installation snapshot"
assert hashes(H / ".config") == saved["configurationHashes"], (
    "Configuration bytes differ"
)
result = {
    "status": "passed",
    "configurationBytesPreserved": True,
    "gameDatabasePreserved": True,
    "policyArtifactsPreserved": True,
    "policyArtifactCount": len(current["artifacts"]),
    "gameTableCounts": current["tableCounts"],
    "logicalDatabaseSha256": current["logicalDatabaseSha256"],
    "rollback": str(B),
}
print(json.dumps(result))
