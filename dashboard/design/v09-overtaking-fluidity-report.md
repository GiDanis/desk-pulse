# Gioco rc.22 — sorpassi, ricompense e fluidità

**17 ottobre 2026 · studio avviato il 16 · candidata rc.22 installata, 624 hash conformi. Verifica funzionale passata; gate di fluidità/qualifica ottica ancora aperti.**

Attuazione del [piano O0–O4/F0–F4](game-overtaking-fluidity-analysis.md). [Evidenze ripetibili](evidence/v09-overtaking-fluidity-implementation-2026-10-16/). Baseline congelata rc.21; piloti reali esclusi dalle campagne.

## Modifiche implementate

- Produzione conserva `race-residual-2` / `residual-racing-1`: il candidato a premi comuni e curva 240 m è stato **respinto** dal confronto fuori banca. Sorpasso confermato dopo 0,5 s, credito unico per incontro/banda conservato. Il ramo sperimentale richiede un profilo privato esplicito (`rewardExperiment=common-units-1`); nessun preset o menu lo seleziona.
- Diagnostica delle regole e degli esiti; l’allineamento raccolta/verifica proposto resta nel candidato sperimentale respinto. Cause distinte per passaggio incompleto, violazione, limite pista e difesa persa. Fase breve della manovra nella riga esistente; risultati distinguono guida valida senza guadagno dal miglioramento promosso.
- **Nessuna migrazione dei premi nei piloti reali:** actor, esplorazione, RNG, campione, replay, critic, ottimizzatori e contatori conservati. La migrazione conservativa implementata per lo studio non viene attivata dai preset. Nessun reset globale e nessun modello di studio importato.
- Controllore geometrico raggruppato fra le vetture; decisioni individuali sempre a 10 Hz, fisica a 60 Hz. Raggi visuali proiettati soltanto per l’auto selezionata. Osservazioni complete non ricostruite nei passi che ne scartano il risultato.
- Checkpoint in processo dedicato, un solo pendente, replay in memoria condivisa preallocata prima dell’ACK di avvio. Copia sigillata prima del passo successivo; encoding/JSON/hash/fsync/commit fuori dalla preview. «Salvato» soltanto dopo persistenza e, in pausa, chiusura del writer; errore senza ACK positivo e possibilità di ritentare. Chiusura del learner con tempo per l’ultimo salvataggio.
- Dossier e aggiornamento GUI non rileggono il replay completo; classifica e dossier riusano gli stessi piloti appena letti nello stesso refresh, senza tre decodifiche dell’archivio. Metadati pubblici senza le tracce dettagliate, che restano nell’artefatto. Plancia aggiornata su revisione, compresi invalidazione/modello/riferimento. Diagnostica delle pose su richiesta.
- Cache limitata delle verifiche complete del campione: policy/base, codice, libreria nativa, runtime Python/NumPy/architettura, configurazione fisica, regole e banca nella chiave; riuso dichiarato, senza nuove esperienze o qualifiche fittizie.

Grafica, pista da 12 m, scala vetture, PB/ultimo/S1–S3 e comandi restano quelli approvati. Le cinque auto rimangono visibili in Gara. Nessun nuovo uso NPU; fisica/learning su CPU, Qt Quick su GPU.

## Misure già acquisite

| Prova | Prima | Candidata | Interpretazione |
| --- | --- | --- | --- |
| Sonda ARM, 1.000 tick, cinque policy e PPO maturo, ABBA | 8,84–8,91 s | 5,31–5,36 s | Circa −40% nel lavoro controllo/fisica/proiezione della sonda; non un numero di FPS. Parità fisica verificata. |
| Esercizio ARM, osservazioni scartate, ABBA | 4,81–4,85 s | 3,95–3,99 s | Circa −18%, stesso premio e stato fisico. |
| Replay SAC pieno, heartbeat del processo principale ARM | massimo 322,88 ms con thread | 24,05 ms con processo/memoria condivisa | Encoding/persistenza restano circa 3,1 s in background. Non è una misura ottica. |
| Aggiornamento dossier dopo salvataggio, PC, campione 35 s | scatto 219,06 ms | massimo 38,56 ms | Rimossa la lettura sincrona del replay nella GUI. Campioni locali, non qualificazione del pannello. |
| Refresh/snapshot GUI, checkpoint reale maturo su PC con profiler | circa 16 ms | circa 8 ms | Snapshot pubblico identico; lettura dei piloti 3→1. Non è un guadagno FPS. |

