# Completare tutti i piloti — diagnosi del menu e piano di qualifica

**21 ottobre 2026 · Europe/Rome · analisi, nessuna correzione runtime installata.**

**Attuazione successiva:** [rc.28 consegnata](v09-pilot-menu-fix-report.md), chiusi P0 e continuità P1; ripresa scientifica Tattico e competizione nel traffico aperte. Il documento conserva la diagnosi originale.

Baseline corrente al momento dello studio: **0.9.0-rc.27**, 640 file nella consegna precedente. Il servizio risulta attivo con `NRestarts=0`. Lettura della produzione in sola lettura alle **16:38:38 italiane**: Crono è in allenamento; nessuna pausa, modifica dei salvataggi o riavvio è stato eseguito per questo studio. Gli hash dei sei sorgenti rilevanti installati coincidono con quelli della riproduzione locale.

## 1. Diagnosi verificata

**Il messaggio «Profilo incompleto o sconosciuto» è un errore del controllo delle impostazioni introdotto con la ricetta rc.27.** Nei quattro profili neurali ci sono tutti i parametri di base. Il produttore dei profili ha aggiunto le chiavi della nuova ricetta, ma il validatore del menu continua ad ammettere soltanto il vecchio insieme di campi.

In `game_store.validate_profile()` il controllo confronta esattamente le chiavi con `default_profile()`, escludendo soltanto `variant`, `recipeVersion` e `controlMode`. Non riconosce:

- `racingObjective`, `racingCurriculum`, `expertLearning`, `racingAnchor`, `raceValidationEvery`, presenti in tutti e quattro i learner;
- `episodeExploration`, presente anche in Crono.

`racingBackup` e `racingHorizon` sono chiavi di sperimentazione registrate nel codice, ma non sono presenti nei profili correnti. Non servono per spiegare il blocco osservato.

La riproduzione usa i profili letti dalla board e un archivio temporaneo. Esegue **il vero percorso `GameSettings → GameService.applySetup`**, senza avviare worker. Il controllo diagnostico che rimuove soltanto le chiavi nuove torna valido per tutti: conferma la causa, **non è la correzione proposta**, perché eliminare i metadati potrebbe rendere incoerente la ricetta con il checkpoint.

Evidenze: [stato salvato](evidence/v09-pilot-completion-audit-2026-10-21/board-state.json), [riproduzione](evidence/v09-pilot-completion-audit-2026-10-21/menu-reproduction.json), [script](evidence/v09-pilot-completion-audit-2026-10-21/reproduce_menu_block.py).

### Perché sembra funzionare soltanto Crono

Il servizio seleziona inizialmente Crono. Se la bozza delle impostazioni non cambia, `GameSettings.apply()` salta `applySetup()` e Start può partire. Scegliendo Memoria, Linea o Tattico, la bozza cambia e attraversa il validatore che li rifiuta. Anche cambiare modalità a Crono attraversa lo stesso errore.

| Percorso provato | Bozza modificata | Esito attuale |
| --- | --- | --- |
| Crono già selezionato, nessun cambio | No | Conferma riuscita, validatore saltato |
| Crono con cambio modalità | Sì | Profilo incompleto o sconosciuto |
| Scelta Memoria dal menu | Sì | Profilo incompleto o sconosciuto |
| Scelta Linea dal menu | Sì | Profilo incompleto o sconosciuto |
| Scelta Tattico dal menu | Sì | Profilo incompleto o sconosciuto |
| Tre piloti precedenti con cambio modalità | Sì | Stesso errore |

Sono otto percorsi: uno passa saltando la validazione, sette falliscono. Gli archivi temporanei non cambiano profilo e nessun worker viene creato. Il pattern riproduce la segnalazione; se sul pannello la frase completa fosse diversa, andrà correlata alla schermata esatta prima di attribuirle questa causa.

### Distinguere altri significati di «incompleto»

`Sorpasso incompleto` è invece un esito dell'esercizio: il pilota ha girato ma non ha consolidato il passaggio richiesto. `Giro incompleto` riguarda un giro/settori non validi. Questi risultati non vanno trasformati in successo per risolvere un errore di selezione. Anche mancare di Qualifica impedisce correttamente la Gara ed è uno stato distinto.

## 2. Stato reale della rosa

Tutti e quattro i checkpoint neurali esistono e il loro contenuto corrisponde all'hash del nome del file. Tutti contengono un attore da **11.999 parametri**. Memoria/Linea/Tattico hanno anche i campi dei due critic, target e replay; la loro assenza di aggiornamenti non è un modello mancante.

| Pilota | Metodo | Nuovi passi fisici salvati nella rc.27 | Aggiornamenti nella nuova epoca | Diagnosi |
| --- | --- | ---: | ---: | --- |
| Maestro | Controllore deterministico | 0 | Non applicabile | Riferimento per Qualifica/Gara; non deve allenarsi. |
| Crono | PPO | 159.457 | 208 | Allenamento effettivo presente; ultimo confronto salvato promuove una versione gara. Il menu resta difettoso se si modifica la bozza. |
| Memoria | SAC | 0 | 0 | Checkpoint migrato presente; nessun allenamento rc.27 salvato nel campione letto. Blocco del menu riprodotto. |
| Linea | TD3 | 0 | 0 | Come Memoria; fondamentali precedenti presenti e rete conservata. |
| Tattico | TD3 con traffico | 0 | 0 | Come gli altri per l'accesso. In aggiunta esiste uno stallo di apprendimento separato nelle precedenti prove su copia. |

