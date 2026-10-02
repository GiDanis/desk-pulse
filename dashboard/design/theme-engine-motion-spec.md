# v0.6.6 — Motion Engine: animazioni e transizioni

**Aggiornamento attuazione v0.6.6:** il piano è implementato nei sorgenti. Contratti effettivi, uso e limiti sono nella [guida del motore](theme-engine-implementation-guide.md); stato dei gate e prove sulla scheda nel [resoconto di migrazione](v066-migration-report.md). Gli snippet di analisi illustrano alternative; per il formato eseguibile usare schema, registry ed esempi distribuiti.
**Revisione 1.0 · 2 ottobre 2026 · proposta funzionale e tecnica.**

Parte integrante del [Theme Engine](theme-engine-construction-spec.md), con [presentazioni/scene](theme-engine-presentation-spec.md) e [migrazione](ux-theme-adaptation-plan.md). Un tema comprende anche il proprio linguaggio di movimento: tipi di transizione, curve, tempi, ampiezze e feedback. Il motore deve permettere nuove animazioni, non soltanto cambiare una durata globale.

## 1. Situazione corrente e responsabilità

`Main.qml.animateMove()` ferma il precedente NumberAnimation, porta il contenuto a ±20 px e lo anima a 0 per 160 ms con OutCubic. Lo stesso movimento viene usato per cambio famiglia e vista. La maschera di luminosità ha un Behavior di 180 ms, non collegato al booleano delle animazioni.

Banner e urgenti appaiono tramite `visible`; il focus è un cambiamento di colore/bordo; il timer Sport cambia gruppo ogni otto secondi. Quest'ultimo è un comportamento di contenuto e non diventa un timer del tema.

