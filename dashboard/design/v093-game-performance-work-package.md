# v0.9.3 — pacchetto di lavoro Gioco, conservato dal primo approfondimento

**Versione conservata il 21 ottobre 2026.** Questo approfondimento riguarda soprattutto il Gioco. Priorità e sequenza dell’intero sistema sono definite dal [piano generale](v093-dashboard-performance-execution-plan.md) e dall’[analisi complessiva](v093-systemwide-analysis.md).

**Analisi preparatoria conclusa; piano pronto per l'attuazione. Implementazione, installazione e qualifica v0.9.3 non eseguite.** Riferimenti: [studio rev.2](v093-dashboard-performance-study.md), [evidenze e ripetibilità](evidence/v093-performance-study-2026-10-21/README.md). Baseline fotografata: core **0.9.0-rc.28**, manifest 642 file, Apple Calm **1.6.3**, Theme API 2.11. Le versioni effettive si ricontrollano all'inizio dell'esecuzione; non sovrascrivere modifiche sopraggiunte.

## 1. Decisioni fissate

1. La Dashboard ha precedenza sull'altro lavoro applicativo. Nessuna quota artificiale di risparmio CPU/RAM; si usano cache, preallocazione e processi quando migliorano il risultato sostenuto.
2. Si conserva Python/PySide6 + QML/Qt Quick. C/C++ è un'estensione mirata, con ABI e build ARM riproducibili. Nessuna riscrittura globale o migrazione di driver nella prima candidata.
3. CPU: controllo, I/O, dati e simulazione. GPU: rendering prioritario. NPU/compute GPU sono opzionali e devono superare il riferimento CPU nel costo completo e nella convivenza col rendering.
4. Il primo intervento è sul **percorso dei metadati Gioco nella GUI**: le sonde sulla base corrente trovano circa 143–220 ms per `_refresh`, con lettura/JSON dominanti. Non è necessario attendere un benchmark GPU per affrontare questo costo.
5. La prima ottimizzazione preserva fisica 60 Hz, decisioni AI 10 Hz dove previste, policy, ricette, RNG e salvataggi. Presentazione ordinaria verso 60 Hz; Gioco prima regolare a 30, poi variante 60 separata.
6. Apple Calm conserva aspetto e comportamento approvati. Non ridurre auto, eliminare dati utili o disattivare avvisi per superare il benchmark. Renderer invisibili possono dormire; l'acquisizione necessaria agli avvisi resta attiva.
7. Tutti i cambiamenti si misurano su payload identificati e copie private; nessun reset/training implicito della rosa reale. Un test riuscito non importa modelli o certificati nella produzione.

## 2. Ordine e dipendenze

| Ordine | Lotto | Dipende da | Esito richiesto |
| --- | --- | --- | --- |
| 0 | **F0.1 identità/strumenti + F0.2 baseline** | Inventario/studio acquisiti | Baseline nativa attribuibile e harness con percentili corretti |
| 1 | **F1.1 metadati fuori dalla GUI** | F0.1; F0.2 come confronto prima/dopo | Commit GUI breve anche con dati maturi e metadati aggiornati senza letture pesanti |
| 2 | **F1.2 query/dossier + F1.3 proiezioni** | F1.1 | Meno riletture/decodifiche, dettagli caricati su richiesta, contratti conservati |
| 3 | **F2.1 cache renderer + F2.2 buffer/checkpoint** | F0; F1 per i dati | Aperture calde e continuità preview migliori |
| 4 | **F3.1 priorità + F3.2 affinità/governor** | Baseline finale F1/F2 congelata | Configurazione sostenuta scelta da confronti distinti |
| 5 | **F4.1 presentazione 60 + F4.2 nativo/grafici/QML** | Baseline F1–F3; trigger misurato | Solo varianti vantaggiose e visivamente/numericamente equivalenti |
| 6 | **F5 acceleratori/driver condizionali** | F0–F4; quota di costo rilevante | Decisione motivata, anche negativa; non è un obbligo per rilasciare |
| 7 | **F6 qualifica e consegna** | Modifiche selezionate congelate | Stesso artefatto verificato, installato e osservato dopo reboot |

