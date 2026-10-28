# SmartPC v0.10 — Acquario · ricerca e ispirazioni

**Revisione 2 · 25 ottobre 2026 · Europe/Rome**

> Aggiornamento esecutivo, 26 ottobre: implementazione completata e rc.2/Apple1.6.5 installati. Questo documento conserva lo studio precedente; [chiusura, stato P0–P7 e limiti](v010-aquarium-completion-report.md).
**Stato dello studio alla redazione: ricerca documentale.** Supporta l'[analisi completa di integrazione](v010-aquarium-integration-study.md). Primo corpus consultato il 13 ottobre: **18 schede**, con documentazione ufficiale, pagine degli autori e prodotti dei rispettivi sviluppatori. Aggiornamento del 25 ottobre: **28 schede complessive**, con nuovi riferimenti e verifica dei sorgenti Qt al tag 6.8.2. Nessuna prova degli asset, del runtime Acquario o della board. Le proposte SmartPC sono nostre inferenze; non sono risultati delle fonti.

I riferimenti di prodotto servono a scegliere composizione/ritmo, quelli tecnici a motivare esperimenti. Non importiamo immagini/personaggi/codice dai prodotti. Le pagine Qt 6.8 possono descrivere 6.8.9: il prototipo dovrà verificare la disponibilità effettiva su Qt/PySide6 6.8.2. Nessuna fonte certifica 60 fps sulla nostra Orange Pi.

## Ispirazioni ed esperienza

### S1 · Marine Aquarium — SereneScreen

