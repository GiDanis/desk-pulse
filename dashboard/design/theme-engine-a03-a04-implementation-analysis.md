# Theme Engine — analisi operativa A0.3 / A0.4

**Revisione 1.0 · 4 ottobre 2026 · Europe/Rome**

**Stato: analisi pronta per lo sviluppo; tracing e nuove fixture runtime non implementati.** Prosegue la [consegna A0.1/A0.2](theme-engine-a0-contracts-report.md) e rende eseguibile il prossimo incremento del [piano A0/A1](theme-engine-a0-a1-implementation-analysis.md). Questa revisione modifica soltanto documentazione ed evidenze di analisi. Non cambia contratti canonici, fingerprint, runtime, provider, preferenze o DB; non distribuisce software né riavvia il servizio.

## 1. Risultato atteso e baseline effettiva

A0.3 deve spiegare dove passa il tempo del cambio tema e associare una richiesta alla revisione delle superfici osservate nel frame Qt. A0.4 deve rendere ripetibile la prova che il cambio conserva navigazione, dati, eventi, focus e identità del compagno. Sono strumenti per sviluppare la personalizzazione profonda; non restringono i layout creativi e non abilitano già i nuovi renderer del bundle.

Workspace di partenza `f67a5af04014b2f14562ead409eeb1d2b63309ea`; codice installato `0b41e0c35c7ba14d59c205b14e77c0338be70c04`, v0.6.6. I **197 SHA** del manifest installato coincidono con il workspace. Nuovo controllo read-only sulla board: gli stessi 197 file coincidono, servizio `active/running`, `NRestarts=0`, PID 108046, `eglfs` / `eglfs_kms`. [Audit sorgenti](evidence/theme-a03-a04-analysis-2026-10-04/source-audit.json), [controllo board](evidence/theme-a03-a04-analysis-2026-10-04/board-baseline.json). Non sono nuove prove di rendering, memoria o prestazioni.

Qt **6.8.2** / PySide **6.8.2.1** provengono dal [profilo installato già acquisito](evidence/theme-a0-contracts-2026-10-04/installed-board-profile.json); il PC di sviluppo usa Qt 6.11.2. Il device tree ora letto dichiara `sun60iw2`, `xunlong,orangepi-4-pro;arm,sun60iw2p1`. Conservare questi identificatori osservati nel profilo delle misure; non dedurre il modello commerciale o il tipo di core da un precedente nome del dispositivo. `QSG_RENDER_LOOP` non è impostato: il render loop effettivo dovrà essere rilevato nel harness, non dichiarato basic/threaded soltanto in base all'ambiente.

I contratti correnti descrivono **44 superfici, 30 route, 16 contesti, 58 DTO, 30 modelli, 32 azioni e 108 requisiti di variante**. Sono `contractOnly`: nessun modulo `SmartPC.ThemeApi 2.0` registrato. I requisiti generati non attestano fixture eseguite. API fingerprint `30013160355ad8ccb3f7c3e39569061e6f4cd9aa64893ea2444fa8a48901cec0`; registry fingerprint B0 invariato. L'analisi non li modifica.

### Riscontri che cambiano il modo di implementare

| Riscontro nel codice | Decisione operativa |
| --- | --- |
| `verify_notifications_board.frame()` verifica tema atteso e candidato assente | Conservare questa metrica storica, affiancare revisioni e identità dei partecipanti correlati al frame |
| `prepareMs` cronometra la chiamata sincrona a `selectDraft` | Non chiamarlo tempo totale dei Loader: comprende validazione, resolver e propagazione sincrona dei segnali |
| `_validate_config()` risolve Day e Night; `_resolve()` richiama `_data()`; cache hit restituisce una deepcopy | Misurare numero di chiamate/cache hit e span annidati prima di attribuire il residuo ai Loader o ottimizzare copie |
| `ViewHost` riusa un renderer quando l'ID coincide e aggiorna `loadedRevision` | Coprire token-only e stesso ID con nuovi valori; `loadedRevision` da solo non prova che lo stile osservato sia aggiornato |
| Notifiche sempre attive per prewarm; preview può duplicare il medesimo content ID con `service: null` | Identificare l'istanza, il ruolo live/preview e la generation; non contare due ack come una sola dipendenza |
| `SceneHost` ha un Loader proprio, senza protocollo prepare/reportCandidate e senza revision ack | Osservarlo come dipendenza distinta; non inventare staging della scena già implementato |
| Shell e 28 overlay non Avvisi sono QML inline/componenti fissi, spesso in `AnimatedLayer` | Observer legacy di stile/route/istanza: nessun ShellHost/OverlayHost pubblico prima di A1 |
| Uscite usano uno snapshot di stile congelato; preview/urgente cambiano l'esposizione | La coerenza deve dichiarare quali uscite congelate sono intenzionali e quali superfici sono esposte |
| `wait_ready()` controlla readiness degli host attivi, non candidato/revisione/SceneHost/frame | Conservare il helper corrente; aggiungere attese più precise, senza cambiare implicitamente tutti i test |
| `auto_refresh=False` non spegne ogni timer e una selezione può avviare comunque un worker | Isolare anche transport, timer di invecchiamento e operazioni di selezione; il solo flag non prova assenza rete |
| I 108 requisiti elencano F1/MotoGP e tab come etichette separate | Aggiungere combinazioni dominio×tab ammissibili, non dichiarare copertura completa dalla sola lista |

## 2. Confine con A1 e criteri di completamento

**A0.3 concluso** significa: recorder limitato/disattivabile, transazioni spiegabili, protocollo di associazione frame verificato sul Qt della board, confronto riproducibile con metrica storica e costo del tracing dichiarato. Un residuo oltre 150 ms può restare aperto con evidenza, causa o ipotesi circoscritta e verifica successiva assegnata. Non aumentare la soglia né dichiarare PASS usando una metrica più favorevole.

