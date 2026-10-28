# Dashboard Orange Pi v0.9.3 — piano esecutivo dell'intero sistema

**Revisione 4 · 22 ottobre 2026 · Europe/Rome.** [Analisi generale rev.3](v093-systemwide-analysis.md), [evidenze](evidence/v093-systemwide-analysis-2026-10-21/README.md). **0.9.3-rc.1 installata:** [consegna, misure e limiti](v093-implementation-report.md), 645 hash e tre reboot verificati. La baseline dello studio era rc.28/Apple Calm 1.6.3/Theme API 2.11. V0–V8 applicati nei rami sostenuti dalle misure; V9 ha installazione/rollback/boot verificati, con target e prove prolungate/fisiche ancora aperti. I criteri sotto restano invariati.

## 1. Perimetro e decisioni

La release ottimizza **macchina e applicazione intere**: boot/Linux, servizi e timer, memoria/storage, acquisizione Meteo/Account/Sport/Squadra/Fantacalcio/F1/MotoGP/Casa/Rete, notifiche, stato/Theme API, shell/viste/impostazioni/Info, Apple Calm e Gioco. Il [vecchio piano centrato sul Gioco](v093-game-performance-work-package.md) è un pacchetto specialistico del lotto V8.

Si conserva Python/PySide6 + QML/Qt Quick, CPU per servizi/contratti, GPU per rendering, NPU/compute solo dove esista un vantaggio completo. Nessuna quota artificiale di risparmio RAM/CPU. Non cambiare dati, ricette, UX o fonti per rendere più facile un benchmark. Conservare identità Apple, avvisi autonomi e dati precedenti correttamente etichettati.

Le priorità provate sono boot/handoff e proiezione Sport, oltre ai metadati Gioco quando usato. Tutti gli altri rami hanno una baseline per dominio e un trigger misurato. L'ordine non è «prima tutto il Gioco, poi il resto».

## 2. Lotti, dipendenze e uscita

| Lotto | Contenuto | Dipendenza | Esito |
| --- | --- | --- | --- |
| **V0** | Baseline e strumenti dell'intera macchina/app | Analisi acquisita | Scenari identificati e timeline completa per ogni gruppo |
| **V1 · P0** | Handoff Plymouth/boot e ruolo dedicato | Inventario V0 | Boot concluso, nessun bootsplash residuo o job estraneo concorrente |
| **V2 · P0/P1** | Getter/proiezioni, acquisizione, startup e concorrenza | V0 | Sport senza ricostruzione pesante nella GUI; tutti i domini responsivi/coerenti |
| **V3** | Eventi/avvisi, commit e deadline | V0; API dati coerenti V2 | Urgenti e ACK affidabili sotto carico misto |
| **V4** | Shell, modelli, cache, rendering Apple/tre temi | V0/V2; V3 per overlay urgenti | Tutte le superfici fluide e corrette, lavoro nascosto eliminato |
| **V5** | Persistenza/SD, RAM, housekeeping e recovery | V0; in coordinamento V2–V4 | Code e memoria stabili, nessuna falsa conferma o perdita |
| **V6** | Priorità, topologia, governor, thread | Baseline delle modifiche V1–V5 | Configurazione sostenuta selezionata con A/B |
| **V7 condizionale** | Nativo/NEON, QML compilato, compute/NPU/driver | Hotspot rimasto dopo i lotti comuni | Beneficio completo o ramo chiuso come non necessario |
| **V8** | Costi specifici Gioco e convivenza con gli altri domini | V0 e percorsi comuni V2–V5 | Metadati/preview/salvataggi ottimizzati, senza regressioni globali |
| **V9** | Qualifica, distribuzione, reboot e uso lungo | Artefatto selezionato e congelato | Ricevuta per tutto il sistema, limiti espliciti |

V3–V5 e V8 si sviluppano in base ai profili, senza attendere tutti i rami condizionali; ogni confronto usa una sola famiglia di cambiamenti. La chiusura V9 richiede tutti i gruppi funzionali, non soltanto il modulo con il maggiore speedup.

