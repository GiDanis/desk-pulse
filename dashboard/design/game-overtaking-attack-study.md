# Impara sorpasso — attacco, passo e controllo

**22 ottobre 2026 · Europe/Rome · studio concluso; seguito nell’[implementazione e verifica A0–A7](v09-overtaking-attack-report.md).**

Richiesta: i piloti devono cercare il passaggio, completarlo e proseguire veloci; stare in coda o affiancati senza guadagnare terreno non deve diventare la soluzione abituale. [Evidenze e riproduzione](evidence/v09-overtaking-study-2026-10-22/README.md).

## 1. Conclusione

Il problema è riprodotto sui checkpoint attuali e **non si risolve aumentando soltanto il bonus di sorpasso**. Ci sono quattro ostacoli verificati nel codice e nelle sonde:

1. La presenza dei rivali seleziona quasi completamente l'esperto traffico prudente, escludendo la competenza veloce acquisita in solitaria. Con due rivali il selettore della base assegna al traffico il **99,9999949%**.
2. Esiste un premio specifico per il passaggio concluso, ma manca un segnale specifico continuo per il terreno guadagnato o perso sul rivale. Progresso e costo del tempo sono già presenti: non siamo in assenza di incentivi alla velocità.
3. La versione gara può essere proposta solo migliorando prima il giro in solitaria. Un candidato migliore nei sorpassi, a tempo solo invariato, non arriva alla verifica gara. Le ripartenze dal campione solo possono inoltre cancellare un tentativo tattico utile prima che sia riconosciuto.
4. Nella modalità continua una fine finestra conserva lo stesso scenario/fase. La rotazione del curriculum avviene alla creazione di un nuovo episodio: una guida senza errori può quindi allenarsi per minuti sempre in Difesa, mentre la preview mostra Sorpasso.

Proposta: **competenza veloce conservata, base traffico preparata per attaccare, selezione neurale meno satura, premio relativo simmetrico e promozione tattica indipendente dal nuovo PB**. Sterzo e pedale rimangono interamente neurali. Nessun controllore agli attuatori, né acceleratore obbligatorio.

## 2. Baseline e prove effettuate

Lettura della board in sola lettura alle **01:47:39 italiane del 22 ottobre** (`23:47:39Z` del 21): core **0.9.0-rc.28**, servizio attivo, `NRestarts=0`, ultima sessione salvata in pausa. Quattordici file rilevanti del simulatore/reti/basi coincidono per SHA256 tra board e copia PC. La candidata trasversale locale 0.9.3-rc.1 non viene attribuita al software installato.

Quattro checkpoint verificati contro l'hash del file, copiati in una directory privata esterna al progetto. Contengono aggiornamenti reali salvati: Crono 631, Memoria 12.257, Linea 22.047, Tattico 5.601 nella ricetta corrente. Non sono contatori confrontabili di costo fra metodi e non dimostrano convergenza. Crono e Memoria hanno `impara_sorpasso` come ultimo obiettivo; Linea e Tattico `impara`.

**48 episodi congelati**, senza apprendimento: tre semi di scenario comuni, candidati attuali, versioni gara e due basi di fabbrica. Su Ovale 1, fisica corrente a 60 Hz, decisioni a 10 Hz, due bot, finestra massima 60 s simulati; alcune prove Memoria finiscono prima. I semi variano lo scenario, **non sono tre addestramenti indipendenti**. Velocità: media temporale campionata a 10 Hz dopo i primi 5 s, poi media dei tre casi; non V max né velocità dell'intero giro.

| Policy congelata | Senza traffico, km/h | Con due bot, km/h | Sorpassi con bot | Eventi contatto / uscite con bot |
| --- | ---: | ---: | ---: | ---: |
| Crono, candidato | 58,65 | 23,89 | 0 | 0 / 0 |
| Memoria, candidato | 50,17* | 21,60* | 0 | 0 / 14 |
| Linea, candidato | 61,18 | 23,95 | 0 | 0 / 0 |
| Tattico, candidato | 45,85 | 24,26 | 4 | 12 / 0 |
| Base guida | 54,10 | 23,94 | 0 | 0 / 0 |
| Base traffico | 54,10 | 39,15 | 6 | 0 / 6 |

\* Memoria esce anche nelle prove senza traffico: non è un confronto fra giri validi. Le versioni gara Crono/Memoria/Linea restano circa 23,94 km/h, zero sorpassi; Tattico gara coincide nei risultati con la base traffico. Un passaggio localmente pulito non rende valida tutta una sessione con uscite successive.

