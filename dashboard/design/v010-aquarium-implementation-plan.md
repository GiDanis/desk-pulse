# SmartPC v0.10 — Acquario Calm · piano esecutivo

**Revisione 1 · 25 ottobre 2026 · Europe/Rome**

> Aggiornamento esecutivo, 26 ottobre: implementazione completata e rc.2/Apple1.6.5 installati. Questo documento conserva lo studio precedente; [chiusura, stato P0–P7 e limiti](v010-aquarium-completion-report.md).
**Stato dello studio alla redazione: pronto come specifica tecnica di partenza, non implementato.** Questa chat autorizza aggiornamento dell'analisi, ricerca e piano; non avvia codice applicativo, generazione degli asset o operazioni sulla board. [Studio di integrazione rev.2](v010-aquarium-integration-study.md), [ricerca rev.2, 28 schede](v010-aquarium-online-research.md), [MasterPlan](release-masterplan.md).

Baseline riletta nei file: **core 0.9.4-rc.3, 654 file, Theme API 2.12 / 68 superfici, Apple Calm 1.6.4 attivo**. [Chiusura funzionale Gioco](v094-game-functional-closure-report.md), [orario/barra e dimming](v094-header-clock-report.md), [ottimizzazioni trasversali consegnate](v093-implementation-report.md). Sono evidenze documentate, senza nuova verifica live in questo studio. L'[audit locale del 25 ottobre](v010-aquarium-source-audit-2026-10-25.json) identifica i file letti e il confronto con il vecchio audit.

## 1. Decisioni di piano: cosa costruire

Sono default di lavoro scelti per eliminare ambiguità tecniche, non scelte grafiche già approvate dall'utente.

| ID | Decisione esecutiva | Motivo / verifica |
| --- | --- | --- |
| D1 | Famiglia `aquarium`, dopo Gioco, slot 9; una vista `aquarium.main`. | Conservare slot precedenti, Home e filtri. Nuova visibilità default attiva; migrazione solo additiva. |
| D2 | Canvas nativo 960×640; **barra con HH:mm conservata sopra la scena**. | La richiesta del 22 ottobre supera l'ipotesi di shell completamente nascosta. Il viewport è full screen, il nuoto usa l'area sicura sotto il chrome. |
| D3 | Un ambiente Calm 2D, camera fissa, due specie originali, sei pesci (4 piccoli/2 medi). | Profilo nominale confrontabile; 1/4/8/16 solo laboratorio. No configuratore di vasche nel primo rilascio. |
| D4 | Rig QML a parti come default; sprite come confronto, shader solo se la qualità o le misure lo richiedono. | Trasferibile al compagno, senza nuovo motore o tool runtime obbligatorio. |
| D5 | Movimento visuale in QML, un FrameAnimation; stato/configurazione/lifecycle in Python. | Nessun aggiornamento Python per frame, nessun worker numerico o clock del Gioco riusato. |
| D6 | 5 pausa/ripresa, 4/6 famiglia, 1 Home, 3 Avvisi, 7 Home dalla vista principale, 9 Menu. | Uscita deterministica coerente con la shell; niente stack di ritorni speciale per una sola vista. |
| D7 | Menu/Inbox congelano; al ritorno riprende solo se prima playing. Urgente congela e richiede 5 per riprendere. | Pausa utente non cancellata dagli overlay; nessun catch-up. |
| D8 | Reduced e Off statici nella prima versione. | Comportamento deterministico, controlli globali rispettati; microgesti Reduced sono un'estensione da qualificare. |
| D9 | Asset locali, niente cloud/API/AI nel loop. Fondo opaco; bolle, piante animate e luce dinamica fuori dal profilo iniziale. | Test leggibile del costo dei modelli animati, senza effetti confondenti. Decorazioni statiche consentite. |
| D10 | Conservare governor/driver/priorità della candidata installata. | v0.9.3 ha selezionato performance su policy6/A76, nice GUI 0/affinità libera; non ripartire da schedutil per presunzione. Rilettura nel preflight futuro. |

