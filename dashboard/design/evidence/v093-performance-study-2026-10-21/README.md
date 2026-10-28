# v0.9.3 — evidenze dello studio prestazioni

**21 ottobre 2026 · Europe/Rome · inventario, analisi e sonde headless; nessuna attuazione runtime o installazione.**

Documento principale: [Dashboard/Apple Calm v0.9.3](../../v093-dashboard-performance-study.md). Baseline corrente rimasta **0.9.0-rc.28**, 642 file del manifest conformi; Apple Calm 1.6.3 attivo, digest `faf3e0032162416a471c8122d320709f47b71df0667b042816fffa4e3b452d62`.

Completamento: [misure e attribuzione §14](../../v093-dashboard-performance-study.md#14-completamento-misure-attribuzione-e-priorità-definitiva), [piano pronto da eseguire](../../v093-dashboard-performance-execution-plan.md). Il primo inventario era passivo; nella seconda fase si aggiungono sonde CPU in processi separati e letture SQLite protette da `mode=ro`. Le eventuali scritture delle sonde sono soltanto in store/settings/cache temporanei eliminati alla fine. Nessun runner EGLFS ha preso il display della produzione.

## Contenuto

| File | Cosa prova | Cosa non prova |
| --- | --- | --- |
| [board-inventory.json](board-inventory.json) | Identità software, core/MIDR/ISA, RAM, governor, librerie mappate, cgroup, processi/thread; quattro campioni passivi circa 6 s; manifest e servizio prima/dopo | Carico sostenuto, collo di bottiglia, qualità visiva o FPS |
| [board-runtime-supplement.json](board-runtime-supplement.json) | Versioni dell'interprete realmente usato, GIL, build NumPy/BLAS/SIMD, enumerazione OpenCL/Vulkan, KMS, configurazione kernel e heartbeat corrente | Training/inferenza accelerati, frequenza frame del contenuto, latenza fisica |
| [board-platform-supplement.json](board-platform-supplement.json) | Informazioni cache esposte/incomplete, trip termici, mount root, hash delle librerie EGL/GLES/PVR/OpenCL/Vulkan | Dimensioni cache mancanti, banda DDR effettiva, limiti di alimentazione o corretto raffreddamento sotto carico |
| [source-audit.json](source-audit.json) | SHA-256 e punti di interesse di 22 sorgenti locali; 71 file QML Apple e due dichiarazioni Canvas | Percentuali di costo runtime, componenti tutti vivi, speedup |
| `inspect_board.py`, `inspect_runtime.py`, `inspect_platform.py` | Procedure di lettura ripetibili, stdout JSON | Non sono test di prestazione |
| `audit_sources.py` | Audit locale, senza import del codice Dashboard | Non esegue o modifica il runtime |
| [board-runtime-supplement.stderr.txt](board-runtime-supplement.stderr.txt) | Warning della sola enumerazione NumPy | Non è un warning QML o un errore del servizio |
| [critical-paths-arm.json](critical-paths-arm.json), [PC](critical-paths-pc.json) | Costi isolati di progressi/scene/checkpoint sintetici e profili; sette hash di sorgente comuni identici | Pacchetto reale, training, latenza del pannello, percentili stabili o fattore CPU PC/ARM |
| [store-growth-arm.json](store-growth-arm.json), [PC](store-growth-pc.json) | Scaling su 0/100/1.000 sessioni/eventi temporanei e progressi nominali 20/40 | Stato della produzione o velocità degli algoritmi appresi |
| [board-store-metadata.json](board-store-metadata.json) | Conteggi, dimensioni e query plan della snapshot SQL corrente in sola lettura | Nessun contenuto di policy/nomi/checkpoint esportato |
| [readonly-metadata-arm.json](readonly-metadata-arm.json) | Tempi dei metodi attuali sui metadati correnti via facade SQLite `mode=ro`, più profilo | Nessuna migrazione/GUI/FPS; connessione riusata, nice 10 e cinque campioni sono limiti espliciti |
| [navigation-pc-apple](navigation-pc-apple), [riepilogo](navigation-pc-summary.json) | 177 azioni del Main offscreen con fixture, zero richieste di rete/messaggi QML; percentili ricalcolati dai grezzi | Pannello, GPU, USB, EGLFS o qualifica di coda con molti campioni |
| [board-readiness.json](board-readiness.json) | FTRACE non compilato e letture del clock framework | La PLL o il rate riportato non certificano frequenza fisica/banda DDR |
| [source-audit-completion.json](source-audit-completion.json) | Audit ampliato per i lettori/strumenti del completamento | Non sostituisce l'audit originale di 22 file, conservato |

Manifest SHA-256 della baseline: `ab50d59de7e37b73a9f885b9e3863ae6571f04089ddf68ea4209296af77e7e2f`.

MainPID supervisor **207975**, GUI **207984** nell'inventario; servizio attivo con **NRestarts=0** nelle ricevute. Heartbeat del supplemento associato al PID GUI corrente, pronto, `home.clock`, nessuna transizione. Nessun learner/writer presente nel cgroup durante l'inventario iniziale; resource tracker separato presente. Nessuna navigazione/Start/Pausa sulla produzione, modifica ai dati dei piloti, installazione, cambio tema/governor, riavvio servizio o reboot. La navigazione automatica PC usa esclusivamente il Main con fixture in processo isolato e rete negata.

## Ripetere le letture

Eseguire dalla radice del checkout, con SSH già configurato. Per conservare la fotografia usare nomi di output nuovi a ogni sessione. Gli script vengono inviati su stdin, senza installarli sulla board; sudo serve a leggere mappe/processi, debugfs e il namespace privato del servizio. Non importano i moduli della Dashboard o interrogano provider.

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 \
  -i /home/giuseppe/.ssh/smartpc_ed25519 smartpc@192.168.1.179 \
  'sudo -n python3 -' \
  < dashboard/design/evidence/v093-performance-study-2026-10-21/inspect_board.py \
  > /tmp/smartpc-v093-inventory-new.json
```

Per `inspect_runtime.py` usare l'interprete del servizio verificato nell'inventario:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 \
  -i /home/giuseppe/.ssh/smartpc_ed25519 smartpc@192.168.1.179 \
  'sudo -n /var/lib/smartpc-dashboard/game-runtime/bin/python -' \
  < dashboard/design/evidence/v093-performance-study-2026-10-21/inspect_runtime.py \
  > /tmp/smartpc-v093-runtime-new.json
```

`inspect_platform.py` usa lo stesso schema del primo comando. Per il solo audit locale:

```bash
python3 dashboard/design/evidence/v093-performance-study-2026-10-21/audit_sources.py \
  > /tmp/smartpc-v093-sources-new.json
```

`clinfo` e `vulkaninfo` enumerano e possono inizializzare transitoriamente il driver; non lanciano i workload di confronto descritti nel piano. Le letture e l'hashing hanno un costo di osservazione non nullo. Nessun dato di questa sessione viene presentato come FPS o guadagno prestazionale.

### Ripetere le sonde del completamento

`probe_critical_paths.py` e `probe_store_growth.py` ricevono `--source` e scrivono JSON su stdout. La prima alloca un replay sintetico di 48 MiB e ne misura la codifica, senza training; la seconda popola soltanto il proprio SQLite temporaneo. Sul PC l'interprete verificato è `/home/giuseppe/.cache/smartpc-population-py312/bin/python`, non il vecchio venv in `.local/share`, che al controllo attuale non dispone di PySide6. Il test in questa sessione usa Qt 6.8.2/NumPy 2.2.6.

```bash
/home/giuseppe/.cache/smartpc-population-py312/bin/python \
  dashboard/design/evidence/v093-performance-study-2026-10-21/probe_critical_paths.py \
  --source dashboard > /tmp/smartpc-v093-critical-pc-new.json
```

Per ARM inviare lo script su stdin, come nell'inventario, con comando remoto:

```bash
sudo -n runuser -u smartpc -- env PYTHONDONTWRITEBYTECODE=1 \
  /var/lib/smartpc-dashboard/game-runtime/bin/python - --source /opt/smartpc/dashboard
```

`inspect_store_metadata.py` è una lettura di conteggi/byte/query plan senza import dell'applicazione. `probe_readonly_metadata.py` va eseguito soltanto sulla board nota tramite lo stesso interprete, senza l'argomento `--source`: il facade protegge il DB con una transazione `mode=ro` e non ne richiama il costruttore/migrazioni. Non modifica pesi, sessioni o dati di apprendimento.

`inspect_readiness.py` legge configurazione e rate dei clock senza abilitare tracing. I raw e i log delle sonde sono conservati; gli stderr delle sonde completate sono vuoti. `navigation-pc-summary.json` usa nearest-rank; il report originale conserva anche le statistiche legacy, che non vanno usate per i percentili piccoli senza ricalcolo.

## Limiti conosciuti

- Percentuale PVR fuori dominio, anche **1505%**: conservata grezza; non utilizzabile per percentuali di occupazione o margine. Nessun cap cosmetico a 100.
- `CONFIG_PSI` e `CONFIG_UCLAMP_TASK` disabilitate; file PSI assenti. Controller CPU non ancora attivato sotto `system.slice`, cpuset non delegato a questo livello. Non sono prove di malfunzionamento della Dashboard.
- L'enumerazione delle policy comprende la directory globale `schedutil`, che non è una terza policy: soltanto policy0/6 hanno CPU associate.
- Query pacchetti con pattern: returncode 1 per alcune assenze; righe senza versione non indicano pacchetti installati. NumPy/BLAS sono nell'ambiente pip del servizio, PVR è vendor: verificarli da metadata/mappe/hash, non soltanto da dpkg.
- `np.show_runtime` segnala `threadpoolctl` assente; nessuna dipendenza è stata installata. La build `MAX_THREADS=64` non misura thread attivi.
- Enumerazione Vulkan riuscita con warning su assenza DISPLAY/XDG_RUNTIME_DIR nel processo di ispezione: nessuna surface grafica provata da quel comando. La GUI resta EGLFS.
- `theme-runtime-status.json` del primo probe non esiste; l'heartbeat corretto è letto nel `/tmp` privato del servizio dal supplemento. Il record è pronto e aggiornato.
- Sysfs cache non espone size/line size/associatività; non ricostruire valori precisi da descrizioni generiche A55/A76. La topologia riportata dal BSP richiede riscontro prima di tuning per cache.
- Le temperature sono una finestra breve; i trip termici sono configurazioni, non eventi di throttling misurati. Alimentazione, memoria nominale, banda DDR e cooling sostenuto non sono qualificati.
- Il vecchio studio dell'11 ottobre contiene una descrizione hardware incompatibile con l'inventario attuale: rettifica aggiunta senza cancellare la storia.

## Fonti tecniche

Consultate il **21 ottobre 2026**, soltanto fonti primarie. Collegamenti e conclusioni nel documento principale; documentazione Qt famiglia 6.8, runtime locale 6.8.2: ogni funzione nuova va verificata sulla patch locale.

- Qt: [prestazioni QML](https://doc.qt.io/qt-6.8/qtquick-performance.html), [scene graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html), [renderer](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph-renderer.html).
- Qt: [Canvas](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html), [QQuickPaintedItem](https://doc.qt.io/qt-6.8/qquickpainteditem.html), [Animator](https://doc.qt.io/qt-6.8/qml-qtquick-animator.html), [compilazione](https://doc.qt.io/qt-6.8/qtqml-qtquick-compiler-tech.html).
- Qt: [QML Profiler](https://doc.qt.io/qtcreator/creator-qml-performance-monitor.html), [debug/logging](https://doc.qt.io/qt-6.8/qtquick-debugging.html).
- [Python 3.13 threading/GIL](https://docs.python.org/3.13/library/threading.html), [NumPy BLAS/thread](https://numpy.org/doc/stable/reference/global_state.html), [GCC 14.2 AArch64](https://gcc.gnu.org/onlinedocs/gcc-14.2.0/gcc/AArch64-Options.html).
- [Linux 6.6 hwcaps ARM64](https://docs.kernel.org/6.6/arch/arm64/elf_hwcaps.html), [CPUFreq](https://docs.kernel.org/6.6/admin-guide/pm/cpufreq.html), [systemd 257 risorse](https://www.freedesktop.org/software/systemd/man/257/systemd.resource-control.html).
- [SDK NPU Vivante/Radxa](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-sdk), [Khronos code Vulkan](https://docs.vulkan.org/guide/latest/queues.html), [sincronizzazione](https://docs.vulkan.org/guide/latest/synchronization.html).
- Imagination: [DDK 25.2](https://blog.imaginationtech.com/driver-update-adds-support-for-vulkan-and-opencl-extensions), [driver open source e hardware supportato](https://developer.imaginationtech.com/solutions/open-source-gpu-driver/).

Il PDF Allwinner e la pagina prodotto Orange Pi non hanno fornito contenuto leggibile attraverso il browser di ricerca in questa sessione; non sostengono nuove specifiche in questo studio. Il riferimento Radxa descrive altri prodotti con lo stesso SoC, senza trasferire automaticamente compatibilità alla nostra immagine.
