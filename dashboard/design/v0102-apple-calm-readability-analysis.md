# v0.10.2 · Apple Calm: leggibilità, notifiche e movimento

29 ottobre 2026 · revisione di analisi 3 · preparazione all’attuazione completata.

La direzione consigliata è **Apple Calm essenziale**: mantenere palette, font e navigazione della dashboard, dare alle notifiche una forma più curata e una gerarchia immediata, aumentare la leggibilità delle viste e usare animazioni brevi. Il riferimento iOS riguarda composizione, coerenza e comportamento; le dimensioni vanno progettate per il display SmartPC e il tastierino.

**Stato:** analisi dei sorgenti, ricerche e concept interattivo con dati sintetici. Nessuna modifica a runtime, bundle attivo, versione, preferenze o board. Il MasterPlan ha già modifiche estranee in corso e non viene riscritto da questa analisi. Non è stata creata né installata una nuova release.

**Seconda passata:** aggiunto lo [studio di rifinitura grafica](v0102-apple-calm-graphic-refinement-study.md): card e superfici aperte, grafici, timing F1, Casa, Account, Menu e qualità di testo/icone. Confermato dall’utente il display **3,5″ orizzontale**; le misure delle tavole sono espresse in larghezza × altezza, **960 × 640**.

**Consolidamento:** completati l’[audit dei dati](v0102-apple-calm-data-audit.md) e il [piano completo di attuazione](v0102-apple-calm-implementation-plan.md), ora riferimento operativo. Tre famiglie di difetti riprodotti entrano prima del restyling; la proposta Meteo è allineata alle tre previsioni giornaliere disponibili. L’analisi è pronta, il codice e la consegna rimangono da eseguire.

## 1. Baseline verificata e limiti

Il checkout dichiara `0.10.2-rc.4`; il bundle sorgente Apple Calm è `1.6.5`. Il MasterPlan revisione 3.36 e il [report grafico rc.4](v010-aquarium-graphics-fix-report.md) documentano l’ultima consegna con Acquario 3D, API 2.14 e ponte EGL/PowerVR. Sono evidenze di quella consegna, non un nuovo controllo dello stato corrente del servizio.

L’analisi legge i file attuali e conserva gli hash in [source-audit.json](evidence/v0102-apple-calm-readability-2026-10-29/source-audit.json). Il checkout contiene già lavoro Gioco/Acquario e documentazione modificati: l’attuazione futura deve partire dai byte della baseline installata e includere soltanto il delta approvato.

| Riscontro nei sorgenti | Conseguenza per la proposta |
| --- | --- |
| `Notice.qml` concentra small, large, inbox, detail e urgent. Banner piccolo: titolo 26 px, corpo 20 px su una riga; inbox: righe da 90 px, titolo 24/corpo 20. | Separare l’anatomia dei componenti; recuperare spazio per fonte/orario e rendere esplicito lo stato. |
| L’inbox identifica il non letto con `●`, ma non mostra per riga categoria, orario o provenienza; il dettaglio usa anche fonte/validità. | Migliorare il riconoscimento senza obbligare ad aprire ogni voce. |
| `NotificationContext.qml` assegna icone specifiche a meteo e account; le altre categorie condividono la campana. | Aggiungere una mappa semantica per Calcio, Motorsport, Rete e Sistema. |
| `EventService` espone il banner per 8 s, avviati dopo acknowledgement di presentazione; `EventEngine` distingue presentato, letto, revocato, scaduto e fuori tempo. | Preservare la macchina degli eventi. La nuova grafica non deve trasformare un banner mostrato in un avviso letto. |
| La visualizzazione è già differita nelle schermate di configurazione e separata dagli urgenti. | Conservare queste regole; verificare anche ritorni, quiete e recupero. |
| La campana/badge attuale è una superficie separata, visibile in Home con non letti e senza banner. `ShellContext.UiStatus` non offre un contatore non letti. | La campana nell’header di tutti i concept è una proposta che richiede integrazione pubblica; non è un semplice cambio di colore. |
| `MotionController` e ricette fade/slide usano `NumberAnimation`; navigazione Apple 100 ms, banner 120 ms. | Qt Quick disegna già con la GPU. Il possibile uso degli Animator richiede una prova distinta. |
| `OutlineIcon.qml` usa un atlante locale e ID semantici; Cantarell e Liberation Sans sono già distribuiti. | Estendere il sistema attuale, senza introdurre icone emoji, dipendenze online o un secondo catalogo runtime. |
| `occupiedRegions` viene comunicato a `SceneHost`. | Questo protegge la scena ambientale; non ridimensiona automaticamente tutte le viste sotto un banner. La riserva di spazio va progettata nel layout. |