I lotti condizionali possono concludersi con **non selezionato**, riportando misura e ragione. Non lasciare il rilascio in attesa di una NPU da occupare senza un carico utile. Se cambiano file dopo un gate, ripetere i controlli interessati sull'artefatto finale.

## 3. F0 — preparazione e baseline nativa

### F0.1 · Congelare lo stato e rendere attendibili gli strumenti

- Ricontrollare manifest/versioni/hash core, tema, librerie native/grafiche, kernel, preferenze e stato Gioco. Salvare un inventario nuovo; quello dello studio non è una garanzia futura.
- Registrare stato iniziale del servizio e heartbeat con PID/start token, tema/digest e sessioni attive. Per i benchmark usare store/cache/preferenze privati. Se c'è apprendimento reale in corso, non interromperlo come effetto collaterale dello studio: la finestra esecutiva deve prevederne pausa durevole e ripresa solo con Start.
- Preparare copia coerente dei dati per la prova, con hash e versione di schema. Evitare `cp` del solo SQLite mentre è scritto; usare una snapshot consistente/backup SQLite o copia a writer fermo. Il processo di benchmark non punta mai alla directory della rosa reale.
- Aggiornare gli strumenti diagnostici: percentile nearest-rank `ceil(p*n)-1`, campioni completi, categorie freddo/caldo separate. `verify_performance_ui.py` usa una formula diversa: su tre aperture il vecchio p95 può nascondere il massimo. Conservare i grezzi e non confrontare percentili definiti in modo diverso.
- FTRACE, PSI e uclamp sono assenti nel kernel attuale. F0 usa timer monotoni, tempi CPU/thread, QML Profiler e logging Qt. Non montare tracefs o impostare uclamp aspettandosi funzioni non compilate. Eventuale perf/PMU è accessorio da verificare, non dipendenza bloccante.

**Consegna:** inventario, copia dei dati, manifest del benchmark, versione dello strumento, protocollo statistico e file di baseline. Nessun tuning o candidato nuovo prima della baseline.

### F0.2 · Misurare la catena fino al frame

Riutilizzare i runner esistenti dopo averne verificato compatibilità col menu rc.28. `verify_performance_ui.py` misura invio software con input sintetico/pumping; `check_game_fluidity_ui.py` usa finestre di event loop reale e distingue traccia pose/swap. Sono strumenti complementari: nessuno certifica da solo pannello, GPU o HID.

| Gruppo | Screening iniziale | Conferma della variante selezionata |
| --- | --- | --- |
| Home e navigazione | Tre temi; giorno/notte e motion off/reduced/normal; freddo/caldo distinti, almeno 200 azioni/categoria dove si decide sul p95 | Almeno 1.000 azioni sulle categorie critiche per valutare p99, con ordine alternato; nessun outlier scartato |
| Dati/avvisi | Fixture piccola/matura; refresh simultanei, errore/offline/ritorno; grafico nascosto/visibile e dati mancanti | Stessi snapshot e percorsi, nessuna perdita di eventi/freschezza; acquisizione reale qualificata separatamente |
| Gioco nominale | Gara 2/5; PPO/SAC/TD3/Tattico con copie mature; Apple inizialmente, poi Base/Functional | Ogni carico nominale almeno 10 min, senza tracing finale; pose, input, step rate e salvataggi |
| Snapshot/ACK | Registrare produzione scena, cattura learner, copia replay, encoding, ACK e refresh metadati | Correlare ogni picco con la fase e la revisione dei dati |

