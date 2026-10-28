# Matrice estesa interrotta manualmente

La prima verifica privata ripeteva i quattro learner maturi in tutte le modalità per ciascun tema. È stata interrotta manualmente tramite SIGTERM al solo runuser del test, prima di qualsiasi sostituzione della produzione, per limitare la chiusura alla manutenzione finale. Il programma ha ripristinato automaticamente il servizio rc.2; NRestarts=0. Il codice SIGTERM nel log descrive questa interruzione, non un crash spontaneo della Dashboard.

I casi parziali non vengono conteggiati come una matrice superata. La verifica conclusiva usa i quattro learner sul PC e un learner nelle quattro modalità per ciascun tema sulla scheda, oltre alle gare. Log, risultato parziale e sorgente del programma interrotto sono conservati. Nessuna modifica a dati o modelli personali.

Dopo la consegna è stato individuato e terminato il solo lettore metadata orfano di questa prova interrotta, verificando UID, parentela e file SQLite aperto nei temporanei privati. Quindi rimossi circa 297 MB di temporanei; servizio e GUI di produzione conservano i PID della nuova consegna. L’audit conclusivo riporta nessun handle rimasto nei temporanei.
