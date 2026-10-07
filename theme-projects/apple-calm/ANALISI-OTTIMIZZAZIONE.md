# Apple Calm — analisi di ottimizzazione e piano 1.2.0

**Baseline storica precedente all’implementazione.** Per la versione corrente e le misure finali consultare [CONSEGNA.md](CONSEGNA.md).

Data: 6 ottobre 2026. Stato: analisi; nessuna modifica al runtime, al tema installato o alle preferenze. Sono state eseguite letture del codice, riproduzioni isolate e misure in sola lettura sulla Orange Pi. Non sono stati arrestati servizi, attivati temi, interrogati provider o cancellati file.

## 1. Baseline verificata

La scheda esegue SmartPC **0.7.0-rc.2** e **Apple Calm 1.1.0**. Il servizio è `active/running`, con `NRestarts=0`; il journal non ha transazioni pendenti. La precedente **1.0.0** è ancora installata e indicata come `previous`.

Il digest attivo è `43344f7fe1264be9fc075c5852abc75bbffa3f493fde744cb9a9548a19c5a123`. Gli SHA di `Main.qml`, `theme_api.py`, `theme_lifecycle.py` e `theme_bundle.py` locali coincidono con quelli installati. Il tema copre 43 superfici della dashboard precedente; le superfici Casa aggiunte nel core corrente non hanno composizioni Apple Calm dedicate.

Il payload installato comprende 59 file, circa 1,12 MB. La memoria corrente dell'intero servizio, nel campione letto, è circa 340 MiB: non è una misura della sola GUI né una prova di esaurimento della RAM.

Le precedenti verifiche EGLFS comprendevano 130 casi funzionali e controlli sui pallini. Il report dichiara esplicitamente **`performance: notVerified`**. I risultati attestano caricamento, contratti e conservazione della navigazione; non attestano fluidità, latenza dal tastierino, correttezza di tutti i testi o visibilità dei pallini sotto ogni overlay. La classifica era stata fotografata nel caso vuoto, che non poteva mostrare il difetto dei nomi.

## 2. Diagnosi della lentezza

### Costo misurato: ricostruzione della stagione per la classifica

La cache sportiva reale contiene **380 partite e 20 squadre**. Nella Orange Pi, in un processo Python separato, sono state misurate tre chiamate consecutive agli stessi adattatori del runtime, senza acquisire nuovi dati:

| Operazione isolata | Prima chiamata | Seconda | Terza |
| --- | ---: | ---: | ---: |
| Normalizzazione completa `SportData` | 233,80 ms | 225,68 ms | 227,14 ms |
| Adattamento `sport.standings`, cache mantenuta | 238,89 ms | 233,01 ms | 232,87 ms |
| Adattamento `sport.overview`, cache mantenuta | 245,61 ms | 5,26 ms | 5,18 ms |
| Lettura e SHA dei file del payload | 3,45 ms | 2,83 ms | 2,58 ms |

**La classifica ripete la normalizzazione completa della stagione anche quando i dati sportivi non cambiano.** In `normalize_legacy`, il ramo `SportListContext` normalizza direttamente `SportData`; il riepilogo passa invece per `_cached`. Questo costo viene raggiunto dalla pubblicazione dei contesti sul thread GUI. È una causa concreta di blocchi potenziali, soprattutto all'apertura e durante cambi di selezione/stato.

Le misure sono microbenchmark, con tre campioni, su dati già in cache: non sono p95, FPS, tempo GPU o latenza dell'intero cambio schermata. Non includono conversione QML→Python, creazione dei QObject, caricamento QML, disegno o presentazione del frame. La verifica completa del bundle include inoltre inventario e metadati; scrittura e sincronizzazione delle lease non sono state cronometrate. La sola lettura/SHA misurata non giustifica attribuire principalmente la lentezza ai file del tema.

Riferimenti: [theme_api.py](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/theme_api.py:278), [PublicContextAdapter.qml](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/components/PublicContextAdapter.qml:55).

### Altri costi presenti nel codice, da misurare nella transizione reale

