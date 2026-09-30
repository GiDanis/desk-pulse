# SmartPC · analisi UI/UX e tastierino 3×3 · proposta v2

Questa proposta sostituisce la mappa di navigazione della bozza v1. **Aggiornamento v0.4:** Account ChatGPT entra nel carosello orizzontale; Menu → Impostazioni → Moduli visibili permette di scegliere le famiglie mostrate. La dashboard QML e il tastierino installati sulla Orange Pi applicano ora questa navigazione.

## Decisione consigliata

SmartPC dovrebbe comportarsi come un **display ambientale che diventa un'interfaccia direzionale quando si preme un tasto**. La Home mostra ora e meteo; aggiunge il prossimo evento solo quando esiste. Il tastierino ha una croce direzionale stabile, un tasto OK e un tasto Indietro. Lo scorrimento orizzontale cambia argomento; quello verticale cambia vista dello stesso argomento. Le azioni dentro una vista si aprono con OK e si chiudono con Indietro.

La riga fissa «SMARTPC / COMPANION · MODALITÀ NOTTE» va eliminata. Lo spazio recuperato ospita il dato principale. Una sola riga compatta con **argomento e vista** appare quando serve orientarsi; notte, connessione e aggiornamento appaiono solo se modificano l'interpretazione dei dati.

## Cosa insegnano i prodotti esistenti

| Riferimento | Osservazione dalle fonti ufficiali | Applicazione a SmartPC |
| --- | --- | --- |
| **Apple Watch** | Punta a contenuti leggibili in un'occhiata e interazioni brevi; raccomanda gerarchie poco profonde. | Una vista, un dato dominante e una o due informazioni secondarie. Le pagine di dettaglio devono restare poche. |
| **Android TV / Apple TV** | Frecce, OK e Indietro richiedono un focus visibile e uno spostamento prevedibile; Apple sconsiglia cambi di focus senza azione dell'utente. | Il tastierino usa la geometria 2/4/6/8 come direzioni, 5 come OK e 7 come Indietro. Un bordo o riempimento indica sempre l'elemento selezionato. |
| **LaMetric TIME** | Mostra app informative autonome e usa pulsanti fisici sul dispositivo; offre anche la rotazione automatica delle app. | Il dispositivo deve essere utile senza telefono. La rotazione automatica può essere un'opzione ambientale, mai il comportamento durante la navigazione. |
| **Tidbyt** | Alterna app scelte dall'utente e le mantiene aggiornate; la configurazione avviene nell'app mobile. | La Home può essere passiva e personale. Sul nostro dispositivo, la navigazione manuale resta un percorso completo. |
| **Home Assistant** | Divide una dashboard in viste e le viste in gruppi/schede. | Prendiamo la gerarchia per argomenti, riducendo a un singolo contenuto dominante per vista. |
| **Google Nest Hub / Echo Show** | Separano contenuto ambientale e controlli; Echo Show consente di scegliere le categorie mostrate nella Home. | L'utente deve scegliere quali riepiloghi e notifiche vedere. I gesti touch di questi prodotti non sono un modello di input per il nostro tastierino. |

