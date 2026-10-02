#!/usr/bin/env bash
# ==============================================================================
# DeskPulse - Turnkey Board Setup Script for Orange Pi Zero 3W / Debian / Armbian
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}       ⚡ DeskPulse - Automated Board Setup ⚡       ${NC}"
echo -e "${BLUE}======================================================${NC}"

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERROR] This installer must be run as root (or with sudo).${NC}" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${YELLOW}[1/6] Installing system packages & Qt 6 Quick runtime...${NC}"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-requests \
    libqt6gui6 \
    libqt6qml6 \
    libqt6quick6 \
    qml6-module-qtquick \
    qml6-module-qtquick-controls \
    qml6-module-qtquick-layouts \
    qml6-module-qtquick-shapes \
    qml6-module-qtquick-window \
    qml6-module-qtwebsockets \
    libqt6websockets6 \
    libgl1-mesa-dri \
    evtest

# Install PySide6 if not installed via apt
if ! python3 -c 'import PySide6.QtQuick' >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing PySide6 via apt/pip...${NC}"
    apt-get install -y python3-pyside6.qtquick python3-pyside6.qtwebsockets || python3 -m pip install --break-system-packages PySide6 requests
fi
# The small native WebSocket module supplies the F1 SignalR Core transport.
if ! python3 -c 'import PySide6.QtWebSockets' >/dev/null 2>&1; then
    apt-get install -y --no-install-recommends python3-pyside6.qtwebsockets || python3 -m pip install --break-system-packages PySide6
fi

echo -e "${YELLOW}[2/6] Configuring dedicated system user & permissions...${NC}"
if ! id smartpc >/dev/null 2>&1; then
    useradd -m -s /bin/bash -G sudo,video,render,input smartpc
    echo -e "${GREEN}Created system user 'smartpc'.${NC}"
else
    usermod -aG video,render,input smartpc
fi

# Ensure user directories exist
mkdir -p /var/lib/smartpc-dashboard /var/cache/smartpc-dashboard
chown -R smartpc:smartpc /var/lib/smartpc-dashboard /var/cache/smartpc-dashboard
chmod 750 /var/lib/smartpc-dashboard /var/cache/smartpc-dashboard

echo -e "${YELLOW}[3/6] Deploying DeskPulse dashboard to /opt/smartpc/dashboard...${NC}"
# Build a complete recursive distribution; cp -u can retain removed files.
STAGING_DIR="$(mktemp -d /opt/smartpc-stage.XXXXXX)"
python3 "$REPO_DIR/scripts/package-dashboard.py" build --source "$REPO_DIR/dashboard" --output "$STAGING_DIR/dashboard"
python3 "$REPO_DIR/scripts/package-dashboard.py" verify "$STAGING_DIR/dashboard"
mkdir -p /opt/smartpc /var/backups
if [[ -d /opt/smartpc/dashboard ]]; then
    tar -czf "/var/backups/smartpc-before-$(date +%Y%m%d-%H%M%S).tar.gz" -C /opt/smartpc dashboard
    systemctl stop smartpc-dashboard.service || true
    mv /opt/smartpc/dashboard "$STAGING_DIR/previous"
fi
mv "$STAGING_DIR/dashboard" /opt/smartpc/dashboard
chown -R smartpc:smartpc /opt/smartpc
chmod +x /opt/smartpc/dashboard/run.sh
# Keep the previous checkout until the service starts successfully.

echo -e "${YELLOW}[4/6] Setting up KMS / EGLFS graphics configuration...${NC}"
mkdir -p /etc/smartpc
if [[ -f "$REPO_DIR/os/system/eglfs-kms.json" ]]; then
    cp "$REPO_DIR/os/system/eglfs-kms.json" /etc/smartpc/eglfs-kms.json
else
    cat << 'EOF' > /etc/smartpc/eglfs-kms.json
{
  "device": "/dev/dri/card0",
  "hwcursor": false
}
EOF
fi
chmod 644 /etc/smartpc/eglfs-kms.json

echo -e "${YELLOW}[5/6] Installing and configuring systemd service...${NC}"
cp "$REPO_DIR/os/system/smartpc-dashboard.service" /etc/systemd/system/smartpc-dashboard.service
systemctl daemon-reload

# Disable desktop display manager if running (LightDM / GDM) to release KMS display
if systemctl is-active --quiet lightdm; then
    echo -e "${YELLOW}Disabling LightDM to allow direct KMS EGLFS execution...${NC}"
    systemctl disable --now lightdm || true
fi

echo -e "${YELLOW}[6/6] Enabling and starting DeskPulse dashboard...${NC}"
systemctl enable smartpc-dashboard.service
systemctl restart smartpc-dashboard.service
DEPLOY_PID="$(systemctl show -p MainPID --value smartpc-dashboard.service)"
sleep 8
if ! systemctl is-active --quiet smartpc-dashboard.service || [[ "$DEPLOY_PID" == "0" ]] || [[ "$(systemctl show -p MainPID --value smartpc-dashboard.service)" != "$DEPLOY_PID" ]]; then
    if [[ -d "$STAGING_DIR/previous" ]]; then
        systemctl stop smartpc-dashboard.service || true
        mv /opt/smartpc/dashboard "$STAGING_DIR/failed"
        mv "$STAGING_DIR/previous" /opt/smartpc/dashboard
        systemctl start smartpc-dashboard.service
    fi
    echo "Dashboard start failed; previous distribution restored." >&2
    exit 1
fi
rm -rf "$STAGING_DIR"

echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}  ✓ DeskPulse installed and running successfully!     ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Check service status with: ${BLUE}sudo systemctl status smartpc-dashboard${NC}"
echo -e "View real-time logs with:  ${BLUE}sudo journalctl -u smartpc-dashboard -f${NC}"