1. **Overlay ricreati.** `ViewHost` carica un nuovo renderer quando cambia la sua identità, crea stile e contesto pubblico, acquisisce una lease e distrugge il precedente dopo il commit. Il singolo host degli overlay paga nuovamente questo lavoro passando fra menu, classifiche e dettagli. Il Loader asincrono non rende asincrone le chiamate Python eseguite prima del caricamento. Le pagine principali già caricate, invece, hanno un percorso di riuso: non vanno trattate tutte come ricreate a ogni tasto.
2. **Contesti conservati e dipendenze ampie.** Gli adattatori restano collegati allo stato quando le pagine sono conservate ma inattive; il payload comune legge navigazione, orologio e dati di route. Occorre misurare quanti aggiornamenti inutili raggiungano ogni host. Le proiezioni per dominio e alcune cache esistono già: vanno estese dove mancano, non riscritte indiscriminatamente.
3. **Liste trasformate in array.** `Format.list/map`, `Rows.rows.slice` e il `Repeater` perdono parte dei vantaggi dei modelli Qt che conservano l'identità delle righe. La ricreazione dei delegate può rifare testi, geometrie e icone. Priorità: modello stabile o proiezione memorizzata per revisione dei dati; virtualizzazione soltanto dove serve. Oggi `Rows` istanzia già solo le righe visibili, quindi non disegna 380 righe contemporaneamente.
4. **Animazioni sovrapposte.** La navigazione anima il contenitore; il cambio renderer può aggiungere `layout.swap`; cambio scheda e aggiornamento dati hanno altri fade. Sono presenti durate di 120 ms, 160 ms per `layout.swap` e 180 ms per i pallini. Un tasto può avviare una transizione prima che il contenuto sia pronto. Occorre un'unica transizione coordinata con il commit e nessun fade dell'intera pagina per il semplice spostamento del focus.
5. **Geometrie delle icone.** Ogni `OutlineIcon` usa `Shape` e `PathSvg`. Riutilizzarle stabilmente evita lavoro; un confronto sulla scheda stabilirà se conviene conservarle come geometrie o rasterizzare le dimensioni usate. Non c'è ancora una misura che le identifichi come causa principale.

Riferimenti: [ViewHost.qml](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/components/ViewHost.qml:135), [Rows.qml](/home/giuseppe/Documenti/Workspace/SmartPC/theme-projects/apple-calm/bundle/qml/Rows.qml:19), [MotionController.qml](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/components/MotionController.qml:23), [OutlineIcon.qml](/home/giuseppe/Documenti/Workspace/SmartPC/theme-projects/apple-calm/bundle/qml/OutlineIcon.qml:23).

### Intervento proposto

- Riutilizzare lo snapshot sportivo normalizzato anche nel ramo `SportListContext`; separare dati di stagione, righe della route, selezione e stato della fonte. Una selezione non deve ricostruire 380 partite. Non aumentare la frequenza delle API dei provider.
- Pubblicare soltanto i campi cambiati e aggiornare i contesti inattivi al momento opportuno, con riallineamento completo prima della loro presentazione. Conservare i controlli di coerenza del frame.
- Conservare renderer e delegate delle schermate frequenti con una cache limitata; chiavi comprensive di superficie, identità del renderer e revisione del tema. Invalidare su cambio tema e rilasciare le risorse prima della pulizia delle revisioni.
- Coordinare caricamento e animazione: il vecchio contenuto resta completo fino a quando il nuovo è pronto; una transizione breve, interrompibile, porta direttamente all'ultima destinazione richiesta. Nessun accumulo di animazioni con tasti rapidi.
- Ottimizzare lease/I/O solo se il trace completo ne dimostra il peso. Conservare verifica dell'integrità e protezione rispetto al garbage collector.

L'orologio centrale ha già un timer che controlla ogni secondo ma cambia `now` al cambio del minuto o del giorno. Non serve ridurre arbitrariamente i controlli di salute o aggiungere animazioni continue per far apparire il tema più fluido.

## 3. Classifica Serie A: difetto confermato nei dati pubblici

