# v0.9 · Gioco — studio di evoluzione, PPO, NEAT e uso della NPU

## Stato implementazione · 11 ottobre 2026

**Aggiornamento rc.3:** [impostazioni e miglioramento del tempo sul giro](game-settings-speed-study.md) implementati e installati dopo autorizzazione. Controllo/Passo, campione verificato distinto dal checkpoint e confronto su prove comuni; cinque seed acquisiti, vantaggio del nuovo reward non uniforme. [Report e limiti](v09-game-settings-pace-report.md). Traffico e backend sperimentali conservano gate di competenza separati.

La candidata corrente è 0.9.0-rc.3; la [consegna rc.2](v09-game-implementation-report.md) conserva le prove precedenti. Il testo seguente conserva lo studio precedente; i candidati numeric9/30 sono sostituiti da race-32-v1, rete 32→16→2 e fisica f1-2. NPU verificata nella rc.2 con una politica appresa, CPU scelta dopo misure; PPO/NEAT e guida nel traffico restano da qualificare.


10 ottobre 2026 · revisione 5 · approfondimento S0 · SmartPC / DeskPulse.

**Stato: ricerca e proposta progettuale.** Nessun simulatore, algoritmo o modello di guida è stato implementato, installato o misurato in questo approfondimento. Le evidenze hardware restano quelle datate nel [primo studio](npu-ai-games-study.md). Le pagine ufficiali e i sorgenti elencati nella sezione 16 sono stati consultati il 10 ottobre 2026; i collegamenti `master/latest` descrivono contenuti mobili, non versioni già scelte per il prodotto.

Questo documento completa lo [studio GUI/UX](v09-game-gui-ux-study.md) e il [MasterPlan](release-masterplan.md). Per i futuri backend PPO/NEAT, le specifiche qui riportate aggiornano i riferimenti della GUI a sola generazione/popolazione e al checkpoint evolutivo. Geometria e controlli concordati rimangono quelli della revisione visiva 2: 3,5″ orizzontale 960×640, arena 912×496, fascia 912×48, 4/6 auto, 2/8 visualizzazione e 5 pausa confermata.

**Estensione di prodotto successiva:** lo [studio piloti, classifica e simulazione](game-drivers-simulation-study.md) rende i piloti entità persistenti con profili/cervelli propri. Le popolazioni e copie ambiente descritte qui appartengono al run di un pilota; non sono la rosa dei piloti. Prima v0.9 con ovale asciutto, vettura standard e dinamica F1 candidata, Pista/Classifica/Progressi e Gara simultanea fra snapshot propri dei piloti; allenamento del solo pilota scelto dall'utente, altri contenuti predisposti tramite cataloghi. `numeric7` e i conteggi seguenti restano il riferimento cinematico F0: F1 propone `numeric9`, da qualificare (rete 9→16→2, 194 parametri).

## 1. Decisione proposta

Predisporre **un ambiente di guida comune e tre backend di apprendimento**, introdotti nell'ordine:

1. **Evoluzione a rete fissa:** riferimento iniziale piccolo, facile da ispezionare e da esportare.
2. **PPO:** primo confronto con apprendimento tramite gradiente e candidato prioritario per esportare una politica fissa sulla NPU.
3. **NEAT:** modalità sperimentale che fa evolvere anche la struttura della rete, interessante da osservare ma più articolata da convertire.

È un ordine di lavoro raccomandato, non una graduatoria di qualità già misurata. NEAT viene studiato anche se l'evoluzione semplice riesce: il suo interesse è il confronto e l'evoluzione della struttura. PPO non è una promessa di maggior velocità o generalizzazione. I due algoritmi sono candidati a estensioni del modulo dopo la prima qualifica dell'ovale; non diventano automaticamente requisiti bloccanti della prima v0.9 e non spostano Compagno/Memoria a nuove release.

La NPU ha un obiettivo esplicito: **provare l'inferenza del campione**, inizialmente a pesi fissi. La fattibilità e il beneficio per la nostra rete restano gate S3. Il gioco può avere un backend CPU verificato mentre questo studio procede.

**Risorse, indicazione aggiornata dell'utente:** il Gioco può utilizzare tutta la RAM effettivamente disponibile dopo Start, secondo le esigenze del backend. Rimosso il precedente tetto candidato di 256 MiB: memoria PyTorch e buffer più grandi non escludono PPO per il solo superamento di quella soglia. La disponibilità si misura nella sessione, non si assume dal vecchio inventario; carichi e crescita si valutano attraverso risposta, stabilità e tempi di calcolo.

## 2. Terminologia e compiti hardware

| Termine | Significato nel gioco | Esecutore iniziale / percorso da studiare |
| --- | --- | --- |
| Ambiente | Pista, sensori, dinamica, collisioni, checkpoint, ricompense. | CPU. |
| Politica / rete di guida | Trasforma l'osservazione in sterzo e accelerazione/frenata. | CPU nel training iniziale; NPU candidata per il campione compilato. |
| Apprendimento | Cambia i pesi; NEAT può cambiare anche i collegamenti. | CPU, dentro un processo separato dalla GUI. |
| Valutazione | Esegue episodi senza modificare la politica e misura la guida. | CPU per ambiente; CPU/NPU per la politica secondo motore reale. |
| Rendering | Disegna pista statica, pose delle auto e UI. | Qt Quick / GPU; separato dal ritmo dell'apprendimento. |
| Compilazione NPU | Converte una rete esportata in un artefatto eseguibile sulla scheda. | PC / toolkit da qualificare. |

Nel gioco, “ragionamento” indica l'inferenza della politica. Una rete eseguita sulla NPU può guidare mentre la CPU gestisce ambiente e apprendimento, ma questa divisione richiede un percorso pratico per distribuire i pesi aggiornati. Non basta scegliere NEAT/PPO per attivarlo.

## 3. Confronto dei tre backend

