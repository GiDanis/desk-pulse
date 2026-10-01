# v0.6 Sport · correzione dettaglio e revisione UX

**30 settembre 2026 — installata sulla Orange Pi.** Questa revisione segue il [piano](./v06-sport-plan.md) e aggiorna il [primo rilascio](./v06-sport-release.md).

## Errore riprodotto e corretto

Aprendo Genoa–Fiorentina, FotMob `5749693`, il campo `header.events` è `null`: l'accesso a `.get()` generava `AttributeError`. Anche `content.stats` è `null` prima della partita. L'estratto reale è conservato in [sport-fotmob-upcoming-detail.json](../fixtures/sport-fotmob-upcoming-detail.json).

Gli adapter gestiscono oggetti e liste facoltativi nulli, anche nel dettaglio ESPN, mantenendo la validazione di competizione e identità. Le partite future mantengono il punteggio assente; non diventano 0–0. Il dettaglio può aggiornare l'orario; una data dichiarata incerta resta da confermare. I marcatori sono ordinati per minuto.

Le eccezioni tecniche vengono registrate nei log. La schermata distingue caricamento, dettaglio indisponibile, dati salvati e informazioni non ancora pubblicate. Gli errori di dettaglio appartengono alla singola partita. Il timestamp del dettaglio è separato da quello del calendario; aggiornare una partita non rende fresco l'intero calendario recuperato dalla cache.

## Consultazione e tasti

- **5 dalla vista Sport:** apre le partite della giornata, invece dell'elenco di tutti gli incontri restanti.
- **2/8:** scorre le partite o la classifica completa. Dalla prima partita, **2** seleziona Giornata: **4/6** cambia turno e **8** torna alle partite. Si possono consultare anche i turni precedenti.
- **4/6 sulle righe:** alterna le schede visibili Partite/Classifica, conservando la selezione di ciascun elenco.
- **5 sulla partita:** apre Riepilogo; **4/6** passa a Statistiche e Formazioni. **2/8** scorre i marcatori quando sono più di quattro. Le formazioni mostrano gli undici titolari per squadra in due colonne.
- **5 nel dettaglio:** aggiorna; **7:** torna alla riga selezionata. Avvisi e Menu conservano la scheda e il focus. La fine di una partita in consultazione mantiene visibile il risultato.

Le partite future mostrano **VS**, orario e stadio. Le schede vuote spiegano che le statistiche arrivano dopo il calcio d'inizio e che le formazioni non sono ancora pubblicate. Stagione, giornata e fonte sono identificabili.

Il caricamento del dettaglio usa il worker Qt senza riscaricare il calendario. Se la persona seleziona un'altra partita durante una richiesta, viene caricata l'ultima selezione al termine di quella corrente. Il trasporto conserva cache HTTP e cooldown.

## Verifiche effettuate

| Controllo | Esito |
| --- | --- |
| Backend | 11 test passati: casi precedenti più payload futuro reale/null, ESPN futuro/null, richiesta del solo dettaglio, cache HTTP più vecchia del calendario e messaggio d'errore comprensibile |
| QML su PC e Orange Pi | Pass: selettore giornata, memoria delle due schede, selezione durante worker attivo, messaggi futuri, ritorno da Avvisi, preferenze, offline/cache, transizione al risultato finale; nessun warning QML |
| Regressione dashboard | `check_dashboard.py` passato su PC e board |
| REST reale sulla board | 380 partite e 20 squadre; dettagli di tre partite future e Milan–Lecce conclusa, senza errore. La conclusa restituisce tre marcatori, tre statistiche e due formazioni da undici giocatori |
| Nuovo processo offline | Recuperati 380 incontri e 20 squadre, stesso timestamp; nessun badge Live |
| Display reale | Catture EGLFS/OpenGL 960×640 di elenco, futuro, statistiche, formazioni, risultati, classifica e impostazioni |
| Installazione | SHA-256 dei cinque file runtime modificati uguali ai sorgenti; servizio `active`, `NRestarts=0`, `ExecMainStatus=0` |

Evidenze: [API reali](./evidence/v06-sport-ux-fix/online.json), [offline](./evidence/v06-sport-ux-fix/offline.json), [installazione](./evidence/v06-sport-ux-fix/installed.json). Il caso d'errore intenzionale nel checker scrive un warning tecnico: serve a verificare che questo testo non raggiunga la UI.

### Catture della nuova UI

