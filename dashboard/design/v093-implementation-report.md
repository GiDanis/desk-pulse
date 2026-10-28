# Dashboard Orange Pi v0.9.3 — attuazione delle ottimizzazioni

**22 ottobre 2026 · candidata 0.9.3-rc.1 installata · 645 file verificati · tre reboot qualificati.** Apple Calm 1.6.3 e Theme API 2.11 conservati; promozione a release stabile ancora aperta. [Piano generale](v093-systemwide-execution-plan.md), [analisi](v093-systemwide-analysis.md), [evidenze e sorgenti delle prove](evidence/v093-implementation-2026-10-21/README.md).

## Interventi dell'intero sistema

| Lotto | Intervento scelto | Confine conservato |
| --- | --- | --- |
| V0 | Oracolo delle nuove viste Rete, percentile nearest-rank, pubblicazione di revisioni immutabili nelle fixture; isolamento completo dei test | I precedenti tentativi/fallimenti restano consultabili; nessun esito negativo nascosto |
| V1 | Handoff Plymouth root separato, prima del kiosk; eliminato il quit preliminare non privilegiato che falliva; escluso il timer estraneo al ruolo dedicato | Dashboard ancora eseguita come smartpc, sandbox e accesso SSH mantenuti; unità e stato timer salvati |
| V2 | Proiezione Sport riusata per identità della fonte, preferenze e soglie temporali esatte; passaggio a QML di riepiloghi della stagione e del solo dettaglio selezionato | Snapshot completi per acquisizione, notifiche e consumatori Python; freshness, cache precedente e revoca Live conservate |
| V3 | Decodifica eventi riusata con limite di 2.048 payload; righe/deadline riusate fino a commit o scadenza, con data_version per scrittori esterni | Persistenza, ordine, coda piena, revoche, quiet, presentazione e ACK restano transazionali |
| V4 | Il bridge MatchContext trasferisce la fonte e il match selezionato; disponibilità Casa/Rete aggiornata dal relativo servizio e sequenza dei moduli distaccata una volta in JavaScript | Stesso snapshot pubblico, verificato per tutti gli stati di fonte; cache overlay già esistente di sei renderer conservata |
| V5 | Lettore metadati persistente in processo, SQLite query_only e transazione coerente; proiezioni per versione/rotta, invalidazione da commit; nessun timer attivo quando il reader è in attesa | Nessuna migrazione o scrittura nel reader; writer e ACK durevoli invariati; tutti gli storici consultabili restano nel dossier e nel database |
| V6 | Confronti ABBA di priorità GUI e governor del cluster A76 | Scelta finale dalle misure; niente SCHED_FIFO, overclock, affinità obbligatoria o limiti RAM artificiali |
| V7 | Nativo numerico e driver correnti conservati; nessun nuovo carico NPU/compute senza un modello e un vantaggio dimostrati | Libreria ARM e precisione numerica invariate; niente sostituzione parziale del driver del kiosk |
| V8 | Metadata reader avviato fuori dalla costruzione iniziale della GUI; curricula privati trasformati in DTO compatti; SQL filtra pilota/modalità/stato prima del JSON; exercise calcolato una volta per valutazione | Start esplicito, ricette, piloti, pesi, fisica, clock e checkpoint non modificati; il reader informativo non avvia learner |
| V9 | Matrice di tutte le superfici, prove EGLFS esclusive, rollback e installazione con ricevuta, verifiche del boot | Qualifica software, fonte live e verifica fisica restano distinte |

Meteo, Account, Squadra/Fantacalcio, F1/MotoGP, Casa, Rete, notifiche, impostazioni e Info fanno parte delle verifiche. I percorsi già efficienti mantengono worker, backoff, quote, push e polling esistenti. Il provider Rete continua a confermare il refresh soltanto dopo store.save; Fantacalcio resta su consultazione. Non si riscrive un servizio da pochi microsecondi per dichiarare un intervento in ogni casella.

## Ripartizione hardware e runtime scelto

L’inventario usa device tree, capacità CPU e driver effettivi, non il solo hostname. La board osservata espone sei Cortex-A55 e due Cortex-A76; il percorso grafico qualificato è PowerVR BXM, EGLFS/KMS/OpenGL a 960×640. La libreria numerica AArch64 preesistente è distribuita con hash invariato, insieme al relativo sorgente C invariato.

