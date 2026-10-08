# v0.8.2 — Affidabilità e risposta

**0.8.2-rc.1 · 8 ottobre 2026 · Theme API 2.4 · Apple Calm 1.2.1.** Prima candidata di consolidamento implementata e installata sulla Orange Pi. Il contratto conserva 56 superfici; questa fase corregge persistenza, lifecycle, feedback e costi misurati. La riorganizzazione Sport/Impostazioni e la nuova densità del display appartengono alla fase 0.8.3 del [piano](v082-v083-consolidation-plan.md).

## C0 · Baseline

Checkout iniziale 0.8.1, HEAD/tag locale `v0.8.1` al commit `d761d7a`; distribuzione effettiva sulla board **0.8.1-rc.1**, 490 file integri e Apple Calm 1.2.0. Le identità sono state riconciliate senza riscrivere il tag stabile. [Baseline board](evidence/v082-consolidation-2026-10-08/baseline-board.json), [baseline locale](evidence/v082-consolidation-2026-10-08/baseline-local/checks.json).

## C1 · Dati e aggiornamenti

- **Meteo:** acquisizione e salvataggio atomico/fsync nel worker; il completamento arriva dopo il tentativo di persistenza. Disco non scrivibile lascia utilizzabile il dato appena acquisito, ma dichiara «cache non salvata» e non conferma il refresh. Fallimento della sostituzione conserva il file precedente completo. Cache incompleta, timestamp non finito/futuro e risposta con valori richiesti non finiti vengono rifiutati. I dati in memoria invecchiano anche quando non arriva un nuovo fetch; la cache fredda conserva l'ora originale e lo stato precedente.
- **Lifecycle:** Meteo e Account vengono chiusi anche quando il caricamento QML fallisce. Meteo fermato durante l'acquisizione non pubblica né avvia un salvataggio tardivo. Una sostituzione atomica già iniziata può terminare in sicurezza. I timer di refresh usano callback senza risultato Qt: durante la verifica è stata riprodotta una segfault Qt 6.8.2 collegando direttamente un nuovo slot `result=bool` a un timer. Sono coperti anche Casa/Rete configurati senza cache, con trasporti sintetici.
- **Account:** file limitato a 32 KiB, schema/numeri/timestamp verificati, invecchiamento senza rilettura del JSON invariato. Watcher riarmato dopo replace atomico; dati invalidi o file assente conservano l'ultima lettura completa con il suo stato/ora. La richiesta manuale dice «Rilettura dal PC»: non promette una sincronizzazione cloud.
- **Refresh manuali:** accettazione, operazione in corso, completamento, errore, cooldown e coda sono distinti. Gli avvisi completano dopo la persistenza del motore; Sport/Motorsport riportano gli errori cache. Solo le richieste accettate consumano il cooldown. Il broker pubblico registra la richiesta prima della chiamata, così non perde il completamento sincrono Account. Le protezioni/quote dei provider rimangono effettive.

Le prove includono rete lenta/offline, persistenza lenta/fallita, risposta incompleta, cache corrotta, richieste duplicate, chiusura durante fetch, clock arretrato, replace atomico Account e broker reale. [Dodici scenari Qt/Main](evidence/v082-consolidation-2026-10-08/local-delivery/check_consolidation_ui.txt), [avvio automatico Casa finale](evidence/v082-consolidation-2026-10-08/cold-casa-final/checks.json), [avvio Rete/lifecycle](evidence/v082-consolidation-2026-10-08/cold-start-final/checks.json).

## C2 · Costi dimostrati

Il confronto avvia processi Qt separati, usando lo stesso snapshot e introducendo **150 ms di ritardo nella sostituzione del file**. Prima la scrittura nel callback GUI blocca il timer; dopo la scrittura del worker lascia rispondere il loop. L'acquisizione esterna è esclusa. I controlli Account usano un file identico invariato.

| Misura sulla Orange Pi | Prima | Dopo |
| --- | ---: | ---: |
| Massimo intervallo callback timer Qt da 5 ms | 155,326 ms | 5,890 ms |
| Parsing Account in 100 controlli automatici invariati | 100 | 0 |
| Durata dei 100 controlli Account | 36,037 ms | 0,748 ms |

[Metodo riproducibile](evidence/v082-consolidation-2026-10-08/profile-maintenance.py), [risultati board](evidence/v082-consolidation-2026-10-08/profile-board.json), [risultati PC](evidence/v082-consolidation-2026-10-08/profile-local.json). Sono misure controllate del loop software e del lavoro su file; non sono GPU time, latenza ottica, FPS né una promessa globale di consumo/velocità. RSS prima/dopo in viste non equivalenti non viene usato come guadagno; non è pubblicato un confronto CPU idle globale.

## C3 · UX immediata