## 3. V0 — baseline comune e oracoli

**Prima di cambiare:** nuovo inventario core/tema/binari/driver/kernel, cgroup, job/timer, stato dei provider, dimensioni cache/DB, preferenze e schema. Manifest/backup e copie consistenti delle sole risorse necessarie ai test. Nessuna copia del solo file SQLite durante scritture; nessuna migrazione implicita su database produttivi da un harness.

Strumentazione con clock monotono e tempi CPU/thread: arrivo fonte→worker→attesa coda→callback→modello→binding/layout→scene graph→submit/present. Per boot: kernel/systemd, import, singoli costruttori, cache, tema/font e primo frame coerente. Per avvisi: revisione fonte→evento durevole→coda→frame→ACK. Registrare attese, copie, byte, righe, segnali emessi e oggetti vivi.

Correggere negli strumenti il percentile nearest-rank; separare freddo/caldo e cardinalità. Portare il controllo delle nuove viste Rete dal vecchio componente legacy al vero host/contentId/contesto pubblico. Conservare i raw e i precedenti fallimenti, senza modificare il prodotto per aggirare un oracolo obsoleto. FTRACE/PSI/uclamp non sono disponibili: iniziare con Qt/userspace, non promettere una traccia kernel già ottenibile.

**Scenari obbligatori di baseline:**

| Gruppo | Riposo/consultazione | Aggiornamento ed errore | Concorrenza |
| --- | --- | --- | --- |
| Home/shell | Oggi, orologio, giornata, menu e transizioni | Cambio minuto/ora/notte, riapertura e dati mancanti | Provider multipli e urgente |
| Meteo/Account | Now/forecast e finestre account | Refresh, file sostituito, cache vecchia/futura/assente | Bollettino e cambio vista |
| Sport/Squadra/Fantacalcio | Hub, calendario, classifica, squadra, dettaglio/voti | Stagione completa, live/revoca/precedente, selezione cambiata durante fetch | Tutte le Serie A e avvisi anche fuori vista; Fantacalcio solo consultato |
| F1/MotoGP | Overview, risultati, timing, pilota e grafici/dettagli | Push/REST, pausa/disconnessione/replay e storico maturo | Due discipline e avviso concorrenti |
| Casa | Overview, inventario, preferiti e dettagli | Aggiornamento, quota/auth/offline e ritorno | Input/avviso durante acquisizione/persistenza |
| Rete | LAN, router, Wi-Fi, porte e storico 1/24 h | Cambio interesse/entità, RRD incompleto, errore e riconciliazione | Grafico + refresh inventario + altro provider |
| Avvisi | Badge, banner piccolo/grande, urgente, inbox/dettaglio | Scadenza/revoca/quiet/raffica/riavvio | Tutti i gruppi di carico, inclusi disco e cambio tema |
| Impostazioni/Info | Ogni pagina, editor tema, dispositivo | Salvataggio/annulla, errore bundle, recovery e scollegamento tastierino | Font/catalogo e refresh senza perdere focus |
| Gioco | Menu/dossier, Gara2/5, camere | Quattro learner maturi su copie, checkpoint e pausa | Gli stessi provider/urgenti continuano a funzionare |

Per ogni famiglia registrare dati nominali, maturi e assenti, giorno/notte e motion normal/reduced/off su Apple; Base/Functional come riferimento funzionale e per attribuire costi comuni. Corpus offline per ripetibilità, fonte reale qualificata separatamente. Prova EGLFS con display esclusivo nella fase di attuazione, stop/ripristino servizio in `finally`; non due processi KMS concorrenti.

## 4. V1 — boot, bootsplash e servizi dedicati

**Riscontro:** `plymouthd` persistente; quit preliminare con status 1 ignorato; `plymouth-quit-wait` in attivazione e sette job pendenti. CPU Plymouth circa 4,43% di un core nel campione. Questo lotto riguarda correttezza dell'avvio oltre al carico evitabile.

