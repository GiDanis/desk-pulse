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
python3 sdk/theme_bundle_tools.py transfer mio-tema.smartpc-theme --board smartpc@IP
```

`--qt-python` seleziona un interprete Qt; `--qmllint` seleziona il linter. Se un tool manca, il report restituisce `notVerified`, mai PASS. `transfer` deposita il pacchetto nell'inbox: importazione e applicazione sono separate e avvengono dal dispositivo. `export ID@VERSION#DIGEST destinazione --store ...` conserva una revisione esistente; il formato esatto di identity è quello restituito dal catalogo.

Nei comandi bundle `import` ed `export`, `--store` indica il root dei dati dell'applicazione che contiene `theme-bundles`, non la sottocartella legacy `themes`. `import` richiede PySide6 ed esegue il preflight Qt in un processo separato; installa una revisione verificata e non applica il tema né modifica le preferenze. Il kit cerca anche il linter incluso in PySide6, quando presente.

Il progetto iniziale introduce Home, shell, notifica piccola e grande completamente esterne all'app. Il progetto include anche esempi eseguibili di ricetta motion, icona procedurale e scena/skin del compagno, caricati dal preflight anche quando inattivi. La scena resta inizialmente disabilitata. `renderer-skeletons/` offre i 16 contesti tipizzati: i template sono intenzionalmente non ready finché contenuti/lifecycle non sono completati.

Le altre 40 superfici dichiarano fallback Base esplicito: il numero 44 è copertura funzionale, non 44 nuovi visuali. Per ridisegnarle aggiungere i renderer, le risorse e i registry, aggiornando entrambe le liste di coverage. Gli esempi usano soltanto `SmartPC.ThemeApi 2.0`, senza controller privati o import relativi al core.

La preview crea veri contesti pubblici e renderer Qt con dati sintetici isolati, genera screenshot e prova assestamento/attività per giorno/notte e Normale/Ridotto/Off. Non è un test ottico, di tutti i flussi della dashboard o di prestazioni EGLFS. Le fixture della dashboard completa sono in `sdk/check_theme_runtime_fixtures.py`; le prove della board e della matrice di consegna rimangono distinte. Le notifiche demo non entrano nel DB reale.

Lo schema 1 resta supportato: `sdk/theme_pack.py check`, `kit`, `profile`, `install` mantengono il profilo dichiarativo precedente. Un bundle eseguibile richiede fiducia nell'autore; il validator e il processo di preflight non costituiscono una sandbox di sicurezza.

`acceptance-matrix.json` contiene i 21 scenari di consegna con stato iniziale non verificato: allegare prove effettive e residui prima di dichiararli chiusi.

`kit-manifest.json` registra SHA dei sorgenti SDK e fingerprint API. Il builder genera `integrity.json` dai file effettivi del progetto; lo stesso digest deve essere controllato sul dispositivo. Non includere dati personali, account, cache dei provider o report con informazioni private.
