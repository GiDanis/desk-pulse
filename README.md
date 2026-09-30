# DeskPulse ⚡

<p align="center">
  <b>Turnkey, always-on ambient desk companion & smart dashboard for Orange Pi Zero 3W and Hagibis 960×640 USB-C display.</b>
  <br>
  <i>Native Qt 6 Quick / QML running directly on DRM/KMS via EGLFS at rock-solid 60 FPS. Zero X11 bloat. Zero Electron lag.</i>
</p>

<p align="center">
  <a href="https://github.com/GiDanis/desk-pulse/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT License"></a>
  <a href="https://www.orangepi.org/"><img src="https://img.shields.io/badge/Board-Orange%20Pi%20Zero%203W-FF6B35?style=for-the-badge&logo=linux&logoColor=white" alt="Orange Pi Zero 3W"></a>
  <a href="https://www.qt.io/"><img src="https://img.shields.io/badge/UI-Qt%206%20%7C%20QML-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="Qt 6 QML"></a>
  <img src="https://img.shields.io/badge/Display-Hagibis%20960%C3%97640%20%40%2060Hz-00C49F?style=for-the-badge" alt="Hagibis Display">
  <img src="https://img.shields.io/badge/Performance-Locked%2060%20FPS-8A2BE2?style=for-the-badge" alt="60 FPS">
  <img src="https://img.shields.io/badge/RAM%20Usage-%3C%2090%20MB-brightgreen?style=for-the-badge" alt="Low RAM">
</p>

<p align="center">
  <a href="#-quick-tour">Quick Tour</a> •
  <a href="#-why-deskpulse">Why DeskPulse?</a> •
  <a href="#-hardware-bill-of-materials">Hardware BOM</a> •
  <a href="#-turnkey-installation">Turnkey Installation</a> •
  <a href="#-navigation--controls">Controls</a> •
  <a href="#-pc-companion--ai-sync">AI & Codex Sync</a> •
  <a href="README.it.md">🇮🇹 Italiano</a>
</p>

---

## 📸 Quick Tour

| **Dynamic Home (Clock & Next Event)** | **Live Weather & 3-Day Forecast** |
|:---:|:---:|
| ![Home Screen](dashboard/preview-v03.png) | ![Weather Screen](dashboard/design/v03-meteo-preview.png) |
| **System Quick Menu** | **Display, Night Dimming & Module Visibility** |
| ![Menu Overlay](dashboard/design/v03-system-menu-board.png) | ![Settings Screen](dashboard/design/v03-system-settings-board.png) |

---

## ⚡ Why DeskPulse?

Most DIY smart displays rely on heavy Chromium/Electron web apps or bulky Android ROMs. On small single-board computers (SBCs), this leads to high temperatures, sluggish frame rates, long boot times, and rapid microSD card wear.

DeskPulse is engineered specifically for **embedded Linux appliance reliability**:

| Metric | ⚡ **DeskPulse (Native EGLFS/KMS)** | 🐢 **Web / Electron Kiosk** |
| :--- | :--- | :--- |
| **Cold Boot to UI** | **~18 seconds** (systemd direct to GPU) | 60–90+ seconds (X11/Wayland + Browser) |
| **RAM Footprint** | **< 90 MB** | 650 MB – 1.2 GB+ |
| **Frame Rate & Fluidity** | **Rock-solid 60 FPS** (PowerVR GPU hardware vsync) | 15–30 FPS with UI stutters |
| **Input Latency** | **Instant (direct evdev kernel polling)** | Laggy JS event loop |
| **MicroSD Card Wear** | **Minimal** (tuned fstab commits, tmpfs, zram, reduced log churn) | High disk cache & browser writes |
| **Offline Resilience** | **Full** (atomic cache, fallback states, zero freeze) | White screens / reload loops |

---

## 🛒 Hardware Bill of Materials

You can assemble this complete desktop setup for **under $40–$50**:

1. **SBC:** [Orange Pi Zero 3W](http://www.orangepi.org/html/hardWare/computerAndCar/details/Orange-Pi-Zero-3W.html) (Allwinner H618 / sun60iw2, 1GB–4GB RAM, PowerVR BXM-4-64 GPU).
2. **Display:** [Hagibis 3.5" IPS USB-C Monitor](https://www.hagibis.com/) (960×640 native resolution, 60 Hz, DisplayPort Alt Mode over USB-C).
3. **Controller:** 9-Key USB Macro Keypad (USB ID `413d:553a` or any standard keyboard).
4. **Storage:** 16GB–32GB Class 10 / A1 MicroSD Card.
5. **Connectivity:** Single USB-C cable for DisplayPort video + power to monitor, 5V/2A power supply for board.

---

## 🚀 Turnkey Installation

### Step 1: Base OS Setup
DeskPulse runs on Debian 13 (Trixie) or Armbian Minimal.
- Optional: Use our safe flasher from your PC:
  ```bash
  sudo ./scripts/flash-sd.sh /path/to/armbian.img /dev/sdX
  ```
- Or provision headless Wi-Fi & SSH keys automatically before first boot:
  ```bash
  sudo ./scripts/configure-wifi-local.py
  ```

### Step 2: 1-Step Board Installer
Once connected to your Orange Pi over SSH:
```bash
# Clone the repository
git clone https://github.com/GiDanis/desk-pulse.git
cd desk-pulse

# Run the automated turnkey installer
sudo ./scripts/setup-board.sh
```

**What `setup-board.sh` does automatically:**
- Installs Qt 6 Quick, PySide6, KMS/DRM drivers, and dependencies.
- Configures dedicated system user `smartpc` with direct `/dev/dri/card0` and `/dev/input` permissions.
- Installs `/etc/smartpc/eglfs-kms.json` for direct hardware rendering.
- Deploys and enables `smartpc-dashboard.service` systemd kiosk unit.
- Disables unused display managers (LightDM/X11) to free memory and GPU resources.

---

## 💻 Local Development / PC Test Mode

You can preview and test DeskPulse directly on your desktop PC:

```bash
# Install dependencies
pip install PySide6 requests

# Launch desktop preview (960x640 window)
./dashboard/run.sh --desktop

# Or launch with simulated event demo
./dashboard/run.sh --demo
```

---

## 🎮 Navigation & Controls

DeskPulse features a predictable 2-axis navigation system designed for a 3×3 physical keypad or standard keyboard arrows:

```text
┌──────────────┬──────────────┬──────────────┐
│    1 Home    │     2 Up     │   3 Alerts   │
├──────────────┼──────────────┼──────────────┤
│    4 Left    │   5 OK/Enter │   6 Right    │
├──────────────┼──────────────┼──────────────┤
│    7 Back    │    8 Down    │    9 Menu    │
└──────────────┴──────────────┴──────────────┘
```

- **Horizontal Carousel (Keys 4 / 6):** Today (Home) ↔ Live Weather ↔ ChatGPT / Codex AI Monitor.
- **Vertical Navigation (Keys 2 / 8):** Deep dive into module views:
  - *Today:* Full Clock & Date ↕ Day Overview.
  - *Weather:* Current Conditions ↕ 3-Day Forecast.
- **Menu (Key 9):**
  - **Appearance:** Theme (Auto / Day / Night), Brightness (Manual & Auto Day/Night schedules).
  - **Module Visibility:** Toggle modules on/off (state preserved across reboots).
  - **Diagnostics:** GPU framerate, temperature, and system metrics.

---

## 🛰️ PC Companion & AI / Codex Sync

DeskPulse includes an ambient AI & Codex quota tracker. It queries the local Codex App Server on your workstation and syncs usage metrics to the board via SSH **without exposing API keys, tokens, or personal identifiers**:

```text
Workstation (PC)                          Orange Pi (DeskPulse)
┌───────────────────────┐   SSH Sync     ┌──────────────────────────────────┐
│ Codex App Server      │  ───────────►  │ /var/cache/smartpc-dashboard/    │
│ dashboard/            │ (JSON payload) │   account-chatgpt.json           │
│   account_sync.py     │                │   (Read by Qt/QML UI)            │
└───────────────────────┘                └──────────────────────────────────┘
```

### Automatic Workstation Sync:
Install the user systemd timer on your PC to sync every 10 minutes:
```bash
cp dashboard/systemd/smartpc-account-sync.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now smartpc-account-sync.timer
```

---

## 🔧 Kernel Hardware Fix: USB-C DP Alt Mode

The Hagibis 3.5" monitor requires USB-C DisplayPort Alternate Mode. On the Allwinner H618 (sun60iw2), the stock vendor kernel has an unasserted CMN PLL1 clock issue that causes DP link training timeouts.

DeskPulse includes the exact tested kernel fix in [`os/kernel-patches/`](os/kernel-patches/):
- `0001-sun60iw2-enable-cmn-pll-for-dp-altmode.patch`: Corrects PHY initialization in `combo0_configure_usb_dp()`.
- Trains the DisplayPort link at 5.4 Gbit/s for flawless 960×640 @ 60 Hz output.

---

## 📂 Repository Structure

```text
desk-pulse/
├── dashboard/               # Qt 6 Quick / QML app & Python backend
│   ├── app.py               # Main application entrypoint
│   ├── Main.qml             # Root UI scene & view coordinator
│   ├── state.py             # Global state machine & property bridge
│   ├── weather.py           # Resilient Open-Meteo provider with atomic cache
│   ├── account.py           # AI & ChatGPT module state handler
│   ├── account_sync.py      # Secure PC-to-board sync utility
│   ├── keypad.py            # Linux evdev USB keypad driver
│   ├── design/              # UI mockups, previews, and UX studies
│   └── systemd/             # Workstation background sync timer & service
├── os/                      # Operating system recipes & kernel patches
│   ├── kernel-patches/      # DP Alt Mode PLL fix for kernel 6.6.98
│   ├── system/              # Drop-in systemd units, eglfs-kms config & display schedule
│   ├── diagnostics/         # GPU benchmarks, APT plans, and sanity scripts
│   └── board-audit-*.md     # Complete reliability audit & microSD wear mitigation
└── scripts/                 # Provisioning & maintenance automation
    ├── setup-board.sh       # ⚡ 1-step turnkey board installer
    ├── flash-sd.sh          # Safe interactive microSD card flasher
    ├── check-sd.sh          # MicroSD filesystem repair & integrity check
    └── prepare-headless.py  # Headless Wi-Fi & SSH key injector
```

---

## 🤝 Contributing

Contributions are welcome! Whether it is adding new modules (Spotify, Home Assistant, Crypto, System Hardware HUD), improving themes, or porting to other SBCs (Raspberry Pi, Radxa):
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingModule`).
3. Commit your Changes (`git commit -m 'Add AmazingModule'`).
4. Push to the Branch (`git push origin feature/AmazingModule`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.

---

<p align="center">
  Crafted with ❤️ by <a href="https://github.com/GiDanis">GiDanis</a> for makers and ambient computing enthusiasts.
</p>
