# Apple Calm v0.10.2 · piano completo di attuazione

29 ottobre 2026 · revisione 1 · **pronto per iniziare l’implementazione, ancora da attuare**.

Il risultato previsto è una Dashboard Apple Calm più leggibile sul display **3,5″ orizzontale, 960×640 px**, con avvisi nello stile compositivo iOS, dati affidabili e movimento breve. La priorità è correggere il significato dei dati prima di rivestire le viste. Palette, Cantarell/Liberation Sans, navigazione e tastierino restano la base del prodotto.

Questo è il piano di riferimento per l’attuazione. Riunisce [analisi e ricerca](v0102-apple-calm-readability-analysis.md), [studio grafico](v0102-apple-calm-graphic-refinement-study.md) e [audit dei dati](v0102-apple-calm-data-audit.md). Le tavole sono proposte con dati sintetici; non sono catture correnti della board. Il checkout dichiara `0.10.2-rc.4` e Apple Calm sorgente `1.6.5`; lo stato effettivamente installato va riaccertato prima di preparare una consegna.

## 1. Decisioni di progetto

| Tema | Scelta per il primo ciclo completo |
| --- | --- |
| Direzione | Calm essenziale. Card per gruppi eterogenei e pannelli; superfici aperte per liste, timing, menu e grafici. Nessun nuovo tema parallelo. |
| Avvisi ordinari | Banner inferiore, un evento alla volta, senza prendere focus. Altezza iniziale 140–152 px, da verificare in QML. Le consultazioni rispettano la fascia occupata; configurazione/modifica conserva il rinvio attuale. |
| Centro avvisi | Tre righe generose come candidato al 100%, capacità ridotta quando il contenuto/110% lo richiede; stessa anatomia di banner e dettaglio. Una riga per evento nella prima consegna. |
| Header | Campana e numero non letti nelle viste appropriate; priorità esplicita a Urgente/Ripristino/Quiete. Se lo spazio manca, eliminare prima ornamenti e puntini, conservando titolo, ora e stato necessario. |
| Account | Mostrare **Residuo** come dato principale: `100-usedPercent`, numero e barra coerenti. Nel dettaglio resta recuperabile l’utilizzato. Solo valori validi; snapshot precedente sempre dichiarato. |
| Meteo | Stima attuale e **tre previsioni giornaliere datate**. Nessuna nuova acquisizione oraria di temperatura/condizione per sostenere il mock. |
| Risultati sportivi | Stato italiano e punteggi per lato; `0 – —` quando un lato manca in un risultato, senza inventare 0–0 per eventi futuri. Tempo, gap e stato Motorsport distinti. |
| Icone | Catalogo semantico/atlante Apple Calm, risorse locali. Simbolo per dominio o azione, testo per stati essenziali; nessun secondo catalogo runtime o icona scaricata in rete. |
| Movimento | Normale/Ridotto/Off; prima conservare le ricette attuali, poi ottimizzare solo ciò che il banco dimostra utile. Nessun blur dinamico nella candidata di base. |
| Provider | Copertura esistente: tutta Serie A, Fantacalcio su consultazione, Casa esclusa dalle nuove notifiche, €0/mese per nuovi servizi. Nessun aumento di polling implicito nel restyling. |

Pannello laterale, raggruppamento avanzato, vetro dinamico e cambio globale del renderer testuale rimangono esperimenti successivi. Non sono dipendenze della consegna qui definita. Arena, policy di guida e renderer Acquario restano quelli della baseline; si verifica la loro convivenza con cornice e avvisi.

## 2. Sequenza e dipendenze

