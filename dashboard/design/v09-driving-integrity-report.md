# Gioco · contratto di guida e integrità dei giri · rc.17

**15 ottobre 2026 · 0.9.0-rc.17 installata e verificata in EGLFS · manifest 602 file.**

Attuazione dello [studio su modalità, giri e metodi](game-methods-lap-integrity-analysis.md). Evidenze in [v09-driving-integrity-2026-10-15](evidence/v09-driving-integrity-2026-10-15/). I dati dei sei piloti originali sono esclusi dagli esperimenti.

## 1. Guida coerente fra modalità

`driving-inputs-1` rende esplicito nel checkpoint e nel modello il significato del contesto della rete. Le reti nuove usano un ingresso costante, indipendente dalla fase interna del curriculum. Quelle storiche conservano il valore ricostruito dalla fase o dalla copertura salvata: per il candidato Evo attuale è **2/9**, per la sua vecchia base Controllo è **1/9**. Anche gli archivi dei singoli esercizi conservano il proprio contesto.

L’adattatore cambia l’osservazione prima dell’inferenza. Non modifica sterzo, gas, freno, fisica o pesi. Vale per reti dense e NEAT, valutazioni, avversari congelati, preview, Qualifica e Gara. I tre ingressi temporali sono calcolati rispetto al progresso sicuro e al suo fronte massimo, anche nei mondi diretti di gara. Il credito non si rigenera arretrando o uscendo volontariamente.

La migrazione avviene al prossimo **Start**, a un confine dichiarato di raccolta. Conserva pesi, topologia, RNG e storia; il solo adattatore conserva anche i momenti dell’ottimizzatore. I rollout con il vecchio significato sono scartati. Il cambio separato di reward dei metodi non Evo ricrea il critic, come previsto per ritorni non confrontabili. I nuovi hash richiedono una nuova Qualifica: nessun certificato viene copiato da un modello a un altro. Gli artefatti storici restano immutabili.

**Precisazione dello studio iniziale:** `World.reset` lasciava il valore 1, ma il ciclo effettivo di `game_worker` impostava già Controllo = 1/9 in Qualifica/Gara. Il precedente probe con valore 1 era un World diagnostico, non l’intero percorso Worker. Il difetto concreto Passo 2/9 → Controllo 1/9 resta confermato. Nella rc.17 è stata provata anche la Qualifica attraverso il Worker reale.

### Risultato sul candidato Evo esistente

[Prova congelata](evidence/v09-driving-integrity-2026-10-15/current-evo.json), nessun aggiornamento dei pesi:

| Prova | Esito |
| --- | --- |
| World di Qualifica | 4 giri puliti, zero uscite; totale 83,53 s |
| Migliore giro lanciato | 20,096 s |
| Guida continua | 130 s, 6 giri puliti, zero uscite/ritiri |
| Main/Worker reale sul PC, Apple Calm | Qualifica misurata 20,205 s; certificato soltanto del nuovo hash |

Questa è una verifica del candidato e del circuito provati; non qualifica automaticamente altri seed, piste, vetture o traffico.

## 2. Settori, fuori pista e traguardo

`ordered-laps-2` separa attraversamenti ordinati, validità della tornata, giri fisici e giri puliti. Una porta attraversata sull’erba invalida il giro e permette il riarmo del successivo. Una porta mancante resta invalidante; inversioni e oscillazioni sulla linea non producono settori aggiuntivi. Nei circuiti poligonali resta la tolleranza fisica di 2 m fra proiezione e porta: una traiettoria larga lecita non viene scartata perché anticipa o ritarda il vertice della polilinea.

Le partenze fuori dall’origine allineano le porte alla geometria reale. Un primo giro parziale non diventa un giro lanciato valido. I contatori sono persistenti e vengono trasportati anche nei batch/collector. Una tornata sporca non dà premio di giro pulito o certificato. Per completare il World moderno servono i giri puliti richiesti; nei tentativi finiti un’uscita continua a rendere non valido l’esercizio. Il budget del tentativo a un giro è calcolato per un giro, anziché ereditare quello da tre.

La prova fisica con escursione fra 40 e 100 m, che prima restava a zero settori, ora registra il primo giro invalido e il successivo pulito. Il footer mostra **Giro non valido**, mantenendo lo spazio della pista.

## 3. Giro infinito e memoria personale

Per Evo/NEAT la fine di una finestra di 60 s non azzera più un esemplare sopravvissuto se la sua rete eseguibile è rimasta identica dopo la riproduzione. Il confronto usa hash dei pesi o della topologia eseguibile. Figli mutati e ritiri iniziano un tentativo nuovo; identità della vita, posa, tempo e porte dei sopravvissuti continuano. La selezione usa il reward della finestra, con addebito del tempo residuo ai ritiri; non somma fitness cumulative delle vite lunghe. Le partenze lanciate dei sopravvissuti e quelle da fermo dei nuovi figli sono dichiarate: la verifica indipendente resta necessaria per confrontare la capacità di partire da zero.

