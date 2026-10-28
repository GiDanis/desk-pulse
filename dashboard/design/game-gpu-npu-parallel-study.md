# Gioco · GPU, NPU e 32 tentativi a velocità reale

**Studio 1 · 14 ottobre 2026 · baseline 0.9.0-rc.14.**

**Stato: studio, inventario nativo e microbenchmark GPU privato completati. Backend GPU/NPU per il gioco non implementati né installati.** Seguito dell'[audit risorse](v09-resource-optimization-analysis.md), del [confronto CPU/NPU rc.10](v09-optimization-report.md) e dello [studio degli incentivi](game-reward-balance-study.md).

**Seguito:** [runtime CPU rc.15](v09-balanced-runtime-report.md): implementazione autorizzata, installazione verificata; microbenchmark iniziali conservati.

## 1. Esito operativo

GPU e NPU sono presenti, ma non basta assegnare loro lavoro per ottenere 32 tentativi a 1×. Il problema coinvolge ambienti, sensori, reti, scheduler, valutazioni e salvataggi. La soluzione va scelta sulla latenza dell'intero ciclo e sulla fluidità della Dashboard.

**Priorità proposta:** motore di ambienti CPU raggruppati e persistenti, con confronto contro un piccolo backend GPU dei sensori. NPU per le reti attuali a bassa priorità: la misura precedente favoriva CPU e riguardava una sola rete congelata. Non rappresenta le 32 reti diverse di Evo, né il training PPO o le topologie NEAT.

Nuova evidenza: il calcolo OpenCL funziona sulla GPU fisica. Un kernel sintetico di raggi mostra possibili vantaggi rispetto a una CPU lasciata allo scheduler, ma **non supera la stessa implementazione CPU nativa quando il processo di prova è fissato sul core ad alta capacità**, nei sei casi misurati. Il risultato prepara un confronto, non giustifica una riscrittura GPU o un'affinità forzata della Dashboard.

Restano da dimostrare: throughput sostenuto ≥1.920 transizioni/s per 32 auto a 60 passi/s, rapporto simulato/reale per ogni tentativo, costi di ottimizzazione/ripasso e convivenza con il rendering a 30 Hz. Nessuna promessa di 32 tentativi sempre a 1×.

## 2. Evidenze raccolte e perimetro

- [Inventario nativo](evidence/v09-gpu-npu-parallel-study-2026-10-14/board-capabilities.json), con [script in sola lettura](evidence/v09-gpu-npu-parallel-study-2026-10-14/audit_board.py).
- [Sorgente del microbenchmark](evidence/v09-gpu-npu-parallel-study-2026-10-14/rays_opencl_probe.c), [prima esecuzione](evidence/v09-gpu-npu-parallel-study-2026-10-14/rays-opencl.json), [ripetizione](evidence/v09-gpu-npu-parallel-study-2026-10-14/rays-opencl-repeat.json), [esecuzione su CPU7](evidence/v09-gpu-npu-parallel-study-2026-10-14/rays-opencl-cpu7.json).
- [Ricevuta finale](evidence/v09-gpu-npu-parallel-study-2026-10-14/post-probe-board.json): servizio active, MainPID 327290 e NRestarts=0 come all'inizio. Nessun riavvio, installazione di dipendenze, cambio governor o modifica ai piloti. La sola prova viene fissata su CPU7; binario e sorgente temporanei sotto /tmp/smartpc-accelerator-study-20261014.
- Confronto NPU storico del 13 ottobre: [ricevuta con hash/precisione](evidence/v09-optimization-2026-10-13/board/npu/runtime-choice.json), consultata e non rieseguita in questo studio.

Le prove GPU sono headless, brevi e prive di training. La presenza del servizio non è una misura della fluidità del display. Nessun carico completo di Pista/32 è qualificato da questi microbenchmark; nessun consumo elettrico è stato misurato.

## 3. Hardware e stack realmente disponibili

