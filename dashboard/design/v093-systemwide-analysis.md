# Dashboard Orange Pi v0.9.3 — analisi dell'intero sistema

**Revisione 3 · 21 ottobre 2026 · Europe/Rome.**

**Perimetro:** macchina Linux dedicata, avvio e servizi, CPU/GPU/NPU, RAM/storage, acquisizione di tutti i domini, persistenza, notifiche, interfaccia Qt/QML, tutte le superfici Apple Calm e carichi concorrenti. Il Gioco è un sottosistema. Questo documento sostituisce la precedente gerarchia di priorità centrata sul Gioco; le [evidenze hardware/Gioco](v093-hardware-and-game-performance-evidence.md) restano conservate.

**Stato:** analisi architetturale e riscontri qui descritti completati; [piano complessivo V0–V9 pronto](v093-systemwide-execution-plan.md). Runtime, sistema e piloti non modificati. Prove native end-to-end, implementazione e qualifica fisica restano attività esecutive esplicite. Non si dichiara individuata ogni causa possibile di scatto dalla sola osservazione o dalle fixture.

## 1. Risultato dell'analisi

Il massimo rendimento richiede una catena corta e prevedibile dalla fonte al frame. Lavoro concorrente abbondante è utile soltanto se non blocca input/rendering/avvisi. L'assenza di limiti artificiali alla RAM permette cache e buffer generosi; la disponibilità di otto core non rende parallela una singola callback Python nella GUI.

**Priorità globali ora supportate da evidenza:** correggere il passaggio dal bootsplash al kiosk e l'avvio rimasto pendente; evitare la ricostruzione/copia di tutto Sport a ogni getter; alleggerire commit/modelli e separare preparazione/persistenza nei percorsi che il profiling trova costosi; mantenere notifiche e provider coerenti; qualificare cache/rendering su tutte le viste. Il costo dei metadati Gioco resta importante quando quel sottosistema è usato, ma non è la diagnosi della macchina intera.

Non emerge saturazione CPU/RAM generale nel campione passivo: il rischio rilevante è **la latenza dei singoli percorsi**, anche con molto hardware libero. Non c'è evidenza per cambiare interamente linguaggio, driver o backend grafico prima di correggere questi percorsi.

## 2. Evidenze e limiti

[Archivio generale e procedure](evidence/v093-systemwide-analysis-2026-10-21/README.md). Audit statico di **52 sorgenti/configurazioni** dei servizi, shell e tema; sonde provider/eventi PC e ARM con rete negata e store temporanei; getter Sport su cache attuale letta offline; osservazione passiva OS di **20,34 s**; corpus di tutte le **62 superfici non Gioco** su Apple giorno/notte, Base e Functional. Le sei superfici Gioco e le precedenti sonde rimangono nell'approfondimento dedicato.

Le sonde CPU usano nice 10, interpreti e piattaforme registrati, pochi campioni: non sono benchmark sostenuti o percentili p99 qualificati. I profili cProfile aggiungono overhead. Le fixture separano il tempo di lavoro dal costo del provider esterno; **non provano latenza/freschezza di API reali**. Il corpus PC usa offscreen/software, setup e modifiche di stile: prova comportamento/invarianti, non velocità della GPU né FPS del pannello. Il sistema non è stato fermato o riavviato.

L'inventario hardware resta: profilo A733, sei A55 e due A76, PowerVR BXM-4-64, NPU VIP, circa 5,72 GiB RAM Linux, Python 3.13.5/Qt 6.8.2/PySide6 6.8.2.1/NumPy 2.2.6. EGLFS/KMS e OpenGL sono il percorso produttivo; OpenCL/Vulkan disponibili non implicano accelerazione automatica di Python/NumPy. Contatori PVR fuori dominio non consentono percentuali GPU; FTRACE/PSI/uclamp non compilati. I dettagli verificabili e le istruzioni sono nell'[allegato hardware](v093-hardware-and-game-performance-evidence.md).

## 3. Macchina, boot e servizi Linux

### 3.1 Risorse osservate

