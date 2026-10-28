# Gioco rc.25 — la rete guida sterzo, gas e freno

**20 ottobre 2026 · rc.25 installata e verificata sulla scheda; perimetro e limiti scientifici sotto.**

Attuazione dello [studio D0–D6](game-direct-driving-study.md).
[Evidenze, script e confronti](evidence/v09-direct-implementation-2026-10-20/).
Questa release cambia il significato delle azioni dei quattro learner: non
interpreta i vecchi pesi residuali come comandi agli attuatori.

## 1. Risultato e rosa

| Pilota | Base iniziale | Perfezionamento |
| --- | --- | --- |
| Maestro | Controllore geometrico esplicito | Riferimento fisso e produttore di esempi, senza aggiornamenti neurali. |
| Crono | Rete preparata A, guida nominale | PPO: esperienze recenti, ricerca del giro valido più rapido. |
| Memoria | Rete preparata A | SAC: replay e policy stocastica durante la raccolta. |
| Linea | Rete preparata A | TD3: attore deterministico, due critic e aggiornamento ritardato. |
| Tattico | Rete preparata B, guida e traffico | TD3 con curriculum di sorpasso/difesa e griglia, verifiche delle abilità. |

Ciascun pilota ha rete, RNG, ottimizzatori, esperienze e campione personali.
La base appresa è già capace; zero passi personali non significa rete casuale.
I campioni dei confronti scientifici non diventano piloti dell'utente.

- Azioni `direct-steer-pedal-v1`: sterzo e pedale firmato, entrambi [-1,1].
  Gas positivo, freno negativo, rilascio a zero; acceleratore e freno simultanei
  richiederebbero un futuro contratto a tre uscite.
- Il bot non corregge, miscela o limita i comandi della rete in apprendimento,
  Qualifica o Gara. Restano i vincoli meccanici e la fisica della vettura.
  Pieno gas disponibile anche oltre 45 km/h; non esiste più un bersaglio di
  velocità imposto dal controllore ai learner.
- MLP con 90 ingressi, 64 neuroni nascosti e due uscite; decisioni 10 Hz, fisica
  60 Hz e grafica con clock separato. CPU per simulazione, inferenza e learning;
  GPU per Qt Quick. Nessun nuovo carico NPU introdotto.
- Sensori: dinamica, deriva, raggi, geometria locale anche a 4/8 m, rivali,
  parametri della vettura e μ configurato. Nessun comando del Maestro, linea
  ideale, velocità obiettivo, ID/posizione assoluta della pista o fase didattica
  nell'attore. μ è un metadato noto del simulatore, non aderenza stimata dalla rete.
- Critic con 94 ingressi, comprendenti il contesto del compito. Comandi precedenti
  e azione mantenuta persistono con il mondo; non si tratta di memoria ricorrente.

## 2. Preparazione delle due basi

