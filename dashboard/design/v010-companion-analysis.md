# SmartPC — v0.11 · Analisi iniziale del compagno interattivo

> **Riallineamento roadmap · 13 ottobre 2026:** Compagno ora v0.11, memoria/scene AI v0.12; la nuova v0.10 è Acquario. Nomi dei file e asset conservati per mantenere i collegamenti. Baseline, fonti e proposte dell’11 ottobre restano storiche; per stato corrente e numerazione vale il [MasterPlan](release-masterplan.md), revisione 2.68. Nessuna nuova verifica sulla board.
**Revisione 6 · 11 ottobre 2026 · Europe/Rome**

**Stato: analisi; scelte proposte da discutere, nessuna implementazione o prova sulla board.**

Riferimento: [MasterPlan, revisione 2.56](release-masterplan.md), soprattutto sezioni 2, 5, 12 e 13. Baseline documentata: core **0.9.0-rc.6**, Theme API **2.9**, **68 superfici**, Apple Calm **1.6.2**. Baseline letta nei documenti e nei sorgenti locali; questa analisi non verifica nuovamente l'installazione Orange Pi.

**Decisioni acquisite:** stile **A — Calm / illustrazione 2D** e accudimento **più attivo**, con bisogni frequenti e conseguenze temporanee recuperabili. L'approfondimento operativo è nella [specifica funzionale e tecnica](v010-companion-functional-spec.md): schermate/input, regole di cura/tempo, mini-gioco, progressione, protocollo delle azioni, persistenza, contratti e gate. I parametri numerici restano proposte da tarare.

**Ricerca online integrata:** [14 riferimenti principali e applicazioni](v010-companion-online-research.md), consultati l'11 ottobre 2026: studi originali sul rapporto e sulla motivazione, comportamento animale nei giochi, utility/animazione, Tamagotchi, Google/W3C, Disney/Spine, ToonCrafter, Qt e SQLite. La specifica revisione 2 amplia personalità, leggibilità dei bisogni, focus, gesti autonomi, compatibilità del rig, uso mirato di Animator, timeout e qualifica degli asset AI. Evidenze esterne, nostre proposte e verifiche future sono distinte.

## 1. Risultato da progettare

Creare un cane riconoscibile che dia compagnia durante l'uso della dashboard e risponda alle azioni della persona. Deve avere comportamenti comprensibili anche offline, lasciare leggibili i dati e cedere immediatamente agli urgenti.

Il MasterPlan prevede già cane locale, riposo/attenzione/gioco, reazioni preparate, SceneHost persistente e profilo Cozy. Mancano la definizione dell'esperienza quotidiana, i comandi, le regole di comportamento, le scene, gli asset e la relativa qualifica.

**Indirizzo confermato dall'utente nella chat:** compagno presente nella dashboard, con una propria schermata per giocare e interagire, **da accudire con bisogni e progressione**, capace anche di **reagire agli avvisi**. Le tre dimensioni sono cumulative; non sono alternative fra cui scegliere.

**Ipotesi di lavoro consigliata entro questo perimetro:** presenza discreta nelle viste compatibili, più una schermata Compagno per interagire. Il piacere nasce da gesti leggibili e risposte coerenti: il cane si accorge di un richiamo, si avvicina, riceve una carezza, gioca e torna tranquillo. Un'animazione casuale continua non basta a costruire questo rapporto. Stile A e intensità di cura sono acquisiti; regole precise dei bisogni, progressione e gioco sono da concordare. È autorizzata l'analisi, non l'implementazione.

## 2. Perimetro del MasterPlan

| Livello | Contenuto |
| --- | --- |
| **v0.11 prevista** | Cane e asset locali; comportamento deterministico; interazioni e reazioni agli eventi qualificati; scene giorno/notte; Cozy; pause, riprese, temi e carico. |
| **Ampliamento v0.11 richiesto dall'utente** | Schermata propria, gioco/interazione, accudimento con bisogni e progressione, reazioni agli avvisi. Analizzare stato persistente minimo, simulazione del tempo e recupero; nomi/skin, azioni e regole precise restano da scegliere. |
| **v0.12 prevista** | Preferenze/storia del compagno come memoria evoluta e planner AI opzionale con azioni/asset validati, retention, cancellazione, budget e fallback. |
| **Nuova fattibilità se richiesta** | Voce, microfono, camera, riconoscimento della persona, conversazione libera e addestramento di modelli. Non sono prerequisiti del cane locale. |

L'ampliamento richiede nella v0.11 una **memoria funzionale minima**: identità, bisogni, progressione e impostazioni devono sopravvivere al reboot. Questo è stato locale del gioco di accudimento; la v0.12 conserva il lavoro sulla storia evoluta e sul planner AI. Le normali impostazioni persistenti e lo stato dei bisogni non costituiscono apprendimento AI. Uno stato conservato durante la navigazione non dimostra recupero al reboot.

