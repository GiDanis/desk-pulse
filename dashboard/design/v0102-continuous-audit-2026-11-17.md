# Dashboard Orange Pi: audit dopo funzionamento continuativo

17 novembre 2026 · analisi, nessuna modifica al runtime o al sistema della board.

La Dashboard è operativa dopo circa **4 giorni e 2 ore**, con servizio attivo e **NRestarts=0**. Il campione attuale non mostra crescita della memoria, dei thread o dei descrittori. Prima di cercare altri guadagni grafici, conviene correggere la misura del soak, il protocollo asincrono dell’Acquario e il conflitto GPIO/PWM del sistema. Non ci sono elementi sufficienti per dichiarare il software privo di leak o completamente qualificato.

## Identità e perimetro

La richiesta indica «v0.10.32»; sulla board e nel checkout `version.py` dichiara **0.10.2-rc.5**. Manifest installato SHA-256 `7b33780f75ce4496089365ae7ad9ab2d5178f5051c4be02cf18b938ff732d1cd`: **550/550 file corrispondenti**. Apple Calm **1.7.0**, digest `daf0a7b1cc0bc19bd2931765b14714dc1dadf685025df337541a65fe9b78d376`, attivo, nessuna attivazione pendente e `lastRecovery=null`.

Anche la copia locale del runtime consegnato il 30 ottobre corrisponde a tutti i 550 hash. Il checkout corrente differisce invece in **14 file del manifest**, soprattutto Gioco e librerie native: non è un sostituto automatico della baseline installata. Le riproduzioni Acquario usano la copia verificata del runtime, non il ramo di ricerca.

Esaminati avvio/chiusura, supervisione, heartbeat, acquisizione e stato delle fonti, eventi e retention, pubblicazione Theme API, lettore metadati Gioco, persistenza e handshake Acquario, timer QML e diagnostica di sistema. È una revisione mirata alla continuità operativa, non una revisione esaustiva di ogni algoritmo di apprendimento o di tutti i renderer.

## Misure attuali

Campione passivo di **25 letture in 120,19 s**, senza inviare input, cambiare vista o riavviare. Vista osservata: **`home.clock`**, non Gara/apprendimento/Acquario animato.

| Indicatore | Risultato |
| --- | --- |
| Servizio | active/running, zero riavvii |
| GUI / supervisore | PID 1255 / PID 1204; processi distinti |
| RSS GUI | **461,32 MiB**, minimo e massimo uguali nel campione |
| PSS GUI | 430,78–430,94 MiB |
| CPU GUI | **0,957% di un core**, media sui 120 s |
| Descrittori / thread GUI | **52 / 19**, costanti |
| Heartbeat | 25/25 ready; età massima osservata 0,262 s |
| Memoria cgroup servizio | circa **650 MiB**, include figli e memoria contabilizzata dal kernel |
| Lettore metadati Gioco | circa **135 MiB RSS / 108 MiB PSS**, rimasto avviato anche nella vista orologio |
| RAM disponibile / swap | circa **5 GiB / 0 MiB utilizzati** alla prima lettura |
| Disco libero | **17.711.079.424 byte**, circa 16,5 GiB |
| Sensori termici | circa 56–61 °C nelle letture iniziali e successive |

RSS dei figli e cgroup non vanno sommati: includono contabilizzazioni e pagine condivise differenti. Il confronto con i 279.496 KiB RSS della consegna del 30 ottobre **non prova un leak**: quel campione era breve, su Home, con storia di utilizzo e cache diverse. Qui manca una serie temporale dei quattro giorni.

L’orario wall-clock di avvio riportato da systemd precede quanto suggerito dall’uptime; la durata è quindi ricavata dal contatore monotono e dal token di inizio processo. Non si attribuisce l’anomalia a una specifica causa RTC/NTP senza ulteriori prove. Attualmente `NTPSynchronized=yes`.

## Risultati e priorità

### A1 · Alta: il vecchio soak misura il supervisore

[`soak.py`](../soak.py), righe 13–18 e 39–49, usa `systemctl MainPID` per leggere RSS. Il launcher attuale esegue il supervisore come MainPID e la GUI come figlio: oggi il vecchio script osserverebbe circa 24 MiB del supervisore, mentre la GUI è a 461 MiB. Inoltre il solo RSS non copre figli, readiness o crescita dei descrittori.

**Intervento proposto:** individuare la GUI discendente del servizio con identità PID + start token; registrare separatamente supervisore, GUI, helper e cgroup. Fallire la verifica se la GUI manca o cambia, anche se MainPID resta invariato. Conservare heartbeat/readiness, CPU, RSS/PSS, thread/FD, temperature e contesto della vista. Timestamp monotoni per durate; orario civile per la consultazione.

**Accettazione:** casi con supervisore vivo/GUI assente, sostituzione della GUI, PID riutilizzato e heartbeat scaduto devono essere rilevati. Nessuna ricevuta storica basata sul solo MainPID viene riqualificata retroattivamente.

### A2 · Alta, sistema: conflitto PD5 e controllo PWM della ventola

