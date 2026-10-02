# v0.6.6 — Piano di migrazione UX, Theme, Presentation e Motion

**Aggiornamento attuazione v0.6.6:** il piano è implementato nei sorgenti. Contratti effettivi, uso e limiti sono nella [guida del motore](theme-engine-implementation-guide.md); stato dei gate e prove sulla scheda nel [resoconto di migrazione](v066-migration-report.md). Gli snippet di analisi illustrano alternative; per il formato eseguibile usare schema, registry ed esempi distribuiti.
**Revisione 2.2 · 2 ottobre 2026 · analisi esecutiva, nessun runtime modificato.**

Riferimenti: [architettura](theme-engine-construction-spec.md), [visualizzazioni e compagno](theme-engine-presentation-spec.md), [animazioni](theme-engine-motion-spec.md), [MasterPlan](release-masterplan.md), [inventario verificato](evidence/v066-theme-analysis/README.md).

Questo piano individua **dove e perché intervenire** sulla dashboard in uso. Evita una sostituzione meccanica degli esadecimali: una migrazione completa deve comprendere tipografia, geometry, focus, composizioni, animazioni e conservazione dello stato.

## 1. Vincoli acquisiti e stato iniziale

Il runtime è una Window QML 960×640; app.py crea provider e DashboardState, quindi inietta keypad/stato e carica Main da file locale. Main possiede navigazione, stack overlay e selezioni di Sport/Racing. I figli ricevono l'intero `dashboard`.

Non esistono ancora ThemeService, registry di presentazioni o scene. Le viste sono create insieme e selezionate tramite `visible`; lo stato di visibilità dei provider è gestito da Main. È una base su cui migrare incrementalmente, senza riscrivere i servizi di dati.

**Il 2 ottobre i 44 file runtime installati confrontati coincidono con il locale.** Differiscono quattro script di test installati. Il manifest e i limiti dell'ispezione sono nel documento di evidenza. Le modifiche documentali già presenti al momento di questa analisi sono preservate; HEAD da solo non descrive la baseline di prodotto.

## 2. Mappa degli interventi Python, input e distribuzione

| File attuale | Riscontro | Intervento proposto | Rischio/verifica |
| --- | --- | --- | --- |
| [app.py](../app.py) | Crea tutti i servizi e inietta iniziali in Main | Creare ThemeService/registry con vita dell'app; preparare Base/font; iniettare contesto esplicito | Avvio prima del primo frame; chiusura worker; niente seconda istanza provider |
| [state.py](../state.py) | QSettings SmartPC/Dashboard, nightMode e animationsEnabled | Adapter Appearance; motionMode/legacy; proprietà separate per stile e dati | Preferenze preesistenti identiche; una scelta tema non emette segnali dei provider |
| [system_info.py](../system_info.py) | Versione hardcoded DeskPulse v0.6; dati dispositivo | Sorgente unica della build; eventuale tema/presentation/renderer in Info | Lettura pura; non avvia acquisizioni o motion |
| [keypad.py](../keypad.py) | Posizioni da codici HID; release/repeat filtrati | Nessun cambio necessario al decoder; prova fisica T0 | Guide 1/7 devono coincidere con azioni effettive |
| [events.py](../events.py) / [event_core.py](../event_core.py) | Durata banner, urgente, inbox/mark-read e disponibilità | Conservare policy; fornire presenter visuale senza nuove ingest/dismiss | Doppio banner, durata lettura, preemption e lettura eventi invariati |
| [weather_alerts.py](../weather_alerts.py) | Normalizza allerta; EventUrgent ora deduce “rossa” dal titolo | Aggiungere livello ufficiale strutturato opzionale e adapter di stile; separare gli eventi Account | Evento meteo/account corretti; cache/event ID non cambiati per il tema |
| Provider meteo/account/sport/racing | Stato e acquisizioni separati dalla UI | Nessuna riscrittura per Theme; adapter di PresentationContext | Contare select/clear/refetch durante cambio visuale |
| [run.sh](../run.sh) | Desktop/device/PySide e fallback QML-only | Includere fallback Base senza backend; percorsi font/data locali | Qt 6.8 board e 6.11 PC; niente qrc non registrato |
| [setup-board.sh](../../scripts/setup-board.sh) | Copia ricorsiva con cp -ru | Manifest della distribuzione per themes/components/motion/font/asset | cp -u non identifica build né rimuove file obsoleti; validare staged deploy |
| [service](../../os/system/smartpc-dashboard.service) | ProtectSystem=strict, StateDirectory/CacheDirectory | Storage temi utente nel percorso scrivibile; mantenere permessi | Nessuna scrittura in /opt, funzionamento col vero utente del kiosk |

