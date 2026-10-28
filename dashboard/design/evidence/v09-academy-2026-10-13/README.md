# Accademia di guida · 13 ottobre 2026

- `before/` e `before-source.json`: backup dei sorgenti prima delle modifiche di questa implementazione; altre modifiche manuali erano già presenti.
- `pc/`: regressioni, UI/immagini 960×640, replay, gare e prove di apprendimento isolate. `smooth-progressive-normalised.json` è il protocollo finale di Partenza; i tentativi precedenti restano visibili.
- `board/`: baseline, backup, recupero SQLite, verifiche native, compatibilità su copie dei sei checkpoint e consegna. I riferimenti congelati delle gare sono controllori geometrici, non reti addestrate certificate.

`base-neat-initial-missing-fixture.txt` documenta il primo arresto del banco: mancava il renderer diagnostico, escluso correttamente dalla distribuzione. È stato aggiunto soltanto alla cartella di prova; l'installazione copia esclusivamente i file del manifest.

I contatori del nuovo percorso ripartono da zero su Start; `production-checkpoints-copy.json` controlla l'archivio del percorso precedente. I valori `stepsAfter` non indicano perdita dei passi originali. Le qualifiche nuove non vengono assegnate dal trasferimento.

I tempi Qt sono misure software. I test non certificano input USB, FPS ottici, abilità universale dei metodi o qualifica dei piloti reali.

La prima cattura completa (`full-startup-initial-early.png`) e il relativo heartbeat (`full-startup-initial-stale.json`) non attestano la GUI pronta: erano troppo precoci. La verifica finale attende il PID corrente e il suo heartbeat coerente; `full-startup.json` contiene `currentPIDVerified=true`. La cattura finale conserva la luminosità notturna dell'utente.
