# Theme Engine v0.6.6: uso e sviluppo

Il motore usa Python/PySide6 per catalogo, validazione, preparazione e salvataggio; Qt Quick/QML per composizione, rendering e animazioni. I pacchetti personali sono JSON. Il compagno definitivo rimane nella v0.9: la v0.6.6 contiene già host persistente, stato dell'attore e registrazione di renderer, con una scena geometrica di prova.

## Uso sulla dashboard

`9 Menu → Impostazioni → Aspetto`. `2/8` selezionano; `4/6` regolano; `5` attiva l'azione; `7` annulla/torna; `1` torna Home. La mappa del decoder è conservata: 1 Home, 7 Back. Le prove automatiche coprono tasti Qt e scancode HID; una pressione umana sul tastierino resta un controllo ergonomico distinto.

Base conserva il carattere di sistema e la composizione iniziale. Functional propone palette grigia/oro, angoli più contenuti, orologio centrato e dissolvenze. Entrambi coprono Oggi, Meteo, Account, Sport, F1/MotoGP, dettagli, Fantacalcio, impostazioni, Informazioni e avvisi.

**Estensione del 3 ottobre:** piccolo/grande/urgente, badge, elenco e dettaglio sono sei presentazioni indipendenti, collegate al registry tramite `NotificationHost`. [Contratto e audit iniziale](theme-engine-notification-spec.md); [collaudo e distribuzione](theme-engine-notification-migration-report.md).

**Direzione di prodotto successiva:** creazione profonda tramite AI, importazione di un tema completo anche con nuovi componenti visuali e pochi adattamenti sul dispositivo. [Analisi, lacune e piano](theme-engine-ai-authoring-spec.md). Il formato bundle e il kit descritti in quella proposta non sono ancora implementati; questa guida continua a descrivere l'importazione schema 1 e l'editor attualmente disponibili.

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

Una cartella `extensions/<nome>/manifest.json`, API 1, può registrare `presentations`, `recipes`, `iconRenderers`, `iconSets`, `sceneRenderers` e `tokens` nel namespace `ext.*`. L'esempio `extensions/example` registra Home Riepilogo, un banner piccolo centrato e una scheda grande; il terzo tema `personal.sample` li seleziona senza aggiungere switch a Main, al resolver o al motore eventi.

Una presentazione riceve `context`: API, contenuto, facade tipizzata, viewport, `model`, `selection`, `active`, `interactive`, orologio/data e `activate(actionId, argument)`. Le presentazioni nuove consumano questi dati. L'adattatore delle viste preesistenti conserva temporaneamente il controller privato; i provider e gli ID selezionati rimangono fuori dal Loader. I registry descrivono file, API, compatibilità e nome leggibile. Il selettore Home elenca i registry compatibili, comprese le estensioni.

`ViewHost` ha un objectName stabile, `currentItem`, `readiness`, `loadedRevision`, `lastError`. Un candidato viene incubato asincronamente con contesto non interattivo e facade della bozza; il visuale corrente rimane visibile fino a Loader.Ready. La revisione viene pubblicata quando sono pronti tutti i candidati necessari: pagina corrente e sei superfici Avvisi preparate. Il generation ID e il content ID identificano ciascun esito; errore/timeout/cancel invalidano la preparazione. Un caricamento fallito conserva la vista precedente; senza vista disponibile viene tentata Base. Il singleton QML possiede inoltre un fallback generato indipendente dal catalogo Python. L'input Qt/HID rimane nel root `inputOwner`; i Loader non rubano focus.

Le icone hanno backend geometria Qt Quick Shapes, glifo TTF, immagine o componente registrato. `AppIcon` mantiene box ottico e ID; `sourceSize` dell'immagine è stabile, cache e decoding asincrono sono abilitati, un simbolo sostitutivo copre l'attesa/errore. Il meteo deriva l'ID dal codice WMO, senza parsing del testo. Atlanti, rig e scene non sono costretti a passare da un icon-font.