La scena resta un test anche della produzione AI: master → parti → rig/clip → verifica visiva e prestazionale. Un placeholder geometrico può abilitare i test del routing, ma non chiude qualità degli asset o 60 fps della scena finale. Il catalogo illustrato finale resta da produrre e valutare; non è un blocco alla scrittura dell'architettura dopo autorizzazione.

## 2. Novità dal 13 ottobre e conseguenze

| Scoperta verificata nei file | Conseguenza operativa |
| --- | --- |
| API 2.12 e clock pubblico della shell, Apple 1.6.4, dimming globale z=30. | Conservare clock/barra e un solo filtro luminosità; nessun overlay Acquario sopra z=30. Non ripristinare bundle 1.6.2 o l'incidente storico. |
| `PublicContextAdapter` trattiene il payload dei nascosti; `modelDomains` restringe i provider; Main evita alberi completi per scene/avvisi. | AquariumContext senza domini informativi, payload dedicato e breve; non leggere `controller.model` generale per ottenere sei pesci. |
| Il bundle consente `dataDomains` solo a PageContext e a un elenco esplicito. | AquariumContext dedicato: **omettere `dataDomains`**, non aggiungere `aquarium` a quell'elenco per aggirare il controllo. Nessun data-domains.json da creare. |
| `currentThemeRenderCoherent()` richiede Ready anche per SceneHost. | Se SceneHost è soppresso durante Acquario, dichiararlo non richiesto nella sola condizione di coerenza; non lasciarlo necessario ma impossibilitato a caricarsi. |
| `PageHost` compensa y−90, contentLayer non ha clip. | Geometria canvas (0,0,960,640) produce host locale y=−90; verificare coordinate assolute, clip e z. Non cambiare il parent globale delle altre pagine. |
| Metadati/letture pesanti del Gioco ora sono separati e l'Auto è in manutenzione. | Non riaprire training, algoritmi o nuove reti per fare Acquario; confrontare carico provider corrente, Gioco senza learner attivo. |
| Fonti Qt al tag 6.8.2 contengono FrameAnimation e Image.retainWhileLoading. | Si può scrivere il percorso candidato senza affidarsi a feature solo 6.9+, con smoke test sul pacchetto effettivo prima di adottarle. |

## 3. File da creare e modificare

Tutti i percorsi della tabella sono relativi alla root del repository. I nuovi file sono **previsti**, non presenti perché questo è un piano.

| File / gruppo | Cambiamento esatto previsto |
| --- | --- |
| `dashboard/aquarium.py` (nuovo) | AquariumService(QObject): snapshot piccolo, session/revisioni, pausa/ripresa, riduttore lifecycle e close; nessun timer di animazione. |
| `dashboard/aquarium_catalog.py` (nuovo) | Lettura/validazione del catalogo asset, limiti, path risolti dentro il pacchetto, hash e profili; niente decode immagini nel costruttore della GUI. |
| `dashboard/presentations/aquarium-main.qml` (nuovo) | Entry point pubblico AquariumContext, readiness, lifecycle e delega al renderer. |
| `dashboard/presentations/aquarium/AquariumVisual.qml`, `FishRig.qml`, `FishSprite.qml`, `AquariumMotion.js` (nuovi) | Scena condivisa, attori e matematica pura con RNG esplicito; nessuna funzione che legge servizi o scrive file. Sprite resta confronto finché selezionato. |
| `dashboard/assets/aquarium/calm-v1/` (nuovo) | Catalogo runtime, ambiente day/night, parti/clip e hash. Originali/concept in design separati dal deployment. |
| `dashboard/app.py` | Costruire/iniettare controller leggero; close esplicito nel teardown. Caricamento del catalogo al primo accesso, non al boot. |
| `dashboard/state.py` | Modulo `aquarium` disponibile localmente, visibilità persistita, proprietà del servizio; nessuna query rete per availability. |
| `dashboard/Main.qml` | Famiglia/slot/vista; servizio/snapshot; pageGeometry/safeArea; comandi e broker; payload anticipato dedicato; PageHost; lifecycle sul vero commit/destinazione; sospensione ambientale e coerenza del tema. |
| `dashboard/components/PublicContextAdapter.qml` / `PresentationContext.qml` | Trasporto mirato se necessario; preferire payload dedicato di Main, evitare nuove dipendenze del modello globale e oggetti servizio pubblici. |
| `dashboard/theme-api/{contexts,surfaces,actions}.json` | Nuovi DTO/AquariumContext, una superficie e due azioni; ruolo/motion/clock ereditati. Toccare semantic-roles solo per campi realmente nuovi. |
| `dashboard/theme_api.py`, `theme_contexts.py`, `theme_api_contract.py` | Normalizzazione tipizzata, default, modelli identitari/enum e azioni; riusare generazione esistente e aggiungere codice speciale solo dove richiesto. |
| `dashboard/presentations/registry.json`, temi builtin | Renderer API2 e fallback per nuova superficie; compatibilità dei bundle precedenti. Scene ambientali conservate. |
| Apple Calm / kit | Mappatura della superficie solo se serve un renderer specifico, colori/focus/menu/orario conservati; kit rigenerato. Non cambiare la versione del bundle per sola documentazione. |
| `dashboard/fixtures/theme-runtime/` e `dashboard/check_aquarium*.py` (nuovi test) | Matrice §10 e fixture statiche, harness QML e prove lifecycle/asset; nessun contatto con stato utente. |
| `scripts/benchmark-aquarium.py` (nuovo, test) | Esecuzione riproducibile in profilo privato, run id/seed/carico e report; niente SSH, installazioni o avvio automatico del training. |
| Versione/manifest/report/README | Aggiornati al momento della candidata; non anticipare versione installata, API/superfici o risultati di benchmark. |