**A0.4 concluso** significa: corpus versionato, runner isolato, copertura per requisito/backend/track, baseline delle viste attuali e oracoli di stato/effetti funzionanti. I casi di binding delle nuove API vengono preparati e marcati `deferredA1`; non possono risultare passati in A0. Per chiudere A1 saranno tutti obbligatori nel modulo reale e nei nuovi host.

Questa separazione evita due errori: aspettare A1 per costruire una baseline, oppure costruire oggetti finti e presentarli come prova della API pubblica. Il mantenimento della baseline non significa che sia già verificata una futura composizione con layout arbitrario.

Non fanno parte di A0.3/A0.4: importazione ZIP/schema 2, identità digest dei bundle, supervisor/journal di attivazione, risoluzione semantica adattiva G21, riscrittura del router, scelta definitiva dei font/palette/animazioni o formato finale del compagno. Le loro prove future riutilizzeranno il corpus e il protocollo.

## 3. A0.3 — recorder e identità delle transazioni

### 3.1 Architettura scelta

Introdurre `theme_trace.py` come componente privato posseduto dall'app/harness. Python conserva transazioni e record; QML notifica passaggi discreti dell'host e del motion. Il render thread scrive soltanto timestamp e dati primitivi già copiati. Non si inviano token o snapshot completi per ogni frame e non si fa passare l'interpolazione delle animazioni da Python.

Il bootstrap in `app.py` e i harness costruiscono/iniettano il recorder soltanto quando richiesto; `DashboardState`/ThemeService ricevono un riferimento privato opzionale e Main un ingresso interno, escluso dalle API pubbliche. Inizializzare prima della prima operazione da misurare, disconnettere prima di distruggere finestra/servizi. Non aggiungere il trace al profilo B0 come capacità del tema.

Modalità: **disabled** di default, **capture** nel harness, **diagnostic** esplicita e temporanea durante sviluppo. Nessun flag del pacchetto tema può abilitarlo. In disabled non costruire record/dizionari/deepcopy né collegare observer di frame; il guard deve precedere la preparazione dei payload. Non introdurre polling, aggiornamenti periodici o rendering provocato dal tracer.

Il linguaggio principale resta Python/PySide6 + QML. Prima di aggiungere una dipendenza C++, verificare un piccolo prototipo delle connessioni Qt su 6.8.2.1: ordine dei segnali, thread, GIL, coda e costo. Se le callback dirette Python introducono blocchi o overhead oltre il budget diagnostico, confinare la parte sync/frame a un piccolo adapter nativo, mantenendo invariata l'interfaccia del recorder. Non riscrivere l'engine per risolvere un problema locale di telemetria. L'eventuale adapter introduce toolchain/header Qt compatibili, build ARM64, ABI test e packaging della libreria dell'app: verificarli prima di sceglierlo. Non distribuire plugin nativi nei temi; la libreria è dell'app e richiederebbe inclusione esplicita nel manifest, oggi non automatica per `.so`.

### 3.2 Chiavi e orologio

Ogni richiesta registra:

| Campo | Significato |
| --- | --- |
| `sessionId`, `traceRequestId` | Identità diagnostiche; non sostituiscono gli ID pubblici delle azioni A1 |
| `operation`, `origin` | selectDraft/token/palette/motion/preview/cancel/reset/apply/recovery; programmatic/Qt/HID |
| `attemptId`, `serviceGeneration` | Tentativo e staging; una navigazione può rilanciare lo stesso cambio con nuova generation |
| `fromRevision`, `targetRevision` | Revisioni appearance; il tema con stesso ID può avere token differenti |
| `hostInstanceId`, `localGeneration` | Istanza del Loader/host e suo tentativo; distinta dal content ID |
| `rendererIdentity` | Origine app, presentation ID, file/digest dal manifest, ruolo live/preview/fallback; in A2 includerà il bundle |
| `surfaceId`, `route`, `participation` | Superficie canonica, route e motivo visible/mandatory/hidden/retained-exit |
| `eventId`, `eventRevision`, `rank` | Correlazione degli Avvisi; nessun titolo/corpo o dato account nel trace |
| `frameSerial`, `thread`, `sequence` | Frame della finestra, thread produttore e ordine del record |

Usare `time.perf_counter_ns()` del processo, con offset dallo start della sessione. Anche i record QML ricevono il timestamp dal recorder; `Date.now()` serve eventualmente per dati di dominio, non per durate. Non mescolare orologi Qt/Python senza calibrazione. Se un intero passa da JavaScript, usare offset limitati e verificare la precisione; preferire timestamp assegnati in Python. Il ritardo di consegna al GUI thread si registra separatamente dall’ingresso nella callback del render thread. Anche una callback diretta Python può attendere il GIL: il suo timestamp è osservato all’ingresso, non una misura garantita dell’istante C++ di emissione. Il prototipo deve quantificare questo errore; se altera il budget o rende ambigua la correlazione, usare il timestamp dell’adapter nativo con clock unico/calibrato e qualità della misura esplicita. Non dichiarare un timestamp Python privo di ritardo per definizione.

Per la latenza da comando usare un record input distinto, prima di `activateKey`/setter, e collegare il traceRequest tramite il contesto causale privato dell’azione. La metrica storica parte da selectDraft e resta tale. Una chiamata differita deve conservare il parent esplicito; non attribuirla all’ultimo tasto ricevuto. Gli input QKeyEvent/KeyDecoder dei test sono simulazioni, non pressioni fisiche.

Digest e nomi dei file sono caricati una volta dal manifest del software, fuori dal percorso del cambio. In A0 sono identità diagnostiche: non cambiare ancora il fast path del renderer né promettere l'identità bundle A2.

Una richiesta può avere più tentativi. Un tentativo superato resta nel trace con causa e parent; nessuna callback tardiva può ereditare il request ID o la revisione corrente. Le chiamate reentranti durante i segnali richiedono una mappa generation→tentativo e span con parent, non una sola variabile globale “cambio attuale”.

