# SmartPC Dashboard v0.4

Dashboard Qt Quick per Orange Pi Zero 3W e display Hagibis 960×640 a 60 Hz. La v0.4 applica la [specifica UX](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/design/ux-navigation-v2.md): un dato dominante per vista, Home dinamica, due assi di navigazione e tasti sempre coerenti. La board usa Orange Pi Debian 13, Qt 6, EGLFS/KMS e GPU PowerVR.

## Esperienza

- **Home:** ora e meteo occupano la schermata. Una tessera «prossimo evento» compare solo quando lo stato contiene un evento valido; per ora si può simulare nella demo. Nessun evento reale viene inventato.
- **Orizzontale:** Oggi ↔ Meteo ↔ Account ChatGPT. Sport, Casa e PC entreranno nel carosello quando avranno dati reali. I moduli nascosti sono saltati senza lasciare schermate vuote.
- **Verticale:** Oggi: Ora/Giornata. Meteo: Adesso/Previsioni. Ogni famiglia ricorda la propria vista.
- **Menu:** Comandi, Impostazioni e Diagnostica. Impostazioni contiene **Aspetto e dispositivo** (tema, luminosità, stato) e **Moduli visibili**. Quest'ultima voce mostra le famiglie disponibili, permette di mostrare o nascondere Meteo e Account ChatGPT e conserva la scelta dopo il riavvio. Oggi resta sempre visibile.
- **Avvisi:** casella vuota fino al motore eventi v0.5.
- L'intestazione non ripete il marchio o la modalità notte. Dati assenti, aggiornamento e offline sono indicati esplicitamente. La transizione tra viste dura 160 ms.

| 1 Home | 2 Su | 3 Avvisi |
| --- | --- | --- |
| 4 Sinistra | **5 OK** | 6 Destra |
| 7 Indietro | 8 Giù | 9 Menu |

La mini tastiera USB `413d:553a` è letta da `keypad.py`, che traduce le scorciatoie firmware esistenti nelle posizioni 1–9. I LED conservano la configurazione attuale. Sul PC si possono usare frecce, Invio, Esc e i numeri. Il menu Comandi mostra la legenda completa.

## Stato dei moduli

`module_state.py` definisce l'involucro comune; `weather.py` e `account.py` espongono `moduleState`, mentre `state.py` espone a QML `weatherState`, `accountState` e `systemState`. Ogni stato usa:

```json
{
  "version": 1,
  "status": "active",
  "source": "Open-Meteo",
  "updatedAt": 1790720000,
  "data": {},
  "error": ""
}
```

`status` vale `active`, `updating`, `stale`, `offline`, `error` o `unavailable`. `updatedAt` è l'istante dell'ultima risposta valida; zero significa nessun dato. QML visualizza stato e origine, senza gestire chiamate di rete. Il provider Meteo effettua richieste in un `QRunnable`, ogni 15 minuti, con timeout di 12 secondi; salva atomicamente l'ultima risposta valida nella cache utente. La previsione comprende tre giorni. L'assenza di rete non trasforma la cache in un dato nuovo. La posizione corrente è Angri, Salerno. I dati provengono da Open-Meteo.

Le preferenze del tema, della luminosità e dei moduli visibili sono salvate con `QSettings` nell'area dati dell'utente del servizio. Nessuna credenziale è scritta nel progetto o inviata a QML.

## Account ChatGPT e crediti

**Account ChatGPT**, terzo modulo nello scorrimento orizzontale, mostra il piano collegato a Codex, le finestre di utilizzo con percentuale usata e ora di ripristino, il saldo dei crediti quando la fonte lo fornisce e il numero di eventuali reset del limite. Saldo e reset sono presentati separatamente. I dati riguardano l'uso ChatGPT/Codex restituito da Codex App Server: non sono la fatturazione dell'API OpenAI né un conteggio completo di tutte le normali chat ChatGPT.

`account_sync.py` interroga **Codex App Server sul PC**, senza stampare o trasferire token, email o ID account. Il PC invia via SSH un riepilogo JSON alla board in `/var/cache/smartpc-dashboard/account-chatgpt.json`, con permessi `600` e sostituzione atomica. Il servizio della board legge soltanto questo file. Quando la sincronizzazione manca da oltre 30 minuti, la pagina conserva i valori precedenti ma mostra **NON AGGIORNATO**; se il file manca o l'account non è collegato, dichiara il dato assente. Un campo credito assente non diventa mai zero.

La sincronizzazione manuale dal PC è:

```bash
python3 dashboard/account_sync.py
```