| Elemento | Riscontro sulla nostra scheda | Conseguenza |
| --- | --- | --- |
| CPU | 8 logiche; capacità kernel 385 per CPU0–5 e 1024 per CPU6–7; massimi esposti circa 1,794/2,002 GHz | Core eterogenei: confronto a caso sullo scheduler può falsare il rapporto CPU/GPU |
| GPU | PowerVR B-Series BXM-4-64; clinfo seleziona un dispositivo GPU fisico | Il compute OpenCL è accessibile, non un fallback software |
| OpenCL | Piattaforma 3.0, profilo embedded; compilatore OpenCL C 1.2 disponibile; driver 24.2@6603887 | Prototipo C possibile con strumenti già presenti; controllare le feature opzionali, non assumere tutte quelle di OpenCL 3 |
| Precisione GPU | FP16/FP32 esposte, FP64 non disponibile nel dispositivo OpenCL | La fisica float64 attuale non si trasferisce bit per bit; serve un protocollo numerico qualificato |
| Memoria GPU | Unified memory dichiarata; SVM coarse-grained, niente fine-grained system sharing/atomics SVM | RAM fisica condivisa non significa zero copie, zero flush o zero sincronizzazione |
| Vulkan | Dispositivo integrato hardware, API 1.3.277; driver proprietario PowerVR 24.2 | Via alternativa per compute; la versione del loader 1.4.309 non è la versione del dispositivo |
| NPU | /dev/vipcore, libVIPlite/libVIPhal e strumenti già provati per VIP9000 | Inferenza NBG disponibile nel perimetro precedente; training non dimostrato |
| Governor letti | GPU simple_ondemand, 400 MHz nell'istantanea; NPU performance, 852 MHz | Nessuna frequenza forzata. Istantanee e runtime_status non determinano energia o utilizzo effettivo |

