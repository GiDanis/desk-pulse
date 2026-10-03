#!/bin/bash
set -euo pipefail
install -d -m 700 /var/backups/smartpc-v066-operations
TASK_STAGE=$(mktemp -d /opt/smartpc-v066-deploy.XXXXXX)
cp -a /tmp/smartpc-v066-stage/dashboard "$TASK_STAGE/dashboard"
python3 /tmp/smartpc-package-dashboard.py verify "$TASK_STAGE/dashboard"
systemctl stop smartpc-dashboard.service
mv /opt/smartpc/dashboard "$TASK_STAGE/previous"
mv "$TASK_STAGE/dashboard" /opt/smartpc/dashboard
chown -R smartpc:smartpc /opt/smartpc/dashboard
systemctl start smartpc-dashboard.service
TASK_PID=$(systemctl show -p MainPID --value smartpc-dashboard.service)
sleep 8
if ! systemctl is-active --quiet smartpc-dashboard.service || [[ "$TASK_PID" == 0 ]] || [[ "$(systemctl show -p MainPID --value smartpc-dashboard.service)" != "$TASK_PID" ]]; then
 systemctl stop smartpc-dashboard.service
 mv /opt/smartpc/dashboard "$TASK_STAGE/failed"
 mv "$TASK_STAGE/previous" /opt/smartpc/dashboard
 systemctl start smartpc-dashboard.service
 exit 1
fi
TASK_PREVIOUS="/var/backups/smartpc-v066-operations/previous-$(date +%Y%m%d-%H%M%S)"
mv "$TASK_STAGE/previous" "$TASK_PREVIOUS"
rmdir "$TASK_STAGE"
python3 /tmp/smartpc-package-dashboard.py verify /opt/smartpc/dashboard
systemctl show -p ActiveState -p MainPID -p NRestarts smartpc-dashboard.service
