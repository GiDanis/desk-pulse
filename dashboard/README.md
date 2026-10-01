# SmartPC Dashboard v0.6

Dashboard Qt Quick per Orange Pi Zero 3W e display Hagibis 960×640 a 60 Hz. La v0.6 applica la [specifica UX](design/ux-navigation-v2.md): un dato dominante per vista, Home dinamica, due assi di navigazione, tasti coerenti e avvisi condivisi. La board usa Orange Pi Debian 13, Qt 6, EGLFS/KMS e GPU PowerVR.

## Esperienza

- **Home:** ora e meteo occupano la schermata. Una tessera «prossimo evento» compare solo quando esiste un evento futuro valido, per esempio un'allerta prevista per domani. Nessun evento viene inventato per riempire lo spazio.
- **Nuovi avvisi:** sulle due viste Home un badge discreto nell'intestazione indica quanti avvisi della casella non sono stati letti e ricorda il tasto **3**. Compare anche per gli avvisi ambientali e dopo la fine del banner. Aprire la casella non segna tutto come letto: il badge si aggiorna quando si apre il dettaglio di ciascun evento, oppure quando l'evento scade o viene annullato. Durante banner, overlay e menu il badge resta nascosto.
- **Orizzontale:** Oggi ↔ Meteo ↔ Account ChatGPT ↔ Serie A ↔ F1 ↔ MotoGP. Casa e PC entreranno nel carosello quando avranno dati reali. I moduli nascosti sono saltati senza lasciare schermate vuote.
- **Verticale:** Oggi: Ora/Giornata. Meteo: Adesso/Previsioni. Serie A: Prossime/In corso quando esiste/Risultati/Classifica. F1 e MotoGP: Programma/In corso quando esiste/Risultati/Classifica. Ogni famiglia ricorda la propria vista.
- **Menu:** Comandi, Impostazioni e Diagnostica. Impostazioni contiene **Aspetto e dispositivo** (tema, luminosità, stato), **Moduli visibili**, **Notifiche**, **Sport · Serie A**, **Sport · F1** e **Sport · MotoGP**. Moduli visibili mostra le famiglie disponibili, permette di mostrare o nascondere Meteo, Account ChatGPT e ogni sport separatamente e conserva la scelta dopo il riavvio. Oggi resta sempre visibile.
- **Avvisi:** il tasto 3 apre la casella da qualsiasi vista. Gli avvisi importanti ricevono un banner breve; quelli prioritari aprono un overlay. Indietro chiude l'overlay e restituisce la vista, il menu e la selezione precedenti.
- **Notifiche:** Menu → Impostazioni → Notifiche permette sempre di attivare o disattivare la fascia di silenzio e regolare inizio e fine a passi di 15 minuti. L'impostazione iniziale è 22:00–07:00, nel fuso Europe/Rome. Il silenzio trattiene i banner fino al termine della fascia, se ancora validi; gli avvisi prioritari restano visibili. Due controlli separati permettono di disattivare le interruzioni di Meteo e Account: gli eventi rimangono consultabili nella casella, ma quella categoria non mostra banner o overlay.
- L'intestazione non ripete il marchio o la modalità notte. Dati assenti, aggiornamento e offline sono indicati esplicitamente. La transizione tra viste dura 160 ms.

| 1 Indietro | 2 Su | 3 Avvisi |
| --- | --- | --- |
| 4 Sinistra | **5 OK** | 6 Destra |
| 7 Home | 8 Giù | 9 Menu |

La mini tastiera USB `413d:553a` è letta da `keypad.py`, che traduce le scorciatoie firmware esistenti nelle posizioni 1–9. I LED conservano la configurazione attuale. Sul PC si possono usare frecce, Invio, Esc e i numeri. Il menu Comandi mostra la legenda completa.

## Stato dei moduli

La **v0.7 Casa è in sviluppo** con API cloud Tuya dirette. `tuya_core.py` e `tuya_probe.py` permettono la prova manuale di inventario e stati Smart Life; `check_tuya.py` verifica protocollo e cache con risposte simulate. Nessuna schermata Casa o sincronizzazione periodica è ancora attiva. Token e rinnovo verificati sul cloud reale; lettura dispositivi impedita dal data center sospeso (`28841107`). [Configurazione Tuya, aggiunte/modifiche e limiti](design/v07-tuya-api-setup.md), [analisi reale](design/v07-tuya-live-analysis.md), [piano aggiornato](design/v07-tuya-direct-plan.md).

