# Gioco — scatti Evo, frame pacing e obiettivo 30 fps

13 ottobre 2026 · **Studio iniziale sulla rc.12; seguito F1/F2 implementato e installato nella [rc.13](v09-pacing-optimization-report.md), con gate iniziale Evo/32 superato. I due prototipi iniziali restano non promossi.**

## Risposta alla segnalazione

La segnalazione di scatti con 32 vetture è compatibile con le misure. **La build attuale non dimostra 60 fps fluidi sotto questo carico.** La scheda riesce a disegnare molti frame, ma le posizioni delle auto non arrivano altrettanto regolarmente. Un contatore vicino a 60 non certifica la fluidità del movimento.

Il nuovo obiettivo del Gioco è **30 fps regolari**, conservando tutte le vetture, scala, temi e qualità dei dati. Non è una dichiarazione di impossibilità hardware dei 60 fps. Nemmeno i prototipi 30 Hz qui provati superano ancora il gate di regolarità: non vengono installati come una correzione già riuscita.

## 1. Monitoraggio del carico reale

[Campione grezzo](evidence/v09-evo-frame-pacing-2026-10-13/live-resources.json): 120 s a intervalli di 2 s, processi e thread della GUI/worker, CPU, frequenze, memoria, temperatura, pressione e stato GPU. Letture soltanto: nessun attach, segnale o modifica ai governor. Dentro la finestra il gioco è stato messo in pausa dall’utente.

La [sintesi attiva](evidence/v09-evo-frame-pacing-2026-10-13/live-active-summary.json) usa soltanto 40 s con worker >20% di un core; esclude il supervisor e i campioni in pausa. La prima sintesi mescolava idle/supervisor e non va usata per valutare il carico di Evo.

| Risorsa | Mediana / limite osservato | Interpretazione |
| --- | --- | --- |
| Thread principale GUI | **82% di un core**, massimo 89,6% | Poco margine per pubblicazione dei dati, binding e animazioni. |
| QSGRenderThread | **24,3% di un core** | Lavoro CPU della pipeline grafica; non è tempo GPU. |
| Processo GUI complessivo | **106,7% di un core** | Somma dei thread; non 106% dell’intera CPU a otto core. |
| Worker apprendimento | **90,9% di un core** | Simulazione/raccolta occupano quasi un core. |
| RAM disponibile | **≥5,18 GiB** | Nessuna evidenza di esaurimento RAM/swap nel campione. |
| Temperatura massima | **58,28 °C** | Nessuna evidenza di intervento del limite termico 85 °C del worker. |
| GPU, contatore del fornitore | **4–9%, mediana 8%** nel campione attivo | Non mostra saturazione; definizione/finestra del driver non equivalgono a timer GPU o FPS ottici. |

La CPU complessiva ha ancora core disponibili; GUI e raccolta hanno vincoli di serializzazione. Allocare altra RAM o spostare la piccola rete sulla NPU non risolve automaticamente questi costi. CPU per fisica/training e GPU Qt sono già utilizzate; non si cambiano backend o frequenze in questa analisi.

## 2. Tre cadenze diverse

1. **Fisica:** DT=1/60 s; il passo numerico resta quello qualificato. Non implica 60 passi per secondo reale per ciascuno dei 32 mondi.
2. **Pubblicazione/consumo:** worker invia scene a 25 Hz, GUI interroga la coda nominalmente ogni 33 ms. La fase diversa e ritardi del ciclo producono consegne variabili; la GUI conserva il pacchetto più recente.
3. **Presentazione:** le `NumberAnimation` dei veicoli durano 40 ms e possono disegnare più frame mentre interpolano. Dopo aver raggiunto il punto, l’auto attende il successivo dato. Molti frame possono quindi ripetere una posizione ferma.

Evo aggiorna un episodio per chiamata al trainer; 32 episodi indipendenti vengono percorsi in sequenza. Quando molti tentativi sono attivi, ciascun mondo avanza meno frequentemente. Quando alcuni finiscono, il codice salta il passo di quei mondi e i superstiti possono avanzare più spesso. Questa è una causa verificabile della variazione percepita; il numero di frame grafici non la descrive da solo. Esplorazione/frenata del pilota e stallo dell’episodio rimangono cause diverse.

Nel [campione privato dal checkpoint reale](evidence/v09-evo-frame-pacing-2026-10-13/board/capture.json): **55,46 frame callback/s**, scene circa 24,5 Hz. Per vetture in movimento, nella presentazione Popolazione, nuovi punti: mediana **56,21 ms**, p95 **101,33 ms**, massimo **149,99 ms**. Sono circa 18 nuovi punti/s al valore mediano, variabili fra auto e periodo, non 60. Le soste sotto 0,5 m/s e i tentativi conclusi sono esclusi da questa metrica.

