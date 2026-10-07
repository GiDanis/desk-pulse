# v0.8 · Rete locale — consegna 0.8.0-rc.1

**7 ottobre 2026 · Europe/Rome · implementata e installata sulla Orange Pi.**

La dashboard legge l'inventario iliadbox dalla board e presenta Panoramica, Dispositivi, Dettaglio e Impostazioni Rete. La consegna è una candidata: il software, le letture reali, EGLFS e il reboot sono verificati; le transizioni fisiche acceso/sonno/scollegato e la copertura dei segmenti isolati restano da osservare. La v0.8.1 non faceva parte di questa consegna; la candidata successiva ha un [resoconto separato](v081-implementation-report.md).

## Comportamento consegnato

- Provider Python asincrono indipendente da Casa, con sessione HTTPS autenticata e logout per ciclo. Nessun agent sui computer e nessuna modifica alla configurazione della box.
- Inventario con identità derivate da router/interfaccia/host, indirizzi IPv4/IPv6, nomi e fonti, MAC e produttore quando attribuibile, riscontri e timestamps. Join Wi-Fi e porta qualificati; non attribuzione automatica di traffico o stato interno dei PC.
- Fino a quattro preferiti, ordine dal tastierino e alias locali tramite CLI/azione Theme. Nessun preferito reale scelto automaticamente. Senza preferiti la Panoramica mostra quattro identità dell'inventario.
- Filtri Tutti, Raggiungibili secondo box, Preferiti e Dati precedenti. Dettaglio per identità stabile anche quando un preferito viene rimosso o cambia il filtro.
- Polling ogni cinque minuti, refresh manuale nel menu comune con cooldown di 30 secondi, single-flight, pausa persistente e backoff dei guasti di trasporto. Errori di credenziale, identità, TLS o archivio sospendono il polling.
- SQLite privato transazionale: un ciclo o salvataggio fallito conserva lo snapshot precedente senza confermare dati nuovi. Al cold start la cache è precedente fino alla prima risposta valida; dopo scadenza il contatore corrente è `—`.
- Limite di 256 identità, riepilogo giornaliero e retention di 30 giorni. I preferiti mancanti restano consultabili come precedenti. Nessun grafico o banner Rete in questa prima consegna.

Il modulo compare dopo un inventario valido e rimane consultabile dalla cache. Il provider continua con modulo nascosto, salvo pausa esplicita. [Uso, tastierino, credenziale, alias e rollback](v08-network-operations.md).

## Fonte reale e limiti

La baseline installata era core **0.7.0-rc.3**, Theme API **2.2**, Apple Calm **1.2.0**; il checkout riportava 0.7.0. È stata conservata e verificata separatamente dalla nuova candidata. La board usa `wlan0`, IPv4 `192.168.1.179` e gateway `192.168.1.254`.

Sessioni e letture iliadbox sono riuscite dalla Orange Pi con il token già autorizzato. Dopo il reboot finale lo snapshot contiene **39 record pub**, **14 raggiungibili secondo la box** in quel ciclo. Il contatore dell'interfaccia indica **54** e l'inventario guest è nullo: la UI espone entrambe le limitazioni, senza trasformarle in 54 dispositivi presenti o in zero guest. Questi numeri descrivono l'acquisizione salvata, non un conteggio immutabile né una prova di presenza fisica.

L'inventario router è la fonte primaria della candidata. ARP, ICMP, mDNS, WebSocket e scansioni IPv6 non sono avviati. La perdita della sorgente produce cache precedente e un errore qualificato, senza una seconda fonte di presenza corrente. L'arricchimento opzionale può fallire senza invalidare un inventario valido; un inventario critico malformato non sostituisce il precedente.

Credenziale e archivio sono fuori da sorgenti, pacchetto e facade QML, con file 0600. HTTPS verifica catena, scadenza, hostname e UID atteso; le CA pubbliche del produttore sono incluse. È disabilitato soltanto `VERIFY_X509_STRICT` per la compatibilità delle CA senza AKI su Python 3.13. La password amministrativa non viene usata dal runtime. I permessi estranei a Rete concessi al token non vengono utilizzati; la loro riduzione resta da verificare nella box.

## Temi e compatibilità

Theme API **2.3** aggiunge quattro superfici (`network.overview`, `network.devices`, `network.detail`, `settings.network`), NetworkContext e DTO/model/azioni pubblici. Contratto generato: **53 superfici, 18 contesti**; fingerprint `c723fe97b5b5032fcc535c427544342770875bf01c6ae373856acd6a84521adc`.

Base ha la Panoramica a tessere, Functional una presentazione a righe. I bundle anteriori a Rete ricevono il fallback Base con lo stile del tema: Apple Calm 1.2.0 rimane immutato, digest `0f30f79c9ed959368df85cc498acb5698a687cdde60448a909136759d1116553`. La compatibilità accetta gruppi additivi completi conosciuti e continua a rifiutare coperture arbitrarie incomplete. [Kit AI aggiornato](artifacts/smartpc-theme-ai-kit-v08.zip).

Gli aggiornamenti del provider notificano i moduli senza riemettere cambi di aspetto. Sono corretti anche un callback del renderer dopo distruzione e il conteggio negativo transitorio del repeater durante il cambio filtro. La prova a freddo ha individuato un timeout del primo caricamento di Apple Calm: il solo primo Loader senza renderer corrente ha ora un budget di otto secondi; sostituzioni e readiness mantengono tre secondi. Dopo la correzione sono stati ripetuti i controlli mirati e un vero reboot mantenendo il tema originale.

