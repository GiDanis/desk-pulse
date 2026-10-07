#!/usr/bin/env bash
# Latest verified Core + Apple Calm, transactional install with exact rollback.
set -euo pipefail
stage=${1:?Usage: install_board.sh STAGE ARCHIVE BACKUP}
archive=${2:?Archive required}
backup=${3:?Fresh transaction backup directory required}
stage=$(realpath "$stage")
case "$stage" in
    /tmp/*|/var/tmp/*) echo "Use a persistent staging directory under /var/lib/smartpc-dashboard; proofs must survive reboot." >&2; exit 2 ;;
esac
runtime=/opt/smartpc/dashboard
data=/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC
evidence="$stage/theme-projects/apple-calm/evidence/optimization-installation"
manifest="$stage/theme-projects/apple-calm/evidence/optimization-installation-manifest.json"
mkdir -p "$evidence"
test "$(id -un)" = smartpc
test "$(sha256sum "$archive" | cut -d ' ' -f1)" = "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["packageSha256"])' "$manifest")"
python3 - "$stage" "$manifest" <<'PY'
import hashlib,json,sys
from pathlib import Path
stage,manifest=map(Path,sys.argv[1:]);expected=json.loads(manifest.read_text());base=stage/'theme-projects/apple-calm/evidence'
for name in ('optimization-board-eglfs-night','optimization-board-eglfs-day'):
    report=json.loads((base/name/'report.json').read_text())
    assert report['status']=='passed' and report['platform']=='eglfs' and report['windowSize']==[960,640]
    assert report['revision']['digest']==expected['bundleDigest'] and not report['qmlWarnings']
    assert len(report['canonicalCases'])>=48 and len(report['navigationDots']['motion'])==3
for name in ('baseline-eglfs','optimized-eglfs'):
    report=json.loads((base/name/'report.json').read_text())
    assert report['status']=='passed' and report['platform']=='eglfs' and not report['qmlWarnings']
assert json.loads((base/'optimization-heartbeat-eglfs.json').read_text())['status']=='passed'
for name,digest in expected['files'].items():assert hashlib.sha256((stage/'runtime-distribution'/name).read_bytes()).hexdigest()==digest,name
for name,digest in expected['previousFiles'].items():assert hashlib.sha256((Path('/opt/smartpc/dashboard')/name).read_bytes()).hexdigest()==digest,'installed baseline changed: '+name
PY
changed=0
finish() {
    result=$?
    if (( result != 0 && changed == 1 )); then
        sudo -n systemctl stop smartpc-dashboard.service
        sudo -n rm -rf "$runtime"
        sudo -n rm -rf "$data"
        sudo -n tar -xzf "$backup/before.tar.gz" -C /
    fi
    sudo -n systemctl start smartpc-dashboard.service
    exit "$result"
}
trap finish EXIT
sudo -n systemctl stop smartpc-dashboard.service
sudo -n install -d -m 0700 "$backup"
sudo -n tar -czf "$backup/before.tar.gz" -C / opt/smartpc/dashboard var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf
sudo -n tar -tzf "$backup/before.tar.gz" > "$evidence/backup-inventory.txt"
sudo -n sha256sum "$backup/before.tar.gz" > "$evidence/backup.sha256"
date --iso-8601=seconds > "$evidence/started-at.txt"
changed=1
# The recursive distribution includes the current Casa implementation and only
# the changes validated above. Providers and cache directories are untouched.
sudo -n cp -a "$stage/runtime-distribution/." "$runtime/"
sudo -n chown -R smartpc:smartpc "$runtime"
export QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software
export XDG_CONFIG_HOME=/var/lib/smartpc-dashboard/.config XDG_DATA_HOME=/var/lib/smartpc-dashboard/.local/share XDG_CACHE_HOME=/var/cache/smartpc-dashboard
python3 - "$runtime" "$archive" "$stage" "$manifest" "$data" "$evidence" <<'PY'
import json,sys
from pathlib import Path
runtime,archive,stage,manifest,data,evidence=map(Path,sys.argv[1:]);sys.path.insert(0,str(runtime))
from PySide6.QtCore import qVersion
from theme_bundle import BundleManager
from theme_runtime import preflight
expected=json.loads(manifest.read_text());cache=json.loads((stage/'theme-projects/apple-calm/evidence/preflight-cache.json').read_text())
assert cache['digest']==expected['bundleDigest'] and cache['result']['status']=='passed' and cache['result']['qt']==qVersion()
# This is the real preflight result for this immutable digest and native Qt.
revision=BundleManager(data,app_root=runtime).import_bundle(archive,preflight=lambda *_:cache['result'],require_preflight=True)
assert revision['digest']==expected['bundleDigest']
(evidence/'import-report.json').write_text(json.dumps(revision,indent=2)+'\n')
PY
python3 "$stage/theme-projects/apple-calm/tools/activate_board.py" --dashboard "$runtime" --manifest "$manifest" --output "$evidence/activation" --apply > "$evidence/activation.log" 2>&1
python3 "$stage/theme-projects/apple-calm/tools/activate_board.py" --dashboard "$runtime" --manifest "$manifest" --output "$evidence/cold-verify" > "$evidence/cold-verify.log" 2>&1
sudo -n systemctl start smartpc-dashboard.service
sleep 8
python3 "$stage/theme-projects/apple-calm/tools/verify_installed_state.py" --manifest "$manifest" --backup "$backup" --output "$evidence/installed-state.json" > "$evidence/installed-state.log" 2>&1
sudo -n journalctl -u smartpc-dashboard.service --since "$(cat "$evidence/started-at.txt")" --no-pager > "$evidence/production-journal.log"
changed=0
trap - EXIT
