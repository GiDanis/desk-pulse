# Piloti — conservare la guida mentre la rete migliora

> **Priorità successiva dell'utente:** chiusura della fase funzionale Auto e passaggio al nuovo modulo. Questa ricerca viene conservata come lavoro futuro; nessuna nuova rete è promossa e i gate qui descritti restano necessari per un'eventuale ripresa. [Decisione e consegna corrente](v094-game-functional-closure-report.md).

**25 ottobre 2026 · Europe/Rome · implementazione e sviluppo; nuova release non qualificata.**

Seguito autorizzato del [piano P0–P9](game-reference-integration-plan.md) e del [report di integrazione](v094-game-reference-implementation-report.md). [Risultati, contratti, log e ricevute](evidence/v094-game-learning-retention-2026-10-25/README.md).

## 1. Stato reale della ripresa

Il prerequisito quantitativo di sviluppo ora passa per **cinque preparazioni indipendenti**. Non sono cinque identità della rosa né cinque metodi qualificati. È stata corretta la preparazione 4102, mantenendo visibili gli esiti negativi delle altre varianti. Le selezioni avvengono sullo sviluppo; non dimostrano ancora una ricetta comune qualificata.

Otto continuazioni RL da **32.768 decisioni** sono concluse: tre con replay esperto, quattro con contesto aggiuntivo e una SAC con maggiore conservazione dello sterzo. L'ultima è osservata a otto punti dello stesso allenamento: non otto semi indipendenti. Ogni confronto usa l'intera banca di sviluppo, 27 finestre pianificate da 180 s; gli episodi interrotti prima restano fallimenti incompleti.

È stato osservato un candidato SAC che migliora passo e passaggi conservando la sicurezza nella banca, ma **non dimezza l'attesa**. Non sono state ridotte le soglie. P6/P7 rimangono aperti; finale mai consultato, nuovi pesi non installati, nessun reset personale.

## 2. Quinta preparazione: correzione propria, poi conservazione

La 4102 perdeva una delle tre manovre in curva. Sono stati raccolti 21 nuovi episodi di allenamento del proprio attore, sette famiglie, fino a 120 s, con interventi offline del docente e interruzione al primo evento non sicuro. Semi nuovi, esclusi gli intervalli sviluppo/finale. Le interruzioni non diventano finestre valide.

Correzione dei due controlli: 8.000 aggiornamenti per canale, LR 0,00001, condizioni prodotte dalla propria memoria neurale. Percezione, memoria della manovra e normalizzazione congelate. Nessuna azione o intenzione del docente durante l'inferenza.

| Variante della stessa preparazione | Giro solo mediano | Curva | Difesa | Traffico valido | Contatti ego |
| --- | ---: | ---: | ---: | ---: | ---: |
| Correzione completa | 23,394 s | 3/3 | 2/3 | 9/9 | 0 |
| Metà della correzione dei controlli | 23,527 s | 3/3 | 3/3 | 8/9 | 22 |
| Tre quarti della correzione dei controlli | **23,456 s** | **3/3** | **3/3** | **9/9** | **0** |

L'interpolazione riguarda coefficienti statici dei due moduli della **stessa** preparazione. Lo script verifica core, normalizzazione e memoria identici; nessuna combinazione fra piloti, selezione per caso o correzione dei comandi in guida. Le due frazioni erano dichiarate prima della loro valutazione.

Ripetizione comune, stessi sorgenti e hash di banca, delle cinque selezioni:

| Preparazione | Giro solo | Traffico valido | Contatti ego nel traffico | Uscite nel traffico | Prerequisito |
| --- | ---: | ---: | ---: | ---: | --- |
| 4101 | 23,492 s | 8/9 | 2 | 0 | Passato |
| 4102 | 23,456 s | 9/9 | 0 | 0 | Passato |
| 4103 | 23,618 s | 7/9 | 17 | 0 | Passato |
| 4104 | 23,461 s | 8/9 | 0 | 1 | Passato |
| 4105 | 23,547 s | 9/9 | 0 | 0 | Passato |