| Incremento | Contenuto e file principali | Uscita verificabile |
| --- | --- | --- |
| I0 · Baseline | Manifest installato, sorgenti corrispondenti, stato del tema, dati/preferenze e prove rc.4. Seguire `os/maintenance-policy.md`. | Baseline identificata per hash, elenco del delta consentito e cartella evidenze dedicata. Il lavoro Gioco/Acquario già presente nel checkout non entra accidentalmente nel pacchetto. |
| I1 · Semantica | D01–D05 dell’audit: `sport_core.py`, `motorsport_core.py`, `racing_timing.py`, `theme_api.py`, `Format.js`, `AccountPage.qml`, fixture. Modificare i produttori solo dove serve una proiezione canonica. | Casi limite fonte → DTO → testo visibile con valori attesi; vecchie cache e zeri preservati. Nessun cambio cosmetico nasconde un campo assente. |
| I2 · Contratto pubblico | `theme-api/contexts.json`, generati, adattatori/context QML e payload in `Main.qml`; stato avvisi, contatore e metadati temporali del timing. | API additiva e coerente, contatore unico, fallback Base/Functional; preflight e fixture aggiornati. I1/I2 possono condividere una candidata interna, mai un contratto a metà. |
| I3 · Componenti e notifiche | Token/metriche, `Label.qml`, `Rows.qml`, `Notice*.qml`, `Notice.qml`, `Shell.qml`, host e guide. | Banner, centro avvisi, dettaglio e urgente leggibili; timer/acknowledgement/lettura preservati, fascia occupata rispettata. |
| I4 · Viste | Meteo, Rete, Calcio, F1/MotoGP, Casa, Account, Home/Menu/Impostazioni con componenti condivisi. | Ogni vista rispetta la matrice dati e le geometrie, giorno/notte e scala 1/1,1. Nessuna nuova destinazione o funzione di provider non prevista. |
| I5 · Movimento e nitidezza | `MotionController`, ricette, wrapper visuale, atlante e banchi testo circoscritti. | Scelta A/B motivata su target; stesso stato finale con Normale/Ridotto/Off; nessun lavoro continuo in idle o nelle viste nascoste. |
| I6 · Candidata | Verifiche pertinenti PC, ARM/EGLFS e pannello; pacchetto e manifest della sola variazione qualificata. | Ricevute legate agli stessi byte, lista dei gate passati/aperti e rollback verificato. |
| I7 · Consegna | Installazione nella successiva fase autorizzata, servizio/heartbeat, warning, conservazione dati e ritorno alla release precedente se necessario. | Report distinto per implementato, installato, verificato sulla board e qualificato fisicamente/live. MasterPlan aggiornato solo con fatti realmente ottenuti. |

Ordine operativo: **I0 → I1/I2 → I3 → I4 → I5 → I6 → I7**. Primo punto revisionabile: I1/I2 e notifiche I3, con screenshot QML e controlli semantici. Il ciclo completo comprende anche le viste I4: non è considerato chiuso dopo il solo banner.

## 3. Contratto dei dati da implementare

### Correzioni senza ambiguità

- **Calcio:** aggiungere `half_time` all’enum pubblico; mapparlo a «Intervallo» e includerlo nel filtro In corso. Non cambiare le condizioni di freschezza/verifica che autorizzano Live. Usare la stessa funzione di stato in lista e dettaglio. Il punteggio mantiene la disponibilità di ciascun lato.
- **Account:** `resetsAt<=0` o non valido → `null` nel DTO; vista difensiva. Per il residuo accettare solo misura disponibile, finita e 0–100; dato mancante → nessuna barra quantitativa, non barra vuota che suggerisce esaurimento. Crediti e reset disponibili rimangono grandezze separate.
- **NumericValue:** rifiutare booleani/non finiti come misure e come testo derivato automaticamente. Conservare i testi formattati espliciti ammessi dal contratto, inclusi tempi. Non estrarre misure da stringhe UI. Aggiornare i produttori e la documentazione insieme al formatter.
- **Meteo:** unità una sola volta; direzione vento dal dato canonico, con testo cardinale deterministico. Distinguere probabilità % e precipitazione mm. Data/ora della stima distinta da raccolta/tentativo. La previsione usa `date`, non indice; cache di ieri non viene etichettata Oggi.

### Proiezione Motorsport

Nei produttori normalizzati mantenere i campi legacy necessari alle altre viste e aggiungere campi canonici, prima della trasformazione in `RacingTiming`. Riempire `driverId`, posizione e `lap` dai dati del pilota corretto; `laps` non va perso perché il DTO chiama il campo `lap`.

