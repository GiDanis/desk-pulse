# v0.9.0-rc.11 · popolazione Evo/NEAT visibile

**13 ottobre 2026 · installata e verificata nel perimetro indicato.** [Evidenze](evidence/v09-population-fix-2026-10-13/) · [manifest 575 file](evidence/v09-population-fix-2026-10-13/release-manifest.json) · [ricevuta](evidence/v09-population-fix-2026-10-13/board/final-receipt.json).

## Correzione

L’Accademia mostrava una preview indipendente singola per tutti i metodi. Evo e NEAT continuavano ad allenare 32 candidati, ma la popolazione era invisibile. Ora la scena legge tutti i tentativi effettivi: nessun passo fisico, consumo RNG o aggiornamento pesi aggiuntivo per disegnarli. Preview superflua disattivata per questi due metodi; PPO/PPO-Smooth/Clone mantengono la propria preview.

- Tutti i candidati presenti, selezione 4/6 su tutta la popolazione, auto selezionata in primo piano; sensori del suo episodio.
- Generazione corrente, numero del tentativo, velocità, esercizio e tentativi conclusi nella fascia compatta esistente. Riga discreta di 32 indicatori; nei primi microesercizi le auto possono sovrapporsi perché partono nello stesso punto.
- Tentativi terminati attenuati fino alla generazione successiva; ID della generazione evita interpolazioni attraverso i reset.
- Sono simulazioni indipendenti dello stesso pilota, senza collisioni fra candidati. Negli esercizi di traffico si mostrano anche i rivali congelati del tentativo selezionato; la camera Duello non associa falsamente due candidati indipendenti.
- Minimap estesa all’insieme delle auto effettivamente presenti. Gara e suoi concorrenti congelati restano nel proprio ramo.

## Verifica e conservazione

19 controlli Accademia PC, precedente giro ARM di 18 controlli e tre controlli finali ARM sulla nuova presentazione/preview/traffico superati. Quattro walkthrough **EGLFS 960×640**: Base/Evo, Functional/NEAT, Apple Calm/Evo Mallory con testo 1,1, Apple Calm/PPO Varano. Nessun warning QML; Start, selezione, cambio camera, Pausa/salvataggio, ripresa e uscita verificati. I timing `frameSwapped` nei report sono misure software, non certificazione ottica 60 FPS.

L’utente ha messo Evo in pausa prima della manutenzione. Checkpoint corrente verificato in sola lettura e ripristinato su istanza privata: **109.295 passi, generazione da mostrare 12**, 32 tentativi e ripresa esatta dopo ulteriore lavoro privato. Nessun riaddestramento del pilota originale.

Conservati tutti i campi dei sei piloti, pesi/checkpoint/storico e **1.261 artefatti** presenti alla consegna. Sessione precedentemente in pausa chiusa come interrotta dalla normale manutenzione: i pesi restano riprendibili con Start. La ricevuta del tentativo finale ha zero sessioni ancora in pausa perché questa chiusura era già avvenuta nel primo tentativo, ripristinato dopo un errore di permessi della cartella delle catture. Nessuna perdita di progresso o modifica del metodo.

575 hash runtime conformi, preferenze e Base attivo conservati; servizio attivo, `NRestarts=0`, heartbeat GUI fresco/pronto. Backup `/var/backups/smartpc-before-population-20261013-121227`, runtime precedente `/opt/smartpc/dashboard-rc10-before-population`. Nessun reboot OS. Le qualifiche estese dei piloti e la taratura fisica restano aperte.
