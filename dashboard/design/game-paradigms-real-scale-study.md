# Gioco — audit dei piloti, fluidità e circuiti in scala reale

**12 ottobre 2026 · Studio per i prossimi passi v0.9.x.**

**Seguito autorizzato:** correzioni dei preset/protocolli, camere e aggiunta di Varano corto e dell'ovale Mallory nella candidata rc.8, con prove e limiti nel [report di implementazione](v09-paradigms-real-circuits-report.md). I riscontri sotto conservano lo stato precedente alle correzioni.

## 1. Perimetro e conclusione

Richiesta: verificare le modifiche manuali ai paradigmi e ai profili fissi, valutare le ottimizzazioni, studiare circuiti realistici con traiettorie e sorpassi. Questo documento aggiunge proposte al piano: le correzioni descritte non sono ancora implementate.

Esaminati i sorgenti attuali, confrontati con la copia della consegna rc.7 in `/tmp/smartpc-v09-rc7-delivery-runtime`. La versione locale resta **0.9.0-rc.7**, ma i file sono cambiati dopo quella consegna. Le sue prove precedenti non certificano automaticamente queste modifiche. La connessione di lettura alla board `192.168.1.179` ha restituito **No route to host**: roster installato, priorità effettive, FPS e stato del servizio attuali non verificati. `dashboard/game.sqlite` locale contiene zero tabelle; non è il database dei piloti di produzione.

Le nuove prove usano mondi in memoria e un archivio temporaneo sul PC, senza toccare i piloti dell'utente. [Script riproducibile](evidence/game-paradigms-real-scale-2026-10-12/diagnose.py), [risultati e impronte dei sorgenti](evidence/game-paradigms-real-scale-2026-10-12/diagnostics.json).

**Esito:** il progetto è fattibile. L'identità stabile di un pilota associato a un metodo ha senso come gioco; vanno corretti alcuni collegamenti tra profili, checkpoint e algoritmi. I circuiti reali richiedono una camera con zoom, tempi di sessione proporzionati, anticipazione delle curve e allenamento specifico al traffico. Aumentare la sola superficie disegnata non produce sorpassi competenti.

## 2. Cosa rappresentano davvero i sei piloti

| Pilota attuale | Implementazione effettiva | Valutazione |
| --- | --- | --- |
| **Evo** | Evoluzione dei pesi di una rete densa 32→16→2, selezione di élite, mutazione e nuovi individui casuali. | Metodo valido e leggero; rete di forma fissa, distinta da NEAT. |
| **Neat** | NEAT-Python, reti feedforward con evoluzione di nodi e connessioni, specie e riproduzione. Parte senza nodi nascosti. | Metodo valido; il numero di neuroni varia durante l'apprendimento. |
| **PPO** | Actor/critic NumPy, azioni gaussiane trasformate con tanh, GAE, obiettivo PPO con clipping, Adam e minibatch. | Metodo appropriato alle azioni continue; resta sperimentale nella competenza di guida. |
| **Pursuit** | Formula fissa basata su errore laterale/direzione e velocità obiettivo 10 m/s. Nessun parametro viene appreso. | Utile riferimento deterministico. Il nome Pure Pursuit è più specifico dell'algoritmo implementato. |
| **Clone** | Rete densa aggiornata per imitare quella stessa formula sulle osservazioni incontrate dalla propria guida. | Vera imitazione supervisionata online, ma non ancora DAgger completo né imitazione di una traiettoria ottima. |
| **PPO-Smooth** | PPO con rumore autoregressivo `noise = .82*noise + sqrt(1-.82²)*white`. | Idea sensata; la probabilità usata negli aggiornamenti non è coerente con il processo di campionamento. Da correggere prima dei confronti. |

Sono **sei identità di gioco**, con tre famiglie che apprendono: evoluzione, rinforzo e imitazione; inoltre un riferimento classico. PPO-Smooth è una variante dell'esplorazione PPO, non una nuova famiglia. Mantenere nomi personali e mostrare separatamente **famiglia / algoritmo / variante** nel dossier evita di confondere metodo e personaggio.

### 2.1 Evoluzione

