# v0.6 · F1 e MotoGP

**1 ottobre 2026.** Estensione della dashboard reale su Orange Pi Zero 3W, display 960×640. Il [piano](v06-sport-plan.md) e la [ricerca](v06-sport-api-research.md) restano i riferimenti. Serie A conserva elenco, rotazione, classifica e dettaglio già verificati.

## UX e contenuti

Il carosello ora è **Oggi → Meteo → Account → Serie A → F1 → MotoGP**. I tre sport sono adiacenti, con preferenze di visibilità indipendenti e una vista verticale ricordata per ciascuno. Non occorre entrare in un selettore di disciplina ogni volta.

| Tasti | Consultazione principale | Pannello aperto |
| --- | --- | --- |
| **4/6** | Famiglia precedente/successiva | Schede risultati/informazioni; in classifica F1, Piloti/Costruttori |
| **2/8** | Programma → In corso se disponibile → Risultati → Classifica | Scorre GP, sessioni o tutte le righe; tre visibili per pagina |
| **5** | Apre calendario, risultati o classifica | GP → weekend → sessione; nel dettaglio aggiorna |
| **7** | Torna a Home | Torna al pannello precedente conservando la selezione |
| **1**, **3**, **9** | Home, Avvisi, Menu | Stessi comandi, anche durante la consultazione di un risultato |

**Da Home, 4 ora apre MotoGP**, ultimo argomento del carosello; altri due 4 portano a Serie A. Da Serie A, 6 apre F1 e il successivo 6 MotoGP. Le famiglie nascoste vengono saltate.

- **Programma:** GP, circuito, prossime sessioni e orario della gara subito visibile; 5 apre l'intero calendario e il weekend. Orari italiani, conversione dei fusi originali e nomi dei giorni italiani. Una data di weekend senza orario di gara non diventa una gara a mezzanotte.
- **Risultati:** podio dell'ultima gara; nel GP si sceglie Gara, Qualifiche, Sprint o altra sessione disponibile. Elenco completo dei partecipanti con team e tempi/distacchi; 4/6 apre le informazioni della sessione. Una sessione futura spiega che i risultati saranno pubblicati dopo l'inizio.
- **Classifica:** primi tre piloti sulla schermata principale, tutte le posizioni con 5. F1 offre anche tutti i Costruttori tramite 4/6. La classifica indica il GP cui si riferisce; il recupero HTTP non equivale a una nuova gara disputata.
- **Impostazioni → Sport · F1 / Sport · MotoGP:** stagione corrente/precedente, prossima gara in Home su scelta esplicita, aggiornamento manuale. Le liste Impostazioni e Moduli visibili sono paginate, senza elementi fuori dal display. Le preferenze persistono; Home non crea tessere vuote.
- **In corso:** tempi/posizioni dalla sessione attiva coerente e fresca. Una disconnessione mantiene la pagina consultata, etichetta i tempi precedenti e toglie Live. Non viene mostrata una pagina vuota quando manca una sessione attiva.

## Fonti, storico e limiti

| Disciplina | Fonte e dati integrati | Copertura dell'interfaccia |
| --- | --- | --- |
| **F1** | Jolpica REST: calendario delle sessioni, risultati Gara/Qualifiche/Sprint, Piloti e Costruttori | Stagione corrente e precedente, GP precedenti caricati alla selezione. Le libere e le qualifiche Sprint hanno il programma, ma non un referto fornito da questo adapter |
| **F1 timing** | WebSocket Qt, **SignalR Core**, otto topic: informazioni/stato sessione, piloti, timing, giri, pista, heartbeat e race control | Posizioni, piloti, team, gap o miglior giro, giro corrente/totale. Accesso senza login provato con snapshot concluso; disponibilità e latenza durante sessione attiva restano da collaudare. Nessuna telemetria completa promessa |
| **MotoGP** | PulseLive REST: GP, broadcast filtrato MotoGP, sessioni risultati, classificazioni e classifica piloti | Stagione corrente e precedente. Libere, Practice, Q1/Q2, Sprint, Warm Up e Gara quando pubblicati; referti caricati su richiesta. Test e altre categorie esclusi |
| **MotoGP timing** | PulseLive `livetiming-lite` | Piloti, posizioni, tempi/gap testuali e giri. Il campione reale è Moto3 non iniziata: escluso dal live MotoGP |

