# Studio e Analisi di Ottimizzazione della Fluidità e delle Prestazioni (v0.9.x)

> **Rettifica del 21 ottobre 2026:** la descrizione hardware T527 / quattro Cortex-A55 / Mali-G57 riportata sotto non corrisponde alla scheda interrogata negli audit successivi. L'inventario attuale espone il profilo A733, sei Cortex-A55 più due Cortex-A76 e GPU PowerVR BXM-4-64; hostname e device tree non certificano da soli l'etichetta commerciale fisica. Per decisioni hardware/driver e nuova baseline usare lo [studio v0.9.3](v093-dashboard-performance-study.md) e le relative evidenze. Questo documento conserva ipotesi e misure storiche: non rappresenta lo stato corrente rc.28 e non certifica utilizzo GPU/NPU o FPS fisici.

> **Avvertenza del 13 ottobre:** il seguente studio storico contiene un’identificazione hardware errata (T527/quattro A55/Mali). Non descrive la baseline rc.9 e non dimostra contesa DRAM o saturazione GPU nella build corrente. Fare riferimento all’[audit risorse aggiornato](v09-resource-optimization-analysis.md), con misure A55/A76/PowerVR e limiti espliciti. Le proposte già implementate non sono nuovi lavori aperti.

**Data:** 11 ottobre 2026 · **Target:** Orange Pi Zero 3W (Allwinner T527 / sun60iw2, 4× Cortex-A55 @ 1,4–1,8 GHz, Mali-G57 EGLFS KMS, display Hagibis 960×640@60Hz, tastierino 3×3 USB).  
**Stato baseline:** Debian 13 Trixie, v0.9.0-rc.5, Theme Engine 2.8 (67 superfici, tema attivo `studio.applecalm` v1.2.0).

---

## 1. Obiettivo dello Studio

Valutare, misurare e confermare in modo rigoroso le cause dei cali di fluidità e dell'elevato consumo di CPU riscontrati sul sistema, con particolare attenzione alle interazioni tra l'interfaccia QML (`app.py`), il motore di simulazione e apprendimento concorrente (`game_worker.py`) e lo strato del sistema operativo Linux.

L'analisi risponde alla domanda di prodotto: **perché il sistema evidenzia latenze e cali di fluidità durante l'uso, e quali interventi garantiscono 60 FPS stabili e risposta immediata ai tasti?**

---

## 2. Evidenze Empiriche Rilevate sulla Scheda Reale (`192.168.1.179`)

La scheda è stata esaminata in due condizioni operative distinte: durante una sessione attiva di apprendimento (`impara`) e in condizione di riposo (dashboard sulla vista `oggi`).

### Tabella 1: Confronto Carico di Sistema e Processi

| Metrica | In Addestramento Gioco (23:42–23:47) | A Riposo / Dashboard Home (23:54) | Variazione |
|---|---:|---:|---:|
| **Load Average (1m, 5m, 15m)** | **2,44 · 2,17 · 1,87** | **1,19 · 1,70 · 1,77** | Calo immediato verso 0,2–0,4 |
| **`app.py` CPU totale** | **45,5% – 84,6%** | **0,0% – 10,0%** | **−75% – −85% CPU** |
| `app.py` thread GUI (LWP 70737) | 37,8% | ~0,1% – 5,0% | Rientro nella norma |
| `app.py` `QSGRenderThread` (LWP 70753) | 8,9% (continuo a 60 FPS) | ~0,0% (sleep) | **Inattivo a riposo** |
| **`game_worker.py` CPU** | **92,3% – 98,0%** (1 core intero) | 0% (processo terminato) | −100% di 1 core |
| **`plymouthd` (OS splash)** | **4,0%** (13 min accumulati) | 0% (ucciso manualmente) | **−4,0% permanente** |
| **Memoria RAM resident (RSS)** | 362 MiB GUI + 140 MiB Worker | 229 MiB GUI | −273 MiB liberati |

