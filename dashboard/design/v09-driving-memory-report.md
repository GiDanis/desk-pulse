# Gioco rc.12 — memoria personale, rientro e record per pista

13 ottobre 2026 · **Implementata, installata e verificata nel perimetro PC/ARM/EGLFS descritto sotto.**

## Risultato

Ogni pilota che apprende conserva una base propria, usata automaticamente dopo **Start** su un contesto nuovo. Il checkpoint locale ha precedenza. Una base parziale è **In formazione**; la sola Partenza non autorizza il nome **Consolidata**. Metodo e identità restano propri del pilota. Pure Pursuit rimane un riferimento deterministico.

- Evoluzione eredita i pesi, mantiene un individuo esatto e conserva esplorazione; NEAT conserva genoma, topologia e innovazioni, senza conversione in rete densa.
- PPO/PPO-Smooth ereditano l’actor, ricreano critic/ottimizzatore per un contesto nuovo e raccolgono nuovi rollout anche durante il ripasso. Clone riusa soltanto esempi etichettati compatibili.
- Familiarizzazione verifica Partenza, Controllo e Rientro; riparte dal primo stadio non dimostrato. È stato corretto un blocco della verifica Partenza che richiedeva già il Controllo.
- Ripasso: una generazione evolutiva su cinque oppure sei ambienti su 32 per i metodi a gradiente, dopo Partenza. Proporzione iniziale, efficacia quantitativa da qualificare. Scenari evolutivi accoppiati fra individui della stessa generazione.
- Promozione della base: prove nuove, accoppiate con la base precedente, almeno 18/20 per ogni contesto dichiarato; validità conservata e mediana non oltre +5% quando confrontabile. Aggiornamento atomico, versioni precedenti e journal conservati. Qualifiche Gara separate.
- Contesti identificati anche da vettura, gomme, fondo, condizioni, geometria, schema osservativo e fisica. Cache dei descrittori per evitare di serializzare la geometria a ogni reset. Nuove vetture/fondi giocabili e ingressi fisici dedicati restano futuri.

## Fuori pista e reward

La fisica f2-1 distingue già asfalto ed esterno: aderenza 0,95 contro 0,45, rotolamento 0,015 contro 0,045; uscita recuperabile fino a 6 m, contatti graduati e ritiro per impatti gravi. La rc.12 aggiunge **Rientro**: partenza oltre il bordo, 40 m di progresso valido e almeno 2 s consecutivi di guida sicura.

Il progresso positivo richiede terreno nuovo percorso in pista; retromarcia, ritorno sullo stesso terreno e tagli non producono credito duplicato. Fallimento −2, successo del compito +2 una sola volta. Non c’è bonus per ogni uscita/rientro. Il giro pulito e la qualifica restano invalidi dopo violazioni; recuperare non cancella gli errori. Nessun controllore nascosto modifica le azioni dei learner; il riferimento/esperto nominato rallenta nel proprio esercizio Rientro.

Protocollo `driving-memory-1`, reward `valid-progress-recovery-1`. Alla prima partenza del percorso precedente si archiviano gli originali e si eliminano statistiche di fitness/optimizer dipendenti dal reward; pesi/genoma e contatori compatibili conservati. Per i precedenti percorsi v1 → Accademia v2, i contatori della nuova Accademia partono da zero e quelli precedenti rimangono archiviati nel dossier; Evo v2 conserva invece i suoi 109.295 passi. Nessuna migrazione di apprendimento al boot o alla consultazione.

## Impostazioni e dossier

Valori del compito effettivo, descrizioni leggibili e sezioni Rete / Apprendimento / Memoria e riproducibilità. Dati NEAT misurati, tempo/rollout/minibatch/GAE/KL PPO, critic e quota clipping quando presenti; nessuna popolazione neurale inventata per Pure Pursuit. Arresto PPO sull’approssimazione KL oltre 0,03; default GAE 0,95 e minibatch 64 conservati.

