# Theme Engine — accettazione supplementare A1–A6

Data: 2026-10-05. Esecuzione sul PC di sviluppo con PySide6/Qt 6.11.2, backend `offscreen`; dati, cache, preferenze e database delle notifiche isolati prima della creazione di Qt. Il risultato riguarda il working tree in integrazione e non costituisce evidenza di rilascio o collaudo EGLFS della board.

## Verifiche

| Blocco | Prova | Evidenza |
| --- | --- | --- |
| T16 / parte T19 | Cinque test con `ThemeService`, resolver, journal e QSettings reali: A→B→ritorno, annulla, ricostruzione del servizio, override separati per revisione immutabile, salvataggio fallito, errore sync e commit journal fallito dopo la scrittura delle preferenze | `evidence/theme-acceptance-supplement-2026-10-05/profiles.log` |
| T11 / parte T12 | Main reale con sei renderer API2 delle notifiche, identità evento small/large, deadline di otto secondi conservata durante preview/cancel, unread badge, inbox e typed itemModel, dettaglio, urgente durante preview, rifiuto di azioni non urgenti e focus protetto | `evidence/theme-acceptance-supplement-2026-10-05/notifications.json` |
| A1/A3/A5 | Main reale con menu esterno `MenuContext`: modello di quattro righe, selezione e attivazione via broker privato, cambio route e ripristino focus | `evidence/theme-acceptance-supplement-2026-10-05/overlay.json` |
| Primo frame coerente | Il renderer overlay viene reso non pronto dopo lo staging ma prima del primo frame: `readyToApply` e `apply` restano bloccati fino al ritorno a pronto e a un frame effettivo del runtime offscreen | `evidence/theme-acceptance-supplement-2026-10-05/overlay.json` |
| Primo frame coerente scena | La scena API2 viene resa non pronta dopo lo staging: il primo frame non viene riconosciuto come coerente e Apply resta bloccato; il ritorno a pronto consente frame e applicazione | `evidence/theme-acceptance-supplement-2026-10-05/scene-frame.json` |
| Parte T05/T09 | Scena valida importata con il vero preflight Qt, poi errore esplicito iniettato nel renderer attivo: recupero Base, revisione in quarantena, journal chiuso e preferenze funzionali/eventi/focus conservati | `evidence/theme-acceptance-supplement-2026-10-05/scene-error.json` |
| Parte T05 | Scena mai pronta: watchdog indipendente di preparazione, candidata respinta e aspetto precedente conservato | `evidence/theme-acceptance-supplement-2026-10-05/scene-neverready.json` |

Le integrazioni finali aggiungono tre prove separate, archiviate nel resoconto A1–A6:

| Blocco | Prova | Evidenza |
| --- | --- | --- |
| Parte T01/T17 | Dieci controlli Main su area content negoziata e full canvas, clipping, viewport/layout tipizzati, fallback legacy, aree sicure attore, annullamento e Apply dopo frame coerente | `evidence/theme-engine-a1-a6-2026-10-05/local/final-integration/layout-ui.json` |
| Parte T11/T12 | Undici controlli notifiche, inclusa perdita di readiness del visuale urgente già committato: fallback app immediato e identità/deadline conservate | `evidence/theme-engine-a1-a6-2026-10-05/local/final-integration/urgent-readiness.json` |
| Parte T16/A5 | Quattro test di allowlist per revisione, adattamenti non consentiti rimossi, policy movimento globale, getter senza I/O, coverage e controlli disabilitati nel Main reale; regressioni profili 5 e impostazioni 13 PASS | `evidence/theme-engine-a1-a6-2026-10-05/local/final-integration/adjustments.log`, `profiles.log`, `settings-api.json` |

Il test T16 simula esplicitamente gli ack di host/frame per isolare il contratto di persistenza: non pretende di dimostrare readiness o presentazione grafica. La prova `scene-neverready` importa intenzionalmente la fixture con un preflight `testOnly`; questo serve a raggiungere il watchdog del runtime e non riproduce il normale percorso di importazione, che deve già respingere un renderer non pronto. Gli altri casi Main usano il vero preflight separato Qt.

I cinque casi Main richiedono zero warning QML. I renderers supplementari sono costruiti in una directory temporanea e non vengono installati fra i temi di produzione.

## Limiti espliciti

Queste prove non chiudono tutti i sottocasi T01–T21. Questa suite PC non prova comportamento fisico del tastierino, leggibilità ottica, tutte le combinazioni di testo/font e layout, prestazioni e plateau RAM, endurance, power-cut reale o reboot hardware. Le prove Qt 6.8.2/EGLFS e del supervisore sono archiviate separatamente nel [resoconto A1–A6](theme-engine-a1-a6-implementation-report.md); conservano i propri esiti e limiti. A6 rimane in corso, con 150 ms e costo diagnostico 1 ms/8 MiB aperti, oltre alla qualificazione dei cinque concept. Il fatto che l'inputOwner mantenga l'activeFocus nella prova non equivale alla verifica di un dispositivo HID fisico.

Comandi riproducibili:

```sh
QT_QPA_PLATFORM=offscreen /home/giuseppe/.local/share/smartpc-dev-venv/bin/python dashboard/check_theme_profiles.py
QT_QPA_PLATFORM=offscreen /home/giuseppe/.local/share/smartpc-dev-venv/bin/python dashboard/check_theme_bundle_acceptance.py --case notifications
QT_QPA_PLATFORM=offscreen /home/giuseppe/.local/share/smartpc-dev-venv/bin/python dashboard/check_theme_bundle_acceptance.py --case overlay
QT_QPA_PLATFORM=offscreen /home/giuseppe/.local/share/smartpc-dev-venv/bin/python dashboard/check_theme_bundle_acceptance.py --case scene-error
QT_QPA_PLATFORM=offscreen /home/giuseppe/.local/share/smartpc-dev-venv/bin/python dashboard/check_theme_bundle_acceptance.py --case scene-neverready
QT_QPA_PLATFORM=offscreen /home/giuseppe/.local/share/smartpc-dev-venv/bin/python dashboard/check_theme_bundle_acceptance.py --case scene-frame
```

Il riepilogo machine-readable e gli hash dei due script sono in `evidence/theme-acceptance-supplement-2026-10-05/summary.json`.
