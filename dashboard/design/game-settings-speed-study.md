# Gioco — impostazioni comprensibili e miglioramento del tempo sul giro

**Nuovo studio UX/circuiti, 11 ottobre:** [impostazioni Apple Calm e secondo circuito](game-settings-circuits-ux-study.md). Analisi delle sezioni, bozza/focus e geometria condivisa, con concept offline; nessun nuovo runtime consegnato.

**Aggiornamento rc.6:** [vista Pilota e dossier](v09-pilot-dossier-report.md), durata/sessioni/profili/risultati e reset confermato con storico conservato; API 2.9, 68 superfici.

**Aggiornamento rc.5:** [Gara e guida PPO](v09-race-ppo-report.md): una vettura per pilota, reti salvate congelate, 3/5/10 giri e dimostrazione PPO distinta dai tentativi di apprendimento.

11 ottobre 2026 · revisione 2 · approfondimento della famiglia v0.9.x.

**Stato aggiornato: implementazione autorizzata e candidata 0.9.0-rc.6 installata.** Ottimizzazioni della fisica/sensori e consegna scene nella [rc.4](v09-game-performance-report.md). Menu senza legenda, descrizioni/valore distinti, Controllo/Passo, campione verificato, valutazioni riprendibili e Progressi dei tempi consegnati; [report e limiti delle prove](v09-game-settings-pace-report.md). Il testo seguente conserva la specifica e l'ispezione iniziale della rc.2, quando questo documento era analisi dei prossimi passi. La tabella della sezione 2 descrive quella baseline, non il runtime attuale. Taratura, competenza traffico/PPO/NEAT e gate fisici restano aperti nel [MasterPlan revisione 2.57](release-masterplan.md).

## 1. Risultato da ottenere

1. Impostazioni Gioco senza legenda permanente dei tasti in basso.
2. Ogni parametro comprensibile: titolo evidente, spiegazione breve secondaria e valore ben distinto.
3. Piloti che prima imparano a completare il giro e poi cercano tempi migliori, mantenendo la capacità di arrivare.
4. Progressi verificabili e persistenti; il miglioramento non è garantito a ogni tentativo o generazione.

Il percorso continua a riguardare un solo pilota selezionato. Gara usa reti congelate; aprire una schermata non avvia allenamento o valutazione.

## 2. Riscontro sul codice attuale

| Punto | Comportamento rilevato | Conseguenza per il prossimo intervento |
| --- | --- | --- |
| Menu | `Main.qml`, `gameMenuRows()`: `title` e `detail`; quest'ultimo contiene soprattutto il valore. | Aggiungere una descrizione distinta dal valore. |
| Disegno | `GameVisual.qml`: cinque righe da 72 px, passo 82 px, titolo 24 px e dettaglio 19 px, moltiplicati per la scala del tema. | La terza informazione richiede una nuova distribuzione interna, non un testo aggiunto alla riga esistente. |
| Fondo menu | Testo fisso «2/8 scegli · 4/6 modifica · 5 conferma · 7 torna». | Eliminare questa legenda nella sola presentazione del menu Gioco. |
| Reward | `game_simulation.py`, `World.step()`: progresso, giro completato, contatti, tempo e sterzo. | Esiste pressione implicita sulla velocità, ma non una fase progressiva qualificata. |
| Evoluzione / NEAT | Selezione tramite fitness del training; il migliore storico è conservato dai backend. | Una fitness ottenuta da un'altra partenza o fase non è una verifica comparabile del campione. |
| PPO | Il modello salvato è l'attore corrente. | Serve distinguere checkpoint per continuare e campione verificato per correre. |
| Progressi | Fitness del training oppure errore del valutatore PPO. | Queste curve non dimostrano direttamente un miglioramento del tempo sul giro. |

Le prove Evoluzione esistenti dimostrano completamento sull'ovale: 23/25 giri indipendenti su cinque seed. Non dimostrano ancora un miglioramento progressivo dei tempi né competenza nel traffico. Le prove PC, i profili nativi e i gate residui conservano lo stato riportato nel report.

## 3. Impostazioni: composizione proposta

### 3.1 Legenda e messaggi

Rimuovere la legenda permanente dal menu Gioco e recuperare la sua fascia di circa 46 px. Conservare i comandi effettivi, il focus, il ritorno e il riferimento generale Comandi. Start/Pausa e il loro feedback restano disponibili in Pista. La rimozione non deve cancellare messaggi di stato o errore: il menu dispone già della fascia superiore per questi esiti.

### 3.2 Titolo, descrizione, valore

