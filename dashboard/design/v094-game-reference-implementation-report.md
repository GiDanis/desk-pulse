# Gioco P0–P9 — esecuzione del piano

> **Decisione successiva del 25 ottobre:** fase funzionale Auto chiusa, manutenzione rc.3 installata e verificata; ricerca P0–P9 parzialmente completata e rinviata per passare al nuovo modulo. I gate scientifici non vengono dichiarati superati e le nuove reti restano escluse dalla produzione. [Chiusura corrente e ricevuta](v094-game-functional-closure-report.md). I resoconti sotto mantengono gli esiti e le date originali.

**Aggiornato al 25 ottobre 2026 · release dei nuovi piloti non ancora qualificata.** Autorizzazione: implementare il [piano P0–P9](game-reference-integration-plan.md). Le dipendenze e i criteri scientifici restano vincolanti: una demo riprodotta o un codice installato non qualificano una nuova ricetta.

## Stato dei lotti

| Lotto | Stato e prove correnti |
| --- | --- |
| P0 | Implementati navigazione 2/8 dall’editing, snapshot coerente della lista, preparazione Start nel figlio, stop asincrono e cambio dopo pausa differito fino all’uscita del vecchio worker. La verifica ARM ha riprodotto il timeout della pausa: 2 s nella GUI contro un collector che può attendere fino a 5 s. ACK intermedio e scadenza esplicita separano la richiesta dalla chiusura del collector. Tredici regressioni pertinenti passate su PC e ARM; altre 17 verifiche del laboratorio passate sul PC. Main/QML su copie dei quattro piloti: 16 avvii/salvataggi e gara per ciascun tema Base/Functional/Apple; Apple completa 1.804 s e 116 ulteriori cicli misti senza crash né warning QML. **Fix funzionale installato nella 0.9.4-rc.2**, 654 file verificati, Apple 1.6.4 attivo, dati/preferenze conservati e GUI pronta/NRestarts=0. Target di latenza non completamente raggiunto, dettagli sotto. |
| P1 | Audit separato di candidato, migliore tattico e gara su copie dei checkpoint correnti, uno/due/tre bot. Alcuni candidati passano ma regrediscono nella finestra lunga; la policy gara conservata non dimostra da sola assenza di aggiornamenti del learner. Nessun training personale durante l’audit. |
| P2 | End2Race originale fissato a `769bedb571125b2392b909fa1e0eb0a0c3649322`, ambiente Python 3.11 separato/Torch 2.7 CPU. Otto scenari originali da 8 s: BC/PPO × Austin/Hockenheim × due casi, otto sorpassi senza collisione secondo il valutatore upstream. Sottoinsieme dichiarato, non intera matrice pubblicata. |
| P3 | Adattatore Gymnasium della stessa Episode/World, sei tick fisici per decisione. Checker Gymnasium/SB3, parità esatta azioni/fisica/premi in sette famiglie, separazione della memoria del docente, ripresa esatta e troncamento passati. |
| P4 | Dataset sequenziali per episodio; azione applicata distinta dall’etichetta del docente, DAgger, split e semi riservati. Il vecchio docente falliva le prove prolungate. Il docente `causal-corridor-teacher-2`, con corsia persistente e budget delle gomme per asse, completa 27 finestre di sviluppo da 180 s senza contatti né uscite aggiuntive. Esempi del docente falliti esclusi dal training; conservati come evidenze. Nuove raccolte marcano il primo evento non sicuro per limitare le correzioni DAgger agli stati precedenti il contatto. |
| P5 | Architetture e inferenza temporale implementate, cinque preparazioni indipendenti completate. La variante GRU 128 + memoria manovra 32 arriva a 9/9 finestre traffico per una preparazione; correzioni e confronti modulari migliorano altre preparazioni ma non producono ancora una ricetta comune robusta in tutte e cinque. Dettagli ed esiti negativi per caso conservati; nessuna promozione. |
| P6 | PPO/SAC/TD3 SB3 separati dalla GUI, ripresa esatta di rete/optimizer/replay/RNG/mondo e trasferimento iniziale verificati. Confronti completi a 32.768 decisioni: nessun metodo conserva contemporaneamente miglioramento e tutti i gate di sicurezza. Maggiore ancoraggio, compito a giro singolo e PPO gSDE non risolvono il limite. Confronti dei moduli neurali degli attuatori addestrabili completati, con memoria e normalizzatori congelati: non qualificano un nuovo default. |
| P7 | Banche distinte, promozione a cinque preparazioni e controllo di identità/sicurezza/passo/attacco/attese/gare implementati. Le prove di sviluppo non soddisfano ancora i criteri comuni: **finale non consultato, nessuna qualifica scientifica**. Non vengono creati certificati per aggirare la mancata competenza. |
| P8 | Backend, quattro profili fissi, Start/preview, statistiche, pausa/salvataggio/ripresa, dossier, memoria personale e migrazione atomica implementati. 18 casi Main/QML PC e 18 nativi EGLFS a 960×640 nei tre temi passati, senza warning né Torch nella GUI. Copie private e pesi non qualificati; attivazione reale ancora esclusa. |
| P9 | Solo P0 consegnato in produzione rc.2, 654 file. Ambiente learner ARM separato installato, aggiornamenti reali/ripresa/retention/upgrade e relay Qt passati. Prove native del prototipo completate, dati/preferenze conservati e servizio ripristinato attivo/NRestarts=0, nessun reboot OS. La consegna dei nuovi modelli resta subordinata a P7; nessuna nuova rete attiva. |

