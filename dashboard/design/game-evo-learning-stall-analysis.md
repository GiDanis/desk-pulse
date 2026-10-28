# Evo · partenze, curve, stallo e decisione sul reset

**14 ottobre 2026 · Fotografia iniziale: analisi e prove private sulla 0.9.0-rc.15.**

**Seguito autorizzato:** implementazione e verifiche di Evo progressivo nella [rc.16](v09-evo-progressive-report.md). Il resto di questo documento conserva lo stato e le conclusioni dello studio iniziale. Il confronto successivo giustifica conservare i pesi e riavviare gli esercizi; non un reset generale della rosa.

Richiesta: capire perché i candidati sterzano/escono subito, vanno dritti in curva oppure rallentano fino a fermarsi; valutare se cancellare i vecchi progressi. Nessun reset, modifica al motore, allenamento originale, riavvio o installazione eseguiti in questo studio.

## 1. Decisione

**Autorizzazione successiva dell’utente:** durante questa fase di test è consentito cancellare la memoria dei piloti se necessario per far funzionare l’apprendimento. Il reset non richiede una nuova conferma; va applicato quando il confronto o le modifiche lo giustificano, indicando quali piloti e quali percorsi sono stati azzerati. Questa autorizzazione non è un ordine di resettare immediatamente tutta la rosa.

**Intervenire prima su curriculum, confronto dei candidati e conservazione delle abilità. Non resettare ora tutti i progressi.** Dopo gli interventi, confrontare una copia di Evo esistente, una inizializzata dalla sua memoria e una veramente nuova a budget/scenari uguali. Scegliere il percorso di ripartenza dai risultati; archiviare sempre quello attuale.

La prova congelata non dimostra che iniziare da zero sia migliore: **4 successi su 256** con la popolazione attuale, **0 su 256** con una appena inizializzata. Non confronta ancora l'efficacia di un riaddestramento prolungato. Non giustifica reset di NEAT/PPO/Clone o una cancellazione delle identità/storico.

Le stime precedenti di 100–500 generazioni erano budget indicativi, non tempi di convergenza misurati. Questa analisi usa finalmente un blocco di apprendimento reale; attendere un altro numero arbitrario di generazioni non risolve automaticamente il problema.

## 2. Stato realmente acquisito

[Sintesi del checkpoint](evidence/v09-evo-learning-stall-2026-10-14/snapshot.json). SQLite in sola lettura e artefatti immutabili della board; sessione Impara in pausa. Cinque moduli verificati SHA-256 contro il checkout: stessa implementazione. Hash corrente `7586f50569b33731739dbddc117c7f7554d52c28a4bdc4dbefb992d086456bed`; origine pre-bilanciamento `711e8058e49323580be2f60df17f7bd998057bd6db4e90299c697fce71c3990b`.

- Evo ha 32 candidati per generazione, rete 68→16→2, seed 1, mutazione nominale 0,15. Le 32 vetture non sono 32 generazioni.
- Passi complessivi 1.992.091; alla migrazione 1.569.172. **422.919 nuovi passi**, generazioni totali 125→156: **31 aggiornamenti nel nuovo protocollo**.
- Fase dichiarata Ingresso curva; pressione sul passo 0. Il limite di velocità del passo non è già stato aumentato dalla nuova progressione.
- **992 tentativi conclusi nella nuova epoca:** 800 di curva, 192 di ripasso Partenza. Curva: **0 arrivi**, 349 ritiri, 449 stalli e 2 timeout. Partenza: 9 successi e 183 stalli.
- Campioni pedale dei nuovi tentativi conclusi: **79,6% freno**, 15,8% gas, 4,6% rilascio. Percentuali di comandi, non forza/energia. Sono aggregate fra esercizi e velocità, non indicano frenate corrette.
- Le ultime sei verifiche non sono superate. Il formato grezzo 0/20 non significa che tutti i 20 siano stati eseguiti: il valutatore interrompe dopo tre fallimenti quando la soglia di accettazione è irraggiungibile. Tre verifiche hanno testato tre curve; tre hanno fallito prima nella Partenza, senza testare la curva.
- Il checkpoint fotografato contiene una nuova griglia ancora a età zero: **55,3 km/h iniziali**, tutti nello stesso scenario. Ingresso curva parte già in movimento; è distinto dalla Partenza da fermo.

I vecchi contatori sono cumulativi: 2.551 successi storici comprendono Rientro/Partenza e non dimostrano successo della curva attuale. I conteggi sopra sottraggono il checkpoint di origine, senza modificare il DB.

