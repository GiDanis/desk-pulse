# Aperture pesanti, CPU e GPU — analisi della 0.8.7

10 ottobre 2026 · installazione osservata `0.8.7-rc.1` · Qt 6.8.2 · Apple Calm 1.6.1 · 960×640.

**Seguito autorizzato:** H1–H3 implementati e consegnati nella [0.8.7-rc.2](v087-opening-implementation-report.md), con confronto nativo, backup e reboot. Questo dossier conserva la diagnosi precedente; stato installato, risultati e residui aggiornati sono nel rapporto di consegna.

La priorità è ridurre il lavoro sincrono necessario per aprire e riaprire le viste. Gli otto core sono disponibili e il rendering hardware PowerVR è attivo. Le prove raccolte indicano costi importanti nella costruzione, normalizzazione e pubblicazione dei contesti della GUI, oltre a un riuso incompleto della cache degli overlay. Non dimostrano una saturazione della GPU o una carenza generale di core.

La segnalazione aggiornata dell’utente è «delay tra il press di un tasto e cambio schermata, con animazione lenta o inesistente». La metrica prioritaria diventa quindi tasto → primo feedback visibile, oltre al tempo della destinazione completa.

Questo documento conclude un'analisi: nessuna modifica al runtime, distribuzione, riavvio del servizio, reboot o modifica dei governor. Le nuove prove sulla board sono passive; i percorsi ripetuti vengono eseguiti sul PC con Main reale, dati sintetici e rete bloccata. Il tema approvato resta il riferimento grafico.

## 1. Evidenze e limiti

| Evidenza | Che cosa stabilisce | Limite |
| --- | --- | --- |
| [Confronto nativo della 0.8.7](v087-performance-implementation-report.md) | Liste e dashboard migliorate; costo residuo delle aperture | Tre aperture per profilo; tempi software, non latenza ottica |
| [Board passiva, 31 campioni / circa 30 s](evidence/v087-heavy-opening-analysis-2026-10-10/passive-board.json) | Versione/hash, thread, core, frequenze, librerie e descrittori grafici effettivi | Nessuna sequenza controllata di tasti o refresh simultanei |
| [Riepilogo CPU](evidence/v087-heavy-opening-analysis-2026-10-10/passive-summary.json) | Carico nella finestra osservata, affinità e ultimo core osservato | L'ultimo core non è una storia delle migrazioni |
| [Profili Python per singola azione](evidence/v087-heavy-opening-analysis-2026-10-10/pc-phase-profile.json) | Attribuzione dei costi di apertura Serie A, chiusura e cambio argomento | PC offscreen; cProfile altera i tempi e non profila GPU o intero codice QML |
| [Nove percorsi e attribuzione per superficie](evidence/v087-heavy-opening-analysis-2026-10-10/pc-route-profiles.json) | Serie A, squadra/selettore, F1/MotoGP, Casa, Rete, Impostazioni e Info | Singole visite profilate, cache progressivamente calda; non una classifica di latenza |
| [Identità e vita dei contesti](evidence/v087-heavy-opening-analysis-2026-10-10/pc-overlay-cache.json) | Riapertura fredda ripetuta contro ritorno da un'altra vista | Riproduzione PC; costo nativo della correzione ancora da misurare |
| [Stato diagnostico PowerVR, dieci letture](evidence/v087-heavy-opening-analysis-2026-10-10/pvr-passive.json) | Driver/firmware, errori e utilizzo istantaneo nel periodo tranquillo | Nessuna attribuzione per frame o apertura |

Le prove PC positive hanno rete negata e nessun messaggio QML durante i percorsi. Il manifest osservato sulla board contiene 514 file senza discrepanze; SHA-256 `73fe019fd96bd2dee817e370c87cac2dbe887155b578c8621298be7343833670`. Il supervisore mantiene PID 1186, GUI PID 1276, servizio active/running e NRestarts=0 durante il campionamento. La [lettura finale](evidence/v087-heavy-opening-analysis-2026-10-10/final-board-health.txt) conferma stessi PID e boot ID, servizio attivo e driver/firmware OK.

## 2. Dove pesa aprire una vista