1. Ricostruire dipendenze, contesto utente/namespace e socket di controllo del quit; acquisire causa dello status 1 senza assumere che sia il driver o QML.
2. Preparare handoff systemd del bootsplash con privilegi adeguati e dipendenze senza ciclo, separato dal processo Qt. Non affidare a un comando che fallisce silenziosamente l'uscita dal bootsplash; non risolvere con `killall` o con un ritardo arbitrario.
3. Su candidata verificare avvio da spento e reboot: pannello 960×640 disponibile, target di boot raggiunti, `systemd-analyze time` utilizzabile, nessun `plymouth-quit-wait` perpetuo, GUI pronta col PID corrente.
4. Inventariare job estranei al ruolo dedicato. Il timer `copytrade-paper-alpaca-close.timer` è presente anche se il servizio era inattivo: nel lotto di sistema escludere/reindirizzare il lavoro estraneo, conservando unità/configurazione e stato per ripristino. Non avviarlo per misurarne il costo.
5. Mantenere rete, tempo, input, SSH/recovery e servizi necessari; manutenzione/logrotate/backup/aggiornamenti in finestre o priorità che non contendano la GUI. Prima misurare durata e dipendenze, poi selezionare cosa modificare.

**Gate:** boot completato e ripetibile su tre avvii della candidata, nessun display nero o nuova perdita di rete/input, nessun servizio necessario soppresso. Backup delle unità e rollback testato. Non attribuire una riduzione di millisecondi al boot finché prima e dopo non sono misurabili con lo stesso criterio.

## 5. V2 — acquisizione, modelli, startup e concorrenza

### V2.1 · Sport e proiezioni comuni — P0

**File:** `sport.py`, `sport_core.py`, `state.py`, `dashboard_summary.py`, adattatore/Theme API ove richiesto. Il getter ricostruisce tutte le 380 partite; 17,26 ms ARM offline su cache attuale. La GUI non deve rifare la stagione per leggere un campo o una riga visibile.

Separare snapshot posseduto e proiezioni per rotta. Preparare/riusare calendario, classifica, overview, squadra e dettaglio sulla revisione effettiva; pubblicare piccoli modelli con identità stabili. Il cache key include fonte/revisione, stagione, selezione/preferenze e scadenze che cambiano validità/live/tempo. Non usare una cache eterna né un timer che annulla la freschezza. I consumer non devono mutare l'albero condiviso; snapshot immutabili/ownership esplicita e copia selettiva ai confini.

**Gate:** stessi risultati/fonti/età del riferimento per lo stesso istante, nessuna copia della stagione intera nel getter caldo, niente stale presentato live. Misurare numero di letture/invalidazioni per frame e costo upstream prima della piccola proiezione QML. Target getter/proiezione calda <1 ms p95 sul carico nominale, da verificare insieme alla latenza end-to-end; nessuna promessa ricavata dalla sola eliminazione di deepcopy.

### V2.2 · Tutti gli altri provider — P1 secondo profilo

Mantenere I/O nei worker esistenti; analizzare callback finali, merge e marshalling. Non introdurre un processo per il piccolo file Account o riscrivere Info da 1,75 ms senza evidenza. Riutilizzare `_data_view` Motorsport già efficiente; verificare payload maturi/push reali prima di modificarlo. Per Rete misurare caps/inventario copiati prima del worker, proiezioni per periodo/interesse e serie. Casa conserva quota/budget/backoff e completezza; nessun nuovo comando o polling invasivo.

Registrare in modo uniforme richiesta, coalescing, attesa in pool, fetch/parse/persistenza, callback e pubblicazione. Una richiesta informativa superata può essere sostituita prima dell'avvio; comandi, revisioni di eventi e ACK durevoli non si perdono. Limiti per fonte e priorità alle fonti urgenti, senza serializzare tutti i provider dietro un'unica coda lenta.

**Gate:** errore o refresh incompleto mantiene l'ultimo snapshot completo, identità e timestamp; selezione cambiata non riceve il risultato della rotta vecchia. Nessun aumento non necessario delle chiamate o degli accessi alla quota. Prove offline con contatori/ordine e qualifica live distinta, preservando tutti i confini di fonte.

