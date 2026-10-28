# Gioco · coerenza della guida, traguardo, infinito e metodi

**15 ottobre 2026 · Analisi e prove private · nessuna modifica al runtime installato.**

Richiesta: interpretare i progressi di Evo, uscite/tagli apparenti e scatti, NEAT aggressivo, utilità degli altri piloti e differenze del giro infinito. **Priorità: correggere il contratto comune fra allenamento e guida, poi tarare i singoli metodi. Conservare Evo.**

Nessun comando viene inviato all’allenamento originale. Nessun riavvio, installazione, reset, modifica ai preset o qualificazione scritta nel gioco reale. Le uniche scritture sulla scheda sono un export diagnostico privato, esterno al gioco; tutti gli esperimenti girano sul PC. `GameStore` viene costruito solo in directory temporanee, mai sui dati originali.

## 1. Cosa è stato realmente verificato

[Fotografia ridotta e hash](evidence/v09-methods-lap-integrity-2026-10-15/snapshot.json), acquisita **15 ottobre, 13:50:29 Europe/Rome**. SQLite aperto `mode=ro`, transazione coerente, artefatti verificati SHA-256. I checkpoint sono salvataggi durevoli, non una registrazione del frame osservato dall’utente.

- Scheda: **0.9.0-rc.16**, servizio attivo, `NRestarts=0`, PID 24575. Gli undici moduli esaminati corrispondono al checkout. Stesso runtime, nessun confronto con un codice differente.
- Sessione Evo Impara in corso; ultimo salvataggio fotografato 13:50:25. Le quantità successive possono già essere cresciute.
- I circa 92 aggiornamenti visti dall’utente sono compatibili con le **96 generazioni della fase Passo** al momento della cattura. Nel nuovo percorso sono 220; il contatore storico del learner è 376. **32 sono i candidati della popolazione**, non le generazioni.

| Pilota, percorso corrente Ovale 1 | Passi salvati | Stato verificato | Lettura corretta |
| --- | ---: | --- | --- |
| Evo | 13.908.853 | Passo, esercizi progressivi superati, pressione tempo 1,0 | Conoscenza consistente da conservare; candidato e memoria base non coincidono. |
| NEAT | 416.655 | Ingresso curva precedente, `balanced-driving-1`, quattro aggiornamenti nella fase | Non ha il nuovo curriculum Evo. Generazione learner 90 include esperienza precedente. |
| PPO | 0 | Profilo storico a 32 ingressi, nessun checkpoint attivo | L’inutilità/convergenza non è dimostrata dai dati del percorso corrente. Start deve effettuare l’espansione prevista. |
| Clone | 2.013 | Partenza, 1.984 esempi e 15 passi Adam | Esperienza molto breve, antecedente al bilanciamento corrente; non è una prova di impossibilità. |
| PPO-Smooth | 0 nel percorso corrente | Actor con 65 aggiornamenti storici, familiarizzazione 0/20 conclusi | Zero passi nuovi non significa pesi mai allenati; l’avvio sta verificando un modello ereditato. |
| Pursuit | Contatori storici presenti | Riferimento geometrico | Non è un modello che apprende. Il runtime corrente impedisce Start di allenamento. |

I successi cumulativi di Evo includono partenze, archi e protocolli precedenti: non sono una percentuale di giri validi nella generazione visibile.

## 2. Problema comune prioritario: la rete riceve un contesto diverso

### 2.1 Riscontro sul codice

Il canale **67, contando da zero, cioè il 68° ingresso**, contiene la fase di allenamento divisa per nove:

- Partenza: 0;
- Controllo: 1/9;
- Passo: 2/9;
- Gara 4: 1.

`Episode.reset/step` lo imposta in funzione della fase. Le viste Qualifica/Gara costruiscono invece direttamente `World`, il cui reset lascia il valore **1**. Inoltre Infinito usa Controllo, mentre il candidato Evo attuale viene selezionato in Passo. Il significato di questo ingresso cambia quindi al passaggio di modalità, pur lasciando invariati pesi e fisica.

Non basta chiamare il file «stessa rete». Va conservato anche il contratto dei suoi ingressi. Anche i tre canali temporali precedenti vanno confrontati fra `World` ed `Episode`, in particolare dopo un fuori pista.

### 2.2 Prova causale su copia