**Versioni candidate:** aggiunta API minore successiva alla 2.12, presumibilmente 2.13, con 69 superfici se si aggiunge soltanto aquarium.main. Prima di codificare rileggere contratto corrente per evitare collisioni con altri lavori. La release prodotto rimane v0.10; `aquarium.menu` non si aggiunge: bastano le voci contestuali del Menu esistente.

## 4. Contratto pubblico da implementare

`AquariumContext extends SurfaceContext`, contextVersion 1. Campo richiesto `aquarium: AquariumSnapshot`. I campi comuni style/lifecycle/viewport/safeArea/motionPolicy/commands/actions restano quelli esistenti. `modelDomains` restituisce lista vuota per questa superficie. La registry del renderer non dichiara `dataDomains`; niente `model.aquarium` o array di posizioni pubblicati a 60 Hz.

| DTO / campo | Tipo e vincoli di piano |
| --- | --- |
| AquariumSnapshot.sessionId | string non vuota per visita, rigenerata dopo unload/reboot; non è l'identità di una specie. |
| configurationRevision / assetRevision | int ≥0 / string di versione+digest; stabili finché configurazione/asset non cambiano. |
| status / errorCode / errorText | enum idle/loading/ready/error; stringhe vuote in assenza d'errore, messaggio sintetico leggibile. |
| requestedPlayback / effectivePlayback | enum playing/paused; enum running/suspended/static/error. Derived dal riduttore, senza bool indipendenti in conflitto. |
| suspendReasons | array di enum, unici, max 16: hidden, preparing, overlay, urgent, theme, assets, display, user, reduced, off. |
| environmentId / seed | id catalogo valido / int 0…2147483647; seed per visita, override soltanto del harness di test. |
| species | array AquariumSpecies max 8, id unici; catalogId, assetId, referenceSize, motionPreset. Per il prodotto iniziale 2. |
| instances | array AquariumInstance max 16; id, speciesId esistente, depth 0/1/2, phase [0,1), startX/startY normalizzati [0,1]. Per il nominale 6. |
| obstacles | array di Rect statici max 16, coordinate locali canvas; shell/avvisi restano app-owned e separati. |

I limiti di cardinalità servono alla validazione del primo contratto, non sono un budget RAM arbitrario. Nessun float NaN/Inf, enum sconosciuto, id duplicato o riferimento a specie assente. I path reali non transitano come comandi; gli assetId sono risolti dal pacchetto/tema registrato. Cataloghi non fidati non possono scegliere URL remoti o uscire dal root con `..`/symlink. Gli asset condivisi possono restare immutabili nel renderer; cambiarli richiede una nuova revision/epoch.