L'analisi v0.11 può avanzare mentre restano aperti gate del Gioco; il rilascio dovrà conservare la baseline e verificare gli effetti della convivenza. Non si dichiara conclusa la qualifica v0.9.

## 3. Cosa c'è già e cosa va ampliato

Riscontri nei sorgenti al momento dell'analisi:

| Base riutilizzabile | Limite attuale e conseguenza |
| --- | --- |
| [SceneHost](../components/SceneHost.qml) persistente nel root | Già gestisce caricamento, regioni, sospensione e recovery. Va riusato; la vita del cane deve avere un controller di prodotto separato dal renderer. |
| [ActorState](../components/ActorState.qml) | Identità, posa, locomozione, sequenza, pausa, anchor e motionMode. Non contiene ancora bisogni, interazioni o decisioni del cane. |
| [Registry scene](../scenes/registry.json) e attore geometrico | Renderer di prova da 30×30 px; non è un cane, un set di animazioni o una prova del futuro carico. |
| Region negotiation in [Main.qml](../Main.qml) | Il percorso builtin dichiara una regione di **56×48 px**, a x=880/y=8. Un footprint più grande non entra e può bloccare/nascondere l'attore. Serve una scelta esplicita delle regioni per ogni presentazione. |
| `scene.main` e `SceneContext` pubblici | La superficie dichiara **zero azioni**; il ViewHost della scena è `interactive: false`. La scena ambientale non è già un'interfaccia di gioco. |
| Notifica fornita alla scena | Main inoltra l'urgente o il banner corrente. Questo non è un flusso completo di eventi semantici di tutti i moduli. Non collegare direttamente ogni refresh a una reazione. |
| Pause e motion già presenti | Main sospende la scena con overlay, urgente, **night** e **quietActive**. La v0.11 deve separare palette notte, silenzio Avvisi, riposo del cane e movimento ridotto, come chiede il MasterPlan. |
| Theme Engine e fallback | Contratti, asset/renderer, staging e recovery esistono. Nuove superfici/azioni richiedono evoluzione additiva, fixture e kit aggiornati; non una riscrittura dell'engine. |

Gli studi storici [presentazioni e compagno](theme-engine-presentation-spec.md) e [guida del motore](theme-engine-implementation-guide.md) contengono idee pertinenti, ma assegnano ancora il cane alla vecchia v0.9 in alcuni passaggi. Per numerazione e stato vale il MasterPlan corrente. Le proposte UX precedenti non sostituiscono i comandi e lo stile attuali.

## 4. Punti di analisi e decisioni attese

| Punto | Domanda da risolvere | Proposta iniziale | Evidenza richiesta prima dell'implementazione |
| --- | --- | --- | --- |
| **Ruolo** | Come convivono presenza, accudimento e avvisi? | Le tre funzioni sono richieste; interazioni brevi e leggibili. | Scenari quotidiani e confini del prodotto. |
| **Identità** | Quale personaggio master nello stile A? | Un cane iniziale illustrato 2D, curioso e calmo; direzione A scelta dall'utente. | Scheda personaggio, asset/pose coerenti e layout 960×640. |
| **Presenza** | Dove appare e quanto spesso? | Home e viste compatibili; vista propria per le azioni. | Mappa regioni con e senza evento, banner, testi grandi e focus. |
| **Comandi** | Quali azioni sono divertenti e leggibili con nove tasti? | Richiama, Accarezza, Gioca; Riposo e visibilità nel menu. | Flusso completo, ritorni e interruzioni, senza pressioni lunghe obbligatorie. |
| **Comportamento** | Come evita ripetizioni senza diventare imprevedibile? | Stati, transizioni, tempi e varianti controllate. | Tabella di transizione, priorità e sequenze riproducibili. |
| **Bisogni** | Quali bisogni e con quali effetti? | Accudimento attivo richiesto; tre bisogni con conseguenze osservabili, temporanee e recuperabili. | Regole del tempo, spegnimento, recupero e significato delle eventuali barre. |
| **Progressione** | Cosa cresce e cosa si sblocca? | Legame persistente e nuove varianti/oggetti; nessuna esperienza per semplice pressione ripetuta. | Regole di avanzamento, salvataggio e benefici riconoscibili. |
| **Eventi** | A cosa reagisce e con quale fiducia? | Pochi eventi qualificati, una reazione breve e deduplicata. | Matrice fonte/freschezza/capacità/annullamento. |
| **Grafica** | Quale combinazione rig/clip nello stile A? | Parti raster AI e rig Qt per gesti semplici, pose/clip per cambi articolati. | Qualità visiva, clip interrompibili, costo di preparazione e memoria. |
| **Temi** | Come funziona in Apple Calm e Cozy? | Stesso cane semantico e comandi; Cozy cambia ambiente/presentazione. | Compatibilità, regioni e fallback dichiarati. |
| **Lifecycle** | Cosa succede con notte, menu, urgente e reboot? | Quiete separata dal tema; nessun replay di vecchie reazioni. | Scenari di sospensione/ripresa, errore asset e recupero. |

