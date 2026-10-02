# Migrazione v0.6.6 Theme Engine

**2 ottobre 2026 · implementata e installata sulla Orange Pi.** Il runtime precedente comunicato come v0.6.5 è conservato nel backup T0. La nuova versione comune è 0.6.6; il manifest identifica ogni file distribuito. La ricostruzione dei precedenti numeri v0.6/v0.6.1 non viene riscritta retroattivamente.

[Uso, formato dei temi ed estensioni](theme-engine-implementation-guide.md). [MasterPlan aggiornato](release-masterplan.md).

## Consegna T0–T5

| Fase | Risultato verificato |
| --- | --- |
| T0 | Backup completo del runtime e dei dati utente, hash dei sorgenti, confronto dei quattro harness divergenti, baseline EGLFS con fixture e comandi ripetibili. Guide riconciliate con decoder conservato: 1 Home, 7 Back. |
| T1 | Resolver/contratto JSON, facade QML tipizzata, registry visuali/motion/icone/scene; Home a sinistra/centrata; attore persistente. |
| T2 | Tutti i 21 QML preesistenti migrati a token/componenti comuni; provider e controller applicativo conservati. Host stabili e test con readiness/riacquisizione del visuale. |
| T3 | Base e Functional su tutte le superfici, varianti giorno/notte, scala/densità, motion Normal/Reduced/Off. |
| T4 | Editor, preview/apply/cancel/reset, import/export asincrono, terzo tema ed estensione realmente selezionati; salvataggio atomico e recovery. |
| T5 | Matrice EGLFS, due stress da 100 cambi, font/immagine reali, reboot offline, crash reale, rollback completo, verifica del packaging e documentazione. |

La scena geometrica è una prova dell'infrastruttura: il compagno, le pose e gli asset definitivi rimangono nella v0.9. Lo stato dell'azione/pose è separato dalla locomozione, affinché un cambio schermata non interrompa un'azione del futuro renderer.

## Verifiche software e visuali

- **22 harness passati localmente**, Qt 6.11.2: [esiti](evidence/v066-migration/local/checks.json).
- **22 harness passati sulla board**, Qt 6.8.2: [esiti con SHA dei test](evidence/v066-migration/board/checks.json). Il controllo QML è stato rieseguito dopo la separazione pose/locomozione.
- **26 casi EGLFS passati**: [matrice](evidence/v066-migration/board/smartpc-v066-matrix/checks.json). Quattro combinazioni Base/Functional × giorno/notte; tre profili normal/reduced/off negli harness di Home, Sport, Motorsport, squadra, Fantacalcio, impostazioni; impostazioni/Info con scala 110% e densità ampia.
- Catture reali 960×640 ispezionate per gerarchie, clipping e leggibilità: [panoramica](evidence/v066-migration/board/theme-overview.png), [font e densità ampia](evidence/v066-migration/board/smartpc-v066-matrix/functional-wide-settings/appearance.png), [dettaglio squadra](evidence/v066-migration/board/smartpc-v066-matrix/base-night-off-check_sport_team_ui/team-future-detail.png).
- Font TTF reale, deduplicazione per digest fra servizi, glifi assenti, famiglia assente e rimozione di un asset già memorizzato; PNG reale e backend glifo/geometria sullo stesso ID.
- Errori di tipo, refusi, contrasto, cicli, risorse e pacchetti incompatibili respinti; cartella di preferenze realmente non scrivibile; processo nuovo dopo Apply; catalogo Python guasto con fallback QML indipendente e navigazione ancora disponibile.
- Menu/urgente durante Loader attivo, burst di swap, input Qt con activeFocus, scancode HID decodificati, selezioni/tab/stack nei dettagli e assenza di nuove chiamate provider/mark-read/dismiss durante un cambio tema.

Nessun warning QML inatteso nei percorsi provati. I test di recovery classificano i guasti deliberati; i collaudi provider durante eventi sportivi realmente attivi restano quelli già aperti prima della migrazione.

## Prestazioni e budget adottati

Scheda effettiva: **Allwinner A733**, 6 Cortex-A55 + 2 Cortex-A76, PowerVR BXM-4-64, Debian 13, Python 3.13.5, PySide6 6.8.2.1 / Qt 6.8.2. Render EGLFS/KMS su card0, OpenGL, pannello 960×640/60 Hz. Non si attribuisce questa misura a Cortex-A53 o H618.

La baseline e il confronto finale usano dati isolati, DejaVu Sans, luminosità al 100%, stessi comandi e finestre di movimento. FrameSwapped misura intervalli fra frame nel processo Qt: non tempo GPU, render time o risposta ottica del pannello. Gli intervalli lunghi all'interno delle finestre vengono conservati; le pause idle sono escluse azzerando il riferimento a ogni azione. La latenza al primo frame viene misurata separatamente.

| Carico EGLFS | p95 intervallo animato | Risultato |
| --- | --- | --- |
| T0, 20 s, Base giorno precedente | 17,814 ms | Nessun intervallo >33,34 ms; PSS finale 102,65 MiB. [Campione](evidence/v066-migration/t0/report.json) |
| Confronto finale Base giorno, 20 s, 43 transizioni | 17,742 ms | Nessun intervallo >33,34 ms; input p95 22.148 ms; PSS finale 103.42 MiB, delta T0 +0.77 MiB. [Campione](evidence/v066-migration/board/smartpc-v066-release-base-day/report.json) |
| Matrice Base giorno/notte | 17,35 / 17,762 ms | Nessun intervallo >33,34 ms nei due campioni. |
| Matrice Functional giorno/notte | 17,604 / 17,687 ms | Nessun intervallo >33,34 ms nei due campioni. |
| Movimento Ridotto | 17,732 ms | Tween più brevi; nessun intervallo >33,34 ms. |
| 100 cambi Base/Functional + scena | 17,736 ms | Primo frame del profilo p95 117,98 ms; max 128,14 ms. Nessun intervallo animato >33,34 ms. |
| 100 cambi con tre famiglie TTF + scena | 17,927 ms | Primo frame coerente p95 115,03 ms; max 193,46 ms; 4 intervalli >33,34 ms, uno >50 ms, max 74,10 ms. |