`module_state.py` definisce l'involucro comune; `weather.py`, `account.py` e `sport.py` espongono `moduleState`, mentre `state.py` espone a QML `weatherState`, `accountState`, `sportState`, `racingStates` (F1/MotoGP) e `systemState`. Ogni stato usa:

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

## Sport · Serie A

La v0.6 integra **FotMob REST diretto** per calendario completo, classifica e dettaglio; **ESPN** è la riserva quando la fonte principale non restituisce dati validi. Non servono API key o abbonamenti. Gli endpoint interni possono cambiare: un errore conserva l'ultimo dato valido e indica origine/ora. Nel fallback ESPN il calendario è limitato ai giorni vicini restituiti dalla fonte, esplicitamente indicato nella schermata.

- Da Home, **4** apre MotoGP; **4, 4, 4** porta a Serie A con tutti i moduli visibili; **2/8** cambiano vista: Prossime, In corso quando presente, Risultati, Classifica. **5** apre l’elenco della vista corrente. In elenco **4/6** alternano partite e classifica, **2/8** scorrono e **5** apre il dettaglio. Classifica completa, tre righe visibili per pagina.
- **Prossime** mostra tutte le partite future della prossima giornata, anche con lo stesso orario, tre per pagina. Le pagine si alternano ogni otto secondi, fermandosi quando si apre un pannello. **In corso** usa lo stesso riepilogo per tutti gli incontri attivi. **Classifica** è direttamente raggiungibile con 2/8 e 5 apre tutte le 20 posizioni. **Risultati** mostra l'ultimo turno; il dettaglio offre marcatori e, quando disponibili, possesso, xG, tiri in porta e moduli delle formazioni.
- **Menu → Impostazioni → Sport** permette di scegliere squadra preferita, tessera della prossima partita in Home, stagione corrente/precedente e aggiornamento manuale. Le scelte sono persistenti. La tessera Home richiede squadra scelta e partita entro sette giorni; di default è disattivata.
- Il timing viene acquisito con polling adattivo (riposo 6 ore, prepartita 15 minuti, avvicinamento/incontro 30 secondi), con timeout, header di cache, backoff e `Retry-After`. Una risposta valida senza cambiamenti non diventa vecchia solo perché il punteggio resta 0–0.
- La vista **In corso** esiste quando il provider segnala un incontro attivo e plausibile. In questa release il feed è indicato **da collaudare**; il badge Live e le notifiche gol richiedono la prova durante una partita prevista nel piano. `SMARTPC_SPORT_LIVE_VERIFIED=1` è il gate tecnico, da attivare dopo la verifica, non un rilevatore automatico di qualità.
- Notifiche disattivate inizialmente; il motore predisposto controlla evento, punteggio e pending VAR, deduplica e imposta una baseline dopo avvio/riconnessione/cambio fonte. ESPN non ha una conferma VAR dimostrata: i suoi eventi non producono overlay gol.

`sport_core.py` contiene adapter, validazione, cache e policy; `sport.py` esegue rete/parsing in worker Qt. `SportView.qml` e `SportOverlay.qml` compongono le viste. Cache in `QStandardPaths.CacheLocation/sport.json` e archivi delle ultime due stagioni. Sul servizio: `/var/cache/smartpc-dashboard/SmartPC/SmartPC/`. Il registro gol è `/var/lib/smartpc-dashboard/sport-goals.json`; credenziali e dataset di prova non entrano nello stato di produzione. Dopo un riavvio offline i dati sono etichettati precedenti, senza nuovi gol. I risultati conclusi vengono ricontrollati e possono essere corretti.

`check_sport.py` verifica normalizzazione, cache atomica, stato/freschezza, errori, VAR e baseline. `check_sport_ui.py` verifica navigazione, classifica completa, dettaglio, fonte visibile, preferenze e recupero offline. Gli estratti storici in `fixtures/` servono esclusivamente a queste verifiche. `verify_sport_board.py` raccoglie dati REST reali e catture/misure EGLFS; richiede il kiosk fermo per possedere il display. Il [resoconto v0.6](design/v06-sport-release.md) distingue prove completate e limiti.

### La mia squadra

**Serie A → La mia squadra → 5** permette di scegliere una preferita. Il calendario include **tutte le competizioni disponibili**, con filtro Solo Serie A. Quattro schede: **Calendario, Risultati, Info, Rosa**; 4/6 cambia scheda, 2/8 scorre, 5 apre una partita o conferma la scelta. In Info puoi cambiare o rimuovere la preferita e aggiornare il profilo.