## 5. Esperienza quotidiana e navigazione proposta

**Presenza ambientale:** il cane riposa o osserva in uno spazio libero dichiarato. Gesti brevi e intervalli calmi; niente attraversamenti sopra ora, meteo, fonte o focus. Se lo spazio manca, una posa compatta prevista o sospensione. Il percorso fra due ancoraggi deve essere sicuro lungo tutta la traiettoria, non soltanto alle estremità.

**Vista Compagno:** cane più grande, ambiente essenziale e accesso alle azioni. Valutare una nuova famiglia del carosello contro un ingresso dal Menu; la famiglia è la proposta iniziale se l'interazione è una funzione usata spesso. Una sola vista nella prima versione evita pagine vuote; un'eventuale seconda scena deve aggiungere un'attività reale.

Nel percorso ordinario **4/6** conservano il cambio famiglia e **2/8** il cambio vista. **5** apre le azioni; nel pannello **2/8** selezionano, **5** conferma e **7** torna alla vista. **1 Home**, **3 Avvisi**, **9 Menu** conservano il significato corrente. L'ingresso nel pannello va trattato esplicitamente: oggi gli overlay sospendono SceneHost, quindi le azioni devono avere una scena dedicata oppure una policy di interazione limitata e dichiarata.

Prima proposta di interazioni e accudimento:

| Azione | Risposta osservabile | Punto da provare |
| --- | --- | --- |
| **Richiama** | Il cane si orienta e si avvicina al punto disponibile. | Si distingue da una semplice rotazione? La traiettoria rimane sicura? |
| **Accarezza** | Posa rilassata e breve risposta affettuosa. | Serve avvicinarsi prima? Il gesto è comprensibile senza mouse? |
| **Gioca** | Lancio breve della palla e ritorno, con una conclusione visibile. | Prima scena preparata; un minigioco con controllo diretto sarebbe un ampliamento da valutare. |
| **Dai da mangiare** | Si avvicina alla ciotola, mangia e torna tranquillo; la sazietà cambia. | Porzione, durata ed eventuale attesa devono evitare accumuli da pressioni ripetute. |
| **Riposo / Sveglia** | Si sistema nella cuccia oppure si risveglia; il recupero dell'energia segue le regole del tempo. | Sonno volontario/orario e sospensione tecnica devono rimanere distinti. |

L'azione produce subito un riscontro di accettazione, poi la clip; richieste ripetute hanno esito esplicito e non accumulano una coda illimitata. Un urgente interrompe subito l'interazione. Il ritorno non riavvia automaticamente il gioco interrotto.

La vista dovrebbe rendere visibili cane, stato corrente, pochi bisogni e avanzamento, senza diventare un pannello diagnostico. Valutare tre indicatori compatti con etichette comprensibili, azioni in un pannello dedicato e nessuna legenda permanente aggiunta alle viste ordinarie.

### 5.1 Bisogni e tempo

**Proposta iniziale da discutere:** tre bisogni nel profilo attivo richiesto. Scale, fasce e coefficienti candidati sono ora sviluppati nella [specifica funzionale](v010-companion-functional-spec.md), con valori alti positivi per Sazietà/Energia/Compagnia e desiderio di compagnia derivato. Non sono parametri finali.

| Bisogno | Evoluzione e cura | Effetto visibile |
| --- | --- | --- |
| **Sazietà** | Diminuisce con il tempo; aumenta dopo una porzione effettivamente consumata. | Interesse per la ciotola e una posa di richiesta discreta; niente valori decorativi. |
| **Energia** | Si consuma giocando; recupera durante il riposo. | Cane più calmo, gioco più breve, proposta di cuccia. Non è il timer di rendering. |
| **Voglia di compagnia** | Cresce senza interazioni; carezze e gioco la soddisfano. | Richiesta breve di attenzione e risposta più affettuosa. Non rappresenta il legame permanente. |

L'umore può essere derivato da questi bisogni e dall'azione corrente, senza una quarta barra indipendente. Le regole devono evitare stati impossibili e cicli senza uscita; essere stanco può suggerire riposo senza impedire per sempre l'interazione.

Analizzare **tempo reale**, **tempo di simulazione** e **tempo dell'animazione** separatamente. Proposta: durante il funzionamento usare tempo trascorso monotono; al recupero usare timestamp persistiti e un intervallo limitato. Un cambio dell'orologio, del fuso o un timestamp futuro non deve azzerare i bisogni né generare progressione. Giorno/notte usa Europe/Rome e orari del cane espliciti.

