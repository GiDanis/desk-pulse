# Sorpassi: implementazione, confronti e consegna A0–A7

22 ottobre 2026 · Europe/Rome. Seguito dello [studio A0–A7](game-overtaking-attack-study.md).

**Installata core 0.9.3-rc.2 · 647 file verificati · Apple Calm 1.6.3 conservato.** Consegna tecnica A0–A7 conclusa, diagnostica attiva e codice sperimentale isolato. **La nuova ricetta di apprendimento non supera i criteri scientifici e non è attivata sui piloti personali: il miglioramento del sorpasso prolungato resta aperto.** [Ricevuta](evidence/v09-overtaking-implementation-2026-10-22/board/final-receipt.json).

## 1. Cambiamenti

| Passo | Implementazione / esito |
| --- | --- |
| A0 | Baseline, checkpoint reali privati, hash e sonde dello studio conservati; nuova lettura della rc.1 installata prima delle modifiche. |
| A1 | Occasioni geometriche, attacchi realmente iniziati, partenze già affiancate, passaggi confermati, tempo in coda/affiancato senza avanzare, tempi di completamento e latenza di attacco. Il timer conta il tempo della vettura, non la somma del tempo di ogni rivale. Dossier e pannello Rete distinguono la raccolta dalla guida mostrata. |
| A2 | Migliore tattico persistente distinto da migliore solo e versione gara. Proposta tattica possibile senza nuovo PB, con passo solo entro +1%, nessuna regressione per caso e nuovo controllo su due griglie. Non si sovrascrive il migliore tattico con una variante peggiore. Qualifica e gara conservano la policy esatta già selezionata. |
| A3 | Confronti privati tra base guida, traffico, selettore meno saturo, rete singola e preparazione offline mediante docente. Nessun nuovo asset di fabbrica qualificato o importato. Le preparazioni capaci negli esercizi brevi falliscono parte del traffico prolungato. |
| A4 | Termine competitivo relativo simmetrico versionato, coefficienti 0 / 0,25 / 0,5; perdite addebitate e guadagni illeciti mascherati, rivali inattivi esclusi. Varianti positive escluse dopo il confronto di sviluppo. Premio di passaggio +0,5 e penalità fisiche conservati. Nessun nuovo shaping potenziale dichiarato invariante o promosso. |
| A5 | Raccolta finita indipendente dalla preview: completamento, attacco, curva, difesa, passo, recupero, traffico. Massimo 24 s per esercizio, 60 s per traffico; rotazione esplicita, replay stratificato SAC/TD3, esplorazione laterale coerente. Codice sperimentale; default personali conservati. |
| A6 | Cinque semi di continuazione per metodo, confronto abbinato vecchia/nuova raccolta a budget fisico uguale e banca finale separata; dettagli nel rapporto quantitativo sotto. Non sono cinque preparazioni indipendenti del docente. |
| A7 | Migrazioni su copie dei quattro piloti, test PC, ARM e Main/Worker reale nei tre temi; installazione del solo codice qualificato con backup, rollback e ricevuta. Stato effettivo nelle evidenze, senza attribuire un risultato di apprendimento alle prove GUI. |

La rete mantiene tutto il controllo di sterzo e pedale. Il docente compare soltanto nella preparazione offline privata; non viene interrogato durante inferenza, apprendimento RL o gara dei piloti.

## 2. Ricetta sperimentale e compatibilità

Attivazione esplicita nel profilo: `trafficLearning=attack-1`, con `relativeAdvantage` versionato. `RACING_DEFAULTS`, profili personali e basi di fabbrica non selezionano automaticamente la ricetta. Installare il candidato non migra silenziosamente i piloti.

La migrazione dalla ricetta `direct-driving-4` verifica la provenienza, conserva attore, campioni solo/gara, totali e generatore casuale; archivia statistiche/valutazioni vecchie, ricrea critic e replay, conserva l'ottimizzatore dell'esperto solo e azzera quello traffico/selettore. I file originali rimangono immutabili. Nessuna cancellazione o reset dei piloti di produzione.

