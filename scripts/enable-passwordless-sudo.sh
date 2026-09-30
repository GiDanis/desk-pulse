#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID == 0 ]]
[[ $(id -u giuseppe) == 1000 ]]
target=/etc/sudoers.d/99-giuseppe-nopasswd
if [[ -e $target ]]; then
    cp -a "$target" "/root/99-giuseppe-nopasswd.backup.$(date +%s)"
fi
tmp=$(mktemp /etc/sudoers.d/.giuseppe-nopasswd.XXXXXX)
trap 'rm -f "$tmp"' EXIT
printf 'giuseppe ALL=(ALL:ALL) NOPASSWD: ALL\n' > "$tmp"
chown root:root "$tmp"
chmod 440 "$tmp"
visudo -cf "$tmp"
mv "$tmp" "$target"
visudo -c
