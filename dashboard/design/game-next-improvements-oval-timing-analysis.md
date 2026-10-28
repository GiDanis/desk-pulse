# Gioco — miglioramenti residuali e cronometraggio nell'ovale

**Attuazione autorizzata e consegnata nella rc.21:** [implementazione, prove e gate residui](v09-timing-improvements-report.md). Il testo seguente conserva la proposta originale; N1/N2 consegnati, N3/N4 parziali, N5 qualificato nel perimetro software nativo documentato.

**16 ottobre 2026 · analisi e proposta UX · nessuna modifica al runtime, ai piloti o alla scheda.**

Baseline documentata: [rc.20, consegna e limiti](v09-residual-implementation-report.md), 617 file, cinque piloti, ovale largo 12 m. Questa analisi legge il checkout e le evidenze della consegna; non aggiunge misure live, benchmark o risultati di apprendimento. Segue i residui R2/R5/R6 del [MasterPlan](release-masterplan.md).

## 1. Risultato proposto

Usare lo spazio interno dell'ovale per una **piccola plancia del pilota selezionato**, lasciando invariati pista, scala dell'auto e footer dei comandi:

- **Personale:** miglior giro pulito lanciato del pilota nel contesto compatibile.
- **Ultimo giro:** tempo dell'ultimo passaggio, anche se non valido, con stato esplicito.
- **S1 / S2 / S3:** scarti dei settori rispetto allo stesso giro personale di riferimento.
- Indicazione sintetica dell'origine: Qualifica, Gara o Campione in anteprima.

È fattibile nell'architettura corrente. I giri esistono già; i tempi intermedi dei settori richiedono nuove misure nel simulatore. La plancia aiuta a leggere la prestazione; il miglioramento dell'apprendimento richiede anche gli interventi separati descritti sotto.

[Concept vettoriale 960×640, dati illustrativi](concepts/game-oval-timing/oval-timing-concept.svg). Non è una schermata installata e non rappresenta i record personali correnti.

## 2. Riscontri nel codice

| Area | Già disponibile | Da aggiungere / limite |
| --- | --- | --- |
| `game_simulation.py`, `World.step/rows` | Tempo simulato, giri, pulizia, primo giro da fermo, tempi completi, massimo 64 giri recenti, `bestLap` | Nessun tempo intermedio dei settori; `bestLap` del mondo include anche giri puliti da fermo. |
| Validazione del giro | Quattro checkpoint ordinati e stato di giro invalido; attraversamento interpolato nel passo fisico | Questi quattro checkpoint non sono tre settori cronometrati; non cambiarli per ottenere tre colonne nella UI. |
| `game_geometry.py` | Lunghezza/pose e normali per i checkpoint esistenti | Gate generici del cronometraggio separati dai gate a quarti; intersezione direzionale e controllo della larghezza. |
| `game_records.py` | Record per pilota/configurazione e modalità, origine/policy; Qualifica esclude il lancio | Gara può registrare il primo giro da fermo; manca un riferimento persistente al giro completo con tutti i settori. |
| Worker e scena | Tutte le auto in Gara; policy selezionata, tempo simulato e tempi del mondo | Oggi i `lapTimes` recenti vengono inclusi nelle righe pubblicate: evitare ulteriore crescita del pacchetto per frame. |
| `game_residual_trainer.py` | Preview del campione distinta dal candidato, verifiche congelate, campione protetto | Il movimento visibile non mostra il candidato in raccolta; i suoi tempi non vanno confusi con apprendimento appena avvenuto. |
| Promozione Tattico | Tre prove solo e tre prove traffico, esiti per abilità | Decisione usa il totale riuscito nel traffico: può compensare una perdita in curva con una riuscita in un'altra abilità. |
| Rendering | Clock 30 Hz, geometria e auto in QML, temi condivisi | Nuovi testi devono essere leggeri, fuori dalla trasformazione delle auto e aggiornati senza ridisegnare la pista. |

## 3. Spazio e layout sul pannello

### 3.1 Dimensioni

