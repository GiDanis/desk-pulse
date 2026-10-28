# v0.9.0-rc.16 · Evo progressivo

14 ottobre 2026 · Implementazione dello [studio sul blocco di Evo](game-evo-learning-stall-analysis.md). Evidenze in [v09-evo-progressive-2026-10-14](evidence/v09-evo-progressive-2026-10-14/).

## Modifiche

1. **Difficoltà stabile e progressiva:** Partenza 1/3/8/20 m, rettilineo 40 m, arco lento 20/50 m, ingresso 60 m, curva 140 m a 28,8 e 39,6 km/h iniziali, un giro pulito; poi Passo e il percorso Accademia già esistente. Velocità iniziale e distanza sono fisse nel livello. Scarto laterale e angolo iniziali dipendono dal seed, con gli stessi valori per tutti i candidati.
2. **Generazione = intera suite:** due scenari principali per ciascuna delle 32 reti; dopo Partenza si aggiunge il ripasso da fermo di 20 m. Se esistono contesti acquisiti su altre piste si aggiunge un loro scenario, con la relativa fisica. Nessun aggiornamento della popolazione prima di aver confrontato tutti i casi. Ripasso e ritorno al compito non azzerano la stagnazione.
3. **Selezione esplicita:** prima successi complessivi, poi abilità conservata, successi principali e infine reward medio. Il punteggio comprende progresso valido, completamento, uscite, ritiro, stallo e costo del tempo. Non è il numero grezzo di generazioni né la pressione del gas. Il migliore corrente viene rivalutato; il vecchio record non reintroduce una rete non vincente nel confronto attuale. Archivi separati per livello/fase.
4. **Mutazioni proporzionate alla rete:** sigma nominale 0,15 divisa per √68 e √16 nelle due matrici; maschera 25%, esplorazione più ampia in pochi discendenti e un immigrato. Due figli esplorano simmetricamente il bias pedale ±0,25. All'avvio realmente casuale, uscita sterzo dimezzata. Nessun comando corretto dal riferimento durante l'apprendimento.
5. **Verifiche:** quattro scenari principali con seed separati dalla selezione, più due partenze e l'eventuale contesto precedente. Tutti i casi vengono eseguiti, anche dopo i primi errori. Servono due verifiche consecutive superate, alla prima e poi ogni quarta generazione del livello. La banca d'esame è stabile e viene riutilizzata: non è un test statistico mai consultato. Le prove finali degli esperimenti usano un'ulteriore banca separata.
6. **Penalità:** per Evo, RewardSpec `balanced-driving-2`, curriculum `evo-progressive-1`, stallo 3 anziché 0,5. Il resto del bilanciamento della rc.15 è conservato. Il miglioramento non è attribuibile alla sola penalità: curriculum, selezione e mutazioni sono cambiati insieme.
7. **UX e storico:** footer compatto con generazione dell'esercizio, scenario e nome del compito, senza ridurre la pista. Dossier con fase, generazioni del percorso, passi del protocollo e successi/stalli/incidenti per esercizio. Pedali e aderenza sono riferiti alla nuova epoca; contatori storici distinti. Risultati con nome del livello e confronti separati anche per velocità iniziale.
8. **Ripartenze distinte:** locale (può riusare la base), intero pilota (pesi casuali, base/contesti/qualifiche cancellati, identità/storico conservati), soli esercizi Evo (pesi, RNG, base, risultati e tempi conservati; nuova epoca da Partenza). Conferma/cancellazione nella UI e nessun avvio automatico. Artefatto precedente immutabile e provenienza registrata.

## Migrazione e scelta della memoria

Il nuovo protocollo viene applicato **al prossimo Start di Evo**, a un confine dichiarato di episodio. Conserva popolazione, pesi, RNG, identità, tempi, storico, base personale e risultati precedenti. Annulla fitness non confrontabili e prove in corso; ricomincia da Partenza 1 m con nuovi contatori. NEAT, PPO, PPO Smooth e Clone restano sul bilanciamento rc.15.

