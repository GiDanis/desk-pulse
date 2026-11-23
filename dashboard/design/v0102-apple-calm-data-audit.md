# Apple Calm v0.10.2 · correttezza dei dati

29 ottobre 2026 · analisi del checkout `0.10.2-rc.4`, bundle sorgente `1.6.5`.

Il controllo ha trovato **tre famiglie di difetti riproducibili**: stato delle partite all’intervallo, tempi/distacchi Motorsport che non arrivano al tema e reset Account sconosciuto rappresentato come data. Si aggiungono una scelta da uniformare sui punteggi parziali e un caso di irrobustimento del confine numerico. Le correzioni sono pianificate, **non applicate**.

Questo documento controlla acquisizione e persistenza nei sorgenti, proiezione nel contratto pubblico e formattazione Apple Calm. Non è una riconciliazione dei database reali della board con tutti i provider. Dati e preferenze dell’utente non sono stati modificati. Il [piano completo](v0102-apple-calm-implementation-plan.md) stabilisce l’attuazione e i gate ancora necessari.

## 1. Metodo ed evidenze

- Lettura mirata dei normalizzatori, dei punti di salvataggio, dei DTO e dei binding QML; nessuna chiamata autenticata ai provider.
- **Otto casi esistenti del runner passati**: `check_dashboard_summary`, `check_theme_api_contract`, `check_theme_api_runtime`, `check_theme_api_adapters`, `check_network_metrics`, `check_events`, `check_motorsport`, `check_casa`. Ricevute [targeted/checks.json](evidence/v0102-apple-calm-readability-2026-10-29/data-audit/targeted/checks.json) e [main-adapter/checks.json](evidence/v0102-apple-calm-readability-2026-10-29/data-audit/main-adapter/checks.json).
- **14 sonde aggiuntive**, usando i normalizzatori Python reali e importando il vero `Format.js` in QQmlEngine: sette aspettative soddisfatte e sette scostamenti registrati. Cinque scostamenti appartengono alle tre famiglie di difetti, uno alla presentazione del punteggio e uno alla validazione numerica. [Sonde e risultati](evidence/v0102-apple-calm-readability-2026-10-29/data-audit/probes.json), [script](evidence/v0102-apple-calm-readability-2026-10-29/data-audit/probe-data.py).
- Banco PC: Python **3.14.4**, Qt **6.11.2**. Non coincide con il target Qt 6.8.2 documentato per Orange Pi: queste sono prove diagnostiche locali, non qualificazione ARM/EGLFS.

I controlli esistenti positivi non smentiscono i difetti: mancavano aspettative sul valore effettivamente mostrato dal formatter Apple Calm in questi casi. Durante l’attuazione le sonde pertinenti diventano regressioni del progetto, con aspettative indipendenti dall’implementazione.

## 2. Difetti e decisioni

