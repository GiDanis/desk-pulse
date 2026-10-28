# Gioco · equilibrio di incentivi, penalità e apprendimento della guida

**Studio 1 · 14 ottobre 2026 · baseline sorgenti 0.9.0-rc.14.**

**Documento storico di analisi; implementazione autorizzata in rc.15, installazione verificata.** Stato effettivo, coefficienti selezionati e gate scientifici nel [report di implementazione](v09-balanced-runtime-report.md). Seguito dello [studio delle modalità](game-session-modes-results-study.md), della [memoria di guida](game-offroad-parameters-transfer-study.md) e della [partenza](game-idle-learning-study.md). Il riferimento della consegna resta [rc.14](v09-session-modes-report.md).

Richiesta: studiare ogni incentivo e penalità, con ricerca su fonti primarie, dopo l'osservazione di piloti che insistono sul gas e vanno in sottosterzo. Il controllo legge codice e un artefatto immutabile Evo; le simulazioni sono private sul PC. Nessun pilota originale allenato/reset, nessuna modifica a preset, fisica, UI o servizio della board.

## 1. Decisione proposta

L'obiettivo è **guidare in modo controllato, completare giri puliti e ridurne il tempo**, poi conservare queste capacità nel traffico e su altre piste. Rilasciare o frenare è una scelta utile quando migliora questi risultati; premere il freno non costituisce da solo un successo.

La prima sperimentazione deve confrontare due interventi:

1. **Intervento locale R1:** mantenere la scala attuale, introdurre credito per ogni giro pulito in continuo, esercizi di ingresso curva e un costo moderato del sottosterzo dannoso prolungato.
2. **Intervento strutturale R2:** le stesse componenti, con progresso e costi rapportati a giro/tempo di riferimento, per mantenere il loro peso relativo fra Ovale, Mallory e Varano.

R2 è la direzione raccomandata per piste e auto future; i suoi coefficienti sotto sono **ipotesi sperimentali**, non un ottimo dimostrato. Prima misurare la graduatoria dei comportamenti congelati, poi verificare che i nuovi piloti riescano effettivamente a scoprirli. Le due verifiche non sono equivalenti.

## 2. Evidenza riproducibile

[Script della prova](evidence/v09-reward-balance-study-2026-10-14/probe_current_rewards.py) e [risultati completi](evidence/v09-reward-balance-study-2026-10-14/current-rewards.json). Python 3.12/NumPy, fisica f2-1, driving-memory-1, Ovale, fase Controllo, modalità Impara giro infinito. Sei controllori congelati × cinque scenari accoppiati 2000901–2000905: **30 tentativi**, circa 55,8 s reali sul PC. Finestra 60 s simulati oppure ritiro/stallo; nessun aggiornamento dei pesi.

Evo usa il candidato immutabile **52ceabc503daa6b7ae699b9342d936b8c2032cf13869cc78b88c5783af65f1d8**, identificato nella diagnosi precedente a 256.890 passi del percorso infinito. Non viene sostituito dall'eventuale candidato più recente. I riferimenti geometrici sono controlli diagnostici: non correggono le azioni di Evo. «Gas fisso» conserva soltanto lo sterzo del riferimento e imposta il pedale a +1.

| Comportamento congelato | Esiti dei 5 tentativi | Giri puliti totali | Progresso valido mediano | Ritorno mediano attuale | Campioni di frenata mediani |
| --- | --- | ---: | ---: | ---: | ---: |
| Fermo | 5 stalli, mediana 7,03 s | 0 | 0 m | −0,64 | 0% |
| Sterzo geometrico + tutto gas | 5 ritiri, mediana 5,98 s | 0 | 56,90 m | +0,40 | 0% |
| Riferimento prudente, fattore 0,7 | 5 finestre complete | 5 | 395,13 m | +38,28 | 1,47% |
| Riferimento, fattore 1 | 5 finestre complete | 5 | 559,86 m | +54,75 | 2,44% |
| Riferimento rapido, fattore 1,4 | 5 finestre complete | 10 | 765,27 m | +75,29 | 3,42% |
| Evo salvato | 5 ritiri, mediana 7,90 s | 0 | 94,07 m | +4,05 | 0% |

Frenata: comando pedale < −0,05; tutto gas: > +0,95. Sono frazioni dei campioni, non percentuali di energia o forza. Il ritorno è la somma senza sconto della ricompensa di allenamento, non un tempo di qualifica. I giri sono quelli interamente chiusi nella finestra; il progresso include il tratto successivo.

