# Guida diretta — velocità costante e candidati più lenti

**20 ottobre 2026, snapshot dei salvataggi intorno alle 23:05 Europe/Rome.**
Diagnosi della rc.25, successiva alla consegna. Lettura SQLite in transazione
sola lettura, senza costruire GameStore; nessuna pausa, modifica dei piloti,
riavvio o nuova ricetta installata. Memoria risultava in esecuzione: i dati qui
sono i checkpoint persistiti, non lo stato ancora in RAM.

[Evidenze e script](evidence/v09-direct-pace-diagnosis-2026-10-20/).

## 1. Il peggioramento osservato esiste

| Misura nel salvataggio | Crono | Memoria |
| --- | ---: | ---: |
| Passi fisici | 411.181 | 32.185 |
| Decisioni | 68.637 | 5.373 |
| Update | 536 | 1.312 |
| Base, verifica finita da fermo | 28,267 s | 28,267 s |
| Migliore verifica conservata | 25,667 s | 28,267 s |
| Ultimo candidato verificato | 25,800 s | 28,667 s |
| PB lanciato nella preview | 24,021 s | 26,739 s |
| Ultimo giro lanciato nella preview | 24,212 s | 27,152 s |

Crono ha migliorato circa il 9,20% nella verifica da fermo, ma gli ultimi
candidati sono peggiori. Memoria non aveva ancora promosso un miglioramento.
Il giro visibile e i suoi intertempi riguardano il **candidato**, aggiornato al
confine del giro; non il campione conservato. Qualifica/Gara scelgono la policy
ammessa e verificata, non promuovono automaticamente ogni candidato.

Il PB della preview può appartenere a una policy diversa; inoltre una nuova
policy eredita lo stato fisico del confine del giro precedente. I confronti
isolati da fermo e i giri lanciati non sono intercambiabili.
[Snapshot riassunto](evidence/v09-direct-pace-diagnosis-2026-10-20/saved-state-summary.json).

## 2. Il pieno gas è disponibile e può convenire

Sulla copia PC, stesso stato iniziale e seme 91001, reti congelate. Solo nella
parte centrale del rettilineo (`abs(x)<20`, `abs(y)>28`, yaw rate sotto 0,05)
una sonda impone un minimo di pedale; sterzo e resto della guida restano della
rete. È un **controfattuale diagnostico**, non un assistente inserito nel gioco.

| Policy | Normale | Pedale minimo 0,25 | Minimo 0,50 | Pieno gas nella zona |
| --- | ---: | ---: | ---: | ---: |
| Base A | 28,283 s | 27,950 s | 27,650 s | 27,133 s |
| Crono campione | 25,667 s | 25,650 s | 25,617 s | 25,400 s |
| Crono candidato salvato | 25,917 s | 25,767 s | 25,800 s | 25,417 s |
| Memoria candidato salvato | 33,700 s | 33,300 s | 33,450 s | 32,783 s |

Tutte le 24 prove di questa sonda completate senza contatti o limiti pista.
Per A il premio ambientale non scontato passa da 0,248951 a 0,279198; per il
campione Crono da 0,308329 a 0,316695. Anche il premio corrente favorisce il
passaggio più rapido in questo caso. Questi risultati non certificano che il
pieno gas sia sicuro in ogni tratto, su altri fondi o in traffico.

Il candidato Memoria salvato dopo la sua ultima verifica è ulteriormente
peggiorato: 33,700 s in questa nuova prova, rispetto al precedente 28,667 s
registrato nella verifica. Il campione è ancora A. La deriva è quindi reale,
non soltanto arrotondamento dei millesimi.
[Tracce e premi](evidence/v09-direct-pace-diagnosis-2026-10-20/policy-counterfactuals.json).

## 3. Cause confermate e ipotesi

**Confermato dal codice e dalle prove:**

- La base A ha imitato un controllore con passo prudente: apprende una politica
  simile a un regolatore di velocità. Rimuovere il bot dagli attuatori non
  rimuove automaticamente questa abitudine dai pesi.
