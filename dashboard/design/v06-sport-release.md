# SmartPC v0.6 · Serie A · resoconto del rilascio

**Data:** 30 settembre 2026. Prima integrazione Sport implementata e installata sulla Orange Pi. Scope: Serie A; F1 e MotoGP rimangono le estensioni successive del [piano](./v06-sport-plan.md).

**Revisione successiva:** [correzione partite future e miglioramenti UX](./v06-sport-ux-fix.md), con nuovi test e catture del runtime. I risultati qui sotto descrivono il primo rilascio.

## Funzioni disponibili

- FotMob REST diretto: calendario della stagione, classifica completa, dettaglio con marcatori/statistiche e moduli delle formazioni quando presenti.
- ESPN come riserva esplicita: scoreboard, classifica e dettagli; calendario dei giorni vicini, indicato come parziale. Nessuna fusione silenziosa dei due provider.
- Sport nel carosello e in Moduli visibili; Prossime, In corso condizionale, Risultati. Elenchi di tre righe, tutte le 20 posizioni accessibili, dettaglio e ritorno del focus.
- Preferenze persistenti: squadra, prossimo incontro in Home, stagione corrente/precedente, aggiornamento manuale controllato. Home Sport disattivata inizialmente; partita futura entro sette giorni dopo preferenza esplicita.
- Worker Qt, polling adattivo, cache HTTP e cooldown, backoff/Retry-After; cache persistente e validata, scrittura atomica e ultimo stato conservato in errore. Archivi delle ultime due stagioni, purgati solo nel namespace delle cache Sport.
- Stato e ora del dato separati dal tentativo di controllo; punteggio mancante distinto da 0–0; nessun badge Live da cache, vecchia partita o stato sconosciuto.
- Motore gol predisposto: evento/punteggio/VAR, baseline, deduplicazione, revoca, preferenza disattivata. Il gate `SMARTPC_SPORT_LIVE_VERIFIED` resta **disattivato**, in attesa di prova attiva. La vista indica feed da collaudare; ESPN non produce overlay gol senza una conferma dimostrata.

## Verifiche completate

| Verifica | Risultato | Evidenza |
| --- | --- | --- |
| Adapter/contratti/persistenza | **8 test passati** su PC e Orange Pi: estratti reali, stati e zero/mancante, atomicità/cache corrotta, freschezza, fallimento provider, VAR/baseline, cooldown 429, fuso/cambio stagione | [check_sport.py](../check_sport.py) |
| QML Sport | Pass su PC e board: prossime/risultati, assenza vista Live vuota, 20 righe, dettaglio, fonte visibile, focus dopo Avvisi, preferenze, errore worker e cache | [check_sport_ui.py](../check_sport_ui.py) |
| Regressione v0.5 | Pass su PC e board: navigazione, meteo/account, banner, casella, badge e impostazioni | [check_dashboard.py](../check_dashboard.py) |
| Rete reale board | FotMob 2026/27: **380 partite, 20 squadre**, senza token | [online.json](./evidence/v06-implementation-orange-pi/online.json) |
| Fallback reale | FotMob forzato indisponibile dal checker; risposte ESPN reali: **20 incontri vicini e 20 squadre** | [fallback PC](./evidence/v06-fallback-implementation-pc.json) |
| Stagione precedente | FotMob 2025/26: 380 fixture; ESPN standings con `season=2025` restituisce la stagione richiesta | Controllo HTTP mirato sul PC durante implementazione; non misura latenza o disponibilità continua |
| Nuovo processo offline | Cache recuperata, 380 partite/20 squadre, stesso timestamp, stato offline e nessun live | [offline.json](./evidence/v06-implementation-orange-pi/offline.json) |
| Reboot del sistema | Boot ID cambiato, servizio attivo con `NRestarts=0`; log conferma rete Sport disabilitata e `cache=True`; cache conservata | [reboot-offline.json](./evidence/v06-implementation-orange-pi/reboot-offline.json) |
| Ripresa normale | Override di prova rimosso; nuovo download valido dopo ripristino; file installati confrontati SHA-256 con sorgenti locali | [installed.json](./evidence/v06-implementation-orange-pi/installed.json) |
| GPU/display | EGLFS/OpenGL, catture 960×640; 15 s, 32 azioni, 170 intervalli: mediana **16,61 ms**, p95 **17,67 ms**, massimo **18,23 ms** | [render.json](./evidence/v06-implementation-orange-pi/render.json) |