Preferenza e profilo sono persistenti. Allenatore, stadio, capienza, bilancio Serie A e giocatori vengono mostrati quando disponibili. Le date da confermare restano tali; in assenza del profilo completo viene dichiarato il calendario parziale Serie A. La tessera opzionale Home resta relativa alla Serie A.

Adapter e worker: `sport_team_core.py`, `sport_team.py`; cache per club `sport-team-{id}.json`. Verifiche: `check_sport_team.py`, `check_sport_team_ui.py`; acquisizione dati reali sulla board: `verify_sport_team_board.py`. [Implementazione, prove sul display e limiti](design/v06-favourite-team-release.md).

### Fantacalcio

Nel dettaglio delle sole partite **Serie A** compare **Fantacalcio**: formazione, titolari, subentrati e panchina, con **voto base e fantavoto della Redazione Fantacalcio**. 4/6 cambia scheda, 2/8 scorre, 5 cambia squadra. Per aggiornare manualmente i voti, 2 sopra il primo calciatore e 5 su Aggiorna voti.

La scheda funziona anche dal calendario della preferita. Le partite future attendono la pubblicazione; valori assenti e SV restano distinguibili. Cache atomica per giornata `fantacalcio-{stagione}-{giornata}.json`, richieste in worker e fonte/data indipendenti dal dettaglio FotMob. Un errore conserva gli ultimi voti validi.

[Implementazione, fonte, verifiche sul display e limiti](design/v06-fantacalcio-release.md). Test: `check_fantacalcio.py` e `check_fantacalcio_ui.py`; acquisizione reale: `verify_fantacalcio_board.py`.

## Sport · F1 e MotoGP

Dal modulo Serie A, **6** apre F1 e un altro **6** MotoGP. **2/8** cambiano vista; **5** apre calendario → GP → sessione oppure la classifica completa. **4/6** nel dettaglio alternano risultati/informazioni e, nella classifica F1, Piloti/Costruttori. **1** torna alla selezione precedente. Il programma mostra subito l'orario della gara oltre alle prossime sessioni.

- **F1:** Jolpica per programma, risultati Gara/Qualifiche/Sprint, Piloti e Costruttori; OpenF1 gratuito per risultati Libere/Qualifiche Sprint e stint delle sessioni concluse dal 2023; SignalR Core via QtWebSockets per il timing.
- **MotoGP:** PulseLive per programma filtrato MotoGP, risultati delle sessioni e classifica piloti; gateway lite per il timing. Altre categorie e test sono esclusi.
- Stagione corrente/precedente selezionabile in **Menu → Impostazioni → Sport · F1 / MotoGP**; anche prossima gara in Home, disattivata inizialmente, e aggiornamento manuale. Cache persistenti separate per sport/anno; fonte, orari italiani e dati precedenti visibili.
- Nessuna API key o abbonamento. I badge Live richiedono il collaudo durante una sessione: `SMARTPC_F1_LIVE_VERIFIED` e `SMARTPC_MOTOGP_LIVE_VERIFIED`, entrambi inizialmente disattivati. La connessione F1 è stata provata con un referto concluso; la latenza attiva e il mapping del gateway MotoGP restano aperti.

Sulla board serve `python3-pyside6.qtwebsockets`, controllato anche da `scripts/setup-board.sh`. Implementazione, controlli, catture reali, dipendenze e ripristino nel [resoconto motorsport](design/v06-motorsport-release.md).

### Dettagli del weekend e delle sessioni

Nel weekend **4/6** cambia tra **Sessioni / Circuito / Riepilogo**. MotoGP aggiunge lunghezza, curve, rettilineo, giri Gara/Sprint, distanza e record; nella scheda Sessione mostra le condizioni registrate di pista, aria/asfalto e umidità. F1 mostra località/paese disponibili da Jolpica e il riepilogo delle sessioni caricate.

Nei risultati **5** apre i dettagli del pilota in quella sessione: posizione, tempo, punti, giri e informazioni del team/moto. F1 aggiunge griglia, variazione griglia-arrivo, giro veloce, Q1/Q2/Q3 e schede **Soste / Giri / Gomme**. La durata Jolpica delle soste è il tempo in pit lane. Gomme indica mescola, intervallo di giri e usura all'inizio dello stint. Non è prevista una preferenza pilota.

