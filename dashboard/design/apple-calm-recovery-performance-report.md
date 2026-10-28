# Apple Calm · recupero e ottimizzazione · rc.19

**16 ottobre 2026 · implementata e installata sulla Orange Pi; verificata nei perimetri PC/EGLFS descritti sotto.**

Seguito del [piano F1–F5](apple-calm-recovery-performance-analysis.md). Candidata core **0.9.0-rc.19**, 608 file; bundle **Apple Calm 1.6.3**, digest finale `faf3e0032162416a471c8122d320709f47b71df0667b042816fffa4e3b452d62`. Theme API **2.11 / 68 superfici** conservata. [Evidenze e strumenti](evidence/apple-calm-implementation-2026-10-15/).

## 1. Problema e comportamento risultante

Apple Calm 1.6.2 era installato ma scompariva dal selettore: il supervisore aveva registrato un'uscita GUI -11 e la revisione in quarantena veniva esclusa dall'elenco. La scomparsa è attribuita con certezza a questo filtro; la responsabilità del tema nel SIGSEGV storico rimane aperta.

Il selettore ora usa un inventario amministrativo separato dal catalogo eseguibile. Un tema bloccato o danneggiato rimane visibile con motivo, versione e data quando registrata. I vecchi incidenti privi di timestamp mostrano «Data non registrata». Se una revisione è sana e un'altra è bloccata, resta possibile attivare quella sana e consultare l'incidente della vecchia. Il focus si conserva per ID dopo il reload; se l'ID scompare, la selezione viene ricondotta all'elenco valido.

L'azione **Verifica** lavora in un processo separato su una copia privata, senza attivare il tema. Il pacchetto originale è protetto da lease durante la prova. La riammissione richiede esito positivo, stesso payload, stesso marker dell'incidente e generazione del lifecycle invariata, senza attivazioni concorrenti. Il lock non rimane occupato durante il rendering. Successo e incidente sono archiviati prima di togliere il blocco; la selezione effettiva richiede poi **Attiva**. Doppio comando e annullamento sono verificati; un annullamento conserva la quarantena.

L'inventario viene acquisito durante il caricamento/reload del catalogo e riusa le revisioni già verificate. I getter QML non fanno nuove scansioni, hash o I/O. Record danneggiati rimangono diagnosticabili; pacchetti senza preflight valido non entrano nel catalogo eseguibile.

## 2. Diagnostica e conservazione delle protezioni

Il fallback a Base, readiness, commit e supervisore restano attivi. I nuovi marker riportano il timestamp. Il supervisore conserva al massimo dieci rapporti `gui-failure-*` con versione core, PID/codice di uscita e ultimo heartbeat pertinente. L'heartbeat aggiunge superficie, renderer, revisione, fase e versione Qt; non include dati dei provider o ambiente/credenziali.

Le matrici originali 1.6.2 e candidate 1.6.3 sulla board hanno superato **1.098 casi ciascuna**, senza warning QML. La candidata passa anche la matrice PC. Il SIGSEGV storico non si è riprodotto in questi casi: **non viene dichiarata una causa del crash né una sua correzione specifica**. La nuova revisione comprende una correzione di lavoro grafico e la riammissione è un percorso protetto, non la cancellazione indiscriminata della quarantena originale.

## 3. Ottimizzazione selezionata

`MiniHistory.qml` e `NetworkHistoryChart.qml` preparavano tutti i punti anche quando nascosti. La nuova revisione sospende preparazione e richieste di paint non pertinenti, riprende con i dati correnti al ritorno visibile e ridisegna anche su disponibilità del Canvas, resize e cambio dei colori usati. Zero, buchi e interruzioni delle serie mantengono il significato originale.

Microbenchmark dei componenti reali su EGLFS: due serie di 512 punti, 200 invalidazioni, tre ripetizioni prima/dopo. Mediane del lavoro di aggiornamento nascosto:

| Componente | Apple 1.6.2 | Apple 1.6.3 | Letture dei punti |
| --- | ---: | ---: | --- |
| MiniHistory | 562,16 ms | 17,61 ms | 204.800 → **0** |
| NetworkHistoryChart | 1.176,67 ms | 25,97 ms | 204.800 → **0** |

Le immagini visibili coincidono esattamente prima/dopo in tutte e tre le coppie native e dopo nascondi/aggiorna/mostra. Il confronto PC conferma la parità dei pixel. Sono misure di componenti su dati sintetici, **non percentuali di accelerazione della dashboard né frequenze reali dei provider**. [Script e risultati](evidence/apple-calm-implementation-2026-10-15/benchmark_charts.py).

