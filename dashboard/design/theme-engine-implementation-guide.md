# Theme Engine v0.6.6: uso e sviluppo

Il motore usa Python/PySide6 per catalogo, validazione, preparazione e salvataggio; Qt Quick/QML per composizione, rendering e animazioni. I pacchetti personali sono JSON. Il compagno definitivo rimane nella v0.9: la v0.6.6 contiene già host persistente, stato dell'attore e registrazione di renderer, con una scena geometrica di prova.

## Uso sulla dashboard

`9 Menu → Impostazioni → Aspetto`. `2/8` selezionano; `4/6` regolano; `5` attiva l'azione; `7` annulla/torna; `1` torna Home. La mappa del decoder è conservata: 1 Home, 7 Back. Le prove automatiche coprono tasti Qt e scancode HID; una pressione umana sul tastierino resta un controllo ergonomico distinto.

Base conserva il carattere di sistema e la composizione iniziale. Functional propone palette grigia/oro, angoli più contenuti, orologio centrato e dissolvenze. Entrambi coprono Oggi, Meteo, Account, Sport, F1/MotoGP, dettagli, Fantacalcio, impostazioni, Informazioni e avvisi.

Il pannello consente palette Auto/Giorno/Notte, movimento Normale/Ridotto/Disattivo, tema e composizione Home, scala del testo 85–110%, densità delle liste, raggio delle schede, accento, famiglie per interfaccia/numeri/orologio, transizioni e scena di prova. La bozza si vede subito; **Applica e salva** la rende persistente. Back/Home o Annulla ripristinano l'ultimo aspetto salvato. Ripristina Base modifica solo la bozza. Un salvataggio fallito ripristina l'aspetto salvato e conserva la bozza per riprovare.

Gli avvisi ufficiali mantengono colori semantici riconoscibili e presentazione urgente immediata. Notte, luminosità, quiet hours e movimento hanno politiche distinte. La scena si sospende durante overlay, urgenze, notte e quiet hours; Ridotto/Disattivo escludono il movimento dell'attore. Non esiste un loop decorativo permanente di default.

## Pacchetti personali

Il servizio usa `QStandardPaths.AppDataLocation/themes`; nel kiosk, con HOME=/var/lib/smartpc-dashboard e applicazione SmartPC, la cartella è `/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/themes`. `theme-imports` e `theme-exports` sono cartelle sorelle. Il menu Importa legge sottocartelle contenenti `theme.json`; Export scrive un nuovo pacchetto completo, con override, varianti giorno/notte e risorse dichiarate. Gli originali di import restano disponibili; ID già installati vengono saltati nel menu e rifiutati dal comando CLI.

CLI, con un runtime Python disponibile:

```sh
python3 dashboard/theme_pack.py --store /percorso/temi list
python3 dashboard/theme_pack.py --store /percorso/temi import dashboard/examples/themes/personal-sample
python3 dashboard/theme_pack.py --store /percorso/temi validate
python3 dashboard/theme_pack.py --store /percorso/temi export personal.sample /percorso/esportazione --id personal.exported
```

Il pacchetto minimo contiene `schemaVersion: 1`, `id`, `name`, `version` e può ereditare `extends: "base"`. I token hanno chiavi piatte, per esempio `colors.surface`, `typography.uiFamily`, `shape.radiusCard`. Sono elencati in `themes/token-contract.json`; lo schema editor è `themes/theme-pack.schema.json`. Validazione semantica effettiva: `ThemeCatalog`, con tipi, intervalli, contrasto, capacità, registry, asset, percorsi contenuti e hash. La palette richiede testo ≥4,5:1 e indicatore di focus ≥3:1. Errori non pubblicano una snapshot parziale.

`presentations` associa contenuto logico a ID registrato. `motion` associa evento a ricetta, `durationMs`, `distancePx`, `easing` e parametri della ricetta. `iconOverrides` mantiene gli ID semantici. `scene` seleziona renderer e configurazione. Gli override avanzati e i token aggiuntivi sono disponibili nel formato JSON; il pannello propone i controlli comuni, senza una voce per ogni token.

Le risorse `font`, `image`, `data` sono locali. Famiglie `asset:<id>` vengono risolte prima della pubblicazione. Asset immagine usati dalle icone devono essere di tipo image. Non si importa codice QML da un pacchetto: nuovi comportamenti sono estensioni distribuite con l'applicazione. Font mancanti, glifi assenti, manifest incompatibili e hash errati producono errori espliciti. Le risorse mantengono le proprie condizioni di licenza: la distribuzione non aggiunge font commerciali.

Envelope iniziale A733: 128 KiB per manifest, 64 risorse per tema, 8 MiB per file, 24 MiB complessivi di file e 24 MiB stimati per immagini decodificate. Sono limiti del validatore di questo profilo, modificabili dopo misure; non fissano il numero di famiglie, pose, presentazioni o ricette che l'architettura può rappresentare. Le dimensioni dei grandi orologi hanno limiti effettivi aggiuntivi per la composizione standard; una nuova presentazione può definire ruoli `ext.*` appropriati.

## Estensioni visuali e compagno

Una cartella `extensions/<nome>/manifest.json`, API 1, può registrare `presentations`, `recipes`, `iconRenderers`, `iconSets`, `sceneRenderers` e `tokens` nel namespace `ext.*`. L'esempio `extensions/example` registra una Home Riepilogo; il terzo tema `personal.sample` la seleziona senza aggiungere switch al resolver.