| Risorsa | Impiego effettivo |
| --- | --- |
| CPU | I/O nei worker esistenti; normalizzazione e contratti in Python; metadati pesanti in processo separato, con letture SQLite coerenti; calcolo numerico già nativo conservato |
| GPU | Scene graph Qt Quick e composizione grafica nel QSGRenderThread hardware; nessun rendering software imposto al kiosk |
| NPU | Nessun nuovo task assegnato: i costi misurati di copie, JSON, binding, SQLite e layout non sono inferenza neurale trasferibile. Nessun modello/beneficio completo qualificato giustifica un caricamento artificiale |
| RAM/SD | Cache derivate per revisioni e richieste, reader persistente, niente MemoryMax o quota artificiale; scritture e ACK durevoli conservati, intero stato utente salvato prima dell’installazione |

Python/PySide6 + QML resta la scelta applicativa. La board usa Python 3.13.5, Qt 6.8.2, PySide6 6.8.2.1; il PC di verifica Python 3.12.13 sullo stesso Qt. Non si sostituiscono kernel, Qt o una parte del driver vendor durante un’ottimizzazione di codice. I dettagli su istruzioni, toolchain, driver e alternative sono nello [studio hardware](v093-hardware-and-game-performance-evidence.md) e nell’[analisi generale](v093-systemwide-analysis.md). Il contatore GPU osservato restituiva valori impossibili: nessuna percentuale di utilizzo GPU è ricavata da quel contatore.

## Sport e proprietà dei dati

`sport.py` mantiene un albero derivato di sola lettura interno. Le soglie comprendono inizio/fine della finestra Live, età 0/90 secondi, inclusività degli estremi, rimozione delle programmate troppo vecchie, cambio stagione e ritorno dell'orologio. Il getter ricalcola lo stato esterno a ogni lettura; un errore temporaneo non modifica né avvelena il calendario conservato.

`DashboardState.sportViewState` e Main pubblicano a QML i dati usati dalla rotta. Il record selezionato conserva eventi, statistiche e formazioni; gli altri record della stagione sono riepiloghi. Il JSON grezzo del provider resta nel backend. Il campo rawStatus trasferisce il motivo previsto da MatchData. Il test confronta il DTO selezionato prima/dopo e preserva identità, ordine, disponibilità e timestamp.

Il bridge di `sport.match.detail` richiedeva l'intero modello Sport per derivare soltanto SourceState. Ora conserva l'envelope e la presenza dei dati; `match` e `fantasy` continuano nei loro campi pubblici completi. La normalizzazione del contesto risultante è identica per active/updating/stale/offline/error/unavailable, con dati presenti e assenti. Nessuna nuova Theme API o versione Apple è richiesta: palette, font, icone, layout e motion del bundle non cambiano.

Il passaggio Python→JavaScript riusa inoltre quattro liste già convertite. Python conserva una coppia lista posseduta/testo JSON per ciascuno dei quattro campi; il Main conserva quattro coppie testo/array JavaScript e decodifica soltanto un testo diverso. Non si ricostruisce la stagione in QVariant a ogni segnale di busy. Il campo di trasporto privato viene rimosso prima di consegnare il modello agli adattatori pubblici.

Il contenitore, lo stato della fonte e i timestamp vengono ripubblicati normalmente; solo le liste derivate sono codificate. Una nuova fonte, il dettaglio selezionato o la soppressione Live invalidano le liste per identità. Una rappresentazione non JSON mantiene il precedente percorso QVariant senza perdere valori. Il Main congela gli array decodificati e ne possiede il ciclo di vita. Nessun QJSValue persistente attraversa il confine Python/QML.

La precedente variante con QJSEngine.evaluate aveva latenze favorevoli ma una crescita RAM eccessiva: circa 1 GB dopo 140 casi nativi, e 344 MB dopo trenta ripetizioni della stessa rotta sul PC. È stata interrotta e scartata, senza installazione. La soluzione con JSON/cache QML mantiene circa **218–219 MB dal decimo al trentesimo giro** dello stesso test PC, dieci contesti/lease e heap Python circa 6,3 MB. GC/trim diagnostici restano confinati al processo privato; nessun trim periodico viene aggiunto alla dashboard. La prova sull’intero corpus e l’osservazione prolungata restano separate da questo confronto mirato.

I test verificano uguaglianza dei valori, Unicode/virgolette, riuso, cambio revisione, aggiornamento di stato/timestamp e fallback NaN; le prove sul vero Main verificano array congelati, cache di quattro campi, identità del match e coerenza del contesto anche selezionando sei partite diverse.

