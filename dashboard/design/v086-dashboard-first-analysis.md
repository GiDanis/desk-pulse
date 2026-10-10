# SmartPC — Dashboard tra gli argomenti, con Apple Calm

**Analisi del 9 ottobre 2026 · proposta 0.8.6 / 0.8.7 · baseline core 0.8.5-rc.1, Apple Calm 1.5.0, Theme API 2.6.**

**Aggiornamento grafico:** il concept verticale iniziale è superato dallo [studio orizzontale 960×640](v086-landscape-graphic-study.md), con tavole native e composizioni derivate da Ora/Meteo/Account. Questa analisi conserva selezione dei dati, navigazione e piano; la geometria aggiornata è nello studio grafico.

La prossima evoluzione deve far capire subito che cosa succede in ciascun argomento. Sport avrà una dashboard per Calcio, Formula 1 e MotoGP; Casa presenterà stati e misure utili; Rete separerà traffico, iliadbox e dispositivi. Il tasto 5 aprirà l'approfondimento della dashboard visibile. Colori, icone, font e carattere di Apple Calm rimangono il riferimento.

**Stato: analisi e concept, non implementazione.** In questa sessione sono stati letti i sorgenti e le prove della consegna precedente. Nessun accesso alla board, richiesta ai provider, cambio tema, installazione o modifica del runtime. La [consegna 0.8.5](v085-settings-implementation-report.md) è la baseline documentata; i suoi campioni di salute sono storici rispetto a questa analisi. [Inventario e hash dei sorgenti esaminati](evidence/v086-dashboard-analysis-2026-10-09/source-audit.json).

## 1. Riscontri nel prodotto attuale

| Area | Comportamento riscontrato nel codice | Miglioramento necessario |
| --- | --- | --- |
| Sport | Main espone una macroarea con una vista DISCIPLINE. SportHub usa righe Calcio/F1/MotoGP con un breve riepilogo. 5 cambia famiglia interna; si incontrano quindi le schede della disciplina. | Le tre discipline diventano tre dashboard consultabili subito. Eliminare la scelta preliminare obbligatoria. |
| Priorità Sport | sportHubRows sceglie una partita futura ordinata per kickoff, oppure il primo evento futuro del racing; non mette in evidenza una diretta qualificata. | Selezione comune: diretta verificata, prossimo appuntamento, ultimo esito pertinente. Usare le sessioni del GP per il prossimo orario. |
| Calcio | SportOverview trasforma partite/classifica in righe di Panel; la tab cambia il contenuto. | Una prima vista sintetica con evento principale, prossimo appuntamento e riepilogo della squadra o del campionato. Liste e classifica complete nell'approfondimento. |
| Racing | RacingOverview riutilizza Panel per calendario, risultati, live e classifica. | Prima vista dedicata a GP/sessione e stato del weekend, poi approfondimento con calendario, sessioni, risultati e classifica. |
| Casa | Due viste Preferiti/Dispositivi; CasaOverview rende fino a quattro schede, con misura principale, stato e dato secondario. Tutti i dispositivi usano blocchi da quattro. | Conservare le schede e aggiungere riepiloghi per funzione, evitando che tutti i dati restino un elenco di dispositivi. |
| Rete | Due viste Panoramica/Dispositivi. Panoramica include Metriche/Dispositivi; le tre schede Metriche sono iliadbox, Wi-Fi e Porte. Traffico e temperature sono già presenti nella scheda principale. | Separare le domande: quanto traffico? come sta la box? quanti record di dispositivi vedo? Wi-Fi/Porte restano dettagli raggiungibili. |
| Navigazione | Casa/Rete: 4/6 cambia vista quando il focus è sulle tab e argomento quando è sui contenuti. Sport: 4/6 cambia le schede della disciplina. | Una regola uniforme sulle dashboard. La diversa modalità nei dettagli deve essere esplicita e verificabile. |
| Occupazione | Shell Apple è 56 px; l'area pagina negoziata recupera il fondo. Panel può ancora riservare 40 px di footer per la fonte e 104 px circa per titolo/sottotitolo. | Non è tutto margine nero: anche intestazioni duplicate e footer generici sottraggono spazio informativo. Concentrare i metadati senza perdere la freschezza. |
| Casa/cloud | casa.moduleState è readOnly; fornisce dispositivi, preferiti, quota/modalità e freschezza. Nessun contratto di comando o raggruppamento per stanza è attestato da questa lettura. | Dashboard di osservazione. Comandi, stanze e storico non vanno presentati come già disponibili. |
| Rete/freschezza | network_core distingue inventario, raggiungibilità secondo box e record precedenti. network_metrics mantiene unità, provenienza e freschezza per capacità. | I conteggi non diventano una prova di presenza; WAN, link e contatori rimangono categorie distinte. |

