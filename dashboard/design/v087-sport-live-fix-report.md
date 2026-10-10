# SmartPC 0.8.7-rc.3 — Priorità agli eventi Sport in corso

Installata sulla Orange Pi il 10 ottobre 2026. Apple Calm 1.6.2 e Theme API 2.7 conservati.

## Problema osservato

La cache della board conteneva Genoa–Fiorentina in corso, 2–1 all’81°, con aggiornamenti recenti. Il riepilogo Serie A selezionava invece Inter–Parma: richiedeva il badge live qualificato e un campo pubblico (`activeLiveVerified`) assente nel payload nativo. Lo stato della partita era disponibile, ma veniva scartato dalla selezione.

Il feed F1 rispondeva con le qualifiche di Singapore concluse e 22 piloti. `GmtOffset: 08:00:00` non veniva convertito perché mancava il segno nel formato atteso. Il riepilogo richiedeva inoltre `eventId`/`sessionId` che il trasporto SignalR non normalizzava. Jolpica non aveva ancora pubblicato risultati per `2026/17/qualifying`; il vecchio riepilogo passava direttamente alla sessione futura.

[Cache Serie A osservata](evidence/v087-sport-live-fix-2026-10-10/observed-sport-cache.json) · [SignalR osservato](evidence/v087-sport-live-fix-2026-10-10/observed-timing.json) · [Risposta Jolpica](evidence/v087-sport-live-fix-2026-10-10/observed-jolpica-qualifying.json).

## Comportamento corretto

- **Serie A:** stato in corso/intervallo, freschezza entro 90 secondi e finestra temporale valida precedono le partite future. Punteggio e minuto sono visibili anche quando il badge live rimane da qualificare: la dicitura è «In corso secondo la fonte». Cache/offline/dati scaduti non attivano questa priorità. Fino a tre partite in corso possono comparire nel riepilogo; 5 apre l’elenco completo con l’evento mostrato selezionato.
- **F1:** offset firmati e non firmati sono convertiti correttamente. Il timing viene associato a una sola sessione attraverso GP, tipo e orario, tollerando uno slittamento fino a sei ore; una corrispondenza assente o ambigua disattiva il live. Il gateway MotoGP espone anch’esso le identità già validate del GP/sessione.
- **Qualifiche e altre sessioni:** timing attivo prima; sessione recente conclusa, risultati pubblicati o ultimi tempi del feed dopo; prossima sessione come contesto. Una sessione con orario trascorso e senza dati mostra «risultati in attesa». I risultati pubblicati precedono gli ultimi tempi conclusi. Nessun orario prova da solo il live.
- **Tasto 5:** apre il timing mostrato, i risultati della sessione selezionata o il weekend pertinente. 7 torna alla dashboard Sport. Il dettaglio distingue timing aggiornato, sessione terminata e tempi precedenti, indicando la fonte.
- **Richieste F1:** le qualifiche vengono cercate al numero del GP pertinente; non dipendono più dalla risoluzione di `last`. Cadenze e provider conservati. [Parametri Jolpica](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md) · [Client SignalR FastF1](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/livetiming/client.py).

## Verifica e consegna

21 regressioni delle proiezioni e 13 degli adapter/timing passano sul PC e sulla board. Passano anche navigazione Sport e Motorsport, adapter di 62 superfici/22 contesti, organizzazione Apple e prove della nuova priorità nei tre temi. Il test Motorsport è aggiornato alla dashboard distinta «La mia squadra» e alla necessità di identificare il GP delle fixture timing.

[Qualifica EGLFS Base](evidence/v087-sport-live-fix-2026-10-10/board-proof/eglfs-base/qualification.json), [Functional](evidence/v087-sport-live-fix-2026-10-10/board-proof/eglfs-functional/qualification.json) e [Apple](evidence/v087-sport-live-fix-2026-10-10/board-proof/eglfs-apple/qualification.json): Main reale a 960×640, dati osservati riprodotti in processi isolati, instradamento F1 attivo con stato/orario simulati, cache e scadenza verificati; zero tentativi di connessione e zero messaggi QML. Il primo tentativo nativo mancava del renderer diagnostico richiesto dall’harness; il servizio è stato ripristinato senza installare. Aggiunto soltanto all’ambiente di prova, il renderer è escluso dall’installazione.

[Manifest](evidence/v087-sport-live-fix-2026-10-10/release-manifest.json): 515 file; [delta rispetto alla board precedente](evidence/v087-sport-live-fix-2026-10-10/delta-scope.json): 10 file, di cui tre controlli. [Ricevuta](evidence/v087-sport-live-fix-2026-10-10/board-proof/install-receipt.json): preferenze conservate, Apple Calm 1.6.2 attivo, GUI fresca e pronta, pending nullo, servizio active/running e NRestarts=0; nessun errore QML rilevato. Backup `/var/backups/smartpc-before-v087-sport-live-20261010T145418Z`; prove persistenti `/var/lib/smartpc-dashboard/v087-sport-live-proof/`.

Il [probe successivo sul codice installato](evidence/v087-sport-live-fix-2026-10-10/board-proof/installed-real-timing.json) verifica un nuovo snapshot SignalR reale dalla board e l’associazione alle qualifiche di Singapore. Le prove di sessione F1 **attiva**, latenza e riconnessione durante l’evento rimangono da eseguire; le qualifiche osservate erano già concluse. Nessun flag di certificazione live o notifiche gol viene abilitato. Questa candidata è verificata dopo riavvio del servizio; il reboot reale della rc.2 rimane una prova della candidata precedente.

[Serie A sul display nativo](evidence/v087-sport-live-fix-2026-10-10/board-proof/eglfs-apple/serie-a-in-progress.png) · [Qualifiche concluse](evidence/v087-sport-live-fix-2026-10-10/board-proof/eglfs-apple/f1-qualifying-finished.png) · [Tutti i tempi](evidence/v087-sport-live-fix-2026-10-10/board-proof/eglfs-apple/f1-qualifying-timing-detail.png).
