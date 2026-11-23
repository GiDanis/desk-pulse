# Apple Calm v0.10.2 · evidenze di analisi

Tutte le nuove immagini sono concept con dati sintetici. Nessuna prova del
runtime installato, della GPU ARM o del pannello fisico è stata svolta qui.

- `screens/`: 15 schermate di proposta, tutte 960×640.
- `preview.html`: involucro locale per revisionare il concept della conversazione.
- `review-concept.cjs`: cattura e controlli del solo concept nel browser.
- `concept-review.json`: interazioni, errori e geometrie a quattro larghezze.
- `contrast-check.json`: contrasto sRGB dei token su superfici opache.
- `artifact-checks.json`: dimensioni, hash del frammento e collegamenti.
- `source-audit.json`: hash dei sorgenti letti e limiti del tentativo di
  cattura della baseline; nessun esito di preflight è stato inventato.

Fonte della proposta e analisi: [documento](../../v0102-apple-calm-readability-analysis.md).
Il frammento resta in `dashboard/design/concepts/v0102-apple-calm/`.

La cartella [refinement](refinement/README.md) contiene 26 tavole della seconda
passata grafica, compreso Meteo corretto a tre giorni e verificato nuovamente;
le prime 15 mantengono il proprio perimetro di verifica.

La cartella [data-audit](data-audit/README.md) conserva otto casi esistenti del
runner passati e 14 sonde aggiuntive: tre famiglie di difetti, una decisione di
presentazione e un caso di validazione da correggere. Sono prove locali dei
sorgenti/DTO/formatter, non dei provider reali o della board.

Riferimenti consolidati: [audit dei dati](../../v0102-apple-calm-data-audit.md)
e [piano completo](../../v0102-apple-calm-implementation-plan.md).
