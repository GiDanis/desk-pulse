# Gioco rc.26 — scuola guida, esplorazione e stabilità

**21 ottobre 2026 · Europe/Rome.** Attuazione della [diagnosi della rc.25](game-direct-pace-stall-diagnosis.md). Evidenze: [campagna e script](evidence/v09-driving-school-2026-10-20/). Stato di installazione nella ricevuta finale, separato dalle prove numeriche.

## 1. Il problema e l'intervento

La rete precedente imitava una guida prudente e prevalentemente centrale; un comando diretto non garantiva di aver appreso accelerazione, frenata e concatenazione delle curve. L'esplorazione longitudinale cambiava troppo rapidamente; il candidato poteva peggiorare e il display non rendeva evidente il campione conservato. Nei salvataggi reali erano presenti anche due errori del writer `/psm_...`.

La nuova preparazione confronta alternative geometriche di traiettoria e profili di velocità con curvatura, grip, potenza e frenata; usa la fisica del simulatore. Sono alternative finite, non una soluzione globalmente ottima. La raccolta supervisionata include gli stati visitati dalla rete e le correzioni del docente: principio dell'[aggregazione dei dati di imitazione](https://proceedings.mlr.press/v15/ross11a.html). Questo lavoro prepara i pesi, non aumenta artificialmente il punteggio RL.

La guida usa due esperti neurali da 64 unità e un selettore sigmoidale neurale sui 90 ingressi: **11.999 parametri dell'attore, tutti allenabili**. Un esperto proviene dalla nuova scuola in solo; quello di traffico conserva la base neurale preparata della rc.25, distinta nei metadati. Inizialmente il selettore favorisce la nuova guida in solo e quella prudente quando rileva avversari. Non chiama il controllore docente e non impone un bersaglio di velocità: sterzo e pedale rimangono uscite della rete. I tentativi con un unico esperto più veloce fallivano alcune gare e sono conservati come varianti respinte.

Per le future preparazioni, le colonne dei sensori mai osservate e sempre nulle vengono neutralizzate: non conservano pesi casuali che reagiscono arbitrariamente al secondo/terzo avversario. La correzione da sola non bastava a qualificare le gare; non è presentata come spiegazione unica.

## 2. Allenamento dei quattro piloti

| Pilota | Metodo | Differenza |
| --- | --- | --- |
| Crono | PPO | Aggiornamenti su rollout, probabilità delle azioni coerenti con l'esplorazione. |
| Memoria | SAC | Replay, critic e ricerca stocastica del pedale. |
| Linea | TD3 | Replay, doppio critic e attore deterministico con rumore durante la raccolta. |
| Tattico | TD3 con curriculum di traffico | Base di traffico distinta, sorpasso/curva/difesa e scenari con più vetture. |
| Maestro | Controllore esplicito | Riferimento e avversario; non si presenta come rete che apprende. |

Le lezioni sono **Accelerazione, Frenata, Traiettoria, Aderenza**, intercalate con giri completi. Misurano gas sostenuto, frenata e riduzione di velocità in curva, variazione laterale e sicurezza su parametri fisici variati. I segmenti non vengono dichiarati giri completi. Per promuovere un campione occorrono conservazione delle abilità e miglioramento della mediana del giro superiore allo 0,1%, insieme ai gate di sicurezza e traffico pertinenti. Prima della promozione sull’ovale si confrontano inoltre due gare congelate da tre giri e cinque auto, con il candidato in mezzo e in fondo alla griglia: nessun ritiro e nessun aumento dei limiti pista rispetto al campione; i contatti sono tracciati separatamente. Partono solo dopo i gate economici; non aggiungono esperienze al replay.

