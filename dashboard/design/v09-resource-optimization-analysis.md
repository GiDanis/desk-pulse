# CPU, GPU, NPU e RAM · audit di ottimizzazione rc.9

**13 ottobre 2026 · analisi, nessuna modifica al runtime installato.** [Evidenze e strumenti](evidence/v09-resource-audit-2026-10-13/). Baseline verificata: **0.9.0-rc.9**, 572 file senza differenze di hash, servizio attivo, nessun riavvio automatico. Piloti originali invariati durante le prove. I processi di benchmark usano archivi temporanei e il codice installato; il servizio rimane acceso. Non sono stati cambiati governor, priorità della dashboard, preferenze o pesi dell'utente.

**Seguito implementato e consegnato:** [rc.10 · ottimizzazione CPU, scene, GPU e buffer](v09-optimization-report.md). Le misure seguenti restano il baseline rc.9; non sono lo stato prestazionale della nuova candidata.

## 1. Risposta

**La ripartizione dei compiti è sensata, ma il sistema non è completamente ottimizzato.** GPU per Qt Quick, CPU per fisica/sensori/training, RAM per stato/cache: coerente con il carico attuale. Il limite misurato è il lavoro seriale di preparazione dell'ambiente e delle osservazioni; non la quantità di RAM o una dimostrata saturazione della GPU. La NPU non viene usata dal gioco e non è il primo intervento da fare.

Non occorre consumare tutte le risorse disponibili per usarle bene. Occorre aumentare le transizioni utili al secondo e rispettare il tempo della GUI, mantenendo fisica, RNG, checkpoint e comandi corretti.

## 2. Hardware e dati correnti

| Risorsa | Osservazione sulla scheda | Interpretazione |
| --- | --- | --- |
| CPU | 6 Cortex-A55 (CPU 0–5, massimo 1,794 GHz) + 2 Cortex-A76 (6–7, massimo 2,002 GHz); `schedutil` | Non otto core equivalenti. Worker e GUI sono osservati sui core grandi, ma senza affinità obbligatoria. |
| GPU | PowerVR; librerie EGL/GLES PVR caricate, `/dev/dri/card0` e `renderD128`, `QSGRenderThread` | Grafica accelerata presente; nessun training GPU nel codice. |
| GPU DVFS | `simple_ondemand`, 400 MHz osservati; OPP 400/600/800/1008 MHz, nessuna transizione registrata | Non dimostra saturazione né necessità di alzare la frequenza. Servono misure durante rendering attivo e contatori validi. |
| NPU | Device devfreq presente, 492/852 MHz; governor `performance`, 852 MHz; dominio di alimentazione `on` | Presenza e frequenza non significano inferenza attiva. Il gioco non richiama il runtime NPU. Possibile approfondimento energetico del driver/power management. |
| RAM | 5.718 GiB circa esposti al sistema; 5.287 GiB disponibili nel primo inventario; swap usata 0 | Nessuna pressione di memoria nel campione. La cache Linux è riutilizzabile: RAM “non libera” non equivale a RAM indisponibile. |
| Temperatura | 39–42 °C nel primo inventario; massimo tra le zone campionate nelle due prove worker 45,38 °C | Nessun segnale termico critico nel campione breve; non è una qualifica di uso prolungato. |

**Correzione documentale:** il vecchio [studio fluidità](v09-fluidity-and-performance-optimization-study.md) riportava T527, quattro A55 e Mali-G57. Quella identificazione non descrive questa scheda: il device tree espone `xunlong,orangepi-4-pro`, piattaforma `sun60iw2p1`, e l'inventario corrente mostra A55/A76 e PowerVR. Anche l'identificazione commerciale della scheda va separata dai dati del SoC effettivamente letti. Le misure della vecchia release non sono misure rc.9.

Il driver PVR ha restituito in un primo campione `GPU Utilisation: 200%`, poi 0% a riposo, con stati driver/firmware OK e contatori di errori a zero. **Il 200% non viene usato come percentuale affidabile di saturazione.** Nessuna conclusione su banda DRAM, carico GPU o watt viene dedotta dalla sola frequenza.

## 3. Protocollo e limiti