| ID | Evidenza attuale | Risultato richiesto | Intervento previsto |
| --- | --- | --- | --- |
| D01 · Intervallo | `sport_core.LIVE_STATES` comprende `half_time`, ma l’enum pubblico `MatchData.status` lo esclude: il normalizzatore lo converte in `unavailable`. Inoltre `Format.matches` filtra solo `live` e `matchStatus` non contiene «Intervallo». Nella sonda rimane solo la partita live e il dettaglio mostra «Stato non disponibile». | La partita resta in «In corso», mostra «Intervallo» e conserva il punteggio. Lo stato non basta da solo a dichiarare dati live verificati. | Aggiungere lo stato al contratto e ai generati; allineare formatter, filtri, fixture e temi interessati. Provare live → intervallo → ripresa → fine, anche con dati precedenti. |
| D02 · Motorsport | Risultati F1 e MotoGP normalizzati contengono `value` (`1:42.526`, `01:27.917` nei campioni). `RacingTiming` non lo mappa e il tema legge `time`/`gap`: appare `— · —`. Anche i produttori timing live pubblicano `value` e `laps`, con dettagli distinti per leader/precedente/giro. | Tempo, distacco, intervallo, giro e stato arrivano in campi con significato esplicito. La posizione non viene abbinata al tempo di un’altra sessione. | Proiezione semantica nei produttori/adattatori, conservando compatibilità con cache precedenti. Nessun alias universale `value → time`: in gara quel testo può essere distacco o stato; in qualifica è un tempo. |
| D03 · Reset Account | Il produttore usa `resetsAt=0` per reset sconosciuto; il DTO lo conserva. `AccountPage.qml:32` controlla solo `null`. La sonda produce `Reset 01/01 · 01:00`. | «Reset non disponibile». Nessun timestamp zero o non valido viene presentato come data reale. | Normalizzare il sentinel a `null` nel confine pubblico e mantenere un controllo difensivo nel formatter/vista. Non convertire gli altri zeri validi in assenza. |
| D04 · Punteggio parziale | Il riepilogo conserva il lato noto, ma `Format.matches` nasconde l’intero punteggio se manca un lato. La sonda con 0 e assente produce stringa vuota. | Nelle viste che mostrano il risultato: `0 – —`, con disponibilità esplicita e senza inventare il lato mancante. Per una partita futura nessun punteggio diventa implicitamente 0–0. | Uniformare la convenzione tra riepilogo, lista e dettaglio; distinguere previsto, parziale e finale secondo fonte. È una decisione di presentazione, non prova di punteggi reali errati. |
| D05 · Confine numerico | `numeric(False)` è indisponibile ma porta `displayText="False"`; `Format.number` preferisce quel testo e lo mostra. | Nessun booleano, NaN o infinito diventa una misura. Restano validi 0 e i testi temporali ammessi esplicitamente dal contratto. | Validare nel produttore di `NumericValue`. Non cancellare indiscriminatamente `displayText` quando `available=false`: tempi formattati legittimi usano già il canale solo testuale. Provare entrambe le categorie. |

Riferimenti: [normalizzatore](../theme_api.py:130), [alias](../theme_api.py:105), [contratto](../theme-api/contexts.json), [formatter](../../theme-projects/apple-calm/bundle/qml/Format.js:44), [Account](../../theme-projects/apple-calm/bundle/qml/AccountPage.qml:27), [risultati F1/MotoGP](../motorsport_core.py:184), [timing](../racing_timing.py:125).

## 3. Dati nei posti giusti: matrice fonte → contratto → vista