### 3.3 Record limitati e risultati

Buffer iniziale proposto: **16.384 record**, limite **8 MiB di payload**, massimo **16 richieste aperte**. Sono parametri diagnostici, da confrontare con la memoria Python reale; il limite dei byte serializzati non misura l'heap. Record compatti e vocabolario degli eventi condiviso; serializzazione JSON soltanto al termine/fuori dalle finestre cronometrate. Flush in chunk chiusi se necessario, su percorso isolato e con pubblicazione atomica del report finale.

Ogni overflow registra `recordsDropped` e invalida la misura interessata. Non sovrascrivere silenziosamente la parte lenta di una richiesta. Un trace incompleto non attesta latenza o coerenza. Nessun file continuo nel servizio 24/7, nessun testo di notifica, preferenza sensibile o risposta API nel recorder.

Esiti distinti: `coherentSubmission`, `noVisualChange`, `rejected`, `superseded`, `cancelled`, `failed`, `timeout`, `recoveryFallback`, `unobservedFrame`. Ogni richiesta deve avere un esito, comprese quelle senza revisione pubblicata. Recovery usa una revisione propria: non è un'applicazione riuscita del tema richiesto.

## 4. A0.3 — punti esatti d'intervento e waterfall

| File / funzione corrente | Record/spans da aggiungere | Vincolo |
| --- | --- | --- |
| `app.py` / `state.py` / Main bootstrap | Iniezione/ownership privata, start/stop sessione e connessioni | Nessuna costruzione di recorder nel percorso ordinario disabled |
| `Main.activateKey`, Qt event filter e `keypad.KeyDecoder` nel harness | Input/action sequence e origine simulata/fisica; legame causale al setter | Stesso percorso funzionale; nessun doppio dispatch o cambiamento della mappa dei nove tasti |
| `ThemeService.selectDraft`, `setToken(s)`, `setSection`, `preview`, `cancel`, `resetDraft`, `apply`, `setVariant` | Inizio/fine richiesta, origine, configurazione identificata da hash | La chiamata va tracciata prima della validazione; un rifiuto resta osservabile |
| `ThemeService._validate_config`, `_data`, `_resolve` | Validazione Day/Night, cache hit/miss/invalidation, deepcopy, risorse | Conta tutte le invocazioni; niente doppio conteggio degli span annidati |
| `ThemeCatalog.resolve` / `contrast_issues` | Costruzione/merge, hash asset, token/contrasto/geometry/registry | Distinguere costo incluso nel resolver e lavoro fuori dal cache hit |
| `FontRegistry.acquire/update` | Nuova registrazione vs digest riusato, owners, rimozioni | Registrazione non equivale a upload del primo glifo o a VRAM misurata |
| `_resolve` / `QImageReader` | Header/dimensioni e cache | Il codice attuale non decodifica qui tutte le texture: non chiamarlo costo completo delle immagini |
| `_change`, `_clear_candidate`, `setActiveContent`, `setPreparedContents` | Candidato, lista attese, riavvio/cancel, supersession | Correlazione precedente conservata anche dopo la pulizia del candidato |
| `reportCandidate`, `_publish` | Ack accettato/scartato con motivo, publish begin/end, commit callback | `changed.emit()` può eseguire lavoro sincrono: publish end non è automaticamente il primo frame |
| `ViewHost.prepare/commit` e Loader `ready/fail` | prepare, reuse, setSource, Loader.Ready, presentationReady, commit | Istanza e generation obbligatorie; un renderer riusato non deve apparire come nuovo Loader |
| `NotificationHost.enter/settleMotion` e freeze/preview/fallback | Entrata/uscita, frozen revision, event identity, urgente Base | Non chiamare mai markSeen/markPresented/dismiss dal tracer |
| `SceneHost` Loader / binding | Renderer, stato caricamento/errore, stile osservato, actor identity | Non aggiungere staging della scena in A0; rilevarne il limite |
| `Main` / `AnimatedLayer` | Stile shell, route overlay attiva, focus/inputOwner, exit snapshot | Observer privato del QML attuale; non creare host pubblici fittizi |
| `MotionController` + `FadeRecipe` / `SlideRecipe` | play, start, stop naturale, settle, interruption, missing/error recipe | `currentRecipe` resta vivo dopo la fine: la sua esistenza non significa animazione in corso |
| `SaveJob`, `_saved` | Save begin/end, successo/errore | Persistenza separata dal preview già visibile; rollback di salvataggio è un'altra pubblicazione |

Readiness va scomposta: `Loader.Ready` significa oggetto istanziato; `presentationReady` può ritardare l'ack; commit associa il candidato allo stile live; il frame è un passaggio successivo. Il Timer corrente di ViewHost parte quando il Loader è Ready e `presentationReady` è falso: non copre un Loader fermo in Loading. La fixture deve distinguere `presentationTimeout` da `loading/harnessTimeout`. Eventuali difetti di watchdog vanno registrati e risolti con un intervento funzionale circoscritto, non nascosti dal trace o dichiarati già coperti dal timeout esistente.

Il waterfall è per richiesta, con span annidati e attese asincrone. Mostrare critical path e sovrapposizioni; **non sommare i p95 delle fasi** e non sottrarre due p95 per ottenere una durata. Le ipotesi iniziali riguardano resolver/validazione ripetuta, copie, binding sincroni, incubazione Loader, attesa sync/frame e primi usi di font/ricette. Sono ipotesi da discriminare, non cause già dimostrate dei 155,921 ms.

Ottimizzare dopo la prima misura: scegliere il tratto dominante, preservare validazione Day/Night e invalidazione asset, ripetere lo stesso carico. Nessuna rimozione di controlli o validazione differita solo per superare 150 ms.

## 5. A0.3 — protocollo di frame e coerenza

### 5.1 Associazione scelta e prototipo obbligatorio

