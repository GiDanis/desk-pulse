# v0.9.3 — evidenze hardware e approfondimento Gioco

**Revisione 2 conservata · 21 ottobre 2026.** Questo documento conserva il primo approfondimento, concentrato sul Gioco. L’[analisi generale](v093-dashboard-performance-study.md) e il [piano complessivo](v093-dashboard-performance-execution-plan.md) definiscono ora il perimetro e le priorità dell’intero sistema.

**Stato: analisi preparatoria conclusa con inventario, audit, sonde headless PC/ARM e lettura temporizzata dei metadati attuali; [piano esecutivo pronto](v093-dashboard-performance-execution-plan.md). v0.9.3 non implementata, non installata e non qualificata.** Baseline effettiva: core **0.9.0-rc.28**, 642 hash conformi, Theme API 2.11, Apple Calm **1.6.3 attivo**. La versione 0.9.3 identifica il prossimo lavoro trasversale di ottimizzazione; non rinomina il runtime corrente e non implica che esistano già rilasci 0.9.1/0.9.2. La baseline end-to-end EGLFS e i confronti delle varianti costituiscono F0 e i lotti di esecuzione, non risultati già ottenuti.

## 1. Decisione e obiettivo

La Dashboard è il compito principale della macchina. Possiamo utilizzare la RAM e la capacità di calcolo disponibili per ridurre latenza, caricamenti e scatti: **nessun obiettivo artificiale di minimizzazione della RAM o della CPU**. L'obiettivo è il miglior comportamento sostenuto dell'interfaccia, anche durante acquisizione dati, avvisi, apprendimento, gara e salvataggi.

La proposta è mantenere **QML/Qt Quick per la presentazione, Python/PySide6 per servizi e contratti, C/C++ mirato per i tratti numerici o grafici dimostrati costosi**. CPU e GPU hanno già compiti separati; aggiungere NPU o compute GPU richiede un vantaggio misurato sull'intero percorso. Riempire tutti gli acceleratori o saturare otto core non è una metrica di successo.

Ordine di lavoro: misurare le code lunghe della GUI → ridurre conversioni e preparazione sincrona → sfruttare cache e dati residenti → confrontare priorità/topologia/frequenze → portare in nativo i colli di bottiglia rimasti → valutare compute GPU/NPU quando il carico lo giustifica. Non è una promessa di percentuali di guadagno prima delle prove.

Identità Apple Calm conservata: colori, caratteri, icone, geometria, focus e movimento approvati. Dati live, timestamp, qualità delle fonti, avvisi e salvataggi devono restare corretti. La roadmap successiva rimane Acquario v0.10 → Compagno v0.11 → Memoria/AI v0.12 → Stabilità v1.1.

## 2. Metodo e attendibilità

Evidenze dell'inventario iniziale in [inventario](evidence/v093-performance-study-2026-10-21/board-inventory.json), [runtime/driver](evidence/v093-performance-study-2026-10-21/board-runtime-supplement.json) e [cache/limiti termici/hash grafici](evidence/v093-performance-study-2026-10-21/board-platform-supplement.json); [istruzioni ripetibili e limiti](evidence/v093-performance-study-2026-10-21/README.md). In quell'inventario accesso SSH in sola lettura, nessuna attivazione tema/navigazione/Start/Pausa/installazione/cambio governor o riavvio. Enumerati OpenCL/Vulkan in processi separati, senza kernel di confronto. Nel completamento (§14) sono state aggiunte sonde CPU headless con dati temporanei e una lettura SQLite reale `mode=ro`: nessun display o dato di produzione modificato.

Quattro campioni passivi distanti 2 s, circa 6 s complessivi, dalle **19:54:42 alle 19:54:49**; supplemento dalle **19:56:31**. Il supplemento trova `home.clock`, Apple Calm, heartbeat pronto con età circa 0,58 s e PID GUI 207984. Nel campione iniziale non ci sono learner/writer attivi nel cgroup. Non è una prova di navigazione o apprendimento: il campione non quantifica il collo di bottiglia delle viste pesanti.

Il servizio conserva MainPID **207975**, `active`, `NRestarts=0`. Questi dati provano continuità del servizio nel perimetro osservato; non dimostrano leggibilità del pannello, latenza HID o FPS ottici.

### 2.1 Correzioni delle basi storiche

