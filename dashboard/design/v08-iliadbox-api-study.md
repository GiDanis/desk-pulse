# v0.8 · iliadbox — documentazione locale, token e verifica API

**7 ottobre 2026 · Europe/Rome · letture API e autorizzazione applicativa richiesta dall’utente.**

Approfondimento dello [studio Rete locale](v08-local-network-analysis.md), dopo l'indicazione dell'utente di consultare la documentazione sviluppatore sul router. Le letture sono state eseguite dal PC di sviluppo, non dalla Orange Pi. Dopo la consultazione, l’utente ha chiesto esplicitamente di ottenere il token e ha consentito l’accesso sul display della iliadbox. Registrazione completata; nessuna discovery diretta dei client, modifica alla configurazione di rete o installazione dashboard.

## 1. Riscontri effettivi

| Verifica | Esito |
| --- | --- |
| Interfaccia web `http://192.168.1.254/` | iliadbox OS raggiungibile. |
| Menu → Sviluppatore | Documentazione disponibile anche in modalità ospite. |
| Login web | Un solo campo Password, nessun campo username; accesso riuscito con la credenziale fornita dall'utente. Credenziale non riportata nei file dello studio. |
| `GET /api_version` | HTTP riuscito, `api_version=15.0`, `api_base_url=/api/`. |
| Identificazione restituita | `box_model=ibxgw8-r1`, `box_model_name=iliadbox (r1)`, `device_name=iliadbox Server`. |
| HTTPS | Discovery: `https_available=true`, `https_port=12320`; chiamate locali autenticate su porta 443, chain e hostname verificati. Accesso dalla board ancora da provare. |
| `GET /api/v15/login/` senza token | HTTP 200, `success=true`, `logged_in=false`, challenge presente. Valore del challenge non conservato. |
| `GET /api/v15/lan/browser/interfaces/` senza token | HTTP 403, `success=false`, `error_code=auth_required`. |