[Confronto delle fasi](evidence/v09-methods-lap-integrity-2026-10-15/phase-transfer.json), [adattatore diagnostico](evidence/v09-methods-lap-integrity-2026-10-15/context-adapter.json). Stesso candidato Evo, nessun aggiornamento dei pesi. Nel confronto iniziale Controllo/Passo gli stati fisici sono identici e **cambia soltanto l’ingresso 67**.

| Ambiente della copia | Contesto ricevuto | Esito |
| --- | ---: | --- |
| Un giro Passo, seed 901/902 | 2/9 | 2/2 riusciti, circa 23,1 s |
| Un giro Controllo, stessi seed | 1/9 | 2/2 ritiri, circa 8,9–9,0 s |
| Infinito con contesto Passo, stessi seed | 2/9 | Entrambi vivi alla finestra di 60 s, 11 settori attraversati |
| Infinito con contesto Controllo | 1/9 | Entrambi ritirati nella prima curva |
| World reale di Qualifica, seed 1 | 1 | Ritiro a 22,47 s, nessun giro |
| Stesso World di Qualifica, solo ingresso 67 reso coerente | 2/9 | **Quattro giri puliti**, zero uscite; 23,07 s da fermo, poi 20,20 / 20,16 / **20,10 s** |

L’adattatore diagnostico modifica un’osservazione prima dell’inferenza, **non sterzo, gas, freno o fisica**. Non è installato. Non ha scritto certificati o record. La prova su un circuito/un seed non qualifica tutti i contesti, ma identifica un difetto concreto che precede la taratura dei premi.

### 2.3 Intervento proposto

1. Definire un contratto comune delle osservazioni usato da allenamento, valutazione, preview, infinito, Qualifica e Gara. Un’etichetta interna del curriculum non deve cambiare implicitamente lo stile di guida quando si apre un’altra modalità.
2. Salvare nel modello versione semantica e contesto con cui è stato effettivamente verificato. Non dedurlo dalla schermata aperta. La base personale vecchia, allenata in Controllo, non deve ricevere automaticamente il contesto del candidato Passo.
3. Migrazione compatibile delle reti storiche; nuovi hash e nuove verifiche di Qualifica. Conservare checkpoint, RNG, provenienza e rollback. Non trasferire certificati al modello trasformato.
4. Poi una nuova versione del contratto può eliminare la fase interna dagli ingressi, oppure sostituirla con un dato operativo definito e disponibile ovunque. Prima di aggiungere sensori, chiarire stato del giro, settore atteso e credito valido: i sensori geometrici/slittamenti già presenti non sono pochi.

**Possibilità di conservare matematicamente la guida:** in una rete densa, per un ingresso costante `c`, si può incorporare il suo contributo nel bias nascosto (`b' = b + W67*c`) e azzerare quel peso. Su 256 vettori privati, il controller Evo trasformato riproduce quello condizionato a Passo con errore massimo **4,17×10⁻¹⁶**: [prova](evidence/v09-methods-lap-integrity-2026-10-15/constant-feature-fold.json). Non sono stati salvati i pesi trasformati. Questo verifica la sola inferenza densa: migrazione di popolazioni, critic, Adam, genomi NEAT, basi e qualifiche richiede gate dedicati. Non promettere una conservazione automatica degli ottimizzatori.

## 3. Fuori pista e traguardo: cosa è un bug e cosa no

### 3.1 Fuori pista fisico già presente

Il fuori pista riduce l’aderenza effettiva da 0,95 a 0,45 a parità degli altri fattori, aumenta la resistenza al rotolamento a 0,045, registra ingressi e secondi esterni. Sono controllati sagoma e bordi; oltre circa sei metri dal bordo stradale avviene il ritiro. Non è obbligatorio sparire al primo contatto con l’erba: il recupero è intenzionale.

Il reward usa progresso valido, penalità di uscita/tempo esterno e controllo del giro. Non paga il recupero della stessa distanza andando avanti e indietro: il fronte massimo del progresso viene conservato. Un rientro non deve generare un premio ripetibile con uscite volontarie; resta appropriato misurare recupero e successivo avanzamento sicuro.

### 3.2 Passare sulla linea non equivale a completare il compito

[Prova fisica riproducibile](evidence/v09-methods-lap-integrity-2026-10-15/contracts.json): un controllore diagnostico effettua un’escursione fra circa 40 e 100 m, poi rientra. Non viene teletrasportato.

