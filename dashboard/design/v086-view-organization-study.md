# SmartPC — Organizzazione delle viste e gerarchia delle informazioni

**9 ottobre 2026 · proposta grafica e informativa, prima del codice applicativo · 960×640 orizzontale / 3,5″ / 50–60 cm.**

Questo studio definisce le **15 viste massime dei sei argomenti**: domanda, contenuti, priorità, posizione, dimensioni e primo approfondimento. Conserva lo [studio grafico orizzontale](v086-landscape-graphic-study.md) e sviluppa il [piano dashboard](v086-dashboard-first-analysis.md). Ora, Orologio, Meteo e Account restano riferimenti da affinare; Sport, Casa e Rete assumono una prima vista informativa.

**Stato reale:** analisi, specifiche di progetto e 30 tavole con dati simulati. Non sono nuove superfici Theme API implementate, screenshot QML o prove fisiche. Nessuna modifica al runtime/provider, installazione o accesso alla board. La baseline documentata resta 0.8.5-rc.1 / Apple Calm 1.5.0. [Inventario dei sorgenti/asset conservati](evidence/v086-view-organization-2026-10-09/runtime-baseline.json).

## 1. Che cosa guida la scelta delle informazioni

Per ciascuna vista si sceglie prima la domanda, poi i contenuti. I criteri sono: utilità immediata, relazione con il soggetto, disponibilità/freschezza, preferenze dell'utente e spazio leggibile. Non viene attribuito un punteggio numerico inventato ai campi.

- **Principale:** risponde alla domanda senza aprire menu. Identità e qualificazione fanno parte del dato: 51 °C senza nome del sensore non è sufficiente.
- **Contesto:** permette di interpretare il principale o anticipa la domanda successiva. Prossima sessione accanto a quella corrente; minimo e massimo accanto alla condizione del giorno.
- **Approfondimento:** confronti completi, molte entità e metadati specialistici. Classifica, inventario, porte e radio complete possono usare righe allineate.
- **Impostazioni:** cambiano preferenze/configurazione. Traffico, temperatura box e disponibilità dei dispositivi restano negli argomenti.

Una vista in più è giustificata da una domanda diversa. Non creiamo Utilizzo/Percentuali/Reset come tre pagine quasi identiche né replichiamo Previsioni dentro Giornata. Le 15 viste sono il massimo progettuale: discipline, Ambiente e integrazioni seguono disponibilità e configurazione, senza aggiungere pagine vuote.

## 2. Fonti e traduzione in scelte concrete

Sono stati consultati/ripresi **11 riferimenti primari**: due lavori scientifici, cinque articoli UX degli autori, una proposta di design di Home Assistant, due documenti W3C e la documentazione Open-Meteo. Le indicazioni dimensionali SmartPC sono nostre ipotesi progettuali, non misure certificate dalle fonti. Consultazione: 9 ottobre 2026.