- [Partite della giornata](./evidence/v06-sport-ux-fix/sport-round.png).
- [Dettaglio di una partita futura](./evidence/v06-sport-ux-fix/sport-upcoming-detail.png).
- [Statistiche prima del calcio d'inizio](./evidence/v06-sport-ux-fix/sport-upcoming-stats.png).
- [Formazioni della partita conclusa](./evidence/v06-sport-ux-fix/sport-finished-lineups.png).
- [Statistiche della partita conclusa](./evidence/v06-sport-ux-fix/sport-finished-stats.png).

La misura breve di navigazione dura 15 secondi: 32 azioni, 170 intervalli, mediana **16,56 ms**, p95 **17,77 ms**, massimo **19,92 ms**. Esclude il primo frame dopo un periodo senza animazione; la latenza massima azione/primo frame è registrata separatamente: **134,44 ms**. [Misura completa](./evidence/v06-sport-ux-fix/render.json). Non dimostra 60 fps fissi o stabilità prolungata. Le catture sono state ispezionate; la leggibilità dalla distanza d'uso e la pressione manuale dei tasti restano una verifica dell'apparecchio. I test inviano gli input tramite il segnale Qt del tastierino.

## Backup e limiti

Backup della versione precedente sulla board: `/var/backups/smartpc-dashboard-v06-before-ux-20260930`. Cache e preferenze di produzione sono conservate. I checker usano configurazioni separate.

Non è stato ripetuto il reboot del sistema operativo: questa revisione verifica un nuovo processo offline e il riavvio del servizio. Il precedente test di reboot è documentato nel primo rilascio. Ritardo live, VAR e notifiche gol restano da verificare durante una partita attiva; il gate live resta disattivato.

## Revisione successiva: Classifica diretta e partite contemporanee

Dopo il riscontro sul tastierino, **Classifica** è una vista principale: da Prossime, **8 → 8 → 5** apre tutte le 20 squadre quando non è presente In corso. Se ci sono partite attive, la sequenza include una pressione aggiuntiva di 8. Resta anche il passaggio Partite/Classifica dentro l’elenco. La vista Classifica è disponibile anche quando nell’elenco è selezionato il controllo Giornata.

Il precedente riepilogo prendeva sempre `upcoming[0]`, quindi mostrava soltanto Genoa–Fiorentina. Ora mostra **tutte le partite future della prima giornata in programma**, tre per pagina; ogni otto secondi passa alla pagina successiva. Il contatore dichiara quante partite e pagine sono presenti. In **In corso** vengono mostrati allo stesso modo tutti gli incontri attivi, con il proprio punteggio e minuto; la disponibilità del badge Live mantiene il gate già previsto.

La rotazione funziona solo mentre si consulta il riepilogo: aprendo l’elenco con 5, una partita, Avvisi o Menu si ferma. L’elenco si consulta con 2/8 e conserva il focus. Questa revisione rende Sport un’eccezione esplicita al limite iniziale delle tre viste: tre a riposo, quattro durante una partita attiva.

### Verifica di questa revisione

- `check_sport_ui.py` passato su PC e board, senza warning QML: classifica raggiungibile con 2/8 e 5, tutte le 20 righe, raggiungibilità anche con In corso, quattro fixture allo stesso orario su due pagine, arresto della rotazione nell’elenco, mantenimento del risultato finale. Le fixture simultanee del checker sono dati di prova isolati.
- Gli input del checker attraversano `KeyDecoder` con i codici Ctrl/Shift del dispositivo, prima del segnale Qt. Non è una pressione manuale dei tasti fisici. Nessuna modifica al firmware o al protocollo HID.
- `check_dashboard.py` passato su PC e Orange Pi.
- Catture EGLFS 960×640 su calendario REST reale: [prima pagina](./evidence/v06-sport-navigation/sport-next.png), [seconda pagina con due gare alle 15:00](./evidence/v06-sport-navigation/sport-next-page-2.png), [Classifica principale](./evidence/v06-sport-navigation/sport-table-primary.png), [elenco completo](./evidence/v06-sport-navigation/sport-table.png). La prova active/simultaneous è nel checker, non una nuova osservazione di una partita realmente in corso.
- Campione di navigazione di 15 s: 32 azioni, 161 intervalli, mediana 16,59 ms, p95 17,58 ms, massimo 18,20 ms; latenza massima del primo frame dopo input 151,80 ms, registrata separatamente. [Misura](./evidence/v06-sport-navigation/render.json). Non dimostra 60 fps fissi o prestazioni prolungate.
- Backup prima dell’aggiornamento: `/var/backups/smartpc-dashboard-v06-before-navigation-20260930`. [Installazione e SHA-256](./evidence/v06-sport-navigation/installed.json).
