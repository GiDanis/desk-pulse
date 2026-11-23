# Apple Calm 1.7.0 · leggibilità, avvisi e correttezza dei dati

30 ottobre 2026 · SmartPC 0.10.2-rc.5 · Theme API 2.15 · pannello orizzontale 960×640, 3,5″.

Lavoro autorizzato con «Vai implementa tutto», derivato dal [piano I0–I7](v0102-apple-calm-implementation-plan.md). Candidata derivata dai byte effettivamente installati della rc.4, non dall’intero checkout di ricerca. Le modifiche pregresse Gioco/Acquario e i relativi modelli non sono state sostituite con quelle del checkout.

## Risultato grafico e funzionale

- Avvisi piccoli e grandi in basso, con icona di dominio, titolo, testo, fonte e orario. Inbox con separatori, stato non letto e stato di consegna; dettaglio completo scorrevole. Campanella e contatore sono nella barra comune. Quiete, ripristino e orologio possono coesistere.
- La pagina riserva lo spazio occupato dal banner. Gioco e HUD dell’Acquario rispettano la stessa area utile; la scena 3D mantiene il proprio viewport. Le urgenze mantengono il percorso prioritario esistente.
- Gerarchia tipografica esplicita: titolo avviso 28 px, corpo 24 px, metadati 22 px prima della scala utente. Scala 100/110%, Giorno/Notte; contenuti secondari ridotti quando lo spazio manca, senza ridurre automaticamente il testo essenziale.
- Righe più aperte, separatori sottili e bordo di focus; layout compatti per le viste quando appare un banner. Meteo con Max/Min e probabilità esplicite; Rete con unità, intervalli mancanti e interruzioni conservati; Account con residuo coerente fra numero e barra. Icone Meteo/F1/MotoGP risolte con il vocabolario reale dei provider.

Il tema rappresenta i dati; acquisizione, pianificazione, deduplicazione, revoca, scadenza, lettura e acknowledgement restano nel motore esistente. Non sono stati aggiunti provider, abbonamenti o polling Fantacalcio; tutte le partite di Serie A mantengono il perimetro notifiche esistente. Nessuna nuova notifica Casa.

## Correzioni semantiche

1. `half_time` è conservato dal contratto e mostrato correttamente nei filtri e nei risultati. Un punteggio parziale mantiene il lato noto: `0 – —`; una gara futura non diventa uno 0–0 inventato.
2. Motorsport pubblica distintamente tempo, tipo di tempo, gap e stato. Il totale del vincitore non viene confuso con il distacco degli altri; migliore/ultimo giro rimangono riconoscibili. Alias storici preservati; un risultato della vecchia cache viene indicato come riportato, senza inventarne il significato temporale.
3. Reset Account assente/zero non diventa 1970. Usato 34% → residuo 66%, con barra coerente. Booleani e numeri non finiti non diventano misure; uno zero valido rimane visibile e le stringhe temporali valide sono conservate.
4. Velocità e direzione del vento sono campi distinti; l’orario dell’avviso non viene presentato come prova di controllo recente della fonte.

API 2.15 additiva: contatore e disponibilità avvisi in `UiStatus`; stati pubblici stabili di consegna; campi Motorsport espliciti. Quattro documenti canonici, generati, typeinfo runtime e corpus aggiornati insieme. Fingerprint: `5457c7f00f43ce140ca66be370757785510e99944eb4fa22ce84260d7d409dd0`.

## Movimento e GPU

Qt Quick usa già la GPU. Il backend nativo verificato è EGLFS/OpenGL ES 3.2, Imagination PowerVR B-Series BXM-4-64. Ponte EGL, driver, configurazione KMS e disabilitazione della cache shader della rc.4 sono conservati.

Mantenute le transizioni di proprietà e la policy Normale/Ridotto/Disattivo; nessun blur dinamico né animazione decorativa continua introdotti. Il confronto ABBA fra `NumberAnimation` e `OpacityAnimator` è una misura sintetica separata, con riscaldamento e campioni dichiarati: non dimostra un vantaggio sufficiente per cambiare globalmente la semantica delle animazioni. Intervalli di callback software non equivalgono a FPS ottici, durata GPU o latenza dei tasti.

## Verifiche e attribuzione delle prove

Evidenze in [v0102-apple-calm-implementation-2026-10-30](evidence/v0102-apple-calm-implementation-2026-10-30/). PC target: Python 3.12.13/Qt 6.8.2. Board: aarch64/Qt 6.8.2. Le prime prove Qt 6.11 sono diagnostiche e non sostituiscono quelle target.