**Azioni di superficie:** `aquarium.pause` e `aquarium.resume`, senza target né argomenti, idempotenti. Allowlist con navigazione esistente; nessuna configurazione via mappa libera. `resume` con motion Off/Reduced non modifica preferenze globali e restituisce indisponibilità coerente. L'urgente precede qualsiasi azione. L'esito aggiorna subito lo snapshot del controller; Ready del renderer/primo frame restano esiti distinti. Prima della creazione risorse, un comando può cambiare intenzione ma non inventa “in riproduzione”.

**Trasporto:** getter restituisce snapshot posseduto per revisione, segnale solo per transizione/configurazione. Il renderer istanzia le liste a nuova session/revision, aggiorna numeri nei delegate per frame e non scrive indietro posizioni. Un cambio dell'orario HH:mm, di Sport o del badge non ricostruisce instances/species. La factory normalizza AquariumSnapshot dal payload dedicato; se i DTO ereditati lo permettono, nessun ulteriore bridge ad alta frequenza.

## 5. Composizione, shell e caricamento

1. Canvas `(0,0,960,640)`, z del contenuto sotto shell e notifiche. Per Base/Functional/Apple la header esistente da 56 px resta; gli altri bundle conservano la propria altezza dichiarata. Fallback senza shell esterna conserva headerClock di Main.
2. `safeArea` è il rettangolo sotto l'header effettivo, margine interno di piano 16 px sui lati/fondo; nuoto confinato al suo interno tenendo l'inviluppo del pesce. Decorazioni/fondo possono estendersi dietro il chrome. Overlay hanno la geometria già qualificata, senza una seconda barra duplicata.
3. `dimmingLayer z=30` resta l'unico oscuramento. Nessun sottofondo che scavalca badge/banner/urgente/recovery o loader/cambio tema. Non abbassare il contrasto degli avvisi per rendere più visibili i pesci.
4. Preparazione lazy: mostrare feedback app-owned e mantenere la destinazione precedente finché ViewHost non committa quella nuova. Loader asincrono, poi controllo di tutte le immagini essenziali; niente forzatura sincrona del Loader in corso.
5. Ready QML dipende da geometria e risorse essenziali pronte; primo frame coerente ha ticket/epoch proprio. Evitare un ciclo `ready → active → ready`: le immagini devono poter essere preparate con animazione spenta. Preview/candidate hanno immagine statica.
6. Suspend SceneHost quando la destinazione acquisita è Acquario, mantenendone distinta la configurazione. Adeguare la condizione di mandatory/coerenza, preservando controlli globali per le altre famiglie. Uscita riconsegna l'ambientale soltanto dopo commit della destinazione.

**Ispirazione operativa:** composizione concava o triangolare ADA (S20), con masse laterali e centro libero; traduzione in illustrazione Calm, senza simulazione dell'ecosistema. Master piccoli 70–100 px, medi 120–160 px; il concept finale può correggerli prima di congelare il profilo prestazionale.

## 6. Lifecycle: una sola macchina a stati

Priorità: error/assets/preparing → policy off/reduced → hidden/theme/overlay/display/urgent → user pause → running. Tutti i motivi restano nel set anche quando uno domina la visualizzazione; rimuovere un motivo non cancella gli altri. `requestedPlayback` esprime intenzione utente; `effectivePlayback` è derivato. Urgente imposta anche requested=paused, così la chiusura non fa ripartire il nuoto.

