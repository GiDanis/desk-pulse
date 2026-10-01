# SmartPC · piano v0.6 Sport · Serie A, F1 e MotoGP

**Revisione:** 1 ottobre 2026. Piano per prova privata a **€0/mese**, incrociato con la [ricerca verificata](./v06-sport-api-research.md). L’integrazione Serie A è installata sulla Orange Pi; collaudo live ancora da completare. Dopo il rilascio è stato corretto il dettaglio delle partite future e migliorata la consultazione: [revisione UX](./v06-sport-ux-fix.md).

## 1. Decisioni di prodotto e perimetro

1. **Prima release: Serie A.** Calendario, risultati, classifica e dettaglio essenziale; vista Live e notifiche dipendono dalle prove durante una partita. Aggiungere altre competizioni tramite configurazione e adapter, mantenendo una competizione iniziale.
2. **F1 e MotoGP implementati su richiesta successiva.** Due famiglie adiacenti a Serie A, con programma, risultati e classifiche delle ultime due stagioni. Timing Core/lite predisposto; badge Live condizionato al collaudo attivo. [Resoconto motorsport](v06-motorsport-release.md).
3. **Costo:** endpoint senza chiave per la combinazione iniziale, nessun abbonamento o carta. Le riserve con token gratuito sono facoltative e ancora da collaudare con credenziali.
4. **Provenienza visibile:** fonte e ora di verifica consultabili; dato vecchio/offline/assente riconoscibile. «Live» richiede evento attivo e acquisizione valida recente, non soltanto un HTTP 200.
5. **Navigazione:** Sport entra dopo Account ChatGPT nel carosello quando provider e schermate sono pronti; segue la [mappa UX v2](./ux-navigation-v2.md) e Impostazioni → Moduli visibili. Nessuna pagina vuota per una famiglia ancora da implementare.
6. **Home dinamica:** l'eventuale prossimo incontro viene pubblicato come `nextRelevantEvent` solo dopo una preferenza esplicita, con finestra di rilevanza e scadenza. Senza un evento rilevante la Home conserva ora e meteo. Nessuna squadra preferita è stata ancora scelta.

## 2. Combinazione delle fonti e prove effettive

| Ambito | Scelta proposta | Confermato oggi | Condizione prima del live |
| --- | --- | --- | --- |
| **Serie A** | FotMob REST `/api/data/` principale; ESPN confronto e possibile riserva | PC e board: calendario, 20 squadre in classifica, stesso risultato e dettagli Inter–Monza 4–1 | Confrontare punteggio, eventi, VAR e stato durante una partita; scegliere il provider per tempestività e continuità |
| **F1 statico** | Jolpica | Calendario, ultima gara/qualifica, classifiche e un risultato del 1950 da PC e board | Gestire limite, paginazione e cache; la copertura di ogni anno/campo resta da verificare |
| **F1 timing** | Client **SignalR Core** aggiornato | Negotiate 200 da entrambi; WebSocket senza login dal PC con snapshot di otto topic di una gara conclusa | Prova durante sessione attiva e streaming sulla board; disponibilità di ogni topic da registrare |
| **MotoGP statico** | PulseLive REST | Stagioni 1949–2026, eventi, categorie e classifica corrente da PC e board | Collegare correttamente UUID; verificare risultati di sessione e programma futuro |
| **MotoGP timing** | PulseLive `livetiming-lite` | Payload leggibile; campione Moto3 FP1 non iniziata | Osservare MotoGP attiva, confermare stati e unità; filtrare categoria e sessione |

**Percorsi calcio da adottare:**

```text
FotMob base: https://www.fotmob.com/api/data/
  leagues?id=55&ccode3=ITA&season=2026%2F2027
  tltable?leagueId=55
  matchDetails?matchId={id}
ESPN:
  https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard?dates=YYYYMMDD
  https://site.api.espn.com/apis/v2/sports/soccer/ita.1/standings
  https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/summary?event={id}
```

