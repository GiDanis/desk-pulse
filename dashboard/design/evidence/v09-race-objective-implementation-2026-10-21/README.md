# Evidenze ricetta da corsa rc.27

21 ottobre 2026. [Report della consegna](../../v09-racing-objective-report.md), [studio e fonti](../../game-racing-reward-objective-study.md).

## Mappa delle prove

- `scientific-receipt.json`: tutti i semi completati, budget, risultati iniziali/finali, costo raccolta/update con verifiche separate, contatori ed hash. Le campagne respinte e incomplete non scelgono i default.
- `baseline/`, `reward-only/`: confronti iniziali a fattori fissi. `retained/` e `episode-retained/`: configurazioni scelte dopo le prove di sviluppo. `production/`: cinque nuovi semi 41–45 per ciascuno dei quattro metodi. `extended/`: PPO vecchio/nuovo a 196.608 passi su cinque semi accoppiati.
- `rejected-development-curriculum.json`, `routed/`, `multi-step/`: primi esperimenti influenzati dall'errore dei circuiti parziali. Non sono prove valide del vantaggio del multi-step.
- `circuit-fixed/`, `episode-noise/`, `ppo-horizon/`: alternative non selezionate; i job fermati sono espliciti in `unselected-stopped-jobs.json`.
- `cohort-sources.json`, `source-snapshots/`: sorgenti congelati separati per coorte, inclusi gli asset iniziali. `source-parity.json` e due file `*-source-fresh.json`: parità esatta di learner/world su 4.000 tick per metodo e confini del curriculum dopo il delta finale del contatore. È una sonda di equivalenza, non la ripetizione completa di tutte le campagne.
- `physical-reference.json`: 27 alternative fisiche, migliore finita e repliche nominali/grip ridotto. Previsione geometrica e tempo realmente percorso sono distinti.
- `saved-migration-check.json`: quattro checkpoint reali su copie, attore in solo preservato, traffico consolidato dal proprio campione, hash originali e ripresa esatta. `saved-traffic-check.json`: regressioni dei candidati originali che motivano la conservazione dello snapshot stabile.
- `saved-continuations/`: continuazione delle quattro copie, **soltanto metriche/hash**; pesi personali completi privati. `before-epoch-fix/`: esito precedente di Tattico, conservato. Anche la ripetizione corretta non migliora il suo migliore in questo budget.
- `independent-validation.json`: cinque semi nuovi per migliore solo e policy gara delle quattro copie, più cinque griglie miste complete. `independent-final-attribution.json` conferma gli stessi snapshot Tattico dopo la correzione dell'epoca. Arrivi, contatti, limiti e selezione dell'esperto traffico sono riportati.
- `tests-final.log`, `tests-final-sessions.log`: 91 + 10 casi PC sul codice finale. Tre oggetti Qt non raccolti al teardown generano un ResourceWarning; nessun fallimento dei test. `pc-final.log` è il tentativo di sviluppo prima delle tre riparazioni, non la ricevuta finale.
- `pc-ui/`: Main/Worker reali isolati; Base e Apple, quattro learner e cinque auto. Nessuna misura ottica degli FPS. Le immagini Apple sono state ispezionate a 960×640 e textScale 1,1.
- `board/`: test ARM, tre temi EGLFS, Qualifica GUI, gara completa e preservazione degli originali. `source-checks-before-epoch.json` identifica il codice del walkthrough; il supplemento `final-epoch-tests.txt` copre il delta finale di curriculum/migrazione, senza cambiamenti GUI/inferenza/fisica/premio. Manifest finale e ricevuta distinguono l'installazione.

## Riproduzione

Usare il Python 3.12 del progetto, NumPy e PySide6/Qt 6.8.2 per la UI. Per l'audit autograd aggiungere il target Torch di riferimento. BLAS/OMP a un thread; i tempi reali di campagne concorrenti non sono confronti di velocità del dispositivo.

`train_racing.py` accetta metodo, seme, variante, budget, output e checkpoint opzionale. `campaign.py` orchestra le repliche contro una directory sorgente esplicita, senza cambiare il runtime. `summarize_campaigns.py` produce il riepilogo senza scegliere da gruppi incompleti. Gli esperimenti riportano zero interventi del docente sugli attuatori e zero etichette del docente nei dati RL.

`reference_bank.py` costruisce il riferimento fisico. `check_saved_migration.py`, `train_saved.py` e `validate_final.py` richiedono l'esportazione privata indicata nei loro sorgenti. `finalize_saved_outputs.py` separa i modelli personali dalle metriche pubbliche. Le copie reali non sono modelli distribuiti come campioni.

`prepare_board.py`, `run_board.py`, `prepare_final_board.py`, `qualify_final_delta.py` e `install_rc27.py` documentano la procedura effettiva; **non vanno rilanciati indiscriminatamente sulla produzione**. Verificano manifest, stato fermo, copie private, backup, preservazione e rollback. Il servizio viene sempre riavviato dopo le prove.

## Limiti

La base supervisionata iniziale è comune ai semi; preparazioni indipendenti ancora aperte. Banca nominale sull'ovale standard: non qualifica altri circuiti/fondi/veicoli, ore di uso, tattica generale o FPS ottici. I risultati del riferimento offline non sono miglioramenti appresi. La copia reale Tattico senza guadagno e i contatti in gara restano nel riepilogo.