39 test PC con riferimento gradienti indipendente e 22 controlli mirati ARM passati sul primo candidato; dopo la mancata promozione, altri 11 test mirati PC passati. Ripresa di tutti e quattro i backend dal checkpoint rc.21 identica al codice precedente per learner, RNG, replay, premio e stato fisico (1.071–1.080 passi complessivi per caso). Quattro gare fisiche a 2/4/5 auto e ordinamento premi su cinque comportamenti passati. Verifiche esatte di ripresa, migrazione, writer fallito, raggi e osservazioni scartate su ovale/Varano.

Il log della prima matrice PC segnala sei oggetti Qt non raccoglibili alla chiusura dell’interprete (`ResourceWarning`); i test risultano passati. Questo dato non viene usato come prova di perdita RAM durante l’uso né come assenza generale di warning. I warning QML dei runner nativi sono verificati separatamente.

### Clock grafico: variante scartata

Confronto nativo Apple, sei segmenti da 120 s: vecchio timer → nuovo timer → FrameAnimation → FrameAnimation → nuovo timer → vecchio timer.

- Nuovo timer: p95 delle pose 35,80–36,08 ms; p99 43,29–44,89 ms.
- FrameAnimation: p95 delle pose 36,90–37,47 ms; p99 54,67–60,64 ms.
- I circa 60 swap/s della variante contengono pose duplicate: non dimostrano 60 FPS del movimento. Rimane il presenter monotono a 30 Hz; variante soltanto diagnostica su richiesta, con fallback per refresh diverso da 60 Hz.
- Nei due segmenti nuovi, nessuno swap oltre 100 ms; uno dei due p99 swap è 69,05 ms, oltre la soglia proposta di 66,67 ms. Questo campione non certifica tutti i gate né 30 FPS ottici fissi.

## Campagne concluse e decisioni di promozione

Cinque semi 21–25, 196.608 passi fisici raccolti per seme, ricetta precedente/candidata e variante di curriculum a capacità. Verifiche fuori budget. Campagne aggiuntive PPO/SAC/TD3: cinque semi per metodo, 49.152 passi fisici ciascuno. Banche strutturate sviluppo/selezione/finale separate e congelate prima delle prove; condizioni esplicite di gap, lato, velocità e punto d’ingresso. Nessun tuning sulla banca finale e nessuna promozione di un curriculum dal solo totale aggregato.

La variante a capacità **non viene promossa**: nella selezione, tre semi perdono circa 14–23% del passo; due semi perdono dieci casi già riusciti e non emergono nuovi successi nel traffico. Curriculum fisso conservato, senza scegliere il solo seme migliore.

Audit della banca: nella v1, i due gruppi “sorpasso/curva” diventavano identici dopo l’override dello stato iniziale. I risultati v1 sono conservati, ma non sostengono due competenze distinte. Nuova banca v2 congelata: 240 configurazioni esplicite uniche, seed 99101–99160, ingresso sul rettilineo distinto dall’ingresso curva. Nessun parametro del learner cambiato; valutazione abbinata conclusa. La decisione negativa sul curriculum usa la perdita di passo, indipendente da questa duplicazione.

### Premio comune: non promosso

Banca finale v2, ogni famiglia 60 casi per seme; cinque semi completi con lo stesso budget di 196.608 passi raccolti. Tutte le policy valutate nello stesso ambiente candidato: il diverso orizzonte della base non viene attribuito alla rete. [Riepilogo completo](evidence/v09-overtaking-fluidity-implementation-2026-10-16/heldout-summary.json), [decisione](evidence/v09-overtaking-fluidity-implementation-2026-10-16/reward-promotion-decision.json).