Per confronti A/B usare tre blocchi ABBA di segmenti da 120 s sugli scenari critici, con warmup dichiarato. Il tempo di misura è noto; preparazione e diagnosi non hanno una stima promettibile prima di eseguirle. Non moltiplicare subito tutte le opzioni: selezionare col profilo, poi confermare sul carico completo.

**Finestra EGLFS:** il display è esclusivo. Salvare stato iniziale, fermare il kiosk soltanto nella fase di prova autorizzata, avviare il runner isolato e ripristinare il servizio in un `finally` anche in caso di errore. Al ritorno verificare PID, heartbeat, tema e preferenze. Non far girare due proprietari KMS concorrenti. La sessione di studio non ha eseguito questa interruzione.

## 4. F1 — eliminare i blocchi del percorso CPU/GUI

### F1.1 · Reader persistente e proiezioni leggere dei metadati Gioco — priorità P0

**File:** `game.py`, `game_store.py`, `game_dossier.py`; nuovo modulo privato per lettura/proiezione se necessario. Chiamanti da coprire: costruzione del servizio, ready/ACK saved/qualification/finished, selezione pilota e apertura dossier.

**Problema verificato:** `GameStore.drivers()` decodifica curricula ampi; `_refresh()` legge storico, classifica e dossier in modo sincrono. Nei dati attuali ci sono quattro curricula da circa 0,5–1,1 MB e 110 eventi di valutazione per circa 5,3 MB complessivi. Il profilo del pilota 2 mostra 212 `json.loads`, circa 175 ms cumulativi dei 235 ms profilati. Questi sono tempi del percorso headless sui metadati attuali, non intervalli ottici.

**Implementazione scelta:** preparare metadati/proiezioni in un processo reader persistente, senza simulazione o training. SQLite letto con connessione propria; nessun QObject condiviso tra processi. Il reader restituisce soltanto elenco piloti/fatti verificati, riepilogo della rotta, progressi e pagina di dettagli richiesti. Non spedire alla GUI l'intero curriculum, policy o replay per farli decodificare dopo l'IPC. Thread generico e trasferimento di megabyte con pickle non risolvono automaticamente la contesa GIL.

**Cache e ordine:** connessione reader persistente e invalidazione da commit/`PRAGMA data_version` con semantica verificata per quella connessione; revisione pubblicata dal reader, epoch della sessione e ticket della richiesta. All'inizio di ogni lettura usare una snapshot consistente, terminandola prima del prossimo refresh per vedere commit successivi. Scartare risposte superate per rotta/pilota/epoch; un solo lavoro pendente sostituibile per richieste informative. Comandi e ACK restano sul canale affidabile.

**Comportamento:** conservare l'ultimo stato completo mentre si prepara il nuovo, con stato di aggiornamento esplicito dove necessario. L'ACK «Salvato» continua a dipendere dal writer durevole; la disponibilità del nuovo dossier è una transazione successiva, non una falsa conferma del checkpoint. Gli aggiornamenti arrivano senza riaprire la vista. Nessuna ripresa o preparazione neurale all'apertura della pagina.

**Gate:** commit del risultato GUI p95 ≤4 ms/p99 ≤8 ms come budget di lavoro del callback; nessuna lettura/decodifica ampia nel thread GUI. Latency ACK→metadati e tempo totale reader misurati separatamente, così spostare il problema non lo nasconde. Copertura ticket superato, commit durante lettura, cambio pilota, errore reader, stop e uscita; contenuti uguali al riferimento sincrono per la stessa snapshot.

### F1.2 · Query, aggregati e dossier su richiesta — priorità P0

**File:** `game_store.py`, `game_dossier.py`, nuovo reader.

