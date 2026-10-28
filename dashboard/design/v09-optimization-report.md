# v0.9.0-rc.10 · ottimizzazione CPU, scene, GPU e buffer

**13 ottobre 2026 · implementata e installata; perimetro PC/ARM/EGLFS verificato.** Seguito dell’[audit rc.9](v09-resource-optimization-analysis.md). [Evidenze](evidence/v09-optimization-2026-10-13/). Theme API 2.10/68 superfici invariata; pacchetto 575 file. Parametri dei piloti, f1-2/f2-1, reward, sensori 32/42/68, policy e criteri di qualifica conservati.

## 1. Modifiche

- **R0 · Sensori:** un solo calcolo dei raggi frontali, con la portata dello schema richiesto. Cache di osservazioni e coordinate moderne, con chiavi degli array osservati, protezione delle copie restituite e verifica di modifiche dirette a stato/active/accelerazione/timer. Coordinate con hint cache solo dopo stabilizzazione del segmento. Punti anticipati e curvature raggruppati; kernel legacy conservato.
- **R1 · Preview e ritmi:** un solo passo fisico della preview tra i controlli dei comandi, con backlog limitato; l’invio della scena legge lo stato pronto. Policy della preview congelata brevemente e aggiornata a 25 Hz, distinta da learner/valutazione. Scadenza delle scene indipendente da quella della fisica: Gara/Campione/Prova continuano a 60 passi/s senza il precedente arrotondamento a tre tick che produceva circa 20 scene/s. Nessun salto di passo fisico per raggiungere gli FPS.
- **R2 · RAM:** inflight e rollout PPO in array posseduti e riutilizzati; flat/minibatch e indici di shuffle numerici, dataset Clone con copie numeriche. Conversione in liste al checkpoint; formato JSON leggibile e ripresa dei checkpoint precedenti conservati. Nessuna conversione globale float32 né cambio di algoritmo/ordine RNG.
- **R3 · Collector:** backend sperimentale di 2–4 processi per gli ambienti dello stesso pilota, con risultati ordinati, rivali congelati, Pausa che attende la fine del batch, pending serializzabile e chiusura dei figli. Verificato per Evoluzione/NEAT/PPO/Clone. **Default disattivato:** nei compiti piccoli provati non migliora il throughput e peggiora le scene; nessuna nuova opzione del pilota o rotazione della rosa. Il runtime ordinario mantiene il percorso singolo più veloce.
- **R4 · Grafica/riferimenti:** raggi come pochi elementi geometrici del scene graph, evitando il Canvas di tutta l’arena e i relativi caricamenti di texture. [Motivazione Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html). Gare dei riferimenti geometrici con calcolo comune dei controlli; niente osservazioni neurali inutilizzate. Le reti continuano a ricevere tutti i sensori. Grafico dei progressi resta Canvas, aggiornato sui punti visibili e non a ogni scena.
- **R5 · NPU:** esportatore e programma diagnostico aggiornati per dimensione reale degli ingressi/batch e FP16/FP32. Nuova prova nativa della rete congelata 68→16→2; CPU ancora scelta. Niente nuovo backend NPU dichiarato attivo nel gioco, niente modifica ai governor.

La preview può differire temporalmente dal percorso precedente, perché l’avanzamento è distribuito e la policy viene trattenuta fra brevi aggiornamenti. Non viene usata per learning, promozioni o qualifiche; le equazioni, DT e comandi dei mondi autorevoli sono conservati.

## 2. Prestazioni sulla scheda

Worker privati concorrenti alla Home installata, codice candidato, stesso protocollo di 18 s e popolazione 32. Non sono FPS della pista renderizzata o confronto di qualità dell’apprendimento.

| Caso | Rc.9 | Rc.10 scelta | Limite |
| --- | ---: | ---: | --- |
| Scene Impara | 11,32 Hz | **25,07 Hz** | Coda IPC, nuova preview e deadline; finestra breve. |
| Scene Gara 4 | 18,11 Hz | **25,11 Hz** | Riferimenti congelati, circuito tecnico. |
| Pausa worker Impara | 115,49 ms | **1,11 ms** | Ack IPC nella prova, non latenza USB/ottica. |
| Pausa worker Gara | 9,91 ms | **9,29 ms** | Differenze piccole, nessun guadagno generale attribuito. |
| Training, prima ottimizzazione | circa 1.623 transizioni in 18 s | circa 3.807–3.835 nuove in 18 s | Compito Partenza; budget breve, niente qualifica della convergenza. |

