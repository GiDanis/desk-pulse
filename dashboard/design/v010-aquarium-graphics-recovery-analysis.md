# Acquario 3D: analisi della regressione grafica e piano di correzione

29 ottobre 2026 · analisi completata, causa del difetto fisico ancora da isolare.

**Seguito esecutivo aggiornato:** [rc.4 installata e verifica nativa/reboot](v010-aquarium-graphics-fix-report.md). Riprodotti disallineamento delle interrogazioni GL e scanout vuoto con cache shader; ponte EGL e bypass cache attivi. La rete è tornata disponibile. G0–G4 eseguiti, G5 completato per installazione/120s/rientri/reboot software; pannello confermato dall’utente, ottica/tasti fisici/durata estesa aperti. I paragrafi seguenti conservano il punto di partenza dell’analisi.

Il primo intervento deve verificare l’integrazione grafica Qt/EGL/GLES. Non ci sono ancora prove che occorra ridurre il numero di pesci o cambiare i modelli. Produzione lasciata in recupero 2D; durante questa analisi nessun riavvio del servizio, reboot, installazione di pacchetti o modifica alle preferenze.

## Fatti e limiti

- Dopo il reboot OS della 0.10.2-rc.2 l’utente ha visto glitch e contenuti illeggibili. Il ritorno al 2D, con riavvio dell’app, ha ripristinato la leggibilità fisicamente confermata.
- Il recupero esclude insieme due cambi: preload della GLES del produttore e richiesta esplicita del contesto ES3. Non distingue quale dei due sia necessario al difetto; il riavvio stesso è un’ulteriore variabile.
- Il launcher attiva il preload prima del supervisor. `AquariumService` configura il formato globale all’avvio, anche quando è aperta Home. Il problema può quindi precedere la visualizzazione dei pesci.
- La board è ancora nello stesso boot del recupero. Home pronta, heartbeat recente, servizio attivo e NRestarts=0: [lettura corrente](evidence/v010-aquarium-graphics-analysis-2026-10-29/board-readonly-state.json).
- Le prove precedenti hanno misurato callback e sei draw call; non hanno qualificato la resa fisica dopo reboot. Il campo `glContext` del banco è inizializzato a `{}` e non viene popolato. La versione richiesta `[3,0]` non dimostra quella effettiva.
- Non abbiamo una cattura dello scanout durante i glitch. La cattura raccolta dopo il recupero riguarda soltanto il 2D e non consente un confronto prima/dopo.

## Verifica isolata delle librerie sulla board

Due processi diagnostici separati hanno importato QtGui e risolto i simboli, con e senza preload. Nessuna QGuiApplication, inizializzazione EGL, finestra o acquisizione del display. `LD_DEBUG=bindings` e `LD_BIND_NOW=1` documentano le risoluzioni di QtGui, oltre alla ricerca dei simboli con ctypes.

| Verifica | Senza preload | Con preload GLES del produttore |
| --- | --- | --- |
| Tipo di build dichiarato da Qt | `LibGL` | `LibGL` |
| Binding QtGui di `glGetString` e `glGetIntegerv` | `libGL.so.1` | `/usr/local/lib/libGLESv2.so.2` |
| Risoluzione tramite `eglGetProcAddress` | `libglapi` del produttore | `libglapi` del produttore |

QtGui dipende da `libOpenGL` e `libGLX`; EGL e GBM effettivamente mappate provengono da `/usr/local/lib`. La EGL locale non espone `__egl_Main`, ingresso previsto per un ICD EGL GLVND. Il solo contenuto delle mappe non prova un’incompatibilità, ma documenta la combinazione da verificare.

La prima sonda non trovava i simboli nello scope globale di Python: QtGui era caricato localmente. È conservata come tentativo fallito. La sonda corretta promuove le dipendenze nello scope globale del solo figlio diagnostico; i binding effettivi di QtGui sono riportati separatamente. Indirizzi diversi fra wrapper e `eglGetProcAddress` sono normali e **non dimostrano da soli un dispatch errato**. [Sonda](evidence/v010-aquarium-graphics-analysis-2026-10-29/probe-symbol-owners.py), [risultati](evidence/v010-aquarium-graphics-analysis-2026-10-29/board-symbol-owners.json).

