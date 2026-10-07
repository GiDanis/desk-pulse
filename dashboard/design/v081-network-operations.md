# v0.8.1 · Consultare router, Wi-Fi e porte

Le nuove viste sono nella famiglia **Rete**. In Panoramica seleziona l’intestazione (2 dalla prima tessera) e premi **5** per gli Approfondimenti. Puoi anche toccare «APPROFONDIMENTI» o aprire le tre voci da **Impostazioni / Rete**. Base e Functional condividono gli stessi dati; un tema precedente usa il fallback Base nello stile del tema.

- **iliadbox / Internet:** Stato con traffico WAN, capacità riportata, firmware, uptime, sensori del router, potenza ottica e stato update/standby. Storico WAN, temperature o ventola, nelle finestre 1 h e 24 h.
- **Wi-Fi:** scegli una radio, poi una stazione. Il dettaglio distingue segnale raw in dB, ultimo link riportato, durata dell’associazione, contatori e traffico LAN ricavato dai delta. Il record LAN si apre solo con un join verificato di host ID e MAC.
- **Porte Ethernet:** scegli una porta per statistiche aggregate, host visti e storico RX/TX. Una porta con link down non conserva una falsa velocità attuale. Più MAC possono appartenere a uno switch a valle.

**2/8** selezionano righe, **5** apre, **4/6** cambiano scheda, **7** torna indietro, **1/9** conservano Home/menu. Nello storico **2/8** alternano 1 h/24 h; **5** alterna WAN, temperatura e ventola nella vista router. I grafici delle porte mantengono RX/TX della porta selezionata. Per cambiare entità torna a Radio/Porte e sceglila dall’elenco. La selezione LAN torna al punto precedente dopo un approfondimento.

**Aggiorna** richiede un refresh manuale; nelle sezioni con righe è disponibile anche una riga selezionabile dal tastierino. Il cooldown è 30 s: una richiesta rifiutata o accodata non certifica dati nuovi. La pausa della raccolta nelle Impostazioni ferma anche le nuove acquisizioni automatiche; la richiesta manuale rimane disponibile. Un errore di autorizzazione richiede il recupero tramite Aggiorna inventario o Rileggi configurazione in Impostazioni / Rete.

## Frequenze, dati precedenti e limiti

Inventario e preferiti mantengono il ciclo **300 s**. Le metriche aggiuntive sono raccolte solo con un approfondimento visibile, a **30 s**; metadati radio/router fino a **600 s**, RRD almeno **60 s** tra acquisizioni della stessa finestra. Non esiste uno storico locale continuo per le stazioni quando la pagina era chiusa.

Una fonte in errore conserva il proprio ultimo dato con **PRECEDENTE**. Il grafico salvato conserva le date effettive, senza spostare l’asse al presente. Il cold start tratta tutte le metriche salvate come precedenti; il nuovo inventario non rende automaticamente attuali le metriche. Reset, cambio associazione, intervallo troppo lungo o clock invertito annullano il rate derivato: il valore diventa non disponibile fino alla nuova baseline.

La capacità riportata non è uno speed test. Traffico WAN, LAN per stazione e aggregato porta sono livelli distinti. Sensori e ventola sono quelli della iliadbox, non della Orange Pi. Non sono esposti consumo mensile per host, presenza fisica certa, MLO simultaneo o occupazione canale non qualificata. La consultazione non cambia Wi-Fi, porte, firmware o configurazione del router.

## Archivio e recupero

Il token già autorizzato rimane nel file privato descritto nelle [operazioni v0.8](v08-network-operations.md). Le nuove fonti non richiedono un secondo token. Nessuna password amministratore entra nel runtime.

L’inventario rimane in `~/.local/state/smartpc/network/`; le metriche sono in un SQLite complementare `~/.local/state/smartpc/network-metrics/<scope>.sqlite3`, file 600 e cartella 700. Le finestre sono limitate a 10.000 punti raw e 180 punti pubblici per serie, massimo due serie visibili. Payload cache massimo 8 MiB; entità ritirate vengono eliminate dalla cache e la lettura valida precedente dell’inventario rimane disponibile se l’archivio metriche è corrotto.

La consegna salva ricevuta e verifier in `/var/lib/smartpc-dashboard/v081-proof/`; il backup comprende runtime, configurazione e cache sotto `/var/backups/smartpc-before-v081-…`. Per il rollback usa il percorso esatto della ricevuta: ferma il servizio, ripristina la cartella `dashboard` del backup in `/opt/smartpc/dashboard`, poi riavvia il servizio. La versione v0.8 ignora il nuovo archivio complementare; non è necessario eliminare credenziali o preferenze. [Prove e ambito della candidata](v081-implementation-report.md).
