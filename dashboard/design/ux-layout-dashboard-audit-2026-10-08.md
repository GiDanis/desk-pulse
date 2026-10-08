# SmartPC — audit di spazio, coerenza grafica e dashboard

Data: 8 ottobre 2026. Baseline: SmartPC **0.8.3-rc.1**, Apple Calm **1.3.0**, display nominale **3,5″ / 960×640**, distanza dichiarata **50–60 cm**.

La priorità è correggere la relazione fra contenuti, navigazione e spazio disponibile. Ridurre soltanto i margini lascerebbe in funzione le riserve vuote e il difetto che mostra i contenuti sbagliati in Informazioni. La direzione proposta è una griglia comune, una barra superiore leggermente più sottile, liste realmente scorrevoli e dashboard Casa/Rete centrate sui valori. Le indicazioni permanenti dei tasti e i contatori di pagina richiesti dall’utente vanno eliminati recuperando anche la loro geometria.

Questo documento è **analisi e proposta**, non una release implementata. Core, renderer del tema e installazione Orange Pi non sono stati modificati. Sono stati aggiunti soltanto strumenti ed evidenze di analisi e un confronto visivo nella chat. Non sono stati eseguiti aggiornamenti, restart o reboot della scheda.

## 1. Metodo e attendibilità

| Livello | Evidenza raccolta | Cosa consente di concludere |
|---|---|---|
| Installazione reale, lettura | Manifest: 498 file senza differenze; servizio attivo, `NRestarts=0`; Apple Calm 1.3.0, digest `10bd33af67b331a2e2993ef83b7c5724800edeb078bd029a8ce08059e8ae0c86` | Identità della baseline installata; non certificazione delle nuove proposte |
| Riproduzione locale | Main reale, Qt 6.8.2, dati sintetici, trasporti provider bloccati; 19 catture Apple e 18 Base | Bug e geometrie riproducibili senza dati/account esterni |
| Inventario statico | 60 superfici dichiarate, 59 renderer propri Apple; 36 basati su `Panel` | Ampiezza della revisione necessaria; non 60 nuove verifiche visuali |
| Prototipo nella chat | Sport, Casa, Rete, Risorse: confronto fra catture attuali e proposta interattiva | Gerarchia e uso dello spazio da discutere; valori dimostrativi, nessuna funzione installata |
| Fonti esterne | 13 riferimenti principali, compresi 2 studi accademici consultati negli abstract | Principi di progetto; nessuna prova di leggibilità sul nostro hardware |

Il runner usa il codice esistente con ambienti di preferenze isolati. Nei due audit: **zero warning QML e zero chiamate ai trasporti provider**. Questo non implica assenza di bug: il difetto Informazioni passa proprio senza warning.

Evidenze: [audit Apple](evidence/ux-space-audit-2026-10-08/apple/audit.json), [audit Base](evidence/ux-space-audit-2026-10-08/base/audit.json), [baseline scheda](evidence/ux-space-audit-2026-10-08/board-readonly-baseline.json), [inventario di tutte le superfici](evidence/ux-space-audit-2026-10-08/surface-inventory.json), [runner riproducibile](evidence/ux-space-audit-2026-10-08/audit_ui.py).

Non abbiamo aperto nuove sessioni EGLFS: avrebbero richiesto di interrompere il servizio. Restano da verificare sul pannello fisico font, resa IPS, contrasto e comodità a 50–60 cm.

## 2. Difetti funzionali prima della rifinitura

### 2.1 Dispositivo e Risorse identici: bug riprodotto

La segnalazione è confermata in Apple Calm. Passando da **Dispositivo** a **Risorse**, cambia la scheda selezionata ma rimangono le sei righe del dispositivo. Il controller e il contesto pubblico hanno già i dati corretti.

| Scheda | Dati corretti nel controller/DTO | Righe effettivamente renderizzate in Apple |
|---|---|---|
| Dispositivo | Software, Dispositivo, Sistema operativo, Display, Tastierino USB, Fuso orario | Le sei righe corrette |
| Risorse | Temperature, CPU dashboard, RAM sistema, RAM dashboard, Archiviazione, Continuità | Le sei righe di Dispositivo |
| Rete | Connessione, Indirizzo IP, Segnale Wi-Fi, Account dal PC | Le quattro righe corrette |
| Dati | Meteo, Protezione Civile, Account ChatGPT, Casa/Smart Life, Serie A, Formula 1, MotoGP | Le sette righe corrette |

