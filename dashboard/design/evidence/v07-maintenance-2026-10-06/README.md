# Evidenze manutenzione v0.7.0-rc.2

[Interventi, verifiche e limiti](../../v07-maintenance-report.md).

- `baseline.json`: commit di riferimento, stato Git e hash Python all'inizio della revisione. Le modifiche Casa/Theme preesistenti rimangono distinte dalla manutenzione.
- `maintenance-files.json`: hash dei file Python cambiati dalla baseline della revisione e strumenti aggiunti.
- `static-before.txt`, `static-after.txt`, `syntax.json`: 66 segnalazioni iniziali, controllo Ruff finale pulito e sintassi di 136 file Python.
- `core-before.txt`: regressioni nuove osservate prima dei fix su codici osservati e qualità del dato secondario.
- `local/`: primo giro con Qt 6.10.3 e test storici precedenti alle correzioni. Contiene fallimenti; non è il risultato finale e non qualifica Qt 6.10.
- `local-qt68/`: intera suite di 64 controlli con Qt 6.8.2. Include il primo fallimento del flag qmllint incompatibile.
- `local-postfix/`, `api-runtime-qt68.txt`, `api-runtime-qt610.txt`: correzione del flag e gate del contratto pubblico/typo superato. Non attestano il resto dei bundle con Qt 6.10.
- `local-summary.json`: esiti più recenti dei 64 controlli nell'ambiente coerente con la board; indica esplicitamente il report del rerun corretto.
- `board/checks.json` e i `.txt` corrispondenti: 21 controlli mirati offscreen, tutti superati sulla Orange Pi. Ogni processo usa stato e preferenze isolati.
- `board/eglfs-base.json`, `board/eglfs-functional.json` e directory PNG: 11 scenari di provider/UI per profilo con EGLFS/KMS 960×640. I dati sono demo e la quota è sintetica.
- `board/real-cache-render.txt`, `board/real-cache-overview.png`, `board/real-cache-detail.png`: cache di produzione sul display reale, 16 dispositivi/4 preferiti; etichette di dato precedente, nessuna nuova richiesta cloud. Harness diagnostico con preferenze isolate.
- `board/installation.json`, `board/installed-journal.txt`, `board-health-before.json`, `board-state-before.json`: backup, 454 hash verificati, servizio active/running senza riavvii automatici, preferenze/ledger conservati e contatore ancora 8.
- `release-manifest.json`: distribuzione runtime installata. Il pacchetto diagnostico usato per i test include un renderer fixture aggiuntivo, assente dal runtime.
- `install-board.py`, `health-board.py`, `render-real-cache.py`: procedure usate per installazione e prove, con percorsi della sessione. L'installer esegue prove di rendering prima della sostituzione e ripristina il runtime precedente se la verifica successiva fallisce.

Le catture Base della cache reale e Functional demo sono state ispezionate visivamente: nessuna sovrapposizione o dato offline presentato come corrente. Il testo lungo del movimento è abbreviato nella riga Functional; è disponibile integralmente nel dettaglio.

Nessuna prova di modifica fisica dei dispositivi, tastierino fisico, interruzione della rete, reboot del sistema operativo o benchmark GPU in questa revisione. Nessuna credenziale o risposta cloud grezza è inclusa nelle evidenze.