1. Filtrare modo/stato/pilota/contesto in SQL dove il dato esiste in colonna. `sessions()` oggi legge e decodifica tutto prima del filtro: non propagare questo schema nel nuovo reader.
2. Separare elenco/summary da dettagli; paginare eventi e sessioni con chiave stabile, conservando accesso all'intero storico. Nessuna cancellazione di esperienze o risultati per ridurre il costo.
3. Riutilizzare nella stessa revisione le letture necessarie a lista, classifica, ore e dossier. Non calcolare totali passando ogni volta per tutti i payload completi. Cache degli aggregati invalidata su inserimento/aggiornamento/reset e cambio contesto.
4. Valutare indici dopo `EXPLAIN QUERY PLAN` delle query finali. Un indice non elimina il costo di decodificare megabyte inutili; prima ridurre i dati necessari. Eventuali nuovi indici/cache persistenti hanno versione e rollback e non cambiano il significato dei record.

**Gate:** stessi risultati su DB vuoto, corrente e cresciuto; prima/ultima pagina, pareggi d'ordine, inserimento mentre si pagina, altri circuiti/obiettivi, reset e sessioni interrotte. Screening 0/100/1.000 eventi e sessioni, senza peggiorare il caso corrente; riportare righe/byte letti e CPU. Nessun limite nascosto alla consultabilità.

### F1.3 · Progressi e commit scene — priorità P1, con due ambiti distinti

**Progressi:** `game.py:_progress` chiama `exercise()` cinque volte per valutazione. Calcolare una volta il risultato per prova e conservarne la proiezione per revisione. I limiti attuali sono 20 valutazioni residuali/40 nel percorso Academy: non motivare il refactor con uno storico corrente illimitato. Lasciare pienamente corretti promozioni, confronto, dati mancanti e cambio policy.

**Scene:** misurare byte e campi dei veri pacchetti, poi ridurre al solo necessario per la rotta attiva. L'esperimento 0,26→3,65 ms aggiunge 100 righe sintetiche: dimostra sensibilità al payload, non che tali righe esistano in produzione. Se il commit effettivo domina, progettare un percorso interno con ownership immutabile/copia singola o buffer numerici; validazione pubblica, commit atomico e identità di contesto restano obbligatori. Non togliere le copie senza protezione dall'alias del chiamante.

**Gate:** equivalenza degli snapshot/progressi, nessun lavoro metadati a ogni posa, payload massimo esplicito e costo commit misurato. Corruzione, mutazione dopo invio e vecchia epoch non devono alterare l'ultimo stato valido. Se il contributo scene è piccolo, mantenere il trasporto attuale e chiudere il ramo come non necessario.

## 5. F2 — sfruttare RAM e separare i costi dei salvataggi

### F2.1 · Cache e precaricamento mirati

**File:** `components/ViewHost.qml`, `Main.qml`, `PublicContextAdapter.qml`, `theme_api.py`, componenti Apple interessati.

Audit puntuale delle istanze: il supporto a `retainedLoaders` esiste, ma `cacheLimit` di default è **0** e l'audit non trova assegnazioni letterali `cacheLimit:` in Main. Non dichiarare già attiva una cache capiente senza verificare il valore dell'istanza. Misurare prima hit/miss e creazioni.

Prima variante: riuso dei renderer recentemente visitati dello stesso tema/revisione e prefetch della sola rotta probabile, eseguito fuori dalle finestre di input/urgente. Provare capacità 2/4/8 per host pertinente, non creare 68 superfici per saturare RAM. Incrementare oltre soltanto se hit rate/aperture lo giustificano. Per i renderer nascosti congelare binding/animazioni/letture; al ritorno pubblicare la revisione corrente prima di esporli.

Invalidazione obbligatoria per generazione del lifecycle, revisione/digest tema, registry/presentazione, compatibilità viewport e contratti. Nessun riuso di una revisione in quarantena. Provare richieste urgenti durante prefetch, cambio tema, annullamento e fallback. Conservare il precedente comportamento di focus/motion e il numero di oggetti vivi atteso dopo il rilascio.

**Gate:** aperture calde target p95 ≤100 ms; nessuna regressione delle fredde fuori dalla variabilità osservata; letture/pitture dei grafici invisibili restano zero; RAM può crescere per cache dichiarate, poi deve assestarsi sul ciclo ripetuto.

