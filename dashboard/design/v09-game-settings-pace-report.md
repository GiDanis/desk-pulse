# SmartPC 0.9.0-rc.3 — impostazioni e apprendimento del passo

**Consegna successiva:** [0.9.0-rc.4, prestazioni del motore e delle scene](v09-game-performance-report.md) installata. Questo report conserva i risultati della rc.3.

11 ottobre 2026 · Implementazione autorizzata dello [studio](game-settings-speed-study.md).

**Candidata implementata e installata**, API 2.8 / 67 superfici / Apple Calm 1.6.2. Le nuove funzioni sono consegnate; competenza generale nel traffico, PPO/NEAT e accettazione fisica conservano gate separati. Evidenze in [questa cartella](evidence/v09-game-settings-pace-2026-10-11/).

## 1. Risultato per l'utente

- Menu Gioco senza legenda permanente dei tasti. Titolo, valore a destra e descrizione secondaria separati, palette/font del tema. Cinque righe alla scala 1, quattro alla scala 1,1; focus e paginazione mantengono la selezione visibile. Descrizioni per parametri generali, Evoluzione, NEAT e PPO, creazione, partecipanti e Start. Mutazione indica ampiezza, non probabilità percentuale.
- **Controllo → Passo** automatico dopo due finestre indipendenti con almeno 9/10 giri validi. In Passo l'incentivo sul tempo cresce gradualmente in otto generazioni/aggiornamenti. Traffico resta una scelta esplicita del profilo, con l'avversario fisso già presente: non viene inserito silenziosamente e non diventa competenza Gara qualificata.
- **Candidato, checkpoint e campione distinti.** Dieci partenze variate per finestra, identiche per candidato e campione. Il nuovo campione deve arrivare almeno 9 volte, mantenere il numero di arrivi del precedente sulla stessa finestra e migliorare la mediana di oltre 0,05 s; recupero ammesso se il precedente fallisce la soglia. Un candidato inaffidabile non rimpiazza il campione.
- **Progressi** mostra fase, passi/minuti, tempi mediani delle prove affidabili, giri validi e migliore giro del campione. Il guadagno dell'ultima promozione usa le prove abbinate della medesima finestra. La prima qualifica è un riferimento storico, non una sottrazione tra partenze diverse. Fitness/loss non vengono presentate come misura di velocità.
- In Pista compare la fase o «Valutazione»; durante le prove sono disegnate le vetture effettivamente valutate, selezionabili anche oltre le prime sette. Arena e proporzioni rimangono 912×496 / vettura 4,4×1,8 m. Gara/Prova/Campione continuano a usare politiche congelate.

## 2. Implementazione e compatibilità

[`game_curriculum.py`](../game_curriculum.py) contiene reward/evaluation versionati, finestre di selezione, promozione e mondi di valutazione separati dal training. Solitario vettorizzato; traffico usa mondi distinti con un solo learner. I checkpoint comprendono RNG e mondi delle valutazioni interrotte. La valutazione viene eseguita dal worker dopo Start, al primo aggiornamento e poi ogni cinque generazioni Evoluzione/NEAT oppure otto aggiornamenti PPO; la sua durata è registrata separatamente. Non parte aprendo Progressi/Classifica o al boot.

La ricompensa **`control-pace-1`** conserva il progresso e il premio del giro; in Passo porta la penalità temporale da 0,02 a 0,30 punti/s e aggiunge un bonus limitato a 5 punti per un giro valido sotto il riferimento fisso di 60 s. Questi coefficienti sono sperimentali. La fisica `f1-2`, sensori `race-32-v1`, azioni e limiti reali della vettura non cambiano. La penalità di sterzo attuale resta presente; una diversa penalità delle oscillazioni è un esperimento successivo, non una funzione consegnata.

Evoluzione/NEAT propongono il vincitore della generazione corrente per la valutazione, evitando di affidarsi al solo record ottenuto su un'altra partenza. I punteggi storici si invalidano al cambio di criterio. Per PPO la transizione avviene a un aggiornamento completato: buffer precedente eliminato, mondi resettati, critico/optimizer del critico reinizializzati, attore conservato. Gli incrementi graduali successivi avvengono tra rollout, senza minibatch miste.

SQLite aggiunge `candidate` e `curriculum`. Aggiornamento del campione, checkpoint e prova della promozione sono nella stessa transazione; artefatti JSON con hash/fsync già presenti. Il profilo originale del campione resta associato al suo modello anche se si cambiano parametri modificabili. Piloti precedenti e modelli restano conservati ed etichettati precedenti, senza inventare una qualifica; i nuovi candidati non qualificati non diventano automaticamente modelli Gara. Cambi incompatibili avviano un percorso nuovo e conservano la politica precedente.

Le mappe del menu aggiungono `description`/`value`, mantenendo `detail`; DTO pubblici, fixture, catalogo con hash e kit aggiornati. API 2.8 e bundle Apple Calm immutabile conservati. CPU rimane il backend del gioco: il confronto NPU della rc.2 non viene reinterpretato come un nuovo benchmark.

## 3. Apprendimento: prove e limiti

Cinque reti Evoluzione inizializzate casualmente, popolazione 32, senza controller che imposti o corregga la guida. Allenamento continuato per 36–41 generazioni; promozioni su finestre diverse e valutazione finale su dieci partenze comuni mai usate per selezionare i campioni.