Qt distingue `afterAnimating` sul GUI thread, sincronizzazione del scene graph e `frameSwapped` dal render thread. La documentazione 6.8 guida il protocollo; non certifica automaticamente il comportamento del bridge PySide sul nostro backend. [QQuickWindow](https://doc.qt.io/qt-6.8/qquickwindow.html#afterAnimating), [scene graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html).

1. **Snapshot GUI:** dopo le animazioni, raccogliere un ticket immutabile con revisione di stile osservata, renderer/istanza, geometria valida, esposizione e dipendenze. Includere shell/overlay legacy e scena. Un cambiamento rilevante dopo lo snapshot invalida il ticket: non attribuire alla sincronizzazione uno stato antecedente al polish.
2. **Latch sync:** in `afterSynchronizing`, connessione diretta, associare il ticket già copiato al seriale del frame. Callback minima: nessuna lettura di QML/QObject del GUI thread, nessun provider, nessun segnale che rientri nel GUI, nessuna I/O.
3. **Emissione frame:** in `frameSwapped`, callback diretta, registrare timestamp monotono e seriale sincronizzato. La consegna al consumer GUI trasporta il record congelato. Una callback queued arrivata dopo un nuovo publish non può essere classificata usando lo stato corrente.
4. **Classificazione GUI:** verificare ticket, revisioni, partecipanti e policy; produrre il primo `coherentSubmission`. Latenza della coda e record non associabili sono separati. Invalidation del scene graph svuota le associazioni, non la storia delle richieste.

Prototipo con GUI occupata, publish fra sync e callback, revisione A→B→A, font/renderer uguali con token diversi, viewport nascosto e riaperto, candidato cancellato e callback tardiva. Verificare basic e threaded dove disponibili; **EGLFS Qt 6.8.2 / PySide 6.8.2.1 è il destinatario vincolante**. Annotare thread ID/ordine ed eventuali blocchi del GIL. Una correlazione ambigua rimane `unobservedFrame`: non si ripiega sul tema corrente per produrre PASS.

Questo prova **stato Qt campionato correlato alla sincronizzazione e all'invio del frame**. Non verifica genericamente tutti i pixel di un renderer arbitrario, tempo GPU o risposta ottica. Screenshot/assert di stile e geometria completano le prove funzionali fuori dalle misure; non usare `grabWindow()` ad ogni frame o nella finestra cronometrata. Un nuovo renderer che gestisce rendering asincrono proprio dovrà rispettare il protocollo readiness A1/A2 e avere test specifici.

### 5.2 Partecipanti: non confondere active, visible e obbligatorio

- **Pagine:** la pagina attiva continua ad esistere sotto gli overlay. Stabilire l'esposizione da route, ordine dei layer e preemption, non dal solo `visible`. In caso di trasparenza conservare la pagina come esposta; usare esclusioni solo per copertura opaca provata.
- **Avvisi live:** tutte le sei istanze sono dipendenze obbligatorie di prewarm quando selezionate; solo quelle mostrate partecipano alla revisione del frame. Verificare anche commit/readiness delle nascoste, senza promettere un frame che non hanno disegnato.
- **Preview:** partecipante distinto, con identità d'istanza e `preview=true`; non attesta la consegna reale e non raddoppia l'ack per content ID del servizio.
- **Shell/overlay:** observer della facade e route attiva; per ora si dichiara `legacyInline`, non un renderer sostituibile già migrato. Gli elementi protetti sono osservabili ma non sostituibili dal tema.
- **Scena:** richiesta solo quando enabled/esposta e non sospesa; renderer disabled/suspended è `notRequired`, con motivo. Se appare mentre il cambio è pendente, aggiornare il tentativo/insieme atteso.
- **Uscite congelate:** un'uscita decorativa autorizzata può usare la vecchia revisione fino allo stop. Registrarla come `retainedExit` senza azioni. Una vecchia revisione su una superficie live attiva non è equivalente.
- **Urgente Base indipendente:** può preemptare con stile fallback durante loading. È una risposta funzionale valida, non il frame del tema richiesto. Correlare event ID/revision/rank e marcare il cambio interrotto/superato quando applicabile.

Un ack per host richiede `loadedRevision`, revisione effettiva della facade osservata e renderer/generation attesi. Stile staged e live devono risultare distinti. Per render presence verificare area/intersezione viewport e opacità effettiva non nulla; un Loader pronto ma trasparente non dimostra contenuto presentato. La soglia tecnica di presenza non equivale a leggibilità: il frame a motion terminato e la verifica sul pannello restano separati.

**Prima submission coerente:** tutti i partecipanti attivi esposti sono sulla revisione attesa, o sono eccezioni frozen/fallback dichiarate; le dipendenze obbligatorie sono committate. **Frame completamente assestato:** nessun motion finito/cancellato lascia trasformazioni/opacità obsolete; includere termine delle uscite congelate. Riportare anche la coerenza stretta senza uscite vecchie quando queste esistono. Non sommare la durata del tween al tempo di preparazione come se fossero sempre seriali.

Off non deve dipendere da un'animazione che produce frame. Per una richiesta realmente senza variazione visuale, l'esito è `noVisualChange`, provato dal confronto della configurazione/stato rilevante e degli effetti: nessun frame forzato dal tracer. Se una variazione visibile richiede un frame che non arriva, è timeout/unobserved, non no-op.

## 6. A0.3 — baseline, statistiche e budget

### 6.1 Baseline storica conservata

[Revisione dei raw report](evidence/theme-a03-a04-analysis-2026-10-04/historical-baseline-review.json), [harness corrente](../verify_notifications_board.py), [resoconto originale](theme-engine-notification-migration-report.md).

| Profilo storico · 100 cambi | Preset senza TTF nuovi | Tre TTF |
| --- | --- | --- |
| Richiesta→frame tema, p95 / max | 155,921 / 174,347 ms | 143,556 / 232,135 ms |
| “Warm” storico dopo primi 6 cambi · 94 campioni | 151,777 ms | 140,086 ms |
| Chiamata sincrona selectDraft, p95 | 116,023 ms | 104,607 ms |
| Crescita PSS fra finestre warm/late | 0,336 MiB | 0,305 MiB |

La regola della latenza warm è `swap > 6`. Gli **intervalli frame** warm usano invece `firstUseOfModeAndTheme == false`. Queste due definizioni non coincidono: l'harness introduce anche modalità nuove dopo il sesto cambio. I report restano immutati; i nuovi campi chiameranno la prima regola `legacyWarmAfterSix`, affiancando cold/warm per cache/render/font effettivi e per coppia modalità/tema. Un processo nuovo è process-cold, non una promessa di cache disco/GPU completamente svuotata.

Ripetere come compatibility lane la sequenza esatta: Base/Functional/Personal Sample, 100 cambi, tick 350 ms, finestre di azione 300 ms, notifiche ogni 10 passi piccola/grande/urgente, stessi punti screenshot e controlli di deadline/SQLite. La baseline precedente non è un confronto sperimentale isolato per il solo costo A0: per l'overhead servono anche trace off/on nello stesso build e carico.

### 6.2 Report nuovo

Per ciascun run: versione del report/trace, manifest e hash dei fixture/azioni, API/registry fingerprint, backend/render loop/Qt/PySide/device tree, geometria/DPR/scaling, clock di dominio, cache profile, font registrati, numero richieste/risultati/timeout/cancel/supersession, raw record e campioni memoria/CPU.

Metriche separate:

| Metrica | Perché serve |
| --- | --- |
| `legacyRequestToThemeFrameMs` | Comparabilità con i raw report precedenti |
| `requestToCoherentSubmissionMs` | Nuova misura di revisione dei partecipanti |
| `mandatoryParticipantsCommittedMs` | Dipendenze nascoste, prewarm urgente e scena osservata |
| `requestToMotionSettledFrameMs` | Fine effettiva/settle del movimento, senza timer stimato da durationMs |
| `requestToPersistedMs` | Apply/save del sistema; non si confonde con preview |
| `eventIdRevisionRankToSubmissionMs` | Prima risposta ad Avviso; confronto separato dalla latenza tema |
| `recordingCost`, `queuedDeliveryLag` | Costo del tracing e ritardo del consumer |

Conservare la funzione statistica storica `floor((n-1)*q)`, q=0,95, senza interpolazione, e dichiararla. Per statistiche alternative usare nomi/metodo espliciti, mai sostituzione silenziosa. Riportare campioni, mediana/p95/max e ogni esito non misurabile. p95 dei successi da solo non certifica un run con richieste perse. Per il benchmark ordinario, timeout/frame mancanti/overflow inaspettati invalidano l'accettazione; cancellazioni intenzionali appartengono alla suite di interruzione e mantengono il loro denominatore.

Tre coppie iniziali di run trace off/on, ordine alternato, **100 cambi per run**, profili no-font e tre-font; stessi input e situazione di avvio. Misurare anche idle separato. Obiettivi diagnostici iniziali da validare: p95 del lavoro di registrazione accumulato per richiesta ≤1 ms, incremento PSS diagnostico ≤8 MiB e nessun timer/frame prodotto in idle. Se jitter o quantizzazione a vsync impediscono un'attribuzione, dichiarare l'esito inconcludente e usare i costi interni, senza attribuire ogni differenza di p95 al tracing.

L'obiettivo di prodotto rimane **p95 cambio completo 150 ms** e **p95 intervalli nelle finestre ordinarie 20 ms**. La metrica più rigorosa può risultare più lenta di quella storica; ciò non è automaticamente una regressione del rendering. Il residuo no-font storico è **+5,921 ms** e resta aperto finché nuova evidenza lo chiude. Nessun limite rigido per qualsiasi tema arbitrario senza profilo/budget risorse verificati.

Non confrontare PSS di un harness con provider isolati (circa 120 MiB nel campione storico) con RSS/PSS del kiosk live a carico diverso. Registrare RSS e PSS separati; cache font registrati, glifi rasterizzati, texture e memoria condivisa sono fenomeni distinti. Nessuna “VRAM aggiuntiva” dedotta dal numero di TTF. Campionamento memoria 100 ms e punti screenshot restano fuori dagli span interni e sono identici nei confronti.

## 7. A0.4 — corpus e tre track verificabili

Il [piano delle fixture](evidence/theme-a03-a04-analysis-2026-10-04/fixture-plan.json) assegna tutti i 108 requisiti a 16 famiglie, con sorgenti e test esistenti. È un piano, non contiene scenari runtime già passati.

| Track | Cosa prova in A0.4 | Cosa non prova |
| --- | --- | --- |
| `contractData` | Snapshot validi e vettori negativi per tipi/modelli/contesti; null/zero/false; revisioni, unità, fonte | Registrazione QObject, notifiche dei modelli e binding QML nuovi |
| `legacyUi` | Main e viste Base attuali, route reali, tasti, selezioni, effetti e coerenza prima/dopo cambio | API pubblica 2 o una shell sostituibile non ancora implementata |
| `publicApiBinding` | Input/risultati attesi preparati e versionati | Esecuzione rinviata A1, nessun PASS o mock import spacciato per modulo reale |

Non derivare i risultati attesi dal medesimo adapter che si vuole testare. Conservare il payload di origine e un vettore canonico atteso revisionato; i test di schema generati sono complementari agli assert di significato. Meteo: il dato numerico originale non è ancora esposto dal runtime; la fixture preserva il payload raw e verifica separatamente il testo legacy, lasciando al binding A1 la prova che il numero arriva senza parsing delle stringhe.

Layout proposto dei file, **da implementare**:

```text
fixtures/theme-runtime/
  catalog.json                 # scenario ID, input hashes, requisiti coperti
  domains/                     # payload sintetici/normalizzati e vettori attesi
  scenarios/                   # stato iniziale, azioni, invarianti, esiti
  negative/                    # input invalidi con errore atteso
  renderers/                   # lenti/guasti/mai pronti, solo harness isolato
  README.md                    # clock, provenienza, limiti, come aggiungere casi
```

Il catalogo riferisce i requisiti generati dai contratti: non mantenere un secondo inventario canonico delle superfici. Una modifica del contratto deve mostrare casi mancanti/stale, non riallineare automaticamente gli expected. Risorse guaste e QML di fault injection non vanno registrati come estensioni del runtime distribuito. Filtrarli dal package/install; il corpus dati può essere incluso soltanto se necessario al runner installato, con hash nel manifest. In alternativa distribuire la suite diagnostica separata e identificata da manifest proprio.

Ogni scenario dichiara: ID, `covers`, clock, payload/hash, stato iniziale, route/selezione/tab/anchor, eventi e actor, sequenza di azioni con barriere causali, assert finali, effetti consentiti, profili validi, capacità richieste, fault attesi e status per track/backend. Una lista di label non è uno scenario.

## 8. A0.4 — isolamento e tempo deterministico

Ogni processo fixture possiede XDG_CONFIG/DATA/CACHE, theme store, cache provider, inbox/export e SQLite in directory temporanee create prima del primo QObject/QSettings. Usare gli stessi nomi organizzazione/app del runtime, ma directory isolate, per verificare la vera serializzazione. Il runner rifiuta root/store/DB che coincidono con il servizio. Nessun test usa credenziali o account live.

Due lane complementari:

- **Deterministica:** provider/transport finti per dati e completamenti; clock di dominio fisso e monotono controllato; assert del motore eventi e dello stato. Riproduce refresh fuori ordine, rimozioni ed errori senza dormire minuti o spostare globalmente il clock di performance.
- **Qt reale:** eventi/timer/rendering Qt e dati sintetici; monotono reale per latenza/banner. Se il tempo wall va congelato, applicare il patch ai moduli di dominio e impostare il clock QML, evitando `patch('time.time')` globale per l'intero processo. Test clock edge separati dal benchmark.

L'adapter di test fornisce barriere prima/dopo publish, prepare, ready, commit, first frame, save e completamento worker. Non basare le race su “sleep 80 ms e sperare”. I renderer di fault hanno comandi deterministici release/fail oltre alle versioni temporizzate necessarie alla compatibilità storica.

`auto_refresh=False` non basta: EventService avvia il tick di 60 s; Sport/Racing hanno age timer; SystemInfo può leggere OS/processi; Main ha clock e rotazione Sport. Fermare o governare soltanto i timer estranei al caso. Il banner timer resta reale nei test di deadline. Per device.info il timer di aggiornamento è intenzionale e ha expected separato.

Bloccare il transport prima dei costruttori/provider, non dopo l'avvio di un worker. Contare selezioni/refresh ai servizi effettivi (`SportService`, FavouriteTeam/Fantacalcio, Motorsport), non soltanto agli slot DashboardState. Un'azione user di dettaglio può selezionare; la stessa operazione durante uno swap deve avere delta zero. Fare un controllo positivo passando per Qt/HID e mostrando che il contatore intercetta un effetto reale: uno spy che non vede il dispatcher non è un oracolo valido.

Gli eventi hanno revisioni/source order e finestre issued/starts/expires controllate. Gli snapshot SQLite comprendono id, source revision, notified/dismissed level, seen, cancelled; includere payload/revision/rank quando il caso li cambia. Non pretendere uguaglianza totale del DB se un timer o providerResult autorizzato deve modificarlo. Taggare le cause e confrontare soltanto le differenze attese.

Cleanup: fermare timer, attendere/annullare worker, disconnettere observer, drenare deleteLater sul thread corretto e chiudere SQLite. Non riciclare riferimenti QObject dopo lo swap né svuotare indiscriminatamente component cache con oggetti vivi. Un crash/timeout del processo figlio produce un risultato fallito con artefatti parziali, non un caso sparito dal report.

## 9. A0.4 — oracoli di stato e scenari obbligatori

### 9.1 Invarianti causali

| Stato/effetto | Assert prima/dopo il solo cambio tema | Eccezione esplicita |
| --- | --- | --- |
| Famiglia, pagina, stack | Identità/pagine/route conservate, focus `inputOwner` | Input user o modulo rimosso dal dominio può cambiare destinazione |
| Selezione e tab | ID selezionato e tab logica conservati | ID rimosso: fallback per ID/clamp dichiarato, senza riselezione/refetch arbitrario |
| Scroll | Anchor ID + posizione interna; legacy anche indice/offset | Densità diversa può cambiare l'offset pixel, non scegliere un'altra riga in modo casuale |
| Draft | Valori funzionali non appearance invariati | Il draft appearance cambia come richiesto; Cancel torna al committed, Apply salva una volta |
| Eventi | Id/revision/rank e seen/dismiss/delivery invariati | Primo frame di banner pending può avviare la consegna una sola volta; urgente/timer possono preemptare |
| Deadline banner | Deadline monotona invariata dopo la prima consegna | Rimozione/scadenza/nuova revisione/rank seguono la policy eventi, non il cambio grafico |
| Provider | Delta zero per select/clear/refresh/network causati dallo swap | Navigazione/fonte refresh user e completamento programmato hanno effetto dichiarato |
| ActorState | Stesso QObject/app-owned actorId; pose/anchor policy coerente | sequence/locomotion possono avanzare per un vero movimento; non richiedere uguaglianza immotivata |
| Host/motion | Current e candidato limitati; generation vecchie scartate; trasformazioni pulite | Retained exit e fallback autorizzati osservati separatamente |

Separare sempre stato transitorio e persistito. Un titolo diverso o screenshot corretto non prova selezione o deadline. L'opacità del renderer non determina che un evento sia stato letto.

### 9.2 Copertura funzionale

| Famiglia | Minimo di casi e incroci |
| --- | --- |
| Home/Meteo | Con/senza evento prossimo, clock/day boundary, temperatura e pioggia zero, forecast vuoto/parziale/offline con dati precedenti, nessuna scheda vuota riservata |
| Account | Consumo zero, crediti assenti, molte finestre/scroll, warning/critical, reset; freshness verificata, nessun saldo inventato |
| Menu/Comandi/Riepilogo | First-run/manual, opzione selezionata, Oggi/Meteo, stack e input durante prepare/cancel |
| Settings | Tutte le 13 sezioni canoniche, row ID condizionali/disabled, brightness/quiet midnight, cooldown, bozza errata, preview, save fail, import/export isolati |
| Info | Tutte le quattro tab, riga oltre viewport, OS/rete/fonte assente, timer consentito solo quando visibile |
| Sport/Fantacalcio | Quattro viste overview; scheduled/live/finished×tab applicabili×via diretta/squadra; zero gol e voti zero distinti da assenza; vote provvisorio/storico, classifica vuota/parziale, worker vecchio |
| Squadra/Picker | Nessuna/preferita, calendario parziale, risultati/info/organico, filtro Serie A, lista riordinata e ID rimosso, nessuna modifica favorita dal solo tema |
| Motorsport | F1 e MotoGP×tab ammissibili di calendario/evento/sessione/classifica/live/driver; risultati/tempi/gomme/soste reali o assenti; classifiche driver/costruttori quando supportate |
| Avvisi | Sei modalità, fonti meteo/account/sport/generica/sconosciuta, ID/revision/rank, pending→frame→deadline, seen/dismiss, inbox inserimento/rimozione/anchor, dettaglio scroll, preview senza scritture |
| Shell/Scena | Pagina/overlay/notte/urgente/recovery; attore/canvas/enabled=false, occupiedRegions, normale/ridotto/off/paused, identità persistente, Loader scena lento/guasto |

Applicare tutte le sette disponibilità (`active/updating/stale/offline/error/unavailable/pending`) con combinazioni sensate di `hasData/isStale`, non un prodotto indiscriminato. Valori `0/false/null`, liste vuote e campo mancante: optional mancante è ammesso solo dal contratto; required mancante è un caso negativo, non una visualizzazione normale. `partialRefresh` conserva l'ultimo dato completo quando previsto; un completamento di selezione superata non torna corrente.

Prove Avvisi aggiuntive: titolo 100 caratteri/corpo 240, Unicode e stringhe senza spazi, lunghezze oltre envelope con truncation/scroll dichiarati, font grandi ammessi, fonte/validità leggibili, geometria massima/minima valida e fuori budget respinta. Prima consegna da opacity zero, evento rimosso durante loading, urgente durante import/preview/save/swap, modifica font a banner visibile, stale revision/rank, categoria mutata senza cancellare inbox.

Incroci: tutte le sei modalità × Day/Night × Normale/Ridotto/Off; fonti×stati e testi limite nei punti sensibili. Le tab Racing non disponibili per MotoGP devono provare fallback/indisponibilità corretti, non dati F1 riciclati. I concept UX restano guide per i futuri renderer: il corpus non impone un numero massimo di composizioni, formato icone o animazioni del compagno.

### 9.3 Matrix sostenibile, senza copertura apparente

1. Tutti i **108 requisiti atomici** almeno una volta, con scenario concreto e assert; scene.normal/reduced/off richiedono profilo coerente.
2. Tutte le **44 superfici** nei sei profili Day/Night×motion su Base; vincoli scene/route producono scenari distinti, non skip silenziosi.
3. Functional su ogni famiglia e incroci a rischio: focus, contrasto scuro, density/scroll, notifiche, freeze, draft e scene; font esistenti della board per stress senza scegliere quelli definitivi.
4. Prodotti dominio×tab/stato×route espliciti; ogni coppia valida obbligatoria. Pairwise solo per dimensioni decorative indipendenti dopo aver coperto i prodotti funzionali.
5. Fault/race in suite separata; benchmark board ristretto al carico comparabile e ai rischi nuovi. Gli screenshot coprono rappresentanti e geometrie limite, non tutte le combinazioni cronometrate.

Lo stato per requisito è `planned`, `passed`, `failed`, `notVerified`, `deferredA1`; per combinazioni incompatibili usare motivo e regola verificata. Non esiste “PASS perché il file del requisito è presente”. A1 farà fallire il gate se un `publicApiBinding` richiesto resta deferred.

## 10. A0.4 — race, fault e recupero

Sequenze obbligatorie, con barriere e outcome atteso:

- Token-only, renderer replacement e A→B→A; richieste rapide prima del ready; renderer stesso ID con nuovo font/palette; theme/style revision distinct.
- Navigazione e apertura dettaglio/menu durante prepare; cambio activeContent rilancia la generation; callback vecchia dopo commit/cancel.
- Ready ritardato, QML invalido, presentationReady mai true, errore Loader, fase Loading non conclusa; report conserva precedente/recovery e tipo di timeout.
- Urgente in ogni fase: prima richiesta, resolve terminato, loading, ready parziale, publish, motion, preview/import/save. Urgente Base non attende il candidato né un fade; focus e tasti Back/Home ancora efficaci.
- Evento rimosso/revision/rank superati prima del primo frame; un ack precedente non consegna né avvia il timer del nuovo evento. Un banner già consegnato non riparte al cambio tema/font.
- Inbox inserita prima del selected ID, selected rimosso, lista riordinata; worker di una selezione vecchia completa durante swap. Confronto per identità e causazione.
- Salvataggio fallito, cancel dopo preview, recupero catalogo guasto, scene Loader guasto; software precedente e urgent fallback usabili, nessuna perdita dei dati.
- Viewport non esposto o scene graph invalidato; callback frame ritardata/associata a ticket obsoleto, buffer pieno. Non convertire questi casi in misure favorevoli.

Errori QML intenzionali: allowlist del solo componente di fault e dello scenario relativo, con messaggio/count attesi. Tutti gli altri warning restano failure. Non sopprimere globalmente QQml warnings per far passare Broken.qml. I fault non entrano nei campioni di latenza ordinaria.

## 11. File nuovi/modificati e sequenza concreta

Nomi proposti, non comandi o file runtime già presenti:

| Incremento | File e attività | Uscita verificabile |
| --- | --- | --- |
| A0.3.0 | Micro-harness privato di finestra/observer Qt, thread ID e ticket | Qt 6.8.2 / PySide 6.8.2.1 EGLFS associa revisioni/seriali sotto race; GIL/ordine/costo chiariti prima di strumentare Main |
| A0.3.1 | `theme_trace.py`, test recorder, iniezione app/state/harness; hook `theme_service.py/theme_core.py` | Richieste/spans/esiti, no-op disabled, bounded buffer, stale generation e rifiuti osservabili |
| A0.3.2 | Observer privati ViewHost/NotificationHost/SceneHost/Main/AnimatedLayer; motion controller/recipes | Commit/reuse/font/preview/fallback/inline distinti, protocollo sync/frame e stop/settle verificati |
| A0.3.3 | `verify_theme_trace_board.py`, compatibility lane di `verify_notifications_board.py` | Legacy e nuova coerenza affiancate, cold/warm espliciti, trace off/on e cause/residui documentati |
| A0.4.0 | Corpus `fixtures/theme-runtime`, catalogo/schema scenario e clock/transport di test | Input provenance/hash e requisiti mappati; tre track senza falsi PASS |
| A0.4.1 | Nuovi helper in `theme_test_support.py` o modulo supporto distinto; `check_theme_runtime_fixtures.py` | Replay legacy reale, attese revisione/frame, contatori con controllo positivo, cleanup isolato |
| A0.4.2 | Data vectors, race/fault runner, bridge ai test dominio esistenti | 108 requisiti + prodotti funzionali coperti, invarianti/provider/eventi, publicApiBinding deferred esplicito |
| A0.4.3 | Board runner/report/packaging diagnostico e resoconto A0 | Ripetibilità Qt board, regressioni appropriate, baseline e residui per avviare A1 |

A0.4.0 può essere preparato dopo il prototipo e il recorder, prima della misura finale A0.3.3: clock/transport/oracoli aiutano anche il trace. La suite storica rimane disponibile durante lo sviluppo; non rimpiazzarla tutta con il nuovo runner in un'unica modifica.

Test recorder: clock injected, span nesting, multiproducer ordering, nessuna relabel di callback, max buffer/requests, terminal exactly once, export incompleto/errori, disabled senza record, nessun effetto lato dominio. Test fixture meaningful: expected indipendenti, ordinamento/ID/nullable e azioni reali; non snapshot automatici che replicano l'implementazione.

Riutilizzare `check_theme_api_contract/core/ui/motion/fonts/icons/persistence/recovery/authoring/authoring_ui`, `check_notifications/events`, `check_dashboard/settings/sport_ui/sport_team_ui/fantacalcio_ui/motorsport_ui`. Questi test hanno assert Base specifici utili per la baseline; il runner nuovo li completa, non li rende validi per ogni futuro layout pretendendo gli stessi objectName interni.

## 12. Protocollo di verifica e consegna

**PC:** stdlib recorder/contract/fixture checks; Qt 6.11.2 per funzionalità/offscreen, fault e race. Separare artefatti/skip per dipendenze mancanti. `qmllint` sintetico A0.2 non prova il modulo futuro e non sostituisce i test Qt.

**Board funzionale:** build candidato in staging, hash, fixture offscreen su Qt 6.8.2 / PySide 6.8.2.1, preferenze/provider/SQLite isolati. Nessuna installazione o reset del DB per eseguire fixture. Tutte le risorse diagnostiche provengono dal package/corpus hashati.

**Board EGLFS:** usare la finestra diagnostica sul display 960×640 e il percorso graphics già provato. EGLFS richiede accesso esclusivo: fermare il kiosk soltanto per la finestra di collaudo, con trap/timeout che lo riavvia anche in errore. Non avviare un secondo rendering contendente e non ripiegare silenziosamente su offscreen. Conservare preferenze e stato reale, fixture/catture in directory separata. Pressione umana sul tastierino resta una prova ergonomica distinta da QKeyEvent/KeyDecoder.

**Installazione dell'incremento:** dopo verifiche, manifest di commit pulito, backup software/stato, installazione atomica, avvio servizio EGLFS, hash/`active`/`NRestarts=0`, warning, preferenze e rollback secondo MasterPlan. Tracing disabled nel servizio ordinario. Non fare nuovo tag/rilascio automaticamente per A0; non riavviare la board soltanto per chiamare “cold” un test di processo.

Artefatti minimi: `session.json`, trace/versione e raw records, `transactions.json`, `fixture-coverage.json`, `effects.json`, report delle metriche con denominatori/metodo/overflow, warning attesi/inattesi, screenshot funzionali fuori timing, manifest e profilo Qt/hardware. Il report finale separa storico, misura fresca, inferenza, residuo e test deferred A1.

## 13. Decisioni pronte per partire

La sequenza tecnica è definita: **prototipo dell'associazione frame → recorder privato → hook degli host e motion → corpus/oracoli isolati → confronto legacy/coerente su board → consolidamento A0**. Il primo incremento implementativo è A0.3.0/A0.3.1; nessuna scelta estetica definitiva è necessaria.

Il punto che il prototipo deve risolvere è tecnico e circoscritto: affidabilità e costo delle connessioni dirette PySide sul render thread. Le altre decisioni sono fissate: clock unico, identità per istanza/generation/revisione, buffer limitato, tre track, effetti causali, incroci funzionali espliciti e soglie esistenti conservate. L'analisi non chiede di anticipare la scelta dei font né limita animazioni, icone, visualizzazioni o compagno; rende verificabile la loro futura migrazione.