**Ablazione causale aggiuntiva, tre casi abbinati:** sulla sola base di fabbrica, copiare l'esperto veloce A anche nel posto B, conservando selettore, osservazioni dei rivali, fisica e comandi neurali, porta la media a **48,99 km/h**, con **2 sorpassi e 74 eventi di contatto**, contro 23,94 km/h, zero passaggi/contatti della base originale. Dimostra l'effetto della scelta dell'esperto in questi casi e il costo di eliminarne la prudenza indiscriminatamente. Non è una soluzione da installare.

È riprodotta la rinuncia al sorpasso. **L'arresto assoluto mentre affiancati non è riprodotto nelle 48 sonde** con la definizione diagnostica velocità <1 m/s e prossimità longitudinale/fisica; rimane da correlare a una traccia lunga del caso visualizzato. Il salvataggio preview Crono contiene già 273 s simulati e zero passaggi. Le sonde non misurano FPS, prestazioni della board o miglioramento durante nuovi aggiornamenti.

## 3. Diagnosi punto per punto

### 3.1 Il selettore distingue presenza, non necessità di prudenza

La base contiene due esperti da 64 unità e un selettore sigmoidale allenabile. Il selettore iniziale è stato preparato sui soli tre flag di presenza dei rivali; i sensori li possono vedere entro 150 m **fisici**, anche se sono dietro o lontani lungo il circuito.

| Rivali osservati dalla base | Peso esperto traffico | Derivata del selettore |
| --- | ---: | ---: |
| 0 | 0,873% | 0,00865 |
| 1 | 99,7604% | 0,00239 |
| 2 | 99,9999949% | circa 5,08 × 10⁻⁸ |
| 3 | quasi 100% | circa 1,07 × 10⁻¹² |

La saturazione rende difficile modificare il selettore mediante gradienti; non prova che sia matematicamente immutabile con Adam. Nei checkpoint il suo scostamento L2 dalla base è circa 5,9 × 10⁻⁷ Crono, 5,8 × 10⁻⁹ Memoria, zero Linea e 0,0138 Tattico. L'esperto B può comunque cambiare. Il routing attuale aggiorna A sui campioni senza rivali, B e selettore sui campioni con rivali: conserva il passo solo, ma non trasferisce automaticamente quel passo a B.

**Intervento da confrontare:** preparare B con passo libero, attacco e difesa; preparare il selettore con distanza, velocità relativa, separazione laterale e rischio, evitando logits iniziali estremi. Confrontare questa miscela con una singola policy diretta preparata sugli stessi dati. Nessun cambio manuale di esperto durante la guida, nessuna rimozione cieca del routing o della protezione Adam già corretta.

### 3.2 Il premio è tardivo e «tentativo» oggi è un nome troppo generoso

Il rilevatore arma l'incontro quando trova un rivale davanti a meno di 40 m e incrementa `pass_attempts`: **è un incontro disponibile, non la prova che l'auto abbia attaccato**. Richiede poi affiancamento, avanzamento oltre `lunghezza auto + 1 m` e mantenimento pulito di 0,5 s. Conserva cooldown e un credito per rivale/banda di giro: queste protezioni già esistono.

Premi attuali: passaggio +0,5; violazione sportiva −2; ritiro −3; uscita −0,5; contatto a velocità d'impatto 1 m/s −0,35, a 5 m/s −0,95. Non sono equivalenze fra ritorni attesi: contano sconto, durata e critic. Il bonus non è nullo, ma il solo suo aumento non insegna come completare il tratto intermedio.

Nelle finestre continue si riceve 1 per giro di progresso valido; negli esercizi finiti di sorpasso 2, oltre a successo/insuccesso del compito. Il critic dispone del contesto finito/fase: questa differenza non dimostra da sola un errore. Le finestre di 60 s sono già troncamenti che continuano fisica/incontri, non sconfitte da trasformare in terminali. La finestra non va premiata come un passaggio riuscito.

### 3.3 Il criterio di promozione non misura il miglioramento tattico

In `RacingCheck`, `raceProposed` richiede tre verifiche solo valide e un nuovo miglioramento rispetto al tempo solo di riferimento della policy gara. In seguito controlla due griglie e regressioni di sicurezza; soltanto Tattico ha anche otto prove tattiche specifiche. **Nessun tempo di sorpasso o tasso di attacco può proporre da solo il candidato.**