Ordine dei dieci esercizi: completamento, attacco, curva, passo, traffico, completamento, difesa, passo, curva, recupero. È una rotazione di episodi con durata massima dichiarata, **non una promessa di percentuali identiche di secondi raccolti per famiglia**. PPO usa rollout correnti; nessun replay on-policy di dati vecchi. SAC/TD3 campionano 64 transizioni con quote completamento/attacco/curva/difesa/passo/recupero/traffico `8/8/12/8/16/6/6`; un gruppo vuoto usa il buffer vivo uniforme. Non è PER.

Lo sterzo esplorato coerente usa deviazione 0,01, limitata a ±0,025. L'ancoraggio originale dello sterzo è conservato: togliere quello traffico nel prototipo ha peggiorato la stabilità. Verifica sperimentale ogni 8.192 decisioni, separata dal vecchio intervallo 2.048: il confronto finale misura il pacchetto, non attribuisce causalmente il risultato a una sola modifica.

## 3. Esperimenti eseguiti

- Preparazioni congelate: 80 esercizi di sviluppo, quattro famiglie × cinque scenari × quattro preparazioni; poi 40 prove estese solo/due bot. Le basi traffico riescono negli esercizi brevi ma producono uscite nella prova lunga. Nessuna selezione dalla sola banca facile.
- Rete singola: cinque semi di ottimizzazione supervisionata sulla stessa base/dataset, 10/12 esercizi riusciti ciascuno, due timeout di passo; non è un confronto a costo uguale né cinque docenti indipendenti.
- Preparazione fisica offline: docente verificato su uno/due/tre bot, rete B preparata e raffinata con aggregazione di esempi. Il candidato fallisce la selezione estesa, incluse griglie; escluso. Una variante di permutazione non ha completato il salvataggio per quota temporanea: esclusa, nessuna qualità attribuita al file parziale.
- Sviluppo premi/curriculum: due semi × quattro varianti × 196.608 passi. I coefficienti positivi peggiorano alcuni candidati; resta 0 nel confronto finale. Due semi di sviluppo non vengono chiamati qualifica completa.
- Finale: quattro ruoli PPO/SAC/TD3/TD3 tattico × cinque semi × due varianti; 196.608 passi fisici trattenuti per esecuzione. Stesse condizioni iniziali abbinate, nessun accesso alla banca finale per aggiornare la rete.

**Contabilità:** passi fisici raccolti, decisioni, aggiornamenti e verifiche sono separati. Un limite di quota di `/tmp` ha interrotto alcuni checkpoint di prova; la directory privata è stata trasferita su SSD, 1.513 file verificati per hash, e le esecuzioni mancanti sono riprese dagli ultimi checkpoint atomici validi. I budget contano le transizioni trattenute, non il lavoro perso e rieseguito. Per queste esecuzioni il tempo del processo ripreso non comprende quello precedente: **nessun confronto affidabile di velocità reale o risparmio CPU complessivo viene dichiarato**.

La banca principale contiene, per policy gara congelata, 40 esercizi tattici, 15 finestre continue con uno/due/tre bot, tre prove solo su tre giri e due griglie a cinque auto su tre giri. Il supplemento successivo, senza ritocchi ai modelli, misura dieci attacchi con latenza e due griglie a due auto. La banca breve non certifica altri circuiti o superfici.

## 4. Risultati quantitativi

Il confronto è completo: **40 esecuzioni, 7.864.320 passi fisici trattenuti**, 2.320 episodi della banca principale, 80 griglie a cinque auto, più 400 attacchi diagnostici e 80 griglie a due auto. Il budget riguarda la continuazione RL; preparazione e controlli di sviluppo sono conteggiati separatamente.

| Pilota / metodo | Completamento + rettilineo puliti | Curva pulita | Finestre traffico pulite con passaggio | Semi con attesa dimezzata | Semi con sicurezza non peggiore |
| --- | ---: | ---: | ---: | ---: | ---: |
| Crono / PPO | 100/100 | 50/50 | 0/75 | 0/5 | 1/5 |
| Memoria / SAC | 100/100 | 50/50 | 0/75 | 0/5 | 5/5 |
| Linea / TD3 | 100/100 | 50/50 | 0/75 | 0/5 | 5/5 |
| Tattico / TD3 | 100/100 | 50/50 | 0/75 | 0/5 | 4/5 |

