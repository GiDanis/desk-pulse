# Gioco — piano di integrazione dei riferimenti pubblici e correzione delle impostazioni

> **Decisione successiva del 25 ottobre:** fase funzionale Auto chiusa, manutenzione rc.3 installata e verificata; ricerca P0–P9 parzialmente completata e rinviata per passare al nuovo modulo. I gate scientifici non vengono dichiarati superati e le nuove reti restano escluse dalla produzione. [Chiusura corrente e ricevuta](v094-game-functional-closure-report.md). I resoconti sotto mantengono gli esiti e le date originali.

**23 ottobre 2026 · Europe/Rome · piano autorizzato; esecuzione in corso.**

Stato corrente e prove nel [report di esecuzione](v094-game-reference-implementation-report.md). Le osservazioni seguenti descrivono il momento della pianificazione; non sostituiscono la ricevuta di consegna.

Richiesta: adottare un riferimento riproducibile per migliorare guida e sorpassi; correggere il menu nel quale si scende con 8, non si riesce a risalire con 2 e, premendo Start in fondo, la Dashboard può bloccarsi ed entrare in recovery.

**Ordine operativo: stabilità del menu/Start → riferimento originale riprodotto → ambiente compatibile → base neurale competente → apprendimento misurato → integrazione e consegna.** Il fix delle impostazioni ha una consegna autonoma: non deve attendere una nuova campagna di apprendimento.

[Evidenze della pianificazione](evidence/game-reference-integration-plan-2026-10-23/README.md) · [attuazione A0–A7 e risultati negativi](v09-overtaking-attack-report.md) · [MasterPlan](release-masterplan.md).

## 1. Stato verificato e confini

### Scheda corrente

- Lettura del 23 ottobre, 00:48 CEST: **core 0.9.4-rc.1**, servizio attivo/running, `NRestarts=1`. È successiva alla rc.2 del Gioco: non attribuire il nuovo incidente alla sola revisione precedente.
- Apple Calm **1.6.4**, digest `d67dccb9bf336273afa9f9cd1b2c23bc9fbe2947f04274f9dfa97a2ac56e0e28`, risulta nuovamente attivo, nessuna attivazione pendente. La cronologia conserva recovery, verifica isolata e successiva riattivazione.
- **22 ottobre 19:41:27 CEST:** il supervisore registra «GUI heartbeat assente», interrompe la GUI, seleziona Base e restituisce 75/TEMPFAIL; systemd riavvia. Il report della GUI contiene `exitCode=-9` dopo l'intervento del watchdog e ultimo contesto `home.now`, renderer `studio.applecalm.homenow`, non una traccia completa di Start. Non dimostra un SIGSEGV né prova il collegamento causale fra quel particolare episodio e il menu.
- Nel campione kernel 19:30–19:45 non sono emerse righe corrispondenti ai filtri OOM/segfault/GPU usati. È assenza nel campione, non esclusione generale di quei guasti. Il picco di memoria riportato da systemd per quell'esecuzione è 453,4 MB, non una diagnosi di esaurimento RAM.
- SHA256 di `Main.qml`, `game.py`, `game_settings.py`, `game_worker.py`, `game_direct.py`, `game_direct_trainer.py` e `GameSettingsVisual.qml` coerenti tra scheda e sorgente locale esaminato.

### Riproduzione di pianificazione

Il controller Python su dati nuovi risale correttamente nelle cinque modalità. Una prova **Main/QML reale su PC**, Apple Calm 1.6.4, 960×640, completa due discese/risalite per modalità mediante `activateKey(8/2)` senza warning QML. Non avvia worker e non usa salvataggi personali o input HID fisico. **Il difetto segnalato resta aperto.** I precedenti walkthrough usavano anche helper diretti per scegliere righe/valori: non coprivano tutta la sequenza fisica segnalata.

In questa fase: letture della scheda, consultazione di codice/fonti e prove PC isolate. Nessuna modifica runtime, installazione di dipendenze, input sul display della scheda, arresto del servizio, riattivazione del tema o allenamento eseguiti.

## 2. Priorità immediata: menu e Start

### 2.1 Diagnosi da completare prima della correzione

