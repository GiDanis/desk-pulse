# Gioco v0.9 — Scheda Pilota, storico e reset

11 ottobre 2026 · **0.9.0-rc.6 installata** · Theme API 2.9 / 68 superfici / Apple Calm 1.6.2.

## Prodotto e comandi

Quarta vista **Pilota** nella famiglia Gioco. **5** apre la scheda del pilota selezionato; **4/6** cambia Sintesi/Metodo/Storico/Risultati/Reset, **2/8** scorre le righe e pagina, **7** torna indietro. Nella Sintesi, **5 sulla riga Pilota** sceglie il successivo; resta disponibile la selezione dal menu Gioco. La scheda non avvia calcolo o allenamento.

- **Sintesi:** tempo attivo e passi dall'ultimo reset, durata complessiva inclusi gli allenamenti archiviati dai reset, numero di sessioni/reset, disponibilità e qualifica del modello, gare concluse/arrivi/vittorie e data di creazione. Una posizione 1 con ritiro non conta come vittoria.
- **Metodo:** profilo attuale e, quando presente, profilo della rete salvata per gareggiare. Mostra metodo, popolazione/tentativi, neuroni iniziali, seed, durata episodio e traffico; mutazione per Evoluzione/NEAT, learning rate/gamma/rollout/epoche per PPO. I neuroni indicano l'architettura iniziale, non il numero evoluto di nodi NEAT.
- **Storico:** sessioni del solo pilota, stato e profilo originale, cambi di parametri, valutazioni e reset. **5** su una sessione apre durata/passi e parametri registrati; su un cambio profilo mostra prima/dopo. Pagina tutte le sessioni e gli eventi significativi, senza trattare ogni autosalvataggio come una nuova sessione.
- **Risultati:** gare, prove standard, osservazioni Campione e valutazioni. Data, posizione/stato/giri, tempi disponibili, arrivi nelle prove e promozione del campione provengono dai dati salvati. I risultati delle versioni precedenti sono riconoscibili; una sessione interrotta non diventa un arrivo.
- **Reset:** prima richiesta, quindi scelta iniziale **Annulla** e seconda scelta **Conferma reset** con nome del pilota. Cambiare scheda, uscire o aprire il menu annulla la conferma pendente.

Reset ammesso solo da fermo, dopo il salvataggio. Azzera rete da gara, candidato, checkpoint, curriculum, passi e tempo attuali; toglie il pilota dalla selezione Gara. Conserva identità, nome, parametri, storico e risultati delle vecchie versioni. Il precedente stato viene archiviato nell'evento reset, gli artefatti restano immutabili. Gli altri piloti non cambiano. Non è stato resettato alcun pilota dell'utente durante questa consegna.

## Dati e compatibilità

Nuove sessioni Impara registrano **passi e secondi attivi della singola sessione** insieme al checkpoint nella stessa transazione SQLite. Le pause sono escluse; il profilo della sessione non cambia retroattivamente quando si configura il pilota. La durata totale già disponibile resta consultabile per i piloti precedenti. Se una vecchia sessione non ha statistiche proprie, mostra **Durata di sessione non registrata**: non deduce il tempo di allenamento dalle date di apertura/chiusura.

Nuovo renderer pubblico `game.driver`; `game.driver.details` diventa il dossier. Contesti e azioni esistenti rimangono compatibili, payload dossier additivo nelle mappe di GameContext; minor 2.9, registri e riferimenti QML rigenerati. Base/Functional adottano la nuova presentazione; i bundle precedenti ricevono il fallback per la nuova superficie, mantenendo lo stile corrente. Il catalogo delle fixture aggiunge lo scenario senza dichiararlo verificato per sola presenza.

Fisica, reward, reti e regole Gara della rc.5 non cambiano. Il reset conserva la documentazione degli allenamenti, senza attribuire competenza al nuovo pilota azzerato.

## Verifiche

[Otto gate PC](evidence/v09-pilot-dossier-2026-10-11/regression-final/checks.json): **16 test motore**, cinque curriculum, lifecycle Main, nuova scheda, contratto/runtime Theme API, bundle/kit e corpus. Test aggiunti su reset atomico, campi azzerati, isolamento dell'altro pilota, artefatti/sessioni invariati, riapertura dell'archivio, risultati precedenti, parametri prima/dopo, tempo cumulativo e rifiuto delle statistiche di una sessione appartenente a un altro pilota.

[Nuova scheda PC Apple Calm](evidence/v09-pilot-dossier-2026-10-11/pc-dossier/report.json). [Qualifica nativa](evidence/v09-pilot-dossier-2026-10-11/board-native/qualification.json): **EGLFS/KMS 960×640, Base, Functional e Apple Calm**, scala testo 1,1, Main reale, archivi e piloti privati. In ciascuna prova un worker allena realmente il pilota, salva durata/passi e viene fermato; il test esercita pagina, schede, profilo originario, annullamento/conferma/uscita e cambio pilota. Reset mentre il worker gira o su un'altra identità rifiutati; nessun worker parte aprendo la scheda, nessun warning QML.

[Cattura vista](evidence/v09-pilot-dossier-2026-10-11/board-native/apple/pilot-page.png) · [Conferma reset](evidence/v09-pilot-dossier-2026-10-11/board-native/apple/reset-confirmation.png). Risultati gara storici verificati nei test di persistenza con fixture; gara reale di tre giri qualificata nella [rc.5](v09-race-ppo-report.md). Non si dichiara una nuova qualifica di traffico, competenza PPO/NEAT o FPS ottici.

## Consegna

[Pacchetto rc.6](evidence/v09-pilot-dossier-2026-10-11/package.json), **551 file** di runtime verificati; [kit API 2.9](evidence/v09-pilot-dossier-2026-10-11/smartpc-theme-kit-v09-rc6.zip). [Ricevuta](evidence/v09-pilot-dossier-2026-10-11/board-install/final-receipt.json): backup, manifest senza differenze, GUI pronta/fresca, servizio active/running e NRestarts=0; tutte le colonne dei piloti, tutti gli artefatti, tema e preferenze preservati. Riavvio del servizio; nessun nuovo reboot OS. [MasterPlan 2.56](release-masterplan.md) aggiornato con la quarta vista e il reset, mantenendo i gate residui del Gioco e le release successive.