Base, provenienza, abilità e risultati nel dossier. **Reset esperienza locale** conserva base e altri contesti; **Reset intero pilota** azzera base/contesti con conferma e archiviazione. Identità, paradigma, risultati e artefatti storici conservati. Importazione manuale avanzata resta un recupero esplicito di reti dense compatibili; il normale riuso automatico include NEAT e non richiede di scegliere il donatore.

## Gara: tutte le vetture e record

Tutte le auto del gruppo rimangono visibili anche in modalità Sensori. Segui/Duello/Sensori sui circuiti lunghi inquadrano l’intero gruppo; Circuito mantiene la panoramica. La minimappa di gara è rimossa per evitare sovrapposizioni. L’ovale allarga l’inquadratura quando una vettura entra nel fuori pista. Sagome e carreggiata usano la stessa scala fisica. Tutti i tentativi Evo/NEAT hanno inoltre un delegate visivo effettivo, senza limite storico a otto sagome.

Telemetria delle sessioni osservate Gara/Prova/Campione:

- Ogni giro è cronometrato al passaggio effettivo dei cancelli sequenziali, con interpolazione nel sottopasso fisico. Pause e conto alla rovescia esclusi. Primo giro da fermo segnalato; giri successivi lanciati.
- Uscite o contatti rendono quel giro non pulito. I tempi rimangono nel risultato, ma il record usa solo giri puliti.
- V max è il massimo della velocità fisica `hypot(longitudinale, laterale)`, campionata nei sottopassi, prima che l’arrivo/ritiro azzeri le velocità.
- Record persistenti delle **sessioni concluse**, separati per pista/geometria, configurazione fisica e Gara/Prova/Campione; schema dei sensori escluso dalla categoria fisica. Pilota, policy e sessione attribuiti. Il massimo può includere la marcia fuori pista; non è una qualifica di guida pulita.
- Classifica mostra record della pista e configurazione della gara/prova consultata. Dossier mostra i record personali sulle diverse piste/configurazioni, anche di modelli precedenti. Cambiare pilota o azzerarne la memoria non cancella i risultati storici.
- Sessioni vecchie prive di telemetria mostrano valori assenti. Nessun giro viene ricavato dividendo il tempo totale per il numero di giri. Record di training parallelo e corse interrotte non mescolati con quelli conclusi.

## Prove e studio

[Regressioni PC](evidence/v09-driving-memory-2026-10-13/regression-final.txt): **79 test**. [Record](evidence/v09-driving-memory-2026-10-13/records-tests.txt): **3 test**, giri effettivi, somme dei tempi, snapshot/ripresa, cancelli su quattro piste, contatti/limiti e categorie persistenti. [Contratto Theme API](evidence/v09-driving-memory-2026-10-13/theme-contract-final.txt): **31 test**, uno skip previsto. Lint F superato.

Walkthrough PC Apple Calm: memoria, reset/cancellazione, dossier, impostazioni e gara sensori; Base: popolazione 32 e ovale/fuori pista. Nessun avviso QML. Fixture analitiche e controllori di riferimento sono esplicitamente etichettati: non provano la competenza di un pilota neurale reale.

[Studio cinque semi](evidence/v09-driving-memory-2026-10-13/five-seed-screening.json): 55 casi, cinque metodi, da zero / trasferito / trasferito con ripasso, più mutazioni Evo e varianti PPO. Budget massimo 32.000 transizioni e 45 s CPU per stadio; stop effettivo registrato. Screening di compiti iniziali, non qualifica di guida/traffico. Il primo screening con il vecchio prerequisito è conservato come superato, non usato per scegliere parametri.

| Metodo | Mediana successi da zero | Mediana successi trasferito | Mediana stalli da zero → trasferito |
| --- | ---: | ---: | ---: |
| Evo | 95 | 114 | 23 → 11 |
| NEAT | 84 | 115 | 41 → 19 |
| PPO | 51 | 146 | 18 → 0 |
| PPO-Smooth | 60 | 150 | 18 → 0 |
| Clone | 192 | 384 | 0 → 0 |