Il controllo aggiuntivo «dato presente → assente» ha rilevato un difetto nella prima variante ottimizzata: il ritorno anticipato con `chart=null` lasciava i vecchi pixel del MiniHistory. Il bundle finale conserva il guard della visibilità ma ripristina il clear prima del controllo del dato, come nell'originale. Il test riproduce il difetto sulla variante preliminare e passa sul bundle finale. La variante preliminare aveva digest `d27cdea…`; i suoi risultati di durata e le immagini non vengono attribuiti senza distinzione al digest finale. Il supplemento finale verifica assenza, ripresa e parità dei pixel in EGLFS, oltre alla matrice del payload corretto.

Non sono state adottate sostituzioni generali con Animator, nuovi layer, migrazioni dei grafici al scene graph, riscritture Python/C++, affinità o clock forzati. Il beneficio dimostrato riguarda i grafici nascosti; gli altri candidati P1–P6 rimangono condizionali ai propri costi e confronti. CPU per stato/logica, GPU PowerVR per rendering; nessun nuovo carico NPU. Grafica, font, icone, motion policy e frequenza fisica del Gioco sono conservati.

È stato inoltre corretto un costo comune: entrando nelle impostazioni si apre una bozza anche senza modifiche; uscire da quella bozza ripubblicava l'aspetto e incrementava la revisione. `cancel()` ora evita la pubblicazione se aspetto visibile e salvato coincidono e non esistono candidata o attivazione. La bozza viene comunque eliminata, con notifica dell'editor. Il nuovo test verifica zero chiamate a `_publish`, revisione e snapshot invariati; annullamento di modifiche vere, caricamento, salvataggio e recovery seguono i percorsi originali. Il confronto finale misura anche il numero di pubblicazioni durante la navigazione.

## 4. Protocollo completo e correzione del runner

L'app completa usa fixture private e dati fissi, senza accessi di rete; i confronti Apple usano lo stesso contratto, testo 1,1 e la stessa sequenza di Home/Orologio, meteo, Account, Sport, Casa, Rete, Menu, impostazioni, selettore e avvisi urgenti. La baseline conserva il core preparatorio prima della correzione di `cancel()` e Apple 1.6.2; la candidata comprende quella correzione e Apple 1.6.3. Il [protocollo e gli hash](evidence/apple-calm-implementation-2026-10-15/final-comparison-protocol.json) distinguono le due modifiche. Tre coppie alternano l'ordine prima/dopo, con 30 s di assestamento e 60 s misurati per caso. Base/Functional, notte Reduced/Off e impostazioni Gioco hanno walkthrough separati. Le soglie di non regressione sono registrate nei [criteri](evidence/apple-calm-implementation-2026-10-15/performance-criteria.json).

Il primo runner usava `processEvents()` senza drenare `DeferredDelete`, fuori da `app.exec()`. Il primo soak completava 30 minuti senza crash/warning ma cresceva da circa 200 a 706 MiB RSS. Quella crescita non viene presentata come una perdita del runtime: il ciclo manuale ritardava la distruzione degli oggetti QML. I log restano conservati come controllo diagnostico, senza qualificare G6.

Il runner corretto elabora le distruzioni differite al confine delle azioni, come il normale ciclo Qt, e registra anche numero di contesti, lease e oggetti QML. Il controllo PC di 120 s mostra memoria circa 208–211 MiB durante i campioni a 100/200 azioni, contesti stabili a 17. Il teardown della fixture drena inoltre gli oggetti prima di rimuovere i file privati: il primo tentativo che li rimuoveva troppo presto è conservato nei log. La correzione riguarda la fedeltà dei test e non viene venduta come risparmio RAM della produzione. Un secondo tentativo lungo è stato interrotto deliberatamente per includere il fix della bozza invariata; resta marcato superseded. Il test lungo successivo riguarda il core finale e il payload grafico preliminare, seguito dal supplemento mirato sul payload finale per il caso dato assente.

**Esito nativo con runner corretto:** tre coppie completate. Mediana dei p95 di prontezza host **337,98 → 339,71 ms**, intervalli frame **18,77 → 18,01 ms**: nessuna regressione secondo il criterio fissato, nessun miglioramento globale della prontezza dimostrato. Pubblicazioni dell'aspetto durante la navigazione **7/7/7 → 0/0/0**; stalli >100 ms **4/4/3 → 3/3/3**. [Riepilogo numerico](evidence/apple-calm-implementation-2026-10-15/board-final/performance-summary.json).

Il soak sul core finale dura **1.800,13 s / 2.683 azioni**, con zero warning, accessi di rete o pubblicazioni inutili dell'aspetto. Frame callback: mediana **16,45 ms**, p95 **17,95 ms**, p99 **21,04 ms**, massimo **182,56 ms**, tre intervalli >100 ms. Prontezza host: mediana **130,03 ms**, p95 **323,02 ms**, massimo **608,80 ms**. Sono misure software, non latenza ottica/USB o tempo GPU: stalli e primi ingressi restano visibili, senza dichiarare 60 FPS fissi.