| Misura passiva | Riscontro | Conseguenza |
| --- | --- | --- |
| CPU complessiva, tutti i core | **3,47% occupata**, iowait circa **0,056%**, finestra 20,34 s | Non dimostra capacità sotto carico; non supporta una diagnosi di saturazione permanente |
| Processo GUI | **13,62% di un core**, RSS circa 449 MiB, PSS circa 432 MiB | Percentuale di un core e percentuale dell'intera macchina sono grandezze diverse |
| Plymouth | Processo vivo, circa **4,43% di un core**, RSS 13 MiB | Lavoro estraneo alla presentazione ordinaria ancora attivo dopo il boot |
| Memoria | Disponibile circa **4,94 GiB**, cgroup Dashboard circa 551 MiB | Usare cache/preallocazione; nessuna pressione RAM dimostrata nel campione |
| Swap/fault | Delta swap-in/out, major fault e OOM **zero** nel campione | Nessuna base per eliminare zram o cambiare VM a caso |
| Root SD | Circa **74% usata**, 7,9 GB disponibili; journal circa 48,9 MB | Inventario e retention utili, senza cancellazioni automatiche di backup/piloti |
| Storage | ext4 noatime/commit=30; scheduler `none`, read-ahead 512 KiB; zram lzo-rle, swappiness 10 | Parametri già presenti, non nuovi interventi da rivendicare |

Il campione comprende il costo dell'osservatore. Non misura il carico nominale di tutte le viste né energia elettrica, temperatura sostenuta o frame. Le scritture di sistema avvenute nel campione non provano che le abbia causate la GUI: i delta `write_bytes` dei processi GUI/Plymouth erano zero.

### 3.2 Avvio incompleto e passaggio dal bootsplash

`systemd-analyze time/critical-chain` non restituiscono il tempo di boot: **FinishTimestampMonotonic=0**. `plymouth-quit-wait.service` è ancora `activating`, con sette job pendenti, inclusi multi-user/graphical target. `plymouthd` PID 217 è vivo da circa 46 ore. L'`ExecStartPre` del kiosk ha eseguito `plymouth quit` con **status 1**, errore ignorato. Nessuna unità risulta `failed`: questo non equivale a boot completato.

**Conclusione verificata:** passaggio dal bootsplash incompleto; causa precisa dello status 1 da attribuire nel lotto V1 (privilegi/socket/ordine dei servizi). Non assumere una causa unica o correggere con un kill generico. Progettare un handoff systemd con privilegi adeguati, dipendenze senza ciclo e diagnostica leggibile, separato dal processo Qt; verificare al reboot che il boot termini e il pannello rimanga operativo. Non è stato applicato alcun fix.

### 3.3 Macchina dedicata e lavoro pianificato

I servizi attivi includono rete, tempo, SSH, udev, journald, login e kiosk: sono dipendenze da valutare, non una lista da disattivare. Nel timer inventory compare anche **`copytrade-paper-alpaca-close.timer`**, che può avviare un servizio estraneo alla Dashboard; il servizio era inattivo durante la lettura. La sua presenza nello storico `blame` non significa consumo continuo attuale. Per il ruolo esclusivo dichiarato, V1 include bonifica/reindirizzamento dei job estranei, conservandone configurazione e ripristino; nessuna modifica o chiamata a quel servizio durante lo studio.

Manutenzione, logrotate, aggiornamenti e backup OS possono coincidere con la GUI. Inventariare durata e concorrenza, assegnare finestre/priorità adeguate e mantenere accesso/recovery/tempo/rete. `blame` non è la catena critica: misurare il boot soltanto dopo risoluzione dei job pendenti.

## 4. Runtime, avvio applicativo e pianificazione comune

`app.py` importa e costruisce servizi, stato, Theme API e QML in sequenza prima di `application.exec()`. Caricamenti cache, DB, impostazioni, cataloghi/font e metadati possono quindi ritardare il primo frame anche quando le richieste HTTP successive usano worker. Rete e Gioco vengono costruiti pur restando in navigazione normale; non implica che parta l'apprendimento.

Separare e misurare: processo Python/import → Qt/engine → inizializzazione di ogni servizio → cache locale → tema/font → primo contenuto coerente → avvio acquisizione. Distinguere primo frame da tutti i provider freschi. Un valore precedente esplicitamente dichiarato è preferibile a bloccare la presentazione, ma il caricamento non deve essere dichiarato completato senza dati/coerenza verificati.

