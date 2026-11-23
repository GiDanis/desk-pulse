#!/usr/bin/env bash
# Native EGLFS QA with isolated state; restore the kiosk on every exit.
set -euo pipefail
stage=${1:?Usage: verify_board.sh STAGE SPORT_CACHE_JSON}
cache=${2:?Provide a copy of the existing sport cache; no provider requests}
cd "$stage"
trap 'sudo -n systemctl start smartpc-dashboard.service' EXIT
sudo -n systemctl stop smartpc-dashboard.service
export QT_QPA_PLATFORM=eglfs QT_QPA_EGLFS_INTEGRATION=eglfs_kms QT_QPA_EGLFS_HIDECURSOR=1
export QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json QSG_RHI_BACKEND=opengl
unset QT_QUICK_BACKEND QSG_INFO
project=theme-projects/apple-calm
evidence=$project/evidence
python3 "$project/tools/verify_optimization.py" --sport-cache "$cache" --cycles 3 --output "$evidence/optimized-eglfs" > "$evidence/optimized-eglfs.log" 2>&1
python3 "$project/tools/verify_main.py" --all --palette night --output "$evidence/optimization-board-eglfs-night" > "$evidence/optimization-board-eglfs-night.log" 2>&1
python3 "$project/tools/verify_main.py" --palette day --output "$evidence/optimization-board-eglfs-day" > "$evidence/optimization-board-eglfs-day.log" 2>&1
python3 "$project/tools/verify_heartbeat.py" --output "$evidence/optimization-heartbeat-eglfs.json" > "$evidence/optimization-heartbeat-eglfs.log" 2>&1
