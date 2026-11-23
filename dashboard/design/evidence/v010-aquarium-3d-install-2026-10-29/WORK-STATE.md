# Chiusura consegna3D,29 ottobre2026

0.10.2-rc.2 installata su548file, manifest8f210df92292890d1aac76a35ee3d60f3d53c28a8c9fa38188f8d9a043410dbc. API2.14/71, AppleCalm1.6.5; Acquario aperto, sei individui dei quattro tipi, servizio attivo/NRestarts0.

- `release-delta.json` / `release-manifest.json`: delta selezionato dalla baseline0.10.1, nessun codice/libreria Gioco diverso distribuito.
- `pc-candidate/`, `pc-native-candidate-fixed/`: controlli mirati e workflow grafico. Primo tentativo diagnostico senza Canvas richiesto dall'harness fallito; risorsa aggiunta solo alla distribuzione diagnostica.
- `board/arm-candidate/`: tre suite positive, un errore perché manca qmllint nel target; `board/arm-runtime-with-pc-lint/`:39 runtime test passati e uno skip esplicito della sola lint verificata suPC40/40. Il contratto segnala lo skip del validatore JSON Schema indipendente assente.
- `board/qualification/`:21controlli/tema Base/Functional/Apple sulla rc.1; Apple120s dopo60s:59,9668callback/s, p95 18,069ms, p99 20,178ms, massimo44,517ms, zero stalli>50ms, sei drawcall. Main/Game: navigazione otto famiglie e Start/Pause/Save di Crono in dati privati.
- `board-rc2/`:null guard per mesh in distruzione,21controlli EGLFS brevi, installazione, gestione reale via evdev e persistenza degli stessi sei individui/permanenze dopo riavvio dell'app. Zero problemi QML/grafici nei processi rc.2. Eccezioni di chiusura semafori multiprocessing riscontrate anche nella baseline e conservate come limite distinto.
- `rollback-export-receipt.json`:rollback completo privato verificato3270file/4link,259MB. Board:`/var/backups/smartpc-maintenance/rollback-0.10.1-rc.1-aquarium3d-20261029-121954`. Recupero runtime:`sudo python3 /var/backups/smartpc-maintenance/restore-aquarium3d-0.10.2.py`; preparato, non eseguito come rehearsal.
- `work-export-receipt.json`, `cleanup-receipt.json`:2407file/link esportati e verificati, maintenance-work rimossa. Archivi privati fuoriGit in `/home/giuseppe/Documenti/SmartPC-backups/aquarium-3d-install-20261029`.

Preferenze/config byte-identici, Game database/215artefatti e tutti i precedenti pacchetti/hold conservati; aggiunti soltanto i sei pacchetti Qt dichiarati. Nessun reboot OS. Misura120s attribuita alla rc.1; rc.2 ha il piccolo guard e controllo breve/reale. Fisico/ottica/live/durata estesa/freddo restano aperti; candidata non promossa stabile. Report corrente:`../../v010-aquarium-3d-installation-report.md`.