| Transizione | Effetto richiesto | Prova minima |
| --- | --- | --- |
| Nuova visita | requested=playing, frame iniziale valido; avvio solo a commit+Ready+normal. | Apri mentre carica e cambia subito argomento. Nessun clock orfano. |
| Pausa/Resume | Comando esplicito idempotente, repeat tasto 5 ignorato. | Pausa→Menu→chiudi resta paused. Resume doppio non duplica clock. |
| Menu/Inbox | Aggiunge motivo; congela fasi, sprite e particelle. | Chiudi dopo 10 s: posa identica, poi moto continuo se prima playing. |
| Urgente | Congela e requested=paused, input al router urgente. | Durante virata/caricamento/cambio tema; nessuna attesa del pesce. |
| Reduced/Off | Statico, niente clock; resume non scavalca Aspetto. | Varia policy mentre sospeso, ripassa a normal senza catch-up. |
| Notte/Quiete | Palette/fonte Avvisi separate dal playback. | Night non equivale a hidden; quiet non spegne il nuoto. |
| Uscita / nascondi modulo | Ferma e rilascia risorse secondo host; nessuna scrittura periodica. | Venti rientri, numero di clock attivi 0/1, conteggio delegate stabile. |
| Cambio tema/candidate | Sospensione e nuova epoch; candidate statico. | Callback vecchie ignorate; avvisi e clock HH:mm funzionanti. |
| Errore/unload | Fallback statico+messaggio; uscite attive, controller non dichiara running. | Specie essenziale mancante contro decorazione opzionale mancante. |
| Reboot | Solo visibilità/configurazione persistite, navigazione di avvio corrente. | Nessun autoswitch ad Acquario né progresso durante assenza. |

**Persistenza iniziale:** soltanto visibilità modulo nel percorso QSettings già usato. Pausa utente vale nella visita, non riapre al reboot un'animazione nascosta. Ambiente e nominale sono preset versionati, non impostazioni modificabili nel Menu. Il costruttore del servizio non legge tutti i PNG, non scrive DB e non avvia timer. Un loader/cache impiega worker solo per I/O realmente bloccante, consegnando esiti per epoch al thread GUI.

## 7. Matematica del movimento e comportamento visivo

**Percorso selezionato per il primo codice:** Bézier cubiche locali, generatori con seed esplicito e tabella di lunghezza campionata al cambio segmento. B(t) usa quattro controlli; posizione, tangente e angolo derivano dalla stessa curva. Proseguire con tangente concorde e velocità raccordata; non estrarre ogni frame una destinazione casuale. Campionare lunghezza con 32 intervalli iniziali, confronto 64 se l'errore è visibile; mantenere la tabella fuori dal lavoro per frame.

A ogni frame si avanza una distanza `speedPxPerSecond × dt` e si converte distanza→parametro con la tabella; la qualità del passo si verifica su curve dritte/strette e bordi. Niente uso del parametro t come se fosse lunghezza. Non serve Catmull–Rom per MVP; se introdotta, centripeta (S21) evita alcune cuspidi locali, ma non risolve da sola bordi, velocità o intersezioni globali.

**Contenimento:** controlli nella regione erosa dall'inviluppo della specie; dove la regione è rettangolare/convessa il hull dei controlli aiuta il contenimento del centro. Verificare anche pinne/rotazione, aree opache e curva completa: il centro dentro non basta. Generazione con massimo 8 tentativi e percorso valido di fallback; nessun while illimitato nella GUI. Precalcolare il segmento successivo prima del termine senza far partire una cascata di ricalcoli ogni frame.

**Clock:** unico FrameAnimation della scena, pausa esplicita e fase attiva posseduta da AquariumVisual. All'inizio/rientro si scarta il primo delta di collegamento; la fase non viene impostata al wall clock. Per `dt > 0,100 s`, mantenere posa e registrare una discontinuità, poi continuare senza recupero del tempo perduto. È un degrado dichiarato del tempo visuale, non una prova di frame regolari. Non usare smoothFrameTime per pilotare la velocità o mascherare stalli; serve alla sola diagnostica.

**Nuoto:** coda oscillante con fase individuale, pinna con fase differente, ampiezza/ritmo moderatamente legati alla velocità. Corpo/occhio restano stabili, nessun effetto gelatina. Piccoli 20–45 px/s, medi 15–30 px/s, virata 1–2,5 s sono candidati di taratura artistica. Raccordo dell'angolo sul percorso breve. Sprite di virata se un rig laterale produce un'inversione piatta: non trasformare una scala X negativa istantanea in una “virata naturale” dichiarata.