La distinzione con NEAT è corretta: Evo mantiene la forma della rete e cerca pesi migliori, NEAT evolve anche la struttura. Il riferimento originale di [NEAT](https://nn.cs.utexas.edu/?stanley:ec02) descrive proprio l'evoluzione della topologia e la protezione dell'innovazione tramite specie.

Ottimizzazioni candidate: intensità di mutazione adattata alla stagnazione, più perturbazioni comuni per confrontare gli individui, controllo della diversità, campioni di partenza identici tra candidati, valutazione separata del campione. Conservare le mutazioni esplorative e l'élite; misurare tempo alla prima qualifica e passi per migliorarla. Aumentare la popolazione aumenta lavoro fisico e valutazioni, non garantisce apprendimento migliore. Prima confrontare 16/32/64 con budget e seed equivalenti.

### 2.2 NEAT

La configurazione usa `num_hidden=0`, collegamenti iniziali diretti, attivazione tanh e possibilità di aggiungere nodi/connessioni. Dire “parametri non modificabili” può fissare le **regole di evoluzione**, ma non può significare “neuroni sempre fissi”: l'aumento della struttura è parte del metodo.

Mostrare nodi, connessioni, specie e complessità del campione; valutare costo della rete quando cresce, stagnazione e ricambio delle specie. Un eventuale limite o una penalità di complessità deve essere esplicito nel preset. Non è dimostrato che partire dalla rete più piccola dia sempre il pilota migliore. Le precedenti prove di checkpoint restano riferimenti, da integrare per i nuovi preset.

### 2.3 PPO e PPO-Smooth

PPO standard ha un impianto coerente con il [paper originale](https://arxiv.org/abs/1707.06347): raccoglie esperienze con una policy e ne limita gli aggiornamenti mediante il rapporto tra probabilità nuove e vecchie. La distinzione tra termine fisico e limite temporale per il bootstrap è presente. Il controllo del nuovo PPO-Smooth non permette di estendere questo giudizio alla variante.

**Problema riprodotto:** al primo campionamento lo stato del rumore è zero. La varianza effettiva è `0,3276 × sigma²`, ma `log_probability()` usa `sigma²`. Nella prova da 32 ambienti lo scarto massimo del logaritmo della probabilità è **1,32494**. Nei passi successivi anche la media condizionata dipende dal rumore precedente. La densità marginale non basta per un rapporto corretto delle probabilità della traiettoria. Inoltre il rumore non viene azzerato per i singoli ambienti quando ripartono e non è incluso nelle osservazioni del critic. Riprendere il suo checkpoint conserva il rumore, ma non corregge queste incoerenze.

Due strade da studiare:

1. Mantenere PPO standard e migliorare la regolarità attraverso dinamica dello sterzo già presente, penalità moderata sulle variazioni e valutazione dell'oscillazione. Registrare azione precedente e versione dell'obiettivo se necessari. Non alterare arbitrariamente l'azione senza trattarne le conseguenze sul modello della policy.
2. Implementare un'esplorazione correlata con densità, stato, reset e gradienti coerenti; confrontare una soluzione documentata come [gSDE](https://arxiv.org/abs/2005.05719). È una proposta di ricerca, non una proprietà già acquisita dal codice attuale.

Servono verifiche numeriche dei gradienti e un confronto a parità di budget, non soltanto la visione di uno sterzo più morbido. In gara entrambe le varianti esportano una rete deterministica congelata: oggi la differenza riguarda l'allenamento, non l'aggiunta di rumore in gara.

### 2.4 Il pilota geometrico

In `PurePursuit.act()` e `Policy.act(kind='reference')` la sterzata è `clip(heading/pi*2.6 + offsetNormalizzato*.7)`. Il [Pure Pursuit geometrico](https://www.ri.cmu.edu/publication_view.html?pub_id=278) segue un punto più avanti sulla traiettoria e ricava la curvatura dal bersaglio e dalla distanza di anticipo. Quel calcolo è presente nel controller diagnostico tecnico `reference_actions()`, ma non nel nuovo pilota chiamato Pursuit.

Il controllore attuale comunque **funziona sulle piste disponibili**: dieci partenze variate per pista, dieci arrivi su dieci sull'ovale (circa 36,22 s) e dieci su dieci sul tecnico (circa 30,21 s), un giro e nessun avversario. Il controller diagnostico tecnico, più prudente a 7 m/s, fa dieci arrivi intorno a 40,22 s; tempi non confrontabili come superiorità algoritmica perché le velocità obiettivo sono diverse. Nessuna di queste prove certifica il sorpasso o circuiti futuri.

Proposta: chiamarlo **Guida geometrica** finché non usa un vero bersaglio anticipato; mantenerlo come riferimento subito disponibile, con tempo di addestramento zero. Per curve più varie, usare anticipo legato alla velocità e un profilo di frenata/velocità per curvatura. “Linea ideale” va sostituito con “linea di riferimento” finché non esiste un'ottimizzazione del tempo sul giro.

### 2.5 Imitazione

Clone imita la guida geometrica attuale, non i campioni Evo/PPO e non una soluzione ottima. Il target longitudinale si avvicina a 10 m/s; non riceve il reward per diventare più veloce. La progressione Controllo→Passo può cambiare il criterio di selezione, ma **non cambia l'obiettivo supervisionato**. Una rete può occasionalmente superare il maestro per approssimazione: non è un meccanismo progettato per migliorarlo.

Inoltre le copie ritirate restano inattive fino alla fine comune della generazione, mentre `learn_step()` usa tutte le righe, comprese osservazioni azzerate da `active_only=True`. La prova mostra che una riga nulla ha target `[0,1]` e aggiorna i pesi: i ritiri possono occupare gran parte del batch con esempi senza una scena di guida valida.

Interventi proposti: maschera dei campioni realmente attivi prima del passo, ripartenze individuali per imitazione, batch e buffer di esempi persistenti/versionati, loss separata di sterzo e accelerazione, held-out e maestro esplicito. L'attuale gradiente a ogni passo non garantisce più qualità di un minibatch meno frequente. DAgger aggiunge raccolta e aggregazione degli esempi negli stati visitati dal pilota, affrontando il cambiamento della distribuzione rispetto alle dimostrazioni; il codice attuale interroga il maestro in quegli stati ma non aggrega un dataset. [Studio originale DAgger](https://proceedings.mlr.press/v15/ross11a.html).

Un **pilota ibrido Imitazione→PPO** può essere un personaggio distinto: impara prima una guida affidabile e poi cerca velocità con il reward. La sequenza è parte del suo preset fisso e va registrata nello storico.

## 3. Profili fissi: intenzione valida, vincoli incompleti

Il menu disabilita metodo, rete e parametri avanzati. Il backend invece accetta ancora cambiamenti di algoritmo/neuroni tramite `set_profile()`, `configure()` e `applySetup()`; l'azione pubblica `game.configure` resta collegata in Main. Questo non è un problema di sicurezza: significa che l'identità fissa del pilota è una regola della presentazione, non ancora del dominio.

| Riscontro | Effetto | Proposta |
| --- | --- | --- |
| Lettura di un circuito senza percorso esistente usa `default_profile(number)`, sempre Evo. | La prova legge tutti e sei i piloti come Evoluzione sul tecnico prima della prima selezione. `profileFor()` usa quella lettura; la bozza può quindi applicare Evo al pilota quando si cambia circuito. `_ensure_paths()` copia il profilo originale, ma la successiva applicazione della bozza può sovrascriverlo. | Fallback al preset del pilota; letture e creazione percorso devono concordare. Gate obbligatorio: algoritmo invariato nel cambio circuito dalla UI. |
| `traffic` resta modificabile per i piloti che apprendono. | Cambia scenario e chiave strutturale del percorso; non tutti i parametri sono fissi. | Fissare il protocollo nel preset oppure separare la scelta della sessione dal metodo immutabile. |
| Nuovo pilota usa il default Evo, mentre il metodo è bloccato. | Non si può creare un nuovo Clone/PPO/NEAT dalla UI. | Scegliere un preset prima di creare l'identità; poi sola consultazione. |
| Reset del riferimento elimina la policy pronta. | Pursuit dopo reset risulta senza modello, benché non debba apprendere. | Ricreare il riferimento o usare “Ripristina riferimento”, senza azzerare una finta formazione. |
| Trasferimento accetta una rete densa Clone compatibile; worker inizializza soltanto PPO o Evolution. | Pesi di imitazione trasferiti possono essere accettati e poi ignorati. | Gestire esplicitamente ogni backend; rifiutare prima ciò che non sa inizializzare. |
| Preset e metodi sono ripetuti in learning/store/settings/service. | Nuovi metodi possono avere nomi, disponibilità e parametri incoerenti. | Registro comune delle capacità e ID/versione del preset. |

**Contratto proposto:** `driver.id` stabile, `preset.id/version`, famiglia, algoritmo, architettura, seed, regole di apprendimento immutabili; percorsi separati per circuito/vettura/fondo/protocollo. Una nuova versione del preset crea un percorso distinto, con il precedente consultabile. Un checkpoint si riprende soltanto con configurazione compatibile. Il reset conserva storia e identità. Il preset NEAT fissa le regole, non la topologia risultante.

I sei piloti attuali hanno seed diversi (1…6), quindi il confronto tra un singolo Evo e un singolo PPO non isola l'effetto dell'algoritmo. Nella classifica è una gara tra personaggi; nelle prove tecniche servono almeno cinque seed per metodo e condizioni uguali. I risultati migliori non devono sostituire la mediana o nascondere i ritiri.

## 4. Altri metodi da aggiungere allo studio

| Candidato | Cosa aggiunge | Priorità |
| --- | --- | --- |
| **Imitazione con DAgger** | Maestro negli stati visitati, dataset aggregato, recupero dagli errori. | Alta: evoluzione concreta di Clone, dopo un maestro verificato. |
| **Imitazione→PPO** | Partenza guidata, poi ricerca autonoma di un passo migliore. | Alta: preset ibrido distinto e storico delle due fasi. |
| **SAC** | Rinforzo per azioni continue, riuso delle esperienze con replay, ottimizzazione con entropia. | Primo nuovo algoritmo RL da sperimentare; attore/critic, target e buffer aumentano lavoro, da misurare. |
| **TD3** | Attore deterministico, due critic e aggiornamenti ritardati. | Alternativa a SAC se utile al confronto; non necessaria insieme a SAC nel primo passo. |
| **PPO con memoria** | Policy ricorrente per informazioni temporali e osservazione parziale. | Dopo circuiti/traffico; è una variante di architettura, non un nuovo paradigma. |
| **CEM/CMA-ES** | Altri metodi di ricerca dei parametri senza gradienti. | Solo dopo il confronto Evo/NEAT; attenzione al costo in dimensione elevata. |
| **A2C / DQN** | A2C offre un altro aggiornamento actor/critic; DQN standard richiede azioni discrete. | Non prioritari: minor differenziazione da PPO oppure discretizzazione artificiale di sterzo/pedali. |
| **MPC** | Controllo predittivo del veicolo e dei vincoli. | Riferimento futuro; non un nuovo pilota che apprende da solo, costo online da studiare. |

SAC e TD3 sono documentati nei lavori originali: [SAC](https://proceedings.mlr.press/v80/haarnoja18b.html), [TD3](https://arxiv.org/abs/1802.09477). La scelta prioritaria di SAC è una proposta per questo progetto, non una superiorità già misurata sulla board. Le nuove identità entrano nel piano; nessun modello è stato creato o scaricato durante l'analisi.

## 5. Fluidità: cosa conservare e cosa misurare

| Modifica manuale | Giudizio sul codice | Limite o seguito |
| --- | --- | --- |
| `requestPaint()` solo con Canvas visibile; uscita prima di `getContext()`. | Sensata: elimina richieste e preparazione inutili. | Non prova da sola una riduzione numerica dei frame persi. |
| Animazioni delle auto abilitate solo con `car.visible`. | Sensata per le vetture nascoste. | Verificare anche il lifecycle della vista e cambio di selezione. |
| Worker `setpriority(...,10)`. | Più esplicito della somma relativa di `nice()`. | Il servizio nel repository non contiene `Nice=-5`: l'ipotesi del vecchio studio dipende dall'installazione effettiva. Nessuna precedenza assoluta della GUI è garantita da nice. |
| Poll GUI 33 ms attivo / 250 ms in pausa. | Riduce controlli a vuoto. | Ripresa da pausa lascia inizialmente 250 ms fino a `ready`; rimettere subito il ritmo attivo nella ripresa. Separare messaggi di controllo e scena. |
| `sleep(.001)` alla pubblicazione dei frame. | Cede un breve intervallo circa 25 volte/s. | Non limita il lavoro a ogni passo e non impedisce che il training saturi un core. Va misurato il compromesso GUI/passi al secondo. |
| Prova multigiro a tempo reale. | Utile come osservazione di una prestazione. | Ha sostituito cinque partenze variate con una singola partenza fissa. Separare prova visibile e benchmark standard, versionare risultati/classifica. |
| Più giri in allenamento/preview. | Sensato come futura fase di resistenza. | Il limite episodio rimasto 60 s e la qualifica da un giro non sono coerenti con il nuovo compito. |
| `Process.close()` con errore assorbito dopo terminate/join. | Evita un'eccezione visibile. | Se il processo è ancora vivo il riferimento viene perso: occorre lifecycle che conservi il processo fino a uscita verificata. |
| Plymouth chiuso prima di EGLFS. | Plausibile pulizia del boot. | Confermare daemon e percorso del comando sulla board; non dedurre un recupero CPU attuale dalla modifica al file. |

Un residuo grafico: nel Canvas del grafico ora `p.length<2` ritorna **prima del clear**. Se si passa da dati precedenti a zero/un punto, il disegno vecchio può restare; la guardia di visibilità è corretta, ma il clear deve precedere l'uscita per pochi punti quando il Canvas è visibile.

La documentazione [Qt 6.8 sulla performance](https://doc.qt.io/qt-6.8/qtquick-performance.html) raccomanda di profilare bindings, conversioni e funzioni costose. Il [Canvas Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html) descrive il rendering su immagine e i costi di aggiornamento: ridurre paint inutili è motivato, quantificare il guadagno richiede misure.

Il precedente `v09-fluidity-and-performance-optimization-study.md` ha alcune affermazioni da rettificare: hardware T527/Mali/4×A55 e baseline rc.5/API2.8 non corrispondono alla baseline rc.7/A733/PowerVR di questo lavoro; il produttore descrive A733 con due A76 e sei A55. [Specifiche A733](https://www.allwinnertech.com/index.php?a=index&c=product&id=139). Non è stato trovato nel corpus un file `study_results.json` con il benchmark lì citato; “tutte le ipotesi confermate”, contesa DRAM causale e 60 FPS garantiti non sono conclusioni riproducibili da quel testo. Le ottimizzazioni possono essere valide anche quando la spiegazione causale è ancora da verificare.

**Riferimento storico separato:** il soak nativo rc.7 di 30 minuti, precedente alle nuove modifiche, aveva 1.705.280 passi salvati, pausa 174 ms, massimo termico 64,48 °C e timing software p95 **64,73 ms**, quindi non dimostrava 60 FPS costanti. [Risultato originale](evidence/v09-settings-circuits-2026-10-11/board-native/soak-summary.json). Non estendere quei numeri a questa revisione manuale.

Architettura candidata: fisica a passo fisso 60 Hz, training accelerato indipendente, scene compatte a 25–30 Hz con timestamp, interpolazione del rendering a 60 Hz, stato/menu/statistiche aggiornati soltanto quando cambiano. Pausa/errore/salvataggio hanno un canale rapido. Limitare ritardo e coda; evitare ricostruzione dei percorsi statici quando la camera si muove. Tutta la RAM disponibile può essere usata dopo Start, ma aumentare buffer e copie non risolve un collo di bottiglia della CPU/GUI.

## 6. Dimensioni attuali e riferimenti reali

Misure dai contenuti realmente usati: ovale **338,779 m**, tecnico **272,052 m**, entrambi larghi **10 m**. Auto standard **4,4×1,8 m**, passo 2,65 m, massa 1.200 kg, potenza 85 kW. Il tecnico attuale è un circuito compatto di esercizio; la carreggiata ha già una larghezza realistica per un circuito stretto, lo sviluppo complessivo è molto ridotto.

| Riferimento primario | Lunghezza | Larghezza pubblicata | Rettifilo partenza | Uso nello studio |
| --- | ---: | ---: | ---: | --- |
| [Varano corto, scheda ufficiale](https://www.autodromovarano.it/wp-content/uploads/2024/04/pista_1640_19.pdf) | 1.640 m | 10–12 m | 467 m | Primo riferimento consigliato: dimensioni complete e circuito più corto. |
| [Varano completo, scheda ufficiale](https://www.autodromovarano.it/wp-content/uploads/2024/04/pista_2350_19.pdf) | 2.350 m | 10–12 m | 467 m | Estensione successiva con più combinazioni di curve. |
| [Magione, regolamento pubblicato dall'autodromo](https://www.autodromomagione.com/wp-content/uploads/2018/02/REGOLAMENTO-100-MIGLIA.pdf) | 2.507 m | Non ricavata dalla fonte consultata | Non ricavato dalla fonte consultata | Seconda famiglia di layout; verificare planimetria/dimensioni prima di importare. Fonte storica 2018. |
| [Mugello, sito ufficiale](https://www.mugellocircuit.it/it/pista/il-tracciato-ai-raggi-x) | 5.245 m | Non ricavata dalla pagina consultata | Non ricavato dalla pagina consultata | Stress e varietà successivi; altimetria non riprodotta dal modello 2D attuale. |

L'[Appendice O FIA 2026](https://www.fia.com/system/files/documents/appendix_o_2026_published_23122025.pdf), §§7.2, 7.3, 7.7, considera la lunghezza sulla mezzeria, propone per nuovi circuiti permanenti almeno 12 m di larghezza, almeno 15 m per la griglia fino all'uscita della prima curva e preferibilmente almeno 250 m tra partenza e prima curva. Le transizioni di larghezza dovrebbero essere graduali, non oltre 1 m ogni 20 m. Sono riferimenti di progettazione; non rendono irrealistico un circuito esistente da 10 m e non sono un requisito di omologazione del nostro gioco.

**Scelta proposta:** mantenere i due circuiti attuali per allenamento rapido; aggiungere un tracciato derivato da Varano corto, in metri, con sviluppo 1.640 m e larghezze 10–12 m. Prima versione eventualmente a larghezza uniforme 12 m, dichiarando l'approssimazione. Non ingrandire l'auto e non moltiplicare insieme lunghezza del circuito, larghezza dell'asfalto e dimensioni del veicolo: ogni misura ha il proprio significato.

Copiare le **dimensioni documentate** è già preparabile; una mappa promozionale e una lunghezza totale non forniscono coordinate metriche esatte, ogni raggio e le larghezze locali. Ricostruire una mezzeria, calibrare lo sviluppo e verificare curve/bordi; registrare fonte, revisione, trasformazione e precisione. Etichetta iniziale “ispirato a Varano corto” o “ricostruzione approssimata”, non replica geometrica esatta. La planimetria ufficiale riporta anche pendenza/banking: nel modello piano quei fenomeni restano esclusi dalla prima ricostruzione.

### 6.1 Spazio per traiettorie e sorpassi

Con due auto larghe 1,8 m, margini esterni 0,75 m per lato e separazione 0,75 m, una sezione rettilinea richiede **5,85 m**. Per tre auto gli stessi margini e due separazioni richiedono **8,40 m**. Sono ingombri statici di progetto, non distanze di sicurezza valide a qualunque velocità. Gli attuali 10 m consentono già affiancamenti, ma curve molto corte e guida centrata sulla mezzeria limitano le occasioni.

Su un nuovo layout servono rettilinei da centinaia di metri, frenate prima di curve lente, cambi di raggio progressivi, vie di fuga distinte dal bordo stradale e traiettorie alternative. Un sorpasso deve essere completato e mantenuto senza taglio, contatto o frenata innaturale dell'avversario; non basta vedere due icone affiancate.

Per un ovale più grande si può preparare un nuovo ID con due rettilinei di 600 m e raggio di mezzeria 100 m: lunghezza teorica **1.828,319 m**, larghezza 12 m, auto invariata. È una proposta sintetica con dimensioni da autodromo, non un ovale reale copiato e non un'alternativa alla ricostruzione tecnica. Il vecchio ovale resta riconoscibile nello storico.

## 7. Camera e GUI sul 3,5″ orizzontale 960×640

La proporzione fisica è `pxPerMetro` uguale per strada, vettura e traiettorie. Nella vista completa la scala dipende dall'**ingombro** del circuito, non solo dalla lunghezza del giro. Con 912 px utili e ingombro ipotetico di 1.000 m, un'auto lunga 4,4 m è appena **4,0 px** e larga **1,64 px**. Nell'ovale sintetico proposto, ingombro esterno 812×212 m, la vista completa sarebbe dello stesso ordine: circa 5 px di lunghezza. L'auto fisica può rimanere esatta, ma non leggibile come vettura dettagliata.

**Tre modalità candidate:**

- **Segui pilota, predefinita:** nord fisso, camera morbida senza rotazione continua, anticipo nella direzione di marcia, zoom con limiti e isteresi. Obiettivo iniziale 5–8 px/m: auto lunga 22–35 px, carreggiata 12 m larga 60–96 px, campo orizzontale circa 114–182 m con 912 px utili. Valori di progetto da verificare sul display fisico.
- **Duello:** estende l'inquadratura al pilota selezionato e al rivale vicino, con soglia oltre la quale riprende il pilota e indica l'altro fuori campo. Non allargare artificialmente le sagome per renderle visibili.
- **Circuito:** vista completa con piccoli marcatori di posizione identificabili come simboli, non auto fuori scala; minimappa coerente quando si torna a Segui/Duello.

Minimappa candidata circa 150×100 px, collocata senza coprire il bersaglio; dati essenziali pilota, posizione/giro e velocità in un bordo compatto. Dossier e risultati restano nella loro vista. Nessun ritorno del titolo grande “Auto che impara” o della legenda tasti permanente. Colori, font, motion policy e token dei temi rimangono comuni.

Quando gira la simulazione: 2/8 selezionano il pilota, 4/6 cambiano modalità camera, **5 richiede pausa**; solo dopo acknowledgment torna la navigazione normale. Il controllo camera/display già esistente dovrà essere mappato senza ambiguità e mantenere sensori accessibili. Movimento ridotto: meno transizioni, camera stabile e niente oscillazioni di zoom. La camera trasforma lo stesso mondo metrico: non influenza collisioni, sensori, tempi o apprendimento.

## 8. Simulazione, tempi e apprendimento sui nuovi circuiti

### 8.1 Tre giri: incompatibilità attuale e limiti

Il worker crea ora mondi di training da tre giri; i checkpoint precedenti erano da uno. `World.restore()` confronta anche `laps`: la prova riproduce **Mondo salvato incompatibile**. La configurazione generale non registra questo cambio di protocollo. Serve una versione esplicita del compito e una ripartenza dell'episodio con conservazione dei pesi e provenienza, evitando di presentarla come una ripresa bit per bit.

Con il riferimento attuale, tre giri sull'ovale sono dell'ordine di 108 s e sul tecnico 90 s: limite 60 s insufficiente anche per una guida corretta. Una rete più veloce può riuscirci, ma il limite distorce la prima fase di apprendimento. La qualifica automatica resta un giro con limite 60 s: non dimostra resistenza su tre giri. La nuova Prova ha cambiato protocollo senza sostituire la scritta Classifica `valid/5`: risultati e denominatore vanno distinti e versionati.

Su 1.640 m, con una **velocità media ipotetica** di 20 m/s, un giro richiede 82 s e tre 246 s. Il preset iniziale da 60 s e perfino il massimo UI da 180 s non bastano per tre giri a quella media. Anche il limite gara `max(300,laps*120)` può penalizzare piste lunghe e piloti più lenti ma validi. Calcolare i limiti dal riferimento circuito/vettura e dalla fase; aggiungere rilevazione di stagnazione senza confondere lentezza iniziale e fallimento definitivo.

Proposta di curriculum: recupero e settori → giro completo affidabile → passo → tre giri consistenti → traffico e sorpasso. Premiare progresso continuo, affidabilità e poi tempo; penalità morbide di contatto/variazione dei comandi. Normalizzare bonus e soglie al compito e versionare reward/qualifica. Oggi il bonus usa un riferimento 60 s e il premio progresso cresce con i metri: cambiare circuito richiede confronti di score per ambito, non una graduatoria globale dei reward.

### 8.2 Anticipazione e limiti fisici

La policy vede cinque raggi fino a 50 m, errore laterale/direzione, dinamica e tre avversari fino a 40 m. Non vede esplicitamente la curvatura più avanti. Sopra 30 m/s il canale velocità longitudinale, normalizzato con `/30`, satura per il clip finale: non è un limite di velocità del motore, ma perdita di informazione. A 30 m/s e decelerazione ipotetica 7 m/s², frenare fino a zero richiede circa **64,3 m** senza margini; cinquanta metri di sensori possono essere insufficienti.

Studiare `race-observation-v2`: campioni di mezzeria/curvatura e larghezza a distanze crescenti (per esempio 15/30/60/100/150 m), velocità di riferimento, distanza e velocità relativa dei rivali con identità più stabile tra slot, precedente azione ove utile. Questo cambia input e compatibilità delle reti: non caricare vecchi pesi come se avessero gli stessi sensori. Fissare se tutti i metodi ricevono la stessa informazione o se il maestro usa una mappa privilegiata, dichiarandolo nel confronto.

La velocità utile in curva dipende dal raggio e dall'aderenza: prima approssimazione piana `v ≈ sqrt(mu*g*R)`. Con mu=0,95, R=11,28 m dà circa 37 km/h, R=50 m circa 78 km/h, R=100 m circa 110 km/h. Sono stime senza transitori e senza carico aerodinamico, non limiti esatti del nostro modello. Curve più ampie permettono velocità realistica senza aumentare artificialmente la potenza. Frenata/sterzo combinati, energia, rettilineo e attrito vanno verificati sulla vettura standard prima di aggiungere modelli di auto.

### 8.3 Traffico e gara

L'allenamento solitario non dimostra sorpassi: i canali degli avversari sono vuoti. La modalità traffico attuale incontra un solo bot prudente, insufficiente a qualificare tutte le gare tra quattro piloti. Preparare scenari graduati: auto davanti più lenta, affiancamento in rettilineo, frenata in coppia, ingresso/uscita curva, reinserimento, rivali con velocità e comportamento diversi. Politiche dei rivali congelate durante un confronto; archivio dei rivali e partenza variata separati dalle prove finali.

Conservare la gara a una vettura per pilota e nessun aggiornamento dei pesi. Qualificare separatamente affidabilità, passo, resistenza e traffico; classifica per circuito/vettura/fondo/regole/hash della policy. Possibile mantenere il riferimento geometrico in una categoria dedicata oppure mostrare esplicitamente il suo tipo quando partecipa alla stessa gara.

### 8.4 Geometria e costi

La dimensione in metri non moltiplica da sola i pixel né il costo fisico. Contano segmenti, copie attive, sottopassi, collisioni e sensori. Non estendere il tecnico 384 punti a una pista di chilometri mantenendo automaticamente la stessa precisione: servirà densità adattata alla curvatura e un budget d'errore della sagoma/bordo.

Indice spaziale e proiezione topologica esistenti sono una base utile; verificare tratti ravvicinati e orientamenti antiorari, griglie sufficientemente distanziate, cancelli anti-taglio e coordinate di start. Larghezza variabile oggi non è un dato locale della mezzeria: aggiungere bordi e larghezza interpolata usati dalla **stessa** geometria di sensori/render/collisioni. Densità fisica e dettaglio grafico possono differire solo con un errore massimo dichiarato e senza falsificare il bordo visibile.

Sul render preparare la geometria in coordinate del mondo, poi traslare/scalare il contenitore con la camera: non riformattare tutti i PathSvg ogni frame. Usare segmenti visibili/detail level se la misura dimostra necessità. Quattro vetture in gara sono un carico molto diverso da 32/64/256 copie di training.

CPU: fisica, reward, allenamento e reti piccole; GPU: scena 2D; NPU: solo eventuale inferenza di modelli più grandi se mostra beneficio. L'aumento del circuito e l'arrivo di SAC non rendono automaticamente conveniente la NPU né la rendono un acceleratore della geometria. Le vecchie misure CPU/NPU sulle reti piccole restano un riferimento da ripetere soltanto se cambia il carico rilevante.

## 9. Piano operativo proposto e criteri di uscita

| Ordine | Blocco | Criterio verificabile |
| --- | --- | --- |
| **P0** | Integrità del pilota e dei protocolli | Tutti i sei preset mantengono metodo/rete nel cambio circuito, dal primo accesso; nessuna azione pubblica altera i campi fissi; creazione sceglie il preset; reset/transfer hanno esito coerente per ogni backend. Nessuna perdita dei modelli storici. |
| **P0** | Correttezza apprendimento | Probabilità/gradienti/reset del rumore coerenti prima di promuovere PPO-Smooth; Clone non apprende dalle righe inattive; maestro nominato; limiti multigiro e migrazione checkpoint espliciti. |
| **P1** | Fluidità della revisione manuale | Profilo su board raggiungibile, prima/dopo sullo stesso carico; pause mediane/p95, scene obsolete/scarti, passi/s, memoria/termica, frame CPU/GPU distinti. Obiettivo 60 FPS; se non raggiunto, documentare il limite e tarare il carico. |
| **P1** | Camera e mondo grande | 960×640, testo 1–1,1, giorno/notte e temi comuni; auto/asfalto con scala identica; interazione mentre simula e ritorno dopo pausa; verifica fisica del 3,5″. |
| **P2** | Circuito metrico derivato da Varano corto | Lunghezza 1.640 m entro tolleranza di ricostruzione dichiarata, larghezza documentata o approssimazione esplicita, geometria condivisa, nessun taglio/cambio ramo/griglia in contatto. Fonte e hash registrati. |
| **P2** | Competenza e gara | Almeno cinque seed per metodo, budget uguali; prima qualifica, tasso di arrivo, mediana/spread/ritiri; held-out distinto; 3/5/10 giri, due/quattro piloti, modelli immutati. Separare giro solo e sorpasso. |
| **P3** | DAgger, ibrido e SAC | Verifica numerica/round-trip/resume, confronto con i metodi attuali su circuito e carico comuni. Un algoritmo nuovo per volta, senza allargare il roster prima di avere prove utili. |
| **Dopo** | Più circuiti, vetture e fondi | Parametri e ambiti versionati; aderenza/forza/potenza verificabili. Bagnato, sterrato, usura, danni e altimetria richiedono analisi e collaudi propri. |

Per la fluidità partire da un carico rappresentativo Evo/PPO/NEAT e gara di quattro auto; allargare il collaudo solo per i rischi specifici del nuovo algoritmo/circuito. Non ripetere indiscriminatamente tutte le prove storiche. Nessun gate soddisfatto dalla sola disponibilità di RAM o dal refresh a 60 Hz del pannello.

**Decisione proposta:** conservare l'idea dei piloti fissi, correggere prima gli errori P0, poi camera/tempi/sensori per un mondo più grande; aggiungere il primo circuito reale come ricostruzione documentata, qualificare la guida e soltanto dopo ampliare i paradigmi. Fisica 2D e rendering 2D rimangono una scelta adatta, con fattibilità prestazionale da misurare sul nuovo contenuto.