La panoramica Sport ferma la rotazione al primo input, conserva pagina e pausa attraverso gli overlay e riprende soltanto dopo uscita/rientro nella famiglia. Dati e aggiornamenti mostrano l'esito effettivo, compresi errori cache e coda Rete. Apple Calm 1.2.1 riusa il glifo Rete già presente, associa la famiglia/voce Impostazioni e allinea i titoli al pannello comune; il footer evita feedback duplicati.

**U06 non riprodotto:** l'ispezione della cattura storica e delle nuove schermate non conferma la sovrapposizione titolo/sottotitolo ipotizzata nell'analisi. Non viene inventata una correzione geometrica; l'audit di overflow alle scale supportate resta nella fase 0.8.3.

Apple Calm viene consegnato come revisione immutabile nuova, digest `575fd88f93592423d53eba0ba7deedcd3fab25398baddb768a8d224768fa0b21`. Non si modificano i byte della 1.2.0 installata.

## C4 · Qualifica e distribuzione

- **70 casi locali superati** con Python 3.12.14, PySide6 6.8.2.1 / Qt 6.8.2: suite completa più verifiche mirate dopo gli ultimi fix. [Indice con provenienza degli esiti](evidence/v082-consolidation-2026-10-08/regression-final.json). I run iniziali falliti rimangono consultabili: mock storici da allineare, callback timer Qt e caso di avvio Casa inizialmente collocato dopo la scadenza della policy sintetica.
- `ruff check dashboard scripts` e `git diff --check` superati.
- Board Qt 6.8.2: otto casi offscreen pertinenti e tre controlli finali Casa/Rete, senza chiamate live Casa nelle fixture.
- EGLFS/KMS 960×640: dodici scenari Main nei profili Base giorno e Functional notte. Apple Calm notte: tre superfici canoniche interessate, 138 passi di navigazione, movimento Normale/Ridotto/Disattivo, scroll e azioni; nessun warning QML.
- Preflight nativo Apple Calm: 864 renderer isolati sul Qt della board; la matrice offscreen resta distinta dalla prova EGLFS. Localmente verificate le stesse tre superfici in palette giorno.
- **491 file runtime** corrispondenti al manifest. Distribuzione diagnostica separata; il renderer Canvas di diagnosi non entra nel runtime.
- [Kit AI autonomo v0.8.2](artifacts/smartpc-theme-ai-kit-v082.zip): 489 file SDK, contratto invariato e core della candidata, nessuno stato privato. Hash verificati e dodici scenari Qt/Main eseguiti fuori dal repository. [Export](evidence/v082-consolidation-2026-10-08/sdk-kit.json), [UI isolata](evidence/v082-consolidation-2026-10-08/sdk-ui.txt).

Backup completo **`/var/backups/smartpc-before-v082-20261008T072838Z`**: runtime, configurazione, dati/local state e cache. La prima transazione ha esercitato il rollback automatico perché l'heartbeat non era ancora presente al controllo a 10 s; runtime/tema/preferenze precedenti sono stati ripristinati e verificati. L'installer ora attende readiness con un limite di 40 s, senza rilassare l'identità o la freschezza richieste. La seconda transazione è passata. [Ricevuta](evidence/v082-consolidation-2026-10-08/install-receipt.json).

**Reboot completato:** Boot ID cambiato, servizio `active/running`, `NRestarts=0`, GUI pronta e heartbeat fresco; manifest, Apple Calm 1.2.1 e tutte le 38 preferenze conservati. Il ledger Casa coincide con il backup: nessuna nuova richiesta Casa registrata durante questa consegna. [Prima](evidence/v082-consolidation-2026-10-08/board/pre-reboot-health.json), [dopo](evidence/v082-consolidation-2026-10-08/board/post-reboot-health.json), [verifica finale](evidence/v082-consolidation-2026-10-08/board/delivery-verification.json). La prova e il verifier sono salvati persistentemente in `/var/lib/smartpc-dashboard/v082-proof/`, indipendenti da `/tmp`. [Uso e rollback](v082-maintenance-operations.md).

## Ambito e residui

C0–C4 sono implementate per questa candidata, con le limitazioni di misura dichiarate. Non è creato un nuovo tag stabile: versione del checkout modificato e versione installata sono 0.8.2-rc.1. Restano collaudo fisico del tastierino/distanza 50–60 cm, scollegamento e ripresa reale della rete, power-cut e prova prolungata. Quota e comandi Casa, Sport live qualificato e i limiti di copertura/guest Rete restano gate separati.

La **fase 0.8.3** realizza l'ingresso Sport unico, il riordino delle Impostazioni, la copertura grafica Rete, l'atlante delle icone mancanti e la densità/gerarchia coerenti per il display. Il dossier di ricerca resta il riferimento; le sue ipotesi fisiche non diventano prove di usabilità grazie ai soli screenshot.