L'endpoint ESPN standings sotto `apis/site/v2` restituisce un oggetto vuoto; validare struttura e righe. FotMob ha fornito 380 fixture anche nella stagione storica 2024/25. I wrapper distribuiti `pyfotmob` e `mobfot` esaminati puntano ai vecchi percorsi: preferire REST diretto. Usare un User-Agent applicativo trasparente; i test con UA standard, applicativo e Mozilla sono tutti riusciti. Non è dimostrata la causa TLS/Akamai dei vecchi 403 né la necessità di Mozilla.

**Riserve:** BSD dichiara REST calcio gratuito con 7.500 richieste/giorno; senza token il live risponde 401. football-data.org dichiara Serie A free con dati ritardati e 10 richieste/minuto; senza token risponde 403. Sono alternative documentate da abilitare e verificare, non fallback già pronti. API-Football free, 100 richieste/giorno e stagioni limitate, non è adatto al polling continuo previsto. openfootball può fornire fixture offline di sviluppo; `soccerdata` è uno scraper per analisi sul PC, non un provider live o un archivio senza limiti.

**F1:** il percorso legacy `/signalr/negotiate` ha risposto 401; il LiveF1 esaminato lo usa ancora. Non adottare la libreria senza verificare il supporto Core della versione scelta. Il client FastF1 aggiornato offre un riferimento Core, ma accesso attivo, carico CPU/RAM e telemetria gratuita non sono stati misurati. ESPN F1 è una riserva candidata per riepiloghi: abbiamo letto una gara futura, non tutte le sessioni né un live.

**MotoGP:** backend del sito con documentazione community. `results/categories` richiede `seasonUuid`; la lista eventi include anche test. Nel timing abbiamo osservato `N`, posizioni -1 e tempi testuali zero. Non codificare `A/R` come attiva, `B` come verde o gap come millisecondi senza prove. Un codice sconosciuto resta `unknown`; uno snapshot Moto3 non attiva la vista MotoGP.

## 3. Esperienza sul display 960×640

Viste verticali: **Prossime → In corso, quando esiste → Risultati → Classifica → La mia squadra**. Dopo il riscontro sull’accessibilità, Classifica è una vista principale raggiungibile con 2/8. Con la sezione preferita Sport ha quattro viste a riposo e cinque quando si consulta un incontro attivo: eccezione esplicita al limite iniziale di tre della mappa UX. Tastierino: 2/8 cambiano vista o scorrono il pannello aperto; 5 OK apre/seleziona; 7 Indietro chiude; 4/6 cambiano famiglia in consultazione. Tastiera: Enter/Return = OK, Esc/Backspace = Indietro, coerentemente con [Main.qml](../Main.qml).

| Vista | Dato principale | Dettaglio con OK | Stati particolari |
| --- | --- | --- | --- |
| **Prossime** | Incontri futuri della prima giornata con partite in programma, tre per pagina, squadre e orari `Europe/Rome` | Partite del turno; massimo tre righe visibili, elenco scorrevole | Mostrare il prossimo incontro anche oltre sette giorni. Se data/orario non confermati indicarlo; nessun evento solo quando la fonte valida non ne fornisce |
| **Live** | Tutte le partite in corso, tre per pagina, punteggio e fase/minuto restituiti dalla fonte | Selezione delle partite simultanee e statistiche essenziali dell'incontro scelto | Live solo con stato attivo verificato; a fonte interrotta tenere l'ultimo incontro visibile come «Dati precedenti», togliere badge Live e fermare notifiche |
| **Risultati** | Ultimo turno, anche parzialmente completato con etichetta coerente | Pannello con scelta Risultati/Classifica; classifica completa delle 20 squadre scorrevole | Calendario rinviato e gare mancanti non diventano risultati 0–0; stagione e turno sempre identificabili |

| **Classifica** | Prime tre posizioni | Classifica completa delle 20 squadre; 2/8 scorre nel pannello aperto | Accessibile direttamente dalle viste principali, anche con giornata selezionata nell’elenco |

Prossime e In corso alternano le pagine ogni otto secondi solo durante la consultazione della vista principale. Aprendo elenco, dettaglio, Menu o Avvisi, la rotazione si ferma. Gli incontri con lo stesso orario restano distinti: nessuna deduplicazione per data.

