# Esecuzione Gioco P0–P9 · 23 ottobre 2026

**P0 funzionale installato nella 0.9.4-rc.2; nuove reti non qualificate.**

- `upstream-demo.json`: demo End2Race originale su sottoinsieme dichiarato, codice/config/checkpoint identificati; non misura SmartPC.
- `private-policy-role-audit.json`: risultati numerici dell’audit su copie dei piloti; nessun peso, replay o credenziale.
- `pc-apple.json`, `pc-base.json`, `pc-functional.json`: Main/QML, quattro piloti × quattro modalità, navigazione/Start/pausa/salvataggio su copie. HID fisico escluso.
- `pc-race-apple.json`: gara da Start al fondo delle impostazioni, tutte le quattro auto rappresentate.

[Report di attuazione e limiti](../../v094-game-reference-implementation-report.md) · [piano](../../game-reference-integration-plan.md).

## Studio e implementazione

- `frozen-prefix-4101.json` … `4105.json`: cinque preparazioni indipendenti, stessa banca di sviluppo e stessi sorgenti congelati, 27 finestre da tre minuti ciascuna. `development-readiness.json` conserva il rifiuto del gate di sviluppo; non è una qualifica finale.
- `teacher-tyres-development-3.json`: docente corretto nelle finestre prolungate. Le altre varianti del docente restano confronti diagnostici.
- `development-*.json`, `frozen-set-gru*.json`, `frozen-normalized-sac*.json`: screening dichiarati, inclusi esiti negativi; nessun nuovo modello attivato.
- `lab-units-final-v2.log`, `checkpoint-units.log`, `set-gru-parity.log`: parità fisica e numerica, ripresa degli aggiornamenti e invarianza ai rivali.
- `pc-temporal-cost.json`, `arm-temporal-cost.json`: costo di inferenza sperimentale con sensori freschi e della fisica, sorgenti/hash dichiarati; non misurano training, gara qualificata o FPS ottici.

`final-receipt.json`, `p0-release-manifest.json`, `p0-source-scope.json`, `arm-unit.txt` e `arm-{base,functional,apple}.json` attestano la consegna P0: 654 hash, dati conservati, tre temi EGLFS, 30 minuti misti/116 cicli Apple. `arm-apple-*` riporta anche monitor, retention del solo archivio privato e cattura della prova. Il flag passed della ricevuta riguarda i controlli funzionali/lifecycle elencati: non certifica tutti i target di latenza, HID, FPS o la nuova ricetta. Pesi, replay e dati personali esclusi da questa cartella.
