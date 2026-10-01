# v0.7 Casa · prova delle API Tuya

**1 ottobre 2026.** Percorso scelto: API cloud Tuya. Implementati `tuya_core.py`, client di sola lettura senza dipendenze aggiuntive, e `tuya_probe.py`, prova manuale. Token e rinnovo verificati sul cloud reale; lettura dispositivi impedita dal data center sospeso (`28841107`). [Risultati e prove ancora necessarie](v07-tuya-live-analysis.md). Schermata Casa, preferiti, scheduling e riconnessione automatica dopo un'interruzione di rete restano da integrare. Nessun comando ai dispositivi.

## Collegamento iniziale

La sola app Smart Life non autorizza il nostro client. Serve un progetto sviluppatore, distinto dall'account dell'app:

1. Creare un account su [Tuya Developer Platform](https://platform.tuya.com/).
2. Aprire **Cloud → Cloud Project → Project Management** e creare un progetto, per esempio `SmartPC Casa`, con **Development Method: Smart Home**. Verificare il data center corrispondente all'account Smart Life.
3. Verificare disponibilità, scadenza e quota di **IoT Core**, con servizi autorizzati al progetto. La guida Tuya elenca anche **Smart Home Basic Service**; controllare nell'API Explorer che le API sotto siano disponibili. Valutare la Trial Edition se offerta: la prova non richiede un acquisto, ma non è dimostrato un accesso gratuito permanente. [Procedura ufficiale](https://developer.tuya.com/en/docs/developer/apply-cloud-api-key?id=Kff30z8sv62ah), [piani IoT Core](https://developer.tuya.com/en/docs/iot/membership-service?id=K9m8k45jwvg9j).
4. Nel progetto: **Devices → Link App Account → Add App Account → Tuya App Account Authorization**. Scansionare il QR con Smart Life e autorizzare. Lasciare **Automatic Link**, predefinito nella guida Tuya. Non occorre riassociare i dispositivi. Annotare l'**UID dell'account collegato**, poi controllare **All Devices**. [Collegamento documentato](https://developer.tuya.com/en/docs/developer/apply-cloud-api-key?id=Kff30z8sv62ah).
5. Recuperare **Client ID** e **Client Secret** da **Authorization Key**. Inserirli soltanto nel file privato sotto, senza inviarli in chat.




Confrontare l'elenco API con l'app: dispositivi condivisi, hub e modelli particolari richiedono verifica. Non è ancora provato che tutte le funzioni dell'app siano esposte dall'API.

## Configurazione privata sul PC

Configurazione in `/home/giuseppe/.config/smartpc/tuya-cloud.json`, fuori dal progetto, con permessi `600`. Client ID e Client Secret forniti dall'utente sono già stati trasferiti qui; anche Central Europe e l'UID sono configurati. Il blocco attuale è la risposta di data center sospeso, non un campo mancante:

| Campo | Valore dalla console |
| --- | --- |
| `endpoint` | URL API del data center del progetto/account, senza slash finale |
| `access_id` | Client ID / Access ID |
| `access_secret` | Client Secret / Access Secret |
| `uid` | UID nella pagina dell'account Smart Life collegato, non il Client ID |

Endpoint europei: `https://openapi.tuyaeu.com` per **Central Europe**, `https://openapi-weaz.tuyaeu.com` per **Western Europe**. Verificare il data center dove compare l'account anziché dedurlo dalla sola residenza. Il client accetta soltanto gli endpoint ufficiali della [struttura delle richieste Tuya](https://developer.tuya.com/en/docs/iot/api-request?id=Ka4a8uuo1j4t4).

Il file deve restare privato, regolare e non un collegamento simbolico. Token, risposte grezze, local key, IP e coordinate non vengono persistiti. La cache salva soltanto elenco normalizzato, data e impronta del progetto/account, per non riutilizzare dati di un altro account. Credenziali mai nel QML o nel repository. Nessuna credenziale è stata trasferita sulla Orange Pi; la configurazione di produzione verrà definita dopo questa prova.

## Comandi di prova

Controllo formato senza rete:

```bash
python3 /home/giuseppe/Documenti/Workspace/SmartPC/dashboard/tuya_probe.py --check-config
```

Acquisizione completa dell'elenco:

```bash
python3 /home/giuseppe/Documenti/Workspace/SmartPC/dashboard/tuya_probe.py
```

Il terminale mostra nomi, indici e disponibilità secondo Tuya, senza identificativi o chiavi. Per specifiche e ultimi stati riportati di massimo quattro dispositivi:

```bash
python3 /home/giuseppe/Documenti/Workspace/SmartPC/dashboard/tuya_probe.py --device-index 1 --device-index 2
```

Gli indici sono temporanei: controllare i nomi del nuovo elenco. I futuri preferiti useranno gli identificativi stabili. Valori senza tipo/scala verificabili restano «Dato da verificare», mai zero o spento. Una risposta riuscita rappresenta l'ultimo stato riportato dal cloud, non la raggiungibilità fisica istantanea.

Cache: `~/.cache/smartpc/tuya-inventory.json`, oppure sotto `XDG_CACHE_HOME`. Una pagina e due dispositivi richiedono normalmente **6 chiamate**: token, elenco, specifiche e stato per ciascuno. Il token è riutilizzato/rinnovato in memoria durante l'esecuzione; ogni nuovo avvio del probe lo acquisisce nuovamente. Nessun timer avvia richieste in background.

## Aggiunte e modifiche nell'app

Con Automatic Link il comportamento atteso è associare il dispositivo in Smart Life e ritrovarlo nel progetto; va verificato con un'aggiunta reale. Il probe scopre l'elenco a ogni esecuzione. Nella dashboard il provider farà la stessa lettura periodicamente e su richiesta.

| Operazione | Gestione prevista nella dashboard |
| --- | --- |
| Aggiunta | Compare nell'elenco dopo una sincronizzazione completa; scegli tu se inserirlo nelle quattro tessere |
| Rinomina | Nome aggiornato, selezione conservata se l'identificativo è uguale |
| Rimozione | Selezione non disponibile dopo una risposta completa valida; vecchi stati non presentati come attuali |
| Nuova associazione / sostituzione | Se cambia identificativo è un dispositivo nuovo da selezionare; nessuna migrazione soltanto per nome |
| Errore rete / quota / accesso | Ultimo elenco conservato come precedente; errori non interpretati come rimozioni |

Il probe implementa già confronto aggiunti/rimossi/rinominati e isolamento della cache per account. Preferiti e sincronizzazione periodica restano da sviluppare. Un elenco vuoto cancella il precedente solo se valido e completo; una paginazione interrotta conserva la cache.

## API e limiti

- Inventario per UID: `GET /v1.3/iot-03/devices`, `source_type=tuyaUser`, `source_id=UID`, con tutte le pagine. [Inventario](https://developer.tuya.com/en/docs/cloud/dc413408fe?id=Kc09y2ons2i3b).
- Tipo, scala e unità: `GET /v1.2/iot-03/devices/{device_id}/specification`. [Specifiche](https://developer.tuya.com/en/docs/cloud/85b8f49180?id=Kb5rg8mvrccb7).
- Stato: `GET /v1.0/iot-03/devices/{device_id}/status`. [Stati](https://developer.tuya.com/en/docs/cloud/1ef1a3044b?id=Kconf2usgnfwo).
- [Firme ufficiali](https://developer.tuya.com/en/docs/iot/new-singnature?id=Kbw0q34cs2e5g), timeout 12 secondi, limite risposta 2 MiB, redirect rifiutati. Token non valido: una sola ri-autenticazione e ripetizione della GET. Rete e quota non producono cicli di retry nel probe.

Con errore `1106`, controllare servizi, UID e data center nell'API Explorer. Un token ottenuto non prova il permesso di leggere dispositivi. `429` segnala il limite HTTP; limiti di servizio possono arrivare come altri codici API. Nessun fallback silenzioso su tutti gli utenti del progetto.

Dimensionare il polling sulla quota effettiva: un elenco di una pagina ogni cinque minuti consuma **8.640 richieste in 30 giorni**, escluse letture degli stati e token. Quattro GET di stato al minuto consumerebbero da sole **172.800 richieste**. La frequenza continua non è ancora scelta; le specifiche potranno avere una cache distinta dagli stati.

## Verifiche e prossimo passo

`check_tuya.py`: **21 controlli superati sul PC e 21 sulla Orange Pi** il 1 ottobre 2026, più verifica di sintassi Python sul PC. Coprono vettori pubblici delle firme, paginazione, token, cache atomica, isolamento account, errori e sensori, inclusa la nuova diagnosi di data center sospeso. Sulla board sono stati eseguiti in una directory temporanea senza modificare il kiosk, con risposte simulate. Separatamente, **token e rinnovo sono verificati sul cloud reale**; accesso ai dispositivi, compatibilità, rendering e affidabilità della v0.7 restano non verificati. Nessuna misura RAM, FPS o latenza degli stati dei dispositivi eseguita in questa fase.

Con l'account configurato: confrontare luce, presa e sensore Zigbee con l'app; cambiare stato fisicamente/dall'app; misurare ritardo e disponibilità con dispositivo disalimentato; provare aggiunte/rinomine/rimozioni. Poi integrare worker Qt, selezione persistente, quattro tessere, backoff, offline e reboot senza rete.

Il probe non è avviato dal kiosk e non cambia il servizio dashboard. Per rimuoverlo eliminare i tre file Python dedicati e, se desiderato, configurazione/cache private. Nessun servizio aggiunto da disabilitare.
