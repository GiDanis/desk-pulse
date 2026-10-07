# Evidenze v0.7.0-rc.1 · 6 ottobre 2026

Il [resoconto](../../v07-implementation-report.md) distingue prove locali, risposte cloud, rendering e limiti fisici.

- `v07-board-live.json`: probe del provider sulla board; due GET, stato attivo, valori normalizzati e nessuna chiave/UID/ID dispositivo nel report. Il primo avvio del kiosk aveva già conteggiato sei GET.
- `v07-casa-ui*.json`, `v07-board-*-eglfs.json`: scenari sintetici worker/UI/scheduler e rendering; quote e orari sono intenzionalmente simulati.
- `v07-board-locked-casa-ui.json`: stessa verifica Qt dopo l'aggiunta della serializzazione dei contatori.
- `v07-casa-fixtures.json`, `v07-contract-fixtures.json`, `v07-api-adapters.json`: quattro nuove superfici in due profili, corpus strutturale e normalizzazione pubblica; copertura storica completa UI non dichiarata.
- `v07-real-cache-render.json`, `v07-real-cache-*.png`: dati di produzione salvati mostrati dal renderer EGLFS, con etichetta esplicita di precedente/cache; harness diagnostico e preferenze isolate, zero chiamate cloud aggiuntive.
- `v07-board-*-captures/`: immagini EGLFS con dati **demo**. Non sono fotografie di dispositivi reali.
- `release-manifest.json`: hash di tutti i 453 file della distribuzione installata; credenziali escluse.
- `v07-install-receipt.json`, `v07-final-install-receipt.json`: backup, versione e conservazione preferenze; la seconda è il record dell'output verificato dell'installazione finale.
- `preexisting-theme-changes.patch`: modifiche già presenti prima dell'implementazione Casa, preservate e non attribuite a questo modulo.
- `v07-*-reboot-health.json`: stato servizio, hash, preferenze, contatore, inventario e identità del boot.

Le prove offline/concorrenza usano risposte simulate. Non sono stati comandati dispositivi, disconnessi gateway o interrotta fisicamente la rete domestica. La quota continuativa del progetto non è stata presunta.

Il reboot ha cancellato i file temporanei della board: i record finali di installazione, health precedente e test Qt con contatore serializzato conservano i risultati osservati nei tool. La PNG reale di overview è stata scaricata; il dettaglio è stato renderizzato/verificato, ma la sua PNG temporanea non è stata recuperata. `capture-real-cache.py` conserva la procedura diagnostica, da usare con checkout sorgente o pacchetto diagnostico.

Riavvio reale concluso: boot ID diverso, 453 hash conformi, servizio active/running con NRestarts=0, preferenze e 16 dispositivi/4 preferiti conservati. Contatore ancora 8: nessuna richiesta Casa aggiuntiva al riavvio in modalità senza quota. La rete era disponibile.
