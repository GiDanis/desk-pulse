# Gioco rc.24 — incentivi e apprendimento dei quattro piloti

**20 ottobre 2026 · rc.24 installata; confronti, migrazione e verifiche native completati nel perimetro dichiarato.**

Attuazione della parte dedicata all'apprendimento dello
[studio Crono](game-crono-exploration-pace-study.md). Rosa invariata: Crono/PPO,
Memoria/SAC, Linea/TD3 e Tattico/TD3. Maestro resta un riferimento fisso.
[Evidenze e script](evidence/v09-learning-incentives-2026-10-20/).

## 1. Nuova ricetta

`race-residual-4` / `residual-racing-3`, versionate separatamente dal candidato
`race-residual-3` respinto nella rc.22. Non vengono riattivati i premi comuni,
il cutoff modificato o la curva 240 m di quell'esperimento.

- **Critic asimmetrico per tutti i metodi:** 94 ingressi, comprendenti compito
  finito/continuo, distanza residua normalizzata, budget residuo quando finito
  e fase. La policy mantiene i propri 90 ingressi locali. L'alias riprodotto
  sull'ovale è risolto per il valore futuro senza dare un ID arbitrario di pista
  all'attore.
- **Incentivo intermedio al confine delle decisioni:** potenziale congelato
  `Phi = -0,25 * distanza_residua_normalizzata + 0,05 * velocita_in_avanti_normalizzata`,
  con velocità normalizzata limitata a [0,2]. Il segnale è
  `gamma * Phi(next) - Phi(current)`, con potenziale zero ai veri terminali e
  conservato ai troncamenti. È contabilizzato in `shaping`, anche nel ritorno
  dell'episodio. I passaggi fisici non vengono moltiplicati in esperienze.
- Progresso valido e termine tempo restano la base del premio. Contatti,
  sottosterzo pericoloso, tagli, uscite e stallo conservano le protezioni.
  Non si premia direttamente il pedale premuto o l'oscillazione della corsia.
- **Esplorazione:** sigma laterale iniziale 0,04 per PPO e 0,08 per SAC/TD3,
  corrispondenti vicino al neutro a circa 17/34 cm di bersaglio, prima della
  risposta fisica; prima era circa 4 cm. Sigma passo 0,15 per PPO e 0,08 per
  SAC/TD3. Limiti inferiori/superiori espliciti, con checkpoint e RNG persistenti.
- **PPO specifico:** GAE conserva la scala 1,6 s; entropia 0,0001. Il critic usa
  un prior coerente col potenziale, `V = V_rete - Phi`, anche in campionamento,
  bootstrap, loss e diagnostica. La corrispondente cancellazione nel residuo di
  Bellman è verificata. Non si è trasferita a PPO la prima taratura comune.
- **SAC/TD3:** replay a 192 valori per transizione con contesti corrente e
  successivo; Q con 96 ingressi stato/azione. L'attore continua a vedere 90
  ingressi. Gradiente SAC e ritardo/target TD3 mantengono le rispettive regole.

Fisica 60 Hz, decisioni 10 Hz, controller e intervallo di autorità invariati.
Il profilo velocità fisico più ampio e gli ambienti multipli dello studio
restano fasi successive: questa consegna misura il contributo dell'apprendimento
sotto lo stesso controllore. Non attribuisce guadagni a un aumento del limite
di velocità o a un nuovo Maestro.

## 2. Confronto a budget fisico uguale

Cinque semi di apprendimento **31–35**, **49.152 passi fisici raccolti** per
metodo/revisione, circa 8.200 decisioni; piccole differenze nel numero di
decisioni derivano dalle transizioni terminali parziali. Aggiornamenti e
verifiche contati separatamente. Campagne PC concorrenti: tempi a parete non
usati per dichiarare un'accelerazione dell'hardware.

La prima candidata comune, su 40 run completi vecchia/nuova, migliora tre
metodi ma peggiora PPO (mediana di selezione circa 36,58 contro 35,90 s).
**Quella taratura PPO è respinta.** Otto piccoli confronti di sviluppo e quattro
varianti a esplorazione ampia non giustificano la scelta di un default. Dopo
l'introduzione del prior del critic, PPO viene confrontato nuovamente su tutti
e cinque i semi allo stesso budget completo.

