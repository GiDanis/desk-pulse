# Ricetta residuale 4 — 20 ottobre 2026

Report: [incentivi e apprendimento](../../v09-learning-incentives-report.md).

## Campagne e gate

- `campaign.py`, `old-*` / `new-*`: 40 run, cinque semi per quattro metodi e due
  ricette. Candidata comune A, ricetta precedente congelata rc.23.
- `ppo_development.py`, `dev-*`: sviluppo privato; otto run brevi e quattro a
  rumore ampio. Non promossi. Variante PPO prior: cinque run completi allo stesso
  budget, dopo il risultato negativo della candidata comune su PPO.
- `final-bank.json`, `evaluate_final.py`, `final-*.json`: banca congelata prima
  della valutazione. 40 gruppi modello/seme/revisione, 320 casi in totale.
  `final-summary.json` è il riepilogo dei gruppi completi.
- `reproduce_final.py`, `reproduced-*`, `final-source-reproduction.json`: replica
  esatta sul codice finale di un seme per ciascun metodo. I cinque hash dei
  moduli di training restano identici dopo la correzione della fixture GUI.
- `tests-final-pc.txt`: 46 controlli finali. Gli altri log di test sono fasi o
  sottoinsiemi, non ulteriori test distinti da sommare.
- `pc-controls/`: quattro learner e comandi con l'app completa. Il primo
  qualificatore della fixture usava una matrice condivisa con falsi rivali;
  corretto in mondi realmente separati nelle prove native finali. Le campagne
  scientifiche usavano già Episode/mondi separati.

Non usare i tempi PC delle campagne concorrenti come benchmark di wall-clock.
I modelli generati qui sono privati dello studio e non installati nei piloti
dell'utente. La banca di selezione usata durante il training è diversa dal
finale; dopo la lettura di questo finale non si è modificata la ricetta scelta.

## Scheda

`prepare_board.py`, `run_board_checks.py`, `run_board_ui_final.py` e
`install_rc24.py` descrivono copia privata, verifiche, supplemento finale e
installazione con gate. `recover_journal.py` protegge database e hot journal
preesistenti e valida il normale recupero SQLite su una copia prima di farlo
sull'originale. Il suo backup grezzo è esterno alle evidenze.

I quattro checkpoint originali e il database recuperato restano in cartelle
private sulla scheda; nelle evidenze pubbliche vengono raccolti soltanto log,
hash, ricevute e schermate. Non includere `private/` o
`private-recovered-game/` negli archivi di consegna.

Una candidata passata nei gate funzionali non certifica convergenza, vantaggio
su ogni seme, competenza su ogni pista o 30 FPS ottici fissi. I limiti dei
confronti e i risultati negativi sono parte del report.

## Consegna conclusa

`board/final-receipt.json`: rc.24 installata, 626 hash conformi, cinque piloti e
72/72 artefatti originali/preferenze conservati; Apple Calm 1.6.3 attivo,
heartbeat GUI del processo corrente pronto, NRestarts=0. Otto test ARM e tre
walkthrough EGLFS finali passati. Migrazione dei checkpoint al prossimo Start.
`board/fixture-correction.json` documenta la correzione del solo qualificatore
diagnostico; `board/source-checks.json` lega le prove finali ai sorgenti installati.
