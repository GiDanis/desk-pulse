# Migrazione delle notifiche al Theme Engine

**3 ottobre 2026 · estensione della v0.6.6.** Implementata, collaudata in EGLFS e installata sulla board, con prova del rollback completo. Il manifest finale e la salute dopo reboot fisico sono registrati insieme alla distribuzione.

L'[audit iniziale](theme-engine-notification-spec.md) rimane la prova del problema sul runtime 15b7f7a: sei composizioni fisse e sovrapposizioni con testi lunghi. La migrazione mantiene Python/PySide6 per eventi, identità, SQLite e preferenze; QML per visuali e movimento. [Guida per uso e autori](theme-engine-implementation-guide.md#personalizzare-gli-avvisi).

## Risultato funzionale

- Sei content ID indipendenti: piccolo, grande, urgente, badge, elenco e dettaglio. Host con nomi stabili; nuovi renderer ricevono NotificationContext API 1. Main/EventEngine/ThemeService non contengono switch per i temi dimostrativi.
- 181 token locali con facade tipizzata: colori, geometria, spaziature, forme, quattro font/ruoli, righe e visibilità. Ereditarietà globale, override locali, contrasto e riserva di spazio dei template forniti. Renderer inediti possono usare layout/token propri.
- Base conserva la disposizione ordinaria; Functional usa fascia con icona e scheda divisa; personal.sample dimostra banner centrato e poster registrati da un'estensione. Piccolo e grande non sono varianti obbligate di un singolo componente.
- Aspetto → Avvisi: selettori dal registry, personalizzazione, preview dei sei ambiti, applicazione/reset. Preview fuori dal DB; ritorno al pannello padre conserva la bozza; Back/Home fuori dall'editor annullano.
- Un solo commit dopo la preparazione di tutti i candidati necessari. Timeout/errore/cancel mantengono la vista valida e invalidano Apply. Font candidati rilasciati su fallimento. Recupero Base anche per un asset dedicato eliminato prima del cambio giorno/notte.
- Urgente Base di emergenza disponibile mentre il visuale scelto carica; comandi immediati. Il banner viene consegnato solo dopo un frame con contenuto visibile, validato per ID/revisione/rank. Otto secondi nel servizio, nessun riavvio per cambio tema.
- Dettaglio in flusso scorrevole da tastierino: titolo/corpo/fonte non si sovrappongono. L'elenco mantiene la selezione per ID con inserimenti e densità diversa.
- Ricette per modalità, Normale/Ridotto/Disattivo, un solo controller sulle trasformazioni del Loader. Il tween parte dopo il completamento dei binding del commit; una callback superata viene scartata. Un cambio di revisione non cancella il tween appena avviato. Nessun loop Python per frame.
- Ingombri trasmessi alle scene: pausa della locomozione quando manca spazio, posa/azione conservate; spostamento una sola volta per anchor. Il compagno definitivo resta nella v0.9.

## Verifiche e prove

**23 harness PC Qt 6.11.2** e **23 harness board Qt 6.8.2/PySide6 6.8.2.1** passati: [PC](evidence/notification-engine-migration/local-suite/checks.json), [board con SHA dei test](evidence/notification-engine-migration/board-suite/checks.json). Eventi/provider/configurazione non usano dati di produzione nelle fixture.

`check_notifications.py` verifica dieci famiglie di casi: consegna differita e callback di revisione superata; tre temi con avvisi visibili e DB/deadline/focus invariati; entry trasparente senza falsa consegna; ingombri e locomozione della scena; dimensioni massime delle schede; dettaglio lungo completamente raggiungibile; selezione per ID; editor/preview isolati; staging coordinato/errore/timeout/cancel; urgente a freddo con renderer ritardato e chiusura da tastierino. Il test di errore registra soltanto il warning del Broken.qml deliberatamente non valido. Nessun warning QML inatteso.

Il test Dashboard ora mantiene il ciclo principale Qt attivo fra le attese mediante QEventLoop locali: fermarlo impediva il rendering necessario al nuovo acknowledgment. Il test squadra congela soltanto il clock di presentazione delle fixture registrate al 1 ottobre; la partita futura della fixture era già passata nella data reale del test. Nessun cambiamento al modulo Sport.

La matrice EGLFS usa tre temi × piccolo/grande/urgente in ciascuna delle sei combinazioni giorno/notte × movimento Normale/Ridotto/Off, più i casi di errore/readiness/focus e testi massimi. Catture native 960×640: [giorno Normale](evidence/notification-engine-migration/eglfs/day-normal/report.json), [notte Off](evidence/notification-engine-migration/eglfs/night-off/report.json). Esempi: [poster personale](evidence/notification-engine-migration/eglfs/day-normal/personal.sample-large.png), [dimensioni massime](evidence/notification-engine-migration/eglfs/day-normal/maximum-roles-large.png), [fonte raggiunta nel dettaglio](evidence/notification-engine-migration/eglfs/night-off/long-detail-bottom.png).

**Processo nuovo realmente offline:** preferenze/cache/SQLite isolati, namespace PrivateNetwork senza indirizzi globali e route. La chiamata reale Open-Meteo fallisce; il meteo salvato rimane. Functional/notte/Ridotto e titolo locale 31 px vengono ricaricati; avviso consegnato non riproposto, avviso in attesa consegnato dopo il frame, letture/chiusure preservate. [Report](evidence/notification-engine-migration/offline/report.json), [cattura EGLFS](evidence/notification-engine-migration/offline/cold-notifications.png). Questa prova è un riavvio del processo, non un nuovo reboot fisico; il precedente reboot offline della v0.6.6 resta documentato separatamente.