Il provider e la cache usano `team` e `teamId`. Il DTO pubblico `Standing` espone `name`, `id` ed `entityId`; manca la conversione specifica. Il renderer legge correttamente il campo pubblico `name`, ma lo riceve vuoto.

Riproduzione reale della conversione, con una riga sintetica dello stesso formato:

```text
Input:  team="Inter", teamId="inter", position=1, points=16
Output attraverso SportData:
        name="", entityId="", id="SportData:standings:0"
```

Nella cache della scheda tutte le **20 righe** hanno `team`, nessuna ha `name`; dopo la normalizzazione tutti i 20 nomi risultano vuoti. Non è un problema di font o di elisione del testo.

È perso anche l'ID della squadra: il core seleziona usando `teamId`, mentre il modello può pubblicare un ID sintetico basato sulla posizione. Questo può rendere incoerenti selezione e azioni sulle righe. Inoltre il broker gestisce `details.open` sul riepilogo sportivo come apertura di una partita: una riga di classifica non deve essere inviata a quel percorso come se fosse un incontro.

Correzione prevista nel confine provider→DTO: `team → name`, identità stabile derivata da `teamId`, `entityId` coerente, azione esplicita per le squadre o riga non apribile quando non esiste un dettaglio appropriato. I campi già canonici devono avere precedenza; Formula 1 e MotoGP, che forniscono già nomi e ID propri, vanno verificati separatamente.

Test necessari: nomi e ID nelle 20 righe; classifica completa e parziale; aggiornamento/reordino mantenendo la squadra selezionata; nome lungo senza nascondere i punti; valori mancanti; tastierino e azioni; confronto Base/Apple Calm sullo stesso snapshot. Nessuna correzione con dati inventati nel QML.

Riferimenti: [sport_core.py](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/sport_core.py:195), [theme_api.py](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/theme_api.py:107), [Format.js](/home/giuseppe/Documenti/Workspace/SmartPC/theme-projects/apple-calm/bundle/qml/Format.js:43), [Main.qml](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/Main.qml:376).

## 4. Pallini: definire una sola grammatica di navigazione

Sono confermati tre limiti:

- I pallini esistono soltanto in `Shell.qml`. Gli overlay a schermo intero, con fondo opaco, sono sopra la shell e li coprono. `Panel`, dettagli e notifiche a pieno schermo non ricostruiscono quel sistema.
- La shell pubblica argomento e vista principale. Le schede dei dettagli usano invece `selection.tabId`/`tabs`; le pagine delle liste usano un contatore di righe. Sono tre concetti distinti e oggi non condividono un indicatore coerente.
- Casa introduce interazioni diverse: selezione di dispositivi e focus sulle schede. Le sue superfici usano il fallback e la geometria Base, mentre la shell Apple Calm resta quella del tema precedente. La matrice dei pallini precedente non copriva questi percorsi.

Non è dimostrato un errore generale nell'aritmetica dei contatori: i test esistenti passano sulle viste principali. Sono confermati copertura incompleta e significato diverso a seconda della schermata. La sincronizzazione durante il caricamento e le pressioni rapide richiede una nuova verifica.

### Regole proposte

| Situazione | Centro in alto | Margine destro |
| --- | --- | --- |
| Vista principale | Argomenti visibili, nell'ordine reale | Viste dell'argomento |
| Dettaglio con più schede | Argomento di origine | Schede del dettaglio; titolo della scheda visibile |
| Dettaglio singolo, menu o impostazione senza schede | Argomento di origine | Un solo punto, senza simulare altre viste |
| Lista lunga | Come per la schermata che la contiene | Viste/schede; lo scorrimento delle righe usa un indicatore di scorrimento separato |
| Casa | Argomenti visibili | Preferiti/Dispositivi; la selezione della riga non sposta i pallini |
| Avviso urgente a pieno schermo | Sospensione esplicita della navigazione | Sospensione esplicita, ripristino esatto alla chiusura |

I pallini non devono rappresentare una squadra, una riga o ogni elemento della lista. Un dettaglio con quattro schede mostra quattro punti anche se contiene venti righe. Le schede possono conservare una breve etichetta, senza ripristinare legende inferiori tipo `2/8 SCORRI` o `4/6 SCHEDE`.