Un piccolo banco o avoidance reattivo sono estensioni dopo la scena nominale. La naturalezza studiata da Tu/Terzopoulos (S19) ispira il coordinamento corpo/pinne, non richiede idrodinamica o neurali. Il test riproducibile imposta seed e tempi; determinismo della traiettoria non significa medesimi pixel fra backend o diversi frame rate.

## 8. Asset e ottimizzazioni nell'ordine giusto

**Pacchetto:** catalog.json schemaVersion 1; id/assetVersion; due specie con canvas, parts e pivot in pixel, bounding envelope, motionPreset e clip opzionali. Ogni parte ha id/path relativo/hash/dimensioni/ordine. Le clip dichiarano frame count, frame size, layout e fps; rifiutare frame fuori sheet. Ambiente day/night separato, file essenziali e opzionali distinti. Manifest non contiene QML/codice generato né URL arbitrari.

**Flusso di produzione da eseguire dopo autorizzazione:** concept 960×640 → un master laterale → parti complete nelle giunzioni → rig nuoto/quiete/virata → sheet equivalente per confronto → seconda specie. Controlli su alpha reale, seam sul massimo gesto, silhouette a taglia finale, identità fra pose, pivot stabili e chiusura del loop anche in velocità. Scheda 0–2 per identità/alpha/naturalità/loop/leggibilità, candidato 8/10 senza zero; registrare tentativi e correzioni. Le immagini AI sono materiale da lavorare, non automaticamente modelli animati pronti.

| Ordine | Ottimizzazione da applicare/provare | Quando fermarsi |
| --- | --- | --- |
| O1 | Payload piccolo, revisioni stabili, delegate persistenti, unico clock e stop completo fuori vista. | Deve essere già corretto nel verticale; non richiede una riscrittura generale. |
| O2 | Fondo opaco, parti ritagliate, source identiche condivise, sourceSize fisso, caricamento lazy/asincrono. | Verificare costo di apertura, texture e memoria effettiva. |
| O3 | A/B rig/sprite stessa silhouette/taglia/ritmo; sprite interpolate on/off; smooth alla qualità necessaria. | Scegliere qualità+frame pacing, non solo numero di Item. |
| O4 | Batching/atlante/overdraw con diagnostica breve; niente layer/clip per pesce. | Gli strumenti cambiano il carico: accettazione con diagnostica spenta. |
| O5 | Eventuale shader locale `.qsb`, supporto atlante/subrect e alpha premoltiplicato; no luce fullscreen iniziale. | Solo se corregge un difetto o riduce costo con qualità equivalente. |
| O6 | Eventuale elemento QSG nativo isolato dopo profilo CPU/JS. | Richiede build ARM, gestione thread/lifetime e parità; non è prerequisito della v0.10. |

`retainWhileLoading` può evitare un vuoto nel cambio risorse ma aumenta memoria transitoria e non sostituisce lo staging; usarlo solo se il percorso effettivo ne beneficia. Il preload non deve duplicare caricamento già gestito dal ViewHost. Non assumere che sheet grande sia nell'atlante Qt o che uno shader non ne provochi una copia: S24/S25 e ShaderEffect documentano i confini. Nessuna modifica globale degli atlas env, governor o driver nell'esperimento nominale.

## 9. Scomposizione esecutiva P0–P7

