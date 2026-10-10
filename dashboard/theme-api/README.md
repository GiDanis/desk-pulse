# Contratti pubblici e runtime Theme API — A1

`surfaces.json`, `contexts.json`, `actions.json` e `semantic-roles.json` sono gli input canonici. `generated/` contiene riferimento, schema degli snapshot, blueprint dei tipi QML, metadati, righe impostazioni, requisiti delle fixture e relativi hash. Non modificare i file generati: rigenerarli dagli input.

Il modulo corrente è `SmartPC.ThemeApi 2.7`, compatibile con gli import 2.0–2.6. La minor 2.7 aggiunge il riepilogo opzionale `dashboardSummary` sui contesti di superficie e due approfondimenti inventario. Le coordinate native e i valori già qualificati sono proiezioni di sola lettura, senza nuovo polling per scheda. La minor 2.6 aggiunge il DTO opzionale `AccountCredits` e `AccountData.credits`: crediti illimitati, saldo disponibile anche a zero e dato assente restano distinti. L’adapter riconosce anche `windowDurationMins` del backend. Le minor precedenti includono contesti Rete, metriche iliadbox, macroarea Sport e shell con geometria negoziata. `PageContext.network` è nullable e il dominio `network` può essere dichiarato dai renderer. `theme_api.bootstrap_theme_api(engine)` registra i tipi PySide e aggiunge l'import path pubblico; `qml/SmartPC/ThemeApi/runtime.qmltypes` è la descrizione usata dal runtime/SDK. Il metadata del validatore conserva **contractOnly** e `runtimeModuleVerified=false`: è il risultato di una verifica statica, non una dichiarazione sull'assenza del modulo implementato. Il fingerprint API identifica i quattro contratti, mentre `registryFingerprint` continua a identificare i registri B0. Un hash diverso non determina da solo l'incompatibilità di un minor.

Sono censite 62 superfici, 22 contesti, 74 DTO, 41 modelli e 48 azioni. `PublicContextFactory` crea i contesti posseduti dall'app e aggiorna snapshot canonici o ingressi legacy attraverso adattatori privati. Le proprietà pubbliche sono read-only, i DTO restano stabili negli aggiornamenti e i modelli applicano diff per identità con insert/remove/move. Il broker verifica forma, allowlist, lifecycle, interattività, preview e generazione; la disponibilità effettiva e la priorità urgente restano controlli del router privato dell'app. Una richiesta senza router viene rifiutata. La consegna asincrona restituisce `pending` e il router completa esplicitamente il risultato; questo evita false conferme di salvataggio o refresh. Le viste legacy rimangono compatibili attraverso i loro ingressi privati.

Le 126 varianti sono requisiti dichiarati nel corpus corrente, con scenari supplementari su otto profili; la matrice legacy e le verifiche degli adapter pubblici hanno ambiti distinti. A1/G21 implementa il grafo di 75 coppie di contrasto e ruoli adattivi; palette chiare e Notte rossa sono esercitate su Main reale. La misura ottica del pannello rimane un gate separato. [Consegna e limiti A1–A6](../design/theme-engine-a1-a6-implementation-report.md).

La copertura confronta registri, content ID, route letterali e il dispatch dinamico dichiarato `row.target`. Usa un lexer conservativo, non il parser completo QML né l'analisi generale dei flussi: route costruite mediante codice arbitrario devono essere censite e verificate durante la migrazione degli host.

Dal repository:

```sh
python3 scripts/generate-theme-api-contract.py
python3 scripts/generate-theme-api-contract.py --check
python3 dashboard/check_theme_api_contract.py
```

Il pacchetto installato include la stessa CLI:

```sh
python3 dashboard/theme_api_tools.py --check
```

`--qmllint /percorso/qmllint` verifica il blueprint in un modulo sintetico temporaneo. `check_theme_api_runtime.py` verifica invece gli oggetti registrati, un renderer fuori dall'albero dell'app, la mutazione vietata delle proprietà e il lint del modulo reale, incluso un nome errato che deve fallire. I numeri nullable usano `QVariant`. I puntatori annidati Python usano `QObject*`: PySide non dispone dei converter per getter con nomi di puntatore Python personalizzati. I loro oggetti effettivi sono istanze dei DTO registrati e il tooling restringe il tipo usando il contratto validato. Colori, numeri non nullable, booleani e stringhe mantengono i tipi Qt nativi. Non si promette compilazione AOT o tipizzazione statica di ogni role di modello.

```sh
python3 dashboard/theme_api.py # rigenera runtime.qmltypes, richiede PySide6
python3 dashboard/check_theme_api_runtime.py
```

`motionPolicy` è disponibile su tutti i contesti di superficie e sulle notifiche per rispettare Off/Ridotto/sospensione senza interrogare Python per frame. `ThemeStyle.tokenSnapshot` rende disponibili le estensioni di token del tema negli snapshot; le facade generate nel pacchetto trasformano quei token in proprietà QML tipizzate. Queste aggiunte sono opzionali nel contratto e conservano la validità degli snapshot precedenti.

Il validatore Python usa solo la libreria standard, distingue zero/falso/null, rifiuta numeri non finiti, campi sconosciuti e ID di modello duplicati. Lo schema JSON è una vista complementare: l'identità delle righe e le allowlist delle azioni sono verificate dal validatore Python.

Gli input canonici dichiarano `apiState=implemented`, policy G21 attiva e adapter delle righe implementato. Il checker statico restituisce `availability=contractOnly`, `declaredImplementation=implemented`, `runtimeModuleVerified=false`: la presenza del codice non viene confusa con il livello della verifica eseguita. Il fingerprint cambia anche quando cambiano questi metadata, senza alterare automaticamente la compatibilità dell'API.

Per `details.open`, una pagina può usare il proprio `contentId` per aprire il dettaglio app-owned, oppure l'identità di un match/evento del proprio modello per una selezione diretta. I tab del dettaglio usano gli ID del modello `tabs`; fixture/classifica Sport usano `sport.fixtures` e `sport.standings` e pubblicano il corrente in `selection.tabId`. `selection` conserva tab, ID e indice effettivi anche nei risultati di sessione/driver. Il refresh accetta l'alias pubblico `weather` come fonte privata `meteo`. Azioni non disponibili nello stato corrente restituiscono errore, senza effetti impliciti.