Riferimento: screenshot nativi rc.20 **960×640**. L'area pista occupa circa `x=24, y=72, w=912, h=496`; con l'ovale corrente la scala nominale è circa 6 px/m. Il bordo interno ha ingombro **122×50 m**, ossia circa **732×300 px**, a forma di capsula.

Una plancia centrale iniziale **480×208 px** è geometricamente contenuta nell'isola, con margine anche agli angoli: non serve rimpicciolire la pista. Il rettangolo di ingombro dell'isola da solo non garantisce che ogni suo angolo sia libero: verificare il contenimento nella capsula e la scala effettiva della camera. I numeri sono una verifica geometrica del layout, non una prova di leggibilità fisica.

### 3.2 Gerarchia

1. Nome del pilota e origine dei dati, una riga.
2. Due colonne: Personale e Ultimo giro; cifre allineate, font numerico del tema.
3. Tre colonne S1/S2/S3 con delta firmato. Esempio: `−0,080`, `+0,120`, `+0,170`.
4. Una sola nota di riferimento: `Δ vs giro personale`. Quando assente: `Primo giro lanciato` / `Settori da misurare`.

Cifre principali candidate 32–36 px, testi 20–22 px, delta 22–24 px; rispettare textScale, night/day, motion e token del tema. Confermare sul display da 3,5 pollici alla distanza d'uso, senza assumere che lo screenshot sul PC dimostri leggibilità. Niente tabella di cinque piloti, grafici continui o descrizioni estese al centro.

### 3.3 Colori e interazioni

- Segno e numero sempre leggibili: miglioramento `−`, peggioramento `+`, assenza `—`. Il colore è un rinforzo, non l'unico significato.
- Usare i ruoli semantici dei temi; evitare una nuova palette fissa rosso/verde o il viola “record” non appartenente al sistema.
- Nessun tasto aggiuntivo: 4/6 cambia pilota in Gara e aggiorna la plancia; 2/8 conserva le camere; 5 conserva Start/Pausa e salvataggio.
- Plancia senza area cliccabile; non intercetta input. Nessun lampeggio o animazione delle cifre obbligatoria.
- Giro invalido: mantenere il tempo e aggiungere `Non valido`; niente PB aggiornato e niente delta verde celebrativo.

### 3.4 Visibilità sicura

Solo `oval-1`, vista globale con area interna verificata. In Sensori proporre plancia nascosta, per non coprire i raggi. Nei circuiti complessi o nelle camere ravvicinate non inferire spazio libero dal centro del bounding box: fallback compatto nel pannello dati, senza overlay sulla pista.

Auto e numeri delle vetture hanno priorità grafica. Una vettura fuori pista può attraversare l'isola: renderizzarla sopra la plancia e nascondere/ridurre la plancia se il suo ingombro occupa la zona dei testi. Non mascherare un incidente per mantenere leggibile il cronometro. Pausa mantiene gli ultimi dati confermati; reset/salto di episodio azzera il giro in corso, senza ripresentare settori dell'episodio precedente.

## 4. Significato esatto dei tempi

### 4.1 Tre riferimenti distinti

| Riferimento | Significato | Presentazione |
| --- | --- | --- |
| PB personale persistente | Miglior giro **pulito e lanciato** del pilota, tra sessioni compatibili di Qualifica/Gara | “Personale”; origine disponibile nel dossier. |
| Migliore della sessione | Miglior giro lanciato della sessione, della versione attualmente in uso | Dettaglio o riferimento selezionabile successivo; non sostituire silenziosamente il PB storico. |
| Migliore in anteprima | Giro del campione visibile nell'allenamento, non certificato ufficiale | “PB anteprima”; separato da Qualifica/Gara. |

Non mescolare allenamento, verifiche accelerate, preview e gara per ottenere un record apparentemente più rapido. In anteprima i giri possono migliorare anche per gomme/velocità iniziale/stato del controllore, pur con pesi invariati: mostrare “Campione in anteprima”, non “AI migliorata”. Il progresso appreso continua a derivare dalle verifiche indipendenti.

Il PB persistente è personale, quindi può appartenere a una policy precedente. Conservare hash e origine; non fingere che il modello corrente l'abbia ottenuto. Dopo un reset delle correzioni lo storico può restare consultabile, con indicazione “modello precedente”; il confronto con la versione attuale va dichiarato. Il PB non concede né rinnova una qualifica.