| Lotto | Dipendenza | Consegna e uscita |
| --- | --- | --- |
| **P0 · Contratto e fixtures** | Piano / preflight locale | DTO/superficie/azioni, snapshot sintetico e fixture; generator/check/runtime API passano, bundle precedenti hanno fallback. Nessuna installazione. |
| **P1 · Lifecycle/controller** | P0 | Service/riduttore, visibilità/default, pause/epoch/close. Test automatici di §6 senza provider o archivio reale. |
| **P2 · Verticale shell** | P0–P1 | Routing/slot9/PageHost/payload dedicato/safeArea; headerClock+dimming e notifiche nei tre temi, placeholder statico dichiarato. Coerenza tema senza deadlock. |
| **P3 · Un pesce e motion** | P2 | Rig/curve/clock/asset catalog, nuoto/virata/quiete; QML smoke PC e A1 nativo privato quando autorizzato. Sprites A/B, scelta renderer. |
| **P4 · Scena finale** | P3 / master validato | Seconda specie, 6 istanze, day/night/static off/reduced, decorazioni statiche. Asset AI valutati e versionati. |
| **P5 · Capacità e ottimizzazione** | P4 | A2 scala1/4/8/16, A3 refresh/avvisi, 3 repliche e confronto diagnostico O1–O6 necessario. Profilo nominale fissato prima delle misure finali. |
| **P6 · Qualifica e packaging** | P5 | Soak30min, cicli rientro, input/pannello dove disponibile, kit/manifest/backup/rollback ed esiti distinti. |
| **P7 · Installazione e report** | P6 / autorizzazione consegna | Preflight live, distribuzione/ricevuta, preferenze/archivi conservati, servizio/GUI e reboot attribuibile se eseguito. MasterPlan aggiorna soltanto evidenze effettive. |

Il primo codice utile è P0–P2: non attende una generazione perfetta degli asset e non finge di aver già provato il carico finale. P3 decide rig/sprite prima della moltiplicazione delle specie. Nessun lotto riapre i P0–P9 scientifici del Gioco messi in manutenzione. Non creare branch o candidati installati per il solo completamento di questo piano.

## 10. Verifiche da scrivere e comandi

| ID | Prova | Esito necessario |
| --- | --- | --- |
| T1 | Validazione catalogo/snapshot: duplicati, NaN/Inf, cardinalità, path e sheet incoerente. | Rifiuto specifico senza caricare/avviare contenuti parziali. |
| T2 | Riduttore: pausa→overlay→off→rientro→normal, urgente durante loading, doppio Resume/close. | requested ed effective coerenti; nessun callback tardivo o secondo clock. |
| T3 | Matematica su orari sintetici e frame diversi: retta, curva stretta, dt lungo, pause10s, seed ripetuto. | Inviluppo contenuto, velocità/raccordo regolari entro tolleranza dichiarata, nessun catch-up. |
| T4 | Main reale tre temi e scale1/1,1: entry/exit, 5repeat, 7, Home/Menu/Avvisi e broker. | Clock HH:mm visibile, header non sovrapposto al nuoto, z/dimming e input corretti. |
| T5 | Contract/staging: bundle vecchio, candidate, renderer errato, asset essenziale/opzionale assente. | Fallback/Ready distinti, preview statica, nessun deadlock della coerenza. |
| T6 | Revisioni: 300 frame con 6 pesci, cambio minuto, refresh Sport e banner. | Nessuna ripubblicazione per-frame di snapshot/instances o lettura del modello Sport dalla superficie Acquario. |
| T7 | Venti cicli mostra/nascondi, pause30s, cambio tema e errore asset. | Nessun tick visuale nascosto, conteggi stabili; memoria assestata distinta da crescita illimitata. |
| T8 | A0–A5 del piano e replay refresh/urgente poi fonti reali. | Report software/ottico separati e campione riproducibile. |

Nomi previsti: `check_aquarium.py` (T1/T2), `check_aquarium_motion.py` (T3), `check_aquarium_ui.py` (T4–T7). Verificare la matematica eseguendo la stessa implementazione JS del renderer con engine/harness Qt, non una copia Python che potrebbe divergere. Gli offscreen/software provano correttezza, non gli FPS PowerVR. Non eseguire ora comandi che rigenerano API o avviano test applicativi: sono la sequenza futura.

```sh
python3 scripts/generate-theme-api-contract.py
python3 scripts/generate-theme-api-contract.py --check
python3 dashboard/theme_api.py
python3 dashboard/check_theme_api_contract.py
python3 dashboard/check_theme_api_runtime.py
python3 dashboard/check_aquarium.py
python3 dashboard/check_aquarium_motion.py
python3 dashboard/check_aquarium_ui.py
```

