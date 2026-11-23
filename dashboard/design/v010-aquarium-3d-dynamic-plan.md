# Acquario 3D dinamico — piano esecutivo

**Revisione 4 · 29 ottobre 2026 · Europe/Rome · candidata0.10.2-rc.4 installata, qualifica estesa aperta.**

Specifica di riferimento: [analisi di integrazione](v010-aquarium-3d-dynamic-analysis.md). Baseline riletta: core 0.10.1-rc.1 installato, Apple Calm 1.6.5, API 2.13 / 69 superfici. Il nuovo sorgente espone API 2.14 / 71 superfici. [Implementazione, misure e limiti](v010-aquarium-3d-dynamic-implementation-report.md): prove isolate PC/ARM/EGLFS svolte. [Consegna0.10.2-rc.2](v010-aquarium-3d-installation-report.md) completata su autorizzazione successiva:548 file/API2.14 sulla board.

## 1. Decisioni acquisite e default tecnici

| Decisione | Stato |
| --- | --- |
| Vero 3D, pesci curati, 50–55 fps accettabili; 60 non obbligatori. | Richiesta esplicita dell’utente. |
| Catalogo estendibile, scelta dei tipi, informazioni conservate e sostituzioni dopo N giorni. | Richiesta esplicita dell’utente. |
| Giorni trascorsi anche con acquario chiuso o board spenta. | Confermato dall’utente in questa analisi. |
| Giorno = 24 ore, istanti UTC; nuova permanenza dal commit, riconciliazione senza riprodurre cambi mai mostrati. | Convenzione tecnica proposta e documentata. |
| Quattro tipi iniziali, sei pesci nominali; composizione modificabile entro il profilo qualificato. | Default di lavoro da verificare con il campione artistico. |
| Pesci fissi o a durata, successore scelto o da gruppo automatico; storico degli individui. | Perimetro proposto della prima funzione completa. |
| Nuove superfici `aquarium.3d` e `aquarium.manage`, contratti 2D conservati. | Scelta architetturale proposta, API candidata 2.14 / 71 superfici. |
| Prossima candidata della linea 0.10; Compagno alla 0.11. | Numero da assegnare dopo riallineamento del checkout, che contiene lavori concorrenti 0.10.1-rc.1; nessun incremento effettuato qui. |

## 2. Ordine dei lotti

L’implementazione è stata autorizzata il 29 ottobre. La tabella seguente conserva la definizione dei lotti; lo stato aggiornato è riportato sotto. D0 e D1 evitano di costruire l’intero configuratore su un percorso asset non adatto alla board. D2 e D3 possono essere sviluppati e verificati su PC con clock e asset finti; D4 li integra con il renderer scelto.

| Lotto | Lavoro concreto | Dipendenze | Criterio di completamento |
| --- | --- | --- | --- |
| **D0 · Preflight e contratti** | Rileggere baseline/tema/Qt/refresh/governor reali quando iniziano le prove; congelare schema catalogo, schema store, DTO, unità, durate e gate; definire affidabilità dell’orologio. Inventariare moduli ARM, importer e toolchain. | Analisi presente. | Schemi e protocollo versionati; differenze dalla baseline esplicite. Nessun uso implicito dell’overlay sperimentale come runtime installato. |
| **D1 · Un pesce finale** | Produrre un modello curato con sorgente, rig, materiale, miniature e ciclo; validare GLB e conversione Qt. Confrontare rig con poche ossa e deformazione procedurale solo su questo campione; mostrare frontale/laterale/virata a dimensione reale. | D0. | Aspetto valutabile, rig scelto e prova isolata PC/ARM di un pesce e sei copie; confronto qualità/costo documentato. La sonda geometrica non chiude il lotto artistico. |
| **D2 · Catalogo e archivio** | Loader schema 2, manifest e validatore; registro generato; store SQLite, migrazioni, pesci/posti/permanenze/storico, revisioni e comandi idempotenti. Mantenere percorso schema 1. | D0; contratto D1 per i rig. | Aggiungere una specie compatibile senza modificare servizio/renderer; salvataggio/ripresa e conservazione della storia provati su dati isolati. |
| **D3 · Calendario e rotazione** | Riduttore puro con clock/RNG iniettati, scadenze, selezione, riserve, cambi in attesa e riconciliazione al boot/rientro. Preparazione e commit separati. | D2. | Tempi, assenze, errori e crash deterministici; nessun doppio ingresso e nessun soggiorno fittizio. |
| **D4 · Scena 3D e popolazione** | Renderer dedicato, volume XYZ, rig e clock unico, diff per identità, cache e preparazione del successore, transizioni, lifecycle/ACK. | D1–D3. | Sostituire un pesce senza resettare gli altri; pausa, urgenti, tema e Reduced/Off corretti; errori recuperabili. |
| **D5 · Gestione e Theme API** | Nuovi contesti/superfici/azioni, routing/menu e gestione Pesci/Catalogo/Rotazione/Storico, schede e bozze; generazione SDK/fallback nei tre temi. | D2–D4. | Intero percorso da tastierino, stato persistente, comandi validati e conflitti di revisione gestiti. API precedente ancora compatibile. |
| **D6 · Catalogo finale e qualifica** | Portare a quattro tipi curati; carichi misti, aggiunta di un quinto tipo tramite soli asset/dati, rientri e sostituzioni, prove nominali e sessioni lunghe con fonti dashboard. | D4–D5. | Aspetto e nuova soglia 50–55 valutati sugli asset finali, nessuna crescita progressiva; report dei residui. |
| **D7 · Consegna candidata** | Backup, migrazione su copia, manifest dipendenze ARM, installazione riproducibile, controllo della GUI e rollback; aggiornare versioni, ricevute e MasterPlan solo all’esito reale. | D6 e perimetro di consegna autorizzato. | Preferenze/temi/Gioco conservati; artefatto identificato, salute verificata e limiti ottici/live dichiarati. Reboot solo se parte della prova autorizzata. |

