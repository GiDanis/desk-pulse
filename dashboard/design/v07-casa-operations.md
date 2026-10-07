# Casa / Smart Life · uso e configurazione v0.7

La dashboard consulta Tuya Cloud direttamente dalla Orange Pi. Nessun Home Assistant o server aggiuntivo. Il telefono continua a usare Smart Life per associazioni e comandi; il display non invia comandi ai dispositivi.

## Schermate

Casa compare nel carosello quando il collegamento è configurato e ci sono preferiti. Il primo inventario propone fino a quattro dispositivi con stati leggibili: temperatura, presa, lampada e movimento. Sono proposte modificabili, non una certificazione fisica dei modelli.

- Preferiti: quattro tessere grandi in Base; quattro righe nel profilo Functional.
- Dispositivi: inventario completo, paginato sul display. I dispositivi non scelti possono avere stato non disponibile finché non se ne acquisiscono le specifiche.
- Dettaglio: dati interpretati, qualità, disponibilità e istante della lettura.
- Menu → Impostazioni → Casa / Smart Life: aggiunta/rimozione e ordine dei preferiti, polling e rilettura configurazione. Le righe dei dispositivi seguono i quattro controlli iniziali.
- Menu → Impostazioni → Dati e aggiornamenti → Casa / Smart Life: **5 aggiorna**. L'esito viene confermato solo dopo acquisizione completa e salvataggio; aggiornamento rifiutato durante un altro ciclo o entro 30 secondi.

In Casa **2/8** seleziona un dispositivo, **5** apre il dettaglio. Premere **2 dalla prima riga** seleziona le viste: **4/6** cambia Preferiti/Dispositivi e **8** torna ai dispositivi. In Impostazioni Casa, **5** cambia preferito e **4/6** sposta un preferito. **7** torna indietro, **1** torna Home.

## Nuovi dispositivi, nomi e rimozioni

Associare normalmente da Smart Life. Il collegamento del progetto Tuya deve conservare Automatic Link. Il prossimo aggiornamento completo della dashboard scopre aggiunte e nuovi nomi; la scelta dei preferiti segue l'identità, non il nome. Un nuovo dispositivo non sostituisce un preferito esistente. Rimozioni confermate dopo due acquisizioni complete; un preferito rimosso rimane identificabile come non più disponibile, finché lo si deseleziona. Un errore o una pagina incompleta non elimina dispositivi.

Il gateway Zigbee rimane quello dell'impianto. La dashboard legge ciò che il cloud espone: non è un rilevatore istantaneo di movimento o un allarme. «Online secondo Tuya» descrive la risposta del cloud, non una verifica sulla rete locale. «Cloud letto» è l'ora della nostra acquisizione, non l'ora fisica dell'evento. Offline, cache e valori precedenti sono sempre indicati.

## File privati

- Credenziali board: `/var/lib/smartpc-dashboard/.config/smartpc/tuya-cloud.json`, proprietario smartpc, permessi 600, directory 700.
- Quota: stessa directory, file `tuya-policy.json`. Copiare il [modello disattivato](v07-tuya-policy.example.json) e compilare con **valori reali della console**.
- Cache, preferiti e contatori: `/var/lib/smartpc-dashboard/.local/state/smartpc/casa/`, file separati per account/progetto, permessi 600. Non cancellare il contatore per aggirare il limite.

`periodStart` e `periodEnd` sono inizio/fine effettivi del periodo quota, `serviceExpiresAt` è la scadenza effettiva del servizio; tutti sono timestamp Unix in secondi. `apiAllowance` è la quota mensile assegnata; `consumedBeforeStart` è il consumo totale del progetto già avvenuto prima dell'avvio del conteggio dashboard. Comprende prove e altri client. Per prudenza il passaggio dal limite manuale conserva le chiamate già contate, anche se la console può già includerle. Nessun numero del listino viene assunto come quota assegnata.

Dopo la modifica usare **Rileggi configurazione**. Senza una policy valida: una discovery iniziale se non esiste cache, poi solo aggiornamenti manuali, con limite persistente di **100 richieste HTTP aggiuntive della dashboard**. Le prove precedenti e altri client non fanno parte di questo contatore locale; il consumo Tuya va verificato nella console.

Con policy valida: ciclo base ogni 5 minuti; fino a 1 minuto mentre si consulta Casa, massimo 2 ore al giorno UTC e solo se il margine residuo sostiene la proiezione. Riserva del 20%, conteggio di token/pagine/specifiche/retry prima dell'invio. Scrittori del contatore serializzati con lock e rilettura del ledger, anche durante una prova manuale in un altro processo. Specifiche solo per preferiti nuovi/modificati o una volta al giorno. Errori di rete: backoff 5/10/20/40/60 minuti con piccolo jitter; quota/autorizzazione/API bloccata: polling sospeso. Scadenza o orologio arretrato blocca nuove richieste. La scelta manuale di sospendere il polling è persistente.

Il contatore è relativo a questa dashboard, non una lettura del consumo condiviso del progetto. Il contratto quota è esplicito e va aggiornato per il periodo successivo; non si inventa un rinnovo del servizio.
