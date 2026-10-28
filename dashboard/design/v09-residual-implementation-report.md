# v0.9 rc.20 — Maestro e apprendimento residuale

**16 ottobre 2026 · 0.9.0-rc.20 installata sulla scheda · 617 hash conformi · cinque piloti nuovi · preferenze conservate.**

Attua la [riprogettazione](game-base-driver-redesign-analysis.md). La raccolta completa è in [evidence/v09-residual-implementation-2026-10-16](evidence/v09-residual-implementation-2026-10-16/). I vecchi risultati Evo/NEAT restano storici: non vengono presentati come risultati della nuova architettura.

## Cosa cambia

| Pilota | Metodo e differenza |
| --- | --- |
| Maestro | Controller geometrico fisso, segue la pista e gestisce corridoi/distanze nel traffico. Non apprende. |
| Crono | PPO residuale: raccolta recente e aggiornamenti della policy. |
| Memoria | SAC residuale: replay, due critic, actor stocastico durante l'allenamento; entropia fissata nella ricetta. |
| Linea | TD3 residuale: replay, due critic, aggiornamenti ritardati e actor deterministico con rumore separato nel training. |
| Tattico | TD3; prima 8.192 decisioni sul passo, poi esercizi misti e ripasso del solo. Impara sorpasso permette di scegliere subito il traffico. |

Tutti partono dalla **stessa base capace**, con correzione neurale iniziale nulla. La consegna non importa i pesi degli esperimenti nei piloti personali. La capacità iniziale appartiene al controller; i miglioramenti appresi richiedono misure effettive.

L'ovale base passa da **10 a 12 m**, un metro per lato. Vettura 4,4 × 1,8 m, centrolinea e lunghezza del circuito invariati; fisica, margini, sensori, disegno e bounds concordano. Le correzioni laterali possono raggiungere entrambi i lati dell'intero corridoio legale; zero riproduce esattamente il Maestro. Il passo può variare del ±25% rispetto al riferimento, entro il controllore fisico. Questo inviluppo iniziale non promette il tempo ottimo assoluto.

Primo contesto abilitato: **Ovale 1, auto standard, asfalto asciutto**. Gli altri circuiti esistenti restano elencati come «Da verificare» per questa base, con geometrie conservate. L'infrastruttura trasferisce automaticamente i pesi verificati del medesimo pilota in un nuovo contesto, senza copiarne qualifiche o record; il nuovo campione deve superare le proprie prove prima della promozione.

## Controllo, dati e interfaccia

- Un solo allievo attivo; rete da 90 ingressi e 32 neuroni interni, azioni su linea e passo a 10 Hz. Fisica/controllore a 60 Hz; presentazione separata a 30 Hz.
- Sensori causali con ruoli espliciti davanti/dietro/affiancato, comandi base e stato precedente del residuo. Nessuna guida da pixel o modello linguistico.
- **Candidato, campione e versione qualificata separati**. Verifica congelata ogni 2.048 decisioni; tre giri solo e, per Tattico, tre esercizi aggiuntivi nel traffico. Una regressione conserva il campione. Qualifica e Gara non esplorano.
- Giri continui nella preview del campione; reset degli episodi di raccolta separati dal movimento visibile. Pausa/Salvato e acquisizione dei tasti restano espliciti. Nessun training al boot o alla sola apertura della vista.
- Gara da **2 a 5 piloti**, una macchina per identità, tutte visibili. Conta i giri percorsi; un giro non valido non aggiunge un giro alla distanza di gara. Rimane escluso dai record puliti.
- Menu con soli cinque piloti e ricette consultabili; niente creazione delle vecchie varianti. Dossier con metodo, frequenze, replay, decisioni, risultati, costo delle verifiche e contributo misurato rispetto alla base.
- Reset locale/totale delle correzioni mantiene la guida del Maestro e lo storico misurato; elimina le qualifiche relative ai modelli resettati.

## Apprendimento, premi e ripresa

Progresso fisico valido e costo del tempo; penalità per fuori pista, contatto, ritiro, sottosterzo dannoso e stallo. Nessun premio diretto al gas o al comando di velocità. Sorpassi con incontro armato, affiancamento, superamento completo mantenuto almeno 0,5 s e credito unico per avversario/banda di giro. Stesso rilevatore negli esercizi residuali brevi e continui. Cambi ripetuti di linea davanti a una minaccia e frenate arbitrarie hanno regole semplificate; non si attribuisce l'intenzione del contatto e non si dichiara conformità a un regolamento sportivo.

Checkpoint con actor, critic, target, ottimizzatori, RNG, replay e punto della raccolta. Ricetta incompatibile: errore esplicito, niente reinterpretazione delle vecchie azioni. Replay binario compresso con posizione fisica/cursore conservati. Conservazione di due checkpoint recenti per contesto e artefatti realmente referenziati; metriche storiche mantenute senza tutti i vecchi salvataggi pesanti.

Una correzione del prototipo ha riattivato il protocollo del progresso valido negli episodi nuovi: le prime prove private senza quel protocollo non ricevevano il termine progresso. Non era il percorso della precedente produzione e non spiega da sola le ore storiche di Evo/NEAT. Le prove fallite rimangono nei file di sviluppo.