Esempio di contenuto della riga:

```text
Popolazione                                      32
Reti candidate valutate per ogni generazione.
```

- Titolo in `textPrimary`, famiglia tipografica del tema, circa 24 px alla scala 1.0.
- Descrizione in `textSecondary`, circa 19 px: grigio coerente con il tema, senza colore fisso o opacità aggiuntiva che riduca il contrasto.
- Valore nella colonna destra, leggibile e allineato; numeri con la famiglia numerica del tema. Focus tramite il bordo/accento già previsto.
- Margini, superfici e raggi derivati dallo stile corrente di Base, Functional e Apple Calm.
- Risoluzione di riferimento **960×640, 3,5″ orizzontale**. La modifica riguarda il menu e preserva l'arena 912×496 della pista.

Proposta geometrica da verificare nel renderer: header compatto di circa 104 px nel contenuto del menu; cinque righe con passo circa 88 px se le descrizioni occupano una riga. Con scala 1.1 o testi su due righe, quattro righe con passo circa 112 px e paginazione coerente con la selezione. Il contenuto del menu con margini attuali è 896×576: entrambi i candidati richiedono una verifica delle misure effettive del font. Calcolare insieme indice iniziale, numero di righe e loro altezza; nessun elemento selezionato fuori schermo o salto della selezione cambiando scala.

Preferire descrizioni concise e un massimo di due righe. Non ridurre ulteriormente il font per far entrare tutto; evitare troncamenti del significato e sovrapposizioni con il valore. La scala del tema si applica a tutti e tre gli elementi.

### 3.3 Testi candidati e significato reale

| Parametro | Descrizione breve proposta | Precisazione per lo studio/implementazione |
| --- | --- | --- |
| Modalità | Scegli allenamento, gara o prova del modello salvato. | Adattare il testo alla scelta; Campione osserva la politica salvata. |
| Pilota | Identità con rete, allenamento e risultati propri. | Nessuna confusione con i tentativi interni alla popolazione. |
| Metodo | Come il pilota modifica la propria rete. | Evoluzione, PPO, NEAT; mantenere l'etichetta sperimentale pertinente. |
| Popolazione | Reti candidate valutate per ogni generazione. | Evoluzione/NEAT: più tentativi, maggiore lavoro; non equivale a più piloti in Gara. |
| Copie ambiente | Tentativi paralleli dello stesso pilota. | PPO: stessa rete, ambienti indipendenti; non reti diverse. |
| Mutazione | Intensità delle modifiche ai pesi della rete. | Evoluzione: deviazione standard del rumore; maschera di probabilità 25% separata e attualmente fissa. NEAT: ampiezza di mutazione di pesi e bias; probabilità e mutazioni strutturali sono nella configurazione. Non mostrare 0,15 come «15% di mutazioni». |
| Neuroni nascosti | Dimensione dello strato interno della rete. | Evoluzione/PPO: più capacità e calcolo, senza garanzia di guida migliore. NEAT crea la struttura durante l'evoluzione: questa voce resta assente. |
| Seme iniziale | Punto di partenza casuale dell'allenamento. | Utile per ripetere esperimenti; la riproduzione richiede anche profilo, versioni e checkpoint/RNG compatibili. |
| Limite tentativo | Durata massima di ogni prova di guida. | Tempo simulato, non durata della sessione dell'utente. Un limite troppo corto può impedire il primo giro completo. |
| Allenamento | Da solo o con un avversario fisso. | La candidata ha un bot a velocità obiettivo 7 m/s; non insegna automaticamente la Gara contro ogni pilota. |
| Learning rate | Ampiezza degli aggiornamenti della rete. | PPO: un valore alto può rendere instabile l'apprendimento; non promettere che sia più veloce. Valutare il titolo italiano «Passo di apprendimento». |
| Rollout | Passi raccolti per copia prima di un aggiornamento. | PPO: 256 passi a 60 Hz sono circa 4,27 s simulati per copia; 32 copie producono 8.192 transizioni. È diverso dal limite del tentativo. |
| Epoche | Passaggi di apprendimento sugli stessi dati. | PPO: più passaggi aumentano il costo e possono peggiorare la generalizzazione. |
| Sconto ricompense | Quanto pesano i risultati più lontani nel tempo. | PPO: vicino a 1 considera maggiormente il futuro. A 60 Hz, gamma 0,995 ha scala indicativa 1/(1−gamma) di 200 passi, circa 3,33 s; non è un orizzonte rigido, GAE usa anche lambda. |
| Nuovo pilota | Crea un'identità con un allenamento indipendente. | Conservare l'identità del pilota precedente. |
| Partecipante | Includi questo modello salvato nella sessione. | Presente quando la modalità richiede la selezione dei partecipanti. |
| Start | Avvia la modalità scelta con questi parametri. | Descrizione contestuale; feedback reale se non avviabile. |