Il kernel segnala ripetutamente `pin PD5 already requested`, `enable pwm chan 5 failed` e `thermal cooling_device9: Cannot set pwm!`. Nell’evidenza salvata, **tutti gli ultimi 1.500 messaggi kernel**, distribuiti su circa **495 s**, appartengono a questo gruppo; 188 sono `Cannot set pwm!`.

Il pin 101/PD5 risulta esportato da **sysfs**, uscita **alta**. `cooling_device9` è `pwm-fan`, stato 0, massimo 4. Questo **non dimostra che la ventola sia ferma**: il livello alto potrebbe essere una gestione manuale intenzionale. Non sono stati modificati GPIO, PWM, device tree, governor, kernel o servizi.

**Intervento proposto:** ricostruire chi esporta PD5 e verificare fisicamente la ventola; assegnare il controllo a un solo meccanismo coerente con l’hardware e con la configurazione voluta. Correggere la causa degli errori, senza limitarsi a nasconderli nei log. Qualificare separatamente la modifica OS, con rollback e verifica termica a carico.

**Accettazione:** ventola fisicamente verificata, controllo previsto funzionante, assenza del conflitto durante transizioni termiche, recovery del display e tastierino preservati. Nel journal interrogato non risultano messaggi della Dashboard del boot corrente: questa assenza **non certifica zero warning QML nei quattro giorni**.

### A3 · Media: Acquario, accettazione della richiesta confusa con completamento

[`AquariumPopulation.submit`](../aquarium_population.py), righe 26–52, restituisce `True` quando accoda il lavoro. [`Aquarium3DVisual.qml`](../presentations/aquarium/Aquarium3DVisual.qml), righe 81 e 89–91, usa `.accepted` per impostare `shownSent` e `candidateSent`. La gestione azioni in `Main.qml` non attende un completamento Acquario dedicato.

Riproduzione isolata sulla baseline: richiesta `prepared` accettata, worker con errore SQLite controllato, candidato ancora pendente, stato della scena ancora `ready` perché esiste lo snapshot precedente. Il ramo QML smette di inviare `prepared` quando `candidateSent=true`; il normale refresh successivo riconcilia i dati ma non riesegue quel comando. La permanenza del blocco nel renderer è una conclusione dalla lettura del ramo QML, non da una prova grafica con fault injection.

Il testo errore è presente nello snapshot, ma il pannello che lo contiene può restare nascosto quando asset, movimento e playback sono normali.

**Intervento proposto:** distinguere accodamento, esecuzione e commit; correlare il risultato a operazione e generazione. Per errore transitorio ripristinare il tentativo con attesa e limite; per errore persistente mostrare un esito recuperabile. `shown` e `prepared` devono essere idempotenti. Conservare lo snapshot valido senza chiamare completata un’operazione fallita.

**Accettazione:** errore DB dopo accettazione, esito tardivo, cambio vista e rientro, candidato superato e comando ripetuto. Nessuna falsa conferma, sostituzione duplicata o perdita di storico.

### A4 · Media: lettore metadati Gioco sempre residente

L’app costruisce `GameService(async_metadata=True)` all’avvio. Il lettore viene avviato dalla prima richiesta; [`game_metadata.py`](../game_metadata.py), righe 160–173, ferma il timer quando è inattivo ma conserva il processo fino alla chiusura del servizio. Nella lettura attuale il figlio mantiene circa **108 MiB PSS** anche su `home.clock`. È un costo spiegabile dal progetto, non una prova di leak.

**Intervento proposto:** confrontare avvio su richiesta e rilascio dopo inattività con il comportamento attuale, mantenendo una proiezione compatta per il menu. La possibilità di recuperare memoria va misurata insieme al costo della prima apertura e della riapertura. Non modificare learner, modelli, reward, database o piloti per questa ottimizzazione.

**Accettazione:** prima apertura/riapertura, selezione pilota, sessione attiva, salvataggio e ripresa; nessun helper duplicato e nessuna interruzione del learner. Il risparmio esatto resta da misurare.

### A5 · Bassa: riconciliazione Acquario e scritture anche senza rotazioni

Dopo il caricamento, il timer della popolazione resta attivo ogni minuto anche fuori dalla vista. [`AquariumStore.reconcile`](../aquarium_store.py), righe 119–131, scrive sempre `lastTime`. La prova isolata con sei pesci fissi, nessuna scadenza e nessun candidato produce **una riga modificata per ognuna di tre riconciliazioni**. Il ritmo nominale è quindi fino a 1.440 transazioni al giorno del solo timer dopo il caricamento, oltre ai comandi.

Non è una misura dei byte fisicamente scritti sulla SD: sul kernel corrente mancano `/proc/PID/io` e `io.stat` del cgroup. Il valore di `lastTime` serve anche alla protezione contro arretramenti dell’orologio e non va semplicemente eliminato.

**Intervento proposto:** separare calendario, watermark persistente e notifiche della UI; usare la prossima scadenza e una riconciliazione al rientro, evitando pubblicazioni senza differenze. Ridurre le scritture soltanto preservando la protezione dell’orologio e il tempo trascorso a board spenta.

