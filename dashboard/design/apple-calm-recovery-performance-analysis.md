# Apple Calm · recupero, gestione dei temi e prestazioni

**Revisione 1 · 15 ottobre 2026 · Europe/Rome.**

**Stato: analisi preparatoria. Nessun fix implementato, tema riattivato, pacchetto installato o servizio riavviato durante questo audit.** Modifiche limitate alla documentazione e alle evidenze locali. Baseline letta dalla board: **0.9.0-rc.18**, 606 hash conformi, Theme API 2.11/68 superfici; Base attivo, Apple Calm 1.6.2 installato ma in quarantena. La dicitura utente «v0.9.1» non identifica il runtime verificato e non viene assegnata a una futura release da questo studio.


**Seguito del 16 ottobre:** il piano è stato attuato nella rc.19 / Apple 1.6.3; [report, ricevuta e limiti di qualifica](apple-calm-recovery-performance-report.md). Le osservazioni e lo stato preparatorio qui sopra descrivono l’audit precedente all’implementazione.

## 1. Obiettivo e perimetro

Preparare un intervento che renda Apple Calm nuovamente selezionabile dopo una verifica controllata, renda comprensibili gli errori dei temi e riduca il lavoro non necessario della dashboard conservando grafica, colori, font, icone, geometrie approvate e funzioni esistenti.

Il tema comprende pagine, shell, avvisi, grafici e transizioni. Il piano riguarda anche i percorsi comuni che ne determinano stabilità e costo: supervisore, catalogo, lifecycle, contesti Python/QML, cache e dati. Non modifica fisica, apprendimento o parametri dei piloti. GPU compute, NPU, governor e affinità restano esperimenti condizionati a un beneficio misurato, senza nuove dipendenze di produzione presupposte.

## 2. Evidenze e grado di certezza

La [fotografia della board](evidence/apple-calm-recovery-performance-2026-10-15/board-readonly-snapshot.json) conserva data UTC di acquisizione, manifest, servizio, identità installata, quarantena ed eventi di recupero. I timestamp qui sotto sono convertiti in Europe/Rome. È una lettura di stato, non una prova funzionale di Apple Calm.

| Riscontro | Esito | Limite |
| --- | --- | --- |
| Runtime | 0.9.0-rc.18, 606 file, nessuna differenza SHA-256 | Non è una nuova qualifica completa della release |
| Servizio | active, MainPID 107039, NRestarts=0 nell'audit | MainPID è il supervisore; NRestarts=0 non cancella i crash storici |
| Tema attivo | Base, nessuna attivazione pendente | Non significa Apple attivo o selezionabile |
| Bundle Apple | 1.6.2, digest `29f17b2dcf54ae37024426b1f3a9d6177f62d7c930ab26308d2381b8cc8cd8d4` | Pacchetto presente non equivale a runtime funzionante |
| Quarantena | `processo GUI terminato con codice -11`, failures=1 nel marker | SIGSEGV della GUI, causa originaria non attribuita |
| Elenco revisioni, verifica precedente nella stessa sessione | Nessun bundle selezionabile; Apple compare includendo quarantena | Base/Functional appartengono anche al catalogo incorporato: non è «nessun tema installato» |
| Stack del crash | Non disponibile nell'ispezione | Journal della finestra vuoto, `coredumpctl` assente; nessun simbolo o debugger installato |

Eventi significativi del journal applicativo:

- 10 ottobre, 18:54:16: SIGSEGV con Apple Calm; 18:55:02: SIGSEGV anche con Base. Successivi errori di permessi del journal sono storici e non dimostrano un problema di permessi attuale.
- 11 ottobre, 16:28:13: `Timeout caricamento studio.applecalm.noticeurgent`.
- 11 ottobre, 23:54:01: uscita GUI -11 con Apple; marker di quarantena modificato alle 23:54:00 circa. La piccola differenza deriva da file/evento distinti e non cambia l'ordine operativo.
- 12 ottobre, 19:50:58 e 20:13:52: startup/readiness timeout con Base.

Il marker conserva soltanto un conteggio e un motivo; non rappresenta tutta la sequenza storica. `lastRecovery=null` nel journal corrente non annulla il marker persistente. Le prove EGLFS Apple delle consegne precedenti restano valide per i loro ambienti e percorsi, ma non attestano la selezionabilità nella configurazione di produzione attuale.

