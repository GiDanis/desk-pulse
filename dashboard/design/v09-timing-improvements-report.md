# v0.9 rc.21 — plancia dell’ovale e protezione delle abilità

**16 ottobre 2026 · 0.9.0-rc.21 installata · 621 hash conformi · cinque piloti e loro esperienza conservati.**

Attua la prima consegna del [piano N0–N5](game-next-improvements-oval-timing-analysis.md). [Evidenze e runner](evidence/v09-timing-improvements-2026-10-16/). La rosa resta Maestro, Crono, Memoria, Linea, Tattico: nessun reset o importazione di pesi sperimentali.

## Esperienza

- Plancia nell’isola dell’ovale: pilota selezionato, personale, ultimo giro e scarti S1/S2/S3. Pista, auto e scala conservate; nessun comando aggiunto.
- Il giro da fermo è **Lancio**, escluso dal personale. Tempi assenti `—`, giro sporco **Non valido**, modello storico **PB · altro modello**.
- In allenamento compare **Campione in anteprima / PB anteprima**: non produce record ufficiali. La preview mostra il campione congelato, non prova da sola un nuovo apprendimento.
- Un nuovo personale mostra il guadagno rispetto al PB precedente. I settori di confronto provengono dallo stesso giro congelato all’inizio; non sono la somma di tre record presi da giri diversi.
- 4/6 cambia pilota; 2/8 conserva le camere, Sensori nasconde la plancia; 5 mette in pausa e conferma il salvataggio dopo la persistenza. Tutte le auto hanno priorità grafica. Se una vettura entra nell’isola o manca spazio geometrico, la plancia si nasconde.
- Nel dossier: personale lanciato e settori realmente disponibili, modello d’origine; finestre di raccolta e giri puliti misurati distinti dalle verifiche brevi.

## Cronometraggio e archivio

`game_timing.py` è opt-in: due nuovi attraversamenti a un terzo e due terzi, più il traguardo autorevole della fisica. I quattro checkpoint del giro restano invariati. Direzione, larghezza, ordine, pulizia e interpolazione sono controllati; la somma dei settori coincide con il giro entro 1e-9 s nei test. I tre decimali sono un formato, non una certificazione dell’esattezza fisica al millisecondo.

`lap-timing-1 / thirds-1`, tabella SQLite `timing_laps`, unicità sessione/pilota/giro, contesto fisico separato dalla versione del modello. Scritture serializzate in un thread fuori dal passo fisico, attesa esplicita su Pausa/fine. Scene lossy e record persistenti sono separati. I campi storici dei consumer restano presenti: questa fase non elimina `lapTimes` dalla scena.

Snapshot con settori e riferimento; ripresa di vecchi snapshot senza intermedi inventati, primo giro parziale escluso dal PB. Il PB storico senza settori viene conservato anche se più veloce dei nuovi giri; gli intermedi rimangono assenti finché realmente misurati. Reset delle correzioni conserva lo storico.

