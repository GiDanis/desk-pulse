# SmartPC · piano v0.7 Casa

> **Revisione della direzione:** dopo la richiesta di semplificazione del 1 ottobre 2026, valutare prima il [cloud Tuya diretto](./v07-tuya-direct-plan.md). Le sezioni seguenti conservano la proposta Home Assistant come alternativa; la sua installazione non è il prossimo passo previsto.

**Revisione:** 1 ottobre 2026. **Stato:** proposta da discutere, non implementata. Fonti esterne e alternative: [ricerca Smart Life/Tuya](./v07-home-assistant-research.md).

**Informazioni confermate:** nessuna installazione Home Assistant; dispositivi già gestiti nell'app, alcuni Wi-Fi e altri Zigbee; valutazione richiesta sulla stessa Orange Pi. Risorse attuali lette via SSH; compatibilità dei modelli e comportamento con HA attivo non ancora verificati.

## 1. Obiettivo e baseline verificata

Seguire il MasterPlan della chat **Dashboard Orange Pi MasterPlan**: Home Assistant alimenta poche tessere grandi con stati affidabili; il primo rilascio è di consultazione. Comandi successivi solo per azioni nominate e collaudate. Uscita: riconnessione automatica, offline riconoscibile e nessuna falsa conferma.

Nel sorgente attuale sono registrate Oggi, Meteo, Account ChatGPT, Serie A, F1 e MotoGP. Casa non ha ancora provider o schermata. `module_state.py` offre già `active`, `updating`, `stale`, `offline`, `error`, `unavailable`; `state.py` gestisce preferenze e visibilità; `app.py` compone i servizi; `Main.qml` gestisce famiglie e pannelli. Questa verifica è sul workspace: non costituisce un nuovo collaudo fisico della v0.6.

## 2. Perimetro proposto

- **v0.7 iniziale:** 3–4 tessere scelte; lettura di `light`, `switch`, `sensor`, `binary_sensor` quando esposti e verificati; cache, dettaglio, connessione, stato per entità e riconnessione.
- **Estensione successiva:** un comando esplicito su una luce scelta, se richiesto e dopo prove. La presa del PC resta di consultazione nella prima versione.
- Stanze si aggiunge soltanto quando l'inventario rende utile il raggruppamento; nessuna seconda vista vuota obbligatoria.
- Potenza, energia e batteria compaiono solo se disponibili, con unità provate. Nessuna stima di consumi presentata come misura.
- Avvisi Casa e automazioni richiedono regole scelte dall'utente: non derivarli automaticamente dall'elenco dispositivi.
- La Home conserva ora/meteo e l'evento condizionale; non aggiungere una tessera Casa permanente.

Proposta iniziale: **Home Assistant Container sulla stessa Orange Pi, subordinato alla verifica di risorse e prestazioni**, con integrazione Tuya inclusa in Home Assistant. I dispositivi Zigbee già presenti nell'account possono essere valutati attraverso il loro hub e la stessa integrazione cloud: non serve decidere ora una nuova rete Zigbee o comprare un coordinatore. Occorre identificare hub e supporto effettivo. Collegamenti locali valutati caso per caso; Home Assistant resta il punto unico d'accesso di SmartPC.

## 3. Preparazione dell'impianto

1. Valutare la stessa Orange Pi: RAM e spazio liberi, architettura/page size, runtime Docker disponibile, consumi del kiosk, storage e backup. Verificare l'immagine ARM64 corrente di Home Assistant Container e la compatibilità con Debian prima di installare. Se emergerà l'errore jemalloc documentato nella guida Linux, valutarne l'opzione prevista dopo aver verificato la page size; non applicare workaround preventivi.
2. Compilare l'inventario sotto; nessuna compatibilità presunta dalla sola presenza nell'app.
3. Collegare Smart Life con la procedura corrente documentata nella ricerca.
4. Selezionare una luce e una presa, poi un sensore se presente. Verificare prima in Home Assistant nomi, unità e variazioni reali.
5. Registrare versione Home Assistant, integrazione, firmware quando disponibile e modalità cloud/locale.