Il trainer privato passa da circa 319.497 a 326.510 transizioni in 35 s, circa 200 transizioni/s aggregate. Con 32 mondi tutti attivi, 60 passi/s ciascuno richiederebbero 1.920 transizioni/s: la richiesta è differente dal disegnare 30 frame/s. Il campione parte a metà generazione, con **32 sagome ma 1–21 tentativi attivi**, e include il passaggio alla valutazione. Non qualifica il peggiore carico di 32 auto tutte in movimento, né ogni pista/metodo.

## 3. Confronto nativo sulla stessa sequenza

Pannello EGLFS **960×640**, Base, dati e provider privati. Copia del checkpoint Evo `6e6ecaa5…`, 319.423 passi, generazione salvata 20/corrente 21, 32 tentativi, 16 neuroni, mutazione manuale 0,15. Originali e parametri conservati.

Registrati 35 s di scene reali del worker privato, poi riprodotti gli stessi pacchetti in ciascun caso. Il replay separa il costo del renderer dalla variabilità del learner; non include un worker concorrente. Non confrontare direttamente la CPU del replay con la CPU totale della sessione live come se tutti i carichi fossero identici.

| Caso, 35 s | Frame callback/s | Mediana intervallo | p95 intervallo | Massimo | GUI principale / render, % di un core |
| --- | ---: | ---: | ---: | ---: | ---: |
| Evo reale ripreso su copia | 55,46 | 16,85 ms | 30,41 ms | 116,78 ms | 58,6 / 42,2 |
| Replay originale, 32 sagome | 49,28 | 19,17 ms | 36,51 ms | 112,82 ms | 66,7 / 34,9 |
| Replay originale, 8 sagome | 56,88 | 18,08 ms | 28,72 ms | 130,39 ms | 54,6 / 25,1 |
| Interpolazione Python a 30 Hz, 32 | 29,26 | 33,33 ms | 51,71 ms | 167,42 ms | 70,2 / 22,6 |
| Clock/interpolazione QML, 32 | 29,03 | 31,71 ms | 64,90 ms | 118,53 ms | 66,5 / 22,4 |

[Evidenze e sintesi](evidence/v09-evo-frame-pacing-2026-10-13/comparison-summary.json). La riga 8 sagome è una **diagnosi**, non una proposta di nascondere tentativi o di ridurre la popolazione. Nel replay vengono mostrati soltanto i primi otto punti degli stessi pacchetti; alcuni erano già conclusi. La sonda delle pose perde i delegate quando il modello passa 32→8, perciò non esiste una metrica valida di movimento per quella riga. Il costo della sonda è diverso: circa 0,04 ms per callback contro 0,37–0,58 ms nei casi 32; parte della differenza di CPU deriva dalla strumentazione.

I prototipi interpolano soltanto tra posizioni reali, senza estrapolare, guidare, cambiare reward o avanzare la fisica. Reset/cambio identità interrompono l’interpolazione. Il primo rinnova tutta la scena Python a ogni tick; il secondo riceve i pacchetti e muove pose nel renderer QML. Il clock QML rimuove anche le animazioni indipendenti di camera/auto. Entrambi sono copie di prova, non codice installato.

Per il primo veicolo osservato nel replay Popolazione, intervallo p95 fra variazioni della posa: originale **91,7 ms**, prototipo Python **41,7 ms**, QML **73,0 ms**. C’è un beneficio sul movimento, ma **non basta**: frame tardivi e costo del thread principale restano. I callback software e le pose degli item QML non sono fotografia del pannello, latenza ottica o durata GPU. Frequenze/governor rimangono quelli ordinari e i campioni brevi non rappresentano un soak.

## 4. Decisione e ottimizzazioni ordinate

**F0 acquisito:** diagnosi del carico reale, cadenze separate, sequenza reale riproducibile e due prototipi 30 Hz. **F1/F2 erano non qualificati al termine di questa matrice iniziale; il seguito rc.13 è documentato sotto.**

