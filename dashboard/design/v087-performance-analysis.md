# SmartPC 0.8.7 — studio delle prestazioni e piano di ottimizzazione

**9 ottobre 2026 · baseline installata 0.8.6-rc.2, Apple Calm 1.6.0 · analisi, non consegna software.**

**Aggiornamento successivo:** ottimizzazioni applicate e consegnate nella 0.8.7-rc.1. Questo documento conserva i risultati dell’analisi precedente alla patch; misure native, implementazione e gate residui sono nel [report di consegna](v087-performance-implementation-report.md).

## Decisione proposta

Conservare Qt Quick/QML e Python/PySide6. Prima ottimizzare la cache dello stile, la pubblicazione dei contesti e il caricamento delle viste. Il confronto sul PC individua lavoro evitabile nel percorso comune del tema Apple Calm; non giustifica una riscrittura del prodotto. La grafica approvata, le informazioni e la navigazione rimangono vincoli del prossimo intervento.

Il problema segnalato riguarda **tutto, anche i tasti nelle liste**. Un servizio attivo e senza riavvii non dimostra che l'interfaccia sia reattiva. Le prove funzionali della 0.8.6 rimangono valide nel loro perimetro; questa analisi aggiunge una qualifica distinta delle prestazioni.

**Risultato più concreto:** la cache dello stile usa `id(style_input)` come parte della chiave. Nel test Apple, per una stessa cache, cambiano centinaia di identità del wrapper Python mentre revisione del tema e geometria rimangono uguali. Conservando quel wrapper nel solo processo sperimentale, le ricostruzioni diminuiscono fortemente e la risposta delle liste migliora. Nessuna modifica è stata installata sulla board.

## 1. Metodo, baseline e limiti

Sono stati eseguiti:

1. Letture passive della Orange Pi: servizio, memoria, temperature, frequenze e CPU dei singoli thread per circa 24 secondi, senza interferire con display o preferenze.
2. Lettura del journal disponibile e delle dimensioni delle cache Sport, senza chiamare i provider.
3. Esecuzione isolata del vero `Main.qml` con i provider del harness esistente, rete negata e 380 partite sintetiche. La cache reale Serie A contiene anch'essa 380 incontri; i contenuti restano diversi.
4. Confronto Base/Apple con motion disattivata; misure senza cProfile separate dai profili di attribuzione del lavoro.
5. Esperimento A/B esclusivamente sul PC: mantenimento del wrapper dello stile per contesto, senza cambiare i sorgenti del runtime, la Theme API o gli asset.

PC: Python 3.12.14, Qt 6.8.2, PySide6 6.8.2.1, piattaforma offscreen e renderer software. Board: Python 3.13.5, Qt 6.8.2, kiosk EGLFS. **I millisecondi del PC non sono i millisecondi della board**, né misure GPU o ottiche.

Il percorso contiene 36 cambi di vista tramite `activateKey`, 72 selezioni effettive nella lista Serie A, apertura/ritorno e cambi di famiglia preparatori. La selezione alterna giù/su, verificando che l'indice cambi: nessun comando al bordo è contato come selezione riuscita. Il harness blocca i trasporti; le esecuzioni finali hanno zero tentativi di rete e zero messaggi QML durante il percorso misurato.

La misura software termina dopo `ViewHost` pronto e un ulteriore passaggio dell'event loop. Non attende una prova ottica del focus. L'invocazione bypassa USB/evdev, quindi non esclude un problema fisico del tastierino. È una misura del costo applicativo utile a localizzare il lavoro.

