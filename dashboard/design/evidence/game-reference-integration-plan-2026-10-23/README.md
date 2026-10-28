# Piano Gioco e stabilità menu · 23 ottobre 2026

Analisi e pianificazione, nessuna correzione runtime o installazione eseguita.

- `board-observations.json`: lettura corrente core 0.9.4-rc.1, hash di sette file coerenti, incidente watchdog e storia di recovery/readmission. I log completi rimangono nella cache privata; nessun core dump, archivio piloti o credenziale è copiato qui.
- `pc-navigation-apple.json`: Main reale con Apple Calm 1.6.4, cinque modalità, due discese/risalite complete per modalità, dati nuovi isolati. Start e tastierino fisico non provati; il report non chiude il bug.
- `probe_navigation.py`: riproduzione PC di sola navigazione. Eseguire con `PYTHONPATH=dashboard`, runtime Python 3.12/PySide6 6.8.2.1, `--theme apple --output DIRECTORY_NUOVA`; nessun Start o apprendimento.
- `upstream-audit.json`: commit End2Race fissato, hash di nove file letti, contratto di controllo e licenza; nessuna esecuzione di codice esterno o installazione di dipendenze.

Piano ufficiale: [integrazione e criteri](../../game-reference-integration-plan.md). Dati e incidenti precedenti non vengono presentati come una riproduzione del problema segnalato oggi.