### 4.2 Chiave di compatibilità

Pilota + geometria/revisione pista + auto + gomme + fondo/condizioni + fisica + regole di giro + **layout/versione dei settori** + tipo di partenza. Metadati: sessione, modalità, policy/base/compositore, origine e data. Variare la rete non cancella il PB personale ma cambia la provenienza; variazioni fisiche o del layout aprono un riferimento diverso.

La ricetta di apprendimento non basta a stabilire che due giri siano confrontabili. Conservare le categorie esistenti: non sovrascrivere i vecchi record Gara che ammettevano il giro da fermo. Il nuovo cronometraggio deve usare un protocollo esplicito e può filtrare i dati storici solo quando ne conosce gli attributi.

### 4.3 Ultimo giro, lancio e invalidità

- Il primo passaggio da fermo appare come `Lancio`, con il suo tempo; escluso da PB e confronti di giro lanciato.
- Dopo il traguardo, Ultimo giro resta visibile fino al successivo completamento. Un giro invalido resta visibile e marcato.
- Nessun giro terminato: `—`, senza zeri inventati.
- Ritiro a metà giro: mostrare lo stato del giro interrotto; l'ultimo giro completo non viene sostituito da un tempo parziale.
- Cambio pilota mostra il suo record e il suo giro, mai quelli dell'auto selezionata prima.
- Tempi autorevoli dal simulatore; pause e rallentamenti grafici non entrano nel tempo sul giro.

## 5. Settori e delta

### 5.1 Scelta proposta

**Tre settori cronometrati**, inizialmente a `L/3`, `2L/3` e al traguardo dell'ovale; lunghezza totale circa 338,78 m, quindi circa 112,93 m per settore. Sono settori sintetici del nostro ovale, non settori di un circuito reale. Ogni futura pista può dichiarare distanze diverse nel catalogo e una revisione propria.

I quattro checkpoint attuali restano per l'integrità del giro. Il nuovo rilevatore di timing ha uno stato separato. Se le prove dimostrassero che quattro intertempi sono più utili didatticamente, la scelta può essere rivista **prima** di pubblicare record con il nuovo schema, non a metà di una sessione.

### 5.2 Misura

Attraversamento del gate nel verso giusto, entro la sezione della strada; interpolazione temporale nel substep fisico e avanzamento ordinato. Niente tempi calcolati dalla coordinata dello sprite o dalla ricezione del pacchetto QML. Gestire attraversamenti multipli nello stesso step, wrap del giro e inizio griglia dietro il traguardo.

`S1=t1−tStart`, `S2=t2−t1`, `S3=tFinish−t2`; la somma deve coincidere col giro entro la tolleranza numerica dichiarata. Il delta del settore è `S_i attuale − S_i riferimento`; il delta cumulativo è un'altra quantità e deve avere un nome diverso.

Tre decimali sono il formato del risultato interpolato, non la prova di esattezza fisica al millisecondo. Eventuale giro corrente in futuro: aggiornamento a 10 Hz, decimi; niente animazione di millisecondi.

### 5.3 Riferimento congelato per giro

All'inizio del giro congelare **l'intero giro PB di riferimento**, incluso ID/policy/layout e i tre settori. Non confrontare S1 con il PB vecchio e S2 con un PB aggiornato durante il giro.

Al completamento mostrare il delta rispetto al riferimento che era attivo. Se arriva un nuovo PB: aggiornare il record, mantenere il delta della prestazione appena conclusa con dicitura `vs PB precedente`, poi adottare il nuovo riferimento al prossimo giro. Così si evita `0,000` proprio quando si migliora.

Settore non ancora completato: `—`/indicatore neutro. Settori completati restano visibili fino al giro successivo, con numero del giro; per il giro in corso sostituire progressivamente le colonne senza mescolare righe non etichettate. Decisione iniziale: mostrare i settori del giro in corso dopo il primo attraversamento, mantenendo Ultimo giro separato; giro/reset ID sempre presente nel dato.

### 5.4 Migliori settori e giro ideale

