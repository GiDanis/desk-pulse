# v0.6.6 — Review: bridge, Loader/focus e memoria dei font

**Aggiornamento attuazione v0.6.6:** il piano è implementato nei sorgenti. Contratti effettivi, uso e limiti sono nella [guida del motore](theme-engine-implementation-guide.md); stato dei gate e prove sulla scheda nel [resoconto di migrazione](v066-migration-report.md). Gli snippet di analisi illustrano alternative; per il formato eseguibile usare schema, registry ed esempi distribuiti.
**Revisione 1.0 · 2 ottobre 2026 · analisi, nessuna modifica al runtime.**

Risponde ai dubbi 2–4 sul Theme Engine. Le correzioni sono integrate nella [specifica costruttiva](theme-engine-construction-spec.md), nel [contratto delle presentazioni](theme-engine-presentation-spec.md) e nel [piano di migrazione](ux-theme-adaptation-plan.md). Non sono prove di un motore implementato.

Il successivo dubbio sulle icone è sviluppato nel [contratto dedicato](theme-engine-icon-spec.md): icon-font/geometrie hanno costi propri, catalogo semantico e renderer aperti preservano personalizzazione e scene del compagno.

## 1. Valutazione e priorità

| Dubbio | Giudizio | Decisione progettuale | Evidenza ancora necessaria |
| --- | --- | --- | --- |
| 2 · var/dizionari e tipizzazione | Rischio di contratto concreto; stima del costo a ogni frame da correggere | Alias tipizzati obbligatori; mappe confinate alla facade; nessuna pubblicazione Python per frame | Profilo bridge/conversioni/fan-out su Qt 6.8.2 |
| 3 · Loader, test e focus | Regressione concreta se la migrazione conserva le assunzioni eager | Host persistenti, readiness/revisione osservabili, assert scoped, input owner nella shell | Test async/error/cancel e due percorsi di input |
| 4 · font/cache/RAM | Rischio concreto di carico e crescita; caricamento TTF e texture non equivalenti | Caricamento su necessità, deduplica, riferimenti e budget di picco/plateau | Font reali, glyph warmup, swap ripetuti e memoria del renderer |

Questi punti sono prerequisiti di T1 e gate di T5. Non giustificano da soli una riscrittura Python → C++; richiedono un confine più preciso fra configurazione, render e lifecycle.

## 2. Bridge Python ↔ QML

### Cosa è corretto

Una mappa dinamica non fornisce un contratto statico per ogni chiave. Errori nei percorsi, conversioni ripetute e letture superflue vanno prevenuti. La proposta di flattening è corretta e rende esplicita la facade tipizzata già prevista nell'architettura.

### Cosa va corretto

Il numero di elementi × 60 fps non è il numero di valutazioni di un binding di colore. QML segue le dipendenze: il colore viene ricalcolato quando cambia una dipendenza, non perché un'altra proprietà sta animando. Un tema immutato non deve attraversare continuamente il bridge. Se si ripubblicasse la mappa a ogni frame, il problema diventerebbe reale per conversioni e invalidazione diffusa. [Qt: property binding](https://doc.qt.io/qt-6.8/qtqml-syntax-propertybinding.html).

