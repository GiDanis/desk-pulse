# v0.6 · Scheda Fantacalcio

Implementata e installata sull’Orange Pi il **1 ottobre 2026**.

**Aggiornamento:** [feed anonimo live, stagione persistente e recupero dello storico](v06-fantacalcio-live.md). Il documento collegato aggiorna la frequenza live a 30 secondi, aggiunge la finestra prepartita e distingue i fantavoti live calcolati dai valori pubblicati descritti qui.

## Funzione e comandi

Aprendo una partita **Serie A**, il dettaglio ha quattro schede: **Riepilogo, Statistiche, Formazioni, Fantacalcio**. La quarta scheda è disponibile anche aprendo la partita da **La mia squadra**. Per le altre competizioni il dettaglio conserva le tre schede precedenti.

Fantacalcio mostra una squadra alla volta:

- modulo, titolari, subentrati e panchina completa quando la formazione è disponibile;
- ruolo, numero, nome e minuto della sostituzione disponibile;
- **Voto base** e **Fantavoto**, come chiarito dall’utente: voto con bonus/malus già inclusi nel valore pubblicato dalla redazione;
- fonte e data dei voti, indicazione dei dati salvati e messaggi di attesa/errore.

**4/6** cambia scheda, **2/8** scorre tutti i giocatori e **5** cambia squadra. Per un aggiornamento manuale: risalire con 2 sopra il primo giocatore e premere 5 sulla riga «Aggiorna voti»; 8 torna ai calciatori. Le diciture fisiche restano **1 Indietro / 7 Home**, con i gestori esistenti del tastierino.

Le partite future mostrano le formazioni eventualmente pubblicate e l’attesa dei voti. I giocatori senza un voto disponibile hanno **—**; un valore esplicito «senza voto» viene mostrato come **SV**. Non viene attribuito un voto ai panchinari che non hanno giocato.

## Fonte e abbinamento