Nel dettaglio futuro si può sommare il migliore S1/S2/S3 ottenuto in giri diversi: è un **Giro ideale**, non un tempo effettivamente realizzato e non entra in classifica o qualifica. Prima versione: delta contro i tre settori dello stesso PB, senza giro ideale nella plancia.

Promuovere PB e migliori settori soltanto dopo che l'intero giro risulta valido. Un S1 pulito seguito da un taglio in S3 non deve aggiornare il record in questa prima ricetta. Vecchi giri senza settori restano record di giro con intertempi `—`: non ricostruirli dividendo il tempo per tre. Attendere un nuovo giro con telemetria completa per un riferimento settoriale utilizzabile, senza perdere il PB storico.

## 6. Contratto dati e persistenza proposti

Nuovo oggetto `timing`, versionato e additivo, per vettura; proiezione compatta della sola auto selezionata nella UI:

- `version`, `sectorLayoutId`, `timingContextHash`, `driverId`, `policyHash`, `source` (race/qualifying/preview), `runId`, `lapId`/`resetKey`, `revision` monotona.
- Giro corrente: stato/partenza, secondi simulati, settore attivo, validità e motivo.
- Ultimo giro: durata, tre settori opzionali, validità e origine.
- Riferimento: record ID, durata, settori opzionali, policy/origine, tipo e compatibilità.
- Delta per settore con ID del giro/riferimento; dati mancanti `null`. Nessun `0` usato come assenza.

Backend dedicato candidato `game_timing.py`: calcolo/stato nel Worker, niente SQLite o accesso disco nel ciclo fisico. `World.snapshot/restore` conserva stato dei gate, tempi, validità e riferimento; schema retrocompatibile per snapshot senza timing, che riprendono senza intermedi ricostruiti.

Persistenza con tabella/protocollo dedicato o estensione versionata dei record, da scegliere dopo verifica delle migrazioni. Salvataggio atomico su giro confermato e Pausa, con vincolo di unicità per sessione/pilota/giro: niente doppio credito al replay di un evento. Scritture/invio asincroni non devono interrompere la preview. Un salvataggio non confermato non va indicato come persistente.

Eventi affidabili di giro/settore per archivio; scena lossy “ultimo stato” per la GUI: la perdita di un frame non perde un record. Pubblicare tre settori e due tempi, non duplicare 64 giri di storia a ogni frame. Prima fase additiva; rimozione di vecchi campi soltanto dopo aver censito i consumer.

## 7. Miglioramenti dell'apprendimento da implementare in seguito

### 7.1 Promozione per abilità — priorità alta

Riscontro rc.20: Tattico congelato 20/20 sorpassi semplici e difese, **10/20 in curva contro 15/20 della base**. Non compensare una regressione in curva con un successo in rettilineo.

- Confronto separato solo, rettilineo, curva, difesa, sicurezza; soglia minima/non regressione per ciascuna famiglia.
- Banca di sviluppo stratificata più ampia; banca finale nuova e non usata nella taratura. I seed finali già osservati non diventano una nuova verifica indipendente dopo che li si usa per correggere la policy.
- Conservare il campione per contesto/abilità con esito comprensibile; successo diagnostico non concede automaticamente Qualifica.
- Verifica preliminare economica di sicurezza, poi confronto completo quando utile; mai promuovere da una sola prova più veloce. Misurare anche i candidati validi scartati e il costo per accettazione.

### 7.2 Curva con avversario: diagnosi prima dei pesi

Loggare ingresso curva, velocità e frenata reali, linea richiesta/eseguita, gap longitudinale/laterale, ingombri, limite del compositore e causa dell'insuccesso. Separare: nessun passaggio entro la fine dell'esercizio, blocco prudenziale, ritiro, uscita e manovra illecita.

Confrontare tre casi sullo stesso scenario: Maestro, residuo solo passo, residuo linea+passo. Verificare se la maggiore velocità peggiora l'affiancamento o se la linea viene annullata da un limite del controllo. Ampliare sensori o rete solo se manca una variabile causale: i ruoli dei rivali e le velocità relative esistono già nei 90 ingressi.