### F2.2 · Snapshot learner/replay e writer

**File:** `game_worker.py`, `game_direct_trainer.py`, `game_residual_learning.py`, `game_checkpoint_writer.py`.

Il writer è già un processo separato. Le sonde ARM su replay sintetico pieno trovano cattura learner circa 8,19 ms, copia preallocata circa 6,93 ms, encoding circa 2,77 s. Le fasi sono separate e i campioni non costituiscono una latenza unica di salvataggio; manca ancora la misura dell'intero checkpoint attuale maturo.

Prima tracciare cattura array→copia sigillata→IPC→encoding→fsync/commit→ACK, includendo copie della policy, optimizer, curriculum e prove. Se la cattura interrompe preview/fisica oltre il budget, usare snapshot numerici posseduti e buffer doppi/versionati; conversione liste/JSON nel writer. Non passare array mutabili mentre il learner continua a scriverli. Un solo checkpoint pendente, backpressure e gestione errore/chiusura; niente accumulo infinito o fsync eliminato.

**Gate:** ripresa esatta di RNG/pesi/replay/ottimizzatori, checkpoint coerente sotto scrittura concorrente, fallimento writer senza ACK positivo, pausa che attende persistenza effettiva. La scena deve restare regolare durante salvataggi nominali; il target è il percorso interattivo, non nascondere una coda crescente.

## 6. F3 — precedenza e hardware dedicato

Confrontare sulla stessa candidata F1/F2, **una variabile alla volta**:

| Esperimento | Riferimento → candidati | Verifica |
| --- | --- | --- |
| Priorità | GUI nice 0 → −5; learner resta esplicitamente 10 | Nice effettiva di GUI, render, helper e figli dopo spawn/riapertura; contesa e input |
| Peso servizio | Default → `CPUWeight=1000` | systemd abilita automaticamente il controller richiesto; verificare `cpu.weight` e gerarchia. Non scrivere manualmente `cgroup.subtree_control` |
| Posizionamento | Scheduler libero → GUI/render su maschera 6–7; learner libero oppure maschera separata | Non ereditare per errore 6–7 a tutti i figli; verificare TID, throughput e code, senza presumere che il pinning vinca |
| CPUFreq | schedutil → performance sul cluster veloce; solo poi entrambi | Clock/cooling/temperature e frame dopo riscaldamento |
| GPU devfreq | simple_ondemand → performance soltanto se supportato e utile | Contatori attuali discordanti: misurare tempi render, non una percentuale PVR fuori dominio |

`Nice=-5` o `CPUWeight=1000` sono candidati da selezionare, non valori magici. Sul PC dedicato il peso esterno può non produrre benefici. Se più varianti passano con differenze entro rumore, mantenere la più semplice. Niente quote CPU/RAM di risparmio, niente RT/overclock/disattivazione termica come scorciatoia.

**Rollback:** salvare unità/drop-in, governor e maschere originali; ripristinarli e verificare anche dopo riavvio. Non modificare l'intera `system.slice` per un beneficio del solo servizio. Test sostenuto almeno 60 min sulla combinazione scelta, con temperatura/cooling e clock associati alle latenze.

## 7. F4/F5 — rendering, nativo e acceleratori

### F4.1 · Presentazione a 60 Hz

Dopo aver tolto i blocchi GUI, confrontare presenter monotono attuale a 30 con una variante visuale a 60, mantenendo fisica/AI invariati. Usare campioni monotoni e interpolazione coerente di pose/camera/sensori, senza extrapolazioni illimitate. Misurare latenza introdotta dal buffer e pose distinte presentate. La vecchia variante FrameAnimation non viene promossa senza nuovo A/B: i risultati storici non la favorivano.