## Prove e risultati

### Correttezza e prodotto

- **17 controlli mirati PC**, incluso confronto dei gradienti analitici SAC/critic con PyTorch autograd. Torch è una dipendenza di riferimento sul PC, non del runtime ARM.
- ARM: suite circuiti/record/pacing e residui; successiva suite dei 17 controlli, con riferimento Torch esplicitamente saltato. Parità neutra, ripresa JSON anche oltre un episodio, replay/RNG, TD3 ritardato, modello stabile per Qualifica, migrazione atomica e ripristino.
- [Banca fisica reward e gare](evidence/v09-residual-implementation-2026-10-16/v2-pc-acceptance.json): giro più rapido premiato rispetto alla base; fermo, tutto gas e rettilineo/taglio falliscono con ritorno inferiore. Gare 2/3, 4/5, 5/3 e 5/5 vetture/giri, due ordini della griglia; tutti arrivati. Giri invalidi e record distinti.
- [Gare con cinque policy già allenate](evidence/v09-residual-implementation-2026-10-16/trained-five-car-races.json): tre e cinque giri, tutti arrivati nella prova fisica privata; ultimo arrivo 13,02/24,40 s dopo il primo, entro la finestra Worker di 30 s. Non certifica tutte le combinazioni future.
- Maestro sull'ovale: **20/20 partenze, 20/20 giri e 5/5 serie da cinque giri puliti**, su PC e ARM. [Banca PC](evidence/v09-residual-implementation-2026-10-16/v2-base-oval-full.json).
- Crono seed 11 congelato: stessa banca indipendente, **20/20, 20/20, 5/5**. [Esiti](evidence/v09-residual-implementation-2026-10-16/v2-ppo-held-full.json).

### Confronto a dati uguali

PPO/SAC/TD3: cinque seed abbinati 11–15, **8.192 decisioni** ciascuno, circa 49 mila passi fisici, stessa base/azioni/reward e senza dimostrazioni esterne. I tempi includono le verifiche; esecuzioni PC concorrenti, non benchmark di un singolo processo isolato.

La banca di sviluppo sceglie il campione. I seed 810xx/820xx della verifica finale sono distinti dai 910xx usati nelle promozioni. Gli snapshot del confronto precedono le ultime aggiunte dei metadati, il conteggio riservato alla Gara e l'unificazione del rilevatore nel traffico; controllo, reward e aggiornamenti nel compito solo restano invariati. [Parità esatta delle policy finali](evidence/v09-residual-implementation-2026-10-16/solo-study-final-inference-parity.json), con hash dei sorgenti nei singoli risultati. Questa equivalenza non viene estesa ai vecchi studi tattici.

[Riepilogo completo dei gruppi](evidence/v09-residual-implementation-2026-10-16/learning-summary.json):

| Metodo | Riduzione del tempo nella prova da fermo, cinque seed | Episodi di raccolta puliti |
| --- | ---: | --- |
| PPO | 1,49–2,53% | Tutti |
| SAC | 13,38–16,32% | Tutti |
| TD3 | 14,38–17,45% | Tutti |

Su ARM, seed 21 e 4.096 decisioni: circa 198/202/204 s per PPO/SAC/TD3, incluse le verifiche, con due probe concorrenti; circa 24.550 passi fisici per metodo. Miglioramento verificato nella prova rispettivamente 1,08%, 14,10% e 1,27%. Non sono tempi garantiti con la GUI né un confronto statistico ARM a cinque seed. Il confronto non seleziona un algoritmo universalmente migliore e non dimostra generalizzazione ad altre auto, fondi o piste.

[Qualifica privata a policy congelate](evidence/v09-residual-implementation-2026-10-16/frozen-flying-laps.json), seed 11 fissato, tre giri lanciati puliti ciascuno:

| Versione | Mediana giro lanciato | Miglioramento sulla base |
| --- | ---: | ---: |
| Maestro | 35,701 s | riferimento |
| Crono PPO | 34,849 s | 2,39% |
| Memoria SAC | 29,785 s | 16,57% |
| Linea TD3 | 30,005 s | 15,96% |

Sono simulazioni private, non certificati o record trasferiti all'archivio installato. Non sommare questi guadagni con quelli delle prove da fermo o dei paper.

### Traffico e limiti

Maestro: **20/20 sorpassi semplici, 20/20 difese, 15/20 sorpassi in curva**, senza contatti/uscite nella banca. [Rilevatore finale](evidence/v09-residual-implementation-2026-10-16/base-held-pass-traffic.json).

Il primo curriculum Tattico mescolava subito tutti i compiti: tre seed su cinque non promuovevano un candidato. Lo studio completo resta conservato. La ricetta successiva consolida prima il solo; confronto a 16.384 decisioni, distinto dal budget dei tre metodi del confronto principale.

