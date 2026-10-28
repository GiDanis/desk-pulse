# Gioco — modalità, qualifica, allenamento continuo e risultati comprensibili

**13 ottobre 2026 · analisi e piano, nessuna implementazione/distribuzione.** Baseline letta sulla scheda: **0.9.0-rc.13**, servizio attivo; NEAT in allenamento sull’Ovale. Lo studio integra la richiesta dell’utente e lo [studio della fluidità](game-frame-pacing-study.md). Le decisioni di prodotto richieste entrano nel seguito v0.9.x; i dettagli proposti sono da verificare prima della consegna. [Evidenze salvate in sola lettura](evidence/v09-session-modes-results-study-2026-10-13/saved-state.json).

## 1. Problemi riscontrati

| Punto | Stato nel codice/dato salvato | Intervento necessario |
| --- | --- | --- |
| Modalità | `impara`, `gara`, `prova`, `campione`, duplicate fra service, worker, impostazioni e renderer. Prova può valutare più piloti in sequenza; Campione osserva un modello senza allenarlo. | Cinque modalità esplicite, con contratto comune e impostazioni pertinenti. |
| «20/20 valide · 4,91 s» | Nei dati Evo è la valutazione **21, Rientro**, 20 successi su 20, mediana **4,908333 s**, migliore 4,833333 s, obiettivo **40 m**. Nella stessa verifica: Partenza 20/20; Controllo 0 successi, **3 eseguite su 20**, 17 non eseguite. | Mostrare esercizio, distanza, tempo tipico, prove eseguite/non eseguite e verdetto complessivo. Un rientro riuscito non prova un giro completo. |
| Riassunto dei risultati | `game_dossier.py` usa «Valutazione» e la sola coppia validi/totale con mediana; non porta i dettagli dell’esercizio. Progressi mostra i tempi senza rendere visibili tutti i prerequisiti. | Risultati per compito e distinzione fra progresso, verifica tecnica e qualifica cronometrata. |
| Velocità percepita | I km/h sono lo stato longitudinale del modello fisico; i tentativi Evo/NEAT avanzano a turno. I 30 Hz di presentazione non equivalgono a 60 passi reali/s per ciascun mondo. | Osservazione del pilota a 1× e rapporto tempo simulato/reale esplicito nella vista dei tentativi. |
| Tentativo concluso | `completed` può essere vero mentre `World.rows()` conserva velocità e stato «in corsa» dell’ultimo passo fisico; il renderer mostra comunque i km/h. | «Tentativo concluso · ultima velocità…», senza presentarla come velocità corrente. Stesso trattamento per pausa e arrivo. |
| Accesso alla gara | Percorso moderno: certificati interni Solitario e Gara 2/4, almeno 18/20 scenari di tre giri. Eccezioni per riferimento geometrico e modelli legacy dell’Ovale. | Accesso di tutti i piloti basato almeno su **un giro valido di Qualifica**, con versione e contesto verificati. |
| Modello da qualificare | I nuovi pesi salvati sono spesso in `candidate`; `policy` può essere il vecchio campione o il percorso precedente. Prova/Gara oggi richiedono `policy`. | Qualifica deve poter misurare il candidato salvato attuale, senza richiedere una certificazione di gara precedente. |
| Griglia | L’ordine degli ID selezionati determina la griglia; non esiste ordinamento per un tempo ufficiale di qualifica. | Opzioni «Più veloce davanti» e «Più lento davanti», basate sui tempi della versione effettivamente schierata. |
| Allenamento continuo | Compiti con distanza, giri e limite finiti; il mondo termina al numero di giri previsto. Sorpasso attuale è un esercizio di 200 m, non un inseguimento continuo. | Obiettivi e finestre di apprendimento nuovi, senza chiusura automatica al primo giro. |

La verifica salvata Evo **non dimostra che il pilota sappia già completare un giro**. L’ultima valutazione disponibile è inoltre diversa da quella segnalata: Rientro 10 successi su 10 eseguiti, su 20 previsti, con Controllo fallito dopo 3 tentativi. Non si attribuiscono successi alle prove non eseguite. L’allenamento NEAT in corso ha dati non ancora salvati: il file dell’audit non è una lettura delle posizioni live.

## 2. Cinque modalità richieste