Acquisire la sequenza minima con: modalità, pilota, obiettivo, checkpoint/hash/dimensione, eventuale worker già in pausa, sezione/bozza/modifica attive, riga scelta prima/dopo il tasto, renderer effettivo, versione Qt e tempi monotoni. Separare i tre ingressi: HID dedicato → `KeyDecoder`, tastiera Qt → `Keys`, azione pubblica → `settingsKey`.

La registrazione deve essere limitata e priva di pesi, replay o credenziali: posizione del tasto, esito del decoder, selectedId/index, revisione delle righe, stato worker e durata del comando sono sufficienti. Non richiedere all'utente di riprodurre ripetutamente il crash sulla produzione: provare prima su copie private del salvataggio.

Ipotesi da discriminare, non cause già accertate:

1. Il tasto 2 non arriva o viene consumato da un percorso diverso; verificare modificatori Ctrl e press/release del dispositivo, senza intercettare altre tastiere.
2. La selezione cambia nel controller ma il renderer rimane sulla pagina precedente; controllare atomicità di righe/selectedId/index e clamp alla pagina finale/Start.
3. Stato di modifica rimasto attivo. Oggi 2/8 vengono ignorati durante `edit`: verificare se l'interfaccia comunica lo stato e se coincide con la sequenza osservata.
4. Start provoca lavoro sincrono, attesa IPC, copie o I/O nel thread GUI. `applySetup`, validazione archivio, `_refresh`, `stop` e creazione del processo vanno cronometrati separatamente. `stop()` contiene attese sincrone fino a 10 s in alcune condizioni: è un rischio da misurare, non la causa dimostrata dell'incidente.
5. Riavvio di un worker sospeso/in chiusura o doppio Start; ricostruire ticket/epoch e ordine degli ACK senza duplicare processi.
6. In caso di stallo riprodotto: stack Python/Qt e campione CPU per thread/I/O, contemporanei all'ultima riga e allo stato worker. Il watchdog resta il recupero esterno.

### 2.2 Comportamento da implementare

- **2/8 devono permettere sempre di tornare sui campi precedenti/successivi.** Proposta UX: se un valore è in modifica, 2/8 lo validano nella bozza e si spostano; una validazione fallita resta sul campo con motivo leggibile. Nessuna scrittura dell'archivio solo per scorrere.
- 4/6 modificano il valore quando si sta editando; fuori dall'editing passano tra Sessione/Allenamento/Gestione dove previsto. 5 apre/conferma il campo oppure avvia solo se è selezionato Start. 7 annulla il valore o risale al livello precedente.
- Focus conservato per identità della riga. Se cambiano modalità/righe, normalizzare sulla nuova lista prima di calcolare pagina e movimento; nessun salto al footer per un indice vecchio.
- Un'unica istantanea coerente per righe, selezione, enabled e stato bozza. Il renderer segue quella selezione; non mantiene un secondo indice indipendente.
- Start espone subito «Avvio…» e impedisce richieste duplicate. Letture pesanti, preparazione modelli e chiusura/salvataggio worker devono lasciare attivo l'event loop. Ticket di avvio, annullamento e timeout espliciti; errore del worker mostrato nel Gioco con ultimo checkpoint intatto.
- Preservare messaggi reali di Qualifica mancante, numero di partecipanti e archivio indisponibile. Nessun crash come modalità di rifiuto.
- Conservare grafica Apple Calm, descrizioni grigie e schermata 3,5" orizzontale a 960×640; nessuna nuova legenda fissa in basso.
- **Non allungare o disattivare il watchdog per mascherare il blocco.** La recovery deve continuare a funzionare e conservare la diagnosi.

### 2.3 Criteri del fix