[Prima](evidence/v09-resource-audit-2026-10-13/board-profile.json), [dopo deadline](evidence/v09-optimization-2026-10-13/paced-board.json), [primo seguito numerico](evidence/v09-optimization-2026-10-13/first-board.json).

Profilazione equivalente della raccolta (6 s/caso, overhead di cProfile): Evoluzione/NEAT/PPO/PPO-Smooth da circa 128–131 a 251–259 transizioni/s; Clone da 114 a 210; Sorpasso Varano da 96 a 171; Gara 4 Varano da 66 a 115. Sono campioni iniziali; non descrivono optimizer maturi/topologie NEAT cresciute. I JSON conservano numeri e distribuzione dei tempi.

**Prova R3:** due collector, Partenza, 18 s: circa 3.700 transizioni contro circa 3.835 del percorso singolo; scene **16,88 Hz contro 23,05 Hz** prima della correzione finale delle deadline. Serializzazione/ripristino dei piccoli mondi e IPC annullano il parallelismo nel caso provato. Il confronto decide il default; non dimostra che i collector siano inutili per ogni futuro carico. [Risultati](evidence/v09-optimization-2026-10-13/pool-board.json).

## 3. NPU: nuova misura

Stessa policy PPO-Smooth congelata proveniente dalla prova isolata rc.9, hash `58d76cf9…`, 68 ingressi, 16 neuroni nascosti, 2 uscite. 512 batch per taglia, 512/2.048/16.384 vettori. Modelli compilati per `VIP9000NANODI_PID0X1000003B`, via ACUITY 6.30.22. [Workflow del fornitore](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-usage).

| Batch | CPU mediana | NPU mediana completa | Massimo errore azioni |
| --- | ---: | ---: | ---: |
| 1 | **43,67 µs** | 61,33 µs | 0,000327 |
| 4 | **50,29 µs** | 86,31 µs | 0,000393 |
| 32 | **97,96 µs** | 116,04 µs | 0,000479 |

La NPU usa FP16 I/O/interno; il programma include conversioni dal/al file float32, copie, flush, esecuzione e readback nei tempi. La policy CPU mantiene float64. Soglia della prova numerica 0,002; errori osservati <0,0005. Caricamento iniziale circa 3,4–4,5 ms. [Dati](evidence/v09-optimization-2026-10-13/board/npu/runtime-choice.json).

CPU più rapida in tutti i tre campioni, prima ancora dei costi per aggiornare/ricompilare i pesi. La verifica non certifica guida NPU a ciclo chiuso, più modelli distinti, training NPU o risparmio energetico. Il dominio NPU/governor restano invariati; energia/runtime PM richiedono misure proprie. I primi tentativi di conversione hanno corretto il target `--optimize` e il volume di output; un primo batch4 fallito è stato rigenerato con successo. Solo i binari finali entrano nel confronto.

## 4. Correttezza e ripresa

**64 controlli PC superati** nel giro finale: core, curriculum, Accademia, circuiti e sei gate aggiuntivi di ottimizzazione. [Log](evidence/v09-optimization-2026-10-13/release-regression.txt).

- Parità esatta delle osservazioni 32/42/68 e degli snapshot fisici rispetto al sorgente rc.9, quattro circuiti, f1-2/f2-1, più vetture e ripristino.
- Cache invalidate dalle modifiche dirette osservate; array restituiti modificabili senza alterare la cache interna.
- PPO: stesso campionamento/likelihood, rollout, gradienti/optimizer e RNG; ripresa a metà aggiornamento identica al runtime precedente.
- Clone: stesso ordine/esempi/gradiente/RNG e checkpoint, eliminando solo rappresentazioni intermedie.
- Collector: parità dei batch autorevoli, ordine di risultati e RNG; checkpoint con batch in volo riprendibile sul percorso seriale.
- Griglia dei riferimenti: controlli e snapshot identici alla valutazione per singola auto, quattro circuiti e due versioni fisiche.