File nuovi proposti: theme_core.py, theme_service.py, theme_cli.py, facade/schema/packs/fallback, components, motion e registry/host delle presentazioni. I nomi dettagliati del registry possono essere definiti in T1; il contratto è nella specifica presentation.

## 3. Main.qml: confine più delicato

[Main.qml](../Main.qml), punti individuati nel sorgente letto:

| Zona | Comportamento attuale | Intervento |
| --- | --- | --- |
| Inizio Window | Sfondo giorno/notte letterale, geometria 960×640 | Theme background, shell/viewport stabile |
| Righe 246–250 | ink/muted/accent/panel/edge | Alias temporanei a Theme, poi consumatori espliciti |
| Righe 269–280 | day/night e brightness derivati | Ingresso variante al resolver; luminosità rimane controllo separato |
| Righe 335–351 | animateMove/navigateFamily/navigateView | Controller motion con eventi distinti e assi coerenti |
| Righe 440 e seguenti | activateKey e branch dei pannelli | Conservare router; esporre action IDs e guide comuni |
| Righe 681–695 | contentLayer e figli sempre istanziati | ViewHost, PresentationContext e sostituzione visuale controllata |
| Righe 716–734 circa | Overlay, banner e urgente | Lifecycle presenter; priorità separata da animazione |
| Ultime righe | Diagnostics/devPanel e maschera black | Token per debug; black tecnico documentato; policy motion per brightness |

Le posizioni sono riferimenti dell'inventario iniziale, non indirizzi permanenti dopo le modifiche.

Sequenza consigliata:

1. Aggiungere il servizio/facade senza cambiare il rendering.
2. Collegare gli alias esistenti ai token: molte viste migrano subito nelle superfici comuni.
3. Estrarre il context della Home e una lista senza spostare lo stato del router.
4. Introdurre ViewHost e due presentazioni Home, conservando le selezioni fuori dai visuali.
5. Migrare gli altri contesti e sostituire `dashboard.*` nei nuovi componenti.
6. Tokenizzare tipografia/forme/metriche per ruolo e collegare le ricette motion.
7. Rimuovere alias temporanei solo quando i consumatori e i harness sono aggiornati.

Non trasformare Main in un nuovo monolite contenente tutte le palette, scene e ricette.

## 4. Copertura completa delle 21 superfici QML

| File | Da migrare | Prove specifiche |
| --- | --- | --- |
| [Main.qml](../Main.qml) | Shell, header/footer, content host, palette, motion, debug | Cambio in stack e in transizione; alias/policy coerenti |
| [InfoCard.qml](../InfoCard.qml) | Palette duplicata night, radius13, font condizionati dalla lunghezza | Temperatura/messaggio assente/titolo lungo; larghezze 334/520/872 |
| [HomeNow.qml](../HomeNow.qml) | Orologio152, data31, divider, card/event geometry | Evento presente/assente; due presentazioni; nessuno spazio vuoto |
| [HomeDay.qml](../HomeDay.qml) | Card e valori del riepilogo | Data/meteo/cache/evento opzionale |
| [WeatherNow.qml](../WeatherNow.qml) | Dato principale, linea, card | Temperatura negativa, dato assente, description lunga |
| [WeatherForecast.qml](../WeatherForecast.qml) | Righe91, radius10, font/colonne | Tre giorni, lista vuota, ° e percentuali |
| [AccountChatGPT.qml](../AccountChatGPT.qml) | Piano/barre/crediti, usageColor e soglie | 0/1/2/molte finestre; cache, critico, crediti omessi |
| [DashboardOverlay.qml](../DashboardOverlay.qml) | Menu/Comandi/Avvisi/dettaglio, focus, sfondo | Stack multilivello, primo avvio, mark-read solo su dettaglio |
| [SettingsPanel.qml](../SettingsPanel.qml) | Sfondo/focus, pagina da quattro righe, editor Aspetto | Densità e paginazione, sottomenu Notifiche, bozza/cancel/apply |
| [DeviceInfo.qml](../DeviceInfo.qml) | Font NativeRendering, tab, righe, guida | Informazioni sola lettura; font/frame compare senza rimuovere workaround alla cieca |
| [SportView.qml](../SportView.qml) | Tre righe, status, classifica e punteggi | Prossime/live/risultati/classifica; gate live conservato |
| [SportOverlay.qml](../SportOverlay.qml) | Liste4/tab/detail, lineup/stats, settings collegati | Round selector -1, selezione per ID, dettaglio e font lunghi |
| [SportTeamView.qml](../SportTeamView.qml) | Squadra/placeholder/status | Nessuna preferita; cache; nome/stadio lungo |
| [SportTeamOverlay.qml](../SportTeamOverlay.qml) | Picker, tab, info/rosa, row paging | Ultima riga, filtro/coppe, ritorno alla stessa partita |
| [SportFantasy.qml](../SportFantasy.qml) | Cinque righe dense, colonne voto/SV, focus | Zero e voto assente/SV; provvisori/pubblicati, ultimo giocatore |
| [MotorsportView.qml](../MotorsportView.qml) | Programma/risultati/timing/classifica | F1/MotoGP, stato del feed, sorgente corretta |
| [MotorsportOverlay.qml](../MotorsportOverlay.qml) | Tutti i dettagli/sessioni/piloti/tabelle, tab e focus | Cambio layout durante timing, ID pilota/sessione, campi mancanti |
| [EventBanner.qml](../EventBanner.qml) | Presenter, piccolo/grande, fondo, font e motion | Scadenza, sostituzione, nessun doppio mark-read |
| [EventLargeBanner.qml](../EventLargeBanner.qml) | Wrapper che riusa EventBanner | Copertura ereditata, objectName e geometria mantenuti |
| [EventUrgent.qml](../EventUrgent.qml) | SemanticStyle, layout, priorità e guida corretta | Meteo/account/demo, title lungo, accesso immediato durante motion |
| [UnreadAlertsBadge.qml](../UnreadAlertsBadge.qml) | Radius/border/font, stato non letto | Non duplica banner; count corretto e clic/input invariati |

