#!/usr/bin/env python3
"""Delete only inventoried, externally verified historical SmartPC archives.

Default is validation only. Never follows symlinks or deletes live app roots.
The receipt must come from verification of every member of the off-board tar.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import time


def permitted(path):
    p = Path(path)
    if not p.is_absolute() or ".." in p.parts:
        return False
    if p.parent == Path("/var/backups"):
        return p.name.startswith("smartpc") and p.name not in {
            "smartpc-os-snapshots",
            "smartpc-os-pass2",
            "smartpc-apple-calm-current",
            "smartpc-maintenance",
        }
    if p.parent == Path("/opt/smartpc"):
        return (
            p.name.startswith(("dashboard-", "rc18-"))
            and p.name != "dashboard-before-completion-20261026-121653"
        )
    if p.parent == Path("/var/lib/smartpc-dashboard"):
        return p.name not in {
            ".cache",
            ".config",
            ".local",
            "game-runtime",
            "pilot-learner-runtime",
            "aquarium-backups",
            "maintenance-work",
            "maintenance-receipts",
        } and (
            p.is_dir()
            or p.suffix in {".py", ".qml", ".txt", ".tgz", ".tar"}
            or p.name.endswith(".tar.gz")
            or p.name.startswith(("game-performance-", "smartpc-evo-current-analysis"))
        )
    return str(p) in {
        "/home/smartpc/dp-kernel-fix/linux",
        "/var/tmp/smartpc-p0p9-metadata-copy",
        "/var/lib/smartpc-dashboard/aquarium-backups/20261026-035116",
        "/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game-racing-stage-20261021-132509",
    }


def open_references(roots):
    result = []

    def selected(target):
        return any(target == p or target.startswith(p + "/") for p in roots)

    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        for directory in ("fd", "map_files"):
            try:
                entries = list((proc / directory).iterdir())
            except FileNotFoundError:
                continue
            for entry in entries:
                try:
                    target = os.readlink(entry)
                except FileNotFoundError:
                    continue
                if selected(target):
                    result.append([proc.name, directory, target])
        for kind in ("cwd", "exe"):
            try:
                target = os.readlink(proc / kind)
            except FileNotFoundError:
                continue
            if selected(target):
                result.append([proc.name, kind, target])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise RuntimeError("Run as root to inspect every process and preserve metadata")
    raw = args.inventory.read_bytes()
    inventory = json.loads(raw)
    receipt = json.loads(args.receipt.read_text())
    if (
        receipt.get("status") != "passed"
        or receipt.get("inventorySha256") != hashlib.sha256(raw).hexdigest()
    ):
        raise ValueError("No matching verified off-board archive")
    if receipt.get("roots") != inventory["roots"]:
        raise ValueError("Archive root selection differs")
    roots = ["/" + p for p in inventory["roots"]]
    if not roots or any(not permitted(p) or Path(p).is_symlink() for p in roots):
        raise ValueError("Selection contains a protected or unsupported root")
    if any(p != q and p.startswith(q + "/") for p in roots for q in roots):
        raise ValueError("Overlapping roots")
    actual = set()
    for root in roots:
        pending = [root]
        while pending:
            name = pending.pop()
            s = os.lstat(name)
            relative = name.lstrip("/")
            actual.add(relative)
            expected = inventory["entries"].get(relative)
            if expected is None:
                raise ValueError("New file after backup: " + name)
            current = {
                "mode": s.st_mode,
                "uid": s.st_uid,
                "gid": s.st_gid,
                "mtimeNs": s.st_mtime_ns,
                "size": s.st_size,
                "dev": s.st_dev,
                "ino": s.st_ino,
                "nlink": s.st_nlink,
            }
            if any(expected[k] != v for k, v in current.items()):
                raise ValueError("Changed after backup: " + name)
            if stat.S_ISLNK(s.st_mode) and os.readlink(name) != expected["target"]:
                raise ValueError("Changed link: " + name)
            if stat.S_ISDIR(s.st_mode):
                pending.extend(os.path.join(name, n) for n in os.listdir(name))
    if actual != set(inventory["entries"]):
        raise ValueError("Inventory files disappeared after backup")
    references = open_references(roots)
    if references:
        raise ValueError("Open process references: " + repr(references[:20]))
    before = shutil.disk_usage("/")
    removed = []
    if args.apply:
        for root in roots:
            if Path(root).is_dir():
                shutil.rmtree(root)
            else:
                Path(root).unlink()
            removed.append(root)
        os.sync()
    after = shutil.disk_usage("/")
    report = {
        "status": "passed",
        "applied": args.apply,
        "checkedEntries": len(actual),
        "roots": roots,
        "removedRoots": removed,
        "openReferences": references,
        "externalArchiveSha256": receipt["archiveSha256"],
        "freeBytesBefore": before.free,
        "freeBytesAfter": after.free,
        "recoveredBytes": after.free - before.free,
        "completedAt": time.time(),
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in {"roots", "removedRoots"}}
        )
    )


if __name__ == "__main__":
    main()