Theme API resta **2.11**: aggiunta facoltativa dentro la `legacyMap` `GameContext.scene.cars[].timing`, senza azioni o superfici nuove. [Contratto e significato dei null](../theme-api/README.md#cronometraggio-gioco-rc21-additivo-api-211).

## Protezione e diagnosi dell’apprendimento

Tattico verifica tre giri solo, due sorpassi sul rettilineo, quattro in curva e due difese per candidato e campione. Un insuccesso in un caso già riuscito al campione, un nuovo contatto o un nuovo fuori pista impedisce la promozione: i successi non si compensano tra famiglie. Le regressioni sono motivate nei risultati. Gli altri tre learner conservano il confronto sui tre giri puliti.

La verifica di Tattico passa da ogni 2.048 a ogni 4.096 decisioni, con banca più ampia. Un vecchio confronto ancora incompleto viene scartato; pesi, ottimizzatore, RNG, replay e campione rimangono compatibili. Nessuna migrazione della ricetta o delle qualifiche.

Regole `spatial-rules-2` **solo nelle verifiche congelate**: orizzonte di frenata dipendente da velocità/aderenza/distanza d’arresto; controllo dello spazio laterale durante l’affiancamento. Diagnostica campionata e limitata a 20 punti per esercizio: velocità, gas/freno, sterzo, linea richiesta/eseguita, gap, velocità relativa e contatti. Sono regole osservabili del gioco, senza attribuzione dell’intenzione.

I premi usati per raccogliere esperienza e il replay esistente **non cambiano**. La banca ricompense viene rieseguita; normalizzazione fra esercizi e continui, nuovo shaping e generalizzazione tattica richiedono ancora ricerca versionata. Non vengono promessi miglioramenti universali a tutti i metodi.

## Verifiche

- **33 test PC**, tutti passati: cronometraggio reale, parità fisica/premi, ripresa, gate avversi, storico/PB, unicità, spazio/frenata, protezione per abilità, regressioni residuali/record/pacing.
- **33 test ARM**, 32 passati e uno escluso: riferimento autograd Torch PC-only. Nessuna dipendenza Torch introdotta nella scheda.
- Checkpoint reale Crono: 269.972 passi, 45.048 decisioni, 4.412,689 s di esperienza. Pesi e campione conservati, ripresa di ottimizzatore/RNG identica fra due copie; zero scritture di produzione. [Esito](evidence/v09-timing-improvements-2026-10-16/mature-resume.json).
- Main/Worker reale in privato: selezione, cinque vetture, record prima dell’ACK Pausa, dati assenti/invalidi/anteprima, notte e textScale **1,1**, massimo ammesso dal contratto attuale. Gli screenshot `fixture-*` sono prove di rendering dichiarate; i record misurati sono dei veri mondi Qualifica/Gara.

### Confronto su cinque semi

Budget fissato: 16.384 decisioni, semi 11–15, nessun peso di studio importato nei piloti. Stessa ricetta, fisica, rete e curriculum della rc.20; cambiano banca/frequenza/protezione della promozione. [Costi e regressioni](evidence/v09-timing-improvements-2026-10-16/study-costs.json). I runner dichiarano hash delle sorgenti e checkpoint privati.

La sorgente congelata dello studio precede la correzione dell’ACK, il confronto con PB storici e la sola diagnostica campionata delle regole: queste differenze non cambiano actor, reward o decisioni di promozione. La banca finale nuova 94101–94120 non viene usata per il tuning; stessa banca/regole per Maestro e campioni rc.20/rc.21 dei cinque semi. Ablazione di sviluppo separata 95201–95210: Maestro, solo passo, linea+passo del seme 11 fissato in anticipo. [Banca finale completa](evidence/v09-timing-improvements-2026-10-16/heldout-summary.json), 20 scenari identici per famiglia, ripetuti sui cinque campioni:

| Campione | Sorpassi rettilineo /20 | Sorpassi curva /20 | Difese /20 |
| --- | --- | --- | --- |
| Maestro | 20 | 16 | 20 |
| rc.20, semi 11–15 | 20, 20, 20, 18, 20 | 10, 18, 18, 4, 20 | 20 per seme |
| rc.21, semi 11–15 | 20 per seme | 16 per seme | 20 per seme |

La nuova selezione conserva il livello della base in questi cinque campioni e limita il caso peggiore osservato. In curva migliora due confronti abbinati, ne peggiora tre; media 16 anziché 14, mediana 16 anziché 18. **Non supera Maestro e non dimostra apprendimento tattico generale.** I 100 esiti condividono gli stessi 20 scenari: non sono 100 scenari indipendenti. Il criterio di non regressione è garantito sulla banca di promozione; la banca finale controlla la generalizzazione senza garantirla su ogni situazione futura.

Nell’ablazione di sviluppo i tre casi ottengono **7/10**: gli stessi tre insuccessi, nessun contatto/fuori pista/violazione, ma il sorpasso non è ancora completato al limite dei 160 m. Nei campioni finali il rivale è ancora affiancato o pochi metri avanti; la linea eseguita è vicina a quella richiesta. Questo isola un limite della manovra e della durata dell’esercizio, senza evidenza che basti aumentare rete o premio. Nessun parametro viene ritoccato usando questa banca: un confronto su lunghezza dell’esercizio e inviluppo di velocità sarà una ricetta successiva dichiarata.

Nel nuovo screening le verifiche consumano circa **57% del tempo PC**. La cadenza ridotta limita la frequenza ma la banca è più ampia: resta un costo rilevante. I tempi PC precedenti provengono da una campagna distinta e non certificano uno speedup a parità di carico del sistema.

### Fluidità e consegna

Prove native EGLFS a 960×640, Base/Functional/Apple Calm. A/B in ordine ABBA nel vero `QEventLoop.exec`, senza pumping di `processEvents` nei segmenti misurati. Per il confronto esteso ogni segmento usa una nuova gara allo stesso seed/policy per restare in movimento. Soglia fissata prima della misura: aumento p95 non oltre max(2 ms, 5%). Le statistiche sono intervalli software `frameSwapped`, non FPS ottici.

[Ricevuta finale](evidence/v09-timing-improvements-2026-10-16/board/final-receipt.json) e [manifest ARM](evidence/v09-timing-improvements-2026-10-16/board/runtime-manifest.json): 621 hash conformi, GUI pronta, Base attivo/Apple Calm 1.6.3 selezionabile, NRestarts=0, preferenze e 36 artefatti conservati; [controllo finale indipendente](evidence/v09-timing-improvements-2026-10-16/board/final-health.json). Tutte le righe delle tabelle preesistenti identiche salvo la chiusura della sessione già in pausa come `interrupted`, senza cambiare il checkpoint. Solo la nuova tabella timing vuota è aggiunta allo store personale. Backup dati/config esterno e rollback `/opt/smartpc/dashboard-rc20-before-timing`; nessun reboot OS e nessun allenamento di produzione avviato.

| Tema | Segmenti ABBA | p95 HUD acceso medio | p95 spento medio | Differenza | Massimo osservato |
| --- | --- | --- | --- | --- | --- |
| Base | 4 × 12 s | 42,07 ms | 43,48 ms | −1,41 ms | 68,08 ms |
| Functional | 4 × 12 s | 43,06 ms | 48,56 ms | −5,50 ms | 78,30 ms |
| Apple Calm | 4 × 120 s | 47,70 ms | 46,76 ms | +0,94 ms | 124,79 ms |

Il gate applicato alla **media dei p95 dei due segmenti per condizione** passa: Apple +0,94 ms entro max(2 ms, 5%). Non è il p95 dell’unione di tutti i frame. I singoli segmenti Apple variano da 41,75 a 51,77 ms e il picco più alto è 124,79 ms: il rumore supera la differenza media, quindi **parità stretta e assenza di scatti non sono dimostrate**. Nessuna garanzia di 30 fps fissi né accelerazione globale; una qualifica più stretta richiede un confronto mirato con correlazione fra frame, eventi e carico. I confronti brevi non dimostrano che nascondere la plancia rallenti il sistema.

[Campione risorse](evidence/v09-timing-improvements-2026-10-16/resource-summary.json): 24 letture ogni 10 s durante la gara Apple, circa 5,13 GiB disponibili e CPU sotto 52 °C. RSS e tick CPU per PID nel report; nessuna misura di occupazione GPU/NPU dedotta da temperature o frequenze. Restano distinti: costo della plancia in gara e costo delle fasi di training maturo; un campione gara non certifica raccolta/update/verifica/salvataggio sotto qualsiasi carico.

## Gate residui

N1/N2 implementati e verificati nel perimetro descritto; N3 parziale: protezioni e diagnosi aggiunte, ottimizzazione della manovra e banca R2 estesa ancora aperte. N4 è uno screening controllato su cinque semi, non prova di convergenza o superiorità generale; N5 ha verifica software nativa e consegna con rollback, mentre leggibilità alla distanza d’uso, FPS ottici, latenza input e training maturo prolungato richiedono qualifica ulteriore. Nessuna nuova accelerazione NPU: CPU per fisica/apprendimento, GPU per QML.

## Studio successivo

[Perfezionamento sorpassi e fluidità, O0–O4/F0–F4](game-overtaking-fluidity-analysis.md): nuove sonde su copie e proposta operativa. Non cambia la ricevuta o il runtime rc.21 di questa consegna.