1. Dashboard installata osservata per 8 s: CPU per thread, RSS/PSS, memoria disponibile e frequenze/temperature.
2. Worker PPO-Smooth privato per 18 s, Partenza/Ovale, poi Pausa/Salvato; worker Gara privato per 18 s, quattro riferimenti congelati/circuito tecnico. GUI installata sempre sulla Home.
3. Profilazione `cProfile` per 6 s ciascuna di Evoluzione/NEAT/PPO/PPO-Smooth/Clone in Partenza; PPO anche in Sorpasso e Gara 4 su Varano. Preset iniziali, non checkpoint reali addestrati. Questi brevi campioni non arrivano agli aggiornamenti dell'optimizer: descrivono raccolta/ambiente.
4. Le prove EGLFS della consegna rc.9 restano evidenze separate della vista Gioco effettivamente renderizzata. Non vengono sostituite dai benchmark headless.

CPU% è riferita a **un core**: 100% non significa tutta la CPU a otto core. PSS evita di sommare integralmente pagine condivise; RSS resta diagnostica. Gli intervalli delle scene misurano la coda IPC, non i fotogrammi GPU, il display o la latenza USB. `cProfile` aggiunge costo: transizioni/s profilate non sono benchmark di velocità assoluta o qualità di apprendimento. Tempi cumulativi annidati non vanno sommati.

## 4. Risultati dei processi

| Caso | CPU GUI, un core | CPU worker, un core | RAM GUI RSS/PSS | RAM worker RSS/PSS | Scene consegnate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Home, 8 s | 10,75% | — | 216,49 / 201,49 MiB | — | — |
| Home + Impara privato, 18 s | 11,32% | 94,25% complessivi | 217,46 / 201,23 MiB | 42,48 / 30,41 MiB | **11,32 Hz** |
| Home + Gara 4 privata, 18 s | 4,11% | 82,21% complessivi | 215,65 / 199,32 MiB | 39,74 / 27,50 MiB | **18,11 Hz** |

I PSS dettagliati e le letture di memoria sono nel [JSON](evidence/v09-resource-audit-2026-10-13/board-profile.json). Nessun worker usa tutta la CPU della scheda. Il render thread della Home resta a 0 jiffy misurati nel breve intervallo; ciò non descrive la sua attività durante la pista animata. La differenza di CPU della Home nei tre casi risente di timers/provider: non è un confronto A/B di ottimizzazione GUI.

- Impara: mediana consegna scene 79,32 ms, p95 144,17 ms, massimo 155,72 ms; circa 1.623 transizioni nuove in 18 s. Pausa worker 115,49 ms, salvataggio dopo ack 86,09 ms nel campione temporaneo.
- Gara 4: mediana scene 55,42 ms, p95 60,71 ms, massimo 82,60 ms; Pausa worker 9,91 ms.
- Worker `nice=10`, GUI `nice=0` osservati; consentiti tutti i core 0–7. Il vecchio assunto GUI `nice=-5` non è il dato corrente.

Il target del produttore scene è 25 Hz, ma **non è raggiunto in queste prove**. Le interpolazioni QML possono produrre più frame di rendering delle scene ricevute; non ripristinano informazione fisica mancante. È un problema da trattare prima di aumentare popolazioni o introdurre più thread.

Le prove native rc.9, su protocollo differente, registravano riferimento mobile Varano: mediana `frameSwapped` 16,71 ms, p95 34,72 ms; walkthrough Apple/PPO-Smooth: mediana 17,20 ms, p95 37,05 ms. Confermano che 60 FPS costanti non sono già qualificati; non identificano da sole il componente responsabile.

## 5. CPU: dove passa il tempo

| Metodo / compito | Transizioni/s, profilate | Preparazione osservazioni, tempo cumulativo / 6 s |
| --- | ---: | ---: |
| Evoluzione / Partenza | 129,8 | 4,43 s ≈74% |
| NEAT / Partenza | 128,5 | 4,36 s ≈73% |
| PPO / Partenza | 129,6 | 4,41 s ≈74% |
| PPO-Smooth / Partenza | 130,8 | 4,41 s ≈74% |
| Clone / Partenza | 114,4 | 3,90 s ≈65%; maestro esplicito ha un costo aggiuntivo |
| PPO / Sorpasso Varano | 95,7 | 3,53 s ≈59% |
| PPO / Gara 4 Varano | 65,8 | 3,35 s ≈56%; controllori dei rivali circa 1,22 s cumulativi |

