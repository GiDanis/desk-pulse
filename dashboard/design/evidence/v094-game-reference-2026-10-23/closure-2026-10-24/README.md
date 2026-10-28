# Ripresa Piloti · 24 ottobre 2026

Prove su dati privati, nessuna nuova rete qualificata o installata. Produzione 0.9.4-rc.2 conservata.

- `pc-core-receipt.json` e `pc-core-tests.log`: 28 test, sorgenti stabili durante la suite.
- `pc-ui-{base,functional,apple}.json`: sei casi Main/QML per tema, 960×640, nessun warning; controllo/inferenza senza Torch nella GUI. Le PNG sono catture delle prove private sul PC, non del display corrente.
- `arm-runtime-1/`: prima ripetizione ARM con vero modello a memoria 32, quattro learner, pausa iniziale, autosalvataggio, ripresa e relay Qt. Misure software del worker, non FPS ottici.
- `release-upgrade-tests.log`: quattro controlli della migrazione, incluso aggiornamento con backend invariato. Il primo tentativo del nuovo test aveva un import JSON mancante nel banco; corretto e ripetuto, non era un fallimento della transazione.
- `short-session-retention.log`: conservazione delle radici e pulizia fra sessioni brevi, su archivio temporaneo.
- `preparation-summary.json`, `development/`: solo gruppi di sviluppo completamente conclusi, hash di banca/policy e dati per caso. Le cinque preparazioni sono indipendenti; le varianti sono rifiniture abbinate della stessa preparazione.

La banca finale è separata e non è stata consultata. Un singolo 9/9 nel traffico non chiude P5–P9; le prove di apprendimento e le gare restano distinte dalla correttezza tecnica del software.