Nel timing **4/6** cambia **Tempi / Pista / Direzione** e **5** apre i tempi del singolo pilota. I campi avanzati compaiono solo se ricevuti; i badge Live restano subordinati alla verifica attiva. **1 Indietro / 7 Home** sono le etichette del tastierino fisico.

Non servono registrazioni o API key. OpenF1 viene interrogato fuori dalla finestra a pagamento: sessione conclusa da almeno 30 minuti; l'adapter applica anche una soglia prudente di due ore dall'inizio. Richieste opzionali in worker, cache persistente e fonti/date distinte; un errore aggiuntivo conserva il risultato principale. [Dettagli, prove reali e ripristino](design/v06-racing-details-release.md).

## Revisione del codice Sport

La revisione del 1 ottobre riusa le presentazioni F1/MotoGP e i referti già caricati, sposta il salvataggio Serie A nel worker e conserva i dettagli dei piloti durante gli aggiornamenti. Include protezioni alla chiusura e correzioni dei delta SignalR. **5 Aggiorna** mantiene il controllo manuale con pausa di 30 secondi. [Misure sulla board, verifiche e ripristino](design/v06-sport-code-review.md). Regressioni mirate: `check_sport_optimization.py`.

## Account ChatGPT e crediti

**Account ChatGPT**, terzo modulo nello scorrimento orizzontale, mostra il piano collegato a Codex, le finestre di utilizzo con percentuale usata e ora di ripristino, il saldo dei crediti quando la fonte lo fornisce e il numero di eventuali reset del limite. Saldo e reset sono presentati separatamente. I dati riguardano l'uso ChatGPT/Codex restituito da Codex App Server: non sono la fatturazione dell'API OpenAI né un conteggio completo di tutte le normali chat ChatGPT.

`account_sync.py` interroga **Codex App Server sul PC**, senza stampare o trasferire token, email o ID account. Il PC invia via SSH un riepilogo JSON alla board in `/var/cache/smartpc-dashboard/account-chatgpt.json`, con permessi `600` e sostituzione atomica. Il servizio della board legge soltanto questo file. Quando la sincronizzazione manca da oltre 30 minuti, la pagina conserva i valori precedenti ma mostra **NON AGGIORNATO**; se il file manca o l'account non è collegato, dichiara il dato assente. Un campo credito assente non diventa mai zero.

La sincronizzazione manuale dal PC è:

```bash
python3 dashboard/account_sync.py
```

`SMARTPC_ACCOUNT_HOST` può sostituire l'host SSH predefinito `smartpc@192.168.1.179`; `--identity` seleziona una chiave diversa. Le unità in `dashboard/systemd/` installate in `~/.config/systemd/user/` eseguono il controllo ogni 10 minuti mentre il PC è acceso; il timer utente richiede che il servizio systemd dell'utente sia attivo anche dopo il logout. Per verificarle: `systemctl --user status smartpc-account-sync.timer` e `systemctl --user start smartpc-account-sync.service`. L'integrazione è di sola lettura: non acquista crediti né consuma i reset disponibili. La pagina evidenzia l'utilizzo dall'80% e dal 95%; queste soglie si possono cambiare con `SMARTPC_ACCOUNT_WARNING_PERCENT` e `SMARTPC_ACCOUNT_CRITICAL_PERCENT` nell'ambiente del servizio dashboard, poi riavviandolo. Il motore eventi crea una voce ambientale all'80% e un banner al 95%, solo da dati ancora aggiornati; non ripete l'avviso a ogni sincronizzazione.

## Motore eventi e allerta meteo

`event_core.py` conserva in SQLite identità, priorità, validità e stato di consegna degli eventi. `events.py` collega il motore a Qt e offre ai moduli un ingresso comune: un modulo consegna il proprio snapshot di eventi, il motore decide casella, banner, overlay e tessera futura della Home. Un aggiornamento identico non ricompare; una priorità aumentata può comparire di nuovo. Gli eventi scaduti o rimossi dalla fonte escono dalla casella. Il database si trova nella directory di stato del servizio (`/var/lib/smartpc-dashboard/events.sqlite3` sulla board) e i record più vecchi di sette giorni vengono eliminati.

### Contratto per nuovi moduli