## 3. Prova congelata e risolvibilità

[Script riproducibile](evidence/v09-evo-learning-stall-2026-10-14/probe_frozen.py), [risultati completi](evidence/v09-evo-learning-stall-2026-10-14/frozen.json). PC, fisica e protocollo installati, otto scenari 0–7 accoppiati. Non vengono aggiornati pesi o fitness originali. Le copie fresche hanno lo stesso preset; non sono un nuovo pilota nella Dashboard.

| Controllore/popolazione congelata | Prove | Arrivi | Ritiri | Stalli | Progresso valido mediano |
| --- | ---: | ---: | ---: | ---: | ---: |
| Popolazione Evo attuale | 256 | 4 | 79 | 173 | 47,45 m |
| Popolazione Evo nuova | 256 | 0 | 213 | 43 | 24,58 m |
| Migliore/candidato Evo attuale | 8 ciascuno | 0 | 0 | 8 | 56,69 m |
| Migliore Evo pre-migrazione | 8 | 0 | 8 | 0 | 79,52 m |
| Memoria personale di guida | 8 | 0 | 6 | 0 | 134,61 m, con 2 esercizi falliti per pulizia |
| Riferimento geometrico | 8 | 8 | 0 | 0 | 140,05 m |
| Sterzo del riferimento + freno fisso | 8 | 0 | 0 | 8 | 11,94 m |
| Sterzo del riferimento + gas fisso | 8 | 0 | 8 | 0 | 67,54 m |
| Comandi nulli | 8 | 0 | 8 | 0 | 59,81 m |

I quattro successi della popolazione attuale appartengono a due candidati (7 e 21), nelle velocità iniziali inferiori/intermedie. Esiste quindi un segnale utile da conservare; il candidato globale salvato non è quello più generalizzabile sui casi del confronto.

Il riferimento risolve tutti gli otto ingressi, compresi quelli veloci. L'esercizio è fisicamente possibile. Questo non dimostra che una rete casuale o mutata riesca facilmente a scoprirlo, né esclude errori in altre condizioni fisiche.

Nessuna popolazione ha |sterzo iniziale|>0,8 nel confronto attuale; il vecchio migliore supera 0,8 in cinque degli otto casi. Le uscite attuali non richiedono necessariamente un comando quasi massimo: a velocità elevata basta un errore più piccolo mantenuto. Il freno del candidato attuale occupa mediamente il 75% dei campioni nei casi congelati.

## 4. Meccanismi trovati

### 4.1 La difficoltà salta fra scenari

`reset_episodes()` estrae un nuovo seed condiviso per i 32 candidati a ogni generazione. La condivisione è corretta per la parità all'interno di quel confronto. `bend_scenario()` cambia però ingresso e fattore di velocità indipendentemente dal successo raggiunto.

Nel [tracciato privato del scheduler](evidence/v09-evo-learning-stall-2026-10-14/schedule.json) gli ingressi passano fra circa **21,8 e 64,8 km/h**, alternati con il fermo della Partenza. Non esiste ancora una scala di difficoltà che prima stabilizzi una curva lenta e poi aumenti la velocità/distanza.

140 m richiedono approccio, curva e uscita in un'unica prova. Dal successo di Partenza/Rientro precedente si è passati a questo esercizio dopo la migrazione: conservare la rete non significa aver dimostrato quei compiti alla nuova velocità iniziale.

**Proposta:** rettilineo controllato → arco breve lento → ingresso/uscita → curva completa → giro, con velocità e distanza progressive. Mantenere la carreggiata realistica; non allargare artificialmente la pista. Promuovere difficoltà solo dopo validità su un insieme stabile di scenari riservati.

### 4.2 Fitness storico e seed differenti

`Evolution.update()` conserva `bestScore` finché il nuovo punteggio non lo supera. Il relativo genoma viene rimesso in popolazione anche quando il seed/scenario è cambiato. Il contesto include pista/fase/pressione, ma non l'insieme degli scenari o la difficoltà dell'ingresso.

Il confronto è equo fra le 32 reti di una generazione, ma il record numerico può provenire da un ingresso diverso. La normalizzazione delle unità non elimina questa variabilità. Il fatto che i candidati 7/21 riescano in alcuni casi e il globale si fermi in tutti gli otto è un motivo concreto per rivalutare l'aggregazione; non dimostra che vincere la generazione precedente fosse sbagliato nel suo specifico scenario.

