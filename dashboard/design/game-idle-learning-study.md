# Gioco · piloti fermi e apprendimento della partenza

**Studio 1 · 12 ottobre 2026 · sorgenti 0.9.0-rc.8.**

**Seguito 13 ottobre:** implementazione nella [rc.9 Accademia](v09-academy-report.md), con prove e limiti aggiornati. Il testo seguente conserva lo studio preparatorio del 12 ottobre e le sue misure sulla rc.8.

Seguito dello [studio spazio gara, fisica e sensori](game-racing-space-physics-sensors-study.md). Richiesta: comprendere perché alcune auto restano ferme mentre imparano e preparare il lavoro per l'implementazione. Analisi con ispezione del codice, fonti primarie e prove PC isolate. Nessun pilota originale è allenato/reset, nessun runtime o preset è modificato, nessuna installazione è effettuata.

## 1. Conclusione operativa

Il comportamento è possibile con l'obiettivo attuale: una politica può imparare a non accelerare perché evita una perdita immediata per incidente. La parola «paura» descrive l'effetto visibile, non uno stato emotivo della rete.

**Non manca del tutto un premio al movimento:** il progresso in avanti è già premiato e una partenza corretta rende più dell'immobilità. Il problema è rendere quel comportamento abbastanza facile da scoprire, senza sprecare tentativi lunghi o trasformare l'agente in un'auto che accelera sempre.

Priorità prima delle estensioni fisiche maggiori:

1. Registrare la causa della sosta e i termini della ricompensa.
2. Rilevare stallo e riciclare i tentativi improduttivi **solo in allenamento**.
3. Introdurre un compito breve di partenza/avanzamento prima del giro completo.
4. Confrontare reward e orizzonte PPO in secondi, preservando metodo e percorso precedente.
5. Verificare che la partenza migliori senza peggiorare frenate, validità e traffico.

Queste sono proposte per il seguito v0.9, non correzioni già qualificate. L'attribuzione ai singoli piloti osservati dall'utente richiede tracce correnti di comandi, stati e fase; le prove qui sotto verificano il meccanismo, non diagnosticano un checkpoint di produzione.

## 2. Tre fenomeni da distinguere

| Fenomeno | Dati che lo distinguono | Intervento |
| --- | --- | --- |
| Politica immobile | Auto attiva, passi fisici avanzano, gas nullo/freno, progresso vicino a zero. | Obiettivo, esplorazione e curriculum. |
| Auto inattiva o attesa della popolazione | Arrivata/ritirata, altri candidati ancora attivi. | Stato chiaro; non chiamarlo stallo del pilota. |
| Fisica temporaneamente sospesa dal training | Aggiornamento rete/valutazione/salvataggio o pausa, senza nuovi passi del mondo mostrato. | Profilazione e indicazione discreta della fase; timer di stallo fermo. |

La gara usa politiche congelate; l'allenamento PPO usa azioni campionate. Una rete con gas medio negativo può avere una dimostrazione deterministica ferma e ancora provare ad accelerare durante il training. Campione, candidato e singolo tentativo non sono lo stesso oggetto.

Pure Pursuit non apprende: se appare fermo, controllare fase/pausa/ritiro e geometria del controllore prima di applicare una diagnosi di mancata esplorazione.

## 3. Incentivi correnti, verificati nel codice

Ricompensa di `World.step`, sommata sui sottopassi:

```text
progresso / 10 + 10 × arrivo − 5 × contatto
− h × attivo × (0,02 + 0,28 × peso_Passo)
− h × attivo × 0,005 × |sterzo|
+ bonus_arrivo_veloce_limitato
− h × attivo × costo_PPO_Smooth × errore_comando_sterzo²
```

La fase Controllo ha peso Passo zero; nella fase Passo aumenta gradualmente fino a uno. Il bonus veloce vale solo dopo un arrivo valido. A veicolo fermo e sterzo zero:

- Controllo: −0,02 punti per secondo simulato.
- Passo a peso uno: −0,30 punti per secondo simulato.
- Contatto: −5 punti una volta, con ritiro.

In 15 secondi stare fermi costa soltanto **−0,30** in Controllo. Partire sterzando male può perdere quasi cinque punti in pochi secondi. È un incentivo plausibile a evitare azioni rischiose quando la rete non sa ancora guidare.

Sul rettilineo, trascurando altri costi, il bilancio del reward continuo diventa positivo sopra 0,2 m/s in Controllo e 3 m/s in Passo a peso uno. Questo è un bilancio matematico, **non un comando di velocità minima**, né una prova che la rete sappia raggiungerla in sicurezza.

### Durata massima senza movimento