| Nome sul display | Marca/modello | Protocollo/hub | Entità HA | Dato e unità | Stato stimato? | Prove riuscite |
| --- | --- | --- | --- | --- | --- | --- |
| Da scegliere | Da rilevare | Da rilevare | Da rilevare | Da rilevare | Da verificare | Nessuna |

Luce, presa PC e sensori sono esempi di prodotto, non dispositivi già confermati dell'utente. Restano da rilevare modelli, hub Zigbee e priorità della prima schermata.

### Prova prevista di coesistenza sulla Orange Pi

Lettura passiva via SSH del **1 ottobre 2026**, con kiosk attivo, senza modificare servizi:

| Dato osservato | Valore |
| --- | --- |
| Architettura / page size | `aarch64` / 4096 byte |
| RAM totale / disponibile | 5855 / 5470 MiB |
| Swap usata | 0 MiB su 2927 MiB |
| Spazio disponibile sul filesystem root | Circa 21 GiB |
| Docker installato | 29.7.2 |
| Docker e containerd | Inattivi e disabilitati |
| Kiosk | Servizio attivo; `MemoryCurrent` circa 119 MiB, 5 task |
| Temperatura thermal zone 0 | Circa 41,7 °C |

Questa fotografia rende plausibile la prova Container, ma non misura HA né certifica prestazioni sotto carico. Docker è già installato: la fase attuativa dovrà valutare riattivazione e autostart. La lettura non ha avviato Docker o scaricato immagini.

Installazione Container da eseguire solo nella fase attuativa, dopo backup. Directory persistente distinta per Home Assistant; autoriavvio indipendente dal kiosk; nessun cambio dell'OS o del percorso grafico. Configurare rotazione dei log e registrazione dello storico solo per entità utili, con conservazione limitata da definire dopo misure. Usare prima soltanto Tuya, senza componenti aggiuntivi non necessari.

Misurare la stessa sequenza di animazioni con dashboard sola e con HA attivo: avvio a freddo, aggiornamenti dei dispositivi, riconnessioni e scritture del database. Registrare frame interval, CPU, RAM, swap, temperature e spazio. Eventuali limiti di risorse del container si tarano sui risultati, evitando di provocare riavvii per memoria insufficiente. Condizione per accettare la soluzione: requisiti del display conservati e assenza di pressione persistente sulla memoria; altrimenti ridurre il carico o proporre un host separato. Nessuna garanzia di 60 fps prima di questa prova.

## 4. Architettura prevista

| Componente proposto | Responsabilità |
| --- | --- |
| `home_assistant_core.py` | Contratto dati, normalizzazione, policy di disponibilità, validazione configurazione/cache |
| `home_assistant.py` | Client WebSocket in worker dedicato, retry, snapshot, segnali Qt, arresto ordinato |
| `CasaView.qml` | Panoramica con tessere leggibili e stati per dispositivo |
| `CasaOverlay.qml` | Elenco/dettaglio e, solo nell'estensione, azioni esplicite |
| `app.py`, `state.py` | Composizione servizio, `casaState`, preferenze e visibilità |
| `Main.qml`, `DashboardOverlay.qml` | Famiglia Casa dopo MotoGP, tasti e impostazioni |

Riutilizzare l'involucro `module_state`; aggiungere nel suo `data` stato di connessione ed entità individuali. La rete non lavora nel thread Qt grafico. Valutare QtWebSockets nel runtime della board; un'eventuale libreria Python va motivata e verificata prima di diventare dipendenza. L'implementazione sceglierà un solo client.

