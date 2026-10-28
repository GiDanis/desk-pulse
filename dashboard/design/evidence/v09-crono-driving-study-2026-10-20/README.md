# Studio Crono — sonde del 20 ottobre 2026

Analisi: [guida, esplorazione, incentivi e viste](../../game-crono-exploration-pace-study.md).

- `board-snapshot.json`: lettura SQLite query-only e dati selezionati del
  checkpoint salvato. Non è lo stato non ancora salvato del learner in RAM.
- `probe_controls.py`, `control-probes.json` e `.txt`: otto configurazioni senza
  apprendimento; tre giri ciascuna e un episodio finito per la contabilità dei
  premi. Le sonde fattore 1,5/1,8 hanno autorità diversa dai modelli attuali.
- `probe_alias.py`, `finite-horizon-alias.json`: coppia di stati solo simmetrici
  con distanza residua diversa e osservazioni indistinguibili.
- `derived-diagnostics.json`: scala dei premi e della traccia GAE; equivalenze
  non scontate, non nuovi pesi ottimizzati.
- `source-scope.json`: riscontro fra sorgenti PC, pacchetto rc.23 e hash
  installati. Le sonde PC non misurano prestazioni native ARM.

Il checkpoint è copiato con directory 0700 e file 0600 fuori dal repository,
in `/tmp/smartpc-crono-study-20261020/crono.json`. Nessun peso o replay incluso
nelle evidenze. Nessuno store aperto in scrittura sugli originali, nessun
riavvio o avvio di sessioni del gioco sulla scheda da parte dello studio.

Riproduzione dalla radice del progetto, con la copia privata disponibile:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=dashboard /home/giuseppe/.cache/smartpc-population-py312/bin/python dashboard/design/evidence/v09-crono-driving-study-2026-10-20/probe_controls.py --checkpoint /tmp/smartpc-crono-study-20261020/crono.json --snapshot dashboard/design/evidence/v09-crono-driving-study-2026-10-20/board-snapshot.json --output /tmp/smartpc-crono-controls.json
OPENBLAS_NUM_THREADS=1 PYTHONPATH=dashboard /home/giuseppe/.cache/smartpc-population-py312/bin/python dashboard/design/evidence/v09-crono-driving-study-2026-10-20/probe_alias.py
```

Fonti primarie consultate il 20 ottobre 2026, con collegamenti e limiti di
applicazione riportati nell'analisi. Le campagne comparative di apprendimento
non sono state eseguite e nessun nuovo default è stato promosso.
