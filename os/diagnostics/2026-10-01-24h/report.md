# Verifica operatività Orange Pi — 1 ottobre 2026

Raccolta SSH in sola lettura su `orangepizero3w`, terminata alle 22:40 circa, Europe/Rome. Nessun riavvio, deploy, cambio delle impostazioni o input inviato alla dashboard.

## Esito

La scheda ha superato 25 ore di uptime. Nel journal raccolto non risultano crash del processo dashboard, riavvii automatici per errore, OOM o errori di I/O/filesystem. Non è però un test di 24 ore della stessa applicazione: ci sono stati numerosi arresti e avvii ordinati, insieme a errori applicativi e warning del sistema da approfondire.

## Continuità e copertura

- Boot corrente: 30 settembre, 21:25:45. Uptime alle 22:39:19 del 1 ottobre: 25 h 13 min circa.
- Journal dashboard e kernel raccolti dal boot corrente. Warning di sistema raccolti nelle 24 ore precedenti le 22:37:37.
- Dal boot: 25 avvii della dashboard e 25 arresti ordinati registrati; il primo arresto riguarda il passaggio dal boot precedente. Nella finestra di 24 ore dei warning: 22 arresti e 22 avvii.
- Non risultano `Main process exited`, `Failed with result` o `Scheduled restart job` della dashboard nella finestra verificata. `NRestarts=0` al momento del controllo conferma solo il contatore corrente, non sostituisce la lettura della cronologia.
- Tratto continuo più lungo: 1 ottobre 00:49:25–16:44:23, **15 h 54 min 59 s** circa.
- Processo attuale: PID 135069, avviato alle 21:25:39; nessun successivo messaggio di errore della dashboard fino alla raccolta.
- Gli arresti sono regolari e compatibili con interventi/test; il journal dell'unità non identifica chi li abbia richiesti.

## Risorse attuali

Snapshot alle 22:39:19; non sono massimi/minimi storici di 24 ore.

| Indicatore | Valore |
|---|---|
| Dashboard | active/running |
| RSS processo | circa 175 MiB |
| PSS processo | circa 162 MiB |
| Memoria contabilizzata dal cgroup | circa 114 MiB, picco circa 117 MiB |
| CPU media del processo corrente | circa 2,2% di un core |
| CPU termica | 42,6–44,2 °C |
| GPU termica | 42,0 °C |
| RAM disponibile sistema | circa 5,3 GiB su 5,7 GiB |
| Swap utilizzata | 0 |
| Spazio libero microSD | circa 21 GiB; filesystem occupato al 28% |
| Unità systemd fallite | 0 |
| DisplayPort | DP-1 connected; 960×640 presente nei modi |

RSS, PSS e cgroup sono misure diverse e non vanno confrontate come se fossero equivalenti. Il processo attuale ha un RSS superiore al vecchio riferimento di 85–90 MiB della dashboard iniziale. Mancano campioni omogenei lungo le 24 ore per valutare una perdita di memoria. Il journal riporta un picco contabilizzato di 100,8 MiB per il tratto continuo notturno, ma le versioni dell'applicazione sono cambiate.

## Anomalie applicative

1. **Squadra preferita: tre `UnboundLocalError`**, alle 17:57:58, 18:54:27 e 18:59:02. La vecchia `_finished()` usava `interval` prima di assegnarlo, interrompendo quel callback e la programmazione del polling successivo. Il codice attualmente installato assegna `interval = profile_interval(...)`: la correzione è già presente. Nessuna ricorrenza nei log dopo le 19:04.
2. **Chiusura eventi: un `sqlite3.ProgrammingError`**, alle 20:54:49, durante la sequenza di arresto: un aggiornamento Sport tentava di usare il database già chiuso. Il codice installato contiene ora `_closed` e il controllo in `publish_snapshot()`. Nessuna ricorrenza nei successivi arresti registrati. Questo non equivale a un nuovo test mirato della race.
3. **Nove warning QML di binding circolare** in `DashboardOverlay.qml`, sei il 30 settembre alle 22:34 e tre il 1 ottobre alle 19:25. Coincidono con i cambi di connessione del tastierino. Il codice attuale conserva getter delle informazioni di sistema che possono aggiornare lo stato ed emettere notifiche durante la lettura: possibile causa da verificare con una riproduzione mirata. Il problema resta aperto.
4. **Tre errori provider Sport**: due MotoGP alle 16:44:40 e 17:47:37, uno sul dettaglio calcio alle 18:15:45. Non causano un crash del servizio. Il messaggio non distingue indisponibilità della rete da risposta non valida, quindi la causa remota non è attribuibile dai soli log.

