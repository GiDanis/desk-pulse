# SmartPC 0.9.0-rc.2 — Gioco, piloti e simulazione

**Consegna successiva:** [0.9.0-rc.3, impostazioni e passo](v09-game-settings-pace-report.md) implementata e installata dopo questo report. Il presente documento conserva esiti e limiti della rc.2.

11 ottobre 2026 · Implementazione autorizzata dopo gli studi. **Candidata implementata e installata; qualifica completa del piano ancora aperta.**

## Funzioni implementate

La famiglia **Gioco**, dopo Rete, comprende **Pista, Classifica e Progressi**. Il display è 960×640 orizzontale, con arena 912×496 e HUD 912×48. Ovale asfaltato asciutto, vettura standard 4,4×1,8 m, strada 10 m e scala uniforme; nessun titolo locale o pannello laterale sottrae spazio alla pista.

**Impara** allena esclusivamente il pilota selezionato. Quattro identità iniziali e creazione di altri piloti, profilo individuale, rete, checkpoint e storico persistenti. Evoluzione, PPO e NEAT sono implementazioni effettive; **PPO e NEAT sono etichettati sperimentali**, poiché il funzionamento numerico non dimostra ancora la qualità della guida. Cambiare struttura, metodo, seed, popolazione o curriculum avvia un nuovo percorso; conserva il precedente modello e la sua provenienza, senza attribuirgli il nuovo metodo.

**Gara** schiera contemporaneamente 2–4 piloti, ognuno con la propria rete congelata. Griglia, conto alla rovescia, tre giri, contatti con ritiro, ordine di arrivo, ex aequo e tempo scaduto sono reali. **Prova** usa cinque condizioni iniziali comuni e conserva risultati con hash dei modelli/configurazione; **Campione** mostra il modello salvato. Solo sessioni concluse alimentano la classifica: una gara interrotta non diventa un risultato completo. Allenamenti e risultati non sono condivisi tra piloti.

Aprire la vista o riavviare il sistema non avvia il calcolo. **5 Start/Pausa**, **4/6 auto osservata**, **2/8 Tutte/Solo auto/Sensori** durante la simulazione. La navigazione è trattenuta fino all'ack reale di pausa; salvataggio e pausa sono stati distinti. Home/uscita sospendono, salvano e rilasciano il processo; al ritorno serve Start. Menu, cambio tema e interruzioni mantengono la sospensione. Guasti del worker o dell'archivio hanno stato esplicito. Le animazioni decorative possono essere disattivate; il movimento funzionale della simulazione continua.

## Motore e persistenza

Fisica dinamica 2D CPU a passo fisso 60 Hz, due sottopassi nominali, con massa, potenza, trazione/frenata, velocità laterale e aderenza combinata. Collisioni tra rettangoli orientati, bordo campionato e sottopassi adattivi limitano il tunnelling; è un modello simulativo semplificato, non una certificazione di un veicolo reale. I giri richiedono checkpoint sequenziali.

Profilo comune **race-32-v1**: cinque raggi, stato dinamico, scostamento/direzione e tre avversari percepibili; rete densa iniziale **32→16→2, 562 parametri**. Sostituisce i candidati numeric9/30 degli studi. Nessun controller geometrico inizializza o corregge le azioni dei piloti: il controller di riferimento serve solo ai test fisici e all'avversario fisso del curriculum.

Processo dedicato avviato su richiesta, BLAS a un thread, snapshot limitati a 25 Hz e rendering separato. SQLite per identità/sessioni; artefatti JSON immutabili con SHA-256, fsync e sostituzione atomica. Checkpoint completi di RNG, mondi, popolazione/specie, optimizer e avanzamento delle minibatch PPO. Una sessione rimasta aperta al riavvio viene marcata interrotta. Il profilo di apprendimento salvato accompagna il modello congelato.

