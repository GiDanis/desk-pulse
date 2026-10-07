# v0.7 Casa / Smart Life · verifica prima dell'implementazione

> Aggiornamento 6 ottobre: il modulo è implementato nella candidata v0.7.0-rc.1. [Consegna e verifiche attuali](v07-implementation-report.md), [uso e quota](v07-casa-operations.md). Il testo sotto conserva l’analisi e le evidenze antecedenti.

**6 ottobre 2026. Esito: pronti a iniziare lo sviluppo del provider e delle schermate. L'attivazione continuativa richiede quota/scadenza reali; il rilascio richiede ancora collaudi fisici e sulla Orange Pi.**

Questa revisione aggiorna il [piano diretto](v07-tuya-direct-plan.md) rispetto al [MasterPlan corrente](release-masterplan.md). La baseline è v0.6.6 con Theme Engine e API pubblica già presenti. Casa rimane analisi/prototipo: questa attività modifica la documentazione, senza integrare un provider nel kiosk.

## Evidenze aggiornate

Il [resoconto del controllo](evidence/v07-readiness-2026-10-06/README.md) separa prove attuali, prove storiche e attività ancora aperte.

| Area | Riscontro del 6 ottobre | Conseguenza |
| --- | --- | --- |
| Client Tuya | 22 test offline superati sul PC | Firma, token, normalizzazione e cache del client esistente sono riutilizzabili. Non verificano lo scheduler futuro. |
| Accesso cloud | 8 GET complessive, incluse autenticazione e quattro specifiche | Il progetto permette ancora di leggere i dati scelti per il campione. |
| Risposta cumulativa | 16 identità uniche; 7 online, 9 offline; 10 elenchi stati, 83 campi | Un ciclo ordinario può aggiornare inventario e stati con una pagina; sei dispositivi non espongono stati in questa risposta. |
| Paginazione | Pagina 1 e 2 con dimensione 1 restituiscono due identità diverse | I parametri funzionano sul progetto; la gestione completa di più pagine resta da implementare e testare. |
| Tipi e unità | Specifiche di temperatura/umidità, presa, lampada e movimento leggibili | Le tessere possono usare un insieme ristretto di dati interpretati. JSON, raw e bitmap restano non verificati. |
| Board | Servizio active/running, NRestarts=0, versione 0.6.6 | La verifica è di salute e versione; non è una prova Tuya live sulla board. |
| Quota | Pricing ufficiale ricontrollato; console privata non verificata | Il riferimento pubblico di 26.000 API/mese non costituisce la quota assegnata al nostro progetto. |

La prova attuale non ha misurato propagazione rispetto all'app, spegnimenti, aggiunte/rimozioni o riavvio offline. Il rinnovo reale e i test simulati sulla board appartengono alla [verifica precedente](v07-tuya-live-analysis.md), non sono stati ripetuti oggi.

## Architettura scelta

Un servizio Python **dentro il processo della dashboard** interroga OpenAPI Tuya in un worker. QML riceve dati normalizzati dal backend. Si riusano `tuya_core.py`, il contenitore `module_state`, navigazione, impostazioni, cache e Theme Engine; il probe rimane uno strumento manuale.

La Orange Pi eseguirà le acquisizioni anche quando il PC è spento. Smart Life continua ad associare i dispositivi all'account; il collegamento fisico Zigbee rimane al suo hub. Non serve un ulteriore server per il modulo Casa.

Per la distribuzione il file privato del servizio è previsto in `/var/lib/smartpc-dashboard/.config/smartpc/tuya-cloud.json`, proprietario `smartpc`, permessi 600 e directory privata. È il percorso coerente con HOME e StateDirectory dell'unità attuale. Credenziali e token non entrano in sorgenti, temi, QML, export o fixture. Oggi il file è ancora soltanto sul PC: non è stato trasferito né sono state modificate configurazioni della board.

## Correzioni necessarie al piano precedente

### 1. Un adapter cumulativo dedicato

Il client attuale legge `/v1.3/iot-03/devices` con cursore e acquisisce specifiche/stati separatamente. Il provider ordinario userà `GET /v1.0/users/{uid}/devices?page_no=1&page_size=50`, che restituisce una lista con stati e disponibilità. **Cambiare solo l'URL del metodo attuale sarebbe errato.** [Contratto ufficiale](https://developer.tuya.com/en/docs/cloud/ad2823ae46?id=Kconjtzq1vk1q).

Il nuovo adapter deve validare identità, limiti, forma e codici, scartare local key, IP, coordinate e UID prima della persistenza. Termina quando una pagina ha meno righe di `page_size`; una pagina piena comporta una richiesta successiva, eventualmente vuota. Imporre limite di pagine/dispositivi e rifiutare identità duplicate o pagine ripetute. Un errore impedisce di pubblicare l'inventario parziale.