I cinque metodi iniziali hanno velocità simile nella raccolta perché condividono un ambiente costoso. In Partenza, circa 42–43% dell'intero campione passa in `ray_distances`; la fisica `World.step` occupa circa 24% cumulativo e la rete non compare tra le funzioni principali. Questo non vale automaticamente per NEAT molto cresciute o per grandi optimizer.

### Calcoli ripetuti verificati nel codice

1. **Raggi frontali scartati:** `World.observations()` calcola i cinque raggi a 50 m, poi nello schema 68 li ricalcola a 150 m e sovrascrive i primi. Mantenere 50 m soltanto per i percorsi 32/42; calcolare direttamente 150 m per 68. Non richiede ridurre sensori o cambiare il comportamento.
2. **Osservazioni di uno stesso stato:** `Episode.step()` restituisce l'osservazione finale; la successiva costruzione del batch la ricalcola. Cache con revisione dello stato, invalidata da step/reset/perturb/restore/contatto. Per PPO, l'osservazione prima del reset e terminated/truncated devono rimanere esatte.
3. **Coordinate e pose:** uno stesso stato ripete `coordinates()` e molte `track.poses()` per offset, punti anticipati, curvature e controllori. Riutilizzare coordinate per stato e raggruppare i punti anticipati senza cambiare geometria/gates.
4. **Traffic curriculum:** quando i rivali sono policy congelate, `Episode.opponent_actions()` può ricostruire le osservazioni dell'intero mondo per ogni rivale. Riutilizzare una matrice per schema/stato. La Gara nel worker già costruisce una matrice comune: non confondere i due percorsi.
5. **Piccoli mondi:** 32 ambienti sono elaborati uno per volta per mantenere la risposta ai comandi. Il costo delle piccole operazioni NumPy/allocazioni domina; aumentare soltanto `OPENBLAS_NUM_THREADS` non parallelizza questa parte.
6. **Preview:** la simulazione visibile avanza nello stesso worker che raccoglie training; `frame()` esegue passi fisici e nuove osservazioni. Il suo costo va separato dalla rete allenata e misurato prima di decidere un processo dedicato. La preview può usare una policy congelata aggiornata a confini dichiarati senza modificare il training; qualsiasi cadenza diversa resta un esperimento.

### Misura separata della preview

Una seconda prova privata usa timer leggeri attorno a `AcademyTrainer.frame()` e `tick()`, senza modificare file installati: 212 preparazioni di scena, mediana **34,39 ms**, p95 **40,95 ms**, massimo **50,45 ms**. Somma dei tempi wall delle chiamate frame **6,32 s**, contro **10,91 s** dei tick del trainer nell'intera vita campionata del worker. Questi timer comprendono il lavoro Python/numerico della preview, non rendering QML o GPU; includono qualche chiamata fuori dalla finestra centrale di 18 s e non sono una ripartizione esatta del tempo CPU.

Nella finestra centrale la consegna resta **11,60 Hz**. La sola preparazione della preview consuma quasi l'intero intervallo obiettivo di 40 ms; il batch iniziale di osservazioni può inoltre rendere un tick molto più lungo (massimo campionato **80,58 ms**). Il problema è quindi già nel produttore CPU/preview anche senza disegnare la pista sulla GUI. [Dati](evidence/v09-resource-audit-2026-10-13/preview-components.json).

La strumentazione registra risultati solo nel processo temporaneo; il primo tentativo non ha raccolto il file dei timer alla pulizia del temporaneo ed è stato corretto. Non viene usato come una misura riuscita.

### Uso dei core

Scelta attuale corretta: GUI separata dal worker, NumPy/BLAS limitato a un thread nel child, nessun training al boot, pacing reale per Gara. Un core impegnato in apprendimento è lavoro utile, non prova di un bug o di contesa DRAM.