I totali di passo/tempo precedenti non significano che i nuovi critic abbiano già imparato. I contatori di epoca sono indispensabili per leggere lo stato. La fotografia comprende solo dati già salvati: Crono prosegue dopo l'acquisizione.

## 3. Perché i test precedenti non hanno intercettato il blocco

Il walkthrough della rc.27 verificava effettivamente quattro learner, aggiornamenti, salvataggi, Qualifica e Gara. Per passare fra piloti chiamava però **`selectDriver()` direttamente**, quindi Start, mentre i profili delle fixture erano caricati direttamente nell'archivio privato. Il controllo del menu riguardava la consultazione, non la conferma di una bozza modificata con un profilo rc.27.

Questo lascia scoperto il percorso usato dall'utente. Le prove numeriche dei metodi rimangono evidenze valide di quel perimetro; non dimostrano che tutti fossero raggiungibili attraverso le impostazioni reali. La regressione va registrata nella consegna e nel MasterPlan, aggiungendo un controllo sul percorso completo.

## 4. Correzione progettata — priorità P0

### 4.1 Un contratto coerente per profili e ricette

1. Separare esplicitamente campi obbligatori del profilo e metadati versionati opzionali della ricetta.
2. Centralizzare le chiavi e le versioni ammesse insieme a `game_racing_presets`, evitando un elenco diverso fra produttore, validatore e persistenza.
3. Validare tipo, valori e compatibilità con metodo e `controlMode`. Riconoscere i profili completi rc.27 e quelli precedenti già archiviati; rifiutare campi realmente sconosciuti, versioni future non supportate e valori errati con un messaggio specifico.
4. Conservare i campi ricevuti: niente eliminazione silenziosa, reset di checkpoint o cambio di metodo per superare la validazione.
5. Tenere distinti `profile` di allenamento e `policy_profile` della versione che corre. Una semplice selezione non aggiorna la ricetta di una policy storica, non invalida certificati pertinenti e non crea un nuovo percorso in `profile_paths`.
6. Verificare tutti i chiamanti: `applySetup`, `set_profile`, `updateProfile`, attivazione dei vecchi percorsi e ripristino degli obiettivi. I parametri fissi dei piloti rimangono in sola consultazione.