| Seme | Vecchia: solo mediano | Candidata: solo mediano | Vecchia: sorpassi | Candidata: sorpassi |
| --- | ---: | ---: | ---: | ---: |
| 21 | 28,52 s | 29,77 s | 60/60 | 0/60 |
| 22 | 28,40 s | 28,98 s | 60/60 | 0/60 |
| 23 | 28,40 s | 30,20 s | 60/60 | 0/60 |
| 24 | 28,80 s | 29,62 s | 43/60 | 0/60 |
| 25 | 28,43 s | 28,72 s | 60/60 | 58/60 |

Sorpassi: media/mediana/peggiore vecchia 56,6/60/43 su 60; candidata 11,6/0/0. Vecchia 283/300 e zero contatti, candidata 58/300 e un contatto; entrambe zero limiti/violazioni registrate. Solo/curva/difesa: entrambe 300/300, ma il solo medio delle mediane peggiora 28,51→29,46 s (+3,3%). Non è quindi giustificato sostituire la ricetta esistente.

Il Maestro congelato riesce in 60/60 solo, sorpasso e curva, 21/60 difesa; il solo mediano è 36,28 s. La difesa riuscita del learner può derivare anche dal maggior passo: non dimostra una strategia neurale di bloccaggio. Il seme 24 della ricetta precedente perde comunque 17 sorpassi; conservare quella ricetta è una scelta di non regressione, **non una certificazione che il problema dei sorpassi sia risolto**.

Screening dei backend col premio candidato (49.152 passi fisici/seme): PPO/SAC/TD3 completano tutti e cinque i semi e promuovono almeno un miglioramento nei controlli interni. Mediane dell’ultimo campione promosso: PPO 34,60–35,65 s; SAC 30,33–33,35 s; TD3 29,60–32,87 s. Questi non sono cinque confronti vecchio/nuovo per ciascun backend né una generalizzazione al traffico; il risultato negativo di Tattico impedisce la promozione comune anche agli altri metodi.

Per il prossimo studio: separare in ablation scala dei premi, bootstrap ai confini e allineamento delle regole, che questo candidato cambia insieme; ampliare la verifica con scenari di sviluppo realmente distinti prima di congelare un nuovo finale. La diagnosi osservata è soprattutto passaggio incompleto (242 casi candidati; uno con contatto), non un aumento generalizzato di uscite. Non prova quale cambiamento abbia causato la regressione.

Persistenza del lato, cap basato sugli ingombri, esplorazione di manovre e shaping potenziale restano esperimenti successivi: nessun cap di sicurezza è stato rimosso. Prima di un nuovo tuning servirà congelare una nuova banca finale; la v2 ora è conosciuta. Campagne su ovale a budget finito, non qualificazione su Varano o fondi diversi. Tempi di campagna PC influenzati da carico concorrente, quindi non usati per vantaggi di tempo reale.

## Matrice O0–O4 / F0–F4

| Fase | Esito |
| --- | --- |
| O0 | Baseline, budget e banche congelati; cause e riproducibilità controllate. Audit v1 e sostituzione v2 dichiarati. |
| O1 | Fasi/esiti leggibili e invarianti del sorpasso conservati. Distanza 240 m e regole allineate provate nel candidato, non promosse insieme alla ricetta respinta. |
| O2 | Premi comuni e confini espliciti implementati e testati nello studio; beneficio di apprendimento non confermato. Default precedente conservato, nessuna migrazione reale. |
| O3 | Progressione a capacità confrontata e respinta. Cap/aderenza conservati; altre varianti richiedono esperimenti distinti. |
| O4 | Cinque semi completi, budget fisico uguale, banca finale v2 e risultati negativi inclusi. Nessun modello dello studio importato. |
| F0 | Baseline nativa A/B e tracing separato fra callback, pose e pacchetti. |
| F1 | Costi controllo/physics/sensori e salvataggi confermati su ARM. Origine dei picchi residui del render loop non ancora isolata. |
| F2 | Batch del controllo, sensori/osservazioni su richiesta, timing a revisione, writer/cache implementati con parità fisica. FrameAnimation respinto, timer monotono 30 Hz conservato. |
| F3 | Sonde ARM ABBA e sei segmenti nativi A/B da 120 s: vantaggi del lavoro CPU misurati; nessuna accelerazione globale dei frame né chiusura dei gate di coda dichiarata. |
| F4 | Sei carichi da dieci minuti completati e supplemento finale PPO da 120 s. Gate software severo non superato per picchi >100 ms; qualifica prolungata di tutti i carichi sull’identica revisione finale e misura ottica/HID umana aperte. |