Il sorgente Qt **6.8.2** conferma che il rilevamento della versione usa chiamate GL dirette, mentre la ricerca delle funzioni passa prima da EGL. È una spiegazione plausibile della precedente discrepanza fra versione riportata da Qt e versione nativa; non è ancora la spiegazione dei glitch. [QEGLPlatformContext 6.8.2](https://raw.githubusercontent.com/qt/qtbase/v6.8.2/src/gui/opengl/platform/egl/qeglplatformcontext.cpp).

GLVND coordina il dispatch per thread attraverso EGL/GLX e la tabella del contesto corrente. Una combinazione che aggira tale coordinamento richiede verifica; la presenza di più librerie GL non basta a condannarla. [Architettura ufficiale libglvnd](https://github.com/NVIDIA/libglvnd/blob/master/README.md).

## Ipotesi ordinate per utilità diagnostica

| Ipotesi | Motivo | Confronto discriminante |
| --- | --- | --- |
| Interazione preload / librerie GL | Il preload cambia i binding dell’intera app, anche su Home | Stessa scena 2D e stesso formato, cambiando solo preload |
| Contesto ES3 o EGLConfig scelto | Il recupero esclude anche la richiesta ES3 | Stesse librerie, cambiando solo formato; registrare EGLConfig e formato reale |
| Render target 3D / skinning | View3D usa un target offscreen; i pesci usano ossa | Pattern 2D → cubo → pesce rigido → pesce con rig → sei pesci |
| Avvio, cache o ciclo di vita | Il difetto è stato segnalato intorno al reboot; prima misuravamo processi già avviati | Stessi byte, avvio app e reboot; cache privata nuova/conservata |
| Presentazione GBM/KMS o sincronizzazione | Un pannello corrotto può coesistere con heartbeat sano | Immagine del renderer, scanout, stato DRM e osservazione fisica nello stesso caso |

Il rapporto temporale con il reboot non prova che il reboot sia la causa. Mancano la riproduzione controllata e la cattura del guasto. Non attribuire il problema a DP/PLL, kernel o potenza della GPU senza nuove evidenze.

## Piano esecutivo G0–G5

**G0 — Banco con recupero garantito.** Baseline esatta dei 548 file e degli override. Archivi di prova separati da dati e pesci reali; una sola area di lavoro sulla board. Un solo processo EGLFS proprietario del display alla volta: i confronti nativi richiederanno una breve finestra di prova, non si eseguono in parallelo al kiosk. Un controllore esterno al processo grafico deve ripristinare il servizio 2D a scadenza, anche se il processo di prova si blocca. Nessuna promozione automatica in base all’import di QtQuick3D.

**G1 — Osservabilità prima della correzione.** Registrare separatamente formato richiesto e formato effettivo del contesto della finestra, GL_VENDOR, GL_RENDERER, GL_VERSION, GLSL, EGLConfig, colore/profondità/stencil, samples, API RHI, librerie e binding. Dati obbligatori: campo vuoto significa diagnosi incompleta. Usare inizialmente `QT_QPA_EGLFS_DEBUG`, `QSG_INFO` e log KMS; per le interrogazioni mancanti un piccolo helper nativo sul thread di rendering, con contesto corrente, eseguito una volta e senza modificare stato GL. Evitare callback Python dirette sul render thread, già problematiche per GIL e chiusura del banco. [Diagnostica EGLFS](https://doc.qt.io/qt-6.8/embedded-linux.html), [contesto e thread di QQuickWindow](https://doc.qt.io/qt-6.8/qquickwindow.html#beforeRendering).

**G2 — Matrice minima, scena 2D senza View3D.** Separare gli interruttori diagnostici oggi accoppiati da `SMARTPC_AQUARIUM_RENDERER`. Usare un pattern sintetico 960×640 con colori, testo, griglia e animazione, seguito da Home.

| Caso | Preload | Formato richiesto | Scopo |
| --- | --- | --- | --- |
| A | Assente | Baseline 2D | Riferimento |
| B | Assente | ES3 esplicito | Isolare il formato |
| C | GLES del produttore | Baseline 2D | Isolare il preload |
| D | GLES del produttore | ES3 esplicito | Riprodurre il percorso installato |

Eseguire i quattro casi una volta, ripetere solo il confronto che discrimina il guasto. Prima fase senza screenshot QML/readback, che possono introdurre altri target e sincronizzazioni; seconda fase con catture dichiarate. Non cambiare simultaneamente render loop, swap interval o configurazione KMS. Se la matrice non riproduce, il risultato è inconcludente e si passa al ciclo di vita, senza scegliere una correzione arbitraria.

**G3 — Progressione 3D e decisione.** Con il percorso 2D sano verificare cubo, un pesce rigido, lo stesso pesce con rig e sei pesci. Se il guasto compare già nel pattern, fermare il lavoro sui modelli. Se compare soltanto con skinning, isolare shader e texture delle ossa. Se riguarda solo la presentazione, confrontare formato/modifier/pitch, scanout ed eventi DRM; l’immagine restituita dal renderer non sostituisce il pannello.

**G4 — Correzione secondo l’esito.**

1. Se il contesto ES3 è sano senza preload e il problema è solo il riconoscimento delle capacità, valutare una correzione circoscritta dell’integrazione Qt che interroghi le funzioni del contesto corretto. Non dichiarare una versione GL senza verificarla.
2. Se il preload è determinante, preferire un runtime Qt/GLES coerente, compatibile con PySide e isolato in un prefisso dedicato, oppure un adattamento circoscritto verificabile. Una build privata ha un costo di manutenzione e richiede di ricontrollare i moduli Qt usati: non sostituire globalmente le librerie di sistema come primo tentativo.
3. Se il difetto riguarda EGLConfig, scegliere il formato che supera il confronto mantenendo zero MSAA e registrando quello effettivo. Profondità/stencil 24/8 sono anche la scelta dell’helper Qt, quindi non sono già una prova di errore.
4. Se il solo skinning nativo richiede un percorso grafico non affidabile, valutare deformazione CPU degli stessi modelli e upload della geometria: resta vero 3D. Sono **1701 vertici per pesce, 10206 per sei**, circa **0,735 MB per aggiornamento** se si reinvia tutto il buffer da 72 byte/vertice, ovvero circa **44 MB/s a 60 aggiornamenti/s**, esclusi copie, calcolo e overhead. È una stima di traffico, non una misura di costo o una promessa di FPS. Prima un microbenchmark ARM, poi confronto visivo e misure: niente aggiornamento per vertice in un ciclo Python senza valutarne il costo.

Sostituire la richiesta ES3 con `idealSurfaceFormat()` non costituisce da solo una soluzione. Nel sorgente 6.8.2 l’helper sceglie il ramo desktop se Qt dichiara `LibGL`, come avviene qui. L’ordine previsto è dopo QGuiApplication e prima del contenuto Quick; il codice attuale imposta il formato prima del caricamento di Main, quindi non abbiamo provato un errore di ordine. [Helper Qt 6.8.2](https://raw.githubusercontent.com/qt/qtquick3d/v6.8.2/src/quick3d/qquick3d.cpp), [contratto pubblico](https://doc.qt.io/qt-6.8/qquick3d.html#idealSurfaceFormat).

**G5 — Consegna e accettazione.** Ripetere solo i casi pertinenti al delta finale: Home, Meteo, Acquario, gestione, Gioco e ritorno, dieci rientri, arresto/riavvio app, reboot OS e conferma fisica. Prima 120 secondi dopo riscaldamento per il confronto, poi 30 minuti sulla sola candidata vincente. Target nominale 60 fps, 50–55 accettabili secondo la richiesta; riportare callback, distribuzione degli intervalli, stalli, CPU/RSS e temperatura separatamente dalla verifica ottica. Nessuna soglia p95 nuova viene inventata come già approvata. Conservare il recupero 2D e gli archivi fino all’accettazione della candidata; la sola assenza di warning non conclude il gate.

## Criterio di chiusura

La correzione è pronta quando la variante responsabile è riprodotta o un intervento mirato è sostenuto da confronti ripetuti, il percorso corretto supera la navigazione e il reboot con resa fisica confermata, le capacità GL sono raccolte dal contesto effettivo e dati/preferenze restano preservati. Se manca una riproduzione, dichiarare il limite e ampliare la prova pertinente. L’analisi attuale prepara queste attività; non ha implementato né validato la correzione.

[Ricevuta dell’analisi](evidence/v010-aquarium-graphics-analysis-2026-10-29/analysis-receipt.json). Compagno 0.11 e Memoria/AI 0.12 invariati; il recupero non cambia la richiesta di un Acquario realmente 3D.
