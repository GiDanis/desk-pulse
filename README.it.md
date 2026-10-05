# DeskPulse OS ⚡ (Italiano)

<p align="center">
  <b>Il Sistema Operativo Ambientale Open-Source per Display da Scrivania e Single Board Computer.</b>
  <br>
  <i>Accelerato su GPU a 60 FPS stabili direttamente su DRM/KMS tramite Qt 6 Quick / EGLFS. Zero overhead X11. Zero lag Electron. Solo <90 MB di RAM.</i>
</p>

---

## 🎨 Novità della Versione v0.6.6: Theme & Motion Engine

Il rilascio **v0.6.6** introduce un rivoluzionario **Motore di Temi, Animazioni e Presentazioni** che disaccoppia completamente lo stile visivo e i layout dai dati applicativi e dai servizi Linux sottostanti:

- 🎭 **Token Semantici di Design & Palette Adattive:**
  - Contratto semantico completo per colori, bordi, tipografie e raggi di curvatura—zero valori esadecimali hardcoded nelle viste.
  - Cambio automatico Giorno/Notte e modalità notturne dedicate ad alto contrasto (es. Notte Rossa per camere oscurate).
  - Include due temi di produzione verificati: **Neo-Retro Base** e **Braun Functional**.
- 🎬 **Motore di Movimento Dichiarativo:**
  - Ricette di transizione intercambiabili (`Fade`, `Slide`, `Cut`, `SceneMove`, `Value`) con garanzia di frame-pacing.
  - Politica di riduzione del movimento ad attivazione automatica o su preferenza utente.
- 🧩 **Layout di Presentazione Modulari:**
  - Layout grafici svincolati dai provider dati; le superfici possono cambiare aspetto dinamicamente senza alterare la logica.
  - Sei superfici di notifica estensibili (Small Rail, Large Split, Urgent, Inbox, Detail, Badge).
- 🛠️ **SDK di Creazione Temi Offline (`smartpc-theme` CLI):**
  - Tool da riga di comando per creare, validare, fare anteprime e impacchettare bundle di temi personali (`init`, `validate`, `preview`, `pack`, `inspect`, `export`).
  - Validazione schema-1 rigorosa eseguibile senza dipendenze grafiche.
- ⚡ **Cambio Tema a Caldo Senza Riavvio:**
  - Cambio di profilo istantaneo in `Menu → Impostazioni → Aspetto` preservando lo stato dei moduli e la ricezione dati.
- 🛡️ **Soak Test 24 Ore Documentato:**
  - Collaudo di funzionamento continuo di 24 ore sulla Orange Pi fisica (`os/diagnostics/2026-10-01-24h/`): zero memory leak e stabilità `NRestarts=0`.

---

## 📸 Gli Spazi di Lavoro

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
| **Affidabilità 24/7** | **Soak Test 24h Verificato (0 crash, ~43°C)** | Rischio elevato di freeze del browser |
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

## 🛒 Hardware Necessario (~35–45 €)

1. **SBC:** Orange Pi Zero 3W (Allwinner A733 sulla scheda collaudata, GPU PowerVR BXM-4-64). Compatibile con altre board Linux ARM64.
2. **Display:** Monitor USB-C Hagibis 3.5" IPS (960×640 a 60 Hz con DisplayPort Alt Mode).
3. **Controller:** Mini tastierino USB 9 tasti (ID `413d:553a`) o normale tastiera.
4. **Memoria:** Scheda MicroSD da 16GB–32GB Classe 10 / A1.
5. **Cavi:** Cavo USB-C con supporto video DP + alimentazione per lo schermo, alimentatore 5V/2A per la scheda.

---

## ⚡ Installazione Chiavi in Mano

```bash
# Accedi via SSH alla tua board
git clone https://github.com/GiDanis/desk-pulse.git
cd desk-pulse
sudo ./scripts/setup-board.sh
```

Lo script configura automaticamente pacchetti Qt6, permessi utente `smartpc`, file di configurazione EGLFS e servizio systemd con avvio immediato a 60 FPS.

---

## 🎮 Comandi & Navigazione Tastierino

```text
┌──────────────┬──────────────┬──────────────┐
│   1 Home    │     2 Su     │   3 Avvisi   │
├──────────────┼──────────────┼──────────────┤
│  4 Sinistra  │  5 Seleziona │   6 Destra   │
├──────────────┼──────────────┼──────────────┤
│ 7 Indietro  │    8 Giù     │    9 Menu    │
└──────────────┴──────────────┴──────────────┘
```

- **Carosello Orizzontale (Tasti 4 / 6):** Oggi ↔ Meteo ↔ AI/Codex ↔ Serie A ↔ F1 ↔ MotoGP.
- **Navigazione Verticale (Tasti 2 / 8):** Viste di dettaglio (es. Calendario ↕ Classifica ↕ Risultati).
- **Azione / Aggiorna (Tasto 5):** Apre i dettagli dell'incontro/GP o forza un aggiornamento dati.
- **Tasto Rapido Home (Tasto 7):** Torna istantaneamente all'orologio principale da qualsiasi profondità.
- **Menu di Sistema (Tasto 9):** Regolazione aspetto (temi, luminosità), notifiche (fascia silenzio), moduli visibili e telemetria hardware in tempo reale.

---

## 🗺️ Roadmap

- [x] **v0.4:** Compositore diretto EGLFS/KMS, Home dinamica, Meteo Open-Meteo.
- [x] **v0.5:** Motore eventi persistente, allerte Protezione Civile, badge notifiche.
- [x] **v0.6:** Hub Serie A, Squadra del Cuore, Fantacalcio, F1 & MotoGP con telemetria live SignalR.
- [x] **v0.6.1:** **Architettura Impostazioni Modulare, Wi-Fi Live, Fantacalcio Live & Verifica 24h.**

Versione runtime: **v0.6.6 Theme Engine**, migrata dalla baseline v0.6.5. Il [MasterPlan dei rilasci](dashboard/design/release-masterplan.md), aggiornato al 2 ottobre 2026, distingue allineamento versione/manifest, verifiche completate e collaudi live rimasti.

- [x] **v0.6.6:** **Theme Engine** — Base/Functional, layout e animazioni sostituibili, editor, pacchetti personali e scene persistenti. [Uso e sviluppo](dashboard/design/theme-engine-implementation-guide.md), [collaudo e limiti](dashboard/design/v066-migration-report.md).
- [ ] **v0.7:** **Casa / Smart Life** — Cloud Tuya diretto; analisi/probe API disponibili, polling/UI di produzione da realizzare.
- [ ] **v0.8:** **Rete locale** — Panoramica dei dispositivi e informazioni osservabili dalla board, con eventuali dati router; nessun agent sui computer.
- [ ] **v0.8.1 (facoltativa):** Metadati router verificati e profili Hardware/Cyberdeck aggiuntivi.
- [ ] **v0.9:** Compagno animato e profilo Cozy.
- [ ] **v0.10:** Memoria del compagno e scene AI validate.
- [ ] **v1.0:** Stabilità integrata, installazione, aggiornamento e recupero.

---

## 📄 Licenza

Distribuito sotto Licenza MIT. Consulta il file [LICENSE](LICENSE) per ulteriori dettagli.
