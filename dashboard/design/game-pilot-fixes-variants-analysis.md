# Gioco · analisi dei piloti attuali, fix e nuove varianti

**15 ottobre 2026 · revisione 1 · analisi per il seguito v0.9.x.**

**Attuazione successiva:** [rc.18 installata e stato dei gate](v09-pilot-improvement-report.md). Diagnostica e ricette sono implementate; la selezione scientifica delle varianti e le condizioni G6 restano distinte. Il testo seguente conserva la proposta e la fotografia delle 16:04 precedenti all'attuazione.

Baseline documentata: **0.9.0-rc.17**. Questo studio aggiunge diagnosi, esperimenti e criteri di scelta al [MasterPlan](release-masterplan.md); i fix e i nuovi piloti descritti sotto sono **da implementare/confrontare**. La documentazione e la raccolta di metadati sono il lavoro svolto in questa sessione. Nessun nuovo training, reset, cambio dei parametri o riavvio della Dashboard.

## 1. Risposta e decisioni proposte

I sei piloti hanno ruoli sensati, ma non sono sei paradigmi indipendenti: Evo e NEAT fanno ricerca evolutiva, PPO apprende per rinforzo, Clone per imitazione, PPO-Smooth è una variante PPO e Pursuit è un controllore scritto nel codice.

**Non ci sono prove per dichiararli tutti rotti, né per dichiararli tutti capaci di gareggiare.** Occorre separare difetti del software, efficacia del training, maturità del singolo pilota e comportamento della popolazione esplorativa.

Ordine consigliato:

1. Rendere verificabili motivi dei fallimenti, parametri effettivi e risultati del migliore congelato.
2. Seguire il NEAT attuale fino al passaggio dall'arco al giro: ha già fatto progressi; preservarne il checkpoint come controllo.
3. Confrontare i metodi puri su budget estesi e più seed, distinguendo i piloti originali dalle copie sperimentali.
4. Primo nuovo metodo utile al gioco: **Clone → PPO**, con maestro dichiarato e passaggio di fase persistente.
5. Prime varianti pure: **NEAT-64**, **NEAT-Risposta**, poi **Evo-32N** se emerge un limite di capacità. Nessuna promessa che siano migliori.
6. Dopo una guida affidabile: **Regolare**, **Attaccante**, **Polivalente**; SAC come ulteriore algoritmo sperimentale.

## 2. Evidenza usata e limiti

### 2.1 Fotografia attuale della rosa sulla scheda

[Metadati acquisiti](evidence/v09-pilot-audit-2026-10-15/roster-metadata.json) il **15 ottobre alle 16:04:06 Europe/Rome**, in un'unica transazione SQLite in sola lettura, verificando gli hash dei checkpoint letti. [Script ripetibile](evidence/v09-pilot-audit-2026-10-15/audit_roster.py): non costruisce `GameStore`, non esegue reti o learner e non cambia lo stato delle sessioni. I dati seguenti sono **quelli salvati a quell'istante**, non telemetria continua. Il servizio risultava attivo con `NRestarts=0` nel controllo in sola lettura precedente; nessuna nuova verifica visiva è attribuita a questo studio.

[Provenienza e controlli](evidence/v09-pilot-audit-2026-10-15/analysis-provenance.json): i 15 file del motore esaminati coincidono per SHA-256 con quelli installati in `/opt/smartpc/dashboard`. Verificati sintassi dello script e collegamenti locali dello studio. Questa corrispondenza non costituisce un nuovo test di guida o di convergenza.

Le righe principali riguardano l'ovale storico `oval-1`. Gli altri percorsi e obiettivi sono distinti nel JSON.

| Pilota | Passi salvati sull'ovale | Stato del checkpoint | Cosa possiamo concludere |
| --- | ---: | --- | --- |
| Evo | 14.438.939 | `balanced-driving-2`, curriculum oltre il giro, fase Passo | Esperienza estesa; il precedente candidato congelato rc.17 aveva completato più giri. Il nuovo checkpoint non è stato riprovato in questa analisi. |
| NEAT | 1.043.504 | `balanced-driving-3`, livello 6: Arco lento · 50 m; 32 candidati | Non è fermo alla partenza. Nell'epoca corrente sono stati raccolti 626.849 passi dopo il contatore iniziale 416.655. |
| PPO | 0 | Profilo v1, nessun checkpoint sull'ovale | Nessun esito personale sull'ovale consente ancora di valutarne la convergenza; non è un fallimento dimostrato dell'algoritmo. |
| Pursuit | 77.536 | Riferimento geometrico storico | I passi registrano esecuzione, non apprendimento. Verificare la versione del riferimento per ogni pista. |
| Clone | 8.221 | `balanced-driving-3`, Partenza · 1 m | Ancora iniziale; il successo del Clone sperimentale non è una qualifica di questo pilota. |
| PPO-Smooth | 0 | Checkpoint storico `balanced-driving-1`, 25,6 s salvati, nessun contratto ingressi persistente | Migrazione prevista al prossimo Start. Il contatore zero e il checkpoint storico non dimostrano da soli assenza assoluta di una storia precedente. |