| Aspetto | Evoluzione fissa | NEAT | PPO |
| --- | --- | --- | --- |
| Oggetto appreso | Pesi di una rete fissa. | Pesi e struttura dei genomi. | Pesi della politica e del valutatore usato nel training. |
| Auto durante Impara | Individui con politiche diverse. | Individui con politiche e strutture diverse. | Copie indipendenti dell'ambiente raccolgono esperienze per una politica condivisa. |
| Unità di avanzamento interna | Generazione. | Generazione; specie, nodi e collegamenti nei dettagli. | Passi totali raccolti e aggiornamenti del modello. |
| Complessità progettuale | Più contenuta. | Specie, crossover, innovazioni e crescita della rete. | Raccolta esperienze, valore atteso, aggiornamenti e iperparametri. |
| Percorso campione NPU | Grafo denso fisso. | Grafo specifico del vincitore da congelare e convertire. | Politica di azione fissa; valutatore non necessario alla guida. |
| Rischio principale da misurare | Ricerca inefficiente o stagnazione. | Costo delle reti irregolari, crescita e specie troppo piccole. | Costo PyTorch/aggiornamenti, ricompense e dati insufficienti. |

NEAT e PPO hanno basi diverse: il [lavoro originale NEAT](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf) studia evoluzione strutturale, specie e crossover; il [lavoro originale PPO](https://arxiv.org/abs/1707.06347) alterna raccolta di esperienze e ottimizzazione per minibatch. La tabella contiene nostre conseguenze progettuali per l'ovale, non benchmark tratti da quei lavori.

In Impara le copie di allenamento sono **tentativi dello stesso pilota, indipendenti fisicamente tra copie**. Il curriculum di una copia può contenere avversari fissi con contatti/sensori comuni: soltanto quel pilota aggiorna la rete. In Gara partecipano invece più piloti salvati nello stesso mondo, tutti a pesi congelati. Questo requisito entra nella prima v0.9 ed è approfondito nello [studio piloti/Gara](game-drivers-simulation-study.md); il profilo osservativo solitario non dimostra capacità di sorpasso.

## 4. Ambiente comune: il lavoro che rende valido il confronto

Proposta: nucleo numerico senza GUI e adapter Gymnasium per PPO. Evoluzione e NEAT usano lo stesso nucleo; niente tre simulatori leggermente diversi. Gymnasium definisce osservazioni, azioni, reset con seed e risultato del passo con segnali di fine episodio distinti. [Ambiente personalizzato](https://gymnasium.farama.org/introduction/create_custom_env/).

Contratto candidato:

- `reset(seed, scenario)` restituisce osservazione e metadati.
- `step(action)` applica un passo fisico fisso e restituisce osservazione, ricompensa, `terminated`, `truncated`, informazioni.
- Snapshot grafico separato: posa, identità del tentativo/episodio e stato, senza generare immagini per il training numerico.
- Versionare `environment`, `physics`, `observation`, `action`, `reward`, geometria/checkpoint e configurazione. Un cambio dei sensori rende incompatibili i vecchi pesi salvo migrazione esplicita.

Le collisioni del veicolo e l'avanzamento attraverso checkpoint ordinati devono essere corretti prima di provare a migliorare una rete. Attraversamenti fra due passi, inversioni, angoli, partenze e reset sono casi del simulatore; un algoritmo non deve “risolvere” un difetto della geometria.

### 4.1 Osservazioni e azioni

Profilo iniziale `numeric7`: cinque distanze ai bordi, velocità e velocità angolare, normalizzate con limiti fisici fissi documentati; vettore float32 a sette elementi. Azioni continue in `[-1, 1]²`: sterzo e comando longitudinale firmato, positivo accelera e negativo frena. La prima fisica non include retromarcia comandata; una penalità per avanzamento negativo resta utile contro exploit geometrici.

**Rischio progettuale:** sette valori non garantiscono osservabilità sufficiente in ogni curva o direzione. Se il simulatore introduce stato nascosto dell'attuatore, oppure gli stessi sensori corrispondono a situazioni che richiedono azioni opposte, prima del confronto va deciso un profilo osservativo adeguato. Candidati da confrontare: stato dello sterzo applicato, breve storia dei sensori oppure orientamento rispetto alla tangente locale della pista. La tangente sarebbe informazione aggiuntiva dichiarata, non sterzo preparato. Ogni aggiunta vale per tutti i backend e cambia `observationVersion`; non passare alla sola PPO dati privilegiati.

Mantenere identici mapping, saturazioni e limiti dello sterzo fra training e campione. Per PPO, il campione deterministico deve riprodurre il clipping/mapping realmente usato nel training; non aggiungere un `tanh` all'esportazione che cambi la politica. La normalizzazione delle azioni e osservazioni è raccomandata nelle [indicazioni SB3](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html); le scelte specifiche sopra sono proposte per il nostro ambiente.

### 4.2 Ricompensa e fitness

Schema candidato, senza coefficienti qualificati:

`r = w_progress * delta_progress_signed - w_time * dt - w_jerk * delta_steer² + bonus_valid_lap - penalty_track_exit`

`delta_progress_signed` usa il percorso ordinato e uno stato di avanzamento coerente, non la distanza euclidea né il solo movimento positivo. Una sequenza avanti/indietro non deve accumulare premi; bonus di checkpoint/giro solo su attraversamenti validi, senza ripetizioni a cavallo della linea. Validare il rapporto tra premio sul giro, avanzamento e costo temporale. Lo sterzo instabile è un termine opzionale da aggiungere solo se non impedisce di affrontare le curve.

Per l'evoluzione, fitness candidata = media della somma non scontata delle ricompense su scenari di training assegnati in comune a tutta la popolazione. PPO usa le stesse ricompense del nucleo, con la propria stima scontata nel training. Il confronto pubblico usa risultati di guida esterni: tasso di giri validi, avanzamento, collisioni e tempi; non confronta direttamente loss PPO e fitness NEAT.

Il primo giro deve essere osservabile senza rendere il premio troppo raro. Un'auto ferma, oscillante, che taglia la pista o sfrutta un reset non può diventare campione. Baseline casuale e controller deterministico separato aiutano a distinguere problemi dell'ambiente da problemi dell'apprendimento.

### 4.3 Fine episodio e reset

Proposta: uscita/collisione e completamento del compito definiscono `terminated`; limite esterno di passi definisce `truncated`. Uno stallo può essere un fallimento del compito se definito esplicitamente. Pausa utente congela lo stato: non genera una ricompensa o un fallimento inventato. Arresto/crash interrompe la sessione e non crea un episodio valido nei risultati.

Gymnasium spiega perché distinguere fine del compito e interruzione esterna cambia il calcolo del valore futuro. Se scegliamo un compito con orizzonte temporale intrinseco, il tempo residuo deve far parte dell'osservazione. [Gestione dei limiti temporali](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/).

Gli adapter vettoriali SB3 hanno API e autoreset propri: conservare l'osservazione finale nell'`info` previsto dall'adapter ed evitare di usare la prima osservazione del nuovo episodio come ultima del vecchio. Non trattare `Gymnasium VectorEnv` e `SB3 VecEnv` come interfacce intercambiabili. [Documentazione VecEnv](https://stable-baselines3.readthedocs.io/en/master/guide/vec_envs.html).

## 5. Evoluzione fissa: riferimento iniziale

Con `numeric7`, candidato MLP `7→16→2`, **162 parametri**. Attivazioni, normalizzazione e precisione fanno parte del profilo; la forma della rete da sola non definisce la politica.

Confrontare popolazioni 16/32/64 sullo stesso ambiente. Conservare elite, generare mutazioni dei pesi, registrare distribuzione dei risultati e seed. Numero di elite, ampiezza delle mutazioni e criterio di selezione sono configurazione versionata, non slider liberi nel kiosk. Evitare un confronto nel quale tutti i candidati migliori abbiano ricevuto soltanto partenze più facili.

Riferimento CPU con calcoli raggruppati, controlli di valori finiti e footprint piccolo. Primo esportabile NPU: il campione congelato e confrontato sugli stessi vettori CPU. Il vantaggio previsto è la semplicità dello studio, non un'accelerazione già misurata.

## 6. PPO: profilo e vincoli

Libreria candidata: **Stable Baselines3 con PyTorch**, riutilizzando l'implementazione. PPO aggiorna una politica usando esperienze raccolte dalla politica corrente; il valore atteso aiuta il training. La raccolta e l'ottimizzazione sono fasi diverse e vanno esposte correttamente allo stato della sessione. [PPO SB3](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html).

### Profilo iniziale da sperimentare

- `MlpPolicy`, `device=cpu`, azioni continue; primo confronto con attore `7→16→2` e valutatore separato `7→16→1`.
- Conteggio teorico per queste due torri: attore 162, valutatore 145, due parametri della dispersione delle azioni = **309 parametri**; dipende dalla configurazione effettiva. La RAM del runtime non si deduce da questo numero.
- Confrontare 1/4/8 ambienti indipendenti; partire da esecuzione nello stesso worker e misurare prima di introdurre sottoprocessi.
- Candidato `n_steps=256` per ambiente, `batch_size=64`, `n_epochs=4`; learning rate 3e-4, clip 0,2, gamma 0,99 e GAE lambda 0,95 sono valori iniziali di ricerca, non tuning validato.
- Con quattro ambienti il rollout ha 1.024 transizioni; un aggiornamento con quattro epoche e batch 64 esegue 64 minibatch. I passi mostrati sono la somma delle transizioni dei quattro ambienti, non il numero dei tick del renderer.
- Un attore con due strati da 32 è una seconda prova se necessario. Va registrata la maggiore capacità: il confronto non rimane “stessa rete”.

**Sconto e tempo fisico:** con una decisione ogni 1/60 s, gamma 0,99 dimezza il peso di una ricompensa futura dopo circa 69 passi, cioè 1,15 s simulati. Il giro completo può essere molto più lungo: il premio denso aiuta, ma gamma non va scelto soltanto copiando un default. Confrontare 0,99 / 0,995 / 0,999 in un pilot controllato; il cambio di frequenza della politica richiede di riesaminare l'orizzonte temporale. Questi valori sono un'analisi matematica del profilo proposto, non risultati di apprendimento.

Il buffer numerico delle osservazioni è piccolo rispetto al runtime: 1.024 × 7 × 4 byte = 28.672 byte per le sole osservazioni. Azioni, valori, log probabilità, ricompense, gradienti e memoria PyTorch si aggiungono. Questa aritmetica descrive solo una parte della memoria usata; il backend può utilizzare la RAM disponibile senza un tetto fisso del modulo.

La documentazione SB3 consiglia principalmente CPU per PPO senza CNN. Non è una raccomandazione per la nostra VIPLite né una prova di prestazioni A733. Evitare otto processi solo perché sono disponibili otto CPU; profiler, pool numerici e avvisi della dashboard determinano il profilo sostenibile.

### Pausa durante gli aggiornamenti

Il callback dopo un passo non garantisce una pausa pronta durante l'ottimizzazione. Serve controllo cooperativo anche tra minibatch, gestione del rollout parziale e un confine consistente per i checkpoint. Il worker non restituisce ack “Pausa” mentre sta ancora aggiornando i pesi. Se un singolo blocco PyTorch eccede il budget, ridurre/tarare il profilo o interrompere il worker recuperando l'ultimo checkpoint; non promettere ripresa esatta di un blocco interrotto.

Il campione PPO guida in modalità deterministica; durante Impara l'esplorazione può produrre traiettorie peggiori di quelle del modello valutato. Il miglior checkpoint può essere precedente all'ultimo: selezionarlo mediante validazione separata, non chiamare campione ogni aggiornamento.

## 7. NEAT: profilo, costi e semantica

Libreria candidata: **neat-python**. Il progetto descrive genomi di nodi/connessioni, fitness, riproduzione e specie. [Panoramica NEAT-Python](https://neat-python.readthedocs.io/en/latest/neat_overview.html).

Profilo candidato:

- Sette ingressi e due uscite come gli altri backend; partire da struttura minima, senza strato nascosto fisso.
- `feed_forward=True`, aggregazione `sum`, una sola attivazione scelta e nessuna mutazione dell'attivazione nel primo profilo. Confrontare popolazioni 32/64; 16 rimane una prova di costo, non popolazione adeguata alle specie già dimostrata.
- Specie, soglia di compatibilità, stagnazione, elitismo e probabilità di mutazione configurati esplicitamente. La configurazione ufficiale distingue connessioni ricorrenti, crescita e operatori: non chiamare NEAT una semplice mutazione dei 162 pesi. [Configurazione](https://neat-python.readthedocs.io/en/latest/config_file.html).
- Nessun limite di nodi/connessioni viene assunto come parametro universale già disponibile. Se serve un limite rigido di risorse, definire un adapter di mutazione che lo rispetti o fermare il profilo e dichiararne il motivo. Una penalità di complessità cambierebbe l'obiettivo e deve essere versionata.

L'interpretazione in Python di reti diverse può costare più di matrici dense raggruppate. È una previsione da misurare per fase, non un difetto prestazionale già osservato. Il numero delle specie non è percentuale di completamento e può crescere/scendere senza rappresentare un miglioramento.

**Dettaglio importante per l'esportazione:** nel sorgente consultato, `tanh` NEAT usa un fattore 2,5 sull'ingresso e `sigmoid` un fattore 5, con clipping. Sostituirli con le funzioni standard senza queste trasformazioni cambia la rete. Conservare anche bias, response, ordine dei nodi, connessioni abilitate e aggregazioni. [Attivazioni nel sorgente](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/neat/activations.py).

Il repository consultato include esportazione JSON della rete; è un formato intermedio, non un `.nb` né prova di export ONNX/NPU funzionante. Prima verificare l'API della versione scelta, poi confrontare un interprete di riferimento con il grafo esportato. [Modulo export](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/neat/export/__init__.py).

## 8. NPU: obiettivo concreto e catena di verifica

La documentazione Vivante/Radxa distingue compilazione offline, runtime e driver. VIPLite carica modelli precompilati; il JIT del driver unificato non va assunto disponibile nella nostra installazione. [SDK](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-sdk).

| Percorso | Prima prova utile | Limite da risolvere |
| --- | --- | --- |
| Evoluzione fissa → campione NPU | MLP congelato, operatori elementari. | Conversione e beneficio end-to-end della rete piccola. |
| PPO → campione NPU | Esportazione della sola catena che produce azioni deterministiche. | Normalizzazione, clipping, operatori e parità. |
| NEAT → campione NPU | Vincitore feedforward congelato, rappresentazione DAG fedele. | Struttura sparsa/irregolare e semantica degli operatori. |
| Training con inferenza NPU | Politica fissa dentro una raccolta, poi aggiornamento pesi CPU. | Distribuzione dei nuovi pesi e costo del cambio di modello. |
| Training interamente NPU | Nessun percorso qualificato. | Gradiente, ottimizzatore e/o evoluzione non verificati. |

Percorso PPO proposto: checkpoint CPU → wrapper deterministico delle azioni → ONNX → test CPU di parità → ACUITY per A733/v3 → `.nb` → runner persistente VIPLite → prova della guida. SB3 documenta export ONNX e segnala che il postprocessing delle azioni continue va trattato: non basta esportare un oggetto policy e assumere azioni identiche. [Export SB3](https://stable-baselines3.readthedocs.io/en/master/guide/export.html).

La guida ACUITY documenta parsing, quantizzazione e compilazione, con target v3 per A733. Operatori, forme, batch e quantizzazione della nostra rete sono ancora da qualificare. Calibrare sugli ingressi reali raccolti; includere bordi e velocità estreme. [Procedura ACUITY](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-usage).

Prova S3 proposta:

1. Almeno 1.000 osservazioni reference con versione/scenario, azioni CPU e hash del modello.
2. Confronto per componente, valori finiti, saturazioni e mapping; definire tolleranze prima dell'esito. La tolleranza numerica deve poi superare episodi completi con gli stessi seed.
3. Misura separata di apertura/caricamento, preparazione/copie, inferenza, lettura e decisione completa: p50/p95/p99, freddo/caldo.
4. Confronto CPU/NPU a sessione persistente, stesso batch e stessi ingressi; benchmark batch 1 e batch condiviso se convertibile.
5. Guida di valutazione, CPU/RAM/temperatura, convivenza dashboard e stop. Non usare il throughput YOLO come FPS del gioco.
6. NPU promossa se corretta e con vantaggio ripetibile di tempi/risorse, oppure se abilita una politica altrimenti insostenibile; pubblicare anche esiti negativi.

PPO con una politica condivisa ha un possibile vantaggio organizzativo rispetto a 32 reti diverse: può raggruppare più osservazioni sotto gli stessi pesi. È un'inferenza progettuale da provare. Non serve il valutatore PPO sul percorso di guida del campione.

Durante Impara la compilazione a ogni generazione/aggiornamento non è il percorso predefinito. Un test di pesi aggiornabili o ricompilazione periodica deve includere costo totale, blocchi, trasferimento atomico, recupero e versioni del modello; attivarlo solo dopo misura. Non si promette compatibilità fra stack TIM-VX/OpenVX e VIPLite dalla sola parentela del chip.

## 9. Dipendenze e fattibilità sulla scheda

Il repository SmartPC letto in questa sessione ha un ambiente di sviluppo Qt/Python, non un lockfile del futuro training. Nessuna libreria AI è stata aggiunta qui.

| Componente candidato | Riscontro documentale | Verifica da fare in S1/S2 |
| --- | --- | --- |
| NumPy / nucleo | Elaborazione numerica comune proposta. | Versione, pool numerici e prestazioni PC/ARM. |
| Gymnasium | Interfaccia ambiente usata da PPO. | Versione compatibile con SB3 scelta, checker e seed. |
| neat-python | Metadata `master`: Python ≥3.8, core senza elenco di dipendenze obbligatorie; extra esempi/GPU separati. | Pacchetto/tag fissato, config coerente, prestazioni e checkpoint. |
| SB3 / PyTorch | `setup.py` consultato: Python ≥3.10, Gymnasium, NumPy, Torch e cloudpickle. | Wheel CPU per ABI/Python/ARM della board, import, istruzioni CPU, disco/RAM e thread. |
| ONNX / toolkit NPU | Catena di esportazione/conversione proposta. | Disponibilità PC, versioni operatori, compatibilità con driver e licenza redistribuzione artefatti. |

Fonti dei metadata: [NEAT pyproject](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/pyproject.toml), [SB3 setup](https://raw.githubusercontent.com/DLR-RM/stable-baselines3/master/setup.py). La pagina NEAT consultata espone intestazione 1.1.0 e campi marcati 2.1, mentre il sorgente master dichiara 2.1.0; SB3 master mostra una versione di sviluppo. Per questo la selezione richiede un tag/pacchetto preciso con config, sorgenti e dipendenze allineati, non l'installazione indiscriminata di `latest`.

SB3 è MIT e neat-python ha licenza BSD a tre clausole nei file consultati. Conservare avvisi e licenze delle versioni effettivamente distribuite; verificare separatamente toolkit NPU e dipendenze. [Licenza SB3](https://raw.githubusercontent.com/DLR-RM/stable-baselines3/master/LICENSE), [licenza NEAT](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/LICENSE).

Importare backend pesanti soltanto nel worker dopo Start. Una libreria assente rende il backend “non disponibile” con motivo e mantiene utilizzabili quelli qualificati. Niente download o installazioni durante una sessione. PyTorch può utilizzare la RAM disponibile dopo Start: il superamento di 256 MiB non è più un motivo di esclusione. Registrare memoria disponibile e picchi effettivi, distinguendo necessità del backend, buffer utili e crescita anomala.

### 9.1 Allocazione della RAM disponibile

Dopo Start rilevare la memoria effettivamente disponibile e dimensionare le allocazioni utili al backend, senza quota fissa in MiB o percentuale arbitraria. Non preallocare tutta la RAM per consumarla: usare quanto serve a modello, ottimizzatore, rollout e popolazione. Rivalutare la disponibilità durante la sessione; nessun valore del vecchio inventario diventa una prenotazione permanente.

Sono candidati a un confronto anche rollout/batch e popolazioni più grandi dei profili iniziali. Più RAM non implica più velocità: aumentare ambienti, individui o batch soltanto confrontando tempo di apprendimento, durata degli aggiornamenti e risposta di input/GUI. Il numero di auto disegnate e la coda IPC restano indipendenti dalla memoria concessa al training.

In Pausa si può conservare lo stato utile alla ripresa; alla chiusura della sessione rilasciare worker, buffer e modello quando non più necessari. In caso di disponibilità ridotta durante il lavoro, gestire le allocazioni e il profilo senza compromettere la dashboard. I criteri riguardano stabilità e prestazioni effettive, non il superamento di una quota di RAM.

### 9.2 Profili ampliati di ricerca

L'indicazione sulla RAM amplia lo spazio degli esperimenti. I valori qui sotto sono candidati, non capacità già dimostrate sulla board e non limiti massimi di memoria.

| Dimensione | Primo riferimento | Estensioni da confrontare | Cosa decide l'adozione |
| --- | --- | --- | --- |
| Popolazione Evoluzione | 16 / 32 / 64 individui. | 128 / 256, poi ulteriori incrementi se utili. | Successo per passi e tempo, durata generazione, costi sensori/collisioni. |
| Popolazione NEAT | 32 / 64 individui. | 128 / 256 con misure di specie e crescita. | Diversità utile, successo e costo della valutazione/riproduzione. |
| Ambienti PPO | 1 / 4 / 8 copie indipendenti. | 16 / 32, senza equipararli al numero di processi. | Transizioni/s, apprendimento, costi di scheduling e pause. |
| Rollout PPO per ambiente | 256 passi. | 1.024 / 2.048 passi. | Qualità dei dati, frequenza aggiornamenti, tempo attivo al miglioramento. |
| Minibatch PPO | 64. | 128 / 256, poi altri valori compatibili con il rollout. | Durata del singolo blocco e qualità degli aggiornamenti. |
| Capacità attore denso | 7→16→2. | 7→32→32→2 e 7→64→64→2. | Beneficio di guida/robustezza rispetto al costo. |

Si può usare più RAM per una popolazione o un rollout più grande, ma non si devono aumentare tutte queste dimensioni insieme e attribuire il risultato a un singolo fattore. Sequenza del pilot: numero di individui/ambienti → capacità rete → rollout/minibatch. Mantenere fisica, osservazioni, ricompense e scenari fissi; conservare il riferimento precedente e registrare ogni configurazione.

Per le reti dense proposte, i conteggi dell'attore sono 162 / 1.378 / 4.802 parametri. Con PPO a torri separate attore/valutatore della stessa larghezza, i totali teorici sono 309 / 2.725 / 9.541, includendo due parametri di dispersione delle azioni. Sono pochi pesi rispetto alla RAM della scheda; gli incrementi hanno senso se migliorano la guida, non perché occorra consumare la memoria. Per NEAT la capacità cresce tramite l'algoritmo, non selezionando una di queste architetture dense.

### 9.3 Conti dei buffer PPO e impiego utile della memoria

Nel `RolloutBuffer` SB3 consultato, con osservazioni a sette valori e azioni a due valori float32, gli array base contengono 15 float per transizione: osservazioni (7), azioni (2) e sei scalari fra ricompense, ritorni, inizio episodio, valori, log probabilità e vantaggi. Il costo teorico è quindi **60 byte per transizione**. [Sorgente RolloutBuffer](https://raw.githubusercontent.com/DLR-RM/stable-baselines3/master/stable_baselines3/common/buffers.py).

| Esempio candidato | Transizioni per raccolta | Array base del buffer | Tempo simulato per ambiente a 60 decisioni/s |
| --- | ---: | ---: | ---: |
| 4 ambienti × 256 passi | 1.024 | 60 KiB | 4,27 s |
| 16 ambienti × 1.024 passi | 16.384 | 0,94 MiB | 17,07 s |
| 32 ambienti × 2.048 passi | 65.536 | 3,75 MiB | 34,13 s |

Questi conti non includono copie/flattening, tensori minibatch, autograd, ottimizzatore, librerie, simulatore, IPC e GUI: il picco si misura durante l'esecuzione. I secondi sono di simulazione per ambiente, non una previsione del tempo reale di raccolta. Le righe illustrano ordini di grandezza, non sono una prova simultanea nella quale cambiare numero di ambienti e rollout senza controlli.

Il buffer PPO conserva esperienze della politica corrente per l'aggiornamento e viene rinnovato dopo il ciclo: una grande raccolta storica non diventa automaticamente un replay utilizzabile da PPO. Registrazioni utili per ricerca, validazione e calibrazione NPU sono separate dai rollout di training e conservano versione della politica e provenienza. [Implementazione buffer SB3](https://raw.githubusercontent.com/DLR-RM/stable-baselines3/master/stable_baselines3/common/buffers.py).

Dopo i pilot scegliere il profilo locale per successo, tempo al primo giro e risposta della vista. Un profilo più grande si promuove se porta un beneficio ripetibile; il worker continua ad avere tutti i dati necessari in RAM, senza una quota artificiale. Il confronto NPU comprende anche le reti dense ampliate, ma una rete da poche migliaia di parametri non dimostra da sola che l'acceleratore sia vantaggioso.

Addestramento PPO sul PC e campione sulla board è un'alternativa valida se il training locale non è sostenibile. Deve essere etichettata come modello addestrato sul PC: non soddisfa da sola la modalità “impara sulla scheda”.

Ogni pilota PPO ha una propria politica/valutatore/ottimizzatore; le copie ambiente condividono soltanto la politica di quel pilota. L'utente sceglie e allena un solo pilota alla volta, poi lo salva; nessuna rotazione automatica. Gli altri stati utili possono rimanere in RAM. In Gara ciascun pilota usa la propria politica congelata: critic/ottimizzatore non sono necessari alla guida. Gli avversari del curriculum sono bot/snapshot fissi, non altri learner. Prova standard resta valutazione solitaria a pesi fissi: regole e risultati sono nello [studio piloti](game-drivers-simulation-study.md).

## 10. Integrazione GUI/UX: stessa arena, dati corretti

Aggiungere nel Menu, a sessione ferma, **Metodo: Evoluzione / PPO / NEAT**. Metodo e motore sono due informazioni diverse: `PPO · CPU` oppure `Campione · NPU`; la scelta dell'algoritmo non forza un acceleratore.

| Elemento | Evoluzione / NEAT | PPO |
| --- | --- | --- |
| Fascia compatta | Stato, `Gen 12`, auto osservata, azione 5. | Stato, `Passi 24k` o `Agg 12` con etichetta esplicita, tentativo osservato, azione 5. |
| Auto selezionata | Identificativo individuo/genoma. | Identificativo ambiente + episodio. |
| Durante ottimizzazione | Fase selezione/mutazione esplicita. | “Aggiorna rete”; pose ferme se la raccolta è ferma. |
| Progressi | Valutazioni e generazioni nei dettagli. | Valutazioni e passi/aggiornamenti nei dettagli. |
| Dettagli aggiuntivi | NEAT: nodi, collegamenti, specie. | Ambienti, rollout e ultimo aggiornamento. |

In Gara la fascia mostra giro/posizione e pilota, senza contatori di training; 4/6 cambia concorrente osservato e 2/8 solo visualizzazione. I backend ammessi espongono la medesima interfaccia qualificata di osservazioni/azioni, incluse le informazioni sugli avversari.

Durante raccolta/ottimizzazione restano catturate le frecce; 4/6 sceglie il tentativo e 2/8 cambia soltanto visualizzazione. In Campione con una sola auto, 4/6 non inventa altri candidati. Il reset PPO cambia episodeId, così il renderer non interpola da una posa finale alla partenza successiva. Nessun contatore generazione fittizio per PPO.

**Progressi comune:** valutazione della politica/campione su scenari di validazione, asse x passi totali raccolti oppure tempo attivo reale dichiarato. All'interno di Evoluzione/NEAT è possibile il grafico per generazione già studiato; non sovrapporlo direttamente agli aggiornamenti PPO. Record cumulativo e risultato dell'ultima valutazione sono distinti, con possibilità reale di regressione.

La selezione del metodo si applica a una sessione nuova o a un salvataggio compatibile di quel metodo. Non convertire una popolazione NEAT in PPO né riutilizzare il suo grafico come continuazione. Mostrare voci future non disponibili solo con motivo leggibile; la prima release può esporre soltanto Evoluzione.

Questa revisione aggiunge contratti candidati `algorithm`, `algorithmCapabilities`, `trainingPhase`, `environmentSteps`, `updateIndex`, `generation` opzionale, `policyVersion`, `selectedAttemptId`, `trainingEngine`, `inferenceEngine`, `validationSummary` e azione `game.algorithm.select`. Non sono API implementate. La fascia resta 48 px; loss, specie e rete non diventano pannelli permanenti sopra la pista. Le tavole r2 rappresentano ancora soltanto il concept evolutivo, senza nuove prove visive multi-algoritmo.

## 11. Processo, pause e sicurezza degli stati

Controller unico con `Pronto → Avvio → Raccolta/Valutazione → Aggiornamento → Pausa`, modalità Campione e Gara separate, con fault esplicito. Gara usa un controller del mondo comune e non attraversa Aggiornamento; l'ack ferma tutti i partecipanti e il timer. Uno stesso algoritmo può alternare fasi interne senza cambiare i comandi di navigazione. Core, worker e broker devono usare lo stesso stato confermato.

Proposta di interfaccia backend: `capabilities`, `start(profile)`, `advance(budget)`, `request_pause`, `checkpoint_consistent`, `export_policy`, `metrics`. Non è uno schema Python già implementato. `advance` deve avere confini di interruzione utili; nascondere un intero `learn()` o `Population.run()` bloccante non basta per la pausa ≤250 ms.

All'ack di pausa non devono esserci passi né mutazioni in corso. Pubblicare epoch/sequence/sessionId e policyVersion; scartare risposte vecchie. Home, uscita e urgente sospendono anche l'ottimizzazione; il ritorno attende Start. I/O asincrono non sblocca la navigazione fingendo che il training sia fermo.

Budget e controlli della GUI r2 rimangono candidati: feedback p95 ≤150 ms, pausa ≤250 ms, obiettivo 60 FPS e nessuna swap indotta. Se non sostenibili, restringere il profilo e dichiarare il limite prima della candidata; non trasformare un fallimento di risorse in nuove regole implicite di input.

## 12. Persistenza: campione e ripresa sono artefatti diversi

Manifest comune: schema, algoritmo/versione libreria, ambiente/observation/action/reward/physics/track revision, configurazione, seed, conteggi, provenance PC/board, motore, precisione e hash. Artefatti locali versionati con checkpoint precedente valido; salvataggio atomico e successo dopo persistenza confermata.

| Backend | Campione per guidare | Ripresa del training |
| --- | --- | --- |
| Evoluzione fissa | Pesi, attivazioni e normalizzazione. | Popolazione, generazione, RNG, scenari, stato/confine di valutazione. |
| NEAT | Genoma vincitore/config e rete congelata fedele. | Popolazione, specie, innovazioni, RNG, generazione e versione/config della libreria. |
| PPO | Attore e preprocessing/postprocessing deterministico. | Attore, valutatore, ottimizzatore, contatori/schedule, RNG e normalizzazione; stato rollout/ambienti se si promette ripresa esatta a metà raccolta. |

Il checkpointer NEAT nel sorgente consultato conserva popolazione, specie e RNG usando gzip/pickle; questo non include il nostro simulatore e non certifica ripresa identica dopo cambio versione. [Sorgente checkpoint](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/neat/checkpoint.py).

Proposta iniziale PPO: salvataggio a confine di aggiornamento consistente, ripresa con nuovi episodi dichiarata; nessuna promessa di identità dei tentativi interrotti. La pausa in RAM può conservare il rollout parziale se supportato, ma checkpoint su disco e pausa non sono equivalenti. Stato `Salvato` e disponibilità `Ripresa` hanno esiti distinti.

Per NEAT salvare a un confine consistente della generazione; se una pausa cade durante una valutazione, distinguere stato mantenuto in RAM da ultimo checkpoint durevole. File incompatibile o corrotto: conservare evidenza e precedente valido, niente avvio automatico al reboot. Non caricare pickle/modelli esterni arbitrari nel processo kiosk: importazione di modelli non fa parte dell'MVP.

## 13. Protocollo sperimentale e confronto corretto

La scelta si basa su prove della nostra pista. Le pubblicazioni originali non dimostrano risultati su questo ambiente. Variabilità tra seed e valutazione separata sono richiamate dalle [indicazioni SB3](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html).

### Sequenza proposta

1. **Controllo ambiente:** determinismo, geometria e mapping, baseline casuale e controller separato; validare che il compito sia risolvibile e il premio non sfruttabile.
2. **Smoke PC:** un seed per backend, valori finiti, crescita dei contatori, pausa e checkpoint. Non è prova di apprendimento affidabile.
3. **Pilot PC:** cinque seed indipendenti per ciascun profilo qualificato; budget iniziali 100k, 500k e 1M transizioni, registrando tempo e distribuzioni. Sono budget di ricerca, non stime di minuti sulla board.
4. **Validazione periodica:** dieci episodi con partenze/scenari separati dal training, stessa frequenza in passi per tutti; selezione del miglior checkpoint solo qui. Valutazione deterministica dei campioni PPO, nessuna mutazione in tutti i backend.
5. **Test finale separato:** scenari/seed non usati per scegliere checkpoint o iperparametri; ovale di dimensioni differenti e perturbazioni di partenza. Circuiti complessi diventano test aggiuntivi quando la geometria è validata.
6. **Board:** ripetere i profili candidati in esecuzione isolata e con dashboard, includendo provider, input, overlay/urgenti, sessione almeno 30 minuti e termica stabilizzata.

### Due confronti da pubblicare

- **Stesso numero di transizioni:** ogni passo di ogni individuo/ambiente conta. Mostra quanta esperienza serve, senza chiamare uguali generazioni di dimensioni diverse.
- **Stesso tempo attivo reale:** include simulatori, inferenza, aggiornamenti e valutazioni; esclude pause utente. Misurare separatamente avvio/caricamento e tempo di sola formazione per interpretare il costo.

Registrare anche tempo simulato, tempo al primo giro di training e al primo giro in validazione, successo su episodi finali, avanzamento, collisioni, mediana e dispersione dei tempi sui soli giri validi, CPU/RSS/swap, tempi per fase e frame pacing. Un algoritmo con zero giri validi non ha “tempo sul giro zero”; il dato è assente. Valutazioni hanno costo esplicito e contatori separati dai passi di training.

L'ovale può essere memorizzato con un comportamento ripetitivo; una rete che completa solo la partenza standard non è un guidatore generale. Non dichiarare il vincitore da un unico seed o dal miglior filmato. Pubblicare fallimenti, gate aperti e configurazioni. Cinque seed sono il primo criterio pratico, non sufficienza statistica universale.

Tenere fissi fisica/sensori/reward per il confronto principale. Un confronto con dimensioni di rete differenti valuta profili completi, non il solo algoritmo. Budget di tuning documentato per metodo; niente tuning sul test finale.

## 14. Rischi e prove che li risolvono

| Rischio | Prova / decisione |
| --- | --- |
| Sensori insufficienti | Analisi di stati ambigui e confronto osservazioni prima di scegliere il backend. |
| Premio sfruttabile | Controller avversi: fermo, oscillazione, taglio, checkpoint fuori ordine e reset. |
| PPO non apprende in tempi utili | Curve per passi/tempo e cinque seed; semplificare compito o tarare reward prima di aggiungere GPU/NPU. |
| Disponibilità RAM cambia durante la sessione | Tutta la RAM disponibile utilizzabile; misurare import/picchi, gestire allocazioni e crescita anomala. Nessun tetto fisso di 256 MiB. |
| NEAT cresce oltre il carico sostenibile | Misure nodi/collegamenti/specie e tempi; profilo limitato e motivo di stop. |
| Pause lente nelle librerie | Prove in sensori, riproduzione e minibatch; cooperazione o recupero worker. |
| NPU cambia le azioni | Reference vettoriali più episodi di guida e confronto precisione. |
| NPU più lenta della CPU | Misura completa a runtime persistente; adozione motivata, esito negativo conservato. |
| GUI ingannevole | Nessuna generazione PPO inventata; tentativi indipendenti e motore reale; grafico da valutazioni. |
| Ripresa incompleta presentata come esatta | Confine checkpoint e capability espliciti per metodo/versione. |

## 15. Fasi e decisioni di rilascio

| Fase MasterPlan | Approfondimento algoritmi | Criterio di uscita proposto |
| --- | --- | --- |
| S0 | Questo studio e fonti primarie. | Decisioni/candidati separati dai risultati. |
| S1a | Nucleo comune, osservazioni/reward, evoluzione fissa. | Ambiente corretto e apprendimento riproducibile. |
| S1b | Gara condivisa/curriculum traffico secondo studio piloti; confronto adapter PPO e NEAT sul PC come estensione. | Checkpoint, pause e confronto su seed senza promesse di prestazioni board. |
| S2 | Installabilità/profili, uso della RAM disponibile e tempi per ciascun backend. | Metodo disponibile soltanto se sostenibile e verificato. |
| S3 | Campione denso/PPO prioritario; NEAT congelato successivo. | Conversione fedele, costo completo e decisione CPU/NPU. |
| S4 | Pista/Classifica/Progressi, Gara e contratti adattati all'algoritmo. | Geometria r2, contatori veri, capture input e lifecycle. |
| S5 | Candidata con soli backend promossi. | Evidenze PC/board/pannello, persistenza e stabilità. |

S1b include il confronto di studio degli algoritmi e non obbliga a consegnare tre backend nella prima release. Il successivo requisito piloti/Gara/Classifica/F1 estende invece il perimetro minimo v0.9 come descritto nello [studio simulativo](game-drivers-simulation-study.md); queste funzioni richiedono gate propri. Raccomandazione di prodotto: v0.9 iniziale Evoluzione; estensione PPO prima di NEAT se supera i gate. Le versioni delle estensioni si assegnano dopo le prove; la sequenza v0.10 Compagno / v0.11 Memoria resta quella concordata.

**Risposta di fattibilità:** progettare i tre metodi nello stesso modulo ha senso. La fisica e la GUI sono condivisibili; apprendimento, contatori, checkpoint e profili di risorse richiedono adapter specifici. L'uso reale della NPU è un esperimento prioritario sul campione e non una proprietà già acquisita scegliendo PPO/NEAT. Il prossimo risultato da produrre, dopo autorizzazione a implementare, è l'ambiente PC S1 con evidenze di apprendimento.

## 16. Fonti primarie consultate e limiti

Consultazione: 10 ottobre 2026. Sintesi originali brevi, senza copia degli articoli. Pagine/sorgenti mobili da rifissare alla versione scelta durante S1. Questa ricerca non comprende installazioni, test di pacchetti ARM o nuove sonde sulla board.

| Fonte | Informazione utilizzata | Limite per SmartPC |
| --- | --- | --- |
| [Stanley e Miikkulainen, 2002](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf) | NEAT: evoluzione della struttura, specie e crossover. | Benchmark del lavoro diversi dalla nostra pista. |
| [Schulman et al., PPO, 2017](https://arxiv.org/abs/1707.06347) | Raccolta e ottimizzazione per minibatch. | Nessuna garanzia di convergenza sul nostro ambiente. |
| [PPO SB3](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html) | MLP, CPU, attore/valore, rollout e parametri. | Non backend VIPLite; master è sviluppo. |
| [RL tips SB3](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html) | Normalizzazione, valutazione e più seed. | Default e tuning non sono risultati board. |
| [VecEnv SB3](https://stable-baselines3.readthedocs.io/en/master/guide/vec_envs.html) | Ambienti indipendenti, autoreset e osservazione finale. | Richiede adapter, non coincide con VectorEnv Gymnasium. |
| [Buffer SB3](https://raw.githubusercontent.com/DLR-RM/stable-baselines3/master/stable_baselines3/common/buffers.py) | Array rollout, formato e ciclo on-policy. | Conteggi teorici; picco del runtime da misurare. |
| [Export SB3](https://stable-baselines3.readthedocs.io/en/master/guide/export.html) | Politica esportabile, postprocessing continuo. | ONNX non dimostra compilazione ACUITY. |
| [Gymnasium custom Env](https://gymnasium.farama.org/introduction/create_custom_env/) e [time limits](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/) | Contratto reset/step, termination/truncation. | Dinamica e reward da progettare/validare. |
| [NEAT overview](https://neat-python.readthedocs.io/en/latest/neat_overview.html) e [config](https://neat-python.readthedocs.io/en/latest/config_file.html) | Genomi, specie e opzioni feedforward. | Documentazione e tag da allineare. |
| [NEAT activations](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/neat/activations.py), [export](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/neat/export/__init__.py), [checkpoint](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/neat/checkpoint.py) | Semantica numerica, JSON e contenuti del salvataggio. | Sorgenti master, nessun port eseguito. |
| [NEAT metadata](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/pyproject.toml), [SB3 metadata](https://raw.githubusercontent.com/DLR-RM/stable-baselines3/master/setup.py) e rispettive [licenze NEAT](https://raw.githubusercontent.com/CodeReclaimers/neat-python/master/LICENSE) / [SB3](https://raw.githubusercontent.com/DLR-RM/stable-baselines3/master/LICENSE) | Dipendenze/Python e condizioni distribuzione. | Verifica del pacchetto scelto e delle dipendenze ancora necessaria. |
| [Vivante SDK](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-sdk) e [ACUITY](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-usage) | Driver, compilazione e target A733. | Piattaforma Radxa dello stesso SoC; compatibilità Orange Pi da qualificare. |