- Il primo settore viene attraversato fuori pista e non accreditato.
- A **59,93 s** supera fisicamente la linea: progresso geometrico 338,87 m, ma solo **280,86 m validi**, settore ancora 0. L’auto continua.
- A **69,95 s**, raggiunti 338,81 m validi dopo 396,83 m geometrici, il compito termina **non valido**. Nessun falso successo osservato in questa prova.

Il riferimento senza escursione termina regolarmente sulla linea, con quattro settori e zero uscite. La misura usa il centro della vettura: il muso può superare la linea circa 2,2 m prima del riferimento fisico usato dal timer.

**Problema UX reale:** manca una spiegazione immediata «giro invalidato / settore mancante». Il comportamento appare un exploit anche quando il tentativo non sarà accettato.

### 3.3 Settore saltato che non si riaggancia: difetto riprodotto

I settori dell’ovale richiedono che il progresso passi dal lato precedente a quello successivo della soglia. Se quel passaggio viene rifiutato perché esterno, la soglia resta alle spalle. Non viene riarmata al passaggio successivo sul traguardo.

[Prova continua di 130 s](evidence/v09-methods-lap-integrity-2026-10-15/gate-recovery.json): dopo un’unica escursione di 10,03 s, l’auto rientra e supera la linea due volte, a 59,93 e 119,28 s. I settori restano **0**, nessun giro registrato; nella seconda tornata non aumenta il tempo fuori pista. Questa condizione può compromettere Infinito e recupero di un giro successivo anche in Qualifica.

**Correzione proposta:** separare attraversamento fisico dei settori, validità della tornata, conteggio dei giri e avanzamento sicuro. Un giro sporco non dà premio/tempo valido, ma non deve impedire per sempre di iniziare una nuova tornata pulita. Riarmare sul traguardo con controlli di verso, ordine e distanza plausibile; non basta azzerare i settori a ogni contatto con la linea. Tagli interni, inversioni, oscillazioni sulla linea e salti di settori devono restare invalidi. Verificare anche partenze fuori dall’origine ufficiale sui circuiti poligonali: soglie relative al progresso e porte fisiche assolute non devono divergere. Questa variante non è stata provata nello studio corrente.

## 4. Evo: migliorare il pilota migliore, non eliminare l’esplorazione

[Popolazione congelata](evidence/v09-methods-lap-integrity-2026-10-15/frozen-pilots.json), due scenari principali della sua banca, 64 tentativi complessivi:

- 12 successi, 46 ritiri, cinque non validi, uno stallo;
- **l’elite in posizione 0 completa entrambi i casi**, circa 23 s;
- 32/32 danno gas inizialmente; lo sterzo supera metà comando in sette/tre candidati, senza saturazioni oltre 0,9.

La distribuzione osservata dall’utente è plausibile. Non è stata ricostruita la sua esatta generazione o l’esatta ripartizione prima/seconda curva. Il checkpoint fotografato aveva una nuova griglia ancora attiva; questi sono nuovi episodi privati, senza evoluzione.

Una popolazione contiene mutazioni ed esploratori: non è necessario che tutti i 32 completino il giro perché esista un pilota utile. Occorre mostrare distintamente **candidato in prova, migliore verificato e popolazione esplorativa**. Qualifica usa attualmente prima il candidato più recente; il modello stabile deve restare selezionabile e attribuito alla sua versione.

Passi proposti:

- conservare pesi e base di Evo; correggere prima il contesto di guida;
- mantenere un archivio del migliore verificato per circuito/configurazione, distinto dal vincitore della generazione corrente;
- ampliare il ripasso con partenza, curva lenta/veloce su entrambi i lati e passaggi fra giri: la sola Partenza non conserva tutte le abilità;
- variare la banca con regole dichiarate, rivalutando candidati e baseline sulle stesse condizioni. Non confrontare vecchi record di fitness su banche diverse;
- pressione sul tempo subordinata a giri puliti ripetibili. Nel codice, dopo gli esercizi, cresce di 0,125 a ogni aggiornamento fino a 1; la conferma continuativa della competenza va resa più forte;
- valutare una quota maggiore di mutazioni locali quando il migliore è già valido. La scala attuale 1,7 e i discendenti ampi spiegano parte delle uscite; non togliere tutta l’esplorazione.