- Nessun tetto 36/45 km/h e nessuna penalità del gas in sé. Nella sonda A può
  raggiungere circa 75,8 km/h, il campione Crono circa 64,5 km/h, col pedale
  modificato nel tratto centrale. Non sono velocità raggiunte dalla rete da sola.
- Rumore longitudinale piccolo: sigma latente iniziale 0,10, nuova estrazione
  ogni 0,1 s; nell'ultimo salvataggio circa 0,099 per Crono e 0,113 per Memoria.
  Vicino al pedale di crociera questo produce soprattutto piccole variazioni:
  non equivale a sperimentare deliberatamente uno o due secondi di pieno gas,
  seguiti da una frenata anticipata.
- SAC usa un attore con LR 10⁻⁵ e critic appresi dai propri campioni; la prima
  fase ha anche l'ancora verso la rete iniziale. A 5.373 transizioni l'ancora
  prevista fino a 4.096 è già nulla: non spiega da sola il peggioramento attuale.
- PPO non ha il meccanismo di ripartenza dell'attore dai campioni migliori
  presente in SAC/TD3. I candidati possono continuare a peggiorare pur
  conservando il migliore separatamente; il display non rende abbastanza
  evidente tale differenza.
- Le prove rc.25 su semi 31–35 non erano una garanzia per i semi prodotto 2/3:
  SAC aveva migliorato soltanto 3/5 semi. Il riepilogo positivo non dimostrava
  convergenza uniforme né capacità di cercare il limite della vettura.

**Ipotesi principale da confrontare:** la ricerca locale intorno alla guida
imitata e un segnale di vantaggio piccolo non producono abbastanza sequenze
longitudinali utili; i critic/gradienti possono spostare il candidato verso
un passo peggiore. Un basso errore del critic sui campioni non certifica la
correttezza delle sue preferenze per azioni molto diverse. La sonda dei gradienti
salvati mostra anche critic con pendenze longitudinali discordi: è un indizio,
non una prova causale completa della deriva.

