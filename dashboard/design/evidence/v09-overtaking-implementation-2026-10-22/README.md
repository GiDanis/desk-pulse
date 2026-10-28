# Sorpassi A0–A7 · attuazione del 22 ottobre 2026

**Core 0.9.3-rc.2 installata, 647 hash conformi, GUI pronta e NRestarts=0.** Stato e limiti: [report](../../v09-overtaking-attack-report.md). Ricetta sperimentale non promossa; nessun modello personale qui contenuto.

## Risultati autorevoli

- `final-summary.json`: tutti i 40 gruppi completi, 20 confronti abbinati e gate per ciascun seme.
- `experiment-decision.json`: decisione esplicita di non attivare la ricetta.
- `final-cohorts/`: 40 esecuzioni a 196.608 passi raccolti; candidati, solo e migliore traffico nella banca di sviluppo. Non usare i `.log` per stimare il tempo totale dopo ripresa.
- `heldout/`: 40 policy gara esatte, 58 episodi e due griglie per policy. I file `.lock` sono soltanto coordinamento, non risultati.
- `supplement/`: latenza d'attacco e due griglie a due vetture per policy, aggiunte senza ritoccare i modelli.
- `preparation-controls.json`, `extended-preparation-controls.json`, `dense-controls.json`, `teacher-selection-821.json`: controlli di preparazione e motivi di esclusione.
- `development/`: otto esecuzioni a due semi per scegliere la variante da sottoporre al finale. Gruppi interrotti nei relativi archivi non sono promossi.
- `pc/`, `pc-checks.json`, `personal-copy-migration.json`: test, Main/Worker, nuovo pannello e conservazione delle copie personali.
- `board/`: 56 test ARM più dieci attacco sulla correzione finale, tre temi EGLFS, riapertura e ricevuta acquisiti. `post-install-audit.json` verifica manifest, PID GUI e assenza di profili sperimentali attivati. La ricevuta certifica il codice installato; non qualifica l'apprendimento sperimentale.

## Riproduzione

Runtime PC: Python 3.12 / NumPy / PySide6 6.8.2, `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`. I pesi personali e i checkpoint completi sono in directory private esterne al repository. Per i confronti di fabbrica basta la base già presente nel progetto; non riusare i checkpoint dei piloti reali per scegliere coefficienti.

`final-bank.json` è congelata prima della selezione; `final-source.json` elenca il sorgente del training. `source-at-training/` conserva i cinque file differenti dalla candidata finale, incluse sole diagnostiche, metadati di versione, ripristino dei vecchi test e protezione del migliore tattico. `source-equivalence.json` verifica che ogni training candidato abbia al massimo una proposta tattica accettata: la nuova protezione non cambia questi percorsi. `metadata-parity.json` confronta traiettorie e premi identici su tre casi numerici congelati; non è una prova generale di convergenza.

`train.py` riprende checkpoint atomici e non scrive modelli nel repository. `retry_final.py` valida tutti gli hash della copia congelata prima della ripresa. **Non rilanciare `run_final.py` su risultati esistenti:** prepara una copia nuova e ricopia i sorgenti correnti; usare una directory nuova o la ripresa congelata per evitare di attribuire vecchie esecuzioni al nuovo codice.

`evaluate_final.py` valuta soltanto la policy gara congelata, non seleziona un candidato guardando i risultati. `summarize.py` rifiuta gruppi incompleti. Semi di training 741–745, sviluppo 976101–976103, verifica interna 973101–973103, finale 977101–977305; le griglie hanno semi dedicati 977402/977404 e 977501/977502.

## Incidenti e limiti di misura

`storage-recovery.json`: trasferimento della sola directory privata di prova su SSD dopo quota `/tmp`; 1.513 file preservati per hash. Alcune transizioni sono state rieseguite dall'ultimo salvataggio: i budget finali contano i passi trattenuti, senza dichiarare uguaglianza del costo reale totale. `quota-resume-results.json` e i 40 JSON finali sono autorevoli rispetto agli errori iniziali di `final-progress.json`.

`heldout-before-unique-metrics/` conserva report diagnostici superati: non unirli al finale. L'abortita permutazione 822 non ha prodotto un modello completo qualificabile. Nessun successo del docente, test GUI o singolo seme viene presentato come apprendimento generalizzato.