Sorgenti principali: [Main](../Main.qml), [SportHub Apple](../../theme-projects/apple-calm/bundle/qml/SportHub.qml), [SportOverview](../../theme-projects/apple-calm/bundle/qml/SportOverview.qml), [RacingOverview](../../theme-projects/apple-calm/bundle/qml/RacingOverview.qml), [CasaOverview](../../theme-projects/apple-calm/bundle/qml/CasaOverview.qml), [NetworkOverview](../../theme-projects/apple-calm/bundle/qml/NetworkOverview.qml), [Panel](../../theme-projects/apple-calm/bundle/qml/Panel.qml).

## 2. Ricerca: che cosa adottare e con quali limiti

Sono stati consultati **13 riferimenti primari**, tra articoli degli autori, studi scientifici e documentazione ufficiale. Le applicazioni a SmartPC qui sotto sono scelte di progetto, non risultati sperimentali ottenuti sul nostro display. Consultazione: 9 ottobre 2026. Nessuna copia di asset o di codice di terzi.

| Fonte | Evidenza o principio | Applicazione proposta a SmartPC |
| --- | --- | --- |
| [Bach et al., Dashboard Design Patterns, IEEE VIS 2022 / TVCG 2023](https://arxiv.org/abs/2205.00757) | Revisione di 144 dashboard e workshop di due settimane con 23 partecipanti; analizza schemi e compromessi di spazio, contenuti e interazione. | Definire una grammatica condivisa: stato/numero principale, contesto, approfondimento. Non disegnare nove pagine indipendenti. |
| [Blascheck et al., Glanceable Visualization, InfoVis 2018](https://www.microsoft.com/en-us/research/wp-content/uploads/2018/08/GlanceableVis-InfoVis2018.pdf) | Due studi su smartwatch confrontano barre, donut e barre radiali con 7/12/24 valori. Barre e donut risultano più rapidi delle barre radiali nel compito studiato. | Pochi segnali, valori leggibili e grafici compatti. Il risultato riguarda un confronto controllato: non dimostra che un donut sia la migliore UI per WAN o Sport. |
| [While et al., Glanceable Data Visualizations for Older Adults, CHI 2024](https://arxiv.org/abs/2403.12343) | Replica su persone di almeno 65 anni, con differenze osservate soprattutto nel gruppo 75+. | Non trattare risoluzione elevata come permesso di usare caratteri piccoli. Il testo principale va verificato fisicamente a 50–60 cm; nessun tempo di lettura trasferito dallo smartwatch. |
| [Nielsen, Progressive Disclosure, 2006](https://www.nngroup.com/articles/progressive-disclosure/) | Presentare prima opzioni importanti, rendere disponibili quelle specialistiche su richiesta. | La dashboard è informativa senza aprire un menu; 5 espande. Configurazione e metadati tecnici non occupano la prima vista. |
| [Laubheimer, Dashboards: Making Charts and Graphs Easier to Understand, 2017](https://www.nngroup.com/articles/dashboards-preattentive/) | Dashboard per comprensione rapida; posizione e lunghezza aiutano a leggere quantità, colore e forma aiutano il raggruppamento. | Numeri con unità, barre/linee per relazioni quantitative, testo per gli stati. Nessun tachimetro decorativo. |
| [Home Assistant, Project Grace / Dashboard chapter 1, 2024](https://www.home-assistant.io/blog/2024/03/04/dashboard-chapter-1/) | Griglia e sezioni rispondono ai problemi di prevedibilità della masonry; dimensioni regolari aiutano memoria spaziale. | Griglia stabile, schede che non cambiano posto quando arriva un dato. Più spazio utile senza riordinamento continuo. |
| [Home Assistant, Sections](https://www.home-assistant.io/dashboards/sections/) | Raggruppamento in griglia e visibilità condizionale; il riempimento automatico può cambiare l'ordine. | Sezioni coerenti e condizionali basate sulle capacità configurate; ordine mantenuto durante l'interazione. |
| [Home Assistant, Tile card](https://www.home-assistant.io/dashboards/tile/) | Una scheda combina nome, stato e attributi; le azioni sono configurabili. | Icona + nome + valore/stato + fonte temporale. La scheda Casa può essere leggibile senza essere un interruttore. |
| [Home Assistant, Dashboard views](https://www.home-assistant.io/dashboards/views/) | Le viste possono collegarsi attraverso azioni di navigazione e includere sottoviste. | Dettagli fuori dal ciclo delle dashboard; 7 ricostruisce vista, focus e posizione di origine. |
| [Android TV, Focus system](https://developer.android.com/design/ui/tv/guides/styles/focus-system) | Stati normale, focalizzato, premuto e selezionato distinti; indicatori come bordo e colore. | Usare bordo e superficie Apple esistenti. Distinguere tab attiva da elemento focalizzato. Trasferiamo il principio per D-pad, non le misure in dp da un televisore. |
| [Grafana, Dashboard best practices](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/) | Gerarchia e drill-down, consistenza dei template, evitare refresh non necessari. | DTO sintetici condivisi, priorità deterministica, interesse del provider limitato alla vista consultata. Nessun nuovo polling per ogni scheda. |
| [W3C, Understanding Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | Contrasto del testo: 4,5:1 per testo normale e 3:1 per testo grande, con definizioni specifiche. | Come obiettivo interno adottare almeno 4,5:1 per tutti i testi essenziali, incluse le schede focalizzate; non convertire automaticamente pixel QML in punti CSS. |
| [W3C, Understanding Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) | Il focus non deve risultare completamente nascosto; il documento distingue il minimo dalla visibilità completa. | Obiettivo SmartPC più forte: scheda focalizzata e testo principale interamente visibili, anche con overlay e scala testo massima. |

**Sintesi critica.** Gli studi su smartwatch non equivalgono a SmartPC: cambiano dimensioni fisiche, distanza, visione periferica e input. Le fonti non dicono tutte la stessa cosa sui grafici circolari: il risultato favorevole dei donut in un compito limitato non annulla i limiti di confronto segnalati da NN/g. Per WAN scegliamo numeri e linee con unità, perché la domanda è traffico nel tempo, non quota di un totale. Tutte le fonti orientano il prototipo; solo le prove sul pannello valutano questa applicazione.

## 3. Architettura delle viste proposta

| Argomento | Dashboard nel ciclo principale | 5: approfondimento |
| --- | --- | --- |
| Sport | Calcio · Formula 1 · MotoGP | Dashboard estesa della disciplina, già aperta sul contenuto prioritario; calendario, risultati e classifica come sezioni interne. |
| Casa | Preferiti · Ambiente, se ci sono sensori supportati · Dispositivi | Preferiti: stati estesi; Ambiente: misure dei sensori; Dispositivi: inventario selezionabile. Da qui il dettaglio del dispositivo. |
| Rete | Traffico · iliadbox · Dispositivi | Traffico: storico WAN; iliadbox: stato completo e accessi Wi-Fi/Porte; Dispositivi: inventario e dettaglio LAN. |
| Oggi | Ora · Orologio · Giornata | Evento o riepilogo pertinente, conservando la funzione delle viste attuali. |
| Meteo | Adesso · Previsioni | Dettaglio delle condizioni o del periodo, con allerte rilevanti. |
| Account | Utilizzo | Finestre di limite e dettagli disponibili; nessuna nuova vista obbligatoria. |

Le nove dashboard dei primi tre argomenti sono il **massimo iniziale**, non un obbligo per tutte le configurazioni. Sport mantiene soltanto discipline abilitate; Ambiente appare se esistono sensori normalizzati utili. Un provider configurato ma offline conserva la propria vista con stato precedente: la perdita di rete non deve spostare gli argomenti durante l'uso.

Tre livelli ammessi: **dashboard → approfondimento → entità specifica**, dove il terzo è necessario per una partita, una sessione o un dispositivo. Nessun livello intermedio contenente solo nomi di menu. L'approfondimento deve già contenere informazioni aggiuntive e non replicare la stessa scheda più grande.

## 4. Contratto di navigazione comune

Questa è una modifica proposta al controller, non un comportamento che il solo bundle Apple può garantire. Un tema non deve inventare la semantica dei tasti.

| Contesto | 2 / 8 | 4 / 6 | 5 | 7 |
| --- | --- | --- | --- | --- |
| Dashboard principale | Dashboard precedente/successiva nell'argomento | Argomento precedente/successivo | Apre l'approfondimento della dashboard corrente | Nessun effetto alla radice; mai chiude l'app |
| Approfondimento | Muove il focus/scorre dati | Sezione precedente/successiva, se esiste | Apre l'entità focalizzata o esegue l'azione esplicita | Ritorna alla dashboard di origine |
| Dettaglio di entità | Scorre righe o focus | Tab del dettaglio, se esistono | Solo azione dichiarata; non attiva comandi cloud implicitamente | Ritorna al contesto precedente |

1/Home, 3/Avvisi e 9/Menu mantengono il significato acquisito. Ogni argomento ricorda l'ultima dashboard visitata. Per le dashboard verticali ci si ferma alle estremità; il cambio argomento conserva la policy corrente di avvolgimento. Nei dettagli, le tab mantengono una policy uniforme da verificare con gli altri moduli.

La dashboard di primo livello non richiede di selezionare ogni scheda: 5 ha una destinazione deterministica per l'intera vista. Nel prototipo eventuali pulsanti di apertura delle schede devono convergere nello stesso approfondimento, senza fingere focus diversi che il tastierino non può raggiungere. Dopo 5, i contenuti diventano selezionabili con 2/8. Il ritorno conserva ID di vista/entità e posizione; se l'entità scompare, si sceglie il vicino valido, non una riga casuale.

Pallini discreti per orientamento, nome dell'argomento e della dashboard una volta sola. Nessun footer permanente con tasti, conteggi di pagina o istruzioni. L'aiuto resta in Comandi. Le notifiche urgenti conservano precedenza e ritorno corretto; la rotazione automatica non cambia vista/focus mentre si interagisce.

## 5. Sport: tre viste con informazioni principali

### Calcio

**Domanda:** c'è una partita in corso o quando si gioca la prossima?

- Scheda principale: partita live qualificata, altrimenti prossima partita; squadre, risultato oppure data/ora locale, competizione e stato esplicito.
- Scheda secondaria: prossimo appuntamento quando la principale è live; altrimenti ultimo risultato concluso pertinente.
- Altra scheda: posizione/punti della squadra scelta, se configurata e fornita; altrimenti breve riepilogo del campionato selezionato. Non aggiungere una seconda classifica completa.
- Approfondimento: partite, calendario, risultati, classifica e La mia squadra con i dati già presenti; Fantacalcio resta collegato alla partita dove supportato.

Priorità dei candidati: live della squadra scelta → altro live della competizione selezionata → prossima partita della squadra scelta → prossima partita della competizione → ultimo risultato. All'interno di una categoria usare ordine temporale e ID stabile. Se ci sono più live, mostrare uno e il conteggio degli altri; nessun carosello che interrompa la lettura.

Non dedurre una diretta dall'orario. Il dato normalizzato deve includere stato live, verifica e freschezza adeguata; source.status active da solo può riferirsi al calendario. Il backend attuale disattiva isLive nei dati stale/offline: la nuova sintesi deve mantenere questa garanzia.

### Formula 1 / MotoGP

**Domanda:** quale sessione viene prima, e che cosa sta succedendo nel weekend?

- Principale: sessione effettivamente live e verificata; altrimenti prossima sessione utile del GP, con nome, data/ora locale e circuito.
- Secondaria: prossima sessione distinta dalla principale o ultimo risultato disponibile.
- Altra scheda: leader/posizione di interesse oppure stato del campionato, solo con classifica presente e pertinente alla stagione.
- Approfondimento: dashboard estesa del weekend con tab Sessioni/Calendario/Risultati/Classifica e accesso al timing quando qualificato. MotoGP mantiene distinte le classi previste dal provider; nessuna commistione di classifica gara e mondiale.

Un GP può essere iniziato mentre la gara è domani: selezionare l'evento solo con start futuro perde prove e qualifiche. Serve un selettore basato sulle sessioni, non soltanto sull'inizio dell'evento. Se l'orario è noto ma il feed live manca, mostrare **In programma · live non verificato**, non In diretta. Gli ultimi risultati riportano sessione e stagione.

### Stati senza contenuto prioritario

Calendario presente senza appuntamenti futuri: ultimo esito utile e accesso al calendario. Fonte mai disponibile: messaggio breve e accesso alla configurazione. Fuori stagione: indicazione della stagione effettivamente disponibile. Non cambiare un dato mancante in 0–0, posizione 0 o evento live.

## 6. Casa / IoT: dal catalogo al riepilogo

| Vista | Informazioni immediatamente utili | Approfondimento | Dipendenza |
| --- | --- | --- | --- |
| Preferiti | Fino a quattro dispositivi già scelti; nome, misura/stato principale, secondo dato utile e freschezza per dispositivo. | Schede estese dei preferiti e selezione del dettaglio. | Dati attuali riutilizzabili. |
| Ambiente | Una misura prioritaria nominata e fino a tre letture di temperatura/umidità o movimento realmente supportate; esplicitare a quale dispositivo si riferiscono. | Misure complete, disponibilità e data dell'osservazione per sensore. | Nuova proiezione semantica dei codici normalizzati; non richiede necessariamente nuove API. |
| Dispositivi | Numero di dispositivi nel catalogo, disponibilità cloud corrente o precedente, preferiti e ultimo aggiornamento; mini riepilogo dei dispositivi più utili. | Inventario completo, selezione e metriche del singolo dispositivo. | Conteggi derivabili con regole di freschezza condivise. |

**Scelta della misura di Ambiente:** primo sensore ambientale tra i preferiti, poi ordine stabile del catalogo. Niente media tra stanze o temperature estreme usate come qualità della casa. Se un sensore è diventato temporaneamente offline, mantenere la scheda e il suo ultimo dato marcato precedente. Se non esiste alcun sensore supportato/configurato, Ambiente non viene aggiunta.

La disponibilità è quella riportata dal cloud, non un accertamento sulla LAN. Un interruttore ON riportato non prova che una lampada stia realmente illuminando. I riepiloghi di disponibilità devono distinguere dato corrente, precedente e assente: non basta contare il testo della scheda o un flag salvato.

**Ottimizzazioni da acquisire:** omogeneità delle righe di stato, meno testo di polling ripetuto, fonte breve nel contesto utile, aggiornamento manuale nell'approfondimento con feedback corretto. La dashboard legge snapshot; non avvia richieste a ogni cambio scheda.

**Espansioni successive, con dipendenza esplicita:** raggruppamento per stanza richiede metadati reali o una preferenza locale; storico richiede raccolta/persistenza; consumo energetico richiede contatori e unità affidabili. Non sommare potenze di dispositivi diversi chiamandole consumo totale. I comandi Tuya sono un progetto separato: la baseline attuale è readOnly.

## 7. Rete locale: tre dashboard dedicate

### Traffico

Principale: **Download WAN / Upload WAN**, numeri grandi con unità coerenti. Secondaria: stato WAN riportato dalla box. Terzo elemento facoltativo: mini andamento relativo a un intervallo dichiarato, soltanto quando lo storico qualificato esiste. 5 apre il grafico completo e le finestre temporali già supportate.

Traffico istantaneo non è velocità massima, capacità riportata non è speed test, traffico WAN aggregato non è consumo del singolo dispositivo. Storico mancante: valori e stato usano lo spazio disponibile, senza una cornice vuota per il grafico. Storico con buchi: nessuna linea interpolata tra intervalli mancanti, periodo e unità leggibili. Le due direzioni mantengono etichette, non solo colori.

### iliadbox

Principale: stato Internet riportato, uptime e firmware, con aggiornamento temporale appropriato. Secondarie: sensori termici nominati, Wi-Fi e porte con stato disponibile. 5 apre lo stato completo; da schede esplicite si accede a radio, stazioni, porte e storico.

Nessuna temperatura della box etichettata come Orange Pi. Nessun voto Buona/Scarsa o allarme termico senza soglia documentata. Se il provider pubblica più sensori, scelta stabile e nomi conservati; non chiamare CPU un sensore T1 non identificato. Il catalogo box ha una freschezza diversa dalla WAN: un timestamp unico non rende tutti i valori correnti.

### Dispositivi

Principale: **N record nell'inventario router**; seconda misura **M raggiungibili secondo box**, solo se il conteggio è corrente. Copertura parziale evidenziata con frase compatta. Due/tre dispositivi di interesse o preferiti possono accompagnare i numeri, senza sostituire l'inventario completo. 5 apre l'elenco con filtri espliciti e dettaglio identità/indirizzi/link/osservazioni.

Non usare Dispositivi connessi per un totale che include record storici. Un dispositivo non raggiungibile non è necessariamente spento. Un'associazione Wi-Fi non equivale a un host unico; MAC sulle porte non equivale a numero di PC. Gli stati salvati dopo reboot restano precedenti fino alla lettura valida.

### Costi e frequenze

Traffico in primo piano può usare l'interesse router esistente. In iliadbox servono cataloghi con le loro TTL; Wi-Fi/Porte non vanno raccolti per intero a ogni refresh della dashboard. Una vista fuori schermo non acquisisce tutte le stazioni o lo storico. Le metriche riusano scheduler, cache atomiche e provider esistenti. Eventuali informazioni riassuntive aggiuntive devono essere misurate come incremento reale di richieste, CPU e memoria prima del rilascio.

## 8. Geometria e coerenza Apple Calm

Il precedente schema con principale a tutta larghezza e secondarie sotto è superato. Riferimento aggiornato: [studio grafico, §§3–5](v086-landscape-graphic-study.md). Schermo 960×640 orizzontale, barra 56 px, margini laterali 24 px e fondo 16 px. Identità locale compatta; schede da y=120 a y=624, area 912×504.

Tre famiglie: principale 400×504 affiancata a schede di contesto; griglia 2×2 di schede 448×244; misura principale con grafico e due secondarie. Intervalli 16 px, font/icone/palette Apple esistenti. Fino a quattro secondarie solo se utili; nessuna card di riempimento. Le dashboard restano orizzontali anche con scala massima, adottando composizioni meno dense; lo scorrimento è consentito nei dettagli.

Le tavole sono dimostrative, non catture QML. Ingombri dei testi controllati con i font effettivi; leggibilità fisica, tutte le scale e gli stati rimangono gate distinti prima del rilascio.

## 9. Dati, controller e Theme API

La richiesta non si risolve con sole geometrie Apple: servono nuovi riepiloghi e una navigazione comune nel core. Python possiede normalizzazione e stato; QML presenta i dati e usa azioni pubbliche.

| Intervento | Possibile riuso | Nuovo lavoro |
| --- | --- | --- |
| Sintesi Sport | Partite, squadra, eventi, sessioni, classifica e flag live già esposti. | Selettore deterministico del contenuto prioritario; freschezza separata calendario/live/risultati; proiezione pubblica con ID della destinazione. |
| Sintesi Casa | Preferiti, dispositivi, metriche normalizzate, disponibilità e quota. | Classificazione Ambiente e conteggi qualificati; nessun parsing di stringhe formattate per fare aggregati. |
| Sintesi Rete | Stato WAN, sensori, uptime, firmware, inventario e storico. | Proiezione per dashboard e timestamp per blocco; interesse del provider legato alla vista. |
| Controller | Macroarea Sport separata dagli slot provider, overlay e route esistenti. | Dashboard IDs stabili, navigazione 2/8 omogenea, stato di ritorno e migrazione delle preferenze numeriche se necessaria. |
| Renderer | Shell, schede, iconografia, DTO e azioni di dettaglio. | Componenti di sintesi adattivi; eliminazione della dipendenza dal generico Panel dove non adatto. |
| Contratto | Theme API 2.6 e fallback Base/Functional attuali. | Verificare quali campi/azioni/superfici mancano. Se cambiano i DTO pubblici: revisione API additiva, inventario, fixture, metadati, kit e fallback aggiornati. Non dichiarare 2.6 invariata in anticipo. |

Il riepilogo dovrebbe trasportare: ID dashboard, identità del contenuto principale, valore e unità, stato di verifica, fonte/timestamp, blocchi secondari e destinazione dell'approfondimento. Sono responsabilità da definire nello schema, non nomi di campi già promessi dal contratto.

Non costruire tutte le nove UI contemporaneamente. Mantenere il lifecycle di PageHost/ViewHost, readiness, caricamento tema e supervisore acquisiti nella 0.8.5. Nessuna I/O da QML, aggiornamenti indipendenti per card o timer duplicati. Base e Functional devono interpretare le nuove route anche se l'ottimizzazione visiva parte da Apple. Vecchi bundle: fallback valido, mai indice fuori range o renderer undefined.

## 10. Opportunità ulteriori negli altri argomenti

| Area | Miglioramento applicabile | Confine |
| --- | --- | --- |
| Oggi | Riepilogo evento solo quando pertinente; collegare al dettaglio corretto e conservare ora/meteo come priorità senza eventi. | Non duplicare Giornata o creare un hub con un'altra lista di argomenti. |
| Meteo | Condizioni principali, prossime ore e allerta significativa con stesso rapporto principale/secondario. | Una vista diversa solo se risponde a una domanda diversa; niente pagine quasi identiche. |
| Account | Finestre realmente disponibili, reset e stato della sincronizzazione; dettaglio delle finestre eccedenti. | Nessuna metrica inventata quando il provider non la espone. |
| Impostazioni/Info | Riutilizzare sintesi e nomi di Rete/Casa, collegamenti ai dettagli; configurazione resta separata. | Non ricollocare traffico/temperature nelle impostazioni. |
| Avvisi | Aprire l'entità legata all'avviso e ritornare al contesto precedente. | Conservare inbox, lettura e precedenza degli avvisi urgenti. |

## 11. Piano versione per versione

Le numerazioni sono **proposte da inserire nel MasterPlan**, non versioni implementate o installate.

### 0.8.6 — Dashboard principali e navigazione

1. **A0 · Contratto e prototipo:** definire i DTO mancanti, la mappa dei tasti e le route; prototipo 960×640 delle nove viste massime e dei casi senza dati. Gate: informazioni prioritarie riconoscibili a 50–60 cm e azione 5 comprensibile.
2. **A1 · Sport:** sostituire la scelta preliminare obbligatoria con Calcio/F1/MotoGP; priorità live verificato/prossimo/ultimo, sessioni e destinazioni corrette. Gate: un solo 5 dalla dashboard ai primi dati aggiuntivi.
3. **A2 · Rete:** Traffico/iliadbox/Dispositivi; riuso delle metriche e dell'inventario, stato e timestamp separati. Gate: nessuna falsa presenza o confusione WAN/link; traffico e temperature consultabili senza impostazioni.
4. **A3 · Casa:** Preferiti/Dispositivi e Ambiente quando supportata; schede coerenti e conteggi verificabili. Gate: nessun nuovo consumo quota a causa della sola impaginazione.
5. **A4 · Compatibilità e rilascio candidato:** Base/Functional, bundle precedenti, preferenze e fallback; verifiche locali, EGLFS e confronto di richieste/CPU/memoria. Installazione solo nel seguito autorizzato, con backup/manifest/reboot e gate umano.

Versione Apple separata dal core: candidato aggiornamento del bundle, numero esatto da decidere dopo il contratto. Non cambiare VERSION né manifest runtime durante questa analisi.

### 0.8.7 — Approfondimenti coerenti e rifinitura

1. **B1 · Dashboard estese:** primo approfondimento già informativo, schede selezionabili, tab coerenti per Sport/Casa/Rete; almeno un dato aggiuntivo utile immediatamente visibile.
2. **B2 · Riduzione dei doppioni:** eliminare header/footer ripetuti, tab con contenuti quasi uguali e passaggi che aprono solo un menu; riuso delle sintesi in Info.
3. **B3 · Altri argomenti:** applicare la stessa grammatica a Meteo/Oggi/Account dove porta un miglioramento concreto.
4. **B4 · Affinamento fisico:** scala testo, nomi lunghi, day/night, avvisi, durata dell'interazione e performance misurata sulla board; correggere i risultati del collaudo umano.

Se una dashboard della 0.8.6 richiede la struttura dei dettagli di B1 per funzionare, quel pezzo di B1 viene anticipato: nessuna release che mostra schede con un 5 senza destinazione utile. Storico Casa, stanze e comandi cloud restano fuori da entrambe finché le dipendenze non sono studiate e autorizzate.

## 12. Criteri di accettazione e scenari

| ID | Scenario | Risultato richiesto |
| --- | --- | --- |
| UX01 | Ogni dashboard di Sport/Casa/Rete | Risponde a una domanda concreta senza aprire menu; un dato principale e fino a quattro secondarie utili, oppure mosaico 2×2 per soggetti equivalenti. |
| UX02 | 2/8, 4/6, 5, 7 in tutti gli argomenti | Semantica uniforme nel livello; nessun cambio argomento dipendente dal focus sulle tab. |
| UX03 | Rientro dopo dettagli, avvisi, impostazioni e cambio tema | Dashboard/entità/focus ripristinati per ID; fallback deterministico se manca l'entità. |
| UX04 | 960×640, scala minima/default/massima, nomi lunghi, giorno/notte | Nessun clipping, sovrapposizione ai pallini o footer fantasma; elementi essenziali leggibili. |
| UX05 | Sport con live, prossimo, più live, GP in corso con gara futura | Priorità deterministica; sessione giusta, orario locale e stagione corretta. |
| UX06 | Sport stale/offline/demo o live non verificato | Nessuna falsa In diretta; demo distinta; ultimo dato marcato precedente. |
| UX07 | Casa 0/1/4/>4 dispositivi, 0/1/più sensori, preferiti vuoti | Nessuna scheda fittizia; Ambiente condizionale; dati precedenti non entrano in un totale corrente. |
| UX08 | Rete inventario parziale/storico, contatore zero/null, reset, buchi storico | Null distinto da zero; copertura dichiarata; nessuna presenza o velocità per host dedotta. |
| UX09 | WAN aggiornata con catalogo sensori precedente | Stati/freschezza separati per blocco; nessun badge Aggiornato globale ingannevole. |
| UX10 | Cambio rapido dashboard/tema con reduced motion, urgent e refresh in corso | Lifecycle/watchdog acquisiti rispettati, nessuna QML warning o azione duplicata. |
| UX11 | Dashboard visibili e fuori schermo per sessioni comparabili | Richieste provider conformi alle policy; nessun polling invisibile; prestazioni confrontate con baseline sulla board. |
| UX12 | Task sul pannello a 50–60 cm | Individuare prossimo evento, WAN, temperatura box e conteggio qualificato senza esitazioni ricorrenti; documentare errori e tempi, senza promettere soglie prima del test. |

Task suggeriti per il collaudo: «Quando è la prossima sessione F1?», «Quale partita è live verificata?», «Quanto traffico WAN c'è?», «Questa temperatura appartiene a box o board?», «Quanti record sono raggiungibili secondo box?», «Quanto è recente la temperatura di questo sensore?». Raccogliere il tempo al primo dato corretto, pressioni, errori e giudizio di leggibilità. Una review guidata dell'utente è utile, ma non si presenta come studio statistico.

## 13. Decisione progettuale

**Direzione raccomandata:** togliere la scelta preliminare di Sport e rendere le dashboard il primo livello degli argomenti; dividere Rete secondo Traffico/iliadbox/Dispositivi; estendere Casa con una vista Ambiente condizionale. Conservare Apple Calm, le schede acquisite e le garanzie dei provider. Il cambiamento più importante è la selezione delle informazioni e l'uniformità dell'apertura dei dettagli.

La successiva implementazione parte da A0/A1 e prosegue A2/A3, senza trasformare la presente analisi in certificazione del runtime. Restano da validare contratto pubblico, layout QML reale, sostenibilità delle fonti e lettura fisica. Il concept mostra la proposta, non un rilascio.