Ogni modulo chiama `EventService.publish_snapshot(source, events)` sul thread Qt principale; i risultati di un worker arrivano tramite un segnale. Lo snapshot completo sostituisce soltanto gli eventi della propria fonte. Una lista vuota valida li annulla; un errore di rete deve conservare lo snapshot precedente. L'ID deve essere stabile e contenere il prefisso della fonte. Esempio:

```python
event_service.publish_snapshot("casa", [{
    "version": 1, "id": "casa:porta:20260930", "source": "casa",
    "sourceLabel": "Casa", "category": "casa", "priority": 2,
    "bannerSize": "large",
    "title": "Porta aperta", "detail": "Ingresso aperto da cinque minuti",
    "issuedAt": now, "startsAt": now, "expiresAt": now + 600,
    "revision": "1", "sourceUrl": "", "showOnHome": False,
}])
```

Le priorità sono `1` ambientale (casella), `2` importante (banner di otto secondi), `3` urgente (overlay fino alla conferma o alla scadenza). `notificationRank`, opzionale e uguale alla priorità per default, permette di distinguere aumenti di gravità nella stessa presentazione: l'allerta arancione vale 3 e la rossa 4. `revision` aggiorna il contenuto senza ripetere la consegna. `showOnHome` abilita solo la tessera di un evento futuro valido. I componenti degli avvisi sono comuni a tutte le fonti; il modulo non crea un proprio banner.

Ogni evento di priorità `2` sceglie il formato con `bannerSize`:

| Valore | Componente | Presentazione |
| --- | --- | --- |
| `"small"` (predefinito) | `EventBanner.qml` | Fascia in basso, titolo e descrizione su una riga |
| `"large"` | `EventLargeBanner.qml` | Pannello nell'area centrale, titolo su due righe, descrizione su tre righe e fonte |

Il banner grande riusa lo stesso componente grafico con `large: true`. Entrambi lasciano disponibili i comandi, non cambiano vista o focus, si chiudono dopo otto secondi e rispettano la fascia di silenzio e i controlli per categoria. Il tasto 3 apre la casella e nasconde il banner durante la consultazione. Il formato non modifica priorità o stato di consegna: cambiare solo `bannerSize` su un evento già mostrato non lo fa ricomparire. Per gli eventi urgenti resta l'overlay `EventUrgent.qml`.

`weather_alerts.py` legge ogni 30 minuti il bollettino pubblico di criticità del Dipartimento della Protezione Civile e i suoi dati di zona. Seleziona **Angri** dall'elenco dei comuni, poi considera i rischi idraulico, temporali e idrogeologico per oggi e domani. Un'allerta gialla genera un banner; arancione o rossa un overlay prioritario. Il bollettino è una valutazione quotidiana, con possibili correzioni: non è un feed di emergenza in tempo reale. La schermata Avvisi indica quando la fonte non è aggiornata; un errore di rete non trasforma i dati precedenti in una nuova allerta e non inventa «nessuna allerta».

Il provider salva atomicamente l'ultimo bollettino valido in `$XDG_CACHE_HOME/smartpc-dashboard/dpc-bulletin.json` (`/var/cache/smartpc-dashboard/smartpc-dashboard/dpc-bulletin.json` sulla board). La cache contiene chiave, ora di emissione, ultimo download, ultima verifica e proprietà della zona di Angri per oggi/domani; non conserva le geometrie nazionali. Dopo avere letto la pagina ufficiale, una chiave invariata riusa metadati e mappe già validati. Il file temporaneo viene sincronizzato e sostituito con `os.replace`; una risposta incompleta o non valida conserva il file precedente. Se il disco non è scrivibile, i dati validi restano utilizzabili nella sessione e la fonte segnala «cache non salvata».

All'avvio gli eventi vengono ricostruiti dalla cache senza attendere la rete, mantenendo le scadenze originali e lo stato letto/consegnato di SQLite. I dati caricati da disco sono indicati come **cache · da verificare**, con `sourceCheckedAt` e `sourceFetchedAt` precedenti; un fallimento della rete non aggiorna queste ore. La revisione della fonte è salvata insieme agli eventi anche quando il bollettino è vuoto: una vecchia cache non può far ricomparire un'allerta annullata da un bollettino più recente. Dopo la fine della validità la cache non produce più allerte. La demo in memoria non legge questa cache.

Le preferenze della fascia di silenzio sono salvate con le altre impostazioni in `QSettings`. Il tasto 3 e il menu sono sempre disponibili; un banner non sposta il focus. Nell'overlay prioritario, 5 apre il dettaglio, 7 lo chiude tornando al punto precedente e 1 lo chiude tornando alla Home. La casella mostra gli avvisi in corso o futuri, fino a tre righe per pagina; 2/8 selezionano e 5 apre il dettaglio.