L'aggiornamento usa gradienti stimati da campioni, non una regola simbolica
“rettilineo = accelera”: [fondamenti della policy optimization, OpenAI](https://spinningup.openai.com/en/latest/spinningup/rl_intro3.html).
Per SAC entrano anche valore appreso ed entropia:
[documentazione primaria SAC](https://spinningup.openai.com/en/latest/algorithms/sac.html).

## 4. Intervento da preparare

1. Esplorazione del pedale più ampia e coerente nel tempo, separata da quella
   dello sterzo; per PPO mantenere probabilità/rapporti coerenti e non inserire
   azioni modificate come se fossero campioni della policy corrente.
2. Esercizi iniziali accelerazione sul rettilineo → frenata → ingresso curva,
   con intervalli di velocità variabili e verifiche del giro completo. Gli
   esercizi preparano la rete; il bot continua a essere assente dalla guida.
3. Confronto longitudinale controllato dei critic SAC con ritorni misurati;
   verificare avvio, scala e aggiornamenti prima di scegliere nuovi coefficienti.
4. Gestire esplicitamente la deriva PPO e distinguere in GUI **candidato in
   prova / campione migliore / ultimo confronto**, senza nascondere gli errori.
5. Conservare il premio fondato su tempo/progresso valido; misurare eventuali
   modifiche di scala. Un bonus diretto al gas da solo può pagare azioni inutili.
6. Confronti completi che includano i semi prodotto 2/3 oltre a gruppi indipendenti,
   giri da fermo e lanciati distinti, rettilinei/curve/contatti e traiettorie.
   Stabilità su budget lungo: il buon risultato di pochi update non basta.

Non è necessario azzerare i piloti per spiegare il fenomeno. La successiva
ricetta dovrà gestire esplicitamente i vecchi replay/critic e mantenere copie
riproducibili dei checkpoint; nessuna modifica attiva eseguita in questa analisi.


## 5. Fondamenti di guida: lacuna confermata nel percorso didattico

Lettura del codice successiva alla segnalazione sul comportamento casuale.
Il completamento del giro non certifica separatamente accelerazione, frenata,
scelta della traiettoria e gestione dell'aderenza.

### Cosa insegna oggi il docente

`game_control.pursuit_actions` segue un punto geometrico avanti sulla strada;
in solo il bersaglio laterale tende al riferimento centrale. Stima una velocità
prudente dalla curvatura e propaga limiti di frenata. Non ottimizza una traiettoria
per minimizzare il tempo sul giro.

Inoltre `maximum = 24 if track.length > 600 else 10`: sul nostro ovale il
riferimento massimo di preparazione è **10 m/s × 1,35 = 48,6 km/h**. La curva
viene affrontata con un riferimento dello stesso ordine. Questo è un limite
del docente usato per generare gli esempi, **non un limite agli attuatori della
rete in esecuzione**. Spiega perché la base tende alla velocità di crociera e
perché le dimostrazioni non rappresentano una guida sportiva completa.

La preparazione include stati a velocità/offset/grip differenti ed esempi di
freno; quindi non è corretto affermare che la rete non abbia mai visto frenare.
Manca la dimostrazione verificata che sappia concatenare accelerazione, punto
di frenata, ingresso, percorrenza e uscita per guadagnare tempo.

### Cosa allena oggi il perfezionamento

Per Crono, Memoria e Linea `new_episode` seleziona principalmente `pace`, con
alcune configurazioni fisiche variate. Le vecchie fasi didattiche presenti nel
progetto non costituiscono un curriculum obbligatorio per questi learner diretti.
Tattico aggiunge esercizi di traffico. I controlli di promozione solo verificano
completamento/tempo del giro; non certificano singolarmente le abilità elencate.

L'attore attuale è una rete feed-forward: i sensori di gomme/fisica forniscono
informazione, ma non sono una conoscenza già appresa né un pianificatore che
simuli e confronti in anticipo più traiettorie. Le variazioni casuali degli
attuatori sono l'esplorazione dei metodi; il gradiente usa i risultati, ma la
progressione didattica attuale non garantisce che emergano le abilità necessarie.

### Preparazione da sostituire, prima della nuova taratura

| Abilità | Esercizio e dimostrazione richiesti | Verifica indipendente |
| --- | --- | --- |
| Accelerazione | Uscita curva e rettilineo a velocità iniziali diverse, gas sostenuto quando utile | Tempo sul tratto, accelerazione, comandi e sicurezza; nessun premio al solo pedale. |
| Frenata | Curva con velocità d'arrivo, grip e potenza diversi; punto di frenata anticipato e rilascio | Velocità/posizione d'ingresso, completamento e tempo fino all'uscita, senza penalizzare la frenata utile. |
| Traiettoria | Alternative geometriche fisicamente percorribili con profilo di velocità coerente | Tempo dell'intera curva/tratto successivo, margini vettura e limiti; evitare una traiettoria obbligatoria premiata per somiglianza. |
| Aderenza | Condizioni nominali e prossime al limite, recupero di errori controllati | Risposta dei comandi, deriva, uscita e tempo su valori esclusi dalla raccolta. |
| Giro e duello | Concatenazione delle abilità, poi avversari con comportamento variabile | Giri lanciati ripetuti e gare, contatti/violazioni separati dal solo arrivo. |

Il nuovo docente dovrà generare esempi confrontando traiettorie e profili di
velocità con la fisica, con provenienza/versione distinta da A/B. La rete li
apprende nella preparazione; il perfezionamento mantiene l'autorità diretta.
Prima di cambiare i default: verifiche delle singole abilità e del giro completo,
più semi incluse le identità prodotto, prova lunga di conservazione del campione.
La competenza iniziale va registrata separatamente dai successivi guadagni RL.

Questo approfondimento amplia la diagnosi: la priorità è una base didattica
più completa e verificabile, insieme all'esplorazione e alla stabilità descritte
sopra. Non basta la dicitura generica “rete preparata” per dichiarare acquisiti
fondamenti di guida sportiva.

## 6. Attuazione successiva — 21 ottobre

La diagnosi resta la fotografia della rc.25. Il [report rc.26](v09-driving-school-report.md) registra nuova preparazione, lezioni, esplorazione, stabilità, migrazione, prove e installazione. Le copie dei vecchi checkpoint e i confronti sono distinti dalle reti installate. Non dichiara risolta la convergenza universale o la competenza tattica generale.
