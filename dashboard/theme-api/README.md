# Contratti pubblici e runtime Theme API — A1

`surfaces.json`, `contexts.json`, `actions.json` e `semantic-roles.json` sono gli input canonici. `generated/` contiene riferimento, schema degli snapshot, blueprint dei tipi QML, metadati, righe impostazioni, requisiti delle fixture e relativi hash. Non modificare i file generati: rigenerarli dagli input.

Il modulo corrente è `SmartPC.ThemeApi 2.13`, compatibile con gli import 2.0–2.12. La minor 2.13 aggiunge `aquarium.main`, `AquariumContext` e i DTO `AquariumSnapshot`, `AquariumSpecies`, `AquariumInstance`, con azioni `aquarium.pause/resume`. Il catalogo locale e lo stato sono separati dalle pose QML: nessun provider o aggiornamento Python per frame. I bundle precedenti usano un fallback builtin additivo. La minor 2.12 aggiunge il campo opzionale `ShellContext.clock` di tipo `ClockState`, aggiornato dall’orologio centrale per la barra persistente. La minor 2.11 aggiunge Qualifica, Impara giro infinito e Impara sorpasso all’azione game.mode, e mappe opzionali di griglia, vista allenamento, bot e risultati cronometrati. Le modalità Prova/Campione restano alias storici e non producono nuove qualifiche. La minor 2.10 aggiunge le mappe `GameContext.game.settings` (sezioni, righe, bozza, editing e focus per ID), `tracks`, `trackId` e `drawing`, senza nuove superfici. I menu usano il controller app-owned: game.option.activate apre o conferma un campo, game.option.step ne cambia il valore quando è aperto. game.start sul menu applica la bozza; 7 annulla il campo o torna al livello precedente. Le classifiche sono filtrate per ambito fisico del circuito; la scheda Pilota mantiene lo storico con la provenienza. La minor 2.9 aggiunge `game.driver`, dossier per pilota e fallback per i bundle esistenti; `GameContext.game.dossier` contiene sintesi, profili, sessioni, risultati e storico. Le azioni della scheda usano game.option.activate con target dossier:/session:/event:/reset e conferma posseduta dall’app. La minor 2.8 introduce cinque superfici Gioco e GameContext. La minor 2.7 aggiunge il riepilogo opzionale `dashboardSummary` sui contesti di superficie e due approfondimenti inventario. Le coordinate native e i valori già qualificati sono proiezioni di sola lettura, senza nuovo polling per scheda. La minor 2.6 aggiunge il DTO opzionale `AccountCredits` e `AccountData.credits`: crediti illimitati, saldo disponibile anche a zero e dato assente restano distinti. L’adapter riconosce anche `windowDurationMins` del backend. Le minor precedenti includono contesti Rete, metriche iliadbox, macroarea Sport e shell con geometria negoziata. `PageContext.network` è nullable e il dominio `network` può essere dichiarato dai renderer. `theme_api.bootstrap_theme_api(engine)` registra i tipi PySide e aggiunge l'import path pubblico; `qml/SmartPC/ThemeApi/runtime.qmltypes` è la descrizione usata dal runtime/SDK. Il metadata del validatore conserva **contractOnly** e `runtimeModuleVerified=false`: è il risultato di una verifica statica, non una dichiarazione sull'assenza del modulo implementato. Il fingerprint API identifica i quattro contratti, mentre `registryFingerprint` continua a identificare i registri B0. Un hash diverso non determina da solo l'incompatibilità di un minor.

Sono censite 69 superfici, 24 contesti, 77 DTO, 41 modelli e 61 azioni. `PublicContextFactory` crea i contesti posseduti dall'app e aggiorna snapshot canonici o ingressi legacy attraverso adattatori privati. Le proprietà pubbliche sono read-only, i DTO restano stabili negli aggiornamenti e i modelli applicano diff per identità con insert/remove/move. Il broker verifica forma, allowlist, lifecycle, interattività, preview e generazione; la disponibilità effettiva e la priorità urgente restano controlli del router privato dell'app. Una richiesta senza router viene rifiutata. La consegna asincrona restituisce `pending` e il router completa esplicitamente il risultato; questo evita false conferme di salvataggio o refresh. Le viste legacy rimangono compatibili attraverso i loro ingressi privati.

