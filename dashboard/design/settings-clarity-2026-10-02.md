# Struttura delle impostazioni e Wi-Fi — 2 ottobre 2026

La richiesta riguarda la suddivisione dei menu, con priorità a Notifiche. La nuova pagina Notifiche contiene solo gli accessi alle due funzioni, con stato della fascia oraria e spiegazione delle regole.

| Percorso | Contenuto |
| --- | --- |
| Impostazioni → Notifiche → Fascia silenzio | Attivazione, inizio e fine; orari inattivi quando il silenzio è disabilitato; stato attuale della fascia |
| Impostazioni → Notifiche → Avvisi sullo schermo | Meteo, Account e notifiche gol se Sport è disponibile |
| Impostazioni → Account ChatGPT | Soglie di utilizzo; separate dalle regole di presentazione degli avvisi |
| Impostazioni → Sport | Squadra, stagione, riepiloghi Home; collegamenti alle pagine centrali di notifiche e aggiornamenti |
| Impostazioni → Dati e aggiornamenti | Stato delle fonti e unico punto per il loro aggiornamento manuale |
| Menu → Informazioni | Dispositivo, Risorse, Rete, Dati; sola lettura |

I sottomenu conservano selezioni indipendenti: tornare dalla fascia silenzio, dalle categorie o da un collegamento Sport mantiene il focus di provenienza. Le liste restano ferme ai bordi. Il collegamento all'aggiornamento di Sport/F1/MotoGP apre la stessa pagina Dati e aggiornamenti con la fonte preselezionata, senza inviare una richiesta al semplice ingresso.

## Regole delle notifiche

Il comportamento del motore eventi resta quello esistente, ora esplicitato nelle pagine corrette:

| Categoria | Fuori fascia silenzio | Durante la fascia silenzio | Elenco Avvisi |
| --- | --- | --- | --- |
| Meteo/Account consentiti | Banner e urgenti | Solo urgenti | Disponibile |
| Meteo/Account nascosti | Nessuna interruzione | Nessuna interruzione | Disponibile |

Gli orari includono l'inizio ed escludono la fine e possono attraversare la mezzanotte. Disattivare la fascia rimuove solo la pausa dei banner, senza riabilitare categorie nascoste. I gol sono banner della squadra preferita: conservano la verifica live obbligatoria e rispettano il silenzio orario. La regolazione è nella pagina delle categorie; Sport contiene solo un collegamento.

## Aggiornamenti e Wi-Fi

Informazioni non avvia aggiornamenti delle fonti, né con 5 né con il click sulle righe. La scheda Dati indica il percorso della pagina centrale. Rimangono le acquisizioni mirate del dettaglio di una partita, sessione o pilota nelle rispettive viste.

Sul kernel della board `/proc/net/wireless` non esiste, mentre NetworkManager rileva la qualità della connessione. `SystemInfo` usa un `QProcess` asincrono per `nmcli --wait 2 -t -f ACTIVE,SIGNAL device wifi list ifname INTERFACCIA --rescan no`. Non vengono richieste scansioni, SSID o credenziali. La qualità è mostrata in percentuale con fonte e ora della lettura; non è RSSI in dBm. Il fallback aggiorna al massimo ogni 30 secondi, solo con Informazioni aperta, ha timeout di 2,5 secondi e si interrompe all'uscita. Un errore restituisce N/D e non conserva un segnale precedente come misura corrente.

I getter restano privi di I/O e segnali; gli snapshot delle altre risorse si aggiornano ogni cinque secondi durante Info.

## Verifica

- `check_settings.py`: navigazione dei sottomenu e focus al ritorno, orari inattivi, persistenza categorie, accessi centrali da Sport/F1, protezione delle notifiche gol, Info in sola lettura, pausa manuale e getter senza effetti collaterali. Un processo fittizio verifica qualità percentuale, errore, timeout e prosecuzione del timer Qt mentre la lettura è in corso.
- `check_events.py`: tutte le combinazioni di categoria abilitata/nascosta, fascia attiva/inattiva e priorità banner/urgente mantengono l'elenco e il conteggio non letti.
- Le prove usano preferenze, cache ed eventi isolati. Le immagini descrivono il processo di verifica e non una nuova acquisizione delle fonti online.

- PC, PySide6 6.11.2: dashboard, impostazioni, Sport, Motorsport e motore eventi superati. Orange Pi, PySide6 6.8.2.1: dashboard, impostazioni, Motorsport e motore eventi superati su copia isolata.
- EGLFS/KMS + OpenGL sulla board: prova delle nuove impostazioni e catture a 960×640 superate, `qmlWarnings: []`. Schermate dei due sottomenu Notifiche e Info Rete controllate visivamente. Qualità Wi-Fi reale rilevata: **54%**; interfaccia `wlan0` e IP della board corretti.
- Una prima prova estesa Motorsport è fallita sulla connessione simulata. Il timer di età del servizio, attivo anche con aggiornamenti automatici disabilitati, chiama correttamente `ensure(False)` e scollegava il flusso fittizio tra i tasti. La verifica ferma quel timer soltanto durante l'iniezione del flusso simulato e lo riattiva dopo la prova di disconnessione. Nessuna modifica al timer di produzione. La verifica corretta passa su PC e board.
- Installazione alle **00:04:15 del 2 ottobre**: servizio `active/running`, PID **202220**, `NRestarts=0` al controllo finale. I sei componenti runtime installati hanno hash identici ai file locali. Hash di `Dashboard.conf` identico prima, dopo e al controllo finale; nessun errore applicativo nei log di questo avvio fino al controllo finale.

La verifica non misura 24 ore di continuità, FPS sostenuti, un reboot o ricezione di allerte reali. La dashboard normale è stata fermata solo durante l'acquisizione EGLFS e l'installazione, poi riavviata. Le altre prove erano headless, con preferenze isolate.

## Evidenze e ripristino

- [Risultato EGLFS e misure reali](evidence/settings-clarity-2026-10-02/verification.json)
- [Notifiche: pagina principale](evidence/settings-clarity-2026-10-02/notifications.png)
- [Fascia silenzio](evidence/settings-clarity-2026-10-02/notification-quiet.png)
- [Categorie degli avvisi](evidence/settings-clarity-2026-10-02/notification-categories.png)
- [Segnale Wi-Fi](evidence/settings-clarity-2026-10-02/info-network.png)
- [Info Dati in sola lettura](evidence/settings-clarity-2026-10-02/info-data.png)
- [Prova Motorsport sulla board](evidence/settings-clarity-2026-10-02/motorsport-check.txt)
- [Installazione e hash delle preferenze](evidence/settings-clarity-2026-10-02/installation.txt)
- [Servizio e log successivi](evidence/settings-clarity-2026-10-02/post-install.txt)

Backup precedente a questa revisione: `/var/backups/smartpc-dashboard-20261002-before-settings-clarity`. Per ripristinarla sulla board:

```bash
sudo systemctl stop smartpc-dashboard
sudo cp -a /var/backups/smartpc-dashboard-20261002-before-settings-clarity/. /opt/smartpc/dashboard/
sudo systemctl start smartpc-dashboard
```