La riproduzione funziona sia con il tastierino sia con l’azione pubblica `tabs.select`: anche quando l’azione restituisce `completed`, le righe restano errate. Base mostra Risorse correttamente.

**Causa individuata:** `DeviceInfo.qml` materializza `context.rows` tramite `Format.info()` / `Format.list()`, che legge `model.count` e `model.get(i)` e costruisce un array JavaScript. Il modello pubblico sostituisce le identità con i corretti segnali strutturali Qt, ma il suo numero finale rimane sei: `countChanged` non viene emesso. L’array derivato non acquisisce automaticamente le nuove identità. Il renderer legge anche `context.dataRevision`, che in questo percorso resta **0**: il payload di Main non pubblica una revisione utile a questa sostituzione.

Riferimenti: [DeviceInfo Apple](../../theme-projects/apple-calm/bundle/qml/DeviceInfo.qml), [Format](../../theme-projects/apple-calm/bundle/qml/Format.js), [modello pubblico](../theme_models.py), [payload Main](../Main.qml).

**Intervento richiesto:** fare consumare alle liste i modelli e ruoli Qt direttamente dove possibile; per le proiezioni/filtri in array, introdurre una dipendenza di revisione affidabile. Il contratto deve coprire sostituzioni con uguale cardinalità, aggiornamenti e riordini, mantenendo identità e focus. Non risolvere forzando il reload del renderer o emettendo un falso cambiamento del numero di righe.

Il rischio si estende alle altre proiezioni materializzate, ma **il difetto specifico è stato riprodotto qui**, non su tutte le 36 superfici `Panel`. Va aggiunta una regressione che confronti i testi e i valori realmente visibili, oltre a stato del controller, numero di elementi e assenza di warning.

### 2.2 Timestamp di Informazioni perso

Il contesto pubblico `InfoContext.updatedAt` risulta nullo in tutte le schede, mentre lo snapshot di sistema contiene un timestamp valido (`1790848800.0` nel fixture). La cattura Apple mostra **“Rilevato” senza un’ora**. Occorre passare il timestamp coerente con le misure e rendere robusta la formattazione dei valori nulli/assenti. Non va inventata una data per completare il footer.

### 2.3 Inventario fonti incompleto

La scheda Dati comprende sette fonti, ma non Rete/iliadbox, ormai parte del prodotto. È un’omissione nel contenuto attuale, distinta dal bug delle righe duplicate. La futura scheda deve distinguere provider configurato, ultima lettura disponibile, cache precedente e problema corrente; nessuna conferma di funzionamento ottenuta soltanto dalla presenza di una cache.

## 3. Dove si perde lo spazio

### 3.1 Geometria esterna effettiva

| Elemento Apple Calm | Baseline |
|---|---:|
| Display | 960×640 px |
| Barra superiore | 64 px |
| Inizio contenuto | x=32, y=80 |
| Area contenuto | 896×528 px |
| Fine contenuto | y=608 |
| Margine inferiore esterno | 32 px |
| Guida globale dichiarata nel bundle | 0×0 px |
| Regione scena dichiarata | x=32, y=610, 80×22 px |

Il nero inferiore non dipende solo dalla guida globale, già azzerata nel bundle Apple. Dentro i componenti restano altri spazi riservati:

- `Panel` in modalità pagina: 106 px prima del corpo e **45 px** sotto il corpo.
- `Panel` overlay: 136 px prima del corpo e **55 px** sotto il corpo.
- `Rows`: **26 px** sottratti alla capacità per il contatore, anche quando non serve.
- Liste paginate: spazio restante sotto l’ultima riga, senza scorrimento continuo.
- Viste personalizzate: guide locali, intestazioni multiple e misure differenti.

La sola combinazione footer+contatore riserva **71 px nelle pagine / 81 px negli overlay** che usano entrambi i componenti. È un budget da riprogettare, non un guadagno universale già dimostrato. Non si deve sommare due volte la stessa area.

Su un pannello nominale 3,5″ con rapporto 3:2, l’area attiva stimata è 73,97×49,31 mm: circa **12,98 px/mm**. Il solo bordo di 32 px equivale a circa 2,47 mm; un centimetro corrisponderebbe a circa 130 px. La percezione dell’utente è compatibile con la somma di bordo, footer e vuoto della paginazione. Sono stime geometriche nominali, non una misura con righello del pannello installato.