Per spegnimento o lunghe assenze confrontare congelamento e avanzamento limitato. La proposta consigliata è un recupero limitato: ritorno a bisogni ordinari gestibili, energia coerente con l'eventuale riposo, nessuna morte, malattia o perdita irreversibile introdotta nella prima versione. Il legame non diminuisce per assenza. Queste sono regole proposte, non comportamenti approvati o già implementati.

Le richieste del cane restano segnali discreti nella sua vista/presenza; proporre un ingresso in Avvisi soltanto se desiderato, con frequenza limitata. I bisogni ordinari non diventano urgenti e non competono con avvisi meteo o altri eventi prioritari.

### 5.2 Progressione utile

Separare **bisogni variabili** e **legame persistente**. Il legame cresce con interazioni completate e cura coerente, secondo regole dichiarate; una pressione rifiutata, un'azione interrotta o il semplice trascorrere del tempo non valgono automaticamente come esperienza.

Confrontare due forme: crescita per livelli con progressi visibili oppure traguardi di relazione senza numero dominante. Proposta: pochi traguardi leggibili che sbloccano saluti/varianti di gioco, una cuccia o un oggetto, rendendo osservabile l'avanzamento. Evitare punti senza effetti e scegliere se l'aspetto rimane stabile o cambia con una crescita cucciolo/adulto; quest'ultima moltiplica gli asset e va valutata esplicitamente.

Prevedere limiti ai guadagni da azioni ripetute, senza obbligare a sessioni quotidiane o introdurre streak nella prima versione. Sbloccare un oggetto richiede che esista una scena funzionante; un catalogo di premi futuri non costituisce progressione consegnata.

### 5.3 Salvataggio minimo della v0.11

Schema candidato versionato: identificativo del cane, eventuale nome/skin, bisogni, timestamp di aggiornamento, legame/traguardi/sblocchi e impostazioni. Lo stato temporaneo di una clip non deve essere l'unica rappresentazione salvata: riprendere da una posa semantica sicura evita dipendenze dal numero di frame.

Usare persistenza locale atomica/transactional coerente con lo store del prodotto, senza scritture per frame. Decidere checkpoint periodici e salvataggi ai cambi significativi; un'interazione deve applicare bisogni/progresso una sola volta. Cache/stato corrotti, storage non scrivibile e reset volontario richiedono esiti reali e recupero esplicito. L'UI non mostra «Salvato» prima della conferma.

Questa persistenza minima amplia la v0.11 rispetto alla sola scena del MasterPlan. La v0.12 potrà usare una storia più ricca per preferenze e pianificazione, con retention/cancellazione proprie; l'accudimento base deve rimanere utile offline anche senza quel planner.

## 6. Comportamento: farlo sembrare vivo con regole leggibili

Stati semantici candidati: **Riposo, Osserva, Attenzione, Avvicinamento, Interazione, Gioco, Sonno**. La sospensione tecnica rimane distinta dal Sonno: un cane nascosto per un urgente non si è addormentato.

Per ogni stato descrivere ingresso, clip, durata, interruzioni, completamento e fallback statico. Pose e locomozione rimangono separate: può essere attento mentre cammina. L'uscita dal renderer o il cambio tema non azzerano l'identità.

Ordine proposto delle priorità: **urgente/recovery → focus e spazio protetto → comando esplicito → evento qualificato → comportamento ambientale**. Gli eventi ordinari durante un'interazione possono essere scartati o conservati con scadenza breve; non devono interrompere ogni gesto.

La varietà può usare scelte pesate e un seed controllato per le prove. L'autorità resta nel controller: stesso contesto e seed producono lo stesso comportamento, senza affidare regole di prodotto alle transizioni casuali del renderer. Analizzare anticipazione, risposta e ritorno alla calma prima di aumentare il numero di clip.

La ricerca suggerisce una selezione leggera dei gesti con priorità, compatibilità, inerzia e pause, sviluppata nella specifica §9.1. Il temperamento candidato è stabile; l'umore varia con i bisogni. La progressione dovrebbe aggiungere saluti/risposte/oggetti realmente visibili. Sono applicazioni progettuali degli studi, non efficacia già dimostrata per il nostro cane.

## 7. Reazioni ai moduli