**Python decide eventi e policy; QML esegue il movimento.** Non inviare coordinate o segnali Python a 60 Hz. Le animazioni Qt Quick usano tipi dedicati, Behavior, States/Transitions e gruppi paralleli/sequenziali. [Qt animations 6.8](https://doc.qt.io/qt-6.8/qtquick-statesanimations-animations.html).

Non tutte le animazioni QML girano indipendentemente sul render thread. Gli Animator operano sul scene graph e non aggiornano continuamente il valore QML della proprietà; possono essere adatti a decorazioni, ma richiedono attenzione a letture dello stato e finalizzazione. NumberAnimation rimane il primo candidato per elementi con geometria osservata da controller/test. [Animator Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-animator.html).

## 2. Quattro livelli di movimento

| Livello | Scopo | Autorità |
| --- | --- | --- |
| Interazione | Focus, pressione, cambio tab e pagina | UI/controller; risposta immediata |
| Transizione di presentazione | Entrata/uscita pannello, cambio composizione o tema | ViewHost e MotionController |
| Informazione | Aggiornamento di un valore o comparsa di un avviso | Dato/evento reale; la ricetta non inventa lo stato |
| Ambientale/scena | Decorazioni, compagno, passaggi fra viste | SceneHost; preferenze e priorità di prodotto |

Durata di un banner, scadenza evento, intervallo polling e timeout non sono motion tokens. Il colore di un avviso non cambia la sua priorità. Una breve animazione non prova che un comando sia stato eseguito.

## 3. Eventi semantici da supportare

| Evento | Ricette iniziali candidate | Invariante |
| --- | --- | --- |
| `navigate.family` | slide orizzontale, dissolve, cut | Destinazione unica; input successivo operativo |
| `navigate.view` | slide verticale, dissolve, cut | Asse coerente con 2/8; nessuna nuova pagina |
| `focus.change` | bordo/riempimento, breve halo locale | Focus identificabile dal primo frame |
| `control.activate` | press, tint, cut | Azione inviata una sola volta |
| `panel.enter/exit` | fade, breve slide, cut | Stack e ritorno non dipendono dall'animazione |
| `tab.change` | underline, tint, cut | Tab e contenuto aggiornati insieme |
| `data.update` | breve highlight facoltativo | Testo/valore reale pubblicato subito; niente conteggi fittizi |
| `banner.enter/exit` | slide/fade locale, cut | Evento corrente e scadenza governati dall'EventService |
| `urgent.present` | cut obbligatorio del contenuto, enfasi locale facoltativa | Nessuna attesa per leggere l'urgente |
| `theme.commit` | cut, conferma nell'editor | Niente oscuramento integrale obbligatorio |
| `layout.swap` | cut o dissolve del solo visuale | Controller e selected ID persistono |
| `brightness.change` | interpolazione breve o cut | Limite di luminosità invariato |
| `scene.action` | clip/path/renderer extension | Scena non intercetta input o avvisi |

Il registry permette altre ricette e combinazioni. Non limitare il futuro a slide/fade: primitive di percorso, sequenze, rig, sprite e renderer specializzati possono essere registrati tramite estensioni. La compatibilità e il costo vengono dichiarati per ricetta.

Per `data.update`, un eventuale tween del grafico separa valore corrente e rappresentazione interpolata; l'etichetta mostra il valore reale. Punteggi, allerta e percentuali non contano lentamente verso il nuovo numero.

## 4. Ricette: parametri e contratto estensibile

Ogni ricetta ha:

- ID/versione e tipo di evento compatibile;
- parametri tipizzati, default, intervalli e unità;
- esecutore QML o adapter registrato;
- stato iniziale/finale, comportamento in interruzione;
- fallback Reduced e Off;
- capabilities e risorse richieste;
- costo osservato sui carichi verificati.

Parametri base: `durationMs`, `delayMs`, `easing`, `distancePx`, `scaleFrom`, `opacityFrom`; parametri ulteriori appartengono allo schema della specifica ricetta. Non un oggetto JSON libero con un arbitrary target/property.

Curve iniziali: linear, outCubic, inOutCubic; elastic/back/spring restano disponibili attraverso ricette qualificate, senza imporle al testo funzionale. Mapping dei nomi a enum Qt nel renderer, non stringhe eseguite con eval.

Esempio parziale del motion di un profilo:

```json
{
  "navigate.family": {
    "recipe": "builtin.slide",
    "durationMs": 160,
    "distancePx": 20,
    "axis": "horizontal",
    "easing": "outCubic"
  },
  "navigate.view": {
    "recipe": "builtin.slide",
    "durationMs": 160,
    "distancePx": 16,
    "axis": "vertical",
    "easing": "outCubic"
  },
  "focus.change": {
    "recipe": "builtin.focusTint",
    "durationMs": 90
  },
  "banner.enter": {
    "recipe": "builtin.bannerSlide",
    "durationMs": 160,
    "distancePx": 12
  },
  "urgent.present": {"recipe": "builtin.cut"}
}
```

ID illustrativi, da implementare. Le chiavi `navigate.family/view` sono canoniche; non duplicare la stessa ricetta con nomi diversi negli esempi e nel resolver.

Parametri candidati per UI funzionale: durata 0–300 ms, ritardo 0 ms sul primo feedback, spostamento 0–32 px, scala 0,98–1,02; non sono limiti universali alle scene. Una nuova ricetta può definire parametri e spazi diversi; mantiene recovery e fallback.

## 5. Policy del movimento

Evolvere il booleano in **`motionMode: normal | reduced | off`**. La policy utente prevale sulle preferenze del tema.

| Modalità | Interazione/transizioni | Informazione | Compagno/ambiente |
| --- | --- | --- | --- |
| Normal | Ricette del tema | Highlight locale, dove utile | Secondo preferenze/capacità |
| Reduced | Nessun ampio spostamento, zoom o bounce; feedback statico o fade breve | Dato aggiornato direttamente | Posa/clip calma, niente attraversamenti ampi |
| Off | Stato finale immediato | Dato e feedback testuale immediati | Posa statica |

Reduced non è “stessa animazione più lenta”. Ogni ricetta deve fornire un'alternativa; se non la fornisce si risolve a cut. Off non cancella azioni, stati o notifiche.

Preferenze indipendenti: `ambientMotionEnabled`, eventuale intensità e velocità utente. Range guidato candidato 0,75–1,25 della durata per la UI; per scene parametri separati. Il resolver evita che il moltiplicatore superi il limite funzionale della ricetta.

Migrazione in DashboardState:

- Se `motionMode` manca: `animationsEnabled=false` → Off; true → Normal.
- Getter legacy `animationsEnabled` rimane derivato per componenti/harness non ancora migrati.
- Scrivere il nuovo modo su scelta esplicita, conservando la chiave legacy coerente per rollback.
- Palette notte, luminosità e fascia silenzio rimangono indipendenti.
- Spegnere movimento durante una transizione finalizza immediatamente l'elemento; non basta cambiare la durata della prossima animazione.

`quietActive` esiste oggi come derivazione nel SettingsPanel e come policy nel motore eventi; il futuro controller del cane deve ricevere un valore comune, evitando un terzo calcolo. Consolidamento da includere quando si integra il compagno, senza duplicare ora scheduler e timer.

## 6. Lifecycle e gestione degli input rapidi

Stati dell'esecutore: **idle → preparing → running → settling → idle**, oppure **suspended/error** per renderer di scena.

Il controller applicativo cambia lo stato semantico subito. Il motion esegue solo il transitorio visuale. Le azioni non aspettano il segnale “animation finished” per esistere.

Una ricetta cattura parametri e revisione all'avvio: un nuovo tema non altera la durata o la curva a metà della stessa esecuzione.

Politiche:

| Caso | Gestione |
| --- | --- |
| Nuovo cambio famiglia/vista | Finalizza la transizione precedente al suo stato logico, mostra ultima destinazione, avvia un nuovo transitorio; niente coda di pagine |
| Cambio selezione veloce | Focus logico immediato; retarget/finalizza feedback precedente |
| OK durante navigazione | Agisce sulla destinazione logica corrente, con guida coerente |
| Back/Home | Prima aggiorna stato/stack; ferma transitori incompatibili e ripristina valori finali |
| Cambio tema/layout | Finalizza motion locale, commuta snapshot/visuale; scena globale conserva stato semantico |
| Urgente durante transizione | Stop dei transitori che possono oscurarlo; urgente immediato, input secondo contract urgente |
| Nuovo dato durante highlight | Latest value wins; highlight retarget, nessun replay |
| Chiusura vista | Stop/pause del visuale; nessun timer/animazione ambientale inutile |
| Asset/renderer in errore | Fallback statico, errore osservabile, input e dati disponibili |

Non mettere debounce temporali sul tastierino per mascherare un controller instabile. Il decoder già filtra release/auto-repeat; una pressione valida deve ricevere esito coerente.

Per `x/y/opacity/scale/rotation`, ogni ricetta possiede un wrapper dedicato. Non animare una proprietà contemporaneamente posseduta da anchors o da un'altra ricetta. Meglio transform del contenuto che spostamento del contenitore con geometria di layout.

## 7. Visible, uscite e timer degli avvisi

La visibilità semantica e quella dell'esecutore non coincidono sempre: un'uscita animata ha bisogno di un oggetto visuale ancora presente.

Per i banner:

- Quando EventService espone un evento, copiare i soli dati visuali in un presenter; avviare enter.
- La durata di lettura attuale resta governata dal servizio. Non estendere in modo implicito gli otto secondi perché il tema è più lento.
- Quando il servizio termina il banner, l'exit può mostrare un residuo visuale breve non interattivo; evento scaduto/annullato o urgente lo rimuove immediatamente.
- Un nuovo evento sostituisce il residuo senza duplicare inbox/mark-read/dismiss.
- Entrata/uscita non richiama setBannerAvailable o ingest. L'origine applicativa resta il controller.

Per gli urgenti, il contenuto compare subito; nessun fade da opacity 0 per tutto il pannello. Una enfasi sulla linea/bordo è facoltativa e senza lampeggio ripetuto. Il timer del tema non autochiude un urgente.

Per pannelli/settings/Info, “chiuso” diventa vero nel router subito; un eventuale visuale di uscita non intercetta input. Il nuovo contesto è la sola autorità di azione.

## 8. Animazioni profondamente diverse per profilo

| Profilo | Linguaggio da prototipare | Esempi |
| --- | --- | --- |
| Base | Morbido e discreto | Slide corto, focus locale, piccoli fade |
| Functional | Netto e preciso | Cut o transizione più breve, underline, risposta secca |
| Hardware | Meccanico | Indicatori segmentati e press controllato |
| Cyberdeck | Strumentale | Reveal per gruppi e linee; testo essenziale subito, niente finto typing di dati |
| Cozy | Organico | Percorsi/clip morbidi, compagno e ambiente; dati stabili |

Gli ultimi tre profili non sono ancora rilasciati. Per Base/Functional la prima release deve dimostrare **almeno due ricette distinguibili**, con preset Normal/Reduced/Off, anziché due colori e la stessa unica animazione.

L'utente può combinare palette e motion diversi. Le nuove ricette si sviluppano nel registry delle estensioni; la facade non deve crescere di switch per il nome del tema.

## 9. Compagno e scene

Il dettaglio del SceneHost è nella [specifica presentation](theme-engine-presentation-spec.md). In questa fase fissare:

- Un attore persistente può spostarsi fra ancoraggi di viste diverse.
- Stato comportamentale/azioni non dipendono dai frame dello sprite.
- Preemption, sospensione e cambio skin/renderer usano checkpoint semantici.
- La scena espone readiness e fallback statico.
- Attori nascosti non continuano ad animare senza una necessità del controller.
- Le zone occupate da dati, focus e avvisi hanno precedenza.
- Nessun Python per frame; percorsi e clip vengono eseguiti dal renderer.

Non imporre al compagno un limite di 300 ms o un massimo di 32 px: sono parametri delle transizioni funzionali. Scene, clip e percorsi hanno contratti e budget propri. La futura AI può chiedere azioni già registrate; non scrive QML o shader da eseguire.

## 10. Prestazioni: misurare il percorso corretto

Prima renderer di base: NumberAnimation/ColorAnimation/Transforms e primitive standard; nessuna necessità di C++ per il tween. Evitare animare font size, larghezze e anchors di tutte le righe come transizione ordinaria: producono lavoro di layout da misurare.

Animator da considerare per decorazioni senza bisogno di leggere coordinate intermedie, dopo una prova di stop e stato finale. C++/QSG per una primitiva costosa dimostrata. Shader per un effetto specifico con fallback.

Qt ShaderEffect usa shader preparati nel formato supportato dal toolkit; un frammento GLSL incollato da un tema non costituisce automaticamente un asset pronto. [ShaderEffect Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-shadereffect.html).

Budget separati per: UI, companion foreground, ambiente. Niente fullscreen blur o layer per default. Stima una texture RGBA 960×640: circa 2,34 MiB prima di copie, buffering e altri overhead. Due visuali in staging e uno sprite atlas hanno costi distinti.

La sospensione ambientale a vista nascosta/urgente è prevista. Un'eventuale riduzione automatica degli effetti sotto carico deve essere una policy dichiarata e osservabile, non una degradazione nascosta della funzione.

## 11. Protocollo di misura e limiti del benchmark attuale

`benchmark.py` oggi:

- Naviga fra quattro azioni nella modalità demo, senza tutte le viste Sport.
- Campiona solo vicino all'azione.
- Scarta gli intervalli ≥100 ms.

È utile per un confronto breve, ma **può nascondere un blocco lungo dentro un'animazione** e non copre cambio tema, focus, scene o interruzioni. Per T5 serve un harness motion dedicato; non bastano quei numeri.

Protocollo proposto:

1. Fissare build, Qt, percorso EGLFS/KMS/OpenGL, render loop, viewport, dati e font.
2. Warmup dichiarato: primo uso dei glyph/asset distinto dal cambio caldo.
3. Registrare trigger/input, stato dell'animazione e frameSwapped con clock monotono.
4. Escludere intervalli idle tramite lo stato del test, **non tramite la durata dell'intervallo**. Conservare i blocchi lunghi durante animazione e il ritardo trigger→primo frame.
5. Riportare conteggio frame, durata effettiva, p50/p95/p99/max, frame mancanti, intervalli oltre 16,67/33,34/50 ms.
6. Separare input→stato logico, input→primo feedback e latenza→frame coerente per tema/layout.
7. RSS/PSS/cgroup/CPU e log in campioni passivi; nessuna animazione diagnostica permanente.
8. Stesso carico prima/dopo: Home con/senza evento, focus list, pannello, banner, Sport e visual swap.
9. Offscreen/software solo per comportamento; la prova prestazionale è sulla board.
10. Ripetere cold/warm e burst; dichiarare numero di campioni e variabilità.

FrameSwapped è un segnale del percorso Qt, non una ripresa ottica del pannello o una misura diretta del tempo GPU. Input fisico comprende anche il tastierino; la latenza end-to-end può richiedere una prova visuale distinta. Un'animazione di 120 ms offre pochi frame: aggregare più esecuzioni per percentili significativi.

**Obiettivo:** animazioni a 60 fps, non 60 fps forzati in idle. Gate candidati dopo baseline: nessun blocco >50 ms attribuibile al motore nel percorso caldo; p95/p99 e frame mancanti non peggiorano oltre il budget fissato in T0/T1. Se la baseline non raggiunge l'obiettivo, dichiararlo e affrontare il limite prima di attestare i 60 fps.

## 12. Matrice di collaudo

| Prova | Evidenza necessaria |
| --- | --- |
| Famiglia/vista Base e Functional | Movimento distinto, asse corretto, stato finale esatto |
| 20 pressioni valide alternate | Destinazione corretta, nessuna coda o oggetto invisibile |
| Focus e OK durante transizione | Azione sull'ID corretto, un solo invio |
| Reduced/Off a metà animazione | Cut coerente, wrapper x/y=0, opacity/scale normali |
| Cambio palette/layout durante motion | Stato applicativo invariato e visuale assestato |
| Giorno→notte e luminosità | Lettura/focus conservati; nessun avvio decorativo di notte |
| Banner piccolo/grande, scadenza/sostituzione | Durata governata dal servizio, niente residui su urgente |
| Urgente in editor/pannello/scene | Testo e azioni disponibili immediatamente, ritorno corretto |
| Vista nascosta per 60 s | Motion ambientale sospeso, nessun loop inutile |
| Asset/ricetta incompatibile | Fallback dichiarato e comandi operativi |
| Attore fra Home e Meteo | Identità/azione persistenti e ancoraggi coerenti |
| 100 cicli tema/presentation | Rilascio visuali/transitori, memoria senza crescita persistente |

Catture statiche dimostrano la composizione, non la fluidità. Per motion servono tracce temporali e osservazione sul display; un eventuale video è supporto, non sostituisce gli intervalli.

## 13. Criterio di completezza

Il Motion Engine è completo per v0.6.6 quando:

- I profili possono scegliere ricette e parametri per evento.
- L'utente dispone di Normal/Reduced/Off e personalizzazione guidata.
- Il comportamento rimane deterministico sotto input rapido e urgenze.
- Nuove ricette possono registrarsi senza cambiare il resolver o la navigazione.
- Le scene future hanno lifecycle e policy già compatibili.
- L'intero insieme rilasciato è misurato sulla board, con residui espliciti.

Una sola `motionDuration` o un booleano che spegne soltanto lo slide non soddisfano questo contratto.
