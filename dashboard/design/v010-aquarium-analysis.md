# SmartPC v0.10 — Acquario Calm · analisi preliminare

**Revisione 3 · 25 ottobre 2026 · Europe/Rome**

> Aggiornamento esecutivo, 26 ottobre: implementazione completata e rc.2/Apple1.6.5 installati. Questo documento conserva lo studio precedente; [chiusura, stato P0–P7 e limiti](v010-aquarium-completion-report.md).
**Stato dello studio alla redazione: pianificazione e analisi; nessun runtime modificato, asset prodotto, benchmark o intervento Orange Pi.** Riferimento: [MasterPlan 2.68](release-masterplan.md). Baseline storica della preliminare del 13 ottobre: core 0.9.0-rc.12, Theme API 2.10, 68 superfici, Apple Calm 1.6.2 disponibile; Base attivo. Questi dati vengono dal MasterPlan, senza nuova verifica live.

**Seguito corrente:** [studio completo rev.2](v010-aquarium-integration-study.md), [ricerca online, 28 schede](v010-aquarium-online-research.md) e [piano esecutivo P0–P7](v010-aquarium-implementation-plan.md). Baseline documentata del 25 ottobre: 0.9.4-rc.3 / API 2.12 / 68 superfici / Apple Calm 1.6.4 attivo, senza nuova verifica live. Prevalgono questi documenti per architettura, lifecycle, fullscreen e protocollo operativo.

## 1. Risultato richiesto e perimetro proposto

Nuovo argomento **Acquario**, semplice, a tutto schermo **960×640**, con lo stesso stile **Calm / illustrazione 2D** scelto per il [Compagno A](v010-companion-functional-spec.md), ora v0.11. È una scena piacevole da osservare e una prova preparatoria di due capacità: creare in chat personaggi/asset animati coerenti e farli funzionare sulla board con obiettivo **60 fps**. Memoria/scene AI slitta a v0.12, Stabilità integrata a v1.1; il perimetro completo del compagno resta conservato.

Interpretiamo “modelli animati” come pesci illustrati con parti/rig o sequenze di pose locali. Il 3D non è richiesto: sarebbe una fattibilità distinta. Prima proposta: un ambiente, 2 specie e 4–6 pesci, fondo statico, nuoto lento con coda/pinne, virate e profondità ottenuta con pochi livelli. Questi numeri sono candidati per la scena nominale, da fissare prima del benchmark. Bolle/piante/luce sono aggiunte misurate separatamente. Cura, bisogni, progressione e AI durante l'esecuzione non servono a questo esperimento.

**Tutto schermo, aggiornamento 25 ottobre:** canvas sull'intero pannello con barra/orario HH:mm conservati sopra, come richiesto e consegnato in v0.9.4. Nessun contatore prestazionale permanente. 4/6 cambiano argomento, 5 pausa/ripresa, 7 Home dalla vista principale, 1 Home/3 Avvisi/9 Menu conservati. Overlay/urgente sospendono il visuale secondo il piano; notte, quiete Avvisi e motion restano distinti. La precedente ipotesi di nascondere la barra è superata.

## 2. Approfondimenti necessari prima del prototipo

| Tema | Cosa analizzare in profondità | Risultato concreto |
| --- | --- | --- |
| **Direzione Calm** | Palette/accenti, silhouette, scala sul pannello, spazio vuoto, acqua e profondità; confronto con il concept del compagno. | Un concept 960×640 e un pesce master approvati, senza confondere preview e asset pronti. |
| **Produzione AI** | Identità fra pose, parti separate, alpha pulito, perni, occlusioni, virate, raccordo del loop e costo di correzione. | Catalogo minimo nuoto/virata/quiete, manifest con dimensioni/clip e registro di tentativi/correzioni. |
| **Rig o sprite** | Stessa silhouette e traiettoria con rig a parti contro sprite sheet; naturalezza, artefatti di blending, numero di nodi e memoria texture. | Confronto A/B su un pesce, poi scelta motivata sulla board. |
| **Movimento** | Traiettorie continue, accelerazioni dolci, limiti del fondale, cambi direzione, sovrapposizioni e variazioni controllate. | Sequenze riproducibili con seed; tempo reale indipendente dai frame persi, niente scatti dopo una pausa. |
| **Runtime/Theme** | Argomento e superficie dedicata proposta `aquarium.main`, shell tutto schermo, fallback Base/Functional/Calm, lifecycle e caricamento. | Contratto additivo, routing dei nove tasti e matrice uscite/overlay/urgente/cambio tema. SceneHost va valutato per riuso, non dato per già adatto al fullscreen. |
| **Prestazioni** | CPU GUI/render, texture upload, overdraw/alpha, shader/particelle, caricamento e frame pacing. | Carico nominale e protocollo congelati, capacità massima sperimentale distinta dal profilo di prodotto. |
| **Concorrenza e stabilità** | Refresh/fonti/avvisi reali della dashboard, errori asset, sospensione dei nascosti, rientro e crescita della memoria. | Scena locale/offline, lavoro animato fermo fuori vista, recupero/fallback e report dei limiti. |

La generazione di una bella immagine non prova la disponibilità di un rig o di un loop utilizzabile. La prima prova deve produrre **un pesce completo animabile**; contare tentativi, difetti e lavoro manuale, poi replicare la pipeline per una seconda specie. Il pacchetto finale deve vivere localmente e funzionare senza richieste AI durante il nuoto.

## 3. Approccio iniziale per i 60 fps

**Ipotesi da provare:** QML/Qt Quick per composizione e animazione, asset locali preparati una volta, fondo opaco statico e pesci di dimensioni contenute. Preferire trasformazioni dei nodi/parti a un ridisegno CPU dell'intero acquario a ogni frame. Python conserva configurazione e lifecycle; evitare uno snapshot Python→QML per ogni fotogramma. Movimento e deformazione devono restare coerenti anche se la logica delle traiettorie ha un ritmo inferiore al rendering.