La banca finale è stata congelata prima di esaminarne i risultati, distinta
dalle verifiche usate per le promozioni durante il training: cinque casi solo
per policy; per Tattico altri dodici casi di sorpasso, curva e difesa.
[Banca](evidence/v09-learning-incentives-2026-10-20/final-bank.json) ·
[riepilogo finale](evidence/v09-learning-incentives-2026-10-20/final-summary.json).

| Pilota | Mediana precedente | Mediana nuova | Riduzione | Semi con tempo migliore |
| --- | ---: | ---: | ---: | ---: |
| Crono / PPO | 35,900 s | 35,183 s | 2,00% | 5/5 |
| Memoria / SAC | 31,883 s | 30,117 s | 5,54% | 4/5 |
| Linea / TD3 | 31,483 s | 29,783 s | 5,40% | 3/5 |
| Tattico / TD3 | 36,867 s | 29,783 s | 19,21% | 4/5 |

Tutti i gruppi solo: **25/25** prove valide, nessun contatto, limite pista o
violazione. Tattico nel traffico: **56/60 → 57/60**, senza contatti/uscite/
violazioni in entrambe le condizioni. La differenza di una prova non dimostra
una superiorità tattica generale. La mediana precedente di Tattico comprende
semi che avevano conservato la base, non cinque campioni già veloci.

I tempi sono quelli delle prove finite con partenza da fermo, non nuovi PB
ufficiali di giri lanciati. I modelli dello studio non vengono importati nei
piloti dell'utente. La soglia desiderata del 5% in almeno 4/5 semi rimane
**aperta per PPO e Linea**: il beneficio aggregato è misurato, non uniforme e
non una promessa di miglioramento a ogni giro.

## 3. Attribuzione al codice finale

Le campagne usano sorgenti congelate: candidata comune per SAC/TD3/Tattico e
variante prior per PPO. Una replica sul pacchetto finale, seme 31 e budget
completo per ognuno dei quattro metodi, produce **gli stessi attori, campioni,
ricette e statistiche**, verificati con uguaglianza esatta.
[Ricevuta](evidence/v09-learning-incentives-2026-10-20/final-source-reproduction.json).

46 test PC passati, inclusi gradienti asimmetrici contro differenze finite,
telescopicità del potenziale, prior PPO, separazione degli ingressi,
contabilità dei premi, migrazione di ogni backend, ripresa esatta e protezione
di qualifiche/record. Tre oggetti Qt non raccoglibili segnalati al teardown
dell'interprete; nessun fallimento di test. Il controllo iniziale con
un'aspettativa ancora riferita alla vecchia versione è conservato come tale,
poi aggiornato alla nuova ricetta dichiarata.

## 4. Migrazione al prossimo Start

L'installazione non apre un nuovo allenamento. Al successivo Start:

1. Conserva attore, ottimizzatore dell'attore, RNG, contatori cumulativi e
   campione verificato, con prove precedenti e origine.
2. Archivia riferimento al checkpoint originale, vecchia ricetta, statistiche
   e verifiche. Gli artefatti originali restano raggiungibili anche dal pruning.
3. Ricrea critic, relativi ottimizzatori e dati di apprendimento: replay/rollout
   vecchi non possiedono il nuovo contesto e non vengono reinterpretati.
4. Avvia un nuovo episodio di raccolta; nessuna transizione o verifica lasciata
   a metà viene riutilizzata con il nuovo premio.
5. Mantiene la vecchia policy per Qualifica/Gara finché una nuova candidata non
   supera le verifiche complete. Non importa un modello della campagna al posto
   del pilota già allenato.

La nuova esplorazione è una modifica esplicita della distribuzione di raccolta;
la policy deterministica iniziale conserva i pesi e gli stessi controlli.
I risultati scientifici su piloti nuovi non garantiscono il medesimo guadagno
sui checkpoint maturi: questi sono verificati per correttezza di migrazione,
continuità dei contatori e funzionamento sul display.

## 5. Viste e comandi

- Panoramica iniziale **Circuito**; **Segui** ora funziona anche sull'ovale.
  Duello viene proposto quando ci sono più auto.
- **2/8** scorre Circuito / Segui / Duello quando disponibile / Telemetria /
  Sensori. La telemetria aggiuntiva è disponibile nell'allenamento sull'ovale.
- In Telemetria, **4/6** scorre **Guida / Premi / Rete**. Guida mostra dati e
  comandi del pilota in allenamento; Premi le somme dell'episodio raccolto;
  Rete aggiornamenti, decisioni ed esplorazione espressa in centimetri.