Una presentazione riceve `context`: API, contenuto, facade tipizzata, viewport, `model`, `selection`, `active`, `interactive`, orologio/data e `activate(actionId, argument)`. Le presentazioni nuove consumano questi dati. L'adattatore delle viste preesistenti conserva temporaneamente il controller privato; i provider e gli ID selezionati rimangono fuori dal Loader. I registry descrivono file, API, compatibilità e nome leggibile. Il selettore Home elenca i registry compatibili, comprese le estensioni.

`ViewHost` ha un objectName stabile, `currentItem`, `readiness`, `loadedRevision`, `lastError`. Un candidato viene incubato asincronamente con contesto non interattivo e facade della bozza; il visuale corrente rimane visibile fino a Loader.Ready. La revisione viene pubblicata al commit del candidato. Un caricamento fallito conserva la vista precedente; senza vista disponibile viene tentata Base. Il singleton QML possiede inoltre un fallback generato indipendente dal catalogo Python. L'input Qt/HID rimane nel root `inputOwner`; i Loader non rubano focus.

Le icone hanno backend geometria Qt Quick Shapes, glifo TTF, immagine o componente registrato. `AppIcon` mantiene box ottico e ID; `sourceSize` dell'immagine è stabile, cache e decoding asincrono sono abilitati, un simbolo sostitutivo copre l'attesa/errore. Il meteo deriva l'ID dal codice WMO, senza parsing del testo. Atlanti, rig e scene non sono costretti a passare da un icon-font.

Le ricette implementano `play(item, configuration, direction, vertical)` e `settle()`. Il controller risolve il file dal registry, finalizza la ricetta precedente, cattura parametri e policy, e avvia tween Qt nativi. `events` dichiara compatibilità ed eleggibilità nel selettore; `name` è la label utente. Sono collegati navigazione, pannelli, banner, selezione, schede, aggiornamenti dei dati, cambio composizione, luminosità e spostamento dell'attore. `urgent.present` resta un cut immediato. Ridotto limita durata/distanza; Off finalizza subito gli elementi. Nessun aggiornamento Python ad ogni frame.

`SceneHost` appartiene al root della finestra, non alla pagina. `ActorState` conserva identità, pose/azione, locomozione separata, sequenza, pausa, anchor e motionMode durante navigazione/cambi tema. Un renderer riceve `active`, `style`, `actorState`, `configuration`. `sceneMode: "actor"` usa un footprint dichiarato; `sceneMode: "canvas"` offre l'intero viewport 960×640 per un renderer QML, shader o integrazione nativa. Il renderer deve rispettare lifecycle, aree sicure, pause e budget della scheda. Il formato della futura animazione del cane non viene scelto da questa release.

## Costi, test e distribuzione

Lo snapshot attraversa il bridge solo a cambi discreti; le viste leggono proprietà QML tipizzate della facade. Questo non rende gratuito il cambio tema e non garantisce AOT o overhead zero. Le superfici nascoste trattengono l'ultima facade e tornano allo stile corrente quando attive: cambiare font non forza immediatamente il ricalcolo di tutti gli overlay nascosti.

Le risoluzioni già validate sono memorizzate in una LRU di 32 snapshot, invalidata alla rilettura del catalogo e quando dimensione/mtime degli asset cambiano. Il catalogo non carica tutti i TTF. Registrazioni deduplicate per SHA, riferimenti ai servizi e ai candidati, LRU di quattro registrazioni inattive. Le risorse del tema attivo restano referenziate. Non si deduce la liberazione delle texture dalla sola rimozione di un font: lo stress misura warmup e plateau della PSS. Nuovi font e primi glifi possono produrre frame più lunghi; la garanzia va limitata ai carichi misurati.

`check_theme_core/ui/motion/fonts/icons/persistence/recovery.py` coprono contratti, QML reale, focus, swap, TTF/PNG reali, persistenza con processi nuovi e cartella non scrivibile, recovery indipendente. Gli harness originali attendono gli host e riacquisiscono il contenuto; i test nei dettagli verificano che un cambio tema non richiami selezioni provider, mark-read o dismiss.

`verify_theme_board.py` misura frameSwapped nelle finestre di movimento; `verify_theme_stress.py` esegue 100 cambi con tre famiglie TTF; `verify_theme_offline.py` verifica cold start in namespace di rete isolato. I risultati e i limiti sono nel [resoconto di migrazione](v066-migration-report.md).

```sh
python3 scripts/generate-theme-contract.py
python3 scripts/package-dashboard.py build --output /percorso/build/dashboard
python3 scripts/package-dashboard.py verify /percorso/build/dashboard
```

Il generatore aggiorna schema e fallback quando cambia il contratto. Il packaging è ricorsivo, include qmldir/JS/JSON/QML e tutte le risorse dichiarate, anche con estensioni specifiche di un renderer, e produce SHA256 per ogni file. Esclude preferenze, cache, design e bytecode. L'installer richiede Qt Quick Shapes, verifica la distribuzione, conserva quella precedente e ripristina in caso di processo non stabile all'avvio. Il rollback sostituisce l'intera cartella di runtime, preservando dati utente; evita di mescolare vecchi e nuovi sottodirectory.