Questa misurazione stabilisce in modo inequivocabile che:
1. **La dashboard da sola, a riposo, è efficiente:** consuma meno del 10% di CPU, con `QSGRenderThread` che dorme correttamente quando lo Scene Graph non è sporcato.
2. **L'attivazione del dominio Gioco innesca un consumo cumulativo anomalo (oltre il 170% di CPU):** il thread grafico viene bombardato di notifiche e ridipinture forzate a 60 FPS, mentre il worker monopolizza un core e contende il bus di memoria DRAM/cache L2 con la GPU Mali.

---

## 3. Validazione Delle Singole Ipotesi di Ottimizzazione

### Ipotesi H1: Invalidazione Continua dello Scene Graph e Clear CPU del Canvas 2D
* **Riferimento:** [`dashboard/presentations/GameVisual.qml:159-173`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/presentations/GameVisual.qml#L159-L173) e [`dashboard/presentations/GameVisual.qml:241-253`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/presentations/GameVisual.qml#L241-L253).
* **Diagnosi nel codice:**
  ```qml
  Canvas {
      id: sensors
      anchors.fill: parent
      visible: root.g.display === "sensori" && root.cars.length > 0
      onVisibleChanged: requestPaint()
      Connections { target: root; function onSceneChanged() { sensors.requestPaint() } }
      onPaint: {
          const c = getContext("2d");
          c.clearRect(0, 0, width, height);
          if (!visible) return;
          ...
      }
  }
  ```
  1. `Connections` invoca `sensors.requestPaint()` ad **ogni fotogramma** generato (25 volte/s), indipendentemente dal valore di `visible` (la modalità predefinita all'avvio è `"tutte"`, quindi `visible` è quasi sempre `false`).
  2. La chiamata `requestPaint()` marca l'elemento come *dirty* nell'albero QSG di Qt. Di conseguenza, il thread `QSGRenderThread` non può dormire e sveglia la pipeline di composizione a ogni frame (spiegando gli 8,9% di CPU continui del render thread).
  3. All'esecuzione di `onPaint`, `getContext("2d")` e `c.clearRect(0, 0, width, height)` vengono invocati **prima** di controllare `if (!visible) return`. Viene quindi allocato e ripulito su CPU un buffer di 960×584 pixel a vuoto.
  4. Identico comportamento si riscontra nel Canvas del grafico [`plot`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/presentations/GameVisual.qml#L241).
* **Esito:** **CONFERMATO.**
* **Intervento correttivo:**
  - Nel connettore: `function onSceneChanged() { if (sensors.visible) sensors.requestPaint() }`.
  - In `onPaint`: `if (!visible) return;` come prima riga tassativa, prima di `getContext("2d")` e `clearRect`.

---

### Ipotesi H2: Esecuzione di 24 `NumberAnimation` Simultanee anche con Vetture Nascoste
* **Riferimento:** [`dashboard/presentations/GameVisual.qml:148-150`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/presentations/GameVisual.qml#L148-L150).
* **Diagnosi nel codice:**
  Le 8 vetture nel `Repeater` contengono:
  ```qml
  Behavior on px { enabled: car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration: 40; easing.type: Easing.Linear } }
  Behavior on py { enabled: car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration: 40; easing.type: Easing.Linear } }
  Behavior on angle { enabled: car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"; NumberAnimation { duration: 40; easing.type: Easing.Linear } }
  ```
  1. La condizione `enabled` **non include `car.visible`**.
  2. Quando l'utente seleziona la modalità di vista `"solo"` (o quando la schermata pista è in secondo piano), 7 delle 8 auto hanno `visible: false`.
  3. Ciononostante, ad ogni pacchetto inviato dal worker, le coordinate `px`, `py`, `angle` di tutte le 8 vetture cambiano, avviando 24 animazioni `NumberAnimation` nel motore di animazione QtQuick.
  4. La prova di micro-benchmark eseguita sulla scheda (`study_results.json`) ha confermato che il costo di aggiornamento di 24 animazioni attive rispetto a 3 è di **3,88 ms vs 2,76 ms** per ciclo (~29% di riduzione immediata).
* **Esito:** **CONFERMATO.**
* **Intervento correttivo:**
  Estendere la condizione di abilitazione con `car.visible`:
  `enabled: car.visible && car.smooth && root.g.runState === "running" && root.ctx.motionPolicy.mode === "normal"`.

---

### Ipotesi H3: Bug di Calcolo Priorità del Processo Worker (`Nice 0` anziché Nice Basso)
* **Riferimento:** [`dashboard/game_worker.py:16-19`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/game_worker.py#L16-L19).
* **Diagnosi nel codice:**
  All'inizio di `worker_main`:
  ```python
  try:
      os.nice(5)
  except OSError:
      pass
  ```
  1. Il servizio systemd `smartpc-dashboard.service` avvia `app.py` con `Nice=-5` (alta priorità per garantire la fluidità del kiosk).
  2. Su Linux, la syscall `nice(inc)` aggiunge `inc` al valore di priorità corrente del processo.
  3. Di conseguenza: **`-5 + 5 = 0`**.
  4. L'ispezione empirica sulla scheda tramite `ps -o pid,ni,pri,comm -p 70737,73784` ha confermato:
     ```text
       PID  NI PRI COMMAND
     70737  -5  24 python
     73784   0  19 python
     ```
  5. Il worker non girava affatto come processo di sfondo a bassa priorità (Nice +10/+15), bensì a **Nice 0**, competendo ad armi pari per i tempi di CPU con l'intero sistema operativo.
* **Esito:** **CONFERMATO.**
* **Intervento correttivo:**
  Impostare esplicitamente la priorità assoluta di background:
  ```python
  try:
      os.setpriority(os.PRIO_PROCESS, 0, 10)
  except OSError:
      try:
          os.nice(15)
      except OSError:
          pass
  ```

---

### Ipotesi H4: Loop di Addestramento del Worker Senza Pacing (Saturazione 100% CPU)
* **Riferimento:** [`dashboard/game_worker.py:318-350`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/game_worker.py#L318-L350).
* **Diagnosi nel codice:**
  Nel blocco `mode == 'impara'`:
  - `World.step()`, `learner.act()` e `learner.sample()` vengono eseguiti in un ciclo continuo `while not stopping:` senza alcun vincolo temporale.
  - Al contrario di `mode == 'gara'`, dove alle righe 399–400 è presente il pacing a `DT` (`remaining = DT - (monotonic - started); command.poll(remaining)`), in `impara` la CPU è costretta a girare al 100%.
  - Un core Cortex-A55 interamente saturato da continue moltiplicazioni matriciali NumPy e allocazioni genera contesa sul bus DRAM con la GPU Mali, provocando frame drop e ritardi negli eventi di input.
* **Esito:** **CONFERMATO.**
* **Intervento correttivo:**
  Introdurre un micro-yielding nel loop di addestramento: permettere un breve respiro (es. yielding cooperativo o target di passi fisici commisurato alla frequenza della GUI) in modo che il worker rilasci i timeslice e non saturi il processore.

---

### Ipotesi H5: Disallineamento Frequenza di Polling (16 ms vs 40 ms) e Marshalling Shiboken
* **Riferimento:** [`dashboard/game.py:55-57`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/game.py#L55-L57) e [`dashboard/game.py:369-398`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/game.py#L369-L398).
* **Diagnosi nel codice:**
  1. `self._timer.setInterval(16)`: `_poll()` viene eseguito 60 volte al secondo (ogni 16 ms).
  2. Il worker invia fotogrammi solo ogni 40 ms (`if time.monotonic() - last_frame >= 1/25: send_frame()`).
  3. L'ispezione GDB ha mostrato che le letture di `self.scene` da QML innescano conversioni profonde tramite `Shiboken::Conversions::getConverter` di un dizionario con 8 auto, array float e metadati.
  4. Inoltre, quando il gioco è in pausa, il timer continua a girare a 16 ms senza motivo.
  5. Se l'utente si sposta sulle schermate secondarie (*Classifica*, *Progressi*, *Dossier*), `gameService` continua a emettere `sceneChanged` a 25 Hz anche se la pista 2D non è visualizzata a schermo.
* **Esito:** **CONFERMATO.**
* **Intervento correttivo:**
  - Portare il timer di polling a **33 ms** (30 Hz) durante l'esecuzione e a **250 ms** quando in pausa.
  - Sopprimere o ridurre l'emissione di `sceneChanged` quando la vista attiva non è `game.track`.

---

### Ipotesi H6: Processo Plymouth Persistente a Livello OS
* **Riferimento:** [`os/system/smartpc-dashboard.service`](file:///home/giuseppe/Documenti/Workspace/SmartPC/os/system/smartpc-dashboard.service) e `/usr/sbin/plymouthd`.
* **Diagnosi nel sistema:**
  1. Sulla scheda reale, `plymouthd --mode=boot` (PID 219) era attivo ininterrottamente da 5 ore e 23 minuti, consumando il **4,0% di CPU fisso** e mantenendo un task attivo (`plymouth-quit-wait.service`).
  2. Nessun servizio del target di avvio richiamava la terminazione dello splash screen una volta presa in carico la GPU da EGLFS KMS.
  3. L'esecuzione di `sudo plymouth quit` ha chiuso immediatamente il demone e rilasciato la CPU.
* **Esito:** **CONFERMATO E VERIFICATO.**
* **Intervento correttivo:**
  Aggiungere `ExecStartPre=-/usr/bin/plymouth quit` nel file di servizio systemd [`smartpc-dashboard.service`](file:///home/giuseppe/Documenti/Workspace/SmartPC/os/system/smartpc-dashboard.service).

---

## 4. Matrice di Sintesi e Piano Operativo

| ID | Ottimizzazione | File Coinvolti | Rischio | Impatto sulla Fluidità |
|---|---|---|---|---|
| **OPT-1** | Guardare `requestPaint()` con `visible` e anticipare `if (!visible) return` nei Canvas 2D | [`GameVisual.qml`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/presentations/GameVisual.qml) | Nullo (trasparente) | **Altissimo:** elimina wake-up continui di `QSGRenderThread` e clear CPU a vuoto |
| **OPT-2** | Condizionare i `Behavior` di animazione a `car.visible` | [`GameVisual.qml`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/presentations/GameVisual.qml) | Nullo | **Medio-Alto:** −21 animazioni attive in modalità `"solo"` |
| **OPT-3** | Priorità reale `os.setpriority(..., 10)` nel worker | [`game_worker.py`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/game_worker.py) | Nullo | **Alto:** il kernel concede sempre precedenza alla GUI |
| **OPT-4** | Micro-pacing cooperativo nel loop `impara` | [`game_worker.py`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/game_worker.py) | Basso | **Altissimo:** sblocca risorse di memoria e termiche della scheda |
| **OPT-5** | Timer di poll commisurato (33 ms / 250 ms) e throttling viste | [`game.py`](file:///home/giuseppe/Documenti/Workspace/SmartPC/dashboard/game.py) | Basso | **Medio:** riduce l'overhead Shiboken nel thread Python |
| **OPT-6** | Uscita automatica di Plymouth al boot del kiosk | [`smartpc-dashboard.service`](file:///home/giuseppe/Documenti/Workspace/SmartPC/os/system/smartpc-dashboard.service) | Nullo | **Immediato:** recupera il 4% di CPU OS permanente |

Tutte le 6 ipotesi sono state verificate e confermate con evidenze numeriche e tracciati di sistema.
