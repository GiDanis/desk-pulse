#!/usr/bin/env bash
# ==============================================================================
# DeskPulse - Safe SD Card Flasher
# ==============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Questo script richiede privilegi di amministratore (sudo)." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

image="${1:-}"
device="${2:-}"

# Auto-detect image if not specified
if [[ -z "$image" ]]; then
    default_img="$(find "$REPO_DIR/os" -maxdepth 2 -name "*.img" ! -name "*headless*" 2>/dev/null | head -n 1 || true)"
    if [[ -n "$default_img" ]]; then
        image="$default_img"
    else
        read -rp "Percorso file immagine OS (.img): " image
    fi
fi

if [[ ! -f "$image" ]]; then
    echo "[ERRORE] File immagine non trovato: $image" >&2
    exit 1
fi

# List available block devices if device not specified
if [[ -z "$device" ]]; then
    echo "Dispositivi di memoria disponibili:"
    lsblk -d -o NAME,SIZE,TYPE,TRAN,MODEL,VENDOR
    echo ""
    read -rp "Inserisci il device di destinazione (es. /dev/sdX o /dev/mmcblkX): " device
fi

if [[ ! -b "$device" ]]; then
    echo "[ERRORE] Il dispositivo $device non esiste o non è un block device valido." >&2
    exit 1
fi

# Safety guard: ensure not root drive
root_drive="$(findmnt -n -o SOURCE / | sed 's/[0-9]*$//; s/p[0-9]*$//')"
if [[ "$(readlink -f "$device")" == "$(readlink -f "$root_drive")" ]]; then
    echo "[PERICOLO] Il device selezionato ($device) corrisponde al disco di sistema in uso!" >&2
    exit 1
fi

echo ""
echo "=== RIEPILOGO SCRITTURA ==="
echo "Immagine sorgente: $image ($(du -h "$image" | cut -f1))"
echo "Dispositivo target: $device ($(lsblk -d -n -o SIZE "$device"))"
echo "==========================="
read -rp "ATTENZIONE: Tutti i dati su $device verranno cancellati. Procedere? (digitare 'SI'): " confirm

if [[ "$confirm" != "SI" ]]; then
    echo "Operazione annullata."
    exit 0
fi

# Unmount any mounted partitions
echo "Smontaggio partizioni attive su $device..."
for part in "${device}"* ; do
    if findmnt -rn -S "$(readlink -f "$part")" >/dev/null 2>&1; then
        umount "$part" || true
    fi
done

echo "Scrittura in corso..."
dd if="$image" of="$device" bs=4M conv=fsync status=progress
sync
blockdev --flushbufs "$device"

echo "Verifica integrità dei byte scritti..."
cmp -n "$(stat -c %s "$image")" "$image" "$device"
echo "✓ VERIFICA COMPLETATA: microSD identica all'immagine sorgente."

blockdev --rereadpt "$device" || true
udevadm settle || true
echo ""
echo "Partizionamento finale:"
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS "$(readlink -f "$device")"