In **Menu → Impostazioni → Aspetto e dispositivo** i tasti `2/8` selezionano una riga, `4/6` modificano il valore e `5` passa al valore successivo. Tema offre auto/giorno/notte. Luminosità offre auto/manuale; il livello manuale e i livelli automatici giorno/notte vanno dal 20% al 100% a passi del 5%. In Auto, il valore predefinito è 100% dalle 07:00 alle 20:59 e 65% dalle 21:00 alle 06:59; entrambi i livelli e gli orari sono modificabili. Il tema Auto usa gli stessi orari. Il valore effettivo compare nella schermata.

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

`F12` apre il pannello demo: si possono cambiare meteo online/offline/assente, tessera evento e scenari Avvisi (nessuno, prossimo, banner, banner grande, urgente). I tasti della dashboard continuano a cambiare vista. La demo non chiama Open-Meteo o il bollettino ufficiale e usa un database eventi in memoria, separato dagli avvisi reali.

`Main.qml` gestisce navigazione e composizione; `HomeNow.qml`, `HomeDay.qml`, `WeatherNow.qml`, `WeatherForecast.qml` e `AccountChatGPT.qml` sono le viste indipendenti. `DashboardOverlay.qml` contiene menu e impostazioni. Una nuova famiglia va aggiunta al registro `allFamilies` in `Main.qml`, insieme alle sue viste e al relativo provider; solo dopo entra in **Moduli visibili**. In modalità `--device`, `run.sh` nasconde il cursore software di EGLFS anche quando la mini tastiera USB espone un'interfaccia mouse.

## Verifiche e ripristino

Verifica v0.5 del 30/09/2026:

- Sei test del motore e sei test della cache superati sul PC e sulla board; controllo QML completo superato in entrambi i runtime, inclusi i due formati di banner, timer, badge non letti, recupero da cache, soglie Account, ritorno del focus e preferenze persistenti. Cambiare formato conserva lo stato di consegna e i payload precedenti usano il formato piccolo.
- Acquisite e controllate le schermate Home, banner piccolo, banner grande, overlay urgente e Notifiche dal renderer EGLFS della board a 960×640. Gli avvisi nelle catture sono simulati e dichiarati come tali; non è stata provocata un'allerta ufficiale.
- Lettura della fonte Protezione Civile eseguita anche dalla board; il bollettino verificato non conteneva allerte per Angri.
- Misura GPU di 12 secondi: 26 transizioni, 260 frame, mediana 16,60 ms, p95 17,76 ms, massimo 19,59 ms. È una misura breve di navigazione, non un test di durata o una garanzia di 60 fps costanti.
- Dopo le prove il servizio è attivo, con `NRestarts=0`. In questa verifica i tasti sono stati simulati; la leggibilità alla distanza d'uso e la prova manuale dei pulsanti restano da confermare sull'apparecchio.
- Estensione cache e badge: prova sulla board con due processi separati e rete simulata come indisponibile. Il secondo avvio recupera il bollettino di prova, conserva lettura e consegna ed evita un nuovo banner. Verificato anche il recupero da cache con database inizialmente vuoto e il caso di cache precedente a un bollettino senza allerte. La prova non comporta un riavvio del sistema operativo o la disattivazione del Wi-Fi.
- Catture EGLFS aggiuntive delle due viste Home con badge e della Home dopo la lettura, senza badge. Il badge non cambia la composizione di ora/meteo e non riserva una tessera eventi.
- Verifica reale della cache sulla board: bollettino `20260930_1423`, zero allerte per Angri, file di 1268 byte. Primo recupero con quattro richieste; seconda verifica della stessa chiave con una sola richiesta alla pagina ufficiale, senza scaricare nuovamente metadati o mappe.

`check_dashboard.py` esegue un controllo rapido di caricamento QML, navigazione, visibilità delle cinque viste, Account ChatGPT, impostazioni, eventi demo, ritorno del focus, silenzio per orario/categoria, durata reale del banner, badge non letti e ricostruzione da cache al riavvio offline senza usare la rete. `check_events.py` verifica deduplicazione, escalation anche da arancione a rossa, scadenza, persistenza, non letti, isolamento delle fonti, dati invalidi e selezione di Angri. `check_weather_alerts.py` verifica chiave invariata, cache dopo riavvio, scadenze, aggiornamenti invalidi, file corrotto e sostituzione atomica fallita. Si possono avviare con `python3 dashboard/check_dashboard.py`, `python3 dashboard/check_events.py` e `python3 dashboard/check_weather_alerts.py` dove PySide6 è installato; gli ultimi due non richiedono Qt.

