# Evidenze — obiettivo da corsa, 21 ottobre 2026

[Studio e interpretazione](../../game-racing-reward-objective-study.md).

## Provenienza

- Snapshot persistito della board acquisito alle **08:27:05 UTC / 10:27:05 Europe/Rome**. SQLite letto in transazione di sola lettura e artefatti caricati come file, senza costruire `GameStore` o avviare un pilota.
- Baseline `0.9.0-rc.26`; gli hash dei moduli rilevanti sono in `source-snapshot.json` e corrispondono al runtime letto.
- `saved-state-summary.json` contiene contatori e verifiche, senza pesi personali. Non è lo stato in RAM di un eventuale allenamento successivo.
- `frozen-objective-probes.json`: 27 simulazioni su reti congelate, seme iniziale 981001; tutte completano tre giri con zero contatti/limiti. Include tracce, termini del premio e una dimostrazione sintetica dell’ottimizzatore.
- `reward-ordering-audit.json`: 24 simulazioni, seme iniziale 981017, grip nominale/ridotto; 15 successi e 9 ritiri, ricalcolo del coefficiente di sottosterzo sulle stesse traiettorie.

Il secondo seme varia l’inizializzazione dell’episodio, non crea un addestramento indipendente. Gli interventi sul pedale sono diagnostici, non modelli appresi o assistenti installati. Le reti private sono conservate nella copia di lavoro `/tmp/smartpc-race-objective-private-2026-10-21/`; per riprodurre i candidati occorre quell’input, non incluso nella cartella pubblica.

## Riproduzione locale

Dalla radice del progetto, nell’ambiente numerico già disponibile:

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=dashboard /home/giuseppe/.cache/smartpc-population-py312/bin/python dashboard/design/evidence/v09-race-objective-study-2026-10-21/probe_objectives.py
OPENBLAS_NUM_THREADS=1 PYTHONPATH=dashboard /home/giuseppe/.cache/smartpc-population-py312/bin/python dashboard/design/evidence/v09-race-objective-study-2026-10-21/probe_rankings.py
python3 dashboard/design/evidence/v09-race-objective-study-2026-10-21/plot_objectives.py
```

Le prime due procedure scrivono solo i risultati accanto agli script e non accedono allo store di produzione. La terza usa Matplotlib presente nel Python di sistema e ricrea PNG/SVG. Non installano dipendenze né modificano il runtime.

## Controlli eseguiti

Controllati: 27 + 24 risultati, conteggi di validità, conflitto tempo/premio nei tre casi Base/Crono/Memoria del secondo banco, inversione coerente dopo rimozione del solo proxy, hash dei sorgenti ancora invariati e collegamenti locali dei due documenti. Figura ispezionata visivamente. Nessun test o nuova qualifica dell’applicazione dichiarati da queste sonde.

## Fonti

Consultazione del 21 ottobre 2026; collegamenti e limiti nel §6 dello studio. Articoli originali GT Sophy/Fuchs/Evans/Ng/Adam, repository degli autori TUM, documentazione Stable Baselines3/Gymnasium/AWS; resoconto diretto Ray Goh e due discussioni originali Reddit distinti dalle prove scientifiche.
