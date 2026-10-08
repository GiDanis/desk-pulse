"""Transactional 0.8.3 install with EGLFS qualification and full rollback."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

STAGE = Path("/var/lib/smartpc-dashboard/v083-staging")
PROJECT = STAGE / "smartpc-v083-project"
RUNTIME = Path("/opt/smartpc/dashboard")
HOME_PATH = Path("/var/lib/smartpc-dashboard")
PROOF = HOME_PATH / "v083-proof"
DATA = HOME_PATH / ".local/share/SmartPC/SmartPC"
source = STAGE / "smartpc-v083-runtime-fontfix"
manifest = json.loads((source / "release-manifest.json").read_text())
assert manifest["version"] == "0.8.3-rc.1"
for relative, digest in manifest["sha256"].items():
    assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == digest, relative
assert not (source / "fixtures/theme-runtime/renderers").exists()
cache = json.loads((PROJECT / "theme-projects/apple-calm/evidence/preflight-cache.json").read_text())
assert cache["result"]["status"] == "passed" and cache["result"]["qt"] == "6.8.2"
assert cache["digest"] == "10bd33af67b331a2e2993ef83b7c5724800edeb078bd029a8ce08059e8ae0c86", "Exact final revision must pass native preflight"
before = json.loads((PROOF / "baseline-health.json").read_text())
assert before["version"] == "0.8.2-rc.1" and not before["manifestMismatches"]
assert before["activeTheme"]["id"] == "studio.applecalm", "Preserve the selected theme if it changed before this transaction"
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup = Path("/var/backups") / ("smartpc-before-v083-" + stamp)
backup.mkdir(mode=0o700)
started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
environment = ["HOME=" + str(HOME_PATH), "XDG_CONFIG_HOME=" + str(HOME_PATH / ".config"),
               "XDG_DATA_HOME=" + str(HOME_PATH / ".local/share"), "XDG_CACHE_HOME=/var/cache/smartpc-dashboard"]
eglfs = ["QT_QPA_PLATFORM=eglfs", "QT_QPA_EGLFS_INTEGRATION=eglfs_kms",
         "QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json", "QT_QPA_EGLFS_HIDECURSOR=1", "QSG_RHI_BACKEND=opengl"]
software = ["QT_QPA_PLATFORM=offscreen", "QT_QUICK_BACKEND=software"]


def run_user(arguments, log, graphics, timeout=120):
    with (PROOF / log).open("w") as stream:
        subprocess.run(["runuser", "-u", "smartpc", "--", "env", *environment, *graphics, "python3", *map(str, arguments)],
                       stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=timeout)


subprocess.run(["systemctl", "stop", "smartpc-dashboard"], check=True)
installed = False
backed_up = False
try:
    shutil.copytree(RUNTIME, backup / "dashboard")
    shutil.copytree(HOME_PATH / ".config", backup / "config")
    shutil.copytree(HOME_PATH / ".local", backup / "local")
    shutil.copytree("/var/cache/smartpc-dashboard", backup / "cache")
    backed_up = True
    for profile in ("base:day:off", "functional:night:off"):
        run_user([PROJECT / "dashboard/check_ux_consolidation_ui.py", "--profile", profile, "--capture-dir", PROOF / ("capture-"+profile.split(":")[0])],
                 "eglfs-" + profile.split(":")[0] + ".txt", eglfs)
    run_user([PROJECT / "dashboard/check_network_metrics_ui.py", "--capture", PROOF / "capture-network"], "eglfs-network-metrics.txt", eglfs, 120)
    run_user([PROJECT / "dashboard/check_consolidation_ui.py"], "eglfs-maintenance.txt", eglfs, 120)
    run_user([PROJECT / "theme-projects/apple-calm/tools/verify_main.py", "--output", PROOF / "apple-eglfs",
              "--palette", "night", "--surfaces", "sport.hub,settings.index,settings.display,settings.services,settings.sports,settings.appearance.management,settings.sources,network.overview,network.devices,network.detail,settings.network,network.router,network.wifi,network.ports,shell.main"], "apple-eglfs.txt", eglfs, 240)
    new = RUNTIME.with_name("dashboard-v083.new-" + stamp)
    shutil.copytree(source, new)
    RUNTIME.rename(backup / "replaced-runtime")
    try:
        new.rename(RUNTIME)
    except BaseException:
        (backup / "replaced-runtime").rename(RUNTIME)
        raise
    installed = True
    # The native preflight belongs to this exact immutable digest. Import does
    # not mutate an older bundle; activation chooses the new revision explicitly.
    importer = PROOF / "import-production.py"
    importer.write_text('''import json,sys
from pathlib import Path
sys.path.insert(0,"/opt/smartpc/dashboard")
from theme_bundle import BundleManager
proof=Path("/var/lib/smartpc-dashboard/v083-proof")
cache=json.loads((proof/"native-theme-preflight.json").read_text())
revision=BundleManager(Path("/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC")).import_bundle(Path("/var/lib/smartpc-dashboard/v083-staging/smartpc-apple-calm-1.3.0-fontfix.smartpc-theme"),preflight=lambda *_:cache["result"],require_preflight=True)
assert revision["digest"]==cache["digest"] and revision["version"]=="1.3.0"
(proof/"production-theme-import.json").write_text(json.dumps(revision,indent=2)+"\\n")
''')
    run_user([importer], "theme-import.txt", software)
    theme_manifest = PROOF / "theme-selection.json"
    theme_manifest.write_text(json.dumps({"themeVersion": "1.3.0", "bundleDigest": cache["digest"]}))
    helper = PROJECT / "theme-projects/apple-calm/tools/activate_board.py"
    run_user([helper, "--dashboard", RUNTIME, "--output", PROOF / "activation", "--manifest", theme_manifest, "--apply"],
             "theme-activation.txt", software)
    run_user([helper, "--dashboard", RUNTIME, "--output", PROOF / "cold-verify", "--manifest", theme_manifest],
             "theme-cold-verify.txt", software)
    subprocess.run(["systemctl", "start", "smartpc-dashboard"], check=True)
    deadline = time.monotonic() + 40
    while True:
        run_user(["/var/lib/smartpc-dashboard/v083-proof/board-health.py", "--output", PROOF / "installed-health.json"], "installed-health.txt", software)
        after = json.loads((PROOF / "installed-health.json").read_text())
        heartbeat = after["guiHeartbeat"]
        if heartbeat and heartbeat["ready"] and 0 <= heartbeat["ageSeconds"] < 15:
            break
        assert time.monotonic() < deadline, "GUI readiness/heartbeat missing after bounded startup wait"
        time.sleep(2)
    assert after["version"] == manifest["version"] and not after["manifestMismatches"]
    assert after["service"]["ActiveState"] == "active" and after["service"]["NRestarts"] == "0"
    assert after["guiHeartbeat"] and after["guiHeartbeat"]["ready"] and 0 <= after["guiHeartbeat"]["ageSeconds"] < 15
    assert after["guiHeartbeat"]["selection"] == after["activeTheme"] and after["guiHeartbeat"]["pending"] is None
    assert all(after["preferenceHashes"].get(key)==digest for key,digest in before["preferenceHashes"].items()), "Existing preferences changed"
    assert set(after["preferenceHashes"])-set(before["preferenceHashes"]) == {"navigation/schemaVersion","navigation/sportVisible"}
    assert after["activeTheme"]["version"] == "1.3.0" and after["activeTheme"]["digest"] == cache["digest"]
    journal = subprocess.check_output(["journalctl", "-u", "smartpc-dashboard", "--since", started, "--no-pager"], text=True)
    warnings = [line for line in journal.splitlines() if any(marker in line for marker in
                ("ReferenceError", "TypeError", "Binding loop", "QQmlApplicationEngine failed", "Traceback", "Segmentation fault"))]
    assert not warnings, warnings
    (PROOF / "installed-journal.txt").write_text(journal)
    receipt = {"status": "passed", "version": manifest["version"], "files": len(manifest["sha256"]), "navigationMigrationAddedKeys": ["navigation/schemaVersion","navigation/sportVisible"],
               "backup": str(backup), "preferencesPreserved": True, "manifestVerified": True,
               "theme": after["activeTheme"], "bootIdBefore": before["bootId"], "installedAt": time.time(),
               "qmlWarnings": warnings, "restartKind": "service restart; reboot proof separate"}
    (PROOF / "install-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)
except BaseException:
    subprocess.run(["systemctl", "stop", "smartpc-dashboard"], check=False)
    if installed:
        shutil.rmtree(RUNTIME)
        shutil.copytree(backup / "dashboard", RUNTIME)
    if backed_up:
        # Restore the transaction state without ever lowering the Casa consumption ledger.
        newest_budgets = {p.name:p.read_bytes() for p in (HOME_PATH/".local/state/smartpc/casa").glob("*-budget.json")}
        for saved, target in (("config", HOME_PATH / ".config"), ("local", HOME_PATH / ".local"),
                              ("cache", Path("/var/cache/smartpc-dashboard"))):
            shutil.rmtree(target)
            shutil.copytree(backup / saved, target)
            subprocess.run(["chown", "-R", "smartpc:smartpc", str(target)], check=True)
        for name,content in newest_budgets.items():
            destination=HOME_PATH/".local/state/smartpc/casa"/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(content)
            subprocess.run(["chown","smartpc:smartpc",str(destination)],check=True)
    raise
finally:
    subprocess.run(["systemctl", "start", "smartpc-dashboard"], check=True)