NumPy 2.2.6 e neat-python 1.1.0 sono installati nel venv della board; PPO usa NumPy e gradienti analitici, senza dipendenza PyTorch. Nessun tetto di RAM di 256 MiB: sono controllate memoria effettivamente disponibile e temperature. I limiti dei singoli parametri e di persistenza sono espliciti, distinti da una prenotazione di RAM. Profili ampliati fino a 256 copie non sono ancora qualificati in carico.

TrackSpec, VehicleSpec, TireProfile, SurfaceProfile e ConditionProfile separano contenuti, fisica e pilota. Sono predisposizioni: questa candidata contiene soltanto ovale, vettura e condizioni standard. Nuovi circuiti, sterrato, pioggia e vetture richiedono contenuti e collaudi propri.

## CPU e NPU: risultato effettivo

Una politica Evoluzione realmente appresa è esportata ONNX, convertita con ACUITY 6.30.22 per **VIP9000NANODI_PID0X1000003B**, caricata ed eseguita sulla NPU A733 tramite VIPLite. Corretto il target del simulatore: la variante PLUS errata provocava allocazione e terminazione OOM del compilatore. Le risorse SDK restano sul PC; la conversione non avviene nel training.

Su 512 vettori, errore massimo CPU/NPU **0,0000983**. Il benchmark mantiene il modello caricato e include copia dell'input, flush, esecuzione e lettura dell'output; esclude scrittura delle evidenze. Mediana NPU **63,1 µs**, p95 **86,1 µs**, caricamento iniziale **4,57 ms**. La stessa politica NumPy sulla board impiega **42,3 µs**; due/quattro inferenze CPU circa 84,3/167,1 µs. **Runtime scelto: CPU**, più veloce per questa rete piccola. La dashboard non mostra una falsa attività NPU.

Questa prova dimostra inferenza e parità numerica di un modello. Non certifica guida NPU a ciclo chiuso né una gara NPU con quattro modelli distinti. L'accelerazione resta una possibile estensione per reti/carichi che ne dimostrino il vantaggio. [Misure, modello e scelta](evidence/v09-game-implementation-2026-10-10/npu/runtime-choice.json).

## Prove acquisite

- Dieci prove del motore: fisica/giri, sottopassi, contatti veloci/ex aequo, sensori avversari, ripresa esatta di Evoluzione/NEAT/PPO anche tra minibatch, gradienti PPO, corruzione/isolamento, worker reali e Gara/Prova con modelli distinti congelati. Le politiche volutamente scarse dei test di protocollo non sono prove di abilità di guida. [Esito](evidence/v09-game-implementation-2026-10-10/game-engine-tests-release.txt).
- Evoluzione su cinque seed PC: da inizializzazione casuale a modelli che completano **23/25 giri di valutazione separata** sullo stesso ovale, con perturbazioni iniziali. Quattro modelli completano 5/5; uno 3/5. Non è generalizzazione al traffico o ad altri circuiti. [Risultati](evidence/v09-game-implementation-2026-10-10/learning-evolution-summary.json).
- Inventario regressioni: ultimo risultato positivo per **81 casi** dopo ripetizioni mirate; conservati i fallimenti iniziali e le correzioni. Contratti Theme API e fixture Gioco verificati. [Inventario](evidence/v09-game-implementation-2026-10-10/regression-summary.json).
- Sei profili nativi EGLFS, 960×640: Base, Functional, Apple Calm, giorno/notte, normal/reduced/off, scala 1/1,1 e i tre algoritmi. Zero warning QML, nessun trasporto esterno nei test isolati. Ripetuti dopo le ultime correzioni di lifecycle/provenienza, con ulteriore sessione di 60 secondi. [Qualifica finale](evidence/v09-game-implementation-2026-10-10/board-final-native/qualification.json).
- Sessione nativa Evoluzione **30 minuti**, massimo CPU **56,234 °C**, worker **40.000 KiB**, GUI massimo **213.536 KiB**, pausa ack **55,8 ms**. Il motore fisico/learning è quello della candidata; il soak precede le ultime correzioni di rilascio alla Home e provenienza, coperte dalla ripetizione mirata. Il timing Qt mediano di 17,92 ms è software; **non dimostra 60 FPS costanti o latenza ottica**. [Soak](evidence/v09-game-implementation-2026-10-10/board-native/qualification.json).