- Provenienza esplicita: la prova visibile deterministica e l'episodio raccolto
  sono distinti. Il numero di aggiornamenti non viene chiamato generazione.
- Pannello nell'isola dell'ovale con verifica dello spazio e delle vetture;
  pista/auto mantengono scala e proporzioni. In Gara tutte le auto restano
  visibili. **5** conserva Pausa/Salvato.

Walkthrough PC completo: quattro learner, nuove camere/pannelli, salvataggio e
gara con cinque auto, senza warning QML. Nessun nuovo dato architetturale
invasivo nei flussi normali dell'utente.

## 6. Incidente SQLite preesistente rilevato durante la consegna

Prima delle prove native, la lettura query-only degli originali fallisce:
`game.sqlite-journal` presente dall'ultima chiusura del worker delle 17:09.
Il servizio rc.23 è attivo, senza worker di training. Il journal non viene
rimosso manualmente né ignorato con `immutable`.

Servizio fermato nella finestra autorizzata; copia completa di database,
journal, artefatti e configurazione con hash. Il normale recupero SQLite viene
provato su una seconda copia e verificato con `integrity_check`; poi eseguito
sull'originale come utente smartpc. Tutte le righe coincidono con la copia
recuperata, tutti gli artefatti sono conservati e le query read-only tornano
a funzionare. Crono recuperato contiene **468.832 passi**.

È il rollback automatico di una transazione non completata, previsto da
[SQLite](https://www.sqlite.org/atomiccommit.html), non un reset dei piloti.
Il backup grezzo permette ulteriori verifiche. Nel journal del servizio sono
presenti errori di cleanup dei semafori Python; la causa dell'interruzione
precedente non viene attribuita senza una riproduzione. Questo recupero non è
una dimostrazione di aver risolto ogni possibile problema di arresto del worker.

## 7. Qualifica nativa e installazione

Otto test ARM passati su contesto, gradienti, migrazione, replay, RNG e ripresa.
Prove EGLFS 960×640 completate nei temi **Base, Functional e Apple Calm** con
copie dei quattro checkpoint reali: Start/update, contatori cumulativi,
Circuito/Segui/Telemetria/Sensori, pannelli Guida/Premi/Rete, Pausa/Salvato e
gara con cinque auto visibili. Nessun warning QML nei tre walkthrough.

La prima fixture delle qualifiche numeriche usava una matrice a cinque righe
come cinque prove indipendenti: il controllo dei veicoli vicini vedeva falsi
rivali. Corretta la sola fixture in cinque mondi separati, quindi ripetuti tutti
e tre i walkthrough nativi. Le campagne scientifiche usavano già mondi separati
e non erano coinvolte. Le qualifiche fisiche isolate dei checkpoint reali,
uguali nei tre temi, risultano: Maestro 35,701 s, Crono 32,041 s, Memoria
29,034 s, Linea e Tattico 35,701 s. Sono preparazione numerica della griglia
privata, non nuove qualifiche ufficiali GUI nei dati originali.
[Correzione](evidence/v09-learning-incentives-2026-10-20/board/fixture-correction.json).

**Installazione completata:** rc.24, manifest **626 file**, nessuna discordanza;
servizio attivo con **NRestarts=0**, heartbeat GUI pronto e fresco del PID
**40873**, coincidente con il processo corrente. Apple Calm **1.6.3** attivo
come prima, hash di tutte le preferenze conservati, cinque piloti e **72/72
artefatti** originali intatti. Tabelle originali conservate, salvo l'eventuale
chiusura della sessione in pausa al riavvio; nessun training originale lanciato
per il collaudo. La migrazione della ricetta avverrà al prossimo Start.

Backup completo dei dati e delle preferenze:
`/var/lib/smartpc-dashboard/game-backups/before-incentives-20261020-175023`
e cartella omonima con suffisso `-config`.
Rollback runtime: `/opt/smartpc/dashboard-rc23-before-incentives`.
Solo riavvio del servizio, **nessun reboot OS**.
[Ricevuta finale](evidence/v09-learning-incentives-2026-10-20/board/final-receipt.json) ·
[verifiche dei sorgenti](evidence/v09-learning-incentives-2026-10-20/board/source-checks.json).

Qualifica di apprendimento maturo prolungato, altri circuiti/fondi, target 5%
per tutti, profilo velocità più ampio, 1/2/4 ambienti e FPS ottici restano aperti.