**Proposta:** piccolo insieme stratificato di 2–4 scenari per generazione, identico per tutti; set distinto per promozione. Rivalutare l'elite nel contesto corrente; conservare record storici solo con insieme/versione dichiarati. Distinguere successo, progressione valida e tempo, evitando che un singolo seed facile decida il campione.

Costo: quattro scenari aumentano il lavoro circa quattro volte a parità di altre condizioni. Misurare sia transizioni sia valutazioni del candidato e tenere la preview separata; non promettere 32 copie a 1×.

### 4.3 Ripasso e stagnazione interferiscono

Ogni quinto aggiornamento in Impara, senza copertura su altre piste, tutti i candidati passano a Partenza. Il cambio di contesto chiama `change_reward()`, che azzera `bestScore`, stagnazione e scala di mutazione; avviene di nuovo tornando alla curva. Il singolo archivio `best` viene condiviso fra compiti.

Il tracciato diagnostico usa punteggi costanti, non è un allenamento reale: nonostante assenza di miglioramento, il contatore resta nel ciclo **0→1→2→3→0** e la scala non supera 1,15. Il meccanismo pensato per aumentare l'esplorazione dopo 20 generazioni stagnanti non può accumularle in questo percorso. Inoltre la selezione su Partenza può favorire una rete diversa dal miglior controllore di curva.

**Proposta:** archivi/contatori per esercizio e difficoltà, oppure fitness con componenti di retention esplicite. Ripassare Partenza senza sostituire il riferimento di curva; includerne il risultato nel verdetto del candidato. Dopo una serie di fallimenti reali, introdurre diversità dichiarata senza perdere le reti migliori. Non rimuovere il ripasso: le verifiche dimostrano che l'abilità di partire non è attualmente conservata dal candidato.

### 4.4 Fra i fallimenti conviene fermarsi

Nel confronto il riferimento completo ottiene punteggio di selezione mediano **+3,807**; il candidato che si ferma **−0,288**; il controllo con tutto gas **−3,180**. Il premio non preferisce lo stallo a una curva pulita. Preferisce però lo stallo a un incidente, e quest'ultimo è molto più frequente nelle varianti esplorate.

Con una curva intera ancora difficile da scoprire, l'evoluzione può migliorare evitando il peggior esito, senza imparare ad attraversarla. Il freno diffuso e i 632 stalli nella nuova epoca sono coerenti con questa spiegazione. Da soli non dimostrano che aumentare una penalità risolverebbe il problema.

**Proposta:** bilanciare le categorie di insuccesso sullo stesso compito, aggiungere traguardi di difficoltà progressiva, preservare il credito valido. Confrontare penalità di stallo e ritiro tramite comportamenti congelati e apprendimento a budget uguali. Escludere le attese legittime nel traffico. Nessun acceleratore minimo, freno automatico o premio per tenere il gas.

### 4.5 Mutazioni e inizializzazione

L'inizializzazione normalizza per ingressi/neuroni; la mutazione applica invece σ=0,15 assoluto a circa il 25% dei pesi. Sulla prima rete fresca campionata, la norma della perturbazione media è **2,49**, contro norma della rete **2,17**. Questo segnala una perturbazione grande rispetto a una rete iniziale, non prova da solo che tutte le variazioni siano dannose.

L'ablation diagnostica con σ per fan-in riduce la perturbazione a **0,319**. Sul genoma attuale, variazione media dello sterzo iniziale: 0,178 assoluta contro 0,037 normalizzata. Questi sono cambiamenti di azione su stati congelati, non tempi di convergenza. Mutazioni più piccole possono anche rallentare l'esplorazione.

I due candidati con bias pedale −1/−2 cambiano il pedale in tutte le situazioni; non insegnano quando frenare e quando ripartire. Il resto della rete deve scoprire quella dipendenza dagli ingressi.

**Proposta da verificare:** maggioranza di variazioni piccole, rare variazioni ampie/immigrati, scale distinte per strato/uscita e perturbazione effettiva misurata sul comportamento. Esplorazione del pedale in entrambi i sensi. Inizializzazione con uscite più contenute da confrontare, conservando tutti i parametri e la versione del metodo nel dossier. Ogni candidato continua a guidare con la propria rete; nessun maestro nascosto per Evo.

### 4.6 UI e statistiche

