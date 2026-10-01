# SmartPC · ricerca v0.7 Casa · Smart Life, Tuya e Home Assistant

> **Aggiornamento del 1 ottobre 2026:** è stata aggiunta la [valutazione del cloud Tuya diretto](./v07-tuya-direct-plan.md), ora prioritaria per la prova minima. Home Assistant resta un'alternativa, anziché un prerequisito.

**Data:** 1 ottobre 2026. **Stato:** ricerca documentale verificata sul web; nessuna integrazione installata e nessun dispositivo dell'utente collaudato. Piano operativo: [v07-home-assistant-plan.md](./v07-home-assistant-plan.md).

**Impianto confermato dall'utente:** Home Assistant non è installato; i dispositivi sono già comandabili da remoto attraverso l'app. Sono presenti dispositivi Wi-Fi e Zigbee. L'utente chiede di valutare Home Assistant sulla stessa Orange Pi; modelli e hub Zigbee restano da identificare.

## 1. Percorso iniziale consigliato

SmartPC diventa un client di Home Assistant sulla rete domestica. Home Assistant gestisce i dispositivi; SmartPC presenta soltanto le entità selezionate. Iniziare con l'integrazione Tuya inclusa in Home Assistant e valutare collegamenti locali per i modelli che ne traggono beneficio. È una proposta di progetto, subordinata all'inventario reale.

```text
Dispositivi Tuya ↔ cloud Tuya ↔ integrazione Tuya in Home Assistant
                                     ↓ API sulla LAN
                            provider Python SmartPC → QML
Smart Life continua a usare l'account e i dispositivi già associati.
```

Con un'integrazione locale compatibile, il primo collegamento diventa dispositivo ↔ Home Assistant sulla LAN. Il contratto SmartPC resta lo stesso: evita di legare la grafica a uno specifico produttore.

## 2. Integrazione Tuya inclusa in Home Assistant

