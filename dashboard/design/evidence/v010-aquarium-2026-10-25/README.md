# Acquario Calm · evidenze 25–26 ottobre 2026

Candidata 0.10.0-rc.1, API 2.13/69 superfici. Stato di consegna nel [report](../../v010-aquarium-implementation-report.md) e nel MasterPlan; la presenza degli artefatti non equivale a installazione o qualifica fisica.

- `runtime-scope.json`, `delivery-delta.json`, `runtime-selected.diff`: overlay selezionato sulla distribuzione ARM 0.9.4-rc.3, con hash; i prototipi estranei del checkout sono esclusi.
- `runtime-distribution.tar.gz`, `release-manifest.json`: distribuzione ricorsiva, senza preferenze, dati utente o renderer diagnostici.
- `pc-checks.json`, `pc-final/`, `pc-ui/`: controlli controller/motion/API/GC, broker pubblico reale, fixture semantiche e catture. I risultati offscreen non misurano gli FPS del pannello.
- `asset-production.md`, `SmartPC-Theme-API-2.13.zip`, `kit-check.json`: prompt/provenienza degli asset locali, SDK riutilizzabile e verifica degli hash/uso indipendente dal repository.
- `screening-native/`: confronto iniziale rig/sprite6, stress16 e integrazione nei tre temi. Campioni brevi, precedenti al completamento del percorso pubblico delle azioni.
- `development-native/`, `development-receipt.json`: lavoro intermedio con durata interrotta; non chiude la qualifica finale.
- `pre-broker-fix-native/`, `pre-broker-fix-receipt.json`: tre repliche e durata30min positive, prima della correzione della durata degli ActionResult; conservate come evidenza storica, non usate per consegnare la nuova build.
- `run-qualification.py`: precheck isolati PC-equivalenti su ARM e grafica EGLFS esclusiva; sorgenti congelati e controllati prima/dopo ogni caso; riavvio del servizio nel finally. Le prove finali hanno report con intervalli grezzi, risorse e scope software.
- `verify-actions.py`: integrazione pubblica requestAction→broker→Main, positiva e negativa, con attesa dell'effetto asincrono effettivo.
- `install-board.py`, `board-health.py`: verifica del manifest e della corrispondenza con i sorgenti qualificati, backup quiescente e scambio con recupero automatico. Percorsi/risultati effettivi nella ricevuta finale, quando acquisita.

L'assenza di warning inattesi non nasconde la prova negativa dell'immagine: `expectedAssetWarnings` registra separatamente la diagnostica richiesta. Timestamp/pose e stima degli slot appartengono al software; non sono tempi GPU, FPS ottici o latenza HID. Gli archivi e i vecchi risultati restano distinguibili dalla revisione finale.