**Regola di revisione:** ogni esadecimale residuo viene classificato come tema, significato di dominio o tecnico. Ogni misura residua indica se è struttura del viewport o un token del componente. “Zero numeri nel QML” non è l'obiettivo: i limiti di un layout e le unità del grafico restano codice di composizione.

## 5. Componenti comuni: estrarre comportamento visuale, non dati

| Componente | Contratto utile |
| --- | --- |
| AppText | Ruolo tipografico, famiglia/peso effettivo, wrap/elide, fonte stile iniettabile |
| AppIcon | IconId semantico, stile tipizzato, box ottico, renderer/fallback; nessun input proprio |
| Surface / InfoCard | Superficie, bordi/raggi, inset e slots contenuto |
| SelectableRow | selected/enabled/pressed, ID, metriche e feedback; selezione logica esterna |
| DataStatus | status/source/timestamp, testo e simbolo; tinta semantica |
| TabStrip | ID/tab corrente, indicazione e motion; controller decide il tab |
| ViewHeader | Contesto/indice; stile e collocazione configurabili |
| KeyGuide | Action IDs e mappa input unica; il tema cambia presentazione, non testo numerico arbitrario |
| ViewHost | Lifecycle del visuale, preparazione, stato applicativo persistente |
| SceneHost | Continuazione attori fra viste, ancoraggi e preemption |

Iniziare da un componente usato almeno in Home/menu e una lista Sport. Non inventare una libreria generale con decine di controlli inutilizzati.

Preview deve poter fornire `style` diverso dal globale, con la stessa API di alias tipizzati della facade attiva; non duplicare i controlli a mano per ogni tema né passare mappe raw ai binding dei componenti standard. I componenti di recupero e l'urgente mantengono un percorso di fallback leggibile.

Strategia icone: [catalogo e backend](theme-engine-icon-spec.md). Base conserva inizialmente testo/geometrie; T1 prova AppIcon su simbolo sistema e meteo senza cambiare tutte le viste. WeatherNow/Home/Forecast ricevono iconId dal code già normalizzato; non dal testo description o dalla palette notte. La stella preferito di SportTeamOverlay può migrare allo stesso contratto senza cambiare la selezione. Stemmi/mescole reali richiedono dati e asset disponibili, non nuove acquisizioni nel tema. Qualificare Shape, glifi ed eventuale decoder SVG sulla Qt board; tenere il renderer del compagno nel SceneHost.

## 6. Regressioni da prevenire