**NEAT, dettaglio importante:** le ultime otto suite archiviate riportano al massimo **1/2 scenari principali superati dallo stesso candidato**, con ripasso conservato dal candidato selezionato. Il reward medio migliore registrato sale da circa 1,74 a 2,68; non basta a promuovere lo stadio. Nei tentativi registrati dell'arco da 50 m risultano 65 successi su 512, 358 esiti `contact`, 78 stalli, 10 non validi e un timeout. Sono candidati/scenari ripetuti, non 512 piloti o prove indipendenti del campione. Una sola specie è presente nel checkpoint; questo è un dato da seguire, non una prova automatica di errore della speciazione.

Il nome `contact` è ambiguo: `Episode.step` lo assegna a **qualsiasi** `world.retired[0]`. Il World può ritirare anche per impatto col limite esterno. Quei 358 esiti non possono essere presentati come 358 collisioni con avversari.

### 2.2 Esperimenti precedenti riutilizzati

[Report rc.17](v09-driving-integrity-report.md), [risultati](evidence/v09-driving-integrity-2026-10-15/learning-summary.json): 48 run privati, 12 milioni di transizioni, 250.000 per run. Cinque seed per ogni baseline, tre per ogni variante di taratura; due scenari di esame per seed della baseline.

| Metodo, inizializzazione | Partenza 20 m | Arco lento 20 m | Ingresso 60 m | Giro ovale |
| --- | ---: | ---: | ---: | ---: |
| Evo nuovo | 10/10 | 5/10 | 3/10 | 0/10 |
| NEAT nuovo | 10/10 | 10/10 | 5/10 | 0/10 |
| PPO nuovo | 10/10 | 8/10 | 3/10 | 0/10 |
| PPO-Smooth nuovo | 10/10 | 9/10 | 7/10 | 0/10 |
| PPO-Smooth da actor storico | 8/10 | 8/10 | 5/10 | 0/10 |
| Clone nuovo | 10/10 | 10/10 | 10/10 | 10/10 |

Queste sono **prove brevi**, non limiti assoluti dei metodi. Clone riceve indicazioni dall'esperto: informazione e costo del maestro devono essere dichiarati. Smooth storico usa un solo actor di origine con cinque nuovi seed di apprendimento. Evo personale ha molto più training e non costituisce un confronto a 250 mila passi. Nessun nuovo esperimento di convergenza viene attribuito a questa analisi.

## 3. Cosa sanno e cosa stanno cercando di imparare

### Sensori e azioni effettivi

La versione attuale dell'Accademia usa `race-68-v3`: raggi ai bordi, velocità e rotazione, sterzo, distanza laterale, disallineamento rispetto alla pista, punti davanti a 15/40/80/150 m, curvature, margini della carrozzeria, accelerazioni, segnali di deriva, vicinanza/rischio degli avversari e contesto temporale. Le azioni sono sterzo e pedale firmato: gas positivo, freno negativo.

I learner ricevono numeri, non l'immagine del display. Avere il segnale della curva non significa conoscere già come usarlo. Nelle fasi solitarie gli ingressi degli avversari non forniscono esperienza di sorpasso.

Le reti attuali sono **feed-forward**: la memoria personale persistente conserva conoscenze, modelli e copertura, ma non è uno stato neurale ricorrente che ricorda la sequenza degli ultimi secondi. L'eventuale aggiunta di ricorrenza è un esperimento diverso, da motivare con un problema di osservabilità.

### Incentivo comune, aggiornamenti diversi

`game_rewards.specification` usa progresso per giro 10, giro pulito 3, tempo 0,5→2 con la pressione sul passo, uscita 0,5, tempo esterno 2, ritiro 3, sottosterzo dannoso 1, stallo 3 nei preset progressivi e sorpasso pulito 0,5. I coefficienti temporali sono normalizzati: non sono penalità da sottrarre interamente a ogni frame.

Il progresso premiato è nuovo avanzamento sicuro; i giri devono rispettare porte e validità. Non si premiano il semplice gas, il semplice freno, l'essere immobili al centro o il solo superamento di una vettura. Evitare nuove ricompense che impongano sempre la linea centrale: servono traiettorie larghe lecite e spazio per sorpassare.

Evo/NEAT usano l'esito per selezionare candidati; PPO lo usa per aggiornare actor e critic; **Clone aggiorna sui comandi del maestro**, non tramite il reward. Il reward può aiutare a valutare Clone e promuovere gli esercizi, ma cambiarlo non corregge direttamente le sue etichette di guida.

### Imparare a guidare e imparare a gareggiare

