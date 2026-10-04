# Theme Engine — consegna A0.1 / A0.2

**4 ottobre 2026 · Europe/Rome · v0.6.6 · branch `codex/v0.6.6-theme-engine`**

Sono implementati inventario pubblico, contratti canonici, validazione degli snapshot e delle richieste, generatore e fingerprint API. È il primo incremento dell'[analisi A0/A1](theme-engine-a0-a1-implementation-analysis.md). A0.3/A0.4 e A1 rimangono aperti. Non viene registrato un modulo QML nuovo né abilitato il formato bundle.

## Consegna

I quattro [input canonici](../theme-api/README.md) descrivono **44 superfici**, **30 route**, **16 contesti**, **58 DTO**, **30 modelli**, **32 azioni** e **75 coppie semantiche di contrasto**. Le **108 varianti** generate sono requisiti delle fixture A0.4, non casi runtime già eseguiti. Le righe Settings hanno ID stabili e posizione legacy esplicita; quelle condizionali vanno tradotte sulla lista effettiva. `menu.activate` è distinta da `settings.activate`, aggiunta alla bozza perché appartiene a un'altra superficie.

`theme_api_contract.py` valida riferimenti, eredità, sola lettura, assenza di handle privati, identità dei modelli, limiti ed enum. Distingue zero, falso e valore mancante, rifiuta non finiti, campi extra, ID vuoti/duplicati e date impossibili. Le allowlist verificano forma e superficie della richiesta; non autorizzano effetti nell'app. Il broker runtime resta A1.

`NotificationContext` conserva il contratto visuale 1: mappe/liste legacy, ritorno booleano di `requestAction`, `formatStamp` e segnale `settleMotionRequested`. I sidecar tipizzati sono opzionali. Il modello pubblico futuro non espone callback, controller o ingressi dell'host; gli attuali oggetti legacy non vengono modificati in questa consegna.

Il generatore produce riferimento, schema snapshot JSON, blueprint `contract.qmltypes`, metadati, righe Settings, requisiti fixture e manifest con hash. `--check` fallisce su file obsoleti, route/content ID non censiti o dispatch dinamico non dichiarato. È un inventario conservativo di sorgenti letterali e siti dinamici dichiarati, non un parser completo QML o un'analisi generale dei flussi.

Il profilo B0 resta `profileVersion: 1` / `profileKind: schema1`. Aggiunge `apiFingerprint` e `themeApiContract`, con `availability: contractOnly` e `runtimeModuleVerified: false`. Una root precedente senza contratti restituisce API indisponibile; una directory parziale non viene ignorata. `registryFingerprint` resta quello B0. La CLI generatrice è inclusa anche nel pacchetto installabile: `python3 theme_api_tools.py --check`.

## Verifiche riproducibili

[Evidenze PC](evidence/theme-a0-contracts-2026-10-04/pc-checks.json): **31 test contratto + 20 authoring B0 + 17 resolver**, tutti passati. Rigenerazione deterministica e controllo di obsolescenza passati. Il blueprint è verificato con `qmllint` Qt 6.11.2 in un modulo sintetico: accessi pubblici corretti passano, `style.surfaec` fallisce. Dipendenze QtQuick/QtQml esplicite e tipi non risolti trattati come errore. Il blueprint non prova importazione o metaoggetti reali nell'app; va confrontato con la registrazione A1 prima del SDK. [Qt: typeinfo](https://doc.qt.io/qt-6.8/qtqml-modules-qmldir.html), [qmllint](https://doc.qt.io/qt-6.8/qtqml-tooling-qmllint.html).

[Pacchetto isolato sulla board](evidence/theme-a0-contracts-2026-10-04/board-contract-checks.json): **30 test contratto passati, 1 saltato**, più 20 B0 e 17 resolver passati; generatore `--check` passato. Il test saltato riguarda il validatore JSON Schema indipendente, assente sulla board; il validatore standard library resta verificato. `qmllint` non disponibile nelle posizioni Qt/PySide e PATH ispezionati: nessuna certificazione del blueprint su Qt 6.8.2.