Le ricette implementano `play(item, configuration, direction, vertical)` e `settle()`. Il controller risolve il file dal registry, finalizza la ricetta precedente, cattura parametri e policy, e avvia tween Qt nativi. `events` dichiara compatibilità ed eleggibilità nel selettore; `name` è la label utente. Sono collegati navigazione, pannelli, banner, selezione, schede, aggiornamenti dei dati, cambio composizione, luminosità e spostamento dell'attore. `urgent.present` resta un cut immediato. Ridotto limita durata/distanza; Off finalizza subito gli elementi. Nessun aggiornamento Python ad ogni frame.

`SceneHost` appartiene al root della finestra, non alla pagina. `ActorState` conserva identità, pose/azione, locomozione separata, sequenza, pausa, anchor e motionMode durante navigazione/cambi tema. Un renderer riceve `active`, `style`, `actorState`, `configuration`. `sceneMode: "actor"` usa un footprint dichiarato; `sceneMode: "canvas"` offre l'intero viewport 960×640 per un renderer QML, shader o integrazione nativa. Il renderer deve rispettare lifecycle, aree sicure, pause e budget della scheda. Può dichiarare `occupiedRegions` e `notificationEvent` come proprietà: riceve gli ingombri e l'evento senza controllare consegna o lettura. Gli attori vengono riposizionati fuori dalle notifiche quando possibile e sospesi quando manca spazio; un canvas deve dichiarare `respectsOccupiedRegions: true` e rispettare quelle aree. Urgenze/overlay continuano a sospendere la scena. Il formato della futura animazione del cane non viene scelto da questa release.

## Costi, test e distribuzione

Lo snapshot attraversa il bridge solo a cambi discreti; le viste leggono proprietà QML tipizzate della facade. Questo non rende gratuito il cambio tema e non garantisce AOT o overhead zero. Gli overlay storici nascosti trattengono l'ultima facade e tornano allo stile corrente quando attivi. Le sei presentazioni Avvisi selezionate sono invece preparate anche quando nascoste: serve a rendere immediato l'urgente e a validare tutte le composizioni prima di Apply. L'elenco nascosto riceve un modello vuoto. Lo staging conserva soltanto vecchio visuale e candidato per gli slot cambiati; nessun caricamento di tutte le varianti dei temi. Il relativo costo di memoria è misurato nel [collaudo notifiche](theme-engine-notification-migration-report.md).

Le risoluzioni già validate sono memorizzate in una LRU di 32 snapshot, invalidata alla rilettura del catalogo e quando dimensione/mtime degli asset cambiano. Il catalogo non carica tutti i TTF. Registrazioni deduplicate per SHA, riferimenti ai servizi e ai candidati, LRU di quattro registrazioni inattive. Le risorse del tema attivo restano referenziate. Non si deduce la liberazione delle texture dalla sola rimozione di un font: lo stress misura warmup e plateau della PSS. Nuovi font e primi glifi possono produrre frame più lunghi; la garanzia va limitata ai carichi misurati.

`check_theme_core/ui/motion/fonts/icons/persistence/recovery.py` coprono contratti, QML reale, focus, swap, TTF/PNG reali, persistenza con processi nuovi e cartella non scrivibile, recovery indipendente. Gli harness originali attendono gli host e riacquisiscono il contenuto; i test nei dettagli verificano che un cambio tema non richiami selezioni provider, mark-read o dismiss.

`verify_theme_board.py` misura frameSwapped nelle finestre di movimento; `verify_theme_stress.py` esegue 100 cambi con tre famiglie TTF; `verify_theme_offline.py` verifica cold start in namespace di rete isolato. I risultati e i limiti sono nel [resoconto di migrazione](v066-migration-report.md).

```sh
python3 scripts/generate-theme-contract.py
python3 scripts/package-dashboard.py build --output /percorso/build/dashboard
python3 scripts/package-dashboard.py verify /percorso/build/dashboard
```

