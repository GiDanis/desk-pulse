# Gioco v0.9 — Gara e visualizzazione PPO

La candidata corrente è rc.6; [scheda Pilota e ricevuta corrente](v09-pilot-dossier-report.md). Il presente report conserva la consegna rc.5.

11 ottobre 2026 · **0.9.0-rc.5** · Theme API 2.8 / 67 superfici / Apple Calm 1.6.2.

## Problemi individuati

Il motore prevedeva già tre giri e reti congelate, ma il menu chiudeva anche dopo uno Start rifiutato. Senza selezione iniziale dei concorrenti, la mancata partenza risultava poco comprensibile. L'ispezione non trova recenti sessioni Gara nella base dell'utente; non attribuiamo il problema a un crash del motore non osservato.

PPO riavviava subito le copie terminate mentre l'allenamento correva più veloce del tempo reale. Il disegno dei rollout mostrava auto ritirate, nuove partenze e cambi durante la valutazione, producendo apparizioni/sparizioni difficili da seguire.

## Correzioni

- **Gara:** scegliendo la modalità, se la lista è vuota vengono schierati fino a quattro piloti con un modello salvato. Il menu mostra partecipazione, tipo di modello salvato e distanza **3, 5 o 10 giri**; non espone parametri di allenamento. Restano modificabili i concorrenti.
- **Start:** richiede da due a quattro modelli disponibili. Se mancano, il menu resta aperto con il motivo; il tasto 5 sulla pista apre il menu dopo un avvio rifiutato.
- **Una vettura per pilota:** ogni partecipante carica la propria politica congelata. Nessuna mutazione o allenamento durante la gara. Nome, identità e versione del modello partecipano alla registrazione del risultato.
- **Giri corretti:** anche le file arretrate contano rispetto al traguardo comune. Regolamento `race-2`, limite massimo `max(300, giri × 120)` secondi simulati e finestra finale di 30 secondi dal primo arrivo. Contatti/bordi mantengono il ritiro, senza attribuzione di colpa.
- **PPO:** la pista mostra una sola **Guida PPO**, un mondo fisico indipendente, guidato deterministicamente dall'attore corrente e avanzato in tempo reale. Dopo un ritiro/arrivo il corpo resta visibile per un secondo con stato Ripartenza/Giro completato; quindi riparte. Le copie, i campioni raccolti e le valutazioni continuano in parallelo nel learner. Questa guida non è una prova standard né un campione qualificato e non modifica il training o i suoi RNG.
- **Pausa:** conserva l'ack reale e blocca la navigazione fino alla conferma; alla ripresa non recupera in accelerazione il tempo trascorso in pausa.

Fisica `f1-2`, sensori, reward, checkpoint e backend CPU restano compatibili. La separazione del preview riguarda PPO; Evoluzione/NEAT continuano a mostrare i tentativi della popolazione.

## Verifiche

[Sette gate PC](evidence/v09-race-ppo-2026-10-11/regression/checks.json): quattordici test del motore, cinque del curriculum, Main/QML, contratto e runtime Theme API, bundle/kit e corpus. Il nuovo test verifica avanzamento reale del preview, pausa tra tentativi e scarto dei lunghi intervalli. [Menu/griglie PC](evidence/v09-race-ppo-2026-10-11/pc-race/report.json) e [PPO PC](evidence/v09-race-ppo-2026-10-11/pc-ppo-final/report.json).

**Scheda, EGLFS/KMS 960×640, Apple Calm scala 1,1**, archivi privati:

- [Gara completa](evidence/v09-race-ppo-2026-10-11/board-native/race/report.json): due politiche Evoluzione realmente apprese nelle precedenti prove seed 1/5. Un concorrente arriva dopo tre giri, l'altro si ritira; due risultati, identità uniche e modelli invariati. Verificata anche la griglia a quattro e la selezione di cinque giri. Pausa circa **21,7 ms**, nessun warning QML. Il controllo dieci giri riguarda la configurazione, non una gara intera di dieci giri.
- [PPO 60 secondi](evidence/v09-race-ppo-2026-10-11/board-native/ppo/report.json): una sola auto con identità `preview` verificata durante l'intera prova, learner con 32 tentativi paralleli; **219.776 passi** salvati, pausa circa **32,3 ms**, nessun warning QML. Intervalli software frameSwapped: mediana 21,1 ms, p95 54,7 ms, massimo 296,9 ms. Non sono misure ottiche/GPU né prova di 60 FPS costanti.

[Cattura arrivo](evidence/v09-race-ppo-2026-10-11/board-native/race/race-finished.png) · [Guida PPO](evidence/v09-race-ppo-2026-10-11/board-native/ppo/soak-end.png). Non sono sessioni di allenamento dei piloti dell'utente. La griglia a quattro prova avvio/lifecycle; non certifica quattro concorrenti capaci di completare la gara nel traffico.

## Consegna e dati preservati

[Pacchetto finale](evidence/v09-race-ppo-2026-10-11/final-package.json): manifest **546 file** verificato; codice Gioco identico alla build provata nativamente, controllo diagnostico PPO aggiornato. [Ricevuta installazione](evidence/v09-race-ppo-2026-10-11/board-install/final-receipt.json): backup completo, manifest senza differenze, GUI pronta e fresca, servizio attivo con NRestarts=0; preferenze/tema, tutte le colonne dei piloti e artefatti confrontati al backup. Riavvio del servizio, nessun nuovo reboot OS. [Kit aggiornato](evidence/v09-race-ppo-2026-10-11/smartpc-theme-kit-v09-rc5.zip) e [MasterPlan 2.55](release-masterplan.md).

Al controllo iniziale due piloti avevano una politica salvata utilizzabile. Un altro PPO aveva solo un candidato/checkpoint: non viene promosso per far partire una gara. Se un pilota cambia metodo, Gara identifica il metodo della politica salvata, che può appartenere al profilo precedente.

## Limiti e prossimi passi

Restano aperti competenza PPO/NEAT, taratura del reward e del tempo dei singoli episodi PPO, guida nel traffico, carico ampliato e lettura/input fisici. Un modello disponibile non garantisce arrivo o competitività; la correzione non inventa campioni, competenze o vincitori. Le prove di tre giri sull'ovale non dimostrano guida generale. Il piano mantiene Compagno v0.10 e Memoria v0.11 dopo la chiusura dei gate pertinenti del Gioco.