**Non cancellare i piloti originali.** Lo screening non dimostra un vantaggio del reset: le copie attuali raggiungono gli esercizi intermedi come quelle casuali, e le prove estese mostrano apprendimento utile conservando i pesi. Non sono stati installati i modelli addestrati nelle prove private.

## Prove di apprendimento

Script [probe_training.py](evidence/v09-evo-progressive-2026-10-14/probe_training.py), origine checkpoint rc.15 `7586f50569b33731739dbddc117c7f7554d52c28a4bdc4dbefb992d086456bed`. Copie in memoria; nessun accesso in scrittura al gioco originale.

- **Screening:** attuale / base personale / casuale, seed 1/11/21, 250.000 transizioni di allenamento per caso. Ordine controbilanciato, stesso preset 32×68→16→2 e stessi seed/scenari per condizione. Le inizializzazioni sono intenzionalmente diverse; dopo l'inizializzazione il flusso delle mutazioni è accoppiato. Quasi tutti raggiungono il primo arco lento; nessuna delle tre condizioni domina tutti gli esercizi. I tempi PC sotto tre processi concorrenti non misurano le prestazioni della board.
- **Estensione preliminare:** copie attuali, stessi tre seed, 1.500.000 transizioni ciascuno. Livelli raggiunti 9/8/10, generazioni 45/61/60. Nella banca finale separata: tutti 4/4 su Partenza, rettilineo, arco breve e ingresso curva; curva completa 2/4, 0/4, 4/4; giro intero 0/4, 0/4, 4/4. Questo è un miglioramento rispetto al blocco precedente, senza garantire convergenza di ogni seed.
- **Estensione a cinque seed:** 1/11/21/31/41, 3.000.000 transizioni per caso; [sintesi completa](evidence/v09-evo-progressive-2026-10-14/qualification-summary.json). Non è un confronto a cinque seed delle tre inizializzazioni.

| Seed | Livello finale (0–10; 11 = esercizi superati) | Generazioni nuove | Ingresso 60 m /4 | Curva 140 m /4 | Giro intero /4 | Passi verifica di livello |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 11 | 57 | 4 | 2 | 4 | 59.976 |
| 11 | 8 | 85 | 4 | 1 | 0 | 56.875 |
| 21 | 11 | 72 | 2 | 2 | 4 | 49.492 |
| 31 | 11 | 67 | 4 | 4 | 4 | 62.657 |
| 41 | 9 | 81 | 4 | 4 | 4 | 56.688 |

Partenza e rettilineo finali 4/4 per ciascun seed. **Quattro reti su cinque completano tutti i quattro giri finali**; tre hanno anche superato l'intera progressione prima del budget. Il seed 41 sa fare il giro ma non ha ancora superato stabilmente la curva veloce nelle verifiche previste. Gli altri due controlli non si possono sostituire a vicenda.

**Limite emerso:** avere imparato il giro non conserva automaticamente tutti gli esercizi con partenze in movimento. Il seed 21 torna a 2/4 nell'ingresso breve; il seed 41 perde due archi lenti. Il ripasso Partenza funziona, mentre servono futuri studi di ripasso cumulativo degli archi a velocità diverse, conservando banche e costi confrontabili. Non allentare pulizia o promozioni per far risultare riuscite queste prove. Nessuna qualifica di Gara attribuita da questi dati.

Costo PC (cinque processi concorrenti): 385,6–490,8 s complessivi per caso; tempo dei valutatori 38,1–87,0 s dopo aver sottratto il contatore storico ereditato di 1.899,769 s. Le due grandezze hanno perimetri diversi, come precisato sotto.

I budget dichiarati contano le transizioni della popolazione, escludendo le valutazioni. Nell'estensione finale vengono riportati i passi delle sole verifiche di livello e il tempo dei valutatori, escluso il consolidamento Review. Il tempo complessivo include anche i Review; il loro costo non è isolato in un contatore separato. Il dato grezzo cumulativo ereditato e la sottrazione sono conservati nei JSON. Nelle prime due campagne sono disponibili numero/risultati delle verifiche e tempo complessivo, ma manca un contatore totale separato delle loro transizioni. L'aggiunta successiva di contatori e metadati non modifica fisica, azioni, selezione o RNG.