| Seed | Prima mediana, s | Mediana finale, s | Guadagno, s | Giri validi prima → dopo |
| --- | ---: | ---: | ---: | --- |
| 1 | 30,71 | 24,77 | 5,94 | 10/10 → 10/10 |
| 2 | 33,77 | 24,19 | 9,58 | 10/10 → 10/10 |
| 3 | 39,40 | 22,87 | 16,53 | 10/10 → 10/10 |
| 4 | 36,76 | 23,04 | 13,72 | 10/10 → 9/10 |
| 5 | 37,81 | 27,96 | 9,85 | 10/10 → 10/10 |

[Dati grezzi e riepilogo](evidence/v09-game-settings-pace-2026-10-11/learning-summary.json): **49/50 giri validi** finali, contro 50/50 del primo campione. Tutti i seed raggiungono almeno 9/10, ma il seed 4 perde un arrivo: non dichiarare affidabilità assolutamente invariata. Le mediane escludono i fallimenti, riportati separatamente.

Un secondo esperimento mantiene la ricompensa Controllo e continua l'allenamento fino allo stesso budget di transizioni; si termina la generazione corrente, con eccedenza massima 1,65%. Stesso criterio di promozione e partenze finali abbinate. Il nuovo obiettivo è più veloce in tre seed, meno veloce in due; vantaggio mediano tra seed circa **0,82 s**, ma 49/50 contro 50/50 arrivi. [Confronto completo](evidence/v09-game-settings-pace-2026-10-11/reward-comparison.json). Una parte importante del guadagno viene dal proseguire l'allenamento: non attribuire tutto alla nuova ricompensa, non dichiararla universalmente superiore. Servono ulteriori seed/scenari per una conclusione statistica e una taratura definitiva.

I primi esperimenti hanno intercettato una discrepanza tra lo stato reale `arrivato` e il conteggio dei giri; corretta prima della distribuzione e coperta da un test sul giro effettivo del simulatore. I log precedenti sono conservati come diagnostica, non come risultato di apprendimento.

## 4. Verifiche PC e Orange Pi

- Dieci controlli del motore e cinque nuovi controlli di curriculum: dinamica, gradienti/ripresa PPO, NEAT/RNG, promozione affidabile, soglia temporale, compatibilità, artefatti e valutazioni solo/traffico ripristinate. Un giro realmente completato verifica il conteggio degli arrivi.
- Main reale: tutte le righe del menu, descrizioni dentro l'altezza disponibile, assenza legenda, tre temi, testo 1/1,1, Evoluzione/PPO/NEAT, input durante simulazione, pausa/salvataggio e uscita Home. Nessun avviso QML nelle prove native.
- Contratti/runtime/kit e corpus verificati. Il controllo di corpus ha rilevato l'hash della fixture modificata non ancora aggiornato; catalogo corretto e controllo ripetuto con successo, oltre alla fixture menu eseguita nei renderer Base/Functional.
- EGLFS/KMS reale 960×640: sei profili di menu/lifecycle e verifica finale Apple Calm scala 1,1 con Progressi popolato da evidenze reali in archivio isolato. Sessione finale 120 s; CPU massima osservata **51,09 °C**, pausa circa **17,9 ms**. Il precedente soak 30 minuti della rc.2 resta evidenza storica, non un nuovo soak rc.3.
- Worker reale anche sulla board: pausa dentro una valutazione, salvataggio dei mondi, nuovo processo che riprende e raggiunge Passo con campione 10/10. Ack circa **0,57 e 1,35 ms** nel processo isolato. Nessun controller per la politica del pilota; il modello fixture proveniva da un precedente allenamento Evoluzione reale. [Prova](evidence/v09-game-settings-pace-2026-10-11/board-final-native/worker-store/worker-evaluation-proof.json).

Screenshot e tempi Qt non certificano leggibilità ottica, pressioni fisiche dei tasti o 60 FPS costanti. Le prove private non sostituiscono né allenano i piloti dell'utente.

## 5. Distribuzione e residui

Manifest rc.3 **545 file**, kit aggiornato e backup del runtime/stato prima dell'installazione. Preferenze, tema e contenuto dei registri dei piloti precedenti confrontati semanticamente; nessun cambiamento delle loro reti, passi o profili durante la migrazione. [Ricevuta finale](evidence/v09-game-settings-pace-2026-10-11/board-install/final-receipt.json): reboot reale, 44 preferenze, Apple Calm 1.6.2, servizio active/running con NRestarts=0 e heartbeat GUI pronto/fresco. Checkpoint Evoluzione/PPO/NEAT e risultati Gara conservati dopo reboot in archivio isolato, nessuna ripresa automatica.

Restano: taratura/robustezza su altri seed e scenari, competenza nel traffico e Gara 2/4, qualità di apprendimento PPO/NEAT, profili ampliati, frame pacing in Gara, lettura/input fisici e uso prolungato della build finale. Queste funzioni sono implementate dove descritto, ma le qualifiche non vengono chiuse dal solo completamento del codice. Preset, mutazione adattiva, nuovi circuiti/vetture/fondi e penalità alternative restano evoluzioni successive. Compagno v0.10 e Memoria v0.11 mantengono la sequenza del MasterPlan.