- Getter di stile che interrogano disco/rete o emettono segnali durante lettura.
- Layout switch che richiama selectMatch/clearFantacalcio per via di onCompleted/onDestruction.
- ID selezionato perso perché il delegate appartiene al vecchio visuale.
- Paginazione rimasta /4 dopo il cambio densità.
- Asset caricati durante una transizione; cache font illimitata dopo molte preview.
- Controller condiviso accidentalmente fra più QQmlApplicationEngine nei test.
- Theme.qml che accede a context property non iniettate nel harness.
- Token in `var` mutati senza NOTIFY e binding interrotti da setter JS.
- Banner invisibile a fine animazione o un visuale di uscita che continua a ricevere input.
- Urgente nascosto da scene, scrim, staging o transizione di tema.
- La voce “Palette” che perde il precedente nightMode, o Off che riattiva vecchie animazioni.
- Valori semanticamente errati: stale presentato come errore critico, assente come zero, tint di tema usata per allerta ufficiale.
- Pretendere che NativeRendering in DeviceInfo possa essere rimosso senza confronto visivo e prestazionale.
- Aggiornare la snapshot del tema durante ogni frame del tween; nascondere refusi con fallback per campo o `value || default` che elimina raggio 0.
- Cercare visuali caricati pigramente prima della readiness, conservare riferimenti distrutti o trovare objectName duplicati nello staging.
- Chiamare forceActiveFocus in ogni onLoaded; il candidato sottrae input a un menu/urgente aperto durante il caricamento.
- Registrare tutti i font del catalogo o considerare removeApplicationFont una prova di rilascio delle texture GPU.
- Icon-font con glifi mancanti/fallback estranei, ID/PUA sparsi nei consumatori o sourceSize SVG legata a una dimensione animata.

## 7. Programma delle prove

Non eseguire adesso i collaudi runtime per una modifica documentale. Durante l'implementazione, riusare e parametrizzare i harness esistenti, **senza diminuire le aspettative di prodotto per farli passare**.

| Gruppo | Harness attuali rilevanti | Nuove verifiche |
| --- | --- | --- |
| Base/navigation | check_dashboard.py, check_settings.py | Entrambi i temi, input guide, editor, dimensioni e fallback |
| Eventi | check_events.py, check_weather_alerts.py | Presenter lifecycle, structured severity, invarianti inbox/durata |
| Calcio | check_sport_ui.py, check_sport_team_ui.py | ID e richieste invariati sotto theme/presentation swap |
| Fantacalcio | check_fantacalcio.py, check_fantacalcio_ui.py | SV/zero/voti, ultimo giocatore, layout ampio |
| Motorsport | check_motorsport.py, check_motorsport_ui.py | Timing/sessione/pilota, preemption, cache e tab |
| Motore puro, nuovo | check_theme_core.py proposto | Merge/eredità/cicli/API/range/contrasto/errore/id duplicate |
| QML engine, nuovo | check_theme_ui.py proposto | Facade per engine, snapshot, due layout, ready/error/fallback |
| Motion/presentation, nuovo | check_theme_motion.py proposto | Cut/interrupt/reduced/off, input rapido, attore persistente |
| Board | verify_*_board.py esistenti + harness Theme proposto | Catture EGLFS, motion traces, font e risorse reali |

Le quattro copie di test diverse sulla board vanno confrontate: non copiarle automaticamente sul locale e non dichiarare passata una suite usando una revisione ignota. Ogni run registra commit/manifest dei harness.

Le prove usano XDG_CONFIG_HOME/cache/eventi isolati e dati controllati. Sport in demo non è creato dal launcher: per copertura usare fixture e servizi finti dei harness Sport, non assumere che F12 produca tutte le discipline.

### 7.1 Adeguamenti obbligatori dei harness

Prima dei Loader dinamici, separare assert di comportamento e assert sulla presentazione. In check_dashboard gli host persistenti sostituiscono i riferimenti alle viste eager; in check_sport_ui fonte/testi/righe si verificano sotto il currentItem pronto o nel contesto, secondo il ruolo dell'asserzione. Non rimuovere assert sui dati per far passare il nuovo layout. Attendere readiness della revisione e fallire su error/timeout; riacquisire i riferimenti dopo ogni swap.