**Gate 30 nominale:** p95 pose ≤36,7 ms, p99 ≤50 ms, nessun intervallo >100 ms nei segmenti stazionari. **Gate 60 nominale:** p95 ≤18,5 ms, p99 ≤25 ms, nessun intervallo >50 ms; conteggio deadline mancate e conferma pannello separata. Non dichiarare «60 fissi» da questi soli percentili. Un caricamento esplicito resta categoria distinta, non si scarta uno scatto imprevisto chiamandolo caricamento.

### F4.2 · Nativo/NEON e grafici/QML — attivazione per costo misurato

- Kernel numerici: baseline C corrente `-O3 -ffp-contract=off` contro algoritmo/batch migliorati, tuning A76/A55 e NEON dove utile. Stessi ingressi/risultati, report vettorizzazione e architettura. Nessun fast-math o riduzione FP che cambi silenziosamente contatti/policy.
- Grafici Apple: conservare Canvas invisibile senza lavoro. Se il grafico visibile pesa, prima riusare proiezioni per pixel con min/max/buchi; poi prototipo QSGGeometry/Shape. QQuickPaintedItem 6.8 non equivale automaticamente a pittura GPU. Esigere parità visuale giorno/notte/scale/dati mancanti.
- QML compilato: prototipo su modulo stabile tramite build Qt, con confronto freddo/caldo e compatibilità del tema dinamico. Non rendere obbligatorio qmlsc commerciale; inventariare dipendenze dev soltanto per il ramo selezionato.

**Trigger:** il pezzo deve comparire nel percorso critico/negli scatti, oppure rappresentare una quota significativa del tempo CPU misurato. Se pesa meno del 10% del tratto e non causa code, non anticiparlo ai blocchi già verificati. Il 10% è una priorità di lavoro, non una regola che nasconde un picco raro attribuito.

### F5 · GPU compute/NPU/driver — rami condizionali

| Ramo | Prima di iniziare | Promozione |
| --- | --- | --- |
| OpenCL sensori | Profilo indica geometria/sensori rilevanti dopo CPU native/batch; precisione definita | Tempo completo inferiore alla CPU nativa veloce, nessuna regressione del rendering; buffer/scene coerenti |
| NPU reti attuali | Forward attuale pesa abbastanza; operatori e toolchain realmente disponibili | Stessa rete/policy/precisione qualificata, prima esecuzione e caldo inclusi, qualità guida e costo aggiornamento versione documentati |
| Driver/Qt/Vulkan | Profilo o bug attribuito al driver rende utile il confronto; immagine alternativa avviabile | Pacchetto BSP/firmware/userspace coerente, display e API richieste verificati, vantaggio sostenuto e rollback su supporto precedente |

Nessun backend GPU/NPU di training viene dato per disponibile. Un ramo non vantaggioso si chiude con una ricevuta negativa e non ritarda la candidata. Migrazione driver/kernel su clone SD, senza sostituire singole librerie EGL sulla produzione. Non abilitare acceleratori a scopo dimostrativo.

## 8. F6 — validazione, installazione e prova finale

### F6.1 · Congelamento e regressioni

Identificare codice, bundle e binari nativi finali; decidere versioni dai cambiamenti effettivi. Core previsto **0.9.3** alla promozione; prerelease con suffisso rc soltanto quando esiste la candidata. Apple Calm cambia versione soltanto se cambia il bundle; Theme API cambia soltanto se cambia il contratto pubblico. Test interessati a dati/scene/read model, lifecycle temi, input/urgenti e checkpoint, con confronto visuale Base/Functional/Apple 960×640.

Rigenerare SDK/fixture/kit solo se il contratto cambia; mantenere compatibilità delle presentazioni. Un test che cerca nomi/schema vecchi va adeguato a un oracolo di prodotto, non aggirato per ottenere verde. Tutte le cinque auto previste in Gara devono restare visibili e tutte le cinque identità conservate.

### F6.2 · Stesso artefatto, carico lungo e misure fisiche

