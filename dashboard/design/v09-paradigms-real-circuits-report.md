# Gioco — preset corretti e circuiti metrici

12 ottobre 2026 · candidata 0.9.0-rc.8 installata · Theme API 2.10 · display 960×640.

Seguito implementativo autorizzato dello [studio dei paradigmi](game-paradigms-real-scale-study.md). Le modifiche manuali ai sei piloti e alla fluidità sono conservate. Questo report distingue correzioni del software, compatibilità dei modelli e competenza di guida.

## 1. Circuiti e scala

| Circuito | Sviluppo fisico | Carreggiata nel gioco | Provenienza |
| --- | --- | --- | --- |
| Ovale e Circuito Tecnico | Contenuti precedenti conservati | 10 m | Percorsi e reti storiche conservati |
| Mallory · Ovale | 1.609,344 m, un miglio | 12 m | Ovale semplice ispirato al riferimento ufficiale |
| Varano · Corto | 1.640 m | 12 m uniformi | Ricostruzione della pianta ufficiale corta |

Il [documento di Mallory Park](https://www.malloryparkcircuit.com/wp-content/uploads/2014/03/Mallory-Park-Map.pdf) indica l'ovale di un miglio. Il gioco lo semplifica in due rettilinei e due semicirconferenze: raggio 80 m e larghezza 12 m sono scelte di progetto, **non misure pubblicate di Mallory**. Nessuna sopraelevazione.

La [scheda ufficiale di Varano corto](https://www.autodromovarano.it/wp-content/uploads/2024/04/pista_1640_19.pdf) documenta 1.640 m, larghezza 10–12 m e rettifilo di partenza 467 m. Il tracciato del gioco è ricalcato e raccordato dalla pianta, poi calibrato sullo sviluppo complessivo: **non è un rilievo topografico**, non garantisce il rettifilo esatto di 467 m e usa larghezza uniforme. Altimetria e banking non sono simulati.

Entrambi hanno 768 segmenti, metri come unità, geometria/hash/fonti nel catalogo. Il generatore riproducibile è `dashboard/build_game_tracks.py`. Il primo raccordo di Varano risultava troppo stretto per il veicolo standard; è stato corretto prima della consegna. I test verificano tre giri del riferimento, bordi, assenza di contatto nella griglia da quattro auto e sviluppo metrico.

Auto standard **4,4×1,8 m**, passo 2,65 m. La pista da 12 m è larga circa 6,7 vetture: spazio fisico per scegliere traiettorie e affiancarsi. Bordo disegnato, contatti, raggi, proiezione e cancelli condividono la stessa geometria. Questo spazio non insegna da solo a sorpassare.

## 2. Integrità dei piloti

Un registro comune definisce Evoluzione, NEAT, PPO, Pure Pursuit, Clone e PPO-Smooth. Creare un pilota permette di scegliere uno di questi preset. I parametri sono fissi anche nel backend: `configure`, bozza/Start e chiamate pubbliche non cambiano metodo, rete, popolazione, traffico o seme del pilota. Il primo accesso a un nuovo circuito mantiene il metodo scelto; eliminato il fallback involontario a Evo.

I nuovi percorsi metrici usano `race-42-v2`: conservano i primi 32 canali e aggiungono velocità estesa, larghezza e quattro bersagli anticipati a 15/40/80/150 m. **Le reti storiche restano a 32 ingressi**, con i propri pesi, topologie, RNG e artefatti: non vengono ridimensionate. Nuovi circuiti hanno percorsi indipendenti; il trasferimento controlla anche la versione dei sensori. Reset mirato e storico continuano a preservare identità e altri circuiti.

## 3. Correzioni e ottimizzazioni dei metodi

| Metodo | Intervento |
| --- | --- |
| Evoluzione | Elitismo e nuovi individui conservati; intensità effettiva della mutazione cresce da 1× a massimo 2× dopo stagnazione. Diversità e stagnazione registrate; stato/RNG ripristinabili. Nessuna superiorità di apprendimento dichiarata senza confronto a budget uguali. |
| NEAT | Numero di ingressi coerente col percorso, incluse reti precedenti. Metriche di specie/nodi/connessioni già presenti conservate. Nessun limite di complessità introdotto senza una misura del costo. |
| PPO | Input/critic/rollout coerenti con 32 o 42 canali, incluso bootstrap delle osservazioni successive. Compito e reward migrati esplicitamente. |
| PPO-Smooth | Rimosso il rumore OU con probabilità incoerente. Campionamento gaussiano standard e likelihood esatta; costo moderato della differenza fra sterzo comandato e sterzo fisico. Rollout/aggiornamenti OU pendenti scartati, pesi dell'attore conservati. |
| Pure Pursuit | Vero bersaglio anticipato e velocità limitata dalla curvatura/frenata. Non ha optimizer né contatori di apprendimento nuovi. Start passa alla guida del riferimento. L'artefatto geometrico esatto può gareggiare come riferimento pronto; non riceve un badge di qualifica neurale. |
| Clone | Etichette esplicite del maestro geometrico negli stati visitati, buffer aggregato di 2.048 esempi, batch fino a 128, nessun esempio da auto inattive. Reset dei singoli episodi; dataset e optimizer persistenti. È un'aggregazione in stile DAgger, non un confronto pubblicato con DAgger completo. |

Le vecchie policy `reference` mantengono la guida reattiva precedente. Il dossier indica la versione; le durate storiche di Pursuit non vengono cancellate né riclassificate come nuovo apprendimento. Nuovi percorsi e reset espliciti producono il riferimento geometrico attuale.

Clone apprende il comportamento del maestro e non cerca autonomamente di batterlo. Evoluzione/NEAT/PPO cercano miglioramenti attraverso i propri obiettivi. Il pilota ibrido Imitazione→PPO e SAC rimangono esperimenti successivi, come stabilito nello studio: nessun nuovo algoritmo non verificato viene presentato come pronto.

## 4. Compiti multigiro e provenienza

`driving-task-2`: Controllo richiede un giro; Passo richiede tre giri. Il limite deriva dalla lunghezza del circuito a 7 m/s medi con margine 1,8, rispettando almeno il budget del preset. Per Varano sono circa 422 s a un giro e 1.265 s a tre giri; il veicolo non è obbligato a quella velocità.

La Gara usa i 3/5/10 giri scelti e un limite proporzionato, con almeno 300 s. Prova segue lo stesso numero di giri, una vettura per pilota, protocollo `time-trial-laps-2`; totale tentativi e giri sono letti dai risultati, senza mostrare sempre `/5`.

`control-pace-3` normalizza il riferimento temporale del bonus al compito. `paired-10-laps-v2` confronta candidato e campione su dieci scenari identici, separati dal RNG di training. Sui nuovi circuiti un modello neurale diventa eleggibile dopo almeno **9/10 arrivi su tre giri**, con esatto hash della policy e ambito del percorso. Non è una certificazione del sorpasso.

Cambio del compito: mondo e rollout incompatibili ripartono; rete e contatori sopravvivono. Cambio del reward PPO: esperienza/critic/optimizer incoerenti vengono ricreati, attore conservato. Valutazioni pendenti di versione precedente vengono scartate. Checkpoint, sessione e dossier registrano il compito effettivo; i dati vecchi mancanti non sono inventati.

Il traffico esistente usa ora un bot geometrico con anticipo e velocità prudente anche sulle piste lunghe. L'ingresso automatico in scenari di sorpasso e la relativa qualifica restano lavoro sperimentale: il training solitario non viene dichiarato sufficiente per gare pulite a quattro.

## 5. Camera e risposta dell'interfaccia

Sui circuiti lunghi:

- **Segui:** auto osservata e anticipo, orientamento geografico stabile, zoom legato alla velocità.
- **Duello:** include il rivale vicino, con scala comune a pista e auto.
- **Circuito:** panoramica completa con proporzioni fisiche.
- **Sensori:** guida ravvicinata e raggi diagnostici.

Minimappa 150×100 con gli stessi bordi e marcatori di posizione. Durante la simulazione **4/6 sceglie l'auto, 2/8 cambia camera, 5 mette in pausa** e restituisce la navigazione. Riduzione del movimento rispettata. Le verifiche automatiche del routing non certificano lettura o uso del tastierino fisico.

I bordi dei circuiti metrici passano alla GUI come percorsi SVG statici; migliaia di coordinate fisiche restano nel worker. Nessuna importazione NumPy per ottenere il contenuto visivo. [Misura isolata](evidence/v09-paradigms-real-circuits-2026-10-12/gui-projection-benchmark.json): copia/normalizzazione dei soli dati statici, sullo stesso circuito, da circa 4,3 ms a 0,030 ms mediani. Non è una misura di FPS o di velocità di apprendimento.

La minimappa usa otto delegate stabili, come l'arena, evitando ricreazioni del modello ad ogni scena; l’avviso Qt riprodotto nel cambio del disegno iniziale dell’ovale al circuito nuovo è stato corretto mantenendo stabili anche le delegate delle strisce di partenza e delle righe. Le impostazioni sono caricate soltanto nel Menu; la candidata finale è stata riprovata. Le scene obsolete nella coda limitata vengono scartate; pausa/ripresa accelerano temporaneamente il polling. La chiusura conserva il processo finché è effettivamente terminato e impedisce di sostituirlo con un secondo worker.

L'apertura di un archivio già migrato non riscrive più `PRAGMA user_version=2`: la vecchia chiamata forzava un commit durevole anche senza cambiamenti. Una regressione controlla byte e timestamp del database dopo una seconda apertura. Migrazioni effettive e interruzione delle sessioni abbandonate rimangono transazionali. Un errore di inizializzazione dei temi viene ora registrato nel journal del servizio.

## 6. Evidenze e consegna

[Evidenze riproducibili](evidence/v09-paradigms-real-circuits-2026-10-12/): test numerici/fisici, UI PC e native EGLFS, manifest e ricevuta di installazione. Le prove UI usano archivi privati e provider bloccati.

- 16 test del motore, 11 di geometria/percorsi, 10 nuove regressioni di circuiti/profili/likelihood/compatibilità/avvio SQLite.
- 31 test del contratto temi, uno saltato perché il validatore JSON Schema indipendente non è disponibile nel runtime PC.
- Settings Base/Funzionale/Apple, giorno/notte, testo 1,1, avvio esplicito, profili fissi, cambio circuito, pausa/ripresa, reset selettivo e dossier.
- Varano: auto geometrica in movimento, quattro camere e nessun addestramento attribuito al riferimento.
- Gara nativa: due auto su tre giri e quattro su cinque; almeno un arrivo per gara, selezione dieci giri e una sola vettura per identità. Policy salvate congelate. Sono fixture di reti evolutive storiche: i nomi dei piloti nella prova non dimostrano competenza del metodo omonimo. Alcuni partecipanti si ritirano per contatto; nessuna affermazione di gara pulita o sorpassi qualificati.

**Consegna installata:** [ricevuta finale](evidence/v09-paradigms-real-circuits-2026-10-12/board-install/final-receipt.json), manifest di 567 file senza discrepanze; servizio attivo, heartbeat fresco e `NRestarts=0` anche dopo l'avvio normale senza diagnostica. Base attivo conservato; Apple Calm 1.6.2 disponibile. Sei piloti originali, tutte le tabelle SQLite del gioco, 765 artefatti e preferenze invariati. Backup `/var/backups/smartpc-before-v09-20261012-201401`. Stesso boot: nessun nuovo reboot OS attribuito alla rc.8.

I sei checkpoint di produzione sono stati avviati, messi in pausa e ripresi su **copie temporanee**; gli originali non sono stati allenati o resettati. I nove gate numerici iniziali sono passati sulla board, così come la nuova regressione dell'apertura SQLite; dieci gate complessivi sul PC. Le ultime modifiche dopo la qualifica UI nativa riguardano i default delle CLI diagnostiche, l'avvio SQLite e il log degli errori dei temi; nessuna geometria o composizione grafica è cambiata.

I tentativi iniziali d'installazione sono stati respinti dal gate di avvio e ripristinati automaticamente. La diagnostica del servizio ha mostrato attese all'apertura SQLite e al caricamento QML, mentre il backup di oltre 550 MB lasciava centinaia di MB di scritture pendenti. La procedura finale chiude le connessioni SQLite di verifica e completa il flush di backup/staging **prima** di avviare il watchdog. Timeout e durabilità non ridotti; override diagnostico rimosso. Il kernel riporta anche timeout del controller SD durante questo boot: restano un riscontro hardware distinto, non una dimostrazione di stalli CPU o un guasto hardware risolto. [Log diagnostico](evidence/v09-paradigms-real-circuits-2026-10-12/board-native/startup-diagnostic-journal.txt) e [controllo stabile](evidence/v09-paradigms-real-circuits-2026-10-12/board-install/steady.json).

Le misure native di frameSwapped riguardano il movimento osservato, non FPS ottici o una garanzia di 60 FPS costanti. Il frame nativo della Home nella ricevuta dimostra il rendering del kiosk completo, non l'osservazione ottica del pannello.

## 7. Lavoro successivo qualificato come sperimentale

1. Scenari di traffico graduati e modelli congelati dei rivali: guida affiancata, frenata in coppia, sorpasso e reinserimento; distinguere prova solitaria e qualifica traffico.
2. Confronto di almeno cinque seed per metodo a budget uguali sui nuovi circuiti: tempo alla prima qualifica, arrivi, mediana/spread/ritiri e held-out. Includere l'ablazione della mutazione adattiva e del costo sterzo.
3. Costo delle reti NEAT crescenti, carichi ampliati e sessioni prolungate; verifica fisica del 3,5″/tastierino e frame pacing nelle gare più impegnative.
4. Ibrido Clone→PPO e poi un esperimento SAC. Nuove vetture/fondi richiedono contenuti e protocolli propri, non soltanto modifiche grafiche.

Fisica, apprendimento e inferenza di questa candidata restano su **CPU**. Nessuna accelerazione NPU nuova dichiarata.