### A6 · Media per lo sviluppo: ambiente test PC non riproducibile oggi

Il Python predefinito è 3.14 e non trova PySide6. Il vecchio venv dichiara Python 3.12 ma i suoi eseguibili puntano a `/usr/bin/python3`, ora 3.14. I pacchetti nella cartella Python 3.12 espongono attualmente **Qt 6.11.2**, mentre il requisito di progetto è PySide6 6.8.2.1 / Qt 6.8.2, come la board. Il banco launcher incontra inoltre `numpy` assente.

**Intervento proposto:** ricostruire un ambiente PC separato con interprete e dipendenze bloccati e una verifica preliminare delle versioni. Nessuna installazione o riparazione degli ambienti è stata eseguita durante questo audit.

## Cosa mantenere

- Heartbeat effimero in tmpfs, con scrittura non durevole; journal di attivazione separato e durevole. L’ottimizzazione delle scritture heartbeat è già presente.
- Cache limitate e rilascio esplicito dei contesti Theme API; polling adattivo Rete e finestre di recupero; worker fuori dal thread GUI per le acquisizioni principali.
- Retention eventi e dati precedenti conservati in caso di errore della fonte; limiti alle risposte HTTP e budget calcio persistente. Non emerge una ragione per aumentare le chiamate API o forzare altri clock CPU/GPU.
- Separazione tra dati correnti, cache, consegna del banner e conferma di presentazione. Il protocollo Acquario va portato allo stesso livello di precisione.

Questi sono riscontri di lettura del codice, non una qualifica live delle singole fonti.

## Verifiche eseguite e limiti

**Cinque dei sei casi selezionati sono passati**, in due ambienti distinti:

- `check_events`, `check_network`, `check_theme_watchdog_transition`: positivi con Python locale; il watchdog usa processi reali isolati e timeout accelerati.
- `check_notification_updates` e `check_theme_recovery`: positivi con Python 3.12 esplicito e pacchetti Qt locali **6.11.2**. Il primo contiene 14 test.
- `check_app_lifecycle`: **bloccato dalle dipendenze PC** (`numpy` assente dopo il primo ostacolo PySide6), non qualificato. I tre test di questo caso non passano nel banco attuale.

Le regressioni del runner usano il checkout locale: non qualificano automaticamente i 14 file diversi dal runtime installato. Le due sonde Acquario usano invece la copia con tutti i 550 hash verificati. I primi esiti falliti per dipendenze restano conservati insieme ai successivi; non sono cancellati o presentati come regressioni risolte del prodotto.

Non eseguiti: matrice completa, nuovi test sulla board, navigazione attiva, misura FPS ottici/input, fault reali alle fonti, Gara/apprendimento sotto carico, riavvio app/OS, soak attivo 24 h. Non modificati: runtime, preferenze, temi, dati, servizi o configurazione OS della board. Sono stati aggiunti solo report e sonde locali e il riferimento nel MasterPlan.

## Sequenza proposta per la manutenzione

1. **Rendere affidabili le prove:** ambiente PC coerente con ARM e soak sui processi corretti, con misure limitate e identità della build.
2. **Correggere il protocollo Acquario:** conferma dopo commit, recupero da errore e visibilità dell’esito. Prove mirate PC, poi ARM/EGLFS.
3. **Risolvere il conflitto ventola come intervento OS separato**, dopo avere chiarito la configurazione fisica voluta e preparato il rollback.
4. **Misurare le ottimizzazioni:** helper Gioco su richiesta e riconciliazione Acquario; confronto della memoria e delle aperture su percorsi uguali.
5. **Qualificare la candidata:** campione Home a riposo, aperture/rientri, Acquario animato, Gara/apprendimento e fonti concorrenti; osservazione prolungata con serie temporale, poi gate fisici/live pertinenti. Nessuna promozione a stabile dal solo uptime o dal solo RSS piatto per due minuti.

La prossima release dovrebbe concentrarsi su affidabilità misurabile e riduzione del lavoro inutile. Il numero di versione e l’implementazione non sono stati cambiati da questo audit.

## Evidenze

[Riepilogo e differenze di baseline](evidence/v0102-continuous-audit-2026-11-17/summary.json), [25 campioni board](evidence/v0102-continuous-audit-2026-11-17/board-observation.jsonl), [OS/termica/kernel](evidence/v0102-continuous-audit-2026-11-17/system-observation.json), [sonde isolate](evidence/v0102-continuous-audit-2026-11-17/fault-probes.json), [primo passaggio runner](evidence/v0102-continuous-audit-2026-11-17/checks/checks.json), [passaggio Python 3.12/Qt 6.11.2](evidence/v0102-continuous-audit-2026-11-17/checks-local-qt611/checks.json). Gli script nella stessa cartella rendono ripetibile la raccolta, ma i PID della sonda OS sono riferiti a questa sessione e vanno risolti nuovamente prima di un altro uso.
