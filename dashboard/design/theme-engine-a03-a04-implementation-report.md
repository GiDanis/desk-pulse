# Theme Engine — implementazione e collaudo A0.3 / A0.4

**Revisione 1.0 · 4 ottobre 2026 · Europe/Rome**

**Stato: implementazione consegnata e installata sulla board; accettazione completa A0 ancora aperta per prestazioni, un assestamento non misurabile e lacune semantiche dichiarate.** L'incremento sviluppa l'[analisi approvata A0.3/A0.4](theme-engine-a03-a04-implementation-analysis.md), dopo i [contratti A0.1/A0.2](theme-engine-a0-contracts-report.md). Non registra il modulo pubblico `SmartPC.ThemeApi 2.0`, non importa nuovi renderer da un bundle e non conclude la migrazione A1–A6. Il runtime provato e installato è `d643cfbbe8ec592fa3d3d0d61d5dce06d55084b7`. Manifest ed evidenze distinguono prove funzionali, misure diagnostiche e gate non raggiunti.

## 1. Risultato implementato e confini

A0.3 aggiunge osservabilità del cambio tema: richiesta, validazione, resolver/cache, risorse, staging, commit, frame Qt correlato e fine effettiva del motion. A0.4 aggiunge casi riproducibili sulla dashboard reale e controlli degli effetti. L'estetica dei temi, i dati, il dispatcher dei nove tasti e la politica delle notifiche restano di competenza dei rispettivi componenti; il tracer non marca gli eventi come letti/consegnati e non modifica deadline o selezioni.

| Blocco | Implementazione presente | Limite da conservare nella valutazione |
| --- | --- | --- |
| A0.3.0 | Prototipo Qt con ticket immutabili, thread e race | Timestamp Python, ritardo GIL non quantificato indipendentemente |
| A0.3.1 | Recorder bounded, hook Python, ownership opt-in | Budget diagnostici 1 ms / 8 MiB non chiusi |
| A0.3.2 | Observer di host, notifiche, shell/overlay legacy, scena e motion | Stato Qt campionato; nessuna certificazione universale dei pixel |
| A0.3.3 | Compatibility lane storica, trace off/on, metriche con denominatori | 1.200 cambi completati; gate di costo e latenza non raggiunti, un frame finale non misurabile; target 150/20 ms invariati |
| A0.4 | Corpus hashato, tre track, runner isolato, regressioni/fault | Esecuzione per backend/profilo distinta dal numero di file; API pubblica deferred A1 |

Le sorgenti finali sono identificate dal commit `d643cfb`: 351 file nel runtime e 352 nel pacchetto diagnostico, entrambi costruiti da checkout pulito. Tutti i 351 SHA installati coincidono. API fingerprint `30013160355ad8ccb3f7c3e39569061e6f4cd9aa64893ea2444fa8a48901cec0` e registry fingerprint `ec7c2c887519b354a748c8fad07e5c02db2a447a425e3eaec2d0f536c3e1d3d6` conservati. La documentazione finale può avere un commit successivo senza cambiare questi sorgenti.

## 2. Recorder e integrazione

[`theme_trace.py`](../theme_trace.py) è stdlib, multiproducer e protetto da lock. Usa l'orologio monotono del processo con offset di sessione; assegna sequence, thread e request ID senza serializzare JSON nel percorso cronometrato. Scope thread-local e span annidati conservano la causa anche nelle chiamate reentranti. La correlazione generation/revision non ricade sull'ultima richiesta ricevuta: una callback tardiva mantiene l'identità originale.

I limiti predefiniti sono **16.384 record, 8 MiB di payload stimato e 16 richieste aperte**. Anche riepiloghi e mappe di correlazione sono limitati. Overflow, richieste non terminate, eviction/conflitti, regressioni del clock e riepiloghi frame mancanti restano espliciti. Il risultato terminale viene conservato anche quando il buffer non può più accettare il record finale; il run diventa incompleto. Il budget del payload è una stima conservativa dei dati serializzati, non una misura dell'heap Python o della memoria grafica.

