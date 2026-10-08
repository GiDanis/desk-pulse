# Corpus runtime A0.4

Il catalogo contiene 108 requisiti canonici, uno scenario per requisito, e 28
combinazioni supplementari: stato partita × tab calcio, MotoGP × tab e stati
meteo. Le otto configurazioni comprendono Base Day/Night × Normal/Reduced/Off e
Functional Day Normal / Night Reduced. Gli input e gli expected sono versionati
e verificati per hash; non si aggiornano automaticamente quando cambia un DTO.

`contractData` valida 16 contesti strutturali e vettori indipendenti per zero,
false, null e input non validi. `legacyUi` carica Main e provider reali con seed
sintetici. `publicApiBinding` resta **deferredA1**: non viene registrato un modulo
finto SmartPC.ThemeApi 2.0. Le suite aggiuntive verificano notifiche, timer di
otto secondi, errori/timeout, callback superate, persistenza, focus e selezioni.

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python3 dashboard/check_theme_runtime_fixtures.py --track all --regressions --output /tmp/theme-fixtures.json
python3 scripts/package-dashboard.py build --diagnostics --output /tmp/theme-diagnostic/dashboard
```

Ogni profilo/suite usa un processo con timeout, XDG_CONFIG/DATA/CACHE/STATE,
theme store, cache e SQLite privati. DNS/socket sono negati prima dei provider;
un controllo positivo verifica che il blocco e le sonde sugli effetti funzionino.
Il clock wall dei moduli di dominio è controllato localmente, il clock Qt e
perf_counter rimangono reali. Nessuna credenziale, cache o DB del kiosk viene
usata. Le combinazioni non applicabili sono dichiarate nel catalogo.

Il package normale esclude `renderers/`; per la matrice legacy occorre il
checkout sorgente o il package **diagnostic**, identificato dal proprio manifest.
Il renderer Canvas è registrato soltanto dal runner e non dai temi installati.
Una selezione `--profiles` / `--select` riporta esplicitamente copertura parziale.

Per aggiungere un caso: definire payload ed expected indipendenti, route, azioni,
barriere dei worker, effetti consentiti e assert; aggiornare gli hash del catalogo
dopo review. Non trasformare una label o un caso non eseguito in PASS. Le fixture
non attestano provider live, tastierino fisico, rendering GPU o prestazioni EGLFS.