### 3.2 Sport: una disciplina esclusa per tre pixel

Misura del renderer reale: corpo lista **377 px**, altezza logica riga **118 px**, capacità calcolata `floor((377−26)/118)=2`. Per ottenere tre righe secondo quella formula servirebbero 354 px; ne rimangono 351: **mancano appena 3 px**.

Inoltre, le tre card dipinte occuperebbero `3×110 + 2×8 = 346 px`, perché la formula conteggia anche lo spazio dopo l’ultima card. Di conseguenza il sistema pagina Calcio/Formula 1/MotoGP e mostra il contatore quando le tre card possono già entrare nel corpo nominale senza rimpicciolire il testo standard.

[Sport attuale Apple](evidence/ux-space-audit-2026-10-08/apple/sport.hub.png).

Questo caso rende evidente perché nascondere soltanto la scritta non basta: occorre eliminare la riserva nella formula e ripensare il flusso delle righe.

### 3.3 Allineamenti non governati da una regola unica

La pagina e l’intestazione Apple usano 32 px. Alcuni pannelli di rete copiati dal core continuano a usare 44 px: **12 px di scarto**. Il fallback core di `pageGeometry` è `(44,90,872,455)`, diverso dalla geometria esterna del tema. Overlay e pagine applicano ulteriori inset locali.

La correzione deve partire da un sistema di coordinate condiviso: area sicura del tema, margine di pagina, padding della card, allineamento del testo e riserva per notifiche/scena. Le coordinate assolute vanno limitate ai componenti che ne hanno realmente bisogno.

## 4. Griglia candidata per 960×640

| Regola | Oggi Apple | Proposta iniziale |
|---|---:|---:|
| Barra superiore | 64 | **56 px** |
| Distanza barra/contenuto | 16 | **16 px** |
| Margini laterali | 32 | **24 px** |
| Margine inferiore | 32 | **16 px** |
| Area contenuto | x32, y80, 896×528 | **x24, y72, 912×552** |

La barra scende di 8 px, cioè 12,5%; resta riconoscibile e leggibile. La sola geometria esterna aumenta l’area utile del **6,41%**, prima del recupero delle riserve interne. Questa è una **candidata da validare**, non una misura ottimale dimostrata da uno studio sul nostro display.

Regole complementari:

- Ritmo di base 8 px, con aggiustamenti ottici di 4 px; padding card 16 px; separazioni 12 o 16 px secondo il componente.
- Un bordo comune per titolo contestuale, card e valori. Spostare l’icona/header con la griglia, non soltanto il contenuto.
- Numeri principali circa 48–60 px, titoli 32–38 px, descrizioni importanti 28–32 px come punto di partenza; correggere i testi da 18 px che contengono informazioni necessarie. Queste dimensioni richiedono prova a 50–60 cm.
- Conservare l’ingrandimento del testo già supportato. Le card possono diventare più alte e scorrere; nessuna riduzione automatica del carattere per far entrare più righe.
- Footer condizionale: nessuno spazio se non esiste un messaggio. Stato e ultima lettura accanto al valore interessato; errori e conferme di salvataggio in un’area contestuale visibile.
- Un solo scorrimento verticale per dashboard; indicatore sottile interno all’area. Nessuna lista scorrevole dentro una seconda lista.
- Le regioni sicure per scena e notifiche devono essere riconciliate con la nuova area: il contenuto proposto arriva oltre la regione scena attuale. Se la scena è attiva, definire una riserva coerente; non cancellarla implicitamente.

