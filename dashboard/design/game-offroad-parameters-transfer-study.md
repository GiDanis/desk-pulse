# Gioco · fuori pista, parametri effettivi e trasferimento fra circuiti

**13 ottobre 2026 · analisi verificata sul codice rc.11, profili letti sulla scheda e fixture isolate.** [Risultati riproducibili](evidence/v09-offroad-parameters-transfer-2026-10-13/probe.json) · [programma della verifica](evidence/v09-offroad-parameters-transfer-2026-10-13/probe.py) · [profili correnti della scheda](evidence/v09-offroad-parameters-transfer-2026-10-13/board-profiles.json).

**Decisione aggiunta dell’utente:** ogni pilota deve conservare una memoria di guida propria, riutilizzata automaticamente su nuovi circuiti e vetture; l’esperienza specifica si affina sul nuovo contesto. Progetto dettagliato nella sezione 5.1; non ancora implementato.

Le prove controllano comportamento e collegamento dei parametri. Non sono una ricerca esaustiva degli iperparametri né una certificazione della convergenza. La rc.11 corregge la visualizzazione della popolazione; gli interventi di questo studio sono i prossimi lotti, non già installati.

## 1. Fuori pista: la dinamica cambia davvero

Nel percorso Accademia/fisica **f2-1**, la vettura ha aderenza nominale **0,95 sull’asfalto asciutto e 0,45 nella zona esterna**, coefficiente di rotolamento **0,015 → 0,045**. Il coefficiente effettivo tiene conto anche di condizione e gomme. Il limite di attrito viene condiviso fra forza longitudinale e laterale su asse anteriore/posteriore: meno accelerazione, frenata e risposta in curva, maggiore decelerazione per resistenza. La rilevazione riguarda il corpo vettura campionato, non soltanto il centro. Il regime esterno entra nel calcolo delle forze dal sottopasso successivo alla rilevazione.

Fixture a 12 m/s, rettilineo, stesso comando e 0,5 s:

| Comando | Asfalto, velocità finale | Zona esterna, velocità finale |
| --- | ---: | ---: |
| Accelerazione massima | 14,216 m/s | 12,961 m/s |
| Frenata massima | 7,916 m/s | 9,553 m/s |

Con sterzo 0,25 per 0,2 s la velocità di imbardata è 0,316 contro 0,258 rad/s. Sono fixture deterministiche in regime esterno predisposto, non dati sperimentali di pneumatici reali. Il rientro ripristina i coefficienti dell’asfalto; oltre circa **6 m dal bordo**, o in caso di impatto grave, la vettura viene ritirata. Il percorso storico f1-2 conserva la propria fisica e può terminare subito al contatto col bordo: non estendere la descrizione f2 ai vecchi checkpoint.

**Limite:** il fuori pista è un profilo esterno uniforme. Non ci sono ancora pneumatici singoli su superfici diverse, cordoli, sabbia/ghiaia/erba distinti, ruote/ABS/TCS, usura o temperatura. Anche una porzione del corpo fuori dal bordo attiva il profilo ridotto per tutta l’auto. Parametri predisposti non equivalgono a nuovi terreni giocabili.

## 2. Premi e penalità attuali

| Evento | Obiettivo effettivo |
| --- | --- |
| Avanzamento in pista | Delta di progresso / 10; in Partenza normalizzato alla distanza 1/3/8/20 m. |
| Fuori pista | Premio di progresso azzerato; costo aggiuntivo **−0,2 per secondo simulato**. |
| Tempo impiegato | −0,02/s in Partenza/Controllo, −0,30/s nelle fasi di passo/traffico. Il tempo promuove velocità utile, non una velocità minima imposta. |
| Rientro | Cessa il costo fuori pista e riparte il normale premio di progresso. **Nessun bonus dedicato**. |
| Giri/tagli | Gate accreditati solo in sequenza e in pista. Il bonus di arrivo viene tolto se ci sono violazioni. |
| Esercizio breve valido | +2; sorpasso valido +0,5 una volta per rivale. |
| Stallo / ritiro | Stallo −0,5; ritiro −5, oltre ai termini degli eventuali contatti. |

Un’uscita incrementa `trackLimits`; il contatore resta dopo il rientro. La qualifica attuale richiede **zero violazioni e zero contatti**: rientrare consente di continuare a guidare, ma non rende di nuovo valido quello stesso tentativo di qualifica.