## P0: difetti effettivamente individuati

1. In modifica, 2/8 venivano consumati senza muovere il focus. Ora validano la bozza e si spostano senza scrivere il database solo per scorrere.
2. Start e chiusura potevano svolgere preparazione/attese nel thread GUI. La preparazione dell’archivio e del modello è nel figlio; stop/pending mutation sono gestiti dall’event loop con ticket di sessione.
3. Su scheda è stata riprodotta l’interruzione della pausa di Memoria: il limite di 2 s poteva scadere prima dell’ACK, mentre `quiesce()` ammette 5 s. Il worker conferma subito la ricezione; l’interfaccia conserva la fase di attesa/salvataggio. Nessun cambiamento del watchdog esterno.
4. **Difetto del banco di prova:** impostare globalmente TMPDIR sul disco spostava anche l’heartbeat. Profiling nativo: due fsync occupavano circa 32 s. Ora solo i dati dei test usano `SMARTPC_TEST_DATA_TMP`; l’heartbeat rimane atomico ma non durevole in RAM. Journal e preferenze mantengono fsync. Le prove iniziali fallite restano archiviate; non dimostrano un difetto di fork.

Il trasporto locale basato su posix_spawn è un prototipo selezionabile soltanto esplicitamente nei test. La produzione conserva multiprocessing/spawn; nessun vantaggio attribuito al nuovo trasporto senza confronto end-to-end.

La correzione dei difetti riprodotti non attribuisce retroattivamente l’incidente watchdog del 22 ottobre a una singola causa: per quell’episodio manca la traccia completa della GUI.

## Riproducibilità e limiti degli esperimenti

- Runtime GUI PC: Python 3.12/PySide6 6.8.2.1 corrente, non modificato.
- Laboratorio SmartPC: Python 3.12, Torch 2.7 CPU, Gymnasium 1.2.3, SB3/sb3-contrib 2.7.1. End2Race: Python 3.11 e dipendenze originali; override quadprog 0.1.13 coerente con install.sh upstream. Nessuna dipendenza Torch/Gymnasium installata nella GUI.
- `game-reference-run.py` congela sorgenti e manifest per l’intero lavoro, così modifiche successive al repository non cambiano una ripresa. Dataset pubblicati atomici; copie immutabili e hash separano raccolta, BC e RL.
- Le ricette esplorative che cambiano più elementi sono confronti di pacchetti; non attribuiscono causalmente un beneficio a un singolo iperparametro. Dataset aggregati aggiunti al seme di sviluppo non vengono presentati come cinque preparazioni della nuova ricetta.
- La parità di inferenza e un basso errore supervisionato non garantiscono una guida prolungata senza contatti. Gli esiti negativi rimangono espliciti; non si promuove la rete che “sembra migliore” guardando il finale.
- Primo walkthrough PC interrotto da quota dell’area /tmp; ripetuto su SSD e passato. Il banco ARM usa hard link soltanto per artefatti immutabili e copie reali del DB. Durante il soak è stata eseguita la retention **solo nell’archivio privato** per limitarne la crescita; registrazione separata. Originali e backup non potati.
- I tempi dei comandi sono software. Sul soak Apple sono comparsi picchi oltre l’obiettivo iniziale di 250 ms; misure finali: Base p95 30,2 ms/max 129,1; Functional 27,9/147,2; Apple 39,5/544,0 su 2.810 comandi, otto oltre 250 ms. Nel campione esterno di heartbeat compaiono intervalli fino a circa 2,8 s. Nessuna di queste misure è latenza HID o FPS ottici; il target di reattività resta parzialmente aperto.

[Evidenze pubblicabili](evidence/v094-game-reference-2026-10-23/README.md). Dati personali, replay, pesi, laboratori e log completi restano nella cache privata `/home/giuseppe/.cache/smartpc-p0-p9-20261023/`.

## Costo del prototipo GRU sulla scheda

Probe privato con Dashboard attiva, NumPy 2.2.6/Python 3.13.5, GRU 128, 300 decisioni per carico, sensori nativi e cache delle osservazioni invalidata prima della misura. Policy sperimentale identificata dall’hash, mai caricata nell’archivio dei piloti.

| Carico | Sensori + reti p95 | Sei tick fisici p95 |
| --- | ---: | ---: |
| Una vettura | 1,69 ms | 9,56 ms |
| Cinque vetture | 4,61 ms | 13,20 ms |

Inizializzazione della policy circa 113 ms nel processo separato; RSS massimo del probe circa 44 MiB. Queste misure descrivono il costo di inferenza CPU e di quella simulazione, non il training Torch, una gara qualificata, gli FPS del display o un vantaggio GPU/NPU. Correzione del metodo: il primo probe riusava involontariamente le osservazioni del test isolato; i JSON pubblicati sono le ripetizioni con sensori freschi e hash dei sorgenti. Nessuna dipendenza nuova installata nel runtime GUI/ARM. [Dati ARM](evidence/v094-game-reference-2026-10-23/arm-temporal-cost.json).

## Lavoro ancora necessario