Una o due informazioni secondarie per pagina: punteggio e fase hanno priorità. xG, possesso, tiri e formazioni sono dettagli facoltativi; non riempire la vista principale con tutte le statistiche. Mantenere focus e selezione quando arrivano aggiornamenti, cambia la disponibilità della vista Live o termina un incontro. Non spostare la persona dalla pagina che sta consultando.

Orari memorizzati in UTC e resi in `Europe/Rome`, inclusi mezzanotte, ora legale e cambio stagione. Non calcolare il minuto solo dall'orologio locale: pause, recupero e interruzioni richiedono il dato della fonte. Sono necessari casi di collaudo per nomi lunghi, marcatori mancanti e più incontri allo stesso orario.

## 4. Contratti dati e freschezza

Il contratto `SportMatch` è implementato in strutture Python; `SportSession` è ora normalizzato in `motorsport_core.py` per le estensioni motorsport. Usare dataclass/strutture Python coerenti col progetto; non introdurre Pydantic soltanto per questa specifica. Campi mancanti sono `null`, liste vuote sono reali assenze con semantica documentata; nessun valore zero fittizio.

### 4.1 `SportMatch`: partita tra due squadre

| Gruppo | Campi minimi |
| --- | --- |
| Identità | `sport`, `competitionId`, `season`, `canonicalMatchId`, `provider`, `providerMatchId` |
| Squadre | `homeTeamId`, `awayTeamId`, nomi; identificativi canonici e mappa degli ID provider |
| Programma | `kickoffUtc` nullable, `round`, eventuale `venue`, motivo di rinvio |
| Stato | `scheduled`, `live`, `half_time`, `finished`, `postponed`, `cancelled`, `unknown`; conservare anche `rawStatus` |
| Risultato | `homeScore`/`awayScore` nullable, fase/minuto, eventuali supplementari e rigori separati per future coppe |
| Dettaglio | Eventi con ID, tipo, squadra, minuto e stato conferma/revoca; statistiche/roster facoltativi |
| Provenienza | `checkedAt`, `fetchedAt`, eventuale `sourceDataAt`, `dataChangedAt`, `fromCache` |

Identità risolta usando competizione, stagione, ID squadre, lati casa/trasferta e ID provider. L'orario è un controllo, non l'identità esclusiva: può cambiare con un rinvio. Preservare lo stesso evento canonico quando si cambia fonte.

**Mappa canonica squadre Serie A (normalizzazione provider):**
Per evitare ambiguità tra FotMob ed ESPN, l'adapter risolve il nome squadra tramite slug canonico statico:
* `internazionale` → `inter`
* `ac milan` → `milan`
* `as roma` → `roma`
* `ss lazio` → `lazio`
* `verona` / `hellas verona fc` → `hellas_verona`
* `juventus fc` → `juventus`
Gli altri nomi sono normalizzati in slug; ogni eventuale nuovo alias va verificato. Non dedurre una corrispondenza incerta dal solo orario.

**Macchina a stati unificata (`status`):**
| Stato canonico | Condizione FotMob (`matchDetails` / `header`) | Condizione ESPN (`status.type`) |
| :--- | :--- | :--- |
| `scheduled` | `status.started == false` | `state == "pre"` o `STATUS_SCHEDULED` |
| `live` | `ongoing == true` e `status.started == true` | `state == "in"` (`STATUS_FIRST_HALF`, `STATUS_SECOND_HALF`) |
| `half_time` | `status.reason.short == "HT"` | `name == "STATUS_HALFTIME"` |
| `finished` | `status.finished == true` e `ongoing == false` | `state == "post"` o `STATUS_FULL_TIME` |
| `postponed` | `status.cancelled == true` con motivo rinvio | `name == "STATUS_POSTPONED"` |
| `cancelled` | `status.cancelled == true` definitiva | `name == "STATUS_CANCELLED"` |

### 4.2 `SportSession`: futura estensione motorsport

