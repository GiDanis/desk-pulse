# DeskPulse OS ⚡ (Italiano)

<p align="center">
  <b>Il Sistema Operativo Ambientale Open-Source per Display da Scrivania e Single Board Computer.</b>
  <br>
  <i>Rendering Qt Quick accelerato su GPU tramite EGLFS e DRM/KMS. Prestazioni e risorse attuali sono documentate nei rapporti di consegna sulla board.</i>
</p>

---

## 🌐 Novità della Versione v0.8.0: Rete Locale & Case 3D per Scrivania

Il rilascio **v0.8.0** introduce il modulo **Rete Locale (LAN Hub)** per router Freebox / Iliadbox OS, l'estensione del **Theme Engine 2.3** (53 superfici) e il pacchetto completo di **Case 3D Stampabili per Scrivania**:

- 🌐 **Integrazione Nativа Rete Locale & Router (LAN Hub):**
  - **Zero Agent sui Computer**: Client asincrono diretto integrato nel processo per leggere l'inventario del router Freebox/Iliadbox senza installare software o demoni sui PC della rete.
  - **Discovery Completa degli Host**: Riconoscimento di tutti i dispositivi attivi e storici con indirizzi IPv4/IPv6, produttore hardware dal MAC, frequenze Wi-Fi e porte switch Ethernet.
  - **4 Tessere Dispositivi Preferiti**: Stato immediato per workstation, NAS, stampante o server in visuale Base (tessere) o Functional (righe).
  - **Filtri Multi-Categoria**: Selezione rapida tra *Tutti*, *Raggiungibili*, *Preferiti* e *Dati precedenti*.
  - **Database SQLite Transazionale**: Archivio privato persistente con conservazione a 30 giorni e limite di sicurezza di 256 host; la cache sopravvive ai riavvii di rete.
  - **Operatività in Sola Lettura**: Non altera firewall, DHCP o impostazioni del router.
- 🎨 **Theme Engine 2.3 (53 Superfici & 18 Contesti):**
  - 4 nuove superfici di presentazione (`network.overview`, `network.devices`, `network.detail`, `settings.network`).
  - Fallback additivo elegante allo stile Base per i bundle di terze parti (piena compatibilità con Apple Calm 1.2.0).
  - Tolleranza all'avvio a freddo estesa a 8 secondi per il primo caricamento.
- 🖨️ **Case 3D per Scrivania Retro-Futuristico Stampabile:**
  - Pacchetto CAD 3D completo fornito direttamente nel repository (`SmartPC_3D_Print_Package/` e [`cad_model/`](cad_model/)) con sorgenti OpenSCAD e modelli STL di precisione.
  - **3 Stili Iconici**:
    - **Classic**: Ispirato ai computer compatti desktop anni '80/'90.
    - **Quadra**: Design architettonico moderno e minimale.
    - **Cyber**: Taglio cyberpunk tattico con prese d'aria laterali e feritoie di raffreddamento.
  - Modellato su misura per Orange Pi Zero 3W e display USB-C Hagibis 3.5", con alloggiamento per dissipatori 38×38/40×40mm e coperchio posteriore a scatto.
- 🛡️ **Stabilità Hardware & Appliance Verificata:**
  - Collaudato sulla Orange Pi Zero 3W fisica con discovery LAN reale, zero crash e persistenza systemd `NRestarts=0`.

---

**Candidata installata: 0.8.7-rc.3 · 10 ottobre 2026.** Sport dà priorità alle partite in corso con dati freschi e al timing della sessione. Le qualifiche concluse restano visibili con gli ultimi tempi; 5 apre l’evento mostrato. Apple Calm 1.6.2 e preferenze conservati, tre temi verificati su EGLFS. [Fix Sport e limiti di verifica](dashboard/design/v087-sport-live-fix-report.md).

**Precedente candidata 0.8.7-rc.2 · 10 ottobre 2026.** Apple Calm 1.6.2 attivo, Theme API 2.7 invariata. Riaperture con cache limitata, dati mirati e contesti inizializzati una volta; palette, font, icone e informazioni conservati, dissolvenze brevi da 100 ms. Nel confronto software EGLFS con motion off: Serie A mediana 466 → 138 ms, Casa 153 → 71 ms, Rete 249 → 111 ms. Tre temi, 515 file, backup, 40 preferenze e personalizzazioni verificati dopo reboot reale. Primi ingressi, Impostazioni e feedback fisico conservano gate residui. [Consegna e limiti](dashboard/design/v087-opening-implementation-report.md) · [MasterPlan](dashboard/design/release-masterplan.md).

## 📸 Gli Spazi di Lavoro