## Qualifica nativa e consegna

Campionamento nativo prolungato eseguito: Qualifica, Gara a cinque auto e PPO/SAC/TD3 con memoria matura, tracing acceso/spento, tre temi e flussi di pausa/ripresa. Dataset SAC/TD3 sintetico pieno dichiarato come stress di persistenza, non competenza appresa. PPO da copia privata reale; originale intatto. I carichi maturi usano la ricetta precedente conservata. Il riuso delle letture GUI è successivo ai campioni lunghi PPO/SAC; Tattico e il supplemento finale PPO lo includono. I ricevuti di affinamento delimitano l’attribuzione, senza presentare tutti i carichi come dieci minuti sulla stessa identica revisione finale. Misure ottiche e comandi HID umani rimangono una verifica separata.

### Campioni nativi da dieci minuti

Intervalli di **callback software** in movimento; per Gara/Qualifica i valori sono intervalli fra i cinque segmenti da 120 s, senza mediare via i picchi. [Raw e riepilogo](evidence/v09-overtaking-fluidity-implementation-2026-10-16/board/performance-summary.json).

| Carico | p95 swap | p99 swap | Massimo swap | Velocità simulata |
| --- | ---: | ---: | ---: | ---: |
| Gara Base, cinque auto | 44,78–46,33 ms | 59,84–68,60 ms | 79,35–115,69 ms | ~1× |
| Qualifica Functional | 41,69–45,13 ms | 52,93–58,05 ms | 74,34–125,93 ms | ~1× |
| Gara Apple, cinque auto | 44,83–52,53 ms | 66,33–75,46 ms | 94,18–118,04 ms | ~1× |
| Crono PPO maturo | 38,93 ms | 59,29 ms | 277,02 ms | 0,9998× |
| SAC replay pieno | 42,18 ms | 64,06 ms | 140,43 ms | ~1× |
| Tattico TD3 replay pieno | 42,30 ms | 64,47 ms | 170,99 ms | 0,9999× |

Le pose hanno età p95 120 ms, massimo 176,34 ms nel PPO e 120 ms negli altri carichi. Nessun intervallo di posa ripetuta in movimento rilevato dalla sonda. Il buffering è fresco, ma la callback può arrivare in ritardo: cadenza media circa 29,8–30 Hz **non equivale a 30 FPS fissi**. Tutte le cinque auto presenti/visibili in Gara.

Il campione Apple con tracing spento (120 s) mantiene picchi: p95 48,28 ms, p99 75,42 ms, massimo 114,77 ms, due intervalli oltre 100 ms. Non è giustificato attribuire tutto il ritardo alla diagnostica. Non è una misura ottica né un A/B bilanciato sufficiente per stimare esattamente l’overhead della sonda.

Nei campioni maturi compaiono raccolta, verifica e salvataggio; aggiornamenti off-policy sono sincroni dentro la raccolta, quelli PPO hanno fase distinta. Preparazione checkpoint massima osservata: PPO 60,15 ms, SAC 35,38 ms, Tattico 42,62 ms, superiore alla sola copia condivisa della microsonda. Restano quindi lavori sincroni da profilare. Nel PPO, 22/26 intervalli swap >100 ms attraversano il contesto `saving→idle`; è un’associazione ai pacchetti adiacenti, non un’attribuzione causale completa. Il riuso delle letture GUI mira al costo di refresh confermato dal profiler, senza sostenere che elimini ogni scatto.