### V2.3 · Avvio applicativo e risvegli

Misurare import/costruttori/cache/font prima dell'engine e spostare fuori dal primo frame il lavoro differibile. Primo contenuto coerente con cache dichiarata, caricamento/provider non ancora pronti espliciti; nessun training prima di Start. Precaricare in RAM le sole proiezioni/viste probabili e leggere cataloghi/font una volta per revisione.

Contare timer e wakeup, senza confondere tick e HTTP: clock/heartbeat 1 s, segnale Python 250 ms, Info 5 s in monitoraggio, keypad riconnessione 2 s, tick Casa 5 s e scadenze adattive. Aggregare callback coincidenti solo se riduce lavoro misurato e non introduce ritardi su input, quiet, scadenze o recovery. Rendere il heartbeat meno costoso mantenendone semantica e supervisione; è già su tmpfs.

**Gate:** primo frame coerente e servizi pronti misurati separatamente; nessuna richiesta provider prima della sua policy; shutdown e avvio QML fallito chiudono worker/processi/Qt senza regressioni Shiboken.

## 6. V3 — notifiche come percorso prioritario completo

**File:** `events.py`, `event_core.py`, adattatori fonti, modelli e presentazioni avvisi. Collegare una timeline per identità/revisione da acquisizione ad ACK del frame. Provare urgente durante ogni scenario V0, inclusi salvataggi, tema e I/O.

Ridurre le decodifiche ripetute nel tick condividendo una proiezione per revisione e istante, solo se il profiling lo richiede. Query/indici e commit vanno misurati; la modalità WAL esiste già. Con due eventi attivi reali il caso sintetico da 1.000 non giustifica automaticamente un nuovo processo. Se un tratto mantiene il GIL troppo a lungo, proiettare prima e trasferire il minimo; mantenere seriali revisioni/commit della stessa fonte.

**Gate:** nessun perso/duplicato/falso goal/live; revoca e quiet corretti; tutti gli incontri previsti continuano ad acquisire anche a vista nascosta; inbox/storico e coda piena coerenti. «Presentato» solo dopo ACK del frame corrispondente. Stress 0/100/1.000 eventi distinto dal nominale; target callback ordinario p95 ≤4 ms/p99 ≤8 ms e risposta urgente locale entro 100 ms p95 dopo evento già acquisito, senza confonderla con la latenza del provider. Verifica fisica separata.

## 7. V4 — shell, modelli e tutte le superfici Apple Calm

**File:** Main, State/Theme API/models, ViewHost/OverlayHost/SceneHost, bundle Apple. Registrare costruzioni, hit/miss cache, binding, segnali, aggiornamenti di righe e layout; cercare invalidazioni ampie da clock/stile/stato indipendenti dalla rotta. Non aggiungere una nuova cache sopra un getter che ricostruisce comunque tutto.

Preservare le ottimizzazioni esistenti: domini per rotta, Qt.callLater, sospensione renderer nascosti, atlas icone, grafici senza letture punti invisibili. Cache renderer 2/4/8 come varianti per host pertinente, verificando il valore effettivo e non il solo supporto; refresh dati prima dell'esposizione. Precaricamento fuori finestre input/urgente. Invalidazione per tema/generazione/contratto/viewport e quarantena; niente vecchio renderer tornato eseguibile per un cache hit.

Modelli: aggiornare le sole righe/ruoli cambiati, identità/focus e ordinamento stabili; evitare reset globali, oggetti ricreati e conversioni di alberi invariati. Grafici: proiezioni per pixel che preservino min/max/buchi, poi eventuale QSGGeometry/Shape se il visibile domina. Canvas/QQuickPaintedItem non diventano automaticamente rendering vettoriale GPU. Asset/font: niente doppio caricamento o rasterizzazione per frame; qualità/testo/icone/palette invariati.

