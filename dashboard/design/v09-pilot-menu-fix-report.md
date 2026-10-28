# Gioco rc.28 — tutti i piloti dal menu

**21 ottobre 2026 · Europe/Rome.** Attuazione della [diagnosi del blocco dei profili](game-pilots-completion-study.md), con correzione P0 e verifica della continuità dei quattro learner. [Evidenze](evidence/v09-pilot-menu-fix-2026-10-21/README.md).

**0.9.0-rc.28 installata e verificata sulla board**, 642 hash conformi. Nessuna rete dei benchmark importata in produzione.

## 1. Correzione

La rc.27 produceva profili con i nuovi campi della ricetta, ma il menu li confrontava con il vecchio elenco chiuso. Scegliendo Memoria, Linea o Tattico, oppure cambiando modalità a Crono, la conferma falliva con «Profilo incompleto o sconosciuto». Crono già selezionato e una bozza invariata saltavano quel controllo.

`game_racing_presets` ora contiene il registro condiviso delle chiavi della ricetta, dei valori e dei tipi supportati, insieme ai default di produzione. `validate_profile` distingue i parametri mancanti da quelli sconosciuti e accetta i metadati riconosciuti. Rimangono i controlli su tipo, intervallo e compatibilità: per esempio un booleano non è una frequenza intera, una versione futura non è ammessa e le opzioni GAE/multi-step devono appartenere al metodo appropriato.

La validazione conserva tutti i campi ricevuti e non aggiunge default ai profili storici. `profile`, `policy_profile`, policy qualificate e checkpoint restano distinti. Scegliere un altro pilota non cambia metodo, seme o memoria, né apre un nuovo percorso. I parametri dei piloti restano fissi e consultabili.

Il [delta rispetto alla rc.27](evidence/v09-pilot-menu-fix-2026-10-21/source-delta.json) riguarda solo **validatore, registro delle ricette e versione**, con due nuovi diagnostici. Algoritmi, reward, curriculum, inferenza, fisica, pesi iniziali, QML e tema sono invariati.

## 2. Verifica attraverso il percorso usato dall'utente

Il nuovo diagnostico carica Main e Worker reali in un archivio privato. Apre il menu, seleziona il pilota, cambia modalità con i comandi del controller del tastierino e preme l'azione Start. Per questo controllo non usa `selectDriver()` come scorciatoia per scegliere il pilota.

| Prova | Risultato PC |
| --- | --- |
| Contratto e regressione del menu | 4 test, inclusi 20 casi pilota/modalità, campi errati, profili storici, annullamento e ruolo di Maestro. |
| Compatibilità modalità/ricette/profili | 23 test passati. |
| Impara, Infinito, Sorpasso | **12/12 combinazioni** con avanzamento, nuovi aggiornamenti e salvataggio durevole. |
| Pesi neurali | Gli attori cambiano realmente in tutte le 12 sessioni; hash e norma della differenza, senza pubblicare pesi personali. |
| Nuova apertura dell'app privata | **4/4 learner** scelti dal menu, ripresi e salvati con passi e aggiornamenti crescenti. |
| Qualifica e Gara | Quattro avvii di Qualifica dal menu, cinque policy cronometrate individualmente e cinque auto schierate tramite il menu. |

Il controllo dei pesi è nei [risultati degli artefatti](evidence/v09-pilot-menu-fix-2026-10-21/pc-learning-proof.json). Dimostra un aggiornamento dell'attore, non un miglioramento del tempo sul giro. I contatori degli algoritmi hanno significati diversi e non sono una classifica della velocità di apprendimento.

Per la ripresa l'app del primo passaggio viene chiusa; una seconda esecuzione apre la copia salvata, quindi ripete menu → Start → Pausa → salvataggio per tutti. Le copie derivano dai quattro checkpoint effettivamente presenti sulla board al momento della pausa; i modelli personali rimangono nei percorsi privati.

### Qualifica e gara