Risorse diagnostiche: memoria disponibile minima ~3.967 MiB, temperatura CPU massima ~62,1 °C nei campioni coperti. RAM della GUI comprende i buffer diagnostici in memoria; il primo segmento Base non ha copertura del collector ripreso. [Riepilogo risorse](evidence/v09-overtaking-fluidity-implementation-2026-10-16/board/resources-summary.json). CPU 100% significa un core logico, non tutta la scheda; le temperature GPU/NPU non misurano utilizzo degli acceleratori.

13 test mirati ARM finali passati in 121,57 s; flussi finali su Main/Worker con tutti e quattro gli allievi e cinque auto passati, zero messaggi QML raccolti. Le verifiche GUI sono isolate e offline: traffico reale dei provider, prova ottica/HID e qualifica prolungata sull’identica revisione finale di tutti i carichi rimangono separati.

### Supplemento finale e installazione

PPO maturo con GUI finale, 120 s: p95 swap 37,50 ms, p99 52,96 ms, massimo 153,37 ms, cinque intervalli >100 ms; pose p95 34,47 ms, p99 41,80 ms, massimo 156,32 ms. Simulazione 0,99994×. Il confronto corretto con i **primi 120 s** del vecchio campione lungo, non col suo massimo a 600 s, trova p95 37,43→37,50 ms, p99 55,00→52,96 ms, massimo 174,98→153,37 ms e sei→cinque intervalli >100 ms. Un solo confronto cronologico, non ABBA: il beneficio di tempo CPU della GUI è misurato dal profiler, **l’accelerazione globale del rendering resta inconclusiva**. [Confronto](evidence/v09-overtaking-fluidity-implementation-2026-10-16/board/ppo-refresh-comparison.json).

**Installazione completata:** [ricevuta](evidence/v09-overtaking-fluidity-implementation-2026-10-16/board/final-receipt.json), [salute successiva](evidence/v09-overtaking-fluidity-implementation-2026-10-16/board/final-health.json), [staging ARM](evidence/v09-overtaking-fluidity-implementation-2026-10-16/board/stage-receipt.json).

- Runtime `0.9.0-rc.22`, **624 file** conformi; manifest SHA-256 `7a920362a80ef0d6ba39f1d3269381d745a630943b2c8b857de7a0fe19bd989b`. Sottoinsieme runtime identico alle sorgenti diagnostiche finali; libreria ARM verificata.
- Servizio active/running, `NRestarts=0`, GUI pronta con PID nuovo verificato e conferma successiva sullo stesso processo. Base attivo, 44 preferenze conservate (40 non di aspetto); stesso boot, solo riavvio del servizio.
- Cinque piloti e **36 artefatti originali** conservati con gli stessi hash; tabelle originali identiche, nessuna sessione in pausa da riclassificare, nessun allenamento di produzione lanciato e nessuna migrazione dei premi. Al termine nessun learner/writer attivo; collector diagnostico terminato.
- Backup dati completo `/var/lib/smartpc-dashboard/game-backups/before-overtake-20261017-215917` e configurazione con suffisso `-config`; runtime precedente `/opt/smartpc/dashboard-rc21-before-overtake` disponibile per rollback.

La ricevuta attesta installazione e conservazione, non il superamento di F4. Il gate severo dei callback è fallito anche con tracing spento; non vengono dichiarati 30 FPS ottici fissi, migliore apprendimento dei sorpassi o risoluzione di tutti i picchi. Prossimo lavoro mirato: profilare il tratto ACK→refresh→render e la preparazione dello snapshot maturo, quindi ripetere A/B e qualifica prolungata sullo stesso artefatto finale. Per i premi, nuova ablation e nuova banca finale prima di un altro default.
Roadmap successiva invariata: Acquario v0.10 → Compagno v0.11 → Memoria/AI v0.12 → Stabilità v1.1.