Il guard disabled precede scope e costruzione dei metadati; il servizio ordinario non costruisce il bridge e non collega observer di frame. I metadati accettano identità, revisioni, hash, conteggi e tempi primitivi bounded. Titoli/corpi delle notifiche, token completi, preferenze sensibili, credenziali e risposte dei provider non entrano nel trace. Le eccezioni esportano il tipo, non il messaggio privato.

[`theme_trace_hooks.py`](../theme_trace_hooks.py) e [`theme_service.py`](../theme_service.py) registrano le operazioni prima della validazione, i rifiuti, tutte le risoluzioni Day/Night, hit/miss/invalidation e copie della cache, acquisizione/riuso dei font e lettura degli header immagini. [`theme_core.py`](../theme_core.py) registra resolver, validazione, contrasto e hash degli asset. La registrazione TTF non misura upload dei glifi; la lettura dell'header non misura la decodifica di tutte le texture.

`candidate()` precede `candidateChanged.emit()` e `published()` precede `changed.emit()`, perché i segnali eseguono anche lavoro sincrono. Le risposte dei candidati dichiarano accepted/noCandidate/staleGeneration/unexpectedContent. La navigazione che rilancia lo staging conserva la richiesta con una nuova generation. Cancel, supersession e recovery rimangono risultati distinti dal commit del tema richiesto.

Il salvataggio segue una catena separata: apply → job queued → worker → callback `_saved`. Il worker riceve soltanto recorder e request ID privati. La callback GUI attesta persisted o failed; un'anteprima già visibile non viene presentata come preferenza già salvata.

## 3. Associazione frame e correzioni emerse

[`theme_frame_trace.py`](../theme_frame_trace.py) e [`theme_trace_bridge.py`](../theme_trace_bridge.py) implementano il protocollo:

1. La GUI campiona revisioni, identità, readiness, presenza e motion dopo le animazioni, copiando un ticket immutabile.
2. `afterSynchronizing` associa quel ticket al seriale del frame con callback diretta e soli dati copiati.
3. `frameSwapped` congela submission e timestamp; la consegna queued porta il record originale al consumer GUI.
4. Il classifier usa il ticket, senza leggere lo stato successivo del servizio per riparare una correlazione ambigua.

La revisione osservata della facade, il renderer, l'istanza e la generation sono distinti. Le sei notifiche prewarmed sono dipendenze obbligatorie anche nascoste; solo le superfici esposte attestano presenza nel frame. La preview ha un'altra istanza e non prova consegna reale. Shell e overlay sono osservati come `legacyInline`: non sono già nuovi host pubblici sostituibili. Le uscite frozen sono eccezioni dichiarate senza azioni; la coerenza stretta e il frame assestato restano metriche separate. Il fallback urgente Base non prova un frame del tema richiesto.

Il collaudo ha richiesto correzioni precise del protocollo, oltre ai test della funzione pura:

- Lo stop naturale del motion può avvenire dopo il campionamento GUI dell'ultimo frame. Il ticket può essere aggiornato soltanto nella finestra GUI ancora aperta prima del sync; un latch già sincronizzato non viene riscritto.
- La pubblicazione successiva non deve classificare come superseded una richiesta il cui frame è già sincronizzato o accodato. Il trasferimento latch → queued identity è ora atomico sotto lo stesso lock, mantenendo osservabile l'identità durante la costruzione del record. Un frame A può arrivare dopo la pubblicazione B senza diventare un frame B.
- Una cattura `grabWindow()` sincrona può attendere il render thread mentre Python trattiene il GIL. Gli screenshot funzionali sospendono esplicitamente le callback dirette, fuori dalle finestre di latenza, e riattaccano l'observer dopo la cattura. Il gap viene registrato; non vale come frame misurato.
- No-op, rifiuti e richieste cancellate non acquisiscono una finta latenza zero né un successivo frame settled attribuito alla revisione conservata. Riepiloghi incoerenti/mancanti invalidano l'accettazione.