Riferimenti locali: [Notice.qml](../../theme-projects/apple-calm/bundle/qml/Notice.qml), [Shell.qml](../../theme-projects/apple-calm/bundle/qml/Shell.qml), [NotificationHost.qml](../components/NotificationHost.qml), [NotificationContext.qml](../components/NotificationContext.qml), [events.py](../events.py), [event_core.py](../event_core.py), [contratti pubblici](../theme-api/contexts.json).

Il tentativo di catturare la baseline attuale nel banco PC non è completato: l’interprete predefinito non risolveva PySide6; usando le librerie già presenti il processo ha rilevato Qt 6.11.2, mentre il target documentato è 6.8.2. Il catalogo ha correttamente rifiutato l’attivazione del bundle senza preflight. Non è stato falsificato un esito positivo né aggirata la guardia. Il teardown diagnostico ha inoltre prodotto due messaggi `ThemeChooser.qml:60`, registrati nel JSON. Non sono evidenza di una regressione del servizio in produzione.

Le [vecchie catture fixture Apple Calm](../../theme-projects/apple-calm/evidence/optimization-main-pc-release/alerts.inbox--default.png) aiutano a riconoscere il linguaggio precedente, ma non sono schermate correnti della board. Tutte le nuove schermate sotto sono **proposte**, renderizzate nel browser.

## 2. Ricerca: cosa applicare e cosa verificare sul pannello