## Navigazione e disponibilità dei moduli

Un profilo del dettaglio Sport ha rilevato 162 letture indirette di visibleModules e altrettante ricostruzioni dell’inventario Rete nello stesso handler. `networkAvailable` e `casaAvailable` conservano ora il solo booleano di disponibilità, aggiornato dal segnale del provider **prima** dei segnali inoltrati alla UI. Non si memorizzano età o stato live. Main distacca la reference sequence Qt una volta per notifica con slice: le ricerche JavaScript non rientrano continuamente in Python.

Il test ripete 400 letture senza ricostruzioni e verifica cambi di inventario/configurazione/preferiti, aggiornamento dei moduli e ordine dei segnali. La matrice delle superfici verifica il normale aggiornamento dei binding.

## Metadati e concorrenza

`game_metadata.py` usa un processo distinto dal learner: le decodifiche pesanti non contendono il GIL della GUI. Un solo lavoro può essere in corso; richieste informative successive sono accorpate e solo il ticket corrente viene pubblicato. Una selezione nuova non mostra il dossier del pilota precedente. I comandi continuano a validare il database corrente prima di mutare lo stato o avviare una sessione.

Il reader conserva una base per data_version/circuito/obiettivo e fino a sedici dossier della base corrente. Il DTO mantiene progressi già calcolati, prove di idoneità e informazioni usate dalle impostazioni; episodi, modelli e array privati restano nel processo/database. Lo storico grezzo duplicato e inutilizzato viene rimosso dal QVariantMap della GUI; lo storico effettivamente consultabile, con dettagli, totali e provenienza, resta nel dossier. Nessun dato durevole viene cancellato.

Un nuovo commit invalida la base. Gli errori informativi hanno tentativi di recupero limitati; risultati superati non vengono applicati. Shutdown e inizializzazione QML fallita chiudono il reader; fermare il reader non può perdere un commit perché esso non scrive. Le prove verificano anche commit esterni, cambio selezione e assenza di sessioni avviate implicitamente.

## Misure da non confondere

La cache Sport reale osservata contiene 380 partite. Il getter Python passa da circa **17,3 ms a 0,058 ms di mediana**, senza chiamate di rete e conservando lo stato stale. Questo rapporto riguarda quel getter, non la velocità dell'intera dashboard.

Il primo DTO del metadata reader misurava 1,4–1,9 MB e aveva ancora costi GUI eccessivi. È stato scartato. I primi campioni compatti misuravano 70–125 KB; la lettura finale dello store reale restituisce **93–164 KB**. Progresso, dossier e classifiche sono confrontati con le letture complete. La prova finale confronta dieci letture con la proiezione completa: gap massimo del timer di osservazione 16,85 ms, ultima ricezione/pubblicazione strumentata 1,87/1,89 ms. Include confronti e serializzazione diagnostica; non è una misura di latenza della schermata. Round trip, pubblicazione e frame restano metriche distinte.

Il corpus non Gioco comprende 154 scenari/62 superfici. La matrice usa Apple giorno completo, Apple notte/Base/Functional con una visita per superficie. Le sei superfici Gioco hanno prove dedicate. I tempi di run_case comprendono setup, mutazioni di stile e pumping: non sono FPS.

La prova EGLFS usa input sintetico e il frame successivo marcato dopo la readiness. È un limite software conservativo, non la prima risposta ottica misurata con sensore. Si conservano freddo, caldo, percentili e outlier; un target non dimostrato resta aperto.

## Risposta osservata sulla board

Confronto sulla stessa Orange Pi, EGLFS/OpenGL, Apple Calm invariato, governor performance sui soli A76. Sei cicli, primo ciclo distinto dai cinque caldi, stessa stagione privata di 380 partite. La misura aggancia la coerenza del contesto nel thread GUI prima della sincronizzazione e marca il primo frame corrispondente nel thread di rendering. I callback nel thread di rendering leggono soltanto ticket primitivi protetti da lock.

| Operazione sullo stesso incontro | Mediana rc.28 | Mediana rc.1 scelta | p95 rc.28 → rc.1 |
| --- | ---: | ---: | ---: |
| Apertura dettaglio Sport | 1.353,94 ms | 105,40 ms | 1.357,18 → 115,38 ms |
| Ritorno alla lista | 161,67 ms | 56,15 ms | 202,37 → 62,80 ms |
| Scorrimento lista | 20,41 ms | 21,11 ms | 31,73 → 31,48 ms |
| Apertura lista | 115,11 ms | 83,54 ms | 158,72 → 90,91 ms |