Gli ultimi tre file saranno creati durante P0–P4; lo stesso vale per benchmark-aquarium.py. Usare l'interprete/runtime di progetto con PySide disponibile e isolare QSettings/cache/DB nei test. Lint PC con strumento reale; se qmllint manca su ARM annotare indisponibilità, non dichiararlo passato e non installarlo implicitamente.

## 11. Protocollo prestazionale fissato per il primo confronto

A0 ambiente → A1 un pesce → A2 scala → A3 integrazione → A4 durata → A5 fisico/consegna, come nello studio. Per A1/A2: 60s warm-up, 120s registrati, tre repliche, ordine A/B alternato; stesso seed/taglia/percorso/tema/build. Nominale 6 pesci, varianti di stress 1/4/8/16; nessun effetto dinamico nominale iniziale. Rig/sprite partono dallo stesso master: un renderer più brutto non vince per pochi ms.

**Soglie candidate congelate prima del test:** a refresh vicino a60Hz, callback medi ≥59/s, p95 intervalli ≤18,5ms, slot mancati stimati ≤1%, meno di2 stalli >50ms in ciascuna finestra120s; massimo/p99 e peggiori finestre1/10s pubblicati. La soglia rende esplicito il precedente “nessuno stallo ripetuto”: un singolo stallo rimane nel report. Nessun cambio di soglia dopo aver visto i dati per far passare il risultato. Cambi tema/loading/urgente hanno finestre separate ma non vengono eliminati dal report dell'esperienza.

Percentili nearest-rank sui raw, durata monotona completa e contatori totali; non mediare p95 per nascondere una replica fallita. Questa è qualifica **vicina a60 software**, non 60 costanti. Per “60 costanti nel perimetro” occorrono anche assenza di frame mancati nel campione e riscontro fisico di fotogrammi nuovi; il loop della coda a12–24 pose/s si distingue dalla traslazione/orientamento continui a60.

Registrare baseline/candidate commit o hash dei sorgenti, manifest asset, Qt/PySide/driver/backend/render loop, refresh effettivo, governor per cluster, nice/affinity, temperatura iniziale/finale, seed/population/renderer, callback/pose, CPU thread/RSS/PSS, finestre peggiori e strumenti disponibili. GPU busy non attendibile resta “non disponibile”. Nessun nuovo limite RAM e nessuna alterazione del driver per ottenere il target.

Profilazione QSG_INFO/logging e QSG_VISUALIZE in esecuzioni diagnostiche brevi **dopo averne verificato il supporto**, separata dalle finestre di accettazione; niente `grabWindow` ricorrente durante il benchmark. Ticket primitivi nel render thread e flush fuori dalla finestra; usare la tecnica di misurazione già qualificata nella v0.9.3 evitando nuove callback Python pesanti a ogni frame. Registrare overhead con strumenti on/off.

La prova30min deve includere minuto/refresh/banner, rientri e temperatura stabilizzata; se la strumentazione ottica non è disponibile, il relativo gate resta aperto e il report non dichiara 60fisici. Un degrado a30fps è una variante distinta, mai raggiungimento dei60. Se nominale fallisce: isolare costo, correggere, ripetere confronto pertinente; non togliere provider/avvisi per migliorare artificialmente il numero.

## 12. Prontezza, limiti e chiusura futura

**Pronto per iniziare a scrivere, quando richiesto:** perimetro, file, contratto, stato, routing, orario, clock, motion, algoritmi, test e successione P0–P7 hanno default concreti. **Da produrre durante l'implementazione:** concept/master, asset finali, scelta rig/sprite sulle misure e taratura artistica. **Da dimostrare prima della release:** qualità AI, prestazioni native/sostenute, input e pannello, installazione/rollback. Le ultime due categorie sono gate di esecuzione, non analisi lasciata indefinita.

Non servono ora un nuovo studio generale di hardware, un motore esterno, un cambio linguaggio, cloud o inferenza NPU. Rimangono rami condizionali solo se una prova specifica li giustifica. Il rapporto finale dovrà dichiarare separatamente: pianificato / implementato / verificato PC / verificato EGLFS / installato / qualificato fisicamente, con residui e versione per ogni evidenza.