P0 funzionale consegnato; restano picchi di latenza e verifica HID/ottica. Per la nuova ricetta: correggere la competenza della base nel traffico prolungato, poi dimostrare il beneficio RL sulla propria base e completare cinque preparazioni della stessa ricetta, finale separato e gare due/cinque auto con i modelli esatti. Il backend ARM del prototipo è verificato; la consegna dei pesi finali richiederà la ricevuta legata a quei pesi. Fino ad allora P5–P9 relativi al nuovo learner non sono completati. Nessun reset dei piloti personali effettuato; nessun miglioramento generale o accelerazione esponenziale dichiarati.

## Storico della ripresa per la chiusura dei Piloti — 23 ottobre

Richiesta esplicita di completare la release; lavoro autonomo in corso. La baseline installata rimane la rc.2. Cache privata di questa ripresa: `/home/giuseppe/.cache/smartpc-pilot-release-20261023/`; sorgenti iniziali e sorgenti di ogni esperimento congelati separatamente.

### Correzioni e nuovo backend implementati

- Raccolta stepwise della rete con storia: prima ripeteva l'osservazione corrente invece di conservare le precedenti. Ora coincide con il forward sull'intera sequenza.
- Aggiornamento della sola testa della GRU: conserva memoria e cadenza a 10 Hz se encoder/normalizzatori non cambiano. Hash canonico della policy verificato anche usando byte immutabili dell'encoder già serializzati; nessuna serializzazione completa per frame.
- Conteggio globale dei contatti nella banca: gli eventi persistenti non vengono più sommati a ogni tick. Contatti ego e globali restano distinti; i vecchi contatori globali non sono confrontabili come se fossero corretti. Le nuove banche sono versionate e includono gli ulteriori sorgenti che determinano scenari/metriche.
- Tempi di attacco riferiti alle occasioni offerte: partenza già affiancata distinta da nuovo attacco, occasioni ignorate conservate nel denominatore. Il gate controlla anche che siano presenti tutti i casi della banca congelata.
- PPO/SAC/TD3 di riferimento aggiornano la lettura diretta degli attuatori su caratteristiche neurali ricorrenti congelate. Trasferimento iniziale esatto, nessuna seconda imitazione con perdita; replay semanticamente stabile e prior neurale solo durante training. Tattico è la specializzazione TD3 con curriculum racecraft, non un quarto algoritmo.
- Checkpoint atomici con replay compresso, optimizer, RNG, ambiente e memoria; ripresa esatta degli aggiornamenti verificata per i tre algoritmi. GUI e metadati mantengono il loro interprete; Torch appartiene al processo di apprendimento separato.
- Integrazione prototipo: Start esplicito, preview continua con rete congelata per giro, statistiche reali di decisioni/episodi/aggiornamenti, pausa con ACK intermedio, salvataggio periodico su writer, ripresa e stop. Dossier e profili fissi descrivono il backend effettivo. Reset usa la nuova base qualificata, mai la vecchia rete densa per errore.
- Attivazione atomica dei quattro profili e dell'autorità della release nella stessa transazione SQLite; oggetti immutabili durevoli prima dei puntatori. Installazione rifiutata senza cinque preparazioni, qualifiche scientifiche, hash delle policy e ricevuta ARM completa. Percorsi precedenti archiviati e identità/storico conservati.
- La chiusura asincrona del vecchio controller riconosce anche l'ACK `saved`, evitando di lasciare lo stato di salvataggio pendente.

### Confronti effettivamente eseguiti

Tutti i risultati seguenti sono **sviluppo su una preparazione**, non cinque preparazioni della nuova ricetta e non qualifica finale.

| Variante | Risultato osservato sulle 27 finestre da 180 s |
| --- | --- |
| Maggiore precisione dello sterzo e supervisione dell'intenzione, vecchi sensori | Traffico ancora 3/9 valido; aumentare soltanto il fit non risolve il problema. |
| Sensori `direct-physical-90-road-v2` | 5/9 traffico validi, ma regressioni in curva/difesa. Nessuna promozione. La prima rifinitura usa una copia immutabile dei primi 38 episodi pubblicati, non l'intera raccolta successiva da 54. |
| Correzioni DAgger senza intervento | 3/9 traffico validi e molti contatti; non selezionata. |
| PPO, SAC e TD3 sulla medesima base corretta, 32.768 decisioni ciascuno | 3/9 traffico validi per ciascuno; la competenza della base resta il collo di bottiglia. |
| TD3 Tattico, stesso budget, curriculum racecraft | 0/9 traffico validi; regressioni nelle manovre. Non selezionato. |
| GRU con lettura non lineare aggiuntiva | 2/9 traffico validi; maggiore capacità della testa da sola insufficiente. |
| Rappresentazione esplicita della manovra interamente neurale | Traccia di errore: inizialmente sceglie il lato libero, poi perde l'intento durante la curva e rientra verso i rivali. Calibrare il bias del pedale ripristina le prove semplici ma non risolve il traffico. |

Il seguito ha introdotto raccolta con interventi **solo offline**, proposte della rete distinte dai comandi applicati e dagli interventi del docente; controllo fisico supervisionato distinto dalla memoria della manovra. La rete in inferenza continua a scegliere sterzo/gas/freno senza bot o corsie/velocità imposte. Le prove con intenzione oracle sono diagnostiche esplicitamente etichettate, mai qualificabili o esportate come guida autonoma.

### ARM e stato della consegna