| Gruppo | Campi minimi |
| --- | --- |
| Identità | `sport`, `competitionId` stabile (`f1`/`motogp`), `season`, `canonicalSessionId`, `providerSessionId`, `provider`, categoria |
| Programma | Meeting, circuito, tipo sessione, inizio/fine UTC nullable; offset originale preservato |
| Ciclo sessione | `scheduled`, `active`, `finished`, `cancelled`, `unknown`, più valore raw |
| Stato pista | Separato dal ciclo sessione: bandiere/SC/VSC soltanto quando mappati con evidenza |
| Timing | Giro corrente/totale nullable, tempo residuo nullable, classifica con posizione valida, numero pilota, nome, team, gap raw e valore normalizzato se noto, stato pit |
| Provenienza | Come `SportMatch`, più heartbeat/ultimo delta separati dall'età dei dati di sessione |

Per SignalR Core: risultato iniziale + delta aggiornano lo stesso stato; un cambio sessione lo azzera. Riconnessione → nuova sottoscrizione/snapshot. Per MotoGP: categoria, identità e stato validi prima di pubblicare timing. Il tipo sessione e lo stato pista non si confondono con l'attività della connessione.

### 4.3 Stato del modulo e regola Live

Usare l'envelope esistente di [module_state.py](../module_state.py): `version`, `status`, `source`, `updatedAt`, `data`, `error`. Stati ammessi: `active`, `updating`, `stale`, `offline`, `error`, `unavailable`. `active` indica il modulo disponibile; il ciclo della partita sta in `data`. Dettagli di provenienza e timestamp stanno nel payload senza cambiare il contratto degli altri moduli.

- `checkedAt`: ultimo tentativo di controllo, anche fallito.
- `fetchedAt`: ultima acquisizione valida; `updatedAt` segue questo timestamp, non un tentativo fallito.
- `sourceDataAt`: timestamp della fonte se disponibile; non inventarlo usando la ricezione.
- `dataChangedAt`: ultima variazione dei dati, distinta dalla freschezza.

Uno 0–0 invariato può essere fresco dopo una risposta valida. Viceversa HTTP 200, heartbeat o `fetchedAt` recente non rendono attivo un vecchio snapshot F1 o una futura sessione MotoGP. Valutare insieme identità, finestra/stato sessione, contenuto e timestamp/cache della fonte.

**Proposta iniziale Serie A:** polling 30 s; dopo circa 90 s senza controllo valido, togliere Live e mostrare età dell'ultimo dato. La soglia va tarata con le prove; se il provider indica dati più vecchi applicare anche quel vincolo. Per calendario e risultati valgono scadenze differenti, senza applicare 90 s a tutto il modulo. Nessuna nuova notifica da dati stale/offline.

## 5. Architettura, persistenza e notifiche

### 5.1 Integrazione Python/Qt

Worker `QRunnable`/`QThreadPool`, già usati nel [meteo](../weather.py), per HTTP e parsing; nessuna rete nel thread QML. Pubblicazione di snapshot coerenti attraverso lo stato condiviso. Per F1 è implementato il client Core con QWebSocket asincrono, timeout e riconnessione; aggiornamenti raggruppati per evitare un ridisegno per ogni delta. Misurare navigazione e animazioni rappresentative sulla board.

Per HTTP: timeout, validazione schema/identità e risposta massima; rifiutare HTML, JSON vuoto dove si attendono dati, punteggi impossibili e stagione errata. Una risposta più vecchia non sovrascrive una revisione più recente. Mantenere l'ultimo dato valido durante aggiornamento/errori.

Il fallback cambia la fonte visibile e acquisisce una baseline coerente. Non sommare silenziosamente punteggio ESPN e marcatori FotMob con tempi diversi. La fonte secondaria è candidata fino a verifica live; un errore non attiva automaticamente servizi che richiedono un token assente.

### 5.2 Cache persistente

Cache `sport.json` sotto `QStandardPaths.CacheLocation`, seguendo il meteo e la `CacheDirectory` persistente del servizio. **Non `/tmp`.** Registro deduplicazione/eventi nella directory di stato, riusando [events.py](../events.py), `STATE_DIRECTORY`/fallback XDG. Cache e registro hanno scopi distinti.