## Verifica

| Livello | Risultato ed evidenza | Limite della prova |
| --- | --- | --- |
| Regressioni PC, Qt 6.8.2.1 | **67 controlli superati**, suite completa seguita da rerun mirati delle modifiche successive. [Indice finale](evidence/v08-implementation-2026-10-07/local-verification.json). | Non tutte le prove storiche sono state ripetute dopo ogni modifica; l'indice identifica il file dell'ultimo esito di ciascun controllo. |
| Protocollo/cache/identità | Sette gruppi di test: HMAC, UID/config, risposta invalida, IP riutilizzato, MAC locali, IPv6, guest nullo, persistenza/permessi/retention e bundle vecchi. | Trasporto sintetico isolato, non API reali. |
| Main e provider | Base/giorno e Functional/notte: 17 verifiche per profilo; errori e revoca, backoff, pausa, single-flight, salvataggio fuori dalla GUI, identità del dettaglio, filtri vuoti e 256 host. [Esito finale PC](evidence/v08-implementation-2026-10-07/local-selection-final.txt). | Comandi programmati, non tastierino fisico. |
| Orange Pi EGLFS 960×640 | Base/Functional superati; Apple Calm con cache reale di 39 record, quattro superfici e bundle immutato. Nessun warning QML raccolto. [Rendering](evidence/v08-implementation-2026-10-07/board-eglfs-final.txt). | Le catture con nomi LAN reali rimangono nell'area privata della board. La suite di rendering precede l'ultimo adeguamento del budget a freddo; quest'ultimo è verificato dal servizio e reboot finali. |
| SDK autonomo | Export senza stato privato, test Network core/UI superati. [Export](evidence/v08-implementation-2026-10-07/sdk-export-final.json), [core](evidence/v08-implementation-2026-10-07/sdk-core-final.txt), [UI](evidence/v08-implementation-2026-10-07/sdk-ui-final.txt). | Il kit non certifica un nuovo tema o la sua prestazione fisica. |
| Installazione | **475 file** confrontati con SHA-256 del manifest, servizio attivo, GUI pronta e snapshot reale fresco. [Ricevuta finale](evidence/v08-implementation-2026-10-07/install-receipt-final.json). | Manifest riferito a checkout modificato, commit base `1ecb2b728ca1f7454efecb844a97d1f0d02102f5`; nessun tag stabile creato. |
| Reboot reale finale | Boot ID cambiato; Apple Calm e preferenze conservati; servizio `active/running`, `NRestarts=0`, nessun warning QML dei pattern verificati, 39 record freschi. [Prima](evidence/v08-implementation-2026-10-07/pre-reboot-health.json), [dopo](evidence/v08-implementation-2026-10-07/post-reboot-health-final.json). | Reboot ordinato, non power-cut o cold start con LAN fisicamente assente. |

Il reboot finale passa da `cc08d7d3-df4d-4174-8e40-21f2d13f5091` a `4ff29e9f-4344-45bd-a59a-b77d01fae83f`. SHA-256 preferenze prima/dopo: `f266f144166e8e065ba1af4f830dbe06e5d22956b475c6ba98db6cd9cb59dc4a`. RSS GUI nell'ultimo controllo: **245864 KiB**; non è una misura GPU, un confronto prestazionale controllato o una prova di stabilità prolungata.

Verificatore e riscontro del reboot sono salvati anche in `/var/lib/smartpc-dashboard/v08-proof/`, fuori da `/tmp`. Il primo tentativo precedente alla correzione aveva mantenuto il recupero Base dopo un timeout: non viene contato come gate superato. I file intermedi nella cartella delle evidenze sono storici; valgono gli esiti finali collegati sopra.

## Backup e residui

Backup originale per rollback a rc.3: **`/var/backups/smartpc-before-v08-20261007T162020Z`**. Backup dell'ultima installazione candidata: `/var/backups/smartpc-before-v08-20261007T170119Z`. Stato/cache/credenziali private non sono esportati. Le preferenze e l'attivazione Apple Calm originali sono state ripristinate prima della distribuzione finale, conservando l'archivio Network acquisito.

N0 sorgente/baseline, N1/N2 provider/persistenza e N3 viste/temi sono consegnati; N5 ha distribuzione, hash e reboot verificati, con accettazione fisica ancora aperta. **N4 notifiche Rete è rinviato**, come previsto per la prima consultazione utile. Rimangono:

- confronto controllato di apparecchi accesi, in sonno e scollegati, MAC/IP variabili e segmenti isolati;
- perdita/ritorno fisico della LAN, avvio offline, IPv6 di un endpoint fisico qualificato, power-cut e uso prolungato;
- input del tastierino reale e eventuali misure ottiche di leggibilità/risposta;
- riduzione dei permessi effettivi del token, senza confonderla con la sola lettura del client;
- v0.8.1: viste iliadbox/Internet, Wi-Fi, Porte e grafici, con unità/reset/copertura da qualificare.

Le simulazioni verificano la gestione degli errori; non chiudono questi riscontri fisici. Quota/collaudi Casa e gate Live Sport mantengono il loro stato precedente.