## 3. Diagnosi: perché Apple Calm scompare

La catena è verificabile nei sorgenti:

1. [theme_supervisor.py](../theme_supervisor.py), `supervise`: un'uscita GUI non richiesta, o un timeout, chiama `recover(..., failed_active=True)`.
2. [theme_lifecycle.py](../theme_lifecycle.py), `recover`: identifica candidata/tema attivo, scrive il marker di quarantena e sceglie precedente o Base. Non contiene una prova che il tema abbia causato il crash.
3. [theme_bundle.py](../theme_bundle.py), `list_revisions`: per impostazione predefinita esclude le revisioni in quarantena; gli errori di verifica vengono saltati.
4. [theme_runtime.py](../theme_runtime.py), `make_catalog`: costruisce il catalogo eseguibile dalle revisioni ammesse.
5. [theme_service.py](../theme_service.py), proprietà `themes`, e [SettingsPanel.qml](../SettingsPanel.qml): presentano il catalogo risultante, senza una riga per il bundle bloccato.

**Causa della scomparsa accertata: esclusione della revisione in quarantena. Causa del SIGSEGV ancora aperta.** Crash con Base e timeout di un renderer Apple suggeriscono più percorsi da indagare, non una causa unica già provata. Non attribuire il problema a saturazione GPU, NPU inutilizzata, RAM o incompatibilità API senza evidenza specifica.

## 4. Comportamento di prodotto da implementare

Separare l'inventario amministrativo dei temi dal catalogo dei renderer eseguibili. Una revisione bloccata deve essere descrivibile senza caricarne QML, font, animazioni o risorse. La validazione dei descrittori rimane limitata e tollera errori mostrando una diagnosi; nessun rendering del bundle per costruire la lista.

| Stato mostrato | Selezione e azioni |
| --- | --- |
| Disponibile | Selezionabile attraverso l'attuale attivazione con readiness e commit |
| Attivo | Identità/versione effettivamente applicate, distinta dalla candidata |
| Bloccato dopo un errore | Riga visibile, motivo/data quando presenti, dettaglio e verifica controllata; nessuna attivazione diretta |
| Incompatibile o danneggiato | Motivo leggibile; nessuna esecuzione; import di una revisione valida come percorso di riparazione |
| In verifica | Operazione in corso, esito e annullamento coerenti con il lifecycle |

«Installato» è un attributo indipendente dallo stato, non sinonimo di disponibile. Mostrare una riga per tema e il dettaglio delle revisioni; una revisione sana dello stesso ID resta selezionabile anche se un'altra è bloccata. Il focus resta legato all'ID dopo aggiornamenti. Se mancano data/versione di un vecchio record, mostrare «non registrata», senza dedurle come certe dal mtime.

Per i guasti comuni: mantenere il fallback prudente e descrivere «GUI interrotta mentre era attivo questo tema; causa da verificare». Distinguere crash, timeout di caricamento, readiness persa, pacchetto non valido e arresto richiesto. Non disattivare il supervisore né introdurre tentativi automatici illimitati. L'utente deve trovare il motivo anche dopo che la GUI ha recuperato Base.

## 5. Recupero e diagnosi del crash

### A0 · Conservare e riprodurre

- Acquisire nuovamente identità runtime, marker, cronologia e preferenze prima delle prove. Conservare copia dei record originali, non sovrascriverli per «pulire» lo stato.
- Preparare store/cache/preferenze e dati di prova isolati. Verificare gli hash del bundle e la compatibilità dei contratti; non modificare il payload immutabile installato.
- Provare prima il rendering isolato; qualificare poi EGLFS/KMS 960×640 in una finestra dedicata, con ripristino di Base. L'offscreen non chiude i rischi driver/display.
- Riprodurre cambio tema, ritorno/annulla, shell, avvisi piccoli/grandi/urgenti, apertura/chiusura degli overlay e arresto della GUI. Priorità al renderer `noticeurgent` e al teardown Python/QML.
- Registrare per ogni errore versione core/Qt, identità bundle, fase, renderer/superficie, generazione, codice/segnale, stato heartbeat e righe diagnostiche pertinenti. Nessun token o payload privato nei log.
- Se il crash si riproduce, acquisire stack con strumenti disponibili o predisporre separatamente una cattura limitata per spazio/retention. Non installare debugger, abilitare dump globali o alzare timeout per nascondere il problema in questo lotto documentale.

