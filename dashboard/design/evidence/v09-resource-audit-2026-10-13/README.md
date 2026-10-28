# Audit risorse · 13 ottobre 2026

- `hardware-runtime.json`: manifest rc.9/572 hash, librerie/devices GPU, CPU policies, devfreq e stato driver. Non identifica un carico GPU affidabile dal primo contatore anomalo.
- `board-profile.json`: 8 s Home, due worker temporanei da 18 s, sette campioni cProfile da 6 s; dump gioco originale invariato. Throughput profilato distinto dalle scene IPC e dagli FPS.
- `preview-components.json`: secondo worker privato con timer su frame/tick. Timers wall delle componenti CPU; pista QML non renderizzata dal processo di prova.
- `final-health.json`: controllo finale usando HOME/XDG e utente corretti; servizio attivo e manifest conforme.
- Script `probe-board.py`, `probe-preview.py`, `read-hardware.py`: strumenti di analisi; non fanno parte del pacchetto runtime. I primi tentativi hanno corretto l'assenza del file kernel `/proc/.../children` usando `ps` e la raccolta del file timer alla pulizia del temporaneo.

Nessun servizio fermato, nessun cambio di governor/affinità della dashboard, nessun allenamento dei piloti originali. Benchmarks concorrenti alla Home, non prova di frame pacing della pista. I risultati nativi precedenti rc.9 sono riportati separatamente nello studio.
