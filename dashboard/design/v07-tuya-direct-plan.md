# SmartPC · v0.7 Casa · proposta semplificata con cloud Tuya diretto

**Revisione:** 1 ottobre 2026. **Decisione approvata:** procedere con API cloud Tuya dirette. **Stato:** client di lettura e probe implementati; token/rinnovo, inventario di 16 dispositivi, protocolli e letture su quattro dispositivi verificati sul cloud reale. UID e firma dei cursori corretti; 22 controlli offline superati su PC e board. Schermata Casa, collaudo fisico e provider periodico ancora da sviluppare. [Configurazione](v07-tuya-api-setup.md), [analisi reale](v07-tuya-live-analysis.md).

## Decisione di lavoro

**Collocazione nel piano del 2 ottobre:** v0.7 ancora in analisi e prototipo della sorgente, dopo il Theme Engine v0.6.6 proposto. Il [MasterPlan dei rilasci](release-masterplan.md) descrive implementazione periodica, budget, UI e prove fisiche necessari al rilascio. L'esistenza del probe non equivale a Casa integrata.

Sviluppare un piccolo provider Python che collega SmartPC direttamente al cloud Tuya. Home Assistant rimane un'alternativa. Il risultato di prodotto resta quello del MasterPlan: poche tessere leggibili, ultimi stati riconoscibili, riconnessione automatica e nessuna falsa conferma. Il primo passo implementato è la prova OpenAPI senza dipendenze aggiuntive.

```text
SmartPC / provider Python ↔ cloud Tuya ↔ dispositivi Wi-Fi o hub Zigbee
                               ↕
                          app Smart Life
```

Il cloud può fornire dati dei dispositivi già associati all'account, se autorizzati ed esposti dall'API scelta. Modelli, hub e funzioni restano da verificare. Il collegamento Zigbee fisico resta gestito dal suo hub; il provider non comunica direttamente con la radio Zigbee.

## Due percorsi da distinguere

### A. OpenAPI del progetto cloud

Tuya documenta la creazione di un progetto, Client ID/Secret, abilitazione dei servizi e collegamento dell'account Smart Life via QR. [Procedura ufficiale](https://developer.tuya.com/en/docs/developer/apply-cloud-api-key?id=Kff30z8sv62ah).

È documentata, per esempio, la lettura dello stato tramite `GET /v1.0/iot-03/devices/{device_id}/status`, con coppie codice/valore. [API stato](https://developer.tuya.com/en/docs/cloud/1ef1a3044b?id=Kconf2usgnfwo).

L'accesso sviluppatore è distinto dall'uso dell'app. IoT Core ha piani, quote e una Trial Edition: non presumere API gratuite senza scadenza o rinnovi. Verificare nel progetto durata effettiva, servizi e quota; non sottoscrivere un piano a pagamento per la prova. Il polling va dimensionato sulla quota residua. [Pricing ufficiale](https://developer.tuya.com/en/docs/iot/membership-service?id=K9m8k45jwvg9j).

### B. Tuya Device Sharing SDK

Il progetto ufficiale è un SDK Python con elenco dispositivi, aggiornamenti, listener e comandi. Il codice del manager usa un `client_id` e informazioni di autorizzazione: non richiede un processo Home Assistant in esecuzione. [SDK Tuya](https://github.com/tuya/tuya-device-sharing-sdk), [manager](https://github.com/tuya/tuya-device-sharing-sdk/blob/main/tuya_sharing/manager.py).

Questo rende plausibile un provider autonomo, ma non dimostra che il percorso di autorizzazione previsto per Home Assistant sia disponibile a un'app arbitraria. Verificare come ottenere un'identità client SmartPC consentita e quali condizioni si applicano; non considerare il riuso del client ID Home Assistant una soluzione pubblica già approvata. La disponibilità del codice e la licenza SDK non equivalgono all'accesso al servizio cloud.

## Prova minima prima della UI

1. Collegare il progetto OpenAPI all'account Smart Life e verificare servizi, quota e scadenza. Il percorso scelto è OpenAPI; Sharing SDK resta una ricerca alternativa. La prova richiede configurazione dell'utente, senza password o secret in chat.
2. Leggere elenco, modello e stato di una luce e una presa effettivamente presenti, più un sensore o sottodispositivo Zigbee se disponibile. Registrare dati realmente esposti e unità.
3. Cambiare stato dall'app o dal pulsante fisico; misurare ricezione, disponibilità e comportamento con dispositivo disalimentato.
4. Provare rinnovo token, perdita/ripristino della rete, riavvio del provider e quota/servizio non disponibili.
5. Confermare sostenibilità del percorso con autorizzazione, costo e manutenzione effettivi; se non accettabili riesaminare le alternative.

Risultato atteso della prova: inventario normalizzato e due/tre dispositivi con variazioni osservate. Uno script che legge una risposta una sola volta non conclude la verifica di affidabilità.

## Implementazione ridotta proposta dopo la prova

Provider `tuya_core.py` / `tuya.py` con lavoro di rete in background e stato normalizzato `casaState`; cache atomica solo per dispositivi scelti; credenziali nel backend fuori dal progetto/QML. Nessun Docker, database Home Assistant o rete Zigbee nuova necessari per questo percorso.

Schermata `CasaView.qml`: massimo quattro tessere con nome, icona, testo e stato del dato. Dettaglio con provenienza e ultimo stato ricevuto. Riutilizzare navigazione, involucro dei moduli e impostazioni esistenti.

Resta necessaria la gestione di autenticazione, rinnovo token, codici dei dispositivi, timeout, retry e disponibilità: meno infrastruttura, ma parte dell'adapter che Home Assistant gestiva passa al nostro software. Usare l'SDK/API scelto per evitare di reinventare il protocollo.

Il dato cloud resta «ultimo stato riportato»: una chiamata riuscita non prova la raggiungibilità fisica istantanea del dispositivo. Offline del provider, disponibilità del dispositivo e cache devono restare distinti; valori mancanti mai convertiti in zero o «spento». Nessun comando nel primo rilascio; eventuali azioni nominate richiedono riscontro e collaudo fisico.

## Uscita dalla v0.7

- Stati confrontati con dispositivi reali e app, inclusi almeno un Wi-Fi e un Zigbee se presenti nella selezione.
- Nessun blocco del rendering; animazioni misurate su EGLFS con acquisizione attiva.
- Riconnessione e rinnovo token provati; quota esaurita e autorizzazione revocata riconoscibili.
- Cache precedente evidente, recupero dopo reboot senza rete e nessuna falsa conferma.
- Fonti, dipendenze, configurazione e rollback documentati.

**Prossimo passaggio:** confrontare stati e variazioni con Smart Life e dispositivi fisici, verificare quota/scadenza e integrare provider/UI. Il client gestisce inventario paginato, token, specifiche/stati e cache atomica normalizzata; l'accesso reale è ora verificato. La v0.7 resta in sviluppo.

**Proposta di economia delle chiamate:** verificata una risposta Smart Home cumulativa con disponibilità e stati dei dispositivi selezionati. Per il provider valutare questo adapter e specifiche in cache, evitando GET separate a ogni tessera. Base cinque minuti, un minuto durante consultazione con budget; [calcoli e policy proposta](v07-tuya-polling-budget.md). Scheduling non ancora implementato.
