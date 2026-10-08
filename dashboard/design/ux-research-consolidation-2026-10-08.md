# SmartPC — Studio approfondito di UX e grafica per 0.8.2 / 0.8.3

**8 ottobre 2026 · Europe/Rome · Analisi e specifica di verifica.**

**Condizione d'uso confermata dall'utente:** display osservato normalmente a **50–60 cm**. È la distanza primaria del protocollo; 30–40 cm serve soltanto al confronto ravvicinato.

Questo dossier amplia il [piano di consolidamento](v082-v083-consolidation-plan.md). Comprende **32 riferimenti: 9 pubblicazioni scientifiche e 23 documenti di linee guida/metodo/implementazione**, confrontati con i sorgenti e le evidenze già presenti. La bibliografia distingue testi accessibili, abstract e raccomandazioni professionali. Non è una revisione sistematica della letteratura e non attesta prove nuove sulla Orange Pi.

## 1. Decisioni che cambiano rispetto al primo piano

1. **Calibrazione fisica prima dei font definitivi.** I precedenti 26–30 px per il testo principale non sono una baseline di leggibilità approvata. L'utente ha confermato 50–60 cm: verificare area attiva, scala reale e altezza dei glifi a quella distanza. Confrontare composizioni che privilegiano testo più grande e meno contenuto.
2. **Numero di categorie non fissato a priori.** Confrontare l'indice Impostazioni in sei gruppi con uno più diretto in otto gruppi. Entrambi occupano due pagine se le righe sono quattro: sei voci non riducono automaticamente pagine o tasti.
3. **Sport unico confermato, percorso da qualificare.** Indice Calcio/F1/MotoGP leggibile e guida coerente; verificare se il passaggio aggiunto pesa nell'uso frequente. Conservare ultima disciplina e selezione nella sessione, senza saltare l'indice in modo imprevedibile.
4. **Coerenza misurata anche per stati.** La matrice comprende selezionato, focus, disabilitato, aggiornamento, precedente, offline, errore e vuoto, non soltanto screenshot con dati sani.
5. **Grafici nello stesso sistema visivo.** `NetworkHistoryChart.qml` usa attualmente `16px sans-serif` nel Canvas; è una divergenza verificata nel codice. Assi, legenda e unità devono rispettare font/scala/contrasto del tema. Confrontare le serie senza affidarsi soltanto al colore.
6. **Icone: significato prima dell'estetica.** Riconoscere il disegno e capire l'azione sono verifiche separate. Correggere prima il mapping Rete già mancante in Apple Calm; creare soltanto i simboli che la matrice dimostra assenti o ambigui.
7. **Palette chiara e scura qualificate separatamente.** Una preferenza estetica o una prova in un solo ambiente non dimostra prestazioni migliori in tutte le condizioni.
8. **Stabilità della navigazione durante il refresh.** Riga selezionata, ordine e posizione non cambiano sotto il dito/tasto per aggiornamenti di dati o avvisi; l'entità mantiene la propria identità.
9. **Feedback immediato distinto dalla disponibilità dei dati.** L'interfaccia risponde al comando mentre il worker lavora, mantenendo chiaro se la richiesta è stata accettata e se l'ultimo risultato è stato salvato.
10. **Prototipi e prove servono a scegliere, non a certificare in anticipo.** Nessuna implementazione di nuovo provider, comando Casa, discovery, compagno o AI è inclusa in questo studio.

## 2. Metodo e qualità delle evidenze

Domande guida: che cosa deve capire l'utente a colpo d'occhio? Quanto costa raggiungere un dettaglio? Dove cerca una preferenza? Sa distinguere un dato vecchio da un dato attuale? Capisce un'icona senza aiuto? Riesce a tornare al punto di partenza dopo un avviso?

Classificazione usata nel dossier:

| Tipo | Cosa permette di concludere | Cosa non dimostra |
| --- | --- | --- |
| Esperimento o studio sul campo | Effetto osservato nei compiti, partecipanti e dispositivi studiati | Stesso effetto quantitativo su SmartPC |
| Review / meta-analisi | Convergenze, variabilità e limiti di un insieme di studi | Un valore universale di font, densità o numero di voci |
| Linea guida di ente/prodotto | Principio e metodo di progettazione applicabile con adattamento | Prova empirica diretta sul nostro hardware |
| Ispezione del codice | Presenza di una scelta, percorso o limite nei sorgenti | Gravità effettiva percepita o latenza fisica |
| Proposta SmartPC | Ipotesi concreta, basata sul contesto e pronta a essere verificata | Funzione già implementata o risultato PASS |

Per cinque pubblicazioni è stato consultato il testo accessibile nelle sezioni pertinenti; per quattro l'abstract/sintesi primaria disponibile. Alcuni accessi diretti a PMC/editore sono falliti: si è usato il PDF dell'autore, il repository universitario o l'abstract del record primario. Non si attribuiscono metodi o risultati ulteriori ai testi non accessibili.

Le fonti di TV, web e dispositivi mobili sono usate per principi di focus, gerarchia e riconoscibilità. Misure in CSS px, dp, punti, diagonali e distanze di altri apparecchi **non vengono copiate come pixel fisici SmartPC**. Per l'implementazione Qt si usa la documentazione **6.8**, coerente con la board.