Ambiente `pilot-learner-runtime` separato, circa 680 MiB su disco: Torch 2.7.0+cpu, NumPy 2.2.6, Gymnasium 1.2.3, SB3 2.7.1. Import e gradiente CPU verificati; GUI invariata. Primo test completo del prototipo a thread: 12 test, quattro fallimenti per avanzamento del lifecycle entro il tempo previsto, 425 s. Non è una qualifica ARM passata. Il seguito usa processi separati per training e preview; non eredita Torch nella GUI né nel processo dei metadati.

L'utente ha segnalato rallentamento e riavviato la scheda. Dopo il reboot: servizio attivo/NRestarts=0, circa 5,3 GiB disponibili, swap zero, temperature circa 42–43 °C e carico basso nel campione. Non è stata provata la causa del rallentamento. Accesso SSH intermittente anche senza learner attivo; un trasferimento successivo con segmenti piccoli e invio cadenzato ha superato la verifica SHA256. Nessuna modifica persistente alla rete della scheda. Nessuna nuova rete installata, nessun reset dei piloti reali.

### Qualifica, memoria personale e trasporto

Corretto il percorso che avrebbe mandato in Qualifica sempre la base iniziale dei nuovi learner: ora viene congelato il candidato salvato. Il tempo rimane legato a quella precisa policy; gli aggiornamenti successivi non sostituiscono silenziosamente la versione gara. I certificati del vecchio backend restano storici e non abilitano il nuovo. Obiettivi e percorsi preesistenti vengono archiviati durante la migrazione; una seconda installazione dello stesso pacchetto conserva i progressi.

I salvataggi di sorpasso e guida alimentano il candidato personale condiviso. Un nuovo obiettivo parte da quella conoscenza; un checkpoint già esistente mantiene la propria ripresa esatta. La Qualifica può misurare l'ultimo candidato personale. I tempi restano da ottenere su ogni circuito e non si trasferiscono con i pesi. Reset rimuove anche il candidato condiviso. Copertura mediante test su archivi privati; nessuna migrazione di produzione effettuata.

Preview e learner usano ora due processi avviati con `posix_spawn` e socket Unix privati. Rimossi dal nuovo collegamento interno `multiprocessing.Queue`, semafori nominati e ricostruzione del main. La GUI e il processo di preview non importano Torch. Il processo di apprendimento termina se il proprietario viene ucciso; chiusura ordinata, writer e snapshot restano espliciti. Questo elimina il ricorso a un meccanismo IPC già problematico sul sistema; non prova che i precedenti timeout avessero tutti quella causa.

### Ulteriori risultati dello sviluppo

Stessa preparazione esplorativa, nessuna qualifica finale:

| Preparazione | Finestre semplici | Traffico pulito e completato |
| --- | --- | --- |
| Memoria neurale della manovra e due controlli distinti | Solo/attacco/affiancamento/curva 3/3 ciascuno; difesa e recupero regrediscono. | 3/9 |
| Copertura fisica e correzioni con interventi solo offline | Tutte le sei famiglie fuori dal traffico 3/3; mediana solo circa 23,294 s. | 4/9 |
| Ulteriori correzioni negli stati visitati e campionamento degli errori di sterzo/pedale | Le prove semplici restano distinte dagli esiti nel traffico. | 5/9; soglia 7/9 non raggiunta |

La copertura aggiuntiva contiene 50.000 stati fisici supervisionati: partenze, rientri e frenate davanti a rivali. Sono **stati campionati**, non episodi completati o prove gara. Le ablation con intenzione del docente mostrano che anche il controllo longitudinale, oltre alla memoria della manovra, necessita correzioni in situazioni con più vetture. Nessuna intenzione oracle è disponibile nell'inferenza esportata.

Seguito di sviluppo dichiarato: massimo due ulteriori cicli, ciascuno con 18 raccolte a tre bot fino a 150 s, interrotte al primo evento non sicuro, 3.000 aggiornamenti della memoria e 6.000 per ogni controllo. L'interruzione della raccolta è etichettata `censoredAtUnsafe`; non diventa una finestra valida. Ogni ciclo usa nuovi semi di raccolta, sorgenti e dati congelati e le 27 finestre di sviluppo complete; il finale rimane riservato. Superare questo screening non sostituirebbe le cinque preparazioni indipendenti né la dimostrazione del guadagno RL.

### Correzione del metodo di misura ARM

Le prime prove del learner erano limitate con `taskset -c 0,1` ai core A55. Lettura live: CPU 0–5 capacità 385 e massimo 1,794 GHz; CPU 6–7 capacità 1024 e massimo 2,002 GHz. La politica di sistema della Dashboard conserva affinità libera. I timeout di avanzamento su A55 non descrivono automaticamente la capacità complessiva della scheda.

Confronto privato, stesso modello GRU 128, stessi semi, stessi algoritmi e un gradiente per decisione off-policy, otto blocchi per carico. Sensori nativi attivi, Torch a un thread; Dashboard attiva. Tempi mediani per blocco:

| Carico | A55, core 0–1 | A76, core 6–7 |
| --- | ---: | ---: |
| PPO · 128 decisioni | 5,932 s | 1,906 s |
| SAC · 32 decisioni | 3,488 s | 1,368 s |
| TD3 traffico · 32 decisioni | 3,969 s | 1,411 s |
| TD3 racecraft · 32 decisioni | 3,402 s | 1,253 s |