Per metodo: Evo/NEAT usano questo ritorno come fitness; PPO/PPO-Smooth aggiornano actor/critic dalle transizioni e dai ritorni; **Clone impara dalle azioni del maestro**, non dalla ricompensa tramite policy gradient. Per Clone i premi servono a risultati/selezione/qualifica, mentre il comportamento dipende dagli esempi di recupero forniti dal maestro. Pure Pursuit non impara.

### Punti da correggere prima di aggiungere un premio di rientro

1. **Separare la valutazione del giro pulito dall’esercizio di recupero.** Oggi un esercizio termina `skill_failed` anche dopo un rientro riuscito; manca una qualifica esplicita della capacità di recuperare. Aggiungere scenari fuori pista controllati e metriche tempo/distanza esterna, stabilità al rientro, contatti e mantenimento della guida normale.
2. **Controllare il progresso non valido.** Il progresso geometrico continua ad avanzare fuori pista, anche se non viene pagato. L’obiettivo di distanza può terminare con fallimento; manca un costo finale specifico di `skill_failed`. La validazione evita la promozione di un campione scorretto, ma la fitness di training può indirizzare male la selezione prima della validazione.
3. **Verificare cicli sfruttabili.** La fixture conferma che andare nella direzione opposta in pista sottrae progresso, fuori pista lo azzera. Questo crea un’asimmetria da provare con traiettorie chiuse/shortcut; non dimostra che un pilota reale abbia già imparato a sfruttarla. Distinguere progresso geometrico da progresso valido accreditabile e penalizzare arretramento/tagli in modo coerente.
4. **Niente pagamento ad ogni attraversamento del bordo.** Un bonus semplice di rientro potrebbe remunerare uscite deliberate ripetute. Preferire shaping basato su potenziale `γΦ(s′)−Φ(s)`, con stati/timer/versioni espliciti e condizioni terminali coerenti, oppure premio una tantum nel solo esercizio di recupero. Questo principio deriva da [Ng, Harada e Russell, ICML 1999](https://ai.stanford.edu/~ang/papers/shaping-icml99.pdf); la sua applicazione al nostro ambiente deve rispettare le ipotesi e non certifica automaticamente qualsiasi shaping.

Modifica di reward/task richiede una nuova versione, archivio/ripresa dichiarati e confronto con la baseline; preservare i percorsi correnti. Non aumentare indiscriminatamente le penalità: durante l’apprendimento iniziale potrebbe tornare conveniente restare fermi.

## 3. Parametri di rete e apprendimento

**Scheda corrente:** Evo è già Accademia, 68 ingressi, 32 candidati, 16 neuroni, mutazione 0,15, seme 1, 109.295 passi; Controllo, 11 generazioni completate. NEAT/PPO/Pursuit/Clone/PPO-Smooth mantengono ancora i percorsi storici a 32 ingressi letti nello snapshot; passano al nuovo percorso solo dopo Start, conservando il precedente. Nessun cambio silenzioso dei preset manuali.

| Metodo/parametro | Valore / collegamento | Valutazione e confronto utile |
| --- | --- | --- |
| Evo, rete | 68→16→2, **1.138 parametri** nel nuovo percorso | Piccola e sostenibile; capacità ottimale non dimostrata. Confrontare 16/32/64 a budget uguali. |
| Evo, popolazione | 32; quattro elite, un nuovo individuo indipendente | Base coerente, crescita 64/128 solo dopo qualità/costo. |
| Evo, mutazione | σ=0,15 su circa il 25% dei pesi; scala da 1 a 2 con stagnazione | È intensità, non probabilità di mutazione. Confrontare σ=0,05/0,10/0,15 e adattamento; i pesi iniziali dei nuovi ingressi sono piccoli, quindi serve misurare saturazione e diversità. |
| NEAT | 32; inizialmente zero nodi nascosti, connessioni dirette; nodi/connessioni evolvono | `hidden=16` nel profilo condiviso non definisce la topologia NEAT. Mutazione pesi/bias σ=0,15, tassi 0,8/0,7, aggiunta nodo 0,15/connessione 0,30, stagnazione 20. Esporre topologia/specie vere. |
| PPO/PPO-Smooth, rete | Actor 68→16→2, critic 68→16→1 | Dimensione moderata; training NumPy sulla CPU. Niente beneficio NPU dedotto dalla dimensione. |
| PPO, raccolta | 32 copie × 256 passi = **8.192 transizioni**; 4,27 s simulati per copia | Raccolta plausibile; 4 epoche × minibatch 64 = **512 minibatch** per aggiornamento. Confrontare 256/512/1.024 e minibatch 64/128/256. Le copie non sono processi CPU distinti nel backend ordinario. |
| PPO, passo / clipping | 0,0003; clip ratio 0,2; gradiente massimo 0,5; entropia 0,001 | Valori iniziali ragionevoli, non ottimo verificato. Manca telemetria KL/clip fraction/varianza spiegata e arresto adattivo KL. |
| PPO, futuro | Accademia γ=exp(−DT/40)=0,999583420… | Orizzonte delle ricompense **40 s**, diverso dal γ storico 0,995. |
| PPO, GAE | λ=0,95 fisso; traccia `−DT/log(γλ)` = **0,322 s** | Non è la stessa cosa dell’orizzonte reward; il critic fa bootstrap. Da confrontare λ corrente con orizzonti GAE 2/4 s, non da cambiare soltanto perché il numero è piccolo. |
| Clone | 16 neuroni, passo 0,0003, dataset massimo 2.048 esempi, batch 128 | Dataset e maestri determinano apprendimento/recupero. Confrontare copertura delle curve/fuori pista/traffico e conservazione di esempi rari. |
| Pure Pursuit | Geometrico, nessun training | Popolazione/neuroni/epoche del profilo condiviso non sono parametri di rete attiva. |

Le definizioni di rollout, minibatch, GAE, clipping e KL sono confrontate con la [documentazione PPO ufficiale di Stable Baselines3](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html). Il nostro motore è un’implementazione NumPy propria, non SB3 installato nel gioco. Parametri NEAT verificati sulla [documentazione NEAT-Python](https://neat-python.readthedocs.io/en/stable/config_file.html). I valori delle librerie sono riferimenti iniziali, non una prova dell’ottimo per le nostre piste.

### Riproducibilità e correttezza del confronto

- Seme/RNG separati per learner, episodi, preview e valutazione; stato RNG/optimizer/episodi salvato. Le verifiche di ripresa passano nello stesso runtime a pari passi, incluso il checkpoint reale Evo su copia. Questo non promette identità dei bit fra architetture/versioni o uguale numero di passi a pari tempo di parete.
- Candidato/campione valutati su scenari accoppiati e congelati; fine ambiente distinta fra `terminated` e `truncated`, con bootstrap PPO corretto. [Semantica Gymnasium](https://gymnasium.farama.org/main/introduction/migration_guide/).
- Durante il training evolutivo i 32 candidati hanno **32 semi e perturbazioni differenti**. Diversifica l’esperienza ma introduce rumore nella selezione. Provare stessi scenari per ciascun candidato della generazione, rotazione degli scenari fra generazioni e successiva fitness media su più scenari.
- I sei piloti manuali hanno semi distinti per identità. Per confrontare i metodi, eseguire copie di ciascun metodo sugli stessi cinque semi e budget, non confrontare una sola rosa. [Indicazioni ufficiali sulla valutazione RL](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html).
- Registrare codice/config hash, task/reward/fisica/sensori, scenario e policy hash, passi/episodi/secondi simulati/CPU attiva, topologia reale NEAT e hardware/runtime. Preview e FPS non misurano qualità dell’apprendimento.

## 4. Impostazioni: mostrare il funzionamento reale

La struttura esistente Sessione / Allenamento / Gestione e i profili non modificabili sono coerenti con l’identità dei piloti. Servono correzioni dei dati e una navigazione più esplicita, mantenendo titoli grandi, descrizioni in `textSecondary`, tre righe paginabili, focus stabile e nessuna legenda tastiera permanente.

**Problema verificato:** `episodeSeconds=60` è ancora mostrato come limite del tentativo, ma l’Accademia usa il TaskSpec: Partenza 15 s, inseguimento 40 s, sorpasso/affiancamento 50 s, difesa 40 s, gruppo 60 s; Controllo/Passo/Gare dipendono da lunghezza e giri. Il valore storico non modifica questi limiti. Il gruppo Riproducibilità mescola oggi seme e durata; tutti i gruppi hanno inoltre il titolo generico “Parametri avanzati”.

### Sistemazione proposta

1. **Sessione:** modalità, circuito, pilota/schieramento, giri e Start. Mostrare terreno/condizione/vettura effettivi.
2. **Allenamento:** metodo fisso, percorso Accademia, esercizio attuale e criteri di avanzamento; accesso “Profilo tecnico” in sola lettura.
3. **Profilo tecnico → Rete:** sensori/schema, forma e numero dei parametri; candidati Evo/NEAT oppure copie PPO/Clone; NEAT mostra nodi/connessioni/specie correnti.
4. **→ Apprendimento:** soltanto valori realmente usati; σ/scala/tassi evolutivi, PPO rollout totale/minibatch/epoche/orizzonti, Clone batch/dataset/maestro. Valori salvati distinti dai default/fissi; niente numeri inattivi presentati come regolazioni.
5. **→ Riproducibilità:** seme e versione del percorso, task/reward/fisica/schema, sorgente degli eventuali pesi. **Durata del compito** passa alle informazioni dell’esercizio, derivata dal protocollo, non al campo storico di 60 s.
6. **Gestione → Memoria del pilota:** riuso automatico della base personale; mostrare origine/versione e specializzazione del contesto. Importazione manuale da un circuito resta solo recupero avanzato dei percorsi storici, con sorgente compatibile esplicita. Oggi la sorgente è il primo altro circuito del catalogo: comportamento da sostituire. Reset distinti della specializzazione e dell’intero pilota.

Le informazioni attive provengono da DTO normalizzati, senza importare NumPy per aprire il menu o avviare training. Dossier conserva dettaglio scientifico e provenienza; menu resta leggibile a 960×640, scala 1/1,1 nei tre temi.

## 5. Un pilota può portare ciò che ha imparato su un’altra pista?

**Architettura installata rc.11, da evolvere secondo la nuova richiesta:** identità unica del pilota, percorso/pesi/checkpoint/qualifica separati per circuito. Cambiare pista non trasferisce automaticamente il cervello. I sensori di geometria locale possono permettere generalizzazione, ma abilità sull’ovale non prova guida/sorpassi a Varano.

Esiste “Trasferisci da altra pista”: accetta un modello denso salvato, stesso metodo/dimensione/schema, destinazione vuota. Copia pesi iniziali, conserva l’origine e richiede qualifica nuova. NEAT è escluso perché `kind=neat`; Pure Pursuit rigenera il riferimento della pista e non trasferisce apprendimento. Il trasferimento fra metodi non è previsto.

**Bug riprodotto nel percorso Accademia v2:** l’inizializzatore viene registrato ma ignorato. `activate_academy()` ritorna subito se il profilo è già v2 e `game_worker` non applica l’inizializzatore nel ramo AcademyTrainer. La fixture crea un donatore con tutti i pesi 0,123: trasferimento accettato, sorgente intatta, nessun checkpoint nuovo e pesi del learner destinatario casuali. Il test storico verifica la registrazione, non il consumo dopo Start. Quindi non si può dichiarare oggi il trasferimento Accademia funzionante per tutte le condizioni.

### Correzione e sviluppo

- **Prima:** consumo atomico dell’inizializzatore al primo Start anche per v2, fonte/hash nel checkpoint/dossier; rete inizializzata davvero dal donatore, critic/buffer/reward memories nuovi, contatori/qualifiche della destinazione nuovi. Origine e percorsi non sovrascritti. Test su worker effettivo e ripresa, oltre alla funzione di archivio.
- Trasferimento dei campioni compatibili; candidati non qualificati eventuali solo con etichetta/provenienza esplicite. Migrazione sensori 32/42→68 già definita per Start non significa trasferimento arbitrario sempre compatibile.
- **NEAT:** futuro trasferimento dell’intero genoma/topologia e mapping ingressi, fitness/specie coerenti e qualifica distinta. Non convertire una rete NEAT in un vettore di pesi denso.
- **Decisione aggiornata:** memoria generale personale e inizializzazione automatica diventano parte del prossimo lotto A; il lotto D completa consolidamento multipista, estensione a vetture/fondi diversi e verifiche di generalizzazione. Il trasferimento manuale diventa strumento di recupero, non il flusso normale. Specifica seguente.

### 5.1 Requisito: memoria personale e riuso automatico

**Un pilota conserva ciò che sa fare.** Evo, NEAT, PPO, Clone e PPO-Smooth mantengono ciascuno il proprio metodo e la propria base appresa. Passando dall’ovale a Varano o alla futura vettura diversa, il pilota parte da quella base e adatta velocità, frenate, traiettorie e gestione dell’aderenza. I principi acquisiti possono essere condivisi fra i contesti dello stesso pilota; le basi di piloti differenti restano indipendenti.

“Memoria di guida” indica pesi/genoma, abilità misurate e un archivio di scenari/esempi utili. Una cronologia di giri o un testo descrittivo non dà da solo capacità di guida alla rete. Non occorre introdurre un LLM né una rete ricorrente per conservare l’apprendimento fra sessioni; eventuale memoria temporale durante una manovra è una questione ulteriore.

Un pilota mai addestrato ha **base vuota**: deve ancora imparare. L’obiettivo “sa già guidare sul circuito nuovo” si applica al riuso delle competenze precedentemente acquisite, con efficacia da misurare. Non introdurre sterzo/gas automatici nascosti per fingere il trasferimento; Clone mantiene il maestro esplicito, Pure Pursuit mantiene il riferimento geometrico senza apprendimento.

### 5.2 Struttura proposta: base, esperienza locale e modello di gara

| Livello | Contenuto persistente | Uso |
| --- | --- | --- |
| **Base personale** | Policy/genoma generale versionato, schema input/output, metodo, competenze e prove di conservazione, hash/provenienza. | Inizializza automaticamente il primo allenamento in un nuovo contesto. Resta disponibile se la specializzazione peggiora. |
| **Esperienza del contesto** | Policy derivata e checkpoint locale, circuito/geometria, vettura/gomme, fondo/condizione/fisica, task/reward, contatori, evidenze e versione base d’origine. | Affina guida, passo, recupero e traffico nel contesto scelto; riprende esattamente le sessioni già iniziate. |
| **Campione di gara** | Versione congelata qualificata per quell’ambito, separata dal candidato e dal checkpoint in corso. | Una vettura per pilota; nessun aggiornamento della rete durante la gara. |

Prima implementazione: **base congelata + copia della policy per ogni contesto**. Consente il riuso senza richiedere subito rete a più teste o adapter. La copia locale conserva già il comportamento generale iniziale e lo affina. La base si aggiorna solo dopo consolidamento verificato; gli aggiornamenti non riscrivono specialisti/checkpoint esistenti. Una fusione aritmetica di pesi allenati separatamente non è il consolidamento previsto.

Il contesto ha chiave/hash dei parametri effettivi, non solo nome del circuito: potenza/massa/dimensioni, gomme, superficie/condizione e versioni fisiche possono cambiare il comportamento. Si conserva una stessa identità del pilota anche se aggiungiamo vetture diverse. Le qualifiche restano legate a **policy hash + configurazione + protocollo**, senza invalidare i record storici.

### 5.3 Flusso automatico dopo Start

1. Se esiste un checkpoint locale compatibile, **riprendere quel checkpoint**, inclusi optimizer/RNG/episodi. Una base più recente non lo sostituisce durante la ripresa.
2. Al primo allenamento di un contesto nuovo, selezionare la base personale compatibile approvata e creare atomicamente il percorso derivato. Nessun comando manuale “Trasferisci” necessario.
3. Al primo popolamento della nuova architettura, ricavare la base dai modelli storici dello stesso pilota: verificare compatibilità e abilità su una batteria comune. Scegliere la copertura dimostrata delle abilità, non la sola data, il maggior numero di passi o la fitness di task diversi. Conservare gli originali; niente media fra pesi/genomi.
4. Se non esiste ancora una base consolidata, riusare l’ultimo candidato compatibile dello stesso pilota come **base provvisoria**: provenienza e stato visibili, senza attribuirgli abilità o qualifiche non provate. Nessun degrado silenzioso a pesi casuali.
5. Se la base è vuota, avviare l’apprendimento iniziale. Se è incompatibile, mostrare il motivo e preservarla; una migrazione definita e verificata può espandere gli ingressi. Metodo del pilota resta fisso.
6. Eseguire una verifica di familiarizzazione al nuovo contesto, poi scegliere gli esercizi necessari dai risultati. Non imporre nuovamente tutta la Partenza 1→3→8→20 m a chi dimostra già la guida di base; allo stesso tempo non saltare curve/frenata/recupero/traffico non verificati.
7. Salvare esperienza locale, versione della base usata e risultati di trasferimento. Promuovere un campione locale soltanto con le sue prove; consolidare la base con il processo della sezione 5.5.

Aprire/cambiare schermata consulta i metadati; inizializzazione, familiarizzazione, ripasso e consolidamento si eseguono soltanto durante **Start**, nello stesso lavoro del pilota selezionato. Pausa salva e sospende tutte queste attività; niente allenamento globale al boot o mentre Gioco è chiuso.

### 5.4 Supporto coerente con ogni paradigma

| Metodo | Conoscenza riutilizzata | Adattamento/conservazione |
| --- | --- | --- |
| **Evo** | Pesi della policy densa personale. | Inserire la base e sue perturbazioni controllate nella nuova popolazione, conservando individui esplorativi. Fitness accoppiata su contesto nuovo e scenari di ripasso. Fitness/stagnazione del vecchio compito non trasferite come giudizio del nuovo. |
| **NEAT** | Genoma completo, topologia, pesi/bias e identificatori delle innovazioni coerenti. | Popolazione iniziale derivata dal genoma con varianti; ricostruzione di specie/fitness sul nuovo compito. Mapping ingressi e contatori validi, nessuna conversione implicita a rete densa. Il precedente limite “solo dense” va rimosso con test dedicati. |
| **PPO/PPO-Smooth** | Actor della base; eventuale critic generale solo se schema/obiettivo e parità sono verificati. | Per la prima versione inizializzare actor, critic/optimizer locali e rollout nuovi. Ripasso tramite **nuove transizioni** generate sui vecchi contesti dalla policy corrente. Non inserire rollout storici fuori policy nel normale update PPO. Qualsiasi distillazione/regolarizzazione aggiuntiva deve essere versionata e studiata. |
| **Clone** | Pesi personali e dataset etichettato stratificato per abilità/contesto/provenienza del maestro. | Nuovi esempi insieme a esempi di curve, recupero e traffico già acquisiti; copertura bilanciata, senza sostituire tutto con l’ultimo circuito. Maestro sempre dichiarato. |
| **Pure Pursuit** | Algoritmo geometrico e sue configurazioni versionate. | Si adatta alla geometria disponibile come riferimento. Nessuna falsa “memoria neurale” o crescita di competenza dichiarata. |

La ripresa di un contesto esistente mantiene il suo stato completo. L’inizializzazione di uno nuovo trasferisce il comportamento utile, mentre separa contatori, stato dell’ottimizzazione ed evidenze specifiche del task. Le particolarità NEAT e PPO rendono insufficiente una copia generica dello stesso JSON per tutti i metodi.

### 5.5 Consolidamento e protezione delle abilità precedenti

Allenare un contesto nuovo può deteriorare capacità precedenti. Gli studi su [CLEAR, NeurIPS 2019](https://papers.neurips.cc/paper_files/paper/2019/hash/fa7cdfad1a5aaf8370ebeda47a1ff1c3-Abstract.html) e [EWC, PNAS 2017](https://doi.org/10.1073/pnas.1611835114) motivano rispettivamente ripasso dell’esperienza e protezione dei parametri importanti. Sono riferimenti di ricerca; non dimostrano che quei metodi siano già applicabili senza modifiche al nostro PPO NumPy o a NEAT.

**Prima scelta da sperimentare:** curriculum misto con scenari ricreati e memoria congelata precedente. Il pilota si allena soprattutto nel contesto attivo e ripassa contesti acquisiti; rapporto iniziale candidato **80% nuovo / 20% ripasso**, confrontato con 100/0 e 60/40, a budget uguali. È un’ipotesi di studio, non una proporzione già ottimizzata. PPO raccoglie esperienze correnti; Clone può riusare esempi; Evo/NEAT valutano genomi su scenari accoppiati. Il paradigma resta quello scelto dal pilota.

- Archivio scenari stratificato per partenza, curve/frenata, recupero, passo e traffico, con contesto e seed riproducibili. Separare training/ripasso dalle prove riservate.
- Promuovere una nuova **base candidata** solo se mantiene le abilità precedenti e aggiunge/generalizza esperienza utile. La base consolidata precedente resta congelata e ripristinabile.
- Primo gate proposto: almeno **18/20 scenari validi** per ciascuna abilità dichiarata, sui contesti coperti; confronto accoppiato con la base precedente. Nessuna promozione se aumenta il numero di stalli/urti/uscite o se un’abilità passa sotto il gate. Usare distribuzioni e scenari sufficienti per interpretare variazioni, non un singolo episodio.
- Per il passo, studiare un margine candidato massimo di peggioramento del **5% della mediana** sui contesti precedenti, da fissare dopo misurare la variabilità. Recupero di sicurezza e velocità sono metriche distinte; una regressione non viene nascosta dalla media globale.
- Aggiornare il puntatore della base atomicamente con policy hash, provenienza, prove e configurazione. Un’interruzione lascia recuperabile la base precedente e il checkpoint locale; niente promozioni parziali.

RAM disponibile utilizzabile dopo Start per scenari/esempi e buffer necessari; cataloghi persistenti su disco, caricamento mirato dei contesti in uso. Non duplicare tutti gli optimizer/ambienti di tutte le piste in RAM e non avviare un learner per pista. Tempi di Pausa, throughput e GUI rimangono gate misurati; nessun nuovo backend NPU implicito.

### 5.6 Cambiare vettura o fondo

La memoria generale deve sostenere lo stesso pilota con auto di potenza, massa, freni e gomme differenti. Il comportamento trasferito deve essere condizionato da informazioni fisiche osservabili: capacità di accelerazione/frenata, geometria della vettura, aderenza nominale e suoi limiti di disponibilità, oltre ai sensori locali di strada/traffico. Il modello attuale a 68 ingressi **non certifica questa copertura**.

Definire uno schema osservativo futuro versionato, normalizzato e stabile fra i contenuti. Parametri di configurazione noti possono essere ingressi espliciti; stato di aderenza effettivo non disponibile non viene fornito come conoscenza onnisciente nascosta. Separare conoscenza delle specifiche da stima attraverso la dinamica. Espansione 32/42/68 e mapping NEAT devono conservare comportamento di riferimento e rendere tracciabile la migrazione.

Nella prima consegna restano vettura standard/asfalto asciutto e riuso fra circuiti. Il disegno dati include già vettura/gomme/fondo/condizione; generalizzazione fisica si qualifica quando esistono i nuovi contenuti. Provare una vettura più potente o meno aderente richiede familiarizzazione e prove proprie; “sa guidare” non garantisce automaticamente velocità ottimale o sicurezza su ogni auto.

### 5.7 UX: continuità visibile, pochi comandi

- Cambiare circuito/auto mantiene il pilota selezionato. Dossier mostra **Base di guida**, competenze acquisite, esperienza specifica, versione base d’origine e qualifica dell’ambito.
- Per contesto nuovo: “Usa la memoria del pilota”; dopo Start: “Familiarizzazione”, poi nome dell’esercizio necessario. Per contesto già appreso: “Riprendi esperienza”. Per candidato provvisorio: “Base in formazione”. Niente selettore obbligatorio della pista donatrice.
- Parametri del metodo restano in sola lettura. Provenienza e confronti completi nel dossier, fascia Pista con fase compatta; manteniamo 960×640 e i tre temi.
- La vista resta sul circuito osservato. Episodi di ripasso su altre geometrie non vengono sovrapposti a quella pista; fase di ripasso/consolidamento esplicita e popolazione/contatori riferiti al contesto visibile. Le scene restano dati reali.
- Reset **esperienza di questo contesto** e reset **intero pilota** distinti. Il primo conserva la base personale e alla ripartenza la riutilizza; il secondo azzera anche la base con conferma nominativa e archivio precedente. Gestione avanzata può ripartire da una versione storica compatibile senza cancellare gli altri percorsi.

### 5.8 Accettazione della memoria automatica

1. Nuovo contesto inizializzato dalla base **dello stesso pilota**, dopo Start, senza azione manuale; actor/genoma verificati nel worker effettivo e nella ripresa.
2. Esistente checkpoint ripreso identicamente, anche quando la base personale è stata aggiornata altrove. Nessuna sovrascrittura di campioni locali o qualifiche.
3. Spegnimento/riavvio conserva base, esperienza locale, provenienza e abilità dimostrate; nessun training al boot.
4. Confronto da zero / memoria trasferita / memoria + ripasso, stesso budget e almeno cinque semi per ciascun metodo che impara. Misurare abilità iniziale, passi/tempo per familiarizzarsi, stalli/validità/urti/recupero/tempi e costo sulla scheda.
5. Giro di apprendimento **ovale → circuito tecnico/Varano → ritorno all’ovale**; la base candidata mantiene le competenze originarie, senza contare soltanto la velocità dell’ultimo circuito. Hold-out e adattamento separati.
6. NEAT mantiene topologia/innovazioni compatibili; PPO non riceve rollout obsoleti nel normale update; Clone conserva etichette/provenienza. Tutti conservano il paradigma fisso e una sola sessione di apprendimento del pilota scelto.
7. Auto/fondi nuovi aggiunti in seguito: input fisici/schema e test prima di dichiarare il riuso qualificato. Una buona prova sull’ovale asciutto non genera automaticamente una qualifica su Varano bagnato o una vettura diversa.

## 6. Ordine dei prossimi lotti e accettazione

| Lotto | Attività | Gate |
| --- | --- | --- |
| **A · Memoria automatica e valori attivi** | Base personale versionata, bootstrap dai percorsi compatibili, inizializzazione automatica v2 al primo Start e priorità al checkpoint locale; DTO/menu/dossier veritieri. | Pesi/genoma personali effettivi nel worker/ripresa, origine conservata, nuova qualifica; nessuna azione manuale necessaria, tre temi 960×640. |
| **B · Recupero e reward** | Scenari rientro, progresso valido/anti-ciclo, obiettivo fallimento e provenienza versionata. | Fuori pista reversibile fisicamente; cicli/tagli non redditizi; rientro sicuro misurabile senza oscillare apposta sul bordo; guida normale conservata. Confronto cinque semi. |
| **C · Taratura metodi** | Scenari accoppiati Evo/NEAT; diagnostica PPO, confronto λ/rollout/minibatch; copertura Clone. | Stessi budget/scenari, mediana e dispersione su cinque semi, stalli/validità/tempi/urti/recuperi; migliore qualità a costo sostenibile, Pausa e GUI preservate. |
| **D · Consolidamento e generalizzazione** | Ripasso secondo il metodo, promozione della base, conservazione delle abilità e schema per vetture/fondi futuri. | Ovale → Varano → ovale, cinque semi, base precedente recuperabile; competenze originarie conservate, qualifiche per contesto/policy distinte. |

Non modificare i parametri dei piloti esistenti per una supposizione. Eseguire ricerca su copie, scegliere il profilo dai risultati e aprire un percorso versionato con originali conservati. CPU per fisica/training/inferenza dei piccoli modelli; grafica Qt sulla GPU; nessun cambio NPU motivato da queste nuove domande senza confronto completo.

## 7. Attuazione rc.12 e requisito Gara aggiunto

La rc.12 implementa memoria automatica personale, rientro e credito valido, scenari evolutivi accoppiati, diagnostica PPO, menu/dossier, ripasso e consolidamento. [Report di attuazione e prove](v09-driving-memory-report.md). I gate 18/20 e margine tempi 5% sono fissati nel protocollo iniziale; ricerca di efficacia/ottimo e generalizzazione fisica restano distinte dall’implementazione. La sola Partenza lascia la base **In formazione**.

**Richiesta del 13 ottobre:** tutte le vetture sempre visibili in Gara, incluse camera Sensori e gruppi separati. Inquadratura del gruppo e margine per il fuori pista, senza minimappa che copra auto. Record per pista e configurazione: giro più veloce pulito, massimo fisico della velocità, policy/pilota/sessione e primo giro da fermo dichiarati. Tempi misurati nei cancelli, pause escluse; nessuna stima dai risultati vecchi. Gare/Prove/Campione concluse separate, training/interruzioni esclusi dal record di gara. Classifica sintetica e dossier personale. Schema e prove descritti nel report rc.12.
