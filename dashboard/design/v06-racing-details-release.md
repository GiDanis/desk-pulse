# v0.6 · dettagli F1 e MotoGP

Aggiornamento del 1 ottobre 2026, implementato e installato sulla Orange Pi.
Decisione dell'utente: arricchire weekend, circuito e risultati; nessun pilota preferito.

## Esperienza sul display

- **Weekend → 4/6:** Sessioni, Circuito, Riepilogo. Il riepilogo usa i referti già caricati; le sessioni non ancora pubblicate rimangono assenti.
- **Sessione → Risultati → 5:** dettagli del pilota selezionato nella sessione. Nessun nuovo modulo o sistema di preferiti.
- **F1:** posizione, tempo/distacco, punti, griglia, differenza griglia-arrivo, giro veloce, giri, stato, Q1/Q2/Q3 quando presenti. La differenza griglia-arrivo non conta i sorpassi.
- **Gara F1 → 4/6:** Dettagli, Soste, Giri, Gomme. Nelle altre sessioni compaiono Dettagli e Gomme. Soste usa la durata in pit lane fornita da Jolpica, non il solo cambio gomme. Giri è limitato a 100 risultati per pilota e segnala l'eventuale elenco parziale. Gomme mostra mescola, giri dello stint e vita delle gomme al suo inizio.
- **Libere e qualifiche Sprint F1:** referti OpenF1 delle sessioni concluse, con nomi/team della stessa sessione. Non si riutilizza la classifica piloti come elenco iscritti.
- **MotoGP Circuito:** lunghezza, curve destra/sinistra, rettilineo, giri Gara/Sprint, distanza, paese e località. F1 usa circuito, paese e località realmente presenti in Jolpica: nessuna lunghezza inventata.
- **MotoGP Sessione:** pista asciutta/bagnata, temperatura aria/asfalto, umidità e meteo registrati, con ora della sessione e stato. Non sono previsioni.
- **MotoGP Risultati:** moto/costruttore, numero, nazionalità, velocità media e giro migliore quando forniti; record del circuito/pole nel riepilogo.
- **Timing → 4/6:** Tempi, Pista, Direzione. **5** apre distacchi, ultimo/miglior giro, settori, gomme/soste e stato box disponibili per il pilota. MotoGP conserva i soli campi del gateway lite; non promette gomme o telemetria.
- Liste a tre righe, **2/8** scorre, ritorno conserva sessione e pilota selezionato. Etichette fisiche **1 Indietro / 7 Home**. Nei pannelli informativi e nei dettagli, **5 Aggiorna**.

## Fonti, costo e account