## 3. File e punti di intervento

Percorsi relativi alla root del progetto; la tabella conserva il perimetro iniziale. I file effettivi e le responsabilità consolidate sono descritti nel report di implementazione.

| File o area | Intervento previsto |
| --- | --- |
| `dashboard/aquarium.py` | Orchestrazione dello stato persistente, revisioni distinte e comandi; mantenere il lifecycle corrente. Nessuna creazione fissa di sei pesci in `_publish()`. |
| `dashboard/aquarium_catalog.py` | Loader schema 1/2, metadati separati dagli asset residenti, risoluzione dei riferimenti e rig compatibili. |
| `dashboard/aquarium_store.py` — nuovo | Connessione proprietaria, migrazioni, transazioni, vincoli, snapshot di schede e operazioni idempotenti. |
| `dashboard/aquarium_rotation.py` — nuovo | Funzioni pure per scadenze, eleggibilità, selezione e riconciliazione. |
| `dashboard/aquarium_models.py` — nuovo | Modello per identità della popolazione e proiezioni paginate di catalogo/storico; nessun traffico di pose per frame. |
| `dashboard/assets/aquarium/calm-3d-v1/` — nuovo | Catalogo, quattro tipi, risorse Qt convertite, ambiente, miniature, manifest e qualifiche per digest/profilo. |
| `dashboard/presentations/aquarium-3d.qml` e `aquarium/Aquarium3DVisual.qml` — nuovi | Entry point pubblico e scena 3D; import QtQuick3D confinato al percorso dedicato. |
| `aquarium/Fish3DActor.qml`, `Fish3DRig.qml`, `AquariumMotion3D.js` — nuovi sotto presentations | Separare identità/locomozione, rig comune e matematica; diff della popolazione e transizioni. |
| `dashboard/presentations/aquarium-manage.qml` e componenti di gestione — nuovi | Liste, schede, bozze, durata e gruppo; stile/focus/comandi condivisi. |
| `dashboard/Main.qml`, `app.py`, `state.py` | Nuove destinazioni, menu, payload e broker; costruzione/chiusura del servizio e disponibilità del percorso 3D. |
| `dashboard/theme-api/{contexts,surfaces,actions}.json` | DTO 3D e gestione, due nuove superfici, azioni con ID e revisione; nessun campo 2D riutilizzato con altro significato. |
| `theme_contexts.py`, `theme_api.py`, `theme_api_contract.py`, generatore e registry | Generazione/registrazione dei contratti, diff, limiti e fallback; verificare se servono adattamenti del trasporto. |
| `dashboard/theme_bundle.py` | Ammissione additiva dei fallback per le due nuove superfici nell’elenco già usato da `aquarium.main`; prova con bundle storici senza mutarli. |
| `components/PublicContextAdapter.qml` | Solo eventuali proiezioni mirate richieste dai nuovi contesti; nessun modello globale per la scena. |
| Temi builtin, Apple Calm e authoring kit | Fallback per nuove superfici, fixture e template; nuove identità di bundle solo se cambiano i file del bundle, senza modifiche in posto a versioni installate. |
| `dashboard/check_aquarium_*.py` e nuove fixture | Estensioni mirate per store, calendario, azioni/UI e rig; preservare test del percorso 2D. |
| Script authoring/benchmark — nuovi | Validazione/conversione asset e prova con `QApplication.exec()` normale, workload e digest registrati. Nessuna esecuzione automatica su dati utente. |