La v0.2 aveva già superato i test di meteo online, cache offline e riavvio senza Wi-Fi. Sul dispositivo, il servizio riparte automaticamente dopo un crash; la configurazione è in [smartpc-dashboard.service](../os/system/smartpc-dashboard.service). La scena diagnostica visualizza FPS e intervallo p95 tra frame, ma un valore basso su una schermata ferma è normale: non misura da solo la fluidità delle transizioni. `benchmark.py` misura intervalli di frame mentre simula cambi di vista sul renderer EGLFS/GPU; va eseguito con il servizio fermo. `soak.py` osserva memoria, temperatura e stabilità del servizio senza inviare input.

Prima di installare una nuova versione sulla board, salvare `/opt/smartpc/dashboard` in `/var/backups/`. Il backup della v0.3 precedente al modulo Account è `/var/backups/smartpc-dashboard-v03-before-account`. Per ripristinare, copiare i file salvati nella cartella dell'app e riavviare il servizio; disabilitare anche `smartpc-account-sync.timer` sul PC se la funzione non serve più. Non serve Git per questo passaggio; la creazione del repository è rimandata.

Controlli utili:

```bash
sudo systemctl status smartpc-dashboard
sudo journalctl -u smartpc-dashboard --since "10 minutes ago"
sudo systemctl restart smartpc-dashboard
```

Il backup della v0.4 prima del motore eventi è `/var/backups/smartpc-dashboard-v04-before-events`; quello della v0.5 prima del secondo formato di banner è `/var/backups/smartpc-dashboard-v05-before-banner-sizes`; prima di cache e badge è stato salvato `/var/backups/smartpc-dashboard-v05-before-cache-badge`. Il target è 960×640 a 60 Hz. Le scene future andranno misurate sulla board. Il vecchio timer Xorg per la luminosità è disabilitato nel kiosk EGLFS; il conflitto dell'aggiornamento Xorg resta annotato nel [resoconto OS](../os/board-audit-2026-09-29.md).

### Revisione Sport: dettaglio e navigazione

Il dettaglio delle partite future gestisce eventi/statistiche `null`. Mostra stato, orario e stadio, poi le schede **Riepilogo / Statistiche / Formazioni**; i dati non ancora pubblicati hanno un messaggio coerente. Le formazioni disponibili mostrano tutti gli undici titolari di entrambe le squadre.

- In Sport, **5** apre le partite della giornata; **2/8** scorre e **4/6** alterna Partite/Classifica.
- Dalla prima partita, **2** porta al selettore Giornata: **4/6** cambia turno e **8** torna alle partite. Questo consente anche la consultazione dei turni precedenti.
- Nel dettaglio, **4/6** cambia scheda, **2/8** scorre i marcatori se sono più di quattro, **5** aggiorna e **7** torna alla riga selezionata.

Gli errori tecnici restano nei log; caricamento, indisponibilità e dati salvati sono indicati nella schermata. La richiesta di dettaglio usa il worker senza riscaricare il calendario; una selezione fatta durante un caricamento viene eseguita appena termina la richiesta corrente. [Verifiche e catture](./design/v06-sport-ux-fix.md).

### Accesso diretto alla classifica e più partite

Da **Prossime**, senza incontri attivi, premere **8 due volte** per Classifica e **5** per l’elenco completo. Se è presente In corso, serve una pressione aggiuntiva. In **Prossime / In corso**, il numero di partite e l’indice della pagina sono visibili; tre righe mostrano ciascuna le proprie squadre, orario/stato e punteggio. Gli incontri simultanei restano separati. **5** apre l’elenco con selezione stabile e 2/8 permette di consultarli manualmente.

### Etichette del tastierino · 1 ottobre 2026

Dopo il riscontro sul dispositivo, i suggerimenti nei pannelli e nella legenda Comandi indicano **1 Indietro** e **7 Home**. Aggiornato anche l’avviso urgente (**1 Chiudi**, **7 Home**). La revisione modifica le etichette e conserva il comportamento dei comandi esistente.