Il protocollo attuale permette `max(60 s, lunghezza / 7 × 1,8)` per giro. Nessun limite specifico per stallo.

| Circuito | Controllo, un giro | Passo, tre giri |
| --- | ---: | ---: |
| Ovale compatto | 87,1 s | 261,3 s |
| Circuito Tecnico | 70,0 s | 209,9 s |
| Mallory | 413,8 s | 1.241,5 s |
| Varano | 421,7 s | 1.265,1 s |

Sono **secondi simulati**, non durata reale della sessione. Evoluzione/NEAT aspettano il completamento dell'intera popolazione prima della nuova generazione: un candidato fermo può prolungare il ciclo. PPO/Clone riavviano gli episodi conclusi, ma un episodio immobile può comunque consumare molti passi prima del timeout.

Non si deve correggere questo problema accorciando arbitrariamente il budget necessario per un giro reale: serve un limite specifico al mancato avanzamento.

## 4. PPO: l'orizzonte temporale è corto

Il preset usa `gamma=0,995` per passo a 60 Hz. Il peso di una ricompensa dopo t secondi è `gamma^(60t)`:

| Ritardo | Peso della ricompensa |
| --- | ---: |
| 1 s | 0,7403 |
| 5 s | 0,2223 |
| 10 s | 0,0494 |
| 30 s | 0,0001207 |
| 60 s | 0,0000000146 |

L'orizzonte di decadimento a 1/e è circa **3,325 s**. Il ritorno scontato di una politica sempre ferma, nel modello continuativo senza altri eventi, tende a −0,0667 in Controllo e −1 in Passo. Non coincide con il valore esatto del critic appreso, ma mostra la scala del confronto con un incidente vicino.

Il GAE usa λ=0,95; il decadimento della traccia γλ è circa 0,296 s. Il critic e il bootstrap possono propagare informazione oltre quel tratto: non significa che PPO possa apprendere soltanto 0,3 s di comportamento. Il rollout corrente da 256 passi copre 4,267 s per ambiente. Parametri, frequenza decisionale e tempo fisico vanno valutati insieme.