Le descrizioni sono informazione, non nuovi controlli. Visibilità e significato seguono il backend selezionato. Valutare in seguito preset comprensibili («Primi giri», «Migliora il tempo») prima di esporre ulteriori coefficienti di reward; non aggiungere subito decine di opzioni.

### 3.4 Contratto e compatibilità

Il `GameContext` corrente espone `rows` come array di `legacyMap`. Proporre campi additivi `description` e `value`, mantenendo `detail` per presentazioni precedenti. Produrre i testi nel modello delle righe, così temi e fallback ricevono lo stesso significato. Aggiornare fixture, reference e kit al momento dell'implementazione; un cambiamento incompatibile richiederà la relativa versione del contratto. I bundle importati rimangono immutabili.

## 4. Velocità: cosa viene premiato oggi

Ricompensa attuale, per sottopasso di durata `h`:

```text
r = avanzamento/10 + 10·giro_finito − 5·contatto
    − 0,02·h·attivo − 0,005·h·attivo·|sterzo|
```

L'avanzamento è firmato e i checkpoint del giro sono sequenziali. Sullo stesso giro completo, il contributo di avanzamento è sostanzialmente uguale tra piloti; arrivare dieci secondi prima risparmia circa **0,2 punti** della penalità temporale. PPO sconta inoltre le ricompense future. Il training di produzione continua fino a pausa/uscita o condizioni di arresto: il completamento del primo giro non attiva una nuova fase di velocità.

Quindi l'incentivo esiste, ma può risultare debole rispetto agli altri termini. La penalità sul valore assoluto dello sterzo non misura specificamente lo zig-zag: curva necessaria e oscillazioni vanno distinte nello studio. Premiare solo la velocità istantanea rischia di favorire accelerazioni che terminano fuori pista. L'obiettivo di prodotto deve essere **ridurre il tempo di giri validi con affidabilità mantenuta**, entro potenza, frenata e aderenza della vettura.

## 5. Percorso candidato: controllo → passo → traffico

| Fase | Apprendimento desiderato | Verifica per avanzare |
| --- | --- | --- |
| **Controllo** | Avanzare nella direzione corretta, rimanere in pista e completare un giro. | Prima affidabilità su partenze variate; esempio da tarare: almeno 9/10 giri validi in due finestre indipendenti. |
| **Passo** | Accelerare sul rettilineo, gestire curva/frenata e scegliere una traiettoria efficace. | Tempi mediani migliori su prove comuni, senza perdere l'affidabilità richiesta. |
| **Traffico** | Mantenere passo e controllo con altri veicoli, evitare contatti e imparare il sorpasso. | Scenari di traffico variati e infine Gara 2/4 con modelli congelati competenti. |

Le soglie sono proposte sperimentali, non gate già superati. L'avversario fisso attualmente selezionabile è un punto di partenza del traffico; non esiste ancora questa progressione automatica. Conservare anche prove in solitario durante il traffico per verificare regressioni.

### 5.1 Ricompensa e selezione da confrontare

1. Baseline attuale invariata, come controllo.
2. Penalità temporale normalizzata rispetto a una scala di tempo di riferimento fissata per configurazione; peso più rilevante nella fase Passo, con transizione graduale.
3. Bonus limitato per giro valido veloce, ad esempio proporzionale a `clip(1−T/T_ref, 0, 1)`, insieme al progresso utile ai tentativi iniziali. Il riferimento non dipende dal record della generazione corrente.
4. Penalità per variazioni eccessive dello sterzo, da confrontare con il termine attuale senza impedire le curve necessarie. Non imporre di seguire sempre il centro: una traiettoria migliore può usare la larghezza della pista.

Coefficienti e transizione vanno tarati su esperimenti; il confronto deve isolare un cambiamento alla volta. Per Evoluzione/NEAT separare fitness di training e regola di promozione. Per PPO il ritorno scontato rimane parte dell'ottimizzazione, mentre il campione si promuove con valutazione indipendente. Se cambia la scala del reward, i `bestScore` storici non vanno confrontati numericamente con quelli della nuova fase.

## 6. Campione affidabile, persistenza e UI

