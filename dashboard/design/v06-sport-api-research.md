# v0.6 Sport · ricerca API incrociata e verificata

**Revisione:** 30 settembre 2026. Prova privata, budget ricorrente €0, Serie A nella prima release; F1 e MotoGP preparati per estensioni successive. Questo documento integra la revisione dell'utente con la ricerca precedente e nuovi controlli riproducibili.

## 1. Decisione e stato effettivo

| Sport | Combinazione proposta | Cosa è verificato oggi | Cosa manca |
| --- | --- | --- | --- |
| **Serie A** | **FotMob REST diretto principale; ESPN confronto e possibile riserva** | Calendario, classifica, risultato e dettaglio della stessa partita dal PC e dalla Orange Pi. | Ritardo gol, correzioni VAR, inizio/fine e continuità durante una partita vera. |
| **F1** | **Jolpica per calendario/risultati/classifiche; client SignalR Core per timing** | REST attuale e storico dal PC e dalla board; connessione WebSocket e snapshot di otto topic senza login dal PC. | Aggiornamenti durante una sessione attiva e streaming sulla board. Il LiveF1 esaminato usa ancora il percorso legacy che ha risposto 401. |
| **MotoGP** | **PulseLive REST risultati/classifiche; `livetiming-lite` candidato live** | Stagioni 1949–2026, eventi, categorie e classifica corrente; payload timing leggibile dal PC e dalla board. | Sessione MotoGP attiva, significato degli stati e delle unità del timing, programma completo delle sessioni future. |

Questa selezione è adatta alla prova gratuita. Non è una misura di disponibilità continua né una garanzia che tutte le funzioni rimangano accessibili. F1: lo snapshot acquisito descrive una gara conclusa il 26 settembre; MotoGP: il payload descrive Moto3 FP1 del 2 ottobre non iniziata. Nessuno dei due va etichettato come live oggi.

## 2. Evidenze e metodo

Sono state effettuate **37 richieste HTTP dal PC e le stesse 37 dalla Orange Pi**, senza credenziali: in ciascuna esecuzione 33 risposte 200, un 404 e tre rifiuti di autenticazione (due 401, un 403). I rifiuti previsti servono a distinguere endpoint pubblici e protetti; il totale non è un punteggio di affidabilità. Sono registrati timestamp UTC, durata HTTP, tipo JSON, campi, dimensione, hash del corpo e header di cache. Un 200 vuoto non equivale a dati utili.

- [Report PC](./evidence/v06-provider-check-pc.json).
- [Report Orange Pi](./evidence/v06-provider-check-orange-pi.json).
- [Verifica mirata FotMob per data e xG storici dal PC](./evidence/v06-fotmob-detail-check-pc.json), due richieste aggiuntive.
- [Handshake e snapshot SignalR Core dal PC](./evidence/v06-signalrcore-check-pc.json).
- [Checker HTTP e sorgenti, Python standard library](./tools/check_sport_providers.py).
- [Checker WebSocket, Node con WebSocket integrato](./tools/check_f1_signalrcore.mjs).

Nessun account creato, nessun token richiesto o salvato, nessuna libreria importata dai wheel scaricati. I wheel FotMob sono stati soltanto aperti come archivi per leggere gli URL nel sorgente. I report non esportano cookie o token di connessione. La dashboard sulla board non è stata modificata o riavviata.

## 3. Incrocio delle analisi: correzioni sostanziali

