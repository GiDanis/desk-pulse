# Evidenze dispositivo A1–A6

I report sono separati per sorgente e scopo.

- `initial`: primo staging, stato dirty dichiarato.
- `final-pre-layout`: sorgente `5cbbc3c`, stress storico, tracing incompleto in alcuni run.
- `before-projection`: sorgente `dc85680`, stress di 1.200 cambi; l’esito iniziale fallito dell’overlay è conservato.
- `before-subscriptions`: sorgente `fa7fe11`, altri 1.200 cambi, offline e idle; il test layout ha un esito intermittente fallito, conservato.
- `final-subscriptions`: sorgente `17db764`, sette verifiche mirate passate su Qt 6.8.2, Main reale offscreen/EGLFS: selezione domini, dati freschi, giorno/notte, layout, animazione, sei notifiche e menu esterno. La scena animata è osservata passivamente, senza animazione diagnostica aggiunta.
- `final-install`: sorgente `bb4d76c`, 15 test di recovery/salvataggio sulla board, manifest runtime 435 file, backup/installazione/persistenza e vero reboot del servizio EGLFS. L’ultima modifica differisce dai test UI solo per il salvataggio asincrono e il relativo test; `source-continuity.json` elenca i due file.

Non vengono ripetuti altri stress per rispettare la decisione del 6 ottobre: dispositivo dedicato, risorse disponibili per la dashboard, budget diagnostici storici informativi. I risultati oltre soglia restano tali. Il primo controllo d’installazione ha eseguito rollback perché pretendeva un journal fisico con Base; il controllo è stato corretto per lo stato iniziale senza journal. La verifica post-reboot usa una breve attesa di heartbeat pronto invece di un singolo campione. I rispettivi esiti iniziali sono conservati.

Reboot richiesto via sistema operativo, input sintetico e rete isolata sono distinti da power cut, tastierino fisico, lettura ottica e soak 24/7. Le prove offline storiche non diventano prove offline del sorgente finale per attribuzione. Il runtime in produzione conserva Base e tutte le preferenze esistenti; il tema Studio usato dai test usa dati/store isolati.
