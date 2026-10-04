# Evidenze della preparazione A0/A1

Acquisite il 4 ottobre 2026 dal checkout `16a92649e3f2e2923a3d5fd84babd13c9f6af689`. Sono un audit di sorgenti e proposte di contratto, non il risultato dei futuri test A0/A1.

- `source-audit.json`: conteggi, SHA dei file interessati, route, dipendenze legacy e usi semantic/accent; confronto locale dei 183 file con il manifest B0 salvato. Nessuna nuova verifica degli hash sulla board.
- `surface-contract-proposal.json`: 44 superfici logiche e relative varianti. Gli ID nuovi non sono registrati nel runtime.
- `api-contract-proposal.json`: 16 famiglie di contesti, 31 action ID proposti e mappa G01–G21. Non è uno schema completo o congelato: i DTO, le allowlist per superficie e il grafo semantico completi sono deliverable A0.
- `board-profile.json`: output del comando B0 `profile --board`, in un processo offscreen separato; Qt/font/registri, non layout/input/performance EGLFS.
- `analysis-review.json`: controlli realmente eseguiti su questa preparazione; distingue verifiche dei documenti e del profilo da test runtime non eseguiti.

## Metodo

Conteggio QML: file `dashboard/**/*.qml`; presentazioni/content ID dal registro principale `dashboard/presentations/registry.json`. I registry delle estensioni non sono inclusi nel conteggio delle 17 presentazioni principali.

Route: unione delle stringhe letterali in `Main.qml` per `pushOverlay(...)` e confronti di `overlay`, più la lista `SettingsPanel.targets`. Revisione manuale delle aperture dinamiche `row.target`, della route `racingSettings` parametrizzata F1/MotoGP e delle condizioni negli overlay Sport/Team/Racing. Le intestazioni residue in DashboardOverlay non sono nuove superfici se non hanno una route attiva. La diagnostica e devPanel sono protetti e non entrano nelle 44 superfici sostituibili.

Accoppiamenti: righe con `context.controller` o `required property var dashboard`. Ruoli: righe con `SemanticStyle.*` o `noticeAccent`. Queste estrazioni sono indizi navigabili, non una completa analisi statica degli usi dei token. Il grafo degli usi effettivi e la verifica dei campi sono lavoro A0.

Hash: SHA-256 sui file sorgenti indicati e sui percorsi del manifest salvato `../theme-authoring-b0-2026-10-03/final-manifest.json`; confronto soltanto nel workspace.

Profilo riacquisito tramite:

```sh
python3 dashboard/theme_pack.py profile --board smartpc@192.168.1.179 --output /tmp/smartpc-a0-target-profile.json --format json
```

Il file prodotto è copiato come `board-profile.json`. Il comando non applica un tema o modifica preferenze/eventi. Le credenziali SSH non sono esportate nel profilo.

## Confine

Runtime, endpoint/polling, preferenze, DB eventi, versione e tag non sono stati modificati. I risultati EGLFS del B0 sono riferimenti pregressi separati. Nessuna prova di A1, palette chiare, nuovi host o bundle è attestata da questi file.