| Dominio | Dati autorevoli e destinazione | Regola di esposizione | Stato del controllo |
| --- | --- | --- | --- |
| Home / riepiloghi | `dashboard_summary.py` → `DashboardSummary` → Home e `TopicDashboard`. | Il riepilogo conserva identità, priorità, provenienza e disponibilità del dominio; non costruisce un risultato dal titolo di una notifica. | Suite passata; selezione della fonte e zeri letti nei sorgenti. Gate QML per valori lunghi e cache precedenti ancora da fare. |
| Meteo attuale | `weather.py.numeric` → `WeatherData`: °C, %, mm, km/h e direzione in gradi; `weather_time` → `observationAt`. | Temperatura e percepita distinte; precipitazione mm distinta dalla probabilità %. «Stima del modello» non implica sensore locale. Timestamp della stima distinto da ultimo download/tentativo. | Sonda sul vero normalizzatore conserva 0 °C. Unità e richiesta provider verificate nei sorgenti. |
| Previsioni | `forecast[].date`, `highValue`, `lowValue`, `rainProbabilityValue`, `code` → tre `WeatherForecast`. | Data identifica il giorno; massima/minima e probabilità massima giornaliera. Non dedurre «Oggi» dal solo indice se la cache è vecchia. | Tre date conservate nella sonda. **Il contratto non offre quattro previsioni orarie di temperatura/condizione**: la tavola è stata corretta a tre giorni. |
| Calcio | `canonicalMatchId`, squadre casa/trasferta, stato, minuto, punteggi e incidenti → `MatchData`. | Mai scambiare casa/trasferta o sommare recupero al minuto senza contratto. `half_time` non è indisponibilità. Un aumento del punteggio non certifica un gol. | D01 e D04 aperti; suite riepilogo passata. Qualifica eventi reali gol/VAR ancora aperta. |
| F1 / MotoGP | Disciplina + stagione + evento + sessione + pilota; risultati separati da timing live. | Gara: tempo del vincitore/distacco degli altri; qualifica: tempo migliore; timing: ultimo/miglior giro, gap leader e intervallo distinti. Stato ai box/ritirato non è un tempo. | D02 riprodotto sui risultati di entrambe le discipline; produttori live letti staticamente. Necessarie fixture semantiche live dedicate. |
| Rete | `network_metrics.py`: byte/s × 8 → bit/s; bitrate fisico router in decimi di Mbit/s; storico con tempo e discontinuità. | Download/upload secondo la prospettiva documentata, esplicitata in vista; traffico corrente distinto da capacità. Zero traffico è valido; sconosciuto è `—`. | Suite metriche passata; conversioni lette. Il provider Freebox documenta `signal` in **dB**: non cambiarlo in dBm per analogia con altri sistemi. |
| Dispositivi LAN | Inventario/router/board → disponibilità, copertura e raccolta proprie. | «Online secondo router» non significa presenza fisica certa. Preferiti/alias appartengono all’ID, non all’ordine delle righe. | Lettura di `network_core.py`; prova fisica di ingresso/uscita non svolta. |
| Grafici | Serie temporali tipizzate, null e `breakBefore` → `NetworkHistoryChart`. | Non collegare buchi; assi/unità coerenti; non scambiare ultimo campione valido con dato corrente. Il grafico si svuota se i dati spariscono. | Gestione null/discontinuità e ridisegno su cambiamenti già presenti nei sorgenti; futura regressione presente → assente → presente. |
| Casa | `casa_core.display_devices` → `CasaDevice`/`CasaMetric`: valore, unità, `checkedAt`, `stale`, `previous`, disponibilità. | Una fonte attiva non rende attuale ogni misura: contano dispositivo e singolo stato. Zero, falso e offline restano distinti; leggere «Spento» non significa comando eseguito. | Suite Casa passata, semantica per misura letta. Nessuna sessione Tuya reale o comando eseguito. |
| Account | App Server → snapshot → `AccountData.windows`, crediti e reset separati. | `usedPercent` è utilizzato. Se si sceglie il residuo: `100-used`, solo su numero valido 0–100, e stessa grandezza nella barra. Una finestra mancante non è quota zero. | Alias durata 300 minuti e utilizzato 34 verificati; residuo proposto 66. D03 aperto. Snapshot non equivale a sessione corrente verificata. |
| Notifiche | `EventEngine` → `NotificationEvent` → banner/elenco/dettaglio. | Fonte, ID e revisione stabili; emissione, ricezione, validità, presentazione e lettura distinti. Rettifica/revoca prevalgono sul testo precedente. | Suite eventi passata; mancanti nel DTO alcuni stati di ciclo vita e contatore globale in `UiStatus`. Serve estensione pubblica per la proposta completa. |
| Menu / impostazioni | Registro destinazioni e `SettingRow` → selezione per ID, azione pubblica, risultato asincrono. | Un tasto premuto non è successo confermato. Il valore visualizzato segue il commit dell’operazione; spiegare indisponibilità. | Lettura dei binding condivisi, suite adattatori passata. Nessuna impostazione cambiata. |
| Gioco / Acquario | Scene e modelli attuali, identificativi gara/sessione e storico propri. | Il lavoro grafico riguarda cornice, leggibilità e convivenza con avvisi. Non sostituire tempi correnti con record storici, non azzerare piloti/pesci, non qualificare una policy con una prova grafica. | Fuori dalle sonde di contenuto di questo audit; copertura futura di overlay/carico. Rendering e logica ambientale conservati. |