Questo confronto misura il laboratorio e quella rete, non FPS ottici o la nuova architettura completa nella GUI. RSS massimo del processo nel campione A76 circa 390 MiB. L'ipotesi di dimezzare i gradienti è rimasta un'ablation esplicita e non il default: la ricetta conserva un aggiornamento per decisione per SAC/TD3. La suite con socket viene ripetuta senza limitare il processo ai soli A55. Un primo tentativo di questa suite ha fallito nell'ispezione dei figli perché il kernel non espone `/proc/.../children`: aggiunto il fallback su `PPid`, senza attribuire quel difetto del test al learner.


## Ripresa del 24 ottobre: integrazione verificata e confronti indipendenti

La Dashboard reale rimane **0.9.4-rc.2**: nessun nuovo modello attivato, nessun reset dei piloti personali. Per le prove private EGLFS il servizio è stato fermato e ripristinato; nessun reboot OS eseguito. La scheda risponde, servizio attivo con `NRestarts=0`; circa 5 GB disponibili prima dei test privati. Le verifiche successive usano archivi e interpreti separati.

### Runtime e ciclo di vita

La persistenza ora appartiene al processo di apprendimento: checkpoint binario completo, oggetti JSON durevoli, transazione SQLite e memoria condivisa del pilota precedono l’ACK di salvataggio. La preview invia mondo e piccolo readout, senza serializzare una policy completa nel proprio thread. L’autosalvataggio non soddisfa per errore una richiesta manuale di pausa; ripresa comunica lo stesso evento `ready` dello Start. Pausa prima del primo aggiornamento conserva uno snapshot valido a zero decisioni.

La manutenzione dei checkpoint ha un marcatore persistente con intervallo di cinque minuti; non dipende più da dieci salvataggi nello stesso processo. L’ACK durevole precede la manutenzione facoltativa, che conserva i riferimenti correnti, gli archivi e due salvataggi recenti. Test su più riaperture: vecchi optimizer rimossi, modello certificato portatile e due snapshot di ripresa conservati. Non è una prova di soak prolungato su SSD.

Aggiornare in futuro una release mantenendo backend e dimensioni non può riesumare il vecchio candidato personale: memoria, obiettivi archiviati e qualifiche precedenti vengono conservati nello storico; i puntatori personali e le qualifiche attive della vecchia release vengono disattivati nella stessa transazione. Un’installazione identica ripetuta continua a essere idempotente.

### Prove tecniche completate

- **28 test PC** sul nucleo corrente, con hash dei sorgenti prima/dopo invariati: reti temporali, trasferimento esatto dei readout, checkpoint/aggiornamenti, ambiente, promozione, release e lifecycle reale.
- **18 casi Main/QML** su PC, sei per ciascun tema Base/Functional/Apple: Crono nelle tre modalità, Memoria/Linea/Tattico nei sorpassi, avanzamento reale degli aggiornamenti, viste differenti, pausa/salvataggio e stop. Risoluzione 960×640, nessun warning QML, nessun Torch nella GUI. Pesi sperimentali esplicitamente non qualificati; nessuna qualifica o autorità di release fabbricata.
- **ARM, modello reale GRU 128 + memoria 32:** i quattro learner aprono, aggiornano, salvano, ripartono e si fermano; pausa a zero decisioni e relay Qt tra interpreti passati. Due test del runtime e sette del controller passati sul primo snapshot. Ripetizione sulle correzioni di manutenzione/upgrade completata: sette controlli runtime/release e sette del relay Qt passati, con ricevuta distinta.

Nel campione ARM Crono di 40 s, comprendente un autosalvataggio: 1.170 frame attivi, intervallo mediano 33,13 ms, p95 34,89 ms, p99 35,38 ms, massimo 59,54 ms, simulazione mediana 0,9988×. Negli altri sette brevi campioni il p95 varia circa 34,7–50,4 ms. L’ACK di salvataggio durevole richiede circa 2,5–4,0 s; ricezione della pausa e fine del salvataggio restano distinti. Sono misure del produttore software su archivi privati, non FPS ottici, latenza HID, gara o qualifica scientifica. Nessun confronto prima/dopo sullo stesso intervallo attivo dimostra da solo quale componente abbia causato gli stalli storici.

### Cinque preparazioni, senza scegliere solo il risultato migliore

Cinque core originali indipendenti, cinque inizializzazioni degli attuatori e cinque dataset comprendenti raccolte specifiche. Stessa ricetta e budget per ogni preparazione. Ogni valutazione completa contiene 27 finestre di sviluppo da 180 s. Il raffinamento usa correzioni negli stati visitati dal proprio attore; le raccolte interrotte al primo evento non sicuro rimangono esplicitamente censurate.

| Preparazione | Traffico dopo preparazione | Traffico dopo proprie correzioni |
| --- | ---: | ---: |
| 4101 | 6/9 | 4/9 |
| 4102 | 7/9 | 6/9 |
| 4103 | 5/9 | 8/9 |
| 4104 | 7/9 | 8/9 |
| 4105 | 7/9 | 9/9 |

