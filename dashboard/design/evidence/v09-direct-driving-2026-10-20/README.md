# Prototipo privato di guida diretta — 20 ottobre 2026

`receipt.json` riassume il perimetro: nessuna modifica della scheda o dello store
originale. Non sono modelli ufficiali da importare nei piloti attivi.

- `prototype.py`, `base-31..35.json` e relativi `.weights.json`: preparazione
  supervisionata e aggregazione degli stati realmente visitati dalla rete.
  Gli esempi iniziali sono comuni, gli attori e l'ottimizzazione hanno cinque
  semi distinti. `origin.trainingSeed` identifica il seme del bootstrap; il
  template del profilo in questi asset privati usa il seme pilota 31, ricreato
  con il vero profilo di ciascun run da `train_direct.py` prima del rinforzo.
- `dev-31.*`: prima fattibilità, precedente al congelamento delle interfacce.
- `dev-rl-*`: una sonda completa per metodo a 49.152 passi; PPO positivo,
  SAC/TD3/Tattico respinti. Regole tattiche del nuovo prefisso ancora incomplete
  in questa prima sonda: non usarla come confronto nel traffico.
- `train_direct.py`, `final-ppo-31..35.json`: cinque run PPO su sorgenti congelati
  in `/tmp/smartpc-direct-driving-study/dashboard`. Banca finale 720001–720005,
  distinta dalla raccolta, dalle correzioni supervisionate e dalle promozioni.
- `ppo-summary.json`: gruppi completi e serie separate di tre giri senza training.
- `tests-final-contract.txt`: 42 test passati. Log iniziali conservati: un reset
  non svuotava la cache diretta; corretto. Il confronto PyTorch inizialmente
  saltato è stato eseguito nella verifica finale con dipendenza PC esplicita.
- `receipt.json`: hash dei sorgenti congelati e del candidato attuale. Unica
  differenza successiva: solo il comando diretto dell'ego può marcare le sue
  regole; un rivale diretto non può cambiare quelle dell'ego. Test dedicato
  passato. Nelle campagne solo l'ego è sempre indice 0, quindi ramo equivalente.

I due log di orchestration iniziali falliti derivano rispettivamente dal primo
snapshot con profilo incompleto e da un errore di sintassi dello script di
raccolta dei risultati: nessun run incompleto è contato come un seme completo.

Punteggi, velocità e durate sono simulati su PC. Nessuna attestazione ARM,
fluidità ottica, capacità su altri fondi/vetture o superiorità tattica.
