# Apprendimento visibile — 20 ottobre 2026

- `board-learning-diagnosis.json`: lettura selettiva degli originali in sola
  lettura. Nessun peso/replay incluso.
- `source-delta.json`: perimetro rispetto al pacchetto rc.22.
- `tests-pc.txt`: 41 test; `tests-new.txt` è un sottoinsieme, non test aggiuntivi.
- `pc-ui/`: Main/Worker privati, schermate e traccia per eventi significativi.
- `prepare_board.py`: pacchetti verificati, libreria ARM originale, copia
  protetta del checkpoint Crono fuori dall'archivio di evidenze.
- `run_board_checks.py`: 15 test ARM e tre prove EGLFS; `finally` ripristina il
  servizio Dashboard. Ogni prova parte da una copia del medesimo checkpoint.
- `install_rc23.py`: gate delle sorgenti esatte, backup, scambio runtime,
  riscontro completo delle tabelle/artefatti/preferenze e PID GUI corrente.
- `board/`: risultati nativi e ricevuta, senza la cartella privata dei modelli.

La traccia GUI conserva soltanto variazioni di aggiornamenti, episodi,
verifiche o candidato. Il tempo dell'ultimo evento non è il tempo finale della
simulazione. Sono prove funzionali; non certificano frame pacing, FPS ottici o
un miglior apprendimento rispetto alla rc.22.

Riproduzione PC:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=dashboard:/home/giuseppe/.cache/smartpc-residual-reference /home/giuseppe/.cache/smartpc-population-py312/bin/python -m unittest check_game_residual check_game_timing check_game_overtaking -q
OPENBLAS_NUM_THREADS=1 PYTHONPATH=dashboard /home/giuseppe/.cache/smartpc-population-py312/bin/python dashboard/check_game_learning_visibility_ui.py --seconds 74 --output /tmp/smartpc-learning-ui
```

Raccolta e rete sono effettive nel worker isolato. Le prove non vengono
importate nei piloti reali. Ricetta, premi, iperparametri e generatori casuali
della raccolta restano quelli della rc.22.
