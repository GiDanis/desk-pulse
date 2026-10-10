# Resoconto delle prove NPU del 10 ottobre 2026

Provenienza: risultati dei comandi SSH eseguiti nella stessa conversazione prima della redazione dello studio. Gli estratti sotto sono selezionati dai tool output: questo file non è un nuovo log acquisito né una ripetizione del benchmark. Le prove non erano dotate di timestamp esterno per ogni inferenza.

Destinazione verificata: host `orangepizero3w`, kernel `6.6.98-sun60iw2`, dispositivo `/dev/vipcore`, driver `vipcore`. La raccolta successiva [board-inventory.json](board-inventory.json) fissa timestamp Europe/Rome e hash dei file attualmente presenti.

## Runtime

Il kernel riporta VIPLite `2.0.3.5-AW-2026-03-17`. I programmi riportano la libreria `2.0.3.2-AW-2024-08-30`. Nel test `vpm_run`:

```text
vip lite init OK.
cid=0x1000003b, device_count=1
  device[0] core_count=1
```

Il boot contiene anche `Get NPU Regulator Control FAIL!`, seguito da impostazione a 800 mV / 852 MHz e inizializzazione. Le prove completate non determinano la causa o l'effetto di quel messaggio in altre condizioni di carico.

## Modello di prova

Comando remoto, directory `/opt/vpm_run`:

```bash
timeout 12 ./vpm_run -s sample.txt -l 1 -b 1
```

Il bypass evita salvataggio di output e top5. Un'esecuzione, exit code 0. Estratto:

```text
input 0 dim 224 224 3 1
ouput 0 dim 2 1 0 0
memory pool size=1092352byte
create network 0: 2227 us.
prepare network 0: 1078 us.
read input and golden 0: 5103 us.
golden file count=0
run time for this network 0: 3075 us.
profile inference time=2837us, cycle=2403855
vpm run ret=0
```

Input/quantizzazione e nomi tensori sono riportati dal programma. Nessun confronto con un output corretto atteso: si documentano inizializzazione e inferenza riuscita, non accuratezza o riconoscimento di una classe.

## YOLOv5

Eseguito in una directory temporanea privata, eliminata a fine comando, con librerie preinstallate in `/opt/yolov5/lib`:

```bash
LD_LIBRARY_PATH=/opt/yolov5/lib timeout 20 /opt/yolov5/yolov5 \
  /opt/yolov5/model/yolov5.nb /opt/yolov5/input_data/dog.jpg
```

Exit code dell'eseguibile 0. Estratto:

```text
detection num: 3
16: 86%, dog
7: 65%, truck
1: 56%, bicycle
```

Seconda prova, stessa modalità temporanea, dieci iterazioni:

```bash
LD_LIBRARY_PATH=/opt/yolov5/lib timeout 20 /opt/yolov5/yolov5_bench \
  /opt/yolov5/model/yolov5.nb /opt/yolov5/input_data/dog.jpg 10
```

Exit code dell'eseguibile 0. Numeri riportati:

| Voce | Valore |
| --- | ---: |
| Iterazioni valide / warmup | 10 / 0 |
| Input | 640×640, uint8 |
| Media nella riga progressiva | 46,62 ms |
| Media nel riepilogo finale | 41,95 ms |
| Min / max finali | 39,23 / 44,60 ms |
| p50 / p90 / p99 finali | 41,76 / 44,60 / 44,60 ms |
| Throughput dichiarato | 23,8 FPS |

Il sorgente del benchmark non è stato ispezionato: non attribuire questi tempi a una pipeline completa o a una specifica porzione senza una futura verifica. Dieci campioni senza warmup non qualificano code statistiche o prestazioni sostenute.

## Dashboard e risorse

Prima delle inferenze il servizio era già tornato active/running, supervisore PID 27672; lo stesso PID è osservato dopo le prove. `NRestarts=0` nei controlli successivi. Una precedente lettura inattiva, prima dell'inferenza, resta senza attribuzione causale. Non è stata misurata la risposta della GUI o del tastierino durante i test.

Nel controllo finale delle prove: NPU 852 MHz, governor `performance`, temperatura NPU 40,3 °C, CPU circa 42,9–43,5 °C. La nuova raccolta passiva delle 17:02 riporta NPU 39,3 °C e conserva i numeri aggiornati in JSON. Nessuna installazione, modifica del servizio o governor è stata eseguita per questi test.

