# v0.8.1 · Router, Wi-Fi, porte e storico — consegna

**0.8.1-rc.1 · 7–8 ottobre 2026 · Theme API 2.4 · 56 superfici.** E0–E4 realizzate: tre approfondimenti nella famiglia Rete, backend comune asincrono, cache metriche separata e grafici RRD. La candidata è installata sulla Orange Pi. Base e Functional hanno presentazioni native; Apple Calm 1.2.0 riceve i nuovi fallback Base nello stile del tema, mantenendo il bundle immutato. [Uso e tastierino](v081-network-operations.md).

## E0 · Fonti, unità e budget

La baseline iniziale attestava v0.8.0-rc.1 installata, 475 file verificati, servizio senza restart e Apple Calm. Il checkout era 0.8.0/tag v0.8.0, commit base `99f97f5`. La nuova distribuzione dichiara il checkout modificato e non crea un tag stabile. [Baseline](evidence/v081-implementation-2026-10-07/baseline-board.json).

Il probe dalla board ha eseguito 24 richieste in 3,15 s, con chiusura della sessione. Sono qualificati WAN/FTTH, potenze ottiche, firmware/uptime, sensori/ventola, due radio, stazioni, tre porte e RRD `net/temp/switch` in 1 h e 24 h. Il token esistente è sufficiente alle letture riuscite, con `settings=false`; nessuna password amministratore entra nell’app. [Qualifica filtrata](evidence/v081-implementation-2026-10-07/e0-board-metrics.json).

| Dato | Normalizzazione e significato |
| --- | --- |
| WAN rate / RRD `net` | byte/s × 8 → bit/s. Capacità riportata già in bit/s; non è uno speed test. |
| Potenza SFP | Centi-dBm → dBm, solo con `sfp_has_power_report=true`. RX osservato −18,23 dBm, TX 2,56 dBm nel probe. |
| Sensori / fan | °C / RPM del router, non temperatura o ventola Orange Pi. Firmware osservato 4.9.18.2. |
| Segnale radio | Valore raw in dB, senza percentuale o dBm dedotti. `last_rx/last_tx.bitrate` in decimi di Mbit/s; ultimo link riportato, non throughput Internet. |
| Traffico stazione | Delta esatto dei contatori: RX ricevuto dalla box, TX inviato dalla box. `rx_rate/tx_rate` ambigui non usati. |
| Switch | Rate byte/s × 8; `rrd_id` scoperto dallo stato porta. Traffico aggregato della porta, senza attribuzione del totale a ogni MAC. |

Due trasferimenti controllati da **16 MiB**, campionando la stazione della board, hanno verificato la direzione: PC → board aumentava TX box di 17.572.804 byte; board → PC aumentava RX box di 17.567.491 byte. Non modificano la configurazione del router e non sono uno speed test. [Misura](evidence/v081-implementation-2026-10-07/e0-direction.json).

In acquisizione reale successiva sono riuscite tutte le 18 capacità normalizzate, con 39 record LAN, 2 radio, 7/4 record stazione e 3 porte. RRD 1 h: 360 punti WAN, 30 temperature/porte; 24 h: 1.050 WAN e 720 temperature/porte. Riduzione pubblica fino a 180 punti. Batch WAN/stazione a regime: cinque richieste incluse discovery/challenge/sessione/logout; porta con statistiche: sei. Tempi misurati fra 0,55 e 1,25 s; discovery/metadati iniziali possono aggiungere GET. [Letture reali](evidence/v081-implementation-2026-10-07/live-metrics.json).

Il default resta **30 s**, circa 10–12 richieste/minuto nel dettaglio stabile, più inventario/metadati/storico. Non è stata attivata la proposta 5–10 s. Survey/occupazione canale, MLO simultaneo e neighbor scan non hanno qualifica di freschezza/attività e non entrano nella candidata.

## E1 · Adapter, cache e storico

`network_metrics.py` filtra i campi prima della persistenza; `network_history.py` normalizza finestre/serie, ordina e deduplica timestamp e conserva null e discontinuità. Ogni capacità ha stato, timestamp, errore e ultimo dato indipendenti. Una fonte opzionale guasta non invalida inventario, preferiti o altre capacità sane.

SQLite complementare privato: directory 700, file 600, scope per UID router, validazione completa della whitelist e della struttura annidata al caricamento. Payload massimo 8 MiB, fino a 24 chiavi storiche, entità ritirate eliminate. RRD: massimo 10.000 punti raw, 180 pubblici per serie, due serie visibili; min/max per bucket conservano picchi e interruzioni. La cache fredda è sempre precedente e mantiene le date della finestra salvata.

I contatori rimangono interi Python/SQLite; il DTO espone totali formattati, senza `int` QML o conversioni prima della sottrazione. Nuova associazione, reset, salto di clock, baseline mancante o intervallo >90 s rendono il delta indisponibile. Salvataggio fallito non sostituisce il dato confermato. [Controlli](evidence/v081-implementation-2026-10-07/metrics-core.txt).

## E2 · Coordinatore visibile

Un solo pool/worker della famiglia Rete. Inventario 300 s, metadati 600 s, batch visibile 30 s, stessa finestra RRD almeno 60 s. Pausa automatica, deadline, cancellazione, backoff e cooldown per chiave sono conservati. Interesse dell’ultima vista prevale dopo un risultato tardivo; questo può aggiornare la propria cache, senza essere proiettato nella nuova selezione. Preferenze e refresh inventario richiesti durante un batch sono coalescenti e hanno precedenza al completamento.