Off è stato verificato come assenza di tween e finalizzazione immediata; pochi frame dovuti a Loader/dati non costituiscono un FPS di animazione. Input di navigazione p95 nei quattro profili ordinari: circa 19–35 ms. I budget di uscita sono **p95 ≤20 ms per navigazione ordinaria**, senza frame >33,34 ms nei campioni, e **p95 ≤150 ms per cambio completo del profilo**. Il precedente 100 ms era un'ipotesi dell'analisi: il costo misurato di staging/binding/layout richiede il budget di 150 ms. Non si nasconde il massimo cold di circa 193 ms né si garantiscono 60 fps durante il primo uso di ogni font o durante qualsiasi futura scena.

Memoria dello stress: due preset senza TTF aggiuntivi, PSS picco **109,51 MiB**, crescita fra warmup e ultimi cicli **0,28 MiB**; tre TTF reali, picco **114,40 MiB**, crescita **0,35 MiB**, tre registrazioni al termine. Nessuna crescita persistente nel campione da 100 cambi. [Preset](evidence/v066-migration/board/smartpc-v066-stress-presets/report.json), [tre font](evidence/v066-migration/board/smartpc-v066-stress-final/report.json).

Il primo stress ha rilevato churn del FontDatabase: una LRU di due font inattivi espelleva font riusati al ciclo successivo. Corretti mantenimento limitato di quattro registrazioni inattive, riuso delle snapshot validate, pubblicazione della snapshot già preparata e congelamento dello stile delle superfici nascoste. La misura iniziale con font serif dovuto alla famiglia vuota è stata scartata e il default effettivo di sistema ripristinato.

RSS/PSS/cgroup non rappresentano tutta la memoria grafica condivisa; non sono disponibili contatori affidabili di allocazione GPU per questo collaudo. I campioni del servizio con provider reali sono riportati separatamente in [boot](evidence/v066-migration/board/boot-health.json) e [crash](evidence/v066-migration/board/crash-health.json), senza confrontarli direttamente con fixture leggere. I 100 cicli non equivalgono a un soak di 24 ore.

## Riavvio, crash, rollback e distribuzione

**Reboot fisico offline:** unit temporanea eseguita prima della dashboard, `PrivateNetwork=yes`, preferenze/cache isolate. Functional/notte/Ridotto viene ricaricato; la richiesta reale Open-Meteo fallisce; meteo salvato resta visibile e Home → Meteo funziona. Zero indirizzi globali e route di default; gli interface tunnel privi di indirizzi del kernel sono ammessi. [Report e boot ID](evidence/v066-migration/board/offline/report.json), [cattura](evidence/v066-migration/board/offline/cold-offline.png). La rete host/SSH non è stata disabilitata: questa è una prova offline nel namespace, non una perdita fisica di Wi-Fi dell'intera scheda. Una prima esecuzione è stata scartata per un'asserzione del harness che richiedeva erroneamente il solo interface lo; il controllo corretto è stato rieseguito al reboot. L'unit temporanea è stata rimossa.

**Crash reale:** SIGKILL del processo in servizio, nuova PID e NRestarts=1, dashboard attiva e preferenze con lo stesso SHA prima/dopo. [Evidenza](evidence/v066-migration/board/crash-health.json).

**Rollback reale:** runtime completo estratto dal backup T0 e avviato; 155 file identici all'archivio, nessuna mescolanza di sottodirectory nuove. Reinstallazione del runtime v0.6.6, processo stabile e distribuzione verificata, preferenze immutate. [Report](evidence/v066-migration/board/rollback-report.json).

Backup privati sulla board: `/var/backups/smartpc-v066-t0/dashboard.tar.gz`, `user-state.tar.gz`; copie precedenti e prova di rollback in `/var/backups/smartpc-v066-operations`. Backup del workspace iniziale in `~/.local/state/smartpc-migrations/v066-t0`. Cache e preferenze reali non sono nel repository.

Packaging ricorsivo di **157 file**, SHA256 per file, qmldir/JS/JSON/QML e risorse dichiarate. Qt Quick Shapes installato sulla board (611 KiB, nessun upgrade della Qt); installer aggiornato per la dipendenza e per il rollback in caso di PID non stabile. Versione Info 0.6.6. Commit/tag e manifest conclusivo vengono registrati insieme alle evidenze finali; nessun push o pubblicazione remota implicita.

## Limiti residui del perimetro

La migrazione del motore è completa. Restano distinti: scelta dei font/palette/animazioni definitivi; osservazione ottica e nuova pressione umana del tastierino; soak prolungato; carichi/rig/shader del compagno reale; collaudi live dei provider già aperti. Le nuove presentazioni devono verificare metriche, aree sicure e budget sul dispositivo. Il motore consente di aggiungere renderer/ricette/asset e ruoli; l'estensione non elimina i limiti fisici della scheda.
