# Studio attacco — 22 ottobre 2026

[Analisi e piano](../../game-overtaking-attack-study.md). Solo lettura della board e simulazioni su copie PC. Nessuna mutazione di runtime, database, piloti o preferenze; nessun riavvio o addestramento di produzione.

## Evidenze

- `board-state.json`: fotografia alle 01:47:39 Europe/Rome, rc.28 attiva/NRestarts=0, ultima sessione in pausa, 14 sorgenti/basi uguali al PC; hash dei checkpoint verificati prima della decodifica. Non è una verifica visiva o l'intero manifest.
- `frozen-probes.json`: 48 casi, tre semi di scenario, candidati/versioni gara/basi, con e senza traffico. Tracce a 1 Hz, statistiche campionate a 10 Hz. Alcuni episodi Memoria finiscono prima dei 60 s. Velocità media dopo 5 s; non è V max o tempo di giro.
- `expert-ablation.json`: tre casi sulla base di fabbrica con esperto A copiato in B; selettore/traffico/attuazione neurale conservati. Controprova causale, non proposta di produzione.
- `mechanisms.json`: saturazione del selettore, premi effettivi, ripartenze del candidato, stato preview/raccolta salvato. Rapporti di premi non equivalgono a ritorni attesi.
- `summary.json`: gruppi completi, costi della sonda, runtime locale e hash script. I tempi PC non sono misure della board né confronti di velocità fra ricette.

Tutte le reti personali rimangono in `/tmp/smartpc-overtaking-study-20261022/snapshot.json`, permessi 0600 dentro directory 0700, fuori dal progetto. I risultati pubblicano hash e metriche, non pesi/replay. Il fallback del probe sui salvataggi del 21 ottobre è esplicito nel codice; **questo run usa la nuova fotografia del 22**, come indicato in `capturedAt`.

## Riproduzione

Dal root SmartPC, per una nuova fotografia in sola lettura (riscrive soltanto i file locali dello studio):

```bash
python3 dashboard/design/evidence/v09-overtaking-study-2026-10-22/capture.py
```

Per ogni comando sotto usare `PYTHONPATH=dashboard`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` e Python `/home/giuseppe/.cache/smartpc-population-py312/bin/python`; eseguire in ordine:

1. `probe.py`
2. `mechanisms.py`
3. `ablate.py`
4. `summarize.py`

Non istanziano GameStore, worker, learner o QML. Gli avversari sono i bot congelati del simulatore, mentre l'ego usa solo inferenza neurale. La libreria nativa locale viene identificata nella ricevuta; nessuna libreria ARM viene eseguita sul PC.

## Limiti e aggiustamenti diagnostici

Tre semi di scenario non sono cinque semi di apprendimento: nessun default scelto o convergenza dichiarata. Arresto assoluto affiancato non osservato con il criterio documentato; accodamento/rallentamento e pochi passaggi sì. L'ablazione aumenta gli eventi di contatto: non chiamarli 74 incidenti indipendenti.

I valori `soloPedal`/`trafficPedal` delle tracce sono ombre ricalcolate **dopo** che il comando effettivo aggiorna gli ingressi dell'azione precedente. Non sono la scomposizione esatta del comando eseguito e non sostengono confronti causali istantanei. Il confronto causale usa l'ablazione fisica abbinata. `passAttempts` nel runtime attuale conta incontri armati, non attacchi deliberati.

Una lettura SSH è stata ritentata dopo timeout; una prima versione dello script `mechanisms.py` aveva una chiave Python riservata (`pass`), corretta prima dell'esecuzione riuscita. Nessuno dei due eventi modifica i campioni. Dopo il run del probe è stato aggiunto il main guard per importare `run` nell'ablazione e chiarito il metadato delle ombre; il corpo numerico della sonda è invariato. Esiti negativi e candidati Memoria/Tattico problematici inclusi.