## 4. Scenari funzionali da provare

| ID | Scenario | Esito richiesto |
| --- | --- | --- |
| F01 | Primo accesso e secondo avvio | Store creato una volta; identità e nomi conservati, niente duplicati. |
| F02 | Nuova specie | Nuovo pacchetto/scheda compatibili compaiono nel catalogo e sono selezionabili senza cambiare codice del motore. |
| F03 | Sostituire un solo pesce | Gli altri mantengono attori, fase e traiettoria; lo storico del precedente resta consultabile. |
| F04 | Giorno 6, giorno 7 e stesso evento ripetuto | Il cambio avviene alla scadenza definita; ripetere riconciliazione/azione non duplica ingressi. |
| F05 | Board spenta oltre più durate | Un solo nuovo soggiorno per posto scaduto al ritorno; nessuna storia inventata dei periodi non mostrati. |
| F06 | Orologio indietro, avanti, fuso e cambio ora | Nessun doppio cambio; scadenze UTC conservate, nuova decisione sospesa se il tempo è inaffidabile. |
| F07 | Scadenze simultanee | Riserva comune, rispetto di copie/cooldown/capacità, preparazione seriale. |
| F08 | Gruppo vuoto, unico tipo o tutti esclusi | Stato in attesa leggibile; pesce corrente conservato, niente loop di sostituzione. |
| F09 | Posto fisso, modifica durata/gruppo | Fisso escluso dal calendario; ricalcolo esplicito dalla data di ingresso; modifiche al gruppo non cancellano pesci/storia. |
| F10 | Errore modello/I/O e risposta tardiva | Nessuna perdita del pesce corrente prima del commit; revisione cambiata invalida il candidato. |
| F11 | Crash prima/dopo commit | Riapertura coerente con la transazione, una permanenza corrente e nessun ingresso duplicato. |
| F12 | Pausa, menu, urgente, cambio tema | Clock visuale fermo e ripresa coerente; scadenza matura senza passaggio visivo sotto un urgente. |
| F13 | Nome/variante cambiati e ritorno di un individuo | Identità stabile; nuovo soggiorno distinto e passato leggibile. |
| F14 | Asset aggiornato/rimosso e schema 1 | Versioni referenziate conservate; errore controllato se mancanti, vecchio renderer 2D ancora apribile. |
| F15 | Tastierino, Home/Avvisi e bozze | Focus visibile; uscita sempre disponibile, bozza non salvata non applicata per errore a un altro pesce. |
| F16 | Capacità e qualità | Scene fuori dal profilo non applicate silenziosamente; niente rimozione di pesci scelti o riduzione nascosta della qualità. |

I test di giorni usano un clock simulato: non occorre aspettare settimane. Le prove native delle transizioni verificano il carico reale, non sostituiscono la correttezza temporale dei test deterministici.

## 5. Protocollo prestazionale e visivo

Prima delle prove fissare asset/digest, numero e mix di pesci, risoluzione, luci, rig, varianti, stato del catalogo e provider concorrenti. Rilevare Qt, driver, refresh reale dichiarato dallo stack e configurazione del sistema. Usare l’event loop normale della dashboard; conservare separatamente lo storico del precedente banco.

1. Un modello finale: viste di controllo, nuoto/virata, primo caricamento, pausa e sei copie indipendenti. Non misurare soltanto una posa statica.
2. Profilo nominale: sei pesci dei quattro tipi, tre repliche da almeno 120 s dopo 60 s di riscaldamento, dati grezzi e finestre di 1/10 s; confrontare anche il 2D storico senza attribuirgli i nuovi asset.
3. Scalabilità: 1/4/6/8/16 pesci come screening, con mix omogeneo ed eterogeneo. Solo le composizioni superate entrano nei profili di prodotto.
4. Popolazione dinamica: almeno venti rientri, trenta sostituzioni programmate accelerate, cambio di ogni tipo e ripetizione del ciclo; risorse stabili dopo il riscaldamento e nessuna cache illimitata.
5. Sessione di almeno 30 min con scena finale, provider/clock/avvisi e salvataggi; sessione mista di 60 min per uscita, riapertura, temi e recupero. Le fonti riprodotte e quelle live sono annotate separatamente.
6. Valutazione fisica del display: volume, leggibilità, virate, differenze giorno/notte e cadenza percepita. Un video della board è evidenza visiva; una misura di FPS ottici richiede acquisizione e metodo adeguati, separati dai callback.