## Prestazioni e risorse

A733: 6 Cortex-A55 + 2 Cortex-A76, PowerVR BXM-4-64, EGLFS/KMS/OpenGL, 960×640 a 60 Hz. Nessun benchmark GLX/llvmpipe. Fixture ordinarie identiche e due stress da 100 cambi con avvisi piccolo/grande/urgente; il secondo usa tre TTF veri dedicati ai titoli degli avvisi.

| Misura | Runtime precedente (157 file) | Nuovo runtime (177 file) |
| --- | --- | --- |
| Navigazione, intervallo frame p95 / massimo | 17,900 / 29,465 ms | 17,847 / 30,710 ms |
| Navigazione, intervalli >33,34 ms | 0 | 0 |
| Input → frame p95 / massimo | 19,493 / 25,387 ms | 35,025 / 37,797 ms |
| PSS finale della stessa fixture | 104,03 MiB | 110,83 MiB |

[Baseline](evidence/notification-engine-migration/eglfs/baseline/report.json), [nuovo runtime](evidence/notification-engine-migration/eglfs/current/report.json). Delta PSS +6,80 MiB; il feedback rimane sotto l'obiettivo p95 di 100 ms. Lo scostamento dell’input è circa un frame nel campione di navigazione, coerente con la partenza differita del tween dopo il completamento dei binding; questa attribuzione è un’inferenza, non un profiling delle singole chiamate. Il costo osservato è esplicito.

| Stress da 100 cambi | Preset senza font aggiuntivi | Tre TTF dedicati agli avvisi |
| --- | --- | --- |
| Cambio richiesto → frame, p95 / massimo | 155,921 / 174,347 ms | 143,556 / 232,135 ms |
| Cambio → frame, p95 dopo primi usi | 151,777 ms | 140,086 ms |
| Notifica → frame, p95 | 131,978 ms | 137,054 ms |
| Intervallo frame p95 / massimo (tutti) | 17,990 / 44,162 ms | 17,935 / 88,711 ms |
| Intervalli >33,34 ms / >50 ms | 3 / 0 | 4 / 3 |
| Intervallo frame warm p95 / massimo | 17,940 / 23,217 ms | 17,929 / 23,861 ms |
| Intervalli warm >33,34 ms | 0 | 0 |
| Picco PSS | 120,01 MiB | 122,54 MiB |
| Crescita fra metà e fine del campione | 0,34 MiB | 0,30 MiB |
| Registrazioni font, picco / fine | 0 / 0 | 3 / 3 |

[Preset](evidence/notification-engine-migration/eglfs/stress-presets/report.json), [font](evidence/notification-engine-migration/eglfs/stress-fonts/report.json). Gli assert controllano a ogni cambio anche readiness dei sei host, consegna/letture/chiusure e deadline del banner. Nessun warning QML. Il budget frame ordinario p95 ≤20 ms è rispettato; **l'obiettivo cambio completo p95 ≤150 ms è superato di 5,9 ms nel primo profilo e rimane un limite prestazionale dichiarato**, pur conservando il visuale precedente e i comandi durante la preparazione. I picchi dei primi usi non sono nascosti dal dato warm e richiedono una nuova verifica per font e visuali più costosi. Non si promette un limite rigido di 150 ms per qualunque tema.

 I report conservano tutti gli intervalli lunghi; i dati warm escludono soltanto il primo uso di una coppia modalità/tema e sono riportati separatamente. Nessuna animazione diagnostica aggiunta per generare frame nello stress notifiche. FrameSwapped è invio della presentazione Qt, non tempo GPU o risposta ottica; PSS non misura tutta la memoria grafica.

## Distribuzione, backup e rollback

Il backup T0 originario della v0.6.6 viene conservato. Nuovo backup privato di runtime e dati utente: `/var/backups/smartpc-notifications-20261003/pre-migration/{dashboard.tar.gz,user-state.tar.gz}`. Distribuzione ricorsiva verificata, **177 file**, con sostituzione completa della directory e controllo della PID stabile. [Installazione e SHA degli archivi](evidence/notification-engine-migration/distribution/deployment-report.json).

Rollback effettivo: estrazione del backup fresco, avvio dei 157 file precedenti e verifica del manifest; successivo ripristino e avvio dei 177 file nuovi. Le preferenze conservano SHA `d5ef0b9a6fd454c59f43b116dcdcf6f5e5cda1b85295d668940a8304dd6023de`. [Report](evidence/notification-engine-migration/distribution/rollback-report.json). Durante l'installazione non c'erano righe evento attive in produzione: la conservazione dei diversi livelli è dimostrata dalle fixture SQLite e dalla prova offline, oltre alla preservazione del database reale nel backup e nell'installazione.

La salute con provider reali è distinta dai benchmark isolati: [prima del reboot](evidence/notification-engine-migration/distribution/pre-reboot-health.json). Cache, DB e preferenze reali restano privati.  Nessuna migrazione dello schema SQLite e nessuna modifica alle regole di EventEngine. Il tag v0.6.6 preesistente non viene spostato: il manifest identifica i nuovi sorgenti della stessa linea di versione.
