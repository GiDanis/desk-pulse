# Piloti: conservazione delle competenze, 25 ottobre 2026

[Studio e limiti](../../game-learning-retention-study-2026-10-25.md).

- Cinque preparazioni superano il prerequisito di sviluppo; non cinque modelli scientificamente qualificati. Le preparazioni 4101/4103/4104 conservano casi problematici, visibili nei risultati.
- Otto continuazioni RL da 32.768 decisioni: sette confronti di ricetta e una continuazione SAC osservata a otto punti. Gli otto punti non sono otto allenamenti indipendenti.
- Candidato sicuro osservato a 24.576: miglioramento del passo e dei passaggi, soglia sull’attesa non superata. `selectedDevelopmentCandidate` rimane nullo, `bestSafeObserved` è solo sviluppo. Nessun optimizer salvato esattamente a quel punto.
- Venticinque test PC passati, cattura/ripresa CLI passata, microbenchmark encoder PC/ARM con parità esatta. Nessuna installazione, stop del servizio, reset personale o consultazione del finale in questa ripresa.

Le finestre sono pianificate a 180 s: gli insuccessi precoci sono conservati e non diventano finestre complete. Le soglie non sono state ridotte. I modelli/optimizer/replay/dataset binari restano nel laboratorio privato; qui sono pubblicati hash, ricette, risultati e ricevute, non una rosa installabile.

## Limiti e prove negative

Il primo test del nuovo contatore campionava età zero; il primo test di parità confrontava ingressi float64 con quelli float32 dell’ambiente. I log negativi sono conservati, poi i test sono stati corretti mantenendo uguaglianza esatta. Primo setup ARM interrotto prima del benchmark: il modulo temporale del prototipo non è installato nel runtime rc.2; la misura riuscita usa il progetto privato precedente come riferimento.

Il confronto a 348 valori mantiene invariata la media dei comandi su 92 valori. In SAC la testa della dispersione usa anch’essa il contesto a 348: non è una prova che isola il solo critic. Il confronto successivo fra ancoraggio 25 e 1.000 mantiene questa architettura invariata.

Nel manifest del primo banco esperto, `bots` indica il numero richiesto; gli esercizi dedicati creano un solo rivale fisico. La famiglia `traffic` copre effettivamente uno/due/tre bot. Il collector corrente distingue `requestedBots` e bot effettivi. Il manifest originale congelato è conservato senza riscriverlo.

`encoding/` misura esclusivamente il calcolo dell’encoder, senza costruzione degli oggetti: non è una misura del training totale o degli FPS. `causal-memory-bottleneck.json` è una perturbazione algebrica dello stato interno, non una coppia di storie fisiche raggiungibili dimostrata.