La rete già percorre quattro giri con il contesto giusto. Non serve cancellare oltre tredici milioni di passi per tentare di risolvere un errore di ingresso.

## 5. NEAT: stessa progressione di compiti, evoluzione propria

NEAT conserva il vecchio ingresso di 140 m con velocità iniziali variabili e ripasso ogni quinta generazione. Quel cambio chiama `change_reward()`, azzerando campione e storia di stagnazione delle specie. Le correzioni Evo non sono automaticamente applicate a NEAT.

Due scenari congelati di curva, 32 reti ciascuno: **sei successi, 49 ritiri, due non validi, sette stalli**. Sul compito iniziale di un metro, **29/32** riescono. Quindi partire non è il problema principale.

Lo sterzo iniziale supera metà comando in **14/32** e **29/32** reti; tre/dodici saturano oltre 0,9. L’inizializzazione è `full_direct`, sigma pesi 0,3 e bias 0,3. L’attivazione NEAT-Python è **tanh(2,5 z)**, non la tanh standard: la maggiore sensibilità è documentata nella [libreria ufficiale](https://neat-python.readthedocs.io/en/latest/activation.html). Il fenomeno osservato è compatibile con un controllo troppo sensibile per la velocità d’ingresso; la prova non dimostra che la rete «voglia tagliare».

**Studio di preset NEAT proposto, non taratura già validata:**

| Voce | Attuale | Confronto privato proposto |
| --- | --- | --- |
| Curriculum | Vecchie curve a difficoltà variabile | Progressione comune da rettilineo/arco lento e banca separata di esame |
| Pesi iniziali | sigma 0,3, connessione completa | Sigma 0,04 / 0,08 / 0,12; confrontare piena e parziale in esperimenti separati |
| Bias iniziali | sigma 0,3 | 0,05 / 0,10; segnalare ogni prior introdotto |
| Mutazioni | potenza 0,15 | 0,03 / 0,06 / 0,10, con regressione sulla diversità e precisione |
| Due discendenti speciali | bias pedale −0,4 / −0,8 | Varianti simmetriche piccole; nessuna preferenza permanente per il freno |
| Specie/stagnazione | Riavviate anche al ripasso | Storia della stessa suite e della stessa fase, senza reset fra casi |

La [configurazione ufficiale NEAT](https://neat-python.readthedocs.io/en/latest/config_file.html) permette di distinguere inizializzazione, mutazioni, connessioni e specie. Non cambiare tutte le variabili insieme. Il costruttore NEAT sovrascrive le potenze di mutazione del file di configurazione con `profile.mutation`: cambiare il solo file non basterebbe. Usare un preset versionato e mostrare nel menu i valori effettivi, mantenendo il vincolo del paradigma. Non cambiare la tanh nel solo Python lasciando diversa l’attivazione dell’export o del kernel nativo. Se si introduce un ordinamento multiobiettivo, non passare banalmente i ranghi 0–31 alla stagnazione delle specie: il massimo resterebbe costante anche quando la qualità migliora. Serve una qualità comparabile per fase oltre all’ordine di riproduzione.

NEAT deve restare NEAT: nessun maestro che corregga i comandi in modo nascosto.

## 6. PPO, PPO-Smooth e Clone: segnali di apprendimento misurati

La guida ufficiale [SB3 sulle sperimentazioni RL](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html) raccomanda ambiente semplificato, ingressi/azioni coerenti, valutazione separata e più seed; un preset predefinito non garantisce convergenza sul nostro ambiente. Qui il PPO è una nostra implementazione NumPy, non SB3: la documentazione è un riferimento, non un certificato di equivalenza.

### 6.1 Calibrazione breve reale

Copie temporanee dei piloti, stessa preparazione di Start (`activate_academy` e `prepare_driving`), **50.000 nuove transizioni per metodo**, un solo seed del rispettivo preset. Nessun modello risultante installato. Prove finali congelate su due seed separati: [PPO](evidence/v09-methods-lap-integrity-2026-10-15/ppo-calibration.json), [PPO-Smooth](evidence/v09-methods-lap-integrity-2026-10-15/ppo-smooth-calibration.json), [Clone](evidence/v09-methods-lap-integrity-2026-10-15/clone-calibration.json).

| Metodo | Prima, 20 m | Dopo 50 mila passi, 20 m | Conclusione limitata |
| --- | --- | --- | --- |
| PPO | Due stalli, nessun avanzamento | **2/2 riusciti, 5,57 s** | Impara a partire; non è ancora una prova di guida del circuito. |
| PPO-Smooth | Due ritiri, circa 8–9 m validi | Ancora due ritiri, circa 9–10 m | È il candidato che richiede il confronto più urgente tra pesi ereditati e partenza nuova. |
| Clone | 2/2 riusciti, 6,70–6,72 s | **2/2 riusciti, 3,42–3,43 s** | La supervisione funziona già sul compito breve; serve coprire curve e recuperi. |

PPO ha completato sei aggiornamenti di rollout; nel percorso privato raggiunge il livello Partenza 8 m. Il risultato finale sui 20 m non promuove automaticamente il suo curriculum. PPO-Smooth conserva 65 aggiornamenti storici, poi ne esegue sei nuovi; il confronto non è tra modelli con identica inizializzazione. I tempi PC con tre processi concorrenti non misurano throughput o FPS della board.

### 6.2 PPO

Mantenere inizialmente `gamma = exp(-1/2400) ≈ 0,999583`, GAE λ0,99, LR 0,0003, clip 0,2, target KL 0,03, rollout 256 per 32 ambienti, quattro epoche e minibatch 64. Un rollout è circa **4,27 s simulati per ambiente** e 8.192 transizioni complessive, non 256 tentativi.

Prima risolvere contratto/modalità e curriculum comune. Poi confrontare LR 0,0001/0,0003, λ0,97/0,99 e batch 64/128, una dimensione alla volta. Controllare KL, clipping, varianza spiegata, quota gas/freno e successi deterministici; una loss in diminuzione non certifica un giro.

I due gate numerici mirati già presenti — gradiente contro differenze finite e bootstrap senza teletrasporto alla finestra — sono stati rieseguiti e superati: [esito](evidence/v09-methods-lap-integrity-2026-10-15/ppo-numeric-gates.txt). Non dimostrano convergenza ma evitano di attribuire il problema a una formula senza riscontro.

La logica usa già `terminated` per il bootstrap e `done` per interrompere il GAE: la distinzione prescritta da [Gymnasium per i limiti temporali](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/) non va eliminata. Campionamento gaussiano in training e guida deterministica nei test devono essere distinti. La trasformazione tanh non è da dichiarare errata per la sola assenza di una Jacobiana nel rapporto PPO: la stessa trasformazione si cancella nel rapporto; l’entropia grezza richiede invece una lettura corretta.

Un’eventuale esplorazione temporalmente correlata richiede una distribuzione/likelihood coerente; non ripristinare rumore OU aggiunto a posteriori. Per ora non è necessario sostituire PPO con un altro algoritmo: la calibrazione mostra già un segnale utile, coerente con il [metodo originale](https://arxiv.org/abs/1707.06347).

### 6.3 PPO-Smooth

È PPO con costo fisico dello sterzo brusco, non un paradigma indipendente. La policy ereditata ha una marcata curvatura iniziale e non supera 20 m nei test deterministici. Confrontare copia attuale e nuova a identico budget, poi introdurre il costo smooth solo dopo guida di base affidabile: coefficienti 0 / 0,025 / 0,1 come esperimento. Non resettare Evo per questo risultato. Nessun reset di PPO-Smooth originale viene effettuato nello studio.

### 6.4 Clone

Non bilanciarlo principalmente attraverso premi e penalità: impara dalle azioni del maestro. Servono esempi di rettilinei, curve a velocità diverse, frenate, stati di errore e rientri. La raccolta attuale segue gli stati visitati dall’allievo; il buffer di 2.048 esempi può perdere la copertura delle fasi precedenti. Studiare buffer stratificato 8.192/16.384, mix di manovre e mantenimento dei casi difficili, senza aumentare il costo per ogni frame. Valutare errore sterzo/pedale per manovra, non solo loss globale.

La proposta di iniziare da dimostrazioni dell’esperto e aggregare gli stati dell’allievo ha il riferimento nel [lavoro DAgger](https://arxiv.org/abs/1011.0686). Va dichiarato quando si usa una fase di dimostrazione; non applicarla in modo nascosto a Evo/NEAT/PPO puri.

La rete 68→16→2 è sufficiente a esprimere almeno la guida dell’ovale, come mostra Evo. Confrontare 16/32 neuroni dopo la correzione dell’ambiente; aumentare la rete non è la prima risposta al difetto di contesto.

## 7. Giro infinito: quattro problemi distinti

1. **Fisica continua esistente:** il riferimento supera il giro senza fermarsi e arriva alla finestra di 60 s senza uscite. Non manca del tutto la modalità.
2. **Trasferimento della fase:** il candidato attuale sopravvive ai 60 s se mantiene il contesto Passo, ma si ritira al primo ingresso curva con quello Controllo.
3. **Checkpoint locale precedente:** Infinito conserva un proprio ramo da **496.161 passi**, salvato alle **12:35:20**, contro il nuovo normale fotografato alle 13:50:25. È prioritario nella ripresa e non viene sostituito a ogni miglioramento di Impara. I due piloti locali congelati non sono equivalenti; quello infinito si ritira sui due casi provati. La memoria base di Controllo sa fare il primo giro in 21,35 s, ma si ritira alla curva successiva: un giro da fermo non dimostra endurance.
4. **Finestre ed evoluzione:** la prova sintetica di scheduler dopo una finestra completata mantiene tempo/giri per PPO e Clone, mentre Evo/NEAT ricreano mondi da zero. Il risultato è specifico del confine di raccolta, non una registrazione di allenamento fisico a 60 s. Inoltre il settore saltato blocca i giri successivi anche continuando davvero la fisica, come verificato nella prova di 130 s.

**Contratto da implementare:** una finestra di raccolta non deve apparire come uno schianto del pilota. Separare durata della raccolta, vita dell’auto, cambio del candidato e fine della generazione. Per PPO/Clone continuare il mondo con bootstrap; per Evo/NEAT decidere esplicitamente quali controller sopravvivono alla riproduzione. Solo una policy rimasta identica può ereditare senza ambiguità la stessa vettura. I figli mutati sono nuovi tentativi e vanno segnalati come tali.

Non basta chiamare `next_window()` per tutti: Evo/NEAT hanno selezione/riproduzione e fitness, con problemi di equità se si confronta un’elite già lanciata con un figlio fermo. Nel primo intervento mantenere il metodo riconoscibile e dichiarare il confine di round; lo studio successivo confronta finestre a punteggio normalizzato, budget controllati e continuità delle elite. Endurance deve essere verificata su almeno cinque giri consecutivi, senza tetto fisico di un giro e senza reset occulto a 60 s.

Per il ramo locale già esistente: conservare la possibilità di ripresa; confrontare una copia inizializzata dal nuovo migliore sullo stesso scenario prima di proporne l’adozione. L’automatismo può accettare una base migliore dopo prova accoppiata, non mediare pesi o sostituire silenziosamente il ramo in corso.

## 8. Scatti, tagli apparenti e informazione sul display

Un checkpoint non dimostra un difetto ottico o un teletrasporto del motore. La fisica resta a passi 1/60 s; i cambi di scenario/generazione ricreano deliberatamente le posizioni e cambiano `resetKey`. La presentazione azzera l’interpolazione su quel confine. Ritiro e completamento fermano la vettura; le altre possono continuare.

Prossima strumentazione mirata: ring diagnostico con ID auto/policy, generazione/scenario, motivo del reset, tempo simulato, posizione fisica, posizione pubblicata e presentata, progresso valido/geometrico, settori e stato giro. Correlare questi dati con intervalli del rendering e simRate. Non attribuire gli scatti a GPU/NPU o a un exploit sulla sola impressione visiva.

UI proposta, entro l’attuale footer e dossier, senza ridurre la pista:

- «Gen. della fase · scenario 1/3» e contatore conclusi, separati dal pilota verificato;
- stato «Valido / Giro invalidato / Settore mancante / Nuovo candidato / Finestra conclusa»;
- nel dossier: migliore verificato, candidato corrente, provenienza del ramo infinito, età/versione della base, risultati per esercizio e ultimo motivo di fallimento;
- velocità massima e tempo valido sempre attribuiti a pista/configurazione/policy; un taglio non entra nella classifica.

## 9. Sequenza proposta e criteri di accettazione

| Blocco | Lavoro proposto | Uscita verificabile |
| --- | --- | --- |
| **P0.1 Contratto** | Stessi ingressi e metadati in guida/valutazione; migrazione compatibile e archivi | Policy congelata, stesso stato fisico: osservazioni e prefisso azioni coerenti fra modalità, salvo avversari reali. Vettori casuali per parità migrazione; nessuna vecchia qualifica riattribuita. |
| **P0.2 Giri** | Separare settori, validità e riarmo dopo un giro sporco | Tagli/inversioni/oscillazioni mai validi; giro successivo pulito registrabile dopo l’escursione riprodotta; timer e stato UI spiegano l’esito. |
| **P0.3 Infinito** | Ramo/provenienza espliciti, finestre separate dalla vita della vettura, cambio policy dichiarato | Più di 120 s e cinque giri con controller invariato; nessun reset a una sola frontiera di raccolta, pausa/ripresa identica. Gate dedicato alla riproduzione Evo/NEAT. |
| **P1.1 Curriculum** | Compiti graduali e ripasso comparabile per tutti i metodi | Stessi scenari principali; modalità di selezione/aggiornamento proprie del metodo; promozioni su test deterministici separati. |
| **P1.2 Preset** | NEAT, PPO, Smooth e dataset Clone secondo gli esperimenti sopra | Screening almeno tre seed × 250 mila nuove transizioni; poi cinque seed e budget uguali dichiarati. Riportare anche costo di valutazioni/familiarizzazione. |
| **P1.3 Evo rapido** | Migliore verificato, retention degli archi, pressione tempo condizionata | ≥18/20 giri puliti prima di perseguire il tempo; passi/tempo necessari e regressioni pubblicati. Endurance e gara non dedotti dal giro singolo. |
| **P2 Risorse/UI** | Trace mirato e costo per fase, compatibilità tre temi | Separare reset, ritardo del learner e frame pacing; nessun incremento di budget hardware dichiarato risolutivo senza misura. |

Prima i due difetti comuni riprodotti; poi le ablazioni dei preset. Conservare dati, identità e copie delle policy durante tutto il lavoro. GPU resta dedicata al rendering e NPU non risolve incoerenza degli ingressi o dei criteri di arrivo.

## 10. Limiti delle prove e decisione

- Le prove di apprendimento da 50 mila passi hanno un solo seed per metodo: dimostrano segnali di vita, non convergenza sul circuito.
- L’adattatore di contesto ha quattro giri puliti su Ovale 1 con una vettura e un seed; altri circuiti, meteo e traffico sono ancora da verificare.
- La popolazione congelata è una fotografia, non l’esatta generazione osservata dall’utente. Non sono stati registrati gli scatti sul pannello.
- Il difetto di settore è riprodotto attraverso azioni e fisica reali, ma con un controllore diagnostico; non dimostra che una rete lo cerchi intenzionalmente.
- Alla verifica finale (14:17:42 Europe/Rome), il servizio ha ancora PID 24575, zero riavvii e 598 hash conformi, senza cambiamenti ai moduli. L’ultima sessione risulta interrotta dal salvataggio delle 13:50:44, con gli stessi passi/generazione e una verifica pendente salvata. Non sono stati inviati comandi di pausa/stop/ripresa e questa analisi non attribuisce la causa dell’interruzione. [Verifica del perimetro](evidence/v09-methods-lap-integrity-2026-10-15/scope-verification.json).
- I file con pesi originali restano in percorsi privati; nell’evidenza pubblica sono salvati hash, risultati e script. I diagnostici non fanno parte del runtime.

**Decisione proposta per l’implementazione successiva:** P0.1 → P0.2 → P0.3, preservando Evo; poi curriculum comune e taratura separata NEAT/PPO/Smooth/Clone. Nessuna cancellazione generale della memoria, nessuna promessa che un unico coefficiente di penalità risolva tutti i punti.

## Attuazione del piano · 15 ottobre 2026

L’implementazione autorizzata è tracciata nel [report rc.17](v09-driving-integrity-report.md), con prove e limiti separati. Durante il riesame è emersa una precisazione: il Worker reale di Qualifica/Gara impostava già il canale 67 a **1/9**; il valore **1** appartiene al reset di World e al precedente probe diagnostico privo del ciclo Worker. Il contrasto con Passo **2/9** rimane. La nuova verifica Main→Worker→certificato copre il percorso effettivo e non si limita al World isolato. Le evidenze originarie restano storiche e non vengono riscritte.