| Modalità | Piloti e auto | Apprendimento e fine sessione | Risultati mostrati |
| --- | --- | --- | --- |
| **Impara** | Un pilota persistente; nessun altro pilota della rosa viene allenato. Evo/NEAT mantengono le proprie copie candidate. | Preparazione iniziale e obiettivo di **un giro completo**; dopo affidabilità, miglioramento del passo. Ogni tentativo termina al giro, all’incidente/stallo; la sessione continua fino a Pausa. Gli esercizi iniziali sono nominati, non conteggiati come giri. | Giri riusciti/tentativi, tempo del giro, progresso, causa di interruzione, migliore candidato e andamento. |
| **Qualifica** | Un pilota, una sola auto, senza bot. | Modello salvato congelato: cerca il proprio miglior giro senza aggiornare i pesi durante la misura. Proposta: un giro di lancio e tre cronometrati; basta **un giro valido** per il requisito minimo. | Miglior giro valido, elenco dei giri, motivi di invalidazione, V max, versione misurata. |
| **Gara** | Da 2 a 4 piloti scelti, un’auto per pilota, modelli congelati. | Griglia da qualifica, 3/5/10 giri già disponibili, nessun respawn degli incidentati. Tutte le auto rimangono visibili. | Posizione, giri/distacco, arrivi/ritiri, giro migliore pulito, V max. |
| **Impara giro infinito** | Un pilota; osservazione principale di una sua auto, copie di apprendimento secondo il paradigma. | Continua oltre i traguardi, fino a incidente grave o stallo non risolto; una nuova prova può ripartire con motivo visibile. Il completamento di un giro non chiude il mondo. Pausa conserva il checkpoint. | Giri consecutivi puliti, distanza senza incidente, durata, miglior serie e progressi. |
| **Impara sorpasso** | Un pilota che apprende e **bot dichiarati**, congelati. Proposta iniziale: 1–2 bot, fino a 3 entro i sensori attuali. | Circolazione continua; apprendimento di avvicinamento, scelta traiettoria e sorpasso. Solo il pilota scelto modifica la rete. | Sorpassi tentati/riusciti/puliti, contatti, distanza/giri senza incidente, contesto dei bot. |

«Un pilota» indica un’identità persistente: 32 candidati Evo non sono 32 piloti da schierare. **Metodo, popolazione, mutazione e struttura della rete restano quelli del pilota**; cambiano obiettivo e scenario. Pure Pursuit è un riferimento deterministico: può qualificarsi e gareggiare, ma le tre modalità Impara sono disabilitate con spiegazione, senza trasformare silenziosamente la modalità in Campione.

Qualifica è il momento di misura. L’apprendimento per andare più veloce avviene in Impara: prima completare giri, poi ridurre il tempo mantenendo sicurezza/validità. Una qualifica che cambia i pesi durante i giri non identifica chiaramente il modello misurato; l’uso di un modello congelato è la scelta proposta.

## 3. Qualifica e requisito per la gara

### 3.1 Regole proposte

1. Selezionare il **candidato attuale salvato** o una versione già qualificata, con provenienza chiara. Non richiedere il vecchio `policy` certificato per poter tentare la prima Qualifica. Se necessario, attendere Pausa/Salvato prima di congelare la versione.
2. Usare la configurazione fisica corrente compatibile: circuito/geometria, vettura, gomme, fondo/condizione, regole e schema dei controlli. Nessun adattamento silenzioso di reti legacy alla nuova fisica.
3. Un giro di lancio non entra nel tempo ufficiale. Proposta iniziale: tre giri cronometrati, senza traffico, seed/protocollo registrati, inferenza deterministica dove prevista dal metodo.
4. Giro valido: sequenza completa dei checkpoint e traguardo, nessuna scorciatoia, uscita dai limiti o contatto nel giro; tempo misurato dalla telemetria dei passaggi, non FPS/mediana di un esercizio. Un giro è sufficiente; nessun limite percentuale rispetto al più veloce è richiesto.
5. Salvare ogni giro valido completato atomicamente. Interrompere la sessione successivamente non cancella quel giro; pausa/errore non trasformano un giro parziale in risultato. Questa regola è specifica della Qualifica: i record delle altre modalità conservano la propria provenienza.
6. Un candidato senza giro valido è «Da qualificare». Dettaglio: «Nessun giro completato», «Giro invalidato: fuori pista», «Modello incompatibile», ecc. Il tempo resta assente, mai zero.

### 3.2 Modello che entra in gara

La selezione schiera uno **snapshot qualificato**, non una rete che continua a mutare. L’hash della policy usata in gara deve coincidere con quello cui appartiene il tempo di griglia.

