# Preparazione A0.3 / A0.4 — 4 ottobre 2026

Questi artefatti sono **analisi e piani**, non implementazione del tracer, scenari runtime o nuove misure prestazionali. Il [documento operativo](../../theme-engine-a03-a04-implementation-analysis.md) descrive decisioni, incrementi e gate.

- `source-audit.json`: 197 SHA del manifest A0.1/A0.2 confrontati col workspace, sorgenti/hook rilevanti e metadati canonici.
- `board-baseline.json`: lettura remota di hash, servizio, backend e device tree; nessun restart/probe Qt/stress.
- `historical-baseline-review.json`: ricomputazione dei p95 dai raw report già presenti; distinzione fra le due regole warm. Nessun campione nuovo.
- `trace-plan.json`: identità, clock, buffer, protocollo, metriche e risultati proposti; `runtimeImplemented=false`.
- `fixture-plan.json`: 16 famiglie, input/test esistenti, assegnazione dei 108 requisiti e tre track. Tutti i casi sono `notExecuted`; binding pubblico `deferredA1`.
- `build_plan.py`: ricostruisce audit e piani usando gli input canonici e il manifest storico. Fallisce se i sorgenti runtime non coincidono più con questa baseline; non acquisisce una nuova prova board e non esegue fixture.
- `review_plan.py`: controlla link/anchor, copertura pianificata e assenza di modifiche runtime; produce il report seguente.
- `analysis-review.json`: verifiche di coerenza/documentazione della preparazione, con limiti espliciti.

Per ricostruire i piani sul checkout di questa baseline: `python3 dashboard/design/evidence/theme-a03-a04-analysis-2026-10-04/build_plan.py`. Non usare il successo di questo comando per dichiarare conclusi A0.3/A0.4.
