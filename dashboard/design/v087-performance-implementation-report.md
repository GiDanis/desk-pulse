# 0.8.7 — Reattività con la GUI attuale

9 ottobre 2026 · candidata `0.8.7-rc.1` · Theme API `2.7` invariata · Apple Calm `1.6.1`.

**Implementata, installata e verificata dopo reboot reale sulla Orange Pi.** La candidata conserva grafica, font, icone e informazioni. Lo [studio precedente](v087-performance-analysis.md) mantiene la baseline e le otto fonti ufficiali; i risultati qui appartengono alla patch definitiva.

## Interventi

| Area | Comportamento implementato | Protezione conservata |
| --- | --- | --- |
| Stile | Il contesto trattiene il wrapper QObject e riusa lo stile normalizzato quando revisione, geometria e input sono invariati. | Palette, scala testo, motion, nuovo oggetto e revisione invalidano la cache; rilascio al teardown. |
| Contesti | Normalizzazione per campo e pubblicazione dei soli campi cambiati; i modelli già validati mantengono identità. | Copie possedute dal core, rilevamento delle mutazioni in-place, validazione atomica dei nuovi payload e conservazione dell'ultimo snapshot completo. |
| Shell | La navigazione presentata cambia solo quando cambia il percorso effettivo. | Aperture e transizioni richiedono ancora la readiness della destinazione; nessuna modifica ai comandi. |
| Rete | Il contesto personalizzato non condivide più la stessa chiave di cache con l'envelope generico. | Fonte, indisponibilità e qualità restano esplicite. |
| Dashboard | Un refresh invalida soltanto le proiezioni del dominio coinvolto; scadenza temporale e limite di cache conservati. | Aggiornamenti reali, stati precedenti/offline e calendario completo; polling e I/O provider invariati. |
| Lifecycle | Lease riusa la verifica integrale del bundle soltanto se tutto l'albero mantiene identità, modo, dimensione, mtime e ctime. Il catalogo font è riusato solo con file invariati. | Lock contro GC, lease durabile, verifica completa su import/list/attivazione, rilevamento di alterazioni anche con mtime ripristinato. |
| Apple Calm | Callback di scorrimento nominato e protetto contro la distruzione della griglia. | Nessuna modifica a layout, icone, colori, font o informazioni. |

La differenza rispetto al manifest 0.8.6-rc.2 è limitata a **11 file runtime**, inclusi tre verificatori aggiornati, un nuovo benchmark e la versione. Nessun file rimosso. Il bundle cambia soltanto `DashboardCards.qml` e i due manifest di versione. [Perimetro](evidence/v087-implementation-2026-10-09/delta-scope.json).

Non è stata cambiata la tecnologia: Qt Quick/QML e Python/PySide6 rimangono. Non sono stati ridotti polling, quantità di informazioni, dettagli o dimensioni grafiche. P5 comprende la stabilità dei modelli già necessaria per P2; ulteriori interventi su rendering, immagini o C++ richiedono un costo residuo misurato.

## Protocollo di misura

`verify_performance_ui.py` usa il vero `Main.qml`, un segnale keypad sintetico e dati isolati: 380 partite Serie A, navigazione effettiva, nessuna richiesta di rete. Tre cicli producono 18 cambi argomento, 30 selezioni dashboard, 72 selezioni valide in lista, tre aperture e tre ritorni. I controlli aggiuntivi coprono 16 selezioni ciascuno in Casa, Rete e Impostazioni.

Il timestamp parte prima dell'handler. Dopo la readiness del percorso e del contesto, un aggiornamento esplicito viene associato a un identificativo, acquisito in `beforeSynchronizing` e registrato in `frameSwapped`. È una **misura software conservativa fino alla submission di un frame successivo alla readiness**; include l'attesa aggiunta dal protocollo. Non misura tastierino USB, latenza ottica, esecuzione GPU o necessariamente il primo frame visibile. Nessun outlier viene scartato. I render callback leggono solo identificativi primitivi, senza accesso QML dal thread render.

Baseline e candidata usano la stessa Orange Pi, Qt 6.8.2/PySide6 6.8.2.1, EGLFS e 960×640. Motion off consente il confronto; normal viene verificato separatamente. I numeri PC offscreen non vengono presentati come prestazioni del pannello. Non esiste una distribuzione pre/post dei refresh reali simultanei, né un tracing QML Profiler nativo della patch definitiva.

