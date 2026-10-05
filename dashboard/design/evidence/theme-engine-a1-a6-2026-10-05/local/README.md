# Verifiche locali Theme Engine A1–A6 — 2026-10-05

Questi risultati provano codice locale con Qt 6.11.2/PySide6 e backend offscreen/software. Non provano EGLFS, prestazioni Orange Pi, tasti fisici o provider live. I processi della matrice usano XDG/SQLite/store privati e negano socket/DNS con controllo positivo.

- `new-tests.json`: suite nuove e regressioni per contratto, bundle, SDK, font, icone, tracing. L'unico fallimento iniziale era il conteggio storico `>5` delle violazioni di contrasto: un ruolo ereditato ora viene derivato intenzionalmente; la verifica mirata corretta `>=5` conserva provenienza/variante e assenza di mutazioni.
- `contract-data.json`: 16 vettori strutturali, valori semantici indipendenti e attribuzione dei 108 requisiti canonici. Aggiornati soltanto fingerprint corrente e digest del vettore; i valori non sono stati riscritti.
- `api-runtime-optimized.log`: 29 test della vera API pubblica, modelli Qt readonly, import QML esterno, typeinfo riproducibile e qmllint reale con controllo positivo/typo negativo.
- `api-adapters-final.json`: payload del vero Main normalizzati per 44 superfici/16 famiglie, controlli indipendenti su numeri null/zero/ID e assenza di effetti su provider, navigazione ed eventi. Non significa che esistano 44 nuovi renderer grafici.
- `api-optimization-regressions.json`: preflight Qt, bundle, SDK e contratto ripetuti dopo l'ottimizzazione runtime.
- `check_theme_authoring_ui.log`: import/anteprima/applica da menu normale, sei notifiche, day/night e motion normal/reduced/off, deadline e focus conservati.

Il bundle esempio ha 4 renderer propri e 40 fallback Base espliciti; la prova visuale isolata esercita 72 combinazioni dei 4 renderer e 18 combinazioni ausiliarie (icone, scene, ricette), non 44 redesign.

## Ottimizzazione del bridge DTO

Il profilo `api-profile.log` trova 79 mila letture dei descrittori con deepcopy e 16 mila validazioni ricorsive duplicate per un aggiornamento ricco Home. Lo schema runtime ora compila descrittori immutabili e template indipendenti; la factory valida atomicamente ogni campo modificato prima di pubblicare segnali, mentre i campi posseduti invariati mantengono la validazione precedente. I confronti distinguono esplicitamente false, zero e tipi numerici.

Sul medesimo Home sintetico: prima circa 1.52 s a freddo e 633 ms caldo; dopo `api-profile-final.json` circa 283 ms freddo e 11–12 ms caldo. Sulle 44 superfici: mediana 41.2→2.0 ms, massimo 2369→417 ms, totale 20.86→3.65 s. Le misure locali includono allocazione di DTO e sono confronti di sviluppo: non sono frame time né budget certificati sulla board. `api-profile.log` a freddo usa cProfile e quindi contiene overhead del profiler.

La matrice legacy completa passa tutti gli 8 profili: 136 scenari ciascuno, 1088 esecuzioni, 108 requisiti canonici, zero warning. Tutte le 14 regressioni passano; i due errori iniziali erano indici del vecchio editor e restano nel report originale, insieme ai log dei rerun corretti. `legacy-combined.json`/`legacy-summary.json` aggregano gli esiti risolti senza riscrivere il report iniziale. Il menu ordinario verifica il vero segnale saveFinished e la persistenza di motionOff. L'etichetta ereditata `deferredA1` del runner A0 delimita la corsia legacy; la prova effettiva della nuova API è nei file API sopra.


## Integrazione finale di layout, urgente e adattamenti

Le prove in `final-integration/` usano il vero Main e contesti pubblici su Qt 6.11.2/offscreen, salvo le simulazioni di ack esplicitate dai test unitari. Nessun dato di produzione o richiesta ai provider è necessario.

| Evidenza | Risultato e ambito |
| --- | --- |
| `final-integration/layout-ui.json` | 10 controlli PASS: viewport negoziato/bounded, layout tipizzato, overflow tagliato, area sicura attore, geometria legacy conservata, focus dei nove tasti, annullamento, revisione a schermo intero, attore sospeso senza area compatibile e Apply dopo frame coerente. Zero warning QML. |
| `final-integration/urgent-readiness.json` | 11 controlli PASS sulle sei superfici Avvisi; il visuale urgente perde readiness e il fallback app interviene immediatamente, conservando identità e deadline. Preview, preemption e focus restano verificati; tasti fisici e prestazioni board non sono verificati da questa prova. |
| `final-integration/adjustments.log` | 4 test PASS: allowlist della revisione esatta, rimozione della scala testo ereditata/non consentita, palette automatica quando non adattabile, policy globale Off/Ridotto, editor legacy, getter senza I/O e controlli/coverage nel Main reale. Gli ack dei test unitari sono simulati. |
| `final-integration/profiles.log` | 5 test PASS di persistenza reale QSettings/journal; A/B/ritorno, revisioni e salvataggi falliti. Non certificano un power-cut fisico. |
| `final-integration/settings-api.json` | 13 superfici PASS: ID canonici, range, guardie, metadati draft, operazioni asincrone attese, passaggio semplice/avanzato, ruoli notifiche e nessun effetto provider da Aspetto. Zero warning QML. |

I risultati non chiudono A6: restano budget dispositivo 150 ms e diagnostica 1 ms/8 MiB, verifiche fisiche, endurance e qualificazione dei cinque concept. La matrice board precedente a queste integrazioni è conservata separatamente in `../board/final-pre-layout/`, inclusi i run falliti e i rerun; non attribuire quei numeri al sorgente finale.