**Gate:** tutte le 68 superfici previste (62 non Gioco + 6 Gioco), le varianti di dati e gli overlay urgenti; giorno/notte e motion off/reduced/normal. Frame nominale animato verso 60 Hz: p95 ≤18,5 ms/p99 ≤25 ms, nessun intervallo >50 ms nei tratti stazionari; numero di deadline mancate sempre pubblicato. Scene statiche possono non ridisegnare. Aperture calde p95 ≤100 ms; input ordinario p95 ≤50/p99 ≤100 ms alla prima risposta coerente. Callback/swap sono filtri software, non certificazione ottica di «60 fissi».

## 8. V5 — persistenza, RAM, storage e recupero

Mappare ogni scrittura e ACK: cache provider, metriche/storico, eventi, QSettings, bundle/lease/journal e Gioco. Conservare atomicità e durabilità, evitare ripubblicazione/scrittura identica, raggruppare solo dati semanticamente compatibili. Encoding/hash/compressione/fsync fuori dalle finestre GUI; la callback deve vedere il risultato corretto, non una conferma anticipata.

Rete: conservare `store.save(updates)` prima del refresh-finished positivo e lo scope del router. Eventi: ACK e ordine transazionale; preferenze/temi: annulla/applica/rollback e generazione/lease. Niente `synchronous=OFF`, cache drop, disattivazione swap o journal globale come ricetta generica. Se si modifica WAL/backup/reader concorrenti, testare la versione SQLite effettiva, checkpoint e ripristino.

Usare RAM per proiezioni normalizzate, geometria, texture, buffer e dati recenti, limitando duplicazioni inutili fra Python/JS/QObject. Nessun tetto di risparmio arbitrario; invalidazione e rilascio prevengono crescita illimitata. Separare RAM, PSS, cache kernel e memoria GPU; non sommarle due volte. Root al 74% non richiede cancellare dati: inventariare backup/artifact/journal e pianificarne retention esplicita con ripristino.

**Gate:** assestamento su cicli ripetuti, nessun OOM/swap-in pesante che coincida con stalli, nessun dato perso per worker lento/errore/processo chiuso. Errori disco/quota/spazio pieno in ambiente di test senza ACK falso; database e cache recuperabili dopo interruzione simulata. Manutenzione/cleanup non blocca input e urgente.

## 9. V6/V7 — risorse dedicate, compilazione e acceleratori

Confrontare la candidata comune: GUI nice 0→−5 e learner/helper distinti; CPUWeight candidato 1000 con controller abilitato da systemd e valore verificato; scheduler libero contro affinità selettiva 6–7 per tratti critici, eredità dei figli controllata; schedutil contro performance del cluster veloce e solo poi entrambi. GPU governor in esperimento separato e con tempi grafici attendibili. Mantenere tutti i core disponibili quando utile: non assegnare rigidamente ogni task a un'unità per riempirla.

Priorità a interazione/urgenti/rendering rispetto a batch/housekeeping; niente SCHED_FIFO, nice −20, isolamento CPU, overclock o protezioni termiche disattivate per principio. Un peso fra cgroup non ordina due thread nello stesso processo. Se una variante non supera il rumore, conservare quella semplice. Verificare consumo/temperatura/clock/caloroso carico lungo: nessuna promessa di massima frequenza sostenibile dalla sola tabella OPP.

V7 si apre solo su hotspot residui: C/C++/NEON su loop numerici o QSG; batching/struttura dati prima del solo flag compilatore; ISA compatibile con i core usati, precisione e ordine FP qualificati. QML compilato su modulo stabile con build riproducibile e tema dinamico compatibile. NPU solo con modello utile/operatori/qualità e costo completo; non spostare JSON/HTTP/SQL sulla NPU. GPU compute deve vincere contro CPU nativa ottimizzata e conservare rendering concorrente. Driver/Qt/Vulkan su clone coerente kernel/firmware/userspace, mai sostituzione parziale sul kiosk.