Un carosello a 6 spazi di lavoro fluidi, navigabili in orizzontale e verticale:

| **Orologio Ambient & Shell di Sistema** | **Meteo Live & Previsioni a 3 Giorni** |
|:---:|:---:|
| ![Ambient Clock Shell](dashboard/preview-v03.png) | ![Weather Station](dashboard/design/v03-meteo-preview.png) |
| **Command Center Formula 1** | **Monitor Campionato MotoGP** |
| ![F1 Grand Prix Weekend](dashboard/design/evidence/v06-motorsport/f1-programme.png) | ![MotoGP Championship](dashboard/design/evidence/v06-motorsport/motogp-standings.png) |
| **Arena Serie A & Squadra del Cuore** | **Assistente Fantacalcio con Voti Live** |
| ![Football Hub](dashboard/design/evidence/v06-favourite-team/team-summary.png) | ![Fantacalcio Ratings](dashboard/design/evidence/v06-fantacalcio/fantacalcio-home-starters.png) |
| **Dashboard Casa (Base)** | **Dispositivi & Telemetria Casa (Functional)** |
| ![Casa Overview](theme-projects/apple-calm/evidence/optimization-board-eglfs-day/casa.overview--default.png) | ![Casa Devices](theme-projects/apple-calm/evidence/optimization-board-eglfs-day/casa.devices--default.png) |

---

## 🖨️ Case 3D Stampabile per Scrivania

DeskPulse è una vera appliance completa di hardware e chassis! Il repository include i modelli CAD (`SmartPC_3D_Print_Package/` e [`cad_model/`](cad_model/)) realizzati in OpenSCAD:

| **Stile Classic Retro** | **Stile Deluxe (Feritoie di Raffreddamento)** | **Vista Esplosa & Coperchio Inclinato 6°** |
|:---:|:---:|:---:|
| ![Classic Dock](cad_model/preview_classic_dock.png) | ![Deluxe Dock](cad_model/preview_deluxe_dock.png) | ![Vista Esplosa](cad_model/preview_exploded.png) |

- **Incastro Perfetto**: Creato per Orange Pi Zero 3W e schermo Hagibis 3.5" USB-C con guide interne per i cavi.
- **Raffreddamento a Camino**: Compatibile con dissipatori in alluminio fino a 40×40mm.
- **Pronto da Stampare**: File STL verificati per stampanti FDM standard con ugello da 0.4mm in PLA, PETG o ABS senza supporti sul corpo principale. Leggi [`SmartPC_3D_Print_Package/ISTRUZIONI_DI_STAMPA.txt`](SmartPC_3D_Print_Package/ISTRUZIONI_DI_STAMPA.txt).

---

## ⚡ Perché un OS Dedicato da Scrivania?

| Parametro | ⚡ **DeskPulse OS (Nativo EGLFS/KMS)** | 🐢 **Kiosk Web / Electron** |
| :--- | :--- | :--- |
| **Avvio a Freddo** | **~18 secondi** (da systemd al display) | 60–90+ secondi (desktop + browser) |
| **Consumo RAM** | Dipende da viste, renderer in cache e provider; vedere le prove attuali | Dipende dall’applicazione |
| **Fluidità / Framerate** | OpenGL hardware su display a 60 Hz; tempi dei frame misurati separatamente | Dipende dall’applicazione |
| **Latenza di Input** | **Istantanea (polling kernel Linux evdev)** | Dipendente dall'event loop di JS |
| **Protezione MicroSD** | **Commit a 30s, tmpfs, zram, zero scritture inutili** | Scritture disco elevate che usurano la SD |
| **Affidabilità 24/7** | **Soak Test 24h Verificato (0 crash, ~43°C)** | Rischio elevato di freeze del browser |
| **Resilienza Offline** | **100% resiliente** (cache atomica persistente) | Schermate bianche o tentativi a vuoto |
| **Costi API** | **€0 / Zero API key** (Open-Meteo, Jolpica, PulseLive) | API a pagamento o quote restrittive |

---

## 🏗️ Architettura di Sistema

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                             DeskPulse OS Shell                                              │
│  [Orologio] • [Meteo] • [AI/Codex] • [Serie A] • [F1] • [MotoGP] • [Smart Home] • [Rete Locale / LAN Hub]  │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                               Compositore Accelerato su GPU Qt 6 Quick / QML                                │
│                               Display a 60 Hz via EGLFS/KMS e GPU PowerVR                                │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                    Piano Grafico Diretto DRM/KMS (EGLFS)                                    │
│                            (Bypassa X11 e Wayland • Gestione diretta input evdev)                           │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                     Kernel Linux 6.6 con Patch DP-AltMode                                   │
│                        Protezione MicroSD (swap zram, tmpfs in /tmp, commit fs a 30s)                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
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

