# DeskPulse OS ⚡

<p align="center">
  <b>The Open-Source Ambient Operating System for Desk Displays & Single Board Computers.</b>
  <br>
  <i>Hardware-accelerated at a rock-solid 60 FPS directly on DRM/KMS via Qt 6 Quick / EGLFS. Zero X11 bloat. Zero Electron lag. <90 MB RAM footprint.</i>
</p>

<p align="center">
  <a href="https://github.com/GiDanis/desk-pulse/releases"><img src="https://img.shields.io/github/v/release/GiDanis/desk-pulse?color=blue&style=for-the-badge&logo=github" alt="Latest Release"></a>
  <a href="https://www.orangepi.org/"><img src="https://img.shields.io/badge/Platform-Orange%20Pi%20Zero%203W%20%7C%20SBC-FF6B35?style=for-the-badge&logo=linux&logoColor=white" alt="Platform SBC"></a>
  <a href="https://www.qt.io/"><img src="https://img.shields.io/badge/Compositor-Qt%206%20%7C%20QML%20EGLFS-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="Qt 6 QML"></a>
  <img src="https://img.shields.io/badge/Display-Hagibis%20960%C3%97640%20%40%2060Hz-00C49F?style=for-the-badge" alt="Hagibis Display">
  <img src="https://img.shields.io/badge/Graphics-Locked%2060%20FPS-8A2BE2?style=for-the-badge" alt="60 FPS">
  <img src="https://img.shields.io/badge/24h%20Soak%20Test-Passed%20(0%20Crashes)-success?style=for-the-badge" alt="24h Stability">
  <img src="https://img.shields.io/badge/RAM%20Footprint-%3C%2090%20MB-brightgreen?style=for-the-badge" alt="Low RAM">
  <a href="https://github.com/GiDanis/desk-pulse/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-informational?style=for-the-badge" alt="MIT License"></a>
</p>

<p align="center">
  <a href="#-whats-new-in-v061">What's New in v0.6.1</a> •
  <a href="#-os-workspaces">Workspaces</a> •
  <a href="#-why-a-dedicated-desk-os">Why Desk OS?</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-hardware-bom">Hardware BOM</a> •
  <a href="#-turnkey-installation">Turnkey Installation</a> •
  <a href="#-navigation--controls">Controls</a> •
  <a href="#-roadmap">Roadmap</a> •
  <a href="README.it.md">🇮🇹 Italiano</a>
</p>

---

## 🌟 What is DeskPulse OS?

