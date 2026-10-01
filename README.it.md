# DeskPulse OS ⚡ (Italiano)

<p align="center">
  <b>Il Sistema Operativo Ambientale Open-Source per Display da Scrivania e Single Board Computer.</b>
  <br>
  <i>Accelerato su GPU a 60 FPS stabili direttamente su DRM/KMS tramite Qt 6 Quick / EGLFS. Zero overhead X11. Zero lag Electron. Solo <90 MB di RAM.</i>
</p>

---

## 🌟 Che cos'è DeskPulse OS?

**DeskPulse OS** trasforma un economico single-board computer da 15–25 € (Orange Pi Zero 3W, Raspberry Pi, Radxa) abbinato a un mini monitor da scrivania (come l'Hagibis 3.5" IPS USB-C 960×640) in un vero e proprio **sistema operativo appliance sempre attivo**.

Invece di far girare un pesante ambiente desktop con browser web (kiosk Chromium), DeskPulse OS esegue direttamente a livello kernel un compositore grafico QML su GPU. Funziona 24/7 come centro di controllo compatto per ora, meteo, monitoraggio crediti AI/ChatGPT, Serie A con Fantacalcio, telemetria Formula 1 e MotoGP—con risposta istantanea e comandi fisici tattili.

---

## 📸 Gli Spazi di Lavoro (v0.6)

Un carosello a 6 spazi di lavoro fluidi, navigabili in orizzontale e verticale:

| **Orologio Ambient & Shell di Sistema** | **Meteo Live & Previsioni a 3 Giorni** |
|:---:|:---:|
| ![Ambient Clock Shell](dashboard/preview-v03.png) | ![Weather Station](dashboard/design/v03-meteo-preview.png) |
| **Command Center Formula 1** | **Monitor Campionato MotoGP** |
| ![F1 Grand Prix Weekend](dashboard/design/evidence/v06-motorsport/f1-programme.png) | ![MotoGP Championship](dashboard/design/evidence/v06-motorsport/motogp-standings.png) |
| **Arena Serie A & Squadra del Cuore** | **Assistente Fantacalcio con Voti Live** |
| ![Football Hub](dashboard/design/evidence/v06-favourite-team/team-summary.png) | ![Fantacalcio Ratings](dashboard/design/evidence/v06-fantacalcio/fantacalcio-home-starters.png) |

---

## ⚡ Perché un OS Dedicato da Scrivania?

| Parametro | ⚡ **DeskPulse OS (Nativo EGLFS/KMS)** | 🐢 **Kiosk Web / Electron** |
| :--- | :--- | :--- |
| **Avvio a Freddo** | **~18 secondi** (da systemd al display) | 60–90+ secondi (desktop + browser) |
| **Consumo RAM** | **< 90 MB** (98% della RAM libera!) | 650 MB – 1.2 GB+ |
| **Fluidità / Framerate** | **60 FPS stabili** (vsync GPU PowerVR) | 15–30 FPS con scatti visibili |
| **Latenza di Input** | **Istantanea (polling kernel Linux evdev)** | Dipendente dall'event loop di JS |
| **Protezione MicroSD** | **Commit a 30s, tmpfs, zram, zero scritture inutili** | Scritture disco elevate che usurano la SD |
| **Resilienza Offline** | **100% resiliente** (cache atomica persistente) | Schermate bianche o tentativi a vuoto |
| **Costi API** | **€0 / Zero API key** (Open-Meteo, Jolpica, PulseLive) | API a pagamento o quote restrittive |

---

## 🏗️ Architettura di Sistema

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DeskPulse OS Shell                               │
│  [Orologio]  •  [Meteo]  •  [AI/Codex]  •  [Serie A]  •  [F1]  •  [MotoGP]  │
├─────────────────────────────────────────────────────────────────────────────┤
│               Compositore Accelerato su GPU Qt 6 Quick / QML                │
│                60 FPS Hardware VSync via GPU PowerVR BXM-4-64               │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Piano Grafico Diretto DRM/KMS (EGLFS)                    │
│            (Bypassa X11 e Wayland • Gestione diretta input evdev)           │
├─────────────────────────────────────────────────────────────────────────────┤
│             Kernel Linux 6.6 con Patch Hardware DP-AltMode PLL              │
│       Protezione MicroSD (swap zram, tmpfs in /tmp, commit fs a 30s)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 I Moduli di DeskPulse OS (v0.6)

1. **🕒 Home & Orologio Ambient:** Tipografia ad alto contrasto per visione da scrivania. Mostra automaticamente la card dell'evento o allerta meteo futura solo quando presente.
2. **⛅ Stazione Meteo Live:** Dati orari e previsione a 3 giorni via Open-Meteo con cache atomica locale offline.
3. **🤖 Monitor Quote AI & Codex:** Percentuale finestre ChatGPT, orari di ripristino e saldo crediti sincronizzati in sicurezza via SSH dal PC locale.
4. **⚽ Hub Serie A & Squadra del Cuore:** Calendario completo, classifica a 20 squadre, formazioni ufficiali, statistiche e modulo **Fantacalcio** con titolari, panchinari e pagelle/voti della Redazione.
5. **🏎️ Command Center Formula 1:** Calendario GP con fusi italiani, classifiche Piloti e Costruttori (Jolpica), dettagli stint/gomme (OpenF1) e **live timing SignalR WebSocket** in tempo reale via QtWebSockets.
6. **🏍️ Paddock MotoGP:** Calendario, caratteristiche circuiti, classifiche Sprint e Gara e classifica mondiale piloti (PulseLive).

---

## 🛒 Hardware Necessario (~35–45 €)

1. **SBC:** Orange Pi Zero 3W (Allwinner H618, 1GB–4GB RAM, GPU PowerVR). Compatibile con altre board Linux ARM64.
2. **Display:** Monitor USB-C Hagibis 3.5" IPS (960×640 a 60 Hz con DisplayPort Alt Mode).
3. **Controller:** Mini tastierino USB 9 tasti (ID `413d:553a`) o normale tastiera.
4. **Memoria:** Scheda MicroSD da 16GB–32GB Classe 10 / A1.
5. **Cavi:** Cavo USB-C con supporto video DP + alimentazione per lo schermo, alimentatore 5V/2A per la scheda.

---

## ⚡ Installazione Chiavi in Mano

### 1. Sistema Operativo Base
Installa Debian 13 o Armbian Minimal sulla scheda SD:
```bash
sudo ./scripts/flash-sd.sh /percorso/immagine.img /dev/sdX
```
Configura Wi-Fi headless e chiavi SSH prima dell'avvio:
```bash
sudo ./scripts/configure-wifi-local.py
```

### 2. Setup Automatico sulla Scheda
Accedi via SSH alla tua Orange Pi ed esegui:
```bash
git clone https://github.com/GiDanis/desk-pulse.git
cd desk-pulse
sudo ./scripts/setup-board.sh
```

Lo script installa tutte le librerie Qt6, PySide6, QtWebSockets, configura l'utente `smartpc` e abilita l'avvio automatico del servizio al boot.

---

## 🎮 Comandi & Navigazione Tastierino

Progettato per mini tastierino a matrice 3×3 o frecce della tastiera:

```text
┌──────────────┬──────────────┬──────────────┐
│  1 Indietro  │     2 Su     │   3 Avvisi   │
├──────────────┼──────────────┼──────────────┤
│  4 Sinistra  │  5 Seleziona │   6 Destra   │
├──────────────┼──────────────┼──────────────┤
│    7 Home    │    8 Giù     │    9 Menu    │
└──────────────┴──────────────┴──────────────┘
```

- **Carosello Orizzontale (Tasti 4 / 6):** Oggi ↔ Meteo ↔ AI/Codex ↔ Serie A ↔ F1 ↔ MotoGP.
- **Navigazione Verticale (Tasti 2 / 8):** Viste di dettaglio (es. Calendario ↕ Classifica ↕ Risultati).
- **Azione / Aggiorna (Tasto 5):** Apre i dettagli dell'incontro/GP o forza un aggiornamento dati.
- **Tasto Rapido Home (Tasto 7):** Torna istantaneamente all'orologio principale da qualsiasi profondità.
- **Menu di Sistema (Tasto 9):** Regolazione aspetto (temi, orari luminosità automatica), moduli visibili e diagnostica GPU/CPU.

---

## 🗺️ Roadmap Prossime Versioni

- [x] **v0.4:** Compositore diretto EGLFS/KMS, Home dinamica, Meteo Open-Meteo.
- [x] **v0.5:** Motore eventi persistente, allerte Protezione Civile, badge notifiche.
- [x] **v0.6:** Hub Serie A, Squadra del Cuore, Fantacalcio, F1 & MotoGP con telemetria live SignalR.
- [ ] **v0.7:** **Smart Home Dashboard** — Integrazione nativa locale Tuya & Home Assistant.
- [ ] **v0.8:** **Spotify Connect & Media Player** — Copertina album e controlli musicali fisici.
- [ ] **v0.9:** **PC Hardware Telemetry HUD** — Temperature CPU/GPU del PC da lavoro inviate via LAN.

---

## 📄 Licenza

Distribuito sotto Licenza MIT. Consulta il file [LICENSE](LICENSE) per ulteriori dettagli.
