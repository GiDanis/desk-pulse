# Accelerare l'apprendimento dei piloti: ricerca e proposta

**15 ottobre 2026 · studio, nessuna modifica al runtime o alla scheda.**

## Risposta e termini del confronto

Esistono tecniche che in alcuni compiti riducono molto i dati necessari. Non emerge una garanzia di accelerazione esponenziale per il nostro simulatore. Servono due misure separate: transizioni necessarie per raggiungere una competenza definita e secondi reali necessari per raggiungerla. Più aggiornamenti per transizione possono migliorare la prima misura e peggiorare la seconda.

La priorità proposta deriva dalla lettura delle fonti sotto e dal confronto con il codice corrente; non è un benchmark sulla nostra scheda.

## Cosa esiste già nel progetto

Verificato nei sorgenti correnti:

- `game_learning.py`, `Imitation.learn_step`: etichette del maestro negli stati visitati dall'allievo, aggregazione limitata degli esempi; approccio ispirato a DAgger, non riproduzione integrale dell'algoritmo del paper.
- `game_numeric.py`, `ExampleBuffer`: campionamento stratificato per manovra e riserva per frenate. Non è Prioritized Experience Replay basato sull'errore TD.
- `game_evo_plan.py`: esercizi progressivi, casi comuni ai candidati e ripasso. La sequenza di stadi è prestabilita; non è Prioritized Level Replay.
- `game_hybrid.py`: Clone→PPO, passaggio dopo verifica congelata. Durante il rinforzo il comando arriva dall'actor: non è la somma fra controller base e correzione residuale.
- `game_learning.py`, `PPO.updates`: rollout recenti, più epoche e successivo svuotamento. Non è un archivio off-policy da cui estrarre indefinitamente transizioni storiche.

## 1. Rendere più utile il maestro: prima verifica