| Contesto | Campo e semantica da consegnare al tema |
| --- | --- |
| Qualifica/prove concluse | `time` = giro migliore; `timeKind=best_lap`. Stato come ritirato/non classificato separato. |
| Risultato gara vincitore | `time` = tempo complessivo, `timeKind=total`. |
| Risultato gara altri | `gap` = distacco dichiarato, anche in giri se previsto dalla fonte; non convertirlo in durata complessiva. Stato finale separato. |
| Timing attuale | `time` accompagnato da `timeKind=last_lap` o `best_lap` secondo la sessione e il campo provider; `gap` dal leader, `interval` dal precedente, `lap` completati. Nessun generico `value` assegnato a tutte le colonne. |
| Cache precedente con solo `value` | Conservare un `resultText` di sola esposizione e `resultKind=reported` («Dato riportato»), senza ricavarne numeri o una semantica non provata. Il nuovo fetch popola i canonici; nessun azzeramento delle cache per ottenere il nuovo layout. |

Aggiunte pubbliche proposte a `RacingTiming`: `timeKind` (`total`, `best_lap`, `last_lap`, `reference`, `unavailable`), `resultText` e `resultKind` (`time`, `gap`, `status`, `reported`, `unavailable`). Le etichette visibili sono italiane e centralizzate. `time/gap/interval` restano i canali tipizzati esistenti; i display text preservano la precisione della fonte. Il valore principale e la sua etichetta vengono scelti insieme. Evento/sessione restano identificati nel contesto proprietario, senza usare «ultimo risultato disponibile» come criterio di abbinamento.

### Avvisi e header

Estensione candidata dell’API **2.15**, da generare con gli strumenti del progetto senza modificare a mano solo gli output:

| Campo | Origine e regola |
| --- | --- |
| `UiStatus.unreadCount` | Contatore corrente dell’EventService, stesso significato del Centro avvisi; mai numero dei gruppi o somma delle righe sullo schermo. Intero ≥0. |
| `UiStatus.notificationsAvailable` | Stato di disponibilità del servizio; assenza non presentata come «zero avvisi verificato». Default compatibile false. |
| `NotificationEvent.cancelled`, `expired`, `presented` | Proiezione dei fatti già prodotti dall’engine. `seen` rimane la lettura. Non ricalcolare questi fatti dal colore o dall’animazione. |
| `NotificationEvent.deliveryState` | Codice stabile: `pending`, `presented`, `listed_capacity`, `listed_late`, `revoked`, `expired`, `unavailable`. Mapping dai fatti/rami già usati nell’engine, testo italiano separato. Nessun nuovo ordinamento/priorità implicito. |
| `NotificationEvent.source` | Stato e freschezza della fonte effettiva, quando disponibili. Fonte sconosciuta resta tale; la sola emissione non certifica l’ultimo controllo. |

Niente `receivedAt` inventato, `groupKey` sintetico o storia delle revisioni ricostruita dai titoli. Il primo ciclo usa emissione/validità già disponibili e stati reali. Collegamenti strutturati tra rettifiche e raggruppamento richiederanno una successiva proposta di dominio se la sorgente non li offre.

### Fascia transitoria

Riutilizzare `SurfaceContext.safeArea` e `viewport`, più `ShellLayout.content`, invece di leggere oggetti privati dal bundle. L’host calcola l’intersezione fra regione occupata dal banner e area di contenuto e aggiorna l’area sicura nelle coordinate documentate del destinatario. L’area di contenuto disponibile è l’unica base per il layout: nessuna sottrazione duplicata nel tema.

La nuova composizione ricalcola numero di righe e dettagli secondari, mantenendo dimensione del testo, selezione per ID e posizione nel flusso. La fascia rimane stabile fra avvisi consecutivi in coda; ingresso/uscita non avviano uno scorrimento animato dell’intera pagina. Guide e dato essenziale non vengono coperti. Gli `occupiedRegions` della scena restano una protezione distinta e non sostituiscono questo calcolo. Verificare Base/Functional: compatibilità del contratto e superficie di fallback devono rimanere utilizzabili.

## 4. Componenti, geometria e viste

Dimensioni candidate al 100%: titolo 32–36 px, titolo avviso 28–32, corpo 24–26, fonte/ora 22–24, numeri principali 56–80 e orologio 120–140. Le righe che oggi usano caratteri più grandi non vengono ridotte per somigliare al browser. Passo spaziature 8, padding 20–24, icone 30–36 in area 48–56. Contrasto del testo funzionale ≥4,5:1 sulla superficie composta. La prova sul pannello può richiedere font maggiori e meno righe.

