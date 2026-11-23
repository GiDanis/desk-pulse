# Conservazione e pulizia Orange Pi — v0.10.1

La board contiene il runtime attivo, i dati correnti e un rollback completo recente.
Sorgenti di ricerca, benchmark, catture e backup storici restano sul PC, fuori da
Git quando contengono credenziali o dati privati.

## Distribuzione

- Usare `scripts/package-dashboard.py build --baseline-manifest …` per una
  manutenzione derivata da una versione installata. Preparare i sorgenti dalla
  baseline e applicare soltanto le modifiche qualificate: il filtro del manifest
  limita i nomi, non garantisce da solo che il contenuto dei file sia invariato.
- Il runtime esclude gli script radice `check_*.py` / `verify_*.py` e i renderer
  diagnostici. Il pacchetto `--diagnostics` conserva gli strumenti. Fixture, API,
  CLI temi e risorse dichiarate rimangono disponibili.
- Non confondere il numero di versione del checkout con i byte installati.
  Verificare il manifest e registrare la baseline e il delta della consegna.

## Backup e prove

- Prima di una consegna arrestare ordinatamente il servizio e copiare runtime,
  configurazioni, dati applicativi e database con relativi journal/WAL.
  Conservare proprietari e permessi. Verificare i database sulla copia.
- Conservare sulla board il rollback della precedente release verificata.
  Prima di sostituirlo esportarlo sul PC e verificare contenuti e metadati.
- Usare una sola cartella di lavoro `/var/lib/smartpc-dashboard/maintenance-work`.
  Esportare report/catture sul PC e rimuovere la cartella al termine della consegna.
  Non lasciare altre copie complete di progetto o ambienti Python per ogni prova.
- Nessuna cancellazione automatica in base alla sola anzianità o al nome.
  Lo script `apply-board-archive-cleanup.py` valida un inventario contro una
  ricevuta di verifica esterna, controlla le modifiche successive e i riferimenti
  dei processi; la cancellazione richiede esplicitamente `--apply`.
- Gli snapshot OS gestiti dall'updater conservano la rotazione esistente di due
  archivi. Non modificare hold, driver, bootloader o modalità di aggiornamento
  durante una pulizia dello spazio.

## Dati protetti

Conservare `.config`, `.local`, gli archivi attivi, i file JSON delle fonti e i
relativi database/WAL, `game-runtime`, `pilot-learner-runtime`, i temi e la loro
quarantena. Non cancellare `dp-kernel-fix/uImage.dpfix` o `boot.cmd.dpfix`: sono
usati dal recupero del display. CopyTrade resta fuori dal perimetro dashboard.

Obiettivo operativo: almeno 8–10 GiB liberi. Prima delle nuove prove controllare
`df`; se il margine manca, esportare le evidenze concluse prima di iniziare una
nuova campagna. Queste regole non introducono job di cancellazione periodica.

## Test e costo delle verifiche

- Il runner `scripts/check-dashboard.py` avvia di default cinque suite rapide e
  stampa un solo riepilogo. Conserva i dettagli nei log e in `checks.json`.
- Per una modifica circoscritta usare `--case` sui controlli pertinenti. Consultare
  `--list` per scegliere, poi leggere solo i log dei fallimenti.
- Usare `--suite core`, `ui` o `all` per modifiche trasversali; mantenere i gate
  PC/ARM/EGLFS pertinenti prima della consegna. Il rapido non certifica una release.
- Dopo un esito positivo non ripetere la stessa matrice se sorgenti, dipendenze e
  perimetro sono invariati. Riutilizzare le ricevute solo per la stessa baseline
  e lo stesso delta verificato; nuovi cambi o errori richiedono controlli mirati.