I profili iniziali e quelli senza profiler hanno ruoli diversi: cProfile introduce overhead e non separa completamente QML, Qt nativo e Python. I tempi cumulativi annidati **non vanno sommati**. La documentazione Python distingue la profilazione dalla misura comparativa delle prestazioni. [Python Profilers](https://docs.python.org/3.13/library/profile.html).

Prove e strumenti: [cartella evidence](evidence/v087-performance-analysis-2026-10-09/), [sampler passivo](evidence/v087-performance-analysis-2026-10-09/passive_board_probe.py), [esperimento PC](evidence/v087-performance-analysis-2026-10-09/profile_pc.py).

## 2. Cosa mostra la board

| Osservazione | Risultato | Interpretazione consentita |
| --- | --- | --- |
| Servizio | `active/running`, `NRestarts=0` | Nessun riavvio del kiosk nella finestra; non prova la fluidità. |
| Memoria macchina, prima lettura | 5.363 MiB disponibili su 5.855 MiB; swap usata 0 | Nessun indizio di RAM esaurita in questa lettura. |
| Memoria del servizio | Circa 368 MiB; comprende supervisore e GUI | Non equivale alla sola memoria dei dati né prova assenza di crescita nel tempo. |
| RSS della GUI | Circa 303 → 300 MiB | Non cresce nella breve finestra osservata. |
| CPU GUI | 28,09% di **un core** in media; finestre da 2 s fino al 90,1% | Il lavoro CPU osservato è soprattutto sul thread principale. L'uso durante la raccolta non è stato controllato: non chiamare questa misura «idle». |
| Thread scene graph | Nessun tick CPU rilevato nel campione | Non dimostra che la GPU sia veloce o inutilizzata; non esclude attese del driver. |
| Temperatura | Circa 41–43 °C | Nessun segnale termico evidente nel campione; non è una verifica completa del throttling. |
| Governor | `schedutil`; due policy, limiti 1,794 e 2,002 GHz | La frequenza varia. Non cambiare governor/affinità prima di un confronto controllato. |
| PSI | `/proc/pressure` assente | Pressione CPU/RAM/I/O non disponibile, non pari a zero. |

Correzione metodologica: la prima raccolta identifica il `MainPID` systemd, che è il **supervisore**. È conservata come `board-passive.json` e non viene usata per attribuire CPU alla GUI. Il campione valido è [board-app-passive.json](evidence/v087-performance-analysis-2026-10-09/board-app-passive.json), PID GUI 1242, identificato tramite argv nel cgroup del servizio.

Il journal accessibile contiene **due TypeError** in `DashboardCards.qml`, righe 18–19: callback ritardati che leggono `grid.currentIndex` quando l'oggetto è già nullo. Sono successivi alle verifiche di installazione. La causa di questo difetto di lifecycle è coerente con i due `Qt.callLater` presenti nel componente; il legame con la lentezza generale non è dimostrato. Il journal è parziale per permessi/rotazione. [Estratto disponibile](evidence/v087-performance-analysis-2026-10-09/board-journal.log).

Le cache lette contengono 380 partite Serie A, 51/52 incontri nei due file club archiviati, 23 eventi F1 e 22 MotoGP. File archiviati non implicano moduli simultaneamente attivi. [Volumi e hash del runtime](evidence/v087-performance-analysis-2026-10-09/board-data-volumes.json).

La documentazione kernel descrive le policy CPU e il governor `schedutil`; la frequenza istantanea non basta a qualificare un'azione GUI. [CPU Performance Scaling](https://docs.kernel.org/admin-guide/pm/cpufreq.html).

## 3. Confronto controllato sul PC

Valori arrotondati della prima coppia finale senza cProfile. Il numero di campioni è piccolo: sono indicatori diagnostici, non una certificazione statistica della latenza.

| Stesso percorso, motion off | Base | Apple Calm | Apple, esperimento cache |
| --- | ---: | ---: | ---: |
| Cambio vista caldo, mediana (24 azioni) | 7,4 ms | 22,2 ms | 15,6 ms |
| Cambio vista caldo, p95 | 22,5 ms | 38,4 ms | 29,0 ms |
| Primo ciclo di viste, p95 (12 azioni) | 38,7 ms | 117,4 ms | 117,2 ms |
| Selezione lista, mediana (72 azioni) | 1,8 ms | 20,9 ms | 11,8 ms |
| Selezione lista, p95 | 3,6 ms | 23,7 ms | 15,6 ms |

La cache riduce la mediana della lista di circa **43% nella prima coppia**. La ripetizione serve a controllare la variabilità, non a moltiplicare i campioni artificialmente. Il primo caricamento cambia poco: resta un costo separato da affrontare.

Nella seconda coppia, la mediana della lista passa da 18,1 a 13,4 ms, circa **26% in meno**. Entrambe le coppie mostrano un beneficio, di entità variabile; non estendere il 43% a tutta la GUI o alla board.

Prove: [Base](evidence/v087-performance-analysis-2026-10-09/pc-base-timing.json), [Apple](evidence/v087-performance-analysis-2026-10-09/pc-apple-timing.json), [esperimento Apple](evidence/v087-performance-analysis-2026-10-09/pc-apple-style-experiment.json), [ripetizione Apple](evidence/v087-performance-analysis-2026-10-09/pc-apple-timing-repeat.json), [ripetizione esperimento](evidence/v087-performance-analysis-2026-10-09/pc-apple-style-experiment-repeat.json).

### 3.1 Cache dello stile: difetto riprodotto

Nel profilo Apple:

- 695 pubblicazioni/normalizzazioni di contesto;
- 653 ricostruzioni di stile su 695 lookup, circa **94% di miss**;
- 16 cache di contesto osservate;
- nella cache più variabile, **237 identità di wrapper**, con revisione 5 e viewport 960×640 invariati;
- nella cache delle viste 912×552, altri **77 identificativi**, sempre con la stessa revisione e geometria.

L'esperimento conserva una referenza al wrapper per contesto. Nella prima esecuzione senza profiler, lo stile viene ricostruito **81 volte su 689 lookup**, contro **654 su 694** della baseline senza profiler. Non sono stati modificati colori, font, immagini, coordinate o dati dei provider.

Questo A/B sostiene l'ipotesi che l'identità transitoria del wrapper impedisca il riuso della cache; non è ancora una patch pronta per il runtime. La soluzione deve avere un'identità stabile, invalidazione corretta su revisione/geometria e rilascio delle referenze quando il contesto viene distrutto. Non usare il solo indirizzo senza considerare riuso e lifecycle.

Codice interessato: `theme_api.py::normalize_legacy`, `style_key`, `_cached`. [Contatori e chiavi osservate](evidence/v087-performance-analysis-2026-10-09/pc-apple.json).

### 3.2 Molte pubblicazioni per pochi cambi reali

La baseline Apple senza profiler effettua 694 normalizzazioni contro 89 del tema Base nello stesso workload. Base utilizza anche renderer legacy: **il confronto non attribuisce la differenza a colori, icone o layout Apple**. Misura due percorsi di pubblicazione differenti.

Nel profilo Apple, `updateLegacy` occupa circa 6,11 s su 8,81 s del workload profilato, circa 69% del tempo cumulativo. All'interno si trovano normalizzazione dei DTO, completamento/validazione, copie e confronti. La ricostruzione dello stile da sola è quindi un primo intervento, non l'intero lavoro.

La lista Sport pubblica centinaia di volte `sport.fixtures` e la shell viene aggiornata spesso anche per selezioni di riga. Anche `sport.overview` viene normalizzato durante il percorso che apre l'elenco: occorre verificare quando il precedente host rimane presentato e per quanto tempo, prima di definirlo inutile.

La protezione delle viste nascoste e il batching con `Qt.callLater` esistono già in `PublicContextAdapter.qml`: conservarli e verificare i casi di host in uscita. Non aggiungere un secondo batching senza misurare.

Fonti interne: `Main.qml::publicSurfacePayload`, `PublicContextAdapter.qml::payload/refresh`, `theme_api.py::updateLegacy/update`, `theme_contexts.py::complete_snapshot/_update`. [Profilo Apple](evidence/v087-performance-analysis-2026-10-09/pc-apple.profile.txt), [profilo Base](evidence/v087-performance-analysis-2026-10-09/pc-base.profile.txt).

### 3.3 Dati: distinguere copie inutili da cache che funzionano

Nel profilo Apple, le cache della lista costruiscono partite/classifica/turni solo tre volte per categoria su 220 lookup. Il getter Sport `_data` viene chiamato quattro volte nel workload, non a ogni tasto. **Non è corretto attribuire questa riproduzione al ricalcolo delle 380 partite per ogni selezione.**

Resta un costo potenziale negli aggiornamenti del provider: `sport_core.presentation` copia il calendario; `Main.qml` mantiene proiezioni di Sport e racing nel root; `racingStates` raccoglie entrambi i servizi. Motorsport ha già una cache con scadenze temporali: non sostituirla con una cache cieca.

La cache della proiezione Network viene invece ricostruita a ogni lookup nel profilo osservato: 42/42. È un'altra candidata da investigare con confronto dei dati prima/dopo; il contatore da solo non dimostra un bug, perché la proiezione potrebbe essere cambiata.

`DashboardState._invalidate_dashboards` cancella la cache di tutti gli argomenti quando cambia uno dei domini collegati. Proporre revisioni per dominio/vista e scadenze semantiche; non sospendere la freschezza di eventi, stato offline o dati precedenti. Il riepilogo piccolo introdotto nella 0.8.6 resta utile e va conservato.

### 3.4 Primo caricamento: verifiche e filesystem

Nel profilo ci sono 14 chiamate a `ThemeService.acquireRevision`, circa 0,628 s cumulativi. Il percorso acquisisce una lease e verifica la revisione del bundle prima di proteggere le risorse; si trova nella preparazione del loader e può pesare sul thread GUI. I loader QML sono già asincroni: ciò non rende automaticamente asincrono ogni slot Python chiamato durante la preparazione.

Candidato: verificare la revisione una volta in un punto controllato, proteggere le risorse senza ripetere tutti gli hash a ogni vista e gestire worker/cache/invalidation con la stessa garanzia rispetto alla raccolta delle revisioni. **Non eliminare verifica, lock, lease o recovery** per guadagnare tempo. Il costo su SD richiede misura nativa separata.

### 3.5 Rendering e input: lavoro ancora da misurare

Il codice keypad usa letture non bloccanti e ignora release/auto-repeat. Non emerge un debounce obbligatorio da rimuovere. Rimangono da misurare evento evdev → handler QML e coda degli eventi durante refresh/cambi vista.

Testo, delegati, immagini, Canvas e transizioni possono aggiungere costo. Verificare layout testuali e ricreazione dei delegati prima di cambiare lo stile. Qt documenta costi di conversione/binding, testo, immagini e modelli; applicarli ai punti misurati. [Qt Quick Performance, 6.8](https://doc.qt.io/qt-6.8/qtquick-performance.html).

Qt Quick usa un scene graph e API grafiche native; il rendering non è un ciclo Python che disegna ogni pixel. Il thread GUI può rallentare l'interfaccia anche se il renderer è separato. La presenza di `QSGRenderThread` nel campione è coerente con questa architettura, senza qualificare il driver. [Qt Quick Scene Graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html).

Per le liste, valutare `reuseItems` dove compatibile e conservare modelli con identità stabili; i delegati riutilizzati devono azzerare lo stato locale. Non aumentare indiscriminatamente `cacheBuffer`: memoria e costo dei binding rimangono da valutare. [ListView](https://doc.qt.io/qt-6.8/qml-qtquick-listview.html).

## 4. Linguaggi e runtime: quale scelta conviene

| Scelta | Cosa può migliorare | Cosa rimane | Decisione |
| --- | --- | --- | --- |
| QML + Python/PySide6 ottimizzati | Cache, meno conversioni, aggiornamenti parziali, meno lavoro nel thread GUI | Serve disciplina nei modelli e nel lifecycle | **Prima scelta per 0.8.7.** Mantiene prodotto e temi. |
| QML + piccolo modulo C++ | Normalizzatore/modello specifico, se resta dominante dopo le correzioni | Binding superflui, loader, driver e dati troppo grandi non si risolvono automaticamente | Prototipo successivo solo con hotspot residuo misurato. |
| Backend interamente C++ | Riduce lavoro Python e attraversamenti dei binding se il disegno dei dati cambia | Riscrittura provider, cache, firme/API, scheduler, recovery e test; stessi rischi QML/rendering | Non giustificato dalle prove attuali. |
| Compilazione QML e packaging Python | Può aiutare caricamento e alcune funzioni; distribuzione più strutturata | Non corregge una chiave di cache instabile o troppe pubblicazioni | Studio separato dopo le ottimizzazioni di architettura. |

Python resta adeguato ai provider orientati a I/O. Nel CPython ordinario il GIL limita l'esecuzione parallela del codice Python CPU-bound; un thread aggiuntivo non elimina quel limite. Spostare I/O e preparazione fuori dalla GUI resta utile, mentre la pubblicazione dei QObject/modelli deve rispettare i thread Qt. I build free-threaded Python 3.13 non sono automaticamente il runtime in uso e non vengono proposti come aggiornamento rapido. [Python threading](https://docs.python.org/3.13/library/threading.html).

Qt dispone di compilazione QML a bytecode e, per le funzioni analizzabili, C++; alcune modalità `qmlsc` appartengono alle estensioni commerciali e hanno requisiti specifici. Non assumere che bundle dinamici e oggetti Python diventino interamente codice nativo cambiando un flag. [QML Script Compiler, 6.8](https://doc.qt.io/qt-6.8/qtqml-qml-script-compiler.html).

`pyside6-deploy` usa Nuitka e produce un eseguibile collegato a libpython. Questo descrive il packaging, non una garanzia di velocità del nostro workload. [Deploy Qt for Python, 6.8](https://doc.qt.io/qtforpython-6.8/deployment/deployment-pyside6-deploy.html).

Non introdurre una nuova GUI web o riscrivere il tema per questa minor release: nessuna prova raccolta ne dimostra un beneficio sufficiente a compensare migrazione e nuove regressioni. Questa è una decisione di progetto, non un confronto prestazionale universale tra framework.

## 5. Piano 0.8.7, in ordine di beneficio e rischio

| Fase | Intervento | Verifica richiesta |
| --- | --- | --- |
| P0 · baseline nativa | Misurare input, handler, pubblicazione e primo frame coerente su board, con tracing acceso/spento separati | Almeno tre passaggi freddi/caldi e liste con selezioni effettive; conservare tutti gli outlier. |
| P1 · cache dello stile | Identità stabile per contesto, revisione e geometria; rilascio esplicito al teardown | La selezione in una lista stabile non ricostruisce lo stile; palette, textScale, motion, recovery e cambio tema invalidano correttamente. |
| P2 · pubblicazione selettiva | Separare selezione/navigation dai dati immutabili; ridurre dipendenze della shell e campi comuni non pertinenti | Una selezione non rinormalizza il modello immutato; payload incompleti/malformati conservano l'ultimo stato completo; nessuna perdita di informazioni. |
| P3 · apertura viste e lifecycle | Ridurre verifiche ripetute del bundle preservando lease/lock; correggere i callback su oggetti distrutti | Aperture fredde più rapide; cancellazione, vecchi temi, raccolta revisioni e fallback sicuri; nessun TypeError dopo navigazione rapida. |
| P4 · aggiornamenti backend | Cache Sport e Network per revisione/qualità/scadenza; invalidazione dashboard per dominio | Un aggiornamento Rete non ricostruisce Sport; scadenze live/offline/stale e tutte le partite restano corrette. |
| P5 · rendering mirato | Delegati/modelli stabili, immagini dimensionate, layout testo/Canvas e motion solo se misurati | Confronto native con stessa grafica, fonte e dati; nessuna regressione nei tre temi. |

Per P2 non basta disattivare la validazione. I dati esterni e i nuovi snapshot devono continuare a essere validati prima della pubblicazione; si riusano solo strutture immutate già validate e possedute dal core.

Non congelare i provider mentre si naviga e non perdere tasti per «sembrare fluido». Accodare in modo ordinato eventuali aggiornamenti non urgenti, continuando a gestire notifiche urgenti e azioni pubbliche. Non ridurre polling o dettagli senza verificare le policy e la semantica dei dati.

Le rifiniture visive della 0.8.7 vengono dopo la reattività. Nessun nuovo provider, dipendenza grafica, asset pesante o funzione è necessario per questa fase. La 0.9 Compagno resta successiva al consolidamento.

## 6. Qualifica prima dell'installazione

**Obiettivi proposti, non risultati già ottenuti:**

- Lista calda: input software → frame coerente p95 ≤ 100 ms, nessuna selezione ordinaria oltre 200 ms nel percorso controllato.
- Dashboard calda: p95 ≤ 150 ms; prima apertura ordinaria obiettivo ≤ 300 ms, con i casi più costosi spiegati separatamente.
- Nessuna regressione rispetto alla baseline per Base/Functional; miglioramento ripetibile per Apple, soprattutto liste e impostazioni.
- Durante una selezione, stile e dati invariati restano in cache; i contatori devono dimostrare la riduzione del lavoro, oltre ai tempi.
- Refresh simultaneo e connessioni lente non bloccano il feedback del focus; nessun tasto perso nella sequenza provata.
- Memoria di host/contesti/lease senza crescita monotona dopo cicli ripetuti; preferenze, recovery e dati precedenti conservati.

Matrice: tutte le dashboard, liste Serie A e club, F1/MotoGP, Casa/Rete, impostazioni e cambio tema; giorno/notte, motion attuale/off, primo accesso/caldo, provider aggiornati/precedenti/offline. Includere il calendario completo e la preferita separata come regressioni obbligatorie.

Il QML Profiler può distinguere binding, JavaScript, creazione e fasi del rendering; una raccolta nativa rappresentativa è ancora da eseguire. [Profiling QML applications](https://doc.qt.io/qtcreator/creator-qml-performance-monitor.html).

Il `benchmark.py` storico non basta: usa un workload demo più ristretto e scarta gli intervalli ≥100 ms per separare le pause. Nel nuovo benchmark occorre distinguere idle e azioni con identificativi espliciti, **senza scartare gli stalli delle azioni**. I callback `frameSwapped` misurano un punto software, non il tempo GPU o input→pixel.

Qualifica native EGLFS esclusiva, cambio tema e strumenti che richiedono riavvio del kiosk appartengono all'implementazione/consegna successiva. Non sono stati eseguiti in questa analisi. Una futura installazione richiede backup, manifest, preferenze preservate, test pertinenti e prova del runtime finale; il report deve distinguere miglioramento PC, miglioramento board e giudizio umano sul display.

## 7. Esito e attività ancora aperte

**Confermato nel laboratorio:** costo elevato del percorso Theme API Apple; cache stile inefficace per identità del wrapper; beneficio dell'esperimento senza modifiche grafiche; costi aggiuntivi di normalizzazione e caricamento.

**Osservato sulla board:** picchi CPU sul thread GUI, memoria disponibile, nessun riavvio, due errori di callback del tema. Nessuna misura nativa di latenza o saturazione GPU.

**Ancora da dimostrare:** contributo esatto di ciascun punto alla lentezza sul pannello, comportamento dei refresh reali e del tastierino, primo caricamento su SD, attese driver/scene graph, miglioramento della patch definitiva e stabilità prolungata. Non c'è un confronto controllato con il runtime pre-0.8.6: non attribuire ogni costo esclusivamente all'ultima release.

La proposta è quindi una **0.8.7 dedicata alla reattività, mantenendo la GUI attuale**, con C++ selettivo come opzione soltanto se rimane un costo CPU dominante dopo queste correzioni.