Il prerequisito ammette almeno il 75% in curva/traffico e richiede le competenze semplici complete. **Passarlo non significa zero incidenti in tutti i casi.** Il successivo confronto RL deve conservare la sicurezza per caso; questi risultati non sono una rosa consegnabile. La correzione aggiuntiva della 4102 e le selezioni diverse sono dichiarate: `recipeCommonalityQualified=false`.

## 3. Replay protetto delle dimostrazioni

Implementato un banco separato dalle 32.768 transizioni online, che i nuovi episodi non possono sovrascrivere. Ogni minibatch usa il 25% del banco esperto. Raccolta nella fisica corrente: 21 episodi puliti da 90 s, 16.380 transizioni selezionate con capacità equilibrata per episodio. Sensori/intenti sono codificati dalla memoria causale della base del learner.

Sono conservati **comando applicato, reward, osservazione successiva e terminale fisico**. Il limite temporale di raccolta continua a consentire il bootstrap; non viene confuso con un ritiro. Le azioni del docente non entrano nelle osservazioni. Hash di sorgenti, base e dati impediscono riusi silenziosi incompatibili. Banco, RNG, replay e optimizer partecipano alla ripresa esatta.

È un'opzione di laboratorio esplicita: non un nuovo default e non una riproduzione di DQfD, TD3+BC o RLPD. Una policy esportata con questa ricetta richiede il proprio banco esplicito per un nuovo affinamento; la sua distribuzione nel runtime resta da qualificare.

Nel manifest congelato della prima raccolta, `bots` descrive il numero richiesto. Gli esercizi dedicati hanno un rivale fisico; `traffic` copre realmente 1/2/3 bot. Il collector corrente distingue richiesta e numero effettivo. L'originale non è stato riscritto.

## 4. Contesto del learner: cosa cambia davvero

L'opzione `plastic-context` conserva controlli interamente addestrabili, ricorrenza/normalizzazione congelate e comandi liberi. Il learner riceve 348 valori: 256 rappresentazioni dei controlli della base congelata più i consueti 90 sensori normalizzati e due intenzioni neurali. I controlli addestrabili usano questi ultimi 92 valori; l'esportazione deterministica NumPy conserva gli stessi comandi iniziali.

**Limite del confronto:** in SAC anche la testa che produce la dispersione delle azioni usa i 348 valori. Il confronto non isola quindi il solo critic: cambia anche la rappresentazione disponibile all'esplorazione. La dichiarazione iniziale «solo contesto del critic» era incompleta; questa deviazione è conservata nelle evidenze. Il successivo confronto sterzo 25/1.000 mantiene la medesima architettura.

### Risultati a budget uguale sulla preparazione 4105

Base dopo imitazione: 23,547 s sul giro, 9/9 traffico, zero contatti. LR attore 0,000003; conservazione sterzo 25/pedali 1; esplorazione Gaussian. Una modifica di ricetta per gruppo, non una promessa di causalità fra singoli componenti interni.

| Ricetta | Metodo | Giro solo | Traffico valido | Contatti ego totali |
| --- | --- | ---: | ---: | ---: |
| Replay esperto 25% | SAC | 23,367 s | 5/9 | 5 |
| Replay esperto 25% | TD3 | 22,442 s | 6/9 | 41 |
| Replay esperto 25% | TD3 racecraft | 21,847 s | 5/9 | 17 |
| Contesto 348 | PPO | 23,586 s | 8/9 | 4 |
| Contesto 348 | SAC | 23,628 s | 9/9 | 0 |
| Contesto 348 | TD3 | 24,725 s | 5/9 | 12 |
| Contesto 348 | TD3 racecraft | 23,865 s | 6/9 | 26 |

Il SAC con contesto conserva il traffico ma perde una finestra di difesa, con due uscite. Il solo replay non conserva tutte le manovre. Nessuna delle sette ricette passa congiuntamente i criteri.

## 5. Conservazione dello sterzo e candidati intermedi