Dettaglio −92,2%, ritorno −65,3% e apertura lista −27,4% nelle mediane osservate; lo scorrimento non dimostra un miglioramento. La rc.28 ha cinque aperture calde; la candidata dieci, da due processi distinti.

**Sei incontri diversi:** cinque aperture successive alla prima passano da mediana **1.527,10 a 271,14 ms**, p95 1.530,92→308,87 ms, circa −82,2% nella mediana. Questo caso include la nuova selezione e la sua proiezione, ed è distinto dal riaprire lo stesso incontro. Non nascondere tale differenza dietro un solo numero.

Il trasporto JSON/cache QML è isolato con ABBA sullo stesso governor: prima della modifica il dettaglio dello stesso incontro ha mediana 414,24 ms, dopo 105,40 ms; p95 415,82→115,38 ms. I precedenti 397,51 ms e la variante QJSValue rimangono tentativi intermedi. [Riepilogo e cardinalità](evidence/v093-implementation-2026-10-21/response-latency-summary.json), [raw B0](evidence/v093-implementation-2026-10-21/native-wire-final/first-response-B0/report.json), [B1](evidence/v093-implementation-2026-10-21/native-wire-final/first-response-B1/report.json), [incontri diversi](evidence/v093-implementation-2026-10-21/native-wire-final/distinct-candidate/report.json).

La prova generale con frame forzato dopo readiness resta distinta; il [riepilogo per categoria](evidence/v093-implementation-2026-10-21/performance-final-summary.json) conserva p50/p95/massimi e numerosità. Include input Sport, Casa, Rete, impostazioni, argomenti e dashboard; non è la misura del primo frame né certificazione ottica.

Tre blocchi ABBA del governor mostrano miglioramenti di mediana degli input lista pari a 12,7/18,3/17,5%. È selezionato performance sulla sola policy6, senza limitare gli altri core. Nice −5 non dà un vantaggio ripetibile: resta nice 0, affinity libera e CPUWeight invariato; helper/learner conservano nice 10 e BLAS a un thread. Stop e Start del servizio verificano anche schedutil→performance e il ripristino. Nessun overclock o SCHED_FIFO.

**I target del piano non sono tutti raggiunti.** L’apertura calda p95 ≤100 ms rimane aperta: il dettaglio misurato ha p95 circa 115 ms sullo stesso incontro e 309 ms cambiando incontro. Non sono qualificati 60 Hz costanti nell’intera matrice, p95 urgente ≤100 ms alla prima risposta o input fisico USB. I campioni restano evidenze di miglioramento e correttezza della candidata, non una promozione automatica a release stabile.

La separazione ulteriore calendario/dettaglio è stata provata ma **scartata**: sui match diversi migliora la mediana di circa 18–24% in ABBA rispetto alla cache scelta, mentre la riapertura dello stesso incontro peggiora da circa 105 a 164 ms. Il target esplorativo conservativo del 25% sul p95 non è completamente superato. Il progetto non seleziona una variante dal solo benchmark favorevole: per la consegna si ripristinano i byte della cache a quattro campi già qualificata. Il relativo tentativo, la decisione finale di rigetto e il carico privato interrotto sono conservati in `native-selected-final/`.

## Errori e confronti conservati

- I primi benchmark modificavano una fixture in posto. La nuova cache richiede una revisione pubblicata, come i worker reali: gli strumenti sono stati corretti e quei confronti non qualificano la release.
- L'oracolo Rete cercava il vecchio DashboardOverlay. Il controllo aggiornato usa l'host pubblico e contentId; l'invariante più rigorosa si applica alle quattro nuove viste metrics.
- Il vecchio check_game generale assume ancora piloti inizialmente senza policy. Ripetuto su una copia completa dei sorgenti precedenti, presenta gli stessi cinque failure e un error della candidata. I test delle ricette/rosa attuali sono separati; il fallimento storico non è convertito in un pass.
- Il vecchio check_sport_ui isolava solo le preferenze, poteva leggere configurazione/provider reali e modificava fixture in posto. Ora usa tutti gli spazi XDG privati e revisioni pubblicate. I tentativi iniziali restano nelle evidenze.

## Consegna e stato delle verifiche