## Verifiche PC

- Sei controlli mirati sul core: summary, API runtime (37 test), bundle/lifecycle (27), trace frame, invalidazioni e recovery (15).
- Dodici controlli pertinenti su Casa, Rete, Sport, azioni, contratto, domini, layout, profili, palette, recovery e watchdog; adapter reali delle 62 superfici e supervisore GUI verificati separatamente.
- Vero Main nei quattro profili Base giorno, Functional notte, Apple giorno/notte: tutte le dieci partite della giornata accessibili e preferita separata, nessun warning QML.
- Preflight Apple 1.6.1: 1.098 combinazioni dei renderer pubblici, nessun warning; lint reale passato. La prima invocazione combinata risultava `notVerified` per un percorso qmllint errato; la seconda verifica statica corretta è conservata separatamente. [Verifica ricomposta](evidence/v087-implementation-2026-10-09/local-preflight-verification.json).
- Cache stile rilasciata correttamente, invalidazioni esplicite, payload mutati/malformati e tampering del bundle coperti da regressioni mirate. Le fixture non vengono dichiarate letture live.

## Risultati nativi e consegna

La matrice di 1.098 combinazioni passa anche sulla Orange Pi con Qt 6.8.2 e backend offscreen. Il vero Main passa su EGLFS nei quattro profili Base giorno, Functional notte, Apple giorno/notte: calendario completo e preferita separata, nessun warning QML. Le impostazioni superano otto transizioni tra temi, focus che non attiva, salvataggio compatibile delle modifiche e conferma del frame finale. API runtime: 37 casi, 36 passati e un solo lint saltato perché qmllint non è installato sulla board; il corrispettivo PC con lint reale passa. Bundle 27 casi e recovery 15 passano nativamente.

Confronto delle **stesse prime 126 azioni** di ogni sequenza, motion off; ritorni aggiunti per Casa/Rete/Impostazioni esclusi dal confronto principale. Tempi in millisecondi, tutti gli outlier conservati:

| Apple Calm | Mediana prima | Mediana dopo | p95 prima | p95 dopo | Campioni per versione |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cambio argomento | 199.8 | 133.4 | 525.3 | 406.2 | 18 |
| Selezione dashboard | 121.1 | 80.5 | 237.9 | 168.9 | 30 |
| Selezione lista Serie A | 111.6 | 68.5 | 136.4 | 85.0 | 72 |
| Apertura elenco Serie A | 729.4 | 697.9 | 729.4 | 697.9 | 3 |
| Ritorno | 200.6 | 158.5 | 200.6 | 158.5 | 3 |

Il miglioramento mediano è **38,6% nelle liste**, **33,6% nelle dashboard** e **33,2% nel cambio argomento**. Base mantiene le liste a circa 36 ms, p95 39 ms, rispetto a 36/39 ms precedenti; le altre categorie non mostrano peggioramenti nel campione. I tre campioni di apertura non bastano per attribuire un beneficio affidabile: l'apertura resta circa **0,7 secondi**, con massimo 865 ms contro 1.098 ms della baseline.

Con animazioni **normali**, quelle salvate sul dispositivo, Apple riproduce il beneficio: lista mediana 67,5 ms/p95 84,2 ms. Casa, Rete e Impostazioni hanno p95 rispettivamente 72,9/91,6/64,9 ms su 16 selezioni effettive ciascuno; non esiste una baseline appaiata per queste tre categorie. Le fixture di inventario non provano da sole il comportamento di ogni dimensione della rete reale. Un primo focus Impostazioni può ancora raggiungere 216 ms.

La cache stile passa da 689 ricostruzioni su 736 lookup a 144 su 812: circa 94% → 18%. I contatori della candidata includono 51 azioni aggiuntive; non confrontare i totali come workload identici. Il dominio Rete passa da una ricostruzione per lookup a due su 60 lookup nell'intero campione esteso. Le regressioni unitarie dimostrano il riuso nella selezione stabile e l'invalidazione quando necessaria. [Misure complete e confronto](evidence/v087-implementation-2026-10-09/performance-comparison.json).

