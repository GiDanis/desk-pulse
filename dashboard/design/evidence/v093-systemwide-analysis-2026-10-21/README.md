# v0.9.3 — evidenze dell'analisi dell'intero sistema

**21 ottobre 2026 · Europe/Rome.** [Analisi generale](../../v093-systemwide-analysis.md), [piano V0–V9](../../v093-systemwide-execution-plan.md). Il precedente [archivio hardware/Gioco](../v093-performance-study-2026-10-21/README.md) rimane distinto.

## Riscontri raccolti

| File | Contenuto / perimetro |
| --- | --- |
| [source-system-audit.json](source-system-audit.json) | Hash e siti di timer/I/O/callback di 52 sorgenti/configurazioni di app, domini, notifiche, tema e unità; inventario asset Apple |
| [system-observation.json](system-observation.json) | Undici campioni passivi a distanza 2 s, tutti i processi, CPU/VM/disco, memorie, servizi/timer, boot, cgroup; nessun workload imposto |
| [system-summary.json](system-summary.json) | Delta e attribuzione del campione: CPU globale 3,47%, GUI 13,62%/Plymouth 4,43% di un core; PSS e swap/fault |
| [boot-service-investigation.txt](boot-service-investigation.txt) | Job systemd pendenti, quit Plymouth status 1, unità in attivazione, servizio estraneo inattivo e drop-in della Dashboard |
| [domains-pc.json](domains-pc.json), [domains-arm.json](domains-arm.json) | Getter di tutti i domini e Info, callback Meteo/Account, costruzione servizi su fixture, scaling eventi 0/100/1.000; rete negata e store privati |
| [sport-saved-arm.json](sport-saved-arm.json) | Cache Sport reale letta offline, 380 incontri, getter e profilo; stato `stale`, nessuna verifica live/API |
| [provider-state-metadata.json](provider-state-metadata.json) | Aggregati SQLite eventi in `mode=ro`: 77 righe/2 attive, dimensioni e WAL/SQLite 3.46.1; nessun payload esportato |
| [surface-coverage-summary.json](surface-coverage-summary.json) | Copertura riconciliata di 62 superfici non Gioco; 340 combinazioni distinte su quattro profili PC offscreen |
| `surfaces-*.json` e log associati | Risultati originali/parziali e tail rieseguite con oracolo pubblico Rete; i fallimenti diagnostici non sono cancellati |
| [apple-charts/report.json](apple-charts/report.json) e PNG | Due componenti reali, 2×512 punti e 200 cambi, zero letture nascoste, parità pixel hide/update/show, clearing MiniHistory |

Gli script `inspect_system.py` e `inspect_provider_metadata.py` sono solo letture. `probe_domains.py` e `probe_cached_sport.py` creano servizi/cache/settings temporanei; niente Start/training/provider reali. `probe_all_surfaces.py` opera sul Main in fixture e non prende il display della board. `audit_system_sources.py` è inventario statico, non un profiler.

## Ripetibilità e isolamento

Eseguire dalla radice del checkout. Per mantenere la fotografia usare output nuovi. Interprete PC verificato `/home/giuseppe/.cache/smartpc-population-py312/bin/python` (Python 3.12.13/Qt 6.8.2/NumPy 2.2.6), board `/var/lib/smartpc-dashboard/game-runtime/bin/python` (Python 3.13.5/Qt 6.8.2/NumPy 2.2.6). I processi CPU di sonda usano nice 10 e BLAS a un thread; non cambiano priorità/governor della produzione.

```bash
python3 dashboard/design/evidence/v093-systemwide-analysis-2026-10-21/audit_system_sources.py \
  > /tmp/smartpc-v093-system-sources-new.json

/home/giuseppe/.cache/smartpc-population-py312/bin/python \
  dashboard/design/evidence/v093-systemwide-analysis-2026-10-21/probe_domains.py \
  --source dashboard > /tmp/smartpc-v093-domains-pc-new.json
```

Per il sistema usare SSH, inviando lo script su stdin senza installarlo:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 \
  -i /home/giuseppe/.ssh/smartpc_ed25519 smartpc@192.168.1.179 \
  'sudo -n python3 -' \
  < dashboard/design/evidence/v093-systemwide-analysis-2026-10-21/inspect_system.py \
  > /tmp/smartpc-v093-system-new.json