`SMARTPC_ACCOUNT_HOST` può sostituire l'host SSH predefinito `smartpc@192.168.1.179`; `--identity` seleziona una chiave diversa. Le unità in `dashboard/systemd/` installate in `~/.config/systemd/user/` eseguono il controllo ogni 10 minuti mentre il PC è acceso; il timer utente richiede che il servizio systemd dell'utente sia attivo anche dopo il logout. Per verificarle: `systemctl --user status smartpc-account-sync.timer` e `systemctl --user start smartpc-account-sync.service`. L'integrazione è di sola lettura: non acquista crediti né consuma i reset disponibili. La pagina evidenzia l'utilizzo dall'80% e dal 95%; queste soglie si possono cambiare con `SMARTPC_ACCOUNT_WARNING_PERCENT` e `SMARTPC_ACCOUNT_CRITICAL_PERCENT` nell'ambiente del servizio dashboard, poi riavviandolo. Gli avvisi globali arriveranno con il motore eventi v0.5.

In **Menu → Sistema** i tasti `2/8` selezionano una riga, `4/6` modificano il valore e `5` passa al valore successivo. Tema offre auto/giorno/notte. Luminosità offre auto/manuale; il livello manuale e i livelli automatici giorno/notte vanno dal 20% al 100% a passi del 5%. In Auto, il valore predefinito è 100% dalle 07:00 alle 20:59 e 65% dalle 21:00 alle 06:59; entrambi i livelli e gli orari sono modificabili. Il tema Auto usa gli stessi orari. Il valore effettivo compare nella schermata Sistema.

Il pannello Hagibis non espone un controllo retroilluminazione in `/sys/class/backlight` né DDC. Questa regolazione attenua **l'immagine Qt**, non la retroilluminazione fisica e quindi non garantisce un risparmio energetico del pannello. La soglia minima del 20% mantiene visibili i comandi per recuperare il livello desiderato.

## Esecuzione e demo

```bash
./dashboard/run.sh --desktop
./dashboard/run.sh --device
```

La prima modalità richiede PySide6 o un runtime Qt 6 QML; la seconda usa EGLFS/KMS. La schermata reale del meteo richiede PySide6. Il servizio installato in `/opt/smartpc/dashboard` è `smartpc-dashboard.service`.

Per provare sul PC il layout senza rete:

```bash
./dashboard/run.sh --demo
```

`F12` apre il pannello demo: un clic cambia meteo online/offline/assente, l'altro aggiunge o rimuove il prossimo evento. I tasti della dashboard continuano a cambiare vista. La demo non chiama Open-Meteo.

`Main.qml` gestisce navigazione e composizione; `HomeNow.qml`, `HomeDay.qml`, `WeatherNow.qml`, `WeatherForecast.qml` e `AccountChatGPT.qml` sono le viste indipendenti. `DashboardOverlay.qml` contiene menu e impostazioni. Una nuova famiglia va aggiunta al registro `allFamilies` in `Main.qml`, insieme alle sue viste e al relativo provider; solo dopo entra in **Moduli visibili**. In modalità `--device`, `run.sh` nasconde il cursore software di EGLFS anche quando la mini tastiera USB espone un'interfaccia mouse.

## Verifiche e ripristino

`check_dashboard.py` esegue un controllo rapido di caricamento QML, navigazione, visibilità delle cinque viste, schermata Account ChatGPT nel carosello, stati demo, impostazioni, visibilità persistente dei moduli e luminosità manuale/auto senza usare la rete. Si può avviare con `python3 dashboard/check_dashboard.py` dove PySide6 è installato.

La v0.2 aveva già superato i test di meteo online, cache offline e riavvio senza Wi-Fi. Sul dispositivo, il servizio riparte automaticamente dopo un crash; la configurazione è in [smartpc-dashboard.service](/home/giuseppe/Documenti/Workspace/SmartPC/os/system/smartpc-dashboard.service). La scena diagnostica visualizza FPS e intervallo p95 tra frame, ma un valore basso su una schermata ferma è normale: non misura da solo la fluidità delle transizioni. `benchmark.py` misura intervalli di frame mentre simula cambi di vista sul renderer EGLFS/GPU; va eseguito con il servizio fermo. `soak.py` osserva memoria, temperatura e stabilità del servizio senza inviare input.

Prima di installare una nuova versione sulla board, salvare `/opt/smartpc/dashboard` in `/var/backups/`. Il backup della v0.3 precedente al modulo Account è `/var/backups/smartpc-dashboard-v03-before-account`. Per ripristinare, copiare i file salvati nella cartella dell'app e riavviare il servizio; disabilitare anche `smartpc-account-sync.timer` sul PC se la funzione non serve più. Non serve Git per questo passaggio; la creazione del repository è rimandata.

Controlli utili:

```bash
sudo systemctl status smartpc-dashboard
sudo journalctl -u smartpc-dashboard --since "10 minutes ago"
sudo systemctl restart smartpc-dashboard
```

Il target è 960×640 a 60 Hz. Le scene future andranno misurate sulla board. Il vecchio timer Xorg per la luminosità è disabilitato nel kiosk EGLFS; il conflitto dell'aggiornamento Xorg resta annotato nel [resoconto OS](/home/giuseppe/Documenti/Workspace/SmartPC/os/board-audit-2026-09-29.md).
