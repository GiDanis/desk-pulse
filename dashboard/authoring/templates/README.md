# SmartPC Theme SDK 2

Questo kit contiene il codice degli strumenti, il modulo QML pubblico, i contratti e le fixture sintetiche. Non richiede il repository originale. Richiede Python e PySide6 compatibili con il dispositivo; il kit non distribuisce Qt. Il riferimento del dispositivo è Qt 6.8.2 / display 960×640; un risultato PC con un'altra versione non certifica la board.

Dal runtime puoi esportare il kit con `python3 dashboard/theme_pack.py kit --bundle --output /percorso/nuovo-kit`; `theme_pack.py bundle ...` inoltra tutti i comandi seguenti.

Dal kit:

```sh
python3 sdk/theme_bundle_tools.py init mio-tema --id studio.miotema --name "Il mio tema"
python3 sdk/theme_bundle_tools.py validate mio-tema --lint --runtime
python3 sdk/theme_bundle_tools.py preview mio-tema --output anteprime --matrix
python3 sdk/theme_bundle_tools.py pack mio-tema mio-tema.smartpc-theme
python3 sdk/theme_bundle_tools.py inspect mio-tema.smartpc-theme
python3 sdk/theme_bundle_tools.py import mio-tema.smartpc-theme --store /percorso/dati-prova
python3 sdk/theme_bundle_tools.py list --store /percorso/dati-prova
python3 sdk/theme_bundle_tools.py transfer mio-tema.smartpc-theme --board smartpc@IP
```

`--qt-python` seleziona un interprete Qt; `--qmllint` seleziona il linter. Se un tool manca, il report restituisce `notVerified`, mai PASS. `transfer` deposita il pacchetto nell'inbox: importazione e applicazione sono separate e avvengono dal dispositivo. `export ID@VERSION#DIGEST destinazione --store ...` conserva una revisione esistente; il formato esatto di identity è quello restituito dal catalogo.

Nei comandi bundle `import` ed `export`, `--store` indica il root dei dati dell'applicazione che contiene `theme-bundles`, non la sottocartella legacy `themes`. `import` richiede PySide6 ed esegue il preflight Qt in un processo separato; installa una revisione verificata e non applica il tema né modifica le preferenze. Il kit cerca anche il linter incluso in PySide6, quando presente.

Per amministrare le revisioni: `remove ID@VERSION#DIGEST --store ROOT` e `gc --keep 2 --store ROOT`. Questi comandi rispettano journal e lease: attivo, precedente, candidato e risorse in uso sono protetti; Base non è rimovibile. Il risultato elenca solo le revisioni realmente rimosse. Non cambiano automaticamente il tema attivo e non azzerano eventi o preferenze dei provider.

Il progetto iniziale introduce Home, shell, notifica piccola e grande completamente esterne all'app. Il progetto include anche esempi eseguibili di ricetta motion, icona procedurale e scena/skin del compagno, caricati dal preflight anche quando inattivi. La scena resta inizialmente disabilitata. `renderer-skeletons/` offre i 16 contesti tipizzati: i template sono intenzionalmente non ready finché contenuti/lifecycle non sono completati.

Le altre 39 superfici dichiarano fallback Base esplicito: il numero 44 è copertura funzionale, non 44 nuovi visuali. La scena conta come una delle cinque capacità proprie anche quando è disabilitata. Per ridisegnare le altre superfici aggiungere renderer, risorse e registry, aggiornando entrambe le liste di coverage. Gli esempi usano soltanto `SmartPC.ThemeApi 2.0`, senza controller privati o import relativi al core.

`scene.main` si dichiara esclusivamente attraverso `sceneRenderers` nel registry e `scene.renderer` in `theme.json`, con metadati `sceneMode`, `footprint` e occupazione. Non va aggiunta alle `presentations`: il validator rifiuta due selezioni concorrenti. Un renderer esterno selezionato richiede coverage propria, anche con `enabled: false`; un renderer Base selezionato richiede fallback. Il registry può contenere altre varianti di scena non selezionate. Attivazione e override conservano questa corrispondenza per la revisione installata.

Per cambiare anche la distribuzione dello schermo, un tema che possiede `shell.main` può aggiungere a `bundle.json` un oggetto `layout`, con tutti i campi `header`, `content`, `guide` e `sceneSafeRegions`. I rettangoli usano le coordinate fisiche 960×640; ciascuno contiene esattamente `x`, `y`, `width`, `height`, con numeri finiti non negativi interamente entro il display. `content` deve avere dimensioni positive; header e guida possono essere zero per integrarli nella pagina. Le regioni sicure della scena sono una lista di massimo 64 rettangoli. Il validator rifiuta aree fuori dal display, booleani e campi sconosciuti.

