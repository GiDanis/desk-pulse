#!/bin/bash
set -euo pipefail
sudo systemctl stop smartpc-dashboard.service
trap 'sudo systemctl start smartpc-dashboard.service' EXIT
export QT_QPA_PLATFORM=eglfs QT_QPA_EGLFS_INTEGRATION=eglfs_kms QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json QT_QPA_EGLFS_HIDECURSOR=1 QSG_RHI_BACKEND=opengl
unset QT_QUICK_BACKEND
TASK_DASH=/tmp/smartpc-v066-stage/dashboard
python3 "$TASK_DASH/verify_notifications_board.py" --directory /tmp/smartpc-notifications-eglfs/stress-presets --fonts none
python3 "$TASK_DASH/verify_notifications_board.py" --directory /tmp/smartpc-notifications-eglfs/stress-fonts --fonts three
for variant in day night; do
 for motion in normal reduced off; do
  python3 "$TASK_DASH/check_notifications.py" --capture-dir "/tmp/smartpc-notifications-eglfs/$variant-$motion" --motion "$motion" --variant "$variant"
 done
done

python3 "$TASK_DASH/verify_theme_board.py" --dashboard "$TASK_DASH" --directory /tmp/smartpc-notifications-eglfs/current --duration 20