Controllare callback timer/segnali con ritorni, ownership degli oggetti, distruzione di contesti/renderer e rientranza durante shutdown. La [correzione Shiboken storica](v088-notifications-implementation-report.md) è un caso da escludere con riproduzione, non la diagnosi già confermata di questo crash.

### A1 · Riammissione controllata

La futura azione «Verifica tema» opera inizialmente sulla copia isolata e conserva il blocco di produzione. Dopo esito positivo, riammissione e attivazione devono essere serializzate con gli stessi lock, identità e protezioni del lifecycle. Base rimane recuperabile; errore, interruzione e doppio comando hanno un esito deterministico. Nessun pulsante che cancelli soltanto il file di quarantena.

Se serve correggere il tema, produrre una **nuova revisione** con nuova versione e digest. Se il problema è nel core, conservare l'identità originale del bundle e documentare la compatibilità verificata con il core corretto. Dopo una prova riuscita archiviare l'incidente e registrare l'esito; non cancellare la storia. Una nuova attivazione fallita ripristina il blocco senza ciclo infinito.

## 6. Prestazioni: baseline e limiti

Il campione passivo di 10 s della precedente fase di questa conversazione osservava GUI circa 48% di un core e QSGRenderThread 23,1%, senza worker Gioco; GUI RSS 538 MiB/PSS 507 MiB circa, MemAvailable 4,9 GiB, swap zero, temperature 51,5–57,7 °C. GPU PowerVR con librerie EGL/GLES caricate, 400 MHz letti; NPU 852 MHz, governor performance. **Questi valori provengono dall'output della sessione e non da un benchmark grezzo allegato. Non usarli come baseline quantitativa A/B o come campione Home/idle:** la schermata visibile non era identificata.

Inventario già documentato e letture correnti distinguono sei A55 e due A76, PowerVR, piattaforma device-tree `xunlong,orangepi-4-pro`/`sun60iw2p1`. L'etichetta commerciale Zero 3W non sostituisce l'inventario. Gli [audit precedenti](v09-resource-optimization-analysis.md) e lo [studio GPU/NPU](game-gpu-npu-parallel-study.md) conservano misure delle rispettive release, senza trasferirle alla rc.18.

CPU del render thread non è tempo GPU; clock GPU/NPU non è occupazione o consumo elettrico. RAM disponibile e swap zero non escludono crescita delle cache. FrameSwapped non è misura ottica o latenza del tastierino. Il prossimo lotto deve costruire una baseline contemporanea con scenario identificato.

## 7. Piano di ottimizzazione del tema e dei percorsi comuni

Conservare quanto già implementato: aggiornamenti dei contesti accorpati, cache limitata dei renderer compatibili, readiness, lease delle risorse, policy Normal/Reduced/Off e percorso scene Gioco separato. Non allargare indiscriminatamente le cache e non riscrivere il Theme Engine.

| Lotto | Candidato e punto del codice | Prova e condizione di adozione |
| --- | --- | --- |
| P0 · Baseline | Sequenza ripetibile Base/Apple, identità di superficie e renderer effettivo, tema e motion | Stessi dati locali, risoluzione, scala e carichi; separare primo ingresso e riapertura, profiler e confronto senza profiler |
| P1 · Nascosti | `ViewHost.qml`, `PublicContextAdapter.qml`, timer/Connections dei renderer | Contare refresh, notifiche e requestPaint visibili/nascosti. Evitare lavoro grafico nascosto, ripristinare l'ultimo dato completo al rientro; acquisizione necessaria agli avvisi conservata |
| P2 · Dati | `theme_service.py`, adapter e modelli dei grafici | Misurare copie/mappe e conversioni; separare dati statici, valori e freschezza, pubblicare campi cambiati. Getter QML senza nuovo I/O, hash o risoluzione completa |
| P3 · Grafici Apple | `MiniHistory.qml`, `NetworkHistoryChart.qml` | Preparazione punti, paint CPU e caricamenti texture separati. Prima guardie/invalidazione corretta e cache limitata dei punti; geometria scene graph solo se il costo misurato lo giustifica |
| P4 · Transizioni | `MotionController.qml`, Fade/Slide e `NavigationDots.qml` | A/B NumberAnimation/Animator soltanto per proprietà visuali. Conservare durata, easing, stop/settle, readiness e comportamento di input; nessuna sostituzione globale |
| P5 · Risorse | Font, immagini, componenti creati e renderer trattenuti | Memoria a percorso caldo e dopo ritorno, cache con limite e lease corretti; nessuna crescita monotona degli oggetti dopo assestamento |
| P6 · Acceleratori | Render GPU già attivo; NPU e compute opzionali | Nessun cambiamento di governor/affinità per default. Backend aggiuntivo solo dopo beneficio completo e convivenza col rendering dimostrati |