Persistenza: `schemaVersion`, provider, competizione/stagione, timestamp, dati validati; scrittura temporanea nella stessa directory, flush/fsync e sostituzione atomica (`sport.json.tmp` → `sport.json`). Schema minimo serializzato:
```json
{
  "schemaVersion": 1, "provider": "fotmob", "competitionId": "serie_a",
  "season": "2026/2027", "fetchedAt": "2026-09-30T18:00:00Z",
  "standings": [...], "fixtures": [...], "activeMatches": [...], "lastFinished": [...]
}
```
Gestire cache mancante/corrotta/versione incompatibile senza crash, conservando l'ultimo snapshot valido quando possibile. Retention limitata: stagione corrente e precedente, ultimi dettagli consultati; storico ulteriore su richiesta.

Un vuoto valido nel perimetro «oggi» non cancella calendario/storico di tutta la stagione. Una risposta fallita/incompleta non diventa «Nessuna partita». Al riavvio offline visualizzare dati precedenti con fonte/ora; non emettere notifiche da cache. I referti conclusi rimangono correggibili: ricontrollo dopo circa 15 minuti, 1 ora e il giorno successivo.

### 5.3 Eventi e notifiche gol

Usare il motore eventi esistente e le preferenze della v0.5, incluse fascia di silenzio e interruzioni per categoria. Le notifiche Sport restano disattivate inizialmente finché non sono selezionate preferenze e verificato il comportamento live. L'integrazione deve essere collaudabile con replay senza attivare interruzioni reali.

- Un incremento del punteggio avvia la verifica del dettaglio; non basta da solo a dichiarare un gol confermato.
- Richiedere evento compatibile con punteggio/stato e ID stabile. **Protezione VAR predisposta, da collaudare dal vivo:** FotMob espone in radice di `matchDetails` il campo booleano `hasPendingVAR`. Se `hasPendingVAR == true`, congelare la notifica; confermare l'evento gol solo dopo che `hasPendingVAR` torna `false` e il punteggio resta accreditato. In ESPN, verificare che l'evento compaia in `keyEvents` con ID stabile e senza annotazione di revoca. Nel dubbio o in assenza di conferma, nessun overlay automatico «GOL».
- Deduplicare con identità canonica e ID/revisione evento, persistendo il cutoff. Avvio, riconnessione e cambio provider impostano una baseline; non notificano gol già avvenuti.
- Revoca VAR/correzione del risultato aggiorna o ritira l'avviso; non genera un secondo gol. Retry non duplicano eventi.
- Errori di provider producono uno stato, senza una raffica di overlay. Nessuna notifica storica dal dataset offline.

**Obiettivo da misurare:** arrivo di un gol entro circa 45 s rispetto alla fonte di confronto scelta. Non è una garanzia della release gratuita. Annotare piattaforma TV e suoi ritardi; una differenza rispetto alla TV non misura il ritardo assoluto dal campo. Qualora il ritardo sia maggiore, la UI e la descrizione del prodotto lo dichiarano e le notifiche possono restare escluse.

## 6. Polling e budget di rete

| Fase | Frequenza proposta | Note |
| --- | --- | --- |
| Riposo | Calendario/classifica ogni 6 h, più avvio/manuale controllati | Cache disponibile subito; protezione da richieste manuali ripetute |
| Da -60 min | Stato/formazioni ogni 15 min | Avvicinandosi all'orario previsto, passare al controllo 30 s per rilevare l'inizio, anche se lo stato è ancora scheduled |
| Partita attiva | Score aggregati ogni 30 s; dettaglio della partita scelta o conferma evento | Non scaricare tutti i dettagli a ogni ciclo; la disponibilità del dettaglio può essere diversa dallo score |
| Dopo la fine | Ricontrolli a circa +15 min, +1 h, giorno seguente | Nessun congelamento permanente del referto |
| Errore/429 | `Retry-After`, altrimenti backoff indicativo 60/120/300 s con jitter | Non moltiplicare retry tra worker/provider; mantenere cache e stato dell'errore |