Passo successivo: prima eliminare ridondanze; poi provare **2–4 collector di ambienti dello stesso pilota** con learner centrale e avversari congelati. Non significa allenare più piloti insieme. A55/A76 hanno capacità diversa; confrontare scelta del kernel e affinità selettiva soltanto sui processi di prova. Non riservare entrambi gli A76 al training togliendoli alla GUI. [Scheduler Linux](https://www.kernel.org/doc/html/latest/scheduler/sched-capacity.html).

## 6. GPU: usata correttamente, con margini da misurare

Qt Quick usa EGL/GLES PVR e un thread di rendering. Pista, carrozzerie, testo e trasformazioni passano dal scene graph; il training NumPy non viene accelerato dalla GPU. È una ripartizione appropriata per una pista 2D e reti piccole. [Scene graph Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html).

Sono già presenti: geometria preparata sul cambio circuito, guardie dei Canvas nascosti, animazioni condizionate alla visibilità della vettura, polling 33 ms in corsa/250 ms in pausa, coda scene limitata a due pacchetti e consumo dell'ultimo stato. Non riproporre queste correzioni come mancanti.

Residui:

- Canvas sensori visibile occupa tutta l'arena e viene aggiornato per scena. Qt 6 usa `Canvas.Image`: il disegno ha lavoro CPU e l'aggiornamento carica una texture sulla GPU. Verificare linee nel scene graph o un elemento geometrico per i pochi raggi, con A/B sul pannello. Non è interamente “disegnato dalla NPU/GPU”. [Canvas Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html).
- Metadati/statici e scena dinamica devono avere notifiche distinte; evitare conversioni profonde di mappe e binding non pertinenti. Profilare il DTO reale e la vista attiva prima di un nuovo contratto. [Prestazioni QML](https://doc.qt.io/qt-6.8/qtquick-performance.html).
- Camera ravvicinata muove/scalando la pista: verificare cache/tessellazione dei path nelle camere Segui/Duello, senza introdurre layer a tutto schermo indiscriminatamente.
- GPU ferma a 400 MHz non è prova di un difetto DVFS. Solo un carico grafico profilato e contatori attendibili giustificherebbero intervenire sul governor. Nessun beneficio misurato da shader di fisica/training, Vulkan/OpenCL o riscrittura GPU.

## 7. NPU: cosa ha senso fare

Il runtime attuale non richiama la NPU. Il precedente benchmark della rete **32→16→2**, su 512 vettori, misurava CPU 42,3 µs contro NPU 63,1 µs inclusi trasferimento/flush/esecuzione/readback: CPU era la scelta più veloce per quella rete. [Dati storici](evidence/v09-game-implementation-2026-10-10/npu/runtime-choice.json). Non è un confronto delle reti nuove 68→16/32→2.

Nuovo confronto sensato solo dopo le ottimizzazioni CPU: stesso campione congelato, batch 1/4/32, stesso schema e precisione dichiarata; parità di sterzo/gas, latenza completa, caricamento/compilazione, più modelli distinti e costo energetico. Il training con pesi continuamente aggiornati non è già supportato dal solo benchmark di inferenza; ricompilazioni/conversioni possono annullare i guadagni.

In questo campione, spostare la piccola inferenza sulla NPU lascerebbe intatta la maggior parte del costo dei sensori/ambiente. Non usare l'acceleratore per aumentare una percentuale “NPU usata” senza beneficio al prodotto.

**Questione energetica separata:** dominio NPU `on` e governor `performance` pur senza uso dal gioco. Verificare driver, runtime PM, eventuali altri client e consumo reale; non dedurre spreco in watt dalla frequenza. Eventuale sospensione/governor diverso richiede prova wake-up/parità e rollback; non è stata effettuata in questa analisi.

## 8. RAM e persistenza

RAM sufficiente: GUI circa 216 MiB RSS, worker iniziali circa 40–43 MiB nelle due prove, oltre 5 GiB disponibili nell'inventario. Questi worker partono da preset nuovi: checkpoint NEAT maturi, dataset/rollout completi e più processi possono occupare di più.

La RAM si può usare meglio per:

- buffer NumPy preallocati per rollout/azioni/ricompense/osservazioni; conversioni in liste/JSON al salvataggio, non in ogni ciclo;
- cache dei dati geometrici immutabili e delle osservazioni per revisione dello stato;
- ring buffer/shared memory per collector, con dimensioni/versioni e ownership chiare;
- staging dei checkpoint e scrittura atomica fuori dal tratto che deve pubblicare scene, mantenendo ack “Pausa” distinto da “Salvato”.

Oggi `AcademyTrainer.inflight`, `PPO.remember()` e `PPO.updates()` convertono ripetutamente array↔liste, poi ricostruiscono array. È una scelta pratica per checkpoint riprendibili, ma costa CPU e oggetti Python. Usare float32 è una possibile prova numerica, non una conversione automatica: serve parità di fisica/policy/gradienti e RNG nel perimetro richiesto. BLAS multithread ha senso su matrici abbastanza grandi: [configurazione NumPy 2.2](https://numpy.org/doc/2.2/reference/global_state.html).

Non aumentare popolazione, neuroni o memoria del metodo soltanto perché la RAM è libera: i preset dei piloti sono fissi e quei parametri cambiano l'apprendimento. Prima aumentare efficienza dello stesso problema. La riserva attuale `MemAvailable<128 MiB` è una protezione finale, non un tetto all'uso ordinario della RAM.

Persistenza: scritture JSON/hash/fsync/SQLite sono nel worker e preservano durabilità. Il campione di pausa salva in 86 ms, ma non dimostra assenza di picchi SD. La consegna rc.9 aveva già mostrato attese di flush dopo backup e un journal orfano: non eliminare fsync o durabilità per guadagnare FPS. Misurare separatamente preparazione del checkpoint, codifica, scrittura, fsync e commit; considerare formato binario versionato/compresso dopo misura, conservando lettura dei vecchi artefatti.

## 9. Piano di ottimizzazione proposto

| Ordine | Intervento | Verifica prima dell'adozione |
| --- | --- | --- |
| **R0** | Raggi senza calcolo scartato; cache osservazioni/coordinate e punti anticipati raggruppati | Parità 32/42/68 su pose/traffico/reset/restore; stesso passo fisico, giri e sensori. Benchmark con/senza profiler. |
| **R1** | Separare budget della preview, raccolta e invio scene; ridurre lavoro ripetuto dei rivali | Scene vicine al target 25 Hz, pausa/ack/save, niente perdita di tempo fisico o respawn Gara; frame nativi della pista. |
| **R2** | Buffer numerici preallocati; serializzazione solo al checkpoint; dati statici/dinamici distinti | Replay identico, terminated/truncated, PPO likelihood/GAE, dataset Clone/NEAT e checkpoint pendenti; RSS/PSS e pause di salvataggio. |
| **R3** | Collector multiprocesso dello stesso pilota, prima 2 poi eventualmente 4 | Transizioni utili/s, costo IPC, distribuzione sui core, frame pacing GUI, temperatura e conservazione del metodo. Non assumere scaling lineare. |
| **R4** | Sensori via geometria scene graph e profilazione rendering attivo | Confronto tre temi/camere/sensori, tempi GUI/render/GPU separati, carichi normali; poi decidere sul DVFS. |
| **R5** | NPU nuova rete/policy congelata e gestione energetica | Batch/multi-policy/parità/latenza completa e misura di potenza; adottare solo se vantaggioso. |

R0/R1 hanno priorità sul forcing dei clock o sull'aumento dei neuroni. R2 prepara R3 e sfrutta meglio RAM/CPU. R4 e R5 richiedono misure proprie. Nessuna percentuale di guadagno globale viene garantita prima del confronto.

### Gate della prossima candidata

- Stessa fisica, controlli, sensori, schema e preset quando l'intervento è solo prestazionale; qualsiasi modifica numerica esplicita e versionata.
- Preservare checkpoint originali, archivi, RNG, valutazioni pendenti, hash delle policy e qualifiche.
- Benchmark uguali per Ovale/Varano, Partenza/traffico, reti dense/NEAT, Gara 2/4; distinguere raccolta e aggiornamento optimizer.
- Concorrenza con la pista QML effettivamente visibile, misure delle scene e frame `frameSwapped`; target frame 16,67 ms, p95/max e stalli pubblicati. Nessuna qualifica ottica/USB dedotta dai timer.
- Campione prolungato con checkpoint maturi e salvataggi, RSS/PSS/MemAvailable/swap, temperature/frequenze e riavvii.

**Stato finale:** analisi pronta, attività R0–R5 proposte; software installato invariato a rc.9. Restano da misurare optimizer maturi, carico grafico simultaneo ai nuovi benchmark, GPU busy affidabile e energia NPU.
