# Chiusura funzionale Auto — 25 ottobre 2026

Consegna di manutenzione **core 0.9.4-rc.3**. La fase funzionale entra in manutenzione; nuovi modelli e apprendimento competitivo sono rinviati e non qualificati.

- [Ricevuta scheda](board/final-receipt.json) e [audit successivo](board/post-delivery-audit.json): 654 hash, servizio pronto/NRestarts=0, dati/preferenze/backup conservati, nessun reboot OS.
- [Perimetro](scope.json), [diff esatto rc.2 → rc.3](runtime.diff), [manifest](release-manifest.json), [distribuzione completa](game-maintenance-0.9.4-rc.3.tar.gz) e [hash archivio](distribution.json). Solo protocollo/fine gara/versione modificati; nessuna rete o nuova ricetta inclusa.
- [PC](pc-receipt.json): 19 controlli automatici, sedici sessioni dei quattro learner; [gara corrente a quattro/tre giri](pc-fresh-race/report.json), classifica collegata all'ID della nuova sessione. [Log unità](pc-units.log), [regressioni](pc-finish-window.log).
- ARM: [unità](board/arm-units.log), [regressioni](board/arm-finish-window.log); [Base](board/base/report.json), [Functional](board/functional/report.json), [quattro modalità Apple](board/prior-apple-mode-checks/report.json) e [gara corrente Apple](board/apple/report.json). La riga gara nella prima cattura Apple non è utilizzabile; sostituita solo dalla gara con ID corrente. Quindici sessioni conteggiate, nessun doppio conteggio.
- [Matrice estesa interrotta manualmente](interrupted-extended-matrix/README.md) e [cattura della classifica precedente esclusa](stale-result-capture/README.md): conservate per audit, non presentate come prove di arrivo corrente.
- [Test corretto](check_game_session_ui_fresh.py), [programma di consegna](native_game_close.py), [audit](audit_game_close.py), [regressioni](check_finish_window.py). Prove su copie private; schermate di test a 960×640, non catture della produzione corrente.

Le verifiche dimostrano il perimetro funzionale dichiarato, non apprendimento scientifico, FPS ottici, tastierino reale o uso prolungato. Per il prossimo modulo usare il manifest della distribuzione come baseline: il checkout principale conserva anche prototipi non consegnati. [Report di chiusura](../../v094-game-functional-closure-report.md).
