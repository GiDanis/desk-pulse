# Gioco — verifica prestazioni e lentezza percepita

La candidata corrente è rc.5; [correzione Gara/PPO e ricevuta corrente](v09-race-ppo-report.md). Le misure seguenti appartengono alla rc.4.

11 ottobre 2026 · **0.9.0-rc.4 consegnata (storico)**, Theme API 2.8 / 67 superfici / Apple Calm 1.6.2.

## 1. Diagnosi

La board è stata controllata in lettura: servizio attivo, zero riavvii; temperatura CPU circa 47 °C, governor schedutil. Al controllo non era attivo un worker di gioco. La RAM non risulta il limite della simulazione. Le prove seguenti usano mondi e archivi isolati: non allenano i piloti dell’utente.

Tre fenomeni distinti: velocità fisica del pilota, velocità del motore rispetto all’orologio reale e regolarità dei fotogrammi. Il candidato corrente del Pilota 1 usa NEAT, popolazione 8, mutazione 0,3, Controllo, senza traffico. Su dieci partenze private variate, dieci secondi simulati, acceleratore iniziale medio 0,144, velocità media 6,25 km/h e massimo 17,83 km/h; sette vetture ancora attive. La media comprende auto ferme/ritirate. È evidenza di un candidato ancora prudente/inesperto, non di un modello qualificato o della velocità a regime di NEAT. [Prova](evidence/v09-game-performance-2026-10-11/pilot-board.json).

## 2. Misure del motore sulla board

Benchmark CPU, due secondi reali per caso, sensori e rete dense 32→16→2 misurati separatamente, accelerazione uniforme sul rettilineo e reset dopo quattro secondi simulati. Controlli della pista attivi. Non è un confronto di qualità di apprendimento né una misura FPS. Valori del primo confronto, governor dinamico, senza promessa di incremento costante:

| Mondi | Prima: secondi simulati/s reale | Dopo | Rapporto |
|---|---:|---:|---:|
| Una vettura | 6,42 | 9,92 | 1,54× |
| Gara, quattro vetture condivise | 4,52 | 6,82 | 1,51× |
| Dieci prove indipendenti | 6,37 | 9,81 | 1,54× |
| 32 prove indipendenti | 5,47 | 9,10 | 1,66× |
| 128 prove indipendenti | 3,15 | 7,05 | 2,24× |
| 256 prove indipendenti | 2,07 | 5,46 | 2,64× |

[Prima](evidence/v09-game-performance-2026-10-11/before-board.json) · [Dopo](evidence/v09-game-performance-2026-10-11/after-board.json). La rete dense occupa circa 0,10 ms per tick a 32 auto nel caso iniziale, contro circa 3,05 ms complessivi. Il collo principale è preparazione dei sensori/fisica, non l’inferenza di questa rete. NEAT usa un grafo Python differente e ha una profilazione separata: non estendere il costo dense a tutte le sue topologie. La [precedente qualifica NPU](v09-game-implementation-report.md) conserva il confronto CPU/NPU sulla rete iniziale; questa modifica non cambia backend.

Una misura end-to-end di 12 secondi non è un confronto corretto della velocità di apprendimento: il motore ottimizzato raggiunge prima una valutazione, durante la quale il contatore delle transizioni di training resta fermo. I log conservano questa distinzione. Nel traffico 8, il campione misurato prima/dopo le ottimizzazioni numeriche passa da 233 a 533 transizioni/s, ma non qualifica la capacità di guida e non è una misura universale.

Una successiva prova NEAT 8 strumentata trova ritardi massimi di consegna scene di **2,002 s**, mentre il massimo di un tick fisico è circa **1,6 ms** e di uno step di valutazione **2,4 ms**: la vista restava indietro senza un corrispondente blocco della fisica. Stessa prova dopo la cessione al thread di invio: **283 scene in 12 s**, massimo intervallo **85,6 ms**, pausa **1,1 ms**; prima 47 scene e pausa 1,4 ms. La cessione riduce in questa prova il numero di passi fisici di circa 2,15% mentre rende regolare la pubblicazione. [Prima](evidence/v09-game-performance-2026-10-11/neat-timers-before-yield.json) · [Dopo](evidence/v09-game-performance-2026-10-11/neat-timers-after-yield.json). Il test permanente richiede almeno dieci scene in un secondo durante la valutazione e nessuna pausa di consegna oltre 250 ms.

## 3. Ottimizzazioni realizzate