La preparazione 4105 dopo correzioni conserva tutte le prove semplici, senza contatti/uscite aggiuntive nel gruppo; è **un risultato di sviluppo**, non una promozione a cinque semi. Le altre mostrano perdite di sicurezza o di manovre: la sola media del traffico nasconderebbe il problema. I confronti incrociano memoria e attuatori soltanto all’interno della stessa preparazione, con hash di origine e core/normalizzatori identici verificati. Non si mescolano piloti diversi né si sceglie una policy diversa per ciascun caso.

È stato completato il confronto PPO/SAC/TD3 e specializzazione TD3 racecraft, 32.768 decisioni ciascuno, sulla medesima base di sviluppo più solida. Nessun metodo soddisfa tutti i criteri di miglioramento e sicurezza; dettagli nel seguito del 25 ottobre. Le metriche distinguono decisioni, tick fisici, secondi simulati, episodi e aggiornamenti backend. La seconda verifica ha allenato i controlli usando le intenzioni effettivamente prodotte dalla memoria congelata: gli esiti dipendono dalla preparazione e non qualificano una ricetta comune.

**Gate ancora aperti:** preparazione robusta comune, beneficio RL oltre la propria imitazione in almeno 4/5 preparazioni, finale mai consultato per tarare, gare a due/cinque auto per tre giri e consegna dei modelli esatti dopo la qualifica. Le prove native del prototipo sono completate e non qualificano modelli ancora da selezionare. Le prove tecniche completate non autorizzano a sostituire questi gate con certificati sintetici.

[Evidenze della ripresa](evidence/v094-game-reference-2026-10-23/closure-2026-10-24/README.md).

## Ripresa del 25 ottobre: esiti completi e limite del training

### Integrazione nativa completata

Diciotto sessioni EGLFS/KMS, sei per Base/Functional/Apple Calm, schermo 960×640: Crono in Impara/Infinito/Sorpassi e gli altri tre learner nei sorpassi. Aggiornamenti reali, quattro viste, selezione, pausa durevole e chiusura passati; nessun warning QML e nessun Torch nella GUI. Il caricamento a cache fredda del banco richiede 6,1–7,3 s; è distinto dalla latenza di un comando e non allunga il watchdog di produzione. Backup verificato riutilizzato; database, artefatti e preferenze personali rimangono identici. Servizio ripristinato attivo/NRestarts=0, nessun reboot OS.

Correzioni tecniche aggiuntive: processi figli collegati alla vita del genitore anche in caso di terminazione forzata; cache Matplotlib del solo interprete learner per evitare ricostruzioni a ogni nuova directory privata. Il primo tentativo di profiling aveva registrato un file descriptor prima della pulizia dei descriptor nel figlio: un segnale scriveva nel socket. Era un difetto dello strumento, corretto e conservato nelle prove negative; non dimostra un difetto del trasporto.

### Confronti conclusi a budget uguale

La base 4105 dopo imitazione percorre il giro solo in **23,547 s**, con **9/9** finestre traffico valide e zero contatti. Tutti i confronti seguenti sono sviluppo sulla stessa preparazione: non cinque preparazioni RL e non finale.

| Ricetta, 32.768 decisioni | Giro solo mediano | Traffico valido | Contatti ego nell'intera banca | Esito |
| --- | ---: | ---: | ---: | --- |
| PPO, lettura finale | 23,716 s | 9/9 | 0 | Sicurezza conservata, passo peggiore |
| SAC, lettura finale | 22,687 s | 5/9 | 13 | Passo migliore, regressioni di sicurezza |
| TD3, lettura finale | 23,020 s | 5/9 | 360 | Regressioni di sicurezza |
| TD3 Tattico, racecraft | 23,121 s | 7/9 | 0 | Uscite e difesa insufficiente |
| PPO, giro singolo e prior sterzo 1.000 | 23,520 s | 9/9 | 0 | Guadagno minimo, gate congiunto non raggiunto |
| PPO, esplorazione gSDE coerente | 23,655 s | 9/9 | 0 | Passo peggiore; nessuna promozione |

Anche il confronto con ancoraggio dello sterzo 1.000 per tutti i metodi è concluso: non è una soluzione comune e non cambia i default. Addestrare i controlli sulle intenzioni predette, anziché ideali del docente, e scambiare singoli moduli all'interno della stessa preparazione produce vantaggi e regressioni diversi. La preparazione 4102 resta un esempio del compromesso: il controllo sicuro è lento; la maggiore spinta recupera tempo ma perde manovre in curva. Non si nasconde il seme peggiore né si combinano risultati di vetture diverse per ogni caso.

### Intervento strutturale sul controllo neurale

Il learner precedente aggiorna circa 700 coefficienti dell'ultima lettura; i due moduli non lineari che trasformano sensori/intento in sterzo e pedale rimangono congelati. Questo è un limite di capacità di adattamento documentato nel codice, non la prova che sia l'unica causa degli esiti negativi.

Implementata un'opzione esplicita `plastic-actuators-1`: input stabili di 90 sensori normalizzati e due intenzioni neurali, entrambi i moduli degli attuatori e la lettura addestrabili; memoria percettiva, memoria della manovra e normalizzazione congelate. Nessun docente o limite aggiunto ai comandi durante la guida. Il replay mantiene lo stesso significato fra raccolta e aggiornamento. Export NumPy, hash, aggiornamenti IPC, cambio al confine del giro, snapshot e ripresa includono tutti i coefficienti effettivamente addestrabili.