Il generatore aggiorna schema e fallback quando cambia il contratto. Il packaging è ricorsivo, include qmldir/JS/JSON/QML e tutte le risorse dichiarate, anche con estensioni specifiche di un renderer, e produce SHA256 per ogni file. Esclude preferenze, cache, design e bytecode. L'installer richiede Qt Quick Shapes, verifica la distribuzione, conserva quella precedente e ripristina in caso di processo non stabile all'avvio. Il rollback sostituisce l'intera cartella di runtime, preservando dati utente; evita di mescolare vecchi e nuovi sottodirectory.


## Personalizzare gli Avvisi

`9 Menu → Impostazioni → Aspetto → Avvisi`. Scegli l'ambito, poi composizione, padding, misure titolo/corpo/fonte, raggio, ancoraggio, famiglie font, icona/fonte, densità dell'elenco e ricette di entrata/uscita. I sei selettori di composizione leggono il registry, comprese le estensioni. **Mostra anteprima** usa un evento fittizio fuori dal DB; `4/6` cambiano modalità e `7` torna alla bozza. Un vero urgente prende comunque precedenza. Tornare ad Aspetto conserva la bozza; uscire da Aspetto la annulla. Applica salva l'intera bozza, con conferma soltanto dopo la scrittura riuscita. **Ripristina avvisi del tema** rimuove soltanto gli override Avvisi.

| Contenuto | Gruppo token | Fallback | Host stabile |
| --- | --- | --- | --- |
| `alerts.banner.small` | `notifications.small.*` | `builtin.alerts.small` | `eventBanner` |
| `alerts.banner.large` | `notifications.large.*` | `builtin.alerts.large` | `eventLargeBanner` |
| `alerts.urgent` | `notifications.urgent.*` | `builtin.alerts.urgent` | `eventUrgent` |
| `alerts.badge` | `notifications.badge.*` | `builtin.alerts.badge` | `unreadAlertsBadge` |
| `alerts.inbox` | `notifications.inbox.*` | `builtin.alerts.inbox` | `alertsInbox` |
| `alerts.detail` | `notifications.detail.*` | `builtin.alerts.detail` | `alertDetail` |

Functional usa `builtin.alerts.small-rail` e `builtin.alerts.large-split`; il tema personale usa `example.alerts.small` e `example.alerts.large`. Base conserva la disposizione ordinaria. I sei slot possono essere sovrascritti separatamente; i pacchetti schema 1 preesistenti ricevono automaticamente i fallback mancanti.

I **181 token Avvisi** sono nel contratto generato: colori surface/title/body/source/accent/border, forme, padding/gap, width/height/insetX/insetY/anchor, quattro famiglie e misure tipografiche, pesi, limiti delle righe sintetiche, icona/fonte e righe dell'elenco. L'elenco ha inoltre `notifications.inbox.focusedSurface`. In assenza di override, i ruoli ereditano colori/font/misure globali; un override locale non modifica Home/Sport. `asset:<id>` funziona anche nelle famiglie locali, con lo stesso FontRegistry e la deduplicazione per SHA. `NotificationStyle` espone proprietà QML tipizzate: `surfaceColor`, `noticeAccent`, `titleFamily`, `titleSize`, ecc.; solo la facade legge la mappa.

La geometria è contenuta nel viewport 960×640. Contrasto/range e spazio disponibile vengono validati prima della pubblicazione. I renderer forniti dichiarano `layoutContract`: riserva conservativa di righe, font, padding e guida. Una combinazione che non permette lettura/comandi viene respinta, conservando la precedente bozza visibile e mostrando l'errore. Banner/badge adeguano l'altezza alle metriche reali; le schede sintetiche possono elidere il testo. Il dettaglio usa un flusso completo scorrevole con `2/8`, senza sovrapporre titolo/corpo/fonte. L'elenco calcola le righe effettive e la pagina dalla selezione per ID. Renderer inediti possono definire altri layout e token `ext.*`; `layoutContract` dei template standard non è un limite universale dell'engine.

Esempio di personalizzazione JSON, ereditando Base:

```json
{
  "presentations": {
    "alerts.banner.small": "builtin.alerts.small-rail",
    "alerts.banner.large": "builtin.alerts.large-split"
  },
  "tokens": {
    "notifications.small.anchor": "top",
    "notifications.small.insetY": 106,
    "notifications.large.titleSize": 48,
    "notifications.large.titleFamily": "asset:noticeTitle"
  },
  "assets": [{"id":"noticeTitle","type":"font","path":"NoticeTitle.ttf"}]
}
```

Per una composizione nuova registrare un componente distribuito con l'applicazione:

```json
{
  "apiVersion": 1,
  "presentations": [{
    "id": "studio.alerts.poster",
    "name": "Scheda illustrata",
    "apiVersion": 1,
    "contextApi": "notification1",
    "contentIds": ["alerts.banner.large"],
    "file": "extensions/studio/Poster.qml"
  }]
}
```

Il componente richiede `property var context`; riceve **NotificationContext API 1**, distinto dal contesto delle pagine: `event`, `items`, `selectedEventId`, `unreadCount`, `sourceStatus` (stato del bollettino meteo storico nell’inbox), `sourceText`, `validityText`, `iconId`, viewport/safeArea, `active/interactive/exiting/preview`, `style`, `visualStyle`, `appearanceRevision`, `actions` e `commandHints`. `requestAction(action, eventId, argument)` passa al router: `openInbox`, `openDetails`, `dismiss`, `home`, `back`, `selectEvent`, `moveSelection`, `scrollDetails`. Il renderer non accede al DB o al controller root. La preview non autorizza azioni reali. Testo è PlainText; la gravità usa `weatherSeverity`, non parsing del titolo.

`Loader.Ready` prepara il componente; se necessita risorse aggiuntive, esporre `property bool presentationReady: false` e portarla a true dopo il caricamento. Timeout: 3 secondi. L'Apply resta disabilitato fino al commit coordinato; errore conserva l'aspetto precedente. Il visuale selezionato urgente viene preparato insieme agli altri; se non è ancora pronto al primo avviso, la shell usa immediatamente il componente Base di emergenza, con input attivo.

Le ricette standard includono `banner.small.enter/exit`, `banner.large.enter/exit`, `alerts.badge.enter/exit`, `alerts.inbox.enter/exit`, `alerts.detail.enter/exit`; i vecchi `banner.enter/exit` e `panel.enter/exit` restano fallback. L'urgente compare con cut immediato. Animazioni/decorazioni interne possono usare gli elementi Qt nativi: rispettare `context.active`, `context.exiting` e `context.style.appearance.motionMode`, sospendere quando inattivi ed esporre opzionalmente `settleMotion()`. La shell lo invoca prima del rilascio/swap o della finalizzazione; il contesto offre anche `settleMotion()` per richiederla. Nessun loop Python per pilotare tween. Per icone usare `AppIcon` e gli ID semantici oppure un renderer registrato: glifo, geometria, immagine, atlante e componente restano disponibili.

Un solo controller possiede la trasformazione del Loader Avvisi: le sue ricette di entrata/uscita. Il cambio di revisione finalizza un tween precedente senza cancellare quello appena iniziato dal nuovo commit. `context.ready` si riferisce al nuovo visuale; la locomozione della scena viene avviata una sola volta per cambio effettivo di anchor.

Un renderer con decorazioni fuori dal proprio pannello dichiara `readonly property var occupiedRegions: [Qt.rect(...)]` in coordinate locali: l'host le traduce nel viewport e SceneHost evita quegli ingombri. Il controller mantiene z-order, focus e priorità; nessuna reazione del futuro compagno può segnare un evento letto o ritardare un urgente.

Gli otto secondi del banner iniziano dopo l'acknowledgment del frame Qt, validato per **ID, revisione e notificationRank** catturati prima della sincronizzazione. Un evento cancellato, futuro, superato o preempted durante l'attesa non viene consegnato. Un frame con Loader o visuale completamente trasparente non conferma la consegna. Cambiare tema non riavvia il timer e non marca letto/chiuso l'evento. FrameSwapped indica presentazione sottomessa da Qt; non è una misura ottica del pannello. [QQuickWindow 6.8](https://doc.qt.io/qt-6.8/qquickwindow.html).