La conferma della ricetta a fasi comprende cinque seed completi a 16.384 decisioni: tutti promuovono un miglioramento del passo (14,38–17,45% nella prova da fermo). La raccolta comprende errori: il seed 11 registra due uscite e tre esercizi non riusciti, conservati nei risultati. [Banca congelata finale Tattico seed 11](evidence/v09-residual-implementation-2026-10-16/accepted-tactic-held-traffic.json): 20/20 sorpassi semplici, 20/20 difese e 10/20 sorpassi in curva.

Il successo del bot composto nei passaggi semplici non prova che la rete abbia imparato la tattica. I sorpassi in curva restano un limite concreto: nella prova congelata del primo Tattico a fasi sono **10/20**, contro 15/20 della base. Non si dichiara una competenza tattica generale né una maggiore capacità in curva. Per il seguito servono scenari indipendenti più ampi e promozione che controlli questa regressione senza rendere sproporzionato il costo delle verifiche sulla scheda.

## Risorse e stato della consegna

CPU per fisica, bot, inferenza numerica e aggiornamenti. Kernel nativo per i sensori dove disponibile; rete e critic NumPy. GPU per Qt Quick/OpenGL. **Nessun training o nuovo offload NPU**: queste reti piccole non hanno un vantaggio NPU dimostrato. La RAM ospita replay e checkpoint; disponibilità di memoria non elimina il costo della fisica o delle verifiche.

La consegna registra separatamente prove native, tempi di frame software, tempi delle verifiche, manifest, preferenze e backup. Un pannello a 60 Hz o un clock da 30 Hz non attestano 30 fps ottici fissi.

### Consegna sulla scheda

[Ricevuta](evidence/v09-residual-implementation-2026-10-16/board/final-receipt.json) e [manifest](evidence/v09-residual-implementation-2026-10-16/board/release-manifest.json): rc.20, **617 file**, nessuna differenza; servizio attivo, GUI pronta, `NRestarts=0`. Preferenze, tema Base attivo e Apple Calm 1.6.3 selezionabile conservati. Riavvio del servizio, **nessun reboot OS**.

Tre prove native EGLFS **960×640**, textScale 1,1: Base, Functional, Apple Calm; tutti gli allievi avviati/salvati, dossier, menu, cinque vetture visibili e nessun warning QML. Apple esegue anche una Qualifica reale con giro lanciato valido. I cinque certificati iniziali dello store nuovo derivano poi da simulazioni fisiche indipendenti di ciascuna esatta policy: **35,701 s**, uguali perché i residui iniziali sono neutri. Nessuna qualifica copiata dai vecchi piloti o dagli esperimenti.

[Campione software della gara a cinque vetture](evidence/v09-residual-implementation-2026-10-16/learning-summary.json): circa 356–359 intervalli in 12 s; p95 circa **39–45 ms**, massimo **52–73 ms** nei tre temi. Media vicina a 30 Hz, con intervalli più lunghi. Harness con `processEvents`, non misura ottica né prova di 30 fps fissi; countdown fermo escluso dal campione.

Migrazione con scambio atomico delle directory; **3.193 file originali** mantenuti con hash identici in `/var/lib/smartpc-dashboard/game-backups/before-residual-20261016-162847`. Vecchia rosa e dati assenti dallo store attivo e dall'interfaccia; cinque identità/certificati nuovi, integrità e riferimenti verificati, nessun ripopolamento al successivo avvio. [Controllo successivo in sola lettura](evidence/v09-residual-implementation-2026-10-16/board/post-install-readonly.json): cinque policy attive, cinque qualifiche concluse, contatori training nuovi a zero e nessun Worker attivo. Runtime precedente per rollback in `/opt/smartpc/dashboard-rc19-before-residual`. I backup restano esterni alla Dashboard; non eliminati.

### Lettura dei gate e lavoro residuo

| Gate | Stato effettivo |
| --- | --- |
| R0 | Superato sul primo contesto, con banca completa PC/ARM. |
| R1 | Parità neutra e ripresa deterministica verificate. |
| R2 | Ricetta e rilevatori implementati, prima banca fisica e regressioni passate; copertura completa di frenata arbitraria/spazio/zig-zag resta da estendere. |
| R3 | Beneficio Crono confermato su cinque seed e banca indipendente; anche giri lanciati privati più rapidi. |
| R4 | PPO/SAC/TD3 disponibili, riferimento numerico PC, primi costi ARM e confronto completo PC. Nessun vincitore universale selezionato. |
| R5 | Capacità iniziale semplice verificata; apprendimento tattico generale e sorpasso in curva **non qualificati**. |
| R6 | Migrazione, rosa, qualifiche, tre temi e gare a cinque installati/verificati nel perimetro sopra; prime gare PC fra cinque campioni eterogenei passate; cadenza ottica e gare estese ARM restano prove ulteriori. |

L'implementazione del verticale e la migrazione sono consegnate; non si chiudono artificiosamente gli studi su ricompense, tattica generale, altri circuiti/fondi o prestazioni prolungate. Il seguito rimane Gioco v0.9.x e non rinumera Acquario v0.10, Compagno v0.11, Memoria/AI v0.12, Stabilità v1.1.