Apple raccomanda allineamenti e gerarchie leggibili; Carbon descrive una griglia con unità ricorrenti. Da queste fonti ricaviamo il principio, non copiamo automaticamente i margini di iPhone o i breakpoint desktop sul pannello embedded. [Apple Design Tips](https://developer.apple.com/design/tips/), [Carbon 2x Grid](https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid/overview).

## 5. Eliminazione delle guide senza perdita di orientamento

Eliminare dalle viste ordinarie:

- Guide permanenti dei tasti, globali e locali: `2/8 DISCIPLINE`, `5 APRI`, `7 INDIETRO` e varianti.
- Contatori di pagina `1–2 /3` e riserve dedicate.
- Etichette che spiegano una selezione nascosta dell’intestazione.

Conservare:

- Aiuto/Comandi richiesto esplicitamente dall’utente.
- Nome della sezione, scheda selezionata e focus chiaramente visibile.
- Quantità informative: dispositivi osservati, eventi non letti, numero di partite. Non sono contatori di impaginazione.
- Fonte, stato precedente/offline, unità di misura, errore, conferma di salvataggio e modifiche non applicate.

Sostituzione dell’orientamento: una card parzialmente visibile quando esiste altro contenuto e un indicatore verticale sobrio. I puntini delle viste indicano la vista, non la posizione nella lista: se rimangono, collocarli e mostrarli in modo da non confonderli con l’indicatore di scorrimento.

Oggi Casa/Rete cambiano il significato di 4/6 in base al focus nascosto dell’intestazione; 5 cambia fra apertura del dettaglio e cambio di sezione. Togliere le guide prima di correggere questo comportamento renderebbe il prodotto meno comprensibile.

**Contratto candidato:** alla radice di una dashboard 2/8 selezionano le card, 5 apre il dettaglio, 7 torna conservando elemento e posizione; 4/6 cambiano macroarea. Filtri e viste alternative diventano controlli espliciti selezionabili. Nei dettagli con schede locali, 4/6 possono operare su quelle schede, ma il livello deve essere visibile. Questo contratto va verificato contro tutti i percorsi esistenti e le azioni pubbliche del Theme API prima di implementarlo.

La ricerca sulla progressive disclosure suggerisce di tenere evidenti i compiti frequenti e portare i dettagli in un secondo livello; le indicazioni sullo scrolling sottolineano la necessità di rendere scopribile il contenuto successivo. L’applicazione al tastierino Qt è una nostra deduzione progettuale. [NN/G Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/), [NN/G Scrolling and Scrollbars](https://www.nngroup.com/articles/scrolling-and-scrollbars/).

## 6. Casa / IoT: dashboard leggibile dei dispositivi

**Problema osservato:** Apple usa il pannello generico con righe, footer e paginazione; nei fixture quattro preferiti ne mostra due per volta. Base usa una griglia 2×2, dettagli piccoli e guide anche su più livelli. Il tema non ha una gerarchia coerente fra identità del dispositivo, misura e stato.

[Cattura Apple Casa](evidence/ux-space-audit-2026-10-08/apple/casa.overview.png), [cattura Base Casa](evidence/ux-space-audit-2026-10-08/base/casa.overview.png).

**Proposta:** un feed verticale di card dei preferiti. Ogni card contiene nome breve, valore principale grande, una misura secondaria se disponibile, stato e ultima lettura. Un sensore di temperatura mostra la temperatura come contenuto dominante; umidità e batteria restano subordinate. Per dispositivi senza misura principale, rappresentare il dato effettivamente supportato senza inventare indicatori.

Ordine stabile dei preferiti; accesso esplicito a tutti i dispositivi; stesso modello visivo in elenco e dettaglio. Il dettaglio raccoglie le misure aggiuntive con unità e disponibilità; 7 ripristina identità e posizione, anche dopo un refresh.

Stato precedente o offline vicino al valore, non relegato alla coda generale della pagina. Se un sensore non è disponibile, non mostrare zero. La proposta non aggiunge comandi di accensione/spegnimento: il perimetro corrente resta la lettura dei dati.

Configurazione dell’account, credenziali, associazione e budget del servizio restano nelle impostazioni. Il riepilogo del problema del servizio può essere una card compatta con un collegamento esplicito, senza occupare in permanenza il posto dei dati.

**Core necessario:** proiezione dei DTO con valori prioritari, selezione per identità e bookmark; evitare nuove chiamate per ogni card o gesto. **Apple necessario:** card specifiche del dominio, tipografia e scrolling comuni. Non basta trasferire le stesse righe in un’altra cornice.

## 7. Rete / iliadbox: metriche principali subito disponibili

**Situazione effettiva:** i dettagli Router/Wi-Fi/Porte esistono già e sono raggiungibili anche da Rete. Il percorso richiede però selezionare un’intestazione, premere 5 per entrare in Approfondimenti, poi scegliere uno strumento. Le stesse destinazioni sono in Impostazioni/Rete. La percezione di dover passare dalle impostazioni è quindi comprensibile: è un problema di accesso e gerarchia, non l’assenza delle metriche.

La panoramica Apple riprende un layout del core: conteggi, stato WAN, IP e griglia di dispositivi, con testi da 18–25 px e guida di navigazione sul fondo. Non usa la stessa grammatica delle altre pagine Apple.

[Cattura Rete](evidence/ux-space-audit-2026-10-08/apple/network.overview.png), [strumenti](evidence/ux-space-audit-2026-10-08/apple/network.tools.png), [Router](evidence/ux-space-audit-2026-10-08/apple/network.router.png).

**Ordine proposto del feed:**

1. **Internet / traffico WAN:** download e upload con unità e istante/finestra del campione.
2. **Router:** temperatura iliadbox e stato pertinente disponibile.
3. **Wi-Fi:** radio/bande, stato e dati delle associazioni qualificati.
4. **Porte Ethernet:** link e traffico, con capacità distinta dal consumo.
5. **Dispositivi osservati:** preferiti, riepilogo e accesso all’elenco completo.

I primi due contenuti devono essere leggibili nella prima schermata a dimensione normale se i dati sono supportati. Le card aprono i dettagli già esistenti, compresa la storia disponibile. L’ingrandimento del testo può richiedere scorrimento: priorità alla leggibilità.

**Semantica da rispettare:** traffico WAN misurato dal router non è un test della velocità massima della linea; capacità del link non è traffico; campione RRD e finestra/aggregazione vanno dichiarati correttamente. “Temperatura iliadbox” è distinta da “Temperatura CPU Orange Pi”. Un router raggiungibile non prova da solo la raggiungibilità Internet completa. Identità note e osservazioni del router non provano presenza continua né copertura integrale della LAN.

**Limite tecnico da risolvere:** il contesto della panoramica non offre oggi tutta la proiezione sintetica delle metriche dei dettagli. Serve un’estensione additiva dei DTO e la registrazione dell’interesse alla vista. Un’eventuale dashboard visibile può richiedere il riepilogo leggero, conservando TTL, single flight, persistenza atomica e qualificazione dei dati. Nessun I/O nei binding QML e nessun polling di dettaglio per ogni riga. Le fonti rimangono quelle disponibili; dati mancanti devono rimanere indisponibili.

Impostazioni/Rete deve contenere configurazione e diagnostica amministrativa; l’osservazione ordinaria della rete trova la sua sede principale nella macroarea Rete. Eventuali scorciatoie diagnostiche non devono essere l’unico accesso alle letture quotidiane.

Carbon consiglia una gerarchia dei KPI e un numero limitato di misure dominanti; il catalogo Dashboard Design Patterns offre strutture per riepilogo e dettaglio. Il feed selezionato è una nostra proposta per questo hardware e questi dati. [Carbon Dashboards](https://www.carbondesignsystem.com/building-blocks/data-visualization/dashboards), [Dashboard Design Patterns](https://arxiv.org/abs/2205.00757).

## 8. Problemi simili da includere nella revisione

| Area | Evidenza / limite | Miglioramento proposto |
|---|---|---|
| Sport | Titolo Sport nella shell e nel pannello; corpo paginato | Un titolo contestuale, tre discipline nella panoramica, card coerenti con gli altri domini |
| Informazioni/Menu | La shell mantiene il nome della famiglia sottostante mentre l’overlay è aperto | Header che descrive la superficie effettivamente attiva |
| Impostazioni | Indice, gruppi e dettaglio hanno titoli e riserve di spazio differenti | Stessa struttura pagina; gruppo, controllo, descrizione utile e feedback condizionale |
| Percorsi testuali Casa | Alcuni messaggi rimandano a un vecchio percorso “Impostazioni → Casa” | Etichette derivate dalla navigazione attuale; verificare anche Servizi collegati e preferiti |
| Schede locali | Etichette piccole rispetto a intestazioni e numeri | Dimensioni leggibili e focus evidente senza aumentare il numero di righe di chrome |
| Fonti e footer | Fonte+stato+ora+errore concatenati in una sola riga | Stato breve accanto al valore, dettagli fonte/errori consultabili; non tagliare la qualità dei dati |
| Meteo/forecast | Layout dedicati e colonne, fuori dal `Panel` condiviso | Verifica mirata di unità, testi lunghi e scala; rischio statico, non dichiarazione che ogni vista sia guasta |
| Account | Componente autonomo, unità e intervalli informativi | Allineamento alla griglia comune, distinguere consumo, limite e finestra temporale |
| Home/Oggi | Può essere legittimamente priva di eventi | Distribuire bene il contenuto disponibile; non creare card di riempimento senza informazione |
| Notifiche/avvisi | Hanno regioni e priorità diverse dalle pagine | Conservare urgenza, accesso, indicatori di eventi non letti e contrasto; non applicare rimozione indiscriminata |
| Icone | Stili e dimensioni da verificare insieme a griglia/testo | Riutilizzare il sistema vettoriale; disegnare solo simboli mancanti con stesso tratto, ingombro e centro ottico |
| Valori dinamici | Possibili cambi di larghezza e identità nelle liste | Numeri tabulari, unità sempre riconoscibili, aggiornamenti senza perdita di focus o salti gratuiti |

Per le impostazioni conservare la separazione fra opzioni modificabili e Informazioni di sola lettura. L’intento è rendere più immediata la struttura esistente, evitando di spostare misure quotidiane e diagnostica sotto controlli di configurazione.

L’audit delle icone deve produrre una matrice dominio/azione/stato. Per simboli funzionali piccoli, asset vettoriali coerenti con il set esistente sono preferibili a immagini raster generate: leggibilità e uniformità del tratto vengono prima del numero di nuove icone. Etichette e focus restano comprensibili anche senza il colore.

## 9. Fonti consultate e trasferimento al progetto

Non esiste una fonte che certifichi una UX “perfetta” per SmartPC. Le seguenti fonti sostengono principi; le decisioni numeriche e i percorsi proposti derivano dall’audit locale e richiedono validazione. Il precedente [dossier di ricerca](ux-research-consolidation-2026-10-08.md) resta il contesto più ampio: non tutte le sue fonti sono state consultate nuovamente in questo audit.

| Riferimento primario | Consultazione / principio utile | Applicazione proposta e limite |
|---|---|---|
| [Apple HIG — Layout](https://developer.apple.com/design/human-interface-guidelines/layout) | Contenuto ufficiale indicizzato; la pagina diretta richiede JS. Gerarchia, allineamento, segnali di contenuto ulteriore | Area coerente e contenuto prioritario; safe area di altri dispositivi non trasferita numericamente |
| [Apple — UI Design Do’s and Don’ts](https://developer.apple.com/design/tips/) | Testo ufficiale: chiarezza, allineamento e dimensioni leggibili | Rifinire margini e titoli senza ridurre tutto il testo |
| [Apple — Layout margins](https://developer.apple.com/documentation/uikit/positioning-content-within-layout-margins) | Estratto ufficiale indicizzato sui margini come guide e buffer | Margine intenzionale e comune; nessuna banda vuota arbitraria |
| [Carbon — Dashboards](https://www.carbondesignsystem.com/building-blocks/data-visualization/dashboards) | Pagina completa: gerarchia delle metriche, spaziatura e coerenza | WAN e temperatura visibili, dettagli secondari nel feed; nessuna percentuale di beneficio adottata senza prova locale |
| [Carbon — 2x Grid](https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid/overview) | Pagina completa: unità ricorrenti, margini/padding | Ritmo 8 px adattato; niente copia dei breakpoint desktop |
| [NN/G — Consistency and Standards](https://www.nngroup.com/articles/consistency-and-standards/) | Pagina completa: convenzioni e standard condivisi | Stesso significato di focus e azioni su tutte le macroaree |
| [NN/G — Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | Pagina completa: priorità al compito e accesso ai dettagli | Metriche frequenti visibili; configurazione e dettaglio in livelli espliciti |
| [NN/G — Scrolling and Scrollbars](https://www.nngroup.com/articles/scrolling-and-scrollbars/) | Pagina completa, studio/principi pubblicati nel 2005 | Scorrimento riconoscibile; trasferimento ragionato al keypad, non equivalenza fra web e Qt |
| [Dashboard Design Patterns](https://arxiv.org/abs/2205.00757), [catalogo degli autori](https://dashboarddesignpatterns.github.io/) | Abstract e catalogo: analisi sistematica di 144 dashboard, 8 gruppi di pattern, workshop con 23 partecipanti | Riepilogo/dettaglio e gerarchia; pubblicazione e catalogo contati come un riferimento |
| [Design Patterns and Trade-Offs in Responsive Visualization for Communication](https://arxiv.org/abs/2104.07724) | Abstract: 76 strategie da 378 coppie di visualizzazioni per schermi grandi/piccoli | Adattare contenuti e struttura; non ridurre uniformemente la scala. Studio non specifico del display SmartPC |
| [Qt 6.8 — ListView](https://doc.qt.io/qt-6.8/qml-qtquick-listview.html) | Documentazione ufficiale su modelli, delegate e posizionamento | Liste native; elemento selezionato interamente visibile con `positionViewAtIndex(..., ListView.Contain)`; stato fuori dai delegate riciclati |
| [Qt 6.8 — ScrollIndicator](https://doc.qt.io/qt-6.8/qml-qtquick-controls-scrollindicator.html) | Documentazione ufficiale dell’indicatore collegato a Flickable | Indicatore sottile senza footer o paginazione numerica |
| [W3C — Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) | Criterio e spiegazione ufficiale: contrasto delle parti necessarie dei controlli | Riferimento ingegneristico per focus distinguibile, almeno 3:1 rispetto ai colori adiacenti quando applicabile; nessuna certificazione WCAG e nessuna conversione automatica dei CSS px in misura fisica |

Gli studi accademici sono stati consultati negli abstract: non dichiariamo di aver letto integralmente metodo e risultati dei PDF. Non copiare effetti grafici pesanti, vetro/blur o transizioni perpetue soltanto per assomigliare a un sistema operativo. Apple Calm deve usare la chiarezza dei principi con il costo grafico adatto all’Orange Pi.

## 10. Priorità e responsabilità

P0 = errore del contenuto; P1 = percorso o spazio che ostacola l’uso ordinario; P2 = rifinitura e copertura della coerenza. Sono priorità di intervento, non valutazioni di sicurezza.

| ID | Priorità | Problema | Responsabilità principale | Evidenza |
|---|---|---|---|---|
| U01 | P0 | Risorse mostra Dispositivo | Core Theme API + proiezione Apple | Riprodotto con due input |
| U02 | P1 | Data di rilevamento persa | Payload Info + formattazione Apple | Riprodotto |
| U03 | P1 | Footer/counter riservano spazio anche quando inutili | Componenti Apple e guide core | Codice + misura |
| U04 | P1 | Terza disciplina Sport esclusa | Rows / Sport hub | Misura 377/118/26 |
| U05 | P1 | Margini 32/44 e bordi disallineati | Contratto layout + renderer | Codice |
| U06 | P1 | Barra e contenuto consumano più area del necessario | Shell + manifest layout | Misura; nuova geometria proposta |
| U07 | P1 | Guide e paginatori permanenti | Core + tutti i renderer interessati | Catture/codice |
| U08 | P1 | Significato dei tasti dipende da focus nascosto | Controller navigazione + focus visibile | Codice Casa/Rete |
| U09 | P1 | Casa senza gerarchia delle misure | DTO / card / lista | Catture |
| U10 | P1 | Metriche Rete difficili da trovare | Navigazione + root DTO | Percorso verificato |
| U11 | P1 | Dashboard Rete eterogenea rispetto al tema | Card Apple + componenti condivisi | Catture/codice |
| U12 | P1 | Interesse al riepilogo metriche da collegare al feed | Backend + adapter, con TTL e single flight | Necessità della proposta |
| U13 | P1 | Rete assente dall’inventario Dati | Info / fonti | Righe del controller |
| U14 | P2 | Intestazione non contestuale negli overlay | ShellContext / header | Cattura/codice |
| U15 | P2 | Font importanti piccoli e gerarchie discordanti | Token e componenti dedicati | Catture mirate; audit residuo |
| U16 | P2 | Percorsi testuali vecchi | Microcopy / routing | Codice |
| U17 | P2 | Icone e centro ottico non ancora censiti ovunque | Asset vettoriali e token | Lavoro di inventario da eseguire |
| U18 | P2 | Safe region scena e nuova geometria da riconciliare | Manifest / shell / scene | Contratto attuale |
| U19 | P2 | Stati lunghi e messaggi compressi nel footer | Componenti di stato | Catture/codice |
| U20 | P1 | Test insufficienti sulla sostituzione delle righe | Verifiche renderer/contratto | Bug senza warning |

## 11. Sequenza proposta per la prossima minor release

Non attribuiamo una nuova versione come già pronta o installata. Un’eventuale **0.8.4** può seguire queste fasi, con gate separati:

**A — Correttezza dei contenuti.** Correggere U01/U02, rendere robusta la reattività delle proiezioni e completare Info/Dati. Verificare i testi effettivi sia via tastierino sia tramite azioni pubbliche. Non introdurre un redesign prima di isolare le regressioni.

**B — Fondazione del layout.** Token di geometria comuni; Shell 56 px candidata; margini 24/16; footer condizionali; rimozione completa di guide/pager e della loro riserva. ListView con focus, scrolling e bookmark. Prima applicazione a Sport, Info e impostazioni per verificare tre strutture diverse.

**C — Casa e Rete.** Implementare il feed dei preferiti e quello delle metriche, estensioni additive dei contesti, interesse backend e accessi espliciti ai dettagli. Verificare aggiornamento, dati precedenti, fonti indisponibili e ritorno. Stesso linguaggio visivo in Base e Apple, rispettando i rispettivi stili.

**D — Coerenza di tutte le superfici.** Matrice delle 60 superfici: font, unità, titoli, card, focus, allineamenti, messaggi e icone. Copertura mirata dei componenti personalizzati; inventario statico non sufficiente per chiudere il gate.

**E — Validazione e installazione, quando autorizzate.** Prove locali appropriate, catture reali EGLFS e controllo sul display a 50–60 cm; poi installazione con manifest, backup/rollback e preferenze conservate. Le verifiche sulla scheda devono restare distinte dalla revisione grafica locale.

## 12. Criteri di accettazione misurabili

1. Dispositivo → Risorse → Dispositivo cambia davvero titoli, valori e identità visibili. Stesso risultato con tasti e `tabs.select`; includere riordino, sostituzione di pari cardinalità, lista vuota e modifiche di valore.
2. Ogni misura Info ha timestamp coerente o una dichiarazione di indisponibilità. Nessuna etichetta temporale orfana.
3. Zero guide permanenti dei tasti e zero contatori di impaginazione nelle viste ordinarie interessate. Aiuto, conteggi informativi, stato e feedback rimangono accessibili.
4. Margini delle superfici comparabili seguono la griglia concordata; controlli visivi ammettono aggiustamenti ottici fino a ±2 px motivati, non disallineamenti strutturali da 12 px.
5. Sport mostra le tre discipline alla scala normale senza paginarle. Alla scala ingrandita e con testi lunghi le card rimangono complete e raggiungibili tramite scorrimento; non imporre tre righe se compromette la lettura.
6. Una dashboard ha un unico asse verticale, selezione sempre completamente visibile e nessun salto di posizione non necessario durante refresh. Nessun nuovo tasto per distinguere due scorrimenti annidati.
7. Apertura/ritorno conserva ID della card e bookmark, anche dopo un aggiornamento ordinario. Valutare esplicitamente l’elemento rimosso, il cambio tema e l’interruzione di un avviso.
8. WAN e temperatura iliadbox sono accessibili dalla prima schermata Rete quando supportate; unità e qualità del dato sono visibili. Un dato non disponibile non diventa zero o attuale.
9. Temperatura Orange Pi e iliadbox, CPU del processo e sistema, traffico e capacità di link hanno etichette inequivocabili.
10. La dashboard non moltiplica chiamate per card, binding, frame o singola pressione del tasto. Fonti nascoste rispettano gli interessi previsti; completamento del refresh continua a seguire la persistenza.
11. Prove di testo lungo, nomi di dispositivo, messaggi offline/errore, scala normale/ingrandita e day/night coprono le famiglie di componenti e tutte le superfici modificate.
12. Sul pannello reale, a 50–60 cm, valori e focus sono leggibili senza avvicinarsi; valutazione pratica esplicita dell’utente, non derivata dalla sola cattura PC. Movimento ridotto rispettato e nessuna animazione continua aggiunta.
13. Nessun warning QML nuovo; servizio stabile; preferenze e cache preservate durante l’eventuale consegna. Le misure software dei frame non vengono presentate come latenza ottica o GPU.

## 13. Risultato dell’analisi

Le quattro cause principali sono: **reattività dei contenuti**, **riserve di layout sovrapposte**, **accessi poco evidenti**, **componenti di dominio con gerarchie diverse**. Una correzione professionale passa dai componenti comuni e dal contratto di navigazione, poi dalle card specifiche di Casa/Rete e dalle rifiniture di tutte le viste.

Il confronto nella chat illustra la direzione con valori dimostrativi. Le catture di questo dossier mostrano invece il codice attuale con fixture locali. La proposta non è un rendering QML installato né una certificazione sul pannello. La conclusione non è che la UX sia già perfetta: abbiamo una base concreta e verificabile per chiudere i difetti e giudicare la qualità della prossima minor release.
