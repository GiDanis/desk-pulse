#!/bin/bash
# ==============================================================================
# DeskPulse - Enable Passwordless Sudo for Developer / Appliance User
# ==============================================================================
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

if [[ $EUID -ne 0 ]]; then
    echo "Questo script deve essere eseguito da root (sudo)." >&2
    exit 1
fi

user="${1:-${SUDO_USER:-smartpc}}"

if ! id "$user" >/dev/null 2>&1; then
    echo "[ERRORE] L'utente '$user' non esiste." >&2
    exit 1
fi

target="/etc/sudoers.d/99-${user}-nopasswd"
if [[ -e $target ]]; then
    cp -a "$target" "/root/99-${user}-nopasswd.backup.$(date +%s)"
fi

tmp=$(mktemp /etc/sudoers.d/.nopasswd.XXXXXX)
trap 'rm -f "$tmp"' EXIT

printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$user" > "$tmp"
chown root:root "$tmp"
chmod 440 "$tmp"
visudo -cf "$tmp"
mv "$tmp" "$target"
visudo -c
echo "✓ Sudo senza password configurato per l'utente: $user"