| Fonte consultata | Risultato pertinente | Applicazione proposta e limite |
| --- | --- | --- |
| [Apple HIG · Notifications](https://developer.apple.com/design/human-interface-guidelines/notifications) | Informazione breve, utile a colpo d’occhio; evitare duplicati; badge riferito ai non letti. | Categoria/ora, titolo e una frase; una card per evento. Il dettaglio conserva l’informazione completa. La dashboard mantiene le sue regole di priorità. |
| [Apple HIG · Materials](https://developer.apple.com/design/human-interface-guidelines/materials) | Materiali per distinguere livelli; Liquid Glass usato con parsimonia, principalmente nei controlli e nella navigazione. | Superfici piene, angoli morbidi e ombra lieve danno già separazione. Il vetro dinamico non è un requisito per ottenere un risultato coerente. |
| [Apple HIG · Menus, Icons](https://developer.apple.com/design/human-interface-guidelines/menus?changes=_4_1_8) | Icone consistenti, usate dove rendono riconoscibile l’azione; evitare simboli senza un significato chiaro. | Icona per dominio e azione; testo sempre accanto agli stati essenziali. Nessuna icona decorativa ripetuta su ogni valore. |
| [Apple · Reduced Motion](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria) | Movimento e simulazione della profondità possono disturbare; offrire alternative appropriate. | Normale/Ridotto/Off; niente rimbalzi, lampeggiamenti o blur animato nella proposta di base. |
| [W3C · WCAG 2.2](https://www.w3.org/TR/WCAG22/#contrast-minimum) | Contrasto minimo 4,5:1 per testo normale; 3:1 per testo grande secondo la definizione WCAG. | Usare 4,5:1 per tutto il testo funzionale, anche secondario; verificare il colore composto sullo sfondo effettivo. È un riferimento di progetto, non una dichiarazione di conformità del kiosk. |
| [Dobres, Chahine, Reimer · Applied Ergonomics, 2017](https://jdobr.es/pdf/Dobres-etal-2017-Ambient.pdf) | Studio sperimentale: dimensione, polarità e illuminazione influenzano la lettura rapida; il testo piccolo chiaro su fondo scuro risultava penalizzato soprattutto al buio. | Provare giorno e notte sul display reale. Evitare di considerare il tema scuro automaticamente più leggibile. Studio su parole e condizioni controllate: non determina il font ottimale per SmartPC. |
| [Mark, Gudith, Klocke · CHI 2008](https://www.ics.uci.edu/~gmark/chi08-mark.pdf) | Le interruzioni nello studio aumentavano stress, frustrazione e sforzo, anche quando il compito veniva completato più rapidamente. | Limitare interruzioni e animazioni ripetute. Il lavoro studiato è diverso dalla consultazione di questa dashboard: nessuna percentuale di beneficio viene trasferita al prodotto. |
| [Iqbal e Bailey · CHI 2008](https://doi.org/10.1145/1357054.1357070) | La gestione delle notifiche ai punti di interruzione del compito riduceva frustrazione e tempi di reazione nello studio. | Conservare il rinvio durante modifica/impostazioni. È una motivazione per la policy, non una latenza dimostrata sul nostro sistema. |
| [Qt 6.8 · Animator](https://doc.qt.io/qt-6.8/qml-qtquick-animator.html) | Gli Animator agiscono sul scene graph; il valore QML della proprietà si aggiorna a fine animazione. | Candidato per un wrapper visuale isolato. Prima verificare acknowledgement, trace, hit test, interruzione e posizione finale. |
| [Qt 6.8 · MultiEffect](https://doc.qt.io/qt-6.8/qml-qtquick-effects-multieffect.html#performance), [QML performance](https://doc.qt.io/qt-6.8/qtquick-performance.html) | Blur e ombre sono effetti costosi; contano area elaborata, shader e sorgenti in movimento. | Base senza blur; ombra statica locale. Un eventuale effetto si misura sul carico reale e si disabilita quando non visibile. |

Le durate e le misure proposte nelle sezioni successive sono scelte di progetto da provare. Non sono numeri prescritti da questi studi.

## 3. Leggibilità a 960 × 640

Il profilo nel MasterPlan è **3,5″, 3:2, 960 × 640**, circa 74 × 49 mm e 330 ppi se la diagonale nominale coincide con l’area attiva. In questo caso 24 pixel occupano circa 1,85 mm di corpo tipografico: l’altezza effettiva delle lettere è inferiore e dipende dal font. Copiare i point iPhone in pixel QML sarebbe scorretto.

| Elemento | Candidato iniziale, pixel logici al 100% |
| --- | --- |
| Titolo di vista | 32–36, peso 600 |
| Titolo di notifica | 28–32, peso 600 |
| Corpo di notifica e dato descrittivo | 24–26, peso 400 |
| Fonte, ora, stato | 22–24; se la lettura fisica lo richiede, portare a 24–26 e mostrare meno righe |
| Numero principale | 56–80; orologio Home 120–140 |
| Icona di categoria | 30–36 dentro un contenitore da 48–56 |
| Spaziature | passo 8, padding 20–24, raggi 22–28 |

Cantarell rimane il font UI, Liberation Sans quello numerico. Niente pesi ultralight, testo grigio pallido o testo animato tramite zoom. I numeri mantengono colonne e cifre stabili.

La scala 1,1 deve ricalcolare la capacità delle liste e l’altezza delle card. Quando il contenuto non entra: meno righe per pagina e dettaglio completo, senza ridurre il font. Il titolo può essere abbreviato nella lista, ma severità, fonte, scadenza e rettifiche devono restare recuperabili e non ambigue.

## 4. Notifiche proposte

### Anatomia comune

Icona semantica a sinistra; categoria/fonte e ora nella prima riga; titolo riconoscibile; una frase di contesto; eventuale accesso con il tasto esistente. Stesso ordine nel banner, nella lista e nel dettaglio. L’icona indica il dominio; testo e colore comunicano insieme priorità e disponibilità.

**Calm essenziale, consigliato:** banner inferiore a larghezza quasi piena, margini 24–32, altezza indicativa 140–152 px. La Home del concept riserva questa fascia e mantiene liberi orologio e meteo. Per altre viste la riserva non è ancora implementata: serve un contratto di spazio transitorio o una composizione compatibile, senza spostamenti continui del contenuto.

**Calm laterale, alternativa:** pannello destro di circa 390 px e contenuto a sinistra. Consente più testo e una notifica più persistente, ma richiede una composizione specifica per ogni vista. È una possibile modalità di consultazione dedicata, non la scelta iniziale per tutte le pagine.

Il banner ordinario mantiene gli **8 secondi** attuali come primo candidato. Il timer resta nel backend, separato dall’animazione. L’eventuale modifica del tempo di lettura si decide dopo prova fisica; l’informazione rimane nel Centro avvisi. Nessuna barra di avanzamento richiede ridisegni continui per il solo conto alla rovescia.

### Tre livelli di presentazione

| Livello | Presentazione | Comportamento |
| --- | --- | --- |
| Stato informativo | Aggiornamento nella vista e voce in elenco; contatore quando appropriato. | Nessuna comparsa ripetuta per lo stesso dato. |
| Avviso ordinario/tempestivo | Un banner alla volta; gli altri rimangono in coda/elenco. | Non prende il focus; niente cambio vista automatico. Durante configurazione resta differito. |
| Urgente del sistema | Vista immediata, fonte, area/validità e azioni esistenti. | Prevale su banner, Acquario e scene; non aspetta l’animazione o il caricamento del tema. Conserva il fallback compilato. |

Questi sono livelli di presentazione: non cambiano automaticamente i valori `priority`/`notificationRank` né attribuiscono priorità critica a nuovi provider.

### Centro avvisi e dettaglio

Tre card per pagina al 100%, con capacità calcolata sul contenuto effettivo e sul 110%; focus evidente, icona, categoria, ora e stato «non letto». Il numero nell’header conta gli eventi non letti, non i gruppi visuali o i risultati sportivi. Aprire l’elenco non legge automaticamente tutte le voci. Aprire un dettaglio usa il comportamento di lettura attuale. Ritorno e selezione rimangono legati all’ID.

Il dettaglio mostra contenuto completo, fonte, emissione, validità e stato. Non presenta un punteggio segnalato come «gol confermato». `issuedAt` e `expiresAt` sono già nel DTO pubblico; «ricevuto alle» richiederebbe un timestamp distinto, da non inventare.

Le tavole «senza rete» e «rettificato» illustrano informazioni desiderate. Oggi il DTO pubblico `NotificationEvent` non espone esplicitamente `cancelled`, `expired`, `deliveryState`, `groupKey` e la storia delle revisioni, benché parti di questi dati esistano nell’engine privato. La loro presentazione strutturata richiede un’aggiunta compatibile all’API e alle fixture. Una sola stringa o il colore non sostituiscono quel contratto.

### Affidabilità, raggruppamento e recupero

1. Evento identificato da fonte, ID e revisione; nessun dedup ricavato dal titolo localizzato.
2. Rettifica/VAR aggiorna l’evento o lo collega al precedente e ne conserva la storia; il testo precedente non rimane un fatto corrente.
3. Raggruppamento proposto solo per stessa partita/sessione/dispositivo e finestra esplicita. Prima si valida nel backend; la prima attuazione può mantenere una riga per evento.
4. Eventi distinti non vengono persi dentro un gruppo; urgenti e variazioni di severità restano riconoscibili.
5. Offline mostra età e ultimo dato conservato. Alla riconnessione si riconcilia senza riprodurre in massa i banner scaduti.
6. Non letto, presentato, revocato, scaduto e rinviato rimangono stati distinti. La comparsa animata non è un acknowledgement di lettura.

La copertura rimane quella già prevista dal prodotto: tutta la Serie A, Fantacalcio solo quando consultato, Casa esclusa dalle nuove notifiche, nessun nuovo servizio a pagamento. Questa analisi non modifica acquisizione o chiamate API e non qualifica eventi reali gol/VAR o latenza live.

### Tastierino e interazione

Conservare `3 Avvisi`, `2/8 Scorri`, `5 Dettagli`, `7 Indietro`, `1 Home`, `4 Recenti/Storico`. Il banner non ridefinisce `5` mentre si sta usando una vista. Non introdurre swipe, pressione lunga o un comando di cancellazione globale come requisito.

La campana persistente dell’header richiede spazio verificato con titolo, ora, stato Quiete/Ripristino e puntini. Il concept omette alcuni di questi stati simultanei: la loro collisione è un gate dell’attuazione, non già risolta dalla tavola.

## 5. Miglioramenti per vista e icone

| Vista | Intervento proposto | Icone e dato da rispettare |
| --- | --- | --- |
| Oggi | Orologio dominante, data leggibile, meteo compatto, fascia libera per il banner. | Ora, condizione meteo, campana. I dati demo delle tavole non sono osservazioni attuali. |
| Meteo | Condizione e temperatura principali; separare percepita, umidità, vento e probabilità pioggia; fonte in una riga dedicata. | Termometro, goccia, vento, ombrello. Probabilità non equivale a quantità di pioggia; sole/luna solo con stato astronomico disponibile. |
| Calcio | Squadre e risultato allineati, stato partita separato dall’ora di aggiornamento; meno etichette ripetute. | `sport.football`, calendario, preferito. Gol/VAR solo con evidenza appropriata; il concept usa «segnalato dalla fonte». |
| F1/MotoGP | Colonne stabili per posizione, nome e distacco; evidenziare solo cambi importanti; dettaglio per messaggi lunghi. | `sport.f1`, `sport.motogp`, bandiera. Nessuna luce «live» dedotta da un timer locale. Tavola specifica rinviata alla seconda passata. |
| Rete | Distinguere raggiungibilità del router, stato WAN, traffico e voci registrate. | `network.router`, `network.wifi`, download/upload, storico. Una voce router non prova presenza o copertura. |
| Casa | Valore principale e unità vicini, disponibile/precedente distinguibili, nome dispositivo leggibile. | Icone esistenti temperatura, luce, presa e movimento. Nessuna nuova automazione o notifica Casa. Tavola specifica successiva. |
| Account | Percentuale residua, finestra e orario di aggiornamento in ordine; dati salvati etichettati. | Account, orologio, avviso. Niente conferma positiva da una sessione o uno snapshot vecchi. |
| Impostazioni | Icona per sezione, titolo/descrizione/valore distinti, focus coerente e meno righe quando serve. | Display, notifiche, quiete, moduli, fonti. Modifica/Annulla e preferenze conservati. |
| Gioco e Acquario | Coerenza di header, menu e notifiche; preservare arena, pesci, controlli e dati. | Icone esistenti Gioco/Acquario. Nessuna nuova animazione ambientale continua in questa revisione. |

Il set produttivo resta quello dell’atlante Apple Calm. Il concept usa Lucide per rendere esplorabili le idee: è un’approssimazione esplicita, non un nuovo set approvato. In produzione aggiungere solo simboli mancanti; usare ID semantici e rigenerare atlante e hash del bundle, con fallback. Le icone non vanno aggiunte a ogni cella di una tabella o a ogni misura già chiara.

## 6. GPU e animazioni: proposta concreta

La GPU non è un interruttore da accendere. Il percorso Qt Quick hardware usa già il scene graph per disegnare e comporre. `NumberAnimation` aggiorna proprietà sul lato UI; questo non significa che i pixel siano disegnati dalla CPU. Un Animator può spostare l’avanzamento visuale sul thread di rendering, ma logica, eventi, layout, binding e I/O non diventano lavoro GPU. [Qt Scene Graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html).

| Movimento | Proposta normale | Ridotto / Off |
| --- | --- | --- |
| Entrata banner | 180–220 ms, spostamento 12–18 px e opacità, OutCubic | Fade ≤80 ms / comparsa immediata |
| Uscita banner | 100–140 ms, movimento breve | Fade ≤80 ms / taglio |
| Apertura Centro/dettaglio | 100–160 ms, contenuto leggibile subito | Fade breve / taglio |
| Focus | Indicatore visibile dal primo frame; transizione locale facoltativa ≤80 ms | Immediato |
| Aggiornamento dato | Testo reale subito; lieve evidenza locale facoltativa | Immediato |
| Urgente | Taglio immediato, senza attesa | Identico |

**Ordine tecnico consigliato:** prima ottenere il risultato con primitive Qt Quick e ricette osservabili già esistenti. Poi confrontare `YAnimator`/`OpacityAnimator` su un wrapper visuale dedicato. Non sostituire globalmente le ricette di navigazione con Animator senza una misura del beneficio.

Punto critico: `Main.qml` e il tracing leggono opacità e geometria per riconoscere il frame presentato; con Animator quei valori QML non descrivono la posizione intermedia. Verificare avvio del timer, spazio occupato per l’intero movimento, interruzione da urgente, chiusura e commit del tema. Non usare una lettura di `opacity` come prova di un frame otticamente visibile.

La prima proposta non usa blur dello sfondo. L’ombra è locale e statica; il runtime può ottenerla con risorsa condivisa o geometria semplice, da confrontare. Se si vuole provare il vetro, farlo in un banco isolato su un solo pannello, con alternativa opaca equivalente. Un `MultiEffect` per card, una `layer.enabled` permanente o il blur dell’Acquario animato possono aumentare lavoro, texture e memoria. Non sono ottimizzazioni automatiche.

La rc.4 documenta un problema concreto di cache shader PowerVR. Conservare il ponte EGL e il bypass attuale, non cambiare backend/driver/cache per questa revisione; misurare anche il primo avvio, perché un nuovo effetto può richiedere nuova compilazione shader.

## 7. Schermate di analisi

Il [concept sorgente](concepts/v0102-apple-calm/apple-calm-v0102.html) è la visualizzazione usata in conversazione. Consente di scegliere undici stati e confrontare due composizioni, giorno/notte e movimento. Gli esempi di squadre, risultati, meteo, rete, orari e allerta sono **tutti sintetici**.

| Tavola | Cosa permette di valutare |
| --- | --- |
| [Oggi + banner](evidence/v0102-apple-calm-readability-2026-10-29/screens/home-day.png) | Gerarchia principale e notifica inferiore. |
| [Centro avvisi](evidence/v0102-apple-calm-readability-2026-10-29/screens/inbox-day.png), [110%](evidence/v0102-apple-calm-readability-2026-10-29/screens/inbox-scale110.png) | Tre righe, focus, categoria, ora e non letto. |
| [Dettaglio](evidence/v0102-apple-calm-readability-2026-10-29/screens/detail-day.png) | Contenuto, provenienza e conferma mancante. |
| [Meteo](evidence/v0102-apple-calm-readability-2026-10-29/screens/weather-day.png) | Icone e separazione delle grandezze. |
| [Rete](evidence/v0102-apple-calm-readability-2026-10-29/screens/network-day.png) | Traffico, registrazioni e significato degli stati. |
| [Calcio](evidence/v0102-apple-calm-readability-2026-10-29/screens/sport-day.png) | Risultato, stato e fonte. |
| [Impostazioni](evidence/v0102-apple-calm-readability-2026-10-29/screens/settings-day.png) | Sezioni, valori e icone. |
| [Vuoto](evidence/v0102-apple-calm-readability-2026-10-29/screens/empty-day.png), [offline](evidence/v0102-apple-calm-readability-2026-10-29/screens/offline-day.png), [rettifica](evidence/v0102-apple-calm-readability-2026-10-29/screens/revoked-day.png) | Assenza e correzione dei dati senza falsa freschezza. |
| [Urgente](evidence/v0102-apple-calm-readability-2026-10-29/screens/urgent-day.png) | Priorità immediata con testo leggibile. |
| [Home notte](evidence/v0102-apple-calm-readability-2026-10-29/screens/home-night.png), [avvisi notte](evidence/v0102-apple-calm-readability-2026-10-29/screens/inbox-night.png) | Palette esistente su superfici più chiare nella gerarchia. |
| [Alternativa laterale](evidence/v0102-apple-calm-readability-2026-10-29/screens/home-lateral-day.png) | Notifica estesa e diversa distribuzione dello spazio. |

Non sono stati creati screenshot di dettaglio per tutte le 71 superfici. La [seconda passata](v0102-apple-calm-graphic-refinement-study.md) aggiunge F1, Casa, Account e Menu, oltre a grafici, previsioni e componenti. MotoGP specifico e i sotto-menu completi restano da rifinire dopo la scelta della direzione.

## 8. Attuazione proposta, dopo la scelta grafica

La sequenza preliminare seguente è ora sviluppata e ordinata nel [piano completo](v0102-apple-calm-implementation-plan.md): baseline, correzioni semantiche/contratto, notifiche, viste, movimento e qualifica. Il controllo dati precede i passi grafici A–F.

| Passo | Risultato concreto | Dipendenze e criterio di chiusura |
| --- | --- | --- |
| A · Notifiche leggibili | Componenti distinti banner/lista/dettaglio; icone per categoria, ora/fonte e focus; contrasto e scala 1/1,1. | Riutilizzare EventEngine e azioni. Verifica fonti/tempi già nel DTO. Nessuna variazione della priorità o del timer implicita nel tema. |
| B · Header e spazio | Campana nelle viste appropriate, contatore corretto, gestione Quiete/Ripristino e fascia transitoria. | Aggiunte pubbliche compatibili a UiStatus/layout se necessarie; fallback Base/Functional; nessun accesso privato dal bundle. |
| C · Stati e gestione | Revocato/scaduto/offline strutturati, eventuale raggruppamento coerente. | Contratto DTO, fixture e policy backend espliciti. Un gruppo non perde eventi né rende letto l’intero contenuto. |
| D · Viste | Prima Meteo/Rete/Calcio/Impostazioni; poi F1/MotoGP/Casa/Account e menu. | Layout misurato, nomi lunghi, unità e dati mancanti. Arena e renderer Acquario conservati. |
| E · Movimento | Ricette brevi; A/B NumberAnimation e Animator; ombra statica. | Beneficio misurato, acknowledgement e interruzioni corretti. Blur solo se il banco separato supera i gate. |
| F · Candidata e consegna | Nuovo bundle immutabile e delta runtime minimo, con rollback. | Baseline installata verificata, packaging coerente, prove PC/ARM/EGLFS pertinenti e lettura fisica. Nessun numero di release assegnato ora. |

Per evitare che il lavoro si allarghi senza un beneficio chiaro, il primo incremento dovrebbe chiudere A e il minimo necessario di B. Raggruppamento avanzato, vetro e rifacimento di tutte le viste non sono prerequisiti per migliorare subito gli avvisi.

## 9. Verifiche proporzionate e criteri di accettazione

La prima passata ha verificato concept e documenti: rendering, interazioni locali, assenza di errori JavaScript, dimensioni e flusso del testo. Il successivo [audit dei dati](v0102-apple-calm-data-audit.md) ha aggiunto otto casi esistenti del runner passati e 14 sonde mirate che documentano i casi mancanti. Nessuna prova viene presentata come qualifica della board o del pannello.

Esito degli artefatti: **15 PNG a 960×640**, 44 combinazioni di stato/larghezza al 110% senza sconfinamenti o collisioni rilevate; cinque interazioni locali passate e nessun errore JavaScript. Le 24 coppie di colore del testo sulle superfici opache hanno contrasto minimo **4,85:1**. Questi controlli verificano il concept, non la resa QML o fisica. [Controllo del concept](evidence/v0102-apple-calm-readability-2026-10-29/concept-review.json), [contrasto](evidence/v0102-apple-calm-readability-2026-10-29/contrast-check.json), [file e collegamenti](evidence/v0102-apple-calm-readability-2026-10-29/artifact-checks.json).

Per l’attuazione, selezionare dal runner i casi effettivamente interessati (`python3 scripts/check-dashboard.py --suite ui --list`). Candidati già presenti: `check_notifications`, `check_notification_consultation_ui`, `check_notification_updates`, `check_theme_layout_ui`, `check_theme_api_contract` e `theme-acceptance-notifications`; non eseguirli tutti per principio. Allargare alle suite pertinenti quando vengono modificati controller, DTO o motore condiviso. Un esito rapido non qualifica la release.

| Gate proposto | Accettazione |
| --- | --- |
| Layout | 960×640, giorno/notte e scala 1/1,1; nessun testo essenziale coperto o fuori schermo; nomi lunghi, 0/1/molti avvisi e contenuti multilinea. |
| Eventi | Coda, urgenza, quiete, lettura separata da presentazione, scadenza, revoca/VAR, ritorno e recupero senza replay obsoleto. |
| Contratto tema | API additive, fixture aggiornate, fallback nei tre temi; bundle attuale conservato come revisione precedente. |
| Movimento | Primo feedback immediato; Off senza animazione; Ridotto senza spostamenti ampi; urgenza sempre immediata. |
| Regolarità software ARM | Campione significativo di transizioni per carico, con A/B o ABBA; obiettivo candidato p95 ≤18,5 ms e nessuno stallo >50 ms durante animazione. Riportare p99/massimo, primi avvii e variabilità; non confondere callback con FPS ottici. |
| Risorse | CPU/RSS/temperatura confrontati con la stessa baseline e carico; nessun nuovo aggiornamento continuo in idle; niente timer per ogni icona o lavoro su viste nascoste. Budget memoria fissato dopo il primo A/B, non inventato come risultato già raggiunto. |
| Carichi | Home, liste lunghe, aggiornamento dati, Gara/allenamento e Acquario 3D con banner/urgente. Non extrapolare dalla sola Home. |
| Pannello fisico | Prova alla distanza abituale, giorno/notte, lettura completa entro il tempo del banner; tastierino reale e assenza di disturbi. Nessuna prova ottica svolta in questa analisi. |
| Consegna | Manifest/hash, dati/preferenze/piloti/pesci conservati, backup verificato, servizio/heartbeat corrente e warning QML; reboot dichiarato solo se eseguito. Seguire [maintenance-policy](../../os/maintenance-policy.md). |

**Decisione proposta:** procedere in seguito con Calm essenziale, mantenendo l’identità Apple Calm e dando priorità a leggibilità e affidabilità delle notifiche. La scelta grafica non autorizza implicitamente una modifica al driver, un effetto costoso o una consegna sulla board.
