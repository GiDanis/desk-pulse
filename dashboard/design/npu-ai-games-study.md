# Giochi che imparano e NPU locale — primo studio

**Aggiornamento rc.6:** [vista Pilota e dossier](v09-pilot-dossier-report.md), durata/sessioni/profili/risultati e reset confermato con storico conservato; API 2.9, 68 superfici.

**Aggiornamento rc.5:** [Gara e guida PPO](v09-race-ppo-report.md): una vettura per pilota, reti salvate congelate, 3/5/10 giri e dimostrazione PPO distinta dai tentativi di apprendimento.

## Stato implementazione · 11 ottobre 2026

La candidata corrente è **0.9.0-rc.6**, con [ottimizzazioni del motore e delle scene](v09-game-performance-report.md): menu spiegato, Controllo/Passo, campione verificato e Progressi dei tempi implementati/installati. [Nuovo report e limiti](v09-game-settings-pace-report.md); la [consegna rc.2](v09-game-implementation-report.md) conserva il confronto CPU/NPU e le prove precedenti. Il testo seguente conserva lo studio precedente; i candidati numeric9/30 sono sostituiti in questa build da race-32-v1, rete 32→16→2 e fisica f1-2. NPU verificata nella rc.2 con una politica appresa, CPU scelta dopo misure; PPO/NEAT e guida nel traffico restano da qualificare.


10 ottobre 2026 · studio S0 · SmartPC / DeskPulse · display 960×640.

**Direzione scelta con l'utente:** iniziare da un'auto su **ovale 2D visto dall'alto, pista interamente visibile e camera fissa**, con obiettivo grafico 60 FPS. Una piccola rete neurale migliora attraverso tentativi e selezione. Apprendimento e simulazione sulla CPU; confronto CPU/NPU su un modello fisso come esperimento separato. La NPU è funzionante sulla nostra scheda, ma il suo vantaggio per una rete molto piccola resta da misurare. CarRacing-v3 rimane un riferimento gradito; piste generate e agente che guida dalle immagini sono evoluzioni successive.

La richiesta dell'utente definisce il comportamento: aprire la vista non avvia il lavoro; **Start** avvia l'attività principale. Il calcolo si sospende con Pausa, quando si esce dalla vista o quando un avviso urgente prende il controllo. Alla riapertura si attende un nuovo Start. Queste regole sono una proposta per il futuro modulo, ancora da implementare.

Questo studio documenta hardware, opzioni, limiti e prove necessarie. Il [MasterPlan](release-masterplan.md) assegna ora **v0.9 · Gioco / Auto che impara** come prossimo nuovo modulo; Compagno passa alla v0.10 e Memoria/scene AI alla v0.11. Lo [studio approfondito di fattibilità, GUI e UX](v09-game-gui-ux-study.md) completa S0: revisione GUI/UX 4 su layout/tavole r2 con arena 912×496, fascia compatta, proporzioni fisiche e controllo locale delle frecce durante Simulazione; 5 Pausa confermata restituisce la navigazione. Le tavole rimangono dati demo. Il requisito aggiornato è allenare un pilota selezionato alla volta, salvarlo e poi far gareggiare insieme più piloti addestrati, ciascuno con la propria politica congelata: dettagli nello [studio piloti/Gara](game-drivers-simulation-study.md). In Gara il candidato NPU è l'inferenza di più modelli distinti; residenza, parità e latenza totale richiedono misure proprie. Un batch della stessa rete o un esempio NPU non qualifica questo scenario. Le fasi sperimentali S0–S5 guidano il rilascio; la priorità concordata non certifica implementazione, installazione o fattibilità prestazionale.

**Approfondimento algoritmi:** lo [studio Evoluzione / PPO / NEAT e NPU](game-learning-algorithms-study.md) aggiunge fonti primarie, ambiente comune, profili candidati, confronto riproducibile, checkpoint e semantica GUI per metodo. Ordine raccomandato: evoluzione fissa → PPO → NEAT, con inferenza NPU del campione come esperimento prioritario. Nessun backend aggiuntivo è ancora implementato o qualificato.