La prova reboot usa `SMARTPC_SPORT_OFFLINE=1` nel servizio e riavvia davvero il sistema operativo. Disabilita le richieste del modulo Sport; Wi-Fi e SSH rimangono disponibili. Non è una nuova prova di spegnimento del Wi-Fi per tutti i moduli. L'override temporaneo è stato eliminato e la rete Sport ripristinata.

Le catture e la misura GPU usano dati REST reali, con una configurazione di rendering separata dalle preferenze del kiosk. Nessun replay viene caricato da `app.py`. La misura esclude i periodi senza animazione: è un campione breve di interazione, non un endurance test o una garanzia di 60 fps costanti. Leggibilità alla distanza d'uso e pressione manuale dei tasti restano da confermare sull'apparecchio; l'input nelle verifiche è simulato.

### Catture EGLFS

- [Prossimo incontro](./evidence/v06-implementation-orange-pi/sport-next.png).
- [Risultati](./evidence/v06-implementation-orange-pi/sport-results.png).
- [Classifica](./evidence/v06-implementation-orange-pi/sport-table.png).
- [Impostazioni Sport](./evidence/v06-implementation-orange-pi/sport-settings.png).

## Limiti e decisione di rilascio

**Rilasciata la v0.6 per calendario, risultati, classifica e dettagli Serie A.** La capacità di leggere un payload non qualifica il feed live. Serve ancora una partita attiva per ritardo gol, VAR e continuità; il badge Live e le notifiche non sono abilitati. Non viene promessa una latenza di 45 secondi.

Un header applicativo ESPN usato durante implementazione ha ricevuto 403; urllib con UA standard ha risposto 200. Il client ESPN usa quindi il trasporto standard; il comportamento osservato non identifica la causa del filtro né garantisce accesso futuro. FotMob usa UA applicativo. Errori 403/429 hanno cooldown; per un `Retry-After` attivo non si martella il dettaglio a ogni ciclo.

Non sono implementati F1/MotoGP, telemetria, archivi di tutte le stagioni o notifiche da feed secondari con conferma incerta. Le due stagioni selezionabili coprono la prima release; ulteriori competizioni/provider rimangono estensioni esplicite.

## Backup e ripristino

Prima del deploy sono stati salvati sulla board:

- `/var/backups/smartpc-dashboard-v05-before-sport-20260930` — sorgenti della v0.5.
- `/var/backups/smartpc-v05-state-before-sport-20260930.tar.gz` — directory di stato/preferenze prima di Sport.

È verificata la presenza del backup; **non è stato eseguito un ripristino completo della v0.5**, per non confonderlo con il collaudo della versione nuova. Ripristino concreto dei sorgenti (sulla board):

```bash
sudo systemctl stop smartpc-dashboard
sudo cp -a /var/backups/smartpc-dashboard-v05-before-sport-20260930/. /opt/smartpc/dashboard/
sudo systemctl start smartpc-dashboard
systemctl show smartpc-dashboard -p ActiveState -p NRestarts -p ExecMainStatus
```

I nuovi file Sport rimangono inattivi quando `app.py`, `state.py` e `Main.qml` tornano alla v0.5; non è necessario cancellare cache o archivi per ripristinare il software. L'archivio di stato consente anche il recupero delle preferenze, ma sostituirlo riporterebbe indietro anche gli avvisi successivi: non farlo automaticamente.

Le prove si possono riprodurre usando i tre checker citati. Per `verify_sport_board.py --mode capture`, fermare prima il kiosk e configurare EGLFS come [run.sh](../run.sh), poi riavviare il servizio al termine. Non lasciare l'override offline dopo una verifica.