- Nove controlli PC sui domini/contratti e controlli pertinenti UI/notifiche passati, con successivi passaggi mirati sulle correzioni. Le 33 regressioni finali usano produttori/adattatori reali e il vero `Format.js`, con valori attesi indipendenti.
- Preflight finale PC e ARM: 1.098 renderer ciascuno. Main reale PC: matrice di 148 casi e 14 workflow sulla revisione intermedia; regressione finale degli avvisi, delle icone e dei workflow sulla revisione finale. Navigazione di 120 passaggi e stato finale delle tre modalità di movimento verificati.
- Geometrie e dati: 36 combinazioni per palette, nove viste × due scale × due banner, più header Quiete/Ripristino/contatore e scene Gioco/Acquario. Le prove usano stato privato, dati sintetici e rete negata. Gli screenshot sono esempi di collaudo, non provider live.
- EGLFS sulla revisione finale `daf0a7…`: 148 casi Main Giorno e 61 Notte, 14 workflow per palette, 120 passaggi di navigazione e tre modalità di movimento; 36 combinazioni di leggibilità per palette e quattro prove delle scene. Nessun warning QML, viewport 960×640, API fingerprint corretto. Ricevuta [qualifica nativa](evidence/v0102-apple-calm-implementation-2026-10-30/board/eglfs/qualification.json).
- ABBA nativo finale, 10 s per blocco con riscaldamento separato: proprietà 315/299 intervalli, Animator 452/449. p95 rispettivamente 17,861/17,780 e 17,577/17,513 ms; massimo complessivo 18,665 ms, nessun campione >50 ms. Il primo tentativo da 7 s aveva due blocchi sotto 200 campioni ed è stato sostituito per questo motivo. [Dati e limiti](evidence/v0102-apple-calm-implementation-2026-10-30/board/eglfs/motion.json). Il risultato riguarda la finestra sintetica, non il carico completo o il consumo energetico.
- Il ramo ARM non dispone di `qmllint`: il controllo runtime è passato con un’esclusione esplicita del lint; il lint target PC è passato. Nessun pacchetto di sviluppo installato per aggirare il limite.

### Schermate e osservazione del servizio

[Home del servizio installato, cattura DRM effettiva](evidence/v0102-apple-calm-implementation-2026-10-30/board/scanout/installed-home-actual.png). [Banner piccolo con dati sintetici](evidence/v0102-apple-calm-implementation-2026-10-30/board/eglfs/day/alerts.banner.small--default.png). La prima è memoria di scanout del processo definitivo, non una fotografia del pannello; la seconda è una fixture EGLFS, non una notifica live.

Osservazione passiva Home: 20 s di riscaldamento e 10 s di campione per versione. RSS GUI finale 327.940 KiB sulla rc.4, 279.496 KiB sulla rc.5; CPU del servizio 1,66% e 1,54% di un core. Le letture non sono un confronto accoppiato di carico: provider, cache e temperatura non sono controllati. Non dimostrano un risparmio energetico, assenza di leak o prestazioni sotto Gara/apprendimento. [Baseline](evidence/v0102-apple-calm-implementation-2026-10-30/board/resources-baseline.json), [installata](evidence/v0102-apple-calm-implementation-2026-10-30/board/resources-installed.json).

### Errori incontrati e controlli corretti

Le ricevute iniziali non sono cancellate. Typeinfo generato inizialmente non aggiornato, argomenti mancanti del runner per header/Acquario e due errori del banco tema sono stati corretti: navigazione oltre l’ultima vista e modifica in-place di uno snapshot invece della pubblicazione di una nuova revisione. Il banco delle scene è stato protetto da `main()` per non avviare una seconda GUI nel processo figlio del worker.

Il controllo del profilo finale è stato corretto per riconoscere che `SMARTPC_AQUARIUM_RENDERER` assente usa il default con 3D disponibile: assenza della variabile non significa 2D. Profilo installato, disponibilità e librerie sono verificati nella [ricevuta grafica](evidence/v0102-apple-calm-implementation-2026-10-30/board/post-install-check.json).

`check_game_race_ui` del checkout fallisce sulla selezione di una pista/preset incompatibile con il roster installato congelato. Non è stato modificato il motore Gioco per soddisfare quel banco. La prova visiva isolata usa il Maestro esistente in Qualifica e verifica continuità durante gli avvisi; non certifica nuove reti, apprendimento o gare competitive.

