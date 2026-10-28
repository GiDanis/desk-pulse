# Evidenze rc.7 — impostazioni e circuiti

- `pc/`: verifiche dei kernel, persistenza, curriculum, contratto e runtime API; walkthrough GUI, dossier, NEAT, griglie e gare apprese.
- `matched/` e `learning-comparison.json`: cinque semi per gruppo e 6.400.000 passi per esecuzione; stessi semi/architettura, partenze indipendenti. I passi contano tutte le posizioni della popolazione.
- `fresh-N` / `transfer-N`: confronto esplorativo a 60 generazioni, con passi diversi; distinto dal confronto principale. Nessun controller nelle azioni dei learner.
- `board-native/`: screenshot EGLFS 960×640, tre temi, controlli/archivi isolati, gare, NEAT e sessione PPO di 30 minuti. Ultimi aggiustamenti di rosa qualificata/griglia/cache geometrica verificati separatamente nella matrice finale; il soak riguarda il training PPO standard, non certifica ogni combinazione o FPS ottici.
- `board-install/`: controlli manifest/preferenze/piloti, backup, installazione e reboot; ricevuta scritta solo dopo verifica.
- `package.json`, `source-proof.json`, `kit.json`: distribuzione e kit API 2.10, archivi privati esclusi.
- `previous-installation.json`: baseline rc.6, documento storico.

Le prove che importano politiche apprese usano soltanto archivi privati; nessun pilota utente riceve pesi o reset. Dati falliti delle griglie affiancate conservati in `pc/race-four-physics.json`. La ritenzione ovale dei pesi tecnici non indica perdita dell'archivio: i campioni originali restano intatti.