Questa risposta non documenta un totale o un token di snapshot. Durante più pagine l'elenco può cambiare: non promettere una transazione cloud. Prima di dichiarare rimosso un dispositivo già noto richiedere assenza in due acquisizioni complete successive; nel frattempo segnalarlo come non trovato nell'ultima acquisizione. Nessuna rimozione dopo errore, revoca o inventario incompleto. Verificare anche un inventario validamente vuoto, senza far risorgere dati vecchi al riavvio.

### 2. Tre significati distinti per lo stato

- **Sorgente:** esito dell'acquisizione cloud (`active`, `updating`, `stale`, `offline`, `error`, `unavailable`).
- **Disponibilità dispositivo:** online/offline/sconosciuto dichiarato dal cloud, con istante della lettura e indicazione se proviene dalla cache.
- **Valore:** ultimo stato riportato, unità e qualità dell'interpretazione; campo mancante o non verificato distinto da `false` e zero.

Una nuova GET riuscita rinnova l'ora della **lettura del cloud**, non prova l'ora dell'ultima misura fisica. I campi `update_time` e l'istante di ricezione non diventano timestamp certi di ogni data point senza prova specifica. UI: «Cloud letto alle …» e «Ultimo stato riportato»; quando il dispositivo è offline domina «Offline».

Se manca uno stato nel ciclo successivo, conservare eventualmente il valore precedente con la sua vecchia provenienza, indicandolo non aggiornato. Un valore non interpretato non diventa un valore noto. Dopo perdita del cloud anche il vecchio flag online è soltanto l'ultima disponibilità riportata; il banner della sorgente rende evidente il mancato aggiornamento. Soglia iniziale candidata per dato salvato/stale: due intervalli base senza acquisizione valida, da configurare e verificare.

### 3. Polling con un budget effettivo