Primo test PPO/SAC/TD3 passato: equivalenza iniziale dei comandi, aggiornamento reale degli strati interni degli attuatori, memoria invariata, ripresa esatta degli aggiornamenti e continuità della cadenza. Confronto di guida preregistrato e concluso sulla preparazione 4105, 32.768 decisioni per metodo; ricetta e risultati separati dalle prove del solo ultimo strato. L'opzione non è selezionata in produzione e richiede gli stessi gate prima dell'attivazione.

[Evidenze del 25 ottobre](evidence/v094-game-reference-2026-10-23/closure-2026-10-25/README.md). Nessun reset personale, finale o modello nuovo attivato.

### Chiusura dei confronti di questa ripresa

Ripetizione comune dei cinque candidati di preparazione sugli stessi sorgenti e sulla stessa banca di sviluppo: **4101, 4103, 4104 e 4105 superano il prerequisito; 4102 perde una delle tre manovre in curva**. Anche la combinazione prudente dello sterzo corretto e un quarto della correzione dei pedali mantiene il passo, ma non risolve quella manovra. Il prerequisito ora richiede esplicitamente anche difesa pulita e passo rispetto al riferimento comune; la qualifica finale v2 controlla inoltre che solo/difesa/recupero abbiano davvero completato le finestre previste. I test rifiutano una finestra conclusa prima del tempo anche se contiene già tre giri puliti.

I due confronti completi dei controlli interni addestrabili sono conclusi: stesso budget di 32.768 decisioni per metodo, base 4105, Gaussian, rete LR 0,000003. Il secondo cambia soltanto il coefficiente di conservazione dei pedali da 0,01 a 1 durante il training; i comandi in guida rimangono liberi.

| Metodo | Moduli interni liberi: traffico valido | Con prior pedali 1: giro solo | Con prior pedali 1: traffico valido | Contatti ego con prior 1 |
| --- | ---: | ---: | ---: | ---: |
| Crono / PPO | 8/9 | 23,587 s | 9/9 | 0 |
| Memoria / SAC | 0/9 | 23,450 s | 5/9 | 18 |
| Linea / TD3 | 0/9 | 26,408 s | 7/9 | 13 |
| Tattico / TD3 racecraft | 0/9 | 22,573 s | 4/9 | 17 |

PPO conserva la competenza ma non supera congiuntamente passo e attesa rispetto alla propria imitazione; SAC e Tattico guadagnano sul giro con regressioni nel traffico; Linea resta lento e perde manovre. **Le varianti non sostituiscono i default né qualificano quattro piloti.** La validazione di attivazione è stata eseguita in sola lettura con questi risultati reali e ha rifiutato la proposta: «Qualifica scientifica incompleta». Nessuna installazione o reset personale.

Il controllo neurale più ampio era un'ipotesi da verificare: gli esiti dimostrano che aumentare i parametri addestrabili da circa 700 a circa 57.500 non basta. Il seguito richiede verificare la qualità delle stime del critic e la conservazione delle competenze durante il passaggio da imitazione a RL, usando transizioni del docente con azioni **applicate**, reward e terminali registrati. I dataset disponibili contengono già tali campi; non è implementato un nuovo replay misto qualificato. [TD3+BC, codice degli autori](https://github.com/sfujim/TD3_BC) e [DQfD, pubblicazione AAAI](https://aaai.org/papers/11757-deep-q-learning-from-demonstrations/) motivano l'analisi della combinazione fra dimostrazioni e RL, senza dimostrare un beneficio nella nostra fisica. Il nostro prior sulla base neurale non è una riproduzione di TD3+BC o DQfD.

### Gare complete e correzione del limite dopo il vincitore

Aggiunto un runner riproducibile che usa `World` e `frozen_actions` di produzione, qualifica a quattro giri e griglie a due/cinque per tre giri. Le prove headless con preparazioni diverse arrivano tutte, ma rilevano otto e venti eventi di contatto: sono diagnostiche, non una qualifica di sicurezza o visibilità sul display.

La prova Main/QML usa qualifiche realmente misurate dalla stessa fisica, quattro copie della base neurale e Maestro, senza fabbricare tempi o autorità di release. Ha riprodotto un difetto: il termine fisso a 30 s dal primo arrivo ferma una vettura più lenta ancora nel suo passo di qualifica. La finestra ora considera la differenza fra tempi qualificati per tutti i giri e un ulteriore giro lento, sempre entro il budget totale. Test numerico e ripetizione completa sul PC passati: due e cinque auto tutte arrivate, **4.378 e 4.663 campioni** con sagome interamente contenute nella scena, nelle quattro viste. Queste copie comuni non sono cinque preparazioni indipendenti e gli arrivi non certificano una guida senza contatti.

### Salvataggi grandi e trasporto della pausa

Il checkpoint della rete estesa ripeteva pesi della base in JSON formattato e nello stato dell'ambiente. Ora la preparazione è un oggetto binario locale verificato dal manifest, lo stato dell'ambiente conserva il suo hash e gli argomenti del costruttore usano array numerici. Nel confronto di dimensione, stessa architettura e forme degli optimizer ma livelli diversi di training: circa **13,3 MB → 2,92 MB**. Il dato non è un'accelerazione ARM. Ripresa esatta dei tre metodi, manifest e compatibilità dei checkpoint precedenti verificati. Stop dopo una pausa durevole riusa lo stesso checkpoint, senza scriverne un secondo identico.