L’allenamento successivo non distrugge la versione qualificata: il nuovo candidato può essere più forte, ma finché non supera Qualifica non eredita il tempo del precedente. La rosa distingue «Versione qualificata disponibile» e «Candidato attuale da qualificare»; il menu deve dire quale versione schiera. Un nuovo circuito/auto/fondo richiede un tempo per quel contesto, anche se la conoscenza di guida viene riusata.

I certificati interni di traffico rimangono metriche di preparazione, da esporre separatamente. **Scelta proposta per il gioco:** il requisito operativo è un giro di Qualifica valido; non aggiungere al nuovo ingresso il blocco nascosto dei vecchi 18/20 Gara 2/4. Mostrare comunque «Traffico da allenare» quando manca esperienza. Neppure il riferimento Pure Pursuit è esentato dal registrare un tempo.

I vecchi tempi Prova/Gara e i risultati Accademia restano nello storico. Non diventano automaticamente una Qualifica ufficiale del nuovo protocollo.

## 4. Griglia di partenza

- **Più veloce davanti:** tempo di qualifica crescente, il minore in pole.
- **Più lento davanti:** tempo decrescente, griglia invertita fra i soli partecipanti scelti.
- «Veloce» si riferisce al **giro migliore**, non a V max, numero del pilota o ordine dei clic.
- Proposta parità: confronto dei successivi giri validi disponibili; se non comparabili, numero/ID stabile. Nessuna casualità non registrata.
- Tempo assente, incompatibile o legato a un’altra policy: pilota non schierabile, con collegamento a Qualifica. Ultima versione qualificata esplicitamente selezionabile.
- Prima di Start: riepilogo posizione, pilota, tempo e versione. Il worker ricontrolla e registra l’ordine finale, anche se la UI era corretta.
- Riutilizzare la griglia metrica sfalsata standard da 6 m; verificare sagome, linea di partenza, checkpoint e distanze di sicurezza per tutte le piste. Per auto future lo spazio deve dipendere dalle dimensioni effettive.

## 5. Perché 60 km/h possono apparire lenti

### 5.1 Tre misure distinte

**Velocità fisica**: metri per secondo simulato. **Ritmo del mondo**: secondi simulati per secondo reale. **Presentazione**: frame al secondo del display.

Il worker aggiorna i mondi Evo/NEAT in sequenza. Se un’auto riceve circa 8 passi da 1/60 s per secondo reale, il suo mondo avanza a circa 0,13×: 60 km/h simulati appaiono come circa 8 km/h rispetto al tempo reale. Interpolare a 30 fps distribuisce i pochi metri realmente simulati; non può aggiungere strada inventata.

Il campione privato rc.13 contiene circa 245 transizioni/s aggregate: dividere per 32 e per 60 dà una **stima di capacità 0,128×**, non una misura live dell’auto selezionata. Attivi variabili e verifiche impediscono di usare quell’aggregato come suo fattore effettivo. Per il dato vero servono timestamp/tempo simulato per auto e finestra omogenea, con pause/reset esclusi.

L’Ovale 1 misura **338,78 m**: a 60 km/h costanti un giro richiede circa **20,33 s simulati**, senza considerare accelerazione e rallentamenti. Quindi 4,91 s del Rientro non può essere interpretato come quel giro a quella velocità.

La riga `speed` attuale è la componente longitudinale `u`; V max usa già `hypot(u,v)`. La futura velocità a schermo va definita/coerente come velocità al suolo, conservando i sensori del modello e la compatibilità dei vecchi dati. Questa differenza non spiega il rallentamento di un ordine di grandezza.

### 5.2 Percorso consigliato

- **Vista Pilota a 1×** come osservazione principale: un mondo dedicato al modello corrente, con lo scenario della modalità. Per Evoluzione/NEAT la proposta è una dimostrazione separata dalla valutazione delle copie, per non alterare budget/fitness. Etichetta e descrizione devono chiarire che i giri osservati non sono prove di qualifica o dati di fitness.
- **Vista Tentativi** conservata per Evo/NEAT: tutte le copie reali, scelta completa dell’auto e della generazione, con rapporto del tempo effettivo indicato quando diverso da 1×. Non nascondere la popolazione per risolvere il carico.
- La vista Pilota va realmente sostenuta a 60 passi fisici/s con rendering 30 Hz. Definire un budget di lavoro per training/optimizer/valutazioni e servire i comandi/pose fra i blocchi. Anche la preview PPO attuale avanza al massimo un passo per chiamata: non basta estenderla senza verificare la cadenza.
- Per Qualifica/Gara utilizzare scadenze assolute/accumulatore, recupero limitato dei passi tardivi e telemetria di `simRate`. Il ciclo attuale riporta `race_next_tick` a `now+DT`: una chiamata in ritardo perde fase. Non aumentare DT per compensare e non promettere 1× senza misura.
- Qualifica/Gara: priorità a 1×, senza training concorrente. In allenamento, se necessario ridurre il **lavoro di raccolta tra i tick**, preservando modello/popolazione; batch numerici solo dopo parità e beneficio. Un mondo che non sostiene 1× lo dichiara, senza gonfiare velocità o estrapolare posizioni.
- Tentativo concluso/auto arrivata/ritirata: stato e ultima misura. Pausa: dato congelato dichiarato. Contare l’ultimo valore come velocità live è una fix UX distinta.