DAgger affronta il fatto che gli errori dell'allievo lo portano in stati diversi da quelli delle sole dimostrazioni esperte. Il maestro etichetta anche gli stati prodotti dall'allievo. [Ross et al., AISTATS 2011](https://proceedings.mlr.press/v15/ross11a.html).

**Applicazione proposta:** misurare copertura ed errore degli esempi su frenata prima della curva, ingresso, percorrenza, uscita e recupero; introdurre partenze variate e ripetibili. Verificare che gli ingressi della rete permettano di dedurre il comportamento richiesto dal maestro: informazione geometrica privilegiata non osservabile dall'allievo può creare target incoerenti. Questa è un'ipotesi da controllare, non un difetto già dimostrato.

Il replay è già stratificato: aumentare soltanto la sua capacità non garantisce esempi migliori. Un insegnante prudente può insegnare affidabilità, ma il superamento del suo passo richiede un obiettivo di ottimizzazione successivo.

## 2. Pilota residuale: il nuovo esperimento più diretto

Il comando combina una base competente con una correzione appresa. In RLPP la base è Pure Pursuit; gli autori riportano tempi sul giro fino al 6,37% inferiori rispetto ai controller di riferimento sulla piattaforma F1TENTH. Il valore riguarda il tempo sul giro nel loro esperimento: non è un fattore di accelerazione del training né una previsione per noi. [Ghignone et al., 2025](https://arxiv.org/abs/2501.17311), [codice degli autori](https://github.com/forzaeth/rlpp).

L'idea generale di decomporre controllo noto e parte appresa è descritta anche da [Johannink et al.](https://arxiv.org/abs/1812.03201) e da [Silver et al.](https://arxiv.org/abs/1812.06298).

**Proposta per noi:** nuovo metodo esplicito, con riferimento congelato e hash persistente; correzioni inizialmente limitate per sperimentare punto di frenata, gas e traiettoria. Confrontare riferimento geometrico e, separatamente, una base neurale già verificata. Una base geometrica resta parte della guida anche in Qualifica/Gara: la rete non deve essere presentata come autonoma. Con una base neurale, congelarla e conservarla insieme alla rete residuale.

**Rischi da misurare:** limiti troppo stretti impediscono sorpassi; correzioni ampie possono perdere la guida iniziale. La capacità della base da sola non equivale a capacità acquisita dalla rete residuale. Occorre confrontare base, combinazione e contributo appreso sullo stesso insieme di prove.

## 3. SAC e dati precedenti: riutilizzare le esperienze

SAC è un metodo off-policy per azioni continue che può riutilizzare transizioni storiche. Il lavoro originale documenta risultati di efficienza dei dati in controllo continuo; non stabilisce superiorità universale su PPO. [Haarnoja et al.](https://arxiv.org/abs/1812.05905).

RLPD studia come combinare dati precedenti e nuovi dati online. Gli autori riportano un miglioramento fino a 2,5× rispetto ai confronti del proprio lavoro: non va tradotto in «impara 2,5 volte più in fretta sul nostro ovale». [Ball et al., ICML 2023](https://arxiv.org/abs/2302.02948), [implementazione degli autori](https://github.com/ikostrikov/rlpd).

**Proposta:** prima una baseline SAC piccola e riproducibile; poi variante con traiettorie di maestro e del pilota, contesto fisico/versioni espliciti, campionamento misto e budget dichiarato. Salvare osservazioni, azioni realmente eseguite, reward, osservazioni successive e distinzione fra terminazione e troncamento. Le sole coppie osservazione/azione del Clone non sono un dataset completo di transizioni RL.

Un successivo esperimento può confrontare replay uniforme e prioritario. PER ripete transizioni informative più spesso, con correzioni del bias; non significa allenare soltanto sugli incidenti. [Schaul et al.](https://arxiv.org/abs/1511.05952).

**Costi:** critic aggiuntivi, reti target, ottimizzatori, buffer e aggiornamenti. RAM disponibile utile per i dati; costo CPU da misurare. Non inserire replay storico arbitrario nell'attuale PPO come se fosse SAC. Non importare automaticamente la complessità degli ensemble RLPD sulla scheda.

## 4. Curriculum adattivo: utile anche ai metodi puri

Prioritized Level Replay assegna più raccolta a contesti con potenziale di apprendimento. La letteratura comprende anche curriculum di stati iniziali progressivamente più difficili. [Jiang et al., ICML 2021](https://proceedings.mlr.press/v139/jiang21b.html), [Florensa et al., CoRL 2017](https://arxiv.org/abs/1707.05300).

**Adattamento proposto, da confrontare con il curriculum esistente:** banca di ingressi curva e frenate parametrizzati, frequenze guidate dai risultati recenti, mantenendo una quota di ripasso e varietà. Ripartire talvolta prima della curva che fallisce evita di spendere ogni prova sul medesimo rettilineo. Non scegliere sempre il caso più difficile: un fallimento inevitabile può non dare apprendimento utile.

Per Evo/NEAT, nello stesso confronto tutti i candidati ricevono gli stessi scenari e budget. Separare selezione, adattamento del curriculum e verifica finale; nessun seed della verifica usato per scegliere gli esercizi. Conservare prove complete dalla partenza per rilevare regressioni introdotte dai reset locali.

## 5. World model: possibilità successiva

DreamerV3 impara un modello dell'ambiente e aggiorna il comportamento tramite traiettorie immaginate; TD-MPC2 usa un modello latente con pianificazione. Sono risultati importanti su molti compiti. [Hafner et al., Nature 2025](https://www.nature.com/articles/s41586-025-08744-2), [Hansen et al., ICLR 2024](https://arxiv.org/abs/2310.16828).

**Valutazione per il progetto:** abbiamo già la fisica simulata e ingressi numerici piccoli; apprenderne un surrogato aggiunge errore e costo. Prima misurare quale parte del ciclo costa e se una previsione appresa la riduce davvero. Gli esperimenti del paper Dreamer citato usano una GPU A100 per agente: non sono prova di fattibilità di quel training sulla NPU integrata. Una versione più piccola è un altro esperimento, non esclusa a priori.

NPU/GPU possono accelerare operazioni compatibili; non riducono da sole la quantità di esperienza richiesta. Nessun nuovo backend è qualificato da questa ricerca.

## Proposta di sequenza e accettazione

1. Audit copertura maestro e osservabilità; confronto del curriculum attuale con una variante adattiva, un cambiamento per volta.
2. Nuovo pilota residuale, mantenendo Clone→PPO e metodi puri come confronti separati.
3. Baseline SAC; poi dati di dimostrazione e, solo se utile, replay prioritario.
4. World model dopo evidenza di un beneficio potenziale sul costo totale.

Ogni confronto: almeno cinque seed di training, configurazione fisica e budget identici, banca di verifica separata; pubblicare tutti i seed e gli eventuali mancati apprendimenti. Per il primo confronto si può preregistrare il raggiungimento di 18/20 partenze, 18/20 giri e 4/5 serie di cinque giri puliti, poi misurare il passo a parità di affidabilità. Il set di selezione e quello finale devono usare scenari diversi.

Registrare separatamente transizioni nuove, aggiornamenti, dimostrazioni, chiamate al maestro, costo delle verifiche, tempo reale e simulato. Confrontare tempo alla soglia, successo, giri consecutivi, incidenti, tempo sul giro, trasferimento e frame pacing. Un eventuale obiettivo di riduzione 2× o 5× è una soglia sperimentale da verificare; i fattori non si sommano né si moltiplicano senza prove.

Non è necessario resettare la rosa personale per questa ricerca. Ogni nuovo pilota assistito o inizializzato da dimostrazioni deve avere una ricetta distinta: un Evo inizializzato dal Clone non sarebbe più un confronto di evoluzione da zero.