Possibili interventi da confrontare, non nuovi default già scelti: velocità di riferimento coerente col corridoio laterale, passaggio completabile entro la distanza dell'esercizio, varietà di linee/velocità degli avversari e ripasso del solo. Non allargare nuovamente la pista per nascondere un difetto del pilota.

### 7.3 Incentivi e regole R2

Banca: fermo, taglio, crash rapido, gas continuo in curva, frenata corretta, frenata arbitraria, zig-zag, affiancamento con spazio, rientro, doppio sorpasso artificiale. Verificare ordine dei ritorni, terminali, unicità del credito e motivi di invalidità.

Due punti del codice meritano una misura specifica:

1. La scala del progresso e il bonus terminale cambiano fra esercizio breve `impara` e modalità continue. Studiare se esperienze miste nel replay producono obiettivi poco coerenti; una differenza non prova da sola un bug. Confrontare normalizzazioni in unità fisiche e versionare la ricetta se cambia.
2. Il rilevatore di frenata arbitraria guarda circa 100 m in avanti; i rettilinei del nostro ovale sono lunghi 72 m. Verificare copertura e falsi positivi; possibile orizzonte adattato a velocità, aderenza e distanza di arresto, senza punire una frenata necessaria prima della curva.

Regole di spazio fondate su ingombro e sovrapposizione, senza attribuire intenzioni non osservabili. Nessun nuovo premio positivo per aver “richiesto” una traiettoria o per il solo gas. La telemetria dei settori nasce come misura: non aggiungere subito tre bonus che possono alterare l'obiettivo e incentivare tagli.

### 7.4 Memoria e leggibilità del progresso

Infinito: distinguere giri puliti, finestre di raccolta, episodi interrotti e verifiche riuscite; una finestra conclusa non è una prova fallita. Dossier con seed/ricetta, dati nuovi, aggiornamenti, costo delle verifiche e confronto candidato/campione. Le prove settoriali non sostituiscono la banca di apprendimento indipendente.

Conservare piloti e checkpoint attuali. Qualsiasi nuova osservazione/azione/reward incompatibile richiede migrazione dichiarata, ramo sperimentale e rollback; niente reset globale preventivo o reinterpretazione del replay.

## 8. Fluidità e carico

Baseline rc.20: campione software nativo a cinque vetture, media vicina a 30 Hz, p95 circa 39–45 ms e massimo 52–73 ms; harness con `processEvents`, non misura ottica. Non trasferire le vecchie misure Evo/32 al nuovo carico di un allievo.

Prima del cambiamento: stesso seed/policy/scena, campione rappresentativo del vero event loop Qt, auto in movimento dopo countdown, fasi raccolta/update/verifica/salvataggio. Misurare intervalli di frame, punti fisici presentati, ritardo dei pacchetti, durata delle verifiche e salvataggi maturi, CPU/core/termiche, non solo FPS medi.

HUD: aggiornamento PB/ultimo/settori a evento; eventuale giro corrente al massimo 10 Hz, cifre in box di dimensione stabile. Calcolo settori nel Worker, non QML a 30/60 Hz; nessun Canvas per un grafico continuo, shadow, blur o variazione dei delegate auto. CPU per simulazione/rete, GPU per rendering; nessun bisogno NPU introdotto dai cronometri.

Confronto A/B HUD spento/acceso sulle stesse scene: ordine ABBA, campioni candidati da almeno 120 s in Gara a cinque vetture dopo il countdown, con seed/policy congelati; campioni separati del training per raccolta, update, verifica e salvataggio maturo. Controllare deriva termica e variabilità del carico, senza confondere un intervallo che non contiene verifiche con il costo dell’intera sessione. Criterio candidato: nessun aumento del p95 maggiore di max(2 ms, 5%) rispetto alla baseline abbinata, nessun nuovo gruppo di stalli correlato al settore/giro, nessun peggioramento della cadenza dei veicoli. Soglia da fissare prima delle misure; non è un risultato già ottenuto. Se il rumore la copre, ripetere il confronto mirato, non dichiarare parità.

Spostare o batchare verifiche solo dopo profilo del carico e prova di equivalenza di physics/RNG/ripresa; non parallelizzare il training della medesima policy con pesi mobili durante la verifica. Nessuna promessa di 60 fps o di accelerazione NPU.