- Conservare due ruoli: **candidato in allenamento** e **campione verificato**. I checkpoint attuali continuano a servire per riprendere, ma non costituiscono da soli una promozione indipendente.
- Valutare candidato e campione su condizioni uguali, con reti congelate; promuovere se l'affidabilità supera la soglia e il tempo mediano migliora oltre una tolleranza fissata prima della prova. Gestire esplicitamente il passaggio iniziale da nessun campione a un primo modello affidabile.
- Prova proposta da 10 scenari: utile per scegliere il candidato, ma non sufficiente per concludere una robustezza statistica generale. Usare scenari ulteriori mai utilizzati per scegliere il vincitore nella qualifica finale, per evitare adattamento al solo insieme di selezione.
- Salvare fase, coefficienti/versione del reward, RNG, criteri/versione di valutazione, hash del candidato e campione, configurazione fisica e osservazioni. Migrare i vecchi piloti come percorso legacy, senza inventare una fase già raggiunta.
- Al cambio fase terminare il tentativo corrente; per PPO completare/scartare esplicitamente il rollout della vecchia fase ed evitare minibatch con reward di versioni diverse. Decidere e documentare reset/adattamento del critico. Per Evoluzione/NEAT rivalutare gli élite con il nuovo criterio.
- Aggiornare in modo atomico il campione promosso e la prova che giustifica la promozione; preservare il campione precedente se il processo si interrompe.
- In **Progressi** proporre fase, giri validi/totali, tempo mediano e miglior giro verificato, confrontati con il campione iniziale del percorso. Fitness/loss restano eventualmente diagnostici, senza descriverli come velocità.
- In **Pista** usare solo un'indicazione breve di fase; niente nuova colonna o fascia che riduca l'arena.
- In **Classifica** confrontare stessi circuito, veicolo, gomme, fondo, condizioni, regole e versione della fisica. I punteggi di training di algoritmi/fasi diverse non stabiliscono la graduatoria.

Non promettere progresso monotono del training: i candidati possono peggiorare o raggiungere un plateau. Il campione resta disponibile e si sostituisce solo secondo prove comparabili. Mutazione adattiva, stagnazione e riavvii controllati sono idee successive, da studiare dopo la baseline; nessun cambio silenzioso dei parametri scelti dall'utente.

## 7. Fattibilità e costi sulla board

La proposta usa ambiente numerico e reti già presenti. Descrizioni e menu non richiedono servizi esterni. Fasi, metriche e promozione aggiungono logica/persistenza; il costo principale è la valutazione di più giri. Schedularla a intervalli di generazioni/aggiornamenti da misurare, interrompibile e nel processo dedicato dopo Start, con una quota del budget dichiarata. Non lanciarla all'apertura di Classifica o automaticamente al boot.

CPU rimane il backend scelto per la rete iniziale dopo il confronto acquisito. Un nuovo reward non richiede la NPU; l'eventuale crescita della rete richiederà un nuovo confronto. RAM disponibile utilizzabile secondo l'indicazione dell'utente, senza tetti artificiali; restano da misurare CPU, temperatura, pause e fluidità del render. Aumentare il ritmo del training non equivale a far migliorare il pilota.

## 8. Esperimenti e criteri di accettazione

**Impostazioni:** assenza della legenda, descrizioni semanticamente corrette, valore sempre leggibile, nessuna sovrapposizione; Base/Functional/Apple Calm, scala 1/1,1, focus e paginazione, profili Evoluzione/PPO/NEAT, errori/Start e prova fisica a 50–60 cm. Non cambiare cattura/rilascio dei tasti durante la simulazione.

**Apprendimento:** almeno cinque seed di training per ciascun confronto, budget per transizioni e tempo attivo registrati, valutazione deterministica con partenze comuni; conservare dati grezzi, versioni e hash. Separare selezione e scenari finali di verifica. Confrontare giri validi/totali, mediana e dispersione dei tempi validi, migliore giro, contatti/uscite, passi, tempo di training e costo delle valutazioni. Pubblicare anche tentativi falliti: la sola mediana dei sopravvissuti favorirebbe piloti veloci ma inaffidabili.

Un esito positivo richiede miglioramento di tempo rispetto alla baseline dello stesso pilota/configurazione e affidabilità mantenuta; ripetibilità tra seed, non un unico giro fortunato. PPO/NEAT mantengono gate propri. Verificare exploit: taglio curva, attraversamenti del traguardo, oscillazione sui checkpoint, retromarcia e contatti ad alta velocità.

**Persistenza/lifecycle:** pausa e riavvio durante training, valutazione e promozione; stesso pilota/fase e campione recuperabili, nessuna ripresa implicita, provenienza dei risultati corretta. La nuova composizione e il costo delle prove richiedono verifiche mirate native; le prove storiche non vengono ripetute senza nuovo rischio.

