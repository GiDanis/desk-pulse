# v0.6.6 — inventario verificato prima del Theme Engine

**2 ottobre 2026 · ispezione in sola lettura.**

## Board e provenienza

- Campione: `2026-10-02T00:56:18.010971+02:00`.
- Servizio: `active/running`, PID `202220`, NRestarts `0`; avviato `Fri 2026-10-02 00:04:15 CEST`.
- Qt `6.8.2`, PySide6 `6.8.2.1`; EGLFS/KMS e backend OpenGL definiti da `run.sh --device`.
- Cartella installata: `/opt/smartpc/dashboard`; nessuna directory `themes/` presente.
- HEAD locale: `2057e79f5a43e9296529cbf23251940178f0d544`. Baseline di prodotto v0.6.5 secondo MasterPlan; Info contiene ancora `DeskPulse v0.6`, titolo ultimo commit v0.6.1.
- Confrontati 64 file installati di primo livello (`.qml`, `.py`, `.sh`): tutti i 44 file classificati runtime corrispondono al locale; quattro script di verifica differiscono.
- File differenti: `check_fantacalcio.py`, `check_fantacalcio_ui.py`, `check_motorsport.py`, `check_sport_ui.py`. Vanno riconciliati prima di usare la suite installata come riferimento.
- Memoria: RSS 182.4 MiB; PSS 165.1 MiB. Un campione passivo; nessuna conclusione su crescita o FPS.
- Non eseguiti: restart, cambi preferenze, input, catture EGLFS, reboot o benchmark. Gli hash confrontano i file su disco; non certificano il contenuto già caricato dal processo.

Dati completi: [manifest board](board-baseline.json), [inventario sorgenti](source-inventory.json).

### Riscontro per la review dei rischi

Alle `2026-10-02T19:23:39+02:00`, lettura di identità CPU, Qt e stato servizio: sei CPU part `0xd05` e due `0xd0b`; Qt/PySide invariati, stesso PID e NRestarts 0. [Dati SSH](risk-review-board.json), [review bridge/Loader/font](../../theme-engine-risk-review.md). Questo riscontro non carica font, non renderizza un prototipo e non aggiorna il campione RSS/PSS precedente.

## Inventario QML

Scansione testuale dei soli `dashboard/*.qml`. I conteggi distinguono occorrenze e valori distinti; non provano che ogni letterale sia un errore. `transparent` e `black` sono esclusi dal conteggio degli esadecimali.

Totali: **21 file**, **1925 righe**, **61 occorrenze esadecimali / 20 colori distinti**, **200 espressioni `font.pixelSize`**, **0 `font.family`**, **41 espressioni `radius`**.

Review icone: [scansione e hash dei 21 QML](icon-inventory.json). Zero dichiarazioni di Image, AnimatedImage, AnimatedSprite, SpriteSequence, Shape e Canvas; simboli testuali già presenti, per esempio la stella del preferito. Conteggio lessicale, non profiling o ispezione del scene graph. [Strategia proposta](../../theme-engine-icon-spec.md).

| File | Righe | Hex | Font size | Radius | NativeRendering |
| --- | ---: | ---: | ---: | ---: | ---: |
| [AccountChatGPT.qml](../../../AccountChatGPT.qml) | 127 | 3 | 14 | 6 | 0 |
| [DashboardOverlay.qml](../../../DashboardOverlay.qml) | 99 | 3 | 13 | 2 | 0 |
| [DeviceInfo.qml](../../../DeviceInfo.qml) | 85 | 3 | 9 | 2 | 9 |
| [EventBanner.qml](../../../EventBanner.qml) | 63 | 1 | 5 | 1 | 0 |
| [EventLargeBanner.qml](../../../EventLargeBanner.qml) | 6 | 0 | 0 | 0 | 0 |
| [EventUrgent.qml](../../../EventUrgent.qml) | 45 | 3 | 5 | 0 | 0 |
| [HomeDay.qml](../../../HomeDay.qml) | 12 | 0 | 6 | 0 | 0 |
| [HomeNow.qml](../../../HomeNow.qml) | 25 | 1 | 2 | 0 | 0 |
| [InfoCard.qml](../../../InfoCard.qml) | 17 | 10 | 3 | 1 | 0 |
| [Main.qml](../../../Main.qml) | 747 | 15 | 11 | 2 | 0 |
| [MotorsportOverlay.qml](../../../MotorsportOverlay.qml) | 121 | 3 | 24 | 5 | 0 |
| [MotorsportView.qml](../../../MotorsportView.qml) | 57 | 2 | 11 | 2 | 0 |
| [SettingsPanel.qml](../../../SettingsPanel.qml) | 142 | 2 | 8 | 1 | 0 |
| [SportFantasy.qml](../../../SportFantasy.qml) | 35 | 2 | 13 | 2 | 0 |
| [SportOverlay.qml](../../../SportOverlay.qml) | 141 | 6 | 32 | 7 | 0 |
| [SportTeamOverlay.qml](../../../SportTeamOverlay.qml) | 67 | 4 | 13 | 3 | 0 |
| [SportTeamView.qml](../../../SportTeamView.qml) | 28 | 1 | 10 | 2 | 0 |
| [SportView.qml](../../../SportView.qml) | 58 | 1 | 10 | 3 | 0 |
| [UnreadAlertsBadge.qml](../../../UnreadAlertsBadge.qml) | 16 | 0 | 1 | 1 | 0 |
| [WeatherForecast.qml](../../../WeatherForecast.qml) | 22 | 0 | 7 | 1 | 0 |
| [WeatherNow.qml](../../../WeatherNow.qml) | 12 | 1 | 3 | 0 | 0 |

## Problemi concreti dei vecchi esempi

Rapporti sRGB calcolati per coppie **proposte nei Markdown**, senza attenuazione o antialiasing. Non sono misure del pannello né un giudizio di conformità del software esistente.

| Coppia testo/sfondo | Rapporto | Implicazione |
| --- | ---: | --- |
| `#728a92` / `#1c2d38` | 3.89:1 | Sotto il target di progetto 4,5:1 per testo informativo |
| `#5c747c` / `#14232c` | 3.25:1 | Sotto il target di progetto 4,5:1 per testo informativo |
| `#666664` / `#242424` | 2.70:1 | Sotto il target di progetto 4,5:1 per testo informativo |
| `#8c8c8a` / `#383838` | 3.48:1 | Sotto il target di progetto 4,5:1 per testo informativo |
| `#d9534f` / `#242424` | 3.92:1 | Sotto il target di progetto 4,5:1 per testo informativo |

Il contrasto va verificato anche sullo sfondo selezionato. La palette Functional degli esempi non è pronta al rilascio. Vedere [specifica](../../theme-engine-construction-spec.md) per le correzioni e i gate.