Il reset del candidato torna all'intero campione solo quando i controlli falliscono o non danno guadagno: nei salvataggi sono registrate 14/13/32/5 ripartenze rispettivamente per Crono/Memoria/Linea/Tattico. Non tutte dipendono dal traffico; il rischio di perdere una variante tattica è strutturale, da isolare nel confronto.

Proposta: candidato, migliore solo e migliore traffico distinti. Conservare A mentre si prova B/selettore; ripartire dal migliore del compito. Permettere promozione tattica con miglioramento di passaggi/tempo di completamento, sicurezza mantenuta e passo solo entro una tolleranza esplicita. La policy risultante deve rifare verifiche e Qualifica con il proprio hash.

### 3.4 Girare all'infinito può bloccare la varietà del curriculum

`new_episode()` sceglie una fase secondo il numero di episodi; una finestra continua invece chiama `next_window()` sullo stesso ambiente, conservandone fase, fisica e incontri. È giusto non teletrasportare l'auto visibile ogni minuto, ma il campionatore degli esercizi non deve dipendere soltanto da un errore che forza il reset. Nel checkpoint Crono la raccolta è ancora **Difesa a 296,98 s**, mentre la preview è **Sorpasso a 273,07 s**; Memoria raccoglie **Affiancamento a 426,38 s**.

Non è prova di dati immobili: i learner aggiornano e le finestre avanzano. È copertura poco controllata delle competenze. Proposta: budget di raccolta per famiglia in passi/secondi, esercizi brevi in background e ripasso esplicito, indipendenti dalla continuità della preview. Mostrare la fase reale dell'apprendimento quando differisce dalla prova visibile. Misurare la distribuzione effettiva dei dati, oltre alle probabilità nominali del curriculum.

## 4. Ricerca: cosa riprendere e quali limiti rispettare

Fonti primarie consultate il 22 ottobre; le scelte sotto sono adattamenti proposti, non risultati già ottenuti da SmartPC.