- **Installata:** [ricevuta](evidence/v093-implementation-2026-10-21/installation-receipt.json), 645 hash corrispondenti alla qualifica nativa e ai gate PC/ARM, 18 file nuovi/modificati rispetto alla rc.28 e nessun file rimosso. Sono preservati i byte della libreria numerica ARM e il suo sorgente C.
- **Ripristino provato:** inversione atomica del runtime, avvio reale della rc.28, verifica di salute/preferenze/dati, quindi reinstallazione e avvio della rc.1. Il vecchio runtime è `/opt/smartpc/dashboard-before-v093-20261022-025524`; backup completo `/var/lib/smartpc-dashboard/v093-backups/20261022-025524`. La prova riguarda il runtime; il ripristino del governor è verificato separatamente.
- **Dati conservati anche dopo i boot:** tutte le 14 tabelle Gioco, cinque piloti, 1.005 righe di storico e **211 artefatti originali**; controlli SQLite integrity/foreign-key positivi, nessuna sessione running/paused. Preferenze e pin Apple esattamente uguali al prima. [Verifica finale](evidence/v093-implementation-2026-10-21/post-reboot-preservation.json).
- **Tre reboot effettivi:** boot ID distinti, GUI corrente pronta, NRestarts=0, nessun hash difforme o job sospeso, handoff riuscito e policy6 performance. `systemd-analyze time` restituisce 21,44 / 16,99 / 18,66 s; il coordinator richiede 67,33 / 56,28 / 52,78 s includendo SSH, polling e diagnostica: non sono lo stesso tempo. [Ricevuta](evidence/v093-implementation-2026-10-21/reboot-qualification.json).
- **Copertura:** 14 suite finali PC e 14 ARM, più 340 combinazioni non Gioco su quattro profili; tutte le 68 superfici in EGLFS, 336 casi in 600,5 s e undici controlli di urgente sintetico. Zero warning QML e zero tentativi di rete nel corpus. La ripetizione comprende riscaldamento e cambio stili: RSS 215→591 MB, 31 contesti finali; non dimostra assestamento per ore.
- **Eventi:** nel medesimo stress privato di 1.000 eventi il tick mediano passa da circa 20,90 a **2,47 ms** nella configurazione consegnata. È il costo di quel callback su fixture, non una riduzione globale della CPU né latenza del provider. [Domini ARM finali](evidence/v093-implementation-2026-10-21/domains-arm-final.json).
- **Gioco nella qualifica scelta:** gara cinque auto, 120 s, callback di swap circa 29,98 Hz, p95 37,52 ms, massimo 80,23 ms, nessun intervallo >100 ms. SAC con replay sintetico pieno da 32.768 transizioni: 120 s, circa 29,89 Hz, p95 swap 38,12 ms, massimo 122,55 ms e **tre intervalli swap >100 ms**; presentazione delle pose con massimo 75,82 ms e zero intervalli >100 ms. Non si nascondono gli outlier e non sono FPS ottici. PPO nominale, TD3/Tattico con replay pieno e Qualifica naturale sono conservati nella qualifica precedente sullo stesso codice Gioco/reader.

È avviata una **osservazione passiva finita di otto ore**, unità `smartpc-v093-passive-observation.service`, con campionamento al minuto di heartbeat/PID, manifest, memoria, temperatura e governor. Non genera input, richieste ai provider o learner. Il primo riscontro è sano; la ricevuta conclusiva non esiste ancora. [Stato iniziale](evidence/v093-implementation-2026-10-21/passive-observation-start.json); output sulla board `/var/lib/smartpc-dashboard/v093-proof/passive-eight-hours/`. Tale osservazione non sostituisce la sessione mista attiva di 60 minuti o la qualifica ottica.

## Gate di chiusura

Installazione, conservazione, rollback del runtime e tre avvii della candidata sono verificati dalle ricevute. La promozione stabile richiede ancora i target prestazionali non uniformemente raggiunti e le prove sostenute/fisiche. Il [riscontro finale](evidence/v093-implementation-2026-10-21/final-health.json) conferma GUI pronta, 645 hash integri, Apple Calm 1.6.3 e NRestarts=0.

La sessione mista finale di almeno 60 minuti, il seguito 8–24 ore, le transizioni fisiche HID/pannello e le prove live dei provider non possono essere sostituiti da fixture o da un servizio active. Fino alla loro chiusura, conservare il suffisso rc e indicare i gate mancanti. Non dichiarare 60 FPS fissi, consumo energetico ridotto o uso vantaggioso della NPU da queste misure.
