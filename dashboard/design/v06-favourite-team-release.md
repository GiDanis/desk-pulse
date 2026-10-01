# v0.6 · La mia squadra

Implementata e installata sull’Orange Pi il **1 ottobre 2026**.

## Uso

**Serie A → 2/8 fino a La mia squadra → 5** apre la scelta della preferita. Il selettore comprende le squadre del campionato caricato e «Nessuna preferita» per rimuoverla. La stessa scelta è accessibile da Impostazioni Sport, premendo 5 sulla squadra.

La sezione presenta quattro schede:

- **Calendario:** tutti gli incontri futuri pubblicati per il club, comprese coppe europee, Coppa Italia e amichevoli. Le partite in corso disponibili precedono quelle future. Tre righe per pagina; l’ultima partita è raggiungibile con 2/8.
- **Risultati:** incontri conclusi di tutte le competizioni, dal più recente; 5 apre riepilogo, statistiche e formazioni disponibili.
- **Info:** cambio preferita, aggiornamento manuale, allenatore, stadio, città, capienza, posizione e bilancio Serie A, andamento degli ultimi cinque risultati.
- **Rosa:** giocatori pubblicati dalla fonte, ruolo, numero, età e paese; scorrimento fino all’ultimo giocatore.

4/6 cambia scheda. Nel calendario e nei risultati, 2 dalla prima riga seleziona il filtro; 4/6 o 5 alterna **Tutte / Solo Serie A**. 8 torna alle partite. Il ritorno dal dettaglio conserva la riga selezionata. Le diciture del tastierino restano **1 Indietro / 7 Home**, secondo la correzione richiesta dall’utente; i gestori e la decodifica HID non sono stati modificati.

La preferita viene salvata sul dispositivo. La scheda del club riguarda la stagione corrente fornita dall’endpoint squadra, anche quando il calendario Serie A è impostato sulla stagione precedente. L’eventuale evento in Home continua a riguardare la prossima partita **Serie A**, con la preferenza già esistente; la relativa impostazione è ora denominata esplicitamente «Prossima Serie A in Home».

## Dati e recupero

Fonte **FotMob**, endpoint `teams?id=…&ccode3=ITA` e `matchDetails?matchId=…`. Nessuna nuova chiave o sottoscrizione. Il [profilo pubblico del club](https://www.fotmob.com/teams/8636/overview/inter) offre un riscontro delle informazioni presentate.

`sport_team_core.py` normalizza il profilo e il calendario multicompetizione. `sport_team.py` esegue HTTP, parsing e scrittura della cache in worker Qt. Le partite del club hanno identità separate da quelle del calendario Serie A; non entrano nel suo registro gol o nelle sue classifiche.

Il dettaglio verifica partita, identificativi numerici delle due squadre e competizione, accettando la relazione tra `leagueId` e `parentLeagueId` utilizzata dalle coppe. I nomi estesi dei club non alterano l’identità della preferita. I provider ID ESPN non vengono usati come ID FotMob.

Cache atomica per club: `sport-team-{providerId}.json`, nella stessa directory di `sport.json`. Un riavvio senza rete conserva calendario, risultati e rosa e li etichetta come precedenti. Un errore nel dettaglio conserva l’ultimo profilo valido e riguarda soltanto la partita selezionata. Cambi rapidi della selezione fanno caricare l’ultima richiesta; un risultato della squadra precedente non sostituisce quella attualmente scelta.

Il profilo si aggiorna normalmente ogni sei ore; il timer anticipa il periodo vicino al calcio d’inizio e usa intervalli più brevi durante gli incontri. Il badge Live e le notifiche gol restano soggetti al collaudo già previsto dalla v0.6. Aggiornare un solo dettaglio non rende fresco l’intero calendario salvato.

In assenza del profilo completo resta consultabile il calendario Serie A disponibile, dichiarato **parziale**. Gli orari non confermati non diventano appuntamenti certi, neanche aprendo il dettaglio. Campi assenti restano «—» o «Non disponibile»; non vengono inventati punteggi, rosa o statistiche.

## Verifiche completate

- `check_sport_team.py`: **7 test** su profilo reale, quattro competizioni, campi nulli/sezioni vuote, identità errate, date da confermare, dettagli futuri, cache atomica e recupero dopo errori.
- `check_sport_team_ui.py`: scelta/salvataggio/rimozione attraverso il decoder HID; tutte le partite e tutti i giocatori raggiungibili; filtro, quattro schede, apertura amichevole e Champions, selezioni consecutive, ritorno con focus conservato, preferenza/cache dopo nuovo servizio, Home e classifica Serie A.
- Regressioni `check_sport.py`, `check_sport_ui.py`, `check_motorsport_ui.py` e `check_dashboard.py`: passate.
- **Board, dati REST reali:** calendario Serie A di 380 partite; profilo Inter di 53 incontri, 42 futuri e 25 giocatori. Verificati dettaglio futuro amichevole, futuro Champions e risultato concluso con statistiche e formazioni. Cinque richieste HTTP nel controllo iniziale.
- **Board, EGLFS 960×640:** catture del selettore, calendario, ultima partita, filtro, dettaglio Champions, informazioni e rosa; **zero avvisi QML** durante la verifica automatica. Catture esaminate direttamente.
- **Board, processo nuovo senza rete:** preferita, 53 incontri e 25 giocatori recuperati dalla cache; stato `offline`, nessun badge Live. Non è stato eseguito un reboot del sistema operativo per questa aggiunta.

Resoconti e immagini: [evidenze](./evidence/v06-favourite-team/), [online](./evidence/v06-favourite-team/team-online.json), [navigazione](./evidence/v06-favourite-team/team-ui.json), [offline](./evidence/v06-favourite-team/team-offline.json).

## Limiti

«Tutte le partite future» significa tutte quelle **già pubblicate dalla fonte**: sorteggi e turni ancora non definiti non possono comparire. Il collaudo completo del profilo è stato svolto sull’Inter, non su ciascun club. Statistiche e formazioni dipendono dalla copertura della partita. Non è stata verificata la latenza dei risultati durante un incontro live, né aggiunti loghi o una garanzia di 60 fps continui.

Backup della versione precedente sulla board: `/var/backups/smartpc-dashboard-favourite-team-20261001/dashboard`. Per rollback, fermare `smartpc-dashboard.service`, ripristinare il contenuto della directory salvata in `/opt/smartpc/dashboard` e riavviare il servizio. I dati del controllo si trovano in un profilo QSettings isolato: non impostano l’Inter come preferita dell’utente.
