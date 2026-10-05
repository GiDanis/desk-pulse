#!/usr/bin/env bash
set -u
stage=/tmp/smartpc-theme-17db764-diagnostics
evidence=/var/tmp/smartpc-theme-17db764-final
mkdir -p "$evidence/offscreen" "$evidence/eglfs"
cd "$stage" || exit 1
runcheck() {
 local label="$1"; shift
 timeout 120s "$@" > "$evidence/$label.log" 2>&1
 local result=$?
 printf '%s %s\n' "$label" "$result" >> "$evidence/status.txt"
}
export QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software SMARTPC_TEST_OPTIONAL_LINT=1
runcheck offscreen/data-domains python3 check_theme_data_domains.py
runcheck offscreen/data-domains-main python3 check_theme_data_domains.py --main-proof
runcheck offscreen/pending-context python3 check_theme_pending_context_ui.py "$evidence/offscreen/pending-context.json"
sudo -n systemctl stop smartpc-dashboard.service || exit 1
trap 'sudo -n systemctl start smartpc-dashboard.service' EXIT
export QT_QPA_PLATFORM=eglfs QT_QPA_EGLFS_INTEGRATION=eglfs_kms QT_QPA_EGLFS_HIDECURSOR=1 QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json QSG_RHI_BACKEND=opengl
unset QT_QUICK_BACKEND
runcheck eglfs/layout-ui python3 check_theme_layout_ui.py --output "$evidence/eglfs/layout-ui.json"
runcheck eglfs/public-motion python3 verify_theme_public_motion.py --output "$evidence/eglfs/public-motion.json"
runcheck eglfs/notifications python3 check_theme_bundle_acceptance.py --case notifications --output "$evidence/eglfs/notifications.json"
runcheck eglfs/overlay python3 check_theme_bundle_acceptance.py --case overlay --output "$evidence/eglfs/overlay.json"
cat "$evidence/status.txt"