Lo script configura automaticamente pacchetti Qt6, permessi utente `smartpc`, file di configurazione EGLFS e servizio systemd con avvio della dashboard EGLFS.

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

- **Carosello Orizzontale (Tasti 4 / 6):** Oggi ↔ Meteo ↔ AI/Codex ↔ Sport (Calcio, F1, MotoGP) ↔ Casa ↔ Rete locale.
- **Navigazione Verticale (Tasti 2 / 8):** Viste di dettaglio o navigazione discipline nello Sport Hub.
- **Azione / Entra (Tasto 5):** Apre i dettagli dell'incontro/GP, entra nelle discipline sportive o forza un aggiornamento dati.
- **Tasto Indietro / Home (Tasto 7):** Risale al livello precedente o torna all'orologio principale.
- **Menu di Sistema (Tasto 9):**
  - **Schermo:** Anteprima scala testo e spegnimento display.
  - **Aspetto:** Temi, luminosità e Gestione Temi per import/export.
  - **Moduli e Home:** Visibilità moduli, discipline Sport e tessere dinamiche Home.
  - **Avvisi:** Fascia di silenzio e soglie di allerta.
  - **Servizi collegati:** Stato collegamenti Tuya e router Iliadbox.
  - **Dati e aggiornamenti:** Refresh manuale centralizzato con feedback in tempo reale.

---

## 🌿 Strategia di Branching e Versioning

DeskPulse OS segue una struttura rigorosa di rami Git e tag semantici:

| Branch / Tag | Ruolo & Livello di Stabilità |
| :--- | :--- |
| `main` | Ramo principale di sviluppo pronto per la produzione; collaudato su hardware prima del push. |
| `release/v0.8` | **Ramo di manutenzione stabile corrente (serie v0.8.x)**; aggiornato alla v0.8.3. |
| `release/v0.7` | Ramo di manutenzione per la precedente serie v0.7.x. |
| `release/v0.6` | Ramo di manutenzione per la serie v0.6.x legacy. |
| `v0.8.3`, `v0.8.1`, `v0.8.0`, ... | Tag annotati immutabili coincidenti con le release ufficiali su GitHub. |

---

## 🗺️ Roadmap

- [x] **v0.4:** Compositore diretto EGLFS/KMS, Home dinamica, Meteo Open-Meteo.
- [x] **v0.5:** Motore eventi persistente, allerte Protezione Civile, badge notifiche.
- [x] **v0.6:** Hub Serie A, Squadra del Cuore, Fantacalcio, F1 & MotoGP con telemetria live SignalR.
- [x] **v0.6.1:** Architettura Impostazioni Modulare, Wi-Fi Live, Fantacalcio Live & Verifica 24h.
- [x] **v0.6.6:** **Theme Engine** — Base/Functional, layout e animazioni sostituibili, editor, pacchetti personali e scene persistenti.
- [x] **v0.7.0:** **Casa / Smart Life & Theme Engine 2.2** — Integrazione Tuya diretta, 4 tessere preferite, inventario, telemetria di dettaglio, ledger delle quote, resilienza offline e riduzione del 90.7% della latenza.
- [x] **v0.8.0:** **Rete locale (LAN Hub) & Case 3D Stampabile** — Integrazione router Freebox/Iliadbox, discovery di 39+ host, 4 tessere preferite, telemetria IPv4/IPv6, Theme API 2.3 (53 superfici) e modelli CAD STL/OpenSCAD del case.
- [x] **v0.8.1:** **Metriche Router, Storico RRD & Case 3D Perfezionato** — Viste Iliadbox/Internet, Wi-Fi e porte Ethernet con metriche qualificate e grafici storici RRD 1h/24h; Theme API 2.4 (56 superfici); coperchio con inclinazione ergonomica a 6° e feritoie convettive. [Report di consegna](dashboard/design/v081-implementation-report.md).
- [x] **v0.8.3:** **Sport Hub Unificato, Impostazioni per Compiti & Theme Engine 2.5** — Carosello a 6 macroaree, impostazioni riorganizzate, 60 superfici, ottimizzazione spazi display 3,5″ su Apple Calm 1.3.1 e persistenza atomica worker. [Report di consegna](dashboard/design/v083-implementation-report.md).
- [ ] **v0.9:** Compagno animato e profilo Cozy.
- [ ] **v0.10:** Memoria del compagno e scene AI validate.
- [ ] **v1.0:** Stabilità integrata, installazione, aggiornamento e recupero.

---

## 📄 Licenza

Distribuito sotto Licenza MIT. Consulta il file [LICENSE](LICENSE) per ulteriori dettagli.
