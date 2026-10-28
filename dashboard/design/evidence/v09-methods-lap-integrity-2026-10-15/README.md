# Prove private · 15 ottobre 2026

Analisi: [contratto/metodi/giri](../../game-methods-lap-integrity-analysis.md).

- `snapshot.json`: riduzione dell’export SQLite in sola lettura, con hash e timestamp; nessun peso originale.
- `contracts.json`: passaggio linea con settore mancante, giro pulito, riferimento continuo e fixture sintetica del confine di finestra.
- `gate-recovery.json`: fisica continua reale per 130 s; un’escursione, due passaggi sulla linea, settori che rimangono bloccati.
- `frozen-pilots.json`: popolazioni e controller congelati, scenari accoppiati. I test Controllo sul candidato Passo sono stress di trasferimento del contesto, non il suo compito nativo.
- `phase-transfer.json`, `context-adapter.json`: stessi pesi, confronto fra contesti di inferenza; quattro giri puliti con il valore coerente. Nessuna qualifica scritta nella Dashboard.
- `constant-feature-fold.json`: fattibilità algebrica della conservazione del controller denso; nessun modello trasformato salvato.
- `*-calibration.json`: 50 mila nuove transizioni per metodo, un seed ciascuno, su `GameStore` temporanei; non sono benchmark di convergenza o throughput board.
- `ppo-numeric-gates.txt`: differenze finite del gradiente e bootstrap alla finestra, due gate mirati già disponibili nel progetto.
- `scope-verification.json`: processo/runtime ancora invariati a fine studio; l’allenamento originale può avanzare nel frattempo.

Per riprodurre usare Python 3.12 con NumPy/PySide6/NEAT e `OPENBLAS_NUM_THREADS=1`. `read_snapshot.py` va eseguito come utente smartpc sulla scheda: apre SQLite con `mode=ro`, non costruisce GameStore, scrive soltanto in una cartella diagnostica privata esterna al gioco. L’export completo contiene pesi e non viene incluso qui.

Esempi PC dalla radice del progetto, con un export privato disponibile:

```sh
OPENBLAS_NUM_THREADS=1 python dashboard/design/evidence/v09-methods-lap-integrity-2026-10-15/probe_contracts.py /tmp/contracts.json
OPENBLAS_NUM_THREADS=1 python dashboard/design/evidence/v09-methods-lap-integrity-2026-10-15/probe_pilots.py /tmp/export-privato.json /tmp/frozen.json
OPENBLAS_NUM_THREADS=1 python dashboard/design/evidence/v09-methods-lap-integrity-2026-10-15/probe_context_adapter.py /tmp/export-privato.json /tmp/adapter.json
OPENBLAS_NUM_THREADS=1 python dashboard/design/evidence/v09-methods-lap-integrity-2026-10-15/probe_calibration.py --source /tmp/export-privato.json --name PPO --output /tmp/ppo.json
```

Gli script non installano correzioni. Il fixture di finestra sintetico non va presentato come una registrazione fisica di 60 s; il difetto di riarmo è confermato separatamente da una traiettoria fisica. Nessuna misura ottica, input fisico o gara neurale con avversari è stata acquisita.