| Ingresso | Reazione candidata | Condizione e limite |
| --- | --- | --- |
| Apertura della vista Compagno | Saluto/attenzione. | È un'interazione con la dashboard; non prova presenza fisica riconosciuta. Evitare il saluto a ogni riapertura rapida. |
| Meteo corrente | Breve scena coerente, per esempio osservare la pioggia. | Dato recente e stato normalizzato; cache precedente non presentata come condizione attuale. Un avviso meteo mantiene precedenza. |
| Sport | Attenzione o piccola esultanza. | Solo evento consentito dalla capacità della fonte. Gol/VAR non qualificati non diventano confermati tramite l'animazione. |
| Gioco/Piloti | Gesto celebrativo per un risultato verificato. | Fine/progresso realmente confermati; non a ogni generazione o snapshot. Rispetto del carico e della navigazione del Gioco. |
| Avviso ordinario | Orientarsi brevemente verso il banner, se c'è spazio. | Non marca letto, non modifica consegna o durata; identità/revisione/scadenza impediscono replay. |
| Urgente | Sospensione immediata e spazio libero. | Nessuna attesa per finire una clip; ripresa calma dopo la chiusura. |
| Rete e Casa | Nessuna reazione nella proposta iniziale. | Presenza LAN ambigua non significa «sei tornato»; nuove integrazioni Casa non rientrano nel lavoro già concordato. |

Il compagno consuma eventi normalizzati esistenti: non aggiunge chiamate API per animarsi. Definire una whitelist e non abilitare reazioni per tutti i moduli automaticamente. Un refresh identico, un reboot o una riapertura del banner non devono riprodurre la stessa festa.

Per gli avvisi richiesti dall'utente distinguere **contenuto** e **priorità**: un risultato sportivo può avere una risposta allegra, un avviso meteo una posa attenta, una soglia Account uno sguardo verso il banner. La matrice definitiva va costruita sulle categorie effettivamente consegnate. Un urgente nasconde/sospende subito il cane; non richiede prima una reazione teatrale. In Reduced/Off una posa statica può mantenere il significato, lasciando il testo dell'avviso come fonte dell'informazione.

## 8. Asset, renderer e costo

**Direzione tecnica di studio aggiornata:** pipeline 2D ibrida, con asset AI, parti articolate per gesti continui e brevi clip/pose per azioni che cambiano la silhouette. Il requisito di produzione interamente in questa chat è descritto nella sezione 8.1. Verificare la soluzione sulla stessa breve sequenza: riposo → richiamo → passo → risposta → riposo.

| Soluzione | Interesse per il progetto | Incertezza da risolvere |
| --- | --- | --- |
| **Sprite raster locali** | Identità precisa e animazioni curate; candidato se si sceglie pixel art. | Frame coerenti, atlas/padding, scala, interruzioni, memoria decodificata e preparazione. |
| **Rig 2D con parti QML/immagini** | Varianti di sguardo, orecchie e coda con poche risorse; candidato per illustrazione morbida. | Qualità dei movimenti articolati, nodi/overdraw e mantenimento della silhouette. |
| **Adapter Rive/Lottie, video o 3D** | Da considerare solo se lo stile o le scene lo richiedono. | Supporto effettivo, dipendenze, licenze/toolchain e costo sulla board ancora da qualificare. |