La configurazione corrente usa il **User Code** dell'account Smart Life e un **QR** da scansionare con l'app. Il codice si trova in Profilo → Impostazioni → Account e sicurezza. I nuovi dispositivi aggiunti nell'app richiedono il ricaricamento dell'integrazione. La classe dichiarata è **Cloud Push**. L'SDK non espone tutte le funzioni presenti nell'app: disponibilità di sensori, consumi e funzioni va verificata per dispositivo. [Documentazione Tuya di Home Assistant](https://www.home-assistant.io/integrations/tuya/).

Per il nostro prodotto: mantenere l'account esistente; verificare prima che ciascun dato desiderato compaia in Home Assistant. Una presa riconosciuta come interruttore non implica che esponga anche watt e kWh. L'etichetta «presa PC alimentata» non significa «PC acceso»: lo stato del computer appartiene alla v0.8.

Le vecchie guide con progetto IoT, Access ID e secret descrivono percorsi differenti. Il repository storico Tuya v2 dichiara che quel progetto non è più mantenuto dal team Tuya e rimanda all'integrazione di Home Assistant. Non usare la sua configurazione come procedura iniziale corrente. [README del progetto storico](https://github.com/tuya/tuya-home-assistant).

## 3. Alternative e condizioni d'impiego

| Percorso | Cosa offre | Condizione per SmartPC |
| --- | --- | --- |
| Tuya inclusa in Home Assistant | Collegamento all'account Smart Life tramite cloud | Prima prova proposta; verificare stati, latenza e perdita di Internet |
| Tuya Local, progetto `make-all/tuya-local` | Collegamento locale soprattutto Wi-Fi | Candidato per modelli compatibili e dati mancanti nel cloud |
| LocalTuya, progetto `rospogrigio/localtuya` | Collegamento locale con configurazione dei datapoint | Alternativa da valutare per un modello preciso |
| ZHA / Zigbee2MQTT | Rete Zigbee con coordinatore compatibile | Solo se i dispositivi sono Zigbee e si decide una migrazione |
| Matter | Collegamento attraverso il protocollo Matter | Solo per dispositivi o bridge che lo supportano effettivamente |

**Tuya Local:** richiede indirizzo, device ID e local key; propone anche recupero assistito tramite Smart Life. La chiave cambia dopo un nuovo abbinamento. Documenta limiti per hub, connessioni locali simultanee e sensori a batteria senza hub. Alcuni firmware possono avere problemi dopo una lunga assenza del cloud: «locale» richiede comunque una prova WAN interrotta. [Documentazione del progetto](https://github.com/make-all/tuya-local).

**LocalTuya è un progetto distinto.** Offre aggiornamenti push locali, supporto energetico per dispositivi compatibili e cloud opzionale per reperire le chiavi. La configurazione include la mappa dei datapoint; il README contiene anche riferimenti a vecchi percorsi cloud, da non trasferire alla Tuya inclusa in Home Assistant. [Documentazione LocalTuya](https://github.com/rospogrigio/localtuya).

**Zigbee:** ZHA richiede un coordinatore supportato; dispositivi non conformi possono richiedere handler specifici. L'eventuale riabbinamento va pianificato perché cambia la rete che gestisce il dispositivo. Non presumere che resti contemporaneamente sul vecchio hub Smart Life. [Documentazione ZHA](https://www.home-assistant.io/integrations/zha/).

**Matter:** supporta l'associazione dello stesso dispositivo a più controller. Essere compatibile Tuya non rende automaticamente un dispositivo Matter. Valutare funzioni effettivamente esposte e requisiti di rete se il modello o il bridge lo supporta. [Documentazione Matter](https://www.home-assistant.io/integrations/matter/).

## 4. Dove eseguire Home Assistant

Home Assistant propone oggi **OS** e **Container**; OS è la scelta consigliata per semplicità di gestione, anche in VM. Container richiede gestione autonoma dell'host e non include il sistema di app aggiuntive. [Installazione ufficiale](https://www.home-assistant.io/installation/), [guida Linux](https://www.home-assistant.io/installation/linux/).

**Direzione richiesta: valutare Home Assistant Container sulla stessa Orange Pi.** Conservare Debian e kiosk; verificare architettura immagine, runtime container, RAM, storage, temperature, carico della dashboard e recupero dai guasti prima di proporre l'installazione. Non presumere un'immagine HA OS compatibile con Zero 3W. Un host separato rimane un'alternativa qualora la prova mostri interferenze con il display. Nessuna sostituzione dell'OS è prevista.

Non emerge la necessità di comprare un abbonamento per il collegamento iniziale documentato. L'obiettivo proposto è evitare nuovi servizi a pagamento; hardware disponibile, consumi e condizioni dei servizi esterni vanno valutati separatamente. Nessun acquisto è parte del piano iniziale.

## 5. API e limiti della conferma

Home Assistant espone WebSocket `/api/websocket`, autenticazione, `get_states`, sottoscrizione `state_changed`, `ping`/`pong` e `call_service`. La risposta a una chiamata di servizio descrive l'esecuzione lato Home Assistant: il client deve osservare gli stati successivi. [API WebSocket](https://developers.home-assistant.io/docs/api/websocket/). REST è disponibile per letture e azioni puntuali. [API REST](https://developers.home-assistant.io/docs/api/rest/).

Proposta: WebSocket persistente per le modifiche; snapshot per avvio/riconnessione e riconciliazione periodica. Il ping verifica Home Assistant, non il singolo dispositivo. Anche una lettura REST può restituire uno stato già conservato nel server.

`unknown` e `unavailable` hanno significati distinti. `last_changed` indica una variazione, `last_updated` una variazione di stato/attributi, `last_reported` una scrittura dello stato da parte dell'integrazione; neppure quest'ultimo è un heartbeat fisico universale. Gli attributi `assumed_state` e `restored`, quando presenti, devono influire sulla presentazione. [Oggetto stato](https://www.home-assistant.io/docs/configuration/state_object/).

Il codice Tuya esaminato sul ramo **dev**, come riferimento e non come prova della versione installata, deriva la disponibilità da `device.online` e riceve aggiornamenti dall'SDK. Non dimostra tempi certi di rilevamento di un dispositivo irraggiungibile. [Entità Tuya nel codice Home Assistant](https://github.com/home-assistant/core/blob/dev/homeassistant/components/tuya/entity.py).

Home Assistant permette token persistenti dal profilo utente. [Autenticazione](https://developers.home-assistant.io/docs/auth_api/). Proposta per SmartPC: account dedicato, segreto nel backend, nessun token nello stato QML, cache o log. La selezione di poche entità è una policy applicativa e non rende automaticamente il token limitato a quelle entità o alla sola lettura.

## 6. Da verificare con l'impianto dell'utente

- Home Assistant già presente, macchina ospitante e disponibilità continuativa.
- Modelli, protocolli, eventuali hub e prime entità desiderate.
- Funzioni effettive: stato luce/presa, luminosità, temperatura, umidità, contatto, batteria, potenza ed energia.
- Ritardo app → Home Assistant → SmartPC e pulsante fisico → Home Assistant → SmartPC.
- Cosa mostra Home Assistant con Internet interrotto, dispositivo disalimentato e server riavviato.
- Quali stati sono stimati o ripristinati; quali azioni hanno riscontri sufficienti.

**Conclusione operativa:** ricerca sufficiente per definire l'architettura e il collaudo; compatibilità e affidabilità dell'impianto restano da dimostrare.