| Fonte | Che cosa sostiene | Applicazione / limite |
| --- | --- | --- |
| [Bach et al., Dashboard Design Patterns, IEEE VIS 2022 / TVCG 2023](https://arxiv.org/abs/2205.00757), [materiali degli autori](https://dashboarddesignpatterns.github.io/) | Revisione di 144 dashboard e workshop di due settimane con 23 partecipanti: schemi e compromessi fra contenuti, spazio e interazione. | Grammatica comune con composizioni diverse per evento, confronto e andamento. Consultati abstract e sito dei materiali; nessun risultato quantitativo di usabilità trasferito al pannello. |
| [Sultanum e Setlur, Not Always Top-Left, 2026](https://arxiv.org/html/2608.06845v1) | Studio con 18 autori e 16 utenti: layout, salienza, semantica e compito contribuiscono all'ordine di lettura. | Titolo chiaro, nome del soggetto e valori dominanti lavorano insieme. Mettere qualcosa a sinistra non garantisce che sia capito per primo. Campione orientato a dashboard business e primo contatto; sequenze articolate dai partecipanti, non eye tracking diretto. |
| [Laubheimer, Dashboards and preattentive processing, NN/g](https://www.nngroup.com/articles/dashboards-preattentive/) | Le dashboard comunicano informazioni essenziali rapidamente; lunghezza/posizione aiutano i confronti quantitativi. | Percentuali con barre, andamento con linee, stati con parole e valori. Evitare tachimetri ornamentali per WAN e cerchi ripetuti per ogni sensore. |
| [Gordon, Visual Hierarchy, NN/g](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/) | Scala, contrasto e raggruppamento orientano l'attenzione. | Un elemento dominante nelle viste a evento; pari importanza nei preferiti. Non aumentare tutti i numeri indiscriminatamente. |
| [Nielsen, Progressive Disclosure, NN/g](https://www.nngroup.com/articles/progressive-disclosure/) | Separare ciò che serve spesso dalle funzioni secondarie, rendendo riconoscibile il passaggio. | Dashboard già utile; 5 apre altri dati, non un secondo menu di titoli. Informazioni frequenti come la temperatura router non vengono nascoste in configurazione. |
| [Krause, Consistency and Standards, NN/g](https://www.nngroup.com/articles/consistency-and-standards/) | Coerenza visiva, terminologica e di comportamento favorisce aspettative comprensibili. | Stessi margini, unità, nomi degli stati, ritorno e focus. Coerenza non impone la stessa impaginazione a orologio e inventario. |
| [Budiu, Recognition vs. Recall, NN/g](https://www.nngroup.com/articles/recognition-and-recall/) | Etichette e contesto rendono riconoscibili contenuti e azioni. | Icone con nome, non simboli soli. Aiuto contestuale breve al primo uso o su richiesta, rispettando la rimozione delle guide permanenti dal fondo. |
| [Home Assistant, Dashboard chapter 2, 2024](https://www.home-assistant.io/blog/2024/07/26/dashboard-chapter-2/) | Griglia, token comuni e riduzione degli spazi fra contenuto/funzioni; azioni primarie riconoscibili. | Dimensioni minime e densità deliberate, niente schede allungate senza ragione. Non importiamo valori CSS, touch target o controlli cloud come se valessero già per il nostro tastierino. |
| [W3C, Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) | Il significato non dipende esclusivamente dal colore. | Precedente, assente, live verificato e non raggiungibile restano parole visibili. |
| [W3C, Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | Contrasto minimo del testo con condizioni specifiche per le diverse categorie. | Obiettivo interno 4,5:1 per testo essenziale; controllo dei token separato dal test fisico. Pixel del nostro font non diventano automaticamente punti CSS. |
| [Open-Meteo, definizioni dei parametri](https://open-meteo.com/en/docs) | Temperatura, precipitazione e probabilità hanno unità e intervalli distinti; i dati derivano da modelli meteorologici. | Non scambiare % con mm, una probabilità oraria con il massimo giornaliero, oppure aggiornamento del fetch con periodo del modello. La fonte offre più dati di quelli oggi normalizzati da SmartPC. |

Le fonti orientano la scelta; non dimostrano che cinque schede siano leggibili su 3,5″. L'ultima verifica resta un compito sul pannello a 50–60 cm. La nuova ricerca sull'ordine di lettura rafforza la necessità di etichette significative, oltre alla buona posizione.

## 3. Che cosa abbiamo davvero a disposizione

| Dominio | Riscontro nei sorgenti | Conseguenza progettuale |
| --- | --- | --- |
| Oggi | Orologio locale, meteo e NextEvent esistenti. DayPage ripete tre giorni di forecast più evento. | Conservare Ora/Orologio; dare a Giornata una funzione odierna distinta. NextEvent non è un'agenda personale completa. |
| Meteo | WeatherData contiene temperatura, percepita, umidità, precipitazione, probabilità, vento/raffiche; forecast con data, min/max e probabilità per tre giorni. | Adesso e Previsioni sono realizzabili con i dati attuali. La probabilità oraria viene sintetizzata: non esiste nel DTO la serie completa per un grafico delle prossime ore. |
| Account | AccountWindow espone percentuale, durata e reset; il provider può restituire più servizi e finestre. Crediti e reset credits sono distinti. | Titolo servizio + durata evita due schede entrambe chiamate Codex. Tenere percentuale utilizzata, reset e eventuali crediti nella stessa dashboard. |
| Sport | Partite, squadre/classifiche e sessioni/eventi racing; hub e viste complete già presenti. | Nuovo selettore prioritario e proiezione per dashboard; live e risultati dipendono dalle garanzie della fonte. |
| Casa | Catalogo, preferiti, misure normalizzate e stati/freschezza. | Schede di sola lettura; Ambiente e categorie richiedono proiezioni qualificate, senza classificare un dispositivo soltanto dal suo nome. |
| Rete | Inventario, metriche router/Wi-Fi/porte e storico con qualificazioni. | Traffico, box e record diventano domande separate; raggiungibilità secondo box non è presenza assoluta. |

Riferimenti locali: [famiglie e controller](../Main.qml), [ClockPage](../../theme-projects/apple-calm/bundle/qml/ClockPage.qml), [ClockFocusPage](../../theme-projects/apple-calm/bundle/qml/ClockFocusPage.qml), [DayPage](../../theme-projects/apple-calm/bundle/qml/DayPage.qml), [Meteo attuale](../../theme-projects/apple-calm/bundle/qml/CurrentWeatherPage.qml), [ForecastPage](../../theme-projects/apple-calm/bundle/qml/ForecastPage.qml), [AccountPage](../../theme-projects/apple-calm/bundle/qml/AccountPage.qml), [contratti dei campi](../theme-api/contexts.json), [normalizzazione meteo](../theme_api.py), [provider meteo](../weather.py), [normalizzazione Account](../account_sync.py).

## 4. Regole dimensionali comuni

Barra 56 px; margini laterali 24 px e inferiore 16 px; identità locale y=70/h42; contenuti **x24/y120/w912/h504**. Tutte le composizioni raggiungono y624. Distanza fra schede 16 px, raggio e colori Apple esistenti, padding 20–24 px. Le coordinate che seguono sono native dello schermo, non misure responsive per telefono.

| Ruolo | Grandezza indicativa | Regola |
| --- | --- | --- |
| Ora nella vista Ora | 152 px | Mantiene la funzione dominante acquisita. |
| Ora nella vista Orologio | 224 px | Candidato vicino al riferimento esistente; verificare tutte le ore e la scala massima. |
| Evento/risultato/misura principale | 68–86 px | Identità a 32–34 px, fase/stato a 27–30 px. |
| Quantità secondaria | 38–62 px | Unità vicina al valore; non separata in una zona difficile da associare. |
| Nome/stato lungo | 29–34 px | Preferire parole chiare, una scheda più larga o meno schede alla riduzione automatica del testo. |
| Titolo locale | 32 px | Uno per vista; evitare doppio titolo dell'argomento e sottotitolo ripetuto. |
| Etichette e contesto | 23–27 px | Fonte sintetica 22 px; note lunghe nei dettagli. |
| Assi del grafico | 20–22 px | Valori correnti restano numeri grandi; il grafico non è l'unico accesso alla quantità. |

Sono dimensioni candidate con i font inclusi, non una scala già certificata. Le tre funzioni principali della tipografia restano identità, valore e contesto. Formati diversi hanno adattamenti circoscritti, non decine di dimensioni scelte senza un ruolo.

Le composizioni condivise sono: principale **400×504** + destra in 240×244; griglia **2×2 di 448×244**; principale + grafico **496×244** e due secondarie; tre colonne **293⅓×504** per forecast; due finestre Account **448×324** + schede basse **448×164**. Ora/Orologio conservano composizioni dedicate alla loro funzione, con gli stessi allineamenti e token.

Nomi lunghi o testo grande attivano una variante orizzontale meno densa: ad esempio principale + due schede 496×244, o due colonne forecast per gruppo senza ridurre i caratteri. Le informazioni essenziali rimangono nella prima vista; la priorità decide quali dettagli rinviare. Non torniamo a una colonna verticale obbligatoria sul display.

## 5. Oggi — tre usi distinti

| Vista | Principale e posizione | Contesto e posizione | 5: destinazione proposta |
| --- | --- | --- | --- |
| **Ora** | HH:MM, 152 px, area sinistra x24/y120/w536/h318. Data nella riga identità. | Meteo x576/y120/w360/h504, temperatura 80 px, condizione 34, percepita 27. Evento facoltativo x24/y454/w536/h170, titolo 34 e orario 25. | Dettaglio Oggi con evento pertinente e condizioni complete del giorno. |
| **Orologio** | HH:MM 224 px, x24/y120/w912/h340; niente secondi o grafici aggiuntivi. | Fascia bassa y476/h148: meteo x24/w448, evento x488/w448. Valori 30–36 px. Senza evento, meteo esteso. | Stesso dettaglio Oggi, conservando ritorno alla vista Orologio. |
| **Giornata** | Prossimo evento qualificato a sinistra 400×504; orario 68, titolo 34, data/fase 27. | Meteo del giorno a destra 496×244, min/max 62; sotto probabilità giornaliera e vento 240×244, valori 52/38. | Evento/programma pertinente e contesto del giorno; accesso al dettaglio dell'entità. |

**Giornata senza evento:** meteo del giorno diventa principale; a destra contesti distinti disponibili, per esempio percepita/umidità/vento/probabilità. Nessuna card Nessun evento e nessun doppione dello stesso valore. L'identità della vista rimane Giornata. Se un evento compare durante l'interazione, aggiornare in modo controllato, senza sottrarre focus o aprirlo automaticamente.

La preview mostra Ora/Orologio con un evento di esempio, non un'agenda aggiunta. Giornata cambia la selezione del contenuto, mentre Ora/Orologio richiedono principalmente allineamenti e adattamento dei metadati.

[Ora](evidence/v086-view-organization-2026-10-09/oggi-ora-day.png) · [Orologio](evidence/v086-view-organization-2026-10-09/oggi-orologio-day.png) · [Giornata](evidence/v086-view-organization-2026-10-09/oggi-giornata-day.png).

## 6. Meteo — adesso e confronto fra giorni

### Adesso

Principale x24/y120/w400/h504: condizione 34 px, temperatura 86, percepita 27. Probabilità del periodo corrente solo quando il relativo riferimento temporale è qualificato; altrimenti nei dettagli. Quattro schede a destra: **Vento** x440/y120 (38 px con unità/direzione), **Umidità** x696/y120 (58), **Raffiche** x440/y380 (38), **Precipitazioni** x696/y380 (42, mm e intervallo).

L'ordine mette prima due quantità comuni e poi due approfondimenti della condizione atmosferica. Raffiche mantiene relazione visiva con Vento; Precipitazioni resta distinta da Probabilità. Non inferire da 0 mm che non pioverà nelle prossime ore. 5 apre condizioni complete, periodo e fonte, con allerte pertinenti se disponibili.

### Previsioni

Tre colonne cronologiche: **x24, x333⅓, x642⅔**, ciascuna 293⅓×504. Stessa sequenza interna: giorno/data 32 px, icona 48, massima 62, minima 32–38, condizione 27, massimo giornaliero della probabilità 48 e sua qualificazione 22–24. Valori allineati tra giorni, senza dare un colore diverso a ogni colonna.

5 apre il giorno selezionato: dati disponibili, periodo e fonte. Se si introduce selezione nella dashboard, deve esserci un solo focus tra le colonne e un contorno leggibile; non modificare implicitamente la semantica 2/8. La soluzione iniziale può aprire il dettaglio delle previsioni con il primo giorno pertinente già selezionato e lasciare la scelta del giorno all'interno.

**Confine:** oggi non abbiamo nel DTO una serie completa di temperature/probabilità orarie, UV o alba/tramonto. Queste sono possibili estensioni future, da qualificare separatamente; la fonte esterna le offre, ma il prodotto non le espone automaticamente.

**Mezzanotte/cache:** derivare Oggi/Domani dalla data canonica, non dal testo OGGI salvato al fetch. Il provider costruisce attualmente questa etichetta per la prima riga: è un rischio da verificare con fixture prima/dopo mezzanotte, non un bug di runtime riprodotto in questa analisi. Conservare data e stato precedente; non rinominare una previsione di ieri come quella di oggi.

[Adesso](evidence/v086-view-organization-2026-10-09/meteo-adesso-day.png) · [Previsioni](evidence/v086-view-organization-2026-10-09/meteo-previsioni-day.png).

## 7. Account — una dashboard per consumi e reset

Due schede superiori **x24/x488, y120, 448×324**, dedicate alle due finestre pertinenti dello stesso servizio. Titolo **servizio + durata reale**, 26 px; percentuale **utilizzata** 80; barra 0–100 con lo stesso riferimento; reset 25 px con data/ora locale. Il residuo, se aggiunto, deve essere chiamato Disponibile e calcolato solo da percentuali valide, senza ribaltare silenziosamente il significato della barra.

Sotto, **x24/x488, y460, 448×164**: Crediti disponibili e Reset disponibili, valori 38 px. I reset credits sono un conteggio diverso dalla data di ripristino di una finestra. Niente saldo convertito in euro o numero di messaggi residui dedotto da una percentuale.

Un'unica finestra valida occupa tutta la larghezza superiore. Più finestre/servizi si consultano con 5 nel dettaglio; ordine stabile per servizio e durata, preservando la selezione. Una finestra critica fuori dal gruppo iniziale richiede un segnale nominato, non un riordino continuo delle schede. Soglie e notifiche riusano le preferenze esistenti, senza introdurre regole implicite.

**Riscontro concreto:** la durata è nel DTO, ma AccountPage usa soprattutto la label. Due finestre dello stesso servizio possono quindi avere lo stesso titolo. Il nuovo titolo elimina questa ambiguità usando un dato già esposto. Dati precedenti conservano fonte/tempo e stato; lo scadere dell'orario di reset non autorizza a mostrare consumo 0% senza una nuova lettura.

[Utilizzo](evidence/v086-view-organization-2026-10-09/account-utilizzo-day.png).

## 8. Sport — il primo livello contiene già l'evento

Le tre discipline condividono principale a sinistra **400×504** e quattro contesti a destra, **240×244**, nelle posizioni alto-sinistra, alto-destra, basso-sinistra, basso-destra. Nome del soggetto 34, valore centrale 68–86, fase/data 27; contesti 33–62 secondo formato. 5 apre direttamente l'approfondimento della disciplina, centrato sul contenuto prioritario.

| Vista | Principale | Alto-sinistra | Alto-destra | Basso-sinistra | Basso-destra |
| --- | --- | --- | --- | --- | --- |
| Calcio | Competizione, squadre, risultato live qualificato oppure orario locale; stato esplicito | Prossimo appuntamento distinto, 34 px | Squadra scelta: posizione 62 e punti 23 | Ultimo esito concluso, 48 | Altre partite live qualificate, 42; il conteggio esclude quella principale |
| Formula 1 | GP/circuito e sessione live qualificata oppure prossima; fase/orario | Sessione successiva, 34 | GP successivo e data, 33 | Ultima sessione con pilota/risultato, 34 | Mondiale pertinente, 44 |
| MotoGP | GP/classe, sessione, fase/giro oppure orario | Leader corrente, 34; senza live ultimo vincitore nominato | Distacco verificato, 46; senza live prossimo appuntamento | Ultima sessione Sprint/Gara, 42 | Mondiale della classe/stagione, 34 |

**Priorità Calcio:** live verificato della squadra scelta → altro live della competizione → prossima della preferita → prossima della competizione → ultimo esito pertinente. Identità stabile e ordine temporale risolvono i pari casi. Niente evento rotante che interrompa la lettura.

**Priorità racing:** sessione verificata live → prima sessione utile futura → ultima sessione conclusa. Evento GP e sessione hanno tempi diversi: il GP può essere iniziato mentre qualifiche/gara devono ancora svolgersi. Non dedurre live dalla sola ora; non confondere data del GP corrente con quella del prossimo.

Ogni secondaria è facoltativa. Senza squadra o classifica qualificata, usare il riepilogo pertinente della competizione oppure due contesti più larghi. Senza timing MotoGP, il Distacco non diventa +0,0 s. Nei dettagli calendario, risultati, classifica e timing possono usare righe funzionali, conservando evento e sezione visibili.

[Calcio](evidence/v086-view-organization-2026-10-09/sport-calcio-day.png) · [Formula 1](evidence/v086-view-organization-2026-10-09/sport-f1-day.png) · [MotoGP](evidence/v086-view-organization-2026-10-09/sport-motogp-day.png).

## 9. Casa — osservazione, ambiente e catalogo

| Vista | Organizzazione e dimensioni | Apertura e condizioni |
| --- | --- | --- |
| **Preferiti** | Quattro schede 448×244 in 2×2. Nome 25, misura 48–58 o stato lungo 29–34, attributo/freschezza 23. Ordine scelto dall'utente. | 5 apre preferiti estesi e selezione dispositivo. Uno/due preferiti usano schede più larghe; nessun riquadro fittizio. |
| **Ambiente** | Principale 400×504: sensore nominato, temperatura 86 e tempo. A destra umidità dello stesso sensore 58, altro sensore 58, movimento 31 e copertura delle letture 62. | Solo con codici/misure supportati. 5 apre misure complete e timestamp. Al posto di letture assenti usare meno schede utili. |
| **Dispositivi** | Principale 400×504: numero nel catalogo 86, disponibilità secondo cloud e dati precedenti 27. A destra preferiti/categorie qualificate, conteggi 62. | 5 apre inventario e dettaglio. Senza categorie affidabili mostrare disponibilità e preferiti in due schede più larghe. |

La misura di Ambiente parte dal primo sensore utile fra i preferiti, poi da un ordine stabile; niente media fra stanze. Soggiorno/Studio nei concept sono nomi dimostrativi dei dispositivi, non un nuovo sistema di stanze.

Il precedente resta associato al dispositivo, non soltanto a una nota generale. Non sommare potenze appartenenti a letture di tempi diversi per inventare un totale corrente. ON riportato non prova che la lampada stia illuminando; il cloud non certifica la presenza LAN. Le schede non sembrano interruttori finché non esiste un contratto di comando.

[Preferiti](evidence/v086-view-organization-2026-10-09/casa-preferiti-day.png) · [Ambiente](evidence/v086-view-organization-2026-10-09/casa-ambiente-day.png) · [Dispositivi](evidence/v086-view-organization-2026-10-09/casa-dispositivi-day.png).

## 10. Rete — traffico, stato box, inventario

### Traffico

Principale 400×504: **download 86 px e upload 50 px**, entrambi con etichetta e unità; l'upload non resta una piccola frase di stato. A destra andamento **496×244** e sotto Stato WAN/Capacità box **240×244**, valori 42/38. Fonte/timestamp appartengono alle rispettive misure.

Il grafico principale può usare una stessa scala per download/upload, senza far sembrare uguali quantità molto diverse. Se upload quasi piatto, il suo numero resta leggibile. Nei dettagli due grafici allineati nel tempo con scale esplicite sono preferibili a un doppio asse ambiguo. Buchi sono interruzioni, non tratti interpolati; finestra massima Ultima ora significa periodo richiesto, non garanzia di 60 minuti completi.

5 apre storico WAN con periodo. Velocità istantanea, volume trasferito, capacità riportata e speed test mantengono nomi diversi. Niente valori WAN trasformati in traffico del PC preferito.

### iliadbox

Principale 400×504: **stato WAN 68 px**, nome router 34, uptime 27 e aggiornamento. È un affinamento della tavola precedente, dove l'uptime era il numero dominante: la domanda Come sta la box? richiede prima lo stato, poi i due giorni di uptime.

Quattro secondarie: temperatura del sensore box nominato **56 px**, radio Wi-Fi **43**, porte/link **43**, firmware **34**. Se il nome/versione non entra, valore sintetico qualificato e stringa completa nei dettagli, senza abbassare il testo arbitrariamente. 5 apre stato/sensori e sezioni Wi-Fi/Porte; niente passaggio obbligatorio dalle impostazioni.

Non dare valutazioni Normale/Critica alla temperatura senza soglie documentate per quel sensore. T1/T2 restano identificabili, e una lettura Orange Pi non sostituisce una lettura iliadbox. Catalogo radio/porte e velocità WAN possono avere freschezze diverse.

### Dispositivi

Principale 400×504: **record dell'inventario 86 px**, poi numero di raggiungibili **secondo box**, tempo e copertura parziale. A destra fino a quattro preferiti con nome, stato **29–32 px** e freschezza 23. Se non ci sono preferiti, usare riepiloghi qualificati oppure due schede più larghe; non scegliere automaticamente quattro host come se fossero i preferiti dell'utente.

5 apre l'inventario selezionabile e poi identità/indirizzi/link/osservazioni. Record storico non diventa dispositivo connesso; non raggiungibile non diventa spento. La dashboard facilita la lettura senza eliminare questi significati.

[Traffico](evidence/v086-view-organization-2026-10-09/rete-traffico-day.png) · [iliadbox](evidence/v086-view-organization-2026-10-09/rete-iliadbox-day.png) · [Dispositivi](evidence/v086-view-organization-2026-10-09/rete-dispositivi-day.png).

## 11. Avvisi, impostazioni e informazioni

Sono superfici di servizio, non altre dashboard obbligatorie nel carosello. Mantengono gli stessi font, margini, parole degli stati e ritorni.

| Superficie | Organizzazione proposta | Che cosa evitare |
| --- | --- | --- |
| Avvisi | Non letti/gravità come contesto breve; avviso selezionato con titolo 30–34, origine/data 24, contenuto 26–28. Inbox a righe quando serve scegliere molte entità. | Grandi riquadri vuoti quando non ci sono avvisi; colore come unica spiegazione; sottrarre priorità all'overlay urgente. |
| Impostazioni | Conservare le sei categorie: Schermo, Aspetto, Moduli e Home, Avvisi, Servizi collegati, Dati e aggiornamenti. Schede compatte con valore/stato attuale; controlli nella categoria. | Trasformare ogni controllo in un grafico o nascondere opzioni in un altro hub. |
| Controlli | Nome 26–28, valore 28–32, spiegazione 23–24; poche righe chiare, focus visibile e feedback vicino all'azione. Scorrimento nei dettagli quando necessario. | Ridurre il testo per far stare tutte le opzioni; distinguere attivo/focalizzato soltanto con il colore. |
| Informazioni dispositivo | Identità board, OS/app/tema e versioni. | Duplicare la pagina Risorse. |
| Risorse | CPU, memoria, storage e temperatura **della board**, con unità/fonte/tempo. | Confondere sensori router con board o usare indice grafico per una metrica assente. |

Informazioni resta consultazione; Impostazioni modifica. In Servizi collegati si gestiscono preferiti e raccolta; il traffico e gli stati dei dispositivi si consultano in Rete/Casa. Le destinazioni nominate devono corrispondere alle route reali, non a nuove pagine di testo simili.

## 12. Navigazione e aggiornamenti

Contratto ancora proposto: **2/8 cambia dashboard nell'argomento; 4/6 cambia argomento; 5 apre il contesto della dashboard; 7 torna all'origine**. Nei dettagli 2/8 muove focus/scorre e le tab seguono la stessa regola tra argomenti. Non si deve poter premere 5 solo dopo aver scoperto un focus invisibile su una scheda.

La prima dashboard è un riepilogo di consultazione; la selezione di partita/dispositivo/giorno avviene nel dettaglio. Se in futuro si introduce selezione diretta nella dashboard, occorre risolvere esplicitamente il conflitto con 2/8 prima di implementarla. La preview sceglie le viste dall'esterno: quel selettore non è un nuovo menu dentro SmartPC.

Nessun footer permanente con guide/contatori. Per il primo uso o su richiesta, un aiuto contestuale breve spiega il comando nel contesto. Il titolo/contorno dell'approfondimento rende riconoscibile il passaggio; 7 conserva vista, entità e focus. L'orientamento discreto e l'aiuto risolvono la riconoscibilità senza occupare sempre il fondo.

Provider e frequenze non cambiano soltanto perché aumentano le schede. Nuovo dato aggiorna il blocco, senza ruotare evento, riordinare preferiti o spostare un controllo sotto il focus. Modalità ridotta/niente movimento rimane valida. Dato precedente e caricamento conservano la struttura; un errore non rende corrente il cache.

## 13. Affinamenti prioritari emersi

| Priorità | Affinamento | Prova necessaria prima del rilascio |
| --- | --- | --- |
| P0 | Sport subito informativo e selettore live/prossimo/ultimo | Live qualificato, più live, calendario stale, GP con qualifiche/gara future. |
| P0 | WAN: entrambi i numeri leggibili; box: stato prima dell'uptime | Download/upload molto diversi, storico parziale e freschezza mista. |
| P0 | Disponibilità/freschezza locale sulle schede Casa/Rete | Dati correnti e precedenti insieme; zero diverso da assente. |
| P1 | Titoli Account con servizio/durata, reset credits distinto | Una/due/più finestre, nome uguale, reset superato senza nuovo fetch. |
| P1 | Giornata distinta da Previsioni | Evento presente/assente, evento che compare, meteo assente. |
| P1 | Date forecast e labels Oggi/Domani coerenti | Mezzanotte, cache del giorno prima e ora locale. Rischio individuato, non bug fisico già riprodotto. |
| P1 | Dimensione testo e nomi lunghi | Variante orizzontale meno densa e confronto sul pannello. |
| P2 | Dettagli già informativi e Info/Risorse coerenti | Destinazioni di 5, ritorno 7, focus e assenza di doppioni. |

## 14. Validazione e prossimo passo del MasterPlan

La [mappa strutturata](evidence/v086-view-organization-2026-10-09/view-organization.json) descrive 15 viste e 65 blocchi con rettangoli, grandezze, contenuti, disponibilità e destinazione proposta. È una specifica di design, non un contratto runtime. Il [renderer offline](evidence/v086-view-organization-2026-10-09/render_views.py) riusa font/icone/palette dello studio precedente; il [report](evidence/v086-view-organization-2026-10-09/render-review.json) copre 30 tavole: 15 viste × giorno/notte. Le tavole mostrano un caso informativo sintetico per vista, non tutti gli stati/scale.

Le immagini servono a verificare proporzioni, ritmo, densità e gerarchia. Il controllo dei rettangoli del testo non equivale a un controllo QML né alla certificazione fisica. Il [rapporto di integrità](evidence/v086-view-organization-2026-10-09/analysis-integrity.json) accompagna i controlli finali di questo studio.

Prima dell'implementazione estesa, A0 deve aggiungere fixture per: assenza, precedente/offline, caricamento, nomi lunghi, scala massima, uno/due/molti soggetti e periodo temporale cambiato. Poi prova umana sul pannello: individuare ora, prossima sessione, probabilità del giorno, reset corretto, upload, temperatura box e raggiungibilità qualificata. Registrare errori, pressioni e tempo al primo dato corretto; nessuna soglia di secondi promossa prima della prova.

Sequenza proposta: **Sport e Rete nella 0.8.6**, insieme a Casa con Ambiente condizionale e ai dettagli indispensabili; **Giornata, affinamenti Meteo/Account e restanti dettagli nella 0.8.7**, salvo anticipare difetti di correttezza riprodotti. Conservare Ora/Orologio e le qualità del tema; non includere serie meteo aggiuntive, agenda personale, stanze/comandi Casa o telemetria per host senza nuovo studio delle dipendenze.

Il prossimo lavoro applicativo parte da dati qualificati e varianti reali, non dal riempimento automatico di ogni rettangolo. L'obiettivo è una dashboard che risponde bene anche quando una fonte manca, mantenendo la qualità grafica scelta.