1. Nessun ricalcolo dei sensori a fine tick quando il chiamante non li utilizza: Evoluzione, NEAT, valutazioni, Gara, Campione e Prova. PPO mantiene le osservazioni successive necessarie al critic.
2. Nel traffico le osservazioni già calcolate vengono condivise con il solo avversario fisso, evitando una seconda lettura. Le azioni del learner restano prodotte dalla sua rete.
3. Controllo preliminare conservativo del corpo vettura: quando tutto il cerchio che lo contiene è sicuramente nella carreggiata, non si generano i campioni dettagliati dei bordi. La distanza dal segmento centrale della capsula è 1-Lipschitz; margine di 1e-9 sui casi limite. Nei casi incerti si esegue lo stesso controllo precedente, con la stessa discretizzazione a 0,2 m. Nessuna riduzione delle collisioni tra auto o dei sottopassi adattivi.
4. Frazioni dei campioni precomputate una volta per mondo. Nessun cambio di geometria, potenza, gomme, aderenza, reward, seed o configurazione scelta.
5. Pubblicazione delle scene: `multiprocessing.Queue` invia i dati tramite un thread; una sequenza fitta di operazioni NumPy può ostacolare il thread che deve acquisire il GIL. Il motore proseguiva, ma le scene arrivavano a scatti. Una cessione esplicita con `sleep(0)` a ogni pubblicazione permette lo svuotamento della coda, senza rallentamento intenzionale del training o aumento dei tick fisici.
6. La fascia esistente mostra i km/h effettivi della vettura osservata e distingue l’aggiornamento della rete dalla valutazione. Stessa arena, proporzioni e tema, nessuna legenda aggiunta.

## 4. Compatibilità e prove

Confronto con il sorgente rc.3 conservato: 2.400 tick, mondi 1/32/256 e Gara condivisa 4. Snapshot, RNG, osservazioni, reward e terminazioni identici esattamente. [Equivalenza](evidence/v09-game-performance-2026-10-11/equivalence.json). Tre regressioni permanenti aggiunte: consegna regolare delle scene mentre un worker NEAT reale valuta il candidato; controllo dettagliato contro selezione conservativa su 4.096 corpi variati, incluso stato inattivo; osservazioni opzionali senza variazioni di stato/reward. Physics f1-2 e scope rimangono compatibili con i checkpoint.

Tredici test motore, cinque curriculum e sette gate PC passano: simulazione, ripresa PPO/NEAT/Evoluzione, processi, QML, contratto/runtime Theme API, bundle/kit e corpus. [Gate](evidence/v09-game-performance-2026-10-11/regression-final/checks.json). La prova diagnostica `check_game_ui.py` aggiunge p95/massimo agli intervalli software frameSwapped; questi dati non sono tempi GPU o misure ottiche.

## 5. Verifica grafica sulla scheda

Build finale rc.4 su EGLFS/KMS, 960×640, Apple Calm scala 1,1, archivi isolati: Evoluzione 120 s, NEAT 60 s, controllo lifecycle PPO. Tutte le prove passano, nessun avviso QML, Start/Pausa/salvataggio/uscita/input logico verificati; pausa GUI circa 18,5/11,0/17,3 ms. Temperatura CPU massima campionata 51,46 °C. [Qualifica](evidence/v09-game-performance-2026-10-11/board-native/qualification.json).

Intervalli software frameSwapped: Evoluzione mediana 17,48 ms, p95 38,74 ms, massimo 295,79 ms; NEAT con popolazione standard 32 mediana 27,43 ms, p95 56,85 ms, massimo 275,90 ms. La prova NEAT non usa la popolazione 8 del pilota corrente e non dimostra 60 FPS costanti. Il massimo include la cattura finale del fotogramma; conservare anche il valore grezzo. Non attribuire tutte le latenze residue al motore CPU: resta da analizzare pacing/render su carichi NEAT cresciuti e aggiornamenti PPO lunghi. Il miglioramento misurato della consegna dei pacchetti e l’equivalenza della fisica sono separati da questa qualifica grafica.

## 6. Prossimi studi di apprendimento

La velocità del training non certifica che un pilota impari bene. Con NEAT 8 esemplari e senza campione qualificato serve misurare tempo alla prima qualifica e giri validi su più seed; confrontare popolazioni 8/16/32, stagnazione ed esplorazione senza cambiare silenziosamente il profilo corrente. La ricompensa Controllo può favorire un’auto ferma rispetto a un tentativo breve con urto: studiare il trattamento dell’assenza prolungata di progresso, inclusi premio/penalità e compatibilità. Anche l’età del singolo episodio PPO, rispetto all’orologio comune del mondo, richiede una verifica dedicata e versionata. Dettagli nello [studio aggiornato](game-settings-speed-study.md#10-controllo-prestazioni-e-pilota-prudente--11-ottobre-2026).

Traffico con molte copie, reti NEAT cresciute e grandi aggiornamenti PPO restano casi di carico da misurare; solo dopo le misure valutare batch/parallelismo su più core. Non aumentare automaticamente le risorse o i parametri per mascherare un candidato che non accelera. Rimangono i gate di competenza PPO/NEAT/traffico, input e leggibilità fisici e uso prolungato della build finale del MasterPlan.

## 7. Distribuzione e stato corrente

Manifest rc.4 di 545 file verificato, kit aggiornato, backup completo prima dell’installazione. [Ricevuta](evidence/v09-game-performance-2026-10-11/board-install/final-receipt.json): servizio active/running con NRestarts=0, GUI pronta e fresca, nessuna differenza di manifest; preferenze e tema conservati. Confrontati **tutti i campi dei piloti**, inclusi candidato/curriculum/checkpoint, e **tutti i 20 artefatti** con SHA-256 valido: invariati rispetto al backup. Il servizio è stato riavviato, **nessun nuovo reboot OS**. Non è stata avviata una sessione di training sui piloti dell’utente. [MasterPlan 2.54](release-masterplan.md) aggiornato con consegna, studi e gate residui.