| Priorità | Lavoro | Gate |
| --- | --- | --- |
| **F1 · Clock/presentazione** | Un clock di presentazione a 30 Hz, buffer delle ultime pose, interpolazione coerente per auto/camera/sensori; stessa origine temporale per i contatori. Non riavviare animazioni su dati immutati; non bloccare il display su aggiornamento learner/salvataggio. | Tutte le 32 sagome e auto Gara conservate; reset/pause/valutazione riconoscibili, nessuna estrapolazione o dato inventato. Più regolarità senza maggiore costo del thread GUI. |
| **F2 · Dati/scene graph** | Profilare conversione dei contesti e binding QML; aggiornare soltanto ruoli/pose cambiati, conservare oggetti di auto e dati statici, evitare sorting/rivali/bounds delle camere quando non usati. Evitare di riscrivere tutta la scena a 30 Hz; allineare pubblicazione, consumo e presentazione. | Riduzione del carico del thread principale e dei frame tardivi sulla stessa sequenza, poi con learner concorrente; tre temi, ovale/tecnico/Varano, sensori, menu e pause. |
| **F3 · Raccolta** | Profilare fisica/osservazioni/reward e sperimentare batch numerici di mondi compatibili; mantenere episodi/rivali/RNG distinti e budget equi. Il collector multiprocesso precedente non è selezionato senza nuova evidenza. | Snapshot/reward/azioni/RNG e ripresa numericamente verificati; guadagno misurato su 32 mondi attivi, pause rapide. Nessuna scorciatoia a 30 Hz nella fisica per inseguire gli FPS. |
| **F4 · Qualifica** | Training reale, tutte le auto inizialmente attive, cambi generazione, optimizer/valutazione/ripasso, salvataggio, notifiche e uso prolungato; accettazione visiva sul pannello. | Pubblicare media, p50/p95/p99, stalli e frame mancati. 60 fps restano un’eventuale estensione, non la promessa corrente del Gioco. |

Gate iniziale proposto per **30 regolari**: budget 33,33 ms, p95 ≤50 ms, p99 ≤66,67 ms e nessuna pausa grafica >100 ms nel periodo di movimento continuo, con attività/bordi delle finestre registrati. Separare fine episodio, cambio scenario e sosta decisa dal pilota da ritardi del renderer; anche quei passaggi devono avere feedback coerente. Non cancellare i valori massimi dai report. I prototipi attuali mancano già il p95 e/o il limite degli stalli; serve F2 insieme a F1.

## 5. Conservazione e stato finale

[Ricevuta matrice](evidence/v09-evo-frame-pacing-2026-10-13/board/native-matrix-receipt.json) e [prova QML](evidence/v09-evo-frame-pacing-2026-10-13/board/qml30-receipt.json): archivi dei piloti invariati durante le prove private, checkpoint reale conservato; nessun prototipo installato. La sessione messa in pausa viene chiusa ordinatamente durante la manutenzione, conservando il salvataggio. Servizio normale riattivato, NRestarts=0. Runtime rc.12 e preferenze restano quelli di partenza.

Sonde iniziali corrette: guardia multiprocessing mancante, attesa dei delegate e un SIGSEGV della lettura su segnale di animazione. La misura riuscita usa un timer sul thread GUI e il loop già utilizzato dal harness; costo della sonda registrato, letture dei delegate invalidati escluse. Il crash isolato non è considerato un risultato di prestazioni della Dashboard. I file diagnostici non entrano nel pacchetto runtime.

## 6. Seguito implementato — rc.13

[Consegna, prove e limiti rc.13](v09-pacing-optimization-report.md): input scene separato dal contesto statico, delegate conservati, clock monotono 30 Hz, buffer di campioni e camera/sensori coerenti. Buffer Popolazione 200 ms, Gara/preview 120 ms; niente estrapolazione. Pubblicazione 30 Hz, passo fisico 1/60 s conservato. Calcoli geometrici di contatto preparati solo quando necessari, con parità numerica verificata.

Pacchetto finale, prova privata inizialmente a 32 attivi, 35 s: 30,00 callback/s, p95 frame 43,73 ms, p99 46,59 ms, massimo 91,26 ms. Peggiore p95 di movimento 44,17 ms, massimo 87,43 ms; zero pause >100 ms. Gate iniziale superato nel carico provato. Tre temi/gare 2/4 verificati e dati originali conservati; 584 hash, Base attivo, NRestarts=0.

**F1/F2 consegnati nel perimetro dichiarato; F3 completo e F4 esteso restano aperti.** Il replay iniziale del seguito migliora carico GUI/movimento ma non il p95 dei frame: conservato nei risultati, non assimilato al campione live finale. Restano optimizer/topologie maturi, notifiche concorrenti, transizioni/salvataggi prolungati e controllo ottico/input fisico. Il target non è certificato per ogni scenario futuro.
