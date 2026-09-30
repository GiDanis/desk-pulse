# SmartPC · piano v0.6 Sport · Serie A

**Stato:** piano di analisi, 30 settembre 2026. Nessuna integrazione Sport è ancora implementata o verificata sulla Orange Pi.

## Decisione di prodotto

La prima versione Sport segue **la Serie A italiana**. L'utente potrà aggiungere in seguito altre competizioni a sua scelta; l'architettura non deve codificare «Serie A» dentro QML. La v0.6 è conclusa quando calendario e risultati sono affidabili sul display reale. Il live e le notifiche entrano nella stessa versione solo dopo una prova con una partita reale, una quota gratuita sufficiente e una verifica della latenza. Questo segue il [MasterPlan](chatgpt-conversation://01a0ef3d-1468-7d83-b386-fc79c7cc1e31) e la [navigazione prevista](./ux-navigation-v2.md): Sport entra nel carosello soltanto quando mostra dati utili.

Il vincolo economico è **€0 al mese**. Per la v0.6 non dipendiamo da un servizio a pagamento né promettiamo notifiche istantanee. La dicitura «live» sul display significa che la fonte sta aggiornando una partita in corso; l'interfaccia mostra sempre l'ora dell'ultimo dato.

## Verifica delle fonti

| Fonte | Cosa offre alla v0.6 | Limite o rischio | Scelta |
| --- | --- | --- | --- |
| [football-data.org](https://www.football-data.org/pricing) | Serie A compresa nel piano gratuito; calendario, risultati e classifiche con API documentata. [Copertura](https://www.football-data.org/coverage), [codice `SA`](https://docs.football-data.org/general/v4/lookup_tables.html). | I punteggi del piano gratuito sono dichiarati **ritardati**; limite di 10 chiamate/minuto. Non basare su questa fonte un avviso «GOL!» tempestivo. | **Base affidabile** per calendario, risultati e classifica; fallback per i dati non live. |
| [API-Football / API-Sports](https://api-sports.io/sports/football) | Piano gratuito con 100 richieste/giorno, accesso agli endpoint; [documentazione](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide) per calendario, punteggi live ed eventi. `fixtures?live=<lega>` può leggere più partite in una chiamata. | La [disponibilità dei dati nel free tier](https://api-sports.io/terms) può variare; occorrono account e chiave. La quota si azzera a 00:00 UTC sul portale diretto; 100/giorno non sostengono polling continuo di tutte le partite. | **Candidato live**, subordinato alla prova della stagione e della Serie A con un account gratuito. Non considerare verificata la copertura solo perché l'endpoint esiste. |
| ESPN Site/CDN | Nella [precedente analisi](chatgpt-conversation://6abcfb14-1864-83ed-b0ff-87a9cbf83711) gli endpoint interni erano stati proposti come fonte primaria. | Le [condizioni Disney collegate da ESPN](https://support.espn.com/hc/en-us/sections/360007128391-LEGAL) vietano l'estrazione automatica con script senza permesso scritto. Non risulta una API pubblica per sviluppatori con quota e contratto applicabili a questo uso. | **Non scegliere come provider automatico della dashboard.** La reperibilità tecnica di un URL non concede l'uso continuativo. |
| SofaScore e altri endpoint interni | Possibili dati live. | Interfacce non pubbliche, senza contratto di disponibilità o quota; rischio di cambiamento e accesso bloccato. | Fuori dal piano v0.6. |
| [TheSportsDB](https://www.thesportsdb.com/documentation) | Dati generali e immagini nel piano gratuito. | Livescore e API v2 sono Premium. Diritti dei loghi da verificare separatamente. | Facoltativo per metadati; non necessario alla prima release. |

**Correzione rispetto alla chat iniziale:** ESPN non è una fonte primaria consigliabile per un servizio automatico sempre acceso. Anche «API-Football fallback» non risolve da sola il live se la quota giornaliera è esaurita. La v0.6 deve degradare a calendario/risultati ritardati e indicare chiaramente la situazione.

### F1 e MotoGP, dopo la Serie A

- [Orange Cat Blacktop](https://blacktop.live/api), esaminata nella prima analisi, offre 7.500 richieste mensili gratuite per progetti non commerciali e dati di calendario, risultati e classifiche per F1 e MotoGP. Il piano gratuito ha solo gli endpoint principali; il [feed WebSocket](https://blacktop.live/guides/live-motorsport-data-webhooks-and-websockets) e il live race-weekend dichiarato nel listino sono a pagamento. È quindi una buona candidata futura a €0 per il motorsport **non live**, da confrontare con Jolpica e verificare sui campi necessari.
- [Jolpica F1](https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md) è una buona fonte gratuita per calendario, risultati e classifiche; [termini](https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md) per uso non commerciale e [limiti](https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md) richiedono cache e identificazione dell'app. Non fornisce una promessa di live timing.
- [OpenF1](https://openf1.org/) offre gratuitamente dati storici; l'accesso durante la sessione è a pagamento. Il feed F1 SignalR citato nella prima analisi non è una base gratuita garantita: i [termini F1 TV](https://www.formula1.com/en/information/f1-tv-subscription-terms.384sQqjslhQ2Rhm1LdKgfD) e le [linee guida sui timing data](https://www.formula1.com/en/information/guidelines.4EOKE9RRqevL4niTK9kWyt) richiedono cautela. Non pianificare un `F1LiveProvider` basato su quel feed.
- L'endpoint MotoGP PulseLive è documentato da un [progetto della community](https://github.com/robschmitt/MotoGP-API), ma non come API pubblica per sviluppatori. MotoGP vende l'accesso al live timing tramite [TimingPass](https://www.motogp.com/en/purchase-policy). Calendar/results e live MotoGP vanno analizzati separatamente quando saranno richiesti.

## Esperienza sul display

Sport diventa una famiglia del carosello, dopo Account ChatGPT. Manteniamo tre viste verticali al massimo:

1. **Prossime:** prossima partita di Serie A. Data e ora in `Europe/Rome`, squadre grandi, stato della partita. OK apre l'elenco delle successive della giornata; solo nell'elenco 2/8 scorre le righe. Se non c'è un incontro imminente, mostra il prossimo turno reale; se manca anche questo, «Calendario non disponibile» con origine e ultimo aggiornamento.
2. **Live:** visibile solo quando esiste almeno una partita in corso con dati freschi. Risultato grande, minuto/stato, squadre e «aggiornato alle HH:MM». Con più partite, OK apre un elenco in cui 2/8 sceglie l'incontro; i dettagli appaiono solo quando la fonte li possiede. Se il live è vecchio, mostra «Aggiornamento interrotto» e il punteggio come ultimo dato conosciuto, senza continuare a chiamarlo live.
3. **Risultati:** ultimi risultati del turno e, solo se la qualità è verificata, classifica compatta. Le correzioni della fonte aggiornano il risultato senza ripetere avvisi.

La Home continua a dare precedenza a ora e meteo. Un match della Serie A **non** diventa automaticamente la tessera `nextRelevantEvent`: con tutte le squadre attive produrrebbe un evento quasi permanente. La futura selezione di squadre preferite o un'esplicita preferenza «Sport nella Home» potrà abilitarla. L'assenza di sport non lascia uno spazio vuoto.

## Contratto dati e integrazione

Schema normalizzato proposto, indipendente dagli ID delle fonti:

```text
SportMatch {
  sport, competitionId, season, provider, providerMatchId,
  homeTeam, awayTeam, kickoffUtc, status,
  homeScore?, awayScore?, matchMinute?,
  sourceDataAt?, fetchedAt, checkedAt,
  provisional, stale
}
```

`status` distingue `scheduled`, `live`, `half_time`, `finished`, `postponed`, `cancelled` e `unknown`; un punteggio mancante resta `null`, mai `0`. Gli ID dei provider restano nello strato adapter. Per confrontare la stessa partita su due fonti usiamo competizione, stagione, data e squadre con una mappa verificata: nessuna fusione automatica basata solo sul nome. Le ore si salvano in UTC e si formattano in `Europe/Rome` per la UI.

Il provider Python recupera e convalida uno snapshot fuori dal thread QML, poi pubblica `moduleState` con `source`, `updatedAt`, `status`, dati e errore secondo [module_state.py](../module_state.py). Nel dato Sport conserviamo anche `sourceDataAt` quando disponibile e `fetchedAt`: l'ora della risposta non equivale necessariamente all'ora del fatto sportivo. Cache locale atomica per l'ultimo calendario e i risultati validi; SQLite solo se serve persistenza delle identità e delle transizioni live. Un errore, una risposta vuota inattesa o un payload incompleto non cancellano la cache valida.

Il [motore eventi](../events.py) riceve snapshot Sport con ID stabile e prefisso `sport:`. Si pubblica uno snapshot vuoto **solo** dopo una risposta valida che conferma la fine/assenza degli eventi; un errore di rete conserva lo stato precedente fino alla scadenza. Gli avvisi «inizio partita», «gol» e «risultato finale» richiedono preferenze esplicite, deduplicazione e un'età massima del dato. Nessun gol viene inferito da un semplice cambio di punteggio se l'evento non è confermato; una correzione del punteggio non deve inventare un secondo gol. Le notifiche Sport si integrano nella fascia di silenzio e nel controllo di interruzioni per categoria già esistenti.

## Strategia di richieste, da misurare

**Base football-data.org:** calendario e classifica 1–2 volte al giorno; risultati del turno più spesso nelle ore successive alle partite, sempre con cache. I valori sono una proposta operativa, non un limite imposto dal provider. Il token resta fuori dal repository e da QML.

**Live API-Football:** chiamate solo nei giorni e negli intervalli in cui la Serie A ha partite programmate. Una chiamata aggregata per le partite live della lega ogni **3 minuti** equivale a circa 45 chiamate per una finestra di 135 minuti. Riservare almeno 25 richieste per scoperta, conferma di eventi e recupero; interrompere il live quando la quota residua scende sotto la riserva. Nessun polling live nelle ore senza incontri. La frequenza reale si decide dopo avere misurato disponibilità, latenza e consumo sulla partita di prova; rispettare 429 e `Retry-After` senza aggirare i limiti. [Guida API-Football all'uso della quota](https://www.api-football.com/news/post/how-to-optimize-api-sports-calls-and-quota-usage).

Le notifiche gol avranno una latenza **misurata**, non promessa. La fonte può aggiornarsi in ritardo e il polling aggiunge fino a 3 minuti; per questo la UI usa «Gol rilevato» con ora di acquisizione e indica la fonte. Se la latenza osservata è eccessiva o gli eventi non sono completi, la release mantiene risultati e calendario senza notifiche gol.

## Sequenza di sviluppo e criteri di uscita

| Fase | Lavoro | Evidenza richiesta |
| --- | --- | --- |
| **0 · Prova fonti** | Creare gli account gratuiti necessari, verificare `SA` e la stagione corrente, recuperare un giorno di calendario e un risultato; durante un incontro misurare API-Football su punteggi, eventi, quota e ritardo rispetto alla pagina ufficiale. | Campioni JSON sanitizzati, risposte HTTP, orari, quota consumata e mappa dei campi. La prova live è da fare durante una partita reale. |
| **1 · Dati e cache** | Adapter `FootballDataProvider`, modello normalizzato, cache e stato offline; aggiungere API-Football solo se la fase 0 lo conferma. | Calendario e risultati corretti, cache valida al reboot offline, nessun dato vecchio presentato come nuovo, UI mai bloccata dalla rete. |
| **2 · Viste Sport** | Schermate Prossime/Risultati e Live condizionale, navigazione e visibilità in Impostazioni. | Prova sul pannello 960×640: testo leggibile, 3 righe massimo per elenco, focus e ritorno corretti, nessuna pagina vuota, nessuna regressione a Meteo/Account/Avvisi. |
| **3 · Eventi** | Solo dopo la prova live: notifiche Sport configurabili, controllo quota e deduplicazione. | Una partita reale osservata dall'inizio alla fine; nessun avviso duplicato al refresh/reboot, correzioni gestite, partita conclusa non resta live; overlay/banner non rubano il focus. |
| **4 · Rilascio board** | Backup, installazione, test online/offline e ritorno online, misura del rendering nelle viste Sport e procedura di rollback. | `smartpc-dashboard.service` attivo dopo riavvio, nessun crash, dati/freschezza leggibili e misure annotate sulla Orange Pi. |

La v0.6 può essere rilasciata con fasi 0–2 e 4 se la fonte live gratuita non supera la prova. In quel caso la vista Live resta fuori dal percorso e il README dichiara esplicitamente che risultati e calendario sono la funzione consegnata. La fase 3 passa a un'estensione successiva, con il suo criterio di uscita; non viene dichiarata pronta nella v0.6.

## Decisioni già fissate e punti da verificare

- Fissato: Serie A come prima competizione, costo ricorrente zero, possibilità di aggiungerne altre.
- Da verificare con credenziali gratuite: accesso alla stagione corrente, campi di punteggio/evento, quota e latenza API-Football; disponibilità effettiva di football-data.org sulla board.
- Da scegliere prima delle notifiche: squadre preferite oppure tutte le partite, categorie di avviso abilitate per default, soglia di freschezza che disattiva la dicitura live. In assenza di preferenze, nessuna interruzione sportiva automatica.
- Non eseguito in questa analisi: modifiche al codice, chiamate autenticate ai provider, osservazione di una partita live e prova sulla board.