- Riprodurre la sequenza segnalata, oppure localizzare e motivare il limite della riproduzione; il solo probe PC già passato non è il fix.
- Discese fino a Start, risalite fino alla prima riga, ritorni da editing/picker/schieramento: cicli ripetuti nei cinque modi. Includere righe disabilitate, pagina finale incompleta, cambi di modalità e Start con bozza modificata.
- Start tramite **tasto 5 dopo navigazione**, sia da fermo sia dopo Pausa/Salvato, su copie dei quattro piloti reali; anche doppia pressione, worker lento e fallimento di avvio.
- Confrontare Base, Functional e Apple 1.6.4; scala testo 1/1,1 sui percorsi coinvolti. Verifica EGLFS/HID sul pannello dopo le prove PC.
- Obiettivi iniziali software: risposta visibile ai tasti entro 100 ms al p95 e 250 ms massimo nei cicli a caldo; pubblicare eventuali scarti a freddo, non nasconderli nella media. Start può richiedere più tempo nel worker, mantenendo reattiva la GUI; nessun ritardo aggiuntivo >1 s nella pubblicazione dell’heartbeat attribuibile al comando.
- Sessione nativa mista di almeno 30 minuti comprendente navigazione, avvio/pausa/riavvio e ritorno alla Dashboard: nessun nuovo stallo/recovery, warning QML o processo orfano nel campione. Non è certificazione di assenza universale di crash.
- Tabelle, artefatti, qualifiche e preferenze originali conservati; backup/rollback prima della consegna autorizzata. Recovery/readmission del tema solo dopo qualificazione della revisione corretta, senza cancellare l'incidente.

## 3. Riferimenti pubblici e cosa riusare

### End2Race — riferimento principale