Le 141 varianti sono requisiti dichiarati nel corpus corrente, con scenari supplementari su otto profili; la matrice legacy e le verifiche degli adapter pubblici hanno ambiti distinti. A1/G21 implementa il grafo di 75 coppie di contrasto e ruoli adattivi; palette chiare e Notte rossa sono esercitate su Main reale. La misura ottica del pannello rimane un gate separato. [Consegna e limiti A1–A6](../design/theme-engine-a1-a6-implementation-report.md).

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

Gioco rc.3 conserva `GameContext` e API 2.8. Le mappe di `rows` del menu aggiungono `description` (spiegazione) e `value` (valore), mantenendo `detail` per i renderer precedenti. `game.progress` aggiunge fase, prove di dieci scenari, tempi/validità e stato del campione verificato; `game.drivers` distingue `hasCandidate`, `hasPolicy` e `verified`. Un modello precedente resta consultabile senza diventare verificato. I renderer leggono queste mappe senza interrogare il worker; il modello delle righe conserva la provenienza dei valori e la cattura dei comandi rimane app-owned.

Gli input canonici dichiarano `apiState=implemented`, policy G21 attiva e adapter delle righe implementato. Il checker statico restituisce `availability=contractOnly`, `declaredImplementation=implemented`, `runtimeModuleVerified=false`: la presenza del codice non viene confusa con il livello della verifica eseguita. Il fingerprint cambia anche quando cambiano questi metadata, senza alterare automaticamente la compatibilità dell'API.

Per `details.open`, una pagina può usare il proprio `contentId` per aprire il dettaglio app-owned, oppure l'identità di un match/evento del proprio modello per una selezione diretta. I tab del dettaglio usano gli ID del modello `tabs`; fixture/classifica Sport usano `sport.fixtures` e `sport.standings` e pubblicano il corrente in `selection.tabId`. `selection` conserva tab, ID e indice effettivi anche nei risultati di sessione/driver. Il refresh accetta l'alias pubblico `weather` come fonte privata `meteo`. Azioni non disponibili nello stato corrente restituiscono errore, senza effetti impliciti.

## Cronometraggio Gioco rc.21 (additivo, API 2.11)

`GameContext.scene` resta una `legacyMap` di sola lettura. Le vetture delle sessioni Qualifica/Gara e dell’anteprima possono aggiungere `timing` (protocollo `lap-timing-1`, layout `thirds-1`). L’assenza dell’oggetto conserva il rendering precedente. Nessuna nuova azione, superficie o dipendenza del tema.

`source` distingue `qualifica`, `gara`, `preview`; `policy`, `revision`, `lapId`, `sectorLap`, `currentValid` e `reason` descrivono provenienza e stato. `personal`/`last` sono null oppure record con secondi simulati `time`, `sectors` (tre durate o null), `clean`, `standingStart`, `partial`, `policy`, `source` e identificativo del giro. `deltas` contiene tre scarti di settore o null; `referenceLabel` dichiara il riferimento congelato. Null significa assente; zero resta un valore misurato. Un record storico può avere il tempo senza settori e appartenere a un modello precedente. L’anteprima non scrive record ufficiali né concede qualifiche.

La plancia condivisa è facoltativa e compare solo nell’isola sicura dell’ovale. Nessuna vettura viene filtrata per mostrarla. Il database conserva un contesto fisico/versione settori separato dalla mappa pubblica e garantisce unicità sessione/pilota/giro; Pausa conferma il salvataggio dopo la persistenza. I consumer precedenti dei campi `lapTimes` restano compatibili in questa fase.
