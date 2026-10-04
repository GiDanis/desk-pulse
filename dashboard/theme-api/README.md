# Contratti pubblici Theme API — A0.1/A0.2

`surfaces.json`, `contexts.json`, `actions.json` e `semantic-roles.json` sono gli input canonici. `generated/` contiene riferimento, schema degli snapshot, blueprint dei tipi QML, metadati, righe impostazioni, requisiti delle fixture e relativi hash. Non modificare i file generati: rigenerarli dagli input.

Il modulo dichiarato è `SmartPC.ThemeApi 2.0`, con stato **contractOnly**: questi file non registrano tipi nel motore QML. La registrazione PySide, gli adattatori e gli host sono A1. Il profilo B0 resta schema 1 e aggiunge `apiFingerprint` e `themeApiContract`; `runtimeModuleVerified` resta falso. Il fingerprint API identifica i quattro contratti, mentre `registryFingerprint` continua a identificare i registri B0. Un hash diverso non determina da solo l'incompatibilità di un minor.

Sono censite 44 superfici, 30 route, 16 contesti, 58 DTO, 30 modelli e 32 azioni. Gli ID delle righe Settings sono stabili anche quando una riga condizionale scompare: il broker futuro deve tradurli nella posizione effettiva. Le azioni sono validate per forma e allowlist della superficie; il loro dispatch richiede ancora il broker A1 e la verifica di lifecycle, generazione, priorità urgente e stato del backend. `readOnly` è un vincolo del contratto, non una protezione già applicata agli oggetti del runtime legacy.

Le 108 varianti sono **requisiti**, non fixture runtime già eseguite. I nuovi ruoli di contrasto sono un grafo di usi ammessi: A1/G21 implementerà risoluzione e controllo delle coppie effettivamente renderizzate. Palette chiare non ancora abilitate.

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

`--qmllint /percorso/qmllint` verifica il blueprint in un modulo sintetico temporaneo: una proprietà corretta deve passare, un nome errato deve fallire. Questo controllo non prova un import nell'app. A1 deve confrontare `contract.qmltypes` con i metaoggetti realmente registrati prima di distribuirlo come SDK pubblico. I numeri nullable usano `QVariant`, i modelli richiedono ancora verifica dei ruoli: non si promette tipizzazione statica o compilazione AOT di ogni binding.

Il validatore Python usa solo la libreria standard, distingue zero/falso/null, rifiuta numeri non finiti, campi sconosciuti e ID di modello duplicati. Lo schema JSON è una vista complementare: l'identità delle righe e le allowlist delle azioni sono verificate dal validatore Python.