Architettura proposta: componente di navigazione condiviso e snapshot pubblico unico con argomento, ambito locale, conteggio, ID selezionato e posizione. Il core determina le destinazioni; il tema le rende. Shell e composizioni degli overlay adottano lo stesso componente e riservano le stesse aree, mostrando una sola copia per schermata. Evitare di portare indiscriminatamente la shell sopra gli avvisi urgenti.

Animazione proposta: 120–160 ms in Normal, massimo 80 ms in Reduced, immediata in Off. Movimento fra punti solo nello stesso gruppo; al cambio argomento i punti laterali si riallineano al nuovo gruppo senza attraversare posizioni inesistenti. Titolo, contenuto e selezione diventano coerenti nello stesso commit. L'attuale ordine dei tasti dipende dalla route: l'indicatore segue lo stato effettivo, senza cambiare implicitamente i comandi.

Riferimenti: [Shell.qml](/home/giuseppe/Documenti/Workspace/SmartPC/theme-projects/apple-calm/bundle/qml/Shell.qml:1), [Panel.qml](/home/giuseppe/Documenti/Workspace/SmartPC/theme-projects/apple-calm/bundle/qml/Panel.qml:27), [NavigationDots.qml](/home/giuseppe/Documenti/Workspace/SmartPC/theme-projects/apple-calm/bundle/qml/NavigationDots.qml:1), [Main.qml](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/Main.qml:233).

## 5. Nuova vista Oggi: Orologio

La vista attuale divide il contenuto: circa 59% a orologio/evento e 41% alla grande scheda meteo. L'orario usa un testo nominale di 152 px, riducibile con `Text.Fit`. Ingrandirlo dentro quella colonna non soddisfa la richiesta di una vista dedicata.

Proposta: **terza vista Oggi “OROLOGIO”**, aggiunta a ORA e GIORNATA; per questa analisi la vista iniziale resta quella attuale. L'ordine proposto è ORA → OROLOGIO → GIORNATA. La nuova vista usa l'area 896×528 già disponibile:

```text
┌────────────────────────────────────────────────────────┐
│ OGGI                 ● ○ ○ ○ …                         │
│                                                        │
│                  Martedì 6 ottobre                     │
│                                                        │
│                     12:48                            ● │
│                                                      ● │
│                                                      ○ │
│                                                        │
│        ☀  22 °C · Sereno · località                     │
│        Fonte · stato · ultimo aggiornamento             │
│        Prossimo evento, soltanto quando esiste          │
└────────────────────────────────────────────────────────┘
```

Lo schema è indicativo; il numero dei punti dipende dai moduli visibili. Orario centrato, dimensione nominale **220–250 px** da verificare a 960×640 e con scala testo maggiore; numeri con avanzamento stabile. Data secondaria sopra; meteo compatto sotto, icona 32–40 px e temperatura 28–36 px. Nessun riquadro vuoto riservato a eventi assenti. Fonte e stato meteo restano leggibili; dati precedenti/offline non appaiono attuali.

Niente secondi o due punti lampeggianti come comportamento predefinito. La pagina deve restare statica fra cambi di minuto, dati e navigazione. Di notte si applicano palette e luminosità di sistema, senza creare un altro ciclo di animazione.

Il tema non può inventare autonomamente una nuova vista navigabile: occorre aggiungere la superficie proposta `home.clock` nel core, i riferimenti di navigazione, il contratto pubblico, il fallback Base, le fixture e la copertura del bundle. I dati di orologio e meteo sono già disponibili. La versione API deve seguire il contratto corrente 2.1 e l'estensione risultante, non il vecchio kit 0.6.6 preso isolatamente.

Riferimenti: [ClockPage.qml](/home/giuseppe/Documenti/Workspace/SmartPC/theme-projects/apple-calm/bundle/qml/ClockPage.qml:1), [Main.qml](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/Main.qml:495).

## 6. Conservare soltanto l'ultima versione

La pulizia non si risolve cancellando la directory della 1.0.0. Il lifecycle protegge **active, previous, pending e lease dei renderer**; il garbage collector mantiene per impostazione predefinita due revisioni. Anche `keep_per_theme=1` non eliminerebbe una vecchia revisione ancora protetta come `previous`.