I 32 tentativi Evo/NEAT sono reti candidate dello stesso pilota in mondi separati. Non competono fra loro solo perché sono disegnati insieme. La Gara usa invece una vettura per pilota, policy congelate e una Qualifica riferita allo snapshot e alla configurazione.

La progressione deve distinguere: partenza → controllo e frenata → giro pulito → continuità → passo → traffico e sorpasso → gara. Un solo giro valido resta il requisito prodotto per iscriversi; non certifica automaticamente sorpassi, endurance o abilità su altre piste.

## 4. Analisi per pilota: fix, tarature e mantenimento

### 4.1 Evo — conservare e consolidare

**Già presente:** rete densa 68→16→2, selezione/mutazione, elite, perturbazioni scalate per numero di ingressi, discendenti locali dopo affidabilità e discendenti esplorativi. Archivio del migliore verificato separato dal candidato corrente; trasferimento personale e continuità Infinito implementati nella rc.17.

**Da verificare:** il nuovo candidato deve conservare partenza, entrambi gli archi, frenata e giri successivi mentre migliora il tempo. Mostrare il risultato del campione separatamente dalla percentuale di mutazioni che falliscono. Un candidato veloce ma meno affidabile non deve sostituire automaticamente il campione da gara.

**Esperimenti:** rete da 32 neuroni soltanto contro la rete da 16 a condizioni e budget uguali; variazione della quota esplorativa solo se i dati mostrano stagnazione o regressione. Non azzerare il pilota personale per provare una rete diversa: dimensioni e ottimizzatori devono restare attribuibili a una nuova variante.

**Esito:** nessun nuovo bug specifico di Evo riprodotto in questa sessione. Priorità a verifica della robustezza e del passo, non a un reset.

### 4.2 NEAT — distinguere ventaglio e mancata convergenza

**Già presente:** 32 genomi, topologia variabile, specie, selezione su suite con successi/ripasso/reward, curriculum comune, inferenza nativa, inizializzazione pesi/bias σ0,3 e mutazioni σ0,15. Parte senza nodi nascosti e con collegamenti diretti completi; 68 ingressi significano 136 collegamenti iniziali verso i due output. Le topologie possono poi cambiare.

