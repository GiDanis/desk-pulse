# Orange Pi Zero 3W: OS review (2026-09-29)

Target: always-on SmartPC clock and animated UI on the Hagibis 960×640/60 Hz USB-C display. Development happens on the PC and files are transferred over SSH.

## Verified baseline

- Orange Pi Debian 13 Trixie desktop, kernel `6.6.98-sun60iw2` with the local USB-C DP PLL fix selected at boot.
- Wi-Fi, SSH, LightDM and DP video reconnect after reboot. DP mode is 960×640/60 Hz.
- 5.7 GiB RAM, 2.9 GiB zram swap, about 21 GiB free on the 29 GiB ext4 microSD.
- CPU/GPU thermal zones were about 43 °C at idle after reboot; time synchronisation was active.
- SSH accepts public keys and rejects password and root login.

## Graphics result

- GLX reports Mesa `llvmpipe`, while EGL on X11 reports `PowerVR B-Series BXM-4-64`. A Qt Quick scene launched with `QT_XCB_GL_INTEGRATION=xcb_egl` and `QSG_RHI_BACKEND=opengl` logged that same PowerVR renderer.
- Under X11, Qt warned about broken vsync throttling. A five-second 960×640 smoke animation reported about 65.6 swaps/s and 17 ms p95 frame interval. This is a diagnostic scene, not a full UI benchmark.
- Direct EGLFS initially found no screen. Setting `QT_QPA_EGLFS_INTEGRATION=eglfs_kms` and `QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json` selected `/dev/dri/card0`; the same scene then reported 60 swaps/s and 18 ms p95 frame interval over five seconds on the PowerVR. The driver logged cursor-plane warnings, so cursor behavior still needs a separate test if the final app needs a pointer.
- When building the real UI, prefer the proven EGLFS/KMS path and profile the complete animation workload. The simple scene alone cannot prove sustained 60 fps for the product.

Diagnostic scene: [qtquick-gpu-smoke.qml](diagnostics/qtquick-gpu-smoke.qml). EGLFS device config: [eglfs-kms.json](system/eglfs-kms.json).

## Changes applied

- Disabled `smartmontools` (no SMART-capable disk), CUPS print services, and Docker/containerd (no containers). Packages remain installed and can be enabled again if needed. No failed systemd services remain.
- Changed ext4 `commit=600` to `commit=30` in `/etc/fstab`, and remounted. This reduces the journal commit window in case of a power outage; `noatime`, tmpfs `/tmp`, and zram remain active to limit microSD writes. Previous fstab saved as `/etc/fstab.smartpc-before-audit`. Follow-up inspection corrected the initial ramlog assessment: its service is installed, but `ENABLED=false` means `/var/log` is on the microSD.
- Disabled automatic X screen blanking and DPMS. The Hagibis stays on after inactivity and after reboot.
- Added a day/night X11 software brightness schedule: 1.0 from 07:00 to 20:59; 0.65 from 21:00 to 06:59 (Europe/Rome). `ddcutil detect` found no DDC display and `/sys/class/backlight` is empty, so this changes image brightness, not the physical backlight. The scheduled setting was verified after reboot. Configuration is in [system/](system/).
- Installed the small Qt 6 Quick runtime needed for the graphics test, plus `ddcutil` for the read-only brightness capability check.

## Next product step

Build the first 960×640 fullscreen clock in Qt Quick, launch it with EGLFS/KMS, and measure frame times under the real UI workload. When X11/LightDM is replaced by direct EGLFS, move night dimming into the Qt app because `xrandr` applies only to the current X11 desktop.

## Second pass: continuous-operation reliability

- The old Wi-Fi recovery service unconditionally ran `nmcli connection up`, disconnecting an already healthy connection after boot. Replaced it with [smartpc-wifi-connect](system/smartpc-wifi-connect), which waits for NetworkManager startup and only activates Wi-Fi if disconnected. NetworkManager autoconnect retries are now unlimited (`0`).
- Disabled unused dnsmasq, strongSwan, BRLTTY and LIRC services/socket. There were no VPN connections configured, and DNS resolution uses NetworkManager's external nameservers rather than dnsmasq. Verified DNS resolution after stopping it.
- Removed duplicate syslog writes by disabling rsyslog and journal forwarding. The journal stays persistent with a 50 MiB limit; normal journal sync interval is now five minutes. Recent low-priority log records may be lost on sudden power failure. This setting does not change application/database fsync behavior. Existing text logs are retained, but fresh system diagnostics should be read with `journalctl`.
- APT periodic jobs had been globally disabled. Enabled daily package-index refresh while keeping automatic installation and automatic reboot disabled. Index refresh completed successfully and revealed 171 pending updates.
- Backed up changed pre-existing configuration and service states on the board under `/var/backups/smartpc-os-pass2/`. New configuration is tracked locally in `os/system/`.