Vista Pilota e Tentativi non devono condividere cronometro, ID del mondo o risultati come se fossero la stessa esecuzione. Il buffer rc.13 da 200/120 ms introduce ritardo di presentazione, non una scala temporale costante di 0,13×: le due cause vanno misurate separatamente.

## 6. Allenamento infinito praticabile

“Infinito” è la durata dell’esperienza visibile, non una generazione che non può mai terminare o un array che cresce senza limite.

- Il traguardo conta giri e tempi senza ritirare l’auto. Separare `targetLaps` finito dal conteggio: continuare gate/lap timing oltre un giro, e oltre i tre giri dei compiti attuali.
- Usare finestre finite interne per raccolta/fitness/aggiornamenti. Durata da misurare per circuito e metodo; non attribuire successo o incidente al solo termine di una finestra. Nessun valore numerico `Infinity` nei JSON: obiettivo continuo esplicito e limite assente/nullabile.
- **PPO/PPO-Smooth:** conservare il valore finale al taglio esterno e distinguere truncation dalla terminazione reale. La distinzione è necessaria al calcolo corretto dei target del critic; la pausa conserva lo stato e non è una collisione. [Gymnasium: limiti e bootstrap](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/).
- **Evo/NEAT:** confrontare candidati con budget simulati/scenari comparabili. La fitness può premiare distanza pulita, giri/tempo e penalizzare incidenti, ma le generazioni devono poter aggiornarsi. La vista del pilota non deve assegnare esperienza extra ai candidati soltanto perché selezionati. [NEAT: valutazione e generazioni](https://neat-python.readthedocs.io/en/latest/neat_overview.html).
- **Clone:** mantenere il maestro coerente al compito, inclusi sorpassi; una dimostrazione puramente centrale/solitaria non basta. Nessun controllo del maestro sovrapposto alle azioni del pilota.
- Conoscenza personale riusata all’avvio; checkpoint/progressi separati per obiettivo e contesto fisico. Non sovrascrivere gli optimizer/episodi di Impara con quelli dell’infinito. Base, identità e metodo rimangono comuni.
- Registrare incidenti gravi, stalli reali e soste legittime nel traffico. Il fuori pista recuperabile modifica fisica/reward senza terminare automaticamente ogni tentativo; il giro diventa non pulito. Pausa interrompe l’attività, non cancella il tentativo salvato.
- RAM disponibile per buffer utili, ma storia/eventi devono restare limitati o aggregati. Prove lunghe necessarie: nessun accumulo senza fine di traiettorie, lap list o copie della policy.

Il progetto usa PPO numerico proprio: la documentazione [SB3 PPO](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html) è un riferimento per separare apprendimento e inferenza, non una nuova dipendenza da installare. Reti piccole e fisica continuano su CPU, Qt su GPU; questo studio non introduce un backend NPU.

## 7. Sorpassi continui

Il codice attuale concede un sorpasso una sola volta per rivale, con flag `passed`; richiede inoltre zero contatti e zero uscite **nell’intero episodio**. In una modalità lunga una vecchia uscita potrebbe quindi impedire tutti i premi successivi: non basta rendere infinito il numero di giri.

Proposta di evento verificabile:

1. Rivale prima realmente davanti, con gap e stessa zona fisica della pista; non usare soltanto progressi modulo giro.
2. Avvicinamento/affiancamento, poi margine di sicurezza dietro all’auto del pilota per un intervallo da tarare.
3. Nessun contatto/uscita durante **quella manovra**. Contatori di riferimento all’inizio, non il totale storico della sessione.
4. Premio singolo e cooldown; nuovo incontro solo dopo condizioni nuove. Separare sorpasso e doppiaggio, evitando oscillazioni avanti/indietro per accumulare premi.
5. Penalità per contatti/fuori pista, progresso valido e tempo, insieme al premio: non premiare l’attesa immobile o la sola V max.

Bot deterministici espliciti, velocità/traiettorie variate da seed registrato, nessun loro apprendimento. Prima 1–2, poi 3 se il budget a 1× lo consente. I 68 ingressi già osservano fino a tre rivali: verificarne portate, gap/TTC e ritirati. Nessuna comparsa improvvisa davanti al pilota; bot ritirati/nuovi incontri hanno regole di ripristino sicure, senza falsificare il conteggio dei passaggi. La proposta iniziale evita respawn sul tratto occupato: ripartenza nel nuovo tentativo se il traffico non è più utile.

## 8. Risultati e Progressi — UX sul 960×640

### Risultati del pilota

Tre schede leggibili **Allenamento / Qualifica / Gare**, con storico per pista e versione. Titolo grande, una frase grigia più piccola; righe brevi e dettagli al tasto 5, nello stile approvato. Nessuna legenda permanente 2/8–4/6.

**Esempio reale corretto del dato segnalato:**

> Rientro · 40 m  
> 20 su 20 riusciti · tempo tipico 4,91 s  
> Controllo circuito: 0 su 3 riusciti · 17 non eseguiti  
> Esercizio riuscito; verifica complessiva non superata

Dettaglio: mediana/migliore, protocollo, scenari/semi, motivo dei fallimenti, modello e data. «20/20» non viene intitolato «Giri» né «Pilota pronto».

**Qualifica:** `Miglior giro 0:22,134`, `2/3 giri validi`, `Versione qualificata disponibile`, dettaglio del giro invalidato. Formato giri minuti:secondi,millesimi; esercizi brevi in secondi e con distanza/obiettivo. Sono esempi di formato, non nuovi risultati del pilota.

**Gara:** ordine d’arrivo e stato, distacco/giri effettivi, giro migliore pulito e V max, circuito/configurazione/modello. Ritiri e mancati arrivi non hanno un tempo inventato.

### Come procede l’allenamento

- Obiettivo scelto, fase/esercizio corrente, tempo reale di allenamento e passi effettivi.
- Impara: giri completi e motivi di interruzione; esercizi Partenza/Rientro separati dai giri.
- Infinito: serie di giri puliti, distanza/durata senza incidente, causa dell’ultimo stop.
- Sorpasso: manovre tentate, completate e pulite; contatti/uscite per incontro e totali.
- Grafici con assi/unità e solo campioni dello stesso **esercizio/distanza/protocollo/contesto**. Non unire Partenza 3 m e 20 m, né controllo di un giro con passo di tre giri. Niente linea se mancano dati comparabili.
- Stato complessivo e abilità conservate separati dai successi del singolo esercizio. Testati, riusciti, falliti, non eseguiti e validi ufficiali sono categorie distinte.
- Modello attuale in formazione, ultimo salvataggio e versione qualificata: sostituire l’etichetta generica «Modello precedente» quando nasconde il candidato attuale.

### Preparazione della sessione

Modalità → pilota/circuito → opzioni pertinenti → Start. Solo Gara ha Schieramento e Griglia; Qualifica ha un pilota e giri cronometrati; i due infiniti mostrano «Fino a incidente/Pausa», non un numero di giri che termina la sessione. Sorpasso mostra numero/scenario bot, non partecipanti della rosa. Metodo e parametri rimangono consultabili, non modificati. Focus stabile e ritorno alla riga precedente; 5 conferma/pausa e frecce catturate durante l’attività come ora.

## 9. Architettura e compatibilità

| Area | Lavoro previsto |
| --- | --- |
| Modalità | Registro centrale con ID/label/descrizione, training o modello congelato, tipo obiettivo, conteggio partecipanti, opzioni e protocollo. Sostituire le condizioni sparse su `mode == impara`. |
| `game.py`, `game_settings.py`, `game_worker.py` | Cinque scelte e validazione coerente UI/worker, una selezione in Qualifica, candidate disponibile, griglia ordinata e checkpoint per obiettivo. Nessun avvio automatico aprendo menu o al boot. |
| `game_academy.py`, `game_academy_trainer.py`, `game_protocol.py` | Compiti continui, finestre/fitness, terminazione/troncamento, priorità del mondo osservato e pacing. Conservare le verifiche tecniche come tali. |
| `game_simulation.py` | Traguardo non terminale, telemetria per giro/auto, tick assoluti; validità e prestazioni della nuova dinamica di durata senza cambiare aderenza/dimensioni per mascherare lentezza. |
| `game_records.py`, `game_store.py` | Giro di Qualifica/certificato atomico con hash della policy, circuito/configurazione/protocollo; snapshot qualificati conservati e storico per obiettivo. Schema additivo/migrazione recuperabile, eventi/lap list limitati. |
| Dossier/Progressi | Obiettivo, metri/giri, tempo tipico contro giro ufficiale, eseguiti/non eseguiti, risultato complessivo e curve omogenee. |
| Presentazioni/contratto | Cinque modalità, picker/descriptions e risultati leggibili nei tre temi; azione pubblica `game.mode` oggi ha enum di quattro valori: estensione additiva e fixture/SDK aggiornati dove cambia il contratto. |

**Sensori e canale compito:** oggi `Episode.step()` codifica le fasi dell’Accademia, mentre `World.reset()` lascia il canale finale a 1 per le esecuzioni standalone. Qualifica/Vista Pilota/Gara devono avere una semantica di input verificata contro quella di training; non presumere che gli stessi pesi si comportino allo stesso modo sotto un altro codice di compito. Non aggiungere fasi rinormalizzando tutto l’enum e cambiando il significato degli ingressi esistenti. Decodifica fissa/versionata e prova su policy congelate prima della scelta.

**Vecchi dati:** `prova`/`campione` conservano significato nello storico; eventuali alias API non attribuiscono nuove certificazioni. Reti 32/42/68, genomi NEAT, parametri manuali, base personale e percorsi già salvati vanno conservati. Cambiare modalità non resetta il pilota; preparazione/migrazione del training solo dopo Start esplicito. Qualifica deve evitare la circolarità «serve il modello già certificato per misurare il primo giro».

## 10. Ordine di intervento e accettazione

| Lotto | Intervento | Gate prima della consegna |
| --- | --- | --- |
| **M0 · Comprensibilità** | Risultati per esercizio, metri/giri, testati/non eseguiti, stato della verifica e ultima velocità dei conclusi; dati di ritmo per auto. | Il caso Evo 4,91 s è spiegato come Rientro, con Controllo fallito; nessuna falsa qualifica. Tempo/speed di pausa e fine prova riconoscibili. |
| **M1 · Qualifica/Gara** | Registro modalità, Qualifica su candidato salvato, tempo ufficiale obbligatorio, snapshot scelto, griglia veloce/lento. | Nessun giro→blocco; un giro pulito→accesso; versioni/configurazioni corrette, parità e griglia esatta nei due ordini, Pure Pursuit senza eccezione. Qualifica non cambia pesi. |
| **M2 · Durata e bot** | Impara un giro, infinito e sorpasso continuo; finestre, checkpoint e premi per manovra. | Oltre tre giri senza fine automatica, aggiornamenti NEAT/Evo possibili, bootstrap PPO corretto, niente premi ripetuti/teleport dei bot. Ripresa e memoria per obiettivo verificabili. |
| **M3 · Ritmo e qualifica integrata** | Vista Pilota 1×, Tentativi reali dichiarati, scheduler/optimizer per budget, eventuale batch numerico. | Misurare rapporto simulato/reale, pose/FPS separati, carichi 1/2/4 auto e 32 copie. Proposta 1×: rapporto 0,98–1,02 su finestra stabile dopo warm-up, esclusi countdown/pausa/reset; gate 30 Hz già fissato nello studio. Se manca, dichiarare il limite. |

M0 e diagnosi del ritmo sono la prima priorità; la velocità reale va progettata prima di promuovere le nuove sessioni come gioco a 1×. Matrice finale: Ovale, tecnico, Mallory/Varano; Base/Functional/Apple Calm, movimento normale/ridotto/off, selezione sensori/camera, pause/salvataggi/ripresa, giro invalido e nessun tempo, cambi modello/contesto, gare 2/4 con tutti visibili. Sessioni lunghe per infiniti, optimizer maturi e crescita dati; test fisico sul pannello distinto dal solo software.

**Stato:** fattibile come evoluzione del sistema esistente. Qualifica/griglia e UX riusano molta infrastruttura; le modalità infinite e la vista a velocità reale richiedono modifiche al protocollo/scheduler, non solo etichette. Nessuna di queste fix è implementata o installata da questo studio.

**Aggiornamento di consegna:** M0–M3 implementati e installati nella [rc.14](v09-session-modes-report.md); questo documento conserva l’analisi iniziale. Stato e gate residui nel report e nel MasterPlan 2.73.
