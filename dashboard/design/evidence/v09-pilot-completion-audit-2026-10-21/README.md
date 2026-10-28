# Audit del completamento dei piloti

21 ottobre 2026. [Studio e piano](../../game-pilots-completion-study.md).

- `board-state.json`: fotografia in sola lettura delle 16:38:38 italiane, sorgenti installati, profili, struttura/contatori dei checkpoint e sessione Crono attiva. Non contiene i pesi neurali. Nessun costruttore GameStore sulla produzione e nessuna scrittura remota.
- `reproduce_menu_block.py`: GameStore temporaneo con i profili acquisiti, GameSettings e GameService reali; conferma della bozza, senza Start o worker.
- `menu-reproduction.json` e `.log`: otto percorsi, sette rifiutati; Crono invariato passa saltando il validatore. Quattro profili neurali rifiutati, tutti validi nel controllo del vecchio schema ottenuto togliendo le sole chiavi nuove. Quella rimozione è diagnostica e non viene proposta come fix.

Il test verifica che i sei sorgenti rilevanti usati localmente abbiano gli stessi hash della board. Gli archivi temporanei vengono rimossi, i profili non cambiano e nessun worker viene creato. Qt/PySide6 6.8.2, Python 3.12 del progetto, BLAS a un thread.

Riproduzione: impostare `PYTHONPATH` sui sorgenti rc.27 identificati dagli hash e lanciare lo script con il Python del progetto. Richiede solo lo snapshot pubblico adiacente, non i modelli personali.

Il risultato dimostra il blocco del contratto nel percorso delle impostazioni; non dichiara corretta una futura correzione, non esegue nuovi addestramenti e non certifica l'apprendimento tattico. Le fonti primarie e la matrice di accettazione sono nello studio. Produzione rc.27, piloti, parametri e training attivo restano invariati.

Correzione successiva: [rc.28 e nuovi test del menu](../../v09-pilot-menu-fix-report.md). Lo script di questa cartella riproduce il bug storico e richiede il sorgente precedente; per verificare il codice corretto usare `check_game_menu.py`.