**Decisione: nessuna promozione della nuova ricetta.** Tutti i semi conservano il passo solo entro 1% e arrivano con cinque auto nelle due griglie; questo non significa gare senza contatti o uscite. Nessun metodo supera il gate traffico esteso o dimezza l’attesa rispetto al controllo abbinato. PPO peggiora la sicurezza rispetto alla propria baseline in quattro semi, Tattico in uno. Due-auto con arrivi e ritenzione ego: Crono 4/5, Memoria 5/5, Linea 5/5, Tattico 4/5. Gli attacchi facili iniziano entro il limite in tutti i semi, ma iniziare la manovra non basta a mantenere il passo dopo il passaggio.

Il codice di promozione tattica riconosce alcuni miglioramenti nella banca di selezione, senza attribuirli automaticamente alla policy gara: il [riepilogo per seme](evidence/v09-overtaking-implementation-2026-10-22/final-summary.json) conserva ogni criterio. Non si passa a un coefficiente positivo, non si azzerano i piloti e non si importa una nuova base incompleta.

## 5. Verifiche e consegna

- PC: 47 test sui contratti di attacco, regressioni sorpasso preesistenti, obiettivo gara, reti dirette e menu. Dieci test specifici coprono premio relativo/abusi, rotazione, replay e ripresa esatta, quattro metodi, rilevatore fisico, latenza, promozione senza PB, migrazione, verifica pendente e ripresa di episodi vecchi senza conteggiare tempo storico non osservato.
- Migrazione privata dei quattro piloti personali: attori, campioni solo/gara e contatori conservati; replay nuovo, nessun salvataggio di produzione modificato.
- Main/Worker PC: 12 combinazioni pilota/modalità, aggiornamento e salvataggio dal menu, partenza Qualifica e griglia visibile; la prova PC breve non certifica l'arrivo della gara completa.
- ARM: 56 test passati; dieci test attacco ripetuti sulla correzione finale del timer, compreso il caricamento di vecchi episodi senza conteggiare attese storiche mai osservate. Nessun cambiamento numerico ai comandi o alle ricompense in quest'ultima correzione.
- EGLFS 960×640: Base e Functional quattro piloti ciascuno, Apple Calm tutte le 12 combinazioni pilota/modalità; quattro piloti riaperti e nuovamente salvati. Nessun avviso QML. Gara Apple a cinque vetture su tre giri terminata con tutti gli arrivi; identità delle cinque auto presenti durante tutta la corsa. Il pannello Rete e i tasti delle viste hanno anche una prova PC dedicata con immagine verificata.
- Installazione: backup integrale con hash, rollback runtime rc.1, 647 hash conformi, tutte le righe del database e gli artefatti originali conservati, preferenze/tema invariati, GUI pronta con PID vivo verificato e `NRestarts=0`. Servizio riavviato, nessun reboot OS, nessun allenamento o migrazione della ricetta di produzione avviato. [Prove ARM/native e ricevuta](evidence/v09-overtaking-implementation-2026-10-22/README.md).
- Queste verifiche non misurano FPS ottici, fluidità, latenza fisica del keypad o funzionamento prolungato; i gate generali v0.9.3 restano distinti.

CPU per simulazione e apprendimento, GPU per Qt Quick; NPU invariata. Nessuna attività nuova a vista chiusa o prima di Start. Le diagnostiche sono campionate a 10 Hz e limitate; i modelli personali e sperimentali rimangono esterni al repository.

## 6. Lavoro non promosso e limiti

Non basta completare il codice per dichiarare i piloti capaci di sorpassare: il gate include traffico prolungato, conservazione del passo e griglie reali. Una variante esclusa rimane disponibile per riproduzione privata, non diventa un default attraverso il menu. Il seguito scientifico necessario è una preparazione traffico che superi la banca estesa e una nuova qualifica indipendente prima dell'attivazione personale.

Tattico e Linea usano entrambi TD3; non sono quattro algoritmi differenti. La rete singola e il docente offline sono controlli di sviluppo, non confronti equivalenti di costo o modelli promossi. Contatti e limiti delle griglie a cinque auto sono globali, comprendono anche i rivali congelati; gli episodi misurano gli eventi ego. Il supplemento a due auto riporta anche gli eventi ego. Nessuna attribuzione di colpa o intenzione viene inventata.