La [nota W3C WCAG2ICT](https://www.w3.org/WAI/standards-guidelines/wcag/non-web-ict/) chiarisce l'uso delle indicazioni WCAG nel software non web e i limiti dei sistemi con funzionalità chiusa. Qui è una base di progettazione, non una dichiarazione di conformità o un audit normativo.

### Inventario statico già prodotto

L'[inventario leggibile](ux-consolidation-static-inventory.md) e il [registro JSON con hash delle fonti](evidence/ux-consolidation-2026-10-08/static-inventory.json) rendono ripetibile il confronto con i sorgenti della data indicata:

| Oggetto | Riscontro statico | Implicazione e limite |
| --- | --- | --- |
| Superfici / tema | 56 dichiarazioni; 48 presentazioni esplicite Apple Calm | Tavole e percorsi da verificare sul rendering reale |
| Rete Apple Calm | Sette superfici senza mapping esplicito: overview, devices, detail, router, wifi, ports, settings.network | Qualificare fallback/ereditarietà e coprire nativamente nella nuova revisione; non sono sette bug automaticamente |
| Scena | Anche scene.main non compare tra le presentazioni esplicite | Percorso scene distinto; non assimilarlo alle pagine Rete |
| Impostazioni | 13 sezioni, 97 dichiarazioni di riga incluse condizionali e template | Non sono 97 preferenze o controlli visibili contemporaneamente |
| Registro righe | Non contiene sezioni settings.casa / settings.network, presenti nel contratto delle superfici | Integrare dai controlli/adapter reali; non presumere che manchino le opzioni UI |
| Icone | 22 mapping builtin; 50 forme e 22 alias Apple Calm | Inventario di sorgenti disponibile; resta da completare significato → uso → renderer |

Questo inventario anticipa una parte di U0, senza chiudere l'audit delle schermate o dei controlli generati dinamicamente. L'assenza di una presentazione esplicita è distinta dall'assenza di un percorso funzionante. Durante l'implementazione verificare anche le superfici aggiunte e i sorgenti modificati rispetto agli hash.

## 3. Cosa aggiungono le pubblicazioni scientifiche

| ID | Pubblicazione e materiale consultato | Risultato pertinente e limite | Conseguenza proposta |
| --- | --- | --- | --- |
| S01 | Legge e Bigelow, 2011, review; [testo PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3428264/) | La dimensione angolare e l'x-height descrivono la lettura meglio del solo corpo nominale. L'intervallo studiato riguarda lettura e visione, con variabilità individuale. | Misurare glifi e distanza, non approvare i font da screenshot sul monitor. |
| S02 | Darroch et al., 2005, esperimento; [PDF Glasgow](https://eprints.gla.ac.uk/3220/1/effect_of_age1.pdf) | 24 partecipanti in due fasce d'età su HP iPAQ 640×480; preferenza e prestazione non coincidono sempre. Le taglie in punti e l'hardware storico non sono trasferibili direttamente. | Valutare anche comfort e sforzo, oltre alla lettura corretta; non usare il minimo decifrabile come default. |
| S03 | Dobres, Chahine e Reimer, 2017, esperimento; [PDF autore](https://jdobr.es/pdf/Dobres-etal-2017-Ambient.pdf) | Decisione lessicale con parole italiane, due taglie/polarità e due illuminazioni; 34 partecipanti analizzati. Polarità, taglia e luce interagiscono. Non misura una dashboard a uso libero. | Provare giorno/notte e lettura rapida, separando comfort e correttezza. |
| S04 | Piepenbrock, Mayr e Buchner, 2014, esperimento; [abstract PubMed](https://pubmed.ncbi.nlm.nih.gov/25141597/) | Nel proofreading il vantaggio del testo scuro su fondo chiaro aumenta con caratteri piccoli. È un risultato di quel compito; consultato l'abstract, non l'intero articolo. | Evitare di giustificare microtesti soltanto perché il tema scuro piace; valutare le due palette. |
| S05 | Hou, Anicetus e He, 2022, review; [testo Frontiers](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2022.931646/full) | La letteratura sui lettori anziani varia per dispositivo, lingua, dimensione e spacing; molte prove riguardano testi non latini. | Scala testo reale, nomi leggibili, confronto con visione corretta e distanza abituale; niente unica dimensione «ottimale». |
| S06 | McDougall, de Bruijn e Curry, 2000, serie di studi; [abstract Manchester](https://research.manchester.ac.uk/en/publications/exploring-the-effects-of-icon-characteristics-on-user-performance/) | Concretezza aiuta l'apprendimento iniziale; complessità e distinzione incidono sulla ricerca. Il record primario fornisce l'abstract. | Misurare ambiguità tra simboli simili e comprensione dell'azione; non limitarsi a giudicare l'atlante bello. |
| S07 | Heer e Bostock, CHI 2010, esperimenti; [PDF Stanford](https://hci.stanford.edu/publications/2010/crowd-perception/heer-chi2010.pdf) | Studia codifiche quantitative, dimensione dei grafici e griglia; esistono interazioni fra taglia e scala. I risultati in px del web non fissano l'altezza del grafico sul 3,5″. | Assi/etichette utili, codifiche semplici, griglia sobria e prove con compiti quantitativi. |
| S08 | Iqbal e Horvitz, CSCW 2010, studio sul campo; [sintesi Microsoft Research](https://www.microsoft.com/en-us/research/publication/notifications-and-awareness-a-field-study-of-alert-usage-and-preferences/) | Due settimane di uso notifiche email: valore di consapevolezza e disturbo non coincidono; reazioni diverse fra utenti. Consultata la sintesi degli autori. | Conservare categorie/quiete/inbox; notifiche ordinarie non devono obbligare a cambiare attività. |
| S09 | Scheibehenne, Greifeneder e Todd, 2010, meta-analisi; [abstract editore](https://doi.org/10.1086/651235) | 63 condizioni, 50 esperimenti, 5.036 soggetti: effetto medio dell'eccesso di scelta quasi nullo, con molta variabilità. L'accesso diretto è fallito, ma l'abstract dell'editore era disponibile nei risultati. Non riguarda specificamente menu QML. | Non trattare «meno voci» come legge universale: scegliere mediante compiti e confronti. |

Queste nove pubblicazioni non sono nove prove indipendenti sul prodotto: tre sono sintesi della letteratura e sei lavori empirici; alcune review includono studi citati anche separatamente. L'ampiezza bibliografica non sostituisce l'osservazione di SmartPC.

## 4. Pannello e tipografia: dimensioni reali

### Calcolo preliminare, non misura hardware

Assumendo **diagonale attiva 3,5″, rapporto 960:640, pixel quadrati e mapping 1:1**, la geometria nominale è circa **73,97 × 49,31 mm**, **329,65 ppi**, **0,07705 mm per pixel**. Sono calcoli sulle specifiche fornite, non una verifica dell'area attiva o dello scaling EGLFS.

| `font.pixelSize` nominale | Corpo em teorico in mm | X-height ipotetica se pari al 50% dell'em | Angolo a 50 cm | Angolo a 60 cm |
| --- | --- | --- | --- | --- |
| 18 px | 1,387 | 0,693 | 4,77′ | 3,97′ |
| 22 px | 1,695 | 0,848 | 5,83′ | 4,86′ |
| 26 px | 2,003 | 1,002 | 6,89′ | 5,74′ |
| 30 px | 2,312 | 1,156 | 7,95′ | 6,62′ |
| 34 px | 2,620 | 1,310 | 9,01′ | 7,51′ |
| 40 px | 3,082 | 1,541 | 10,60′ | 8,83′ |
| 48 px | 3,698 | 1,849 | 12,71′ | 10,60′ |
| 54 px | 4,161 | 2,080 | 14,30′ | 11,92′ |

Formula del calcolo: `pitch = diagonale_mm / hypot(960, 640)`; `angolo = 2 × atan(altezza_glifo / (2 × distanza))`. Gli angoli della tabella sono minuti d'arco. L'x-height al 50% è un'ipotesi illustrativa; va misurata per il font/renderer concreto. `pixelSize` non coincide con l'altezza dell'inchiostro del glifo.

La review [S01](https://pmc.ncbi.nlm.nih.gov/articles/PMC3428264/) discute per lettori normalmente vedenti una soglia indicativa intorno a 0,2° di x-height per la lettura fluente. Non la trasformiamo in un minimo universale: lettura di parole isolate, numeri, età, glifi e contrasto cambiano il compito. Il calcolo mostra però perché 18–26 px potrebbero essere troppo piccoli in una dashboard osservata da una scrivania.

**Inferenza numerica per la distanza confermata:** con le medesime ipotesi, 0,2° corrisponderebbe a circa 1,75–2,09 mm di x-height a 50–60 cm, cioè circa 45–54 px di corpo con x-height/em = 0,5. Non è un vincolo universale sui font: è una ragione concreta per includere candidati significativamente più grandi nel confronto.

### Protocollo di calibrazione

1. Misurare diagonale/area attiva e verificare risoluzione, `devicePixelRatio`, scala ed eventuale stretching. Annotare distanza abituale, altezza e inclinazione del dispositivo. Le modifiche CAD presenti nel workspace non sono state esaminate o modificate in questo studio.
2. Misurare nelle catture i glifi `x`, `H`, `0`, `8`, `1`, `I`, `l`, `O`, segni −/+/%, unità e lettere accentate. Controllare il font davvero caricato, non soltanto il nome richiesto.
3. Confrontare una piccola scala di candidati **36/42/48/54 px per le etichette informative principali**, usando gli stessi contenuti a **50 e 60 cm**; includere il layout attuale come riferimento. Numeri e informazioni dominanti possono avere taglie superiori; note secondarie hanno un ruolo distinto e non contengono gli unici indizi di stato. Non sono default già scelti.
4. Confrontare liste da **tre e quattro righe**, con valori principali più grandi e note più corte. Le note essenziali non restano piccole soltanto per far entrare una riga aggiuntiva.
5. Ripetere con illuminazione abituale chiara/scura, palette giorno/notte, luminosità realmente usata e angolo di visione realistico. Non richiedere strumenti di eye tracking o luxmetri per la prima prova; dichiarare quando una condizione non è misurata.
6. Registrare lettura errata, tempo, necessità di avvicinarsi, confusione di simboli e comfort. Scegliere una baseline con margine rispetto al minimo leggibile; prevedere adattamento della composizione se aumenta il testo.

**Distanza abituale confermata: 50–60 cm.** Il confronto principale si svolge a quelle distanze; 30–40 cm verifica la consultazione ravvicinata e non giustifica la riduzione dei testi necessari all'uso abituale. La Home privilegia orologio, meteo e pochi valori grandi; gli approfondimenti possono richiedere lettura più attenta, dichiarando quali contenuti non sono pensati per la lettura rapida a distanza.

### Regole tipografiche proposte

- Pochi ruoli semantici, proporzioni coerenti e font con numeri/glifi chiaramente distinguibili. Numeri tabulari utili nelle colonne, se il font/stack effettivo li supporta; non rendere tutto monospaziato.
- Testo principale in frase normale, senza lunghi paragrafi in maiuscolo. Maiuscole brevi nelle guide solo quando leggibili; apostrofi, accenti e separatori italiani uniformi.
- Valore e unità insieme, nessuna ellissi sul risultato essenziale. Accorciare la descrizione, paginare o aprire dettaglio prima di ridurre il font.
- Titolo lungo su due righe soltanto se la composizione riserva lo spazio; altrimenti etichetta breve più nome completo accessibile nel dettaglio.
- L'interlinea segue il font e non viene compressa per recuperare spazio. La scala testo deve cambiare anche altezza riga, numero di righe e spazio per header/footer.

Sono decisioni di progetto da verificare. La [documentazione Qt Text 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-text.html) descrive metriche/rendering/elisione; non garantisce che NativeRendering o QtRendering sia sempre superiore. Confrontare sul percorso EGLFS reale prima di cambiare il workaround corrente.

## 5. Sistema visivo comune a tutta la UX

La coerenza ha quattro strati: **semantica** (cosa significa), **interazione** (cosa succede), **composizione** (dove lo trovo), **stile** (come appare). Un modulo con gli stessi colori ma focus o ritorno diversi resta incoerente. Le [euristiche Nielsen](https://www.nngroup.com/articles/ten-usability-heuristics/) sono un controllo qualitativo; la proposta seguente è specifica per il prodotto.

| Famiglia di componenti | Parti condivise richieste | Variazioni ammesse |
| --- | --- | --- |
| Header | Titolo locale, contesto, posizione, margini | Icona/identità della macroarea, titolo del dettaglio |
| Schede | Ordine, focus, selezione, lunghezze | Numero e contenuto reali del modulo |
| Riga navigabile | Icona, etichetta, valore, segno di apertura | Numero di righe disponibili secondo layout |
| Controllo | Forma per tipo, valore/unità, disponibilità, feedback | Interruttore, scelta esclusiva, numero, azione |
| Stato dati | Timestamp, disponibilità, errore, aggiornamento | Granularità del singolo provider/capacità |
| Grafico | Assi, unità, legenda, periodo, buchi | Tipo di misura e serie disponibili |
| Footer/guida | Azioni effettive, posizione e gerarchia | Comandi pertinenti alla vista |
| Vuoto/errore | Titolo breve, spiegazione, azione utile | Fonte assente, non configurata, errore, nessun evento |

Ogni tema ha proprie composizioni, ma i token e componenti che svolgono lo stesso ruolo devono rispettare la stessa grammatica interna. Evitare tre copie indipendenti della logica di impostazioni o stato dati. Il contratto Theme resta il ponte dei dati e delle azioni.

### Contrasto e colore

Obiettivo prudente per il testo informativo: **4,5:1**, senza applicare automaticamente l'eccezione CSS per testo grande a un piccolo pannello fisico. Per gli indicatori essenziali di focus/controllo: **3:1** rispetto ai colori adiacenti pertinenti. Verificare le coppie dei token giorno/notte e il risultato reale, soprattutto font sottili. [Testo W3C](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [contrasto non testuale W3C](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).

Separare accento, focus, avvertimento e criticità. Rosso/giallo/verde non sono l'unico canale: usare label, simbolo, forma o tratteggio. «Precedente» non diventa invisibile perché trattato come nota decorativa. L'alert ufficiale conserva il proprio significato anche in un tema personale.

### Tavole di revisione

Produrre tavole omogenee delle 56 superfici di baseline e di quelle aggiunte, con dati sintetici comparabili, per ciascun tema. Includere schermate reali e overlay, non soltanto Home. Evidenziare divergenze in header, body, righe, font, guide, unità e stati. Valutare anche il percorso continuo: aprire, aggiornare, scorrere, ricevere un avviso, tornare.

## 6. Architettura informativa e impostazioni

La [progressive disclosure NN/g](https://www.nngroup.com/articles/progressive-disclosure/) aiuta a differire opzioni specialistiche, purché le frequenti restino visibili e l'accesso sia chiaro. La guida [gerarchie piatte/profonde](https://www.nngroup.com/articles/flat-vs-deep-hierarchy/) ricorda il costo di percorsi profondi. Il [tree testing](https://www.nngroup.com/articles/tree-testing/) permette di confrontare etichette e destinazioni prima della grafica.

### Due alternative da confrontare

| Alternativa | Indice | Vantaggio ipotizzato | Rischio da verificare |
| --- | --- | --- | --- |
| **A · sei gruppi** | Schermo, Aspetto, Moduli e Home, Avvisi, Servizi collegati, Dati e aggiornamenti | Linguaggio orientato ai compiti, separazione comune/moduli | «Servizi» può essere meno riconoscibile di Casa/Rete; preferiti lontani dal modulo |
| **B · otto gruppi diretti** | Schermo, Aspetto, Moduli e Home, Avvisi, Account ChatGPT, Casa, Rete, Dati e aggiornamenti | Accesso diretto ai moduli e loro preferenze | Più voci; sovrapposizione percepita fra stato del servizio e refresh |

L'ordine qui è un candidato stabile, non ordinato dinamicamente secondo la frequenza. Il numero di gruppi si decide dopo il confronto. Per quattro righe/pagina entrambe le alternative richiedono due pagine; confrontare quindi tasti e comprensione, non soltanto il numero di voci. Il risultato di [S09](https://doi.org/10.1086/651235) invita a non ricavare una legge generale dall'idea di «troppe scelte».

**Correzione al primo raggruppamento:** mantenere i preferiti Casa/Rete vicino al loro modulo è un candidato da confrontare con la collocazione in Contenuti. La visibilità della macroarea e l'inclusione in Home sono controlli di «Moduli e Home»; un collegamento contestuale può aprire la stessa preferenza canonica. Informazioni rimane autonoma e non viene nascosta negli avanzati.

### Grammatica dei controlli

| Tipo | Esempio | Presentazione/azione proposta |
| --- | --- | --- |
| Apri pagina | Impostazioni Rete | Titolo + descrizione breve + indicatore di apertura; 5 apre |
| Booleano immediato | Modulo visibile | Stato esplicito, controllo booleano; 5 cambia, esito dopo salvataggio |
| Scelta esclusiva | Luminosità automatica/manuale | Scelta unica riconoscibile; 4/6 regolano solo nella riga pertinente |
| Valore numerico | Livello giorno | Valore, unità, passo, limiti; 4/6 regolano, non aprono un altro contesto |
| Operazione asincrona | Aggiorna fonte | Stato operazione distinto dal valore acquisito; rifiuto/attesa/esito leggibili |
| Bozza con anteprima | Cambio tema | Anteprima, Salva, Annulla; azione finale esplicita |
| Azione di ripristino | Ripristina Base | Descrizione precisa di ciò che cambia; recupero coerente con la bozza |

Le guide [GOV.UK radios](https://design-system.service.gov.uk/components/radios/) e [checkboxes](https://design-system.service.gov.uk/components/checkboxes/) distinguono scelta singola e multipla e richiedono etichette/hint comprensibili. Qui prendiamo la semantica, non i controlli HTML o il flusso di un servizio pubblico. Una sola opzione automatica può disabilitare valori manuali conservati, senza cancellarli.

I controlli avanzati restano raggiungibili e nominati con precisione. L'uscita da una bozza evita salvataggi impliciti; per controlli immediati un errore di persistenza non deve lasciare il messaggio «Salvato». Ridurre le richieste di conferma nelle azioni reversibili; mantenere chiaro l'effetto di ripristini e azioni con perdita reale di preferenze.

### Mappa minima da preparare in U0

Una riga per controllo: ID semantico, sorgente, valore, tipo, destinazione attuale/proposta, frequenza attesa, comportamento di 4/6/5/7, persistenza, disponibilità, feedback, compatibilità tema e rollback. L'ordinamento o la rimozione di una voce non cambia la sua azione per coincidenza di indice. L'adapter [PublicSettingsRows.js](../components/PublicSettingsRows.js) usa già ID/target per vari gruppi: conservare questa separazione e verificare i rami che si basano ancora su posizioni.

## 7. Sport, focus e tastierino

La proposta resta **Oggi → Meteo → Account → Sport → Casa → Rete**, con Sport come unica macroarea. Calcio, F1 e MotoGP conservano provider, cache e ID dei contenuti. Fantacalcio resta nel dettaglio partita, dove la semantica dei voti ha contesto.

La [navigazione TV Android](https://developer.android.com/training/tv/get-started/navigation) è pertinente al D-pad: tutti i controlli raggiungibili, focus uniforme e Back prevedibile. Dimensioni TV e prescrizioni di wrap non vengono copiate: le liste SmartPC possono fermarsi ai confini, mentre il carosello può continuare circolarmente. [Navigazione coerente W3C](https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html) e [focus non nascosto](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) supportano ordine stabile e selezione visibile.

### Regole da verificare come state machine

- Un solo significato prevalente di 4/6 e 2/8 per livello, indicato dalla guida. Nell'indice Sport 4/6 cambia macroarea, 2/8 seleziona disciplina, 5 entra; dentro la disciplina 4/6 cambia scheda.
- 7 torna al livello precedente senza loop e ripristina la selezione valida. 1 resta Home; 3 Avvisi; 9 Menu, rispettando gli urgenti già previsti.
- Focus e selezione non sono la stessa cosa: una scheda attiva rimane riconoscibile quando il focus passa alle righe; una riga può essere selezionata senza che 5 sia valido se non apre un dettaglio.
- Nessun pulsante solo touch irraggiungibile dal keypad; nessuna opzione disabilitata sembra attivabile. La guida non propone un'azione che il contesto non supporta.
- Al rientro da menu/avviso restano disciplina, scheda, pagina ed entità. Se l'entità scompare, focus sul vicino valido e dettaglio chiuso/qualificato; non mostrare un altro dispositivo come se fosse quello selezionato.
- Alla prima interazione cessano rotazioni automatiche della panoramica. Per eventi/programmi cambiati, aggiornare i dati senza sottrarre il controllo all'utente.
- Verificare pressioni rapide, Home/Back durante una transizione, input con loader in preparazione e scollegamento/ricollegamento fisico del keypad. Non introdurre un debounce arbitrario senza evidenza.

La [guida W3C su pausa e aggiornamenti automatici](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html) è un riferimento per il controllo dei contenuti variabili. La regola SmartPC proposta preserva i dati aggiornati ma evita che cambia pagina o focus mentre si sta leggendo.

## 8. Icone: copertura, distinzione e generazione

Il sistema corrente comprende [catalogo](../icons/catalog.json), [AppIcon](../components/AppIcon.qml), geometrie e [sorgenti Apple Calm](../../theme-projects/apple-calm/design/icon-source.json). Apple Calm contiene network, ma `familyIcon()` non associa `network`; risolvere il collegamento prima di generare un asset duplicato.

La [guida NN/g Icon Usability](https://www.nngroup.com/articles/icon-usability/) raccomanda etichette per chiarire il significato; il [metodo di valutazione](https://www.nngroup.com/articles/how-to-test-digital-icons/) separa riconoscimento della forma, interpretazione e utilità nel compito. L'[identificazione coerente W3C](https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html) si applica alle funzioni ripetute. La proposta SmartPC conserva testo vicino ai comandi poco ovvi e evita di affidarsi a tooltip hover sul keypad.

### Specifica di produzione

1. Atlante semantico: famiglia, azione, stato, metrica e destinatario; ID stabile, mapping nei tre temi, simboli simili e fallback.
2. Verificare candidati: Sport generale, router/Internet, Wi-Fi, porta Ethernet, dispositivo, storico, salvataggio, anteprima, import/export. Non tutti sono necessariamente assenti: la matrice decide.
3. Un sistema di griglia, contorni, peso ottico, terminazioni e margini per ciascuna famiglia grafica. Un'icona generale Sport non coincide soltanto con il pallone; le discipline restano riconoscibili.
4. Estendere sorgenti vettoriali/geometrie esistenti e rigenerare l'atlante in una nuova revisione del bundle. Non inserire un mosaico di icone prese da set incompatibili o immagini generate isolate.
5. Confrontare taglie iniziali 24/32/40 px e, se il pannello lo richiede, una taglia più grande; simboli scelti/focused/disabilitati, giorno/notte. La [guida Google Material Symbols](https://developers.google.com/fonts/docs/material_symbols) spiega l'adattamento ottico della forma al variare della taglia; non implica importare un font completo o copiare i dp.
6. Test di significato a due livelli: «che cosa rappresenta?» e «che cosa succede premendo?». Prove in contesto a parità di etichetta/posizione. S06 suggerisce attenzione alla complessità persistente, oltre alla familiarità iniziale.

Nessun simbolo generico unknown nei percorsi normali. Stato offline, dato precedente e refresh non sono rappresentati dallo stesso simbolo ambiguo. La coerenza non richiede silhouette uguali per significati diversi: richiede una grammatica comune con differenze percepibili.

## 9. Stato dati, feedback, vuoti e recupero

Separare **validità/freschezza del dato** e **stato dell'operazione**. Durante un refresh il valore può restare precedente; «in corso» non lo rende attuale. Fonte, timestamp e problema di persistenza sono distinti. La [guida W3C sui messaggi di stato](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) tratta la comunicazione degli esiti senza spostare necessariamente il focus; qui il principio è applicato al feedback QML, senza affermare supporto assistivo già implementato.

| Stato | Messaggio breve candidato | Comportamento |
| --- | --- | --- |
| Richiesta accettata | Aggiornamento avviato | Dati validi ancora visibili, focus invariato |
| Richiesta accodata | Aggiornamento in attesa | Nessuna seconda acquisizione duplicata |
| Cooldown | Puoi aggiornare tra … | Motivo e tempo disponibili, senza finto successo |
| Nuovo dato confermato | Aggiornato alle … | Timestamp effettivo, solo capacità aggiornate |
| Errore con dato salvato | Offline · dato del … | Ultimo dato mantenuto e qualificato |
| Errore di salvataggio | Dato ricevuto · salvataggio non riuscito | Dato in memoria disponibile, durata offline non promessa |
| Mai acquisito | Dati non disponibili | Nessuno zero inventato; azione utile se esiste |
| Servizio non configurato | Configura … | Collegamento alle impostazioni pertinenti, senza dettagli segreti |
| Lista davvero vuota | Nessuna partita in programma / Nessun preferito | Spiegazione specifica, non errore generico |

Le soglie [NN/g sui tempi di risposta](https://www.nngroup.com/articles/response-times-3-important-limits/) sono euristiche per il feedback, non SLA della board: rendere percepibile il comando rapidamente, mantenere progressi/esito e consentire il ritorno. Non simulare una percentuale di progresso se il backend non sa stimarla; non usare uno spinner permanente per una fonte non configurata.

Per ogni parola «Online», «Aggiornato», «Salvato», «Live», «Connesso» associare una condizione documentata. «Rileggi Account» controlla dati provenienti dal PC; «raggiungibile secondo router» non dimostra presenza fisica; «link Wi-Fi» non è velocità Internet; voto provvisorio non è pubblicato. Semplificare il testo senza cancellare queste distinzioni.

## 10. Grafici e numeri

Il grafico serve a rispondere a una domanda: traffico crescente, picco, periodo o interruzione. Il valore corrente/principale resta leggibile senza dover dedurre un numero da una linea. La scelta grafica usa **valore + trend + contesto**; non aggiunge decorazioni prive di funzione.

Lo studio [S07](https://hci.stanford.edu/publications/2010/crowd-perception/heer-chi2010.pdf) mostra che taglia e griglia influenzano l'accuratezza nei compiti sperimentali. Le [palette Carbon](https://www.carbondesignsystem.com/building-blocks/data-visualization/color-palettes) distinguono colori categoriali, sequenziali e di stato. Non trasferiamo palette aziendali né le altezze in px dello studio senza prova sul pannello.

### Correzioni proposte per lo storico Rete

- Sostituire il font Canvas fisso con font/metriche del tema, oppure rendere le etichette attraverso componenti testuali coerenti; scelta tecnica dopo confronto di qualità/costo.
- Asse temporale con inizio/fine reali e pochi riferimenti intermedi leggibili. Periodo salvato immutato quando il dato è precedente.
- Asse dei valori con unità, zero e massimo comprensibili; scalatura esplicita e coerente fra RX/TX della stessa vista. Non sovrapporre grandezze con unità incompatibili su una scala unica.
- Distinguere le due serie con nome e colore, e candidato tratto pieno/tratteggiato; associare la legenda al disegno. Verificare anche in grigio e con simulazioni di differenze nella percezione dei colori, senza trattarle come prova clinica.
- Reset, campione mancante e periodo non raccolto creano buchi, non valori zero o interpolazioni rassicuranti. La riduzione dei punti mantiene picchi/discontinuità già previsti dal backend.
- Togliere dalla vista principale note ripetitive su algoritmi; «Dati mancanti» breve vicino al grafico e dettaglio tecnico consultabile quando utile.
- Durate in minuti/ore/giorni, byte/bit espliciti e formati italiani coerenti. Dati router e Orange Pi chiaramente identificati. Nessuna precisione decimale superiore al significato reale della misura.

Confrontare due compiti: «Quale serie ha avuto il picco maggiore e quando?» e «Questo grafico arriva ad adesso o è salvato?». Un grafico esteticamente ordinato che induce risposte sbagliate non passa la review.

## 11. Avvisi, movimento e attenzione

L'inbox conserva storia, stato di lettura e fonte; i banner sono una forma di interruzione. La sintesi dello studio [S08](https://www.microsoft.com/en-us/research/publication/notifications-and-awareness-a-field-study-of-alert-usage-and-preferences/) sostiene la distinzione fra consapevolezza e obbligo di cambiare attività; non trasferisce i risultati quantitativi dall'email a Sport/Meteo.

Proposta: poche interruzioni ordinarie, categorie/quiete conservate, urgenti chiaramente prioritari. Avvisi consecutivi non cambiano arbitrariamente la pagina di lavoro; tornare dal dettaglio ripristina selezione e scroll. Lo stato «non letto» non si confonde con la gravità o con il fatto che l'evento sia ancora attivo.

Animazioni brevi comunicano il rapporto fra livelli e cambiamenti. Ridotto/Disattivo preservano layout, focus ed esito. Evitare lampeggi, movimento continuo e rotazione della pagina durante lettura/input. Un aggiornamento numerico non richiede spostamento di tutta la tessera. La pausa riguarda il movimento/paginazione automatici, non spegne indiscriminatamente le fonti necessarie agli avvisi.

## 12. Backend e rendering: ottimizzare il lavoro giusto

La [guida performance Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-performance.html) descrive costi di binding, sequenze, layout testo e immagini; la [guida debug/profiling](https://doc.qt.io/qt-6.8/qtquick-debugging.html) offre strumenti per individuarli. L'applicazione concreta è un percorso di misura, non un elenco di flag da abilitare.

| Area | Ipotesi da misurare | Vincolo conservato |
| --- | --- | --- |
| Segnali/contesti | Invalidazioni duplicate, snapshot ricostruiti senza cambiamenti | Nuovo timestamp e stato di età devono arrivare quando cambiano davvero |
| Modelli | Reset completo dove basta aggiornare i ruoli | ID/stato di selezione e record rimossi gestiti correttamente |
| Testo | Layout/parsing ripetuti, font fallback o caricamenti | Niente riduzione della leggibilità per guadagnare un numero |
| Immagini/icone | Dimensione texture, atlante, ricaricamenti | Copertura/fallback e revisione immutabile |
| Timer | Tick troppo frequenti per il dato esposto | Freschezza e avvisi non vengono congelati |
| Worker | Scrittura GUI, richieste concorrenti/obsolete, chiusura | Validazione/persistenza e ultimo dato confermato |
| Viste nascoste | Lavoro visivo inutile | Acquisizioni di fondo previste dalla policy restano possibili |

Misurare freddo/caldo, navigazione, vista Rete aperta/chiusa, provider lento, grafico, menu e avviso. Distinguere timestamp del comando, stato UI, caricamento, frame software e latenza fisica. Non trasformare `frameSwapped` o timer GUI in misure GPU/input-to-pixel.

Confronti prima/dopo con stessi dati/tema e workload; quota delle chiamate e memoria sono parte del risultato. Ottimizzazioni tramite layer, atlanti più grandi, nuovi font o pre-caricamento hanno costi: il fatto che il frame sembri più fluido non dimostra consumo inferiore. Il problema Meteo/persistenza già individuato resta prioritario nella 0.8.2.

## 13. Analisi per modulo e dettagli applicabili

| Area | Domanda primaria della vista | Contenuto dominante | Approfondimento e qualifiche |
| --- | --- | --- | --- |
| Oggi | Che ora è e cosa conta adesso? | Ora/meteo, evento pertinente se esiste | Nessuna tessera vuota; priorità e fonte dell'evento verificabili |
| Meteo | Come è adesso e nei prossimi giorni? | Temperatura/condizione, tre giorni leggibili | Allerta ufficiale distinta; data e luogo reali |
| Account | Quanto uso ho e quando si resetta? | Finestre denominate, quota/tempo e reset | Origine PC, freschezza, credito assente omesso |
| Sport indice | Quale disciplina voglio consultare? | Tre sezioni abilitate e prossimo evento | Nessun evento live simulato, nessun quarto provider |
| Calcio | Prossima partita/risultato della mia squadra? | Squadre, competizione, ora/punteggio | Stagione, rinvio, statistiche, voti/SV/provvisorio |
| F1/MotoGP | Prossima sessione o ultimo esito? | Evento e programma leggibili | Sessione, pilota, DNF/DNS, penalità, timing qualificato |
| Casa | Come stanno i dispositivi che mi interessano? | Preferiti e stato principale | Offline/hub/precedente distinti; nessun comando nuovo |
| Rete inventario | Quali dispositivi sono osservati? | Alias/nome, collegamento, stato qualificato | MAC/IP tecnici nel dettaglio, discrepanze di copertura esplicite |
| Rete Internet | Stato collegamento e traffico? | WAN corrente qualificata e contesto | Non speed test; fibra/sensori del router identificati |
| Wi-Fi/porte | Dove è collegato e che traffico ha? | Entità, link e direzione comprensibile | Porta aggregata ≠ singolo host; segnale raw non percentuale inventata |
| Avvisi | Che cosa richiede attenzione? | Titolo, gravità, ora, lettura | Fonte/corpo nel dettaglio, ritorno conservato |
| Impostazioni | Dove cambio questa preferenza? | Etichetta del compito e valore | Sede canonica, feedback, avanzate raggiungibili |
| Informazioni | Quale software/dispositivo/stato sto usando? | Versione core/tema/API e dispositivo | Pagina di lettura; nessuna acquisizione implicita |

Non creare una pagina per ogni campo disponibile. Un dettaglio aggiunto deve aiutare a decidere o comprendere, e usare una fonte già acquisita nel perimetro. Nomi completi e dati tecnici restano recuperabili quando le sintesi sono abbreviate.

## 14. Protocollo di valutazione prima dell'implementazione completa

### A. Inventario e baseline

Registro delle superfici, dei controlli e delle icone; mappa dei percorsi; condizioni del display; catture attuali. Registrare ogni difetto come «codice verificato», «cattura storica da riprodurre», «ipotesi» o «prova fisica». Nessuna esperienza simulata viene attribuita all'utente.

### B. Confronto delle impostazioni

Tree test qualitativo sul sistema attuale, A6 e B8, con compiti senza indizi della categoria: abbassare la luce notturna, nascondere MotoGP senza Calcio, scegliere la squadra, fermare banner Account, cambiare tema, aggiornare Rete, trovare il problema Casa, capire un dato Account precedente. Non spiegare prima la destinazione corretta. Se l'utente principale confronta più alternative, la familiarità acquisita contamina i tentativi successivi: alternare l'ordine e interpretare il confronto come esplorazione formativa. Un confronto quantitativo tra strutture richiederebbe gruppi indipendenti e un campione adeguato, come descrive la fonte NN/g; non è previsto né attestato in questo dossier.

Registrare prima scelta, raggiungimento, ritorni, tempo e confusione. Il test può iniziare con l'utente principale; eventuali altre persone richiedono disponibilità e autorizzazione separate. Una prova con una sola persona non dimostra percentuali di successo di una popolazione. La verifica automatica del routing non sostituisce il tree test umano.

### C. Prova visiva e di input sul dispositivo

Compiti rappresentativi ripetuti con layout attuale e candidati, a parità di dati. Per i confronti visivi cambiare una variabile principale per volta; per la scelta finale verificare la composizione completa. Nessun mockup generato è equivalente a rendering EGLFS.

| Compito | Errore da intercettare | Misura |
| --- | --- | --- |
| Leggere temperatura, quota, punteggio e data | Segni/unità/glifi confusi | Correttezza, tempo, avvicinamento |
| Aprire Calcio, F1, MotoGP e ritornare | Terzo asse implicito, tasti ambigui | Passaggi, ritorni e focus finale |
| Nascondere una disciplina | Visibilità persa nella migrazione | Stato prima/dopo e reboot |
| Cambiare tema e annullare | Bozza salvata implicitamente | Esito e preferenza persistita |
| Aggiornare durante timeout/disco non scrivibile | Falsa conferma o blocco | Stato comando, dato e persistenza |
| Leggere grafico con buco/reset | Zero/interpolazione implicita | Interpretazione corretta di serie/periodo |
| Ricevere avviso in una lista | Focus rubato o posizione persa | Selezione/scroll dopo il ritorno |
| Scorrere ultima pagina con nome lungo | Riga irraggiungibile o valore troncato | Copertura e numero tasti |
| Aprire fonte mai configurata | Spinner infinito o «vuoto» fuorviante | Messaggio e azione proposta |

### D. Matrice e criteri di accettazione

Tre temi, giorno/notte, Normal/Reduced/Off e scale realmente offerte. Controlli automatici sull'intera copertura pertinente; percorsi fisici rappresentativi scelti per rischio, senza ripetere ogni combinazione storica se non cambia.

- Nessun valore essenziale tagliato; nessuna sovrapposizione; focus della selezione visibile e contrasto dei token registrato.
- Stesso significato delle azioni e disponibilità dei dati nei tre temi; fallback corretti per bundle precedenti.
- Ogni preferenza ha sede canonica, modello di salvataggio e motivo quando disabilitata; migrazione/rollback provati.
- I compiti frequenti non peggiorano senza un beneficio chiaro e documentato. Se il nuovo indice richiede più tasti, verificare che migliori leggibilità/orientamento e riduca errori: una media globale non nasconde una regressione critica.
- No falsa disponibilità/zero/live; dato precedente leggibile, aggiornamento e errore distinti.
- Nessun nuovo warning QML e nessuna acquisizione provocata dalla sola grafica; budget tecnici fissati sulla baseline e confrontati con workload uguale.
- Report finale con risultati numerici dove misurati, osservazioni umane, difetti residui e ambito. Backup, manifest e reboot come nel piano di consolidamento.

Non fissare «95% di successo», «tutti leggono in due secondi» o «massimo cinque utenti bastano» senza disegno di studio e campione adatti. Per la prima iterazione bastano criteri operativi trasparenti e confronto ripetibile, senza falsi risultati statistici.

## 15. Nuove attività per le due release

| ID | Attività concreta | Dipendenza / evidenza | Release |
| --- | --- | --- | --- |
| R01 | Scheda geometria/scala/glifi e distanza | Misura pannello, screenshot/font reali | 0.8.3 U0/U1 |
| R02 | Confronto testo/lista attuale vs candidati | R01, compiti identici | 0.8.3 U1 |
| R03 | Comparazione Impostazioni A6/B8 | Inventario controlli e tree test | 0.8.3 U0/U1 |
| R04 | Mappa dei controlli per ID e persistenza | Nessuna opzione persa; verifiche adapter | 0.8.3 U2/U3 |
| R05 | Matrice di stati per componente/tema | Catture e routing con errori/vuoti | Entrambe |
| R06 | Correzione mapping/titoli Rete Apple Calm | Simbolo esistente, nuovo mapping verificato | 0.8.2 C3 |
| R07 | Revisione font/assi/legenda del grafico | Codice Canvas verificato, confronto render | 0.8.3 U3 |
| R08 | Tavola icone e test di significato | Mapping, forme simili, nuove sorgenti | 0.8.3 U1/U3 |
| R09 | Focus stabile con refresh/eventi/record rimossi | State machine e keypad reale | Entrambe |
| R10 | Vocabolario dati/operazioni/formati | Fonte, timestamp, unità e esiti | Entrambe |
| R11 | Prove palette/scala nelle condizioni d'uso | R01/R02 e coppie di contrasto | 0.8.3 U1/U4 |
| R12 | Profiling mirato con workload uguale | Qt 6.8, metodo dichiarato | 0.8.2 C0/C2 |

La sequenza **0.8.2 → 0.8.3 → 0.9** resta valida. Il dossier amplia la qualità delle decisioni e dei collaudi, non il numero di moduli o provider da sviluppare. Le lacune di quota/live/copertura fisica restano dichiarate nelle schermate interessate e nei report.

## 16. Registro delle 23 fonti di linee guida e metodo

I nove riferimenti scientifici S01–S09 sono registrati nella sezione 3. Le seguenti fonti completano il corpus di 32 documenti; tutti i link sono fonti primarie dell'ente, degli autori o del prodotto. Consultazione: **8 ottobre 2026**.

| ID | Fonte consultata | Uso e limite |
| --- | --- | --- |
| G01 | [W3C WCAG2ICT overview](https://www.w3.org/WAI/standards-guidelines/wcag/non-web-ict/) | Adattamento al non web; nota informativa, non certificazione |
| G02 | [W3C Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | Contrasto testo; non conversione automatica CSS→pannello |
| G03 | [W3C Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) | Controlli, focus e grafica significativa |
| G04 | [W3C Consistent Identification](https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html) | Funzioni ricorrenti riconoscibili |
| G05 | [W3C Consistent Navigation](https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html) | Ordine e orientamento stabili |
| G06 | [W3C Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) | Selezione visibile con overlay e footer |
| G07 | [W3C Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html) | Controllo di movimento/aggiornamenti automatici |
| G08 | [W3C Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) | Esito senza spostamento arbitrario del focus |
| G09 | [Nielsen: Ten Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) | Revisione qualitativa della coerenza; non SLA |
| G10 | [NN/g Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | Frequente vs specialistico, accesso evidente |
| G11 | [NN/g Tree Testing](https://www.nngroup.com/articles/tree-testing/) | Verifica di etichette/destinazioni prima della grafica |
| G12 | [NN/g Flat vs. Deep Hierarchies](https://www.nngroup.com/articles/flat-vs-deep-hierarchy/) | Bilanciamento ampiezza/profondità |
| G13 | [NN/g Icon Usability](https://www.nngroup.com/articles/icon-usability/) | Significato e label in contesto |
| G14 | [NN/g How to Test Digital Icons](https://www.nngroup.com/articles/how-to-test-digital-icons/) | Riconoscimento distinto da interpretazione |
| G15 | [Nielsen: Response Time Limits](https://www.nngroup.com/articles/response-times-3-important-limits/) | Aspettative/feedback; euristiche storiche |
| G16 | [Android Developers: TV Navigation](https://developer.android.com/training/tv/get-started/navigation) | Focus e ritorno con D-pad; non taglie TV |
| G17 | [Google: Material Symbols](https://developers.google.com/fonts/docs/material_symbols) | Varianti e adattamento ottico; non importazione necessaria |
| G18 | [GOV.UK Radios](https://design-system.service.gov.uk/components/radios/) | Scelte esclusive e hint |
| G19 | [GOV.UK Checkboxes](https://design-system.service.gov.uk/components/checkboxes/) | Scelte indipendenti e label |
| G20 | [Carbon Color Palettes](https://www.carbondesignsystem.com/building-blocks/data-visualization/color-palettes) | Semantica delle palette; non stile da copiare |
| G21 | [Qt 6.8 Performance](https://doc.qt.io/qt-6.8/qtquick-performance.html) | Binding, testo, modelli e immagini |
| G22 | [Qt 6.8 Text](https://doc.qt.io/qt-6.8/qml-qtquick-text.html) | Metriche, elisione e rendering |
| G23 | [Qt 6.8 Debugging](https://doc.qt.io/qt-6.8/qtquick-debugging.html) | Profiling controllato, separato dalla produzione |

Non sono state usate opinioni Reddit, risultati generati o copie di standard non verificati come fondamento delle decisioni. Le pagine non accessibili non sono contate come letture complete. Per S09 l'abstract indicizzato dell'editore è il livello consultato; il link DOI conserva l'identità della pubblicazione.

## 17. Risultato di questa analisi e lavoro restante

**Consegnato ora:** dossier bibliografico, confronto delle evidenze, calcolo fisico condizionato a 50–60 cm, inventario statico con hash e registro delle dichiarazioni, decisioni aggiornate, alternative delle impostazioni, protocollo e attività R01–R12. Piano di consolidamento e MasterPlan allineati. Nessun nuovo PASS di rendering, performance, provider o uso fisico.

**Prima di fissare il design:** misura dell'area attiva/scaling e verifica a 50–60 cm, completamento runtime dell'inventario delle superfici/controlli, comparazione A6/B8 e prova dei candidati tipografici. **Durante l'implementazione:** componenti condivisi, fix, migrazione preferenze, nuove icone ove necessarie, revisione dei temi e verifica sul dispositivo. Le modifiche di altre attività presenti nel workspace restano fuori da questa analisi.
