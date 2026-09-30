#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
dev=/dev/disk/by-id/usb-Mass_Storage_Device_121220130416-0:0-part1
target_uuid=$(blkid -s UUID -o value "$dev" 2>/dev/null || true)
[[ "$target_uuid" =~ ^(932dec6a-307e-4174-8694-c4a1ef18eef4|d8bcf295-3d76-4436-be46-7c06b17369f9|B6D0-9AA5)$ ]]
if findmnt -rn -S "$(readlink -f "$dev")" >/dev/null; then umount "$dev"; fi
set +e
e2fsck -f -p "$dev"
status=$?
set -e
echo "Esito riparazione filesystem: $status"
[[ $status -le 1 ]] || exit "$status"
e2fsck -f -n "$dev"
