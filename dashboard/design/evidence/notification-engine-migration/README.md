# Prove della migrazione notifiche · 3 ottobre 2026

Le fixture usano preferenze/cache/SQLite isolati. Le suite non modificano lo stato degli eventi di produzione. I PNG EGLFS sono catture 960×640 della PowerVR; i PNG local usano il backend software del PC.

- `local-suite/checks.json`: 23 harness, Qt 6.11.2; log per test.
- `board-suite/checks.json`: gli stessi 23 harness, Qt 6.8.2; SHA dei file eseguiti.
- `eglfs/day-*`, `eglfs/night-*`: dieci famiglie di assert per tre temi; 13 catture per profilo.
- `eglfs/stress-presets`, `eglfs/stress-fonts`: 100 cambi ciascuno, piccoli/grandi/urgenti e tre TTF reali. Tutti gli intervalli e i primi usi sono conservati nei report. Il profilo warm non include il primo uso della coppia modalità/tema.
- `eglfs/baseline` e `eglfs/current`: medesimo harness di navigazione, 20 secondi, per la distribuzione precedente e la nuova.
- `offline`: processo nuovo in PrivateNetwork, rete effettivamente non disponibile, preferenze/cache/SQLite persistenti della fixture.
- `distribution`: backup/installazione/rollback completi; gli archivi e i dati reali restano privati sulla board. Le prove di salute/integrità accompagnano la distribuzione.

Per ripetere gli assert: `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python3 dashboard/check_notifications.py`. La matrice e le misure fisiche richiedono EGLFS sulla board e il servizio fermo per avere una sola finestra; `eglfs/run-validation.sh` documenta i comandi eseguiti e ripristina il servizio all'uscita. Il controllo offline richiede un nuovo directory di fixture per `verify_notifications_restart.py --prepare`, seguito da un processo con PrivateNetwork=yes.

FrameSwapped indica la presentazione richiesta da Qt, non il tempo GPU o una misura ottica. PSS/RSS non includono necessariamente tutte le allocazioni del driver. I temi futuri devono ripetere le prove sui propri layout, asset e ricette.
