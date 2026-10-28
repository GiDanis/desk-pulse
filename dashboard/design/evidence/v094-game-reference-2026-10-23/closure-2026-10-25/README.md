# Piloti · verifiche del 25 ottobre 2026

Produzione conservata nella **0.9.4-rc.2**, nessun nuovo modello attivato e nessun reset personale. Tutti i nuovi modelli, archivi e qualifiche cronometrate di queste prove sono privati. La banca finale scientifica non è stata consultata.

## Lettura delle prove

- `pc/current-pc-core-*`: nucleo corrente, test con hash prima/dopo. Le ricevute precedenti sono snapshot distinti, non prove retroattive del sorgente nuovo.
- `pc/partial-pause-before-fix.log` e `pc/partial-pause-transport-tests.log`: il test del comando da 2 MB fallisce sui sorgenti congelati precedenti e passa sulla correzione. Un frammento ricevuto viene completato prima di iniziare un altro aggiornamento; il canale inattivo rimane non bloccante.
- `pc/compact-*`: checkpoint senza copie testuali ridondanti della preparazione, optimizer/RNG/mondo esatti e confronto di dimensione. Non è una misura di accelerazione ARM.
- `native/`: precedente matrice EGLFS a 960×640, tre temi e 18 casi del prototipo con sola lettura finale addestrabile.
- `arm-repeat/`, `arm-plastic-received/`, `arm-retention-received/`: snapshot ARM separati, gradienti reali e ripresa esatta; metriche dei frame prodotti e ACK durevoli. Non sono FPS ottici.
- `development/`, `training/`, `development-summary.json`: soltanto gruppi di sviluppo completi, 27 finestre da 180 s ciascuno. Architetture e ricette diverse restano confronti distinti; non tutti gli esiti appartengono alla medesima banca/sorgente. Le coppie BC/RL provengono dalla stessa banca congelata.
- `current-readiness/`: ripetizione delle cinque basi selezionate sulla medesima banca/sorgenti. Quattro superano il prerequisito; 4102 fallisce una manovra in curva. Nessuna qualifica finale.
- `pc/release-readiness-decision.json`: guardia di attivazione realmente esercitata in sola lettura su queste evidenze, proposta rifiutata. Nessun certificato sintetico inserito fra i dati scientifici.

## Gare e visibilità

`races/independent-base-grid-{2,5}.json` misura gare headless con preparazioni diverse: tutti arrivano, ma sono presenti contatti. `allCarsVisible=false` è intenzionale: la simulazione senza GUI non dimostra visibilità sul display.

`pc-reference-races-apple-final/report.json` proviene dal vero Main/QML, con Maestro e quattro copie della medesima preparazione neurale. I tempi per consentire la griglia sono stati misurati facendo guidare realmente i modelli nella stessa fisica, con lancio escluso; non sono una qualifica scientifica. La prima prova con finestra fissa di 30 s dal vincitore è conservata in `races/pc-races-before-finish-window.json`. Dopo la correzione: due/cinque auto su tre giri, tutte arrivate, 4.378/4.663 campioni con sagome contenute nella scena e quattro viste. Le PNG sono catture delle prove private, non del display corrente. L'arrivo non certifica assenza di contatti.

La decisione di release resta negativa finché non sono superati preparazione comune, guadagno RL sulla propria base in almeno quattro di cinque preparazioni, sicurezza, finale e gare con i pesi esatti da consegnare. I test tecnici del codice non sostituiscono queste prove.

## Ripetizione nativa finale

`native-compact/reference-native9-receipt.json` lega la prova ai sorgenti runtime finali, 82 corrispondenze con il PC. Sei test ARM e 18 sessioni dei tre temi, più gare native 2/5 a tre giri. Tutte arrivate e visibili: 3.005/2.121 campioni geometrici, quattro viste, nessun warning QML. Le prove Native7/8 fallite prima della correzione sono conservate negli stessi allegati e non contano come successi.

`native-compact/native9-post-audit.json` è la lettura finale: 654 hash del runtime originale conformi, dati/preferenze uguali al backup, servizio attivo/NRestarts=0 e heartbeat fresco. `installed=false` rimane intenzionale: queste prove non attivano i modelli sperimentali. Nessun reboot OS.