## Installazione e conservazione

**Installata e verificata nel servizio reale:** `smartpc-dashboard.service` attivo/running, `NRestarts=0`, GUI pronta con heartbeat recente e tema 1.7.0 esatto. Il PID della GUI è distinto da quello del supervisore systemd ed è verificato come suo discendente. 550 hash runtime corrispondenti, nessun warning QML/grafico rilevato; stesso boot, nessun reboot OS. [Ricevuta di installazione](evidence/v0102-apple-calm-implementation-2026-10-30/board/installation.json).

Conservati database e 218 artefatti Gioco, sei identità e sei visite Acquario; 44 preferenze controllate, comprese palette/movimento/scala originali. Spazio libero alla consegna: 17.693.904.896 byte, circa 16,5 GiB. La [ricevuta finale](evidence/v0102-apple-calm-implementation-2026-10-30/final-receipt.json) include la verifica dopo la pulizia. Staging rimosso soltanto dopo la verifica sul PC di tutte le 1.313 voci esportate; archivi temporanei RAM rimossi dopo verifica della copia privata. Le copie private e il runtime precedente restano sotto `/var/backups/smartpc-dashboard`; gli archivi privati esportati sul PC sono fuori dal repository. Identità effettive:

| Oggetto | Identità |
| --- | --- |
| Baseline rc.4, 550 file | `85bd9456e8bcd0b90145ed829b5e2f574d2395d5946176170323f7a3c1979dff` |
| Runtime rc.5, 550 file | `7b33780f75ce4496089365ae7ad9ab2d5178f5051c4be02cf18b938ff732d1cd` |
| Apple Calm 1.7.0 finale | `daf0a7b1cc0bc19bd2931765b14714dc1dadf685025df337541a65fe9b78d376` |
| ZIP finale SHA-256 | `d00bab8827bd2909478ba417214267726ca9f95156bb563c7dd5c983b5a8fb9c` |

La revisione intermedia `e6ca13…` è esclusivamente diagnostica: non è il payload da installare. Tutti i file `game*` e le librerie native della baseline rimangono identici. Il backup privato precede l’attivazione e comprende runtime, configurazioni, dati, journal/WAL e cache; sono verificati contenuti, metadati, hardlink, gzip e integrità dei database. Il rollback rimane separato dai sorgenti Git.

### Incidenti di consegna e ripristino

Il primo tentativo ha superato i 30 s dell’estrattore durante l’importazione su storage persistente. La transazione ha ripristinato runtime e dati. Nel secondo tentativo l’importazione con le medesime verifiche è stata eseguita in tmpfs, poi copiata, sincronizzata e verificata prima della rinomina atomica. Nessun controllo o budget dell’archivio è stato allentato.

Il servizio reale ha poi mancato la readiness entro il limite di avvio: il problema si è verificato anche sulla rc.4 e su Base durante i recuperi, con attese di I/O osservate. L’attivazione isolata del tema era passata. Il terzo tentativo ha separato il trasporto compresso in RAM dallo snapshot durevole, drenato tutte le scritture con `sync` prima dell’avvio e ripristinato le preferenze e lo stato del tema originali dal primo backup, evitando di conservare le scelte imposte dal fallback. Avvio reale successivo riuscito entro il limite ordinario, senza cambiare i timeout del supervisore.

Il backup finale confronta 2.518 file originali; archivio con 2.707 membri, contenuti/metadati/hardlink e gzip verificati. Lo snapshot completo è persistente; l’archivio di trasporto in RAM è esportato e verificato sul PC prima della sua rimozione. Sul PC sono verificati il backup completo recente e un archivio separato dello stato grafico originale; il primo backup completo resta verificato anche sulla board. Il primo backup conserva l’aspetto 1.6.5 originario: il ripristino completo deve preservare i dati più recenti e usare quel riferimento per l’apparenza, non lo stato Base prodotto dai timeout. Le prime due transazioni e i relativi errori rimangono documentati nelle evidenze.

## Limiti aperti

La candidata non diventa automaticamente stabile. Restano il riscontro fisico sul pannello da 3,5″ alla distanza abituale, tastierino reale e lettura negli otto secondi; goal/VAR e sessioni F1/MotoGP reali, transizioni LAN, soak prolungato e confronto prestazionale completo della Dashboard sotto Gara/apprendimento. Non è stato eseguito un reboot OS per questa consegna. Questi gate non possono essere chiusi da fixture o catture software.