Qt 6.8 offre [AnimatedSprite](https://doc.qt.io/qt-6.8/qml-qtquick-animatedsprite.html) per una clip raster controllabile, con pause, loop e segnale di completamento naturale. Il completamento non viene emesso semplicemente fermando `running`: l'interruzione deve avere un esito gestito dal controller. Per pixel art, interpolazione e smoothing vanno scelti deliberatamente.

[SpriteSequence](https://doc.qt.io/qt-6.8/qml-qtquick-spritesequence.html) gestisce più animazioni; `goalSprite` segue il percorso di transizioni, mentre `jumpTo` salta subito alla clip richiesta. È un'opzione da confrontare, non la macchina a stati del prodotto già scelta.

Set iniziale candidato: posa calma, sguardo, seduto/attento, passo, risposta alla carezza, gioco breve, sonno e risveglio. Quantità di frame e direzioni dipendono dalle traiettorie approvate; non serve produrre un catalogo enorme prima di verificare una sequenza convincente. Conservare silhouette, proporzioni, punto di appoggio e palette fra le clip; disponibilità e diritti degli asset devono essere documentati.

Distinguere **frequenza delle clip**, **rendering della UI** e **refresh 60 Hz del display**. Una clip illustrata a 8–12 frame/s è un'ipotesi artistica da confrontare, non una prova di prestazioni a 60 FPS. Come ordine di grandezza, 64 frame 128×128 RGBA non compressi sono **4 MiB di pixel**, esclusi padding, copie e altre risorse: il peso del PNG non è la memoria runtime.

La [guida prestazioni Qt Quick 6.8](https://doc.qt.io/qt-6.8/qtquick-performance.html) raccomanda profilazione e attenzione a immagini, binding e lavoro per frame. Per questo progetto si propone di caricare prima le clip della sequenza attiva, mantenere un fallback statico e fermare animazioni/timer inutili quando nascosti. Il costo deve includere il cambio tema, che può mantenere temporaneamente visuali vecchi e candidati.

### 8.1 Produzione di asset e animazioni tramite AI in questa chat

**Requisito aggiunto dall'utente:** tutti gli asset e le animazioni vengono realizzati tramite AI in questa chat. Scegliere la tecnica anche per riproducibilità del personaggio, possibilità di correzione e strumenti effettivamente disponibili, oltre alle prestazioni sulla board. Non assumere un modello 3D, uno scheletro o un progetto di animazione esportabile a partire dalle sole immagini dei concept.

**Scelta consigliata per questa fase: personaggio 2D/2.5D raster a parti, animazione procedurale Qt e piccole sequenze dedicate.** L'AI genera il disegno e le pose usando un riferimento approvato; l'assistente crea in questa chat anche il rig, il codice delle animazioni e le regole di transizione. La creazione AI dell'animazione comprende quindi l'autoria del codice QML/C++, oltre alla generazione delle immagini. A runtime le animazioni sono locali e controllate, senza generazione online.

| Elemento | Come produrlo in chat | Come riprodurlo |
| --- | --- | --- |
| **Identità del cane** | Un riferimento approvato e poche viste canoniche, con scheda di proporzioni, colori e segni distintivi. | Asset condivisi da tutti gli stati, senza un cane diverso per ogni azione. |
| **Respiro, sguardo, occhi, orecchie e coda** | Parti/varianti con sfondo realmente trasparente, generate o corrette a partire dal riferimento. | Trasformazioni, sostituzioni di posa e curve di movimento in Qt; possibilità di variazioni e interruzioni. |
| **Sedersi, alzarsi, camminare, mangiare e giocare** | Pose o piccole sequenze curate per l'azione; rig dove mantiene un gesto convincente. | Clip locali con tempi, contatto delle zampe, completamento e raccordo allo stato successivo. |
| **Ambiente, cuccia, ciotola e oggetti sbloccati** | Asset separati e coerenti con la palette; scene giorno/notte. | Composizione QML con carico e aree protette dichiarati. |
| **Animazione e controllo** | Codice e dati di animazione scritti dall'assistente; anteprime per verificare il risultato. | Qt Quick, con eventuale componente C++ motivato da qualità/performance. |

Per i gesti semplici questa direzione conserva le stesse parti durante il movimento e permette di cambiare intensità/durata senza rigenerare una lunga sequenza. Per i gesti articolati verificare che il rig non dia un effetto di sagoma rigida: rotazioni di parti da sole non dimostrano una camminata naturale. Una clip breve o una deformazione specializzata può essere necessaria.

**Ordine di produzione proposto:**

1. Lo stile A è scelto: approvare il personaggio master e costruire una resa illustrata a strati con giunture/ombre coerenti. B/C/D restano confronti visivi storici, non direzioni da adottare implicitamente.
2. Generare parti/pose per un solo piccolo campione, mantenendo riferimento, vista, palette, scala e appoggio. Usare imagegen per generazione e correzione visiva degli asset raster, con trasparenza quando richiesta; nessuna promessa di suddivisione perfetta al primo output.
3. Definire pivot, sovrapposizioni, scala e mapping semantico. Scrivere respiro, battito degli occhi, attenzione e scodinzolio come prima sequenza di animazione. Qt offre animazioni delle proprietà; questi gesti non richiedono una nuova immagine AI per ogni frame. [PropertyAnimation Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-propertyanimation.html).
4. Verificare in anteprima identità, bordi/trasparenza, giunture, tempi, ritorno alla posa calma e interruzione. Produrre poi una singola azione articolata, per esempio passo o gioco, prima di moltiplicare le clip.
5. Qualificare dimensioni, preparazione, memoria e fluidità sulla board quando sarà autorizzato il prototipo. Solo dopo estendere il catalogo a bisogni, progressione, oggetti e avvisi.

I criteri di accettazione della produzione AI includono stessa anatomia e segni distintivi tra pose, assenza di salti di scala/posizione o sfarfallii, loop senza scatti, appoggio corretto e asset realmente utilizzabili nel renderer. La generazione di un'immagine piacevole non chiude questi gate. Anche una sprite sheet generata va controllata per numero/dimensioni delle celle e coerenza prima di usarla in AnimatedSprite.

Una clip video generata tramite strumenti disponibili in chat resta un'alternativa per azioni specifiche da confrontare: fondo/alpha, identità temporale, loop, decoding e interruzioni vanno verificati. Non è la dipendenza iniziale del comportamento del cane. La scelta ibrida offre un percorso di produzione più controllabile per questo progetto; è una valutazione progettuale, non un benchmark già acquisito o una garanzia sulle uscite AI.

Conservare per ogni asset riferimento, prompt, versione approvata, dimensioni, pivot, azioni compatibili e anteprima. Le immagini dei quattro concept rimangono esempi di stile; non sono state trasformate automaticamente in parti o animazioni di produzione.

## 9. Architettura candidata e temi

Flusso proposto: **comandi/eventi normalizzati → servizio Compagno Python con store locale → snapshot semantico → SceneHost/render adapter QML**. Python decide stato, bisogni, progresso, priorità, tempi e configurazione; QML esegue clip e spostamenti senza aggiornamenti Python per ogni frame. Completamenti/interruzioni tornano al controller con un identificatore dell'azione: un callback vecchio non chiude quella nuova.

Un solo stato di prodotto alimenta presenza ambientale e vista dedicata. Evitare due cani indipendenti: definire chi possiede la clip attiva durante passaggi, pannelli e cambi tema. Il bisogno di un processo dedicato va dimostrato da lavoro costoso; la proposta locale a stati non lo richiede di principio e non richiede NPU.

Il contratto corrente della scena non va forzato tramite accesso ai controller privati. Per la vista richiesta, progettare contesto, azioni tipizzate e stato degli esiti; nomi delle superfici e futura minor API rimangono da definire. Includere Base/Functional, Apple Calm o fallback, corpus e kit della nuova release.

**Cozy** propone ambiente e presentazione coerenti con il cane; non abilita di nascosto il modulo. Il compagno deve poter funzionare anche con Apple Calm. Separare quattro ingressi: palette giorno/notte, silenzio Avvisi, Normal/Reduced/Off e orari di riposo del cane. In Reduced limitare movimento; in Off mantenere pose statiche e azioni comprensibili. La scena notturna può mostrare il cane addormentato anche con notifiche silenziose, se abilitato.

### 9.1 Linguaggi e utilizzo di CPU/GPU

**Requisito aggiunto dall'utente:** scegliere il linguaggio e il percorso più adatti alle prestazioni, sfruttando CPU e GPU. La proposta del controller Python nella sezione precedente è la base di confronto, non un vincolo che esclude un componente nativo del Compagno.

Per lo stack attuale la direzione consigliata è **Qt Quick/QML per la scena, C++ per eventuali componenti intensivi o specializzati e Python per i servizi già esistenti e la logica a bassa frequenza**. La scelta del controller definitivo del Compagno deve essere motivata dal carico reale e dall'integrazione, senza riscrivere i provider per ottenere un beneficio grafico non dimostrato.

| Parte | Percorso candidato | Criterio di scelta |
| --- | --- | --- |
| **Composizione, sprite e trasformazioni** | QML/Qt Quick e renderer nativo Qt. | Asset residenti durante la sequenza, nodi/draw call contenuti e nessun callback Python per frame. |
| **Rig articolato, geometria o calcoli frequenti complessi** | Componente C++ integrato nel scene graph Qt, se necessario. | Confronto di correttezza, tempo CPU per frame, costo di sincronizzazione e beneficio completo sulla board. |
| **Bisogni, traguardi e macchina a stati** | Controller Python esistente come baseline; controller C++ come candidato quando il lavoro o l'integrazione lo giustificano. | Aggiornamenti discreti; un numero basso di timer e operazioni non dimostra un collo di bottiglia Python. |
| **Acquisizione dati e persistenza** | Servizi Python esistenti e I/O fuori dalla GUI. | Non bloccare input/rendering; scritture confermate e snapshot limitati. |
| **Effetti grafici specifici** | Shader GPU tramite Qt, soltanto se utili alla grafica scelta. | Compilazione/preparazione, compatibilità PowerVR, overdraw e costo misurati. |

Qt Quick costruisce un scene graph renderizzato tramite API grafiche, con ottimizzazioni come batching; consente anche estensioni native C++ e shader. Non coincide con un disegno Python per ogni fotogramma. Il render loop può usare un thread dedicato secondo piattaforma/driver: il comportamento effettivo si verifica, non si assume dalla sola architettura. [Scene graph Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html).

L'obiettivo durante l'animazione è un budget di circa **16,67 ms per fotogramma a 60 FPS**, da valutare sull'intero percorso. Un renderer C++ non risolve da solo texture troppo grandi, caricamenti durante la clip, trasparenze sovrapposte, sincronizzazioni o lavoro sulla GUI. Analizzare separatamente CPU, GPU, preparazione asset e intervalli dei frame; una media vicina a 60 non prova assenza di scatti. [Guida prestazioni Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-performance.html).

Distribuire lavoro sui core quando ci sono attività indipendenti che ne beneficiano, senza creare un thread per ogni bisogno o cercare di saturare la macchina. Per lo stile Soft 2.5D resta aperto il confronto fra sequenze preparate e un rig/runtime: l'immagine del concept non richiede 3D in tempo reale. Il caso di prova deve includere cane, interazioni, banner e carichi concomitanti realmente consentiti. Nessun cambio di linguaggio o prestazione viene dichiarato implementato in questa revisione.

## 10. Percorso di studio e gate futuri

Le fasi C0–C2 costituiscono il lavoro di analisi. C3–C5 sono successive attività di implementazione/qualifica, da avviare dopo accordo sul perimetro.

| Fase | Risultato reviewabile | Criterio per avanzare |
| --- | --- | --- |
| **C0 · Prodotto** | Ruolo acquisito dalla risposta dell'utente; scenari, identità e lista incluso/rinviato da completare. | Definite regole di accudimento/progressione e interazioni principali. |
| **C1 · UX e comportamento** | Layout 960×640, mappa tasti, stati, bisogni/tempo, schema persistente e matrice reazioni. | Dati/focus protetti; percorsi e interruzioni completi; recupero del progresso e nessuna fonte ambigua. |
| **C2 · Scelta grafica/tecnica** | Pipeline AI ibrida proposta; personaggio master, campione parti/pose, rig/clip e budget asset da progettare. | Produzione fattibile interamente in chat, identità e raccordi coerenti; criteri osservabili per la prova, senza promettere prestazioni non misurate. |
| **C3 · Nucleo locale** | Controller, accudimento/progresso persistenti, azioni, prima scena, fallback e contratti. | Funziona offline, una sola identità, nessuna coda incontrollata o replay; reboot non perde il cane. |
| **C4 · Integrazione e temi** | Reazioni selezionate, scene giorno/notte, Cozy e compatibilità. | Urgenti/focus/lifecycle prevalgono; eventi freschi e deduplicati; cambio tema recuperabile. |
| **C5 · Qualifica Orange Pi** | Evidenze PC/board, input fisico, frame pacing, manifest/rollback. | Azioni leggibili a 50–60 cm; carico e recovery misurati nella build consegnata. |

Gate pertinenti alla nuova feature:

- **G1 · Esperienza:** azioni riconoscibili, varietà sufficiente e intensità regolabile; confronto d'uso fra presenza discreta e interazione dedicata. Asset AI con identità/anatomia coerenti, trasparenza corretta e loop/raccordi senza salti; animazioni articolate convincenti prima di ampliare il catalogo.
- **G2 · Spazio/input:** Home con/senza evento, viste dense, testi grandi, regioni assenti, pannelli e tastierino fisico; ritorni senza perdita del focus.
- **G3 · Stato/eventi:** richieste ripetute, annullamento, evento scaduto/rettificato, refresh identico e replay dopo reboot; esiti veritieri. Bisogni/progresso applicati una sola volta, storage non scrivibile/corrotto, assenza prolungata e cambi dell'orologio gestiti senza guadagni o perdite inventati.
- **G4 · Policy/lifecycle:** giorno/notte, quiete, Reduced/Off, disabilitazione, asset mancante/corrotto, cambio tema e urgente a metà azione.
- **G5 · Prestazioni:** costo del cane isolato e delle combinazioni realmente consentite, inclusi cambi tema e attività del Gioco; risposta/input e frame pacing distinti. CPU/RAM diagnostiche, nessuna soglia arbitraria derivata dai prototipi storici.
- **G6 · Consegna:** preferenze preservate, backup/manifest, fallback e recupero offline; reboot verificato sulla versione soltanto quando effettivamente eseguito.

## 11. Decisioni da prendere per prime

1. **Bisogni e progressione:** il requisito è acquisito; scegliere bisogni, effetti, tempo durante assenza e traguardi/sblocchi. Decidere eventuale crescita cucciolo/adulto.
2. **Forma dell'interazione:** presenza nelle viste più schermata propria sono richieste; definire azioni di cura e scelta fra scena preparata e minigioco per Gioca.
3. **Identità visiva:** costruire/approvare il master nello stile A scelto, con parti/pose e raccordi per le animazioni nel layout reale.

Dopo queste decisioni, approfondire C1 con quattro scenari: consultazione tranquilla della Home, cura/gioco con avanzamento persistente, arrivo di un urgente durante il gioco, ritorno dopo spegnimento o lunga assenza. Questi scenari fanno emergere requisiti concreti prima di aumentare asset, tecnologie o capacità AI.

## 12. Evidenze e limiti di questa revisione

Analisi del MasterPlan e dei sorgenti locali indicati; integrate fonti online primarie nel [registro della ricerca](v010-companion-online-research.md), con limiti e studi applicativi futuri. Generati quattro concept statici di confronto, con stile A selezionato; nessun asset/rig di produzione, prototipo eseguito, installazione, reboot o benchmark del cane. Questo file accompagna il MasterPlan e non promuove la v0.11 a implementata. Le modifiche locali del Gioco e del MasterPlan già presenti nel checkout non sono state alterate da questa analisi.