## Verifica tecnica

- 75 regressioni PC di bilanciamento, Accademia, modalità, memoria, record, circuiti reali, ottimizzazione e pacing; altri 11 controlli piste.
- Dieci nuovi gate: migrazione, banca stabile ma pose realmente distinte fra selezione/esame, promozione, retention/stagnazione, elite corrente e RNG riproducibile, mutazione normalizzata, ripresa a metà suite/fisica, valutazioni complete/resumibili, geometria del ripasso, riferimento fisico sui 44 casi pista/livello e reset senza reimportare memoria cancellata.
- UI PC Apple 960×640, testo 1,1: 32 tentativi reali, nuova epoca, annullamento e conferma della ripartenza; impostazioni e dossier preesistenti senza warning. Le screenshot mantengono l'identità Apple Calm.
- **Scheda:** dieci gate ARM superati; Base, Functional e Apple Calm EGLFS 960×640/testo 1,1 con 32 tentativi, epoca e ripartenza con pesi/RNG conservati. Altri walkthrough Apple impostazioni/dossier; tre modalità di apprendimento su checkpoint NEAT maturo e Qualifica→Gara con due riferimenti realmente qualificati. Zero warning QML. Nel campione NEAT di 20 s: Pilota 1,00005×, clock 30,00 Hz, frame p95 40,22 ms/p99 52,21 ms/massimo 78,00 ms; misura software, non FPS ottici.

Il motore CPU float64 raggruppato e i sensori nativi della rc.15 sono conservati. GPU per Qt Quick; nessun nuovo calcolo GPU/NPU selezionato. Due/quattro scenari costano più lavoro di una sola prova: la generazione può durare di più. Fisica 60 Hz e presentazione 30 Hz restano separate dalla velocità aggregata di apprendimento; non si promettono 32 tentativi tutti a 1× né 60 FPS ottici.

## Limiti aperti

Generalizzazione quantitativa su quattro circuiti e più aderenze, sorpasso/gara con questi pesi, convergenza di tutti i seed, confronto esteso delle tre inizializzazioni e degli altri paradigmi, ottica/input e uso prolungato. Il riferimento geometrico dimostra risolvibilità fisica degli esercizi; non sostituisce la misura della rete. La Qualifica su una pista resta richiesta prima della Gara e non viene concessa da questi test di allenamento.

## Installazione conclusa

[Ricevuta](evidence/v09-evo-progressive-2026-10-14/final-receipt.json) · [manifest](evidence/v09-evo-progressive-2026-10-14/release-manifest.json). **0.9.0-rc.16 installata**, 598 hash conformi al sorgente finale (libreria compilata ARM64 sulla scheda). Sei piloti, tutte le tabelle e 2.030 artefatti conservati; sola chiusura della sessione già sospesa come interrotta, senza perdita del checkpoint. Nessun modello sperimentale installato e nessun reset dei pesi. Preferenze/tema Base e boot OS identici; servizio attivo, NRestarts=0, GUI pronta.

Backup `/var/backups/smartpc-before-evo-progressive-20261014-201801`; rollback runtime `/opt/smartpc/dashboard-rc15-before-evo-progressive`. **Premere Start per applicare il percorso progressivo a Evo**: i nuovi contatori partono da zero, i passi e la memoria storici rimangono. Il numero di generazione del footer si riferisce all’esercizio; il dossier mostra anche quelle dell’intero nuovo percorso.

**Finitura finale del riepilogo:** dopo la ripartenza con pesi conservati, il compito salvato indica subito 1 m/12 s, anche prima di Start. Correzione di `game_store.py` e assert aggiunti al test di ripartenza; controllo mirato PC/ARM superato. Nessuna modifica a fisica, apprendimento o QML rispetto ai walkthrough precedenti. Manifest iniziale e finale distinti conservati; ricevuta finale con hash manifest e ulteriore rollback runtime, dati originali nuovamente identici.