Theme API **2.8**, 67 superfici, cinque nuovi renderer/contesti pubblici e azioni additive. Apple Calm 1.6.2 mantiene gli asset e usa le nuove presentazioni compatibili. [Kit aggiornato](evidence/v09-game-implementation-2026-10-10/theme-kit-v09-rc2.zip) con SDK, contratti e dipendenze del Gioco.

## Problemi intercettati durante la qualifica

La prima rc.1 è stata ritirata dopo un reboot che ha causato fallback a Base per timeout del renderer urgente Apple Calm. Ripristinate dal backup soltanto configurazione di aspetto e journal del tema, senza alterare eventi o quota dei provider. Una successiva traccia a freddo ha misurato 5,1 secondi per quel caricamento. La rc.2 assegna 15 secondi al caricamento freddo; cambi/preparazione restano a tre secondi e il supervisore mantiene il limite globale di startup. La prova con cambio rapido dei token ha inoltre individuato una pausa mancante quando non nasceva un candidato: ora la pubblicazione dello stile mette in pausa il gioco.

Urgente, cambio dei token, terminazione effettiva del worker e riavvio esplicito sono passati su PC e nativamente con Base, Functional e Apple Calm, senza warning QML. [Prove rc.2](evidence/v09-game-implementation-2026-10-10/board-rc2-native/qualification.json).

## Distribuzione e gate ancora aperti

Runtime **0.9.0-rc.2**, manifest ricorsivo di **543 file**. Installazione con backup del runtime e stato privato, drop-in systemd per il venv, controllo degli hash, preferenze e tema. La rc.1 e il suo primo reboot fallito restano nel dossier; la ricevuta della rc.2 e le prove finali hanno un percorso distinto. Nessuna sessione di apprendimento viene avviata automaticamente dal kiosk.

**Ricevuta finale:** reboot OS con boot ID cambiato, 543 hash coerenti, tutte le 44 preferenze e Apple Calm 1.6.2 conservati, GUI pronta/fresca e `NRestarts=0`. Checkpoint dei tre backend e due risultati Gara conservati attraverso reboot in store di qualifica separato; ripresa esplicita con nuovi passi accertata per Evoluzione, PPO e NEAT. Nessun pilota di collaudo è inserito nella rosa di produzione. [Installazione/reboot](evidence/v09-game-implementation-2026-10-10/board-rc2-install/final-receipt.json).

**Non è ancora chiuso tutto il piano:** la guida nel traffico resta da qualificare. I modelli allenati in solitario possono scontrarsi o fermarsi in Gara; il curriculum con un avversario fisso esiste, ma non ha ancora una dimostrazione comparabile sui cinque seed né una gara 2/4 con piloti competenti. PPO/NEAT non hanno ancora la stessa prova di apprendimento della baseline Evoluzione. Restano carico dei profili ampliati, accettazione fisica di lettura e tastierino, frame pacing nelle gare e uso prolungato della build finale. Nessuno di questi gate viene chiuso dal solo servizio active.

La prima candidata permette di usare e valutare il gioco. Il completamento della qualifica simulativa e delle competenze dei piloti precede una dichiarazione di v0.9 pienamente qualificata. Compagno v0.10 e Memoria v0.11 mantengono la sequenza approvata.

## Analisi aggiunta per i prossimi passi · 11 ottobre 2026

Lo [studio impostazioni e velocità](game-settings-speed-study.md) registra il feedback d'uso: eliminare la legenda dal menu, descrivere i parametri con testo secondario coerente con il tema e studiare il passaggio dalla guida affidabile al miglioramento del tempo sul giro. Include significato effettivo di mutazione/neuroni/parametri PPO, baseline della ricompensa, Controllo/Passo/Traffico e promozione di un campione verificato. Sono prossimi passi v0.9.x nel MasterPlan revisione 2.52: questa aggiunta documentale non cambia il runtime rc.2 né chiude i gate di apprendimento, traffico o lettura fisica.