## 9. Sequenza eseguibile

| Fase | Lavoro | Accettazione |
| --- | --- | --- |
| N0 · baseline | Snapshot su copie e misure del carico nuovo; preservare dati | Stato/contesto riproducibili, origine di ogni metrica. |
| N1 · timing | Protocollo giri/settori, gate generici, stato e persistenza | Somma settori=giro; direzione/validità/ripresa e unicità corrette; nessuna variazione ai quattro checkpoint. |
| N2 · UX | Plancia ovale, origine/PB/ultimo/delta, assenza e invalidità | Pista/scala/auto immutate, tutte le auto visibili, zero/assente distinti, selezione e tasti coerenti. |
| N3 · protezioni | Diagnostica curva, banca R2, promozione per famiglia | Nessuna regressione accettata fra abilità; fallimenti motivati; campione preservato. |
| N4 · confronto | Una modifica per esperimento, budget congelato e cinque seed abbinati | Beneficio su banca indipendente e affidabilità non degradata; confrontare anche Maestro. |
| N5 · pannello/consegna | Base/Functional/Apple, day/night, textScale, A/B prestazioni, installazione e rollback | Nessun warning QML, contatori conservati, assenza di auto coperte, prove native con perimetro esplicito. |

N1–N2 possono essere consegnati come incremento UX senza aspettare tutta la ricerca N3–N4. Non legare la prima plancia al requisito che ogni metodo abbia imparato perfettamente i sorpassi. Resta richiesta autorizzazione all'implementazione prima di cambiare runtime o board.

## 10. Mappa delle modifiche previste

- `game_catalog.py` / geometria: layout dei tre settori con ID/revisione, gate generici; descrittore di area interna sicura solo per ovale.
- Nuovo `game_timing.py`, `game_simulation.py`: attraversamenti e cronometraggio, righe compatte, snapshot/ripresa; evitare dipendenza del timing dal rendering.
- `game_worker.py`, `game_residual_trainer.py`: distinguere source/policy della preview, eventi di timing persistenti e proiezione selezionata.
- `game_store.py`, `game_records.py`: PB/versioni/settori, migrazione non distruttiva, record storici senza intermedi e chiave di contesto.
- `game.py`, contesto pubblico Theme API e fixture: oggetto tipizzato/additivo, null validi e tutte le modalità; audit del contratto prima di scegliere la revisione API. Nessuna nuova superficie o comando solo per disegnare i tempi.
- `GameVisual.qml` o componente condiviso: layout con token/tema, z-order delle auto, riduzione/nascondimento nei casi previsti, niente calcolo fisico.
- `game_racecraft.py`, reward/trainer: diagnosi e miglioramenti N3–N4 in ricette versionate, separati dalla prima plancia.

## 11. Prove mirate richieste

Timing: lancio escluso, tre attraversamenti, giro valido/non valido, giro interrotto, avanti/indietro sul gate, attraversamento fuori sezione, duplicato/out-of-order, frame saltati, pausa/ripresa a metà settore, selezione auto, layout/contesto incompatibile, checkpoint vecchio senza settori, PB di policy precedente, aggiornamento PB senza delta azzerato, giro ideale mai classificato.

UX: cinque vetture, bordo estremo/auto nell'isola, sensori, zoom, mancanza PB/settori, tempi lunghi, delta negativo/positivo, textScale, temi notte/giorno, leggibilità fisica a 3,5 pollici. Non usare solo screenshot PC come accettazione sul pannello.

Apprendimento: esiti per ogni abilità, non solo totale; banca finale nuova; nessun tuning usando ripetutamente il set finale. Se si modificano premi/controllore/sensori, rivedere compatibilità delle qualifiche e preservare il rollback del campione.

## Decisione proposta

**Procedere prima con cronometraggio affidabile e plancia centrale compatta**, poi migliorare promozione, regole e guida in curva sulla base dei dati. Nessun nuovo pilota richiesto. Obiettivo: capire cosa fa il pilota giro dopo giro, senza perdere pista, leggibilità o fluidità e senza attribuire alla rete prestazioni che appartengono al Maestro.