La ripetizione nativa con messaggi grandi ha fallito la pausa nel terzo esercizio di Crono; la Dashboard originale è stata ripristinata. È stato riprodotto un difetto di frammentazione del comando: il figlio vedeva una parte dello snapshot, lo trattava come assenza di un comando completo e poteva iniziare un altro aggiornamento prima di leggere il seguito. Ora completa un comando già iniziato, con timeout locale di 5 s per un mittente bloccato; un canale senza messaggi rimane non bloccante. Test da 2 MB con buffer ridotto passato. Nessun cambiamento al watchdog o ai limiti di pausa/Start della GUI. La prova nativa dei sorgenti corretti è registrata separatamente dalle prove precedenti.

### Ricevuta tecnica finale della ripresa

Sorgenti corretti congelati e confrontati con il PC: **82 file runtime corrispondenti**. Trenta test del nucleo e dieci del controller/trasporto passati sul PC. Sulla Orange Pi: sei controlli di gradienti/ripresa/promozione/frammentazione passati; **18 sessioni Main/QML native**, sei per Base/Functional/Apple Calm, e due gare Apple a due/cinque auto su tre giri completate. Tutte le auto arrivano e restano visibili nelle quattro viste: **3.005 e 2.121 controlli geometrici nativi**. Finestra 960×640, nessun warning QML, nessun Torch nella GUI. Questi campioni non sono FPS ottici né competenza scientifica dei modelli.

La verifica conclusiva conferma core installata **0.9.4-rc.2**, **654 file conformi**, servizio attivo con `NRestarts=0`, heartbeat fresco della GUI e dati/preferenze identici al backup del 24 ottobre. Nessun reboot OS. Le modifiche di questa ripresa e le reti sperimentali rimangono nel prototipo verificato; la produzione non è stata sostituita. Le prove native fallite prima della correzione sono conservate e non sono conteggiate come successi.

**Esito P0–P9:** P0 funzionale consegnato; P1–P4 realizzati nel perimetro dichiarato; P8 e parte tecnica di P9 verificati su copie. **P5/P6 non superano ancora i gate scientifici, P7 finale non eseguito, nuovi modelli non consegnati. L'intera release Piloti non è chiusa.** Il seguito necessario è nel paragrafo sui confronti conclusi; nessuna attivazione viene dedotta dai soli test del software.

### Secondo seguito del 25 ottobre: quinta preparazione e conservazione delle competenze

[Studio completo, codice verificato e risultati](game-learning-retention-study-2026-10-25.md) · [evidenze della nuova ripresa](evidence/v094-game-learning-retention-2026-10-25/README.md).

La correzione propria della 4102, conservata al 75% nei suoi controlli statici, risolve curva e difesa: 3/3 ciascuna, traffico 9/9 e zero contatti. Ripetizione comune delle cinque selezioni sullo stesso codice/banca: **5/5 superano il prerequisito quantitativo di sviluppo**. Non è qualifica di una ricetta comune né assenza di incidenti in tutte le altre preparazioni: 4101/4103/4104 conservano casi problematici esplicitamente riportati.

Implementati replay esperto separato e protetto, variante con contesto aggiuntivo, sonde abbinate del critic e cattura dei candidati intermedi. Otto continuazioni RL da 32.768 decisioni concluse; nessuna cambia il default. Una continuazione SAC con maggiore conservazione dello sterzo produce a 24.576 decisioni un candidato sicuro nella banca: giro 23,547 → 23,488 s, primo passaggio mediano 10,650 → 9,650 s. Attesa −10,6%, sotto il −50% richiesto; a fine training la sicurezza regredisce. Candidato privato conservato come sviluppo, non qualificato o selezionato per Gara; nessun optimizer esatto a 24.576 ricostruito da quello finale.

Il confronto con 348 valori non isola il solo critic: in SAC anche la dispersione delle azioni usa quel contesto. Il semplice replay delle dimostrazioni non conserva tutte le competenze. Corretto inoltre il costo duplicato dell'encoder: in microbenchmark ARM il solo encoder compatto scende 0,693 → 0,410 ms; con contesto 0,692 → 0,525 ms, a feature/memoria/comandi identici. Nessuna deduzione di FPS o throughput complessivo. **25 test PC** e cattura/ripresa CLI passati, benchmark privato ARM senza fermare la Dashboard; stesso PID/NRestarts=0 e manifest invariato.

P6/P7 e consegna dei nuovi modelli rimangono aperti. Finale mai consultato, validatore di attivazione ancora rifiuta «Qualifica scientifica incompleta». Nessuna installazione, reset personale o riavvio del servizio in questo seguito. Le ricevute native precedenti rimangono associate ai loro sorgenti.

## Chiusura della fase funzionale — decisione del 25 ottobre

L'utente dà priorità alla conclusione semplice del modulo Auto e al passaggio al nuovo modulo. Si conserva il prodotto esistente e si consegna la sola manutenzione finale delle gare. Il piano scientifico P0–P9 non è completato: P5/P6/P7 e la consegna dei nuovi pesi vengono rinviati, con banca finale conservata e nessuna soglia ridotta. Non sono prerequisiti per il modulo successivo. [Report della consegna conclusiva](v094-game-functional-closure-report.md). Un'eventuale ripresa della ricerca richiede nuova priorità esplicita e i gate originali.