**Fonti:** [Apple Watch](https://developer.apple.com/design/human-interface-guidelines/designing-for-watchos/), [Apple Focus](https://developer.apple.com/design/human-interface-guidelines/focus-and-selection/), [Apple Remotes](https://developer.apple.com/design/human-interface-guidelines/remotes), [Android TV navigation](https://developer.android.com/training/tv/get-started/navigation), [Android TV focus](https://developer.android.com/design/ui/tv/guides/styles/focus-system), [LaMetric guide](https://lametric.com/sites/default/files/techspecs/2019-12/user_guide.pdf), [Tidbyt](https://tidbyt.com/), [Home Assistant views](https://www.home-assistant.io/dashboards/views/), [Google Nest display](https://support.google.com/googlehome/answer/9137285?hl=en-AU), [Echo Show Home](https://digprjsurvey.amazon.com/csad/help/node/G72DNPRFE2RUHAW7).

La struttura a due assi e la mappa specifica dei tasti sono **deduzioni progettuali per SmartPC**, non comportamenti copiati dai prodotti citati.

## Schemi di comando confrontati

| Schema | Vantaggio | Limite sul nostro prodotto | Giudizio |
| --- | --- | --- | --- |
| Scorciatoie fisse 1–6, come oggi | Una pressione per sei pagine | I tasti non esprimono gli assi; aggiungere viste simili richiede nuove eccezioni e una mappa da ricordare | Utile per il prototipo attuale, debole quando i moduli crescono |
| Croce 2/4/6/8 + OK, Home e Indietro | Movimento spaziale coerente, pochi concetti da imparare, espandibile | Le pagine più lontane richiedono qualche pressione e serve un focus chiarissimo | **Scelta consigliata** |
| Frecce che saltano fra tutte le schede e i comandi visibili | Modello familiare da TV | Su 3,5″ rende lenta anche la semplice lettura di un'altra pagina e spinge a riempire lo schermo di controlli | Solo dentro il pannello di dettaglio/azione |

La soluzione consigliata combina la croce per esplorare le schermate con il focus televisivo **solo dopo** aver premuto OK su un contenuto interattivo.

## Architettura delle schermate

Le famiglie previste nell'asse orizzontale sono Oggi → Meteo → Account ChatGPT → Sport → Casa → PC; **solo le famiglie con provider e schermate pronti** entrano nel carosello. Nella v0.4 sono attive Oggi, Meteo e Account ChatGPT. Menu → Impostazioni → Moduli visibili può nascondere le famiglie disponibili, salvo Oggi che resta sempre raggiungibile. Compagno è una vista di Oggi; Aspetto e dispositivo resta nelle Impostazioni. Una famiglia futura può essere illustrata nella documentazione, senza diventare una pagina vuota nell'uso normale.

Ogni famiglia ha al massimo tre viste principali nell'asse verticale:

| Famiglia | Viste verticali previste |
| --- | --- |
| Oggi | Ora e riepilogo → Giornata → Compagno |
| Meteo | Adesso → Previsioni → Allerte |
| Account ChatGPT | Utilizzo; 2/8 scorrono le finestre quando sono più di due |
| Sport | Prossimo evento → Live, solo quando esiste → Risultati |
| Casa | Panoramica → Stanze; i dispositivi selezionabili si aprono con OK |
| PC | Stato → Attività/notifiche |

Le famiglie visibili formano un carosello circolare; quelle nascoste vengono saltate. La posizione verticale si ricorda separatamente per ciascuna famiglia: tornare a Meteo riapre l'ultima vista Meteo. Il tasto Home riporta sempre a Oggi/Ora. Se si nasconde la famiglia corrente, la dashboard torna a Oggi. Le etichette dei vicini restano una proposta grafica non ancora realizzata nella v0.4.

## Mappa consigliata dei nove tasti

| 1 · HOME | 2 · SU | 3 · AVVISI |
| --- | --- | --- |
| 4 · SINISTRA | **5 · OK** | 6 · DESTRA |
| 7 · INDIETRO | 8 · GIÙ | 9 · MENU |

- **1 Home:** torna a Oggi/Ora da qualsiasi vista; se è aperto un pannello o una conferma, lo chiude prima di tornare.
- **2/8 Su/Giù:** cambiano vista verticale durante la consultazione; in un elenco aperto spostano il focus tra le righe.
- **4/6 Sinistra/Destra:** cambiano famiglia durante la consultazione; in un controllo aperto passano fra campi o regolano un valore quando indicato.
- **5 OK:** apre i dettagli/controlli della vista; dentro un elenco seleziona; davanti a una conferma esegue l'azione.
- **7 Indietro:** chiude il livello corrente e ripristina la vista precedente; al livello principale torna a Oggi/Ora.
- **3 Avvisi:** apre la casella degli eventi da qualsiasi vista; gli eventi urgenti possono aprire un overlay temporaneo con testo breve e azione esplicita.
- **9 Menu:** apre Comandi, Impostazioni e Diagnostica. Impostazioni contiene Aspetto e dispositivo e Moduli visibili.

Il dispositivo USB invia già nove codici distinti e il lettore Python li traduce in posizioni 1–9: la nuova assegnazione richiede la modifica della logica UI, non la riprogrammazione del firmware. **Nessun comando lungo o doppio clic** è necessario: oggi il decoder considera solo la pressione iniziale e le combinazioni lunghe non sono verificate.

I copritasti dovrebbero mostrare le quattro frecce, OK, Home, campanella, Indietro e Menu. Una mappa ricordata solo dallo schermo costringerebbe a guardare il display prima di ogni pressione, perdendo il vantaggio del controllo fisico. Non serve modificare i LED per ottenere questa guida tattile/visiva.

La scelta di 3 Avvisi e 9 Menu prepara le funzioni future; fino a quando l'event engine non c'è, il tasto 3 può mostrare «Nessun avviso» con Indietro ben visibile. I quattro tasti direzionali e OK non cambiano posizione né significato di base.

## Due stati d'interazione, mostrati chiaramente

**Consultazione:** frecce tra famiglie e viste. Il contenuto è perlopiù informativo. OK apre un pannello di dettaglio o azione solo dove c'è qualcosa da aprire. Il focus della pagina è la vista corrente, indicata dal titolo e dagli indici.

**Dettaglio/azione:** le frecce muovono il focus tra voci o regolano controlli, OK conferma, Indietro chiude. Il pannello mostra un'intestazione «SELEZIONA» o «REGOLA» e un focus marcato. Così i tasti 2/8 non hanno due effetti contemporanei. Quando si torna alla consultazione, la posizione nella famiglia resta intatta.

Un comando fisico, per esempio spegnere una presa, deve mostrare prima quale dispositivo verrà modificato e poi lo stato risultante. Un'azione potenzialmente importante richiede un passaggio di conferma. Se un overlay arriva mentre è aperta una conferma, l'azione in corso non viene eseguita né persa silenziosamente.

Avvisi e Menu ricordano vista, scorrimento e focus di partenza: Indietro li chiude e ripristina quel punto esatto. Durante una conferma, 3 e 9 non cambiano schermata; 7 annulla e 1 annulla tornando alla Home. Questo evita azioni sospese in uno stato invisibile.

## Layout consigliato per 960×640 su 3,5″

La risoluzione è alta rispetto alla diagonale: 960×640 su 3,5″ equivale a circa 330 pixel per pollice. Un testo da 20 px occupa circa 1,5 mm in altezza nominale; la leggibilità va giudicata sul pannello alla distanza d'uso, non sul monitor del PC.

La direzione grafica resta **neo-retro sobria**: fondo navy, testo chiaro e verde acqua per focus/stato attivo. Tipografia moderna e nitida per tutti i dati; pixel art riservata al cane e a piccole icone. È una sintesi intenzionale fra la personalità di LaMetric/Tidbyt e la leggibilità richiesta da un display ad alta densità. Ombre diffuse, sfocature e decorazioni animate non aggiungono informazione su questo pannello.

- **Home:** ora e data dominanti, meteo attuale sempre nel contenuto principale. Il prossimo evento compare solo se il motore eventi consegna un evento valido; lo spazio del meteo si espande quando non ce n'è uno. Nessuna tessera vuota, «nessun evento» o spazio riservato permanente. Compagno può comparire come presenza discreta, senza coprire i dati.
- **Barra di contesto:** una riga da circa 48–56 px con il nome dell'argomento e della vista, per esempio «METEO · ADESSO 1/3». Non mostra brand o «modalità notte» in modo permanente.
- **Contenuto:** margini indicativi 28–36 px, un dato dominante per vista, massimo due gruppi secondari. Liste limitate a tre righe visibili; il resto scorre in un pannello aperto.
- **Tipografia iniziale da prototipare:** numero principale 100–150 px, titolo 36–42 px, corpo 30–34 px, suggerimenti dei tasti almeno 24–28 px. Nessun microtesto per funzioni necessarie.
- **Aiuto contestuale:** fascia inferiore con due o tre suggerimenti pertinenti, per esempio «4/6 ARGOMENTO · 2/8 VISTA · 5 APRI». La legenda completa dei nove tasti si apre da Menu → Comandi e appare al primo avvio.
- **Focus:** bordo chiaro, superficie distinta e nome leggibile; il colore da solo non indica selezione. Testo normale con contrasto almeno 4,5:1 come criterio progettuale tratto da [WCAG 2.2](https://www.w3.org/TR/wcag/#contrast-minimum).
- **Animazioni:** transizione direzionale breve, circa 150–220 ms, con feedback immediato alla pressione. La Home ferma non forza rendering continuo; la mascotte si anima nel suo spazio dedicato.

Tre mockup esatti a 960×640 mostrano questa gerarchia senza la vecchia testata: [Home senza evento](./ux-v3-home-base.png), [Home con evento](./ux-v3-home-event.png) e [Meteo/Adesso](./ux-v2-meteo.png). I dati di esempio sono illustrativi. I file SVG omonimi sono le sorgenti modificabili.

### Stati dinamici della Home

La sorgente dello stato offre `nextRelevantEvent` come valore opzionale. Esiste solo per un evento futuro valido che la logica del prodotto ritiene utile mostrare; la UI non inventa un elemento per riempire il layout. Quando è assente, ora e meteo hanno la composizione più ampia. Quando è presente, il meteo si compatta e compare una tessera evento con tipo, titolo e momento. Un evento scaduto o annullato rimuove la tessera. Il passaggio usa una transizione breve senza spostare il focus mentre è aperto un pannello di controllo.

Il meteo mantiene sempre origine, età del dato e stato corrente. Se manca la rete ma esiste una cache valida, la Home mostra il dato con «Offline» e l'ora dell'ultimo aggiornamento; se non c'è alcun dato, mostra «Meteo non disponibile» al posto di temperatura fittizia. Gli avvisi prioritari usano un overlay temporaneo e, alla chiusura, ripristinano la vista e il focus precedenti. Il cane cede sempre spazio agli avvisi.

Account ChatGPT è una famiglia di consultazione nel carosello, con piano, finestre d'uso, crediti solo quando restituiti dalla fonte e ora dell'ultimo aggiornamento. Dati mancanti o vecchi vanno dichiarati. L'utente può nasconderla da Impostazioni → Moduli visibili; ciò non elimina la cache né interrompe la sincronizzazione. Un avviso di soglia può arrivare nella casella Avvisi quando il motore eventi esiste; non occupa una tessera fissa della Home.

### Collegamento al MasterPlan

- **v0.3:** fissare componenti, griglia, navigazione e contratto di stato della Home; provare entrambe le composizioni con eventi simulati nel pannello di sviluppo.
- **v0.4:** aggiungere Account ChatGPT nel carosello e la visibilità persistente dei moduli in Menu → Impostazioni, con stato disponibile/assente/vecchio e navigazione coerente con il tastierino.
- **v0.5:** collegare `nextRelevantEvent` e gli overlay al motore eventi reale; rispettare priorità, scadenza, deduplicazione e ripristino della vista precedente.
- **v0.6–v0.8:** attivare Sport, Casa e PC nell'asse orizzontale quando ciascun provider produce dati affidabili; non mostrare pagine vuote solo per completare il carosello.
- **v0.9:** introdurre il cane nelle viste previste, lasciando ora, meteo e avvisi leggibili e prioritari.

## Comportamento quotidiano

1. **Accensione:** si apre Oggi/Ora. Dati non disponibili indicati con «In attesa» o «Offline · aggiornato alle 12:30», senza mostrare valori vecchi come attuali.
2. **Navigazione:** una pressione sposta di un passo esatto. Il titolo e l'indice cambiano insieme al contenuto. Nessuna pagina cambia da sola mentre l'utente naviga.
3. **Ritorno:** Home in un tasto; Indietro chiude prima overlay, poi dettaglio, poi torna a Oggi se si è al livello principale.
4. **Avvisi:** eventi ordinari entrano nella casella e possono mostrare un banner breve; un evento prioritario può interrompere con un overlay leggibile. La chiusura riporta alla vista esatta precedente.
5. **Notte:** il tema abbassa luminosità e saturazione. La modalità si riconosce dall'aspetto; il menu contiene l'eventuale controllo manuale.
6. **Assenza d'interazione:** la vista scelta resta stabile. Un ritorno automatico alla Home o una rotazione di contenuti sarebbero opzioni esplicite, non impostazioni predefinite.

## Percorsi da provare sul dispositivo

| Compito | Sequenza prevista | Obiettivo |
| --- | --- | --- |
| Vedere l'ora da qualsiasi punto | 1 | Una pressione, nessuna ambiguità |
| Aprire Meteo/Previsioni da Home, partendo da Meteo/Adesso | 6, 8 | Due pressioni; il numero varia se Meteo ricorda un'altra vista |
| Vedere gli avvisi | 3 | Una pressione |
| Aprire un dettaglio, poi tornare | 5, 7 | Ripristino esatto della vista |
| Aprire un controllo Casa | raggiungi Casa, 5, scegli con 2/8, 5 | Focus sempre visibile e conferma per azioni rilevanti |
| Trovare l'aiuto tasti | 9, seleziona Comandi | Accessibile senza ricordare pressioni lunghe |

### Cosa cambia rispetto alla bozza v1

- Compagno e Sistema escono dal carosello orizzontale: restano meno famiglie da attraversare.
- Il 7 riceve una funzione precisa e standard: Indietro.
- Il 3 apre Avvisi e il 9 apre Menu; diagnostica entra nel Menu.
- La legenda completa non occupa il bordo delle schermate.
- Si distingue la navigazione tra viste dalla selezione dei controlli.

### Stato dell'implementazione

La mappa dei nove tasti, Oggi/Meteo/Account nel carosello e la scelta dei moduli visibili sono implementate nella v0.4. Le schermate future entrano nel flusso solo dopo avere dati e stati utili. Restano da completare le etichette dei vicini, il motore eventi reale e le famiglie Sport, Casa e PC.