Il gate candidato è quello dell’analisi §10: obiettivo ≥55, minimo ≥50 nelle finestre attive di 10 s, pose coerenti, p95 ≤35,5 ms/p99 ≤40 ms sul profilo a 60 Hz, stalli isolati e interazione pronta. Osservare revisioni delle pose effettivamente inviate al rendering, non soltanto il conteggio del clock QML. Se il display effettivo ha altro refresh, congelare una soglia coerente prima di iniziare. Non modificare le soglie a posteriori né applicarle retroattivamente alla sonda precedente.

## 6. Ordine di semplificazione se il modello finale costa troppo

Prima profilare: thread, binding/rig, import/caricamenti, risorse e compositing. Poi confrontare riduzione di parti/materiali e risorse duplicate, cache del prossimo pesce, geometria/texture coerenti con la dimensione visibile. Instancing o shader specifico solo se risolvono un costo misurato e preservano fasi e qualità.

Effetti aggiuntivi restano spenti finché il profilo base non è qualificato. Una qualità 3D più leggera può essere un preset dichiarato e verificato; cambiare modello artistico o ridurre il numero scelto richiede una scelta visibile, non un comportamento nascosto. Il recupero tecnico al 2D resta disponibile durante la migrazione, mentre la nuova funzione di prodotto punta al vero 3D.

## 7. Uscita e documentazione

L’implementazione è completa quando il catalogo cresce tramite pacchetti compatibili, l’utente sceglie i tipi, ogni pesce conserva identità e storia, il calendario sopravvive a riavvio/assenza e la scena finale soddisfa qualità e prestazioni dichiarate. Devono esistere ricevute distinte per test PC, prove native, verifica fisica e installazione.

### Stato al 29 ottobre

| Lotto | Stato verificato |
| --- | --- |
| D0 | Contratti, baseline installata e dipendenze ARM rilevati. Sei dipendenze estratte, non installate. Corretto il disallineamento EGL/GLES nella prova e predisposto il launcher. |
| D1 | Quattro modelli originali procedurali, 2564 triangoli e tre ossa ciascuno; sei draw call su board. Pipeline nativa al posto di GLB. Valutazione artistica fisica aperta. |
| D2 | Catalogo e archivio implementati. File con digest e profilo conservato per permanenza; aggiunta di voce compatibile verificata via dati. Importer GLB e caricamento a caldo esclusi. |
| D3 | Calendario UTC, riserve/commit e recupero implementati; 14 test PC/14 ARM, incluso orologio indietro e candidato pendente. |
| D4 | Scena, diff per identità, sostituzione e lifecycle implementati; verifiche PC e tre temi EGLFS mirate. |
| D5 | Gestione da tastierino, contratti/API2.14 e fallback implementati. Corpus171 sul contratto; due nuovi casi UI PC, controlli API runtime e workflow EGLFS. Matrice estesa non ripetuta. |
| D6 | Prima misura120s dopo60s: 59,955 callback/s, p95 18,15 ms/p99 20,52 ms, zero stalli >50 ms. Un caso breve a freddo ha uno stallo308ms: conservato e da approfondire. Ripetibilità, durata, fisico/live e qualifica finale aperti. |
| D7 | Candidata0.10.2-rc.4 installata:550 file, ponte EGL/bypass cache shader, backup e preservazione verificati. Gestione e sei identità nel servizio reale; restart e reboot OS con scanout corretto, NRestarts0. Leggibilità e assenza di glitch confermate dall’utente sulla rc.4; ottica/tasti fisici/durata estesa aperti. [Report](v010-aquarium-graphics-fix-report.md). |

La riduzione dei test è esplicita e autorizzata dall’utente: non sono dichiarate eseguite tre repliche nominali, scala1/4/6/8/16 finale, venti rientri/trenta sostituzioni, soak30/60min o nuova matrice completa. La consegna successiva ha selezionato il delta sulla baseline e svolto nuovi controlli, documentati nel report; i gate fisici/live e di durata restano distinti. Compagno0.11 invariato.