| Vista/componente | Composizione e contenuto richiesti |
| --- | --- |
| Header/Home | Orologio e meteo restano dominanti. Titolo/famiglia, ora, stato sistema e campana hanno una gerarchia di spazio; gestire tutti gli stati simultanei. Riepiloghi non duplicano la notifica come nuovo fatto. |
| Banner | Icona dominio, categoria/fonte e ora, titolo, una frase; accesso al Centro con tasto 3. Un evento per volta. Nessuna azione 5 che sottrae il comando alla vista sottostante. |
| Centro avvisi | Icona, titolo, contesto, ora e non letto; fonte/stato sempre recuperabili. Focus stabile, selezione per ID, Recenti/Storico, conteggio coerente. Nessuna lettura globale all’apertura. |
| Dettaglio/urgente | Testo completo, fonte, emissione, validità, rettifica/revoca. Urgente prevale immediatamente e conserva fallback compilato; nessuna dipendenza da download di asset o fine animazione. |
| Meteo | Gruppo attuale e grandezze secondarie distinte; tre giorni con data, simbolo, Max/Min e probabilità massima giornaliera. Osservazione/stima, previsione e cache hanno etichette coerenti. |
| Rete | Traffico e capacità separati; grafico ampio, assi/unità, stessa scala quando si confrontano serie, download/upload riconoscibili anche senza colore. Buchi visibili. Router/Wi-Fi/porte e dettaglio conservano le proprie unità. |
| Calcio | Colonne squadre/risultato, stato leggibile, minuto solo quando appropriato, VAR come informazione distinta. Elenco, dettaglio, classifica e squadra usano identità/ordine coerenti. Fantacalcio consultivo conserva assenza voto ≠ zero. |
| F1/MotoGP | Posizione, nome e valore principale allineati; etichetta Tempo/Giro migliore/Ultimo giro/Distacco secondo il contratto. Team e stato secondari. Al 110% ridurre righe, non font; dettaglio per intervallo e informazioni aggiuntive. |
| Casa | Dispositivo e misura separati; età e «Precedente» per stato, non solo footer globale. Falso/Spento e indisponibile diversi; preferiti conservati per ID. |
| Account | Due finestre confrontabili, residuo e barra coerenti, durata e reset validi; fonte e ora dello snapshot. Crediti e reset separati. Nessuna conferma di disponibilità corrente da dati vecchi. |
| Menu/Impostazioni | Tre voci grandi quando quattro non entrano; icone semanticamente utili, descrizione e focus. Altre voci raggiungibili con i comandi attuali. Esito azione dal risultato pubblico, non dalla pressione del tasto. |
| Gioco/Acquario | Conservare scena, logica, piloti, pesci e dati. Verificare HUD/guide e avvisi sui carichi reali senza introdurre una nuova arena o cambiare driver/EGL. |

Separare l’anatomia condivisa di `Notice.qml` in componenti piccoli per intestazione, corpo e riga. Riutilizzare questi elementi nelle superfici `NoticeSmall/Large/Inbox/Detail/Urgent`; non duplicare filtri o regole di consegna nel QML. `Rows`, `Panel`, `PageCanvas`, `Metric`, `TopicDashboard` e `DashboardCards` sono i punti di allineamento comuni. Ogni variazione condivisa richiede il controllo delle superfici che la usano.

Tastierino conservato: 3 Avvisi; 2/8 Scorri; 5 Apri/Dettagli nella vista appropriata; 7 Indietro; 1 Home; 4 Recenti/Storico dove previsto. Niente swipe o pressione lunga obbligatori. Il contesto della consultazione e il focus tornano allo stesso ID dopo un avviso.

## 5. Movimento, GPU e nitidezza

Qt Quick usa già il scene graph accelerato nel percorso target: non serve «accendere la GPU» come modifica grafica. Il lavoro utile è limitare preparazione sul thread UI, dimensione delle superfici elaborate e aggiornamenti superflui.