La documentazione ufficiale distingue proprietà riconosciute, obbligatorie e aggiuntive: un contratto chiuso rifiuta i nuovi campi finché non vengono dichiarati. Questo principio descrive il difetto del nostro validatore manuale; non richiede introdurre una libreria JSON Schema. [JSON Schema — Object, Properties e Additional Properties](https://json-schema.org/understanding-json-schema/reference/object).

### 4.2 Interazione e messaggi

- La stessa configurazione valida deve essere accettata sia con bozza invariata sia dopo selezione dal menu. Non usare il percorso diretto come unica prova del fix.
- Mostrare errori che identifichino il campo/versione incompatibile. Distinguere errore tecnico, pilota da allenare, preparazione dei critic, esercizio fallito e Qualifica necessaria.
- Visualizzare metodo, passi/aggiornamenti della nuova epoca e ultimo esito nel dossier; nessun indicatore positivo derivato dal solo contatore storico.
- Maestro resta chiaramente un riferimento: Impara non applicabile, Qualifica/Gara disponibili secondo le regole. Evitare che questa scelta appaia come rete guasta.
- Conservare tema Apple Calm, dimensioni 960×640, descrizioni leggibili e comandi esistenti. Il blocco non richiede nuove pagine o controlli permanenti.

### 4.3 Test necessari per chiudere P0

| Livello | Prova e criterio |
| --- | --- |
| Contratto | I quattro profili reali rc.27 e i profili storici supportati passano senza perdita di campi. Casi con campo sconosciuto, campo obbligatorio assente, tipo/valore errato o ricetta incompatibile falliscono con causa specifica. |
| Persistenza | Cambio pilota/modalità non altera rete, metodo, seme, contatori o policy gara; annullamento invariato, niente archivio/percorso nuovo per la sola selezione. |
| Menu reale | Dopo apertura pulita e dopo riapertura: scegliere dal menu ciascuno dei quattro piloti, confermare e avviare. Verificare sia bozza modificata sia invariata, non chiamare solo `selectDriver()`. |
| Modalità | Matrice di quattro learner × cinque modalità. Le dodici combinazioni Impara/Infinito/Sorpasso partono; Qualifica e Gara rispettano i requisiti reali. Maestro ha gli esiti intenzionali espliciti. |
| Worker | Un ciclo con aggiornamento effettivo per ciascun metodo, Pausa/«Salvato», ripresa dal checkpoint e riapertura dell'app privata. I contatori devono crescere dalla nuova epoca e il modello salvato deve ricaricarsi. |
| Display | Percorso del menu nei tre temi a 960×640/textScale 1,1; niente warning QML, testo leggibile. Una Qualifica per policy effettiva e una Gara completa con cinque auto visibili. |
| Consegna | Confronto sorgenti e manifest; backup, piloti/storico/preferenze conservati, heartbeat GUI corrente e NRestarts=0. Installazione separata dall'analisi; se c'è training attivo, prima Pausa e salvataggio. |

Per il solo fix di contratto non serve ripetere automaticamente tutte le campagne scientifiche: i test mirati coprono la nuova regressione. I confronti di apprendimento vanno ripetuti se cambiano effettivamente ricompense, dati, ottimizzatori o curriculum.

## 5. Completamento dell'apprendimento — priorità P1

Rendere un pilota selezionabile, dimostrare che aggiorna la rete e dimostrare che migliora in gara sono tre risultati separati.

| Metodo | Evidenza già disponibile nelle prove private rc.27 | Lavoro dopo lo sblocco |
| --- | --- | --- |
| Crono/PPO | Progressi su più semi e anche in produzione nel salvataggio letto. | Completare il percorso menu e verificare continuità; nessun reset proposto. |
| Memoria/SAC | Cinque nuovi semi: mediana circa 19,750 s da 22,081; copia reale circa 19,631 s. | Confermare che lo stesso pilota avvii il replay, completi la preparazione dei critic, aggiorni e salvi attraverso la GUI reale. |
| Linea/TD3 | Cinque nuovi semi: mediana circa 19,630 s; copia reale circa 19,669 s. | Stessa verifica di continuità, attore/critic e progressi; conservare il migliore quando il candidato peggiora. |
| Tattico/TD3 traffico | Cinque nuovi semi migliorano, mediana circa 19,798 s; la vecchia copia resta a circa 22,078 s nel budget. | Confronto dedicato della ripresa di quel checkpoint; poi valutazione separata di passo, sorpasso, difesa e gara. |

Questi numeri appartengono ai [benchmark precedenti](v09-racing-objective-report.md), non sono tempi già ottenuti ora dai tre piloti fermi in produzione.

### 5.1 Stallo della copia Tattico: ipotesi da verificare

- Confrontare vecchio candidato e proprio campione come punto di ripresa, preservando entrambi gli originali.
- Confrontare momenti Adam del solo conservati e reinizializzati: il nuovo obiettivo cambia i gradienti. È un'ipotesi, non una causa dimostrata; non applicare un reset generale prima del confronto.
- Misurare valore/errore dei critic, aggiornamenti effettivi e distribuzione degli episodi dalla nuova epoca. Il salto prematuro del curriculum è già corretto, ma la prova precedente mostra che quella correzione da sola non basta.
- Misurare il selettore degli esperti: nelle gare private precedenti favoriva molto spesso l'esperto prudente quando rilevava rivali. Il passo in solo non certifica una gara altrettanto veloce. Proteggere le competenze e valutare una selezione più locale senza introdurre un bot agli attuatori.
- Conservare i fallimenti e i contatti nei risultati. Non promuovere una versione soltanto perché completa un giro più veloce in solo.

Per nuove varianti scientifiche: budget dichiarato uguale fra confronti, almeno cinque addestramenti quando si sceglie un nuovo default, banca finale separata e costo delle verifiche misurato. La guida ufficiale raccomanda più esecuzioni e valutazione distinta dall'esplorazione; il successo di un singolo run non stabilisce la qualità del metodo. [Stable Baselines3 — RL Tips and Tricks](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html).

## 6. Ordine di attuazione e criteri finali

1. **P0, correzione del contratto e percorso reale:** sbloccare tutti i learner senza cambiare ricompense o reti; test mirati, board e consegna conservativa.
2. **P1, continuità di tutti i piloti:** menu → Start → aggiornamento → Pausa → salvataggio → riapertura per ciascuno, con esiti verificabili.
3. **P1, ripresa Tattico:** confronto controllato sul checkpoint che non migliora; nessun azzeramento indiscriminato.
4. **P2, corsa competitiva:** passo nel traffico, varietà dei rivali, eventuali nuovi incentivi relativi e difesa. Confronto con policy gara precedente e tempi/certificati coerenti.

**Definizione di completato:** i quattro learner sono raggiungibili dal menu e realmente allenabili, tutti salvano e riprendono, i risultati distinguono aggiornamento e miglioramento, Qualifica/Gara usano la policy corretta. La superiorità tattica generale e la convergenza garantita non diventano condizioni dichiarate superate con un semplice fix del menu.

Nessuna nuova architettura, dipendenza, allocazione NPU, modifica ai parametri o nuova rc è stata applicata da questo studio. La prossima correzione resta nella famiglia v0.9.x; l'ordine Acquario v0.10 → Compagno v0.11 → Memoria/AI v0.12 → Stabilità v1.1 è invariato.