Rispettare `Cache-Control`/`Age`, limitare concorrenza e registrare budget per endpoint. Nessuna quota pubblicata individuata per FotMob/ESPN: l'intervallo non dimostra assenza di limiti. A 30 s un endpoint costa 240 richieste in 2 h; scoreboard + tre dettagli nello stesso intervallo costano 960, prima dei retry. La prova con due fonti raddoppia la parte comune del traffico. Jolpica non richiede live polling e ha limiti propri documentati.

La fonte di calendario fornisce la stagione; scoreboard per data esplicita e timezone corretta fornisce gli incontri rilevanti. Il default ESPN non è un calendario completo. La finestra di polling copre gare simultanee, recuperi e partite che attraversano mezzanotte senza interrogare tutta la stagione ogni 30 s.

## 7. Piano di sviluppo e criteri di uscita

| Fase | Lavoro | Stato / criterio verificabile |
| --- | --- | --- |
| **0a · Accesso e schema** | Confronto HTTP PC/board, wrapper, protocolli F1, MotoGP | **Completata per i campioni documentati:** 37 richieste per ambiente; WS Core dal PC. [Evidenze](./v06-sport-api-research.md#2-evidenze-e-metodo). Nessuna misura di latenza live |
| **0b · Serie A attiva** | Durante una partita confrontare FotMob/ESPN, inizio, gol, VAR se presente, finale e recupero da errore | **Da fare:** timestamp per fonte, richieste/errors, ritardo rispetto al riferimento dichiarato. Scegliere primaria/riserva senza attribuire una garanzia da una sola partita |
| **1 · Adapter e cache** | Contratto Serie A, stato condiviso, fallback esplicito, persistenza | **Implementata e verificata:** casi pertinenti per punteggio mancante/0–0, rinvio, vuoti/errori, identità tra fonti, corruzione cache e correzione finale |
| **2 · UI Sport** | Tre viste, classifica completa e dettaglio, impostazioni visibilità | **Prove automatiche QML/EGLFS completate; lettura a 1,5 m da verificare manualmente:** 960×640, nomi lunghi, tre righe scorrevoli, tasti coerenti, focus stabile, dati vecchi/assenti riconoscibili |
| **3 · Notifiche facoltative** | Eventi confermati, baseline e deduplicazione persistente | **Condizionata alla 0b:** replay di gol/revoca/riconnessione/cambio fonte; nessun duplicato al reboot. Se le prove non bastano, le notifiche restano disattivate |
| **4 · Rilascio Orange Pi** | Backup versione/config/cache, deploy, reboot offline/online e rollback | **Deploy/reboot e ripresa verificati; rollback completo non eseguito:** servizio avviabile, cache disponibile dopo reboot offline, ripresa online senza falsi avvisi, navigazione/animazioni profilate sulla board, rollback concreto verificabile |
| **5 · Estensioni** | Client Core F1 e adapter PulseLive MotoGP | **Implementata per programma, risultati e classifiche:** REST corrente/precedente, Qt Core su board, cache/offline e catture EGLFS verificati. Sessioni attive, latenza e mapping gateway MotoGP rimangono da collaudare; [prove e limiti](v06-motorsport-release.md) |

**Uscita v0.6:** fasi 1, 2 e 4 completate, con scope chiaro. Calendario/risultati/classifica possono uscire prima della prova live; badge Live e notifiche vengono abilitati soltanto dopo i rispettivi criteri. Nessun dato di fixture/replay viene presentato come attuale.

Il vincolo 60 fps riguarda animazioni e interazione reali sul display, con diagnostica passiva e scenari rappresentativi. Un HTTP riuscito, un check sintattico sul PC o un render statico non provano fluidità/affidabilità sulla board. Il collaudo finale documenta tempi, misure, problemi aperti e decisione di rilascio, includendo reboot senza rete e correzioni al ritorno online.

## 8. Stato dell’implementazione

- **FotMob principale candidato, ESPN riserva candidata** per la Serie A: entrambe le fonti sono accessibili oggi anche dalla Orange Pi e concordano sul match verificato.
- **Jolpica + SignalR Core** per F1; la raccomandazione generica LiveF1 legacy è sostituita dal requisito di protocollo/versione verificati.
- **PulseLive REST + lite** per MotoGP, con filtro categoria e stati/unità da confermare durante sessione attiva.
- Contratti estendibili, cache persistente, freschezza e notifiche condizionate sono definiti. Accesso odierno gratuito non equivale a disponibilità permanente garantita.

L'adapter Serie A, la cache e le viste sono ora implementati. La prima partita utile completa il collaudo live. Stato del deploy, risultati e limiti sono nel [resoconto v0.6](./v06-sport-release.md). Il piano conserva i criteri originali: implementazione e prove live restano evidenze distinte.

## 9. Estensione motorsport · 1 ottobre 2026

Il carosello comprende ora **Serie A → F1 → MotoGP**, con 4/6 tra gli sport, 2/8 tra Programma/Risultati/Classifica e In corso condizionale, 5 per consultare GP/sessioni o tutte le posizioni. Le etichette del tastierino fisico sono **1 Indietro / 7 Home**; il ritorno conserva la selezione. La scelta verticale è separata per ogni disciplina. Moduli visibili e impostazioni sono paginate, tre righe per pagina.

F1 usa Jolpica + Qt SignalR Core; MotoGP usa PulseLive risultati/broadcast/gateway lite. La UI espone stagione corrente e precedente; ulteriori anni restano un ampliamento possibile della consultazione. Libere F1 e qualifiche Sprint non sono fornite da Jolpica: l'aggiornamento dei dettagli aggiunge OpenF1 gratuito per quelle sessioni concluse. MotoGP carica ogni sessione pubblicata alla selezione. I criteri live originali restano aperti: collegarsi a uno snapshot concluso non li soddisfa. Dettagli, prove board, screenshot e ripristino nel [resoconto](v06-motorsport-release.md).

### Dettagli motorsport approvati e implementati

Scelta dell'utente: nessun pilota preferito. Aggiunti **Sessioni / Circuito / Riepilogo** nel weekend e apertura del dettaglio di ogni pilota nei risultati, con griglia, punti, giri, stato e tempi disponibili. Gara F1: soste in pit lane, tempi giro per giro e gomme/stint; altre sessioni F1: dettagli e gomme. MotoGP: caratteristiche del circuito, record, moto/costruttore, velocità media e condizioni registrate della sessione. Timing con viste Pista/Direzione e campi avanzati presenti nel feed, ancora subordinati al collaudo attivo.

Fonti gratuite senza registrazione: Jolpica, OpenF1 storico, endpoint PulseLive e SignalR osservati. Cache e richieste in worker; le fonti aggiuntive hanno errori isolati. [Implementazione e riscontri sulla board](v06-racing-details-release.md).

## Estensione implementata: squadra preferita

Il 1 ottobre 2026 è stata aggiunta **La mia squadra**, con selezione diretta, calendario di tutte le competizioni pubblicate, risultati, dati del club e rosa. Fonte FotMob, cache separata per club, fallback Serie A dichiarato parziale. La verifica comprende navigazione tramite decoder HID, catture EGLFS sulla board e nuovo processo offline. [Resoconto, uso e limiti](./v06-favourite-team-release.md). Le diciture fisiche richieste sono 1 Indietro / 7 Home; i gestori interni dei tasti sono rimasti invariati.

## Estensione implementata: Fantacalcio

Il dettaglio delle sole partite Serie A ha una quarta scheda **Fantacalcio**, disponibile anche da La mia squadra. Mostra formazione, titolari, subentrati e panchina con voto base e fantavoto della Redazione Fantacalcio. Fonte pubblica, cache atomica per giornata, aggiornamento in worker su consultazione, verifica delle identità e dati assenti espliciti. [Resoconto, test e limiti della prova live](./v06-fantacalcio-release.md).

## Revisione del codice · 1 ottobre 2026

Completata dopo l’approvazione dell’implementazione: cache delle presentazioni F1/MotoGP e dei referti, scritture Serie A fuori dal thread GUI, conservazione dei dettagli pilota, merge SignalR e chiusura dei worker. Misure comparative e prove fisiche raccolte prima della distribuzione. [Resoconto e limiti](./v06-sport-code-review.md).