[Repository](https://github.com/michigan-traffic-lab/End2Race) · [revisione fissata](https://github.com/michigan-traffic-lab/End2Race/commit/769bedb571125b2392b909fa1e0eb0a0c3649322) · [paper](https://arxiv.org/abs/2509.16894).

Revisione letta: **769bedb571125b2392b909fa1e0eb0a0c3649322**, 27 settembre 2026. Contiene esperto lattice/Frenet, raccolta esempi, behavioral cloning, GRU, affinamento PPO e valutazioni separate solo/avversario. Licenza principale **Apache-2.0**, verificata nel file della revisione; dipendenze, mappe, dataset e checkpoint richiedono una propria verifica prima della redistribuzione. Non assumere la vecchia etichetta MIT mostrata da alcuni risultati di ricerca.

Il codice corrente differisce dal paper originale: **180 ingressi LiDAR**, embedding velocità 30, **GRU 420**, testa MLP 128. Conteggio analitico 850.556 parametri, circa 3,25 MiB per soli pesi FP32; non è una misura di RAM totale, costo CPU o idoneità della NPU. Configurazione originale: fisica 120 Hz, controllo 40 Hz, planner esperto 10 Hz; veicolo circa 0,58×0,31 m e 3,362 kg. Uscita sterzo + **velocità richiesta**, diversa dai nostri sterzo + pedale.

Prima riprodurre il progetto originale su PC con configurazione/checkpoint esatti. Riusare poi parti selezionate: generazione di scenari, struttura temporale del dataset, rete con memoria, raccolta/verifica e affinamento. Ogni file copiato porta provenienza, commit, licenza/notice e modifiche documentate. La sola somiglianza del nome dell'algoritmo non rende riutilizzabili i pesi.

Il paper segnala anche rientri troppo precoci dopo il sorpasso dovuti all'esperto: includere copertura post-passaggio e rivali dietro, invece di importare quel limite nel nuovo docente. Risultati pubblicati su modellini e prove brevi non sono una promessa sul nostro circuito o sulla scheda.

### Stable-Baselines3 — confronto dell'apprendimento

[Codice](https://github.com/DLR-RM/stable-baselines3) · [ambienti personalizzati](https://stable-baselines3.readthedocs.io/en/master/guide/custom_env.html) · [valutazione](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html).

Usare implementazioni di riferimento PPO/SAC/TD3 sul **nostro ambiente**, con versioni stabili fissate in un ambiente di laboratorio separato. Lo scopo è verificare la catena ambiente→dati→aggiornamento con un secondo learner. Un confronto con architetture/distribuzioni/iperparametri diversi misura il pacchetto, non dimostra da solo un bug matematico nel learner corrente.

[RecurrentPPO di sb3-contrib](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_recurrent.html) usa **LSTM**: non carica direttamente la GRU End2Race. SAC/TD3 standard non diventano ricorrenti solo aggiungendo hidden state al file. Per essi confrontare prima rete densa con storia di osservazioni; un learner ricorrente dedicato richiederebbe un lotto esplicito.

### TD3-Overtake — protocollo di sorpasso

[Studio degli autori](https://arxiv.org/html/2510.26040v1) · [repository indicato](https://github.com/UoA-CARES/autonomous_f1tenth).

Riprendere progressione degli scenari, avversari congelati e confronto contro guida solo. Gli autori hanno rimosso un bonus specifico di sorpasso dopo abusi osservati: confrontarlo come ipotesi, non come nuova ricompensa automaticamente corretta. Il repository usa ROS/Gazebo; non aggiungerli al kiosk per importare il metodo. Licenza dei file esatti ancora da verificare prima di una copia letterale.

## 4. Contratti da mantenere nell'adattamento

1. **La rete guida:** sterzo normalizzato e pedale con segno, gas/freno interamente neurali. Nessun inseguimento automatico di corsia o velocità nelle azioni del pilota, anche durante Gara. Il Maestro è un docente offline e un riferimento esplicitamente nominato.
2. Metri, secondi, kg e forze della nostra fisica. Niente riscalamento dei soli disegni o riuso di soglie per modellini senza conversione e prova.
3. Fisica attuale a 60 Hz e AI inizialmente 10 Hz; grafica indipendente. Le frequenze del riferimento restano nel laboratorio originale, non vengono trasferite implicitamente. Un cambio di cadenza richiede nuova versione, training e prova di costo.
4. Osservazioni disponibili al pilota: dinamica, strada, aderenza dichiarata, rivali e storia causale. Nessuna traiettoria futura dell'avversario, azione del docente o linea ideale del Maestro come scorciatoia nascosta.
5. Memoria ricorrente separata per pilota e automobile; reset all'inizio di un episodio reale, non a ogni frame, finestra continua o giro. Pausa/salvataggio/ripresa comprendono hidden state, normalizzatori e RNG. Gara tra reti congelate, una vettura per identità; tutte le vetture restano rappresentate fino al risultato.
6. Qualifica e record legati all'hash esatto della policy e al contesto fisico. Modello candidato, migliore tattico, migliore solo e versione gara rimangono distinti.
7. Lifecycle esplicito: vista aperta + Start, Pausa con salvataggio durevole, uscita e chiusura controllate. Nessun nuovo training al boot o a vista chiusa.

## 5. Sequenza dei lotti

| Lotto | Lavoro | Dipendenze | Risultato richiesto prima di passare oltre |
| --- | --- | --- | --- |
| P0 · Menu e avvio | Riproduzione, input/focus, bozza e Start asincrono, errore locale e prova recovery. | Evidenze attuali. | Fix qualificato e consegnabile autonomamente; criteri §2.3. |
| P1 · Diagnosi dei piloti | Confrontare candidato, migliore tattico e gara; primo errore, scelte dei rivali, memoria, gradiente e vincoli. | Dati privati congelati. | Una causa riprodotta per gli interventi successivi; nessuna deduzione «nessuno impara» dal solo campione gara. |
| P2 · Riferimento originale | Ambiente PC separato, commit/config/checkpoint/hash/license fissati, demo originale e misure. | Fonti §3. | Comandi/reti originali riprodotti o incompatibilità precisa documentata. Nessuna installazione nella GUI. |
| P3 · Interfaccia Gymnasium | Adattatore della nostra fisica, osservazioni/azioni/reward/terminali, checker e traiettorie abbinate. | Contratti §4; P1. | Stesse azioni → stessa fisica/eventi del runtime; nessuna modifica surrettizia al compito. |
| P4 · Docente e dataset | Manovre complete, più giri, recuperi e attacchi abortiti; raccolta sequenziale e correzioni negli stati visitati dalla rete. | P1/P3, confronto esperto P2. | Docente capace sulle prove estese; etichette causali coerenti e dataset senza contaminazione tra banche. |
| P5 · Base neurale | Densa attuale, storia di osservazioni e GRU compatta; eventuale riferimento GRU 420 sul PC. | P4. | Rete da sola capace di sorpassare e continuare; scelta mediante sviluppo, finale separato. |
| P6 · Affinamento RL | Controlli SB3 PPO/SAC/TD3 e ramo End2Race adattato; incentivi/ancoraggi/routing uno alla volta. | P3/P5. | Miglioramento oltre la preparazione misurato, con sicurezza e passo mantenuti. |
| P7 · Qualifica estesa | Cinque preparazioni/semi, casi nuovi, 1/2/3 bot, griglie 2/5 e più giri. | Ricetta congelata P6. | Gate §8; modello da consegnare scelto senza consultare il finale. |
| P8 · Dashboard | Backend/versioni/checkpoint, profili fissi, fasi comprensibili, dossier, nuove reti nelle modalità esistenti. | P0; prototipo backend P5; attivazione dopo P7. | Funzionalità verificata su copie, stessi comandi e tema, nessun peso incompatibile caricato. |
| P9 · ARM e consegna | Inferenza/learning reali, carico e lifecycle; backup, manifest, migrazione, rollback e ricevuta. | P7/P8. | Nuova ricetta attivabile soltanto dopo gate scientifici e tecnici; stato ufficiale aggiornato. |

P1 e P2 possono avanzare come attività indipendenti mentre si qualifica P0. La nuova rete non è un prerequisito per risolvere il crash. «Codice implementato», «modello qualificato», «installato» e «beneficio verificato» devono essere quattro stati espliciti.

## 6. Dettaglio di ambiente, docente e memoria

### P1 — separare apprendimento e selezione

L'ultima banca lunga A0–A7 ha provato la **policy gara selezionata**, spesso conservata dal campione precedente. Ripetere su copie il confronto a tre ruoli, stessi semi e azioni deterministiche: candidato, migliore tattico, gara. Per ogni errore registrare i secondi prima/dopo il passaggio, distacco, corsia, sterzo/pedale, aderenza, contatto/uscita e scelta dei tre rivali osservati.

Verificare: cambio di slot dei rivali ordinati per distanza; saturazione del selettore A/B; aggiornamenti effettivi di ciascun esperto; entità del vincolo sullo sterzo; allineamento del gradiente e valutazione del critic. Confronti di azioni controllate nello stesso stato: attacco pulito, seguire, rinuncia necessaria, taglio e collisione. Non interpretare un maggiore ritorno in scenari diversi come prova di un premio corretto.

### P3 — un adattatore, stessa simulazione

Interfaccia `reset(seed, options)` e `step(action)` con observation, reward, terminated, truncated e info. Un passo AI contiene inizialmente sei tick fisici; reward integrato sul tempo effettivo. Dichiarare unità di discount/GAE, fine obiettivo, pausa, troncamento esterno e bootstrap. [Semantica ufficiale dei limiti](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/).

Confrontare sequenze di azioni congelate tra adattatore e World/worker: pose, velocità, aderenza, collisioni, progressi, timing e premi devono coincidere entro la tolleranza numerica fissata. Conservare l'ultima osservazione prima dell'eventuale reset automatico. Renderer e UI esclusi dal training headless.

Baseline SB3: fissare architettura, inizializzazione, distribuzione delle azioni, normalizzazione, budget e iperparametri. Il critic del progetto dispone di contesto del compito: se il riferimento usa osservazioni diverse, dichiarare la differenza o predisporre un controllo comune. Non presentare come equivalente un attore che riceve informazioni privilegiate.

### P4 — il docente deve saper continuare dopo il passaggio

Banca: completamento da affiancato; attacco da dietro su entrambi i lati; interno/esterno in curva; ripartenza dopo il passaggio; secondo/terzo rivale; difesa regolare; varco chiuso con rinuncia e nuovo tentativo; recupero. Includere velocità iniziali, gap, posizioni e aderenze dichiarate, non solo partenze dal medesimo rettilineo.

Validare l'esperto su 3–5 giri e su avversari dietro prima di esportare etichette. Memoria del pianificatore separata da quella del learner: interrogare il docente non deve cambiare la simulazione o i comandi precedenti attribuiti alla rete. Le labels devono usare lo stesso istante/cadenza degli ingressi.

Conservare intere sequenze e confini di episodio. Separare train/sviluppo/finale per scenario, seme e contesto: frame adiacenti della stessa traiettoria non devono finire in banche diverse. Aggiungere stati di errore del learner con correzioni del docente; tracce fallite non diventano automaticamente buone azioni supervisionate. Controllare il divario fra errore sui dati e guida autonoma prolungata.

Il vantaggio di passo dell'ego è didattico e dichiarato all'inizio del curriculum; ridurlo verso condizioni realistiche. In Gara nessun aumento occulto della potenza/aderenza dell'ego. Distinguere occasioni fisicamente praticabili da passaggi impossibili: non punire una rinuncia corretta a un varco chiuso.

### P5 — memoria scelta mediante confronto

Primo controllo: rete densa corrente. Secondo: storia causale a lunghezza fissata. Terzo: GRU compatta, dimensioni candidate dichiarate prima del confronto. La GRU originale 420 rimane un riferimento PC, non un obbligo per la scheda.

Confrontare rappresentazione dei rivali per distanza con un'alternativa che mantenga continuità o invariabilità appropriata, senza trasferire identità privilegiate del futuro. Non aggiungere contemporaneamente nuovi sensori, nuova ricompensa e nuova architettura al primo confronto.

La base deve conservare passo solo, stabilità e controllo diretto; un basso MSE sulle etichette non la qualifica. Conservare errori e ripetizioni, senza scegliere il seme più favorevole.

## 7. Metodi, memoria personale e UI

La rosa iniziale resta **Maestro, Crono, Memoria, Linea, Tattico**. P2 può produrre agenti di laboratorio senza aggiungerli alla rosa della Dashboard.

| Pilota | Percorso previsto | Limite da dichiarare |
| --- | --- | --- |
| Maestro | Docente fisico e riferimento congelato verificato. | Non è una rete che apprende in Gara. |
| Crono / PPO | Confronto PPO di riferimento; candidato ricorrente da imitazione + PPO se P5 lo giustifica. | GRU End2Race e LSTM sb3-contrib sono architetture e checkpoint differenti. |
| Memoria / SAC | SAC di riferimento con base preparata e replay controllato; storia di osservazioni se qualificata. | Il nome Memoria non dimostra memoria ricorrente; il replay non sostituisce un hidden state. |
| Linea / TD3 | Primo pilota laboratorio per confrontare learner corrente, SB3 e base adattata. | Nessuna superiorità di TD3 assunta prima della prova. |
| Tattico / TD3 | Stessa famiglia TD3 con curriculum di attacco/difesa e avversari congelati. | È una specializzazione, non un quarto algoritmo distinto. |

L'origine della preparazione, versione sensori/azioni, architettura e ricetta diventano parte dell'identità del modello. Dati/optimizer di dimensioni diverse non sono ricaricati come se fossero compatibili. Percorsi vecchi archiviati e ripristinabili; identità del pilota e totali storici conservati. Nessun reset generalizzato necessario per preparare il nuovo ramo di prova.

Trasferimento tra piste: base compatibile riusabile e affinamento personale per pista/auto/fondo; qualifica e record restano locali all'esatto contesto. Prima qualifica Ovale 1/auto standard/asciutto; supporto alle registrazioni di circuiti/auto rimane predisposto, ma Varano/Mallory/bagnato non ricevono una qualifica per deduzione.

Menu: mantiene parametri tecnici fissi e descrizioni leggibili. Nel dossier distinguere Preparazione, Apprendimento, Verifica, Migliore solo, Migliore traffico e Gara. Esibire azioni/episodi/aggiornamenti reali, attacchi/passaggi e tempi; nessuna generazione fittizia per PPO/SAC/TD3. Preparazione offline del docente non viene contata come miglioramento RL personale.

## 8. Esperimenti e criteri di promozione

Prima screening su un pilota, una modifica per confronto e piccoli gruppi di sviluppo completi. Congelare budget, scenari e regole prima di valutare il finale. La vecchia banca A0–A7 diventa diagnostica/sviluppo: nuova banca finale non riutilizzata per tarare i modelli.

- **Almeno cinque semi completi** per la preparazione e per il metodo che si vuole promuovere. Cinque continuazioni della stessa base non sono cinque preparazioni indipendenti.
- Budget iniziale di sviluppo confrontabile al precedente: 196.608 passi fisici raccolti per continuazione. Eventuale fase più lunga decisa sullo sviluppo e dichiarata prima del finale, senza cambiare budget dopo averne visto gli esiti.
- Contare separatamente esempi/docente, passi fisici, decisioni, gradienti, valutazioni, secondi simulati, tempo reale e risorse; stesse condizioni iniziali abbinate dove il confronto lo permette. Checkpoint atomici su SSD, spazio verificato e ripresa esatta; nessuna stima di accelerazione dai tempi incompleti.
- Banca facile: almeno 90% di passaggi puliti per ciascun seme. Curva/traffico: almeno 75% per ciascun seme e nessuna famiglia critica a zero.
- Attacco tempestivo nelle occasioni facili praticabili: almeno 80% entro 3 s; attesa in coda/affiancato ridotta del 50% sui casi abbinati applicabili. Finestre concluse senza incidenti e senza passaggio non sono automaticamente sorpassi riusciti.
- Niente regressioni di sicurezza per caso/peggior seme; contatti ego e globali distinti, ritiri e uscite non nascosti nella media. Eventi dei rivali congelati riportati separatamente; un solo bot non sicuro non certifica un errore dell'ego.
- Passo solo mediano entro +1% del riferimento comune, compreso il peggior seme. Il miglioramento RL va confrontato con la **propria base dopo imitazione**: validità e tempo al passaggio migliorati in almeno 4/5 semi secondo un margine fissato sullo sviluppo, senza attribuire al RL il vantaggio del docente.
- Prove lunghe di 3–5 giri dopo il primo sorpasso, uno/due/tre bot; griglie a due e cinque auto, tre giri, arrivi validi e tutte le auto rappresentate. Avversari/posizioni nuovi rispetto alla raccolta e casi in cui il sorpasso va rinviato.
- Qualifica finale sia del candidato da consegnare sia della policy effettivamente selezionata per Gara, con hash dichiarati. Distinguere miglioramento non selezionato da assenza di miglioramento; nessuna sostituzione guardando quale policy vince il test finale.

La riproduzione della demo pubblica è un controllo di riferimento; la soglia finale della nostra rete riguarda la nostra fisica. Se un gate fallisce, conservare l'esito e localizzare il difetto: non attivare comunque la ricetta né dichiarare risolto l'apprendimento perché il codice è stato installato.

## 9. CPU, GPU, NPU e consegna

La Dashboard mantiene il runtime Qt corrente. Laboratorio End2Race e laboratorio SB3 sono ambienti separati, con lock di dipendenze/hash e versioni compatibili. Il runtime PC esaminato contiene NumPy 2.2.6/PySide6 6.8.2.1; non contiene Torch/Gymnasium/SB3. Lo script upstream installa Torch 2.7.0 CUDA 12.8 e usa il vecchio Gym: non eseguirlo dentro l'ambiente della Dashboard.

Prima misurare il riferimento su PC. Per ARM qualificare disponibilità/compatibilità del backend, tempo di importazione, inferenza per una e cinque reti, memoria/stato, costo degli aggiornamenti e salvataggi. Il modello carica nel processo worker, senza import pesanti nel thread GUI. Se serve un interprete/backend separato, mantenere esplicito il protocollo IPC e gli ACK; non cambiare silenziosamente l'eseguibile globale dei processi metadata.

CPU: fisica/controllo e training corrente. GPU: Qt Quick; accelerazione di training PC solo se disponibile e misurata. NPU: valutazione facoltativa successiva per una policy congelata compatibile; supporto GRU, conversione, quantizzazione e gestione dei pesi aggiornabili da dimostrare. Presenza dell'acceleratore e risultati su Jetson non certificano vantaggi sulla Orange Pi.

RAM disponibile utilizzabile per buffer/cache quando utile, senza quote arbitrarie; persistenza su disco e crescita limitata per lifecycle restano necessarie. Non spostare l'intero replay nella GUI. Misurare p50/p95/p99 di inferenza e lavoro per decisione, throughput fisico e frame pacing durante learning/gara; una media FPS non certifica fluidità. Rendering di riferimento a 30 Hz da mantenere/qualificare con carico dichiarato, senza promettere 60 FPS ottici.

Consegne distinte: **prima fix menu**, poi nuovo modello soltanto dopo P7. Per ciascuna: manifest esatto, test PC/ARM pertinenti, EGLFS nei tre temi, backup/rollback, preferenze e dati conservati, salute con PID GUI vivo e ricevuta. Nessun cambio dei prossimi rilasci Acquario → Compagno → Memoria/AI dovuto alla sola creazione di questo piano.

## 10. Stato alla fine della pianificazione — storico

Piano, fonti fissate e osservazioni salvati. Menu/Start: incidente di stallo confermato, sequenza specifica non ancora riprodotta end-to-end; nessun fix dichiarato. Apprendimento: riferimento pubblico scelto per il laboratorio, nessuna demo esterna eseguita, nessuna nuova rete qualificata o attivata. Prossimo lavoro autorizzabile: **P0, P1 e P2**, con consegna indipendente della correzione del menu e progressione secondo i gate.


## 11. Esecuzione autorizzata — stato al 25 ottobre

[Report corrente e limiti](v094-game-reference-implementation-report.md). P0 funzionale installato nella core **0.9.4-rc.2**, 654 file; tre temi EGLFS e 30 minuti misti Apple, originali conservati. Picchi software oltre il target di latenza e HID/ottica ancora aperti. P1–P4 realizzati nel perimetro dichiarato. P5: cinque preparazioni indipendenti e confronti estesi, con una base a 9/9 traffico ma ricetta comune non ancora qualificata. P6: confronti PPO/SAC/TD3 completi non superano congiuntamente miglioramento/sicurezza; opzione di affinamento dei moduli degli attuatori implementata e sottoposta a sviluppo separato.

P8/P9 tecnici del prototipo verificati su PC e ARM, **18 sessioni Main/QML per piattaforma**, tre temi 960×640, aggiornamenti reali, viste, pausa/salvataggio/chiusura senza warning QML. Ripetizione finale su sorgenti corretti: 30 test nucleo + 10 controller PC, sei controlli ARM e 18 ulteriori sessioni native con rete estesa; gare complete 2/5 a tre giri, tutte arrivate e visibili. Prove con preparazioni condivise esplicitamente private, distinte da cinque preparazioni scientifiche indipendenti. Servizio originale ripristinato, dati e preferenze conservati; nessuna nuova rete installata. Queste prove non sostituiscono P7: finale mai consultato, cinque preparazioni della stessa ricetta RL e gare 2/5 con modelli qualificati ancora da completare. Non chiamare chiusa l'intera release.

### 11.1 Seguito del 25 ottobre — base corretta e primo guadagno sicuro

[Studio e attuazione](game-learning-retention-study-2026-10-25.md). La quinta preparazione è stata corretta con suoi nuovi dati di allenamento e conservazione dei controlli: ora 5/5 selezioni superano il prerequisito quantitativo comune di sviluppo. Non sono cinque piloti della rosa né la qualifica di una ricetta comune; i casi problematici delle altre preparazioni rimangono nei risultati.

Replay esperto protetto, contesto del learner, candidati intermedi e diagnostica delle stime implementati. Otto continuazioni da 32.768 decisioni concluse. A 24.576, SAC migliora passo e passaggi con sicurezza mantenuta nella banca; non raggiunge la riduzione d'attesa del 50% e non è promosso. Il candidato finale della stessa continuazione regredisce: conservati entrambi gli esiti. Nessuna soglia ridotta.

Eliminati calcoli duplicati dell'encoder, con parità esatta e microbenchmark PC/ARM; 25 test PC e CLI di cattura/ripresa passati. Nessuna nuova verifica Main/QML attribuita a questi sorgenti. Produzione invariata, servizio rimasto attivo, nessun reset o nuovo peso installato. P6/P7, qualifica tecnica dei pesi da consegnare e relativa consegna rimangono necessari prima della chiusura.

## Chiusura della fase funzionale — decisione del 25 ottobre

L'utente dà priorità alla conclusione semplice del modulo Auto e al passaggio al nuovo modulo. Si conserva il prodotto esistente e si consegna la sola manutenzione finale delle gare. Il piano scientifico P0–P9 non è completato: P5/P6/P7 e la consegna dei nuovi pesi vengono rinviati, con banca finale conservata e nessuna soglia ridotta. Non sono prerequisiti per il modulo successivo. [Report della consegna conclusiva](v094-game-functional-closure-report.md). Un'eventuale ripresa della ricerca richiede nuova priorità esplicita e i gate originali.