Fonte esterna verificata per le unità Rete: [Freebox OS SDK · Wi-Fi](https://dev.freebox.fr/sdk/os/wifi/). Le unità di altri provider restano quelle del rispettivo contratto.

## 4. Scrittura, cache e conservazione

La verifica della scrittura è **statica sui percorsi applicativi**, più le regressioni locali indicate; non è un’ispezione dei contenuti privati installati.

| Archivio | Evidenza nei sorgenti | Vincolo per l’attuazione |
| --- | --- | --- |
| Eventi SQLite | `EventEngine.replace_source` valida tutto lo snapshot, rifiuta fonti miste/ID duplicati o appartenenti ad altra fonte e applica aggiornamenti/revoche in transazione. Stato letto e consegna sono distinti. | Il tema non scrive direttamente nel DB. Non azzerare lo storico e non usare il testo del titolo come chiave. Mantenere le verifiche transazionali. |
| Meteo | `save_weather_cache` salva snapshot completo e `fetched_at` in file temporaneo, sincronizza e sostituisce atomicamente; caricamento valida la cache. | Non salvare una stringa renderizzata al posto del valore o sovrascrivere un dato buono con una risposta parziale. Persistenza nel worker, QML solo lettura. |
| Motorsport | Cache per disciplina/anno, validazione e salvataggio dei dati normalizzati; proiezione pubblica separata. | Nuovi campi canonici additivi; vecchie cache leggibili. Nessuna riclassificazione arbitraria di `value` come tempo numerico. |
| Casa / Rete | Snapshot e preferiti/alias legati al dominio/identità; salvataggi controllati dal servizio. Casa conserva età per misura. | Mantenere scope, ID e preferenze. Il riordino grafico non cambia la sorgente né il dispositivo associato. |
| Account | `account_sync.publish` trasferisce in file temporaneo e sostituisce `/var/cache/smartpc-dashboard/account-chatgpt.json`; il lettore valida dimensione, campi e anzianità. | Correggere il sentinel reset nel confine pubblico senza perdere snapshot o crediti; nessuna scrittura di credenziali nel concept. |

Riferimenti: [EventEngine](../event_core.py:126), [cache Meteo](../weather.py:266), [Account sync](../account_sync.py:229), [lettore Account](../account.py:21), [Casa](../casa_core.py:616), [Rete](../network_core.py:294).

## 5. Convenzioni da congelare prima del codice

1. **Assenza e zero:** `null`/indisponibile → `—` e contesto utile; 0 resta 0, falso resta uno stato booleano. Nessun `value || 0` o parsing di numeri dal testo tradotto.
2. **Identità:** prima ID dominio/evento/sessione/dispositivo; indice solo per righe prive di identità e all’interno del relativo proprietario. Selezione e dettagli non passano al vicino dopo un riordino.
3. **Tempo:** epoch in secondi nel contratto, Europa/Roma per l’esposizione italiana. Dati di evento, osservazione, raccolta e tentativo non si scambiano. Il formatter JS usa oggi il fuso host: verificare host/fuso e cambio ora nel gate, senza dichiararlo un difetto dimostrato sulla board.
4. **Freschezza:** fonte aggiornata ≠ ogni dato aggiornato. Conservare provenienza, stato cache e timestamp specifico; vietato trasformare `Salvato` in `Live` per un’animazione o per il solo orario previsto.
5. **Unità e testo:** un’unità per valore; direzione vento da campo numerico/testuale canonico, non estraendola da `12 km/h · NE`. Probabilità oraria e massima giornaliera etichettate secondo l’intervallo. Carte Account coerenti con la grandezza della barra.
6. **Conferme:** mostrare successo solo dopo esito dell’azione; presentazione banner non legge l’evento. Nessuna falsa conferma di gol, stato dispositivo o disponibilità Account.

## 6. Esito e limiti

Il check basta per definire un delta concreto e i test mancanti; **non permette di dichiarare corretti tutti i dati reali dell’intero sistema**. Le tre famiglie di difetti, D04 e D05 entrano nel primo incremento del piano. Le tavole sono esempi sintetici, non dati acquisiti o schermate correnti della board.

Restano da eseguire durante l’attuazione: oracoli fonte → DTO → testo visibile, cache vecchie e transizioni di assenza/ritorno, preflight reale del nuovo bundle, PC/ARM/EGLFS 960×640 con Qt target, provider live pertinenti e lettura/tastierino fisici. Il fallimento del precedente tentativo di cattura QML per preflight non soddisfatto rimane registrato in [source-audit.json](evidence/v0102-apple-calm-readability-2026-10-29/source-audit.json); non è stato aggirato.