Successivo confronto SAC: stessi parametri, contesto e base; solo coefficiente dello sterzo da 25 a 1.000. Budget e otto punti ogni 4.096 decisioni dichiarati prima dell'esecuzione. La cattura avviene a fine aggiornamento; il test verifica che suddividere il training e leggere gli export non cambi la traiettoria degli aggiornamenti.

| Decisioni | Giro solo mediano | Traffico valido | Contatti ego totali | Limiti residui |
| ---: | ---: | ---: | ---: | --- |
| 4.096 | 23,448 s | 9/9 | 0 | Guadagno al passaggio e attesa insufficienti |
| 8.192 | 23,426 s | 9/9 | 0 | Passaggi, attacco tempestivo e attesa |
| 12.288 | 23,432 s | 8/9 | 4 | Sicurezza e attesa |
| 16.384 | 23,378 s | 8/9 | 0 | Un'uscita e attesa |
| 20.480 | 23,496 s | 8/9 | 3 | Sicurezza e attesa |
| **24.576** | **23,488 s** | **9/9** | **0** | **Attesa** |
| 28.672 | 23,470 s | 9/9 | 0 | Attesa |
| 32.768 | 23,333 s | 8/9 | 1 | Sicurezza e attesa |

Il candidato a 24.576 conserva tutte le famiglie, senza nuove uscite/contatti rispetto alla base:

- giro 23,547 → **23,488 s**;
- mediana del primo passaggio sui casi applicabili 10,650 → **9,650 s**;
- attacchi tempestivi **12/13**, circa 92,3%;
- attesa storica 792,95 → **708,95 s**, circa −10,6%, sotto il −50% richiesto.

Questo è un **miglioramento RL osservato su una preparazione**, non cinque preparazioni né finale. I tempi sono mediane definite dal protocollo, non PB assoluti. La media include scenari diversi solo all'interno della stessa banca abbinata.

Il file `bestSafeObserved` conserva l'identità del candidato di sviluppo; `selectedDevelopmentCandidate` rimane nullo secondo tutti i criteri. È conservata la policy portatile privata, non un optimizer esatto a 24.576: non si deve ripartire da quei pesi usando l'optimizer a 32.768. Nessun campione è diventato una versione Gara.

## 6. Misurare avvicinamento e attesa

Il vecchio `queueSeconds` conta vicinanza e allineamento laterale anche quando l'ego sta recuperando velocemente. Rimane intatto per confrontare le evidenze precedenti. Aggiunti `closingApproachSeconds` e `followingWithoutClosingSeconds`, separando la velocità relativa sopra/sotto 0,25 m/s. Con più rivali i due contatori possono riferirsi a rivali diversi e non sono una partizione globale del tempo.

Non si deduce che un passaggio fosse praticabile da questi soli contatori. L'attesa affiancato rimane distinta. Nessun cambiamento ai premi, ai comandi o ai gate correnti. Anche con la nuova lettura, il candidato sicuro non dimezza l'attesa: il problema non sparisce rinominando la statistica.

## 7. Stime del critic e memoria: evidenze e ipotesi

Sonde da snapshot identici, 14 stati di allenamento, cinque valori del pedale, continuazione deterministica per quattro secondi: concordanza di ordinamento circa 70,7% nel primo SAC e 69,1% nel SAC con contesto. Il ritorno finito non è il valore vero del critic a orizzonte lungo/stocastico. Questi numeri **non provano che il contesto abbia corretto le stime**. In alcuni stati del rettilineo il critic preferisce meno gas, mentre la continuazione fisica finita premia più gas.

Un limite strutturale da verificare è visibile nel codice: sia i 92 valori sia le 256 rappresentazioni aggiuntive vedono la storia attraverso due intenzioni proiettate. Non ricevono integralmente il core percettivo da 128 unità e lo stato della manovra da 32. Una perturbazione costruita del core mantiene identico il readout corrente, ma cambia i comandi successivi. È una dimostrazione algebrica di compressione dell'informazione, **non** una coppia di storie fisiche raggiungibili né la causa dimostrata dei fallimenti.

