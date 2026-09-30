#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
image='/home/giuseppe/Documenti/Workspace/SmartPC/os/Armbian_26.8.1_Orangepizero3w_trixie_vendor_6.6.98_minimal.img'
device='/dev/disk/by-id/usb-Mass_Storage_Device_121220130416-0:0'
[[ $EUID -eq 0 ]] || { echo 'Serve autenticazione amministratore.'; exit 1; }
[[ -b "$device" && -f "$image" ]]
[[ $(blockdev --getsize64 "$device") == 31440502784 ]]
[[ $(blkid -p -s UUID -o value "${device}-part1") == B6D0-9AA5 ]]
[[ $(stat -c %s "$image") == 1870659584 ]]
echo 'Destinazione verificata: microSD sostitutiva 32 GB, UUID B6D0-9AA5.'
if findmnt -rn -S "$(readlink -f "${device}-part1")" >/dev/null; then
    umount "${device}-part1"
fi
echo 'Scrittura Armbian Debian 13 sulla microSD...'
dd if="$image" of="$device" bs=4M conv=fsync status=progress
sync
blockdev --flushbufs "$device"
echo 'Verifica integrale dei byte scritti...'
cmp -n "$(stat -c %s "$image")" "$image" "$device"
echo 'VERIFICA COMPLETATA: microSD identica all’immagine.'
blockdev --rereadpt "$device"
udevadm settle
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS "$(readlink -f "$device")"