Nessun abbonamento, chiave API o carta per questi endpoint osservati. La disponibilità futura degli endpoint resta dipendente dai provider. Jolpica documenta limite 500 richieste/ora e 4/secondo: il client applica un budget prudente di 400/ora e separazione di almeno 300 ms. [Documentazione Jolpica](https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md).

Il protocollo Core segue il client aggiornato [FastF1](https://github.com/theOehrly/Fast-F1/blob/master/fastf1/livetiming/client.py); la dashboard usa QtWebSockets e non installa FastF1/pandas. La distinzione tra UUID risultati/broadcast e i percorsi MotoGP sono confermati da risposte reali e confrontati con la [documentazione community](https://github.com/robschmitt/MotoGP-API). Il calendario F1 osservato, incluso il nome del prossimo GP, coincide con il [calendario ufficiale 2026](https://www.formula1.com/en/racing/2026).

**Badge Live ancora sotto collaudo**, separatamente per disciplina: `SMARTPC_F1_LIVE_VERIFIED=1` e `SMARTPC_MOTOGP_LIVE_VERIFIED=1` vanno attivati dopo una sessione reale. Questi flag non rendono attivo un dato vecchio: restano obbligatori identità, stato, finestra temporale, righe valide e freschezza. Per MotoGP non si interpretano A/R o bandiere senza evidenza: un codice sconosciuto richiede un'esplicita indicazione attiva nel broadcast/gateway. N/F e una categoria diversa non attivano il timing. Notifiche di sorpasso/vittoria e telemetria avanzata non sono implementate.

## Implementazione e persistenza

- `motorsport_core.py`: adapter indipendenti da Qt, normalizzazione, identità, validazione, budget Jolpica, dettagli lazy e cache atomica.
- `motorsport.py`: worker per HTTP e salvataggio cache distinti per disciplina, selezione accodata, preferenze, eventi Home e gestione anni. Nessun HTTP sincrono nel thread grafico.
- `racing_timing.py`: trasporto WebSocket asincrono Qt, handshake/subscription Core, merge dei delta, reset al cambio sessione, timeout e riconnessione 60–240 s. Heartbeat da solo non conserva fresco il timing. Connessione F1 limitata alla finestra delle sessioni del calendario.
- `MotorsportView.qml` e `MotorsportOverlay.qml`: riepiloghi e consultazione, integrati con stato, tasti, menu e avvisi condivisi.
- Cache persistenti separate: `f1-2026.json`, `f1-2025.json`, `motogp-2026.json`, `motogp-2025.json` sotto `QStandardPaths.CacheLocation`; sul servizio `/var/cache/smartpc-dashboard/SmartPC/SmartPC/`. Scrittura temporanea, fsync e sostituzione atomica; retention degli ultimi due anni. Un dettaglio riuscito non rende nuovo il calendario conservato da cache.

Calendario/classifiche: aggiornamento ogni 6 ore a riposo, 15 minuti vicino al weekend; controlli ogni minuto vicino al weekend per dettagli selezionati e gateway MotoGP. Timeout 12 s, limite dimensione e `Age`/`Cache-Control`/`Retry-After`. Aggiornamento manuale limitato a uno ogni 30 s. La gara prossima viene inviata al motore eventi entro sette giorni solo dopo l'attivazione della relativa preferenza.

### Dipendenza board

```bash
sudo apt-get install -y --no-install-recommends python3-pyside6.qtwebsockets
```

Installati sulla board soltanto `libqt6websockets6` e `python3-pyside6.qtwebsockets`, senza aggiornare altri pacchetti. Anche `scripts/setup-board.sh` controlla questa dipendenza per nuove installazioni.

## Prove completate

[Evidenze](evidence/v06-motorsport/): tutte le immagini sono catture EGLFS da dati REST realmente scaricati dalla Orange Pi. I fixture nei checker sono esclusivamente dati di test.

| Verifica | Riscontro |
| --- | --- |
| REST F1 2026 / 2025 dalla board | 23 / 24 GP, 23 / 21 piloti, 11 / 10 Costruttori. Referti ultimi GP e un altro GP storico, Gara/Qualifiche/Sprint |
| REST MotoGP 2026 / 2025 dalla board | 22 GP per anno, 30 / 29 piloti. Referti Gara/Sprint/Q2 e, selezionando FP1, 22 / 24 piloti; Q2 comprende 12 qualificati, non l'intera griglia |
| Programma MotoGP futuro | Otto sessioni MotoGP del GP Giappone; media e altre categorie filtrati. Libere 1 venerdì 03:45 e Gara domenica 07:00 italiane, dai timestamp con offset giapponese |
| F1 Qt SignalR PC e board | Connessione e otto topic, 22 righe. Azerbaijan Race con stato `Ends`: `active=false`, `isLive=false` |
| Regressioni adapter | Otto controlli: identità/stagione, fusi, valori mancanti, risultato/giro veloce, cache atomica/corrotta, errori dettaglio, merge/reset/stale SignalR, categoria/stato/sessione gateway, budget |
| QML + decoder HID sul PC e board | Calendario → GP → sessione, selezione conservata, futuri vuoti espliciti, tutte le righe risultati/classifiche, Costruttori, menu paginato, visibilità, preferenze, cambio anno, cache/errori, timing condizionale e perdita del feed |
| Regressioni esistenti | Serie A backend (11 controlli), UI Serie A, Home, banner, badge e impostazioni precedenti superati |
| Processo nuovo offline sulla board | Cache REST reale leggibile, entrambi i moduli `offline`, classifiche/referti conservati, nessun badge Live. La rete è disabilitata nel servizio di verifica; nessun reboot fisico in questa estensione |
| EGLFS / PowerVR | Catture 960×640 di programma, calendario, weekend, sessioni future, risultati, classifiche/Costruttori e impostazioni; nessun errore QML |
| Navigazione breve | 26 azioni in 12 s, 140 intervalli misurati: mediana 16,56 ms, p95 17,61 ms, massimo 18,05 ms; primo frame dopo un'azione massimo 49,70 ms. Campione limitato, non prova di 60 fps costanti o stabilità 24 h |

Per ripetere: `check_motorsport.py`, `check_motorsport_ui.py` e `verify_motorsport_board.py --mode fetch/timing/offline/capture --directory <dir>`. Le modalità sono singoli valori. Capture richiede il kiosk fermo e deve ripristinarlo con trap al termine; usa preferenze separate e risposte REST raccolte nella modalità fetch.

## Deploy e ripristino

Nuovi moduli e integrazioni installati in `/opt/smartpc/dashboard`; servizio `smartpc-dashboard.service` riavviato. Verifica dello stato e hash in [installed.json](evidence/v06-motorsport/installed.json).

Backup prima dell'installazione: `/var/backups/smartpc-dashboard-v06-before-motorsport-20261001/`, contenente sorgente, stato e cache della versione Serie A precedente. Per tornare a quella versione: fermare il servizio, ripristinare la directory `dashboard` nel percorso `/opt/smartpc/dashboard`, poi riavviare. Conservare le preferenze/cache attuali a meno che il ripristino dei dati non sia richiesto; non sovrascrivere automaticamente il database degli avvisi. QtWebSockets può restare installato. Il ripristino completo del backup non è stato eseguito.

### Rimane da verificare

Una sessione attiva F1 e una MotoGP per delta reali, fasi, ritardo, cambi sessione e riconnessione durante l'evento; il mapping dei codici gateway MotoGP rimane condizionato. Servono anche lettura dalla distanza d'uso e una prova prolungata durante il timing. Il collaudo Serie A/VAR rimane separato. La consultazione di calendario, risultati e classifiche è rilasciata con le prove sopra.