I Canvas Apple non hanno attualmente guardie locali complete per visibilità in tutti i percorsi: questo è un candidato da verificare insieme al lifecycle dell'host, **non prova che ridisegnino continuamente mentre nascosti**. Ridisegno al ritorno, resize, cambio palette/scala e modifica dati devono rimanere corretti; evitare grafici congelati.

Gli Animator possono muovere opacity/trasformazioni sul thread di rendering, ma non eliminano creazione degli oggetti, layout, binding o lavoro Python. Le proprietà QML non espongono gli stessi valori intermedi: valutare hit testing, trace, interruzioni e protocollo di coerenza. Una dissolvenza più regolare non corregge una pagina preparata lentamente.

CPU per acquisizione/stato/persistenza e logica; GPU per composizione, geometria e trasformazioni. NPU per inferenza esplicitamente integrata soltanto quando utile al prodotto: non è un motore di animazione. Il confronto storico CPU/NPU delle piccole policy non è un benchmark del tema. Potenza e runtime PM sono uno studio separato, con misurazione elettrica prima di dichiarare risparmio.

## 8. Protocollo comparativo e criteri di accettazione

Prima rendere verificabile Apple in isolamento; poi misurare la stessa build corretta prima/dopo ogni ottimizzazione. Confrontare Base e Apple per distinguere costo comune e specifico. Annotare per ogni superficie se usa renderer Apple o fallback: una pagina Gioco in fallback non misura un renderer Apple autonomo.

Matrice minima, ampliata solo sui rischi emersi:

- Home Ora/Orologio, meteo, Serie A, Casa e Rete con dati fissi; grafici con punti e buchi invariati, Impostazioni e selettore temi.
- Avvisi piccoli/grandi/urgenti, menu e ritorno; evento durante cambio tema o transizione.
- Apple giorno/notte e testo 1/1,1; Normal/Reduced/Off per navigazione, grafici e interruzioni. Functional come controllo di compatibilità nei percorsi comuni modificati.
- Gioco già qualificato: copia privata, carico dichiarato e scene attive, senza training o modifica ai piloti originali; il target 30 Hz del Gioco resta distinto dalle transizioni dashboard a 60 Hz.

Proposta di campionamento: 30 s di assestamento, tre passaggi di 60 s per scenario prestazionale selezionato; 20 aperture/ritorni per distinguere freddo/caldo. Per stabilità: sessione mista di almeno 30 minuti con notifiche e ripetizione dei percorsi. Ordine A/B alternato, temperature/frequenze e carichi esterni registrati. Scenari statici non richiedono ridisegno continuo a 60 Hz.

