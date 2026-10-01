# Impostazioni e Informazioni — 1 ottobre 2026

## Implementato

- Menu con accessi separati a Comandi, Impostazioni, Informazioni e Diagnostica.
- Impostazioni divise in Aspetto, Luminosità, Moduli visibili, Notifiche, Account ChatGPT, Sport, Dati e aggiornamenti. Sport raccoglie i sottomenu dei provider disponibili.
- Liste da quattro righe, indice visibile, focus fermo ai bordi e ritorno alla selezione precedente. Le etichette fisiche del tastierino restano 1 Indietro / 7 Home; la codifica degli eventi esistente è conservata.
- Tema e animazioni separati dalla luce; i livelli non applicabili alla modalità corrente sono visibili ma non modificabili. Minimo luce 20%, incremento 5%, fasce orarie persistenti.
- Soglie Account configurabili e persistenti, applicate al motore eventi senza riavvio: avviso da 1 a 99%, critico fino al 100% e sempre superiore all'avviso. Le variabili d'ambiente rimangono i valori iniziali in assenza di preferenze salvate.
- Aggiornamento manuale delle fonti con pausa minima di 30 secondi. Sport e Motorsport riusano i rispettivi percorsi manuali e i limiti dei provider; Account rilegge la cache del PC senza nuove autenticazioni.
- Informazioni su quattro schede: Dispositivo, Risorse, Rete, Dati. Distinzione tra uptime hardware e processo, RAM sistema e RSS/picco del processo, aggiornamento dati e connessione alla rete locale. Campi mancanti N/D.

## Correzione del binding

I getter precedenti di `SystemInfo` verificavano il tempo trascorso, leggevano il sistema e potevano emettere `changed` durante la valutazione di `systemState` da QML. Un'ulteriore valutazione dello stesso binding poteva quindi iniziare prima della conclusione della prima.

`system_info.py` prepara ora uno snapshot con timestamp stabile. I getter leggono esclusivamente lo snapshot. Un timer ogni cinque secondi raccoglie le informazioni mentre Info è aperta e viene fermato all'uscita. La lettura iniziale avviene una volta all'avvio; non ci sono comandi di rete o subprocess nei getter.

`SettingsPanel.qml` e `DeviceInfo.qml` separano impostazioni e informazioni da `DashboardOverlay.qml`. I modelli di Info e delle fonti vengono popolati soltanto per le rispettive schermate attive. I testi di Info usano `Text.NativeRendering`: nelle prime catture con il rendering predefinito alcuni glifi mostravano spostamenti/tagli transitori sul renderer della board. Le catture finali con rendering nativo sono state controllate visivamente.

## Verificato

- PC, PySide6 6.11.2: `check_dashboard.py`, `check_settings.py`, `check_sport_ui.py`, `check_motorsport_ui.py` superati.
- Orange Pi, PySide6 6.8.2.1 / Qt 6.8.2: regressioni dashboard, nuove impostazioni e Motorsport superate su una copia isolata prima dell'installazione.
- Nuova regressione: getter letti ripetutamente senza I/O/notifiche, timer attivo solo in Info, cambi simulati di connessione del tastierino, navigazione e ritorno del focus, limiti luce, persistenza soglie/animazioni/notifiche, demo senza richieste esterne e pausa tra richieste manuali.
- Prova EGLFS/KMS + OpenGL sulla board, catture 960×640 e `qmlWarnings: []`. Il servizio normale è stato fermato solo durante le catture e ripristinato al termine. Le preferenze di prova sono isolate e non modificano quelle del kiosk.
- Dopo l'installazione delle 23:36:39: servizio `active/running`, PID 190234, `NRestarts=0`, nessun errore applicativo nei log del nuovo avvio fino al controllo finale. Hash dei sette componenti runtime uguali alle copie locali; hash di `Dashboard.conf` identico prima e dopo. [Stato finale](evidence/settings-2026-10-01/post-install.txt).
- Il primo programma di acquisizione usciva dall'event loop dell'applicazione tra le catture e terminava con SIGSEGV prima della prima immagine. Corretto il programma di verifica usando un `QEventLoop` locale: EGLFS mantiene le risorse grafiche fino alla fine. Le prove successive hanno completato regolarmente tutte le catture.

Le catture delle risorse descrivono il processo di verifica; le fonti nelle schermate di prova sono simulate/non disponibili e non certificano una nuova acquisizione online. Non sono stati provocati scollegamenti fisici del tastierino, allerte reali o un reboot della scheda. Questa verifica non misura 24 ore di continuità né 60 fps sostenuti.

## Installazione e ripristino

Backup della dashboard prima dell'intervento: `/var/backups/smartpc-dashboard-20261001-before-settings`.

Sono installati soltanto i componenti di questa revisione e i controlli aggiornati; configurazione del dispositivo, cache, database e preferenze persistenti sono conservati. Gli hash delle preferenze prima/dopo sono in [installation.txt](evidence/settings-2026-10-01/installation.txt).

Per il rollback sulla board:

```bash
sudo systemctl stop smartpc-dashboard
sudo cp -a /var/backups/smartpc-dashboard-20261001-before-settings/. /opt/smartpc/dashboard/
sudo systemctl start smartpc-dashboard
```

I nuovi file non referenziati dal vecchio launcher possono restare nella cartella durante il rollback. Le nuove chiavi di preferenza vengono ignorate dalla versione precedente.

## Evidenze

- [Risultato EGLFS](evidence/settings-2026-10-01/verification.json)
- [Menu impostazioni](evidence/settings-2026-10-01/settings.png)
- [Luminosità](evidence/settings-2026-10-01/brightness-manual.png)
- [Menu Sport](evidence/settings-2026-10-01/sport-settings-menu.png)
- [Info dispositivo](evidence/settings-2026-10-01/info-device.png)
- [Info risorse](evidence/settings-2026-10-01/info-resources.png)
- [Info rete](evidence/settings-2026-10-01/info-network.png)
- [Info dati](evidence/settings-2026-10-01/info-data.png)

Le due disconnessioni USB emerse nell'audit delle 24 ore sono state chiarite dall'utente come movimenti manuali del cavo; nessun intervento sul collegamento USB.