Fonti locali: [documentazione sviluppatore](http://192.168.1.254/doc/index.html), [identificazione API](http://192.168.1.254/api_version). [Resoconto strutturato dei controlli](evidence/v08-iliadbox-study-2026-10-07/preliminary-checks.json), senza password/token/UID. L'indice documentale dichiara anch'esso API 15.0. Il titolo del corpus conserva il nome Freebox OS, ma il contenuto è servito dalla iliadbox reale: non dipendiamo più soltanto dal vecchio SDK pubblico indicizzato.

Il login amministrativo web e l’autenticazione di un’app sono percorsi diversi: il successo del primo non concede automaticamente accesso al provider futuro. Il token è stato ottenuto con il flusso ufficiale di registrazione, senza estrarlo dalla pagina amministrativa. L’app Dispositivi di rete non aveva aperto un elenco verificabile nel controllo preliminare; i conteggi seguenti provengono esclusivamente dalle successive API autenticate.

## 2. Contratti di lettura presenti sul router

Gli esempi del corpus usano v8 per LAN/login e v9 per Wi-Fi, mentre l'identificazione reale è 15.0. Non interpretare queste versioni di esempio come la versione installata. Costruire il client usando la versione scoperta e verificare i singoli endpoint; non assumere tutte le funzionalità funzionanti perché documentate.

| Funzione | Percorso documentato, senza fissare la versione | Uso proposto |
| --- | --- | --- |
| Configurazione LAN | `GET <base>/v<major>/lan/config/` | Nome/gateway/modalità; non presumere un prefisso /24. |
| Interfacce inventario | `GET <base>/v<major>/lan/browser/interfaces/` | Enumerare le interfacce effettive; oggi verificate `pub` e `wifiguest`. |
| Inventario | `GET <base>/v<major>/lan/browser/<interface>/` | Snapshot dei LanHost per interfaccia. |
| Dettaglio host | `GET <base>/v<major>/lan/browser/<interface>/<hostid>/` | Rilettura mirata o approfondimento. |
| Tipi host | `GET <base>/v<major>/lan/browser/types/` | Catalogo di tipi/categorie per icone; classificazione prudente. |
| Lease DHCP | `GET <base>/v<major>/dhcp/dynamic_lease/` | Assegnazioni IPv4, nomi e tempi; non presenza certa. |
| Access point | `GET <base>/v<major>/wifi/ap/` | Enumerare gli AP reali. |
| Stazioni Wi-Fi | `GET <base>/v<major>/wifi/ap/<id>/stations/` | Client associati e metriche, dopo verifica. |
| Stato switch | `GET <base>/v<major>/switch/status/` | Link delle porte; non assegnare una porta a un client senza un'associazione provata. |
| Eventi | WebSocket `<base>/v<major>/ws/event` | Cambi di raggiungibilità degli indirizzi, da sperimentare dopo l'inventario. |

Le letture relative a Wi-Fi riguardano client e AP del router, non una scansione radio. Il corpo `info` dell'host può contenere metadati già raccolti via mDNS, UPnP e DHCP: potrebbe rendere superfluo parte dell'arricchimento diretto dalla board. Fonte e freschezza vanno comunque conservate.

## 3. Semantica LanHost

| Campo | Significato documentato | Regola dashboard |
| --- | --- | --- |
| `id` | Unico sulla relativa interfaccia. | Chiave qualificata con UID box + interfaccia, legata all'ID interno; non assumere unicità globale. |
| `primary_name`, `primary_name_manual` | Nome principale e indicazione della scelta manuale. | Usare il nome del router; alias dashboard separato, senza rinominare il router. |
| `host_type` | Tipo stimato dal router o corretto dall'utente. | Icona/tipo riportato, non modello hardware certo. |
| `l2ident` | Identificatore di livello 2 e tipo. | Il corpus lo dichiara array; gli esempi e tutti i 39 host letti usano un oggetto. Normalizzare esplicitamente la forma verificata; forme inattese non diventano dati validi. |
| `vendor_name` | Produttore ricavato dal MAC. | Stima; MAC locali/privati non identificano il produttore con affidabilità. |
| `persistent` | Host conservato anche se mai attivo dal riavvio. | Appartenenza all'inventario storico; nessuna presenza attuale dedotta. |
| `reachable` | Host che può ricevere traffico dalla box. | «Raggiungibile secondo iliadbox», con ora della lettura e timestamp di riscontro. |
| `active` | Host che invia traffico alla box. | Attività secondo router, distinta dalla raggiungibilità. |
| `last_time_reachable` | Ultimo riscontro di raggiungibilità. | Non sostituirlo con il momento del nostro refresh. |
| `last_activity` | Ultima attività inviata dall'host. | Ora riportata dal router; non certifica uso da parte di una persona. |
| `first_activity` | Prima attività, oppure 0 per record precedenti all'introduzione del campo. | Zero significa non disponibile; non mostrare 1 gennaio 1970 o un'età inventata. |
| `names` | Nomi e fonte, come DHCP, mDNS e altre discovery. | Mantenere la provenienza; nome uguale non fonde due host. |
| `l3connectivities` | Indirizzi IPv4/IPv6, qualità e tempi per connessione; modello se noto. | Ogni indirizzo ha qualità propria; uno raggiungibile non rende attuali tutti gli altri. |
| `info` | Metadati raccolti sull'host. | Normalizzazione di campi utili, limiti di lunghezza e allowlist; niente dump integrale nel tema. |

Fonte: [LAN browser nella documentazione locale](http://192.168.1.254/doc/index.html#lan-browser-226). La semantica del contratto è ora leggibile; durata effettiva degli stati e comportamento acceso/sonno/scollegato restano da misurare.

## 4. Accesso applicativo ottenuto e sessioni verificate

La [documentazione locale Login](http://192.168.1.254/doc/index.html#login) descrive registrazione applicazione, conferma sul pannello della box, app_token persistente, challenge, HMAC-SHA1 e sessione temporanea con header `X-Fbx-App-Auth`.

Sequenza prevista: richiedere autorizzazione una sola volta, seguirne il risultato fino a granted/denied/timeout; salvare l'app_token in configurazione privata; leggere il challenge, calcolare la risposta e aprire/rinnovare una sessione. `SessionStart.password` è la risposta calcolata dal token e challenge, **non la password amministrativa**. Il login web verificato oggi non è il metodo proposto per il polling.

Il permesso `settings` è documentato per modificare impostazioni, mentre le letture restano disponibili all’app autenticata. Nel token ottenuto `settings=false`; la box ha però concesso automaticamente anche permessi per altri servizi: TV, explorer, contatti, chiamate, PVR, VM e downloader. **Le chiamate eseguite sono in sola lettura, ma il token non è limitato alla sola LAN.** Prima dell’integrazione stabile restringere i permessi dalla gestione applicazioni e verificare nuovamente le letture LAN; nessun permesso aggiuntivo è stato abilitato manualmente. Non chiamare PUT/PATCH/DELETE, Wake on LAN o endpoint di gestione Wi-Fi.

La [sezione HTTPS](http://192.168.1.254/doc/index.html#https-access) include CA ECC e RSA specifiche iliadbox per l'Italia e richiede validazione TLS. Prevedere trust circoscritto al client, verifica del nome/chain e confronto con UID atteso; non disabilitare la verifica certificati o importare CA globalmente nel sistema per comodità. Domini e porta vanno scoperti e provati dalla board; non applicare automaticamente il dominio Freebox francese degli esempi alla box italiana.

### Prova completata il 7 ottobre

- App: `it.smartpc.dashboard.network`, nome **SmartPC - Rete locale**, versione dichiarata `0.8-analysis`, dispositivo **SmartPC - preparazione dal PC**.
- `POST /api/v15/login/authorize/` → token e identificatore di tracking; conferma fisica dell’utente, poi `GET /login/authorize/<track_id>` → `granted`.
- Challenge e HMAC-SHA1 → prima sessione; lettura delle interfacce e degli inventari; logout.
- Seconda sessione aperta con lo **stesso app_token**, senza nuova conferma sul display; nuova lettura autenticata riuscita e logout. Le sessioni di verifica sono state chiuse.
- App_token persistente salvato fuori dal repository in `/home/giuseppe/.config/smartpc/iliadbox/app.json`, file `0600`, directory `0700`. Nessun session_token persistito; password amministrativa non necessaria per questo flusso e non conservata nei file dello studio. Il token resta valido finché non viene revocato.
- TLS locale su `192.168.1.254:443`, SNI/hostname dal discovery e CA del corpus locale, trust limitato al client. Python 3.14 rifiuta la chain vendor nel profilo X.509 strict per AKI mancante: usato il profilo compatibile Python 3.12, mantenendo `CERT_REQUIRED`, controllo hostname, firme, scadenze e chain. Nessun `CERT_NONE` o modifica al trust globale. Il bootstrap delle CA proviene dalla documentazione HTTP locale, non da un ancoraggio indipendente già installato: fissare le CA attese prima del provider stabile.

[Resoconto JSON della verifica](evidence/v08-iliadbox-study-2026-10-07/token-verification.json), senza token, nomi, MAC, indirizzi dei client o UID del router.

| Inventario API letto | Esito dello snapshot |
| --- | --- |
| `pub` | 39 record host; 13 `active=true` e 13 `reachable=true`, secondo la box. Non sono una certificazione di 13 apparecchi fisicamente accesi. |
| Campi utili `pub` | 38 host con nome, 38 con IPv4, 36 con IPv6; `l2ident` oggetto in tutti i record. Disponibili anche `access_point`, tempi, `names`, `info`, persistenza e vendor. |
| Contatore interfaccia `pub` | `host_count=54`, diverso dai 39 record restituiti. Conservare entrambi e segnalare la discrepanza; non creare 15 dispositivi, non presentare 54 come numero dei dispositivi osservati. Causa e completezza da verificare. |
| `wifiguest` | `host_count=0`, risposta inventario `success=true, result=null`. La collezione non è disponibile: non convertirla in lista vuota valida né dichiarare «nessun dispositivo». Attivazione/isolamento non verificati. |

Il primo verifier ha rilevato la risposta guest `null` come schema inatteso e chiuso la sessione; la seconda esecuzione la registra come inventario non disponibile, senza perdere il batch valido `pub`. Questo caso e la differenza dei conteggi diventano requisiti concreti del provider e della copertura UI. I conteggi sono uno snapshot dal PC, non un monitoraggio continuativo o una prova dalla Orange Pi.

## 5. Eventi WebSocket e scheduler

Nel completamento dello studio è stato provato l’handshake HTTPS autenticato (`101`) e il router ha accettato la registrazione dei due eventi LAN. Il socket e la sessione sono stati chiusi; non sono stati indotti cambi di presenza. [Evidenza](evidence/v08-iliadbox-study-2026-10-07/network-extra-capabilities.json).

Il corpus documenta `lan_host_l3addr_reachable` e `lan_host_l3addr_unreachable`, relativi alla raggiungibilità di un indirizzo IPv4/IPv6. Il secondo può indicare timeout o cambio IP; non è un evento affidabile di spegnimento dell'intero dispositivo. [Eventi WebSocket](http://192.168.1.254/doc/index.html#websocket-event-api).

Proposta: primo inventario completo via HTTP, poi eventuale WebSocket come accelerazione e rilettura mirata dell'host; mantenere una riconciliazione periodica completa. In assenza di sequenze/replay documentati non promettere consegna esattamente una volta. Dopo disconnessione/sessione scaduta o reboot router: reconnect con backoff, nuovo snapshot e recupero silenzioso. Nessun allarme derivato dalla semplice chiusura del socket.

Il ciclo HTTP ogni cinque minuti rimane una proposta sufficiente per iniziare N1. Prima confrontare il beneficio del WebSocket con complessità, stabilità e aggiornamenti reali; non ridurre il polling a un secondo per imitare eventi istantanei.

## 6. Metriche Wi-Fi e perimetro v0.8.1

`WifiStation` documenta associazione/BSSID, durata e inattività in secondi, contatori byte, rate in byte/s, segnale e statistiche del link. Le letture AP/BSS/stazioni e MLO config sono ora riuscite sul modello: due radio 2,4/5 GHz e 11 associazioni Wi-Fi con join all’inventario. La [mappa capacità/viste](v08-router-capabilities-and-views.md) documenta tipi reali, metriche e limiti. MLO delle stazioni, direzione rate, semantica segnale e roaming restano da provare.

- `rx_bytes`: byte ricevuti dal router dalla stazione; è upload del client verso la box. `tx_bytes`: byte dalla box verso la stazione; è download del client dal punto di vista della box.
- Il testo descrittivo di `tx_rate/rx_rate` non segue in modo evidente la direzione dei contatori. Provare con un trasferimento di direzione nota prima di etichettare upload/download; fino ad allora non inventare la direzione.
- `signal` è descritto come attenuazione in dB: non convertirlo automaticamente in RSSI dBm o percentuale di qualità. La semantica deve essere verificata con UI/valori reali.
- `last_rx/last_tx.bitrate` è descritto in decimi di Mbit/s, con -1 non disponibile; è velocità fisica del link, non banda Internet misurata. Gli oggetti di statistiche/flag sono marcati UNSTABLE nel corpus.
- Durata di associazione non è uptime del dispositivo; contatori possono azzerarsi al reconnect/riavvio. Delta negativi o cambio scope producono nuova baseline, non traffico negativo.

Sono opportunità concrete per v0.8.1, senza spostare implicitamente traffico e diagnostica estesa nel rilascio base. In v0.8 si può mostrare Wi-Fi/cavo soltanto con associazione verificata; assenza dall'elenco Wi-Fi non prova un collegamento cablato.

## 7. Revisione della raccomandazione

Per questa rete, **provare prima il provider iliadbox**: inventario già raccolto dal router, nomi/IPv6/riscontri e autenticazione dedicata documentati. Se il test autenticato dalla Orange Pi conferma schema, copertura e stabilità, il router diventa la fonte primaria; osservazioni locali Linux descrivono la board e fonti dirette LAN completano lacune misurate.

Questo può evitare helper raw, privilegi aggiuntivi e scansioni periodiche nel primo rilascio. La lettura autenticata dal PC conferma un inventario utile e due sessioni riutilizzabili; completezza, stabilità e significato della presenza restano condizionati alle prove N0.

N0 aggiornato:

1. Baseline della board e rete reale; nessuna maschera dedotta dal solo gateway.
2. Restringere i permessi del token già ottenuto; trasferire/configurare la credenziale privata soltanto nella fase board autorizzata e verificare HTTPS/sessione dalla Orange Pi.
3. Ripetere interfacce/inventario dalla board, provare i dettagli, spiegare `host_count` diverso dal numero di record e `result=null` guest; qualificare schema/campi reali.
4. Confrontare inventario noto con device acceso, in sonno e scollegato; verificare tempi di activity/reachability, IPv6 e MAC privati.
5. Decidere router primario, fallback diretto e necessità effettiva del helper; soltanto dopo fissare conteggi/presenza nella UI.

Evidenze attuali: documentazione locale, token/sessioni/HTTPS, inventario autenticato e successivo [catalogo completo con capacità e viste](v08-router-capabilities-and-views.md), letture Wi-Fi/porte/WAN/fibra/sensori/storico e registrazione WebSocket. Residui: permessi minimi e CA attese, Orange Pi, conteggi/guest null e copertura/transizioni fisiche, semantica rate/segnale Wi-Fi, MLO/roaming ed eventi dopo reconnect. Nessun software della dashboard modificato.