| Affermazione nella revisione | Riscontro | Decisione nel piano |
| --- | --- | --- |
| FotMob necessita `Mozilla/5.0`; ESPN blocca browser o UA arbitrari | Con lo stesso client urllib, entrambi rispondono 200 con UA standard, applicativo e Mozilla dal PC e dalla board. | Usare UA trasparente. Nessuna diagnosi certa del precedente 403; nessun aggiramento di blocchi. |
| Classifica ESPN su `.../apis/site/v2/.../standings` | Il percorso risponde 200 ma non contiene la classifica; `.../apis/v2/.../standings` restituisce 20 squadre. | Correggere URL e validare contenuto, non solo HTTP. |
| Wrapper FotMob obsoleti | Confermato nel sorgente distribuito: `pyfotmob` usa `/api/teams`; `mobfot` ha base `/api`. Il vecchio `/api/leagues` dà 404. | Preferire adapter REST `/api/data/`, senza installare i due wrapper così come sono. |
| football-data.org già verificato con 200 | Senza token, l'endpoint partite SA risponde 403 in entrambi gli ambienti. | Funzioni e quota da listino; dati autenticati ancora da verificare. |
| F1 LiveF1/SignalR completamente disponibile a €0 | Il legacy `/signalr/negotiate` risponde 401; `/signalrcore` negozia e consegna snapshot base senza login. | Provare un client Core aggiornato. Non promettere dati attivi o telemetria senza una sessione osservata. |
| Solo `CarData.z` richiede abbonamento | Non provato. Il client FastF1 distingue accesso autenticato e `no_auth`, che può essere parziale. | Registrare capacità dei topic osservati; telemetria esclusa dalla prima estensione. |
| `A/R` = MotoGP attiva, `B` = verde, gap in millisecondi | Non dimostrato dal campione: abbiamo osservato `N`, gap testuali e piloti ai box con `trac_status=B`. | Conservare valori raw; codici sconosciuti diventano `unknown`. Niente mappature inventate. |
| Cache `/tmp/...` valida dopo reboot | `/tmp` non garantisce persistenza; servizio board configura CacheDirectory/StateDirectory. | Cache sotto la directory persistente dell'app e registro eventi persistente. |
| Risultato definitivo congelato dopo 15 minuti | Le fonti possono correggere il referto anche dopo il fischio finale. | Ricontrollo finale, a circa 1 ora e il giorno successivo; storico aggiornabile. |
| 30 secondi è sotto qualunque rate limit | Nessuna quota pubblicata individuata per ESPN/FotMob. Il numero di endpoint moltiplica il carico. | Budget per endpoint, backoff e rispetto di `Retry-After`. |
| `soccerdata`/FBref = storico illimitato offline | Scraper HTTP; il caching riduce richieste ma non elimina limiti della fonte. | Strumento analitico facoltativo sul PC; dati offline esplicitamente etichettati. |

## 4. Calcio: funzioni, percorsi e confronto

### FotMob principale candidato

Base: `https://www.fotmob.com/api/data/`. Serie A: lega `55`, verificata nel payload. Accesso senza token riuscito oggi.

| Percorso | Riscontro |
| --- | --- |
| `leagues?id=55&ccode3=ITA&season=2026%2F2027` | 380 fixture, 50 concluse nel campione, classifica e lista delle stagioni precedenti. |
| `tltable?leagueId=55` | Classifica con 20 squadre. |
| `matchDetails?matchId=5749645` | Inter–Monza del 22 agosto 2026, 4–1; eventi, formazioni, cronaca, statistiche e shotmap popolati. |
| `leagues?id=55&ccode3=ITA&season=2024%2F2025` | 380 fixture di una stagione storica. |
| `matches?date=YYYYMMDD` | 200 nella verifica mirata del 22 agosto: quattro incontri Serie A. Usare la data esplicita per giornata, non come calendario completo della stagione. |

La verifica mirata ha mostrato xG del match campione 1,05–1,23, con valori raw numerici e valori di visualizzazione testuali. Il loro aggiornamento durante una partita non è stato misurato. Gli xG sono accessori e non devono ritardare punteggio, stato o calendario. Un blocco presente può contenere righe di intestazione con valori nulli: distinguere i valori effettivi.

**Parsing:** nei dettagli `header.teams[].score` è numerico; nelle fixture il risultato è in `status.scoreStr`. Il payload espone in radice `hasPendingVAR: bool` (cruciale per inibire false notifiche durante verifiche arbitrali) e `ongoing: bool` (stato di partita attiva). In `header.status` sono esposti `started`, `finished`, `cancelled` e gli orari di avvio/fine tempi in `halfs`. Una gara non iniziata resta senza punteggio, anche se una fonte inserisce 0–0. Statistiche vuote/null non diventano zero. Stati `finished`, `started`, `cancelled` vanno interpretati insieme al motivo; supplementari e rigori restano distinti dal risultato regolamentare quando aggiungeremo coppe.