Oggi esistono global thread pool per diversi provider e pool separati per altri. Il numero dei worker non è una misura di parallelismo utile. Proposta: osservare code/attesa/worker attivi e il tempo delle callback, limitare il lavoro per fonte e aggregare richieste duplicate; proteggere il percorso degli urgenti dal lavoro batch. Non spostare automaticamente tutto su un unico pool o un processo per modulo. [Qt 6.8, QThreadPool](https://doc.qt.io/qt-6.8/qthreadpool.html).

Timer verificati: segnale OS/Python 250 ms; clock e heartbeat GUI 1 s; keypad riconnessione 2 s; Info 5 s solo in monitoraggio; Casa tick 5 s; altri domini con scadenze/adattamento. Sono frequenze di callback, **non necessariamente richieste HTTP**. Account usa watcher e timer a scadenza; Rete e Avvisi hanno pianificazione su interesse/deadline. Consolidare solo il lavoro duplicato dimostrato, preservando scadenze, recupero ed errori.

## 5. Acquisizione e modelli di tutti i domini

| Dominio | Stato del codice e misura | Da fare / salvaguardia |
| --- | --- | --- |
| **Meteo** | HTTP/normalizzazione/cache nel worker; callback finale pubblica lo snapshot. Getter economico nelle fixture; sonda normalizzazione e callback registrata | Evitare ripubblicazione di dati uguali e cascata superflua. Preservare cache atomica, età/fonte, bollettini e stato precedente; non aumentare polling per ottenere fluidità |
| **Account** | File watcher, firma inode/mtime/size, timer per età. File produttivo nell'inventario circa 404 byte; refresh sincrono locale, getter economico | Mantenere cache e gestione sostituzione atomica; coalescere raffiche di watcher se dimostrate. Nessun bisogno misurato di una NPU o di un processo dedicato per leggere 404 byte |
| **Sport/Serie A** | `_data()` richiama `presentation()`, copia l'albero e ricostruisce 380 fixture a ogni getter. Cache corrente 283.216 byte; getter offline ARM **17,26 ms mediano**, max 17,45 ms | Proiezione immutabile per revisione/rotta, cache per campi statici e scadenze temporali. Pubblicare overview/lista/dettaglio senza duplicare la stagione intera. Non congelare live/freschezza/clock e notifiche |
| **Squadra/Fantacalcio** | Inclusi nello stato Sport; dettaglio e acquisizione su consultazione, calendario/rosa e voti distinti | Isolare le invalidazioni dal resto Sport; mantenere selezione, preferita, vecchi dati e disponibilità. Nessun polling continuo Fantacalcio introdotto dall'ottimizzazione |
| **F1/MotoGP** | Worker per disciplina, cache di `_data_view`, dettagli lazy; getter fixture ARM circa **0,009/0,008 ms**. Push F1 con pubblicazione aggregata a 150 ms nel codice | Preservare cache già efficaci. Profilare decodifica push, invalidazione, risultati/dettagli maturi e callback; coalescere aggiornamenti senza perdere incidenti/timing. Un socket connesso non certifica live |
| **Casa/Tuya** | Worker I/O e persistenza; tick 5 s con policy/budget/backoff. Getter demo ARM circa **0,027 ms** | Ottimizzare merge/proiezioni solo se costosi. Preservare quota, budget, identità/scope, autenticazione e stato precedente. Studio prestazioni comprende Casa, senza aggiungere comandi o categorie di avviso |
| **Rete/iliadbox** | Pool proprio; acquisizione e `store.save(updates)` delle metriche nel worker. Getter demo ARM circa **0,422 ms**, 25,9 KB di envelope | Misurare copie di caps/inventario prima del worker e `metricsView` per interesse/periodo. Riuso proiezioni/serie, invalidazione per revisione, evitare riletture storiche al cambio di un campo. Preservare conferma di persistenza e no-agent |
| **Info dispositivo** | Refresh sincrono sysfs/proc e statvfs; nmcli già QProcess con timeout e senza rescan. Sonda ARM **1,75 ms** mediano | Mantenere monitoraggio su consultazione e cache delle parti statiche; non riscrivere in nativo per questo costo isolato senza necessità |

Le misure di fixture riportano forma e dimensione nei JSON; non trasferirle a tutti i payload reali. Per Sport, invece, è stata usata la **cache effettiva salvata**, senza retimarne la fonte e forzando stato precedente: la sonda è offline e non prova aggiornamento attuale del feed.

Nel profilo Sport della cache, `deepcopy` domina (circa 80 ms cumulativi dei 90 ms profilati, contro 17,26 ms non profilati). È un costo comune alle consultazioni e potenzialmente alle dipendenze di Home/Sport: non è stato ancora contato quante volte cada nello stesso frame reale. Prima ridurre il lavoro del getter e misurare invalidazioni/numero letture, poi valutare altri linguaggi.

## 6. Notifiche e aggiornamenti autonomi

La pipeline è acquisizione → normalizzazione/dedup/revisione → stato SQLite → priorità/quiet/deadline → banner/urgente → ACK del frame → inbox/storico. Va misurata nel suo insieme, anche quando la fonte non è aperta. Nessun guadagno è valido se si ottiene sospendendo gli avvisi delle altre partite o mostrando un gol non confermato.

`EventService._tick()` può interrogare snapshot, lookup e deadline, con decodifiche ripetute degli stessi payload. Il getter `eventState` è già una cache: la parte da studiare è la costruzione. Gli ACK di seen/notified/dismiss e alcune decisioni del motore hanno commit SQLite: non usare un thread asincrono senza preservare ordine e durabilità.

Sonda ARM privata, eventi sintetici informativi: tick mediano **0,075 / 3,16 / 20,90 ms** con **0/100/1.000 eventi attivi**. Il DB reale contiene **77 righe, solo 2 attive**, circa 39 KB di payload, modalità WAL. **Il caso 1.000 non è un problema dimostrato del carico attuale.** Serve per dimensionare una raffica e verificare limiti/comportamento. Il motore limita inbox corrente a 100 e storico a 200, mentre selezioni/deadline possono visitare tutte le righe attive.

Candidati: una sola decodifica per revisione/riga nel tick, snapshot coerente condiviso per lookup/deadline, indici/query misurati, aggiornamento GUI aggregato. Conservare invarianti di revoca, scadenza, replay dopo riavvio e coda piena; nessun riordino di urgenti o falso «presentato». La latenza di un urgente deve essere provata sotto refresh simultanei, I/O e cambi tema, non soltanto a riposo.

## 7. Shell, modelli Qt/QML e tutte le viste Apple Calm

Il percorso comune comprende `DashboardState`, summary, `PublicContextAdapter`, normalizzazione/validazione Theme API, modelli QObject, ViewHost/OverlayHost, shell e componenti del tema. Il lavoro può duplicarsi anche se il provider è veloce: conversioni Python↔QVariant↔JS, snapshot completi, confronto, copie, `dataChanged`, layout e costruzione delegati.

Esistono già cache per dominio/summary, proiezione per rotta, aggregazione `Qt.callLater`, sospensione dei renderer trattenuti e stream scena separato. Non riproporli come assenti. Restano da misurare le dipendenze ampie da `now`, stile, stato generale e liste, e il costo dei modelli su liste mature. Il fatto che una proiezione finale sia piccola non evita un getter upstream da 17 ms.

### 7.1 Copertura verificata fuori dal Gioco

Ricostruita la matrice delle **62 superfici non Gioco**, includendo Home/Oggi/orologio/giornata, Meteo, Account, hub/Sport/squadra/Fantacalcio, F1/MotoGP/dettagli pilota, Casa e inventario/dettagli, Rete/router/Wi-Fi/porte, impostazioni, Info, shell/scena e tutte le forme degli avvisi.

| Profilo PC offscreen | Casi distinti riusciti | Superfici distinte |
| --- | ---: | ---: |
| Apple Calm giorno, corpus non Gioco completo | **154** | **62** |
| Apple Calm notte, un caso per superficie | **62** | **62** |
| Base giorno, un caso per superficie | **62** | **62** |
| Functional giorno, un caso per superficie | **62** | **62** |

Totale **340 combinazioni profilo/caso** riconciliate. Rete negata e nessuna richiesta tentata; nessun messaggio QML raccolto nelle esecuzioni riconciliate. Si verificano routing/contenuti, focus, stile, identità attore e deadline/flag degli avvisi attraverso cambi di token. Non sono 340 benchmark FPS né la matrice completa di tutte le varianti su tutti i temi.

Il primo runner si fermava sulle nuove superfici Rete perché cercava un vecchio `DashboardOverlay`. I risultati parziali sono conservati. Nel solo harness dello studio l'oracolo corretto verifica **contentId del vero host, renderer con geometria valida, readiness e contesto pubblico attivo**. I nove casi finali sono stati rieseguiti per profilo; nessuna modifica al runtime per soddisfare il test. La copertura è l'unione dei casi distinti riusciti, non la somma di tentativi e ripetizioni.

### 7.2 Grafica, cache, font e immagini

Apple ha **71 file QML**, due Canvas grafici reali e un atlante PNG **1.200×2.112**, circa 997 KB compressi (circa 9,67 MiB per RGBA non compresso, prima di copie/mipmap). Tre file font nel bundle pesano complessivamente circa 968 KiB. Dimensione su disco non equivale a memoria GPU, e file QML non equivale a istanze vive.

Le sonde correnti dei due grafici (due serie da 512 punti, 200 cambi) confermano **zero letture punti nascosti**, parità pixel dopo hide/update/show e clearing del dato mancante per MiniHistory, senza warning. Non dimostrano il costo grafico visibile nativo. Conservare il comportamento già ottimizzato; se il visibile pesa, confrontare proiezioni riusate/campionamento con minimi/massimi/buchi e poi geometria QSG. Non rasterizzare nuovamente icone già nell'atlante a ogni frame.

ViewHost ha cache trattenuta ma default `cacheLimit=0`: inventariare valori effettivi di tutte le istanze prima di promettere riuso. Dare RAM a renderer/texture/font/proiezioni davvero riutilizzati, disattivando lavoro nascosto; invalidare per tema/generazione/viewport e aggiornare i dati prima di esporre la vista. Clip/trasparenze/layer/offscreen target vanno scelti con profiling e parità visiva. [Qt 6.8, prestazioni](https://doc.qt.io/qt-6.8/qtquick-performance.html).

## 8. Persistenza, storage e RAM dell'intera applicazione

| Archivio/attività | Stato osservato nel codice | Scelta di studio |
| --- | --- | --- |
| Cache Meteo/Sport/Motorsport/Casa | Persistenza atomica in diversi worker | Conservare completezza/hash/commit; profilare serializzazione e competizione I/O, non togliere fsync |
| Cache metriche Rete e storico RRD | Salvataggio prima dell'ACK nel worker, limiti cache/storico | Separare proiezione da lettura/persistenza e misurare timeline interesse→cache→vista |
| Notifiche | SQLite WAL già in uso sul dispositivo; operazioni del motore sul thread chiamante | Non «abilitare WAL» come fix già fatto; misurare transazioni e costo del tick mantenendo ordine |
| Preferenze/tema | QSettings, bundle immutabili, lease, journal di attivazione e cleanup | Evitare scritture uguali; cleanup/manutenzione fuori finestre critiche solo con protocollo lifecycle conservato |
| Heartbeat | Già nel `/tmp` privato, non su SD a ogni secondo | Non dichiarare nuova una migrazione già implementata; misurare serializzazione/letture residue |
| Gioco | Letture JSON e checkpoint pesanti già misurati | Pacchetto specifico V8, senza estenderne i numeri agli altri DB |

Non cambiare globalmente journal mode, synchronous, cache SQLite, VM e read-ahead in un unico esperimento. WAL ha concorrenza e checkpoint da gestire; un reader troppo lungo può impedirne il contenimento. Versione SQLite letta **3.46.1**: ogni nuovo impiego concorrente va verificato sul runtime effettivo. [SQLite WAL](https://www.sqlite.org/wal.html).

RAM libera si usa per dati normalizzati posseduti, proiezioni per rotta/revisione, geometrie, cache dei renderer e buffer numerici. Evitare cinque copie della stessa stagione/provider in Python/JS/QObject. Misurare RSS e soprattutto PSS, cgroup, disponibile, swap/fault e numero di oggetti su cicli ripetuti; una cache dichiarata può crescere e assestarsi, una perdita illimitata no. Non scegliere un limite RAM basso per principio e non svuotare page cache durante l'uso.

## 9. CPU, GPU, NPU, linguaggi e driver per tutto il sistema

| Compito globale | Esecutore proposto | Condizione |
| --- | --- | --- |
| Input, focus, commit minimo modelli, urgenti | CPU/thread GUI con precedenza effettiva | Niente parsing ampio, attesa storage o costruzione di alberi pesanti nella callback |
| HTTP/WebSocket, cache e file, parsing | CPU worker; processo per tratti GIL/JSON pesanti misurati | Trasferire proiezioni piccole, con fonte/revisione e risposta superata scartata |
| Dedup/revisioni/notifiche/persistenza | CPU, scheduler seriale coerente per archivio | Priorità semantica e durabilità, non concorrenza indiscriminata |
| Text/layout/compositing/immagini/grafici | Qt Quick/scene graph + GPU; preparazione CPU dove richiesta | Dati/texture stabili, geometria riusata, niente lavoro nascosto |
| Animazioni visive | Clock Qt/render quando applicabile | Stato logico e hit testing corretti, movimento ridotto preservato |
| Regole, rete locale, riepiloghi | CPU deterministica | Nessun motivo per tradurre HTTP, SQL o JSON in una rete neurale |
| Inferenza di modelli reali futuri o attuali pertinenti | NPU candidata | Modello/operatori/precisione, trasferimenti e latenza completi qualificati |
| Calcolo parallelo numerico realmente dominante | CPU nativa/SIMD o GPU compute | Confronto contro CPU veloce ottimizzata e rendering concorrente |

Conservare Python/PySide per servizi e contratti, QML per presentazione. C/C++/NEON per loop o QQuickItem costosi dopo misura; build ARM compatibile con A55/A76, GIL e confini FFI espliciti. Rust/Cython sono alternative locali, non prerequisiti. QML compilato su moduli stabili e cache di shader/import sono confronti misurabili, non un passaggio automatico di tutto il tema a C++.

NPU non accelera automaticamente lettura dei provider, logica delle notifiche o UI. Non c'è nel carico informativo attuale un modello neurale che giustifichi un backend NPU obbligatorio. È una conclusione sull'architettura disponibile, non una valutazione negativa della NPU. CPU/GPU/NPU condividono DDR e limiti termici.

Topologia eterogenea: confrontare scheduler libero con precedenza/maschere del solo lavoro critico, senza relegare tutti i worker ai core lenti o concentrare tutto su 6–7. Nice/CPUWeight, governor e thread BLAS affrontano problemi diversi. `performance` può aiutare la latenza di salita, ma non elimina termica/alimentazione; misurare il risultato caldo. [Linux CPUFreq](https://docs.kernel.org/6.6/admin-guide/pm/cpufreq.html).

Driver vendor EGL/GLES 24.2 e Qt 6.8.2 restano la baseline. L'aggiornamento richiede kernel/firmware/userspace coerenti, prova su clone e display/recupero; non sostituire libEGL o passare a Vulkan per tentare di risolvere copie JSON. I clock e le API esposte non costituiscono da soli prova di throughput.

## 10. Il ruolo del Gioco nell'analisi complessiva

I risultati precedenti restano: refresh metadati reali headless circa 143–220 ms; getter snapshot 0,13–4,48 ms; snapshot/replay/encoding e code preview da separare. Sono problemi del sottosistema Gioco, da risolvere senza alterare ricette, piloti, fisica e decisioni.

Il [pacchetto di lavoro dedicato](v093-game-performance-work-package.md) viene eseguito nel lotto V8 e concorre alle prove globali di avvisi/rendering/acquisizione. Non detta più da solo ordine o criteri di uscita dell'intera v0.9.3; una release che migliora solo Gara lasciando boot, Sport, Home, notifiche e Rete non qualificati non soddisfa questa richiesta.

## 11. Criteri globali e lavoro da eseguire

Il [piano V0–V9](v093-systemwide-execution-plan.md) specifica implementazioni, dipendenze, test e rollback. Target: avvio concluso e primo frame coerente; interazione e animazioni nominali verso 60 Hz (16,67 ms), nessun blocco JSON/storage nel percorso GUI; timestamp, cache precedente e avvisi affidabili; continuità anche con fonti/worker concorrenti; memoria/termica stabili nell'uso lungo. Il Gioco conserva gate 30 pose regolari ed estensione 60 separata.

Per ogni dominio servono almeno riposo, refresh, interazione e errore/recupero; per il sistema anche rete assente, refresh simultanei, manutenzione storage, urgente e reboot. La prima baseline nativa misura tutti questi gruppi prima di ordinare i rami ancora ipotetici. Non trasformare un getter veloce in priorità di riscrittura solo per coprire una casella.

**Analisi preparatoria conclusa nel perimetro dichiarato:** sono disponibili inventario, audit dell'intero flusso, riscontri OS, sonde per tutti i domini, copertura di tutte le superfici non Gioco e un piano generale. Restano da eseguire le ottimizzazioni selezionate e le prove native/ottiche/sostenute. Nessun nuovo claim di FPS, maggiore freschezza live o risoluzione dei guasti deriva dal solo documento.