Config non segreta: URL, identità delle entità, etichette brevi, ordine, stanza e policy per dato. Sulla stessa board, preferire il collegamento SmartPC–HA via loopback, verificandone l'accesso dalla rete del container; la pagina di configurazione HA deve essere raggiungibile dal telefono/PC sulla LAN. Config segreta: token Home Assistant in file protetto fuori dal progetto, leggibile dal servizio, eventualmente tramite credenziali systemd. Nessuna password Smart Life o local key arriva al provider SmartPC. Account HA dedicato; verificare autorizzazioni reali senza promettere uno scope per entità del token.

Cache atomica nel percorso utente del servizio, per sole entità selezionate; schema versionato, dimensioni limitate, nessun attributo arbitrario, URL di immagini o segreto. Config e demo separate. Una cache corrotta porta a stato assente e recupero dalla rete; non a valori inventati.

## 5. Connessione e riconciliazione

Il protocollo offre snapshot, eventi e heartbeat: [API Home Assistant](https://developers.home-assistant.io/docs/api/websocket/). Le scelte seguenti sono policy proposte per SmartPC, da misurare.

1. Connessione → autenticazione → sottoscrizione con conferma → snapshot iniziale. Accodare gli eventi durante lo snapshot e riconciliarli senza far retrocedere dati più recenti; assegnare una generazione alla sessione per scartare risultati tardivi di connessioni precedenti.
2. Applicare solo entità configurate; evento con `new_state: null` significa entità rimossa. Uno snapshot completo valido rimuove gli stati precedenti non più presenti. Un errore conserva il dato storico con qualità degradata.
3. Heartbeat proposto ogni 15 secondi, timeout 10 secondi: disconnessione riconoscibile entro circa 25 secondi anche senza chiusura esplicita del socket. Questo misura solo il collegamento ad HA.
4. Retry proposto 1, 2, 4, 8, 16, 30, 60 secondi, con jitter; dopo il ripristino, nuova sottoscrizione e snapshot prima di dichiarare il modulo sincronizzato. Nessuna duplicazione di worker/subscription.
5. Riconciliazione proposta ogni 5 minuti e dopo sospensioni o lacune della sessione; rileggere HA non aggiorna artificialmente l'ora della misura fisica.
6. Token rifiutato: stato «Autorizzazione richiesta», retry lento o sospeso fino a cambio configurazione; nessuna tempesta di richieste. Arresto del servizio chiude worker e socket entro il limite systemd.

## 6. Contratto dati e affidabilità

Separare tre informazioni: **connessione SmartPC–HA**, **stato dichiarato dell'entità**, **qualità del dato**. `active` nel modulo descrive la sincronizzazione con Home Assistant, non certifica la risposta fisica di ogni dispositivo.

| Campo proposto | Significato |
| --- | --- |
| `entityId`, `kind`, `label`, `area` | Identità stabile, tipo supportato e nome breve configurato |
| `rawState`, `value`, `unit` | Stato HA originale e dato normalizzato nullable |
| `availability` | `available`, `unavailable`, `unknown`, `missing` |
| `quality` | `reported`, `assumed`, `cached`, `stale`, `unverified` |
| `transport` | `cloud`, `local`, `unknown`, verificato in configurazione |
| `receivedAt`, `haCheckedAt` | Ultimo evento ricevuto e ultimo snapshot verificato in HA |
| `haLastChanged`, `haLastUpdated`, `haLastReported` | Timestamp HA conservati se effettivamente disponibili |
| `deviceObservedAt` | Timestamp della misura fisica solo se attestato dalla fonte; altrimenti null |
| `fromCache`, `reason`, `allowedActions` | Provenienza, motivo della qualità e azioni consentite; lista vuota nel primo rilascio |

Timestamp HA e lettura del server non equivalgono a misura fisica. `last_changed` può restare vecchio su una luce sana; una soglia universale renderebbe falsamente offline dispositivi invariati. I sensori periodici possono avere soglie specifiche dopo aver misurato la cadenza; i sensori a evento richiedono disponibilità/last-seen affidabili, quando esposti. [Semantica degli stati e dei timestamp](https://www.home-assistant.io/docs/configuration/state_object/).

| Situazione | Comportamento previsto |
| --- | --- |
| HA collegato, stato disponibile | Stato con provenienza HA; indicare «Tuya cloud» dove serve |
| HA collegato, entità `unavailable` | «Non disponibile» su quella tessera; gli altri dispositivi restano leggibili |
| `unknown` o entità assente | «Stato sconosciuto» / «Dispositivo non trovato», distinti |
| HA irraggiungibile | «Casa offline»; ultimo stato esplicitamente precedente |
| Avvio da cache | «Dati salvati · da verificare» finché la sessione non è sincronizzata |
| Stato stimato/ripristinato | «Stato da verificare»; nessun comando abilitato |
| Cloud non osservabile, HA ancora raggiungibile | Non attribuire certezza fisica al valore; ultimo stato riportato e limite consultabile |

Un dato numerico assente resta null: non diventa 0 °C, 0 W o batteria 0%. «Non disponibile» non diventa «Spenta». Se il cloud trattiene uno stato senza segnalare il guasto, il display può mostrare soltanto l'ultimo stato riportato, non garantire un offline istantaneo. Se questo limite non soddisfa il prodotto per un modello, si prova il collegamento locale o si esclude quell'entità dal perimetro affidabile.

## 7. Esperienza 960×640

Panoramica con **massimo quattro tessere grandi**, griglia 2×2; meno tessere se nomi/stati rendono la lettura difficile sul pannello. Nome 30–34 px, stato/valore 40–56 px come punto di partenza da controllare fisicamente. Fondo navy, accento teal, testo caldo e icone locali coerenti; niente animazioni continue per simulare attività.

Ogni tessera combina icona, testo e colore: «Accesa», «Spenta», «Non disponibile», «23,4 °C». Uno stato salvato ha etichetta evidente e trattamento attenuato; non basta un piccolo badge in testata. Nomi lunghi si abbreviano in panoramica e restano completi nel dettaglio.

Consultazione: 4/6 cambiano famiglia; 2/8 cambiano vista solo se esiste. 5 apre elenco con massimo tre righe visibili; 2/8 selezionano e 5 apre dettaglio. 7 torna conservando focus, 1 torna a Oggi, 3 apre Avvisi, 9 Menu. Aggiornamenti e riconnessioni conservano il dispositivo selezionato. Se sparisce, mostrare l'indisponibilità senza saltare automaticamente su un altro dispositivo.

Famiglia nascosta prima della configurazione. Dopo la prima configurazione utile resta accessibile offline con i dati salvati e può essere nascosta dalle impostazioni. Un'assenza di rete non fa sparire Casa dal carosello.

## 8. Eventuale estensione comandi

Prima azione candidata: accendere/spegnere una luce nominata, con servizi espliciti `turn_on`/`turn_off`. Evitare `toggle`: gli esiti incerti e i retry possono invertirne l'effetto. La presa PC richiede una decisione specifica perché interrompe l'alimentazione; non abilitarla tramite una regola generica per tutti gli switch.

Flusso: selezione → nome dispositivo/azione → invio → attesa → stato riportato oppure «Esito non confermato». Un successo della chiamata HA non prova l'esito fisico. Osservare un aggiornamento pertinente successivo all'invio, confrontare valore e contesto quando disponibile e controllare che il provider non sia ottimistico. Anche lo stato HA resta distinto dalla prova fisica, che deve far parte del collaudo. [Chiamate di servizio e stati successivi](https://developers.home-assistant.io/docs/api/websocket/).

Timeout iniziale candidato 15 secondi, da regolare con misure. Se manca il riscontro, mantenere lo stato precedente, niente conferma verde. Nessun replay dopo riavvio/riconnessione e nessun retry automatico di un comando incerto. Bloccare doppi invii e azioni con dati precedenti; tornare dalla pagina non cancella una richiesta già trasmessa. Un aggiornamento tardivo può correggere la tessera, senza inventare una conferma retroattiva.

## 9. Fasi e prove d'uscita

| Fase | Risultato concreto | Condizione per proseguire |
| --- | --- | --- |
| A0 · Coesistenza | Valutazione Container sulla Orange Pi | Risorse/immagine idonee; poi confronto delle animazioni con HA attivo |
| A · Impianto | Inventario e HA con primi dispositivi | Entità desiderate leggibili e variazioni confrontate fisicamente |
| B · Collegamento | Probe di lettura, poi provider Python | Snapshot/eventi, token rifiutato, perdita/ripristino, nessun blocco UI |
| C · Grafica | Casa nel carosello e dettaglio | Lettura sul 3,5″, focus conservato, dati assenti/precedenti evidenti |
| D · Robustezza | Cache e recupero | App/board/HA riavviati; rimozioni e dati invalidi gestiti |
| E · Rilascio | Evidenze reali, README e rollback | Perimetro effettivamente verificato e limiti dichiarati |
| F · Comando facoltativo | Una sola azione nominata | Esiti corretti/timeout provati sul dispositivo reale |

Collaudo necessario:

- App Smart Life e pulsante fisico: almeno dieci variazioni per luce/presa candidata. Registrare ritardo fisico→HA e HA→SmartPC, non solo successo HTTP. Obiettivo candidato per il secondo tratto: ≤1 secondo sulla LAN; il limite del primo si decide dai risultati.
- Luce invariata per ore: non deve diventare offline per la sola età di `last_changed`.
- Sensori: confrontare unità, decimali, eventi, misure mancanti e cadenza reale; batteria non equivale a disponibilità.
- Separare perdita della LAN della board, arresto HA, perdita della sola WAN mantenendo la LAN, disalimentazione del dispositivo ed eventuale guasto dell'hub. Documentare ciò che il cloud effettivamente segnala e in quanto tempo.
- Durante la disconnessione cambiare il dispositivo da altra interfaccia disponibile; al ritorno SmartPC deve convergere al nuovo snapshot, senza mantenere la cache come corrente.
- Snapshot/eventi sovrapposti, eventi tardivi, entità rimossa/rinominata, dati malformati, cache corrotta o non scrivibile: nessuna resurrezione dei vecchi stati.
- Riavvio applicazione e reboot fisico della board senza rete; riavvio HA; nessun comando ricreato. Distinguere questi test da una simulazione di errore nel codice.
- Misurare transizioni e navigazione su EGLFS/PowerVR con acquisizione attiva, screenshot reali, RAM/CPU/temperatura e frame interval. Target 60 fps nelle animazioni; non dedurlo dagli FPS a riposo.
- Prova continuativa candidata di 24 ore, incluse riconnessioni, senza crescita persistente di worker/socket/memoria. Aggiornare README, backup e procedura rollback prima dell'installazione di release.

Test previsti di core, protocollo simulato e UI verificano i casi limite; sono complementari alle prove reali. Non dichiarare offline o comandi fisicamente verificati sulla sola base delle fixture.

## 10. Decisioni ancora aperte

1. Accettare o meno la coesistenza sulla Orange Pi in base alle misure; direzione iniziale scelta dall'utente.
2. Dispositivi iniziali e dati realmente esposti; modelli per eventuale prova locale.
3. Affidabilità cloud accettabile per ciascuna entità e limite di latenza misurato.
4. Panoramica soltanto o anche Stanze, secondo il numero di dispositivi scelti.
5. Comando eventuale nominato dall'utente e prove richieste per abilitarlo.

**Stato alla revisione:** MasterPlan e sorgenti attuali esaminati; ricerca web completata; architettura, layout e criteri proposti; nessuna implementazione v0.7, installazione Home Assistant o modifica della board eseguita.