Nuovi asset di prodotto `direct-base-1`, preparati in questo lavoro, seme 75001;
nessun vecchio checkpoint utente o campione RL delle sonde riutilizzato.
Imitazione di stati fisici e aggregazione di stati visitati dalla rete, con
etichette del Maestro calcolate separatamente. Questo meccanismo è ispirato a
[DAgger, Ross et al.](https://proceedings.mlr.press/v15/ross11a.html).
La policy certificata contiene soltanto pesi neurali.

| Asset | Preparazione | Hash della policy |
| --- | --- | --- |
| A — guida | 14.959 esempi, sei round; passo del docente ×1,35 | `5d09561e44e01d7fee19112e5e0de76109c33c61fae252478a8ae327620065c2` |
| B — traffico | 15.731 esempi, sei round; memoria della corsia del docente separata | `a09b6d3c76c7b2d1d8cdb55c46c3100413f034d6744e8b63884708a0f3550273` |

A è stata mantenuta per la sicurezza nelle gare, dopo aver escluso varianti
più aggressive che funzionavano da sole ma si ritiravano in griglia. Nella
raccolta iniziale A la memoria laterale del docente era avanzata una sola volta
per etichetta; il problema è stato corretto nell'helper di preparazione e nella
base B. A rimane l'asset congelato selezionato per guida nominale, senza
certificarla esperta di sorpassi. Il file storico `rejected-base-first.json`
contiene questa candidata A: il nome riflette la precedente valutazione sul
traffico, non la selezione finale per guida nominale. Provenienza, pesi e hash
rendono la base ripetibile come punto di partenza; non si dichiara che rieseguire
l'helper oggi ricrei bit per bit A.

Prove della base A: **15/15** casi solo, recupero e variazione fisica; sei gare
con 2/5 vetture tutte concluse. Nelle tre gare a cinque si contano rispettivamente
4/1/1 contatti e 0/0/1 limiti pista: completamento non significa gara senza incidenti.
[Qualifica](evidence/v09-direct-implementation-2026-10-20/product-qualification-final.json).

B supera i casi di sviluppo solo/sorpasso/curva/difesa. La rosa mista A/A/A/B/
Maestro conclude due prime gare, 10/10 arrivi e zero uscite, con 1/4 contatti.
Altre cinque gare, Tattico in ciascuna posizione della griglia: **25/25 arrivi**,
limiti complessivi per gara 0/0/2/0/0. Non sono gare tutte pulite.
[Griglia](evidence/v09-direct-implementation-2026-10-20/tactical-grid-slots.json).
La qualifica nel menu resta personale e va effettuata prima della Gara.

## 3. Ricetta diretta e incentivi

`direct-driving-2`, separata dal precedente `race-residual-4`.
Progresso valido e costo del tempo rendono vantaggioso completare prima il giro;
contatti, tagli, uscite, sottosterzo dannoso e stallo mantengono costi distinti.
Non si premiano il pedale premuto, velocità fuori pista o giri invalidi.
Shaping potenziale al confine delle decisioni, sconto coerente, terminali e
troncamenti distinti. Prior coerente del valore anche per i backend off-policy.

PPO campiona la propria rete; nessuna dimostrazione spacciata per azione della
policy corrente nel rollout. [PPO, Schulman et al.](https://arxiv.org/abs/1707.06347).
Per SAC/TD3: prime 512 decisioni dedicate ai critic; LR critic 10⁻⁴ e attore
10⁻⁵; regolarizzazione iniziale verso la **rete** di partenza, decrescente a
zero dopo 4.096 transizioni. Non è un filtro dei comandi e non rimane per sempre.
La regolarizzazione ricorda il principio di
[TD3+BC](https://arxiv.org/abs/2106.06860), ma questa implementazione online non
è l'algoritmo offline originale né un'implementazione di RLPD.

Esplorazione in unità degli attuatori: sigma iniziale 0,015 sterzo / 0,10 pedale;
target TD3 0,015, clip 0,03. Le vecchie scale corsia/passo non vengono riusate.
Un candidato off-policy non valido, o tre verifiche senza guadagno, riparte dal
proprio campione: esperienze, critic, RNG e contatori restano, l'ottimizzatore
dell'attore viene ricreato. In guida non interviene il Maestro.

Ogni quarto nuovo episodio varia massa/inerzia, potenza/forza motrice e grip
entro intervalli limitati; hash della configurazione ricalcolato. Tattico passa
al traffico dopo 8.192 decisioni; include anche griglie a cinque con policy rivali
congelate. Sorpassi confermati con permanenza e spazio, difesa osservata dalla
traiettoria reale. Candidato, campione verificato e qualifica ufficiale distinti.

## 4. Apprendimento misurato

Cinque semi **31–35**, banca finale solo 820001–820005 separata da raccolta e
promozione. Stessa A e **49.152 passi fisici** per PPO/SAC/TD3; B e **98.304** per
Tattico, che ha compiti diversi. Non confrontare il tempo a parete dei processi
concorrenti o attribuire a Tattico lo stesso budget degli altri.

| Metodo | Base: mediana | Campione: mediana | Riduzione | Semi migliorati |
| --- | ---: | ---: | ---: | ---: |
| PPO | 28,267 s | 27,917 s | 1,24% | 5/5 |
| SAC | 28,267 s | 24,000 s | 15,09% | 3/5 |
| TD3 | 28,267 s | 27,000 s | 4,48% | 5/5 |
| TD3 Tattico | 28,200 s | 28,200 s | 0% | 0/5 |

Ogni gruppo ha **25/25** prove finali valide, zero contatti e limiti pista.
Sono tempi di esercizi finiti da fermo, non PB ufficiali lanciati. Il vantaggio
della nuova base sul Maestro ordinario è dovuto alla preparazione e al passo
del docente: **non** è il guadagno RL della tabella. Nel seme 31 le V max finali
sono circa 49,82/58,01/53,56/49,12 km/h; non esiste l'obbligo di pieno gas in ogni
rettilineo e non si dichiara ancora il limite prestazionale fisico raggiunto.
[Riepilogo](evidence/v09-direct-implementation-2026-10-20/final-summary.json).

Tattico su banca traffico separata, nove casi per ciascuno dei cinque campioni:
**45/45 → 45/45**, 30 sorpassi confermati in entrambe le condizioni, zero contatti,
limiti o violazioni. Conserva l'abilità insegnata, **non dimostra un ulteriore
vantaggio tattico appreso** in questo budget. La prima versione con A era
15/45 → 15/45, senza sorpassi: esclusa come base di Tattico.
[Traffico finale](evidence/v09-direct-implementation-2026-10-20/traffic-final.json).
Le banche hanno casualità locale ma la stessa geometria: cinque semi non sono
cinque circuiti o cinque tipi di aderenza.

Quattro repliche complete del seme 31 sul codice finale riproducono esattamente
attore, campione, risultati e contatori.
[Ricevuta sorgenti](evidence/v09-direct-implementation-2026-10-20/final-source-reproduction.json).

## 5. UX, test e scheda

Plancia e tema conservati. Guida mostra gas/freno/sterzo effettivi; Rete mostra
esplorazione in gradi, preparazione critic e verifiche. Dossier/impostazioni
spiegano rete preparata, autorità, sensori, frequenze, LR e obiettivo. La rete
non viene descritta come un controllore di corsia. I comandi 2/8 cambiano
Circuito/Segui/Telemetria/Sensori, 4/6 Guida/Premi/Rete, 5 Pausa e salvataggio.
Il campione nella preview è distinto dalle esperienze di raccolta.

45 test PC passati: piena autorità, nessuna chiamata al docente in guida,
causalità degli ingressi, base/provenienza/reset, gradienti, shaping, preparazione
critic, annullamento dell'ancora e ripresa esatta di tutti i backend. Tre oggetti
Qt non raccoglibili segnalati al teardown, senza fallimenti. Il primo walkthrough
ha trovato un parametro `opponents` posizionale non accettato dal trainer:
corretto, coperto da test e ripetuto attraverso il worker reale.

Sul pacchetto finale A/B: **16 test ARM passati**, Base/Functional/Apple
EGLFS 960×640 passati senza avvisi QML, quattro learner con update/salvataggio,
camere e pannelli reali, cinque vetture sempre visibili. Apple comprende una
Qualifica di Crono dalla GUI e una Gara completa: **5/5 arrivi, tre giri**.
Le altre due gare sono prove brevi di integrazione. I precedenti risultati con
A comune sono conservati separatamente e non sostituiscono questo ciclo.
[Report nativi](evidence/v09-direct-implementation-2026-10-20/board/apple/report.json).
In Gara Apple, 3.327 intervalli `frameSwapped`: p95 **49,2 ms**, massimo
**80,1 ms**; Base/Functional nelle prove brevi p95 48,8/49,6 ms. Questi dati
non certificano una cadenza fissa di 30 fps né FPS ottici del pannello.
[Riepilogo consegna](evidence/v09-direct-implementation-2026-10-20/delivery-summary.json).
Una ripetizione ridondante della vecchia stage è stata fermata durante i test
numerici dopo aver rilevato l'ordine errato fra upload e preparazione; il
supervisore ha ripristinato la Dashboard. Il nuovo ciclo verifica esplicitamente
il manifest finale A/B di 632 file prima delle prove.

## 6. Consegna e limiti

Installazione con backup esterno e scambio dell'intero archivio del Gioco:
cinque identità nuove, zero progressi personali/replay/sessioni/record/qualifiche;
quattro reti iniziali A/B più il Maestro. Nessun vecchio certificato o peso
residuale reinterpretato. Preferenze e Apple Calm 1.6.3 conservati e verificati. Manifest **632/632 hash**,
servizio attivo, NRestarts=0, GUI pronta con heartbeat del PID corrente. Solo
riavvio del servizio, boot ID conservato. Nessun allenamento implicito.
[Ricevuta](evidence/v09-direct-implementation-2026-10-20/board/final-receipt.json).
Archivio precedente completo con hash conformi e runtime rc.24 disponibili per
rollback; il nuovo archivio contiene cinque sole policy iniziali, zero storia,
qualifiche, record e progressi personali. Prima della Gara serve una nuova
Qualifica del modello sul circuito/configurazione scelti.

D0 e il percorso funzionale D1–D6 sono implementati. La qualifica scientifica
estesa rimane distinta: preparazioni indipendenti della base, fondi/piste/auto
molto differenti, duelli prolungati, incremento tattico rispetto alla base B,
robustezza SAC su più semi e miglioramenti consistenti oltre il 5%. Non sono
promessi progressi a ogni giro. Nessuna certificazione di 30/60 FPS ottici o
nuovo impiego NPU da questi controlli. Il seguito della ricerca si concentra
su questi limiti misurati, mantenendo il nuovo controllo neurale diretto.