Gli script attuali usano FakeKeypad/keyPressed: conservarli e aggiungere prove Qt keyboard/focus, perché quei segnali bypassano activeFocus. Includere owner attivo, menu/urgente arrivati durante load, candidato obsoleto, errore/cancel, editor e doppio OK. Le [regole host e focus](theme-engine-presentation-spec.md#61-identità-degli-host-readiness-e-compatibilità-dei-test) diventano prerequisiti di T1, non una riparazione a fine T3.

Per il bridge verificare: schema ↔ alias tipizzati, snapshot completa e nuova revisione, raggio 0, refuso respinto, singleton per engine e preview isolata. Misurare contatori di pubblicazione/binding: animare x/opacity senza cambi di stile non deve ripubblicare token; un cambio discreto resta misurabile per conversioni e fan-out. Nessuna soglia prestazionale inventata dal conteggio dei lookup.

Per i font includere primo uso, glifi/pesi/qualità/renderType, memoria di picco durante staging e plateau dopo cambi ripetuti, anche con scene/compagno di prova. Registrare risorse applicative vive e cache Qt/driver osservabili separatamente; il solo PSS non certifica la memoria GPU. [Review con evidenze e gate](theme-engine-risk-review.md).

Per le icone verificare ID/glifo/asset sconosciuto, box/clipping, semantica meteo/offline, preview isolata e sostituzione del backend senza cambiare la vista. Confrontare cold/warm sullo stesso contenuto, includendo geometria/glyph/decoding e swap con motion. L'assenza attuale di Image non costituisce una soglia o un vincolo da mantenere.

## 8. Matrice visuale e di personalizzazione

Copertura minima:

- Due preset × giorno/notte × Normal/Reduced/Off per i percorsi principali.
- Normale/Ampia e densità Regolare/Ampia con nomi/testi lunghi.
- Home con/senza evento, Meteo assente/offline, Account con soglie e campi omessi.
- Settings, Info, inbox/detail/banner piccolo/grande/urgente.
- Tutte le tab/calendari/rosa/voti/timing/piloti delle viste rilasciate.
- Terzo tema derivato e un'estensione presentation di prova per dimostrare espandibilità.
- Attore geometrico persistente fra Home/Meteo: test infrastrutturale, non il cane prodotto.
- Errori di font, pack, presentation, save e theme ID; cold/warm start offline.
- Cambio con stack aperto, nuova densità e input rapido.

Non serve moltiplicare meccanicamente ogni scenario provider per ogni valore del raggio. La validazione numerica copre il contratto; il test UI copre combinazioni rappresentative e gli estremi che possono rompere il layout.

Catture 960×640 ispezionate direttamente, con contenuto identico prima/dopo. Scene e animazioni richiedono anche tracce temporali; uno screenshot non dimostra fluidità.

## 9. Fasi eseguibili, inclusa l'estensibilità profonda

| Fase | Attività | Done verificabile |
| --- | --- | --- |
| T0 | Manifest, quattro harness, versione, guide input, screenshot/font, baseline | Distribuzione e test identificabili; incongruenze annotate/risolte |
| T1 | Schema/facade/resolver + ViewHost + motion + SceneHost di prova | Qt board carica; due Home, una lista e un banner; attore continuo |
| T2a | Main/InfoCard/Home/Meteo, componenti comuni e normal/reduced/off | Prima parte Base equivalente, senza I/O per frame |
| T2b | Overlay/settings/Info/Avvisi e tutti i moduli Sport/Racing | 21 superfici coperte, test routing/events passati |
| T3 | Functional e composizione alternativa, personalizzazioni guidate | Aspetto chiaramente diverso in type/layout/motion, stessi contenuti |
| T4 | Editor bozza, preview, catalogo, import/export, save/recovery | Terzo tema ed estensione registrati; reboot e fallimento save |
| T5 | Board visual/motion/perf, manifest, packaging e rollback | Gate del MasterPlan e delle tre specifiche chiusi |

Queste sono fasi tecniche, non sottoversioni già assegnate. Casa/Rete possono iniziare a sviluppare nuovi visuali sul contratto solo dopo T1 stabile; il loro rilascio non viene dichiarato dal Theme Engine.

## 10. Deploy e ritorno alla baseline

Prima T5: backup della distribuzione completa, manifest/hashes, preferenze e pacchetti utente. Runtime e dati personali sono separati; non distribuire cache/account/events come asset di un tema.

Preparare una copia staged, verificarla su Qt board e controllare permessi. La finestra EGLFS richiede pianificazione perché possiede il display; le prove headless isolate possono precederla senza fermare il kiosk.

Il deploy deve includere cartelle QML, qmldir, JSON/schema, fallback, font/licenze e asset. Una lista di soli *.py/*.qml di primo livello non basta più. Verificare il manifest ricorsivo dopo l'installazione.

Rollback: ripristinare l'intera distribuzione precedente, rimuovendo i file nuovi non previsti nel relativo manifest; conservare i dati utente e le chiavi legacy. Riavviare e verificare input, Home e font. Non usare il semplice cp -a di un vecchio backup come prova che tutti i file nuovi siano spariti.

Nessun deploy, modifica delle preferenze o restart è stato eseguito per questa analisi.