Il produttore del SoC descrive A733 con due Cortex-A76, sei Cortex-A55, PowerVR BXM-4-64 e NPU: [Allwinner, scheda tecnica A733](https://www.allwinnertech.com/uploads/download_source/20260303162657a4.pdf). La tabella sopra deriva dalla nostra installazione. La documentazione Radxa per lo stesso SoC è utile per SDK/NPU, senza identificare la nostra board come Cubie.

Il driver locale è 24.2. Le [novità Imagination DDK 25.2](https://blog.imaginationtech.com/driver-update-adds-support-for-vulkan-and-opencl-extensions), come cooperative matrix e miglioramenti della condivisione di memoria, non provano che quelle funzioni siano disponibili qui. Nessun aggiornamento driver è parte dello studio.

## 4. Che cosa significa realmente 32 auto a 1×

### 4.1 Tre ritmi distinti

1. **Fisica:** ogni mondo deve avanzare 60 passi per secondo reale, con passo simulato 1/60 s e sottopassi adattivi conservati.
2. **Decisioni/apprendimento:** sensori e azioni oggi a 60 Hz; optimizer, selezione e verifiche hanno frequenze proprie. Un nuovo ritmo di decisione modifica il protocollo, non soltanto gli FPS.
3. **Presentazione:** scena/rendering circa 30 Hz con campioni e interpolazione. Più frame non ripristinano passi fisici mancanti.

Per 32 ambienti attivi servono **32 × 60 = 1.920 transizioni/s**, più eventuale dimostrazione e lavoro di training. Con tre bot per ambiente si aggiunge il lavoro delle altre auto e dei loro sensori/controller. Le auto di mondi diversi non collidono fra loro. I candidati della stessa generazione sono parallelizzabili; la generazione successiva dipende dai risultati della precedente.

Il budget indicativo per un passo comune a tutti i mondi è 16,67 ms. In quel budget devono entrare sensori, azioni, fisica e stato minimo; optimizer/valutazioni richiedono capacità aggiuntiva o una separazione esplicita. Il solo kernel di raggi sotto 16 ms non prova che l'intero motore regga.

### 4.2 Architettura attuale

[AcademyTrainer](../game_academy_trainer.py) raccoglie osservazioni e avanza episodi uno alla volta, distribuendo le chiamate per mantenere comandi/preview responsivi. [Worker](../game_worker.py) condivide questo processo con valutazioni, update e salvataggi. In quel percorso una valutazione o un optimizer sospendono la raccolta ordinaria.

Il [collector sperimentale](../game_collectors.py) invia snapshot degli episodi ai figli e riceve stato completo a ogni passo. Era più lento nei piccoli compiti della rc.10. Un nuovo collector con mondi persistenti e piccoli buffer numerici è un'architettura diversa da qualificare, non un semplice interruttore da accendere.

La [rete densa](../game_learning.py) 68→16→2 ha **1.138 parametri**. La dimensione è piccola rispetto all'ambiente; il vecchio profiler rc.9 trovava i sensori dominanti, ma le percentuali di allora non vanno attribuite alla rc.14 dopo le ottimizzazioni. Profilare di nuovo ambienti e reti mature prima del trasferimento.

## 5. GPU: prova nativa su un carico di sensori

### 5.1 Metodo

Kernel OpenCL C 1.2: ogni raggio cerca la prima intersezione con un poligono di 128/512 segmenti. Sei casi: 4/32/128 auto equivalenti, nove raggi ciascuna. Per caso 5 riscaldamenti + 64 campioni, in tre esecuzioni: **18 casi misurati**, 1.152 campioni GPU dopo riscaldamento. Dati deterministici, CPU e GPU FP32, input lievemente variato a ogni iterazione per evitare lavoro costante eliminabile.

Geometria e buffer restano allocati sul dispositivo; ogni batch trasferisce raggi e legge distanze. Misurati CPU nativa scalare, GPU completa vista dall'host e kernel da eventi OpenCL. Compilazione iniziale/context circa 20,8–45,1 ms, esclusi dal regime caldo ma registrati. Compilazione CPU -O2 -ffp-contract=off, senza fast-math; kernel senza fast-relaxed-math.

**Non è il sensore attuale portato sulla GPU.** L'Ovale usa intersezioni analitiche; gli altri circuiti usano selezione dei segmenti per bounding box in NumPy. Tecnico ha 384 punti, Mallory e Varano 768; i confini del circuito sono una struttura ulteriore. Il poligono sintetico non riproduce cancelli, margini, fondo, contatti o complessità della pista reale.

### 5.2 Risultati confrontabili su CPU7 ad alta capacità

| Auto equivalenti / segmenti | CPU nativa mediana | GPU kernel mediana | GPU completa mediana | GPU completa p95 | GPU completa massimo |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4 / 128 | 0,027 ms | 0,264 ms | 0,403 ms | 0,440 ms | 3,188 ms |
| 4 / 512 | 0,126 ms | 0,729 ms | 0,885 ms | 1,055 ms | 1,179 ms |
| 32 / 128 | 0,215 ms | 0,312 ms | 0,473 ms | 0,586 ms | 4,288 ms |
| 32 / 512 | 0,815 ms | 0,871 ms | 1,031 ms | 1,149 ms | 3,481 ms |
| 128 / 128 | 0,864 ms | 0,933 ms | 1,135 ms | 1,253 ms | 1,865 ms |
| 128 / 512 | 3,435 ms | 3,396 ms | 3,670 ms | 6,822 ms | 8,870 ms |

Massimo errore istantaneo rispetto alla stessa aritmetica CPU FP32: circa **5,72×10⁻⁶ m**. Questo non è un confronto con l'algoritmo float64 di produzione, né una verifica della traiettoria a lungo termine.

Nelle due esecuzioni senza affinità, 32 auto/512 segmenti davano CPU 2,093/1,605 ms e GPU completa 1,492/1,187 ms: apparente guadagno circa 1,40/1,35×. CPU7 cambia la conclusione: CPU 0,815 ms contro GPU 1,031 ms. La variazione su 32/128 è ancora più ampia. Non usare le prime misure per pubblicizzare un'accelerazione del gioco.

Conclusione limitata: **il compute funziona e l'overhead è misurabile; questo kernel non giustifica scegliere GPU al posto di CPU nativa ad alta capacità.** Kernel migliori, riduzioni parallele sui segmenti, mappe spaziali, fusione di più sensori e dati residenti potrebbero cambiare il confronto. Vanno confrontati anche con CPU SIMD/multicore e algoritmo spaziale migliore, non soltanto con Python seriale.

### 5.3 Il confronto non chiude questi rischi

- Contesa con render EGLFS attivo di 32 vetture, sensori e camera; non misurata.
- Energia, temperatura in carico lungo, frequenze durante ogni campione; non misurate.
- SIMD/multicore CPU, distribuzione degli ambienti e stato PPO/NEAT; non provati dal microbenchmark.
- Precisione FP32 sui bordi, quasi-parallelismi dei raggi, contatti e deriva numerica multigiro; aperta.
- Kernel proposto semplice, con ciclo sui segmenti per raggio; non rappresenta il massimo della GPU.

## 6. Dove la GPU potrebbe aiutare

| Carico | Possibilità | Decisione preparatoria |
| --- | --- | --- |
| Rendering di pista e auto | Già nel percorso Qt/scene graph, indipendente dal learning | Conservare priorità grafica e target 30 Hz |
| Raggi su piste complesse | Lavoro parallelo ripetibile, geometria statica residente | Primo candidato GPU da confrontare con batch CPU/native e indici spaziali |
| Coordinate/curvature/pose | Gruppi omogenei, dati statici e letture vettoriali | Prima cache e batch CPU; fusione GPU solo se riduce trasferimenti/chiamate |
| Fisica di 32 mondi | Possibile con stato SoA e kernel, ma sottopassi/contatti/eventi sono irregolari | Seconda fase; non trasferire tutta la fisica prima di qualificare precisione e beneficio |
| Inferenza densa comune | Matrici molto piccole nel preset attuale | Bassa priorità; il lancio può costare più del calcolo |
| Evo, reti dense diverse | Stessa forma permette pesi batched residenti fra generazioni | Candidato futuro se aumenta il costo della rete; i benchmark a rete unica non bastano |
| PPO gradienti/Adam | Matrici/loss accelerabili con un backend dedicato | Nessun training GPU attuale; costi di implementazione/verifica maggiori del semplice forward |
| NEAT | Topologie diverse e calcolo sparso/irregolare | Conservare CPU, misurare maturità prima di padding/compilazione per GPU |

Un driver OpenCL non accelera automaticamente NumPy. Serve un backend esplicito C/C++ o binding, con buffer persistenti e scambio minimo. Prima della grande riscrittura misurare il contributo reale del pezzo candidato.

OpenCL è la via del prototipo già funzionante. Vulkan compute è un'alternativa, non un secondo acceleratore: la stessa GPU deve fare render e compute. Code diverse non garantiscono esecuzione hardware simultanea; [Khronos, code Vulkan](https://docs.vulkan.org/guide/latest/queues.html) e [sincronizzazione](https://docs.vulkan.org/guide/latest/synchronization.html). Non migrare il renderer QML a Vulkan soltanto per esplorare compute.

## 7. NPU: utilità reale e limiti dell'evidenza

### 7.1 Confronto acquisito, non nuovo benchmark

Policy PPO-Smooth congelata 68→16→2, 512 batch per taglia, CPU float64 da input float32; NPU FP16, conversioni/copie/flush/esecuzione/readback inclusi.

| Batch di ingressi della medesima rete | CPU mediana | NPU completa mediana | Esito precedente |
| --- | ---: | ---: | --- |
| 1 | 43,67 µs | 61,33 µs | CPU più rapida |
| 4 | 50,29 µs | 86,31 µs | CPU più rapida |
| 32 | 97,96 µs | 116,04 µs | CPU più rapida |

Errore massimo delle azioni <0,0005; caricamento circa 3,4–4,5 ms. Nessun modello diverso per candidato, aggiornamento dei pesi, closed-loop o energia qualificati da quelle prove. Non trasferire questi tempi al genoma NEAT corrente.

Per la sola inferenza di quella rete condivisa, 60 batch32/s corrispondono a circa 5,88 ms di calcolo CPU/s sulla mediana storica. È un ordine di grandezza, non utilizzo corrente del worker né il costo di Evo. Spostarla non eliminerebbe la preparazione dei 1.920 stati al secondo.

### 7.2 Un batch non è una popolazione di modelli

| Caso | Struttura | Ostacolo da verificare |
| --- | --- | --- |
| PPO/PPO-Smooth, 32 ambienti | Un actor e un critic condivisi; actor cambia dopo update | Inferenza batched adatta, ma rete piccola e aggiornamento della versione devono costare meno del risparmio |
| Evo, 32 candidati | 32 insiemi di pesi della stessa forma | 32 grafi o grafo con pesi batched/variabili; trasferimento/compilazione non inclusi nel vecchio test |
| NEAT | Reti con nodi/connessioni diversi che evolvono | Grafi variabili, operatori e ricompilazione/topologia; non equivale a una matrice densa unica |
| Clone | Rete aggiornata da esempi del maestro | La NPU forward non addestra automaticamente la loss supervisionata |
| Qualifica/Gara | 1 o 2–4 modelli congelati | Compatibilità più semplice, ma meno lavoro e nessun effetto diretto sui 32 tentativi di training |

La [documentazione SDK Vivante per A733](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-sdk) descrive conversione/compilazione e inferenza NBG/OpenVX/VIPLite. Questo stack non documenta l'esecuzione del nostro backward, GAE e Adam sulla NPU. «Supporta PyTorch/ONNX in ingresso» significa conversione del modello nel perimetro descritto, non training NumPy automaticamente accelerato.

Il [progetto TIM-VX](https://github.com/VeriSilicon/TIM-VX) offre costruzione di grafi e tensori; le API pubbliche espongono [VARIABLE/INPUT/CONSTANT](https://raw.githubusercontent.com/VeriSilicon/TIM-VX/main/include/tim/vx/types.h) e [copie/handle/cache](https://raw.githubusercontent.com/VeriSilicon/TIM-VX/main/include/tim/vx/tensor.h). Sono una pista per studiare pesi aggiornabili, **non prova** che il nostro driver possa modificare un fully-connected già compilato senza ricompilazione, né che convenga farlo. Verificare sul target operatori, caching, layout e costo di commit della nuova versione.

Modelli visivi o reti dense molto più grandi possono essere carichi futuri adatti all'inferenza NPU. Non aggiungere telecamere virtuali o neuroni soltanto per occupare l'acceleratore: cambierebbe il problema e richiederebbe nuovi protocolli e training.

### 7.3 Fisica e geometria sulla NPU

Il percorso disponibile è orientato a grafi neurali. Non abbiamo un backend NPU per collisioni, raggi, cancelli o reward con gli stessi stati del simulatore. Riscrivere operazioni arbitrarie come grafi, o sostituire la fisica con una rete appresa, è un altro studio con errore/modello da qualificare. Per questa richiesta non è la priorità.

## 8. Architettura candidata da confrontare

1. CPU coordina sessione, generazione, RNG, reward, eventi e salvataggi; mondi persistenti suddivisi in gruppi compatibili.
2. Stato numerico e geometria preparati una volta: eliminare snapshot completi per ogni passo; checkpoint completo solo al confine previsto.
3. Sensori CPU batch/native come baseline. Backend GPU opzionale riceve pose di tutti gli ambienti e restituisce un blocco di osservazioni, con geometria residente e letture aggregate.
4. Inferenza densa già batched dove possibile; CPU di default. Backend NPU opzionale con versione/hash del modello e adozione soltanto al confine, se il costo completo lo giustifica.
5. Fisica e reward avanzano con azioni di quella stessa versione; pubblicazione della scena a 30 Hz separata. Nessuna lettura del futuro o gradiente di una policy diversa da quella che ha generato le esperienze.

Una chiamata GPU per auto/coefficiente, download dopo ogni operazione o ricompilazione NPU per mutazione vanificherebbero il lavoro. Con GPU condivisa, kernel brevi/bounded e dati persistenti devono essere qualificati anche sulla coda dei tempi, non soltanto sulla mediana.

La CPU multicore deve usare anche i core piccoli senza sottrarre automaticamente entrambi i grandi alla GUI. L'affinità CPU7 del microbenchmark è una condizione di confronto, non una configurazione di produzione proposta. RAM libera può contenere buffer e geometrie, ma non sostituisce capacità di calcolo o coerenza delle cache.

## 9. Piano ufficiale di ricerca A0–A4

| Lotto | Prova/artefatto da produrre | Gate |
| --- | --- | --- |
| **A0 · Baseline contemporanea** | Profiler rc.14 con 32 attivi su Ovale/Tecnico/Varano; Evo e NEAT maturi, PPO e traffico, update/ripasso/salvataggi separati | Percentuali attuali e rapporto simulato/reale per ogni auto; nessun uso di percentuali rc.9 come stato corrente |
| **A1 · CPU raggruppata** | SoA/cache/native per geometria; 1/2/4 gruppi persistenti, piccoli buffer IPC, budget e affinità soltanto nelle prove | Stesso protocollo/RNG/checkpoint, miglioramento reale e GUI/comandi conservati; confronto contro il collector vecchio |
| **A2 · GPU sensori** | Portare algoritmo reale, batch32/64/128, buffer residenti; confronto con CPU ottimizzata e varianti di riduzione/spatial index | Prima precisione/edge cases; poi latenza completa e p95/p99 sotto rendering attivo; microbenchmark sintetico non chiude il lotto |
| **A3 · NPU condizionale** | Stessa rete condivisa vs 32 pesi distinti; carico/reload/commit, grafi e operatori, precisione e fallback | Vantaggio completo e ammortizzato su CPU attuale; nessuna ricompilazione nascosta o falsa affermazione di training NPU |
| **A4 · Motore e prodotto** | Backend scelto su copie mature, pausa/ripresa/migrazione dichiarata; 32 tentativi, bot, temi e interruzioni reali | Target per-auto 1× e 30 Hz presentazione, nessuna perdita di qualifica/storico o cambio di fisica mascherato; capacità insufficiente dichiarata |

### 9.1 Matrice minima e metriche

Prima confronto corto 60 s per variante sullo stesso checkpoint privato, tre ripetizioni, senza profiler nel campione di velocità; profiler in passaggio separato. Due circuiti distinti almeno, Ovale e Varano; aggiungere traffico dopo il solitario. Aggiornamenti e review misurati separatamente. L0–B4 sul bilanciamento reward rimangono un asse diverso: non cambiare reward e backend insieme nel confronto di performance.

Rilevare: transizioni/s aggregate, auto attive, rate per auto, gap massimo fra passi, tempo sensori/inferenza/fisica/optimizer/IPC, deadline mancate, p95/p99 scena/clock, comandi di pausa, CPU per core, frequenze/temperature e RAM. GPU busy solo da un contatore affidabile; un governor o un device file non sono una percentuale di utilizzo.

Target iniziale proposto: ogni auto attiva 0,95–1,05× su finestre da 10 s nel carico dichiarato; gap dei passi da confrontare con 16,67 ms, scatti >100 ms evidenziati; presentazione 30 Hz verificata separatamente. Se la rete si ferma durante update/review, dichiarare quella pausa o separarla correttamente: non nascondere il tempo sospeso dal denominatore del rapporto reale.

Selezione backend: beneficio oltre il rumore delle ripetizioni, senza peggioramento materiale dei tempi di presentazione/pausa; candidato ≥20% di throughput in più oppure raggiungimento documentato del target 1× a costo comparabile. Soglie di progetto proposte, non risultati acquisiti. Misurare energia esternamente se si dichiara risparmio in watt; runtime PM/frequenze non bastano.

### 9.2 Compatibilità numerica e riproducibilità

Per sensori FP32: casi radenti, denominatori piccoli, bordi/segmenti coincidenti, piste concatenate, pose esterne, margini reali, limiti di distanza e dati non finiti. Definire tolleranze prima del confronto; non usare automaticamente il piccolo errore sintetico come soglia della produzione.

Per fisica GPU futura: giri multigiro, contatti, sottopassi, gates, validità, fondo e generazione di eventi. Il nostro stato float64 e il dispositivo senza FP64 rendono necessaria una nuova versione del backend/precisione. Conservare l'originale e distinguere riproducibilità entro backend/versione da uguaglianza bit per bit con il percorso CPU precedente.

Per NPU: confronto azioni e poi comportamento a ciclo chiuso; quantizzazione/approssimazione possono alterare frenata e track limits. PPO conserva i raw actions/log-prob della policy effettivamente usata; non campionare sull'acceleratore e calcolare probabilità di un actor diverso. Commit/reload atomici, modello/hash nei risultati, pausa e fallback espliciti.

## 10. Fonti e limiti dell'inferenza

Fonti primarie consultate il 14 ottobre 2026: Allwinner A733, documentazione ufficiale Radxa/Vivante per lo stesso SoC, repository VeriSilicon TIM-VX, [specifica OpenCL](https://registry.khronos.org/OpenCL/specs/unified/html/OpenCL_API.html), guida Khronos Vulkan e aggiornamento driver Imagination. Le disponibilità effettive sopra vengono dall'enumerazione e dal kernel eseguito qui, non dalla brochure di un'altra board.

Regola di decisione: se una parte occupa f del tempo, anche un'accelerazione infinita di quella parte limita il miglioramento totale a 1/(1−f). Esempio puramente aritmetico: accelerare una rete che pesa il 5% non può dare più di circa 1,053× sull'intero ciclo. Il valore 5% è un esempio, non una percentuale misurata nella rc.14.

Le possibilità GPU/NPU e le priorità sono inferenze progettuali dai dati raccolti. Il microbenchmark non esclude kernel GPU più efficienti, il vecchio test NPU non esclude reti più grandi, e nessuno dei due dimostra che basti un acceleratore per 32 mondi a 1×.

**Esito:** preparare A0/A1 come baseline utile anche alla futura GPU; mantenere A2 sperimentale e A3 condizionale. Per il carico attuale la nuova prova sostiene investire prima su batch, codice nativo e distribuzione CPU. Backend, profili e consegna della Dashboard restano invariati.