1. Partire dalle ricette attuali: navigazione 100 ms e banner 120 ms. Nessun rimbalzo, lampeggio, pulsazione continua o contatore animato per ogni avviso.
2. Confrontare `NumberAnimation` e `OpacityAnimator`/`XAnimator`/`YAnimator` su un wrapper isolato, con gli stessi contenuti e carichi. L’Animator aggiorna la proprietà QML alla fine: geometria dichiarata, hit test, acknowledgement e interruzioni devono restare coerenti.
3. Timer ordinario backend iniziale 8 secondi, avviato dall’acknowledgement di presentazione corretto. Il completamento dell’animazione non marca letto. Verificare sparizione, urgenza e cambio evento durante entrata/uscita.
4. Ridotto: dissolvenza breve senza spostamento ampio. Off: stato finale immediato, nessun ritardo introdotto. Stato finale, comandi e consegna uguali nelle tre modalità.
5. Profondità con superfici piene e ombra locale statica/precomposta; nessun layer offscreen su tutte le righe. Blur dinamico escluso dalla candidata base.
6. Banco separato per testo piccolo, orologio e icone: stesso contenuto/dimensione, confronto dei renderer supportati dal target. Cambiare qualità/atlante soltanto sui casi con beneficio dimostrato. Nessun cambio globale di font, MSAA o driver per una preferenza estetica.

Ricerca e motivazione sono raccolte nelle due analisi: Apple HIG, WCAG, studi di leggibilità/interruzione e documentazione Qt 6.8. Le durate e i budget qui proposti sono scelte SmartPC da misurare, non risultati garantiti da quegli studi.

## 6. Verifiche e criteri di accettazione

Consultare `python3 scripts/check-dashboard.py --suite all --list` e selezionare i casi pertinenti; risultati in una directory nuova della candidata. Nessuna ripetizione delle ricevute già positive senza nuovo delta/dipendenza/errore. Non usare il rapido come certificazione completa.

| Gate | Aspettativa e controllo proporzionato |
| --- | --- |
| G1 · Semantica | Regressioni D01–D05, inclusi vero `Format.js` e testo visibile QML. Controlli noti: usato 34 → residuo 66; 0 °C resta 0; reset 0 → assente; 0/assente → 0–—; qualifica e gara non scambiano tempo/gap. `check_dashboard_summary`, `check_theme_api_contract/runtime/adapters`, `check_motorsport` e casi dominio modificati. |
| G2 · Identità/cache | Righe riordinate, due sessioni con stessi piloti, cambio disciplina/anno, cache vecchia, dati presenti → assenti → presenti; nessuna lettura o dettaglio passa all’ID vicino. Vecchie cache leggibili e selezioni/preferiti conservati. |
| G3 · Eventi | Un avviso e coda, quiete, configurazione, revoca/scadenza/rettifica, ritorno, fonte offline e riconnessione senza replay scaduto. `check_events`, `check_notifications`, `check_notification_updates`, `check_notification_consultation_ui` e `theme-acceptance-notifications` secondo il delta. Apertura elenco ≠ lettura di tutti; ack ≠ visto. |
| G4 · API/fallback | Generati e fixture coerenti, nessun accesso privato dal tema, preflight reale passato. Base/Functional e nuova revisione Apple Calm utilizzabili, urgente fallback indipendente. Controlli contratto/layout e runtime fixture selezionati dal runner. |
| G5 · Layout | QML target 960×640 giorno/notte, scala 1/1,1, tutte le viste modificate. Nomi lunghi, numeri massimi, 0/1/molti, fonti/errori lunghi, header con Quiete+Ripristino+badge. Nessuna collisione o testo essenziale coperto dal banner; testo completo recuperabile. `check_theme_layout_ui`, casi UI notifiche e domini interessati. |
| G6 · Movimento | Stesso stato finale nelle tre modalità; comparsa/uscita interrotte, urgente nel mezzo, elenco/ritorno. Nessun acknowledgement anticipato dalla sola creazione del componente; nessun timer di lettura spostato nel tema. |
| G7 · ARM/EGLFS | Stessi byte e Qt target, nessun warning QML sulle superfici interessate; GPU/backend registrati. Home, liste/dati in aggiornamento, Gara/allenamento e Acquario 3D con avvisi/urgente. Un pass PC Qt 6.11 non sostituisce questo gate. |
| G8 · Prestazioni | A/B o ABBA con riscaldamento separato e campione dichiarato per carico, almeno 200 intervalli utili per condizione. Obiettivo candidato p95 ≤18,5 ms e nessuno stallo >50 ms durante animazione; riportare p99/massimo, avvio freddo e variabilità. Se la baseline non passa, documentare e isolare la causa prima di attribuirla al restyling. CPU/RSS/temperatura confrontate; budget RSS fissato dopo baseline, nessun nuovo ciclo continuo in idle. I tempi software non sono FPS ottici o latenza fisica. |
| G9 · Pannello/input | Lettura alla distanza abituale giorno/notte, testi completi durante gli 8 s, scala 110%, tastierino reale, ritorno/focus. Se non leggibile: meno contenuto, caratteri maggiori o durata motivata; non riduzione automatica del font. Richiede riscontro fisico. |
| G10 · Live/conservazione | Verifiche provider pertinenti e confronto di identità/orario/valore, senza falsi gol o disponibilità. Gate reali gol/VAR, F1/MotoGP attivi e transizioni LAN restano dichiarati aperti finché non osservati. Database/preferenze/piloti/pesci conservati; manifest e rollback verificati. |