Qt raccomanda lavoro asincrono e profilazione per restare nel budget di circa 16 ms; elementi traslucidi e shader su superfici ampie richiedono attenzione al costo per pixel. Questo motiva il confronto controllato di alpha/effetti, senza attribuire già alla PowerVR un collo di bottiglia. [Qt 6.8 · prestazioni QML](https://doc.qt.io/qt-6.8/qtquick-performance.html).

Per lo sprite, `AnimatedSprite` riproduce frame da un'unica immagine e può interpolarli; `frameSync` avanza con i frame renderizzati, quindi non è un contatore che certifica 60 fps. Un loop della coda a 12–24 pose/s può essere disegnato entro una scena a 60 fps, ma la sua qualità va valutata separatamente. Per i rig valutare gli Animator dove compatibili con controllo e interruzioni. [AnimatedSprite](https://doc.qt.io/qt-6.8/qml-qtquick-animatedsprite.html), [Animator](https://doc.qt.io/qt-6.8/qml-qtquick-animator.html). Documentazione consultata il 13 ottobre; alcune pagine indicano Qt 6.8.9: verificare le proprietà realmente disponibili nel runtime 6.8.2 della board.

Esempio di memoria **teorica**, non misura: una sheet di 24 frame da 128×128 RGBA8 contiene circa 1,5 MiB di pixel, prima di padding/mipmap/copertura driver. Più istanze possono condividere lo stesso asset; non moltiplicare automaticamente la texture per il numero di pesci. Registrare memoria effettiva, upload e risoluzione: il peso PNG su disco non descrive la memoria GPU.

**Fattibilità:** una scena 2D semplice ha un carico diverso dal Gioco con fisica/sensori/training e rende ragionevole esplorare il target. Le precedenti misure del Gioco non dimostrano né impediscono 60 fps nell'acquario. L'[audit risorse](v09-resource-optimization-analysis.md) identifica A733/PowerVR e distingue frame software, GPU e ottica; alcune analisi più vecchie hanno identificazione hardware superata. Non proporre governor, NPU o riscritture prima di una misura pertinente. Non c'è ancora una previsione numerica affidabile della capacità dell'acquario.

## 4. Protocollo candidato sulla board

| Passo | Prova | Cosa decide |
| --- | --- | --- |
| **A0 · Baseline** | Runtime/driver/backend/render loop, risoluzione e 60 Hz effettivi; stessa build, tema e policy fonti. | Riferimento riproducibile; pannello a 60 Hz non equivale a scena a 60 fps. |
| **A1 · Un pesce** | Fondo statico + un pesce, rig/sprite A/B, traiettoria/scala equivalenti. | Costo e qualità del modello animato, caricamento e primo frame separati dal regime. |
| **A2 · Scala** | 1 → 4 → 8 → 16 pesci, stessi seed/percorsi; poi bolle, piante e luce aggiunti uno alla volta. | Numero sostenibile e primo effetto costoso, senza cambiare più variabili insieme. |
| **A3 · Integrazione** | Carico nominale scelto, fonti/dashboard attive, refresh e avvisi; uscita/rientro, pausa, cambio tema e asset mancante. | Fluidità nella vita reale e priorità degli avvisi; niente training del Gioco invisibile. |
| **A4 · Durata e consegna** | Almeno 30 minuti nominali, osservazione pannello e input, poi installazione/reboot attribuibili alla candidata quando autorizzati. | Tenuta termica, crescita memoria, fallback, manifest/preferenze e ritorno senza lavoro nascosto. |

Salvare intervalli frame p50/p95/p99/massimo, percentuale di intervalli oltre il budget, slot di refresh mancati/stimati e stalli oltre 33,3/50 ms; medie/FPS e finestre temporali, CPU per thread, RSS/PSS e temperature/frequenze. Contatori GPU solo se affidabili; costo della strumentazione annotato. `frameSwapped` è un indicatore software, non una misura diretta del completamento GPU o di fotogrammi nuovi sul pannello: accompagnarlo con verifica ottica, e misurare input separatamente.

**Accettazione da fissare prima della prova:** obiettivo 60 fps / 16,67 ms; proposta di regime nominale ≥59 fps medi, p95 entro un periodo di refresh più tolleranza dichiarata della misura, ≤1% slot mancati e assenza di stalli ripetuti >50 ms, inclusi refresh concorrenti. Pubblicare p99 e peggior finestra senza nasconderli nella media. Queste soglie descrivono una qualifica vicina a 60, non una promessa di 60 costanti; per dichiarare 60 costanti servono anche verifica fisica e assenza di frame mancati nel perimetro registrato. Urgenti/caricamenti si riportano a parte, senza ometterne l'effetto sull'esperienza.

Se il target manca, isolare rig/sprite, alpha/effetti, upload o lavoro GUI; ridurre complessità del profilo nominale e riprovare lo stesso protocollo. Un fallback a 30 fps può essere utile ma non chiude il gate 60 fps. La prova dell'acquario prepara la pipeline del compagno, mentre gameplay, bisogni, persistenza e reazioni del cane richiedono verifiche proprie.

## 5. Prossimo lavoro reviewabile

Prima approfondire **concept/pesce master**, **rig contro sprite** e **protocollo di misura**. Il primo prototipo dovrà dimostrare nuoto continuo, virata e loop pulito con un solo pesce; solo dopo passare a scena nominale e stress crescente. Questo percorso è approfondito nello [studio di integrazione](v010-aquarium-integration-study.md); ricerca e analisi non avviano ora generazione degli asset, sviluppo o distribuzione.