Il diagnostico avvia dalla GUI una Qualifica per ogni learner e verifica che compaia una sola vettura. Il cronometraggio completo delle cinque policy usate in gara viene poi misurato in mondi indipendenti, salvando tempi e certificati della policy esatta. Queste qualifiche complete sono prove fisiche senza rendering; i brevi avvii dalla GUI non vengono presentati come cinque sessioni complete.

La griglia viene composta dal menu, scegliendo **più lento davanti** e tre giri. Il controllo mantiene l'identità di tutte e cinque le vetture visibili durante la corsa. La gara completa sul pannello ha una verifica separata; completamento e contatti non vengono confusi.

## 3. Board e installazione

Un primo walkthrough Apple completa i dodici allenamenti e la gara, poi il diagnostico chiede erroneamente Pausa dopo l'esito `finished`. La produzione viene ripristinata e gli originali restano integri. Corretto il solo diagnostico, Apple e la riapertura vengono ripetuti; Base/Functional e i test ARM precedono questo delta, che riguarda esclusivamente la chiusura di una gara già conclusa. I sorgenti di produzione sono identici fra i due passaggi.

La prima ripresa Tattico incontra poi una verifica lunga a 168 passi dall'avvio: il test attendeva 1.200 nuovi passi entro 180 s mentre la raccolta era sospesa per valutare. Il controllo della breve ripresa off-policy richiede ora 120 nuovi passi, aggiornamenti realmente crescenti e salvataggio; PPO conserva 1.200 passi. La cadenza delle verifiche e i learner non cambiano. La sola riapertura viene ripetuta sui quattro piloti.

**15 test ARM passati.** Base, Functional e Apple Calm verificati su EGLFS 960×640/textScale 1,1, senza warning QML. Anche su ARM i pesi degli attori cambiano nelle dodici sessioni, con artefatti personali privati. I tre walkthrough eseguono rispettivamente quattro, quattro e dodici sessioni attraverso il menu. Una seconda apertura Apple riprende e salva tutti e quattro i learner. La gara Apple si conclude con cinque arrivi su tre giri; tutti rimangono visibili. Le prove di qualifica complete sono fisiche senza rendering e distinte dagli avvii dal menu.

**Rc.28 installata**, manifest di 642 file conforme, servizio attivo/NRestarts=0, heartbeat GUI fresco con il PID corrente. Tutte le righe del database Gioco sono identiche a prima dell'installazione e gli artefatti originali conservano i loro hash. Backup completo di **126 file**, rollback del runtime precedente, preferenze e Apple Calm 1.6.3 invariati. Nessun reset, migrazione di ricetta, importazione di pesi sperimentali o allenamento della produzione; nessun reboot OS.

[Ricevuta finale](evidence/v09-pilot-menu-fix-2026-10-21/board/final-receipt.json) · [manifest ARM](evidence/v09-pilot-menu-fix-2026-10-21/board/installed-manifest.json) · [sorgenti verificati](evidence/v09-pilot-menu-fix-2026-10-21/board/source-checks.json). MasterPlan revisione **3.06**.

## 4. Cosa è completato e cosa rimane aperto

- **P0:** contratto e selezione dei quattro profili dal menu corretti; errori specifici e compatibilità storica verificati.
- **Continuità P1:** i quattro learner partono, aggiornano la rete, salvano e riprendono; le tre modalità di apprendimento sono raggiungibili dal menu. Maestro resta un riferimento e non viene presentato come rete che apprende.
- **Ripresa scientifica Tattico:** resta aperto il caso del checkpoint che non migliorava nel budget precedente. Questa correzione permette di allenarlo e verificarlo dal menu, ma non dichiara risolta la sua convergenza.
- **P2:** passo competitivo nel traffico, selezione degli esperti, incentivi relativi e tattica generale restano nel seguito dello studio. Non sono stati cambiati per correggere il validatore.

Non è stato eseguito un reset dei piloti o un nuovo training della produzione. Le campagne scientifiche della rc.27 conservano il loro perimetro; non vengono ripetute automaticamente perché la matematica dei learner è invariata. I nuovi test coprono la regressione reale che il vecchio walkthrough non esercitava.