La prima regressione PC ha incontrato una quota di `/tmp`, non un errore del codice. Temporanei spostati su disco; controlli rieseguiti. Backup dei sorgenti pre-modifica e manifest conservati nelle evidenze; modifiche manuali esistenti preservate.

## 5. UI e consegna

Perimetro EGLFS 960×640: Base/NEAT, Functional/Clone, Apple/PPO-Smooth su Varano a scala 1,1 e 30 s di uso; impostazioni notturne, dossier e quattro camere/raggi geometrici. Nei casi completati nessun warning QML o traceback Python. Immagini native dei raggi ispezionate; proporzioni, temi e comandi conservati.

Walkthrough Apple/PPO-Smooth: mediana software `frameSwapped` **16,64 ms**, p95 **22,12 ms** contro 17,20/37,05 ms della rc.9. Il soak passa da 15 a 30 s e il training raggiunge più passi: confronto indicativo, non matrice perfettamente A/B. Massimo sull’intero walkthrough **858 ms**, comprensivo di avvio/navigazione/salvataggi; non nascosto come frame pacing continuo.

Riferimento mobile Varano, 20 s: mediana **17,12 ms**, p95 **34,53 ms**, massimo **46,55 ms**, progresso **344 m**. Non mostra un miglioramento generale del riferimento rispetto alla mediana 16,71 ms storica; distinta dal recupero del target delle scene. Nessuna garanzia di 60 FPS costanti o latenza ottica/USB.

Tutti e sei i checkpoint di produzione verificati nelle copie: archivi e parametri precedenti conservati, Pausa/Salvato/ripresa, originali invariati. Ack IPC circa 1,3–3,7 ms nella prova. [Risultati](evidence/v09-optimization-2026-10-13/board/production-checkpoints-copy.json).

Backup completo del runtime/configurazione/dati prima delle prove, con 1.218 artefatti immutabili collegati al backup precedente dopo verifica dell’hash: nessuna duplicazione di 800 MiB di pesi sulla SD. Directory del backup privata; SQLite corrente copiato, nessun ripristino del vecchio journal. [Backup](evidence/v09-optimization-2026-10-13/board/backup.json).

Gare native complete: 2 e 4 riferimenti congelati, tre giri sul circuito tecnico, tutti arrivati e zero respawn; modelli invariati. Sono prove del motore e della UI, non qualifica dei piloti neurali dell’utente. [Gare](evidence/v09-optimization-2026-10-13/board/new-races/report.json).

Sei gate di parità/replay dell’ottimizzazione superati anche su ARM in 38,96 s, senza skip. Installazione **rc.10 / 575 file**, hash conformi, Base attivo, preferenze conservate, servizio active e `NRestarts=0`. **Tutte le tabelle del gioco, tutte le colonne dei sei piloti e i 1.218 artefatti sono identici al baseline corrente rc.9.** Nessuna nuova correzione di sessione/migrazione/allenamento degli originali effettuata durante la consegna. [Manifest](evidence/v09-optimization-2026-10-13/release-manifest.json), [ricevuta finale](evidence/v09-optimization-2026-10-13/board/final-receipt.json).

Avvio dell’app installata con servizi e dati reali sotto manutenzione: cattura dopo heartbeat coerente del PID corrente, nessun Start implicito del gioco, ritorno al servizio normale con nuova verifica dei dati. [Avvio](evidence/v09-optimization-2026-10-13/board/full-startup.json), [immagine](evidence/v09-optimization-2026-10-13/board/full-startup-screen.png), [stato finale](evidence/v09-optimization-2026-10-13/board/final-health.json). La cattura non è una fotografia del pannello o della successiva istanza systemd. Stesso boot ID; **nessun nuovo reboot OS**. Rollback runtime rc.9 disponibile in `/opt/smartpc/dashboard-rc9-before-optimization`.

## 6. Residui

Carichi maturi/soak prolungato, più seed di apprendimento, carico grafico/CPU per thread completo, GPU busy attendibile, energia NPU, lettura/input fisici e FPS ottici restano distinti. I collector richiedono un nuovo confronto su carichi maggiori prima di selezionarli; modelli grandi/visivi NPU richiedono qualifiche proprie. Non si aumenta la popolazione, non si cambiano i neuroni, non si riduce il numero di sensori e non si forza la frequenza della GPU per ottenere questi risultati.