**Estensione piloti/simulazione:** lo [studio piloti, Classifica e F1](game-drivers-simulation-study.md) amplia il prodotto a personaggi persistenti con profili/cervelli propri, allenamento individuale, Gara simultanea fra modelli congelati, prove separate e cataloghi estendibili. Primo ovale asciutto e vettura standard con dinamica 2D contenuta candidata; numeric7 è baseline F0, numeric9 è candidato F1 solitario; Gara richiede osservazioni compatibili con gli avversari. I benchmark NPU esistenti non qualificano nessuna delle due politiche.

## 1. Cosa è stato verificato sulla scheda

Le prove di inferenza sono state eseguite nella chat del 10 ottobre. Il [resoconto delle prove](evidence/npu-ai-games-study-2026-10-10/probe-record.md) riporta i comandi e i risultati osservati, estratti dalla conversazione. Una nuova [raccolta passiva delle 17:02 Europe/Rome](evidence/npu-ai-games-study-2026-10-10/board-inventory.json) conserva modelli, hash, librerie, frequenze, RAM e stato del servizio. La nuova raccolta non ripete i benchmark.

| Aspetto | Riscontro | Cosa possiamo concludere |
| --- | --- | --- |
| Scheda osservata | Host `orangepizero3w`, famiglia `sun60iw2`, kernel `6.6.98-sun60iw2` | Il contesto del progetto è Orange Pi Zero 3W / A733. Il compatible del device tree è `xunlong,orangepi-4-pro`: il nome nel DT non certifica da solo il modello fisico o la marcatura del chip. |
| NPU | `/dev/vipcore`, driver `vipcore`, CID `0x1000003b`, un dispositivo e un core nel test | Presenza ed esecuzione reali accertate; non serve dedurle dalla sola famiglia A733. |
| Driver e libreria | Kernel VIPLite `2.0.3.5-AW-2026-03-17`; spazio utente `2.0.3.2-AW-2024-08-30` riportato dai programmi | La coppia esegue i due esempi presenti. Compatibilità con altri binari/SDK ancora da provare. |
| Frequenze NPU | 492 e 852 MHz disponibili; governor `performance`, 852 MHz osservati | È il limite esposto da questa installazione. Non dedurre 1 GHz operativo né occupazione continua dal governor. |
| RAM | 5,72 GiB totali, 5,27 GiB disponibili nel nuovo campione; swap inutilizzata | Margine istantaneo per un prototipo piccolo; nessuna misura di picco del futuro training. |
| CPU | Otto CPU disponibili al processo di raccolta | Non equivale a otto core esclusivi per il gioco. Due A76 e sei A55 sono la topologia documentata per A733 e coerente con le precedenti prove hardware del progetto. |
| Temperatura | NPU 39,3 °C; CPU circa 41,7–43,0 °C nella nuova raccolta | Campione passivo, non prova di temperatura o throttling durante una sessione lunga. |
| Dashboard | Installazione `0.8.7-rc.3`, servizio active/running, `NRestarts=0` | Stato dopo le prove e durante l'inventario; nessuna misura di latenza GUI sotto training. |