Politica proposta, riferita ad Apple Calm:

1. Durante installazione e verifica del candidato, conservare temporaneamente la versione attiva per recuperare da un errore prima del completamento.
2. Dopo commit e verifica del nuovo tema, usare **Base come recupero stabile**, riallineare i riferimenti di configurazione e adattamento, quindi eliminare le revisioni Apple Calm precedenti quando non hanno lease vive. Una pulizia differita al rilascio delle lease completa il lavoro.
3. A regime il catalogo contiene **una sola Apple Calm**, la versione attiva verificata. Nascondere o rimuovere il controllo “revisione” quando la scelta è unica. “Ultima” significa installata e funzionante, non semplicemente la versione numericamente maggiore.
4. Nel progetto mantenere una sola sorgente del tema e nella consegna un solo pacchetto corrente, sorgenti correnti e checksum correnti. Eliminare le vecchie consegne e copie di preparazione soltanto dopo inventario delle dipendenze. Conservare rapporti sintetici utili; le vecchie immagini/fixture duplicate vanno valutate separatamente dalle fixture di test del core.

Non va introdotto un archivio nascosto permanente di vecchi temi. Un eventuale backup della transazione ha durata limitata; dopo la verifica non fa parte della normale conservazione. Le cache dei provider e le impostazioni personali non sono versioni del tema e non vanno coinvolte nella pulizia.

Riferimenti: [theme_lifecycle.py](/home/giuseppe/Documenti/Workspace/SmartPC/dashboard/theme_lifecycle.py:274).

## 7. Icone: significato distinto e sorgente unica

Esistono 42 disegni originali. Gli SVG di progettazione e `IconPaths.js` rappresentano gli stessi disegni in due formati; il runtime usa il secondo. Non sono 42 SVG caricati due volte dalla GUI, ma la manutenzione delle due copie deve avere una sorgente autorevole e una generazione deterministica.

La duplicazione semantica è confermata: la shell usa `flag` per ogni argomento diverso da Oggi, Meteo, Account e Serie A. Formula 1, MotoGP e Casa finiscono così con lo stesso simbolo. `settingIcon` lascia varie categorie sull'ingranaggio generico.

| Significato | Icona proposta |
| --- | --- |
| Oggi / vista Orologio | Orologio; calendario per Giornata |
| Meteo | Simbolo meteo coerente con la funzione/condizione |
| Account | Account o indicatore di utilizzo |
| Serie A | Pallone |
| Formula 1 | Monoposto, nuovo disegno |
| MotoGP | Moto, nuovo disegno |
| Casa | Casa con elemento di connessione, distinto dal comando Home |
| Classifica | Trofeo o podio |
| Squadra preferita | Stella/scudetto |
| Gara / traguardo | Bandiera a scacchi |
| Integrazioni | Connettore; sorgenti dati con simbolo dedicato |

Uno stesso significato deve riutilizzare la stessa icona: non serve un disegno diverso per ogni riga di partita o ogni pulsante “indietro”. Servono simboli diversi per funzioni diverse. Mappatura centralizzata per ID semantico, senza catene di fallback che trasformino Casa in una bandiera.

Scegliere una fonte vettoriale unica dalla quale generare l'output runtime necessario. Eventuali raster per la scheda saranno derivati di build, senza copie manuali per pagina/versione. Verificare distinguibilità a 24/32/40 px, contrasto giorno/notte e disponibilità di ogni ID. Preferire nuovi vettori coerenti con lo stile già usato, senza icone bitmap arbitrarie.

## 8. Implementazione proposta: una sola consegna 1.2.0

Le fasi seguenti sono tappe di lavoro, non versioni da conservare in parallelo.