Candidati per il confronto: `gamma=exp(−DT/τ)` con τ=20/40/60 s, corrispondenti a 0,999167 / 0,999583 / 0,999722 a 60 Hz. Valori da provare, non un miglioramento garantito: possono aumentare varianza e difficoltà del critic. Confrontare poi λ/rollout separatamente. Il metodo rimane PPO; non riscrivere di nascosto gli iperparametri di un pilota esistente. [Schulman et al., PPO](https://arxiv.org/abs/1707.06347).

Esplorazione iniziale: deviazione standard raw `exp(−0,8)=0,4493`; durante l'apprendimento può scendere fino a `exp(−3)=0,0498`. Un actor con pedale medio negativo e varianza bassa può campionare quasi sempre freno. Questa è un'ipotesi da verificare sul checkpoint corrente, non un collasso osservato in questo studio.

## 5. Esperimenti isolati eseguiti

[Script](evidence/game-idle-learning-2026-10-12/analyze.py) e [audit completo](evidence/game-idle-learning-2026-10-12/audit.json), con hash dei sette sorgenti esaminati. **28 prove a comandi fissi** per massimo 15 s su Ovale/Mallory, Controllo/Passo; cinque campionamenti di PPO non allenati. Nessuno store o checkpoint originale aperto.

Esempi Mallory, Controllo:

| Comando fisso | Avanzamento | Reward totale | Esito entro 15 s |
| --- | ---: | ---: | --- |
| Gas zero | 0 m | −0,300 | Attivo e fermo |
| Freno a veicolo fermo | 0 m | −0,300 | Attivo e fermo |
| Gas 0,02 | 3,594 m | +0,059 | Attivo, molto lento |
| Gas 0,05 | 16,286 m | +1,329 | Attivo |
| Gas 0,20 | 104,656 m | +10,166 | Attivo |
| Gas 1, sterzo 0,8 | 5,169 m | −4,525 | Ritirato |

Il movimento corretto è già conveniente. Serve facilitare la scoperta di partenza e controllo, non aggiungere soltanto un premio per tenere il gas premuto. Anche accelerare molto dritto fino all'uscita può accumulare reward positivo prima di un incidente: eliminare le penalità di sicurezza sarebbe una regressione.

Nei cinque actor PPO appena inizializzati, due hanno gas medio positivo, tre negativo. Le azioni campionate hanno gas positivo tra circa **27,6% e 79,8%** nei campioni di questo scenario. La sola azione deterministica iniziale varia tra −0,267 e +0,354: una dimostrazione può restare ferma senza che l'esplorazione sia assente. Nessuna di queste reti rappresenta un pilota dell'utente.

## 6. Specifica candidata dello stallo

Introdurre una regola di ambiente/curriculum con versione propria, basata sul **tempo simulato**. Non usare il tempo trascorso mentre il worker aggiorna la rete, salva o attende l'interfaccia.

Stato minimo per episodio: età, massimo progresso valido raggiunto, tempo dall'ultimo nuovo progresso, finestra di velocità/progresso, durata delle condizioni di stallo, maschera di contesto. Resettare solo con il nuovo tentativo e includere tutto nel checkpoint.

Parametri iniziali da tarare:

| Campo candidato | Valore da confrontare | Scopo |
| --- | --- | --- |
| Grazia iniziale | 2 s | Non interrompere la prima accelerazione. |
| Velocità quasi nulla | <0,5 m/s | Distinguere immobilità da guida lenta. |
| Finestra progresso | 3 s, meno di 1 m di nuovo progresso valido | Evitare reset del timer con piccoli tremolii. |
| Condizione persistente | 4 s dopo la grazia | Evitare un singolo campione fermo. |
| Mancato avanzamento prolungato | 12–15 s, anche con velocità non nulla | Rilevare oscillazioni/giri su sé stessi. |

I valori non sono gate già acquisiti. Le condizioni devono essere combinate: una frenata breve non è stallo; l'avanzamento va misurato sul corretto ramo del circuito con cancelli, senza usare distanza assoluta percorsa o somme avanti/indietro. Riattraversare lo stesso tratto non deve generare nuovo credito all'infinito.

### Eccezioni di traffico

La sosta può essere corretta dietro un ostacolo o in una situazione di collisione imminente. In questi casi sospendere/modificare il detector secondo un contratto esplicito di corridoio disponibile, non secondo il gas premuto. Imporre comunque un budget finito allo scenario e registrare `blocked`, distinto da `no_progress` e `contact`. Verificare che l'agente non sfrutti l'eccezione parcheggiandosi vicino a un rivale.

In **Gara** non si riavvia né teletrasporta una vettura bloccata: continua secondo le regole del mondo, può scadere il tempo o ricevere una classificazione di ritiro esplicita. In **Impara**, il singolo episodio improduttivo finisce e si rigenera. Evoluzione/NEAT conservano il relativo punteggio e attendono gli altri candidati; non rimettono lo stesso individuo in gara per raccogliere reward aggiuntivo nella medesima valutazione.

### Fine episodio e PPO

Se lo stallo è definito come fallimento del compito, è terminale con `terminated=True`, penalità una volta e niente bootstrap terminale. Se è soltanto un limite esterno per risparmiare calcolo, è truncation e il bootstrap va conservato. Un semplice reset anticipato con bootstrap, senza cambiare incentivi, non risolve necessariamente la politica immobile.

Il backend già distingue `terminated` dal timeout per PPO: mantenere questa separazione e l'osservazione finale prima del reset. Con un fallimento dipendente da timer/finestra, lo stato temporale rilevante deve essere osservabile dal pilota oppure il problema diventa parzialmente osservabile. Rivedere lo schema 48/64 proposto nell'altro studio: potrebbero servire 2–3 canali di tempo/contesto, senza fingere che siano già inclusi. [Gymnasium, termination e truncation](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/).

## 7. Ricompensa e compito di partenza

### Prima soluzione da confrontare

1. Conservare progresso valido e penalità di sicurezza come riferimento.
2. Compito breve **Partenza** su un tratto libero: partire da zero e percorrere 20–40 m entro un budget candidato 10–20 s, con traiettoria valida e senza contatto. Successo una sola volta, poi un nuovo episodio; non promuove il pilota a pronto per Gara.
3. Prove con piccole variazioni di posizione/orientamento; alcune partenze lanciate per apprendere sterzo senza il blocco iniziale, ma mantenere sempre prove da fermo.
4. Stallo terminato con costo limitato da confrontare, per esempio 0,25 / 0,5 / 1 punto; registrare separatamente il costo e verificare che non renda conveniente schiantarsi subito per ricominciare.
5. Successivo Controllo su giro, Passo, poi traffico; richiamare periodicamente le partenze per non dimenticarle.

Il premio va associato all'avanzamento/successo, non al pedale o alla sola velocità: altrimenti il pilota può accelerare verso un bordo, girare su sé stesso o muoversi senza completare il compito. Non introdurre un acceleratore minimo nascosto. Ridurre la penalità per incidente non è la prima scelta.

Prima di fissare coefficienti, confrontare il ritorno di attesa, partenza corretta, guida lenta valida, zig-zag, urto immediato, urto tardivo e blocco giustificato; sia non scontato sia scontato PPO. Un singolo bonus di partenza può essere abusato facendo ripartire la stessa auto ripetutamente: successo per episodio con cancelli/milestone registrati.

### Shaping più strutturato, secondo esperimento

Eventuale termine `F = gamma × Φ(stato_successivo) − Φ(stato)` con potenziale limitato di avanzamento verso il compito e trattamento esplicito dei terminali. La ricerca di Ng, Harada e Russell dà condizioni per preservare le politiche ottime con questo tipo di shaping; non garantisce che qualunque bonus inventato o detector nuovo preservi l'obiettivo. Il reward corrente `delta/10` non è automaticamente quel termine quando gamma<1. [Policy invariance under reward transformations](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf).

Separare questo esperimento dalla modifica di gamma: confronti cumulativi senza ablation non permettono di attribuire il miglioramento.

## 8. Differenze tra paradigmi

| Pilota/metodo | Verifica specifica | Intervento candidato |
| --- | --- | --- |
| Evo | Distribuzione dei pedali, élite ferme, durata della generazione e diversità. | Compito Partenza e stallo; mantenere mutazione adattiva/reinizializzazione già presenti. Eventuale inizializzazione variata orientata alla partenza soltanto come esperimento dichiarato. |
| Neat | Connessioni attive verso il pedale, output/bias, specie e distribuzione di avanzamento. | Stesso compito, valutazione comparabile; non assumere che aumentare nodi risolva il problema. |
| PPO | Media gas, logStd/entropia, vantaggi, valore, timeout e reward scontato. | Compito/stallo, poi gamma in secondi e gestione rollout/critic; varianza adattiva soltanto dopo la diagnosi. |
| PPO-Smooth | Gli stessi dati, più costo del comando di sterzo rispetto agli altri termini. | Verificare che la regolarizzazione non sopprima manovre necessarie; non imputarle automaticamente la causa. |
| Clone | Azioni del maestro e dell'allievo, esempi di partenza/frenata, errore del pedale. | Bilanciare gli esempi per scenario; maestro esplicito, senza convertirlo implicitamente in PPO. |
| Pursuit | Velocità target e comando positivi da fermo, fase/validità del mondo. | Diagnosi deterministica; nessun reward di training deve alterare questo riferimento. |

L'esplorazione PPO corrente campiona comandi nuovi a 60 Hz: cambi rapidi tra gas e freno possono rendere più difficile una partenza sostenuta. Come esperimento successivo, confrontare decisioni mantenute per 2–3 tick fisici. Occorre un MDP dichiarato: reward aggregato con sconto coerente, gamma per intervallo, una probabilità per decisione e gestione dei terminali intermedi; niente rumore aggiunto fuori dalla distribuzione usata da PPO. Conservare correttezza già ottenuta per PPO-Smooth. Allineare frequenza nella valutazione/Gara o dichiarare gli ambiti separati.

## 9. Contratti e file da preparare per l'implementazione

| Area | Specifica prevista |
| --- | --- |
| `game_protocol.py` | TaskSpec versionato con obiettivo Partenza/Controllo/Passo, deadline, configurazione stallo e successi. Versione distinta da fisica/sensori. |
| `game_simulation.py` + modulo di obiettivo/detector | Componenti reward e stato finale osservabili; detector sul tempo simulato e progresso valido, motivo di fine episodio. Preferire logica del compito separata dall'integratore fisico. |
| `game_worker.py` | Applicare detector prima della registrazione PPO, distinguere terminated/truncated; reset soltanto in training, selezione/attesa della popolazione coerenti. |
| `game_learning.py` / `game_neat.py` | Metriche di esplorazione per metodo, punteggi comparabili nella stessa versione; eventuale nuovo preset immutabile documentato. |
| `game_curriculum.py` | Partenza come fase dichiarata; promozione con validità, non fitness soltanto. Reward vecchio e nuovo mai mischiati nello stesso rollout. |
| Store/checkpoint/dossier | Timer, finestra, progresso massimo, motivo finale, contatori, versione obiettivo/reward/trainer/frequenza; snapshot e ripresa deterministici. |
| Context/UI/temi | Campi additivi per fase/attività/motivo; riga breve Pista, dettagli in Pilota/Progressi. Kit/fixture/theme fallback al momento dell'implementazione. |

Eventi diagnostici candidati: `launch_success`, `no_progress`, `blocked`, `contact`, `finish`, `timeout`. Non mappare ogni stallo a «incidente»: l'attuale conteggio di contatti basato sullo stato di ritiro va esteso con il motivo, conservando i record precedenti come tali.

Dati da registrare per finestre/sessione: quota episodi senza partenza, tempo al primo metro e a 10 m, avanzamento massimo, secondi fermi, quota freno a u≈0, gas medio e distribuzione, cause finali, singoli termini reward; PPO logStd/entropia/critic, Evo/NEAT diversità e specie dove disponibili. La telemetria diagnostica non va inviata tutta a ogni frame QML: aggregare nel worker e persistere in background secondo l'architettura esistente.

**Compatibilità:** mantenere identità e paradigma dei piloti, percorsi/versioni precedenti, pesi, storico e contatori. Nessun reset automatico del pilota perché fallisce una partenza. Il cambio reward/trainer richiede nuova sessione dichiarata: chiudere/scartare esplicitamente rollout vecchi, trattare critic/optimizer con provenienza e rivalutare élite. Non aggiungere il nuovo gate a una vecchia prova come se fosse stato superato.

## 10. UX coerente con il sistema

Nessuna nuova fascia che sottragga spazio alla pista. Nella zona informativa esistente mostrare un solo stato selezionato: «Partenza», «Controllo», «Aggiorna rete», «Valutazione» o «Nuovo tentativo». In Pilota/Progressi: «Partenze riuscite», durata mediana della partenza, quota stalli e validità dei giri.

Non mostrare «paura» come diagnosi del modello. Un tentativo riparte, il pilota persiste: rendere evidente questa differenza. Start esplicito, 5 per pausa e comandi di camera/selezione catturati durante la simulazione restano quelli approvati. I valori del metodo restano fissi e leggibili; il curriculum è un percorso di apprendimento, non un menu con molti nuovi coefficienti.

## 11. Sequenza di lavoro e gate

| Lotto | Risultato concreto | Gate richiesto |
| --- | --- | --- |
| **L0 · Diagnosi** | Metriche e motivi di fine episodio, confronto di tracce correnti su copie. | Distinguere immobile, inattivo e aggiornamento; dati finiti, costi contenuti. |
| **L1 · Tentativi utili** | Detector/TaskSpec, fase Partenza, ripresa e reset del solo episodio. | Casi deterministici e checkpoint equivalenti; nessun reset in Gara, nessun falso stallo durante pause/aggiornamenti. |
| **L2 · Obiettivo** | Baseline contro stallo/partenza, poi reward e gamma PPO a budget uguali. | Cinque seed per metodo, held-out e metriche separate; nessuna promozione di un pilota immobile. |
| **L3 · Integrazione** | Dossier/UI/contratti e qualifiche Solitario/Gara dello studio precedente. | Partenza robusta, giri validi e frenate/traffico conservati; prove board e tema prima della consegna. |

Casi indispensabili: auto a gas zero, freno da ferma, partenza tardiva entro/fuori grazia, guida lenta ma progressiva, zig-zag sullo stesso tratto, curva stretta, frenata da alta velocità, rivale fermo davanti, strada libera dietro il rivale, contatto e traguardo nello stesso tick, timeout/terminale nel rollout, pausa/stop/ripresa, popolazione con individui inattivi e Gara senza respawn.

Target iniziali **proposti**, da fissare prima dell'esperimento: ≥18/20 partenze valide da fermo per seed su tratti liberi; ridurre almeno del 50% la quota di episodi senza avanzamento rispetto alla baseline se non è già vicina a zero; detector zero falsi positivi nella suite deterministica di frenate/soste giustificate. Confermare poi validità dei giri e tempi su prove comuni. Non garantire assenza di regressioni con soli 20 campioni: riportare risultati per seed/scenario e incertezza.

Seed di qualifica indipendenti, almeno cinque seed di training per ciascun metodo che apprende, budget di passi **e** tempo CPU dichiarati. Pure Pursuit resta il controllo deterministico su scenari variati. Un reset più rapido aumenta il numero di partenze viste: registrare anche episodi e secondi simulati, evitando confronti soltanto per generazioni o aggiornamenti. Ripetere contro baseline Partenza senza detector per distinguere curriculum da semplice risparmio di calcolo.

**Preparazione completata:** specifica dei lotti, file/contratti, metriche, casi limite, compatibilità e prove analitiche pronte. Efficacia sui piloti esistenti e prestazioni board restano da dimostrare. L0–L2 precedono F1–F3 dello [studio precedente](game-racing-space-physics-sensors-study.md); L3 confluisce in F4. F0 grafico/griglie può procedere indipendentemente. Stato ufficiale nel [MasterPlan](release-masterplan.md).