Lo [studio fluidità dell'11 ottobre](v09-fluidity-and-performance-optimization-study.md) riporta T527, quattro Cortex-A55 e Mali-G57. **Questa descrizione non corrisponde al target oggi interrogato**. Non usarla per scelte di istruzioni, driver o divisione CPU/GPU/NPU. Mantenerla come documento storico con rettifica; anche le sue ipotesi di codice richiedono nuova verifica.

Il nome host `orangepizero3w` non identifica da solo la board fisica. Il device tree dichiara `xunlong,orangepi-4-pro` / `arm,sun60iw2p1`; CPU, GPU e runtime corrispondono al profilo A733 già verificato negli audit precedenti. L'etichetta commerciale esatta e la capacità RAM nominale richiederebbero etichetta/fattura o ispezione fisica: qui registriamo ciò che il sistema espone. Non deduciamo un modello differente dal solo hostname o dal solo device tree.

## 3. Hardware, istruzioni e stack disponibili

| Risorsa | Osservazione attuale | Implicazione |
| --- | --- | --- |
| OS/kernel | Debian 13, ARM64, `6.6.98-sun60iw2`, kernel PREEMPT | Ottimizzare su questo BSP; un kernel upstream più recente non prova compatibilità display/acceleratori |
| CPU0–5 | MIDR parte `0xd05`, Cortex-A55; capacità kernel 385; massimo 1,794 GHz | Buoni candidati per I/O, housekeeping e lavoro parallelo indipendente |
| CPU6–7 | MIDR parte `0xd0b`, Cortex-A76; capacità 1024; massimo 2,002 GHz | Favorire percorsi sensibili alla latenza; non sono otto core equivalenti |
| Governor CPU | `cpufreq-dt`, `schedutil`, minimo 416 MHz; `performance` disponibile | Confrontare latenza di salita di frequenza e prestazione sostenuta, senza assumere che un campione a bassa frequenza sia un difetto |
| ISA | `fp`, `asimd`, `fphp`, `asimdhp`, `asimddp`, `atomics`, AES/PMULL/SHA/CRC, fra gli altri | SIMD NEON/ASIMD e dot product disponibili; vantaggio dipende da algoritmo e dtype |
| NumPy SIMD | NEON/ASIMD, ASIMDHP; SVE e ASIMDFHM non rilevate | Nessun piano basato su AVX, CUDA o SVE per questo target |
| RAM Linux | `MemTotal=5.995.824 KiB`, circa **5,72 GiB** | Ampio spazio per cache/preallocazione; non equivale alla quantità nominale saldata |
| Storage/swap | root ext4 su `mmcblk1`, supporto da 29,3 GiB; zram circa 2,9 GiB | Separare latenza di SD, encoding e commit. Zram è RAM compressa, non RAM fisica aggiuntiva |
| GPU | PowerVR B-Series BXM-4-64 MC1; EGL/GLES proprietari `24.2.6603887` caricati nella GUI | Accelerazione grafica effettivamente usata dal processo, con DRM/KMS |
| Rendering attuale | `QSG_RHI_BACKEND=opengl`, `eglfs_kms`, `QSGRenderThread`; framebuffer DRM 960×640 XR24, modo KMS 60 Hz | Conservare questo percorso come riferimento. Non è rendering X11/GLX software; refresh del modo e FPS del contenuto restano distinti |
| OpenCL | GPU PowerVR enumerata; piattaforma/dispositivo 3.0, linguaggio OpenCL C 1.2, FP16/FP32, niente FP64 | Compute possibile con backend esplicito e feature query; OpenCL 3.0 non rende automatiche tutte le feature opzionali |
| Memoria OpenCL | Unified memory dichiarata | Non dimostra assenza di copie, flush, sincronizzazione o contesa DDR |
| Vulkan | GPU fisica con API 1.3.277 e driver `24.2@6603887`; loader 1.4.309 | Versioni loader/dispositivo distinte; non prova convenienza della migrazione del renderer |
| GPU devfreq | 400/600/800/1008 MHz esposti; `simple_ondemand`; lettura corrente 400 MHz | Tabella da verificare contro clock reali e driver; non è una misura della frequenza effettiva durante ogni frame |
| NPU devfreq | 492/852 MHz, governor `performance`, lettura 852 MHz; modulo `vipcore` presente | Capacità presente; questo inventario non riesegue inferenze né misura utilizzazione NPU |
| Python/PySide/Qt | Python **3.13.5**, GIL attivo; PySide6 **6.8.2.1**, Qt **6.8.2** | Thread Python adatti all'I/O; parallelismo CPU Python richiede processi o nativo che rilasci il GIL |
| Numerico/build | NumPy **2.2.6**, OpenBLAS **0.3.29** ILP64/DYNAMIC_ARCH; GCC **14.2.0** | Build e librerie native già disponibili; numero di thread BLAS effettivo da misurare per processo |
| Servizio | nice 0, nessuna affinità configurata, `MemoryMax/High=infinity` | Non esiste già un tetto RAM da rimuovere; priorità massima utile da cercare con A/B |

Le feature ARM vanno controllate attraverso le capacità esposte dal sistema, non dedotte dalla sola famiglia commerciale: [Linux ARM64 hwcaps](https://docs.kernel.org/6.6/arch/arm64/elf_hwcaps.html). Per nuove build l'insieme di istruzioni deve restare valido sui core sui quali il codice può essere eseguito.

### 3.1 Limiti e anomalie della telemetria

- PVR riporta **GPU Utilisation 1505%** in una lettura. Il dato è fuori dominio: non convertirlo in percentuale, non limitarlo artificialmente a 100, non ricavarne margine libero. Anche `runtime_status=suspended`, frequenza 400 MHz e `trans_stat` senza transizioni non bastano a concludere GPU inutilizzata; la GUI ha librerie/device hardware aperti e un framebuffer allocato dal render thread. Serve correlazione fra eventi grafici e contatori con semantica verificata.
- `CONFIG_PSI` e `CONFIG_UCLAMP_TASK` sono disabilitate. `/proc/pressure/*` è assente: PSI e `CPU*UtilizationClamp` non sono strumenti immediatamente utilizzabili. Non proporre un valore uclamp come intervento operativo senza cambiare e qualificare il kernel.
- Cgroup v2 disponibile: controller `cpu` nel parent, ma non abilitato in `system.slice/cgroup.subtree_control`; file `cpu.weight/cpu.max` assenti nel servizio. `CPUWeight` richiede l'attivazione del controller tramite la configurazione systemd, da verificare dopo applicazione. `cpuset` non è disponibile a questo livello: `AllowedCPUs` non va assunto funzionante nello stato attuale. L'affinità per task è una strada diversa, da provare separatamente.
- `perf` non installato; `CONFIG_PERF_EVENTS=y` non dimostra accessibilità o completezza dei contatori PMU. `threadpoolctl` assente: il massimo 64 thread della build OpenBLAS non è il numero di thread attivi della GUI.
- Il primo probe cerca anche `theme-runtime-status.json`, assente: il supplemento legge correttamente l'heartbeat nel `/tmp` privato del servizio, attraverso `/proc/<supervisor>/root`. Non è un guasto del lifecycle.
- Il glob delle policy nel JSON include la directory globale `schedutil`, con campi mancanti: le policy CPU sono soltanto `policy0` e `policy6`. I pattern `dpkg-query` parzialmente senza corrispondenza non dimostrano assenza delle librerie pip/vendor: valgono mappe del processo e metadati dell'interprete reale.

Temperature nel campione circa 47–51 °C, cooling state 0. Nessuna conclusione sul throttling dopo ore di carico. RSS GUI finale del campione circa **449 MiB**, cgroup circa **549 MiB** inclusi processi/cache contabilizzati: non sommare questi numeri. CPU della GUI circa **0,33% di un core** sui soli 6 s; `%CPU` di `ps` è una media dalla nascita e non è confrontabile direttamente. Non presentare questo riposo come misura di gara/training o miglioramento rispetto alle release precedenti.

Il supplemento cache/termica delle **20:03:43** fotografa anche gli hash dei cinque binari grafici principali e root ext4 `noatime,commit=30`. Il kernel espone livelli cache ma non dimensioni, line size e associatività: non inventare una dimensione o un layout di cache condivisa da queste sole directory. I trip della zona CPU veloce sono 55/90 °C passivi e 110 °C critico, con isteresi dove configurata: non sono temperature consigliate né dimostrano un evento termico attuale. Prima di portare governor al massimo correlare cooling, clock reali e code dei frame. Banda/clock DDR effettivi, alimentazione e raffreddamento nominali rimangono da qualificare; un microbenchmark di banda sarebbe un esperimento successivo.

## 4. Cosa il codice fa già e dove studiare

L'[audit con hash delle sorgenti](evidence/v093-performance-study-2026-10-21/source-audit.json) fissa i file ispezionati. Le righe seguenti descrivono struttura e candidati; **non attribuiscono percentuali di tempo alla rc.28 senza profiling**.

| Area/sorgenti | Già presente | Candidato v0.9.3 e prova decisiva |
| --- | --- | --- |
| `dashboard/run.sh`, `os/system/smartpc-dashboard.service` | EGLFS/KMS, backend OpenGL, supervisor, cache directory, processo dedicato | Priorità/frequenze e binding librerie; confronto dopo reboot con stesso payload |
| `dashboard/state.py` | Segnali per dominio e cache dei riepiloghi | Contare invalidazioni, ricostruzioni e quantità di dati per refresh reale |
| `dashboard/components/PublicContextAdapter.qml` | Proiezione per rotta/dominio, sospensione renderer nascosti, pubblicazione aggregata via `Qt.callLater`, stream scena Gioco | Cercare dipendenze ampie rimaste: epoch, stile, navigation e campi copiati quando non cambiano |
| `dashboard/theme_api.py`, `theme_contexts.py` | DTO validati, confronto differenze, riuso campi, binding diretto della scena | Misurare normalizzazione, confronto ricorsivo, conversioni QVariant e allocazioni per transazione; usare revisioni soltanto se mantengono gli stessi contratti |
| `dashboard/components/ViewHost.qml` | Loader asincrono, renderer trattenuti/riusabili, commit e lifecycle | Cache più ampia/prefetch selettivo con RAM disponibile; contare hit/miss, oggetti vivi e invalidazioni su cambio tema |
| `MiniHistory.qml`, `NetworkHistoryChart.qml` Apple | Nessuna preparazione punti quando nascosti, Canvas aggiornato su cambiamento; dati mancanti puliti nel componente già corretto | Confrontare costo visibile, proiezioni per pixel e geometria scene graph soltanto se il grafico domina |
| `OutlineIcon.qml` Apple | Atlante PNG e `Image.cache=true` | Conservare e misurare upload/memoria: non rimpiazzare icone già ottimizzate con disegno JS per frame |
| `dashboard/game.py` | Processo `spawn` soltanto dopo Start, coda scena max 2, ultimo frame, poll 33 ms / pausa 250 ms; `sceneChanged` distinto | Timeline ricezione→pubblicazione→consumo→posa. Un poll a 33 ms e presenter a 30 Hz possono aggiungere attese: correlare prima di cambiare clock o trasporto |
| `GameService.snapshot/_refresh/stop` | Stato e dossier ricostruiti su eventi; stop con attesa esplicita fino a 10 s in condizioni di chiusura | Misurare ACK→refresh e percorso stop/uscita. Non chiamare `join` nel normale percorso interattivo se il profiler dimostra blocco; conservare ACK/durabilità |
| `game_presentation.py`, `presentations/GameVisual.qml` | Presenter monotono 30 Hz, interpolazione; FrameAnimation alternativo su richiesta | Rimuovere allocazioni/lookup dalle pose; confronto 30 stabile→60 presentazione, con ritmi fisici e learner invariati |
| `game_worker.py` | Processo nice 10, BLAS/OMP/MKL a 1 nel figlio, raccolta/batch, coda limitata | Profilare raccolta, valutazioni, optimizer e snapshot separati; budget per lavoro e priorità relativa |
| `game_checkpoint_writer.py` | Processo di encoding/persistenza, un job pendente, replay via mmap e ACK reale | Restano copia del replay, preparazione checkpoint e `deepcopy` di alcuni metadati nel chiamante; misurare costo prima del writer e applicare snapshot immutabili/doppio buffer se serve |
| `game_native.c/.py`, `scripts/build-game-native.sh` | Kernel C float64 e fallback NumPy; build `-O3 -ffp-contract=off` | Confrontare algoritmo, batching, vettorizzazione e ABI senza chiamate FFI per ogni piccolo elemento |
| `weather.py`, `sport.py`, `network.py`, acquisizione restanti domini | I/O già fuori dalla GUI in diversi provider | Cercare parsing, merge, SQLite, serializzazioni e callback finali ancora sincroni; non duplicare automaticamente un processo per fonte |

I grafici Apple sono due Canvas reali nel bundle; la presenza della parola `PageCanvas` nei wrapper non prova un Canvas raster per pagina. Il bundle contiene 71 file QML, non necessariamente 71 componenti caricati contemporaneamente.

### 4.1 Evidenze storiche utilizzabili, con limiti

- [rc.22, fluidità](v09-overtaking-fluidity-report.md): kernel/caching/writer avevano ridotto lavoro specifico, ma il supplemento PPO conservava swap fino a **153,37 ms** e cinque intervalli >100 ms in 120 s. È una ragione concreta per studiare le code lunghe; non è una misura nuova sulla rc.28.
- [GPU/NPU del 14 ottobre](game-gpu-npu-parallel-study.md): raggi sintetici 32 auto/512 segmenti, CPU nativa su CPU7 **0,815 ms**, GPU completa **1,031 ms** mediane. Compute GPU funzionante, ma quel caso favoriva la CPU; il solo tempo kernel non determina la scelta.
- Nello stesso studio, confronto storico della rete **68→16→2**: batch1 CPU **43,67 µs**, NPU completa **61,33 µs**; batch32 CPU **97,96 µs**, NPU **116,04 µs**. Non trasferire questi numeri alle attuali reti a due esperti da 64 unità o al training: modello, precisione e profilo sono diversi. La rc.28 richiede un nuovo confronto soltanto se il profiler trova l'inferenza rilevante.
- [Apple rc.19](apple-calm-recovery-performance-report.md): eliminato lavoro invisibile e preservata la parità visiva; nessuna accelerazione globale certificata. Non riproporre questi interventi come ancora da implementare.

## 5. Divisione proposta fra CPU, GPU e NPU

| Attività | Esecutore preferito | Condizione per spostarla |
| --- | --- | --- |
| Input, focus, navigazione, avvisi urgenti, commit minimo dei modelli | Thread GUI CPU, corsia di latenza prioritaria | Mantenere ordine e thread affinity Qt; preparazione pesante fuori dal thread |
| HTTP/WebSocket, file/cache, parsing e riconciliazione | Worker I/O CPU; processo se il parsing tiene il GIL abbastanza a lungo | Misura callback→frame e costo IPC, senza degradare freschezza/avvisi |
| Rendering testi, immagini, geometria e compositing | Qt Quick/scene graph → GPU | Conservare la GPU disponibile per i frame; preparazione geometria CPU dove richiesta da Qt |
| Trasformazioni puramente visive | Animazioni Qt/render thread quando applicabili | Nessun binding/logica che richieda il valore intermedio sulla GUI; parità del movimento |
| Fisica, sensori, regole, policy piccole | CPU nativa/NumPy batched nel processo Gioco | Compute GPU soltanto se algoritmo, precisione e latenza completa vincono insieme al rendering |
| Training PPO/SAC/TD3 attuale | CPU NumPy, con parallelismo selettivo | GPU richiede backward/optimizer espliciti; NPU forward non implementa il training |
| Inferenza di un modello congelato abbastanza grande | CPU come baseline, NPU candidata | Grafo compilabile, qualità equivalente, ammortamento conversione/caricamento, costo completo inferiore |
| Encoding/hash/SQLite/fsync/checkpoint | Processo writer CPU | Snapshot coerente, coda limitata, commit durevole e ACK; niente false conferme |
| Video/immagini futuri | Valutare codec/VPU/G2D dedicati quando esiste il contenuto | Non aggiungere lavoro per occupare unità; questa Dashboard non ha un carico video da ottimizzare oggi |

CPU6/7 sono un candidato per GUI/rendering; CPU0–5 per acquisizione/writer e raccolta parallela, lasciando libertà al learner dove rende meglio. È **una variante sperimentale**, non l'assegnazione definitiva: fissare GUI e render sugli stessi due core può creare contesa, escludere il learner dai core veloci può peggiorare preview e latenza, mentre una maschera ereditata dal servizio può limitare anche tutti i figli. Misurare affinità per TID/processo e verificare eredità/riavvio.

La macchina condivide RAM, banda DDR e limiti termici fra acceleratori. Un kernel compute più rapido isolatamente può peggiorare i frame. Il vantaggio va misurato nella sessione mista.

## 6. Linguaggi, compilazione e istruzioni

### 6.1 Scelta dello stack

| Opzione | Decisione preparatoria | Motivo e criterio |
| --- | --- | --- |
| Python/PySide6 + QML | Conservare come architettura principale | Contratti, provider e temi esistono; il costo da ridurre è quello misurato sul percorso critico |
| C/C++ per numerico o QQuickItem/QSGGeometry | Prima estensione nativa da considerare | Confini piccoli, array contigui, poche chiamate, ownership esplicita; confronto contro NumPy/batch |
| Cython | Alternativa per loop Python tipizzati | Prototipo se riduce costo totale e mantiene semplice build ARM64/rollback |
| Rust | Possibile libreria C ABI, senza priorità automatica | Beneficio deve venire da algoritmo/memoria, non dal nome del linguaggio; aggiunge toolchain/integrazione |
| Riscrittura completa C++ | Non selezionata ora | Prima applicare Amdahl al tempo realmente speso in Python e stimare il costo di migrazione dei servizi/tema |
| PyPy, Python senza GIL, Numba/JIT aggiuntivo | Nessun cambio di default | Qualificare compatibilità PySide/Shiboken/NumPy/ARM, startup e disponibilità binari; GIL-free non risolve il thread GUI Qt |
| QML compilato con CMake | Candidato dopo dati/GUI | Prova su un modulo stabile, distribuzione versionata e confronto freddo/caldo |

Con GIL attivo, aumentare thread per loop Python non garantisce parallelismo CPU. Le chiamate native/NumPy possono rilasciarlo, ma vanno misurate per il percorso concreto. I processi hanno costi di IPC e copie; preallocazione e batch devono precedere l'aumento dei processi. [Python 3.13, threading](https://docs.python.org/3.13/library/threading.html), [NumPy, configurazione dei thread BLAS](https://numpy.org/doc/stable/reference/global_state.html).

### 6.2 Build ARM mirata

Il kernel C esistente usa già `-O3` e disabilita contrazione FP. Confrontare separatamente: compilazione corrente; tuning big.LITTLE con `-mtune=cortex-a76.cortex-a55`; variante ISA esplicita compatibile con le feature verificate; eventuali kernel NEON. `-mtune` e `-march/-mcpu` hanno ruoli differenti: non imporre istruzioni disponibili solo su un sottoinsieme dei core. Verificare con GCC 14 locale quali combinazioni sono accettate e controllare il codice generato. [GCC 14.2, opzioni AArch64](https://gcc.gnu.org/onlinedocs/gcc-14.2.0/gcc/AArch64-Options.html).

Prime opportunità: eliminare ripetizioni, raggruppare vetture/segmenti, migliorare l'indice spaziale, rendere contigui input/output, ridurre allocazioni e rami. Poi usare report di vettorizzazione (`-fopt-info-vec-optimized`, `-fopt-info-vec-missed`) e disassemblato. LTO/PGO sono confronti successivi, con profilo rappresentativo e build riproducibile: non accelerano genericamente il codice Python.

NEON può elaborare più valori per istruzione; dot product intero non accelera automaticamente fisica float64. FP16/FP32, `-ffast-math`, fusioni o diverso ordine delle somme possono cambiare contatti, soglie, RNG indiretto e traiettorie. Conservare float64 come riferimento fisico; precisione inferiore richiede prove di raggi quasi paralleli, bordi, giri multipli, decisioni e risultati. Un guadagno numerico che cambia silenziosamente il protocollo non è un'ottimizzazione equivalente.

BLAS: confermare i thread effettivi prima di cambiarli. Confrontare 1/2/4 soltanto sul learner e a matrici attuali; il processo già imposta 1. Estendere a tutta la GUI senza prova può introdurre thread inattivi o contesa. La build OpenBLAS `neoversen1` non dimostra che ogni routine usi un kernel ideale per tutti i nostri core.

### 6.3 QML e cache compilate

Qt distingue cache bytecode/unità compilate e generazione di funzioni C++ con gli strumenti di build; una `.qmlc` non equivale a tutta l'app nativa. `qt_add_qml_module` è la via documentata; `qmlsc` appartiene alle estensioni commerciali, mentre disponibilità e limiti degli altri strumenti vanno verificati sul kit scelto. Non abilitare variabili di ambiente alla cieca. [Qt Quick Compiler 6.8](https://doc.qt.io/qt-6.8/qtqml-qtquick-compiler-tech.html).

Prototipo: un modulo di shell stabile con tipi/required property espliciti e risorse locali; misurare import, istanziazione, binding e apertura calda. Conservare compatibilità col tema caricato dinamicamente, revisione bundle, fallback e riammissione. Non incorporare irreversibilmente i bundle utente nell'eseguibile.

## 7. Rendering e Apple Calm

Il render thread riduce parte del lavoro sulla GUI, ma mantiene fasi di sincronizzazione con essa. Liberare CPU totale non risolve una singola callback lunga nel thread GUI: occorre misurare il percorso fino al frame. [Scene graph Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html).

**Candidati grafici:** separare geometria e sfondi statici dai dati dinamici; aggiornare soltanto modelli/campi cambiati; mantenere stabili delegati e texture; contenere clip, trasparenze sovrapposte e render target intermedi. `layer.enabled` aggiunge memoria e lavoro offscreen: adottarlo solo per sottostrutture costose che si riusano. Valutare batch/overdraw con gli strumenti Qt. [Renderer Qt Quick](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph-renderer.html).

Canvas.Image disegna su immagine e gli aggiornamenti possono richiedere upload di texture: non è geometria vettoriale interamente sulla GPU. Nei grafici Apple a bassa frequenza può essere già la scelta giusta. Se i punti dominano, confrontare proiezione/campionamento per larghezza pixel preservando minimi, massimi e buchi, poi Shape o QQuickItem/QSGGeometry con buffer riusati. **QQuickPaintedItem in Qt 6.8 non garantisce pittura GPU**: spostare QPainter in C++ può ridurre JS ma lasciare raster/upload. [Canvas](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html), [QQuickPaintedItem](https://doc.qt.io/qt-6.8/qquickpainteditem.html).

Gli Animator possono eseguire trasformazioni sul render thread; i valori delle proprietà QML non seguono tutti i passi intermedi. Usarli soltanto per transizioni che non guidano hit testing, focus, sensori o stato applicativo. Non sostituire in blocco le animazioni delle auto. [Animator Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-animator.html).

Il presenter Gioco corrente è **30 Hz per scelta del software**. Un pannello a 60 Hz o 60 swap/s con pose duplicate non produce 60 aggiornamenti del movimento. La variante a FrameAnimation non è già una soluzione: i confronti rc.22 non l'avevano favorita. Per una candidata a 60, campioni fisici, interpolazione, timeline monotona, latenza introdotta dal buffer, camera e sensori devono restare coerenti. Nessuna variazione implicita del passo fisico o del ritmo delle decisioni apprese.

Nelle scene statiche non serve ridisegnare a 60 Hz: è corretto non produrre frame finché non cambia qualcosa. Misurare 60 Hz durante animazioni/scroll/transizioni, non forzare un timer vuoto per mostrare un contatore alto.

## 8. GPU compute, NPU e driver

### 8.1 Criterio per scegliere un acceleratore

Misurare `T_totale = preparazione + trasferimenti/flush + attese + esecuzione + readback + commit del risultato`. Separare caricamento/compilazione iniziale dal regime e ammortizzarli sul numero reale di utilizzi. Vanno aggiunti l'effetto sulla coda dei frame, la versione dei dati e la qualità numerica. Il solo tempo kernel o i TOPS di targa non rispondono alla domanda.

Per compute GPU: geometria e buffer residenti, batch sufficienti, nessun round trip per ogni raggio. Confrontare prima CPU nativa sui core veloci e algoritmo spaziale migliore; poi CPU multicore/batch; poi GPU con rendering attivo. Code Vulkan differenti non garantiscono due GPU né simultaneità hardware e richiedono sincronizzazione esplicita. [Khronos, code](https://docs.vulkan.org/guide/latest/queues.html), [sincronizzazione](https://docs.vulkan.org/guide/latest/synchronization.html).

Per NPU: l'SDK Vivante su A733 descrive conversione/compilazione ed esecuzione di inferenze, non l'esecuzione automatica del nostro training NumPy. [Radxa, guida SDK Vivante](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-sdk). Radxa è un riferimento per lo stesso SoC, non prova che l'intera immagine/SDK sia intercambiabile con la nostra board.

Esperimento NPU eventuale: copie congelate delle reti rc.28, operatori/forme e precisione supportati, toolchain con versioni/hash, confronto CPU/NPU a batch reale, prima esecuzione e caldo, qualità delle azioni e guida completa. Per pesi che cambiano servono misura del costo di conversione/commit e prova del supporto runtime: un grafo `.nb` congelato non dimostra aggiornamento online economico. **Nessun uso obbligatorio NPU per v0.9.3** se non riduce latenza o carico critico.

### 8.2 Driver: mantenere una baseline, qualificare le alternative

Il percorso attuale mescola librerie vendor sotto `/usr/lib`, EGL sotto `/usr/local/lib` e dipendenze Qt di sistema; va fotografato con hash, moduli e firmware prima di confronti. Non sostituire soltanto `libEGL` o Mesa sulla macchina di produzione: compatibilità richiede kernel, firmware, userspace, libgbm/DRM e integrazione display coerenti.

Imagination pubblica DDK più nuovi: il [DDK 25.2](https://blog.imaginationtech.com/driver-update-adds-support-for-vulkan-and-opencl-extensions) documenta nuove estensioni e memoria. Questo non fornisce automaticamente un pacchetto compatibile per il nostro BSP A733/6.6. La [pagina upstream del produttore](https://developer.imaginationtech.com/solutions/open-source-gpu-driver/) cita anche BXM-4-64 in altri SoC: è un segnale di progresso, non una certificazione della nostra combinazione A733/display/OpenCL.

Percorso driver eventuale su immagine SD alternativa/clone: inventario binari/firmware e origine → boot/display 960×640 → EGL/GLES e shader → scene Qt e temi → compute necessario → sospensione/riavvio/lifecycle → carico lungo e temperature. Confrontare prestazione e stabilità sullo stesso scenario. Migrazione Vulkan, aggiornamento Qt e aggiornamento driver sono variabili separate: una sola alla volta. Lasciare questa pista condizionale se le misure indicano colli di bottiglia GUI/IPC.

## 9. Priorità, risorse e funzionamento continuativo

### 9.1 Politica proposta da confrontare

| Variante | Intervento sperimentale | Cosa deve migliorare |
| --- | --- | --- |
| S0 | Stato attuale: nice GUI 0 / learner 10, scheduler libero | Riferimento ripetibile |
| S1 | Nice servizio/GUI moderatamente elevata, primo candidato **−5**, learner esplicitamente 10 | Code di input/GUI; verificare tutti i thread e figli, non il solo supervisor |
| S2 | Come S1, `CPUWeight` candidato **1000** contro default 100, controller abilitato da systemd | Solo contesa fra cgroup; non accelera codice quando non c'è contesa |
| S3 | CPU6–7 preferite/affinità selettiva GUI/render; maschera distinta learner/writer | Tempi critici senza perdita ingiustificata del throughput; verificare eredità delle maschere |
| S4 | Governor CPU `performance`, prima cluster veloce, poi entrambi; GPU separatamente | Code lunghe e comportamento dopo riscaldamento, con confronto temperatura/clock |
| S5 | Cache/prefetch/preallocazione più generosi senza quote CPU/RAM applicative | Aperture più rapide e meno allocazioni nel percorso critico |

Sono candidati, non configurazioni approvate per installazione. «Massima priorità» significa precedenza effettiva all'interazione, al rendering e agli avvisi rispetto a training e manutenzione. Nice −20, SCHED_FIFO/RR, isolamento `isolcpus`, governor massimi di tutte le unità e `mlockall` non sono primi passi: possono peggiorare contesa, I/O e prestazione sostenuta. Un kernel PREEMPT_RT sarebbe una sperimentazione separata, non una cura automatica del throughput.

`CPUWeight` è relativo ai fratelli del cgroup; non ordina GUI e learner che vivono nello stesso servizio. La priorità interna resta per processo/thread o richiede una struttura cgroup esplicita. Nice e frequenza affrontano problemi differenti; `performance` richiede al driver il livello massimo consentito ma non elimina i limiti termici. [systemd 257 resource control](https://www.freedesktop.org/software/systemd/man/257/systemd.resource-control.html), [Linux 6.6 CPUFreq](https://docs.kernel.org/6.6/admin-guide/pm/cpufreq.html).

Raffreddamento, alimentazione stabile e limiti reali della board vanno verificati nel carico sostenuto. Niente overclock o disattivazione delle protezioni termiche nella prima candidata. Priorità grafica non significa fermare rete, storage, watchdog, input o salvataggi da cui dipende la Dashboard.

### 9.2 Usare la RAM per togliere lavoro

Cache riutilizzabili per renderer visitati di frequente, geometrie, atlanti, dati normalizzati per revisione e punti grafico già proiettati. Preallocare buffer numerici, preview e snapshot; una coda latest-only per scene può scartare pose superate, mentre comandi e ACK durevoli devono restare affidabili. Ridurre frequenza delle copie mantenendo il dato corrente e l'ordine degli eventi.

Nessun tetto RAM arbitrario di prodotto. Le cache devono comunque avere identità/versione e una politica di rilascio: «può occupare RAM» non implica crescita infinita o accumulo di revisioni mai più usate. Misurare PSS/RSS, memoria cgroup, disponibile, fault, swap-in/out e latenza dopo cicli ripetuti. La riserva per kernel/driver/commit viene definita con queste misure, non con un requisito generico di basso consumo. Non svuotare la page cache per una presunta ottimizzazione; misurare avvio freddo separatamente.

Il salvataggio resta atomico e durevole: non togliere fsync o i controlli per guadagnare fluidità. Spostare encoding e I/O fuori dal percorso critico, preparare copie coerenti e fare backpressure. Il heartbeat è già su `/tmp` privato: non riproporre una migrazione già fatta.

## 10. Piano delle misure e scenari

### 10.1 Timeline che deve spiegare uno scatto

Registrare con clock monotono: evento input/arrivo dati → coda GUI → handler/normalizzazione → segnali e modelli → binding/layout → sincronizzazione scene graph → render/submit → presentazione osservabile. Per Gioco aggiungere produzione scena, età in coda, ricezione, consumo, campioni interpolati e posa unica.

Misurare sia **tempo CPU** sia **tempo trascorso**: un'attesa vsync è diversa da un calcolo; GPU submit è diverso da esecuzione/completamento. GUI, render e GPU si sovrappongono: non sommare indiscriminatamente durate come se ogni fase fosse seriale. Contare p50/p95/p99/massimo, intervalli >50/>100/>250 ms, frame/pose duplicate e durata degli scatti consecutivi. Riportare campioni e carico esatti.

Strumenti: profiler Python sulle sole finestre sospette; QML Profiler per binding/JS/creazione; logging scene graph e `QSG_RENDER_TIMING` per attribuzione; tracepoint/ftrace o perf soltanto dopo verifica del supporto. Il profiler QML non misura direttamente il costo interno C++: [Qt Creator, profiler](https://doc.qt.io/qtcreator/creator-qml-performance-monitor.html), [debug Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-debugging.html). Profilare in staging con logging controllato, poi ripetere la misura finale senza tracing per quantificare l'overhead. Evitare un log per frame scritto su SD.

Per la GPU confrontare tempi CPU submit, attese/fence ed eventuali timer query supportate; PVRTune solo se versione e driver consentono contatori attendibili. Per il display usare present/page-flip con semantica verificata e verifica ottica/HID. `frameSwapped`, callback Python o `glFinish` aggiunto ovunque non sono una misura universale del tempo GPU né della latenza fisica.

### 10.2 Matrice minima

| Scenario | Varianti necessarie | Evidenza |
| --- | --- | --- |
| Home/clock statico | Apple/Base/Functional, giorno/notte | Wakeup, callback periodiche, nessun polling grafico superfluo |
| Navigazione | Apertura fredda/calda, menu/impostazioni/ritorno, rotazione e input ripetuti | Latenza input→primo frame corretto, cache hit, picchi e oggetti vivi |
| Rete/grafici | Dati nominali e maturi, più serie, buchi/nessun dato, nascosto→visibile | Parità visiva, CPU paint/upload, massimo punti, corretta freschezza |
| Sport/F1/MotoGP/Casa/Account/Meteo | Snapshot piccoli/grandi, refresh simultanei, offline/ritorno e avvisi | Parsing/merge/commit separati, nessuna informazione persa o falsa Live |
| Gioco Gara | 2 e 5 piloti, camere/sensori/telemetria disponibili | Pose uniche, clock, throughput fisico, pannello/input |
| Gioco apprendimento | PPO, SAC, TD3, Tattico con checkpoint/replay maturi su copie | GUI concorrente, optimizer/valutazione/snapshot/salvataggio e ripresa |
| Lifecycle | Start/Pausa/uscita/Home/urgente/cambio tema, riapertura, writer lento/errore | ACK, fermata reale, commit e assenza di ripresa implicita |
| Continuativo | Sessione mista almeno 60 min; seguito 8–24 h | Memoria, termica, clock sostenuti, crescita oggetti, driver reset e code |

Le fixture servono alla ripetibilità. Acquisizioni reali e urgenti live hanno una qualifica separata per fonte: nessuna richiesta API aggiuntiva viene lanciata da questo studio. Il lavoro nascosto da fermare riguarda renderer/animazioni, non l'acquisizione autonoma degli avvisi necessaria anche quando Sport non è aperto.

### 10.3 Confronti equi

Congelare hash core/bundle/native, kernel/driver, preferenze, risoluzione/refresh, snapshot e copie dei piloti. Stessi input, workload e budget; warmup dichiarato, ordine A/B alternato **ABBA** e almeno tre blocchi per lo screening. Per la variante selezionata ripetere finestre più lunghe dopo riscaldamento; non comparare massimo di 120 s con massimo di 10 minuti o una release a riposo con una in training.

Una sola famiglia di modifiche per confronto. Per scheduler confrontare core realmente usati, frequenze e carico: il microbenchmark storico CPU7 dimostra quanto il posizionamento possa cambiare una conclusione CPU/GPU. Per batch/thread/compute riportare throughput e latenza delle singole risposte. Se cambia la numerica verificare anche la guida: non importa quanti FPS produce una simulazione semanticamente diversa.

## 11. Criteri di accettazione proposti per v0.9.3

Questi sono **obiettivi da confermare con la baseline F0**, non risultati già ottenuti. Se il budget nominale non è raggiunto, pubblicare il limite e mantenere il gate aperto.

| Aspetto | Target proposto | Misura necessaria |
| --- | --- | --- |
| UI/motion Apple ordinario | **60 aggiornamenti visivi/s** nei tratti animati nominali; budget 16,67 ms | Frame effettivamente presentati e cambiati; p95 ≤18,5 ms, p99 ≤25 ms, nessun intervallo >50 ms nei tratti stazionari nominali. Software come filtro, pannello/HID per la dichiarazione fisica |
| Gioco, primo gate | **30 pose/s regolari** sotto carico scelto; budget 33,33 ms | p95 ≤36,7 ms, p99 ≤50 ms; nessuna posa tardiva >100 ms nel segmento nominale sostenuto. Le attese dichiarate di caricamento si misurano a parte |
| Gioco, estensione | 60 pose/s se regge senza sacrificare fisica, input o apprendimento | Stesse prove del target 60; non chiamare 60 gli swap con pose duplicate |
| Risposta ai comandi | Candidato p95 ≤50 ms, p99 ≤100 ms per risposta visibile ordinaria | Distinguere feedback del comando dal completamento di caricamento/salvataggio; conferma ottica/HID sul pannello |
| Aperture calde | Candidato p95 ≤100 ms al primo contenuto corretto | Trace fino al frame con dati/rotta giusti, senza placeholder contato come apertura completa |
| Simulazione nominale | Rapporto simulato/reale **0,99–1,01×** quando la modalità promette tempo reale | Passi fisici e wall clock; training throughput riportato separatamente |
| Correttezza | Nessuna regressione di dati, avvisi, focus, palette/motion, checkpoint/identità | Test mirati contratti e confronto visuale su tre temi, pausa/ripresa ed errori |
| RAM/CPU | Nessun tetto di risparmio arbitrario; nessun OOM o crescita senza spiegazione | Memoria/fault/swap, latenza e throughput sostenuti. Cache inizialmente crescenti dichiarate, poi stabilità sul ciclo ripetuto |
| Sostenuto | Carico nominale senza degradazione progressiva, errori driver o restart | Frequenze/temperature/cooling correlati ai frame; 60 min e seguito 8–24 h |

Percentili software non certificano da soli la presentazione fisica. «60 fissi» richiederebbe inoltre verificare e riportare ogni deadline mancata: queste soglie sono un criterio pratico di candidata fluida, non una garanzia matematica di zero frame persi. Le animazioni brevi vanno aggregate in molte ripetizioni; la media FPS da sola non basta.

Per accettare una singola ottimizzazione: beneficio replicato sul suo obiettivo oltre la variabilità della baseline e nessuna regressione funzionale/percettiva negli altri scenari. Primo screening: miglioramento p95/p99 o throughput nell'ordine di almeno 10% dove il rumore lo consente; variazioni minori possono valere per eliminare uno scatto riproducibile. Nessun obbligo di consumare meno CPU/RAM se l'esperienza migliora; un acceleratore va scelto soltanto se migliora il risultato complessivo.

## 12. Lotti pronti per l'implementazione successiva

| Lotto | Lavoro | Uscita/decisione |
| --- | --- | --- |
| **F0 · Baseline** | Harness minimo e timeline su rc.28, tre temi, dati maturi e carico misto | Classifica dei costi e scatti con stack/causa; completare disponibilità PMU/driver/refresh |
| **F1 · GUI/dati** | Togliere blocchi, proiezioni duplicate e invalidazioni inutili; ottimizzare ACK→refresh e stop solo dove misurati | Parità contratti/dati/visiva, riduzione del tratto critico |
| **F2 · Memoria/cache** | Cache generose per rotta/revisione, preallocazione e snapshot coerenti con meno copie | Aperture calde migliori, nessun lavoro nascosto o crescita senza rilascio |
| **F3 · Sistema dedicato** | Nice/CPUWeight, topologia e governor in confronti distinti | Configurazione più veloce sostenuta con ricevuta TID/cgroup/clock; rollback esatto |
| **F4 · Nativo/render** | C/NEON dove serve, grafici QSG e QML compilato come prototipi separati; presenter 60 come variante | Conservare solo ciò che vince sul target e preserva numerica/identità |
| **F5 · Acceleratori condizionali** | Nuove reti NPU o sensori GPU soltanto se rilevanti dopo F0–F4 | Decisione positiva o negativa documentata; backend opzionale/fallback |
| **F6 · Candidata 0.9.3** | Payload finale, confronti ripetuti senza tracing, carico lungo, tre temi, input/pannello e recupero | Manifest/hash/backup/rollback, installazione soltanto nella fase autorizzata e receipt finale |

**Priorità iniziale F0→F1→F2**, poi F3 e i soli prototipi F4 motivati dai risultati. Non iniziare dalla sostituzione del driver o dalla riscrittura totale. Gli interventi sui servizi, codice runtime, sistema o scheda richiedono la fase di attuazione: la richiesta corrente è lo studio preparatorio.

Tutti i checkpoint/campioni/certificati di test restano su copie isolate; nessun nuovo training o reset dei piloti reali per misurare FPS. Se si propone di cambiare fisica, ritmo decisionale o ricetta, quel lavoro esce dall'ottimizzazione equivalente e richiede analisi/protocollo proprio. Theme API/versione Apple cambiano soltanto se l'implementazione effettiva lo richiede; il tema corrente non viene riattivato o rigenerato da questo documento.

## 13. Analisi chiusa e verifiche dell'esecuzione

La struttura hardware/software, i limiti degli strumenti e le strade disponibili sono accertati. Il completamento (§14) identifica un costo CPU concreto nel percorso metadati attuale, sufficiente a dare priorità a reader/proiezioni/cache; non attribuisce ogni scatto dell'intera Dashboard a quell'unica causa.

Restano come prove previste dal piano: timeline end-to-end su rc.28 sotto carico; contatori GPU attendibili o tempi alternativi; comportamento termico sostenuto; thread BLAS effettivi; intero checkpoint maturo; beneficio delle varianti cache/scheduler; confronto 30/60 pose; eventuale convenienza NPU sui modelli attuali; compatibilità di un driver alternativo solo se necessario; verifica ottica/HID. Sono attività di implementazione e qualificazione con procedure e gate nel [piano esecutivo](v093-dashboard-performance-execution-plan.md), non decisioni architetturali lasciate all'utente.

La scelta è **prima liberare il percorso che produce il frame, poi dargli precedenza e dati pronti in RAM; usare gli acceleratori sui carichi per cui superano davvero la CPU senza disturbare il rendering**. Implementazione, installazione e qualifica restano aperte; l'analisi preparatoria non viene confusa con il loro esito.

## 14. Completamento: misure, attribuzione e priorità definitiva

### 14.1 Metodo delle sonde aggiuntive

Eseguiti gli stessi corpi di codice esistenti su PC (Python 3.12.13/x86_64) e scheda (3.13.5/ARM64), Qt 6.8.2/PySide 6.8.2.1/NumPy 2.2.6. Gli hash comuni PC/board delle sette sorgenti della prima sonda coincidono. Processi di studio separati nice 10, BLAS a un thread, nessun vincolo di core/governor imposto. Non confrontare il rapporto PC/ARM come rapporto fra soli processori: interprete, scheduler e piattaforma sono differenti.

Le sonde sintetiche creano SQLite/settings/cache solo in directory temporanee eliminate alla fine; niente Start, training, provider o EGLFS. I tempi wall includono scheduling nel sistema in uso e hanno pochi campioni, dichiarati nei JSON. I profili cProfile aggiungono overhead: servono per l'attribuzione, non sostituiscono i campioni non profilati. Non sono prove p99, energia, FPS o throughput sostenuto.

La sonda dei metadati correnti **non costruisce GameStore sulla directory reale**: usa metodi di lettura attraverso un facade con connessione SQLite `mode=ro` in una snapshot consistente, senza migrazioni. La GameService di supporto ha store/settings privati, poi legge il facade; nessun payload, nome, policy o checkpoint viene esportato nei risultati. La connessione riusata e nice differiscono dal processo GUI reale: il risultato quantifica il lavoro esistente, non una latenza ottica o il massimo di produzione. I processi di studio non hanno fermato la GUI.

### 14.2 Costo reale dei metadati attuali — priorità P0

[Inventario SQL](evidence/v093-performance-study-2026-10-21/board-store-metadata.json): cinque piloti, 16 sessioni, 635 eventi complessivi, inclusi 110 di valutazione con circa **5,28 MB** di payload. I curricula dei quattro learner occupano circa **1,09 / 1,02 / 0,89 / 0,50 MB**, con **20 / 20 / 6 / 0** valutazioni. Non sono mille valutazioni per pilota.

[Letture temporizzate ARM](evidence/v093-performance-study-2026-10-21/readonly-metadata-arm.json), cinque campioni non profilati per misura dopo riscaldamento:

| Operazione/dati attuali | Mediana ARM | Interpretazione |
| --- | ---: | --- |
| `GameStore.drivers()` per l'intera rosa | **103,51 ms** | Letture e decodifica della rosa, non cinque volte questo costo |
| `_refresh`, pilota numero 2 | **220,19 ms** | Include lista, storico, classifica e dossier |
| `_refresh`, pilota numero 3 | **174,58 ms** | Stesso percorso, diverso dossier |
| `_refresh`, pilota numero 4 | **153,96 ms** | Costo anche con sole sei valutazioni nel curriculum |
| `_refresh`, pilota numero 5 | **143,37 ms** | Costi comuni restano anche con zero valutazioni nel curriculum |
| Getter snapshot Python, numeri 2/3/4/5 | **4,48 / 4,04 / 1,52 / 0,13 ms** | Esclude conversione QVariant→QML e rendering |
| Dossier del solo pilota 2 | **86,65 ms** | Lettura/decodifica eventi e costruzione dello storico |

Il profilo `_refresh` del pilota 2 dura circa 235 ms con overhead: **212 `json.loads`, circa 175 ms cumulativi di decodifica**; `drivers` circa 100 ms e dossier circa 92 ms, con tempo annidato. Le durate profilate si sovrappongono: non sommarle. `_refresh` è richiamato direttamente dal controller/ACK nel thread GUI: questo lavoro è un bersaglio concreto per togliere blocchi, anche prima della prova grafica completa.

**Decisione:** reader/proiezioni in processo separato e cache per revisione; fuori dalla GUI query/JSON/aggregati/dossier, verso QML soltanto i dati necessari e coerenti. Spostare lo stesso JSON in un thread o rispedire interi curricula via pickle non dimostra di aver tolto il costo GIL/conversione. La verifica decisiva è il callback GUI e la catena ACK→metadati→frame, non il solo tempo del nuovo reader.

### 14.3 Crescita dello storico e limiti reali dei progressi

[Sonda di crescita ARM](evidence/v093-performance-study-2026-10-21/store-growth-arm.json): store temporaneo, rispettivamente 0/100/1.000 sessioni e altrettanti eventi sintetici; ogni sessione ha payload di 1.003 byte. Mediane `_refresh` **12,98 / 32,16 / 192,50 ms**, dossier **6,42 / 17,87 / 121,55 ms**. È crescita di uno store costruito per la prova, non la misura dello store reale (che ha 16 sessioni e payload differenti). Il problema strutturale è che `sessions()` legge/decodifica tutto prima di filtrare e `driver_events()` materializza tutti gli eventi selezionati. Filtri SQL, letture mirate, paginazione e aggregati invalidati preservano l'intero storico senza rileggerlo continuamente.

Sul curriculum semplice sintetico da 20/40 valutazioni, lo snapshot costa circa **1,27 / 2,34 ms** ARM. `_progress` richiama `exercise()` cinque volte per valutazione; calcolarlo una sola volta è un candidato semplice, ma non sostituisce F1.1. Lo stress a 1.000 valutazioni dà circa **49,02 ms** e 5.000 chiamate: **fuori dai limiti normali attuali**, pari a 20 residuali e 40 Academy. Non rappresentarlo come causa già dimostrata della produzione.

### 14.4 Scena pubblica, snapshot numerici e writer

[Sonda ARM](evidence/v093-performance-study-2026-10-21/critical-paths-arm.json): `factory.update(context, {'scene': ...})` su cinque vetture sintetiche costa **0,259 ms** mediano; aggiungendo 100 righe di metadati sintetici sale a **3,645 ms**. Nel profilo del caso pesante dominano `deepcopy`, validazione/copia del campo e confronto; manca la conversione/rendering QML. Non è il vero pacchetto Gioco e non dimostra che la produzione invii quelle 100 righe. Prima misurare i byte/campi reali; poi proiezione minima e, solo se serve, ownership/copia singola o buffer numerici con identità e invarianti preservate.

Replay SAC sintetico completo **32.768×192 float64 = 50.331.648 byte (48 MiB)**, nessun passo di training:

| Fase separata | Mediana ARM | Scopo |
| --- | ---: | --- |
| `learner.checkpoint(deferred='writer')` | **8,19 ms** | Array→liste di pesi/critic/optimizer; replay consegnato per cattura differita |
| Copia in array preallocato | **6,93 ms** | Costo della copia, non IPC/fsync o ACK |
| Encoding replay fuori preview | **2.773 ms** | Codifica sintetica in processo di sonda; non una latenza di frame |

Il profilo della cattura individua 15 `tolist` come componente principale. Il writer attuale evita encoding/persistenza sul processo preview, ma non annulla preparazione e copia. F2.2 deve misurare il checkpoint intero ed eventualmente spostare conversioni nel writer usando snapshot sigillati/preallocati, conservando durabilità. Non rendere sinonimi «writer asincrono», «zero costo di cattura» e «salvataggio immediato».

### 14.5 Navigazione locale e strumenti disponibili

Eseguito il Main reale Apple con fixture offline e input sintetico su PC offscreen/software: **177 azioni, zero richieste di rete e zero messaggi QML raccolti**. [Grezzi](evidence/v093-performance-study-2026-10-21/navigation-pc-apple), [riepilogo ricalcolato](evidence/v093-performance-study-2026-10-21/navigation-pc-summary.json). Aperture/argomenti hanno picchi circa **248/231 ms**; le liste Sport circa **17,44 ms** mediani. Sono tempi di invio software che includono il protocollo di pumping, non latency del pannello o GPU; campioni piccoli per alcune categorie, nessuna qualifica statistica generale.

La vecchia formula percentile del runner sottostima la coda nei gruppi piccoli: i risultati nuovi usano nearest-rank e conservano tutti i record. Correggere l'harness in F0, non il runtime per adattarlo alla formula.

[Readiness della board](evidence/v093-performance-study-2026-10-21/board-readiness.json): **FTRACE non compilato** oltre a PSI/uclamp già assenti. Non basta montare debugfs/tracefs. I valori clock framework letti sono GPU0 400 MHz, PLL GPU 1.008 MHz, DRAM0/MBUS 600 MHz, PLL DDR 2.400 MHz: nomi e conteggi di enable diversi non certificano frequenza fisica o banda effettiva. La scelta operativa è strumentazione userspace/Qt; nessuna ricompilazione kernel necessaria per iniziare a correggere i blocchi JSON.

### 14.6 Lista ordinata del da farsi

1. **F0:** fissare baseline e oracoli corretti; EGLFS nella finestra esecutiva, senza confondere p95 storico e nuovo.
2. **F1/P0:** reader/proiezioni/cache dei metadati, query e dossier su richiesta. È il contributo costoso verificato sui dati attuali.
3. **F1/P1 + F2:** eliminare lavoro ripetuto nei progressi, mantenere piccole le scene, attivare/qualificare il riuso renderer e alleggerire la cattura prima del writer. Il supporto cache esiste ma il default `cacheLimit=0` non dimostra una cache calda attiva.
4. **F3:** priorità, core e governor misurati sulla candidata migliorata. `CPUWeight` richiede solo configurazione systemd coerente e verifica: il manager abilita il controller quando richiesto, senza scrivere manualmente la gerarchia.
5. **F4:** 60 Hz visuali e nativo/grafici/QML sui soli colli di bottiglia rimasti.
6. **F5 condizionale:** GPU compute/NPU/driver solo con contributo e vantaggio completo dimostrati; è valido chiudere senza un nuovo backend.
7. **F6:** stesso artefatto finale, carico lungo, preservazione dati, installazione/reboot e gate fisici distinti.

Il [piano esecutivo](v093-dashboard-performance-execution-plan.md) specifica per ogni lotto file, implementazione scelta, dipendenze, prove, criteri di uscita e rollback. L'analisi preparatoria è conclusa: il lavoro rimanente è l'esecuzione controllata e la sua qualificazione.