Le fonti consultate sostengono confronti specifici, non un'accelerazione garantita:

- [RLPD, paper degli autori](https://proceedings.mlr.press/v202/ball23a.html) e [codice originale](https://github.com/ikostrikov/rlpd): mescolare dati offline e online richiede scelte coordinate di campionamento, stime di valore e aggiornamenti; aggiungere semplicemente dimostrazioni non ne riproduce il metodo.
- [R2D2, paper originale](https://openreview.net/pdf?id=r1lyTjAqYX): aggiornare reti ricorrenti con replay richiede affrontare deriva delle rappresentazioni e stato ricorrente obsoleto. Congelare il core conserva le nostre semantiche del replay, ma limita cosa può imparare la memoria.
- [Recurrent off-policy baselines, autori](https://arxiv.org/abs/2110.12628): memoria, costo ed esplorazione vanno verificati nel controllo continuo; il nome SAC/TD3 non conferisce automaticamente una memoria addestrabile.

Il seguito P6 richiede distinguere una rappresentazione causale insufficiente da stime di valore inaffidabili, con confronti abbinati e budget dichiarati. Eventuali cambiamenti di memoria/replay o regolarizzazione del critic richiedono nuove prove, non il caricamento dei checkpoint correnti come equivalenti.

## 8. Ottimizzazione del calcolo verificata

`SkillEnv.encode()` eseguiva il forward completo della base e poi ricostruiva gli stessi controlli per ottenere le feature. La variante compatta scartava entrambi i calcoli. Il percorso `encode_only` avanza soltanto la memoria; calcola una volta le rappresentazioni necessarie, oppure nessun controllo nella variante a 92 valori. Il normale forward del pilota rimane equivalente.

Microbenchmark ABBA, 128 osservazioni fisiche, ricorrenza reale, costruzione degli oggetti esclusa:

| Piattaforma / feature | Prima, ms/decisione | Dopo | Riduzione misurata |
| --- | ---: | ---: | ---: |
| PC / 92 | 0,124 | 0,079 | 36,2% |
| PC / 348 | 0,123 | 0,098 | 20,1% |
| Orange Pi / 92 | 0,693 | 0,410 | **40,7%** |
| Orange Pi / 348 | 0,692 | 0,525 | **24,1%** |

Feature, memoria e comandi normali identici nel campione; il test dell'ambiente copre sette combinazioni di architettura/modalità. È il tempo del solo encoder, **non** un guadagno del 41% del sistema, training totale o FPS del pannello. Nessun beneficio attribuito a GPU/NPU.

Prova ARM isolata a priorità ridotta mentre la Dashboard rimane attiva: stesso PID 135058, `NRestarts=0`, manifest di release invariato. Moduli solo nel progetto privato; nessuno stop/riavvio del servizio e nessuna installazione.

## 9. Verifiche concluse e stato ufficiale

- **25 test PC** passati: parità delle azioni, feature e memoria, aggiornamenti/ripresa esatti PPO/SAC/TD3, replay protetto, maschere dei timeout, contatori e rifiuto delle promozioni incomplete.
- Cattura e ripresa CLI reali, 128 → 256 decisioni, file dei candidati conservati.
- Cinque preparazioni e tutte le continuazioni/catture sopra completate; risultati negativi conservati.
- Microbenchmark PC/ARM e salute del servizio verificati. Le prove Main/QML e gare native della ripresa precedente restano quelle dei relativi sorgenti: non sono state ripetute o attribuite a questa variante di training.
- Validatore di attivazione richiamato in sola lettura con i risultati reali: **«Qualifica scientifica incompleta»**.

**P0–P9 non è chiuso.** P5 ha ora cinque selezioni che passano il prerequisito quantitativo di sviluppo; P6 mostra un primo guadagno sicuro su una preparazione, senza il gate completo o una ricetta comune dei quattro metodi. Restano cinque preparazioni della ricetta RL congelata, finale separato, gare dei pesi esatti, qualifica ARM di quei modelli e consegna. Produzione e piloti personali conservati.