Chiusura del codice: G1–G6 passati sul delta finale. Candidata verificata sulla board: aggiungere G7/G8. Grafica accettata fisicamente: aggiungere G9. Qualifica live: solo per le porzioni di G10 effettivamente osservate; non attribuirla a fixture. Un effetto facoltativo che fallisce il confronto viene escluso senza rinviare le correzioni semantiche.

## 7. Pacchetto, versioni e consegna

Il bundle attuale rimane una revisione immutabile e di rollback. Per il nuovo insieme grafico è proposta una revisione **Apple Calm 1.7.0** con API minima coerente con l’estensione; non è stata ancora assegnata o creata. La candidata runtime successiva si numera al congelamento, dopo aver verificato che rc.4 sia ancora la baseline: nessun bump o promessa di rc.5 a partire dal solo checkout sporco.

Prima di installare: confrontare il manifest effettivo, preparare sorgenti dalla baseline e applicare solo il delta, eseguire preflight/packaging e verificare hash. Durante la consegna: backup coerente a servizio fermo di runtime, configurazioni e dati/DB con journal/WAL; verificare la copia e conservare il precedente rollback. Niente pulizia automatica o rimozione di temi, quarantena, dati Gioco/Acquario e preferenze.

Dopo installazione: manifest, servizio attivo, GUI heartbeat recente, `NRestarts`, warning QML, tema realmente attivo e dati/preferenze conservati. Se il gate fallisce, ripristinare il rollback verificato secondo la procedura del progetto. Reboot e prova di ripristino si dichiarano eseguiti soltanto quando svolti. Riferimento vincolante: [maintenance-policy.md](../../os/maintenance-policy.md).

## 8. Stato dell’attuazione · 30 ottobre 2026

Autorizzazione ricevuta: «Vai implementa tutto». Il [report di implementazione](v0102-apple-calm-implementation-report.md) distingue prove iniziali, correzioni del banco, incidente di consegna, rollback e ricevute finali.

| Fase | Stato effettivo |
| --- | --- |
| Analisi, tavole e audit | Completati; tavole e fixture rimangono sintetiche. |
| I0 | Baseline rc.4 identificata per hash; delta separato dal checkout Gioco di ricerca, librerie native preservate. |
| I1/I2 | Correzioni D01–D05 e API 2.15 implementate; 33 regressioni finali PC/ARM, generati/typeinfo/corpus coerenti. |
| I3/I4 | Notifiche, header, icone e viste implementati in Apple Calm 1.7.0; 285 casi EGLFS finali senza warning QML. |
| I5 | Scelta conservativa conclusa: GPU esistente verificata, ABBA registrato, NumberAnimation mantenuto; niente blur dinamico. Normale/Ridotto/Off verificati. |
| I6 | Preflight 1.098 PC/1.098 ARM, Main/QML giorno/notte/110% e scene con banner passati. Lint ARM escluso esplicitamente; lint target PC passato. G7 esteso Gara/apprendimento e G8 completo restano aperti. |
| I7 | Core 0.10.2-rc.5 e tema 1.7.0 installati dopo backup verificato. Servizio reale pronto, NRestarts=0, preferenze/dati/piloti/pesci preservati. Due tentativi iniziali ripristinati; consegna finale riuscita dopo separazione e drenaggio dell’I/O di backup. |
| G9 / live G10 | Pannello e tastierino fisici, eventi reali e soak prolungato aperti; nessuna qualifica attribuita alle fixture. |

La consegna comprende tutte le viste previste. Il passaggio a stabile richiede i gate fisici/live e di carico prolungato ancora aperti; non richiede altro lavoro grafico per rendere concreta e revisionabile questa candidata.