[Pagina del produttore](https://www.serenescreen.com/). Presenta acquario configurabile, specie diverse e una murena con animazione del respiro. **Ispirazione:** scena ambientale con movimento principale e microgesti che rendono vivi anche gli attori quasi fermi. **Applicazione:** pochi pesci con fase individuale, fondale riconoscibile e niente pannelli quotidiani di telemetria. **Limite:** prodotto e resa differiscono dal Calm 2D; catalogo ampio e supporto widescreen non misurano la nostra board.

### S2 · ABZÛ — Giant Squid

[Presentazione ufficiale](https://giantsquidstudios.com/ABZU), [Fluid Motion in ABZÛ, Max Kaufmann](https://giantsquidstudios.com/Fluid-Motion-in-ABZU). Il secondo testo descrive raccordi fra direzione/movimento e segnali anticipatori, con regole valutate tramite playtest. **Ispirazione:** traiettorie leggibili e continuità fra orientamento e nuoto. **Applicazione:** camera fissa, virata anticipata da corpo/coda, velocità e curvatura limitate. **Limite:** il testo tratta un personaggio controllato in 3D; non prova una simulazione di pesci 2D o prestazioni embedded. La camera mobile non è necessaria all'acquario.

### S3 · Endless Ocean Luminous — Nintendo

[Pagina ufficiale](https://www.nintendo.com/us/store/products/endless-ocean-luminous-switch/). Descrive osservazione/esplorazione marina e la possibilità di nuotare con calma oppure catalogare le specie. **Ispirazione:** osservazione come attività completa anche senza punteggio. **Applicazione:** nessun compito obbligatorio per godere dell'acquario. **Limite:** non introduciamo esplorazione, catalogo, multiplayer o progressione; il riferimento non definisce lo stile Calm.

### S4 · Steering — Craig Reynolds, 1999

[Pagina dell'autore e comportamenti](https://www.red3d.com/cwr/steer/). Separa obiettivi, steering e locomozione; include wander, containment e path following. **Applicazione:** scegliere una destinazione/curva lentamente, orientarsi lungo la tangente e animare la coda separatamente. **Limite:** comportamento credibile non implica correttezza biologica; coefficienti e frequenze vanno tarati per questa scena.

### S5 · Boids — Craig Reynolds

[Pagina dell'autore](https://www.red3d.com/cwr/boids/). Separazione, allineamento e coesione generano moto di gruppo; il confronto diretto fra tutte le coppie ha costo quadratico. **Applicazione:** eventuale piccolo banco dopo il nuoto individuale, vicinato limitato e seed riproducibile. **Limite:** 4–6 pesci non richiedono subito un sistema di flocking; il movimento autonomo può essere più semplice. Non giustifica calcolo NPU o migliaia di agenti.

## Asset, rig e generazione

### S6 · Rig a mesh — Spine

[Guida ufficiale mesh](https://us.esotericsoftware.com/spine-meshes), [guida pesi](https://us.esotericsoftware.com/spine-weights). Le mesh e i pesi permettono deformazioni articolate delle immagini; la guida distingue funzionalità dell'editor. **Applicazione:** principi di perni, sovrapposizione e deformazione controllata, iniziando con un rig semplice senza dipendenza Spine. **Limite:** Qt Quick non diventa un runtime Spine leggendo la guida; integrazione, strumenti e licenze andrebbero studiati separatamente se scelti.

### S7 · Generazione immagini — OpenAI Docs

[Guida ufficiale](https://developers.openai.com/api/docs/guides/image-generation). Documenta generazione/editing e output trasparenti nei formati compatibili, ma segnala limiti di continuità del personaggio e precisione della composizione. **Applicazione:** master unico, modifiche con riferimento, verifica alpha e corrispondenza fra parti/pose. **Limite:** documentazione API, non garanzia delle opzioni dell'account/tool in chat, né esportazione di un rig o loop animato pronto. Nessuna chiamata API o scelta di modello/billing in questo studio.

### S8 · ToonCrafter — Xing et al., SIGGRAPH Asia 2024

[Progetto degli autori](https://doubiiu.github.io/projects/ToonCrafter/). Ricerca sull'interpolazione generativa di cartoni; mostra anche fallimenti nella semantica del movimento e nell'apparizione/scomparsa degli oggetti. **Applicazione:** possibile esperimento offline su una virata difficile, dopo il rig/sprite deterministico. **Limite:** non dimostra alpha pulito, loop chiuso, identità stabile o esecuzione sulla board. Non è una funzione di ChatGPT e non è una dipendenza proposta della v0.10.

## Qt Quick e misura

### S9 · Prestazioni QML — Qt

[Guida Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-performance.html). Raccomanda profilazione e poco lavoro bloccante; discute binding, invisibili, trasparenze e shader. **Applicazione:** background statico, pochi aggiornamenti e benchmark di effetti separati. **Limite:** guida generale, senza numeri per A733/PowerVR; una texture “piccola” o un rig “leggero” non è già un benchmark.

### S10 · FrameAnimation — Qt

[Tipo QML](https://doc.qt.io/qt-6.8/qml-qtquick-frameanimation.html). Disponibile da Qt 6.4, segue gli aggiornamenti di animazione e fornisce tempi per movimento imperativo. **Applicazione:** candidato per un clock visivo condiviso, confronto con animazioni dichiarative. **Limite:** callback per frame non prova né fotogrammi distinti sul pannello né deadline rispettate; il suo handler può sovraccaricare la GUI.

### S11 · Animator — Qt

[Tipo QML](https://doc.qt.io/qt-6.8/qml-qtquick-animator.html). Agisce sul scene graph e può animare nel render thread; la proprietà QML corrispondente viene aggiornata alla fine. **Applicazione:** coda/pinna o trasformazioni decorative quando non servono letture intermedie. **Limite:** non leggere `x`/`rotation` come posizione corrente per steering/collisioni; confrontare pause/interruzioni. Non assumere che tutte le animazioni diventino automaticamente render-thread.

### S12 · AnimatedSprite — Qt

[Tipo QML](https://doc.qt.io/qt-6.8/qml-qtquick-animatedsprite.html). Riproduce frame da sheet, con interpolazione opzionale; `frameSync` segue i frame renderizzati. **Applicazione:** nuoto/virata in clip controllate, test blending acceso/spento. **Limite:** dissolvere due pose può creare contorni doppi, non nuovi fotogrammi anatomici; `frameSync` non misura i 60 fps.

### S13 · Scene graph e batching — Qt

[Scene graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html), [renderer predefinito](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph-renderer.html). Il renderer raggruppa primitive compatibili; blending e sovrapposizioni influiscono sulle possibilità di batching. **Applicazione:** asset condivisi, pochi livelli e niente layer offscreen per ogni pesce. **Limite:** il numero di Item non è il numero di draw call, e il batching resta da osservare.

### S14 · Caricamento immagini — Qt

[Image](https://doc.qt.io/qt-6.8/qml-qtquick-image.html). `sourceSize` dimensiona la risorsa caricata; cambiarlo dinamicamente può ricaricare l'immagine. **Applicazione:** taglie preparate, preload e stato Ready/Error, evitare ricaricamenti nel nuoto. **Limite:** cache e texture residenti si misurano; disco compresso e pixel decodificati sono quantità diverse.

### S15 · Canvas — Qt

[Canvas](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html). La guida avverte che aggiornamenti frequenti di grandi Canvas.Image causano upload della texture. **Applicazione:** evitare come primo renderer dell'intero acquario animato. **Limite:** non significa che ogni Canvas sia lento; un elemento statico o piccolo richiede una valutazione distinta.

### S16 · ShaderEffect — Qt

[ShaderEffect](https://doc.qt.io/qt-6.8/qml-qtquick-shadereffect.html). Qt 6 usa shader preparati in pacchetti `.qsb`; backend e compilazione offline sono parte del percorso. **Applicazione:** eventuale deformazione locale della coda, shader di luce solo dopo A/B. **Limite:** non incollare GLSL inline come in esempi Qt 5; verificare pacchetto GLES, toolchain e fallback reali.

### S17 · Fotogrammi e segnali — Qt

[QQuickWindow](https://doc.qt.io/qt-6.8/qquickwindow.html). `frameSwapped` segnala accodamento per presentazione ed è emesso dal render thread; `grabWindow` ha costo prestazionale. **Applicazione:** segnali raccolti con threading sicuro, acquisizioni fuori dalla finestra di misura. **Limite:** callback, tempo GPU, pannello e latenza USB restano prove diverse.

### S18 · Pausa del movimento — W3C

[WCAG 2.2, Understanding 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html). Discute disponibilità di pausa/stop per contenuti che si muovono automaticamente e condizioni di applicabilità. **Applicazione:** pausa raggiungibile e motionMode rispettato. **Limite:** usiamo il principio di controllo del movimento; non dichiariamo conformità WCAG del kiosk né applichiamo indistintamente il criterio web all'acquario.

## Sintesi delle scelte motivate

Rig a parti + percorsi continui è il candidato iniziale più utile per trasferire tecnica al compagno. Sprite resta il confronto per articolazioni/virate; shader una terza opzione se il rig perde qualità. AI genera materiale da qualificare, mentre movimento/lifecycle appartengono al runtime locale. Le ispirazioni non cambiano il perimetro: un acquario Calm semplice, un argomento, una vista, 60 fps da misurare.

## Approfondimento del 25 ottobre — sorgenti e decisioni operative

Le schede S1–S18 conservano la ricerca del 13 ottobre. Seguono **10 nuove schede S19–S28**; le pagine Qt su clock, immagini e renderer sono state ricontrollate il 25 ottobre. Sono **28 schede tematiche**, non 28 esperimenti o siti distinti. Per scelte, file e verifiche vale ora il [piano esecutivo](v010-aquarium-implementation-plan.md). I link code.qt.io al tag 6.8.2 non erano accessibili dal lettore web: il riscontro puntuale è stato fatto sul mirror ufficiale Qt GitHub allo stesso tag, senza presumere una prova del binario installato.

### S19 · Artificial Fishes — Tu e Terzopoulos, SIGGRAPH 1994

[Paper nel sito dell'autore](https://web.cs.ucla.edu/~dt/papers/siggraph94/siggraph94.pdf). Integra locomozione, percezione e comportamento in pesci autonomi fisici. **Spunto:** distinguere gesto, direzione e obiettivo anziché traslare una sagoma immobile. **Scelta SmartPC:** corpo stabile, onda della coda e virata coordinata; variabilità di ritmo per specie. **Limite:** non adottiamo muscoli, idrodinamica o predazione; complessità del paper non è necessaria alla scena Calm, né prova del suo costo su A733.

### S20 · Composizione Nature Aquarium — ADA

[Guida ufficiale, sezione Three Basic Compositions](https://www.adana.co.jp/en/contents/process/index.html/1000). Descrive composizioni triangolare, convessa e concava, con spazio centrale nella concava. **Spunto:** profondità attraverso disposizione e vuoti, prima degli effetti. **Scelta:** due masse laterali e corridoio centrale; primo concept con stessa scena in due densità decorative. **Limite:** riferimento compositivo da vasche piantumate, non prescrizione biologica per le nostre specie marine illustrate; nessuna gestione reale dell'acqua.

### S21 · Curve — Yuksel, Schaefer e Keyser, 2011

[Paper degli autori](https://www.cemyuksel.com/research/catmullrom_param/catmullrom_cad.pdf). Dimostra proprietà della parametrizzazione centripeta Catmull–Rom, incluso evitare cuspidi e auto-intersezioni all'interno del singolo segmento; non basta per una garanzia globale. **Scelta:** iniziare con Bézier cubiche controllate, contenute nella vasca e percorse per lunghezza approssimata. **Alternativa:** Catmull–Rom centripeta se la costruzione da waypoint aiuta, mantenendo verifiche di bordo/curvatura. Nessuna parametrizzazione garantisce da sola velocità costante.

### S22 · Tempo e recupero — Glenn Fiedler

[Testo originale Fix Your Timestep!](https://gafferongames.com/post/fix_your_timestep/). Spiega il rischio di accumulare lavoro per recuperare ritardi e l'importanza del margine di calcolo. **Scelta:** moto visuale con tempo attivo; nessuna coda di tick arretrati dopo pausa o hitch, contare ogni ritardo scartato. **Limite:** l'acquario non è una simulazione fisica da sincronizzare in rete; non copiamo un engine a passo fisso per semplici curve.

### S23 · Loader e readiness — Qt 6.8

[Loader](https://doc.qt.io/qt-6.8/qml-qtquick-loader.html). L'istanza asincrona distribuisce la creazione su più frame; forzare il completamento sincrono durante il caricamento può bloccare. **Scelta:** creare al primo accesso, tenere ultimo contenuto valido fino al commit, distinguere istanza, immagini pronte e primo frame. **Limite:** Loader.Ready non dimostra che ogni texture sia residente né che il primo frame sia visibile; niente doppio preload estraneo al ViewHost.

### S24 · Texture e atlante — Qt 6.8

[QSGTexture](https://doc.qt.io/qt-6.8/qsgtexture.html). Materiali compatibili su un atlante possono essere raggruppati; i riferimenti QSG hanno vincoli di thread. **Scelta:** parti piccole riusate, stessa identità della source, verificare batching con gli strumenti. **Limite:** non confondere la sprite sheet preparata dall'app con l'atlante interno Qt; immagini grandi possono restare fuori dall'atlante. Non modificare i parametri globali dell'atlante prima della misura.

### S25 · Layer e memoria — Qt 6.8

[Item, Memory and Performance](https://doc.qt.io/qt-6.8/qml-qtquick-item.html). Un layer richiede una texture aggiuntiva e può perdere opportunità di batching. **Scelta:** nessun layer per pesce, sfondo precalcolato e alpha limitato alla sagoma. **Limite:** una cache offscreen non è automaticamente più rapida; l'eventuale prova va confrontata a identico risultato visivo e risoluzione. Il filtro luminosità globale già consegnato resta una funzione di sistema.

### S26 · Geometria nativa condizionale — Qt

[Esempio ufficiale Custom Geometry](https://doc.qt.io/qt-6.8/qtquick-scenegraph-customgeometry-example.html). Mostra riuso di nodi e sincronizzazione tramite updatePaintNode. **Scelta:** se profilazione trova costo dominante nel rig/JS, confronto di un elemento nativo isolato. **Limite:** non è una scorciatoia gratuita; build ARM, thread, lifetime e parità visiva vanno provati. Nessun nuovo modulo C++ obbligatorio nel primo percorso.

### S27 · Diagnostica di rendering — Qt

[Renderer, profiling e visualizzazioni](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph-renderer.html), [logging del scene graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html). Espone strumenti per batch, overdraw, clipping, texture e fasi del rendering. **Scelta:** brevi acquisizioni diagnostiche separate dalle misure di accettazione, con controllo dell'overhead. **Limite:** colori/contatori Qt non sono percentuale GPU affidabile o FPS ottici. Non lasciare log per frame nel servizio normale.

### S28 · Capacità ancorate al tag Qt 6.8.2

[Sorgente FrameAnimation](https://github.com/qt/qtdeclarative/blob/v6.8.2/src/quick/util/qquickframeanimation.cpp), [sorgente Image](https://github.com/qt/qtdeclarative/blob/v6.8.2/src/quick/items/qquickimage.cpp). Nel tag sono presenti clock e retainWhileLoading. **Scelta:** un FrameAnimation condiviso con fase della scena separata, pausa esplicita e nessuna velocità derivata dal numero di frame. RetainWhileLoading si valuta solo nei cambi di risorsa, con maggiore memoria transitoria. **Limite:** presenza nel sorgente non qualifica il pacchetto PySide della board; prova minima sul binario prima della selezione.

### Risultato dell'approfondimento

Il primo codice può partire da curve controllate e rig semplice, senza scegliere ora un motore esterno. Le ottimizzazioni iniziali sono strutturali: pochi dati, caricamento lazy, delegate stabili, un clock, assenza di lavoro nascosto e stesso ambiente di misura della baseline installata. Shader, geometria nativa, flocking e cambi dei governor sono rami condizionali con una prova di beneficio; le soglie dei 60 fps restano da verificare.