**Interpretazione:** l'obiettivo attuale assegna già più punti ai riferimenti che guidano bene e velocemente. Non abbiamo dimostrato che «schiantarsi batte un giro pulito». Abbiamo dimostrato che i pochi metri veloci prima del ritiro possono rendere più dello stallo, mentre quel candidato Evo non scopre la frenata nei cinque scenari. Servono feedback anticipato, curriculum ed esplorazione, oltre ai pesi.

Il bonus di arrivo del mondo è **zero in tutti i 30 tentativi**, anche dove sono stati completati giri puliti: in continuo il traguardo non termina il mondo. Il conteggio delle serie pulite esiste come metrica, ma non aggiunge direttamente una ricompensa. Questo è un intervento concreto da preparare.

Limiti: un candidato Evo, una pista, variazioni piccole di posizione/orientamento, nessun traffico, nessun riaddestramento e nessuna misura di FPS/energia. Non dimostra competenza o deficit universali degli altri metodi. Le finestre raggiungono 60,0167 s per discretizzazione; la durata esatta è registrata.

## 3. Inventario degli incentivi attuali

Audit: [fisica/reward](../game_simulation.py), [episodi](../game_academy.py), [trainer](../game_academy_trainer.py), [metodi](../game_learning.py), [NEAT](../game_neat.py), [memoria](../game_driving_memory.py), [maestro geometrico](../game_control.py).