La funzione della libreria è `tanh(2,5 z)`, coerente anche nell'inferenza salvata: può rendere sensibile il comando rispetto a una tanh standard. È una caratteristica dell'implementazione documentata, **non un bug di per sé**. [Attivazioni NEAT-Python](https://neat-python.readthedocs.io/en/latest/activation.html).

**Ipotesi da misurare:** sterzo iniziale troppo ampio, pochi candidati utili per entrambi gli scenari, specializzazione su un ingresso curva, perdita di diversità o crescita della rete senza vantaggio. La fotografia attuale sostiene soprattutto un collo di bottiglia nel superare insieme i due casi da 50 m; non dimostra quale causa lo produca.

**Diagnostica necessaria:** distribuzione dello sterzo/pedale nei primi due secondi e all'ingresso, quota `|sterzo|>0,9`, metri prima dell'uscita, velocità, rischio sottosterzo, causa del ritiro, successo per scenario e per candidato, nodi/connessioni attivi e specie nel tempo. Affiancare il migliore congelato alla popolazione. Una specie sola può essere compatibile con una popolazione piccola; verificare distanze e risultati prima di cambiare soglia.

**Esperimenti nuovi, uno alla volta:**

- `NEAT-64`: 64 genomi, altri parametri invariati. Verificare più diversità utile contro maggior costo per generazione.
- `NEAT-Risposta`: su popolazione nuova, risposta iniziale dei nodi di output 0,4 anziché 1, mantenendo pesi/bias/mutazioni. Riduce la sensibilità iniziale, non impone una traiettoria e non impedisce che i pesi evolvano. Registrare la response nel genoma, nel preset e negli export; parità nativa/Python obbligatoria.
- Solo se serve: inizializzazione sparsa, con percentuale di connessioni dichiarata, contro `full_direct`; rischio di togliere segnali utili. Non abbinarla subito agli altri cambi.

Ridurre semplicemente i sigma **è già stato provato senza vantaggio sul giro** nello screening rc.17. Non riproporre quei numeri come fix convalidato. Un maestro nascosto trasformerebbe il metodo: eventuale NEAT assistito deve essere una nuova ricetta esplicita.

**Esito:** continuare a misurare il pilota corrente; aggiungere diagnostica e confronti mirati. Nessuna cancellazione motivata dalla sola forma a ventaglio.

### 4.3 PPO — prima riferimento affidabile, poi taratura

**Già presente:** actor/critic NumPy separati, esplorazione gaussiana, azioni con tanh, PPO con clip, GAE e bootstrap diverso per terminazione/troncamento. In Accademia γ≈0,99958342: scala di sconto 40 s a 60 Hz; λ 0,99 ha decadimento GAE molto più breve, circa 1,6 s. Rollout 256×32 = 8.192 transizioni, quattro epoche, batch 64, LR 0,0003, clip 0,2, entropia 0,001, limite KL 0,03.

Il γ 0,995 del preset generico non è il γ effettivo della nuova Accademia. Impostazioni, dossier e prova devono mostrare quale configurazione è realmente salvata/usata. Non presentare il nostro PPO come un backend Stable-Baselines3: SB3 è un riferimento per verifica, non la libreria attualmente eseguita.

**Verifiche prima di altre tarature:** controllo numerico dei gradienti e delle shape su casi noti, ritorni/GAE per timeout e reset, coerenza dei rapporti di probabilità e della trasformazione tanh, KL e quota clip, critic, azioni sature ed esplorazione. Il rapporto gaussiano latente può essere coerente con una trasformazione tanh fissa; non dichiarare sbagliata la likelihood solo perché manca il Jacobiano nel rapporto. L'entropia latente e quella dei comandi limitati non sono però la stessa quantità: controllare saturazione e significato del coefficiente.

Confrontare la guida deterministica dell'actor congelato con quella rumorosa di training. Se il critic migliora ma il campione non completa i compiti, il reward/loss da solo non basta. Il pilota personale PPO ha ancora zero passi sull'ovale: manca una prova reale sufficientemente allenata.

**Esperimenti:** estendere il budget prima di assumere incapacità; LR 0,0001 e batch 128 sono già stati confrontati brevemente senza vantaggio sul giro. Sono ipotesi aperte, non preset migliori dimostrati. Se persiste il problema, verificare su copia un'implementazione di riferimento, con ambiente, azioni e budget equivalenti. [PPO originale](https://arxiv.org/abs/1707.06347), [Spinning Up PPO](https://spinningup.openai.com/en/latest/algorithms/ppo.html).

### 4.4 PPO-Smooth — precisare quale regolarità ottimizziamo

**Già presente:** PPO con penalità aggiuntiva sullo scarto fra sterzo richiesto e sterzo fisico attuale, quando non c'è rischio sottosterzo o ritiro. Questo non coincide esattamente con la variazione del comando fra due decisioni e non misura da solo la regolarità del giro.

**Fix di significato/diagnostica:** descrivere il costo effettivo. Se vogliamo penalizzare oscillazioni dei comandi, serve uno stato precedente salvato e ripreso correttamente, una formula normalizzata per il tempo e parità batch/seriale. È un cambiamento di obiettivo da versionare, non una semplice riscrittura del testo.

**Esperimento proposto:** costo aggiuntivo disattivo durante le basi, attivazione graduale dopo guida verificata; confronto accoppiato con coefficiente costante e zero. Evitare che punisca controsterzo, sorpasso o rientro necessari. Gli screening attuali non dimostrano che Smooth sia sempre migliore di PPO né che la policy storica vada cancellata.

### 4.5 Clone — maestro e copertura, oltre alla loss

**Già presente:** maestro geometrico `traffic-pursuit-2`, etichette negli stati raggiunti dall'allievo, replay 8.192 diviso in quattro riserve per frenata/curva/rettilineo/rientro, batch fino a 128 e rete 68→16→2. Nessuna correzione nascosta dei comandi dell'allievo.

Il maestro conosce geometria completa e stati simulati e conserva un obiettivo di corsia; la rete riceve l'osservazione definita. Questo vantaggio informativo, e l'eventuale ambiguità delle etichette dovuta a stato del maestro non osservato, vanno dichiarati. È un controller utile, non una traiettoria ottima dimostrata. La struttura è ispirata all'aggregazione DAgger, senza attribuire automaticamente le garanzie del metodo originale alla nostra approssimazione. [DAgger](https://arxiv.org/abs/1011.0686).

**Da verificare:** errore sterzo/pedale per manovra su esempi separati, giri congelati, rientri, traffico, casi dove il maestro stesso fallisce. Il maestro cambia pressione sul passo: associare le etichette alla sua versione e ai parametri del compito, evitando un mix non dichiarato di obiettivi incompatibili nel replay. Un nuovo maestro richiede rivalutazione di esempi e provenienza.

**Esperimenti:** rete da 32 neuroni o replay da 16.384 esempi soltanto se capacità/copertura sono un limite misurato. Più RAM non rende utili dati ridondanti. Il pilota Clone personale è ancora iniziale; i 10/10 dello screening appartengono ad altre reti sperimentali.

### 4.6 Pursuit — riferimento, non allievo

**Da verificare:** controller e parametri effettivi per ogni circuito, margini di frenata e comportamento nel traffico. La policy deve essere riferita alla pista corretta. L'aggiornamento a `traffic-pursuit-2` cambia comportamento/hash e richiede nuovi tempi di riferimento.

**Fix di comunicazione:** distinguere chilometri/passaggi di esecuzione da passi di apprendimento; niente generazioni, premi di apprendimento o promessa di diventare più veloce col tempo. Resta un ottimo controllo per capire se un problema appartiene all'ambiente o al learner.

## 5. Registro degli interventi proposti

| ID / priorità | Stato della diagnosi | Intervento | Verifica richiesta |
| --- | --- | --- | --- |
| F1 · alta | Ambiguità confermata nel codice: ogni ritiro diventa `contact` | Separare bordo/uscita, contatto auto, stallo e timeout, con fallback «ritiro, causa non disponibile» per lo storico | Casi fisici distinti; somme degli esiti coerenti; nessuna riclassificazione inventata dei vecchi dati |
| F2 · alta | NEAT attuale 1/2 casi principali; popolazione diversa dal campione | Esito per scenario e versione del migliore, metrica separata dei tentativi | Stesso hash congelato nei due casi; visualizzare miglioramento anche se gli esploratori falliscono |
| F3 · alta | Parametri sparsi fra preset, runtime e checkpoint | Descrittore effettivo persistente e consultabile, inclusi response/specie NEAT, γ/λ PPO e maestro Clone | Menu/dossier/sessione riproducono i valori usati; valori vecchi non ricostruibili marcati sconosciuti |
| F4 · alta | Efficacia sul giro ancora aperta per vari metodi | Budget esteso, seed e confronti indipendenti secondo §7 | Nessuna promozione basata soltanto su reward o una singola animazione |
| F5 · media | Costo Smooth diverso dalla generica «regolarità» | Testo preciso; costo progressivo o derivata del comando come esperimenti distinti | Frenata/controsterzo e pulizia preservati; reward versionato se cambia la formula |
| F6 · media | Ipotesi di sensibilità/diversità NEAT | Confronto risposta 0,4 e popolazione 64 separati | Successi sui due casi, tempo al giro, complessità e costo; conservare baseline |
| F7 · media | Maestro e copertura Clone da qualificare oltre l'ovale | Versione completa delle etichette e validazione per manovra | Prove separate, rientri e traffico; mai attribuire il maestro alla rete |

F1–F3 migliorano la diagnosi; non promettono da soli reti migliori. I difetti già corretti dalla rc.17 restano consegnati e non vengono riaperti senza una regressione riprodotta.

## 6. Nuovi piloti: differenze reali e priorità

Un **seed diverso** crea un altro individuo. Una **variante** cambia rete, ricerca o obiettivo. Un **nuovo metodo** cambia come si apprende. La scelta della pista o del ramo Infinito/Sorpasso non deve essere confusa con un algoritmo nuovo.

Tutti i nomi seguenti sono proposte, **nessun pilota aggiunto alla rosa da questa analisi**.

| Proposta | Differenza concreta | Cosa dovrebbe verificare | Ordine |
| --- | --- | --- | --- |
| Evo B / Clone B / NEAT B | Stessa ricetta, seed nuovo | Quanto il risultato dipende dalla casualità; riferimento per gli altri confronti | Controlli sperimentali |
| **Clone → PPO** | Imita prima; poi ottimizza l'actor con PPO | Partire con basi di guida e cercare tempi migliori senza perdere controllo | Primo nuovo metodo |
| **NEAT-64** | 64 candidati invece di 32, stessa configurazione restante | Più ricerca utile per generazione e costo accettabile | Prima variante pura NEAT |
| **NEAT-Risposta** | Response output iniziale 0,4 invece di 1, su genomi nuovi | Meno saturazione iniziale e più candidati che risolvono entrambi i casi | In parallelo come esperimento separato, non combinato a NEAT-64 |
| **Evo-32N** | 32 neuroni interni invece di 16 | Capacità utile su circuiti/traffico più complessi | Dopo verifica del limite di capacità |
| **PPO-Prudente** | LR 0,0001 invece di 0,0003, resto invariato | Aggiornamenti più piccoli con maggiore affidabilità | Confronto esteso; lo screening non ha già scelto un vincitore |
| **Regolare** | Ricetta iniziale candidata Clone→PPO; enfasi su completamento e dispersione dei tempi | Più giri consecutivi puliti e tempi ripetibili | Dopo competenza base |
| **Attaccante** | Stessa base capace, curriculum con sorpassi a entrambi i lati e avversari vari | Passaggi puliti e capacità di rinunciare a un varco chiuso | Dopo competenza base |
| **Polivalente** | Alternanza dichiarata di piste e successivamente grip/vetture, con ripasso | Trasferimento e conservazione delle abilità su ogni contesto | Dopo test di osservabilità/compatibilità |
| **SAC** | Rinforzo off-policy, replay di transizioni, actor, due critic e reti target | Possibile riuso migliore dell'esperienza per comandi continui | Algoritmo successivo, sperimentale |

Evo a 16 neuroni ha 1.138 parametri eseguibili; Evo a 32 neuroni ne ha 2.274 con gli attuali 68 ingressi e due uscite. Raddoppiare la rete non raddoppia tutta la simulazione, ma aumenta inferenza e ricerca. NEAT-64 raddoppia i candidati: non è un'ottimizzazione gratuita né una promessa di 1× per tutti.

### 6.1 Contratto del nuovo metodo Clone → PPO

1. Nuova identità e ricetta immutabile, ad esempio `clone_ppo`; non far apparire PPO puro un pilota istruito dal maestro.
2. Fase Imitazione: stesso maestro e stessi sensori dichiarati di Clone. I comandi eseguiti restano della rete dell'allievo.
3. Passaggio dopo guida verificata su una banca separata: proposta almeno 18/20 partenze e 18/20 giri puliti, più continuità per 5 giri su almeno 4/5 scenari. Soglie progettuali da confrontare, non già superate.
4. Trasferire i pesi densi all'actor mantenendo architettura e contratto ingressi; critic, stato degli ottimizzatori e rollout PPO nuovi. Non trattare le dimostrazioni come rollout on-policy e non mescolare pesi di reti diverse.
5. Calibrare l'esplorazione iniziale su copie; usare una dispersione che non distrugga subito la guida, senza eliminare l'esplorazione. Nessun valore «ottimo» scelto in anticipo.
6. Fase Rinforzo: premi del compito, niente sterzo corretto dall'esperto; archivio del modello pre-passaggio e prove accoppiate prima della promozione. Un rollback non deve trasformare l'esito fallito in esperienza riuscita.
7. Checkpoint completo della fase, origine, budget di ogni fase, optimizer/RNG ed eventuale transizione incompleta; pausa/ripresa senza ripetere o saltare il passaggio.

Il riuso automatico attuale accetta **lo stesso paradigma**: il nuovo metodo richiede dispatch, validazione profili, ricetta, salvataggio, dossier, memoria/export e test dedicati. Non basta aggiungere una voce nel menu. La base imitativa appartiene al nuovo pilota: non si copiano automaticamente altri piloti della rosa. Un futuro import esplicito deve registrarne l'origine.

Potrebbe migliorare rispetto all'imitazione pura, ma **non è garantito che superi il maestro**. Il confronto deve contare anche il costo e i passi dell'imitazione iniziale.

### 6.2 Specializzazioni Regolare / Attaccante / Polivalente

- **Regolare:** affidabilità come primo vincolo, poi mediana e variabilità dei giri; non premiare la sola lentezza o la sopravvivenza da fermo. Registrare entrambe le metriche, senza nascondere i ritiri dalla statistica.
- **Attaccante:** sorpassi completati con margine, senza contatto/uscita, in rettilineo e curva, con bot lenti, pari e veloci. Conservare la protezione contro premi ripetuti arretrando; misurare anche contatti per incontro e completamento della gara. Più penalità non equivalgono automaticamente a migliore tattica.
- **Polivalente:** iniziare con le piste già disponibili. Fondo, gomme e vettura cambiano i limiti fisici; i 68 ingressi non includono un descrittore esplicito completo di tutti questi parametri. Verificare se i segnali dinamici bastano; se serve informazione aggiuntiva, versionare sensori/rete/migrazione e non promettere riuso immediato degli stessi pesi. Valutare su una pista mai usata per aggiornare i pesi, prima e dopo familiarizzazione.

Gli stili sono obiettivi di training, non tre paradigmi autonomi. Nel menu deve comparire anche il metodo effettivo.

### 6.3 SAC e altre alternative

SAC è pertinente perché usa azioni continue e riutilizza transizioni passate; ha però più reti e aggiornamenti. **RAM disponibile non dimostra né velocità né convergenza.** Prima un ambiente equivalente e un riferimento verificato; poi misure su ARM di raccolta, update, memoria e fluidità. [SAC, documentazione Spinning Up](https://spinningup.openai.com/en/latest/algorithms/sac.html).

TD3, politiche ricorrenti e NEAT assistito restano alternative successive: non moltiplicare subito i backend prima di aver isolato il collo di bottiglia. Nessuna nuova promessa di addestramento su NPU.

## 7. Protocollo di confronto e criteri di scelta

### 7.1 Budget, riproducibilità e configurazione

Proposta: riutilizzare lo screening a 250 mila come base; confronti a **1 milione e 3 milioni di nuove transizioni di raccolta**, con cinque seed per variante. I budget sono cumulativi dal punto iniziale dichiarato del run; per le copie personali registrare anche i passi pregressi. Estendere solo i candidati con segnale utile, con regola decisa prima di leggere il test finale. Non sono una previsione dei tempi per imparare.

Per ogni run salvare:

- seed, stato RNG di ogni componente, revisioni del codice/dipendenze e configurazione fisica;
- pista/geometria, fondo, gomme, auto, osservazioni, azioni, reward, curriculum e contratto degli ingressi;
- metodo, variante, preset effettivo, maestro/dimostrazioni se presenti, origine del checkpoint;
- transizioni di raccolta, passi fisici, costo delle verifiche, chiamate al maestro, aggiornamenti, tempo reale e simulato;
- esiti per scenario e hash di candidato/campione, checkpoint intermedi e stato della promozione.

Il solo seed non garantisce riproducibilità fra versioni, backend o hardware. Verificare pausa/ripresa dello stesso run e parità dei percorsi nativi/NumPy dove prevista. Le prove dei seed NEAT devono essere isolate anche rispetto al RNG Python globale.

Stesso numero di transizioni non equivale allo stesso costo: NEAT-64, maestro Clone e update PPO hanno lavori diversi. Riportare **risultato rispetto ai campioni** e **risultato rispetto al tempo/hardware**, separatamente. I tempi di processi PC concorrenti non diventano throughput dell'Orange Pi.

### 7.2 Batteria indipendente

Separare banca di training, banca di validazione per selezionare varianti e banca finale non usata per scegliere i parametri. Ripetere le decisioni significative su nuovi seed; non chiamare «test finale» una banca già usata per la taratura. Questo segue i principi di valutazione su più run e ambienti separati della [guida SB3](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html).

| Capacità | Misura proposta | Gate candidato, da validare |
| --- | --- | --- |
| Partenza | 20 scenari, posa/offset dichiarati, niente comandi esperti | ≥18/20, senza immobilità o uscita |
| Curve e frenata | Entrambi gli archi, velocità 3/6/8/11 m/s quando pertinenti; successi separati per scenario | Nessun caso difficile nascosto nella media; baseline e variante su casi identici |
| Giro | 20 episodi per seed di training, policy congelata | ≥18 giri puliti; tabella per seed e aggregato, senza promessa universale |
| Continuità | 5 scenari, 5 giri consecutivi richiesti per episodio | Almeno 4/5 episodi completati senza reset della policy |
| Passo | Giri puliti, miglior tempo, mediana, dispersione, ritiri | Promuovere un guadagno solo preservando affidabilità; margine candidato 2% da confermare con incertezza |
| Sorpassi | 20 incontri variati per lato/velocità, bot congelati e origini dichiarate | Gate iniziale candidato ≥16/20 puliti, nessun aumento dei contatti rispetto alla base |
| Gara | 2 e 4 piloti, 3/5 giri, entrambe le griglie | Tutte le auto visibili; policy congelate, tempi/ordine/contatti corretti |
| Trasferimento | Circuito non usato nel training; prova prima e dopo adattamento | Distinguere riuso immediato, passi di adattamento e regressione sulla pista precedente |

Le soglie sono decisioni di progetto proposte, non risultati presenti. Per tempi e successi usare riepiloghi per seed e intervalli d'incertezza: cento episodi ottenuti dalle stesse cinque reti non sono cento run di apprendimento indipendenti. Riportare anche fallimenti e valori mancanti.

### 7.3 Lettura delle cause

Per ogni tentativo: scenario, posa/velocità iniziali, hash rete, metri sicuri, tempo simulato, fine reale o finestra, fuori pista, impatti, stallo, controllo sterzo/pedale e rischio sottosterzo. Le durate tipiche degli esercizi non sono tempi sul giro. Stime o dati non disponibili devono restare tali.

Separare le serie **esplorazione**, **candidato corrente**, **migliore verificato**, **snapshot qualificato**. Nel dossier: «Arco 50 m · candidato 1/2 · campione verificato…»; evitare di usare il massimo di un campo come se appartenesse allo stesso candidato massimo di un altro campo.

## 8. UI e prestazioni da predisporre

### Menu e dossier coerenti

Conservare Apple Calm, geometria 960×640, pista grande, impostazioni in sezioni e parametri del pilota in consultazione. Alla creazione proporre metodo e variante con una descrizione breve; il dettaglio tecnico resta nel dossier. Non aggiungere slider per modificare l'identità di un pilota già allenato.

Distinzioni utili: «Da zero / Con maestro», «Metodo / Variante», «Guida / Passo / Sorpassi». Per l'ibrido mostrare «Imitazione → Rinforzo» e fase corrente, non un nome opaco. Offrire le varianti consolidate nel percorso normale; esperimenti e duplicati di seed nella sezione tecnica, senza riempire la rosa automaticamente.

La pista conserva il footer compatto. Diagnosi e grafici appartengono a Progressi/Pilota: generazioni o aggiornamenti, esercizio corrente, tentativi riusciti, risultato del migliore congelato, tempo simulato/reale, provenienza del modello. Raccogliere istogrammi e contatori per batch, non riscrivere il contesto QML a ogni passo fisico.

### Hardware e frequenza delle decisioni

CPU: fisica, policy e apprendimento; GPU: Qt Quick; NPU: eventuale inferenza di una policy congelata solo dopo beneficio completo misurato. I nuovi metodi non rendono automaticamente conveniente la NPU. Mantenere separati il target di presentazione 30 Hz, la fisica 60 Hz e il rapporto tempo simulato/reale.

Esperimento successivo se PPO esplora in modo troppo discontinuo: decisione 20 Hz con azione mantenuta su tre passi fisici, contro 60 Hz. Non è una fix già selezionata. Richiede reward accumulato, sconto/GAE coerenti con la durata, gestione delle terminazioni intermedie e stato del comando in pausa/ripresa. Registrare sia decisioni sia passi fisici; non falsare il confronto contando tre passi come una singola transizione equivalente a quella precedente. Verificare perdita di reattività in sorpasso e rientro.

Misurare NEAT-64 e reti PPO/Clone da 32 neuroni con reti mature, salvataggi e traffico: throughput, p95/p99 del rendering, ritardo input e memoria. Usare tutta la RAM necessaria è compatibile con il requisito dell'utente; buffer più grandi devono comunque avere un beneficio e un costo espliciti.

## 9. Piano di attuazione proposto

| Fase | Lavoro | Uscita verificabile |
| --- | --- | --- |
| G0 | Diagnostica F1–F3 e fotografia ripetibile | Esiti non ambigui, configurazione effettiva, campione distinto dai tentativi |
| G1 | Budget esteso dei sei ruoli esistenti su copie; controlli PPO | Collo di bottiglia per metodo e risultati indipendenti, senza reset generale |
| G2 | NEAT-64, NEAT-Risposta, repliche seed; Evo-32N solo se giustificato | Variante selezionata solo per un vantaggio misurato, costo incluso |
| G3 | Ricetta persistente Clone→PPO | Passaggio/ripresa corretti e confronto con Clone/PPO a costo dichiarato |
| G4 | Regolare e Attaccante | Endurance e sorpassi verificati; nuova Qualifica per ogni nuovo snapshot |
| G5 | Polivalente, confronto multi-pista, eventuali sensori aggiuntivi | Trasferimento e retention misurati, compatibilità versionata |
| G6 | SAC e decisioni 20 Hz se ancora utili | Prototipo confrontabile e beneficio prima dell'integrazione |

G0–G6 restano nel seguito **v0.9.x**; nessuna nuova release dichiarata consegnata. Il resto della roadmap resta Gioco → Acquario v0.10 → Compagno v0.11 → Memoria/AI v0.12 → Stabilità v1.1.

**Politica sui progressi:** le copie sperimentali possono partire da zero o dallo stesso snapshot; dichiarare quale condizione. Un reset personale è autorizzato dall'utente se necessario, ma non è la prima risposta a un'animazione. Conservare checkpoint di controllo, separare vecchio/nuovo reward e non importare certificati tra hash. Le qualifiche esistenti restano attribuite al loro modello, non a una variante futura.

## 10. Fonti e riferimenti tecnici

Fonti esterne primarie consultate il 15 ottobre 2026; documentazioni `latest/master` possono cambiare. Orientano gli esperimenti, non dimostrano l'efficacia del nostro gioco:

- [NEAT originale, Stanley e Miikkulainen](https://nn.cs.utexas.edu/downloads/papers/stanley.ec02.pdf): topologie, innovazioni e specie; nessuna prestazione del paper trasferita al nostro circuito.
- [NEAT-Python: configurazione](https://neat-python.readthedocs.io/en/latest/config_file.html) e [attivazioni](https://neat-python.readthedocs.io/en/latest/activation.html): significato di connessioni iniziali, response e tanh scalata.
- [PPO originale](https://arxiv.org/abs/1707.06347) e [Spinning Up PPO](https://spinningup.openai.com/en/latest/algorithms/ppo.html): raccolta on-policy e aggiornamenti limitati.
- [DAgger originale](https://arxiv.org/abs/1011.0686): aggregazione delle etichette negli stati visitati dall'allievo.
- [SB3, RL Tips and Tricks](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html): più seed, prove separate, budget e attenzione alle convenzioni dell'ambiente.
- [Spinning Up SAC](https://spinningup.openai.com/en/latest/algorithms/sac.html): rinforzo off-policy per azioni continue, replay, due funzioni Q ed entropia.

Sorgenti locali ispezionati: `game_profiles.py`, `game_academy.py`, `game_academy_trainer.py`, `game_evo_plan.py`, `game_neat.py`, `game-neat-config.txt`, `game_learning.py`, `game_rewards.py`, `game_numeric.py`, `game_control.py`, `game_simulation.py`, `game_driving_memory.py`, `game_store.py`, `game_settings.py`, `game_dossier.py`. Prove precedenti e limiti nel [report rc.17](v09-driving-integrity-report.md); il [vecchio studio dei metodi](game-methods-lap-integrity-analysis.md) resta l'analisi storica precedente alle correzioni.