| Gate | Esito richiesto |
| --- | --- |
| G0 · Catalogo | Bundle bloccato visibile senza esecuzione; motivo corretto; revisione sana selezionabile; nessun tema perso dopo reload/riavvio |
| G1 · Recovery | Fallback e quarantena funzionanti su crash/timeout, interruzione e dati danneggiati; nessun blocco da arresto richiesto; nessun retry infinito |
| G2 · Apple | Selezione/commit persistente, annulla, riapertura e avvisi urgenti riusciti; nessun SIGSEGV o nuovo warning QML nei casi verificati |
| G3 · Motion | Normal/Reduced/Off, sospensione, avviso urgente, stop e ripresa coerenti; stile e focus conservati |
| G4 · Performance | Pubblicare mediana/p95/p99/massimo di apertura/frame e stalli >100 ms, CPU per thread, memoria e contatori di lavoro. Miglioramento ripetibile oltre la variabilità, nessuna regressione funzionale; nessun guadagno percentuale promesso prima di P0 |
| G5 · Obiettivi visivi | Per transizioni a 60 Hz, budget nominale 16,67 ms; per Gioco 30 Hz, 33,33 ms. Riportare deadline mancate e stalli: media FPS o pannello a 60 Hz non chiudono il gate. Qualifica fisica/input separata |
| G6 · Integrità | Preferenze non pertinenti, dati provider, avvisi e piloti originali conservati; ultimo dato completo e freschezza veritiera; cache senza crescita monotona nel campione |

I limiti quantitativi finali per p95/p99 e tolleranze di non regressione si fissano dopo P0 e prima di scegliere il candidato, sulla variabilità misurata. G2/G4 descrivono il perimetro provato, non assenza universale di crash o 60 FPS garantiti.

## 9. Sequenza di implementazione e consegna

1. **F1 · Stato temi e diagnostica:** inventario amministrativo, errori leggibili, contesto del guasto e fixture; catalogo eseguibile protetto. Test mirati per revisione sana/bloccata/danneggiata e compatibilità dei record vecchi.
2. **F2 · Verifica e recupero Apple:** copie isolate, urgent/teardown, diagnosi del crash se riproducibile, riparazione core o nuova revisione bundle, riammissione transazionale e fallback verificati.
3. **F3 · Baseline comparativa:** protocolli P0 e metriche registrate, attribuzione dei costi comune/tema, scelta dei candidati P1–P5.
4. **F4 · Ottimizzazioni selezionate:** una famiglia di modifiche alla volta; parità visiva/funzionale prima di giudicare il beneficio. Scartare prototipi senza vantaggio o con regressioni.
5. **F5 · Candidata:** test PC pertinenti, EGLFS e sessione mista, manifest, backup/rollback, ricevuta e aggiornamento MasterPlan. Versione core/bundle determinata dal contenuto reale; SDK/fixture rigenerati se cambia il contratto pubblico.

Prima dell'installazione confrontare nuovamente checkout, runtime e stato vivo. Conservare modifiche locali preesistenti. Il rollback deve comprendere core e stato del lifecycle pertinente senza sovrascrivere dati provider o piloti aggiornati nel frattempo. Distinguere riavvio del servizio da reboot OS; un reboot si dichiara verificato soltanto se eseguito. Documentare implementato, installato, selezionabile e qualificato nei loro perimetri distinti.

**Pronto per iniziare:** F1 ha causa e comportamento atteso definiti; F2 ha un protocollo diagnostico ma non una correzione SIGSEGV già identificata; F3–F4 richiedono baseline e selezione sperimentale. Nessun lotto è implementato da questo documento. La roadmap Gioco v0.9.x → Acquario v0.10 → Compagno v0.11 → Memoria/AI v0.12 → Stabilità v1.1 rimane invariata.

## 10. Riferimenti

- Evidenza corrente: [snapshot in sola lettura](evidence/apple-calm-recovery-performance-2026-10-15/board-readonly-snapshot.json).
- Architettura acquisita: [guida Theme Engine](theme-engine-implementation-guide.md), [motion](theme-engine-motion-spec.md), [studio impostazioni](v085-settings-theme-analysis.md).
- Prestazioni storiche con release e limiti: [audit risorse](v09-resource-optimization-analysis.md), [clock Gioco rc.13](v09-pacing-optimization-report.md), [GPU/NPU](game-gpu-npu-parallel-study.md).
- Fonti ufficiali consultate nella fase diagnostica: [prestazioni QML Qt 6.8](https://doc.qt.io/qt-6.8/qtquick-performance.html), [Canvas Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-canvas.html), [Animator Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-animator.html), [SDK NPU Vivante per A733](https://docs.radxa.com/en/cubie/a7s/app-dev/npu-dev/cubie-acuity-sdk). Il SoC comune non dimostra identità di board/driver col dispositivo Radxa.
