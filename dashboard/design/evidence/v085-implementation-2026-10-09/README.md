# Evidenze 0.8.5 · 9 ottobre 2026

`local-final-results.json` raccoglie gli esiti finali di 75 controlli, con puntatori alle riesecuzioni pertinenti. `regressions/`, `core-first/`, `targeted*/`, `ux-final/` e i log intermedi conservano i tentativi, compresi quelli falliti.

`debug-settings.py` e `debug-captures/` sono diagnostica intermedia con bypass dichiarato del confronto digest mentre si completava il preflight: **non sono qualifica della revisione finale**. `settings-night/`, `settings-day/`, `apple-preflight.json` e la copia delle prove native attestano invece le revisioni esatte.

La baseline dell'incidente e delle prove iniziali resta in `../v085-settings-analysis-2026-10-09/`, non sovrascritta. I dati dei render sono fixture private, con rete negata. I tempi software non sono misure ottiche/GPU/input-pixel. Le prove di installazione e reboot risiedono prima sulla board sotto `/var/lib/smartpc-dashboard/v085-dashboard-proof/`.
