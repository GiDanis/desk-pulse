#!/bin/bash
# ==============================================================================
# DeskPulse - MicroSD Integrity & Filesystem Repair Checker
# ==============================================================================
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

dev="${1:-}"

if [[ -z "$dev" ]]; then
    echo "Dispositivi disponibili:"
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS
    echo ""
    read -rp "Inserisci la partizione da verificare (es. /dev/sdb1 o /dev/mmcblk0p1): " dev
fi

if [[ ! -b "$dev" ]]; then
    echo "[ERRORE] Dispositivo $dev non valido o inesistente." >&2
    exit 1
fi

echo "Controllo partizione $dev..."
if findmnt -rn -S "$(readlink -f "$dev")" >/dev/null 2>&1; then
    echo "Smontaggio partizione attiva..."
    umount "$dev"
fi

set +e
echo "Esecuzione fsck in corso..."
e2fsck -f -p "$dev"
status=$?
set -e

echo "Esito fsck: $status"
if [[ $status -le 1 ]]; then
    echo "✓ Filesystem integro o corretto con successo."
else
    echo "⚠ Riparazione terminata con codice $status."
    exit "$status"
fi

# Verifica in sola lettura di conferma
e2fsck -f -n "$dev"
echo "✓ Verifica completata."
