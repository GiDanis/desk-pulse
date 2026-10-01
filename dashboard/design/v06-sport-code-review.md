# v0.6 · Revisione e ottimizzazione Sport

Completata il **1 ottobre 2026**, dopo l'approvazione dell'implementazione. Ambito: Serie A, squadra preferita, Fantacalcio, F1 e MotoGP. Correzioni distribuite sulla Orange Pi; navigazione e contenuti delle schermate conservati.

## Correzioni

### Meno lavoro sul thread dell'interfaccia

- `MotorsportService` riusa la presentazione derivata dello stesso snapshot: calendario, risultati e righe informative vengono elaborati una volta per revisione. Invalidazione quando cambia snapshot/provenienza, agli orari delle sessioni, alla scadenza del GP, al limite di 30 minuti delle prossime sessioni, dopo 60 secondi o se l'orologio torna indietro. I flag di caricamento, errore e freschezza sono calcolati separatamente.
- `TimingState` riusa le righe fino al prossimo aggiornamento dei topic. Il heartbeat aggiorna la freschezza senza ricostruire l'elenco piloti. Il merge dei delta lavora sul dato posseduto dallo stato, eliminando copie ricorsive ripetute; l'API pubblica `deep_merge` conserva gli input.
- Le copie iniziali degli snapshot per i worker Serie A, squadra e motorsport sono state eliminate dal thread GUI: gli adapter copiano i dati nel worker. Gli snapshot pubblicati vengono sostituiti, non modificati sul posto. Le strutture derivate condivise sono di sola lettura per i consumatori Python; Qt converte i valori per QML.
- Scrittura atomica, `fsync` e pulizia delle vecchie cache Serie A avvengono nel worker. Disco pieno/non scrivibile: i dati validi restano utilizzabili e compare «Cache non salvata». Conservati i criteri di accettazione per stagione e timestamp e la finestra corrente/precedente.

### Richieste e conservazione dei dettagli

- Aprire una sessione F1 carica il suo referto, evitando quelli di altre sessioni. I risultati già presenti vengono riusati per **10 minuti** quando la sessione risale a meno di un giorno; per **6 ore** nello storico consolidato. Cache con timestamp futuro non considerata fresca.
- Programma ed elenco sessioni MotoGP: **60 secondi** durante il weekend, da un'ora prima della prima sessione fino a un giorno dopo il GP; **6 ore** fuori da questa finestra. I risultati hanno il criterio precedente.
- **5 Aggiorna** nei pannelli GP/sessione/pilota ignora questa cache logica; mantiene la pausa di 30 secondi tra comandi manuali, una sola richiesta in lavorazione, cache HTTP e limiti dei provider. Tornare dal pilota alla sessione riusa il referto già disponibile.
- Un aggiornamento della classifica OpenF1 o dell'intero calendario Jolpica conserva gomme, giri e soste già acquisiti per lo stesso pilota. Aggiornare il programma MotoGP conserva risultati, identità e condizioni delle sessioni precedenti.
- Richieste bloccate da cooldown HTTP non consumano il budget locale Jolpica/OpenF1.

### Chiusura e feed F1

- Dopo `close()`, Serie A, squadra, Fantacalcio e motorsport ignorano completamenti tardivi e impediscono nuovi worker. Questo evita richieste successive alla chiusura e pubblicazioni verso servizi eventi già chiusi.
- Il cambio sessione SignalR pulisce i dati della sessione precedente conservando lo stato della connessione ancora aperta. Le revisioni sono monotone; aggiornamenti solo di meteo/direzione gara notificano QML anche senza un nuovo `TimingData`.

## Misure sulla Orange Pi

Stesso hardware e stesso snapshot reale, 30 letture Python di `moduleState` per disciplina. Il servizio di produzione resta attivo durante il confronto; i servizi misurati hanno rete disabilitata tramite `auto_refresh=False`. La prima lettura è inclusa nei 30 campioni.

| Disciplina | Snapshot JSON | Mediana prima | Mediana dopo | p95 prima | p95 dopo | Prima lettura dopo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| F1 2025 | 83.089 byte | 10,357 ms | 0,007 ms | 10,850 ms | 0,043 ms | 10,401 ms |
| MotoGP 2026 | 40.484 byte | 3,746 ms | 0,008 ms | 3,978 ms | 0,027 ms | 3,906 ms |

Il beneficio riguarda le letture ripetute di dati invariati. La prima elaborazione e quelle successive a invalidazione conservano il costo di costruzione. **Non è una misura degli FPS, della conversione QVariant o del tempo GPU.** [Prima](evidence/v06-sport-review/review-before.json) / [dopo](evidence/v06-sport-review/review-after.json).

Confronto delle chiamate agli adapter usando risposte pubbliche reali registrate e cache logica fresca; nessuna nuova chiamata esterna durante questa verifica:

| Riapertura della gara storica già caricata | Prima | Dopo | Righe risultati conservate |
| --- | ---: | ---: | ---: |
| F1, Abu Dhabi 2025 | 2 | 0 | 20 |
| MotoGP, GP 15/2026 | 3 | 0 | 22 |

Sono chiamate al metodo `get` dell'adapter: la cache HTTP poteva già evitare alcuni accessi alla rete nella versione precedente. [Prima](evidence/v06-sport-review/requests-before.json) / [dopo](evidence/v06-sport-review/requests-after.json).

## Verifiche completate

- **46 test automatici** sulla board: 9 regressioni nuove, 11 motorsport, 11 Serie A, 8 squadra e 7 Fantacalcio. Le nuove regressioni coprono riuso/invalidazione, delta e proprietà degli input, scadenze dei risultati, comando manuale, conservazione dei dettagli, scritture su thread worker, disco pieno, chiusura e cooldown. [Log](evidence/v06-sport-review/checks-board.log).
- **Quattro verifiche QML**: motorsport, Serie A, squadra preferita e Fantacalcio. Decoder HID, liste complete, ritorno/focus, selezione più recente, stagioni, partite future/coppe, cache e dati mancanti. Nessun warning QML.
- **16 catture sul display reale**, 960×640, EGLFS/KMS e OpenGL, con risposte reali registrate e preferenze isolate; nessun errore QML. Ispezionate direttamente le viste [Giri F1](evidence/v06-sport-review/f1-laps.png) e [Pilota MotoGP](evidence/v06-sport-review/moto-driver.png). [Rapporto renderer](evidence/v06-sport-review/render.json).
- **Nuovo processo offline**: circuito, dettaglio pilota, gomme/giri F1 e condizioni MotoGP conservati nella cache. [Rapporto](evidence/v06-sport-review/offline.json).
- I messaggi di rete offline e di payload malformato nel log dei test sono guasti intenzionali; il registro della nuova istanza di produzione non contiene errori.

## Distribuzione e recupero

Installati 10 file Python/QML, confrontati con il workspace tramite SHA-256. [Manifest](evidence/v06-sport-review/deploy.json).

Servizio `smartpc-dashboard.service`: `active/running`, `NRestarts=0`; nuova invocation `3ecb70da96fa43edb9f24b2134dac7e9`. Registro di questa invocation vuoto al controllo dopo il riavvio.

Backup completo prima della distribuzione:

```text
/var/backups/smartpc-dashboard-sport-review-20261001/dashboard
```

Per ripristinare: fermare il servizio, ripristinare da quel backup i file elencati nel manifest e riavviare. Preferenze, credenziali e cache di produzione non sono state sostituite dalle prove.

## Limiti rimasti

Il collaudo durante una sessione realmente attiva e quello delle notifiche gol restano aperti secondo i criteri precedenti. I badge Live mantengono gli stessi gate di verifica. Questa revisione non certifica 60 fps e non aggiunge account, costi o nuovi provider.


## Pulizia successiva: codice inutilizzato

Eseguita il 1 ottobre 2026 dopo l’integrazione del feed Fantacalcio. Controllati riferimenti Python/QML e chiamanti prima delle rimozioni:

- Import inutilizzati nei provider e negli script di verifica/test (inclusi `mapping`, `timezone`, `patch` e alias non usati).
- Vecchio wrapper `weather_alerts.fetch_alerts`, senza chiamanti: il servizio eventi usa direttamente `BulletinProvider`, con il suo stato persistente.
- Proprietà `SportView.match`, mai letta; variabile locale della data MotoGP, calcolata e mai usata; nome residuo `extra_at` nel recupero ESPN, sostituito da `_` senza cambiare la richiesta.
- Vecchia immagine `dashboard/preview.png`, priva di riferimenti. I README usano `preview-v03.png`.

Fixture storiche, cache, fonti di riserva, callback Qt/HTMLParser, utilità eseguibili e documentazione delle verifiche rimangono funzionali. Nessun nuovo test che ripeta le rimozioni: riutilizzate le prove di comportamento esistenti.

Verifica: **46 test** sia locali sia sulla Orange Pi (11 Serie A, 11 motorsport, 7 voti pubblicati, 11 feed Fantacalcio, 6 bollettino meteo), più i tre controlli QML Serie A/Fantacalcio/motorsport, tutti passati. Nessun import Python al livello del modulo risulta inutilizzato dall’analisi AST, ricontrollata dopo la pulizia. L’analisi statica non è una garanzia universale di assenza di codice morto; callback e accessi dinamici sono stati valutati separatamente.

Distribuiti i sei file runtime modificati; controllo SHA-256 e stato del servizio registrati nel [report](evidence/v06-cleanup/deploy.json). Backup: `/var/backups/smartpc-dashboard-cleanup-20261001/dashboard`.