**Gate raggiunto:** lista Serie A p95 ≤100 ms, nessuna selezione nel campione oltre 200 ms. **Gate ancora aperti:** dashboard p95 ≤150 ms (osservato 169 ms anche nei cicli successivi al primo) e aperture ordinarie ≤300 ms. La consegna riduce il rallentamento riprodotto; non dichiara tutti gli obiettivi prestazionali chiusi.

Un profilo CPU nativo separato conserva l'attribuzione residua: `updateLegacy` 11,7 s cumulativi nel workload profilato, `normalize_legacy` 6,5 s e `deepcopy` 6,8 s, valori sovrapposti. Il profilo comprende avvio e strumenti di test: introspezione/readiness e processing eventi hanno un costo rilevante. Non sommare questi tempi e non usarli nella tabella A/B; non sono una misura esclusiva delle prime aperture. Servono un profilo delle singole azioni e l'osservazione fisica prima di modificare ulteriormente la costruzione dei contesti o scegliere C++. [Attribuzione CPU](evidence/v087-implementation-2026-10-09/native-profile-summary.json).

P0 ha una baseline e confronto EGLFS controllati; P1/P2/P4 sono implementati e qualificati; P3 consegna riuso delle verifiche, font e callback sicuro, con costo residuo delle aperture esplicito. P5 non introduce modifiche grafiche speculative. Le prove durabili sulla board risiedono in `/var/lib/smartpc-dashboard/v087-performance-proof`; l'[evidenza locale](evidence/v087-implementation-2026-10-09/) conserva script, misure, manifest e ricevute.

**Installazione e reboot completati:** manifest di 514 file, SHA256 `73fe019fd96bd2dee817e370c87cac2dbe887155b578c8621298be7343833670`; tema 1.6.1, digest `083ad5f82a577b45d656f2c92c243b593237233305fe6be5d7e850c0ee38679e`. Backup protetto `/var/backups/smartpc-before-v087-performance-20261009T212333Z`, con core, configurazione, dati e cache; l'installer ripristina automaticamente questi snapshot in caso di errore, conservando gli eventuali budget Tuya aggiornati. Attivazione e avvio a freddo passano attraverso il vero Main e il journal del tema.

Boot precedente `710b737b-2967-48f0-ac4e-9173242b3d6d`, successivo `f1a01e32-4c81-4ddd-a26f-b14b15f2e781`. Verificati GUI fresca/pronta, nessuna attivazione pendente, `active/running`, `NRestarts=0`, nessun warning QML nel journal. Le **40 preferenze non di aspetto**, le personalizzazioni attive e i profili degli altri temi sono conservati; tutte le preferenze dopo l'attivazione sopravvivono al reboot. [Ricevuta di installazione](evidence/v087-implementation-2026-10-09/board-proof/install-receipt.json), [verifica del reboot](evidence/v087-implementation-2026-10-09/board-proof/reboot-verification.json).

Un campione passivo di 20 secondi dopo l'installazione conserva CPU/RSS/temperature e servizio stabile: non costituisce un confronto controllato di idle, né un test prolungato. Il kit autonomo aggiornato [smartpc-theme-sdk-v087-rc1.zip](../../smartpc-theme-sdk-v087-rc1.zip) contiene 512 file SDK verificati; il profilo Qt destinatario non è allegato e non viene dichiarato certificato dall'export.

Le prime invocazioni di qualifica registrano qmllint assente e un timeout del wrapper esterno a 300 secondi. Il processo isolato del preflight ha completato la matrice e salvato il risultato durabile; la qualifica finale riusa soltanto il digest validato e superato. Il wrapper corretto esegue il preflight offscreen senza occupare il display e ammette il limite previsto dal motore. La prima verifica dopo reboot era stata lanciata prima della readiness: il polling ha poi atteso il heartbeat fresco e la verifica finale è passata. Gli esiti iniziali rimangono nelle prove, senza presentarli come gate superati.

## Limiti che restano aperti

Giudizio con tastierino fisico e pannello a 50–60 cm, distribuzione della latenza ottica, refresh reali concorrenti con navigazione, crescita prolungata e uso 24/7. I cicli qualificati non provano un soak test. Nessun nuovo collaudo degli eventi realmente live, quota Tuya o copertura LAN. Nessun tag, commit o promozione stabile implicita.
