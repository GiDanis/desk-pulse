#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
id smartpc >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo smartpc
usermod -p '*' smartpc
install -d -m 700 -o smartpc -g smartpc /home/smartpc/.ssh
install -m 600 -o smartpc -g smartpc /etc/smartpc/authorized_keys /home/smartpc/.ssh/authorized_keys
printf 'smartpc ALL=(ALL:ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/90-smartpc
chmod 440 /etc/sudoers.d/90-smartpc
visudo -cf /etc/sudoers.d/90-smartpc
usermod -L root
chage -d "$(date +%Y-%m-%d)" -M -1 root
chage -d "$(date +%Y-%m-%d)" -M -1 smartpc
timedatectl set-timezone Europe/Rome
ssh-keygen -A
mkdir -p /var/lib/smartpc
touch /var/lib/smartpc/provisioned
