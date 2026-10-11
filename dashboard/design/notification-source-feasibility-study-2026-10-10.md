# SmartPC — Studio delle fonti per notifiche e aggiornamento dati

**Revisione 1 · 10 ottobre 2026 · Europe/Rome · Analisi e letture pubbliche, nessuna integrazione o installazione.**

## 1. Esito e scelta proposta

Per tutte le partite di Serie A esiste una candidata gratuita più promettente di quelle approfondite nel primo dossier: **Bzzoiro Sports Data (BSD), REST v2**. Documenta calendario, risultati, incidenti/VAR, una quota di 7.500 richieste al giorno e una licenza per visualizzazione e conservazione interna. Propongo di qualificarla per prima nello scenario **0 €/mese**, riconfermato esplicitamente dall'utente durante questo studio. Richiede un account/token: lo studio non li ha creati o utilizzati. La fonte non è ancora approvata per il live di SmartPC.

Le alternative a pagamento restano nel confronto per spiegare cosa offrono e **sono escluse dal piano a costo zero**. BSD pubblica un add-on push a **7 USD/mese** nel listino, mentre una pagina della documentazione riporta ancora **3 USD/mese**. APIfootball.com offre un altro percorso WebSocket; API-Sports e Sportmonks alternative REST. Queste opzioni si riesaminerebbero solo con un nuovo requisito di budget. [Listino BSD](https://sports.bzzoiro.com/pricing/), [documentazione socket BSD](https://sports.bzzoiro.com/docs/websocket/).

Le altre fonti richiedono un sistema **ibrido**: stream F1 già presente, eventi iliadbox con recupero HTTP, possibile notifica dei limiti Account sul PC, Meteo/DPC e MotoGP con letture circoscritte. Non occorre un nuovo server cloud per gestire gli avvisi locali.

Perimetro: tutte le partite di Serie A anche a pagina chiusa; Fantacalcio su apertura/cache/refresh manuale; Casa esclusa. Il [piano v0.8.8](notification-data-update-analysis-2026-10-10.md) mantiene rc.1 gestore, rc.2 calcio, rc.3 altre fonti, rc.4 consegna. Questo studio aggiorna la scelta delle fonti, senza autorizzare acquisti o promettere il live.

## 2. Metodo e grado delle evidenze

| Evidenza | Cosa dimostra | Cosa resta da provare |
| --- | --- | --- |
| Documentazione del fornitore | Endpoint, schema, piani, vincoli e capacità dichiarate. | Dati effettivamente disponibili al nostro account e qualità durante gli eventi. |
| Codice corrente | Percorso di acquisizione, filtri, timer, gate e normalizzatori già presenti. | Comportamento attuale della board e disponibilità del servizio remoto. |
| Lettura pubblica eseguita oggi | Risposta HTTP/schema su quello specifico percorso, dal PC. | Autenticazione sport, gol, ritardo, continuità, push e Orange Pi. |
| Prova futura durante evento reale | Capacità osservate, gap, correzioni e latenza rispetto al riferimento annotato. | Non costituisce da sola una garanzia per tutte le partite/sessioni. |

Ricerca su fonti primarie. Confronti commerciali del singolo fornitore non usati come prove contro i concorrenti. Nessun token cercato nei file privati; nessun account/trial/abbonamento attivato, messaggio inviato o chiamata di inferenza eseguita. Le evidenze locali del router sono precedenti e datate, non nuovi controlli della iliadbox.

**Nuove letture dal PC**, conservate in [public-readonly-probes.json](evidence/v088-source-study-2026-10-10/public-readonly-probes.json):

- BSD `/api/v2/coverage/?sport=football`: HTTP 200, oggetto JSON. È una disponibilità aggregata per sport, non la prova della completezza Serie A.
- BSD `/api/v2/events/live/` senza token: HTTP 401. Serve l'accesso previsto; nessun tentativo di aggirarlo.
- OpenF1 `/v1/sessions?year=2024&session_name=Race`: HTTP 200, 24 sessioni storiche. Nessuna qualifica del live.
- Indice bollettini DPC: HTTP 200, 978.930 byte, `ETag`, `Cache-Control: no-store`. Subito dopo, `If-None-Match` con lo stesso ETag: ancora HTTP 200 e stesso contenuto, non 304. Non promettere un risparmio del payload su questo percorso; rispettare `no-store` per la cache HTTP e distinguere la persistenza applicativa dei dati normalizzati.
- Schema pubblico BSD: HTTP 200, OpenAPI 3.0.3 in **YAML**, 702.998 byte nella lettura completata. Il primo tentativo di interpretarlo come JSON è fallito; corretto il formato. La descrizione generale conserva “30+” competizioni mentre il sito ne dichiara di più: usare le capacità effettive, non il numero marketing.
- Schema **offline** di `codex-cli 0.159.0`: contiene `account/rateLimits/updated`. [Evidenza](evidence/v088-source-study-2026-10-10/account-offline-schema.json). Generazione in directory temporanea eliminata; nessuna sessione app-server o modifica dell'account.

## 3. Il requisito calcio non è un solo punteggio

| Capacità | Dato richiesto | Comportamento consentito |
| --- | --- | --- |
| Calendario | Identità competizione/stagione/partita, kickoff e rinvii. | Pianificare le finestre; ora futura non confermata resta tale. |
| Risultato corrente | Punteggio, fase e acquisizione valida recente. | «Risultato aggiornato»; non inventare marcatore o conferma VAR. |
| Gol segnalato | Incidente gol, lato, punteggio coerente e identità deduplicabile. | Testo esplicitamente segnalato dalla fonte, se la capacità viene qualificata. |
| Conferma/revoca | Stato della revisione o decisione esplicita, legame con incidente e punteggio. | «Confermato» solo con prova adeguata; revoca/correzione aggiorna avviso e storico. |
| Inizio/intervallo/finale | Transizione di fase riportata dalla fonte. | Un avviso per transizione nuova, non per la sola scadenza dell'orologio locale. |
| Recupero | Snapshot completo e identità; replay/cursori soltanto se documentati. | Baseline silenziosa al primo avvio/reconnect; niente raffica di vecchi gol. |

Le capacità sono per fonte **e per incontro**. Un valore assente non diventa `false`: in particolare, non inventare `pendingVAR=false` per far passare il tracker esistente. La stabilità dello score per due letture non dimostra una conferma arbitrale.

## 4. Confronto Serie A

Prezzi pubblicati consultati il 10 ottobre; USD ed EUR restano separati, nessuna conversione o imposta inventata. Token necessario salvo i backend attuali non documentati come servizi per sviluppatori.

| Fonte | Costo/accesso pertinente | Trasporto e copertura dichiarati | Esito per SmartPC |
| --- | --- | --- | --- |
| **BSD REST v2** | Gratuito, 7.500 richieste/giorno/account, token, fair use. | Serie A nella copertura; lista live aggregata, incidenti/VAR separati. Cache server live circa 10–30 s. | **Prima candidata da qualificare a costo zero**; resta polling e la conferma gol non è automatica. |
| **BSD WebSocket** | Add-on 7 USD/mese nel listino; doc overview 3 USD, da chiarire. | Copertura `basic/full` verificabile per match; massimo 10 sottoscrizioni/socket. | Candidata tecnica push **esclusa dal piano 0 €**; copertura/correzioni ancora da provare. |
| **APIfootball.com** | European 21 USD/mese, 1.000 chiamate/ora/endpoint; gratuito senza Serie A. | WebSocket documentato e filtro league; Serie A nel piano European. | Seconda candidata push; incidenti, VAR, ripresa e inclusione socket da provare. |
| **API-FOOTBALL / API-Sports** | Free 100/giorno, stagioni limitate; Pro 19 USD/mese, 7.500/giorno. | REST fixtures/eventi, frequenza di aggiornamento dichiarata 15 s, VAR documentato. | Alternativa REST; gratuito insufficiente alla cadenza prevista. Nessun socket calcio stabilito dalle fonti consultate. |
| **Sportmonks v3** | Starter 29 EUR/mese, IVA esclusa, 5 leghe selezionabili, 2.000 chiamate/ora per entità. Free Danimarca/Scozia. | Serie A, REST con `events`, ID incidenti, ordinamento e VAR. | Buona candidata se prevale ricchezza degli eventi; **non gratuita per Serie A**, polling documentato. |
| **football-data.org** | Free con score ritardati; livescore 12 EUR/mese; Deep Data con marcatori 29 EUR/mese, eventuale IVA. | Serie A; REST, score e fase; dettaglio dipendente dal piano. | Free per consultazione con ritardo esplicito; piano 12 EUR utile per score, non automaticamente gol/VAR completi. |
| FotMob attuale | Nessun costo tecnico osservato, ma accesso automatico ristretto dai termini. | Backend usato dal checkout, senza contratto API pubblico qualificato qui. | Non approvare nuova acquisizione sistematica senza accesso consentito. |
| ESPN attuale | Backend del sito; contratto specifico per questi endpoint non stabilito. | REST score/stato; parser attuale non conferma gli incidenti gol. | Non usarlo come promessa di un nuovo servizio live autorizzato/completo. |

Fonti: [BSD piani](https://sports.bzzoiro.com/pricing/), [BSD copertura](https://sports.bzzoiro.com/football-coverage/), [APIfootball piani](https://apifootball.com/), [copertura European](https://apifootball.com/coverage/?plan=1), [API-Sports piani](https://www.api-football.com/pricing), [guida API-Sports](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide), [Sportmonks live/piani](https://www.sportmonks.com/football-api/solutions/livescore-api/), [Sportmonks free](https://www.sportmonks.com/football-api/free-plan/), [football-data piani](https://www.football-data.org/pricing).

### BSD: perché approfondirla per prima

La [licenza dati v4, efficace dal 1 ottobre 2026](https://sports.bzzoiro.com/docs/api-license/) contempla dashboard, conservazione interna e snapshot per studiare revisioni; vieta rivendita/mirror dei dati grezzi e aggiramento dei limiti. I [termini](https://sports.bzzoiro.com/docs/terms/) non promettono uptime. La copertura pubblicata indica Serie A 26/27 con timeline sulle partite già disputate: è una dichiarazione del provider, non un nostro confronto con tutti gli incontri del campionato.

Percorso REST documentato: discovery lega/stagione → `/api/v2/events/` per calendario → `/api/v2/events/live/?league_id=…` aggregato → `/api/v2/events/{id}/incidents/` mirato. Risolvere gli ID; non riutilizzare `55` FotMob o `207` di un altro servizio. La lista live ha una finestra vicino all'incontro: conservare anche le partite attese e riconciliare gli incontri appena usciti dalla lista. [Eventi BSD](https://sports.bzzoiro.com/docs/football/events/), [convenzioni](https://sports.bzzoiro.com/docs/conventions/).

Lo [schema OpenAPI](https://sports.bzzoiro.com/api/schema/) specifica `varDecision` con decisioni come `goalNotAwarded`/`goalAwarded`. **`confirmed` in una decisione VAR indica che la decisione sul campo è rimasta invariata**: non è un booleano generale «questo gol è confermato». Incidente `review` può non avere l'esito. Le righe sono descritte come oggetti variabili, senza ID incidente stabile promesso nello schema letto: deduplicazione, associazione gol/VAR e ordine vanno provati. Punteggio dopo incidente aiuta, ma non elimina questa lacuna.

La [documentazione socket calcio](https://sports.bzzoiro.com/docs/websocket/football/) distingue `basic` da `full`: quest'ultimo include azioni provvisorie, `goal`, `deleted_event` e una storia alla sottoscrizione. Gli esempi non stabiliscono un ID univoco dell'azione da cancellare. Prima di certificare revoche, verificare il legame reale o ricostruire lo stato dal REST. La latenza promozionale non è misurata né garantita per SmartPC.

L'[overview socket](https://sports.bzzoiro.com/docs/websocket/) impone risottoscrizione dopo reconnect e rende disponibili flag per incontro: `live_websocket`, `websocket_plus`. Dieci slot possono coprire dieci partite, ma questo non dimostra che tutte siano sottoscrivibili. Non aggiungere sottoscrizioni a quote/telemetria: non servono agli avvisi e consumano slot/traffico. Serve ancora discovery delle partite imminenti via calendario/REST.

### Le alternative non sono intercambiabili

**APIfootball.com** è un'azienda/servizio diverso da **API-FOOTBALL / API-Sports**. Il primo documenta un socket con filtro competizione e payload partita/marcatori; gli esempi non provano ID incidente, conferma VAR o replay. La pagina della copertura European menziona v2, la documentazione corrente dichiara v3.0.2: verificare discovery v3 e stagione col proprio accesso. I [termini](https://apifootball.com/terms_of_use/) consentono conservazione dei dati, ma non promettono disponibilità. La chiave nell'URL va esclusa da log/evidenze. [Protocollo](https://apifootball.com/documentation/).

**API-Sports** documenta [eventi VAR](https://www.api-football.com/news/post/var-events) dal 2020/21. Non assumere che un evento “Var” confermi sempre un gol: leggere il tipo/dettaglio reale. La guida propone lista fixtures live e dettagli evento; copertura/campi per lega-stagione sono da leggere col token. Il gratuito consente piccoli campioni, non il monitoraggio completo al ritmo richiesto.

**Sportmonks** documenta ID e `sort_order` degli incidenti, tipi di revisione e revoca. Recuperare la tassonomia dal provider; nomi descrittivi delle guide non sono sempre enum da inviare/parsing diretto. La pagina `latest` restituisce aggiornamenti degli ultimi **10 secondi**: interrogandola ogni 30–60 s si rischiano gap. Preferire snapshot completi di incontri rilevanti o una cadenza compatibile, con riconciliazione dopo ogni interruzione. Un endpoint “latest” resta polling. [Eventi](https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/includes/events), [tipi](https://docs.sportmonks.com/v3/definitions/types/events), [livescores](https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/livescores).

**football-data.org** separa livescore da Deep Data; l'[esempio match v4](https://docs.football-data.org/general/v4/match.html) comprende score per gol ma non stabilisce un ID incidente o stato VAR. Il ritardo gratuito non ha una durata garantita nella pagina prezzi consultata: non attribuirgli minuti inventati. [Copertura Serie A](https://www.football-data.org/coverage).

### Fonti da non scegliere come scorciatoia

FotMob [vieta recuperi automatici sistematici e richiede consenso scritto per uso dei dati](https://www.fotmob.com/tos.txt). Il successo storico delle GET non chiude questo gate. Per ESPN, il [supporto ufficiale](https://support.espn.com/hc/en-us/articles/360035445091-Terms-of-Use) rinvia ai termini Disney: il [testo generale statunitense consultato](https://disneytermsofuse.com/english/) restringe l'estrazione automatizzata senza permesso. Non costituisce verifica di tutti i termini regionali/specifici; non emerge qui una concessione per integrare gli endpoint attuali. Proposta: fonte con accesso API esplicito per il nuovo calcio autonomo.

TheSportsDB distingue [gratuito e Premium](https://www.thesportsdb.com/documentation): livescore e v2 sono Premium, quindi non risolve il requisito Serie A live gratis. Non qualificate qui conferme VAR/push. Il precedente [studio Sport](v06-sport-api-research.md) conserva dataset per sviluppo/storico, che non sono stati qualificati come feed di tutte le partite correnti. Backend di altri siti o wrapper comunitari non danno da soli un contratto per usare i dati.

[Sportradar Soccer Push](https://developer.sportradar.com/soccer/docs/soccer-ig-push) è un'alternativa professionale a preventivo/add-on Realtime, non inclusa nel trial self-service. Lo stream HTTP non conserva replay e non sostituisce REST; alcuni cambi di stato richiedono altri feed. Non proposto per il budget attuale. La sola [pagina iniziale Distribution API della Lega Serie A](https://dapi.legaseriea.it/) non documenta un accesso gratuito per sviluppatori: nessun endpoint dedotto o esplorato.

## 5. Quante richieste servono davvero

Calcoli progettuali, non traffico misurato. Per una richiesta periodica: `richieste = durata / intervallo`; sommare pagine, dettagli, retry e discovery. Un endpoint aggregato di competizione non moltiplica le richieste per il numero di partite simultanee.

| Finestra di acquisizione aggregata | Ogni 15 s | Ogni 30 s | Ogni 60 s |
| --- | ---: | ---: | ---: |
| 2 ore | 480 | 240 | 120 |
| 6 ore | 1.440 | 720 | 360 |
| 10 ore | 2.400 | 1.200 | 600 |

Scenario oneroso di confronto: 10 incontri × 2 ore di dettagli ogni 30 s = 2.400 richieste; scoreboard aggregato per 6 ore = 720; totale **3.120**, prima di discovery/retry. Non è la politica raccomandata: dettagli mirati su cambi e incidenti pendenti riducono questo lavoro. La quota BSD 7.500/giorno appare compatibile sulla carta, il gratuito API-Sports 100/giorno non copre neppure il solo scoreboard per 2 ore a 60 s. Il budget va verificato per account e reset UTC; il consumo del PC di studio non si confonde con quello della board.

Per BSD partire, dopo qualifica, da 30–60 s durante incontri pertinenti; non interrogare più rapidamente della cache per inseguire un punteggio. Fuori finestra: calendario lento, una scadenza verso kickoff, recupero dei rinvii; nessun loop per partita inattiva. Quote lette dagli header quando presenti, budget persistente o recuperato dopo reboot e limite ai retry. [Limiti/cache BSD](https://sports.bzzoiro.com/docs/conventions/).

Latenza totale = alimentazione del provider + cache server + attesa del prossimo poll + rete/elaborazione + eventuale revisione VAR + presentazione. Per il solo polling a intervallo P, l'attesa aggiunta nominale è fra 0 e P, circa P/2 in media assumendo arrivi uniformi. Il push elimina quel termine, non gli altri. Nessuna stima qui è una garanzia di tempo dal gol sul campo al display.

Un socket con tutte le azioni di gioco può consumare più traffico/elaborazione di un piccolo REST periodico. Richiedere pochi topic e consolidare cambi; confrontare byte, richieste, wakeup, CPU/RAM e pubblicazioni QML su un carico equivalente. Non dichiarare una percentuale di risparmio prima della misura.

## 6. F1: riuso del push e alternativa documentata

`F1Timing` in [racing_timing.py](../racing_timing.py) usa già QWebSocket/SignalR Core e topic di stato, timing e Race Control. Miglioramento primario: emettere cambi consolidati all'arrivo dei delta, conservando scadenze di sessione/freschezza. Gli snapshot di sessioni concluse conservati dal progetto non certificano una gara attiva.

Il [client upstream FastF1](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/livetiming/client.py) è riferimento tecnico, non un contratto dati con Formula 1; può richiedere autenticazione o fornire un sottoinsieme senza di essa. Proposta a costo zero: qualificare il percorso esistente per capacità osservata. Se arrivano solo alcuni topic, abilitare solo gli eventi supportati; nessun login o abbonamento dedotto dalla riuscita del socket.

**OpenF1** offre un'alternativa comunitaria con API documentata: storico gratuito dal 2023 e live **Sponsor 9,90 EUR/mese** per uso personale; live da 30 minuti prima a 30 minuti dopo la sessione, secondo il servizio. Non è una fonte ufficiale F1. La lettura pubblica di oggi prova lo storico, non questo accesso live. [Accesso, limiti e uso](https://openf1.org/).

Il [trasporto OpenF1](https://openf1.org/auth.html) usa MQTT TLS oppure **MQTT sopra WebSocket**, non JSON libero direttamente su QWebSocket; token OAuth con scadenza, `_id` ordinabile e `_key` per revisioni. I due campi non garantiscono replay dopo un gap. Sottoscrivere solo sessione/Race Control/dati necessari, riconciliare via REST e verificare notifiche senza sovrapporre stream con identità diverse. Candidato eventuale, fuori dal vincolo zero; nessuna ragione di migrare prima di qualificare l'esistente.

**Jolpica** resta adatto a calendario e risultati/classifiche, non ai messaggi istantanei di direzione gara. Limiti anonimi documentati 4 richieste/s e 500/ora; il codice applica un margine locale più prudente. [Limiti upstream](https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md). Non fare polling continuo dello storico per imitare il live.

## 7. MotoGP: nessun push API qualificato

Percorso corrente: PulseLive REST per programma/referti e `timing-gateway/livetiming-lite` per timing, in [motorsport.py](../motorsport.py) e [racing_timing.py](../racing_timing.py). Il progetto ha verifiche di dati, ma non un contratto pubblico di accesso, quota o socket garantito per applicazioni terze. Non sono stati effettuati nuovi probe del timing in questo studio.

Il [TimingPass ufficiale](https://www.motogp.com/it/news/2025/06/20/il-timingpass-si-evolve-arrivano-live-timing-sync-e-lap-chart/752169) è un prodotto di consultazione per persone: non implica una licenza API o l'accesso a un socket da integrare. Non aggiungere quell'abbonamento al budget tecnico assumendo che risolva il problema.

Proposta: conservare il percorso come capacità da qualificare, circoscrivere le letture alle sessioni MotoGP, rallentare fuori sessione e riconciliare al finale. Il polling oggi si estende a finestre ampie del weekend; 60 s per 3 giorni costano teoricamente 4.320 letture del solo timing, mentre 6 ore totali costano 360. È un confronto di finestre, non una misura della board. Categoria/GP/sessione, timestamp e stato esplicito restano obbligatori; codice sconosciuto non genera bandiere o avvisi.

## 8. Meteo e Protezione Civile

**Open-Meteo**: mantenere la fonte e la lettura circa ogni 15 minuti, cache applicativa e stato precedente/offline. Il [servizio free](https://open-meteo.com/en/terms) è per uso non commerciale con CC BY 4.0 e limiti pubblicati; una lettura ogni 15 minuti è circa 96/giorno per URL, prima di retry e varianti. Se SmartPC cambia destinazione commerciale, riesaminare il piano. Non è stato identificato un contratto push utilizzabile nel percorso attuale.

Le [condizioni correnti](https://open-meteo.com/en/docs?past_days=1) sono basate su dati di modello, non una stazione locale. I [metadati di aggiornamento](https://open-meteo.com/en/docs/model-updates) riguardano singoli modelli e non corrispondono automaticamente al risultato Best Match. Aggiungere polling dei metadati non significa risparmiare: mantenere la cadenza semplice finché le misure non giustificano un cambiamento.

**DPC**: mantenere [repository ufficiale e licenza CC BY 4.0](https://github.com/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica). Pubblicazione normalmente entro le 16:00, possibili aggiornamenti/errata corrige dopo; 156 zone, oggi/domani. Non ridurre a una sola lettura al giorno e non dedurre allerta dalle precipitazioni previste. Il provider corrente filtra Angri e distingue validità/emissione.

La prova HTTP mostra che l'ETag dell'indice non ha prodotto 304. Il documento pesa circa 0,98 MB: 48 letture/giorno sarebbero circa 47 MB/giorno di soli corpi HTML se dimensione e risposte restassero uguali. Valutare un indice ufficiale più piccolo o una cadenza adattiva **con limite di ritardo dichiarato**, non eliminare la riconciliazione dopo le 16:00. GitHub raw/REST e il sito DPC hanno contratti distinti; non trasferire automaticamente le regole di quota/304 di uno all'altro.

Gli eventi utili sono nuova allerta per zona, variazione di livello/rischio/validità, revoca/correzione e scadenza. Una nuova emissione equivalente non deve ripetere il banner; un aggiornamento dopo le 16:00 non va perso perché la data è uguale.

## 9. Account: evento documentato, copertura da misurare

Il watcher in [account.py](../account.py) reagisce già al file normalizzato. Il helper [account_sync.py](../account_sync.py) avvia un app-server, legge account/limiti e chiude; [timer PC](../systemd/smartpc-account-sync.timer) ogni 10 minuti. `AppServer.call()` scarta i messaggi che non corrispondono alla risposta attesa: non conserva oggi un ascolto delle notifiche dei limiti.

La [documentazione ufficiale OpenAI App Server](https://learn.chatgpt.com/docs/app-server) descrive **`account/rateLimits/updated`**, confermato come metodo nello schema locale offline 0.159.0. È una opportunità concreta: helper persistente o integrazione con il processo effettivamente osservato, normalizzazione del bucket aggiornato, trasferimento atomico solo al cambiamento. Mantenere lettura iniziale e riconciliazione lenta finché sia provato quando arrivano i messaggi.

**Gate decisivo:** la presenza del metodo non prova che un app-server separato e inattivo riceva ogni consumo fatto da altri processi/dispositivi. Provare cambi durante uso del client effettivo, reset, sessione/account cambiato, PC offline e riavvio. Non ridurre il timer esistente prima di questa verifica; non usare un aggiornamento parziale per cancellare gli altri bucket o marcare tutto fresco.

Sulla board rimangono watcher directory+file, recupero rename, heartbeat/scadenza, ultimo stato completo e soglie con isteresi. Un consumo che cambia ma non attraversa una soglia aggiorna la pagina, senza banner. Limiti ChatGPT/Codex, eventuali crediti workspace e fatturazione API sono dati distinti; campi mancanti non diventano credito zero. Nessuna azione di acquisto/reset/email fa parte di questa integrazione.

## 10. Rete: eventi del router con recupero

La [documentazione letta sulla iliadbox e lo studio del 7 ottobre](v08-iliadbox-api-study.md) documentano `ws/event`, `lan_host_l3addr_reachable` e `lan_host_l3addr_unreachable`; l'[evidenza PC](evidence/v08-iliadbox-study-2026-10-07/network-extra-capabilities.json) conserva handshake 101 e registrazione accettata, **non transizioni fisiche osservate**. Nessuna nuova chiamata al router nello studio odierno.

Proposta: inventario completo → socket che invalida/rilegge l'host → riconciliazione completa lenta. Acquisizione metriche Wi-Fi/porte/traffico conserva il proprio interesse di vista: gli eventi di raggiungibilità non sostituiscono campioni o storico. Il [client corrente](../network.py) apre/chiude sessioni per worker; definire ownership della sessione persistente per non far invalidare il socket da un logout HTTP.

Provare token/permessi già registrati, TLS e identità del router, rinnovo sessione, cambio IPv4/IPv6, sonno/scollegamento e reboot box. “Indirizzo non raggiungibile” non equivale a “persona uscita” o “dispositivo spento”. Nessun agent sugli altri PC, nessun nuovo allarme per il solo socket chiuso.

## 11. Piano di qualifica e decisioni prima del codice

| Passo | Lavoro concreto successivo | Criterio di accettazione |
| --- | --- | --- |
| **F0 · Accesso** | Budget zero confermato; ottenere accesso BSD gratuito tramite account del titolare, token configurato fuori repository/QML. | Piano/termini e fonte annotati; nessun segreto in evidenze, nessun pagamento. |
| **F1 · Copertura e contratto** | Discovery Serie A/stagione, pagine di calendario, incontri passati con incidenti/VAR e schema reale. | Fixture corrette e complete per lo scope letto; null/ordine/ID/correzioni compresi. Schema incompleto conserva ultimo stato e degrada capacità. |
| **F2 · Partite reali** | Tutte le partite simultanee, a pagina Sport chiusa; inizio, score, gol, finale, rinvio e VAR se effettivamente presente. | Ricezione e banner tracciati separatamente; riferimento e timestamp annotati, nessun live dedotto da replay. VAR mancante resta gate aperto per quella capacità. |
| **F3 · Recupero** | Riavvio/offline, timeout, 401/429 e letture fuori ordine/gap per REST. Socket per le fonti gratuite già in scope; socket calcio escluso. | Baseline silenziosa, nessuna doppia notifica, revoche coerenti e budget rispettato; calendario e ultimo stato conservati. |
| **F4 · Altre fonti** | Sessione F1 attiva, evento Account realmente ricevuto, LAN fisica, revisioni DPC, MotoGP identificata. | Ogni fonte abilita soltanto capacità dimostrate; nessun test storico sostituisce l'evento reale. |
| **F5 · Board e risorse** | Poi integrazione autorizzata e candidate v0.8.8; confronto a parità di carico, tre temi e reboot. | Meno lavoro misurato, avvisi affidabili, nessun furto di focus o crescita non controllata; residui espliciti. |

**Scelta raccomandata oggi:** BSD REST da qualificare per tutta Serie A a costo zero; adapter separato dal trasporto, senza dipendenze dagli add-on pagati. Riutilizzare F1 e iliadbox dove osservabili; verificare il nuovo percorso Account; Meteo/DPC e MotoGP rimangono adattivi. Non è stata trovata e provata una soluzione gratuita di push universale per tutte queste fonti.

L'analisi è completata e il piano è reviewable. L'accesso BSD e la qualifica degli eventi reali restano i passi necessari per scegliere una fonte di produzione; non sono già eseguiti. Il gestore comune può essere realizzato in rc.1 indipendentemente da questi gate, dopo autorizzazione all'implementazione.