## 9. Prossimi passi nel piano ufficiale

| Ordine | Lavoro proposto | Uscita concreta |
| --- | --- | --- |
| 1 | Rifinitura impostazioni, descrizioni e compatibilità dei temi. | Menu più leggibile e verificato sulla risoluzione reale. |
| 2 | Strumentazione dei tempi/validità e baseline continuata dopo i primi giri. | Misura di quanto la ricompensa attuale migliora davvero il passo. |
| 3 | Studio sperimentale Controllo/Passo, promozione campione e migrazione. | Scelta motivata di reward/soglie, dati su cinque seed e salvataggi compatibili. |
| 4 | Estendere la qualifica al traffico e ai backend sperimentali. | Evidenze di competenza prima della Gara 2/4; nessuna chiusura anticipata dei gate. |

**Esito della pianificazione:** passi 1–3 implementati nella **0.9.0-rc.3**: menu descritto, misure dei tempi, progressione Controllo/Passo e promozione del campione. Confronti su cinque seed e con reward precedente acquisiti, ma coefficienti ancora sperimentali e robustezza ulteriore aperta. Il passo 4 mantiene la qualifica di traffico e algoritmi sperimentali aperta; nuove penalità/preset/mutazione adattiva sono evoluzioni successive. **Compagno v0.10 e Memoria v0.11** conservano la sequenza. Restano profili ampliati, lettura/input fisico, uso finale prolungato e frame pacing. Gli esiti reali prevalgono sulle soglie e geometrie candidate dello studio.

## 10. Riferimenti consultati

- Sorgenti locali: [menu](../Main.qml), [presentazione](../presentations/GameVisual.qml), [fisica/reward](../game_simulation.py), [Evoluzione/PPO](../game_learning.py), [NEAT](../game_neat.py), [worker](../game_worker.py), [persistenza](../game_store.py) e [contratto](../theme-api/contexts.json), ispezionati l'11 ottobre 2026.
- [Narvekar et al., Curriculum Learning for Reinforcement Learning Domains](https://arxiv.org/abs/2003.04960), 2020: inquadra l'ordinamento dei compiti e le decisioni di trasferimento tra fasi. Il percorso Controllo/Passo/Traffico qui proposto è una scelta da sperimentare su SmartPC, non un risultato del paper.
- [Documentazione ufficiale DeepRacer on AWS, Create a model](https://docs.aws.amazon.com/solutions/latest/deepracer-on-aws/create-a-model.html), consultata l'11 ottobre 2026: distingue time trial e ostacoli e descrive il compromesso velocità/controllo e valutazioni ripetute. È un riferimento di progettazione; SmartPC usa sensori numerici e il proprio motore, non questo servizio.

## 10. Controllo prestazioni e pilota prudente — 11 ottobre 2026

La segnalazione di vetture lente richiede tre misure separate: secondi simulati per secondo reale, velocità fisica in km/h e avanzamento del training/valutazione. Il candidato NEAT dell’utente, popolazione 8, è ancora in Controllo: una prova privata di dieci secondi simulati su dieci partenze mostra circa 6,25 km/h medi, includendo vetture ferme/ritirate. Questo non certifica una difficoltà della NPU. La [verifica prestazioni](v09-game-performance-report.md) documenta profilazione e ottimizzazioni compatibili con i checkpoint.

Prossimo studio di apprendimento: confrontare più seed NEAT con popolazioni 8/16/32, distinguere auto ferme da guida prudente e misurare tempo alla prima qualifica. In Controllo il costo temporale è 0,02/s e l’urto costa 5: sessanta secondi senza progresso costano circa 1,2, quindi nella fase iniziale fermarsi può essere favorito rispetto a un tentativo molto breve che termina in incidente. Valutare terminazione per assenza prolungata di progresso, esplorazione e stagnazione con prove abbinate; una terminazione deve avere una conseguenza esplicita, per non premiare episodi più brevi senza progresso. Versionare ogni cambio di obiettivo e preservare campioni/profili esistenti. Nessuna accelerazione artificiale dell’auto e nessuna promessa di miglioramento monotono.

Nel confronto PPO verificare anche il tempo del singolo episodio dopo `reset_trials`: l’orologio comune del mondo continua e il bonus terminale sul tempo oggi lo usa. Separare l’età della prova dal tempo della sessione richiede una modifica versionata e checkpoint compatibili; non confondere tale verifica con l’ottimizzazione numericamente equivalente del motore.