Voti dalla [pagina pubblica della Redazione Fantacalcio](https://www.fantacalcio.it/voti-fantacalcio-serie-a/2026-27/5), senza una nuova sottoscrizione o credenziali. L’adapter identifica le colonne dalla loro intestazione e legge la coppia voto/fantavoto della redazione. Il valore finale viene riportato dalla fonte: non richiede la configurazione del regolamento di una lega personale.

Formazione e panchina provengono dal dettaglio FotMob già utilizzato dalla dashboard. `lineup_squad()` conserva nomi completi, nome/cognome, numeri e sostituzioni; le precedenti liste di nomi delle formazioni restano compatibili con le cache esistenti.

L’associazione dei voti verifica **Serie A, stagione, giornata, entrambe le squadre e data/ora della partita**. Il dettaglio della squadra preferita recupera la giornata anche quando il calendario multicompetizione non la specifica. Abbreviazioni e accenti vengono normalizzati; l’associazione deve essere univoca all’interno della squadra. Nomi ambigui mantengono il voto separato nella sezione «Voti fonte», con un messaggio visibile.

I codici numerici `55` e `56` utilizzati come segnaposto dal sito vengono trattati come dati assenti; non diventano voti numerici. Il comportamento dei segnaposto è riscontrabile nel [CSS della pagina voti](https://www.fantacalcio.it/css/pages/grades.page.min.css?v=kBzY1Ejnp03GCQQzkbrIk_rQBZ5krIK3rlN6WfrCqB4).

## Architettura e cache

- `fantacalcio_core.py`: parser HTML con libreria standard, verifica dell’identità della fonte, abbinamento dei giocatori e cache atomica.
- `fantacalcio.py`: worker Qt per HTTP, parsing e scrittura. Una cache condivisa per giornata evita una richiesta distinta per ogni partita.
- `SportFantasy.qml`: tabella di cinque righe, squadra selezionabile e scorrimento completo.
- `SportService` e `DashboardState`: selezione della partita e propagazione del nuovo stato alla UI.

Cache: `fantacalcio-{stagione}-{giornata}.json`, nella directory di `sport.json`. Le richieste iniziano quando si consulta la scheda di un incontro già iniziato/concluso; le partite future non richiedono voti. Il timer segue soltanto la consultazione selezionata: 90 secondi per gli incontri in corso, cinque minuti nelle prime 24 ore dal calcio d’inizio, sei ore per gli incontri più vecchi. L’aggiornamento manuale ha un intervallo minimo di 30 secondi.

Un errore conserva i voti validi salvati. La risposta della giornata precedentemente selezionata non sostituisce quella richiesta successivamente. Fonte, ora e stato appartengono ai voti, separatamente dal dettaglio FotMob. Uscendo dal dettaglio o dalla scheda il relativo aggiornamento periodico viene fermato.

## Verifiche completate

- `check_fantacalcio.py`: **7 test** su fonte redazionale, colonne delle altre fonti, roster e voti reali, esclusione delle coppe, stagione/giornata/date errate, valori assenti/SV/segnaposto, nomi ambigui e cache atomica.
- `check_fantacalcio_ui.py`: decoder HID, quattro schede, cambio squadra, tutti i titolari/subentrati/panchinari raggiungibili, aggiornamento manuale in worker, errore con recupero dei voti, partite future senza richieste, percorso della preferita, esclusione delle coppe, Home/Indietro e selezioni consecutive di giornate diverse.
- Regressioni Serie A (`check_sport.py`, `check_sport_ui.py`), preferita (`check_sport_team.py`, ora 8 test, e `check_sport_team_ui.py`) e motorsport (`check_motorsport_ui.py`): passate. Il controllo finale ha corretto un errore preesistente nel timer del profilo squadra (`interval` non inizializzato): aggiunte prove del risveglio prima del calcio d’inizio e della riprogrammazione dopo il completamento di un worker con aggiornamento automatico attivo.
- **Board, HTTP reale:** pagina redazionale della giornata 5 del 2026/27, 20 squadre e 316 righe calciatori. Roma–Inter: 23 giocatori per squadra, di cui 11 titolari, 5 subentrati e 7 rimasti in panchina. Nessun nome non abbinato. Campione verificato: Josep Martínez **6,5 / 4,5**. Una richiesta alla fonte voti e tre richieste FotMob per il controllo iniziale.
- **Board, EGLFS 960×640:** catture di entrambe le squadre, titolari, subentrati, ultimi panchinari, partita futura, percorso della preferita e stato offline. **Zero avvisi QML** durante il test automatizzato; immagini esaminate direttamente.
- **Board, processo nuovo senza rete:** cache redazionale e 23 giocatori per squadra recuperati, stato offline e voti conservati. Non è stato eseguito un reboot del sistema operativo per questa aggiunta.

[Acquisizione online](./evidence/v06-fantacalcio/fantacalcio-online.json), [navigazione](./evidence/v06-fantacalcio/fantacalcio-ui.json), [offline](./evidence/v06-fantacalcio/fantacalcio-offline.json), [immagini](./evidence/v06-fantacalcio/).

## Limiti della verifica

L’integrazione completa e le catture usano un incontro concluso reale, Roma–Inter. Non è stata misurata la latenza della redazione durante una partita live. I voti pubblicati possono subire correzioni; la UI non li presenta come definitivi. Fonte e formazione possono avere copertura diversa: i giocatori senza abbinamento certo conservano valori assenti e le righe della fonte restano consultabili separatamente. Non sono state verificate tutte le giornate storiche.

Backup precedente al deploy: `/var/backups/smartpc-dashboard-fantacalcio-20261001/dashboard`. Per rollback, fermare il servizio, ripristinare la sorgente salvata in `/opt/smartpc/dashboard` e riavviare `smartpc-dashboard.service`. I controlli usano configurazioni isolate e non cambiano preferita, notifiche o impostazioni dell’utente.
