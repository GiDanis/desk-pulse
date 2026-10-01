# Fantacalcio: feed live e storico

Implementato il **1 ottobre 2026**. Estensione della [scheda Fantacalcio](v06-fantacalcio-release.md), approvata dall’utente. Il feed usa la stessa sequenza del [progetto di riferimento](https://github.com/andregri/fantacalcio-voti-live-js) e dei servizi del sito: firma anonima, risorsa `.dat`, descrittore verificato e decodifica Protobuf.

## Stagione: una ricerca per annata

La stagione proviene dalla partita normalizzata, ad esempio `2026/2027`; non viene dedotta dall’anno civile né incrementando un ID conosciuto. La prima richiesta legge la pagina della stagione/giornata, verifica `og:url` ed estrae l’ID dal collegamento `Excel/votes/{seasonId}/{giornata}`. La prova sulla fonte identifica **2026/27 → 21**.

La mappa si salva atomicamente in `fantacalcio-seasons.json`, accanto a `sport.json`. Rimane valida per tutta la stagione e dopo il riavvio del processo. Un’altra giornata riusa lo stesso ID. Una nuova annata richiede una nuova ricerca. Una risorsa live `404` non invalida la stagione e non provoca nuove ricerche.

## Durante la partita

- Richieste soltanto mentre si consulta Fantacalcio, ogni **30 secondi**, condivise per giornata. Fuori dalla scheda il timer si ferma.
- Finestra: quindici minuti prima del calcio d’inizio per gli incontri programmati; partita in corso/intervallo entro quattro ore dal calcio d’inizio; conclusa da meno di tre ore dal calcio d’inizio per la transizione ai voti pubblicati. Rinvii, coppe e vecchie partite non interrogano il feed.
- Il client firma `https://api.fantacalcio.it/v1/st/{seasonId}/matches/live/{giornata}.dat` mediante `https://www.fantacalcio.it/api/v1/SignedUri`. Non invia cookie, utente o password. L’URL firmato resta nel worker, senza salvarlo o registrarlo nei report.
- Il descrittore ufficiale `js/proto/live.txt` viene verificato alla prima risorsa disponibile del processo. Un cambiamento dello schema interrompe la decodifica. Il decoder Python limita dimensioni, lunghezze, tipi e numero di messaggi; non richiede Node o nuove dipendenze di sistema.
- Sono verificati stagione, giornata, entrambe le squadre e calcio d’inizio. Le righe della fonte senza abbinamento univoco restano separate.
- I voti live sono **PROVVISORI**, conservati solo in memoria e utilizzabili per massimo **120 secondi** dall’acquisizione, al netto dell’età HTTP dichiarata. La freschezza del contenuto del provider durante una partita reale resta da misurare.
- I codici `0`, `55`, `56`/voto assente del feed non diventano falsi voti. Gli allenatori sono esclusi.
- Un errore mantiene il campione live ancora valido o i voti pubblicati disponibili. Gli errori del feed hanno una pausa minima di 120 secondi; `401/403` restano distinti da `404`, senza richiedere automaticamente un account.

Il feed espone il **voto base**, non una colonna fantavoto. La UI indica **FANTAVOTO CALCOLATO**. Il profilo classico usato per la stima: gol/rigore segnato +3, assist classico +1, rigore parato +3, rigore sbagliato −3, gol subito −1, autogol −2, giallo −0,5, rosso −1. Eventi senza bonus standard, come sostituzioni, non modificano il voto. Assist soft/gold, contributi, gol annullati, combinazioni giallo+rosso o gol+rigore e codici sconosciuti lasciano il fantavoto **—**, per evitare calcoli ambigui. Non è il regolamento personalizzato di una lega. Per una partita conclusa i voti pubblicati abbinati hanno precedenza sul feed.

## Storico

I voti pubblicati si recuperano dalla pagina pubblica della **stagione e giornata della vecchia partita**. Il feed live non è un archivio permanente. Restano voto base e fantavoto della Redazione Fantacalcio, senza ricalcolare il valore pubblicato. La pagina è condivisa tra tutti gli incontri della giornata e salvata nella cache atomica `fantacalcio-{stagione}-{giornata}.json`; i campioni live non possono sovrascriverla.

Corretto il parser delle annate precedenti: gli URL dei calciatori possono terminare con `/{id}/{stagione}`, invece di `/{id}`. Il parser verifica anche che l’eventuale stagione dell’URL coincida con quella richiesta. Una pagina senza tabellini riconoscibili viene rifiutata, conservando la cache precedente.

Il recupero si applica alle vecchie partite consultabili tramite i calendari e le stagioni già offerte dalla dashboard; questa estensione non aggiunge una nuova schermata di archivio. Sono stati verificati i campioni 2023/24 e 2026/27, non tutte le annate. I voti pubblicati possono essere corretti dalla redazione e vengono aggiornati su consultazione (5 minuti nelle prime 24 ore, 6 ore per incontri più vecchi).

## Verifiche

- **27 test automatici sulla board**: 7 Fantacalcio, 11 nuovi sul feed e 9 regressioni dell’ottimizzazione Sport. Le nuove prove coprono binario reale registrato, confronto con la redazione, cache della stagione tra giornate/processi, cambio annata, schema cambiato, risposta di firma con chiave UUID, pausa su `404`/`401`, storico prioritario, cache pubblicata protetta, payload malformati, bonus ambigui, selezione e scadenza.
- **HTTP reale sulla board:** una ricerca trova ID 21; un nuovo client riusa l’ID con **0 richieste di ricerca**. Descrittore ufficiale confermato. Firma senza credenziali: risorsa live **404**. Una richiesta all’archivio 2023/24, giornata 4: **20 squadre, 318 calciatori**. Terracciano 5,5/3,5, Duncan 6,5/7,5, Bonaventura 7/10; Barak assente. [Report](evidence/v06-fantacalcio-live/fantacalcio-live-http.json).
- **Qt/EGLFS 960×640:** comandi HID, tutti i calciatori, preferita/coppe, manuale, errore, replay dei provvisori e scadenza; zero avvisi QML. [Report](evidence/v06-fantacalcio-live/fantacalcio-ui.json). [Cattura del replay](evidence/v06-fantacalcio-live/fantacalcio-live-replay.png), esaminata direttamente: il replay usa dati di prova, non una partita in corso.
- **Processo nuovo senza rete:** voti pubblicati conservati, 23 giocatori per squadra e stato offline. [Report](evidence/v06-fantacalcio-live/fantacalcio-offline.json). Non è stato eseguito un riavvio del sistema operativo.

**Verifica aperta:** ricezione della risorsa durante una partita Serie A attiva, frequenza degli aggiornamenti e confronto dei voti in quel momento. Il `404` osservato non prova che serva il login e non dimostra ancora accesso anonimo al contenuto live. Non vengono dichiarate latenza o copertura live verificate.

Codice: `fantacalcio_live.py`, `fantacalcio.py`, `fantacalcio_core.py`; controlli: `check_fantacalcio_live.py`, `check_fantacalcio_ui.py`, `verify_fantacalcio_live.py`. [Attribuzione del riferimento e campioni](../third_party/fantacalcio-live-NOTICE.md).

**Installazione verificata:** cinque file runtime corrispondono agli SHA-256 locali; servizio `active/running`, zero riavvii automatici e nessun warning nel journal durante il controllo finale. La mappa 2026/27 → 21 acquisita sulla fonte è installata nella cache di produzione. [Report deploy](evidence/v06-fantacalcio-live/deploy.json).

Backup della sorgente prima dell’installazione: `/var/backups/smartpc-dashboard-fantacalcio-live-20261001/dashboard`. Il deploy aggiorna solo i file runtime Fantacalcio e le due viste interessate.