| Fonte | Riscontro utile | Applicazione proposta |
| --- | --- | --- |
| [Wurman et al., Nature 2022, testo degli autori](https://www.cs.utexas.edu/users/pstone/Papers/bib2html-links/nature22.pdf), pp. 225–226, Methods Rewards/Training scenarios | Il solo progresso può produrre accodamento. Premio simmetrico sul terreno relativo, scenari misti e replay stratificato aiutano; penalità generiche di contatto eccessive inducono timidezza. | Delta relativo con segno, copertura di manovre e campionamento bilanciato; selezione su più metriche. Non copiare pesi né dimensioni delle reti. |
| [Song et al., ICRA 2021](https://rpg.ifi.uzh.ch/docs/ICRA21_Yunlong.pdf), sez. III–IV | Trasferiscono la guida veloce al sorpasso e poi consolidano l'evitamento; ricompensa continua per il vantaggio relativo. | Esercizi facili e ripetibili prima dei duelli difficili, velocità sufficiente per raggiungere il bot, ripasso della guida sola. Le loro penalità non sono unità del nostro simulatore. |
| [Steiner et al., TD3-Overtake, preprint 2025](https://arxiv.org/html/2510.26040v1), sez. III/IV/VI | Addestramento con avversari, partenze variate e vantaggio di velocità; rimuovono il bonus esplicito di sorpasso dopo abusi osservati. Il limite di velocità e l'avversario rallentato restringono l'interpretazione del risultato. | Confrontare una variante senza nuovo bonus terminale, con soli scenari migliori. Non assumere che ogni problema richieda più ricompense. Il loro comando è velocità desiderata, il nostro pedale: pesi/modelli non trasferibili direttamente. |
| [Team Sony AI, esperienza di produzione 2024](https://ai.sony/archive/from-hypothesis-to-reality-the-gt-sophy-team-explains-the-evolution-of-the-breakthrough-ai-agent?hs_amp=true) | Descrivono errori in situazioni poco coperte, e interventi su posizioni iniziali, numero di avversari, premi e prove. | Aggiungere casi difficili osservati alle sole banche di sviluppo; tenere separata la banca finale. È esperienza degli autori, non un'ablation controllata. |
| [Ng, Harada, Russell, ICML 1999](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf) | Condizioni per shaping potenziale che preservi l'obiettivo. | Eventuale `γ Φ(next) − Φ(now)` al confine di decisione, con terminali coerenti; nessuna garanzia di convergenza della rete approssimata. |
| [Gymnasium, gestione dei limiti](https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/) | Terminale del compito e taglio esterno hanno bootstrap diversi. | Conservare le finestre continue, testare salvataggio/ripresa/terminali e non usare una fine finestra come successo o punizione. |

**Copia utile:** adattare formule, disegno degli scenari e protocolli, con attribuzione. Il [repository pubblico Sophy](https://github.com/SonyResearch/gt_sophy_public) espone soprattutto materiale video, non una policy pronta da installare; il supplemento descrive pseudocodice. TD3-Overtake rimanda al [codice degli autori](https://github.com/UoA-CARES/autonomous_f1tenth), basato su ROS/Gazebo: può guidare l'analisi degli scenari. La licenza complessiva di quel repository non è stata accertata; nessun suo codice è importato. Eventuali copie letterali richiedono verifica della licenza del file preciso. Non servono ROS/Gazebo sulla board per applicare queste idee.

## 5. Ricetta di attacco da sperimentare

### 5.1 Obiettivo e segnali

Separare **obiettivo competitivo** e **aiuto temporaneo all'apprendimento**:

```
R = progresso valido − costo del tempo
    + vantaggio relativo con segno
    + eventuale premio unico di passaggio confermato
    − conseguenze di contatti, uscite e manovre irregolari
    + eventuale shaping potenziale temporaneo
```

Proposta iniziale per l'esperimento relativo: distanza dell'ego meno distanza del rivale, continua durante l'incontro; scala di confronto 40 m e coefficienti 0 / 0,25 / 0,5. Sono **candidati da confrontare, nessun default scelto**. Guadagnare terreno dà segno positivo, perderlo negativo. Non sommare solo i delta positivi. Un piccolo guadagno seguito da perdita non deve creare un ciclo vantaggioso; verificare anche il ritorno scontato.

Usare incontri con identità stabile e gap svolto, non il solo modulo del giro. Mascherare il vantaggio ottenuto fuori pista o per spinta, ma addebitare coerentemente le perdite; non resettare favorevolmente il potenziale al limite di prossimità, al cambio del rivale più vicino o a una finestra. Banca di abusi dedicata per capire se il termine modifica l'obiettivo in modo indesiderato. Un delta relativo aggiunto all'obiettivo competitivo **non è automaticamente shaping invariante**: riservare questo nome alla forma potenziale corretta.

Conservare come riferimento +0,5 del passaggio; confrontare prima premio relativo e curriculum senza aumentarli insieme. Nessun premio permanente per gas, solo affiancamento, sterzata di attacco o prossimità. Sono diagnostiche, non successi da accumulare. Una rinuncia per spazio chiuso deve rimanere una scelta valida; una coda prolungata con corridoio praticabile va misurata come occasione non sfruttata. Evitare una nuova punizione generica per l'attesa prima di aver distinto questi casi.

Contatti: mantenere le conseguenze reali; auditare le regole di spazio/frenata nei casi di attacco. Separare contatto lieve, impatto importante e ritiro nelle metriche, senza inventare colpe o intenzioni. Attribuzione semplice solo se geometricamente verificabile; contatti ego e contatti dell'intera griglia vanno riportati entrambi. Non eliminare i limiti per far crescere il numero dei sorpassi.

### 5.2 Esercizi e preparazione della base

| Fase | Scenario | Cosa deve apprendere |
| --- | --- | --- |
| S0 · passo | Solo, più traiettorie/aderenze | Conservare accelerazione, frenata e stabilità già acquisite. |
| S1 · completamento | Già affiancato, corridoi ampi, bot più lento | Continuare ad accelerare quando c'è spazio e portare il corpo vettura interamente avanti. |
| S2 · attacco | Un bot davanti, rettilineo, lato libero alternato | Uscire dalla scia senza inseguire il bot sulla stessa linea. |
| S3 · curva | Interno/esterno, ingressi diversi, bot non sempre cedente | Frenata, spazio affiancati, incrocio e uscita migliore. |
| S4 · difesa e rinuncia | Rivale dietro, o varco realmente chiuso | Difesa regolare; interrompere l'attacco quando necessario e riprovare alla prossima occasione. |
| S5 · traffico/gara | 2–4 rivali congelati con stili diversi | Trasferire le abilità, mantenere il passo dopo il passaggio, gare di più giri. |

Prime esercitazioni con vantaggio di passo del learner e bot su una linea prevedibile; poi ridurre il vantaggio fino a parità di auto. Non cambiare la potenza dell'ego in Gara. Per ogni fase, casi speculari sui due lati e abbastanza spazio/tempo per concludere. Alternare esercizi brevi e finestre continue per non consumare minuti ad aspettare un incontro.

Il Maestro può produrre esempi offline, ma va prima verificato nel nuovo scenario: un docente che affianca e rallenta trasferisce proprio il difetto. Aggiungere esempi riusciti, falliti e recuperi, con dati reali completi per il replay; etichette corrette per la preparazione supervisionata. Testare poi la rete da sola. Nessuna chiamata al Maestro durante l'inferenza del pilota.

### 5.3 Sensori, esplorazione e differenze fra metodi

I canali attuali espongono già posizione/velocità relativa, orientamento, ingombro, rischio di collisione e geometria stradale. Prima misurare se sono usati. Valutare solo in un'ablation successiva gap e velocità **lungo la pista**, spazio laterale e identità stabile del rivale; in curva i soli valori nel corpo vettura possono essere ambigui. Nuova versione degli ingressi e preparazione compatibile se si aggiungono canali. Nessun accesso ad azioni future o traiettoria ideale dell'avversario.

| Pilota | Lavoro specifico proposto |
| --- | --- |
| Crono / PPO | Rollout con occasioni di attacco reali, esplorazione laterale coerente e probabilità esatte. Conservare la correzione del rumore longitudinale; non premiare un gesto di attacco fine a sé stesso. |
| Memoria / SAC | Prima contenere la regressione di uscita del candidato; replay stratificato con successi, tentativi abortiti, completamenti e passo solo. Non riempire il replay soltanto di code. |
| Linea / TD3 | Perturbazioni temporaneamente coerenti di manovra, non solo rumore istantaneo; stesso criterio tattico e replay bilanciato. Non assumere mancata competenza dal solo fatto che finora è stato allenato soprattutto in `impara`. |
| Tattico / TD3 | Gli attacchi esistono, ma il candidato aumenta i contatti: lavorare su completamento pulito e spazio, conservando la migliore variante traffico mentre si prova la nuova. Nessun bonus aggiuntivo per urgenza senza prova. |

Per SAC/TD3 confrontare una distribuzione iniziale dichiarata di replay: 30% attacco/completamento, 20% curva affiancati, 15% difesa/rinuncia, 25% passo solo, 10% recuperi. Quote sperimentali, con conteggi e sostituzione esplicita quando un gruppo è vuoto; non chiamarlo PER. Per PPO bilanciare la raccolta corrente degli scenari, senza rigiocare vecchi rollout come se fossero on-policy. Niente self-play simultaneo necessario nella prima fase: pool di avversari congelati e versionati sufficiente, nuovi snapshot solo dopo qualifica.

## 6. Metriche visibili e gate proposti

Distinguere: **incontri → occasioni praticabili → attacchi avviati → affiancamenti → passaggi confermati → rinunce/occasioni perse**. L'attacco richiede uno spostamento utile o un reale avanzamento relativo, non l'armamento del detector. Esporre a schermo una sola frase e due numeri utili, per esempio «Completa il passaggio · 2/4 riusciti · 6,2 s»; dettagli in risultati/dossier.

Registrare tempo al passaggio, tempo e terreno persi in coda, durata affiancato senza avanzare, contatti ego/globali, uscite, cause di rinuncia, passo dopo sorpasso e miglioramento rispetto alla **medesima policy** precedente. PB solo, competenza tattica e risultato gara restano distinti. Finestra finita: «60 s di allenamento», non «prova riuscita» se nessun passaggio è avvenuto.

**Soglie iniziali da congelare prima del confronto**, non risultati già raggiunti:

- ≥90% di passaggi puliti nella banca facile di completamento/rettilineo, per ciascun seme di training;
- ≥75% nella banca curva/traffico e nessuna famiglia critica con zero successi;
- attacco avviato entro 3 s nel ≥80% delle occasioni facili realmente praticabili; ≥50% di riduzione del tempo perso affiancato/in coda rispetto alla baseline sullo stesso insieme;
- nessun aumento di impatti gravi, ritiri o uscite; contatti lievi riportati senza nasconderli dietro la media;
- passo solo mediano non peggiore di oltre 1%, confrontato con lo stesso punto di partenza; soglia applicata anche al peggior seme;
- gare a 2 e 5 auto su tre giri, tutte visibili, arrivi validi; miglioramento tattico misurato anche contro avversari diversi da quelli di raccolta;
- nessun ciclo positivo da lasciarsi superare/ripassare, taglio, spinta, bot ritirato, wrap, cambio rivale o salvataggio/ripresa.

Un gate aggregato non sostituisce il risultato peggiore per metodo/famiglia. Le opportunità facili della banca devono essere prima dimostrate fisicamente percorribili con un docente congelato; il docente non certifica la convergenza della rete.

## 7. Piano di attuazione A0–A7

| Passo | Contenuto | Stato |
| --- | --- | --- |
| A0 | Baseline reale, hash, sonde congelate e ablazione esperti. | **Concluso in questo studio**; copie personali private. |
| A1 | Metriche/incontri/occasioni/attacchi, banca sviluppo/finale nuove. | Implementato; tempi unici, partenze già affiancate e latenza distinti. Tracce prolungate in banca finale. |
| A2 | Selezione tattica autonoma, checkpoint del migliore traffico, ripartenza per compito, Qualifica legata alla policy gara. | Implementato e verificato; attivazione solo nella ricetta sperimentale. |
| A3 | Base traffico e selettore vs rete singola/preparazione offline. | Confronti eseguiti; nessuna nuova base supera la qualifica estesa. |
| A4 | Premio relativo 0/0,25/0,5, regole e abusi. | Termine implementato; varianti positive respinte in sviluppo, finale con 0. Nessun nuovo potenziale promosso. |
| A5 | Raccolta finita indipendente dalle finestre continue, replay/rollout e rumore specifico. | Implementato sperimentale; rotazione di esercizi con limiti 24/60 s, non quote garantite di tempo per famiglia. Non promosso. |
| A6 | Cinque semi completi per metodo, banche separate e confronto abbinato. | Completati 40 training e banca finale/supplemento. Tutti i metodi falliscono traffico esteso e riduzione attesa; nessun default nuovo. |
| A7 | Compatibilità, GUI 960×640 nei tre temi, ARM e consegna. | Verifiche tecniche e consegna della diagnostica nel report. La ricetta resta isolata: installazione del codice e qualifica scientifica distinte. |

Budget iniziale proposto: **196.608 passi fisici raccolti per metodo/seme/variante**, stesso rapporto aggiornamenti/dati dichiarato; scegliere il confronto lungo prima di vedere il finale. Contare a parte preparazione/docente, decisioni, gradienti, verifiche, tempo simulato, tempo reale e risorse. Cinque semi nuovi di training, separati dai tre semi diagnostici; banca finale congelata e mai usata per scegliere coefficienti. Per confrontare preparazioni, ripeterle con semi indipendenti: cinque continuazioni della stessa base non sono cinque preparazioni.

Non riproporre come già approvata la ricetta «premi comuni + distanza + regole» respinta nel [confronto del 16 ottobre](v09-overtaking-fluidity-report.md). Il controllo attuale è diretto neurale, diverso da quello residuale di allora; serve comunque separare i cambiamenti per attribuire i risultati. Prima A2, poi selettore/base, poi premi e curriculum: non un unico reset con tutte le modifiche insieme.

## 8. Dati, prestazioni e stato di consegna

**Nessun reset dei piloti in questo studio.** Preservare identità, esperienza veloce, campioni, storico e originali immutabili. La futura ricetta archivia i target vecchi: replay ricalcolato solo se contiene stati/eventi sufficienti, altrimenti nuova epoca dei target; critic e ottimizzatori delle parti coinvolte vanno trattati esplicitamente. Non riusare ritorni vecchi senza versione. La soluzione non richiede eliminare tutti i piloti o importare pesi di un altro simulatore.

CPU per fisica e apprendimento, GPU per Qt Quick, NPU invariata. Esercizi mirati possono migliorare l'efficienza dei campioni; non garantiscono un guadagno esponenziale né meno secondi reali senza misura. Replay e tracce devono rimanere limitati e fuori dal percorso del rendering; verifiche tattiche scaglionate con budget visibile. Nessuna nuova richiesta di calcolo a vista chiusa.

La fase originaria di studio consegnava ricerca, 48 sonde più 3 ablazioni, script e MasterPlan, senza modifiche runtime o di produzione. Le implementazioni successive e il loro stato di consegna sono nel [report A0–A7](v09-overtaking-attack-report.md): la nuova ricetta non supera i criteri di promozione e non è attivata sui piloti personali.
