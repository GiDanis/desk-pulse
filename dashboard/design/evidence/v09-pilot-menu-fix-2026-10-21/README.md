# Evidenze della correzione del menu rc.28

21 ottobre 2026. [Report](../../v09-pilot-menu-fix-report.md), [diagnosi precedente](../../game-pilots-completion-study.md).

- `source-delta.json`: tre sorgenti modificati, due diagnostici nuovi; algoritmi/fisica/reward/inferenza/tema invariati.
- `menu-tests.log`: quattro test con matrice di 20 combinazioni pilota/modalità, profili vecchi/nuovi, errori specifici, annullamento e Maestro.
- `compatibility-tests.log`: 23 casi di modalità, ricette e profili passati.
- `pc-checks.json`: riepilogo PC. `pc/apple/` e `pc/apple-reopen/`: report e immagini di Main/Worker reali in archivi isolati, menu e comandi del controller, 12 combinazioni di apprendimento e quattro riprese dopo nuova apertura dell'app.
- `pc-learning-proof.json`: differenze effettive degli attori delle dodici sessioni, con hash e norma; nessun peso personale. `check_learning_artifacts.py` rilegge gli artefatti privati del test.
- `board/`: test ARM, walkthrough Base/Functional/Apple, riapertura Apple, gara completa, preservazione degli originali, sorgenti testati e ricevuta di installazione.

I checkpoint originali sono esportati solo come artefatti immutabili dopo aver verificato che non vi siano sessioni in esecuzione. I dati personali completi sono in percorsi privati; non fanno parte delle evidenze pubbliche. I tre piloti prima bloccati non vengono sostituiti con i migliori modelli dei benchmark.

I diagnostici distribuiti sono `check_game_menu.py` e `check_game_menu_ui.py`. Il secondo accetta tema, snapshot privati, tutte le modalità, gara completa ed esportazione/ripristino dell'archivio privato per verificare la nuova apertura dell'app. Richiede Qt/PySide6 6.8.2 e il Python 3.12 del progetto; per la UI Apple serve il bundle con la sua preflight cache. BLAS/OMP a un thread.

`prepare_board.py`, `run_board.py`, `retry_board.py`, `stage_final_diagnostic.py`, `resume_board.py` e `install_rc28.py` documentano la procedura, con verifica dei manifest, backup, assenza di training attivo, isolamento e rollback. Non vanno rilanciati indiscriminatamente sulla produzione. Il primo walkthrough Apple si ferma nel diagnostico dopo la gara già conclusa, per una richiesta di Pausa non applicabile. Log/immagini e sorgente precedente sono conservati; la correzione del solo diagnostico viene verificata ripetendo Apple e riapertura. Base/Functional hanno lo stesso codice di produzione, con il percorso breve del diagnostico invariato. Il fix non migra le ricette o i modelli; la consegna confronta tutte le righe del database e gli hash degli artefatti originali.

I test provano accesso, aggiornamento, salvataggio, ripresa e correttezza della selezione dei partecipanti. Non promettono guadagni a ogni giro, convergenza di ogni checkpoint, tattica generale o FPS ottici fissi. Qualifiche fisiche senza rendering, avvii GUI e gara completa sono separati nei report.

Un secondo adattamento del solo diagnostico evita di richiedere 1.200 passi di raccolta alla breve ripresa off-policy quando una verifica inizia a 168 passi. Il precedente timeout e i suoi dati restano conservati. La ripresa finale richiede 120 passi nuovi per SAC/TD3, nuovi aggiornamenti e salvataggio; PPO rimane a 1.200. Nessuna modifica ai learner o alla cadenza delle verifiche.