Il prototipo [`verify_theme_frame_protocol.py`](../verify_theme_frame_protocol.py) copre A→B→A, renderer uguale/token diversi, GUI occupata, mutazione prima del consumer, viewport nascosto/riaperto e candidato cancellato. Il timestamp è **Python callback entry**: comprende possibile attesa del GIL. `nativeSignalTimestampVerified=false` e `gilDelayQuantified=false` restano dichiarati. La prova riguarda sincronizzazione e submission Qt, non tempo GPU o risposta ottica del pannello. [Contratto Qt 6.8 QQuickWindow](https://doc.qt.io/qt-6.8/qquickwindow.html), [scene graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html).

La prova terminale supplementare mantiene intatto il ticket sincronizzato. Quando Qt notifica lo stop dopo la sincronizzazione, la GUI può congelare una `MotionStopProof` solo prima della callback di submission e soltanto per la medesima attachment, capture serial ed epoch. Tutti i campi di identità, stile, readiness e geometria devono essere identici; si esclude dal confronto esclusivamente `motionRunning`. Ogni partecipante deve fornire una firma effettiva di trasformazioni, dimensioni, opacità e angoli nel viewport. Un cambio di geometria, candidato, revisione o istanza rifiuta la prova; dopo la submission non è ammessa. Il report distingue `capturedGuiState` da `guiStopBeforeSubmissionWithUnchangedVisualState`. Rimane una prova del sottoinsieme Qt osservato e dell'ordine delle callback Python, con il limite GIL dichiarato: non certifica decorazioni interne arbitrarie o timestamp nativi del pannello.

La lettura diretta `traceRunningNow()` evita un ulteriore problema riprodotto con il vero Qt: durante `runningChanged`, un binding derivato nell'host può conservare il valore precedente mentre la ricetta è già ferma. Il tracer consulta la ricetta, conservando lo stato sconosciuto come movimento attivo.

Il candidato in caricamento non invalida automaticamente il front buffer della revisione precedente. Il classifier distingue `displayedRevisionCoherent`, verificando per ogni dipendenza obbligatoria anche nascosta il renderer caricato contro quello atteso dallo stile effettivo, front readiness e revisione. `loadedRevision` può anticipare il candidato nel riuso: in questo caso la revisione dello stile live rimane l'autorità del front buffer. Il bridge usa questo esito esclusivamente per un frame finale di una richiesta già completata come `coherentSubmission`; non può dare il primo successo a una richiesta pendente o al nuovo candidato. Le prove negative comprendono renderer/revisione sbagliati, fallback e dipendenze nascoste non pronte.

## 4. Corpus A0.4 e qualità degli oracoli

Il [catalogo versionato](../fixtures/theme-runtime/catalog.json) contiene **108 requisiti canonici, 136 scenari e 16 famiglie**, con **otto profili**: Base Day/Night × Normale/Ridotto/Off e Functional Day Normale / Night Ridotto. I 28 casi supplementari comprendono incroci calcio stato×tab, MotoGP×tab applicabili e disponibilità meteo. I supplementari non aumentano il denominatore dei 108 requisiti canonici. Le combinazioni MotoGP non supportate hanno motivo `inapplicable`, senza dati F1 riciclati.

| Track | Verifica implementata | Cosa non attesta |
| --- | --- | --- |
| `contractData` | **16 vettori strutturali** dei contesti e **5 vettori semantici indipendenti** per zero/false/null/errori | QObject registrati, segnali dei modelli o nuovi binding QML |
| `legacyUi` | Main, provider reali con seed sintetici, route e vista attuale prima/dopo due cambi token | API pubblica 2 o layout arbitrari dei bundle futuri |
| `publicApiBinding` | Requisiti e expected predisposti; stato **deferredA1** | Nessun PASS, nessun modulo finto registrato |

I vettori strutturali sono associati al fingerprint canonico; non costituiscono 16 verifiche indipendenti della semantica di ogni dominio. Per il meteo, il corpus conserva payload raw e testo legacy atteso, verificando separatamente la normalizzazione. Il passaggio del valore numerico al futuro DTO senza parsing delle stringhe resta A1.

Gli scenari calcio sostituiscono la partita sintetica **per ID**, dopo avere verificato unicità, invece di aggiungere una copia accanto al seed. Main seleziona con `find()`: un duplicato avrebbe potuto usare la vecchia partita e produrre un falso PASS. Gli expected controllano anche scheduled/live/finished e `null`/zero/scoreText, prima e dopo il cambio. Questa è una correzione dell'oracolo delle fixture, non una prova nuova di punteggi dei provider live.

[`theme_fixture_support.py`](../theme_fixture_support.py) crea directory XDG/config/cache/state/store/SQLite prima dei QObject. Blocca socket e DNS prima dei provider, con controllo positivo. Il wall clock dei moduli di dominio è controllato localmente; timer Qt e monotono restano reali. Timer estranei al caso vengono fermati, worker attesi con barriere bounded, e il cleanup chiude servizi/DB, drena gli oggetti e attende i worker.

Le sonde sono poste nei servizi effettivi per select/clear/refresh e mark seen/dismiss/notified. Un QKeyEvent reale prova che la delegazione arriva alla sonda; il contatore viene azzerato dopo gli effetti di setup autorizzati. Durante il solo cambio token si confrontano navigazione/tab/stack/selezioni/scroll, draft non pertinente, ActorState, flags SQLite e deadline; gli effetti provider/transport devono restare zero. I tasti sintetici non sono pressioni fisiche sul tastierino.

La lane di regressione conserva assert con scope proprio per Dashboard/Home, notifiche, persistenza, impostazioni, Sport, squadra, Fantacalcio, Motorsport ed eventi; le 13 child/suite, incluso il fault Loading, passano sul PC e sulla board con storage isolato. Eseguire una suite non fabbrica automaticamente un PASS atomico per tutti i requisiti del suo dominio. Il fault Loading controlla il vero incubatore Qt: un controllo positivo rilascia il renderer e prova il commit; poi il watchdog di Loading deve conservare la vista precedente e rifiutare il candidato. Readiness e Loading hanno timeout distinti.

### Limiti specifici Home e scena

Gli scenari Home controllano route, host ready/visibile, geometria e invarianti durante il cambio token. Non costituiscono una matrice completa con/senza evento prossimo, cambio giorno e assenza di spazio vuoto: queste prove semantiche devono essere integrate prima di dichiarare chiuso tutto il piano Home. La regressione Dashboard/Home esistente viene inclusa nella lane isolata per aggiungere la propria prova di eventi, orologio e navigazione; la sua riesecuzione finale è passata su PC e board. Non sostituisce automaticamente i casi semantici mancanti nel corpus. Forecast parziale e combinazioni non rappresentate restano non coperte, senza ampliare implicitamente l'attribuzione.

Gli scenari scena verificano enabled, **Loader.Ready**, identità del renderer effettivamente caricato, riferimento del renderer al medesimo QObject ActorState, pose, motionMode e policy paused. Il caso canvas richiede l'istanza diagnostica corretta, registrata solo dal runner; non basta il flag del descrittore. Gli assert rafforzati passano sugli otto profili PC e negli otto replay dedicati sulla board, oltre ai replay completi EGLFS Base/Functional. Il corpus corrente non verifica ogni pixel disegnato; fault di SceneHost lento/guasto e geometrie occupiedRegions non sono esauriti. Il watchdog del ViewHost non vale come prova del Loader di SceneHost, e non certifica risorse, frame budget o formato del futuro compagno animato. I casi normal/reduced/off impostano il modo proprio dello scenario: la matrice esterna non deve essere letta come prodotto indiscriminato 136×8 di animazioni tutte differenti.

## 5. Metriche e budget mantenuti

La compatibility lane conserva Base/Functional/Personal Sample, **100 cambi**, tick 350 ms, finestre 300 ms, notifiche piccola/grande/urgente ogni dieci passi e punti screenshot storici. `legacyRequestToThemeFrameMs` rimane affiancata alla misura più rigorosa. La definizione warm della latenza storica è `swap > 6`; gli intervalli warm escludono invece il primo uso della coppia modalità/tema. Un processo nuovo è process-cold, non cache GPU/disco sicuramente vuote.

[`theme_trace_metrics.py`](../theme_trace_metrics.py) filtra `selectDraft` per non sommare lo startup al denominatore del benchmark. NoVisualChange, rejected, cancelled, superseded, failed, timeout e unobserved restano contati. Mancanza/duplicazione di first coherent o settled, latenze invalide e overflow invalidano la misura. Il percentile resta `sorted[floor((n−1)×q)]`, senza interpolazione; si riportano campioni/mediana/p95/max. Non si sommano p95 delle fasi.

Sono separati: richiesta→coherent submission, richiesta→settled frame, commit/reuse dei partecipanti host obbligatori, apply→persisted, identity/revision/rank della notifica→submission e queued delivery lag. La metrica commit/reuse non comprende automaticamente shell inline e scena: la loro readiness è attestata nel ticket. La metrica evento parte dall'identità normalizzata osservata in QML; la latenza storica dalla pubblicazione dell'evento resta distinta.

`recordingCost` misura il bookkeeping del recorder per richiesta, escludendo il lavoro applicativo dentro gli span. Non rappresenta tutto il costo di screenshot, costruzione del ticket, copie GUI o attesa del GIL. Le callback di cattura/sync/submission e i costi non attribuiti sono riportati separatamente.

**I budget diagnostici iniziali ≤1 ms p95 per richiesta e ≤8 MiB di incremento PSS sono già risultati oltre soglia nelle misure di sviluppo; non sono PASS.** Il candidato finale misura 5,508–5,828 ms p95 di bookkeeping e +16,812–17,672 MiB di picco PSS campionato nelle sei coppie. Entrambi i budget sono oltre soglia. Non si alzano le soglie per chiudere il gate. La PSS include il carico del processo; non coincide con i byte stimati del buffer, e tracemalloc non equivale alla PSS del kiosk. Il tracer rimane opt-in.

Gli obiettivi di prodotto restano **p95 cambio completo ≤150 ms** e **p95 intervalli ordinari ≤20 ms**. La misura storica no-font è **155,921 ms**, con residuo +5,921 ms. Il risultato finale va indicato per profilo/run; una metrica di coerenza diversa o un sottoinsieme di successi non cancella quel confronto. GIL non quantificato, budget diagnostici oltre soglia o prove incomplete rimangono lavori aperti.

## 6. Collaudo, risultati e installazione

| Evidenza | Esito e fonte |
| --- | --- |
| Sorgenti e distribuzione | [351 SHA runtime / 352 diagnostic, checkout pulito](<evidence/theme-a03-a04-implementation-2026-10-04/distribution/source-audit.json>); [manifest runtime](<evidence/theme-a03-a04-implementation-2026-10-04/distribution/runtime-manifest.json>) |
| PC, Qt 6.11.2 | [113 test: 112 passati, un optional skip](<evidence/theme-a03-a04-implementation-2026-10-04/local/unit-checks.json>); [136 scenari × 8 profili, contractData e 13 regressioni PASS](<evidence/theme-a03-a04-implementation-2026-10-04/local/full-matrix-regressions.json>); [100 cambi GL con tracing](<evidence/theme-a03-a04-implementation-2026-10-04/local/gl-front-trace-100.json>) |
| Board A0.4, Qt 6.8.2 / PySide 6.8.2.1 | [20 scenari calcio × 8 profili](<evidence/theme-a03-a04-implementation-2026-10-04/board/fixtures-football-offscreen-1fcb.json>), [scena × 8](<evidence/theme-a03-a04-implementation-2026-10-04/board/fixtures-scene-offscreen-1fcb.json>), [13 regressioni](<evidence/theme-a03-a04-implementation-2026-10-04/board/regressions-offscreen-1fcb.json>) e [136 × 2 profili EGLFS Base/Functional](<evidence/theme-a03-a04-implementation-2026-10-04/board/fixtures-eglfs-1fcb.json>) PASS, senza warning |
| Riuso delle prove A0.4 | Corpus/harness/provider/router invariati fra `1fcb` e `d643`; cambi limitati agli observer privati. [Revisione sorgenti](<evidence/theme-a03-a04-implementation-2026-10-04/distribution/trace-only-source-review.json>). Quattro suite UI/Avvisi/motion/recovery e tutti i test unitari rieseguiti sulla board con `d643`, log nell'archivio finale |
| Protocollo EGLFS `d643` | [Default](<evidence/theme-a03-a04-implementation-2026-10-04/board/final/protocol-unset/report.json>), [basic](<evidence/theme-a03-a04-implementation-2026-10-04/board/final/protocol-basic/report.json>), [threaded](<evidence/theme-a03-a04-implementation-2026-10-04/board/final/protocol-threaded/report.json>) verificati; default realmente threaded. Callback native/GIL non certificati |
| Controllo idle | [Off](<evidence/theme-a03-a04-implementation-2026-10-04/board/final/idle-off.json>) / [on](<evidence/theme-a03-a04-implementation-2026-10-04/board/final/idle-on.json>): zero frame in circa 10 secondi con clock Main fermato, zero warning |
| Stress e raw | [12 run / 1.200 cambi](<evidence/theme-a03-a04-implementation-2026-10-04/board/final/summary.json>); [archivio integrale: report, trace, screenshot e log](<evidence/theme-a03-a04-implementation-2026-10-04/board/final-run-raw.tar.gz>) |
| Installazione | [Distribuzione reversibile](<evidence/theme-a03-a04-implementation-2026-10-04/board/deployment.json>) e [verifica successiva](<evidence/theme-a03-a04-implementation-2026-10-04/board/post-install.json>): `active/running`, PID 158986 stabile, `NRestarts=0`, EGLFS/KMS/OpenGL, nessun warning QML, tracer disattivato |

La prima matrice board completa 136×8 rimane [evidenza storica](<evidence/theme-a03-a04-implementation-2026-10-04/board/historical-full-matrix-f018.json>): non certifica gli oracoli calcio anteriori alla correzione. I replay corretti sopra e la matrice PC la completano per i casi modificati. `contractData` resta 16 vettori strutturali e cinque vettori indipendenti, non 108 semantiche di dominio indipendenti. Tutti i `publicApiBinding` rimangono deferred A1.

La workload funzionale è passata in tutti i 12 run: 100 cambi/run, dieci avvisi/run, geometria 960×640/DPR 1, nessuna rete, warning o errore; tasti/dati sono sintetici. Nei sei run con tracing: **600 richieste, 597 coherentSubmission e tre noVisualChange; 597 prime submission coerenti e 596 assestamenti su 597 richieste eleggibili**. Cinque run diagnostici sono completi; `three-pair2-on` è incompleto e il gate complessivo non passa.

| Profilo / coppia | Trace | p95 storico ms | p95 coerente ms | p95 intervalli warm ms | Picco PSS campionato MiB | p95 recorder ms | Diagnosi completa |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| none / 1 | off | 137.417 | — | 17.790 | 121.614 | — | — |
| none / 1 | on | 132.591 | 152.739 | 27.972 | 139.286 | 5.671 | sì |
| none / 2 | off | 150.480 | — | 17.718 | 121.669 | — | — |
| none / 2 | on | 132.588 | 155.387 | 27.887 | 138.962 | 5.608 | sì |
| none / 3 | off | 146.819 | — | 17.935 | 122.216 | — | — |
| none / 3 | on | 132.471 | 156.398 | 27.984 | 139.028 | 5.508 | sì |
| three / 1 | off | 148.469 | — | 17.835 | 124.024 | — | — |
| three / 1 | on | 136.777 | 158.328 | 28.153 | 141.134 | 5.828 | sì |
| three / 2 | off | 157.106 | — | 17.801 | 124.153 | — | — |
| three / 2 | on | 138.457 | 160.628 | 27.597 | 141.337 | 5.704 | **no, 99/100 assestamenti** |
| three / 3 | off | 140.365 | — | 17.965 | 124.083 | — | — |
| three / 3 | on | 136.758 | 157.259 | 27.816 | 141.024 | 5.753 | sì |

**Residuo di assestamento:** nel run incompleto la richiesta successiva parte mentre le animazioni precedenti sono attive. L'ultima submission osservata della revisione precedente precede lo stop del banner; la nuova revisione viene pubblicata subito dopo. Non esiste una submission stabile qualificabile fra i due passaggi. [Timeline immutabile](<evidence/theme-a03-a04-implementation-2026-10-04/board/final/settlement-residual.json>): `settlementSupersededBeforeObservedSubmission`. Non equivale a un'animazione cancellata e non viene inventata una latenza zero. Il percentile degli assestamenti di quel run descrive 99 campioni; non attesta tutte le 100 richieste. Nessuna ripetizione favorevole sostituisce il run.

Gli intervalli senza tracer sono 17,718–17,965 ms p95, sotto 20 ms; con tracer sono 27,597–28,153 ms, oltre soglia. La metrica storica senza tracer supera 150 ms in due run (150,480 e 157,106 ms); la nuova coerenza strumentata è 152,739–160,628 ms. Il fatto che la metrica storica con tracer sia inferiore non prova un'accelerazione: l'observer modifica costo e ordine delle callback. Nessuna sottrazione di overhead trasforma queste misure in un PASS. Le soglie restano 150/20 ms.

Il tempo CPU nelle finestre campionate è 16,97–18,60 s off e 22,79–24,42 s on: sono secondi CPU del processo, non utilizzo percentuale o tempo GPU. I tre asset font restano al massimo tre registrazioni; questa misura non rappresenta memoria delle texture di glifi. I picchi PSS del benchmark sintetico non sono confrontabili direttamente con il kiosk live; il controllo post-installazione rileva RSS 213,242 MiB / PSS 200,482 MiB con dati/provider reali, senza attestarne una regressione rispetto a una vecchia workload differente.

Backup privato software/stato: `/var/backups/smartpc-theme-a03-a04-20261004-d643cfb`; runtime precedente: `/opt/smartpc/dashboard-a03-previous-d643cfb`. Preferenze identiche e SQLite invariato durante lo scambio; i flags degli eventi preesistenti non sono stati azzerati. I dati utente rimangono sulla board, fuori dal repository. Il package runtime omette il Canvas diagnostico e il servizio non abilita `--theme-trace-output`.

Nessuna prova offscreen certifica prestazioni EGLFS, provider live, tastierino fisico o risposta ottica. I tentativi [5b85](<evidence/theme-a03-a04-implementation-2026-10-04/board/rejected-intermediate.json>) e [1fcb](<evidence/theme-a03-a04-implementation-2026-10-04/board/rejected-intermediate-1fcb.json>) restano separati con raw e cause. L'archivio finale contiene anche il run incompleto: **implementazione consegnata, accettazione prestazionale e completa copertura A0 ancora aperte**.

## 7. Uso del tooling e passaggio ad A1

Con Python/PySide6 disponibile, le verifiche riproducibili sul checkout sono:

```bash
python3 dashboard/check_theme_trace.py
python3 dashboard/check_theme_frame_trace.py
python3 dashboard/check_theme_trace_bridge.py
python3 dashboard/check_theme_trace_metrics.py
python3 dashboard/check_theme_runtime_fixtures.py --track contractData --output /tmp/theme-contract-data.json
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python3 dashboard/check_theme_runtime_fixtures.py --track all --regressions --output /tmp/theme-runtime.json
python3 scripts/package-dashboard.py build --diagnostics --output /tmp/theme-diagnostic/dashboard
```

`--profiles` e `--select` sono sottoinsiemi diagnostici e dichiarano la copertura parziale. Il package runtime esclude i QML in `fixtures/theme-runtime/renderers/`; il package diagnostic include tali risorse e ha un manifest distinto. Non registrare i renderer di fault nel catalogo distribuito dei temi personali.

Il launcher supporta `--theme-trace-output /percorso/session.json` per una sessione diagnostica esplicita; il servizio ordinario rimane senza questo argomento. [`verify_theme_trace_board.py`](../verify_theme_trace_board.py), [`verify_theme_frame_protocol.py`](../verify_theme_frame_protocol.py) e [`verify_theme_trace_idle.py`](../verify_theme_trace_idle.py) richiedono il backend dichiarato e, per EGLFS, accesso esclusivo al display con stop/ripristino controllato del kiosk secondo il piano operativo. Non sostituire un run EGLFS con offscreen lasciando invariata l'etichetta del report.

Il prossimo blocco funzionale rimane **A1**: DTO/QObject pubblici in sola lettura, broker di azioni, adattatori, modulo QML reale e migrazione dei nuovi host, seguiti da G21 e dagli altri gate del [piano esecutivo](theme-engine-ai-execution-plan.md). L'implementazione A0.3/A0.4 e la distribuzione sono consolidate; budget, assestamento non misurabile e lacune Home/scena rimangono gate aperti prima dell'accettazione completa A0. `publicApiBinding=deferredA1` diventa un requisito obbligatorio nella vera API; non basta la presenza del corpus per avanzarlo a PASS.

## 8. Residui assegnati prima del gate completo

- **Costo diagnostico:** ridurre allocazioni/copie del ticket e bookkeeping per richiesta, conservando tutte le identità e gli esiti. Rieseguire le stesse coppie off/on; 1 ms / 8 MiB rimangono i budget. Un observer nativo può essere valutato sulla base del costo misurato e del GIL, senza cambiare lo stack dell'engine o concedere ai temi plugin nativi.
- **Latenza rigorosa:** distinguere la misura storica dal frame che soddisfa tutte le dipendenze. Non sottrarre un p95 diagnostico per inventare una latenza non strumentata. Il target 150 ms resta aperto per la nuova metrica se oltre soglia; gli intervalli ordinari mantengono 20 ms.
- **Copertura semantica A0.4:** aggiungere al corpus Home con/senza evento e confini temporali, forecast parziale/ultimo completo, SceneHost lento/guasto e ulteriori ingombri. Le regressioni esistenti conservano il proprio scope; il mapping di 108 requisiti non certifica tutti i prodotti semantici possibili.
- **A1:** rendere reale il track `publicApiBinding` registrando modulo, DTO in sola lettura e modelli, broker e host. Riprodurre i vettori indipendenti di assenza/zero/false sul bridge tipizzato; non ricavare numeri dal testo legacy.
- **Sistema finale:** bundle con QML/JS/asset esterni, kit AI completo, lifecycle e gate del compagno definitivo restano nei blocchi successivi. Questa consegna non restringe linguaggi visuali, animazioni o iconografie di quei blocchi.

Questi residui impediscono di dichiarare chiusa tutta l'accettazione A0 o l'authoring completo. Non impediscono di usare recorder, corpus e runner consegnati per lo sviluppo di A1; ogni avanzamento del gate dovrà avere evidenza propria.
