# Gioco rc.23 — tentativi e apprendimento visibili

**20 ottobre 2026 · rc.23 installata, 625 hash conformi · cinque piloti e 60 artefatti originali conservati.**

## Diagnosi sullo stato reale

Lettura SQLite in sola lettura e checkpoint persistenti, senza avviare uno store
sugli originali. [Dati selezionati](evidence/v09-learning-visibility-2026-10-20/board-learning-diagnosis.json).

- La vista Impara mostrava sempre il campione congelato, aggiornato soltanto
  dopo una promozione. Il candidato imparava in una simulazione separata. Vedere
  lo stesso tempo non permetteva di capire se la rete stesse cambiando.
- Dopo il primo miglioramento, il riepilogo sostituiva anche il contatore delle
  decisioni con la percentuale sul Maestro: l'attività diventava poco visibile.
- **Crono:** 58.381 decisioni, 456 aggiornamenti, 168 episodi e 28 verifiche.
  Mediana verificata da 36,867 a 33,317 s. Gli ultimi cinque candidati sono
  validi ma più lenti (33,700–34,067 s): stallo reale rispetto al campione.
- **Memoria:** 9.936 decisioni, 2.453 aggiornamenti, 30 episodi, quattro
  promozioni; mediana da 36,867 a 30,450 s. Apprendimento presente, non visibile
  giro per giro nella vecchia anteprima.
- Linea ha 397 aggiornamenti ma nessuna verifica conclusa; Tattico 993 e la
  prima verifica in corso nel checkpoint. Maestro è il riferimento fisso e
  non apprende. Questi numeri hanno budget diversi e non sono una classifica
  scientifica dei metodi.

## Correzione

1. In Impara, Giro infinito e Sorpasso, la vettura visibile prova **il candidato
   attuale**, con una copia congelata della rete per ciascun giro. La rete
   successiva entra dal primo passo fisico dopo l'attraversamento del traguardo.
   Nessun cambio di pesi a metà giro; bot e moto continuo restano coerenti.
2. Contatori permanenti **Agg.**, episodi e verifiche; nell'ovale, **Candidato ·
   prova N**, versione della rete congelata e scarto dell'ultima verifica contro
   il campione. La versione in pista può essere precedente all'ultimo
   aggiornamento, perché termina il giro prima di cambiarla.
3. Il giro completato conserva il modello che lo ha guidato. I tempi delle
   prove confrontano anche candidati diversi, sempre come anteprima. Giro di
   lancio, uscite, settori e giri non validi restano distinti; nessun record
   ufficiale viene prodotto da questa vista.
4. Il campione migliore continua a cambiare soltanto dopo una verifica completa.
   Qualifica e Gara usano il percorso protetto già esistente. Un candidato più
   lento o meno sicuro non lo sostituisce.
5. Pausa e ripresa salvano anche rete visibile, numero di prova e versione.
   Nei vecchi checkpoint si rinnova soltanto la dimostrazione grafica. Actor,
   critic, replay, ottimizzatori, RNG e progresso della raccolta restano intatti.

La raccolta stocastica e accelerata continua nel worker. La prova visibile a
velocità reale **non è il replay delle transizioni raccolte** e non viene
conteggiata come esperienza aggiuntiva. Gli episodi sono quelli realmente
conclusi dalla raccolta; gli aggiornamenti sono quelli del backend. PPO, SAC e
TD3 non hanno generazioni Evo/NEAT: non viene inventato un contatore equivalente.

## Stallo e limiti

La correzione rende osservabile la ricerca e risolve l'anteprima immutabile;
**non garantisce un miglioramento ad ogni giro e non dichiara risolto lo stallo
di PPO**. Nel checkpoint Crono l'esplorazione non è collassata: deviazioni
standard circa 0,0098/0,1486. L'ultima varianza spiegata del critic è negativa;
è un segnale da studiare, non la prova di una causa unica. Un solo checkpoint
non giustifica cambiare insieme premi, learning rate e ricetta dei piloti.

Per una successiva taratura: confrontare separatamente critic e ripartenza
della ricerca dal campione dopo verifiche ripetutamente negative, contro la
baseline conservata. Almeno cinque semi, stessi budget di transizioni e costo
totale incluse verifiche, banca di sviluppo separata da una nuova banca finale;
misurare distribuzione dei miglioramenti, giri puliti e sicurezza. Conservare i
risultati negativi. I premi comuni respinti nella rc.22 non vengono riattivati.

## Verifica e consegna

Evidenze in [v09-learning-visibility-2026-10-20](evidence/v09-learning-visibility-2026-10-20/).

- **41 test PC passati**, inclusi cambio candidato solo al traguardo, attribuzione
  al modello precedente, ripresa JSON, RNG invariato e protezione delle sessioni
  ufficiali. Tre oggetti Qt non raccoglibili segnalati all'uscita dell'interprete;
  nessun fallimento di test.
- Worker/Main privati PC, Base 960×640, 74 s: due cambi di candidato,
  aggiornamenti 0→57, episodi 0→20, verifiche 0→3, nessun warning QML.
- **15 test ARM passati**, compresa ripresa numerica della raccolta e verifica
  che il cambio di candidato non modifichi il RNG del learner.
- Tre prove Main/Worker private **EGLFS 960×640** su Base/Funzionale/Apple Calm,
  rispettivamente 54/45/45 s. Copia dello stesso Crono reale: aggiornamenti
  456→464, episodi 168→171 e un cambio di candidato al traguardo in ogni prova;
  nessun warning QML. Le tracce registrano eventi significativi, non tutti i
  frame. Confronto visivo delle schermate Base/Apple effettuato.
- [Ricevuta di installazione](evidence/v09-learning-visibility-2026-10-20/board/final-receipt.json):
  625 hash conformi, cinque piloti, tutte le tabelle e 60/60 artefatti originali
  conservati; preferenze identiche e **Apple Calm 1.6.3 attivo** come prima della
  consegna. Il tema attivo è cambiato rispetto alla vecchia ricevuta rc.22 ed è
  stato riletto, senza reimpostarlo su Base.
- GUI corrente pronta, PID verificato 23272, servizio active/NRestarts=0.
  Riavvio del servizio, nessun reboot del sistema. Backup dati e rollback
  runtime riportati nella ricevuta. Nessuna nuova certificazione FPS o
  convergenza dei metodi.
