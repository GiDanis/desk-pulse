# SmartPC 0.8.6-rc.2 — Serie A e squadra preferita separate

La 0.8.6-rc.1 dava priorità alla preferita nel riepilogo Calcio e apriva direttamente quella partita con 5. La correzione ripristina la Serie A come panoramica del campionato e aggiunge una dashboard distinta per la squadra personale, conservando Apple Calm 1.6.0, palette, font, icone e Theme API 2.7.

## Percorsi

- Sport → **Serie A** → **5**: partite della giornata pertinente, comprese quelle delle altre squadre. **2/8** scorre tutto l'elenco; **5** apre qualsiasi partita, **7** torna alla riga selezionata. Dal selettore Giornata, raggiungibile con **2** sopra la prima riga, **4/6** consulta gli altri turni.
- Dalla dashboard Serie A, **8** raggiunge **La mia squadra**. **5** apre calendario, risultati, informazioni e rosa della preferita, con le competizioni disponibili nella fonte. Senza una preferita apre la scelta della squadra.
- Continuando con **8** si raggiungono F1 e MotoGP; **4/6** rimane dedicato agli argomenti. Il Menu conserva classifica e calendari. Disabilitare Calcio nasconde entrambe le dashboard calcistiche.

Il riepilogo Serie A ordina gli appuntamenti per tempo e qualifica del live, indipendentemente dalla preferita. La classifica del campionato e la posizione personale sono separate. Il calendario della giornata usa tutti i record del turno, mentre la vista personale filtra soltanto la preferita; fonte, disponibilità e dati precedenti rimangono espliciti. Nessun nuovo polling o provider.

## Qualifica

[Nove controlli locali mirati](evidence/v086-serie-a-fix-2026-10-09/local-results.json): 18 casi delle proiezioni, Sport, squadra, navigazione, adapter e contratto, più Main nei tre temi. Il contratto esegue 31 test, con una prova opzionale JSON Schema saltata perché il validatore indipendente non è installato. È una qualifica del delta, successiva ai 77 controlli della rc.1.

[Quattro profili EGLFS 960×640](evidence/v086-serie-a-fix-2026-10-09/board/qualification.json): Base giorno, Functional notte, Apple giorno/notte. Ogni profilo attraversa le 16 dashboard massime, prova tutte le dieci partite del turno sintetico, apre la decima, verifica ritorno e selezione, separazione della preferita, scelta senza preferita e visibilità di Calcio. Nessun warning QML e nessuna nuova connessione nei test isolati. Le fixture non qualificano il feed durante una partita reale.

[Delta finale dei nomi in classifica](evidence/v086-serie-a-fix-2026-10-09/board/name-delta-receipt.json): supporta il campo normalizzato `team` oltre a `teamName`; 18 test nativi passati. Cambiano soltanto la proiezione e il relativo test rispetto ai quattro profili, senza modifiche a geometrie, azioni, provider, bundle o contratto. La prova PC Apple viene ripetuta dopo questo delta. Il primo tentativo di quel test isolato mancava del percorso verso il modulo Account già installato; si è fermato prima di arrestare il servizio, poi è stato corretto. Log conservato in `name-attempt-1/`.

[Manifest finale di 513 file](evidence/v086-serie-a-fix-2026-10-09/release-manifest.json), [otto file modificati rispetto alla rc.1](evidence/v086-serie-a-fix-2026-10-09/delta-scope.json), provider e pacchetto Apple Calm invariati. [SDK aggiornato](evidence/v086-serie-a-fix-2026-10-09/smartpc-theme-sdk-v086-rc2.zip). [Installazione](evidence/v086-serie-a-fix-2026-10-09/board/install-receipt.json) e [riavvio reale](evidence/v086-serie-a-fix-2026-10-09/board/reboot-verification.json) conservano tutte le preferenze e Apple Calm 1.6.0; GUI fresca, pending nullo, servizio active/running e NRestarts=0, senza warning QML rilevati.

Backup `/var/backups/smartpc-before-v086-seriea-20261009T195803Z`; delta nomi `/var/backups/smartpc-before-v086-seriea-name-20261009T200522Z`. Prove persistenti `/var/lib/smartpc-dashboard/v086-seriea-proof/`. La candidata non crea tag o promozioni stabili; leggibilità fisica, uso prolungato e verifica dei provider live restano separati.

[Cattura nativa dell'elenco](evidence/v086-serie-a-fix-2026-10-09/board/apple-day/serie-a-all-ten-games.png) · [vista personale finale PC](evidence/v086-serie-a-fix-2026-10-09/apple-day/favourite-dashboard.png).