**DeskPulse OS** turns an inexpensive single-board computer ($15–$25 Orange Pi Zero 3W, Raspberry Pi, or Radxa) and a mini desktop monitor (like the 3.5" Hagibis 960×640 IPS screen) into an **appliance-grade ambient desk operating system**.

Instead of treating the board as a desktop computer running a slow browser kiosk, DeskPulse OS boots directly into a native GPU-accelerated QML compositor. It operates 24/7 as your dedicated desk command center for time, weather, AI quota monitoring, live sports, and motorsport telemetry—with near-zero latency and instant tactile controls.

> ⭐ **Star this repository** if you love ambient computing, single-board computers, and distraction-free desk appliances!

---

## ✨ What's New in v0.6.1

The **v0.6.1** release brings modular architectural refinement, enhanced live sports tracking, and verified long-term hardware reliability:

- ⚙️ **Modular Settings & System Info Engine:**
  - Extracted clean `SettingsPanel.qml` and `DeviceInfo.qml` components for crisp, responsive navigation.
  - Non-blocking asynchronous Wi-Fi signal quality monitoring (%) via Linux `nmcli` without active scanning or leaking credentials.
  - Real-time hardware vitals (IP address, board CPU temperature, memory, disk usage).
- 🌙 **Advanced Notification & Quiet Hours Management:**
  - Dedicated Quiet Hours (*"Fascia silenzio"*) with automatic night muting of non-urgent banners.
  - Granular on-screen alert toggles for Weather, ChatGPT quotas, and Favourite Team goal banners.
- 🎩 **Fantacalcio Live Assistant:**
  - Real-time matchday ratings and vote sync during active Serie A matches.
  - Dedicated starters, bench, substitutes, and SV distinction.
- 🛡️ **24-Hour Continuous Operation Soak Test:**
  - Documented 24-hour continuous burn-in run on the physical Orange Pi Zero 3W (`os/diagnostics/2026-10-01-24h/`).
  - Zero memory leaks, thermal equilibrium at ~43°C, and `NRestarts=0` stability.

---

## 📸 OS Workspaces

DeskPulse OS features a seamless 6-workspace horizontal carousel, with deep 2-axis vertical navigation for each workspace:

| **Ambient Clock & Desk Shell** | **Live Weather & 3-Day Forecast** |
|:---:|:---:|
| ![Ambient Clock Shell](dashboard/preview-v03.png) | ![Weather Station](dashboard/design/v03-meteo-preview.png) |
| **Formula 1 Grand Prix Command Center** | **MotoGP World Championship Monitor** |
| ![F1 Grand Prix Weekend](dashboard/design/evidence/v06-motorsport/f1-programme.png) | ![MotoGP Championship](dashboard/design/evidence/v06-motorsport/motogp-standings.png) |
| **Football Hub & Favourite Team** | **Fantacalcio Lineups & Ratings** |
| ![Football Hub](dashboard/design/evidence/v06-favourite-team/team-summary.png) | ![Fantacalcio Ratings](dashboard/design/evidence/v06-fantacalcio/fantacalcio-home-starters.png) |

---

## ⚡ Why a Dedicated Desk OS?

Most DIY desk displays fail because they run bloated operating systems and Electron or Chromium web kiosks. This leads to slow frame rates, 90-second boot times, overheating, and fried microSD cards.

DeskPulse OS was engineered from the kernel up as an **always-on appliance**:

| Metric | ⚡ **DeskPulse OS (Native EGLFS/KMS)** | 🐢 **Web / Electron Kiosk** |
| :--- | :--- | :--- |
| **Cold Boot to Interactive UI** | **~18 seconds** (systemd straight to GPU) | 60–90+ seconds (X11/Wayland + Chrome) |
| **RAM Consumption** | **< 90 MB** (98% of RAM left free!) | 650 MB – 1.2 GB+ |
| **Frame Rate & Fluidity** | **Locked 60 FPS** (PowerVR hardware vsync) | 15–30 FPS with visible stutter |
| **Input Latency** | **Instant (direct Linux evdev kernel polling)** | Laggy JavaScript DOM event loop |
| **MicroSD Card Protection** | **Tuned 30s journal, tmpfs, zram, atomic cache** | Constant disk writes destroy SD cards |
| **24/7 Reliability** | **Verified 24h Soak Test (0 crashes, ~43°C)** | High risk of browser tab crashes |
| **Offline Resilience** | **100% resilient** (cached state, graceful fallbacks) | Error screens, infinite reload loops |
| **API Costs** | **$0 / Zero API Keys** (Open-Meteo, Jolpica, PulseLive) | Expensive subscription APIs |

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DeskPulse OS Shell                               │
│  [Clock]  •  [Weather]  •  [AI/Codex]  •  [Serie A]  •  [F1]  •  [MotoGP]   │
├─────────────────────────────────────────────────────────────────────────────┤
│               Qt 6 Quick / QML Hardware-Accelerated Compositor              │
│               60 FPS Hardware VSync via PowerVR BXM-4-64 GPU                │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Direct DRM/KMS Display Plane (EGLFS)                     │
│           (Bypasses X11 and Wayland • Instant Linux evdev input)            │
├─────────────────────────────────────────────────────────────────────────────┤
│               Hardened Linux 6.6 Kernel with DP-AltMode PLL                 │
│         MicroSD Wear Protection (zram swap, tmpfs /tmp, 30s commit)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Native Workspaces Overview

### 1. 🕒 Ambient Home & Desk Clock
High-contrast typography designed for glanceable reading from desk distance. Dynamic upcoming event card appears automatically when a future calendar event or weather alert is scheduled—no placeholder clutter.

### 2. ⛅ Hyper-Local Weather Station
Live atmospheric conditions, hourly trends, and a 3-day forecast powered by Open-Meteo. Uses an atomic local SQLite/JSON cache with offline-first resilience: if Wi-Fi disconnects, previous valid data remains visible with an explicit offline indicator.

### 3. 🤖 AI & Codex Quota Monitor
Tracks ChatGPT & OpenAI Codex plan limits, usage percentages, reset countdowns, and available credits. Syncs securely over your local network via SSH from your PC workstation **without ever exposing private tokens, passwords, or API keys**.

### 4. ⚽ Serie A Football Hub & Favourite Team HUD
Full season fixtures, live 20-team league standings, and deep match details (lineups, match statistics, goalscorers). Select your favourite club (*"Squadra del Cuore"*) for a dedicated team view with upcoming matches, squad list, and stadium info. Includes **Fantacalcio** starting XI, bench, and live editorial ratings.

### 5. 🏎️ Formula 1 Grand Prix Command Center
Full season calendar with local weekend start times, race results, and driver/constructor world championship standings powered by Jolpica. Features **real-time SignalR WebSocket live timing** via QtWebSockets, tracking positions, lap times, gaps, tyre compounds, and pit stops.

### 6. 🏍️ MotoGP Paddock Monitor
Calendar, circuit specifications, Sprint & Grand Prix classifications, and rider championship standings via PulseLive. Includes live timing lite integration for race sessions.

---

## 🛒 Hardware BOM

Build your own DeskPulse OS station for **~$40–$50**:

1. **SBC:** [Orange Pi Zero 3W](http://www.orangepi.org/html/hardWare/computerAndCar/details/Orange-Pi-Zero-3W.html) (Allwinner A733 on the tested board, PowerVR BXM-4-64 GPU). Compatible with other ARM64 SBCs.
2. **Display:** [Hagibis 3.5" IPS USB-C Monitor](https://www.hagibis.com/) (960×640 native resolution, 60 Hz, USB-C DisplayPort Alt Mode).
3. **Controller:** 9-Key USB Macro Keypad (USB ID `413d:553a`) or standard keyboard.
4. **Storage:** 16GB–32GB Class 10 / A1 MicroSD card.
5. **Cables:** Single USB-C cable for DisplayPort video + power to monitor, 5V/2A power supply for board.

---

## ⚡ Turnkey Installation

### Step 1: Flash Base OS
Install Debian 13 (Trixie) or Armbian Minimal on your microSD card.
- Use our safe interactive flasher:
  ```bash
  sudo ./scripts/flash-sd.sh /path/to/armbian.img /dev/sdX
  ```
- Or provision headless Wi-Fi & SSH keys before first boot:
  ```bash
  sudo ./scripts/configure-wifi-local.py
  ```

### Step 2: 1-Step Board Setup
Log into your Orange Pi via SSH and run:
```bash
# Clone DeskPulse OS
git clone https://github.com/GiDanis/desk-pulse.git
cd desk-pulse

# Run automated turnkey installer
sudo ./scripts/setup-board.sh
```

**`setup-board.sh` automatically:**
- Installs Qt 6 Quick, PySide6, QtWebSockets, and DRM/KMS drivers.
- Sets up system user `smartpc` with `/dev/dri/card0` and `/dev/input` permissions.
- Deploys the EGLFS KMS configuration (`/etc/smartpc/eglfs-kms.json`).
- Disables LightDM/X11 to dedicate 100% of GPU resources to the compositor.
- Enables and starts `smartpc-dashboard.service` at boot.

---

## 💻 Local Desktop / Development Mode

Preview and develop DeskPulse OS directly on your Linux workstation without hardware:

```bash
# Install dependencies
pip install PySide6 requests

# Run desktop window (960x640)
./dashboard/run.sh --desktop

# Or launch demo mode with simulated events
./dashboard/run.sh --demo
```

---

## 🎮 Navigation & Controls

DeskPulse OS is built for physical tactile feedback using a 3×3 matrix macro keypad or keyboard arrows:

```text
┌──────────────┬──────────────┬──────────────┐
│    1 Home    │     2 Up     │   3 Alerts   │
├──────────────┼──────────────┼──────────────┤
│    4 Left    │ 5 Select/Ref │   6 Right    │
├──────────────┼──────────────┼──────────────┤
│   7 Back    │    8 Down    │    9 Menu    │
└──────────────┴──────────────┴──────────────┘
```

- **Horizontal Carousel (Keys 4 / 6):** Today ↔ Weather ↔ AI/Codex ↔ Serie A ↔ F1 ↔ MotoGP.
- **Vertical Navigation (Keys 2 / 8):** Navigate deeper into views (e.g. Schedule ↕ Standings ↕ Results).
- **Action / Refresh (Key 5):** Open match/GP details, expand standings, or trigger an immediate data refresh.
- **Quick Jump (Key 7):** Instant return to the primary Home Clock from any depth.
- **System Menu (Key 9):**
  - **Notifications:** Quiet hours schedule and category-level alert muting.
  - **Appearance:** Theme (Auto / Day / Night), Brightness (Manual & Circadian schedules).
  - **Module Visibility:** Toggle workspaces on or off (persisted across reboots).
  - **Device Info:** Wi-Fi signal quality (%), CPU temperature, IP, RAM and storage vitals.

---

## 🔧 Kernel Patch: USB-C DP Alt Mode

The Hagibis 3.5" monitor requires USB-C DisplayPort Alternate Mode. On the tested Allwinner A733 (sun60iw2), the stock vendor kernel has an unasserted CMN PLL1 clock issue that causes DP link training timeouts.

DeskPulse OS includes the verified kernel fix in [`os/kernel-patches/`](os/kernel-patches/):
- `0001-sun60iw2-enable-cmn-pll-for-dp-altmode.patch`: Corrects PHY initialization in `combo0_configure_usb_dp()`.
- Trains the DisplayPort link at 5.4 Gbit/s for clean 960×640 @ 60 Hz video over a single USB-C cable.

---

## 🗺️ Roadmap

- [x] **v0.4:** Direct EGLFS/KMS compositor, dynamic Home, and Open-Meteo weather.
- [x] **v0.5:** Persistent event engine, Civil Protection alerts, and unread notification badges.
- [x] **v0.6:** Serie A Football Hub, Favourite Team HUD, Fantacalcio, F1 & MotoGP with SignalR live timing.
- [x] **v0.6.1:** **Modular Settings Engine, Live Wi-Fi Monitoring, Fantacalcio Live & 24h Soak Verification.**

Runtime version: **v0.6.6 Theme Engine**, migrated from the v0.6.5 baseline. See the [release MasterPlan](dashboard/design/release-masterplan.md), updated October 2, 2026, for the version/manifest reconciliation, completed checks and remaining live validation.

- [x] **v0.6.6:** **Theme Engine** — Base/Functional, replaceable layouts and motion, editor, personal packs and persistent scenes. [Usage/development](dashboard/design/theme-engine-implementation-guide.md), [verification and limits](dashboard/design/v066-migration-report.md).
- [ ] **v0.7:** **Smart Home** — Direct Tuya cloud integration; analysis/API probes exist, production polling/UI are pending.
- [ ] **v0.8:** **Local Network Overview** — Devices and information collected by the board, with optional router data; no agents on client computers.
- [ ] **v0.8.1 (optional):** Verified router metadata and additional Hardware/Cyberdeck profiles.
- [ ] **v0.9:** Animated companion and Cozy profile.
- [ ] **v0.10:** Companion memory and validated AI scene planning.
- [ ] **v1.0:** Integrated reliability, installation, upgrades and recovery.

---

## 🤝 Contributing

We welcome contributions! Whether you want to add new sports, integrate home automation protocols, or port DeskPulse OS to other SBC platforms:
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/CoolWorkspace`).
3. Commit your Changes (`git commit -m 'Add CoolWorkspace'`).
4. Push to the Branch (`git push origin feature/CoolWorkspace`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.

---

<p align="center">
  Crafted with ❤️ by <a href="https://github.com/GiDanis">GiDanis</a> for makers and ambient computing enthusiasts.
</p>