PPO e Clone mantengono il loro aggiornamento online e il bootstrap delle finestre. La preview può adottare il candidato nuovo al confine di finestra senza azzerare la fisica; hash e motivo del cambio sono espliciti nella traccia. Non si presenta questo cambio come endurance della medesima rete congelata.

Quando esistono un vecchio ramo Infinito e una base Impara più recente, Start avvia un confronto interrompibile: **due partenze e due prove fino a 120 s per versione**, stessi seed. Il ramo locale viene sostituito soltanto se il nuovo candidato parte in entrambi i casi, completa almeno due giri puliti complessivi e supera la qualità locale. Nessuna media dei pesi. Il checkpoint del vecchio ramo e l’origine del nuovo restano referenziati; il confronto non conta come passi di apprendimento.

[Confronto sul vecchio ramo Evo](evidence/v09-driving-integrity-2026-10-15/branch-comparison.json): entrambi partono 2/2; locale zero giri puliti, candidato recente cinque complessivi. Viene adottato il candidato recente nella copia; pausa/ripresa del confronto verificata. Uno dei due casi recenti si ritira dopo circa 29 s: è un miglioramento relativo, **non una certificazione di affidabilità in tutti gli scenari**. I dati originali non sono stati sostituiti dall’esperimento.

## 4. Progressione e metodi

La progressione comune comprende partenze da 1/3/8/20 m, rettilineo, archi lenti e veloci, ingresso curva e giro pulito. Evo/NEAT confrontano la popolazione sulle stesse suite; PPO/Clone mescolano scenari principali e ripasso mantenendo la propria cadenza di aggiornamento. Le promozioni richiedono due esami congelati superati; i semi di esame sono distinti da quelli di raccolta.

Dalle fasi avanzate il ripasso include entrambi gli archi a velocità diverse; dopo gli esercizi include anche il recupero. Non si azzera la stagnazione fra i casi della stessa suite. La pressione sul tempo aumenta dopo una verifica affidabile, non al semplice passare delle generazioni. Quando un’elite Evo risolve entrambi gli scenari principali e conserva abilità, le mutazioni ordinarie rimangono locali; restano discendenti esplorativi.

| Metodo | Scelta nella rc.17 |
| --- | --- |
| Evo | Pesi utili conservati, suite estesa, continuità degli esemplari invariati, mutazioni locali dopo affidabilità. |
| NEAT | Nuova progressione; qualità numerica basata su successi/ripasso/reward, non ranghi ordinali costanti. Specie e storia preservate durante il ripasso. Varianti neonate del pedale piccole e simmetriche. I sigma inferiori non sono stati selezionati senza un vantaggio misurato. |
| PPO | Baseline fisica: orizzonte 40 s, GAE λ0,99, LR0,0003, rollout256 ×32, quattro epoche, batch64, clip0,2 e KL0,03. Confronti separati su LR, GAE e batch. |
| PPO-Smooth | Stesso PPO con costo dei comandi; confronto fra actor storico e partenza nuova. Nessun azzeramento automatico dei dati originali sulla sola prova breve. |
| Clone | Replay da 8.192 esempi, quattro riserve da 2.048 per frenata/curva/rettilineo/rientro, batch bilanciati ed errore per manovra. Maestro dichiarato; azioni della rete non corrette dall’esperto. |

Il migliore verificato viene archiviato separatamente dal candidato esplorativo. Qualifica lo preferisce quando disponibile, altrimenti usa il candidato salvato; il menu spiega la scelta. Il dossier distingue esercizi, aggiornamenti/generazioni, protocollo degli ingressi e provenienza del trasferimento. Parametri del paradigma restano in consultazione.

### Confronti di apprendimento

[Script di screening](evidence/v09-driving-integrity-2026-10-15/screen_methods.py), [conferma](evidence/v09-driving-integrity-2026-10-15/confirm_methods.py). Ogni run usa 250.000 transizioni di raccolta; il costo delle valutazioni è registrato separatamente. Processi privati, nessun addestramento o modello sperimentale installato. I tempi PC con lavori concorrenti non sono throughput della scheda.

[Risultati aggregati](evidence/v09-driving-integrity-2026-10-15/learning-summary.json): **48 run, 12 milioni di transizioni**. Cinque semi per ciascuna baseline; tre per ciascuna ablation. Le colonne seguenti sono prove congelate su due seed separati per ogni run, quindi dieci prove per compito. La Partenza è da 20 m; l’arco lento è da 20 m; l’ingresso curva è da 60 m. L’esame finale non promuove automaticamente il curriculum.

| Metodo / inizializzazione | Partenza | Arco lento | Ingresso curva | Giro ovale |
| --- | ---: | ---: | ---: | ---: |
| Evo nuovo | 10/10 | 5/10 | 3/10 | 0/10 |
| NEAT nuovo, sigma conservati | 10/10 | 10/10 | 5/10 | 0/10 |
| PPO nuovo | 10/10 | 8/10 | 3/10 | 0/10 |
| Smooth nuovo | 10/10 | 9/10 | 7/10 | 0/10 |
| Smooth da actor storico | 8/10 | 8/10 | 5/10 | 0/10 |
| Clone nuovo, maestro dichiarato | 10/10 | 10/10 | 10/10 | 10/10 |