```

`inspect_provider_metadata.py` usa lo stesso schema. `probe_cached_sport.py` viene inviato sullo stesso SSH ma eseguito con `sudo -n runuser -u smartpc -- env PYTHONDONTWRITEBYTECODE=1 /var/lib/smartpc-dashboard/game-runtime/bin/python -`; legge soltanto la cache nota e usa preferenze private.

Per `probe_domains.py` ARM, i quattro JSON di fixture (weather-zero, sport-normalized, racing-f1 e racing-motogp) sono stati caricati dal checkout e anteposti allo script come assegnazione del dizionario `_STUDY_FIXTURES`, usando il `repr` Python dei dati. La board esegue `python - --source /opt/smartpc/dashboard`, in ambiente privato, senza necessità di installare diagnostica nel runtime. I nove hash delle sorgenti comuni PC/ARM permettono il confronto di identità; tempi diversi non misurano il solo rapporto tra CPU.

## Corpus delle superfici

Il catalogo contiene 160 scenari/68 superfici: sei scenari/superfici Gioco esclusi da questa matrice, che qui copre tutti i restanti 154/62.

- Apple giorno: primi 145 casi riusciti del corpus iniziale più nove tail riuscite = **154 casi distinti/62 superfici**.
- Apple notte, Base giorno, Functional giorno: primi 53 casi/superfici riusciti del sottoinsieme a superficie unica più nove tail riuscite = **62/62 per profilo**.
- Totale riconciliato **340**. Non si sommano tentativi falliti, duplicati o riesecuzioni della stessa combinazione.

L'oracolo iniziale del supporto fixture cercava `DashboardOverlay` sulle nuove superfici metrics Rete. Il primo adattamento diagnostico ha usato il nome errato `surfaceId` sul ViewHost, che espone `contentId`: anche quei fallimenti sono conservati. Il controllo finale della sola sonda verifica host pubblico corretto/visibile/pronto, contentId, geometria del renderer e contesto pubblico attivo. Il runtime non è stato cambiato. La correzione dell'harness generale è prevista in V0.

Esempio per la tail corretta:

```bash
/home/giuseppe/.cache/smartpc-population-py312/bin/python \
  dashboard/design/evidence/v093-systemwide-analysis-2026-10-21/probe_all_surfaces.py \
  --source dashboard --theme apple --variant day --public-network-oracle \
  --from-case network.router:default --output /tmp/smartpc-v093-apple-tail-new.json
```

La copertura è funzionale e verifica invarianti di contenuto/focus/stile/delivery/attore. I tempi dei casi includono setup, pumping e modifiche dei token: non sono frame time né un confronto prestazionale nativo fra temi. Tutti i profili usano dati sintetici, stato privato e socket negati.

## Limiti da mantenere visibili

- Nessun riavvio, cambio tema/governor o intervento sulle unità è stato applicato. Il problema Plymouth è identificato, non risolto.
- Il timer estraneo è presente; servizio inattivo nel campione non significa timer disattivato. Non è stato avviato per la prova.
- Il campione CPU dura 20,34 s e include l'osservatore: non certifica saturazione o termica sotto tutti i carichi.
- Getter e callback misurano solo quelle funzioni; la catena fino al pannello/avviso fisico richiede baseline EGLFS/HID/ottica.
- Cache Sport è precedente e dichiarata `stale`; nessuna falsa conferma live o chiamata reale aggiunta.
- Gli altri provider usano fixture/demo: i payload live maturi, quote e tempi API restano da qualificare nell'esecuzione.
- Mille eventi attivi sono stress sintetico; la produzione ne aveva due. Nessuna priorità sproporzionata ricavata dallo stress.
- I grafici sono verificati offscreen: parità pixel e lavoro invisibile non sono GPU timing o FPS.
- NPU/GPU compute/nuovo driver non vengono dichiarati implementati o necessari da questi test.

Fonti primarie aggiornate: [Qt prestazioni](https://doc.qt.io/qt-6.8/qtquick-performance.html), [QThreadPool](https://doc.qt.io/qt-6.8/qthreadpool.html), [Linux CPUFreq](https://docs.kernel.org/6.6/admin-guide/pm/cpufreq.html), [SQLite WAL](https://www.sqlite.org/wal.html). Ulteriori riferimenti hardware/compilazione/acceleratori rimangono nell'archivio precedente con i relativi limiti.