Non assumere esattamente due hash-lookup: implementazione degli oggetti JS/wrapper QVariant, cache e percorso di esecuzione incidono. Il costo va profilato. La facade elimina le letture del dizionario dai consumatori standard e concentra la risoluzione negli alias; **non elimina ogni costo**. Qt raccomanda di evitare lavoro ripetuto e conversioni non necessarie, e distingue `var` dal vecchio `variant`. [Qt: performance QML](https://doc.qt.io/qt-6.8/qtquick-performance.html).

Una `readonly property color` è tipizzata, ma non certifica un binding AOT né equivale a una proprietà C++ letta senza overhead. [app.py](../app.py) carica Main.qml da file; il progetto attuale non dichiara una pipeline di moduli QML compilati. Configurare qmldir/import path/tooling è necessario anche per lint e completamento.

Un campo mancante può produrre undefined, un errore di accesso al ramo o warning di assegnazione/conversione. Non ha un esito universale "trasparente": può rimanere il valore precedente/default. Gli errori devono essere osservati, non dedotti dall'immagine.

### Contratto da adottare

- Theme pack e snapshot risolta usano percorsi canonici piatti: `"colors.surface"`, `"shape.radiusCard"`. La notazione annidata nell'esempio del dubbio non diventa un secondo formato supportato implicitamente.
- Resolver puro: schema, merge e validazione generano una snapshot completa. Campi sconosciuti nei namespace standard sono errori con percorso, non ignorati.
- ThemeService: nuova snapshot e revisione solo per cambi discreti; getter senza I/O e senza ricostruire dizionari a ogni lettura. La facade si collega a un'unica sorgente di commit, evitando binding contemporanei ad accessor notificati separatamente.
- StyleFacade: proprietà `color`, `int`/`real`, `string`, `bool` secondo schema. Theme espone lo stile live; preview/staging usano facades separate con la stessa API. I componenti dichiarano anche il parametro `style` con il tipo QML esportato, evitando che `property var style` annulli i benefici del controllo statico.
- Componenti standard: accessi agli alias; custom renderer: adapter tipizzato locale per i token della sua estensione. Nessun tetto ai namespace futuri e nessun obbligo di aggiungerli tutti al singleton globale.
- Motion: legge/cattura configurazione all'avvio o al retarget discreto della ricetta; interpolazione in QML/render adapter. Animare una proprietà visuale non riscrive la snapshot globale.

Esempio concettuale nel corpo della facade, non modulo completo già disponibile:

```qml
readonly property color surface: tokens["colors.surface"]
readonly property int radiusCard: tokens["shape.radiusCard"]
```

Il fallback avviene scegliendo la snapshot Base completa prima del servizio o mantenendo l'ultima valida su errore. La guardia `resolvedTokens.colors ? ... : default` dell'esempio non verifica che `surface` esista; un ramo presente con foglia assente resta invalido. Anche `value || default` è errato per raggio 0 o false. Fallback per campo non sostituisce la verifica schema ↔ facade.

### Gate del bridge

1. Tutti gli alias standard hanno tipo/percorso/default coerenti con lo schema; una vista che scrive un alias inesistente è segnalata dal tooling/harness.
2. Refusi, tipi errati e colori invalidi respinti prima del commit; raggio 0 preservato; Base disponibile senza servizio.
3. Nessuna pubblicazione theme durante un tween x/opacity a stile invariato; warning/binding removal rilevati nelle prove.
4. Cambio colore/layout e preview isolata applicano la revisione corretta senza mutazioni in-place.
5. Profilare pubblicazione, conversione, numero di binding invalidati e latenza del primo frame coerente sullo stesso carico. Ottimizzare con notifiche granulari/native soltanto se necessario, conservando commit e revisione completa.

## 3. Loader, suite e focus

### Regressione osservabile nei sorgenti

[check_dashboard.py](../check_dashboard.py) cerca e conserva cinque viste appena caricato Main; [check_sport_ui.py](../check_sport_ui.py) naviga e cerca immediatamente fonte, pannello e dettagli. Main oggi crea quei componenti anche quando invisibili. La sostituzione con Loader async rompe tali precondizioni: non va dichiarata compatibile senza aggiornare i harness.

`findChild(QObject, objectName)` interroga l'albero QObject; il scene graph GPU è un'altra struttura. Un `id` QML è locale e non sostituisce objectName/handle pubblico. Il visuale può essere assente o distrutto; il vecchio riferimento non rappresenta necessariamente la vista corrente.

### Soluzione funzionale e tecnica

Un ViewHost piccolo resta presente per content ID. Mantiene identità, contesto e autorità di visibilità; carica solo il visuale necessario. `currentItem` e readiness/revisione sono espliciti; la ricerca dei ruoli visuali parte da quel solo item pronto. ObjectName legacy sull'host aiuta le verifiche strutturali, ma non rende valide automaticamente proprietà come `panel.rows`: gli assert di dati vanno ricondotti a contesto o presentazione secondo il loro significato.

Non imporre a una futura visualizzazione grafica lo stesso albero di una tabella per far passare un test. Conservare copertura di fonte, offline, selected ID, tasti, avvisi e azioni; verificare dettagli del renderer con assert dedicati. Nessun preload di tutte le viste come workaround e nessun `if item is None: skip`.

I harness attendono la readiness applicativa della revisione richiesta con timeout finito; Loader.Ready non basta per asset/contratto. Registrano errori, warning e identità del candidato. Un callback di un vecchio caricamento non può fare commit dopo una navigazione più recente. La [specifica presentation §6](theme-engine-presentation-spec.md#6-commutazione-fra-layout-diversi) definisce il lifecycle.

### Due tipi di focus e due percorsi di input

Nel codice attuale `Connections.onKeyPressed` richiama `app.activateKey` indipendentemente dall'activeFocus del visuale. Un Item della shell riceve invece `Keys.onPressed`. La selezione evidenziata in Sport è un ID di prodotto; activeFocusItem è il destinatario dei tasti Qt. Perdere il primo o il secondo sono regressioni distinte.

Loader è un focus scope. La catena va configurata quando un editor deve ricevere tasti locali, ma `loader.item.forceActiveFocus()` in ogni onLoaded non è una regola sicura: potrebbe sottrarre input a menu, editor diverso o urgente arrivato durante il load. [Qt Loader: focus](https://doc.qt.io/qt-6.8/qml-qtquick-loader.html#focus-and-key-events).

La shell conserva input router e owner, con priorità urgente → overlay/editor → contenuto. Staging non interattivo e senza focus; commit autorizzato soltanto se revisione, contenuto e owner sono ancora validi. Se serve delega locale, FocusScope documentato e ripristino condizionato alla chiusura/distruzione. L'attore nel SceneHost persistente non prende focus per una semplice animazione.

### Gate di lifecycle/input

| Scenario | Assert da mantenere |
| --- | --- |
| Cold load / visuale non ancora pronto | Shell e comandi globali operativi; readiness corretta, nessun falso "vista mancante" |
| Navigazione durante load | Solo la destinazione corrente può diventare interattiva; callback obsoleto scartato |
| Menu o urgente durante load/swap | Owner prioritario conservato; nessun furto di activeFocus |
| Error/cancel | Layout valido o fallback; focus e selezione ripristinati |
| Cambio layout con dettaglio aperto | ID, tab, origine/stack, pagina e provider conservati |
| OK ripetuto / input nei transitori | Una sola azione valida; nessun replay verso la nuova vista |
| Test FakeKeypad e Qt keyboard | Entrambi verificati; l'uno non certifica l'altro |

## 4. Font, cache e memoria su A733

### Baseline e hardware

RSS 182,4 MiB e PSS 165,1 MiB sono il campione passivo delle 00:56 del 2 ottobre, [manifest originale](evidence/v066-theme-analysis/board-baseline.json). Non dimostrano leak né quanta memoria sia disponibile per scene e font. Non sono stati ripresentati come un nuovo benchmark.

Alle 19:23 è stata verificata in sola lettura l'identità CPU/Qt: sei CPU part `0xd05`, due `0xd0b`, Qt 6.8.2/PySide6 6.8.2.1; servizio active/running, stesso PID 202220 e NRestarts 0. [Riscontro SSH](evidence/v066-theme-analysis/risk-review-board.json). L'A733 integra sei Cortex-A55 e due Cortex-A76, secondo [Allwinner](https://www.allwinnertech.com/index.php?a=index&c=product&id=139&solveid=34). Il riferimento Cortex-A53 nel dubbio va corretto; questo non dispensa dal profiling.

### Il costo non è "8 TTF = 8 atlanti completi"

Registrazione di file, font engine, layout/shaping e texture dei glifi sono risorse diverse. Il codice Qt 6.8.2 popola la cache distance field per glifi richiesti, evitando di richiedere di nuovo quelli già presenti; non rasterizza tutti i caratteri solo perché il font è stato registrato. [Sorgente Qt](https://github.com/qt/qtdeclarative/blob/v6.8.2/src/quick/scenegraph/qsgadaptationlayer.cpp).

Con QtRendering il distance field è scalabile: più dimensioni di testo non significano necessariamente più copie dell'atlante. Font/pesi diversi, glifi nuovi, qualità scelta, fallback e renderer incidono comunque. NativeRendering usa il percorso specifico della piattaforma; CurveRendering è un'altra opzione, disponibile già su Qt 6.8, con tradeoff da misurare. Aumentare renderTypeQuality può aumentare la memoria. [Qt Text](https://doc.qt.io/qt-6.8/qml-qtquick-text.html#renderType-prop).

Il pericolo più importante per un dispositivo sempre acceso è il **picco** vecchio+nuovo visuale durante staging, insieme alla crescita dopo molte preview/font diversi. La scena del futuro compagno va inclusa: non basta ottimizzare la Home statica.

### Decisioni integrate

- Ritirato il candidato generico di 8 font attivi. Per T1 partire da una UI con 2–3 pesi e un eventuale numerico, senza imporre quel conteggio all'estensibilità futura.
- Catalogo di metadati; registrazione/preparazione su necessità; niente otto preview vive o carico di tutti i font all'avvio.
- Font registry condiviso nel processo, deduplica per contenuto/versione e riferimenti di tutti gli utilizzatori. Rilasciare soltanto a fine uso; verificare famiglie/pesi reali e conflitti fra pacchetti.
- Uno staging alla volta, budget esplicito per picco e regime, con percorso diretto se la memoria non consente due visuali contemporaneamente.
- Il limite delle cache applicative non implica un'API di controllo completo sulle cache Qt/driver. removeApplicationFont rimuove la registrazione; la sua API non certifica il recupero immediato di tutta la memoria grafica. [QFontDatabase](https://doc.qt.io/qt-6.8/qfontdatabase.html#removeApplicationFont).
- Non assumere una VRAM discreta né derivare occupazione GPU dal solo PSS. Dichiarare cosa è osservabile su questo driver e cosa resta ignoto.

### Gate di memoria e scelta renderer

Misurare lo stesso contenuto dopo avvio freddo, sola registrazione, primo uso, warmup e staging. Usare glifi italiani, simboli, cifre, nomi sportivi lunghi, pesi e dimensioni dei ruoli effettivi. Separare 100 cambi fra gli stessi temi (riuso) da cambi verso nuove famiglie (espansione del working set).

Registrare tempo di primo utilizzo, RSS/PSS/cgroup, picco di swap, risorse applicative vive e plateau dopo assestamento. Metriche GPU/driver solo se disponibili e con metodo dichiarato. Budget numerici definitivi in T0/T1; il candidato +20 MiB PSS non copre automaticamente il picco o ogni risorsa grafica. Cache che si stabilizza e leak monotono richiedono interpretazioni diverse.

Se il budget viene superato: prima meno risorse simultanee e migliore riuso; poi confronti controllati su rendering/qualità del testo o adapter specializzato. CurveRendering per testo grande è un candidato, non una migrazione globale prescritta. Conservare il workaround NativeRendering di DeviceInfo fino a prova sulla board. Nessun riavvio periodico usato per mascherare crescita persistente.

## 5. Dove intervenire nella futura implementazione

| Area | Intervento richiesto |
| --- | --- |
| theme_core / token-contract, da creare | Chiavi canoniche, schema, default completi, errori di percorso, alias/tipi |
| ThemeService / StyleFacade / Theme, da creare | Pubblicazione discreta, API tipizzata comune live/preview, getter economici |
| app.py / launcher | Vita dei servizi, moduli/tooling, registrazione delle sole risorse necessarie |
| Main.qml / controller / ViewHost | Input owner persistente, host stabili, readiness/revisione, callback obsoleti |
| check_dashboard / check_sport_ui / harness correlati | Attese di readiness, assert scoped, refs riacquisiti, copertura keyboard Qt |
| AppText / resource registry | Famiglia/peso/renderer espliciti, deduplica e riferimenti, fallback osservabile |
| Harness board motion/memoria | Bridge, primo uso dei glifi, picco/plateau, scene persistenti e carico identico |

**Stato conclusivo della review:** rischi riconosciuti e soluzioni definite a livello di contratto; implementazione e chiusura quantitativa ancora da dimostrare in T1/T5. La personalizzazione profonda e il compagno futuro restano compatibili con queste regole.