Il precedente confronto sulla stessa board, con motion off e lo stesso protocollo conservativo, resta la baseline di latenza:

| Azione Apple Calm | Prima della 0.8.7 | 0.8.7 | Interpretazione |
| --- | ---: | ---: | --- |
| Focus nella lista Serie A, mediana / p95 | 111,6 / 136,4 ms | 68,5 / 85,0 ms | Miglioramento acquisito |
| Cambio dashboard, mediana / p95 | 121,1 / 237,9 ms | 80,5 / 168,9 ms | Miglioramento, coda ancora oltre il gate 150 ms |
| Apertura Serie A, mediana / massimo, n=3 | 729,4 / 1098,4 ms | 697,9 / 864,8 ms | Campione troppo piccolo per qualificare il freddo |
| Solo handler dell'apertura, mediana | 433,4 ms | 463,0 ms | Lavoro sincrono sostanziale prima che la GUI torni disponibile; confronto n=3 |

Il tempo totale comprende attesa della destinazione, controllo di readiness e invio di un frame richiesto esplicitamente dopo il controllo. L'handler viene misurato attorno all'emissione del tastierino sintetico, prima del polling. La readiness del vecchio harness attraversa ripetutamente tutti i QObject e consulta i metaoggetti: parte del totale è diagnostica. Non va confusa con lentezza del prodotto; il costo dell'handler conferma comunque un problema reale sul percorso sincrono. `frameSwapped` non misura GPU, pannello o tastierino fisico.

### Attribuzione per apertura Serie A

Tre aperture PC con 380 partite sintetiche, profilate separatamente, individuano un percorso ricorrente:

| Voce | Apertura 1 | Apertura 2 | Apertura 3 |
| --- | ---: | ---: | ---: |
| Tempo totale profilato | 516 ms | 327 ms | 328 ms |
| `updateLegacy`, cumulativo | 347 ms / 12 chiamate | 252 ms / 11 | 261 ms / 15 |
| `deepcopy`, cumulativo | 169 ms / 188.538 chiamate | 99 ms / 124.655 | 102 ms / 126.906 |
| `_update` dei contesti, cumulativo | 148 ms / 1.922 | 97 ms / 1.523 | 96 ms / 1.529 |
| Emissioni di segnali osservate | 10.931 | 8.462 | 8.469 |

I tempi cumulativi si sovrappongono e non si sommano. Le chiamate a deepcopy includono ricorsione; i segnali comprendono quelli transitati durante tutta l'azione, non soltanto il nuovo overlay. Sono costi PC con profiler, non nuove misure native. `updateLegacy` pesa circa il 67–80% del totale di queste aperture: la preparazione dei dati merita precedenza rispetto alla riscrittura grafica.

`ViewHost.prepare()` crea sincronicamente il Loader, il contesto di presentazione e il PublicContextAdapter. L'adapter chiama `factory.create()`, che costruisce l'albero dei valori predefiniti; subito dopo `refresh()` normalizza lo stato effettivo e aggiorna gli oggetti/modelli. Verifica della risorsa e acquisizione del lease precedono anch'esse l'avvio del renderer. L'inizializzazione predefinita seguita dall'aggiornamento è un candidato concreto, ma il risparmio ottenibile dal singolo intervento deve ancora essere isolato.