L'A733 è pubblicizzato con una NPU fino a 3 TOPS, ma la famiglia comprende sottovarianti diverse. Il dato commerciale non misura velocità del nostro modello, RAM o addestramento. Qui la prova decisiva è l'inferenza riuscita. [Allwinner A733](https://www.allwinnertech.com/index.php?a=index&c=product&id=139&solveid=34), [datasheet, tabella delle sottovarianti](https://dl.radxa.com/cubie/a7a/docs/hw/datasheet/A733_Datasheet_V0.93.pdf).

### 1.1 Modelli già presenti

| File remoto | Dimensione | Risultato osservato | Limite |
| --- | ---: | --- | --- |
| `/opt/vpm_run/network_binary.nb` | 964.224 byte | Ingresso 224×224×3, due valori in uscita; un'esecuzione completata; profiler interno 2.837 µs | Architettura, etichette e scopo non documentati nei file consultati. Nessun output di riferimento, quindi il test prova esecuzione, non accuratezza. |
| `/opt/yolov5/model/yolov5.nb` | 5.033.536 byte | YOLOv5 su foto: cane, camion, bicicletta; dieci iterazioni, media finale 41,95 ms, min 39,23 e max 44,60 ms | Variante esatta e dati di training non identificati. Tempi riportati dall'eseguibile, senza verifica dei suoi confini di misura. |

Il benchmark YOLO riporta anche una media progressiva di 46,62 ms, distinta dalla statistica finale di 41,95 ms. Conservare entrambe; non chiamare nessuna delle due latenza completa immagine→schermo. I 23,8 FPS dichiarati dal programma sono throughput di quel test, non FPS della GUI o del gioco.

Nel log di boot compare `Get NPU Regulator Control FAIL!`; seguono inizializzazione e prove riuscite. È un messaggio da riesaminare nelle prove termiche, non un guasto funzionale dimostrato. La dashboard è stata brevemente osservata inattiva prima dei test; la successiva riattivazione e il nuovo PID erano già presenti prima dell'inferenza. La causa del cambio di stato non è attribuita alla NPU.

## 2. Apprendimento, inferenza e simulazione

Un gioco che impara richiede tre lavori distinti: simulare ambiente e collisioni, scegliere un'azione usando il modello, modificare il modello in base ai risultati. Il disegno della pista e delle auto è un quarto lavoro, affidato alla grafica Qt Quick.

Il runtime NPU verificato esegue modelli compilati `.nb`. La documentazione descrive inferenza e conversione con ACUITY: importazione, eventuale quantizzazione e compilazione per A733, su PC. L'addestramento sulla NPU e l'aggiornamento efficiente dei pesi durante il training **non sono verificati**. Non proporre di ricompilare un modello a ogni tentativo prima di misurarne costo e fattibilità. [SDK Vivante](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-sdk), [conversione ACUITY](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-usage).

Per il primo esperimento la CPU modifica i pesi, valuta la popolazione e simula la pista. In una fase NPU il modello resta fisso durante la misura, con caricamento una volta e inferenze ripetute. Se l'esportazione non riesce o non migliora il tempo completo, il gioco continua a essere fattibile sulla CPU. Il comportamento della UI deve riportare il motore realmente utilizzato.

## 3. Esperienze possibili e priorità

Questa tabella è una valutazione progettuale, non il risultato di benchmark dei giochi sulla scheda.

| Esperienza | Come impara | Uso plausibile della NPU | Valutazione iniziale |
| --- | --- | --- | --- |
| **Auto 2D con sensori virtuali** | Evoluzione di una piccola rete da distanza ai bordi e velocità | Inferenza del campione fisso, se vantaggiosa | Prima scelta: coerente con l'idea, poche dipendenze e progresso visibile. |
| Flappy Bird / ostacoli | Evoluzione o RL da pochi valori numerici | Beneficio da dimostrare per una rete piccola | Alternativa semplice se la geometria della pista ostacola il primo prototipo. |
| Labirinto / robot cercatore | Tabella Q o piccola rete | Può non servire una rete neurale | Buon esperimento didattico; definire bene esplorazione e premio. |
| Equilibrista / pendolo | RL da posizione e velocità | Inferenza di una politica fissa | Candidato per confrontare algoritmi con un ambiente piccolo. |
| Snake | RL/evoluzione da griglia o caratteristiche | Più plausibile con input immagine, ancora da misurare | Richiede gestione di ricompense ritardate, stalli e percorsi ripetuti. |
| **Auto che legge la pista dalle immagini** | CNN + RL o imitazione | Inferenza della CNN | Seconda esplorazione: training, conversione e costo del generatore di immagini più impegnativi. |
| Simulatore 3D complesso | RL visivo e fisica articolata | Accelerazione della sola politica | Fattibilità aperta; non candidato iniziale per questa dashboard. |

Gymnasium CarRacing-v3 è un riferimento per una pista 2D con tre comandi e osservazione RGB 96×96. Per il nostro primo gioco si propone un ambiente più piccolo con sensori numerici; il confronto con CarRacing visivo sarà successivo. [Ambiente ufficiale](https://gymnasium.farama.org/environments/box2d/car_racing/).

## 4. Proposta concreta: auto 2D che migliora

Prima pista: ovale largo con due rettilinei e due curve semicircolari, interamente visibile a 960×640. Camera fissa, traguardo e checkpoint ordinati; una popolazione prova lo stesso percorso. Si conserva il campione e si generano varianti dei pesi migliori. A schermo il campione corrente e pochi tentativi rappresentativi; il numero di auto simulate può essere maggiore del numero disegnato. Raggio, larghezza e velocità massima sono parametri dell'ambiente, senza introdurre subito un generatore di circuiti arbitrari.

**Ipotesi iniziale da collaudare:** cinque raggi virtuali per la distanza ai bordi, velocità e velocità angolare; sette ingressi, uno strato di 16 neuroni e due uscite per sterzo e accelerazione/frenata. I valori sono normalizzati e le azioni limitate. Nessun accesso alla soluzione futura o a un percorso di sterzo preparato.

Una rete densa `7→16→2` ha 144 pesi e 18 bias, 162 parametri totali. Per 32 auto a 60 decisioni/s, i soli strati densi richiedono circa **276.480 moltiplicazioni e accumuli/s**; non sono inclusi attivazioni, collisioni, raggi, selezione, IPC o disegno. È un conto teorico, non una misura di velocità. Indica perché la piccola rete potrebbe non giustificare il costo di invio alla NPU. Il collo di bottiglia potrebbe essere la geometria o Python.

Si propone una topologia fissa con elitismo e mutazioni come primo algoritmo. È più semplice da convertire e diagnosticare di una rete che cambia struttura. NEAT è anche candidato a una successiva modalità di confronto, dopo evoluzione fissa e PPO: evolve anche la struttura e aggiunge meccanismi specifici, non è un nome da assegnare a un semplice algoritmo genetico. [Stanley e Miikkulainen, NEAT](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf).

PPO su osservazioni numeriche è il primo confronto aggiuntivo proposto, anche se l'evoluzione iniziale riesce; permette di confrontare apprendimento con gradiente e selezione. Introduce rollout, dipendenze e tuning diversi. La documentazione Stable Baselines3 indica CPU come scelta principale per PPO senza CNN; non dedurre che sia già compatibile con la VIPLite installata. [PPO](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html).

I profili PPO/NEAT, i rischi di osservabilità dei sette ingressi e il protocollo di confronto sono definiti nello [studio degli algoritmi](game-learning-algorithms-study.md). La popolazione evolutiva e gli ambienti PPO condividono la geometria ma sono tentativi fisicamente indipendenti. Generazione e checkpoint descritti qui sono la baseline evolutiva; PPO usa passi/aggiornamenti e salvataggi specifici.

### 4.1 Cosa significa «ha imparato»

La distanza utile è l'avanzamento attraverso checkpoint ordinati, con verifica di attraversamento e collisioni fra due passi. Limiti e penalità coprono tempo fermo, retromarcia, uscita dalla pista e sterzo instabile. Un salto numerico oltre un muro o fra checkpoint non deve diventare progresso valido. Non premiare soltanto sopravvivenza: potrebbe favorire un'auto ferma.

Misurare giri completati, avanzamento, collisioni e tempo sul giro, oltre alla fitness. Un punteggio più alto non dimostra automaticamente una guida migliore. Confrontare con azioni casuali e, separatamente, un semplice controller deterministico come riferimento. Il controller di riferimento non deve pilotare gli episodi presentati come apprendimento.

Tenere separati semi di training e valutazione. Per il primo ovale verificare anche partenze con piccoli scostamenti laterali, angolo e velocità diversi, e un ovale di valutazione con dimensioni differenti; la generazione di piste generiche rimane successiva. Un giro sullo stesso ovale dimostra apprendimento di quel compito, non guida generale: una politica poco reattiva può sfruttare la regolarità della pista. Primo criterio proposto: miglioramento su almeno quattro di cinque semi rispetto alla politica casuale; obiettivo successivo, un giro valido entro cinque minuti su pista facile in almeno quattro prove. Sono soglie di prodotto da verificare in S1/S2, non risultati attesi garantiti. Un fallimento produce una nuova decisione di algoritmo/ambiente.

Mostrare «Impara» soltanto quando i pesi stanno realmente cambiando. «Guarda il campione» riproduce un modello fisso; un replay storico mostra una sessione salvata. Generazione, punteggio e grafico derivano dal worker e conservano la loro provenienza. Nessuna crescita artificiale del contatore o del grafico.

### 4.2 Camera fissa e obiettivo 60 FPS

La scelta dell'ovale permette uno sfondo preparato una volta, pochi oggetti mobili e nessun movimento della camera. Il renderer può aggiornare posizione e rotazione delle auto conservando pista e decorazioni. Si propone una geometria Qt Quick o una texture statica per il tracciato; evitare il ridisegno dell'intera pista in un Canvas a ogni frame. Qt segnala il costo degli aggiornamenti di texture per Canvas, soprattutto con grandi superfici o aggiornamenti frequenti. [Canvas, Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html).

I 60 FPS richiedono circa 16,7 ms per frame. Sono un obiettivo plausibile per questa composizione, **ancora da qualificare sulla board durante l'apprendimento**. Restano tre frequenze distinte: rendering verso 60 FPS, fisica a passo fisso da 1/60 s e invio degli snapshot inizialmente 20–30 Hz con interpolazione visuale. Decisioni della rete inizialmente a ogni passo fisico; un successivo confronto a frequenza inferiore deve misurare gli effetti sulla guida. Grafici e statistiche si aggiornano per generazione o a frequenza ridotta. Il training non deve attendere il renderer e il renderer non deve attendere la fine di una generazione. [Timing e lavoro asincrono, Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-performance.html).

In modalità apprendimento veloce il simulatore può eseguire più passi per secondo reale mantenendo invariato il passo fisico; il display continua a mostrare snapshot limitati e indica il fattore di accelerazione. Per osservare una guida leggibile si propone una modalità a velocità normale. Una GUI fluida non prova che il simulatore proceda in tempo reale: misurare entrambe le cose, oltre ai frame saltati. Le misure `frameSwapped` restano tempi software, distinte da una verifica ottica del pannello.

Progressione proposta: **ovale fisso → variazioni controllate dell'ovale → circuiti con curve diverse → generazione di piste valide**. Il futuro generatore deve verificare larghezza, continuità, assenza di incroci indesiderati e correttezza dei checkpoint prima di avviare un episodio. Non si attribuisce generalizzazione alla sola riuscita del primo ovale.

## 5. Start e allocazione delle risorse

Flusso proposto: **Pronto → Avvio → Impara ↔ Pausa → Salvataggio → Pronto**. Errore e interruzione urgente hanno transizioni esplicite. Entrare nella vista mostra pista, ultimo campione e pulsante Start; nessun training o caricamento NPU avviene all'avvio della dashboard.

La sessione è l'attività principale dopo Start: rendering delle viste nascoste e lavori non necessari al gioco si possono limitare dove il lifecycle lo consente. Orologio, input, avvisi, persistenza e recupero restano responsivi. I provider esistenti hanno obblighi di freschezza; `NetworkService.setVisible()` attualmente non sospende il polling. Un eventuale rinvio dei refresh va progettato e reso leggibile, non dedotto dalla visibilità della vista. Fonti interne: [launcher](../app.py), [servizio Rete](../network.py), [shell](../Main.qml).

Un processo dedicato è il punto di partenza proposto per simulazione/training: evita di condividere il GIL della GUI e permette di terminare una sessione bloccata. Pubblicazione di snapshot piccoli a frequenza limitata e coda con capacità uno, sostituendo quello non ancora consumato. QML disegna lo stato corrente, senza I/O, mutazioni dei pesi o un QObject per ogni raggio e parametro. Un eventuale runner NPU C/C++ persiste per tutta la sessione.

Prima un worker e calcoli NumPy raggruppati; poi confronto con due worker se necessario. Non assegnare subito otto worker o tutti gli A76: pool numerici e processi possono moltiplicare i thread e contendere la GUI. Controllare pool di libreria, affinità e CPU per processo soltanto dopo l'attribuzione dei costi. Governor e frequenze globali non sono una premessa del prototipo.

**Profili iniziali proposti:** 16/32/64 auto simulate da confrontare; lo [studio algoritmi](game-learning-algorithms-study.md) aggiunge prove 128/256 e profili PPO ampliati secondo la RAM disponibile. Non sono limiti massimi. Per la GUI, 1–8 mostrate, fisica a passo fisso da 1/60 s, pubblicazione 20–30 Hz. Il renderer può interpolare i due snapshot più recenti; quando il worker resta indietro si riduce il carico o si rende esplicita la lentezza. Non cambiare il passo fisico in base agli FPS e non accumulare indefinitamente gli aggiornamenti.

**RAM, indicazione aggiornata dell'utente:** il gioco può utilizzare tutta la memoria effettivamente disponibile dopo Start, senza il precedente tetto candidato di 256 MiB. Misurare disponibilità e picchi durante la sessione, allocare quanto utile e rilasciare le risorse alla chiusura. Assenza di swap indotta sotto carico, feedback software dei controlli p95 entro 150 ms e pausa del worker entro 250 ms sono obiettivi da misurare. Sono budget candidati; le misure ottiche/tastierino fisico sono un gate separato. La soglia termica dipende dai trip point esposti dal kernel e dalla prova sulla scheda; i 39–43 °C del campione non fissano un limite operativo.

In Pausa si ferma il ciclo di simulazione. Uscita, Home, avviso urgente e sospensione della sessione cancellano il lavoro pendente; il ritorno non riavvia automaticamente. Salvataggio asincrono e atomico del campione e dello stato necessario alla ripresa; se un salvataggio fallisce, ultimo checkpoint valido conservato e messaggio esplicito. Dopo crash o reboot: stato Pronto, recupero del checkpoint valido, nessun training automatico.

Per PPO, pause durante i minibatch e memoria PyTorch richiedono verifiche dedicate; per NEAT, pausa/ripresa e crescita della rete hanno gate specifici. Evoluzione, PPO e NEAT possono utilizzare la RAM disponibile senza quota fissa; i profili iniziali sono punti di partenza da ampliare se le misure di CPU, pause e GUI lo consentono. Vedere [risorse, pause e persistenza](game-learning-algorithms-study.md).

## 6. Modelli aggiuntivi e percorso NPU

Il [Model Zoo Radxa per A733](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/model-zoo) documenta esempi di MobileNet, YOLO, pose, segmentazione, CLIP e Zipformer. Sono precedenti di distribuzione su una piattaforma dello stesso SoC, non certificazione di compatibilità con la nostra coppia driver/libreria. Per il gioco con sensori serve una rete nostra; YOLOv5 rileva oggetti e non è una politica di guida.

Primo port NPU proposto: modello fisso del profilo effettivamente qualificato (`7→16→2` baseline F0, `9→16→2` candidato F1), operatori elementari supportati, ingresso/uscita definiti e vettori di riferimento CPU. Esportazione e compilazione sul PC, target A733/v3 coerente con l'SDK; un solo bundle compilato provato sulla board. Quantizzazione calibrata su osservazioni raccolte e confronto delle azioni su almeno 1.000 vettori, includendo curve, velocità basse e valori ai limiti. L'errore accettabile va collegato all'esito della guida: una piccola differenza numerica può cambiare una collisione.

Misurare apertura del runtime, caricamento, preparazione, copia degli ingressi, inferenza, lettura degli output e durata completa della decisione. Stesso modello, stessi ingressi, batch esplicito, sessione CPU e NPU persistenti; campioni freddi separati dai caldi. Per 32 politiche diverse il test di un solo campione non dimostra l'efficienza della popolazione. Prima di accelerare l'evoluzione sulla NPU occorre chiarire come distribuire pesi diversi e aggiornati senza costi sproporzionati.

Promuovere il percorso NPU se correttezza e costo completo sono migliori in modo ripetibile, oppure se la NPU consente una nuova esperienza che la CPU non sostiene. Anche un risultato CPU più veloce è una conclusione utile dello studio.

Per la guida visiva, un piccolo encoder CNN o politica visiva potrebbe rendere l'NPU più utile. Rimangono aperti: costo di generazione degli ingressi immagine, formato/layout, stacking dei frame, operatori convertibili e apprendimento in tempo utile. Addestramento sul PC e inferenza sulla board è una modalità alternativa da presentare come modello già addestrato; non equivale a imparare sulla scheda.

## 7. Piano degli esperimenti e decisioni

La tabella seguente conserva la sequenza sperimentale hardware originaria; il [MasterPlan](release-masterplan.md) e lo [studio piloti/Gara](game-drivers-simulation-study.md) la estendono al perimetro corrente (F1, un learner selezionato, gara condivisa e risultati persistenti). Le sigle S0–S5 identificano le fasi della futura v0.9, non versioni software. L'installazione nella dashboard segue i prototipi e la qualifica delle risorse; il MasterPlan registra la priorità e i criteri di consegna.

| Fase | Lavoro | Risultato concreto e criterio di uscita | Stato |
| --- | --- | --- | --- |
| **S0 · Fattibilità** | Inventario, prove NPU esistenti, algoritmi, risorse, lifecycle | Questo dossier, evidenze e scelta auto 2D/sensori come primo candidato | Studio scritto; nessun gioco implementato. |
| **S1 · Ambiente e apprendimento PC** | Ovale fisso, simulazione senza GUI, NN fissa, evoluzione, random baseline, semi e checkpoint | Collisioni/checkpoint corretti; risultati veri su cinque semi, partenze variate e ovale di valutazione; misure di apprendimento e costi per fase | Proposto. |
| **S2 · Costo sulla board** | Esecuzione temporanea isolata del prototipo CPU, 16/32/64 auto, prima sessione da cinque minuti | Tempo al primo giro, passi/s, picchi RAM/CPU, temperature, stop e salute GUI; scelta del carico sostenibile | Proposto dopo S1; non eseguito. |
| **S3 · Confronto NPU** | Conversione della rete fissa, parità numerica, CPU/NPU freddo/caldo | Misure complete e decisione di adozione; percorso di pesi aggiornati studiato soltanto se necessario | Proposto; compilatore, conversione e rete custom non verificati. |
| **S4 · Prototipo interattivo** | Ovale a camera fissa 960×640, obiettivo 60 FPS, Start/Pausa, campione e tentativi, grafico reale, salvataggio; contesti/azioni Theme additive e fallback | Controlli leggibili, lifecycle e urgenze, offline/ripresa, fault del worker, compatibilità dei temi/SDK, nessun QML warning; rendering e simulazione misurati anche sotto training | Proposto dopo scelta S2/S3. |
| **S5 · Integrazione candidata** | Completamento integrazione Theme, broker di azioni, fallback dei temi, installer e recovery dopo S4 | Manifest/backup; qualifica EGLFS, tastierino, preferenze, reboot e almeno una sessione continuativa di 30 minuti | Pianificata per la futura v0.9; implementazione e installazione non ancora avviate. |

Il primo punto aperto è **quanto rapidamente una politica numerica semplice impari a completare la pista**, non se la NPU esista. S1 risolve convergenza e ricompensa; S2 risolve costo sulla Orange Pi; S3 risolve il vantaggio dell'acceleratore. Per S5 serviranno nuovi contratti Theme: non aggiungere ora una superficie o un provider al runtime soltanto per rappresentare un'idea.

## 8. Fonti e questioni aperte

Fonti primarie consultate il 10 ottobre 2026, oltre al codice del progetto e alle due evidenze locali:

- Allwinner: [A733](https://www.allwinnertech.com/index.php?a=index&c=product&id=139&solveid=34) e [datasheet](https://dl.radxa.com/cubie/a7a/docs/hw/datasheet/A733_Datasheet_V0.93.pdf), caratteristiche e varianti.
- Radxa: [SDK Vivante](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-sdk), [conversione](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-usage), [Model Zoo](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/model-zoo), percorsi documentati per NPU A733.
- Farama: [CarRacing](https://gymnasium.farama.org/environments/box2d/car_racing/), riferimento per ambiente visivo e comandi.
- Stanley/Miikkulainen: [NEAT](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf), riferimento per neuroevoluzione con topologia variabile.
- Stable Baselines3: [PPO](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html), riferimento per un secondo algoritmo e uso CPU con politiche numeriche.
- Qt 6.8: [prestazioni QML](https://doc.qt.io/qt-6.8/qtquick-performance.html) e [Canvas](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html), timing e costo degli aggiornamenti grafici.

Da risolvere prima di una promessa di prodotto: convergenza su più semi; costo della geometria e della GUI; parità CPU/NPU della rete custom; distribuzione e licenze di toolkit/modelli se aggiunti; compatibilità fra versioni SDK; temperatura sotto carico; salvataggio/ripresa; uso del tastierino e leggibilità reale. Nessuna stima di minuti di training, numero massimo di auto o FPS è qualificata dalle prove YOLO esistenti.