| Fonte | Uso | Costo / account |
| --- | --- | --- |
| [Jolpica](https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md) | Calendario, classifica, gara/qualifiche/Sprint, giri e pit stop | €0, nessun account |
| [OpenF1](https://openf1.org/) | Libere, qualifiche Sprint e stint storici dal 2023 | Piano storico gratuito senza account o API key |
| [SignalR Core, protocollo FastF1](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/livetiming/client.py) | Timing F1 con topic aggiuntivi | Accesso osservato senza account; completezza attiva ancora da verificare |
| PulseLive REST / gateway lite MotoGP | Programma, circuito, condizioni, risultati e timing disponibile | Endpoint osservati senza account o chiavi |

Il live OpenF1 costa €9,90/mese ed è escluso. La finestra live del provider termina 30 minuti dopo la sessione. L'adapter richiede anche almeno due ore dall'inizio prima di ricercare la sessione storica. Identità verificata per stagione, tipo, paese normalizzato e orario; sessioni ambigue o ancora attive non vengono unite ai risultati.

La ricerca OpenF1 usa `%20` nei nomi delle sessioni: durante la prova `Practice+1` ha restituito 404. Confronto dei paesi Jolpica `UAE/USA/UK` con i nomi OpenF1. Nessun endpoint `latest` per associare i referti storici.

## Implementazione e recupero

- `racing_details.py`: dati aggiuntivi, identità OpenF1, dettagli per pilota, righe informazione normalizzate.
- `motorsport_core.py`: conserva i campi dei provider, referti opzionali e circuito/condizioni. Decorazione delle viste separata dal dato salvato.
- `motorsport.py`: richieste in worker, selezione del pilota transitoria, recupero della selezione più recente anche se arriva durante una richiesta.
- `Main.qml` / `MotorsportOverlay.qml`: nuove schede e navigazione senza nuove preferenze.
- `racing_timing.py`: tre topic aggiuntivi TimingAppData, TimingStats, WeatherData; RaceControlMessages era già sottoscritto. Se i topic opzionali vengono rifiutati, la riconnessione torna agli otto topic di base.
- Budget OpenF1 prudente: 25 richieste/minuto, distanza di almeno 400 ms; i topic compressi di telemetria non sono sottoscritti. Dettagli caricati all'apertura e conservati nelle cache esistenti.
- Le cache precedenti rimangono leggibili. Campi mancanti, errori delle fonti aggiuntive e assenza di risultati sono visibili; una richiesta aggiuntiva fallita non elimina il referto principale.

## Prove eseguite

[Dati reali acquisiti sulla board](evidence/v06-racing-details/online.json):

- Abu Dhabi 2025: 20 piloti nelle Libere 1; qualifiche Sprint di un altro GP: 20 piloti.
- Verstappen, gara di Abu Dhabi: una sosta in pit lane, 58 tempi sul giro, due stint. Referti e stint identificati per GP/sessione/pilota.
- Austria MotoGP 2026: circuito con otto campi informativi, quattro record nella risposta, condizioni pista Dry / aria 23º / asfalto 16º / umidità 39%.
- Nessun account, token o abbonamento usato; 32 richieste complessive nella prova delimitata.

`check_motorsport.py`: 11 controlli, inclusi identità/codifica OpenF1, cache, errore aggiuntivo e budget. `check_motorsport_ui.py`: navigazione HID delle nuove schede, dettagli pilota, ritorni, timing, modalità offline, stagioni e impostazioni, eseguito su PC e Orange Pi. Controllo UI Fantacalcio sul PC passato senza avvisi QML.

[Catture EGLFS](evidence/v06-racing-details/render.json): 16 schermate 960×640, renderer OpenGL sulla board e zero avvisi QML. Ispezionate direttamente le schermate Dettagli pilota F1, Circuito MotoGP, Condizioni MotoGP e Gomme delle libere. Non è una misura di prestazioni continuative.

[Cache a freddo](evidence/v06-racing-details/offline.json): nuovo processo senza richieste di rete; restano dettagli F1, stint/giri, circuito e condizioni MotoGP. Non è stato riavviato il sistema operativo.

[SignalR reale](evidence/v06-racing-details/timing.json): 11 topic ricevuti senza autenticazione, 22 righe, condizioni pista/meteo e otto messaggi di direzione disponibili. La sessione risultava `Ends`: conferma dello snapshot concluso, non del live attivo. MotoGP live, latenza, completezza dei campi durante gara e badge Live restano da collaudare; i gate sono mantenuti disattivati.

## Installazione e ripristino

Backup precedente: `/var/backups/smartpc-dashboard-racing-details-20261001/dashboard`.
Fonte installata confrontata con hash SHA-256 per Python/QML principali. Dopo il riavvio del servizio: `active/running`, `NRestarts=0`, nessuna voce di errore nel journal dell'invocazione controllata. Configurazione e preferenze di produzione non sono state sostituite dai controlli isolati.

Ripristino: fermare `smartpc-dashboard.service`, ripristinare i file della cartella di backup in `/opt/smartpc/dashboard`, rimuovere il nuovo `racing_details.py` se si vuole la versione precedente completa e riavviare il servizio. Le cache sono compatibili con la precedente lettura.