[Profilo isolato board](evidence/theme-a0-contracts-2026-10-04/board-staged-profile.json): Qt **6.8.2**, PySide **6.8.2.1**, nuovo fingerprint presente, registri B0 invariati. È un probe offscreen, non una misura EGLFS. La [compatibilità con root precedente](evidence/theme-a0-contracts-2026-10-04/old-board-compatibility-profile.json) è verificata senza confondere assenza del contratto e import QML disponibile.

[Regressione UI B0 sulla board](evidence/theme-a0-contracts-2026-10-04/board-ui-regression.json): menu reale di importazione/selezione/applicazione, preferenze isolate, sei host Avvisi pronti in giorno/notte × Normale/Ridotto/Off; focus e deadline conservati, nessun warning QML. Usa backend offscreen, dati sintetici e tasti Qt; non è una pressione umana sul tastierino né un nuovo collaudo API 2.

[Revisione sorgenti](evidence/theme-a0-contracts-2026-10-04/source-review.json): tutti i **69 QML invariati** rispetto al manifest B0 `a7fd705ca0078e02c38f1b18c94b3a42ee342955`. Il pacchetto cresce da 183 a **197 file**; unico file distribuito preesistente modificato: `theme_probe.py`. Nessuna modifica a provider, polling, persistenza eventi o composizioni. Il packaging ora include `.qmltypes`.

## Distribuzione

Distribuito `/opt/smartpc/dashboard` dal commit **`0b41e0c35c7ba14d59c205b14e77c0338be70c04`**, manifest pulito **197 file**, versione **0.6.6** invariata. [Manifest installato](evidence/theme-a0-contracts-2026-10-04/installed-manifest.json), [prova di installazione](evidence/theme-a0-contracts-2026-10-04/installed-board-proof.json). Tutti gli hash e l'insieme dei file distribuiti coincidono; servizio `active/running`, `NRestarts=0`, backend `eglfs` / `eglfs_kms`, nessun warning QML rilevato nel journal dall'installazione. È un controllo dell'avvio del runtime esistente: nessuna nuova prova prestazionale, reboot o rendering API 2.

Il [profilo acquisito dal servizio installato](evidence/theme-a0-contracts-2026-10-04/installed-board-profile.json) restituisce fingerprint API e stato `contractOnly`, mantenendo schema 1 e `boardRuntime: notVerified` per il probe offscreen. Non eleva l'avvio EGLFS a certificazione di nuovi renderer.

Preferenze: SHA prima/dopo identico. Backup software e stato utente in `/var/backups/smartpc-theme-a0-20261004-0b41e0c`; runtime precedente conservato anche in `/opt/smartpc/dashboard-a0-previous-0b41e0c`. Lo stato utente è copiato a servizio fermo, prima dello scambio. Nessun DB è stato resettato o sostituito; i test UI usano SQLite e preferenze isolate. Il rollback non è stato eseguito in questo incremento.

## Confini e prossimo incremento

Il fingerprint API è `30013160355ad8ccb3f7c3e39569061e6f4cd9aa64893ea2444fa8a48901cec0`; quello B0 resta `ec7c2c887519b354a748c8fad07e5c02db2a447a425e3eaec2d0f536c3e1d3d6`. L'hash attesta il contenuto: compatibilità richiede versioni e capacità, non identità esatta del fingerprint.

A0.3 aggiungerà tracing dalla richiesta al primo frame coerente e analizzerà il residuo già misurato di 155,921 ms. A0.4 trasformerà i requisiti in fixture eseguibili di dati/stato/UI. A1 implementerà registrazione PySide/QML, modelli, broker, shell/overlay host, adattatori e ruoli semantici G21. La grafica rimane inizialmente quella attuale. Risoluzione adattiva dei colori, palette chiare, lifecycle nuovo e bundle QML autonomi non sono consegnati da questi contratti.
