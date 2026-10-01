# v0.7 Casa · verifica delle chiamate reali

**1 ottobre 2026. Stato aggiornato: accesso API riuscito, 16 dispositivi rilevati e specifiche/stati letti per quattro dispositivi.** Il provider periodico e la schermata Casa restano da implementare; affidabilità fisica, propagazione delle modifiche e quote non sono ancora collaudate.

## Problemi identificati e risolti

L'UID inizialmente configurato non coincideva con quello degli account collegati. L'API diagnostica ha restituito un elenco completo di 16 dispositivi con un solo UID: è stato usato quell'UID per correggere il file privato. Non sono stati salvati identificativi o credenziali in questo documento. L'UID del token del progetto e l'UID dell'account configurato erano diversi; non abbiamo usato l'UID del token come sostituto di quello dell'app.

Dopo questa correzione funzionano sia l'inventario generale con filtro `tuyaUser`, sia l'inventario specifico Smart Home: entrambi restituiscono 16 dispositivi. La query delle case restituisce una casa. Il precedente `28841107` (data center sospeso) non compare più nelle nuove prove. Nella prima serie di questo controllo le API per UID restituivano invece `1106`; dopo aver corretto l'UID, le stesse chiamate sono riuscite. La diagnosi non può quindi essere ridotta al solo stato del data center.

Un confronto indipendente con la funzione `_calculate_sign` del connector ufficiale ha trovato un difetto nella firma dei parametri contenenti caratteri speciali: il client firmava i valori codificati nella URL, mentre il connector firma i valori originali ordinati. Corretto separando il percorso da firmare dalla URL codificata per il trasporto. Il difetto non influiva sulla prima pagina con l'UID alfanumerico; avrebbe influenzato cursori particolari ed elenchi di ID separati da virgole. [Connector Python ufficiale](https://github.com/tuya/tuya-connector-python/blob/master/tuya_connector/openapi.py), [regole delle firme](https://developer.tuya.com/en/docs/iot/new-singnature?id=Kbw0q34cs2e5g).

Il confronto dopo la correzione coincide nei tre casi: filtro UID, cursore con spazio/segno più/slash, elenco di più ID. La richiesta reale dei protocolli con 16 ID separati da virgole è riuscita dopo la correzione. Aggiunto un test di regressione con risultato della firma congelato e verificato separatamente sul codice ufficiale.

## Chiamate controllate

Endpoint effettivo: `https://openapi.tuyaeu.com` (Central Europe). Tutte le richieste sono GET; corpo vuoto, timestamp in millisecondi, HMAC-SHA256 maiuscolo. Token solo in memoria; credenziali nel file privato con permessi 600. Nessun comando, modifica di dispositivo o associazione effettuata.

| Scopo | Percorso e parametri | Esito reale |
| --- | --- | --- |
| Token iniziale | `/v1.0/token?grant_type=1` | Riuscito |
| Rinnovo | `/v1.0/token/{refresh_token}`, firma senza access token | Riuscito nella prova precedente |
| Inventario del provider | `/v1.3/iot-03/devices`, `source_type=tuyaUser`, `source_id={UID}`, `page_size=100` | 16 dispositivi, risposta completa |
| Confronto Smart Home | `/v1.0/users/{uid}/devices`, `page_no=1`, `page_size=20` | 16 dispositivi |
| Case dell'account | `/v1.0/users/{uid}/homes` | Una casa |
| Diagnosi account collegati | `/v1.0/iot-01/associated-users/devices`, `size=100` | 16 dispositivi, un UID distinto |
| Specifiche | `/v1.2/iot-03/devices/{device_id}/specification` | Riuscite sui quattro dispositivi selezionati |
| Stati | `/v1.0/iot-03/devices/{device_id}/status` | Riusciti sui quattro dispositivi selezionati |
| Protocolli | `/v1.0/iot-03/devices/protocol`, `device_ids={16 ID}` | 6 Zigbee, 4 Wi-Fi, 6 senza protocollo dichiarato |