RSS **200,07 → 236,46 MiB**; mediana 5–10 minuti **223,46 MiB**, ultimi cinque **236,14 MiB**: +12,68 MiB dopo il primo assestamento. Contesti massimo **17**, lease massimo **27**, oggetti QML massimo **2.379**, swap processo zero, temperatura massima campionata **43,83 °C**. Il criterio diagnostico del campione è superato con contatori limitati; **non è una prova di memoria perfettamente piatta o assenza universale di perdite nell'uso 24/7**. L'RSS cresce moderatamente nel runner e rimane un residuo da osservare su uso reale prolungato. Il digest del payload di questo soak è esplicito nel riepilogo; il delta finale del clear a dato assente ha prove supplementari proprie.

## 5. Verifiche eseguite

| Gruppo | Esito e perimetro |
| --- | --- |
| Bundle | 27 test, integrità/import/export/lease/recovery |
| Riammissione | 10 test: copia isolata, incidente/generazione/payload cambiati, annullamento, descrittori/marker danneggiati, revisione sana accanto a bloccata |
| Recupero del servizio | 16 test di salvataggio, journal, risorse e uscita senza modifiche |
| Contratto API | 31 test, una esclusione preesistente; API/fingerprint conservati |
| Ottimizzazioni acquisite | 4 test di dati/cache/retention |
| Supervisore | 5 prove GUI vere di crash, hang, startup, readiness ed uscita inattesa; protocollo con timer privati separato |
| QML/Impostazioni/Motion | Cambio tema, bozza/annulla/salva, caricamento, interruzioni urgenti, focus, scale e Normal/Reduced/Off |
| Riammissione UI | PC ed EGLFS: Verifica annullabile, nessuna attivazione implicita, attivazione esplicita persistente, urgente e ritorno a Base |
| Board | Matrici da 1.098 casi per originale e payload finale; Base/Functional, notte Reduced/Off, Gioco e riammissione UI. Soak core finale di 30 minuti e supplemento sul bundle finale: sei casi grafici più 30 s nell’app completa, senza warning |

Le fixture mantengono un blocco di rete con controllo positivo. I bypass iniziali del preflight nel test dell'esempio sono dichiarati; la riammissione UI esegue invece il vero subprocess/matrice. Il pacchetto Apple di consegna usa le prove reali con digest e versione Qt corrispondenti. Il primo avvio PC con Python 3.14 non aveva una distribuzione Qt 6.8 compatibile: è stato usato l'ambiente Python 3.12/Qt 6.8.2 già presente, senza installare dipendenze sulla board.

## 6. Distribuzione e stato del piano

Il [delta runtime](evidence/apple-calm-implementation-2026-10-15/runtime-delta.json) contiene undici file modificati e due controlli nuovi rispetto alla rc.18. Il binario numerico ARM è conservato byte per byte; il binario x86 del checkout non viene distribuito sulla Orange Pi. Bundle Apple separato e versionato; payload 1.6.2 immutabile. Kit AI esportato dal contratto corrente, senza nuova minor API.

**Consegna completata:** core **0.9.0-rc.19 / 608 hash conformi**, Apple Calm **1.6.3 selezionabile**, Base ancora attivo. [Ricevuta](evidence/apple-calm-implementation-2026-10-15/board-final/delivery/final-receipt.json) e [inventario di produzione](evidence/apple-calm-implementation-2026-10-15/board-final/delivery/production-inventory.json). Tutte le 44 preferenze verificate sono conservate (40 non pertinenti all’aspetto), così come tutte le tabelle dei 6 piloti e i 3.191 artefatti originali. Servizio active, NRestarts=0, heartbeat GUI fresco/pronto e nessuna attivazione pendente. Nessun reboot OS o allenamento di produzione; incidente 1.6.2 conservato.

Backup software/aspetto: `/var/backups/smartpc-before-apple-recovery-20261016-112906`; runtime precedente: `/opt/smartpc/dashboard-rc18-before-apple-20261016-112906`. Dati provider e piloti restano fuori dal rollback visivo. Il [supplemento del payload finale](evidence/apple-calm-implementation-2026-10-15/board-final/release-supplement.json) conferma clear con dato assente, zero letture dei punti nascosti, pixel visibili identici e ripresa corretta in tutte e tre le coppie EGLFS. La matrice finale è nel [rapporto ARM](evidence/apple-calm-implementation-2026-10-15/board-release-preview/preview-report.json).

F1–F5 completati nel perimetro selezionato: inventario e diagnostica, riammissione protetta, baseline/confronto, ottimizzazione misurata, distribuzione e ricevuta. La causa del SIGSEGV storico resta aperta perché non riprodotta. Gli altri candidati prestazionali rimangono subordinati a misure; uso reale 24/7, crescita RSS residua, primi ingressi, FPS ottici e latenza fisica restano da qualificare. Nessuna qualifica live di Sport/Casa/Rete o competenza dei piloti viene dedotta da queste fixture.