Eseguire i sei carichi Gioco nominali (Gara2/Gara5/PPO/SAC/TD3/Tattico) con Apple per almeno 10 min ciascuno; navigazione e scenari informativi su tre temi. Sessione mista finale almeno 60 min senza tracing; seguito **8–24 h** sulla stessa revisione. Snapshot/checkpoint maturi, refresh e avvisi devono comparire nella prova, non soltanto una scena ferma.

Registrare memoria/oggetti/fault/swap, termica/cooling/clock, code e durabilità. Nessun obbligo di RSS bassa; deve esserci una spiegazione della cache e un assestamento nei cicli ripetuti. CPU 100% di un core non è saturazione dell'intera board. Non promuovere percentuali PVR fuori dominio.

Per FPS e latenza fisica verificare il pannello e il tastierino con metodo ottico/HID appropriato, esponendo risoluzione temporale e incertezza. Se non disponibili, si possono chiudere i gate software, ma la ricevuta mantiene esplicitamente aperta la qualifica fisica; niente claim «60 FPS fissi». Questa verifica richiede osservazione/hardware di misura, non può essere sostituita da un'altra API software.

### F6.3 · Consegna controllata

1. Ricontrollare la produzione appena prima della consegna. Backup runtime/configurazione/dati consistente e verificato; nessuna sovrascrittura dei nuovi progressi fatti nel frattempo.
2. Costruire il pacchetto da sorgente finale e verificarlo con `scripts/package-dashboard.py build --source <staging-dashboard> --output <pacchetto>` e `verify <pacchetto>`. Sono sintassi del tool esistente: i percorsi vanno risolti nell'esecuzione, senza usare directory della rosa come output.
3. Installazione atomica/staged con rollback della release precedente e dei soli stati migrati. Conservare preferenze, archivio incidenti/quarantena, piloti, artefatti e risultati. Non azzerare dati per far passare la nuova vista.
4. Avvio: servizio active, GUI pronta col PID corrente, nessun errore QML rilevante o reset driver nuovo, preferenze/tema/dati confrontati per hash/semantica. Verificare ripresa dal checkpoint senza Start automatico.
5. Reboot attribuibile alla candidata e controllo successivo; distinguere da restart del servizio. Ripetere un ciclo input, apertura, prova/salvataggio su copia e recupero, poi pubblicare receipt finale.

**Ricevuta:** manifest/hash, versioni, test e scenari effettivi, campioni/percentili/deadline mancate, limiti, backup e rollback, prova di conservazione, salute dopo installazione/reboot e gate ancora aperti. Aggiornare il MasterPlan per versione, senza dichiarare chiuso ciò che non è stato eseguito.

## 9. Regole di selezione e arresto del ramo

Una variante deve migliorare il suo obiettivo in modo replicato oltre il rumore della baseline, preservando funzione, identità grafica e gli altri carichi. Usare almeno tre blocchi; cercare un beneficio dell'ordine del 10% per i costi ripetitivi o eliminazione ripetibile dello scatto attribuito. Controllare anche peggiori casi e differenze fra run; la sola mediana globale non promuove nulla.

Se fallisce la correttezza, ripristinare/scartare il ramo prima di misurare ancora. Se il vantaggio non è distinguibile dopo il protocollo prestabilito, mantenere la variante più semplice e registrare «beneficio non dimostrato», senza inseguire indefinitamente i campioni migliori. Se i target finali non sono raggiunti, la release rimane candidata oppure pubblica un perimetro inferiore esplicito; il MasterPlan non converte 30 in 60 per chiudere il lavoro.

**Stato pronto all'esecuzione:** nessuna decisione preliminare dell'utente è necessaria per scegliere lo stack, ordinare le priorità o definire gli esperimenti. Restano da eseguire i lotti tecnici qui descritti e la successiva qualifica, nella fase di attuazione. Questo piano non ha modificato runtime, driver, governor o piloti e non costituisce una ricevuta di installazione.