| Fase | Risultato | Verifica che permette di avanzare |
| --- | --- | --- |
| A — correttezza e costo dei dati | Nomi/ID della classifica corretti; adattamento sportivo memorizzato; azioni coerenti | Confronto sui dati reali già in cache; nomi visibili; selezione mantenuta; costo caldo misurato |
| B — transizioni | Profilo dell'intero percorso; riuso mirato di renderer/delegate; una sola animazione | Navigazione fredda/calda su EGLFS, dati sportivi completi, tasti rapidi e aggiornamento durante il cambio |
| C — navigazione | Snapshot unico; pallini coerenti in pagine, dettagli, Casa e fallback | ID e posizione corrispondono al contenuto presentato; nessuna sparizione accidentale; Normal/Reduced/Off |
| D — Orologio e icone | Terza vista Oggi; meteo compatto; mappa semantica e sorgente grafica unica | Lettura sul pannello 960×640, giorno/notte, dati assenti/offline, nessuna animazione continua |
| E — consegna e pulizia | Nuova versione verificata; sola Apple Calm attiva; consegna corrente unica | Applicazione, recupero Base, rilascio lease, pulizia, riavvio e heartbeat fresco |

File coinvolti nell'implementazione: `dashboard/theme_api.py`, `theme_contexts.py`/modelli se richiesto dal profilo, `Main.qml`, adattatore e host QML, contratti e fixture generati, lifecycle/configurazione delle revisioni; nel tema `Format.js`, `Rows.qml`, composizioni, navigazione, icone e registry. Le modifiche ai file generati dal tema devono partire anche da `tools/assemble.py` e dai blueprint, altrimenti un nuovo assemblaggio ripristina il vecchio comportamento.

Il core contiene già il lavoro Casa 0.7.0-rc.2: l'implementazione dovrà basarsi su quel runtime e preservarlo. La copertura Casa va riallineata al tema senza introdurre nuovi provider o modificare il funzionamento delle integrazioni.

## 9. Acceptance e limiti delle prove

Misurare input ricevuto → destinazione coerente → frame presentato, separando prima apertura, ritorno caldo, apertura overlay e animazione. Usare il trace del core e strumentazione QML mirata; per l'adattamento pubblico aggiungere misure dove manca una span. Contare creazioni di renderer/delegate e aggiornamenti di contesto, non limitarsi ai secondi totali del test.

Obiettivi proposti, da confrontare con la baseline del percorso completo:

- Adattamento caldo della classifica, dati invariati: p95 ≤ 15 ms su un campione sufficiente; selezione senza normalizzazione della stagione. I circa 233 ms attuali sono il riferimento isolato, non il p95 della UI.
- Navigazione calda: primo frame coerente p95 ≤ 100 ms; conclusione della transizione entro 200 ms. Prima apertura: obiettivo entro 300 ms senza frame vuoti. Se non raggiunti, documentare il percorso che supera la soglia.
- Durante le animazioni: intervalli fra frame p95 ≤ 33,3 ms come obiettivo operativo, analizzando anche i ritardi maggiori. Questi intervalli non sono tempo GPU e non attestano da soli 60 FPS o latenza ottica.
- Tasti rapidi in entrambe le direzioni, cambio conteggio dinamico, ritorno dai dettagli e avviso urgente: destinazione finale, focus e pallini corretti, senza coda di transizioni obsolete.
- Classifica con nomi realmente renderizzati; nessun warning QML; Orologio senza ritagli con scala testo aumentata; fonte meteo e dati precedenti sempre distinguibili.
- Dopo consegna: servizio attivo, `NRestarts=0`, heartbeat fresco e coerente, nessuna transazione pendente; preferenze preservate; una sola revisione Apple Calm dopo rilascio delle risorse.

L'acceptance deve includere prova del tastierino reale e osservazione del pannello per giudicare la fluidità percepita. Questa analisi non ha eseguito tali prove né modificato la schermata live. Non serve ripetere un lungo stress test generale: servono prove mirate ai difetti individuati, confronto prima/dopo e un riavvio per verificare attivazione e pulizia.

La rimozione delle legende inferiori resta un requisito. Gli indicatori di fonte, errore e stato dei dati sono informazioni funzionali da mantenere, in forma compatta. Il lavoro è concluso solo quando correttezza e fluidità sono entrambe dimostrate sulla scheda, non quando la sola matrice di caricamento risulta verde.