**Gate:** tre blocchi ABBA sugli scenari rappresentativi, benefici replicati e nessuna regressione funzionale/fonte/visiva; frequenze e termica registrate. Rami non vantaggiosi chiusi con ricevuta negativa. Backup di unità/governor/maschere/driver e ritorno allo stato precedente verificato.

## 10. V8 — pacchetto Gioco dentro il sistema

Applicare il [pacchetto specifico conservato](v093-game-performance-work-package.md), riallineando dipendenze e priorità a V0–V7: reader/proiezioni leggere per query/JSON, dossier/aggregati su richiesta, snapshot/replay sigillati/preallocati e writer durevole; presenter 30 regolare prima della variante 60. Nessuna modifica a piloti, ricette, fisica e ritmi AI per guadagnare FPS.

Le prove includono **anche gli altri domini e gli avvisi** mentre si corre/allena/salva; la loro acquisizione non viene sospesa solo perché la vista è Gioco. Conservare Start/Pausa/uscita/urgente/cambio tema e ripresa esplicita. Non importare policy o certificati dei benchmark.

## 11. V9 — selezione, qualifica e consegna globale

1. Congelare esattamente core/bundle/native/system configuration finali; versionare dal contenuto. Core 0.9.3 alla promozione, prerelease solo quando esiste; bundle Apple/Theme API cambiano soltanto se effettivamente modificati. Rigenerare SDK/fixture se cambia il contratto.
2. Test mirati dei lotti cambiati e matrice di tutte le superfici/rotte/tre temi. Copie offline, dati piccoli/maturi/assenti, input/focus/urgenti e fallback. Nessun fallimento dell'oracolo nascosto come pass.
3. Conferma nativa senza tracing: tutti i gruppi V0, almeno 10 min per carico rappresentativo; sessione mista finale almeno 60 min con refresh, notifiche, scritture e interazioni, poi seguito 8–24 h sulla stessa revisione. Non sostituire con un'ora di Home ferma o sole gare.
4. Almeno tre avvii per boot/handoff; rete assente/ritorno, provider in errore, store/worker lenti, urgenti durante cambio tema, tastierino e recupero. Misurare primo frame corretto e disponibilità fonte separatamente.
5. Verifica fisica del pannello/HID con risoluzione temporale e incertezza dichiarate. Se manca, chiudere soltanto i gate software e mantenere aperti quelli ottici; nessun claim di 60 FPS fissi.
6. Ricontrollare produzione e dati appena prima della consegna, backup coerente e verificato; staging/pacchetto/manifest/hash e rollback. Conservare tutte le preferenze, fonti/cache/quote, eventi/delivery, quarantena, piloti e artefatti aggiornati nel frattempo.
7. Installazione controllata, servizio/GUI col PID corrente pronti e tema corretto; reboot attribuibile alla candidata e controllo successivo di boot, pannello, rete, fonti, avvisi e store. Nessuno Start implicito del Gioco.

**Ricevuta obbligatoria per dominio:** stato implementato/installato/verificato, scenario/payload/hash, campioni/percentili/deadline mancate, disponibilità fonte e limiti, memoria/I/O/termica, backup/rollback e gate aperti. Un miglioramento solo del Gioco non chiude V9. Aggiornare il MasterPlan per versione con risultati reali.

## 12. Regola per scegliere e chiudere un intervento

Prima correttezza/fonte/durabilità/identità, poi beneficio oltre la variabilità. Per i costi ripetuti cercare indicativamente almeno 10% oppure eliminazione ripetibile dello scatto attribuito; riportare tutti gli scenari, anche quelli senza guadagno. La soglia orienta la selezione, non giustifica ignorare picchi rari o regressioni.

Se un ramo non dimostra vantaggio nel protocollo previsto, scartarlo o conservarlo sperimentale e continuare coi problemi provati. Niente riscrittura o acceleratore obbligatorio per «completare» una tabella. Se il target finale non è raggiunto, mantenere il gate aperto e pubblicare il limite. L'analisi originale è conservata; lo stato corrente dell'attuazione è nel report e nelle ricevute. I criteri di questo piano non vengono ridotti per trasformare una candidata in una release qualificata.