Il Loader è già asincrono: questa proprietà riguarda caricamento/compilazione e incubazione del componente, non sposta automaticamente il lavoro Python precedente in un worker. [Semantica ufficiale di Loader](https://doc.qt.io/qt-6.8/qml-qtquick-loader.html).

### Difetto di riuso riprodotto

Cinque cicli reali di 5 → lista Serie A → 7 sul PC creano cinque istanze pubbliche diverse; chiudendo, il currentLoader viene svuotato e il loader della lista non entra nella cache. La stessa cosa si osserva in Impostazioni.

Il percorso lista → Impostazioni → indietro riutilizza invece l'identità precedente della lista, senza nuova generazione: la cache funziona quando si cambia overlay. La differenza è riproducibile, non un'ipotesi basata solo sul codice. In `ViewHost.prepare`, il ramo senza presentazione distrugge il loader corrente; il passaggio a un altro renderer usa `retainOrDestroy` e la cache con limite sei.

La correzione va progettata distinguendo una normale chiusura dalla rimozione di una superficie da un tema. Un renderer obsoleto o un lease invalidato deve continuare a essere rilasciato. Il riuso deve conservare bookmark/focus, aggiornare dati e stile, sospendere refresh e motion quando nascosto e rispettare il limite di memoria. Non si propone di tenere tutte le viste permanentemente attive.

### Squadra: dati fuori dal percorso utile

L’estensione del profilo riproduce un costo molto maggiore aprendo la dashboard Squadra quando non è ancora impostata una preferita: la normalizzazione di `sport.team`, sotto il selettore `sport.team.picker`, prepara 380 partite del campionato. Il selettore non è il principale costo: circa 4,87 s cumulativi profilati sono in normalizzazione di `sport.team`, contro circa 13 ms in quella del picker. Il resto dell’aggiornamento aggiunge costruzione degli oggetti e notifiche.

Una verifica indipendente, senza cProfile e in due processi PC isolati, misura il solo handler della prima apertura: **199 ms con 10 partite, 3852 ms con 380**. Il contesto della dashboard sottostante contiene rispettivamente tutte le 10/380 partite. Sono due campioni sintetici PC, non tempi del pannello o una previsione sulla board. Confermano però che il costo cresce con dati del campionato nella vista squadra. [Prova con 10 partite](evidence/v087-heavy-opening-analysis-2026-10-10/pc-team-cold-10.json), [prova con 380](evidence/v087-heavy-opening-analysis-2026-10-10/pc-team-cold-380.json).

Serve una proiezione mirata per `sport.team`: identità della preferita, fonte e informazioni della squadra richieste dalla superficie. Non deve ricostruire il campionato completo per mostrare questa dashboard. Calendario della squadra, selettore e tutte le partite Serie A restano accessibili nei rispettivi percorsi; campi pubblici e compatibilità dei temi vanno verificati prima di restringere una proiezione. Controllare anche le attivazioni intermedie durante la transazione di navigazione.

Il secondo passaggio “Squadra con modo preparato” nel profilo trova il contesto già visitato: non dimostra che anticipare `sportView` risolva il freddo. La differenza fra quel passaggio e il primo confonde cache calda e preparazione della route; non è un confronto valido di patch.

Il profilo ampliato individua anche normalizzazione significativa nei dettagli F1/MotoGP. Per Casa, Rete e Info una grossa parte del tempo totale è invece il polling diagnostico su un albero ormai grande. Impostazioni ha un handler profilato di circa 312 ms, pur con soli circa 11 ms nella normalizzazione della sua superficie: profilare costruzione del renderer, binding e dati delle righe prima di attribuire tutto al backend Python. Non confrontare i totali delle nove visite come se fossero tutti freddi e con inventari reali.

### Ritardo e animazione sono due misure

`presentPage()` avvia la transizione soltanto quando host e contesto sono pronti. Un’apertura sincrona pesante rinvia quel punto, quindi anche una transizione breve può sembrare partire tardi. Per ogni tasto vanno distinti handler, primo feedback, avvio/termine del movimento, primo frame della nuova destinazione e readiness completa.

Il manifest Apple Calm 1.6.1 imposta `navigate.family`, `navigate.view`, `panel.enter` e `panel.exit` su **builtin.cut, durata 0 ms**; `MotionController.play()` termina subito per questa ricetta. L’assenza di movimento nei relativi percorsi può quindi essere una scelta del tema, non un frame perso. Le eventuali personalizzazioni effettive vanno registrate con la prossima traccia. Inoltre `OverlayHost` disabilita `animateSwap`, e il cambio disciplina 2/8 in Sport non passa dallo stesso `navigateView` degli altri argomenti: esiste una differenza di collegamento degli eventi da verificare.

Proposta grafica contenuta: feedback immediato sul comando e, dove coerente, una breve transizione da 80–120 ms con spostamento minimo o fade già previsto dal sistema. Prima ridurre il lavoro bloccante; aggiungere animazioni non lo elimina. Rispettare motion off/reduced, interrompere correttamente le raffiche, preservare focus e non mostrare come nuova una schermata ancora vecchia. L’animazione di Sport deve seguire gli stessi criteri delle altre dashboard senza ricreare la scena.

## 3. Core e distribuzione dei task

La board osservata ha CPU0–5 Cortex-A55, capacità Linux 385, massimo configurato 1,794 GHz; CPU6–7 Cortex-A76, capacità 1024, massimo 2,002 GHz. Tutti sono online. Le due policy usano `schedutil`; il servizio non impone quota o affinità CPU e i thread osservati possono usare 0–7.

Non sono otto core equivalenti. Linux rappresenta questa differenza di capacità nelle decisioni dello scheduler: assegnare un task fisso a ogni core non garantirebbe la migliore latenza. [Capacity-aware scheduling del kernel](https://docs.kernel.org/scheduler/sched-capacity.html).

Durante circa 30 secondi senza input controllato, il thread GUI consuma il 10,7% di un core; il carico aggregato per core varia circa dall'1,1% all'11,1%. Il suo ultimo core osservato è alternativamente 0 e 7. QSGRenderThread, QQmlThread, QDBusConnection e altri thread sono presenti e quasi inattivi nella finestra, alla risoluzione del contatore CPU. Non esiste una prova di saturazione in questa finestra, né una prova che il lavoro delle aperture sia già distribuito bene. Servono tracce durante quel lavoro.

| Attività nel codice attuale | Dove avviene | Valutazione |
| --- | --- | --- |
| Input, binding, contesti pubblici, modelli, pubblicazione degli snapshot | GUI | Percorso critico dell'apertura; ridurre copie, ricostruzioni e notifiche |
| Meteo, Sport, squadra, Fantacalcio, F1/MotoGP, Casa: acquisizione/persistenza del provider | QRunnable/QThreadPool; risultato pubblicato nella GUI | Separazione I/O già presente; va misurato il costo di pubblicazione |
| Rete locale, letture e operazioni/cache | Pool privato limitato a un worker | Serializzazione deliberata; non aumentare la concorrenza senza verificare client, SQLite e ordine dei risultati |
| Importazione pacchetti tema e salvataggio preferenze | Job di lavoro dedicati | Già fuori dalla GUI; acquisizione del lease rimane nel percorso dell'host |
| Account | File locale limitato a 32 KiB, watcher/timer nella GUI | Sync sul PC separato; non trattarlo come polling cloud della board |
| Scene graph e invio del rendering | QSGRenderThread effettivamente presente | Rendering separato, sincronizzato con la GUI |

L'interprete installato è CPython 3.13.5 con GIL attivo; non è una build free-threaded. I thread aiutano l'I/O e il codice nativo che rilascia il GIL; moltiplicarli non rende parallele le copie e la normalizzazione Python. [Threading Python 3.13](https://docs.python.org/3.13/library/threading.html).

QML e i QObject della GUI devono rispettare il thread di appartenenza. Leggere i metaoggetti dello stato vivo in un worker o costruire là l'albero pubblico con parent GUI sarebbe una soluzione scorretta. L'architettura utile è: snapshot posseduto e versione immutabile → trasformazione pura → risultato verificato → commit nella GUI. [Threads and QObjects](https://doc.qt.io/qt-6.8/threads-qobject.html).

Un processo separato può usare altri core per calcoli Python, ma aggiunge avvio, memoria e serializzazione IPC. Va provato soltanto per una trasformazione abbastanza grande e indipendente, con avvio compatibile con Qt e senza ereditare l'engine grafico. Un processo persistente e una coda limitata potrebbero essere preferibili a un processo per apertura. [Multiprocessing](https://docs.python.org/3.13/library/multiprocessing.html). La build senza GIL richiede anche compatibilità delle estensioni e non è una migrazione proposta per questa manutenzione. [Free-threaded Python](https://docs.python.org/3.13/howto/free-threading-python.html).

## 4. GPU: uso confermato, efficienza da qualificare

L'ambiente richiede EGLFS/KMS e OpenGL. La verifica non si ferma a quelle variabili: il processo GUI ha effettivamente aperto card0/renderD128, i descrittori DRM riportano `drm-driver: pvr`, e sono caricate `libGLESv2_PVR_MESA.so.24.2.6603887` e `libpvr_dri_support.so.24.2.6603887`. È presente QSGRenderThread. Il percorso hardware PowerVR è quindi confermato; non risultano librerie llvmpipe/swrast tra quelle rilevate.

Qt Quick prepara e sincronizza la scena prima del lavoro del renderer: se la GUI passa centinaia di millisecondi a costruire dati, la GPU non può accelerare automaticamente quel tratto. [Architettura scene graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html).

Devfreq espone 400/600/800/1008 MHz, governor `simple_ondemand`. I 31 campioni passivi sono a 400 MHz. Questa frequenza non equivale a utilizzo e non prova che il governor sia guasto. I fdinfo espongono memoria e identità dei client, senza contatori engine/cycles: non si può ricavare il carico dalla memoria allocata, né sommare descrittori duplicati dello stesso client. [Statistiche DRM del kernel](https://docs.kernel.org/gpu/drm-usage-stats.html).

Un approfondimento in sola lettura trova però `/sys/kernel/debug/pvr/status`: dieci letture successive riportano GPU Utilisation 0%, firmware/driver OK e contatori di errori/recovery a zero. È una misura istantanea del driver in una finestra tranquilla, non una percentuale per il processo SmartPC o per le aperture. Il driver e firmware sono Rogue DDK 24.2@6603887, BVNC hardware 36.56.104.183. Non si deduce da questo numero un modello commerciale non verificato.

`PVRPerfServer`, `PVRTune` e `perf` non risultano nel PATH controllato; `pidstat` è disponibile. PVRTune/PVRScope sarebbero adatti a correlare i contatori hardware con i frame, ma la documentazione consultata garantisce Rogue DDK fino a 23.2, mentre qui è 24.2: la compatibilità deve essere verificata prima di proporre un'installazione. [Strumenti e supporto ufficiale PowerVR](https://docs.imgtec.com/tools-manuals/pvrtune-manual/html/pvrtune-manual/topics/introduction.html).

Le icone Apple usano un atlante Image, già adatto al riuso delle texture. I grafici Canvas, invece, usano il disegno 2D che può comportare lavoro CPU e upload della texture. Una riscrittura con geometria scene graph/Shape ha senso soltanto se il profilo dei grafici la giustifica. Va mantenuta la semantica di intervalli mancanti, stati precedenti e unità. [Canvas e prestazioni](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html), [batching del renderer](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph-renderer.html).

## 5. Piano degli interventi, nell'ordine

| Passo | Intervento proposto | Risultato e verifica richiesta |
| --- | --- | --- |
| H0 · Misura mirata | Marker leggeri per handler, normalizzazione, creazione contesti, lease, incubazione, commit e frame; readiness sugli host pertinenti, senza scansioni globali ripetute | Separare freddo/caldo e lavoro reale/strumentazione; acquisire CPU per thread/core, stato GPU e memoria durante le azioni |
| H1 · Riapertura | Conservare in cache bounded l'overlay valido anche alla chiusura normale; distruggere superfici rimosse/revisioni obsolete | Stessa istanza sul riuso, dati aggiornati, zero animazioni/refresh nascosti; invalidazione corretta con cambio tema e recovery |
| H2 · Inizializzazione | Proiettare `sport.team` senza il campionato completo; studiare factory privata con snapshot iniziale già normalizzato, evitando doppia costruzione default → dati; riuso della normalizzazione per versione/dominio e righe stabili | Identità, tipi, default, proprietà, ownership, modelli e tutti i dati invariati; meno copie e segnali misurati, nessuna disattivazione della validazione |
| H3 · Primo feedback | Se il freddo resta lungo, distribuire preparazione/commit in porzioni limitate e dare feedback visibile coerente con il tema; uniformare i percorsi di motion e valutare transizioni brevi | GUI disponibile fra le porzioni; destinazione pronta solo quando davvero coerente; tasti rapidi, annullamento e cambio tema sicuri |
| H4 · Parallelismo selettivo | Portare solo trasformazioni pure pesanti fuori dalla GUI; valutare processo persistente o modulo nativo se il profilo residuo lo richiede | Confrontare guadagno totale con copie/IPC e memoria; scartare risultati obsoleti per generazione, code limitate; non accedere a QObject vivi dai worker |
| H5 · Grafica mirata | Misurare grafici, repaint, layer e upload solo dopo il percorso dati; ottimizzare ciò che risulta costoso | Stessa GUI; GPU e frame correlati sotto carico. Nessun governor performance o affinità permanente senza prova di beneficio e temperatura |

Per Rete, registrare separatamente attesa in coda, chiamata al router, persistenza e pubblicazione. Un dettaglio lento può dipendere da una precedente operazione nello stesso pool: resta un'ipotesi da misurare. Dare priorità al lavoro richiesto dalla vista potrebbe essere più utile di aggiungere letture simultanee. La manutenzione non aumenta implicitamente quote/API o frequenze di polling.

La scelta corrente rimane Qt Quick/QML + Python. H1 e H2 vengono prima di processi/C++, upgrade Qt/interprete, pinning sui core A76 o cambi al tema: risolvono lavoro ripetuto già osservato. Se rimane un tratto di calcolo puro dominante, C++ selettivo può avere senso; non esiste oggi una prova che una riscrittura completa del linguaggio sia necessaria.

## 6. Gate della successiva implementazione

Misurare almeno 30 aperture per percorso, separando prima apertura, riapertura identica, ritorno da dettaglio e cambio tema. Dare precedenza a tasto → cambio argomento e dashboard, Squadra con/senza preferita, Serie A e Impostazioni; poi Casa, Rete traffico/dispositivi, F1/MotoGP e informazioni. Le piccole fixture di Casa/Rete non qualificano gli inventari reali: aggiungere carichi sintetici 16/39 dispositivi e storico con intervalli mancanti, senza esporre dati personali.

Obiettivi da qualificare, non promesse: riapertura p95 ≤150 ms, apertura completa p95 ≤300 ms, primo feedback ≤100 ms; mantenere liste p95 ≤100 ms e dashboard p95 ≤150 ms sulla stessa board. Il confronto usa protocolli identici, profiler disattivato e tutti gli outlier. Per il freddo distinguere cache applicativa nuova da riavvio/OS cache: ripetere processi isolati e riportare la condizione, senza svuotare cache del kiosk live.

Verificare i tre temi, tutte le partite Serie A e squadra separata, preferenze/bookmark, invalidazione dopo refresh, versioni/lease dei bundle, fallback e recovery. Raffiche di tasti non devono perdere azioni, aprire route vecchie o bloccare annullamento. La cache deve restare bounded, con memoria e thread stabili dopo molte aperture; i worker non devono crescere senza limite o ripetere richieste.

Misurare poi sul runtime EGLFS a 960×640 con motion normale e refresh concorrenti controllati, temperature e frequenze. La qualifica della latenza con tastierino fisico e pannello resta separata dal software; il collaudo prolungato non è sostituito da questo campionamento passivo. Font, icone, colori, spazi e organizzazione delle dashboard approvati devono restare riconoscibili.

## 7. Fonti e riproducibilità

Oltre alle fonti ufficiali collegate nelle sezioni, [Qt Quick Performance](https://doc.qt.io/qt-6.8/qtquick-performance.html) sostiene l'ordine di lavoro: profilare, limitare il lavoro della GUI, creare quando serve e controllare i costi dei delegate. Le regole generali vengono applicate ai percorsi riprodotti di SmartPC, senza attribuire ai documenti esterni risultati misurati sulla board.

Script e JSON sono nella [cartella delle prove](evidence/v087-heavy-opening-analysis-2026-10-10/). I quattro diagnostici PC usano ambiente temporaneo, provider isolati e Qt offscreen. `passive-board.py` legge stato proc/sys e manifest tramite SSH; il campionamento PVR legge soltanto stato/frequenza. Nessuno strumento di profiling hardware è stato installato. Il codice applicativo e la versione installata non sono stati modificati da questa analisi.