Le copie locali e installate di `sport_team.py`, `events.py`, `app.py` e `DashboardOverlay.qml` coincidono per SHA-256.

## Sistema, rete e periferiche

- **Timeout MMC/SDIO:** nella finestra di 24 ore ci sono 47 `wait dma hold bit clear timeout` su `4020000.sdmmc` e 32 su `4021000.sdmmc`. La mappatura sysfs identifica il primo come microSD (`mmc1`, root su `mmcblk1p1`) e il secondo come periferica SDIO del Wi-Fi (`mmc2`).
- Sulla microSD gli episodi accompagnano il tuning periodico, circa ogni ora; seguono messaggi `tuning result`. Non risultano `EXT4-fs error`, `I/O error`, `Buffer I/O` o rimontaggio della root in sola lettura. I timeout sono reali; questi log non dimostrano un guasto della scheda né consentono di considerarli innocui senza analisi del driver.
- **Tastierino USB `413d:553a`:** disconnessioni il 30 settembre alle 22:34:36 e il 1 ottobre alle 19:25:16. Nel primo episodio il kernel segnala anche impossibilità di enumerazione e tenta un power cycle; il dispositivo viene riconosciuto di nuovo alle 22:34:43. Nel secondo viene riconosciuto dopo circa un secondo. Riscontro successivo dell'utente: entrambi gli episodi erano scollegamenti manuali. Questa voce è chiarita e non richiede interventi sul collegamento USB.
- **Wi-Fi:** NetworkManager registra quattro rinnovi DHCP regolari e nessuna transizione di disconnessione nel periodo estratto. I timeout SDIO restano un problema da approfondire anche con rete operativa.
- **Audio/Bluetooth:** 158 errori di inizializzazione del sink HDMI e 158 tentativi falliti di contattare BlueZ nelle 24 ore, sotto `user@1001.service` (utente smartpc). Sono rumore persistente di servizi della sessione utente; non sono errori del renderer dashboard.
- **Grafica:** nessun nuovo errore/reset GPU o DRM identificato dopo la fase iniziale di boot. Al boot sono presenti errori del kernel vendor, inclusi DRM/eDP e periferiche non inizializzate; distinguerli dagli eventi durante l'operatività.
- `coredumpctl` non è installato: la verifica non comprende un inventario dei core dump. L'assenza di crash della dashboard è basata sul journal systemd.

## Dati e persistenza

- Cache meteo aggiornata alle 22:25:40; bollettino Protezione Civile controllato alle 22:25:41, revisione `20261001_1408`.
- Account ChatGPT: cache `active`, sincronizzata alle 22:36:04; timer PC attivo e ultime esecuzioni riuscite.
- Cache Sport, squadra selezionata, F1 e MotoGP scritte alle 21:25 circa. Il timestamp del file prova un salvataggio, non l'attualità di ogni singolo campo. Il polling Sport è adattivo, con intervalli fino a sei ore fuori dalle finestre di attività.
- Tutti i JSON della cache esaminati sono leggibili. Database eventi: `PRAGMA quick_check` in sola lettura restituisce `ok`.
- Journal occupato: 48,7 MiB. Root ext4 ancora `rw,noatime,errors=remount-ro,commit=30`.

## Prossime verifiche consigliate

1. Riprodurre e correggere il binding QML circolare nelle informazioni di sistema.
2. Approfondire i timeout microSD/SDIO. Le disconnessioni USB sono state chiarite dall'utente come manuali.
3. Eliminare il rumore dei servizi audio/Bluetooth non utilizzati, dopo averne identificato l'attivazione.
4. Misurare una finestra continua con una versione fissa e campioni passivi di RSS/PSS, CPU e temperatura. I log attuali non dimostrano 60 fps costanti, assenza di schermi neri sul pannello o assenza di memory leak per 24 ore.

## Evidenze locali

- `dashboard.jsonl`: journal completo dell'unità dal boot corrente.
- `kernel.jsonl`: journal kernel dal boot corrente.
- `warnings.jsonl`: warning di sistema delle 24 ore estratte.
- `current-state.json`: snapshot risorse, cache, hash sorgenti e verifica database.
- `system-state.txt`: verifica finale del sistema e journal NetworkManager.