Il confronto warm di Smooth riusa **un actor storico** con cinque nuovi seed di apprendimento, non cinque storie di pretraining indipendenti. Le copie nuove progrediscono meglio nei primi esercizi, ma nessuna delle due inizializzazioni completa il giro nel budget provato: si conserva il dato originale e il reset rimane esplicito. Il candidato Evo già esperto è un’altra condizione, con circa 13,9 milioni di passi: i suoi risultati congelati non vengono confrontati come se avesse avuto solo 250 mila passi.

NEAT è stato confrontato con sigma pesi 0,30→0,08, poi bias 0,30→0,05 e mutazione 0,15→0,06, variando una voce per passaggio. I valori più piccoli non migliorano la batteria tenuta separata; resta il preset precedente con la nuova progressione. PPO è stato confrontato con LR0,0001, GAE0,97 e batch128 separatamente: alcuni seed avanzano di una fase in più, ma nessuna variante dimostra un vantaggio sul giro completo. La baseline resta quella dichiarata; non si presenta questo screening come ottimo globale. Clone riceve informazione dall’esperto, quindi il suo vantaggio non è una prova di superiorità algoritmica a parità di informazione.

## 5. Diagnostica della presentazione

La scena mantiene la presentazione a 30 Hz e la fisica a 60 Hz. Una traccia QML locale, limitata a 120 campioni, associa pubblicazione, presentazione, tempo simulato, coordinate fisiche/interpolate, pilota, policy, generazione/scenario e motivo del reset/cambio rete. Non scrive su disco a ogni frame e non pubblica nuovi segnali per campione. Serve a separare lentezza simulata da discontinuità di presentazione.

CPU: fisica, policy, aggiornamenti e batch; GPU: rendering Qt Quick; NPU: nessun nuovo carico selezionato senza un vantaggio end-to-end. L’export ONNX ingloba il contesto costante nel bias della rete densa, preservando la semantica della policy: 512 vettori, errore massimo **5,71×10⁻⁷**. È parità ONNX/CPU, non prova di esecuzione NPU.

## 6. Verifiche e consegna

- PC: 124 controlli della regressione, più verifiche mirate sul contratto finale e sulle porte; esame reale dei quattro circuiti e delle fasi progressive.
- Scheda: 25 controlli iniziali, 15 gate finali su fisica/continuità e due controlli mirati della migrazione; tutti passati. Sei walkthrough EGLFS sui tre temi, più il controllo finale di associazione della policy nella traccia.
- Main PC Apple Calm: 960×640, scala 1,1 per le impostazioni/dossier, popolazione da 32; nessun warning QML. La Qualifica neurale usa il Worker effettivo.
- Export ONNX: parità CPU verificata; nessuna attribuzione NPU.

[Ricevuta finale](evidence/v09-driving-integrity-2026-10-15/final-receipt.json): **602 hash conformi, sei piloti, 2.600 artefatti e tutte le tabelle originali conservati**, preferenze invariate, Base attivo, GUI pronta, servizio attivo e `NRestarts=0`. Nessun nuovo reboot OS. Backup e percorso di rollback sono indicati nella ricevuta. La migrazione dei percorsi si attiva al prossimo Start; non è stato avviato un allenamento originale dall’installazione.

La prima misura della Qualifica era contaminata dal test, che rileggeva continuamente dal thread GUI l’intero record Evo con gli archivi dei pesi. Questo percorso non appartiene al rendering normale. Il test finale aspetta il certificato dalla cache aggiornata del servizio; l’evidenza iniziale viene conservata come diagnostica del test, senza etichettarla come gate prestazionale superato. Il controllo del menu è stato aggiornato da «Bilanciato 1» a «Progressivo», coerentemente con il nuovo curriculum. I tre walkthrough di popolazione già passati sono riusati perché il prodotto non cambia con queste riparazioni del test.

Timing della qualifica EGLFS corretta: clock circa **29,7 Hz**, frame p95 **38,6 ms**, p99 **49,6 ms**, massimo **91,2 ms** nel controllo finale della traccia. Sono misure Qt, non FPS ottici né una garanzia di 30 fissi per ogni carico. La popolazione resta di 32 e il suo ritmo simulato è mostrato separatamente. I budget RAM/CPU sono diagnostici, non soglie artificiali di consegna.

## 7. Gate ancora aperti

Convergenza e generalizzazione di tutti i paradigmi su circuito completo, trasferimento fra vetture/fondi diversi, competenza nei sorpassi, carichi prolungati e FPS ottici richiedono prove ulteriori. I confronti brevi non diventano qualifiche da gara. In particolare, preservare Evo non significa che tutte le mutazioni debbano arrivare al traguardo, né che sei giri del candidato su una partenza provino robustezza universale.
