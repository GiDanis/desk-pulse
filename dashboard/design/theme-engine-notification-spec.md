# Theme Engine — audit e contratto delle notifiche

**Revisione 2 · 3 ottobre 2026.** Audit iniziale sul runtime v0.6.6, commit 15b7f7a; implementazione successiva autorizzata nella stessa giornata.

**Stato: sei superfici implementate; collaudo e distribuzione nel [resoconto dedicato](theme-engine-notification-migration-report.md).** Le sezioni 1–2 conservano il risultato negativo della baseline precedente, compreso il difetto dei testi lunghi. Le sezioni 3–10 sono il contratto seguito per la migrazione; la [guida aggiornata](theme-engine-implementation-guide.md#personalizzare-gli-avvisi) descrive API e uso effettivi. La verifica iniziale era di sola lettura; implementazione e installazione hanno evidenze separate.

## 1. Baseline verificata

| Superficie | Baseline prima della migrazione | Personalizzazione disponibile | Lacuna |
| --- | --- | --- | --- |
| Banner piccolo | `EventBanner.qml`, 872×93 a x44/y459 | Token condivisi e `banner.enter/exit` | Geometria e composizione fisse, nessun ID di presentazione |
| Banner grande | `EventLargeBanner.qml` → `EventBanner { large: true }`, 872×446 a x44/y106 | Come il piccolo, testo più grande | È una variante dello stesso componente, non un visuale indipendente |
| Urgente | `EventUrgent.qml`, finestra intera | Stile condiviso, indicatore semantico | Posizioni, guida e struttura fisse; nessun renderer alternativo |
| Badge non letti | `UnreadAlertsBadge.qml`, 276×36 a x487/y31 | Stile condiviso | Posizione, testo e struttura fissi |
| Elenco Avvisi | Rami `alerts` di `DashboardOverlay.qml` | Token di stile | Tre righe per pagina e geometria scritte nel componente |
| Dettaglio | Rami `alertDetail` di `DashboardOverlay.qml` | Token di stile | Coordinate verticali fisse, nessuna gestione del testo lungo |

`Main.qml` istanzia direttamente i visuali. `presentations/registry.json` contiene otto content ID di pagina e **zero content ID di notifica**. Base e Functional cambiano stile, ma non disposizione delle notifiche. Font e dimensioni sono ruoli globali: cambiare il corpo di un avviso modifica anche altri componenti che usano quel ruolo.

Il catalogo è già estensibile: una nuova estensione può registrare content ID per le notifiche e un pacchetto JSON può selezionarli. Il problema è nel consumo: **Main continua a disegnare i componenti storici e ignora quella selezione**. Il probe lo dimostra registrando un visuale temporaneo, accettato dal resolver, e osservando zero host collegati e il banner storico ancora visibile. Non basta aggiungere righe al registry.

## 2. Prove del check

Sono stati eseguiti `check_events.py`, `check_dashboard.py`, `check_settings.py`, `check_theme_ui.py` sul PC e sulla board. Tutti passano. Coprono logica/persistenza eventi, banner, non letti, cache, categorie, quiet hours e focus durante caricamenti/cambi tema. Queste suite non provano la sostituibilità delle notifiche: i componenti sono ancora statici.

Il [probe ripetibile](evidence/notification-engine-audit-2026-10-03/probe.py) ha inoltre verificato nove combinazioni: piccolo/grande/urgente × Base giorno/Functional giorno/Functional notte, con movimento disattivato per separare gli assert di stato dai tween. In ciascuna combinazione:

- cambia l'accento secondo la palette; le dimensioni restano identiche;
- ID, stato SQLite di consegna/chiusura/lettura e scadenza monotona del banner restano invariati;
- cambiare tema non invoca `dismissEvent` o `markEventSeen`;
- il focus Qt resta su `inputOwner`, anche con un urgente.

Le preferenze sono isolate; gli eventi sono simulati, nessun provider viene interrogato. Quiet hours è disattivato solo nella fixture per rendere il test indipendente dall'ora. Risultati: [PC Qt 6.11.2](evidence/notification-engine-audit-2026-10-03/local/report.json), [board Qt 6.8.2/PySide 6.8.2.1](evidence/notification-engine-audit-2026-10-03/board/report.json), [suite e salute del servizio](evidence/notification-engine-audit-2026-10-03/board/checks.json). Il servizio reale mantiene PID 6878, NRestarts 0 e lo stesso hash delle preferenze.

**Difetto riprodotto:** un titolo di 100 caratteri con spazi, una descrizione di 240 caratteri e scala 110%, tutti validi per il contratto degli eventi, sovrappongono titolo/descrizione e descrizione/fonte nel dettaglio. Sulla board le sovrapposizioni verticali sono **121 px e 36 px**; sul PC **161 px e 66 px**. Le differenze confermano che le metriche dei font non si possono certificare soltanto sul PC. [Cattura board a 960×640](evidence/notification-engine-audit-2026-10-03/board/long-detail.png).

Le prove sulla board sono offscreen/software, sul codice realmente installato. Non sono misure EGLFS di FPS o memoria GPU e non certificano un nuovo layout. La produzione non è stata fermata o riavviata.

## 3. Confine fra motore eventi e presentazione

Conservare Python/PySide6 per validazione, priorità, identità, cache, SQLite, scadenze e preferenze. Conservare Qt Quick/QML per composizione, asset e animazioni. Non emerge dal check un motivo per cambiare linguaggio o aggiungere un secondo renderer.

`EventEngine` decide ordinamento, validità, categoria, rank, non letti e livelli già notificati/chiusi. `EventService` decide disponibilità, quiet hours e durata del banner. La shell instrada i comandi. Il tema disegna la decisione del sistema.

| Personalizzabile dal tema | Comportamento del sistema conservato |
| --- | --- |
| Presentazione diversa per piccolo/grande/urgente/badge/elenco/dettaglio | Priorità e categoria stabilite dall'evento |
| Allineamento, ancoraggio, dimensioni, spaziature, forme, bordi | Identità, revisione e deduplicazione |
| Ruoli tipografici indipendenti per ciascuna superficie | Lettura/chiusura tramite azione esplicita, non onCompleted |
| Icona semantica, visualizzazione della fonte, illustrazioni, decorazione | Fonte, validità e stato salvato/offline attendibili |
| Ricette di movimento ed effetti del visuale | Urgente e comandi disponibili immediatamente |
| Densità/paginazione e disposizione della guida | Tutto il testo accessibile nel dettaglio; guida e focus leggibili |

Gli otto secondi oggi sono in `EventService._tick`, non nel tema. Se in futuro si vuole una durata configurabile, introdurre una preferenza Notifiche separata e validata; un cambio di palette non deve modificarla o riavviarla. Anche categorie silenziate, quiet hours e formato richiesto dall'evento restano preferenze/policy di prodotto. `bannerSize` seleziona piccolo/grande, non la priorità.

Non dedurre la gravità dal titolo, dall'icona o dal colore del tema. Usare `weatherSeverity`, categoria, priorità e rank strutturati. La forma dell'indicatore può cambiare; il significato resta riconoscibile anche con etichetta testuale. Conservare le convenzioni dei livelli ufficiali nel ruolo semantico; rendere personalizzabili pannello, decorazione e composizione circostante.

## 4. Sei slot indipendenti

Adottare questi content ID e fallback applicativi:

| Content ID | Fallback applicativo | Host stabile |
| --- | --- | --- |
| `alerts.banner.small` | `builtin.alerts.small` | `eventBanner` |
| `alerts.banner.large` | `builtin.alerts.large` | `eventLargeBanner` |
| `alerts.urgent` | `builtin.alerts.urgent` | `eventUrgent` |
| `alerts.badge` | `builtin.alerts.badge` | `unreadAlertsBadge` |
| `alerts.inbox` | `builtin.alerts.inbox` | `alertsInbox` |
| `alerts.detail` | `builtin.alerts.detail` | `alertDetail` |

Un tema eredita tutti i fallback da Base e sovrascrive soltanto ciò che desidera. Piccolo e grande possono scegliere componenti completamente diversi. Nessuna condizione `if themeId === ...` in Main e nessun obbligo di replicare l'albero del componente storico.

Esempio di selezione di renderer: questi ID illustrativi devono essere registrati da un'estensione. La guida contiene un esempio importabile con gli ID forniti:

```json
{
  "presentations": {
    "alerts.banner.small": "example.alerts.topRail",
    "alerts.banner.large": "example.alerts.splitCard",
    "alerts.urgent": "example.alerts.focusPanel"
  },
  "tokens": {
    "notifications.small.titleSize": 28,
    "notifications.large.padding": 28,
    "notifications.large.radius": 14
  }
}
```

Un pacchetto JSON seleziona template/asset/token già registrati. Per una composizione inedita, un'estensione QML applicativa aggiunge renderer e token `ext.*`; il resolver e l'engine eventi non devono cambiare. Questa distinzione va spiegata nella guida per autori: i pacchetti di dati attuali non eseguono QML importato. Non promettere che il solo JSON possa descrivere un renderer arbitrario o che ogni animazione costi uguale sulla board.

Per l'uso senza programmare, fornire preset illustrativi e un selettore alimentato dal registry: fascia, scheda e disposizione divisa sono esempi, non una lista definitiva di forme ammesse. Validare override, ereditarietà, import/export e reset con gli stessi meccanismi del Theme Engine.

## 5. NotificationContext API 1

Creare un contesto dedicato, indipendente dall'istanza visuale e dall'accesso diretto a `dashboard.*`.

| Campo | Contratto |
| --- | --- |
| `apiVersion`, `contentId`, `mode` | Identità/versione; piccolo, grande, urgente, badge, elenco o dettaglio |
| `event` | Snapshot dell'evento: ID/revisione, categoria, priorità/rank, gravità, titolo, descrizione, fonte, timestamp, seen/upcoming |
| `items`, `selectedEventId`, `unreadCount` | Modello elenco e selezione stabile per ID; aggiornamenti non trasferiscono silenziosamente la selezione a un altro evento |
| `sourceStatus` | Stato effettivo della fonte, distinto dal livello dell'allerta |
| `active`, `interactive`, `exiting` | Autorità di visualizzazione/azione assegnata dalla shell; staging senza azioni |
| `style`, `appearanceRevision` | Facade tipizzata della stessa revisione della presentazione |
| `viewportWidth/Height`, `safeArea`, `occupiedRegions` | Area assegnata, spazio per contenuto/guida e ingombri da comunicare alle scene |
| `actions`, `commandHints` | Azioni realmente disponibili e tasti scelti dal router, non inventati dal tema |
| `requestAction(actionId, eventId, arguments)` | Validazione nel controller: evento ancora valido, modalità, owner e azione consentita |
| `ready`, `error`, `settleMotion()` | Stato del visuale e finalizzazione controllata |

Azioni semanticamente nominate: `openInbox`, `openDetails`, `dismiss`, `home`, `back`, `selectEvent`, `moveSelection`, `scrollDetails`. Il renderer non richiama il DB e non segna un evento letto da onLoaded/onCompleted. Conservare il comportamento corrente: aprire il dettaglio dall'elenco marca quell'evento letto; chiudere un urgente registra chiusura/lettura; un banner semplicemente presentato resta non letto.

Per banner in uscita, congelare evento **e** stile fino a fine transizione: nessun testo svuotato o sostituito dalla nuova notifica durante il fade. Una decorazione non prende il focus del tastierino. Le MouseArea richiedono le stesse azioni validate dei tasti Qt.

## 6. Token profondi, layout robusti

Aggiungere gruppi separati per piccolo/grande/urgente/badge/elenco/dettaglio. Nei template standard esporre almeno ruoli di superficie/testo/accento, bordo/raggio, padding/gap, ancoraggio, larghezza/altezza consentite, font di titolo/corpo/fonte/guida, linee sintetiche del banner e densità dell'elenco. Font e grandezze della notifica devono poter essere diversi da Home e Sport.

I gruppi ereditano i ruoli globali quando non personalizzati. Estendere schema, resolver, validazione dei range/contrasto, facade e fallback insieme: non duplicare default incoerenti in sei componenti. Le proprietà standard consumate dai visuali restano QML tipizzate; il dizionario dello snapshot viene convertito dalla facade a cambi discreti, non interrogato per pilotare ogni frame. Non attribuire a questa scelta costi zero o compilazione C++ garantita.

La geometria di un template deve essere una composizione adattabile, non un foglio di coordinate libere. Usare misure del contenuto e area disponibile; titolo/corpo/fonte non si sovrappongono. Banner sintetici possono elidere, ma il dettaglio deve offrire lettura completa tramite area scorrevole/paginata controllabile con `2/8`, mantenendo guida e azioni disponibili. Il dettaglio attuale non gestisce quei comandi: aggiungerli al controller, non soltanto una Flickable nel visuale.

Gestire parole lunghe, font con metriche diverse, testo 85–110%, campi opzionali e contenuto offline. Il contratto evento corrente limita titolo/descrizione a 100/240 caratteri: è una scelta dei dati, distinta dalla capacità del renderer; un futuro ampliamento richiede validazione/cache/schema evento coerenti.

La densità dell'elenco si calcola nel controller con il numero di righe effettivamente disponibili, mantenendo selectedEventId e ensureSelectionVisible. Cambiare tema non deve affidarsi al vecchio `alertIndex` se la lista riceve inserimenti/rimozioni durante lo swap.

## 7. Host, preparazione e commit

Usare un `NotificationHost` persistente o un host generico con contesto specializzato. Riutilizzare le parti affidabili di `ViewHost` — identità, staging, generation ID, readiness, fallback — senza passare un `PresentationContext` di pagina o forzare viewport 872×455 a tutte le notifiche.

**Adeguamento indispensabile:** ThemeService oggi aspetta soltanto `_active_content`, cioè la pagina corrente, prima di pubblicare una presentazione diversa. Con più superfici visibili occorre una preparazione coordinata: identificare gli host interessati; caricare candidati non interattivi; raccogliere esiti con generazione/content ID; pubblicare una revisione coerente quando tutti i visuali necessari sono pronti. Un errore mantiene il precedente aspetto, senza rendere valido Apply. Navigazione, nuova urgenza e una richiesta più recente invalidano callback obsoleti.

Per urgenze conservare un visuale Base di emergenza immediatamente disponibile e indipendente da caricamento/errore del tema. Preparare il visuale urgente selezionato all'attivazione del tema; in caso di notifica arrivata prima di Ready, mostrare immediatamente il fallback e rendere i comandi disponibili. Nessun fade-in obbligatorio che nasconda inizialmente il titolo urgente. L'eventuale sostituzione successiva conserva ID, azioni e focus.

Banner ed elenco/dettaglio possono caricare su richiesta con componenti preparati; non istanziare tutte le varianti di tutti i temi. Limitare staging al vecchio visuale più il candidato necessario; condividere font e asset. Distruzione/retention devono essere esplicite e misurate.

Collegare disponibilità banner alla readiness dell'host, oltre che all'assenza di overlay. Oggi `EventService` marca notificato e avvia otto secondi quando assegna `visibleBanner`, prima di un eventuale Loader: introdurre una fase preparato/presentato oppure un gate pronto e un acknowledgment validato per ID/generazione. Un caricamento lento non deve consumare il tempo di lettura né dichiarare consegnato un avviso mai disegnato. Il timer resta uno solo nel servizio; lo swap non lo riavvia. Una cancellazione/urgenza durante la preparazione annulla il candidato prima della consegna.

## 8. Motion, icone e futuro compagno

Le ricette esistenti `banner.enter/exit` restano fallback. Prevedere override indipendenti per piccolo e grande, con eventi registrati ed eleggibilità coerenti. Il visuale può usare animazioni Qt native per progressi/icone/decorazione senza loop Python. Ogni renderer rispetta Normale/Ridotto/Disattivo e implementa settle/pause; nessuna coda di tween per ogni aggiornamento del provider.

`urgent.present` conserva un'apparizione immediata. Dopo la presentazione si possono animare decorazioni che non tolgono testo/comandi; Ridotto/Off devono eliminarne il movimento appropriato. Non introdurre un ritardo usando l'animazione del compagno.

Icone tramite `AppIcon` e ID semantici di categoria/fonte/gravità, con glifo, geometria, asset o componente registrato. Non limitare tutte le future notifiche a un icon-font. Definire fallback per categoria sconosciuta e costo delle immagini/atlanti; utilizzare cache/font registry già esistenti.

Il contesto notifica espone ingombri reali per una scena. Il futuro compagno può reagire all'evento tramite il controller della scena, senza cambiare consegna/lettura o duplicare un avviso. Shell e NotificationHost restano responsabili di z-order e preemption. Urgente sopra la scena; azioni e dati mai coperti. La v0.6.6 sospende già SceneHost per overlay/urgenze: non eliminare questa protezione mentre si aggiunge il contratto degli ingombri.

## 9. Interventi sul codice

| File/area | Intervento necessario |
| --- | --- |
| `presentations/registry.json`, pacchetti Base/Functional | Registrare sei slot, fallback e visuali alternativi dimostrativi |
| `themes/token-contract.json`, `StyleFacade.qml`, schema/fallback generati | Ruoli notifiche, ereditarietà, controlli range/contrasto e facade tipizzata |
| `components/NotificationContext.qml`, `NotificationHost.qml` | Dati/azioni, identità, readiness, viewport e lifecycle |
| `theme_service.py`, eventuale coordinatore host | Commit di tutti i candidati necessari, annullamento e recupero |
| `Main.qml` | Sostituire istanze dirette, mantenere router e z-order; selezione ID e scroll dettaglio |
| `EventBanner.qml`, `EventLargeBanner.qml`, `EventUrgent.qml`, `UnreadAlertsBadge.qml` | Fallback visuali basati sul contesto, senza stato di consegna/lettura |
| `DashboardOverlay.qml` | Estrarre rami Avvisi/dettaglio in presentazioni registrate e correggere flusso del testo |
| `events.py` | Readiness/presented e consegna, timer invariato fra cambi tema |
| `event_core.py` | Conservare policy/DB; nessuna necessità di migrare SQLite per il solo cambio di visuale |
| `SettingsPanel.qml` | Sezione Aspetto → Avvisi: selettori dal registry, anteprima isolata, override/reset |
| `MotionController`, registry motion/icone e SceneHost | Eventi per modalità, significati, ingombri e preemption |
| Harness, guide e packaging | Ruoli/host stabili, test di nuove composizioni, distribuzione completa e rollback |

## 10. Sequenza e criteri di completamento

1. Formalizzare API/slot/token e correggere il dettaglio con testo lungo, conservando il fallback visivo attuale per testi ordinari.
2. Estrarre controller/contesti e introdurre host con preparazione/commit coordinati, readiness di consegna e urgente di emergenza.
3. Registrare fallback Base e alternative realmente diverse per **piccolo e grande**; dimostrare un terzo tema/estensione senza modifiche a Main/EventEngine/ThemeService.
4. Aggiungere editor guidato, anteprima con eventi simulati fuori da DB/consegna reali e import/export/reset degli override.
5. Validare su PC e board, poi EGLFS con carico comparabile; backup, installazione e rollback prima di dichiarare completata questa estensione.

Gate funzionali: tema differente durante piccolo/grande/urgente; menu o urgente durante staging; evento scaduto/cancellato/sostituito; callback vecchio; font/asset/componenti mancanti; night/reduced/off; avvio offline; testi massimi e scale estreme; elenco aggiornato mantenendo selectedEventId; dettaglio interamente leggibile da tastierino; badge e guida; nessuna doppia consegna/lettura/chiusura né riavvio del timer; fallback urgente immediato.

Gate prestazioni: misurare intervalli frame, latenza input, primo frame dell'avviso, tempo di preparazione e RSS/PSS dopo warmup e cambi ripetuti. Partire dai budget v0.6.6 documentati (frame p95 ≤20 ms, cambio profilo p95 ≤150 ms), separando font freddi e lavoro del provider. Questi sono obiettivi da verificare per i nuovi visuali, non risultati del presente audit. Verificare font/asset selezionati su richiesta e memoria dopo rilascio dei Loader; non promettere budget GPU senza telemetria affidabile.

**Decisione del check iniziale:** la personalizzazione completa delle notifiche era una lacuna del Theme Engine. È stata chiusa con i sei host, il contesto dedicato, i ruoli locali, le composizioni alternative e i gate del [resoconto di migrazione](theme-engine-notification-migration-report.md). Il motore eventi esistente offre una buona base da conservare; il lavoro principale è su presentazioni, contesti, readiness, layout e commit coerente.

## Riferimenti tecnici

Per lifecycle, focus e caricamento: [Qt Quick Loader 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-loader.html). Loader.Ready non equivale a una misurazione del primo frame visibile, e il focus va assegnato dal router.

Per binding, risorse e profilazione: [QML Performance Considerations 6.8](https://doc.qt.io/qt-6.8/qtquick-performance.html). Usare animazioni native e preparazione limitata; valutare gli interventi con misure sulla board.