```json
"layout": {
  "header": {"x": 0, "y": 0, "width": 960, "height": 64},
  "content": {"x": 120, "y": 64, "width": 720, "height": 520},
  "guide": {"x": 120, "y": 590, "width": 720, "height": 40},
  "sceneSafeRegions": [{"x": 0, "y": 64, "width": 96, "height": 520}]
}
```

L'app assegna questa geometria ai renderer pagina API 2 e ne ritaglia il contenuto. `PageContext.viewport` usa coordinate locali `(0,0)` e le dimensioni dell'area; `ShellContext.layout` espone i rettangoli dello schermo. Le pagine Base usate come fallback mantengono la geometria precedente `(44,90,872,455)`: la shell deve rispettare il rettangolo effettivo ricevuto dal contesto durante la navigazione. L'assenza di `layout` conserva il layout attuale. La preview renderizza la pagina nel suo viewport locale e registra anche `contentRect` assoluto; non simula tutti i livelli della dashboard. Import ed export conservano il layout nello stesso payload verificato.

Le risorse visuali opache, per esempio shader compilati `.qsb`, descrizioni di atlas `.atlas`, rig `.rig`, animazioni binarie `.bin` o futuri formati dedicati, possono entrare nel bundle senza aggiungere un decoder al motore. Ogni file con estensione non standard deve essere dichiarato esplicitamente in `bundle.json` come `{"id":"compagno.rig","path":"assets/compagno.rig","type":"data"}`. Quando serve anche nel catalogo dei dati del tema, dichiararlo in `theme.json.assets` con `type: "data"`, percorso e SHA256. I file sono confinati al payload, verificati dal digest e conservati identici attraverso pack/import/export, con gli stessi limiti di 8 MiB per file e 24 MiB complessivi.

La dichiarazione `data` non sostituisce i tipi `qml`, `js`, `font` o `image` e i relativi controlli. Script, librerie native, eseguibili e installatori restano esclusi anche se rinominati nelle dichiarazioni; i comuni header di eseguibili rinominati vengono rifiutati. Questo non cambia il modello di fiducia nel codice dell'autore e non costituisce una sandbox.

Accettare e trasferire un asset opaco non prova che Qt sappia usarlo. Il renderer deve implementarne l'uso con le capacità effettivamente presenti e dichiarare i moduli necessari; preflight ed esecuzione sulla board devono verificare caricamento, animazioni, sospensione e prestazioni. Per `.qsb` occorre produrre uno shader compatibile con Qt e con il backend del dispositivo; atlas e rig richiedono un renderer adeguato. Nessun decoder nativo o plugin viene installato dal tema.

Tutti i renderer di presentazione e scena API 2 devono esporre `ready` e diventare `ready === true`, con `contentReady !== false`, prima di essere considerati validi. Il preflight applica lo stesso controllo del runtime e rifiuta anche un componente che si istanzia senza soddisfarlo.

La preview crea veri contesti pubblici e renderer Qt con dati sintetici isolati, genera screenshot e prova assestamento/attività per giorno/notte e Normale/Ridotto/Off. Non è un test ottico, di tutti i flussi della dashboard o di prestazioni EGLFS. Le fixture della dashboard completa sono in `sdk/check_theme_runtime_fixtures.py`; le prove della board e della matrice di consegna rimangono distinte. Le notifiche demo non entrano nel DB reale.

Lo schema 1 resta supportato: `sdk/theme_pack.py check`, `kit`, `profile`, `install` mantengono il profilo dichiarativo precedente. Un bundle eseguibile richiede fiducia nell'autore; il validator e il processo di preflight non costituiscono una sandbox di sicurezza.

`acceptance-matrix.json` contiene i 21 scenari di consegna con stato iniziale non verificato: allegare prove effettive e residui prima di dichiararli chiusi.

`kit-manifest.json` registra SHA dei sorgenti SDK e fingerprint API. Il builder genera `integrity.json` dai file effettivi del progetto; lo stesso digest deve essere controllato sul dispositivo. Non includere dati personali, account, cache dei provider o report con informazioni private.

Il cambio completo di tema può attendere: la dashboard fornisce una schermata di preparazione propria, con Annulla/Home e precedenza degli urgenti. Il renderer deve comunque raggiungere readiness entro il watchdog e rispettare la fluidità della navigazione e le politiche di movimento. Il riferimento storico 150 ms dei benchmark non è un limite universale per l’applicazione occasionale di un tema.