Rollback: restore the Wi-Fi unit from that backup and remove the new journal/APT drop-ins; re-enable the affected services as needed. Restore the connection retry policy with `nmcli connection modify 'Orange Pi wireless' connection.autoconnect-retries -1`. Run `systemctl daemon-reload` after restoring units.

## Security update and graphics package conflict

- Simulated the general upgrade ([plan](diagnostics/apt-upgrade-plan.txt)). It included third-party Chrome and Docker packages, so that attempt was stopped during download before any packages were installed.
- Selected Debian security updates only, excluding the VLC packages that were already held ([package selection](diagnostics/security-packages-20260929.txt), [simulation](diagnostics/apt-security-plan.txt)). The simulation proposed 69 upgrades without added or removed packages.
- The new Debian `xserver-xorg-core` package could not unpack because the Orange Pi package `xserver-xorg-img-bxm-1.21.1-2.deb` owns its `modesetting_drv.so`. The vendor driver is needed for the proven display/GPU path. Held `xserver-xorg-core`, `xserver-common`, and the vendor Xorg package against future accidental replacement. Configured the remaining unpacked packages and verified `apt-get check` and `dpkg --audit` are clean. `xserver-common` was upgraded; `xserver-xorg-core` remains at `2:21.1.16-1.3+deb13u3`.
- 68 upgrades completed; 103 remain available, including ordinary packages deliberately left for a separate compatibility review. Automatic installation stays off. The vendor kernel image and Xorg driver hashes remained unchanged.
- After reboot, Wi-Fi connected once, SSH and LightDM were active, the Hagibis was still 960×640 with brightness 0.65 and DPMS off, and a Qt Quick smoke scene still reported the PowerVR renderer. There were no failed services. Boot measured 19.1 seconds on this run (about 31 seconds before the second-pass service changes).

The Xorg hold means that Debian's X server security update is pending. Any future attempt to apply it should first repackage or port the Orange Pi driver and test both DP output and EGL acceleration on a recoverable SD image.

## SmartPC dashboard kiosk

- Installed the Qt Quick/PySide6 dashboard at `/opt/smartpc/dashboard`; added the Debian PySide6 QML/Quick packages without upgrading or removing existing packages.
- Added `smartpc-dashboard.service`, enabled on `multi-user.target`, running as the restricted `smartpc` account with `video`, `render` and `input` device groups. `Restart=always` restarts it after process failure.
- The service conflicts with `display-manager.service`; LightDM remains installed/enabled but is inactive while the kiosk service runs. EGLFS/KMS owns the display fullscreen. The QML cursor is blank and the KMS hardware cursor plane is disabled to avoid the driver's cursor-plane warnings.
- Rebooted to verify boot startup: the service came up active without a restart, `display-manager.service` stayed inactive, DP-1 reported connected, and kernel console blanking remained `0`. Forced `SIGKILL` once before reboot; systemd started the app again with a new PID.
- To return to XFCE manually: `sudo systemctl disable --now smartpc-dashboard && sudo systemctl start lightdm`.

## Dashboard v0.1 resource review

- Removed the full-screen background rectangle that overpainted the window's own background color. The weekday/month arrays are now initialized once, and the date label updates only if the day changes.
- A 30-second idle sample on the running EGLFS/KMS kiosk showed about 0.5% CPU on one core, 85–87 MiB RSS, and about 56 MiB PSS. No animation or diagnostics were active; the display refreshed on the one-second clock updates. The temporary diagnostic mode intentionally animates continuously to measure frame pacing.

## 2026-09-30: verifica kiosk v0.3

- Dopo circa dieci ore di attività, `smartpc-dashboard.service` era ancora attivo con `NRestarts=0`. Durante lo schermo nero i tasti continuano a cambiare vista secondo l'osservazione sul pannello: l'applicazione continua a funzionare. Nei log dopo l'avvio non risultano errori DP/GPU o riavvii del servizio; senza l'orario di un episodio il problema fisico del display o del collegamento DP non è ancora attribuibile con certezza.
- `smartpc-display-level.timer` e il relativo servizio Xorg sono stati disabilitati: nel kiosk EGLFS non trovavano il display X e fallivano alle 07:00. Questo elimina un'attività superflua, senza dimostrare che causasse i brevi schermi neri.
- La modalità device imposta `QT_QPA_EGLFS_HIDECURSOR=1`: il tastierino USB espone anche un'interfaccia mouse e EGLFS può mostrare un cursore software dopo il riavvio. Il servizio è stato riavviato e la variabile è presente nel processo; dopo un reboot il servizio era attivo, con `NRestarts=0` e DP-1 connesso.
- La schermata Sistema ora controlla l'attenuazione software dell'immagine, con livello manuale o automatico per orario, percentuali e orari persistenti. Menu e Sistema sono stati acquisiti dal renderer EGLFS della board a 960×640 e confrontati visivamente; dopo la correzione della sovrapposizione, l'utente ha confermato le schermate sul pannello e la variazione effettiva dell'immagine. Non essendoci backlight/DDC, la percentuale non regola la retroilluminazione fisica.