| Termine | Formula o valore corrente | Utilità | Problema/rischio da verificare |
| --- | --- | --- | --- |
| Progresso | Nuovo avanzamento valido / 10; arretramento negativo | Feedback denso; il credito non si ripete percorrendo avanti/indietro lo stesso tratto | Il costo relativo degli errori diminuisce sulle piste lunghe; guadagno iniziale possibile prima del ritiro |
| Partenza | Progresso riscalato a 2 punti per obiettivo 1/3/8/20 m | Permette di scoprire il movimento | Non deve essere il criterio di guida definitiva; insistendo solo qui si esercita soprattutto il gas |
| Tempo | −0,02/s Controllo; −0,30/s Passo | Favorisce tempi inferiori a parità di percorso | Forte pressione precoce può favorire errori o stallo; continuo usa Controllo senza progressione di fase |
| Arrivo | +10 se pulito e terminale | Valorizza il giro completato | Assente al singolo passaggio sul traguardo in continuo |
| Arrivo veloce | Fino a +5, peso Passo, tempo rapportato al budget | Favorisce rapidità dopo validità | Duplica in parte la pressione sul tempo; non opera in continuo |
| Fuori pista | −0,20 per secondo fuori; progresso esterno non premiato | Distingue asfalto/esterno; permette il recupero | Nessun costo separato all'ingresso; il segnale può arrivare dopo la perdita della curva |
| Ritiro | −5 nel mondo | Penalizza perdita del tentativo | Stesso valore su piste di diversa lunghezza; il motivo API «contact» include anche uscita irrecuperabile |
| Contatto recuperabile | −0,05 − 0,15 × min(velocità d'impatto, 12 m/s), evento con cooldown 0,5 s | Scala la gravità e conserva il tentativo | Costo su entrambe le auto; non attribuisce responsabilità sportiva |
| Esercizio superato | +2 quando raggiunge distanza/abilità senza arrivo già pagato | Feedback di successo | Non sommare indiscriminatamente arrivo, esercizio, traguardo e serie |
| Abilità fallita | −2 nel percorso memoria | Separa metri percorsi e compito realmente superato | Evitare duplicazioni con ritiro/stallo; definire la causa |
| Sorpasso | +0,5 per manovra verificata | Valorizza un incontro pulito | Cooldown da solo non prova assenza di farming con scambio ripetuto di posizione |
| Stallo | −0,5 una volta, detector con grazia/progresso/blocco | Ricicla tentativi improduttivi | Una sosta nel traffico o una frenata utile non devono diventare stallo |
| Sterzo | −0,005/s × valore assoluto comando | Piccolo costo di controllo | Anche sterzare correttamente costa; nessun motivo per aumentarlo come cura del sottosterzo |
| PPO-Smooth | −0,03/s × scarto² fra sterzo comandato e sterzo fisico normalizzato | Incentivo alla risposta regolare | È scarto dell'attuatore, non la differenza fra due comandi consecutivi; può penalizzare una correzione necessaria |
| Sottosterzo/sovrasterzo | Nessun termine diretto | Nessun freno artificiale | Feedback tardivo sull'eccesso di richiesta alle gomme |
| Posizione centrale, gas, freno, V max | Nessun premio diretto | Lascia scegliere traiettorie/azioni | Conservare questa proprietà: centro pista e velocità massima non definiscono il giro migliore |

### 3.1 Dimensione del problema fra piste

| Pista nel catalogo attuale | Lunghezza | Progresso premiato per giro | Ritiro −5 equivalente a | Frazione del giro |
| --- | ---: | ---: | ---: | ---: |
| Ovale | 338,78 m | 33,88 | 50 m | 14,76% |
| Tecnico | 272,05 m | 27,21 | 50 m | 18,38% |
| Mallory · Ovale | 1.609,34 m | 160,93 | 50 m | 3,11% |
| Varano · Corto | 1.640,00 m | 164,00 | 50 m | 3,05% |

Questi sono calcoli sul catalogo, non prove dinamiche sulle quattro piste. Il rapporto chiarisce perché copiare coefficienti assoluti non mantiene automaticamente lo stesso equilibrio. Normalizzare tutti i termini per un identico fattore preserva una graduatoria; normalizzare solo alcuni cambia l'obiettivo e richiede confronto.

## 4. Risultati da incentivare, per modalità

| Modalità | Risultato utile | Semantica proposta |
| --- | --- | --- |
| Impara | Un giro pulito; partenza, curva e rientro preparano quel giro | Premi densi del compito, successo singolo, pressione sul tempo dopo affidabilità |
| Impara giro infinito | Percorrenza sostenuta, serie di giri puliti, poi passo | Premio a ogni giro pulito, finestra non terminale, serie diagnostica e non bonus crescente illimitato |
| Impara sorpasso | Guida conservata nel traffico, passaggi puliti e ripetibili | Premio per incontro autentico; giri puliti ancora rilevanti; soste giustificate e incidenti distinti |
| Qualifica | Tempo reale del giro pulito con pesi congelati | Nessun aggiornamento rete; usare cronometro/validità, non una somma reward |
| Gara | Arrivo/ordine/giri/contatti con snapshot qualificati | Nessun training durante gara; non premiare la rete a posteriori fingendo una nuova competenza |

In continuo la serie pulita è per giro, non «mai fuori pista dall'inizio della vita del pilota». Un errore rende sporco il giro interessato; rientrare permette di costruire un nuovo giro pulito. Usare la telemetria di giro, non il contatore cumulativo di track limits come veto permanente.

## 5. Proposta numerica R2, da misurare

### 5.1 Unità condivise

- L: lunghezza del giro in metri. D: distanza dell'esercizio breve, separata da L.
- Tref: tempo di riferimento per pista/vettura/fondo, indipendente dal candidato e congelato nella versione del protocollo. Inizialmente ottenibile da un riferimento geometrico che completa giri puliti; se fallisce usare un valore conservativo dichiarato, non inventare un record.
- Δt: tempo simulato effettivo; integrare i costi continui sui sottopassi oppure sulla decisione con parità verificata. Il totale non deve dipendere da FPS o numero di sottopassi.
- Δsval: avanzamento valido nuovo, con cancelli e credito anti-taglio/anti-ciclo conservati. Δsneg: arretramento. Nessun bonus di avanzamento fuori pista.
- p: pressione sul passo fra 0 e 1, definita dal curriculum e versionata, non dalla fretta del renderer.

Schema candidato per guida sul giro:

~~~text
r = 10 × (Δsval + Δsneg) / L
    − (0,5 + 1,5 × p) × Δt / Tref
    + 3 × evento_giro_pulito
    − 0,5 × evento_ingresso_fuori_pista
    − 2 × Δt_fuori_pista / Tref
    − 2 × rischio_sottosterzo_dannoso × Δt / Tref
    − costo_contatto − costo_ritiro − costo_stallo
    + premio_compito_specifico + shaping_opzionale
~~~

**Proposta, non formula installata.** Il giro pulito terminale e quello continuo ricevono lo stesso evento una sola volta; il successo dell'esercizio non si aggiunge al giro già premiato. Le qualifiche continuano a usare i tempi veri. Il bonus finale di velocità è inizialmente zero per evitare una seconda pressione sul tempo.

| Componente | Candidato iniziale | Intervallo breve di confronto | Vincolo |
| --- | --- | --- | --- |
| Progresso | +10 per giro equivalente valido | Fisso nel primo confronto | Non premio della velocità assoluta o del pedale |
| Tempo | −0,5/Tref/s Controllo → −2/Tref/s Passo | Passo 1 / 2 / 3 per Tref | Aumentare dopo affidabilità; nessuna velocità minima imposta |
| Giro pulito | +3/evento | 2 / 3 / 4 | Pagato una volta, anche in continuo; nessun moltiplicatore infinito per serie |
| Ritiro grave | −3/evento | 2 / 3 / 4 | Una sola perdita per ritiro; contatto che lo causa non duplicato per intero |
| Ingresso fuori pista | −0,5/evento | 0,25 / 0,5 / 1 | Isteresi temporale/geometrica contro vibrazioni sul bordo |
| Permanenza esterna | −2/Tref/s | 1 / 2 / 4 per Tref | Consente il rientro; non triplicare lo stesso errore tramite ulteriori termini |
| Sottosterzo dannoso | Fino a −2/Tref/s | 0 / 1 / 2 per Tref | Attivazione verificata, costo limitato, esclusi fermo e transitori normali |
| Contatto recuperabile | Da −0,2 a −2 secondo impatto | Prima verificare scala esistente riportata a R2 | Cooldown ed eventi reali; nessuna attribuzione automatica di colpa |
| Stallo | −0,5 una volta | Fisso nella prima prova | Conservare grazia/blocco; costo non aggiunto a un ritiro già classificato |
| Partenza | +2 progresso normalizzato su D; +2 successo | Baseline conservata all'inizio | Concluso il compito, passare alla curva; non sommare al giro |
| Rientro | +0,5 successo specifico una volta | 0 / 0,5 | Solo partenza di esercizio già esterna o perdita netta sull'uscita deliberata |
| Sorpasso | +0,5 per incontro pulito | 0,25 / 0,5 / 1 | Il premio non deve ripagare il costo di provocare artificialmente l'incontro |
| Comandi/centro pista | 0 nuovi costi comuni | Ablation separata | Non punire sterzata corretta, frenata d'emergenza o traiettoria esterna |
| PPO-Smooth | Variante specifica mantenuta distinta | Taratura dopo obiettivo comune | Non convertire gli altri piloti in PPO-Smooth né cambiare di nascosto il profilo |

Gli intervalli sono budget di ricerca locali, non un prodotto cartesiano completo. Tarare prima successo/progresso/errore, poi tempo, infine traffico e regolarità. Valutare il costo **integrato sul giro**, non soltanto il numero scritto nella formula.

### 5.2 Controllo aritmetico della graduatoria

Esempi ideali senza shaping, sterzo o traffico; T indica durata rapportata a Tref. Non sono nuove prove di apprendimento:

| Episodio ideale | Controllo p=0 | Passo p=1 |
| --- | ---: | ---: |
| Giro pulito in Tref | 10 + 3 − 0,5 = **12,5** | 10 + 3 − 2 = **11** |
| Giro pulito in 0,8 Tref | **12,6** | **11,4** |
| Giro pulito in 1,2 Tref | **12,4** | **10,6** |
| 30% di giro, poi uscita/ritiro a 0,2 Tref | 3 − 0,1 − 0,5 − 3 = **−0,6**, meno permanenza | **−0,9**, meno permanenza |
| Stallo a 0,2 Tref | −0,1 − 0,5 = **−0,6** | **−0,9** |

Il successo rimane raggiungibile e positivo, la rapidità distingue due giri puliti, l'errore precoce non viene nascosto dal progresso. Un ritiro molto tardivo può ancora ottenere punti: la selezione del campione deve aggiungere validità e retention, non affidarsi soltanto al ritorno. Nessuna somma scalare rende impossibile ogni comportamento indesiderato.

In finestre evolutive fisse, un candidato ritirato presto smette di accumulare costo temporale. Nel confronto R2 calcolare la quota di tempo del **medesimo budget di valutazione** anche per gli slot conclusi, come criterio di fitness esterno. Non introdurre in PPO un costo nascosto del «tempo restante»: una finestra di raccolta non è una morte né un obiettivo finito osservabile.

## 6. Ingresso curva, sottosterzo e freno

### 6.1 La fisica già limita l'aderenza

La vettura standard è a trazione anteriore. La fisica f2-1 include trasferimento del carico, forze longitudinali e budget laterale di ciascun asse. Con molto gas il budget laterale anteriore può ridursi; le forze laterali saturano con una funzione continua. Anche frenare troppo in curva può consumare aderenza: non introdurre la regola «freno sempre buono».

Ordine di grandezza sul raggio centrale di 31 m dell'Ovale: sqrt(μ g R), con μ=0,95, dà circa **61 km/h** per il limite laterale ideale. Non è una velocità obbligatoria: raggio della traiettoria, carico, gomme, transitori e richiesta longitudinale cambiano il risultato. Il valore serve a interpretare i 71 km/h della diagnosi, non a limitare artificialmente l'auto.

### 6.2 Un costo dello slittamento richiede una definizione corretta

Una grande deriva anteriore è un indizio, non da sola una prova di sottosterzo dannoso. Non punire indiscriminatamente qualsiasi slip: una guida rapida può lavorare vicino al limite. Prima raccogliere richiesta/forza disponibile per asse, slip, yaw rate, margini della carrozzeria e loro andamento.

Detector sperimentale:

1. Auto in moto sopra circa 3 m/s; esclusi avvio, blend cinematico e fermo.
2. Richiesta combinata anteriore rispetto a μN anteriore, oppure saturazione effettiva rispetto al budget laterale, con gestione esplicita del budget quasi nullo. La sola forza già clippata non misura quanto la richiesta eccede il limite.
3. Persistenza indicativa 0,2–0,4 s e peggioramento del margine/errore di direzione, oppure insufficiente risposta di rotazione rispetto alla traiettoria locale. Non confrontare sempre con il centro pista durante un sorpasso.
4. Gravità continua limitata fra 0 e 1; penalità piccola e integrata nel tempo. I valori finali di soglia vanno calibrati su riferimento rapido pulito, frenata e recupero.

Nei primi confronti registrare il detector senza premiarlo/penalizzarlo. Il riferimento rapido della prova ha deriva anteriore mediana circa 5,60°, Evo circa 15,55°: soglia identica a zero o un solo grado punirebbe anche la guida valida. Le mediane non determinano una soglia universale, né descrivono i picchi in ogni curva.

L'anticipazione può essere aiutata da un potenziale di stato basato su curva imminente, velocità e margine, con **differenza scontata fra stati**, anziché premio per tenere il freno. Questo resta un'ablation successiva: un profilo di velocità conservativo usato come obiettivo rigido rischia di fissare un tetto al passo.

### 6.3 Curriculum che rende scopribile la soluzione

| Compito | Variazione | Esito utile |
| --- | --- | --- |
| Partenza | 1 → 3 → 8 → 20 m già disponibili | Muoversi e mantenere controllo |
| Curva iniziale | Partenza prima della curva, velocità iniziale sotto/vicino/sopra la velocità utile | Attraversare la curva dentro pista; rilascio o frenata scelti dalla rete |
| Ingresso e uscita | Distanze di approccio, offset e velocità diversi | Ridurre la richiesta prima della curva, tornare ad accelerare quando utile |
| Curve concatenate | Tecnico, poi segmenti metrici di Varano/Mallory | Evitare specializzazione a una sola curva/raggio |
| Giro pulito | Partenze e configurazioni riservate | Trasferire il controllo al giro intero |
| Passo | Pressione graduale solo dopo affidabilità | Migliorare tempo senza perdere arrivi |
| Traffico | Rivali congelati e situazioni libere/bloccate | Frenare/attendere/sorpassare in base allo spazio |

Gli scenari devono includere sia casi risolvibili con rilascio sia casi che richiedono una frenata, verificati prima col simulatore. Non generare ingressi fisicamente impossibili chiamandoli errori del pilota. Non introdurre acceleratore minimo, freno automatico o assistenza del maestro agli agenti Evo/NEAT/PPO.

Il codice attuale ha già curvatura a 20/60/120 m, punti futuri, slip degli assi e margini nei 68 ingressi. Iniziare con questi. Eventuali nuovi sensori sul budget gomme/contesto fisico richiedono revisione degli ingressi e migrazione esplicita, non reinterpretazione silenziosa dei vecchi canali.

## 7. Fuori pista, rientro e scorciatoie

- Conservare la fisica esterna: aderenza ridotta e maggiore resistenza al rotolamento. La ricompensa non deve simulare una fisica diversa.
- Un ingresso fuori costa una volta e la permanenza continua costa nel tempo; niente premio ai metri esterni e niente credito retroattivo per quelli saltati quando rientra.
- Un rientro riuscito vale soprattutto perché permette di tornare ad avanzare e completare il prossimo giro pulito. Il bonus esplicito è riservato al compito Rientro o condizionato a un bilancio che non renda redditizio uscire volontariamente.
- Verificare tutto il corpo dell'auto, cancelli in ordine, nuove frontiere e traiettoria continua. La proiezione su un altro ramo di Varano non deve regalare progresso.
- Entrata/uscita vicina al bordo con isteresi evita premi o penalità ripetuti da tremolio; non falsificare il verdetto di giro pulito.
- Ripasso dei vecchi compiti: mantenere un sottoinsieme di Partenza/Controllo/Rientro mentre si introduce Passo; la conoscenza trasferita resta una policy, non un certificato di tempo su altra pista.

## 8. Sorpassi e comportamento sportivo

Conservare l'incontro verificato: rivale davanti, affiancamento reale, passaggio completato e mantenuto, senza contatti o uscite locali. Distinguere sorpasso, doppiaggio e cambio di posizione perché il bot si ritira. Il premio di +0,5 è inizialmente secondario al controllo del giro.

Preparare prove contro rallentare volontariamente per farsi risuperare, ripetere la stessa coppia nel cooldown, rientrare tagliando, superare bot inattivi e attendere respawn vantaggiosi. Un budget per incontro autentico e un nuovo incontro dopo reale separazione/giro sono più robusti del solo timer. Non punire tutte le distanze piccole: l'affiancamento pulito è richiesto dal prodotto.

Per rischio di contatto futuro, TTC deve considerare velocità relativa e corridoio laterale; distanza longitudinale da sola non distingue un rivale davanti da uno affiancato. Attivare eventuale costo solo quando un impatto evitabile è plausibile. Attribuzione della colpa e regole sportive sono un successivo studio: oggi il costo simmetrico del simulatore è un dato fisico, non un giudizio sull'aggressore.

## 9. Differenze tra metodi e credito temporale

| Metodo | Come usa i premi | Intervento pertinente |
| --- | --- | --- |
| Evo | Fitness accumulata seleziona genitori/élite | Scenari accoppiati, nuovi esercizi, scala comune, verifica del campione su più scenari |
| NEAT | Fitness accumulata seleziona genomi/specie | Stessi compiti; preservare topologia e azzerare confrontabilità storica alla nuova reward |
| PPO | Reward entra in critic e vantaggi | Coefficienti, esplorazione, critic e credito temporale verificati insieme |
| PPO-Smooth | PPO con costo specifico dei comandi | Obiettivo comune più propria regolarità; non impedire manovre rapide necessarie |
| Clone | Aggiornamento supervisionato dalle azioni del maestro | Reward non modifica direttamente la loss di imitazione; migliorare maestro e copertura degli esempi |
| Pursuit | Controllore geometrico fisso | Nessun apprendimento tramite premi; confronto diagnostico e verifica del controllore |

La rete attuale decide sterzo e pedale firmato con saturazione tanh. Se Evo resta a +1, misurare variabilità della popolazione e distribuzione dei comandi prima di alzare mutazione: l'esplorazione può non attraversare facilmente la regione di rilascio/freno. Diversità comportamentale non equivale alla sola deviazione dei pesi. I profili manuali restano fissi; qualsiasi variante di ricerca va identificata separatamente.

PPO moderno usa gamma = exp(−Δt/40), cioè uno sconto con scala 40 s. Ma λ=0,95 è per decisione a 60 Hz: il fattore di decadimento GAE gamma×λ ha una scala di circa **0,322 s**. Il rollout 256 vale **4,267 s per ambiente**, non 32 volte quel tempo perché ci sono 32 copie.

Non significa che PPO «ricordi soltanto 0,322 s»: il critic può propagare valore di lungo periodo. È un punto da confrontare per il credito fra ingresso e uscita curva. Prove separate λ=0,95 / 0,99 / 0,995, rispettivamente circa 0,322 / 1,592 / 3,070 s, con possibile aumento della varianza. Prima isolare l'effetto reward, poi quello di λ/rollout; non attribuire un miglioramento a una modifica cambiandone cinque insieme. [GAE, Schulman et al.](https://arxiv.org/abs/1506.02438)

Infinito: la fine della finestra è truncation, non terminale; bootstrap del valore conservato. Successo/fallimento reale è terminale. La [documentazione Gymnasium](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/) spiega questa distinzione. La baseline la gestisce già: verificare che le nuove reward non la rompano.

## 10. Selezione del pilota e progressione del passo

Distinguere tre livelli:

1. Reward densa per scoprire azioni utili.
2. Fitness della generazione/candidato per lo stesso compito e budget; finché nessuno sa guidare, valorizzare progresso utile senza filtro assoluto che renda tutti uguali.
3. Conservazione/promozione del campione: risultati su scenari riservati, affidabilità e poi tempi. Un picco di fitness non sostituisce questa verifica.

Proposta: Controllo → Passo dopo due insiemi diversi da almeno 18/20 giri puliti, preservando la logica di affidabilità già presente. Aumentare p per finestre, con regressione al controllo se perde affidabilità; in continuo scegliere esplicitamente questo criterio, poiché la fase attuale resta Controllo. La soglia è di curriculum, **non** il requisito di gara: per schierare lo snapshot continua a bastare almeno un giro ufficiale di Qualifica pulito nel contesto corretto.

Confrontare candidato e campione sugli stessi scenari: prima numero di arrivi/contatti, poi mediana e coda dei tempi dei soli giri puliti. I tentativi non eseguiti restano tali. Un ritorno maggiore non basta per sovrascrivere una versione qualificata. Conservare snapshot ufficiale e memoria personale finché una nuova versione supera i rispettivi controlli.

## 11. Ricerca: cosa riusare e cosa non copiare

Fonti primarie consultate il 14 ottobre 2026; sintesi, senza riproduzione estesa:

| Fonte | Risultato pertinente | Applicazione e limite per SmartPC |
| --- | --- | --- |
| [Wurman et al., GT Sophy, Nature 2022; copia dell'autore](https://sam.barrettnexus.com/publications/papers/nature22.pdf) | Policy con azioni continue di accelerazione/frenata/sterzo, scenari misti e ricompensa per comportamento competitivo/sportivo | Studiare insieme controllo, traffico e regole. Hardware, reti e budget non sono confrontabili con la board |
| [Ng, Harada, Russell, ICML 1999; paper](https://people.eecs.berkeley.edu/~pabbeel/cs287-fa09/readings/NgHaradaRussell-shaping-ICML1999.pdf), [pagina dell'autore](https://wordpress.andrewng.org/index.php/publication/policy-invariance-under-reward-transformations-theory-and-application-to-reward-shaping/) | Lo shaping come gamma Φ(s') − Φ(s) preserva la policy ottima sotto le condizioni del risultato | Possibile aiuto denso di curva/margine. Terminale con potenziale coerente, truncation non azzerata; non garantisce convergenza della nostra rete |
| [Learning Autonomous Race Driving with Action Mapping RL, 2024](https://arxiv.org/html/2406.14934v1) | Reward per velocità lungo pista e costi per uscita/direzione/attrito; mapping delle azioni come approccio distinto | Utile il ruolo dell'attrito. Non copiare −100: unità/dinamica/frequenza diverse. Mapping sarebbe assistenza esplicita, non una competenza spontanea |
| [Comparing DRL architectures for autonomous racing, F1TENTH](https://f1tenth.github.io/publications/deep_reinforcement_learning.pdf) | Confronto di architetture, reward e algoritmi nel racing | Separare disegno dell'obiettivo e capacità di apprenderlo; non introdurre una nuova architettura per mascherare una reward debole |
| [Schulman et al., GAE, 2015](https://arxiv.org/abs/1506.02438) | Stima dei vantaggi con compromesso fra bias e varianza | Studiare λ e critic con ritardi di frenata misurati |
| [Farama, Handling Time Limits](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/) | Terminale e limite esterno richiedono bootstrap diverso | Conservare la semantica corretta delle finestre infinite |
| [Henderson et al., Deep RL that Matters](https://arxiv.org/abs/1709.06560), [Agarwal et al., Statistical Precipice](https://arxiv.org/abs/2108.13264) | Variabilità, riproducibilità e incertezza dei confronti | Semi distinti, prove accoppiate, distribuzioni e intervalli; cinque semi sono screening, non superiorità universale |

Le proposte numeriche di questo documento sono **inferenze progettuali per il nostro simulatore**, non coefficienti prescritti da queste pubblicazioni. Shaping arbitrario di freno, centro pista o permanenza può cambiare l'obiettivo. Per potenziali usare formula scontata, stato/timer osservabili, condizioni terminali coerenti e versione fissa durante il confronto; non dichiarare invarianti tutti i termini della proposta R2.

## 12. Piano di taratura senza cambiare tutto insieme

### B0 · Misure e contratto

Versionare RewardSpec con nomi, unità, coefficienti e hash; registrare i termini per giro/esercizio, causa reale del ritiro, pedale, richieste/aderenza, tempi e contesto. Separare somme per slot/generazione da somme per vita continua del pilota. I totali devono riconciliare il reward realmente passato al backend.

Controlli mirati: stesso tragitto a sottopassi diversi dà costo integrato coerente; giro pulito continuo pagato una volta; nessun premio doppio su terminale; primo giro sporco non vieta tutti i successivi; avanti/indietro, taglio e tremolio non creano credito.

### B1 · R1 vs R2 e ingresso curva

Prima una rigraduazione su traiettorie congelate: fermo, tutto gas, frenata eccessiva, riferimenti puliti lenti/rapidi, Evo osservato, recupero. Aggiungere Tecnico e una pista lunga; verificare che il detector distingua limiti utili ed errori.

Poi baseline / R1 / R2 su copie con **cinque semi di apprendimento distinti per Evo, NEAT, PPO e PPO-Smooth**, stessi scenari e budget aggregato di passi. Budget iniziale proposto: 200.000 passi per combinazione; durata CPU registrata e stop anticipato dichiarato. Prima Evo/Ovale per screening, poi estendere le varianti non bocciate; non imporre subito 60 esperimenti lunghi sulla board. Le cinque variazioni della prova attuale non sono cinque addestramenti indipendenti.

Per variante congelare il risultato e misurare 20 ingressi curva + 20 giri riservati, includendo casi senza bisogno di freno e con frenata necessaria. Dati per seed, mediana, intervallo e motivi di fallimento; mai selezionare solo il seed migliore. Obiettivo di screening candidato: ≥18/20 curve completate per seed, nessun aumento degli stalli sui casi liberi, riduzione dei ritiri rispetto alla baseline. Se la baseline è già competente, non accettare peggioramento di arrivi per un minor slip.

### B2 · Passo ed esplorazione

Con la reward scelta: isolare pressione sul tempo e curriculum; poi λ PPO/rollout se il credito ritardato rimane un problema. Per Evo/NEAT misurare disponibilità di rilascio/freno fra candidati e diversità delle traiettorie prima di cambiare mutazioni/topologia.

Promozione candidata: arrivi almeno pari al campione nel set accoppiato; mediana pulita migliore di almeno il maggiore fra 0,1 s e 1%, salvo recupero esplicito di affidabilità. Riportare anche p90 e fallimenti. Questa è una soglia di prodotto proposta, non una significatività statistica universale.

### B3 · Recupero, traffico e trasferimento

Prove ablation del bonus Rientro/sorpasso e attacchi di farming; traffico identico con bot congelati. Successi per incontro, contatti e ritiri per km e per incontro, non solo sorpassi totali. Confronto Ovale → Varano → Ovale e auto/fondi futuri quando realmente disponibili; la memoria viene trasferita, i tempi ufficiali restano locali.

### B4 · Compatibilità e board

Alla prima implementazione autorizzata, creare percorso/checkpoint versionato con pesi/topologia personali conservati. Azzerare soltanto fitness non confrontabili, rollout PPO e stato del critic/optimizer quando richiesto dalla migrazione; descrivere la scelta e conservare l'originale. Non mescolare episodicamente due RewardSpec nello stesso update.

Rivalutare élite/candidato sul nuovo obiettivo, mantenere qualifiche congelate precedenti nel loro scope, registrare hash reward/curriculum nei risultati. Pausa/salvataggio/ripresa riproducibili. Prova mirata sul carico maturo 32 copie, clock 30 Hz e tre temi: nessuna nuova elaborazione costosa nel thread GUI o moltiplicazione delle velocità per far sembrare più rapido il movimento.

## 13. UI e risorse

La pista conserva spazio e proporzioni. Nella Vista Pilota proporre un indicatore compatto **Gas / Rilascio / Freno**; stato «Aderenza al limite» solo se il detector è verificato. Nel dossier: giri puliti/totali, tempo mediano/migliore, ritiri distinti, tempo fuori, stallo libero vs attesa nel traffico, distribuzione dei pedali e versione del protocollo. I punti di reward appartengono alla diagnostica con spiegazione, non sostituiscono tempi e risultati.

Impostazioni: mantenere i profili manuali non modificabili e le descrizioni coerenti al tema. Aggiungere lettura del protocollo/obiettivo effettivo e fase; evitare una schermata con molti coefficienti da regolare per «insegnare a frenare». Le varianti R1/R2 sono strumenti di studio con identità chiara.

CPU: fisica, sensori e termini scalari/vettorizzati nel worker. GPU: rendering già esistente. NPU: non richiesta dal riequilibrio della reward; nessun beneficio dichiarato senza nuovo carico misurato. RAM: buffer limitati di telemetria, scenari/curve precalcolati, dati storici su disco; non inviare 32 tracce complete a QML a ogni frame. La prova PC di 55,8 s non è una misura del costo aggiuntivo sulla board.

## 14. Esito dello studio

Diagnosi numerica acquisita e proposta pronta per sperimentazione. **Priorità: premio di giro pulito in continuo, esercizi che insegnano la gestione dell'ingresso curva, pesi comparabili fra piste, detector di sottosterzo verificato e promozione per risultati riservati.** L'obiettivo finale è il tempo sul giro pulito e la capacità di gareggiare; una percentuale maggiore di frenata non dimostra da sola un miglioramento.

Rimangono aperti: confronto di apprendimento R1/R2, soglie di aderenza, credito PPO, affidabilità sul traffico/trasferimento e costo board. Lo studio prepara questi lotti nel MasterPlan senza dichiararli implementati o installati.