Lo sterzo ha esplorazione piccola e indipendente; il pedale aggiunge un impulso latente esogeno tenuto per **1,2 s**, con blocchi periodicamente neutri. PPO salva il campione gaussiano precedente alla trasformazione e la sua probabilità condizionata allo stesso impulso: il rapporto di probabilità usa la stessa trasformazione, coerentemente con il [criterio PPO](https://spinningup.openai.com/en/latest/algorithms/ppo.html). Test di probabilità e ripresa esatta coprono questo contratto.

Il premio resta basato sul progresso valido e sul tempo: nessun bonus incondizionato al gas. In SAC/TD3, avvio dei critic e breve ancoraggio alla preparazione restano separati. Tutti i metodi, incluso PPO, ripartono dall'attore campione dopo regressione di sicurezza o due verifiche senza guadagno, mantenendo le esperienze e ripristinando l'ottimizzatore dell'attore. In PPO vengono scartati i campioni pendenti del vecchio attore.

## 3. Lettura della schermata

Guida mostra **Candidato**. Nel pannello Rete sono separati campione, ultimo candidato verificato, aggiornamenti, decisioni ed esercizio corrente. Un tentativo più lento non sostituisce automaticamente il migliore. Giro lanciato nella preview e verifica ripetuta da fermo rimangono misure diverse. La palette e la geometria del tema sono conservate.

## 4. Salvataggio e migrazione

Il writer usa un file mmap privato e un processo persistente con ACK dopo il salvataggio durevole. Non usa oggetti POSIX nominati `/psm_*` o semafori del pool. La documentazione del [resource tracker Python](https://docs.python.org/3/library/multiprocessing.shared_memory.html) descrive possibili rimozioni anticipate tra processi; l'origine precisa degli errori osservati non è dimostrata. Non sono state cambiate impostazioni globali di logind/RemoveIPC.

La ricetta passa da `direct-driving-2` a `direct-driving-3`. I quattro piloti ricevono nuove basi preparate e nuovi critic, ottimizzatori e replay; i vecchi checkpoint restano artefatti immutabili archiviati. Identità, storico e contatori di tempo/passi totali rimangono. Le vecchie qualifiche del contesto vengono archiviate una sola volta: la nuova policy deve qualificarsi. Gli altri percorsi migrano quando vengono aperti, senza attribuire loro una nuova qualifica. Nessun campione RL ottenuto nei benchmark viene importato nei piloti reali.

## 5. Verifiche e limiti

La prima campagna della nuova scuola superava i giri e le lezioni, ma i campioni insieme in gara concludevano **20/25** prove. Linea, più veloce in solo, falliva in mezzo e in fondo alla griglia; il difetto è stato riprodotto in due scenari separati. Quella campagna è [conservata e respinta](evidence/v09-driving-school-2026-10-20/before-grid-retention/final-summary.json). La ricetta finale aggiunge la conservazione in gara ai controlli di promozione di tutti i metodi e viene confrontata nuovamente con gli stessi budget. Durante questa verifica la GUI espone il conteggio delle gare, senza restare bloccata sul numero già completo delle lezioni.


- Preparazione scelta: **43/43** esercizi, giri e casi di traffico validi su semi separati; cinque griglie da tre giri, **25/25 arrivi**. Ci sono contatti e due limiti pista in uno scenario: arrivo non significa gara pulita.
- Quattro checkpoint reali su copie private: contatori conservati, nuova epoca e ripresa numerica esatta dopo checkpoint.
- Confronti a budget fissato: cinque semi per metodo, inclusi i semi prodotto 2/3/4/5. Risultati completi, conservazione delle abilità, gare dei campioni e repliche sul codice finale nel riepilogo scientifico.
- Prove PC, ARM, tre temi EGLFS 960×640, Qualifica GUI, gara con cinque auto e ricevuta di installazione sono distinte dal confronto numerico.

Il vantaggio della nuova preparazione non è un guadagno RL. Non si promettono miglioramenti a ogni giro, convergenza uniforme, guida al limite o difesa tattica ottimale. La base iniziale nel traffico è deliberatamente più prudente di quella in solo. Restano da qualificare uso prolungato di ore, altre piste/auto/fondi, duelli più vari e FPS ottici. GPU resta al rendering; CPU gestisce fisica e queste piccole reti, senza nuova dichiarazione di accelerazione NPU.

## 6. Risultati finali a budget fissato

| Metodo | Passi fisici raccolti per seme | Mediana iniziale → campione | Semi migliorati |
| --- | ---: | ---: | ---: |
| residual_ppo | 98,304 | 24.417 → 23.883 s | 5/5 |
| residual_sac | 98,304 | 24.417 → 24.233 s | 5/5 |
| residual_td3 | 98,304 | 24.417 → 24.317 s | 3/5 |
| residual_tactic | 131,072 | 24.417 → 24.417 s | 2/5 |

Cinque giri finali per seme: **100/100 validi**; lezioni indipendenti dei campioni: **80/80 superate**. Tattico: **45/45** casi di traffico validi. Tempi da fermo, non PB lanciati. I quattro semi prodotto sono stati ripetuti sul codice finale con attore, campione, statistiche, valutazioni e risultati esatti.

I cinque confronti fra campioni allenati, tre giri e Tattico nelle cinque posizioni di griglia, hanno prodotto 25/25 arrivi. Contatti e limiti restano riportati separatamente nel [riepilogo](evidence/v09-driving-school-2026-10-20/final-summary.json); questa misura non certifica sorpassi o gare senza contatti.

## 7. Installazione verificata

**0.9.0-rc.26 installata**, 636 hash conformi, 57 test PC e 28 ARM passati. Base/Functional/Apple Calm su EGLFS 960×640 senza warning QML; quattro learner, salvataggi e cinque auto visibili. Il delta finale della conservazione gara, dei suoi test e della migrazione dei profili Infinito/Sorpassi ha un supplemento ARM separato, inclusa la reale policy Linea veloce respinta: QML, preview e aggiornamenti neurali sono invariati rispetto al walkthrough. Apple esegue Qualifica GUI e Gara completa da tre giri. I test PC producono anche un ResourceWarning di teardown per tre oggetti Qt non raccolti: non sono warning QML del runtime né prova di assenza di leak.

Cinque identità conservate, Maestro invariato; i quattro piloti neurali mantengono passi, tempo complessivo e storico e iniziano la nuova epoca con la scuola. Vecchi artefatti integri e backup esterno completo; nuove qualifiche necessarie. Preferenze e Apple Calm 1.6.3 conservati, heartbeat GUI fresco con PID corrente, NRestarts=0, nessun reboot OS. Nessun allenamento di produzione lanciato automaticamente.

[Ricevuta di installazione](evidence/v09-driving-school-2026-10-20/board/final-receipt.json) · [repliche](evidence/v09-driving-school-2026-10-20/final-source-reproduction.json) · [delta del sorgente](evidence/v09-driving-school-2026-10-20/source-delta.json). I tempi `frameSwapped` raccolti sono solo campioni software; non qualificano 30 FPS ottici fissi.
