# Audit dati Apple Calm

Analisi offline del checkout, nessuna modifica runtime/board o stato utente.

- `targeted/checks.json`: sette casi esistenti selezionati, passati.
- `main-adapter/checks.json`: adattatori del tema, passato.
- `probe-data.py` / `probes.json`: 14 sonde dei veri normalizzatori e del vero
  formatter JS del tema; sette aspettative soddisfatte e sette scostamenti.
  Cinque scenari rappresentano tre famiglie di difetti, uno una convenzione di
  presentazione e uno un caso di validazione numerica. Non è una suite tutta verde.
- `source-hashes.json`: sorgenti/contratti aggiuntivi consultati e controllo
  dell'enum `MatchData.status`, che oggi non ammette `half_time`.

Banco PC Python 3.14.4 / Qt 6.11.2; non qualifica Qt target 6.8.2 ARM/EGLFS.
Le sonde sono diagnostiche conservate con l’analisi, non incluse nel runtime.

Documenti: [audit](../../../v0102-apple-calm-data-audit.md) e
[piano completo](../../../v0102-apple-calm-implementation-plan.md).