Con una pagina, su 30 giorni, cinque minuti producono 8.640 letture; un minuto per due ore cumulative al giorno e cinque minuti nelle altre 22 ore producono 11.520. La stima precedente di 12–14 mila richieste con overhead è plausibile per pochi errori e processo stabile, ma non è un limite garantito. Il caso ogni minuto 24/7 produce 43.200 letture e supera il riferimento Trial. [Pricing ufficiale](https://developer.tuya.com/en/docs/iot/membership-service?id=K9m8k45jwvg9j).

Il provider deve contare ogni tentativo HTTP, incluse autenticazioni, recupero token, retry, pagine aggiuntive, specifiche e aggiornamenti manuali, **prima dell'invio**. Il solo `request_count` in RAM del probe è insufficiente. Contatore persistente isolato per progetto, periodo di quota configurato e confronto con consumo della console; un reboot non azzera il saldo. Clock arretrato, file corrotto o periodo non conosciuto non devono regalare nuovo budget.

Policy di partenza: base cinque minuti, accelerazione a un minuto soltanto mentre Casa è consultata, massimo due ore cumulative/giorno e solo se la proiezione sul periodo rimane entro l'80% della risorsa disponibile. Ingresso nella pagina, refresh manuale e timer si uniscono in una sola acquisizione; cooldown e limite di un worker attivo. Le specifiche si memorizzano per ID/prodotto e si aggiornano su cambio schema/modello/codici o verifica ordinaria sostenibile. Nessuna acquisizione separata per ogni tessera.

Backoff candidato per problemi di rete: 5, 10, 20, 40, 60 minuti, con jitter e ripresa alla prima lettura valida. Un codice noto di quota esaurita o servizio scaduto sospende il polling fino al periodo ripristinato o a una verifica manuale dopo correzione. Mappare i codici documentati del provider, oltre a HTTP 429: oggi molti errori business sono ancora generici `api`. Budget insufficiente rende visibile la pausa; non produce timer continui di tentativi rifiutati.

**Avvio sicuro dello sviluppo:** fixture e aggiornamenti manuali contenuti finché quota assegnata, consumo e scadenza non sono noti. Il polling continuativo e l'accelerazione non si abilitano assumendo automaticamente 26.000 chiamate. Questa condizione limita l'attivazione live, non la scrittura dell'adapter e dei test.

### 4. Casa deve entrare anche nel contratto dei temi

`app.py`, `DashboardState`, `Main.qml`, `TOGGLEABLE_MODULES` e il refresh centrale oggi non hanno Casa. Neppure i contratti pubblici censiscono le sue superfici. La v0.7 aggiunge provider, stato, famiglia, impostazioni e DTO pubblici insieme alle viste.

Superfici candidate: `casa.overview`, `casa.devices`, `casa.detail`, `settings.casa`. Dati: sorgente, dispositivi, metriche normalizzate e selezione stabile. Azioni: consultazione, scelta preferiti e refresh della sorgente; nessun comando al dispositivo. Il refresh accettato è una richiesta avviata, non un successo dell'acquisizione: esito asincrono collegato al worker.

Estendere i contratti canonici e rigenerare tooling/fixture, senza modificare direttamente i generati. Aggiornare il kit degli autori e i profili Base/Functional. Per i bundle esistenti verificare fallback Base sulle nuove superfici e dichiarare la copertura parziale; niente pagina vuota o promessa di copertura completa dei vecchi temi. Le aggiunte devono mantenere compatibili i contesti esistenti; la versione API si decide con una verifica esplicita della compatibilità.

### 5. Aggiunte e modifiche restano gestite dall'app

Una nuova associazione in Smart Life compare nell'elenco Casa alla prossima acquisizione completa **se il dispositivo è esposto al progetto cloud collegato**. Non richiede modifica del codice né nuove credenziali. Il ritardo è quello del polling e dell'esposizione cloud, da provare con una vera associazione.

Preferiti, ordine e focus sono salvati per ID dispositivo, non per indice o nome. Rinomina: cambia l'etichetta, conserva la selezione. Nuovo ID dopo sostituzione/reset: nuovo dispositivo da selezionare, senza sostituire automaticamente un preferito. Rimozione confermata: il preferito conserva un'indicazione «Non più disponibile» finché l'utente lo sostituisce o rimuove. Cambio account/progetto: nuova cache e nuova selezione isolata.

## Primo risultato visibile

Panoramica con massimo quattro tessere, elenco a righe grandi e dettaglio. Impostazioni Casa per preferiti/ordine; refresh manuale nel punto comune **Dati e aggiornamenti**. La famiglia entra nel carosello dopo una configurazione utile e una selezione, conservando l'accesso durante un guasto della sorgente. Una configurazione incompleta si gestisce dalle impostazioni senza una pagina vuota in Home.

Campione per lo sviluppo: **T & H Sensor**, **Zigbee Plug**, **Lampada scrivania**, **Sensore di movimento**. È una proposta basata sui dispositivi letti, non una scelta definitiva dei preferiti. Non abbiamo dimostrato che Zigbee Plug sia la presa del PC. Il sensore movimento mostra soltanto l'ultimo evento cloud, senza certificare presenza attuale o generare allarmi.

Tessere: nome, icona semantica, testo e disponibilità; temperatura/umidità per il sensore, interruttore riportato per luce/presa. Potenza e batteria possono entrare nel dettaglio con unità verificate. Nessuna percentuale di luminosità o conversione in kelvin dedotta da un valore senza unità. Contrasto, nomi lunghi, zero/falso e dati mancanti nelle fixture di entrambi i profili a 960×640.

## Sequenza di implementazione e criteri di avanzamento

| Fase | Consegna | Prova richiesta |
| --- | --- | --- |
| C0 · Baseline | Snapshot delle modifiche correnti, quota/scadenza raccolte, campione di collaudo scelto | Preservare il lavoro Theme in corso; nessuna inclusione implicita nella release Casa. |
| C1 · Adapter | Inventario/stati cumulativi, cache specifiche e riconciliazione per ID | Pagine piene/vuote/ripetute, errori intermedi, stati mancanti, isolamento account, cambio schema e rimozioni confermate. |
| C2 · Provider | Worker Qt, token condiviso, scheduler, contatore e backoff persistenti, chiusura entro i limiti del servizio | Refresh simultanei unificati, reboot/clock/reset budget, errori quota/token, risposta tardiva di un account precedente scartata, rendering senza I/O. |
| C3 · UI e Theme API | Preferiti, panoramica, elenco/dettaglio e impostazioni; due profili e kit aggiornati | Zero/falso/null distinti, focus stabile, aggiornamento asincrono senza falso successo, vecchio bundle con fallback e nuova copertura dichiarata. |
| C4 · Collaudo reale | Variazioni da app/pulsante, perdita e ritorno rete, disalimentazione, aggiunta/rinomina/rimozione | Almeno Wi-Fi e Zigbee scelti, confronto con Smart Life, latenza osservata e disponibilità con valori precedenti. |
| C5 · Board e rilascio | Acquisizioni live su Orange Pi, reboot offline, recupero automatico, backup/manifest e rollback | EGLFS 960×640, assenza di warning inattesi, servizio stabile, risorse misurate; quota e limiti documentati. |

**Decisione:** possiamo iniziare C1/C2 con i vincoli sopra e preparare i contratti di C3. Il percorso tecnico scelto è dimostrato; le informazioni mancanti riguardano attivazione e accettazione, non richiedono un'altra architettura. La v0.7 viene dichiarata pronta all'uso solo dopo C4/C5.