Sono conteggi di esercizi, con microobiettivi e possibili stop CPU differenti: non percentuali di qualifica né graduatoria dei metodi. Alcuni casi arrivano a Controllo, molti restano in Partenza. Il ripasso non è esercitato abbastanza da dimostrarne l’efficacia a lungo termine. Mutazione 0,10 e PPO batch 64/GAE 0,95 restano scelte iniziali; non vengono cambiati i preset manuali per un vantaggio marginale nello screening. Confronti su passo/traffico, retention ovale → Varano → ovale e più auto/fondi restano ricerca aperta.

## Consegna e limiti

**0.9.0-rc.12 installata, 582 hash conformi.** [Manifest](evidence/v09-driving-memory-2026-10-13/release-manifest.json), [ricevuta](evidence/v09-driving-memory-2026-10-13/board/final-receipt.json), [qualifica nativa](evidence/v09-driving-memory-2026-10-13/board/native-qualification.json), [piloti reali su copia](evidence/v09-driving-memory-2026-10-13/board/existing-drivers.json).

- ARM: 25 controlli su memoria/record/circuiti superati. Cinque learner reali ripresi deterministicamente su copie; priorità locale, riuso ovale → Varano → ovale e ritorno al checkpoint locale verificati. Pure Pursuit distinto. Include il recente Clone da 2.013 passi; originali intatti.
- Dieci walkthrough EGLFS **960×640**, Base/Functional/Apple Calm: Evo/NEAT/PPO, impostazioni, dossier, memoria/reset, gare sensori su ovale/tecnico/Varano, due gare complete di tre giri con 2/4 riferimenti congelati. Nessun avviso QML nel perimetro osservato. Fixture analitiche/spread/record dichiarate; le corse complete misurano realmente i tempi.
- Gara 2: giri migliori 31,659 e 32,782 s; Gara 4: 31,659 / 31,621 / 32,848 / 32,842 s. V max circa 35,70 km/h. Tutti e tre i giri puliti per ciascuna auto; questi risultati riguardano il circuito tecnico e controllori di riferimento, non una qualifica neurale.
- Pausa confermata nei campioni Evo/NEAT/PPO: 23 / 27 / 42 ms. Timing software `frameSwapped`: mediane 16,9–17,4 ms, p95 24,0–29,3 ms e massimi circa 294–308 ms nel breve walkthrough. Non è prova di 60 FPS ottici costanti. Worker iniziali circa 38–45 MiB RSS e due thread; carichi maturi separati.
- Tutti i campi dei sei piloti, tabelle preesistenti, **1.265 artefatti** e preferenze confrontati/preservati. Nessuna sessione attiva o in pausa alla consegna. Nuove tabelle vuote dopo boot: memoria/contesti si inizializzano solo allo Start esplicito. Base attivo, Apple Calm 1.6.2 disponibile; API 2.10/68 superfici conservata.
- Servizio active/running, NRestarts=0, heartbeat fresco del PID GUI installato; stesso boot, nessun reboot OS nuovo. Backup `/var/backups/smartpc-before-driving-memory-20261013-152744`, runtime precedente `/opt/smartpc/dashboard-rc11-before-driving-memory`. Schema SQLite user_version 2 conservato, tabelle additive. Dopo il primo Start moderno, per ripristinare un runtime storico occorre selezionare l’archivio precedente compatibile: il checkpoint con Rientro non va fornito al vecchio trainer.

I due iniziali errori del harness (hard link tra filesystem e aspettativa di un contesto Varano vuoto quando era già allenato) sono conservati nei log, corretti prima della qualifica. Il servizio precedente è stato riattivato dopo i tentativi interrotti; nessuna promozione o reset negli archivi reali.

CPU: simulazione, training e inferenza dei piccoli modelli. GPU: composizione Qt/EGLFS. NPU non selezionata; nessuna nuova affermazione sulle sue prestazioni. RAM allocata dopo Start per ambienti/buffer necessari, nessun learner per ogni pista al boot.

Restano gate scientifici e fisici: competenza dei piloti reali, training esteso/retention a cinque semi, carichi maturi, lettura/input fisici, spegnimento durante un salvataggio e FPS ottici. La presenza della memoria personale non garantisce che un pilota ancora inesperto sappia guidare tutte le piste. Nessun nuovo reboot OS attribuito alla consegna.
