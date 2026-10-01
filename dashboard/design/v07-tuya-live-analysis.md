# v0.7 Casa · analisi delle prime chiamate reali

**Data: 1 ottobre 2026. Stato: autenticazione verificata; analisi dei dispositivi ancora incompleta.**

Le credenziali fornite dall'utente erano state inserite nella guida Markdown. Client ID, Client Secret e Project Code sono stati trasferiti nel file privato `/home/giuseppe/.config/smartpc/tuya-cloud.json`, con permessi `600`, e rimossi dalla guida. Nessuna chiave o token è riportata qui o negli output diagnostici. Non sono state copiate credenziali sulla Orange Pi.

## Risultati reali

| Prova | Esito osservato |
| --- | --- |
| Token su Western Europe | Ottenuto; firma e credenziali accettate |
| Token su Central Europe | Ottenuto; firma e credenziali accettate |
| Refresh token su Western Europe | Rinnovo reale riuscito, senza token di business nella firma |
| Lettura diagnostica dei dispositivi degli account collegati | Rifiutata sui due endpoint europei con `28841107` |
| Motivo indicato dalla risposta Tuya | Data center sospeso; richiesta di abilitarlo nella piattaforma cloud |
| Inventario completo filtrato per UID | Non eseguito: UID non configurato e data center da verificare |
| Specifiche e stati di dispositivi | Non eseguiti: elenco non disponibile |
| Comandi ai dispositivi | Nessuno |

Eseguite **9 richieste reali di sola lettura/autenticazione**: quattro richieste di token iniziale, un refresh, tre tentativi diagnostici su Western Europe e uno su Central Europe. Il token non viene persistito. La lettura diagnostica ha usato `GET /v1.0/iot-01/associated-users/devices`, documentata da Tuya per gli account associati al progetto, con limite di una pagina. Non è un fallback attivato nel provider e non è stata salvata una risposta grezza. [API diagnostica](https://developer.tuya.com/en/docs/cloud/fc19523d18?id=Kakr4p8nq5xsc).

L'autenticazione riuscita su entrambi gli endpoint **non identifica il data center effettivo dell'account** e non prova il diritto di leggere i dispositivi. Il codice `28841107` è stato associato alla sospensione leggendo la risposta reale, senza stampare il messaggio grezzo; non è stata diagnosticata una scadenza o una quota esaurita.

## Passaggio necessario nella console

1. Aprire il progetto Tuya e verificare/abilitare il data center dove è registrato l'account Smart Life.
2. Verificare che **Devices → Link App Account** contenga l'account autorizzato tramite QR, con **Automatic Link**. Il **Project Code non è l'UID**: l'UID necessario è quello dell'account collegato.
3. Compilare `endpoint` e `uid` nel file privato. Client ID e Client Secret sono già presenti.
4. Verificare servizi **IoT Core / Smart Home Basic Service** autorizzati al progetto, quota e scadenza nell'API Explorer. Non è stato acquistato o attivato un piano a pagamento.

Tuya distingue sottoscrizione del servizio e autorizzazione del progetto a chiamarlo. [Gestione dei servizi API](https://developer.tuya.com/en/docs/iot/applying-for-api-group-permissions?id=Ka6vf012u6q76), [collegamento account Smart Life](https://developer.tuya.com/en/docs/developer/apply-cloud-api-key?id=Kff30z8sv62ah).

## Prove ancora necessarie per completare l'analisi

| Prova | Evidenza da raccogliere |
| --- | --- |
| Inventario per UID | Numero e categorie confrontati con Smart Life, hub/sottodispositivi e disponibilità |
| Luce, presa e sensore Zigbee | Codici realmente esposti, tipi, scale, unità e valori mancanti |
| Cambio di stato dall'app o dal pulsante | Variazione ricevuta dal cloud e ritardo misurato; mai chiamare «attuale» un dato non verificato |
| Dispositivo disalimentato | Comportamento di `online` e distinzione dall'ultimo stato riportato; richiede intervento fisico dell'utente |
| Aggiunta/rinomina/rimozione | Propagazione dell'elenco, stabilità dell'identificativo, comportamento dopo una nuova associazione |
| Ripartenza offline/riconnessione | Cache precedente riconoscibile, nessuna cancellazione per errore e nessuna falsa conferma |
| Budget API | Quota/scadenza effettive e frequenza sostenibile; durata della trial non ancora nota |

Le prove di rete interrotta, token non valido, cache atomica e isolamento account sono coperte da regressioni con risposte simulate. Questa copertura non sostituisce la verifica sul cloud e sui dispositivi fisici. Il rinnovo del token è ora dimostrato anche contro il servizio reale.

**Regressioni aggiornate: 21 controlli superati sul PC e 21 sulla Orange Pi.** Aggiunta la verifica del codice `28841107`: diagnosi esplicita, nessun retry continuo e nessuna perdita della cache. Confermata l'assenza delle credenziali fornite nei file Markdown/Python/JSON/QML della directory dashboard.

La sospensione non va aggirata con retry continui: il client mostra una diagnosi specifica e conserva l'ultima cache valida. La dashboard Casa, i preferiti e lo scheduling restano da integrare dopo aver verificato i payload reali. La v0.7 non è conclusa.