Separare contatori della nuova epoca/fase dai totali storici. Esporre in poche righe: esercizio/difficoltà, generazione della fase, velocità iniziale, arrivi/ritiri/stalli recenti e progresso valido tipico. I tempi di esercizio non diventano tempi di giro; una verifica cancellata indica quali compiti siano stati effettivamente provati.

La distribuzione dei pedali è diagnostica: molte frenate non certificano controllo. Non cambiare la grafica Apple Calm, non aggiungere testo permanente che riduca la pista. Dettagli nel dossier, stato breve nella vista.

## 5. Cosa significa reset nel sistema attuale

| Azione | Effetto | Riparte veramente da pesi casuali? |
| --- | --- | --- |
| Reset del percorso/esercizio attivo | Toglie il checkpoint locale; identità e storico restano. | **Non necessariamente:** il successivo Start può importare la memoria personale compatibile. |
| Reset completo del singolo pilota | Azzera percorsi, obiettivi, qualifiche e memoria; mantiene l'identità, registra l'evento e conserva gli artefatti immutabili/storico. | Sì, per l'apprendimento di Evo; la memoria marcata reset non viene ricostruita dai vecchi percorsi. |
| Reset di tutta la rosa | Coinvolgerebbe gli altri paradigmi. | Fuori dal bisogno diagnosticato; nessuna evidenza per consigliarlo. |

**Scelta raccomandata ora:** conservare Evo. Dopo le correzioni, provare su copie: pesi attuali, migliore memoria personale e rete nuova. Un reset completo di Evo diventa sensato solo se il nuovo percorso risulta più robusto; un reset del curriculum mantenendo le abilità utili può essere preferibile. Rendere queste scelte distinguibili nel menu prima di proporre un'azione sulla produzione.

## 6. Piano concreto del seguito

| Ordine | Lavoro del seguito tecnico | Verifica |
| --- | --- | --- |
| 1 | Contatori per epoca/esercizio e snapshot della diagnosi; archiviare l'Evo attuale. | Niente modifica agli originali; cause/compiti provati espliciti. |
| 2 | Scheduler per difficoltà e ripasso che conserva elite/contatori del compito. | Stagnazione non cancellata artificialmente; Partenza conservata; stesso seed bank per confronto. |
| 3 | Scenari stratificati e fitness/elite rivalutati nel proprio contesto. | Nessuna comparazione fra record di condizioni diverse; promozione su scenari separati. |
| 4 | Ablation stallo/ritiro e scale di mutazione, mantenendo Evo puro. | Successi/giri puliti crescono, non soltanto frenate o punti; meno danno a genomi utili. |
| 5 | Warm attuale / memoria / cold su copie, almeno tre seed per screening, stessi budget e scenari; poi cinque seed per qualifica estesa. | Curve e Partenza valutate entrambe; dispersione, capacità e tempo pulito riportati. |
| 6 | Scelta fra continuazione, riavvio del curriculum o reset completo del solo Evo; UX coerente. | Azione concreta documentata, archivio/rollback e storico conservati. Nessuna migrazione o reset impliciti. |

La prova iniziale deve fermarsi su un budget definito, per esempio 250.000 transizioni per condizione/seed nello screening, distinguendo costo degli scenari e fasi; è un budget di confronto, non una previsione che a quel punto Evo saprà guidare. Non ridurre il carico solo per ottenere un verdetto positivo.

## 7. Fonti e limiti

- [Such et al., Deep Neuroevolution](https://arxiv.org/abs/1712.06567): algoritmi genetici per reti; esempi in cui reward e esplorazione possono non trovare la strategia desiderata. Non fornisce una soglia di generazioni per il nostro Evo.
- [Florensa et al., Reverse Curriculum Generation](https://arxiv.org/abs/1707.05300): distribuzione degli stati iniziali come parte del curriculum. Trasposizione proposta al nostro simulatore, non prova diretta della specifica sequenza di curve.
- [Segal e Sipper, Adaptive Combination of a Genetic Algorithm and Novelty Search](https://arxiv.org/abs/2209.03618): gestione di esplorazione in reward sparse/ingannevoli. Eventuale novità/archivio resta sperimentale; non dichiarato necessario prima delle correzioni concrete del scheduler.

Uno snapshot reale, una pista, due popolazioni congelate e otto scenari: non è un confronto di convergenza multi-seed, né una prova di tutti i paradigmi o circuiti. Il riferimento viene usato come controllo diagnostico e non entra nelle azioni di Evo. Tutte le modifiche proposte sono ancora analisi; runtime e dati originali rimangono invariati.