[pyfotmob su PyPI](https://pypi.org/project/pyfotmob/) 0.0.3 (2023) e [mobfot su PyPI](https://pypi.org/project/mobfot/) 1.4.0 (2024) puntano nel sorgente ai percorsi precedenti. Non sono provider alternativi a FotMob: dipendono dalla stessa fonte. Per il percorso nuovo, il [client recente FotMob-API](https://github.com/writeshh/FotMob-API) documenta REST e cache; è un riferimento, non una dipendenza Node necessaria al prodotto.

### ESPN confronto e riserva candidata

```text
https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard
https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard?dates=YYYYMMDD
https://site.api.espn.com/apis/v2/sports/soccer/ita.1/standings
https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/summary?event={id}
```

È stato confrontato lo stesso incontro: FotMob `5749645`, ESPN `401874931`. Orario 22 agosto 2026 alle 16:30 UTC e risultato 4–1 coincidono. ESPN nomina la squadra `Internazionale`, FotMob `Inter`: occorre una mappa di identità esplicita. Non confrontare partite solo perché iniziano alla stessa ora.

Il summary ESPN contiene cronaca, key events, roster, boxscore e classifica non vuoti. È evidenza di dettaglio su una gara conclusa, non prova di cronaca tempestiva. Lo scoreboard predefinito ha mostrato tre partite future; non assumerlo come intero calendario di stagione. Gli intervalli di date provati in precedenza hanno dato 400: usare date singole verificate.

Il precedente 403 rimane un'osservazione storica. I test attuali non ne dimostrano la causa TLS, non misurano l'effetto di curl e non garantiscono disponibilità futura. L'accesso dalla Orange Pi è riuscito nel campione.

### Altre fonti gratuite

- **BSD:** [listino](https://sports.bzzoiro.com/pricing/) free calcio 7.500 richieste/giorno, token gratuito; REST include live, WebSocket a pagamento. Pubblico `coverage` 200, live senza token 401. [Endpoint](https://sports.bzzoiro.com/docs/football/events/) e copertura sono documentati; continuità e latenza non misurate. Una riserva ancora da abilitare, non un fallback pronto.
- **football-data.org:** [free](https://www.football-data.org/pricing) con Serie A, dati ritardati e 10 chiamate/minuto. Richiede token. Senza credenziali non abbiamo letto le partite; usarlo eventualmente per calendario, risultati e classifica, indicando il ritardo.
- **API-Football:** [free](https://www.api-football.com/pricing/) 100 richieste/giorno e stagioni limitate. Insufficiente per il polling dell'intera Serie A; anche la stagione corrente va verificata prima di un eventuale uso occasionale.
- **openfootball:** [dataset JSON](https://github.com/openfootball/football.json) utile per fixture offline di sviluppo o storico; copertura e aggiornamento della stagione vanno controllati. Non semina automaticamente la cache corrente della dashboard.
- **soccerdata/FBref:** [documentazione caching](https://soccerdata.readthedocs.io/en/stable/intro.html). Raccolta di scraper per analisi, con dipendenze e limiti delle fonti. Non necessario per il risultato che vedremo sul pannello.

## 5. F1: REST e protocollo live

**Jolpica:** base `https://api.jolpi.ca/ergast/f1/`. Verificati da entrambi gli ambienti calendario corrente (23 gare), ultima gara, ultime qualifiche, classifiche piloti/costruttori e risultato 1950/1. Un campione del 1950 conferma l'accesso a quella stagione, non ogni campo di ogni anno. [Limiti attuali](https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md): 4 richieste/secondo di burst, 500/ora continuative senza autenticazione. Usare identificativo applicativo e cache; nessun polling live su Jolpica.

**SignalR:** i due percorsi e protocolli non sono intercambiabili.

| Controllo | PC | Orange Pi | Interpretazione |
| --- | --- | --- | --- |
| `/signalr/negotiate` con parametri legacy | 401 | 401 | Non utilizzabile oggi così com'è, senza credenziali. |
| POST `/signalrcore/negotiate?negotiateVersion=1` | 200 | 200 | Trasporti negoziabili; non dimostra disponibilità dei topic. |
| WebSocket `wss://livetiming.formula1.com/signalrcore`, handshake JSON e `Subscribe` | Riuscito, snapshot di otto topic senza login | Non eseguito | Dati dello snapshot accessibili; il live attivo resta da misurare. |

Lo snapshot ha popolato `Heartbeat`, `SessionInfo`, `SessionStatus`, `TrackStatus`, `DriverList`, `TimingData`, `LapCount`, `RaceControlMessages`. Sessione: gara Azerbaijan del 26 settembre 2026, già conclusa. Ricevere un heartbeat o un JSON oggi non rende live una sessione passata.

Il [sorgente LiveF1 esaminato](https://github.com/GoktugOcal/LiveF1/blob/main/livef1/utils/constants.py) usa ancora `/signalr/`. La raccomandazione precedente «installare LiveF1 per il live» viene quindi corretta: scegliere una versione/client con supporto Core verificato oppure un adapter Python Core minimo. [FastF1](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/livetiming/client.py) già usa Core; il suo client registra messaggi e ammette che l'accesso senza auth possa essere parziale. Non installare tutta la pipeline analitica solo per avere otto topic.

**Comportamento del futuro adapter:** protocollo SignalR Core verificato via WebSocket: handshake JSON terminato dal carattere record separator `\x1e` (ASCII 30) `{"protocol":"json","version":1}\x1e`, sottoscrizione con invocazione `Subscribe` (`type: 1`) e ricezione messaggi `Invocation` (`type: 3`). Lo snapshot iniziale consegna lo stato intero; i messaggi successivi trasmettono **delta parziali** (es. `Lines["1"].BestLapTime` in `TimingData`), imponendo un'aggiornamento incrementale a fusione di dizionario (deep merge) e non la sostituzione distruttiva dell'intero topic. Separare stato sessione e stato pista, resettare lo stato su cambio sessione, risottoscrivere e acquisire un nuovo snapshot dopo disconnessione. Convertire orari usando il fuso/offset fornito dalla fonte; non trattare orari locali senza offset come UTC. Non abbiamo provato `CarData.z`, `Position.z`, radio o qualsiasi abbonamento; nessuna promessa di telemetria gratuita completa.

**ESPN F1:** scoreboard 200, evento futuro con stato scheduled e cache max-age 20 secondi. Candidato per un riepilogo generale; non validato come indicatore di ogni sessione FP/qualifica/sprint o alternativa ai tempi. Il calendario REST e `SessionInfo` restano i riferimenti del futuro adapter.

**FastF1 storico:** utile sul PC per telemetria e analisi dopo sessione. Non è stata misurata la sua CPU/RAM sulla board: niente affermazione «troppo pesante» come risultato di un benchmark inesistente. F1 live e storico sono €0 nella combinazione proposta se i topic necessari rimangono accessibili nella prova attiva.

## 6. MotoGP: dati verificati e codici da confermare

Base corretta: `https://api.motogp.pulselive.com/motogp/v1/`. È il backend del sito, con documentazione community [MotoGP-API](https://github.com/robschmitt/MotoGP-API); l'accessibilità non lo trasforma in un contratto API ufficiale per sviluppatori.

| Percorso | Riscontro PC e board |
| --- | --- |
| `results/seasons` | 78 stagioni, anni 1949–2026. |
| `results/events?seasonUuid={uuid}` | 29 eventi nella lista 2026; 6 nella lista 1949. La lista può comprendere test, quindi non sono 29 GP garantiti. |
| `results/categories?seasonUuid={uuid}` | Categorie e UUID. Senza parametro, una verifica preliminare ha dato 400. |
| `results/standings?seasonUuid={uuid}&categoryUuid={uuid}` | Classifica corrente MotoGP con 30 righe. |
| `timing-gateway/livetiming-lite` | `head` e `rider`, 26 piloti Moto3; sessione N non iniziata del 2 ottobre. |

`results/events` non è stato verificato come calendario dettagliato di tutte le future sessioni. Per orari FP, qualifica, sprint e gara servono anche percorsi sessioni/broadcast e collegamento corretto degli UUID. L'esistenza di una stagione dal 1949 non garantisce copertura uniforme di tutti i risultati e categorie.

Nel timing `remaining` è una stringa numerica ("2100" nel campione), `num_laps` è 0, `pos` è -1, tempi/gap sono stringhe "0.000". Il [campione community](https://github.com/robschmitt/MotoGP-API#live-timing) mostra tempi con formato come `1'47.617`. Conservare raw e normalizzare dopo aver verificato formato/unità; i tempi zero di una sessione non iniziata restano assenti. Non equiparare gap testuali a millisecondi interi né `trac_status=B` a bandiera verde. Posizione negativa non è un piazzamento valido.

**Condizione live futura:** categoria richiesta + identità sessione coerente + stato raw mappato con evidenza ad attiva + finestra temporale valida + dato verificato fresco. N/F o stato sconosciuto non avviano la vista Live. `A/R` non sono confermati da questa osservazione. Una categoria diversa non significa automaticamente «MotoGP indisponibile»: è il feed di un'altra classe, da tenere distinto.

## 7. Costo e richiesta di rete

| Fonte scelta | Spesa prevista | Limiti operativi |
| --- | --- | --- |
| FotMob + ESPN | €0 per gli endpoint letti senza chiave | Nessuna quota pubblicata individuata: rispettare cache, errori e backoff. |
| Jolpica | €0 | Limiti documentati, cache. |
| F1 SignalR Core | €0 per handshake/snapshot base osservato | Accesso durante sessione attiva da verificare. |
| PulseLive | €0 per gli endpoint osservati | Nessuna quota pubblicata individuata; live attivo non misurato. |
| BSD opzionale | Piano REST calcio gratuito dichiarato | Token e budget giornaliero; socket a pagamento escluso dalla scelta. |

A 30 secondi: 240 richieste in 2 ore **per un endpoint**; 720 in 6 ore. Scoreboard più tre dettagli ogni 30 secondi per due ore = 960 richieste, prima di retry e fonte di confronto. Il budget si calcola sommando ogni endpoint, non contando solo il numero di sport. Durante la prova comparativa i due provider generano traffico separato. Nel prodotto seguire score aggregati e scaricare dettagli solo per l'incontro selezionato o per confermare un evento.

## 8. Controlli riproducibili e passi rimanenti

Dal repository, i checker raccolgono risultati, inclusi errori attesi; exit 0 significa report scritto, non «tutte le fonti affidabili».

```bash
python3 dashboard/design/tools/check_sport_providers.py --label pc --output /tmp/v06-provider-check-pc.json
ssh -o BatchMode=yes -o ConnectTimeout=8 smartpc@192.168.1.179 'python3 - --label orange-pi' < dashboard/design/tools/check_sport_providers.py > /tmp/v06-provider-check-orange-pi.json
node dashboard/design/tools/check_f1_signalrcore.mjs /tmp/v06-signalrcore.json
```

Resta una prova durante una partita Serie A per confrontare ritardo, VAR e stato finale; poi una sessione F1 e una MotoGP per le rispettive estensioni. Il riferimento TV può essere ritardato: registrare piattaforma e orario osservato; non chiamare la differenza «latenza assoluta dal campo». Questi sono criteri di collaudo futuri, non test dichiarati completati.

La scelta di prodotto, i contratti dati, cache, navigazione e criteri di rilascio sono nel [piano v0.6](./v06-sport-plan.md).

## 9. Riscontri dell'implementazione

L'integrazione Serie A è ora descritta nel [resoconto del rilascio](./v06-sport-release.md). Il fallback con risposte ESPN reali ha fornito 20 incontri vicini e 20 squadre, con calendario esplicitamente parziale. La stagione FotMob 2025/26 ha restituito 380 fixture; ESPN standings con parametro `season=2025` ha restituito la stagione precedente.

Un UA applicativo diverso (`SmartPC-Dashboard/0.6`) è stato rifiutato da ESPN con 403, mentre urllib standard ha risposto 200. Non contraddice il campione precedente con un altro UA e non dimostra la causa: il client usa UA standard per ESPN, applicativo per FotMob, cooldown/backoff per entrambi. I controlli live durante una partita rimangono aperti.

## 10. Riscontri motorsport · 1 ottobre 2026

L'estensione è implementata e verificata sulla Orange Pi: [resoconto completo](v06-motorsport-release.md), [REST corrente/precedente](evidence/v06-motorsport/online.json), [referti aggiuntivi](evidence/v06-motorsport/additional-results.json), [Qt SignalR](evidence/v06-motorsport/signalr.json), [offline](evidence/v06-motorsport/offline.json), [EGLFS](evidence/v06-motorsport/render.json).

- Jolpica: 23 GP / 23 piloti / 11 Costruttori nel 2026; 24 / 21 / 10 nel 2025. Gara, Qualifiche e Sprint lette per ultimi GP e un GP precedente selezionato. Copertura della UI limitata alle ultime due stagioni; libere/Sprint Qualifying sono ora integrate tramite OpenF1, fuori dalla finestra live.
- F1 SignalR Core: client Qt leggero senza FastF1 installato, otto topic dal PC e dalla board. Snapshot Azerbaijan Race, 22 righe, stato `Ends`; nessun falso Live. Accesso e ritardo durante sessione attiva restano da provare.
- MotoGP: collegamento risultati `event.id` ↔ `toad_api_uuid` broadcast ↔ session UUID. `events/{broadcastUuid}` fornisce date/orari di sessione; filtro categoria MotoGP e tipo SESSION. Giappone: FP1, PR, FP2, Q1, Q2, SPR, WUP, RAC; nessuna conferenza/altre categorie. Date con offset originale convertite a Europe/Rome.
- `results/sessions?eventUuid=…&categoryUuid=…` e `results/session/{sessionUuid}/classification?seasonYear=…&test=false` provati per entrambe le stagioni. Gara/Sprint con tutti i partecipanti e Q2 con 12; FP1 aggiuntiva con 22/24 righe. Risultati consultabili e caricati su selezione, anche libere/Warm Up se pubblicati.
- Gateway ancora Moto3/N nel campione: escluso dal live MotoGP. Stati codificati sconosciuti non sono promossi ad attivi; serve un'indicazione esplicita di attività, oltre a categoria, GP, sessione, data e freschezza.

Nessun costo/API key per gli endpoint letti. La consultazione e il trasporto sono implementati; una prova attiva resta necessaria per badge Live, mapping gateway, ritardo e prestazioni durante il flusso.

## 11. Dati aggiuntivi motorsport · 1 ottobre 2026

[Resoconto e prove](v06-racing-details-release.md). Nessun pilota preferito, su indicazione dell'utente.

- **Jolpica:** griglia, variazione griglia-arrivo, giro veloce e tempi Q1/Q2/Q3 già presenti nei referti. Endpoint filtrati per pilota `pitstops` e `laps` verificati: Verstappen ad Abu Dhabi 2025, una sosta in pit lane e 58 giri. Il tempo della sosta riguarda la pit lane, non il solo cambio gomme.
- **OpenF1 gratuito:** Libere 1 con 20 piloti, Qualifiche Sprint con 20; stint e mescole della stessa sessione, identificati per session_key/numero. Storico dal 2023 senza account; live a pagamento escluso. Gli spazi dei nomi sessione devono essere `%20`, non `+` nell'endpoint osservato. Validazione di stagione, tipo, paese e timestamp; `UAE/USA/UK` normalizzati tra fonti.
- **MotoGP:** circuito nei broadcast con lunghezza, curve, rettilineo, giri/distanza; condizioni registrate nei risultati/sessioni; costruttore, velocità media e record nei referti. Campi preservati e ora mostrati. Dati e condizioni non vengono trasformati in previsioni meteo.
- **SignalR:** ricevuti sulla board tutti gli 11 topic sottoscritti, compresi TimingAppData, TimingStats e WeatherData; 22 righe, tre righe pista/meteo e otto messaggi di direzione. Stato `Ends`: conferma di accessibilità dello snapshot, senza prova durante una sessione attiva. Un eventuale rifiuto dei topic aggiuntivi torna alla sottoscrizione base.
- **Account:** nessuna registrazione richiesta per gli endpoint utilizzati. La registrazione gratuita non viene proposta come metodo per sbloccare il live OpenF1 a pagamento.
