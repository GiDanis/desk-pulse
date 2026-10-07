# v0.8 · Uso e gestione Rete locale

La prima consegna è `0.8.0-rc.1`. Il provider legge la iliadbox dalla Orange Pi e conserva un inventario privato. Non occorrono agent sui PC. Le viste estese router, Wi-Fi, porte e grafici rimangono nella v0.8.1; le notifiche Rete non sono abilitate in questa prima consegna N0–N3.

## Navigazione

Rete entra nel carosello dopo il primo inventario valido. Rimane consultabile con dati salvati e senza preferiti. Panoramica mostra fino a quattro preferiti; prima della scelta mostra quattro identità dell'elenco. Non equivale a quattro dispositivi presenti fisicamente.

- **2/8:** selezione; **2** dalla prima riga sposta il focus alle schede.
- Con il focus sulle schede, **4/6** alterna Panoramica/Dispositivi e **5** cambia filtro. Nell'elenco: Tutti, Raggiungibili secondo box, Preferiti, Dati precedenti.
- **5** sul dispositivo apre Identità, Indirizzi, Collegamento e Riscontri. **4/6** cambia scheda, **2/8** scorre, **5** aggiunge/rimuove un preferito.
- Menu → Impostazioni → **Rete locale**: scegliere fino a quattro preferiti, ordinarli con **4/6**, sospendere la raccolta e rileggere la configurazione.
- Menu → Impostazioni → **Dati e aggiornamenti → Rete locale**: aggiornamento manuale, con singolo ciclo alla volta e intervallo minimo di 30 secondi.

La raccolta automatica avviene ogni cinque minuti, anche con modulo nascosto. Sospenderla conserva il dato e continua a farlo invecchiare; al riavvio non parte una raccolta automatica se era stata sospesa. Un errore di trasporto conserva lo snapshot e ritenta con attesa crescente fino a 30 minuti. Autorizzazione, identità, TLS e archivio non validi sospendono il polling; la lettura manuale o la rilettura di una configurazione valida permettono il recupero.

## Dati e copertura

`Raggiungibile secondo box` è un riscontro del router nell'ultimo ciclo valido. Un dato salvato non diventa attuale perché il dispositivo è selezionato o perché la rete sembra disponibile. Il contatore corrente diventa `—` se il ciclo non è valido/fresco. Anche la cache appena caricata al riavvio è precedente fino a una nuova risposta.

Il dettaglio conserva IP IPv4/IPv6, MAC, nome e relativa fonte, tipo/produttore riportati, timestamps della box e prima osservazione locale. Il produttore non è attribuito ai MAC locali. Il Wi-Fi richiede una stazione associata e identità/MAC corrispondenti; una porta dello switch può avere più dispositivi a valle. `Visto da porta` non significa necessariamente collegamento diretto.

Le prove reali hanno restituito 39 record `pub`, a fronte di 54 nel contatore della box. `wifiguest` ha restituito un inventario nullo: **non è un elenco di zero host**. Questi limiti appaiono nella copertura. Nessuna scansione ARP, ICMP o mDNS viene avviata da questa candidata; eventuali altre fonti richiedono riscontri separati. CPU, RAM, GPU e stato interno dei PC non sono disponibili da questo inventario.

## Credenziale e archivio

Il servizio usa:

- `/var/lib/smartpc-dashboard/.config/smartpc/iliadbox/app.json`: `router`, `router_uid`, `api_domain`, `app_id`, `app_token`; file **0600**, directory iliadbox **0700**. La password amministratore non serve al runtime.
- `/var/lib/smartpc-dashboard/.local/state/smartpc/network/<scope>.sqlite3`: snapshot, preferenze e riepilogo giornaliero privati, file **0600**, directory **0700**. Scope derivato dall'identità del router; gli ID includono anche interfaccia e ID host, non il solo IP.
- Credenziale, identificatori grezzi dell'API e session token non sono consegnati ai temi. Il client apre una sessione per ciclo, usa HMAC-SHA1 richiesto dalla box e tenta il logout; una sessione non viene mai salvata.

HTTPS verifica catena, scadenza e hostname tramite le CA pubbliche del produttore incluse nel runtime. La discovery verifica l'UID salvato e determina la versione API; l'indirizzo di destinazione rimane locale. Il profilo Python disabilita solo `VERIFY_X509_STRICT`, per le CA del produttore prive di AKI; verifica certificati e hostname rimangono obbligatorie.

Gli endpoint di inventario e arricchimento sono letti con GET. I soli POST sono sessione e logout. Non vengono modificati SSID, dispositivi, porte, WAN o configurazione della box. Il token autorizzato espone anche permessi estranei a Rete: questa candidata non li usa. La riduzione dei permessi effettivi rimane da verificare nell'amministrazione della box; un token aggiuntivo non può superare i permessi concessi dal router.

Snapshot e preferenze sono transazionali. Un salvataggio fallito non conferma l'acquisizione né una modifica dei preferiti. Storico giornaliero e identità non più riportate hanno retention di 30 giorni; i preferiti mancanti rimangono come precedenti, entro il limite complessivo di 256 identità. I grafici dello storico non fanno parte della v0.8.

## Alias locali

La dashboard permette preferiti e ordine dal tastierino. Gli alias liberi sono locali e non rinominano l'host sul router. Per configurarli da SSH, fermare il servizio per evitare modifiche concorrenti, elencare gli ID e poi salvare l'alias:

```bash
sudo systemctl stop smartpc-dashboard
python3 /opt/smartpc/dashboard/network_admin.py --config /var/lib/smartpc-dashboard/.config/smartpc/iliadbox/app.json --state-dir /var/lib/smartpc-dashboard/.local/state/smartpc/network
python3 /opt/smartpc/dashboard/network_admin.py --config /var/lib/smartpc-dashboard/.config/smartpc/iliadbox/app.json --state-dir /var/lib/smartpc-dashboard/.local/state/smartpc/network --identity ID --alias 'Computer studio'
sudo systemctl start smartpc-dashboard
```

Un alias vuoto rimuove la personalizzazione. Il tema può proporre un editor usando l'azione pubblica `network.alias.set`; l'esito arriva dopo il salvataggio. Non è stato introdotto un editor di testo sul tastierino a nove tasti.

## Temi, verifica e rollback

Theme API **2.3** aggiunge `NetworkContext`, DTO/model e quattro superfici. Base e Functional hanno presentazioni dedicate; i bundle anteriori a Rete ricevono il fallback Base con il proprio stile. Sono ammessi solo gruppi completi di superfici additive riconosciute: una copertura incompleta arbitraria resta un errore. ZIP, manifest e hash dei temi importati non vengono riscritti.

I test `check_network.py` e `check_network_ui.py` usano dati e trasporti sintetici in aree isolate; non interrogano il router e non leggono il token reale. Il resoconto di consegna distingue queste prove da inventario vivo, rendering EGLFS e reboot.

Il backup originale precedente alla candidata è indicato nel report. Per rollback fermare il servizio, ripristinare la cartella `dashboard` del backup in `/opt/smartpc/dashboard` e riavviare il servizio. Il backup `state` contiene anche credenziali private: non va esportato o incluso nei pacchetti. Stato Rete e preferenze possono essere conservati quando si ripristina soltanto il runtime.