Un `auth_required` consente un solo rinnovo per batch; revoca/UID/TLS fermano la raccolta. `insufficient_rights` è un errore della singola capacità, senza login ripetuti. I segnali metriche non invalidano Aspetto. Il broker pubblico completa il refresh solo dopo persistenza; errori parziali e disco non producono una falsa conferma. La chiusura sopprime i callback delle operazioni in corso. [Worker, UI e broker reali](evidence/v081-implementation-2026-10-07/metrics-broker-final.txt).

## E3 · UI e Theme

Tre overlay condividono renderer e grafico Canvas Qt Quick, senza QtCharts o I/O QML. Router: Stato/Storico, con WAN, temperature e fan separati; Wi-Fi: Radio/Stazioni/Dettaglio; Porte: elenco/host-statistiche/storico. Il collegamento ai record LAN usa identità e MAC verificati, senza fondere stazioni per nome/IP o attribuire traffico porta a singoli host. Il ritorno conserva la selezione LAN.

Theme API **2.4**: 56 superfici, 21 contesti, 70 tipi, 39 modelli, 48 azioni; `NetworkRouterContext`, `NetworkWifiContext`, `NetworkPortsContext` e DTO grafici/righe limitati. Generator, runtime qmltypes, registry, pack e corpus sono aggiornati insieme. La compatibilità aggiunge soltanto i gruppi completi riconosciuti. [Contratto](evidence/v081-implementation-2026-10-07/contract-generated.json).

Il [kit AI v0.8.1](artifacts/smartpc-theme-ai-kit-v081.zip) include SDK autonomo e contratto, senza stato privato o credenziali. Core e UI del kit sono verificati fuori dal repository. L’export del kit non certifica un tema nuovo: resta necessaria la sua qualifica. [Export](evidence/v081-implementation-2026-10-07/sdk-export-complete.json), [core](evidence/v081-implementation-2026-10-07/sdk-core-complete.txt), [UI](evidence/v081-implementation-2026-10-07/sdk-ui-complete.txt).

## E4 · Board, installazione e reboot

| Prova | Evidenza e ambito |
| --- | --- |
| PC Qt 6.8.2 | **69 controlli superati**, suite completa con ricontrolli mirati dopo le correzioni. L’esito consolidato conserva la provenienza dei run precedenti. [Indice](evidence/v081-implementation-2026-10-07/regression-final.json). |
| EGLFS Base/Functional | Tre viste, grafici, pause/errori, tastierino programmato e broker; nessun warning QML. [Ultima verifica](evidence/v081-implementation-2026-10-07/board-eglfs-delivery.txt). |
| Apple Calm 1.2.0 | Tre fallback e grafici reali salvati 1 h/24 h; bundle originale immutato, nessuna richiesta router nel test cache. [Prova](evidence/v081-implementation-2026-10-07/board-apple.txt). |
| Provider reale + GUI | 39,12 s, 35 richieste, sei completamenti riusciti; secondo campione Wi-Fi dopo 30,74 s, nessuna lettura aggiuntiva a vista nascosta. Timer GUI 20 ms: p95 20,74 ms, massimo 476,05 ms nella prova con cambi vista/catture; picco RSS 201.776 KiB. Sono misure del loop software, non FPS GPU o latenza input-to-pixel. [Prova](evidence/v081-implementation-2026-10-07/live-gui.json). |
| Distribuzione | **490 file** corrispondenti al manifest, backup completo, preferenze conservate. Checkout base `99f97f5`, modificato, nessun tag v0.8.1 creato. [Ricevuta finale](evidence/v081-implementation-2026-10-07/install-receipt.json), [verifica consegna](evidence/v081-implementation-2026-10-07/delivery-verification.json). |
| Reboot finale | Boot ID diverso, GUI pronta e heartbeat fresco, servizio `active/running`, `NRestarts=0`, Apple Calm/digest e preferenze conservati, inventario nuovo e sei finestre cache precedenti. [Prima](evidence/v081-implementation-2026-10-07/pre-reboot-health.json), [dopo](evidence/v081-implementation-2026-10-07/post-reboot-health.json). Verifier/prove persistono in `/var/lib/smartpc-dashboard/v081-proof/`. |

Il backup originale v0.8 è `/var/backups/smartpc-before-v081-20261007T220529Z`; la ricevuta finale contiene anche il backup della revisione precedente della candidata. Preferenze hash `f266f144166e8e065ba1af4f830dbe06e5d22956b475c6ba98db6cd9cb59dc4a`. Apple Calm digest `0f30f79c9ed959368df85cc498acb5698a687cdde60448a909136759d1116553`. Le catture con nomi e identificativi reali rimangono private sulla board; il repository contiene soltanto catture sintetiche ed evidenze filtrate.

## Decisione e residui

**E0–E4 completate per il perimetro qualificato della candidata.** La v0.8.1 è pronta all’uso con il token esistente. Rimane `rc.1`: una prova mirata e un reboot ordinato non certificano un funzionamento prolungato, power-cut, un tastierino fisico azionato né perdita/ripresa fisica della LAN. Il RSS del servizio Apple Calm rilevato dopo reboot è 236.752 KiB (circa 231 MiB), riportato nel verifier; nessuna promessa di consumo <90 MB o zero overhead.

Rimangono i gate precedenti di presenza/copertura: 39 record restituiti contro 54 nel contatore box e guest non disponibile; raggiungibili secondo la box non equivale a dispositivi fisicamente accesi. N4/WebSocket/notifiche, quota/comandi Casa, MLO operativo, survey fresco e consumo Internet mensile per host sono separati e non dichiarati chiusi da questa consegna.