L'API generale non era un percorso inventato o privo di filtro: Tuya documenta `tuyaUser` e `source_id=UID`. È elencata nel gruppo General Device Management; la disponibilità va comunque verificata per il progetto. Le API Smart Home sono state confrontate realmente e non usate come un fallback silenzioso su tutti gli utenti. [Inventario generale](https://developer.tuya.com/en/docs/cloud/dc413408fe?id=Kc09y2ons2i3b), [inventario Smart Home](https://developer.tuya.com/en/docs/cloud/ad2823ae46?id=Kconjtzq1vk1q), [API protocolli](https://developer.tuya.com/en/docs/cloud/674e547ab8?id=Kbejlela50w87).

Il provider mantiene l'inventario generale paginato che ora funziona. La risposta Smart Home è una lista con paginazione a numero di pagina: non sarebbe corretto sostituire soltanto il percorso mantenendo il parser/cursore dell'API generale.

## Evidenza dei dispositivi

Disponibilità al momento della verifica: **7 online e 9 offline secondo Tuya**. Le etichette Wi-Fi/Zigbee derivano dall'API protocolli, non dal nome o dal solo flag di sottodispositivo. I sei protocolli mancanti restano non determinati; tra questi figurano gateway e dispositivi con nomi IR/RF, senza attribuire loro un protocollo per supposizione.

| Dispositivo | Protocollo da API | Disponibilità cloud | Ultimo stato riportato letto |
| --- | --- | --- | --- |
| T & H Sensor | Zigbee | Online | 28,2 °C; umidità 43%; batteria 30% |
| Zigbee Plug | Zigbee | Offline | `switch_1=true`; ultimo valore potenza 48 W |
| Lampada scrivania | Wi-Fi | Offline | `switch_led=true`; modalità white |
| Sensore di movimento | Zigbee | Offline | `pir=none`; batteria 82% |

**Offline non significa spento.** La risposta di stato della presa e della lampada continua a contenere `true` mentre l'inventario dice `online=false`. Per il prodotto: testo dominante «Offline», stato del commutatore qualificato come precedente, nessuna conferma di raggiungibilità o di esecuzione. La riuscita della GET non rende fisicamente attuale quel valore.

Le scale sono lette dalle specifiche: temperatura 28,2 °C, corrente 201 mA e tensione 239 V sono esempi normalizzati. I campi strutturati/non supportati (come `colour_data_v2` o bitmap `fault`) restano da verificare, senza traduzioni arbitrarie. I valori di luminosità/temperatura colore senza unità non vengono convertiti automaticamente in percentuale o kelvin.

## Verifiche software e dati conservati

- **22 controlli superati sul PC e 22 sulla Orange Pi**, inclusi firma dei cursori, token, cache atomica, errori, isolamento account e normalizzazione. Le prove sulla board usano risposte simulate e non modificano il kiosk.
- Seconda acquisizione reale: ancora 16 dispositivi, zero aggiunte/rimozioni/rinomine; cache completa normalizzata salvata atomicamente.
- In questo controllo sono state effettuate **25 chiamate Tuya**: confronto degli endpoint, scoperta dell'UID corretto, letture su quattro dispositivi e verifica finale dei protocolli. Le due prove iniziali della firma hanno consultato GitHub senza chiamare Tuya.
- Credenziali, token, local key, IP, coordinate e risposte grezze non vengono scritti nei file della dashboard. Credenziali rimosse dalla guida e mantenute soltanto nel file privato del PC; nessuna trasferita sulla Orange Pi.
- Riepilogo normalizzato in `~/.cache/smartpc/tuya-api-verification.json`; inventario in `~/.cache/smartpc/tuya-inventory.json`. Entrambi privati con permessi 600. Il riepilogo non contiene UID, ID dei dispositivi o segreti.

## Analisi ancora da completare

L'accesso alle API e la lettura dei payload sono ora dimostrati. Per chiudere l'analisi di affidabilità servono ancora confronto con Smart Life/dispositivi fisici, cambi di stato e ritardo misurato, disalimentazione e recupero, aggiunta/rinomina/rimozione reali, quota e scadenza effettive di IoT Core. Nessuna di queste prove è stata dichiarata conclusa sulla sola base della GET.

La schermata dovrà distinguere cloud raggiungibile, dispositivo offline e dato precedente; selezionare massimo quattro dispositivi per ID stabile; applicare polling/backoff entro la quota. Worker Qt, scheduling, cache degli stati con provenienza/freschezza e riavvio offline restano lavoro della v0.7. Il probe attuale è manuale e non è una release completa.
