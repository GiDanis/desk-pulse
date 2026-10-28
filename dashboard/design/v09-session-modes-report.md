# Gioco — consegna modalità, Qualifica e stabilità NEAT

**13 ottobre 2026 · candidato 0.9.0-rc.14 · Theme API 2.11.** Attuazione dello [studio M0–M3](game-session-modes-results-study.md). Implementata, installata e verificata sul perimetro nativo descritto sotto; le misure software non sono FPS ottici.

## Implementazione

- Registro comune di cinque modalità: Impara, Qualifica, Gara, Impara giro infinito, Impara sorpasso. Prova/Campione restano leggibili e invocabili per compatibilità; non attribuiscono nuove qualifiche.
- Un pilota apprende; metodi, popolazione e parametri manuali restano fissi. Pure Pursuit può qualificarsi/gareggiare; Start in Impara viene rifiutato con spiegazione.
- Qualifica congela il candidato salvato, un giro di lancio e tre cronometrati. Almeno un giro pulito, misurato sui quattro passaggi, abilita la gara. Ogni giro valido viene salvato subito, anche se la sessione viene poi messa in pausa. Nessuna conversione dei vecchi esercizi o tempi in certificati nuovi.
- Gara schiera 2–4 snapshot qualificati dello stesso contesto fisico. I tempi appartengono agli hash effettivamente usati; un candidato successivo non eredita il tempo. Griglia crescente/decrescente, parità sui successivi tempi validi e numero/ID stabile. Tutte le vetture rimangono visibili.
- Traguardo non terminale nei due infiniti; finestre interne di 60 secondi simulati consentono aggiornamenti Evo/NEAT. PPO distingue taglio esterno da incidente e prosegue lo stesso mondo dopo il taglio. Checkpoint per obiettivo, circuito e archiviazione dei contesti fisici; identità/base comune. Il reset completo archivia e azzera anche obiettivi e qualifiche.
- Sorpassi con 1–3 bot geometrici dichiarati e congelati. Incontro davanti → affiancamento → margine posteriore tenuto 0,5 s, pulizia locale alla manovra, cooldown 8 s. Una vecchia uscita non vieta tutti i futuri premi. Nessun respawn dei bot sul tratto occupato. Contatti, uscite e stallo continuano a pesare sulla ricompensa.
- Ripasso della memoria anche per gli obiettivi continui, dopo cinque aggiornamenti: base consolidata soltanto dopo verifica delle abilità conservate; non si copiano tempi ufficiali tra circuiti.

## Fix visuale e tempo

NEAT/Evo non cambiano più da popolazione a uno scenario di verifica nella vista Tentativi. Ogni mondo porta una revisione del reset: il renderer non interpola pose di tentativi diversi, anche se il ritorno alla partenza è inferiore a 10 metri.

La vista Pilota osserva una policy congelata per tentativo su un mondo indipendente. Non assegna fitness o giri ufficiali; il modello successivo viene adottato al confine del tentativo. Il cambio di fase dell’allenamento non ricrea la dimostrazione. Le copie reali rimangono disponibili in Tentativi.

Sensori raccolti in piccoli blocchi, passi fisici a DT invariato, recupero temporale limitato e scadenze assolute per Qualifica/Gara. Velocità al suolo coerente con V max; conclusi/pausa mostrano l’ultima velocità. Rapporto simulato/reale distinto dai 30 Hz di presentazione. Nessun aumento artificiale della velocità o extrapolazione delle posizioni. CPU: fisica, reti e training; GPU: Qt; nessun nuovo backend NPU.

Il canale compito conserva i codici esistenti. Qualifica e Gara adottano entrambe Controllo = 1/9, con sensori di traffico reali; il tempo di griglia misura quindi lo stesso codice di distribuzione. I checkpoint precedenti restano artefatti immutabili, inclusi episodi/verifiche in corso.

## Risultati e UX

Impostazioni condizionali, descrizioni brevi e focus per identità: solo Gara mostra rosa/giri/griglia; Qualifica ha un pilota; Sorpasso ha bot. Profilo tecnico consultabile. Nessuna nuova legenda permanente.

Risultati del pilota organizzati in Allenamento / Qualifica / Gare; dettagli navigabili con 5, ritorno con 7. Esercizi in metri e tempo tipico, riusciti su eseguiti, non eseguiti e verdetto complessivo. Il caso Evo 4,91 s è un Rientro di 40 m: Controllo 0/3 e 17 non eseguiti resta una verifica non superata. Grafici limitati a esercizio/distanza/protocollo/contesto comparabili e retention superata. Tempi ufficiali in minuti:secondi,millesimi; versioni e invalidazioni nei dettagli.

## Prove e limiti

- PC: 99 controlli, una esclusione già prevista; nuove modalità, giro vero di qualifica, conservazione snapshot, ripresa, finestre PPO, mondo oltre quattro giri, reset NEAT e risultati tecnici.
- ARM: dieci nuovi controlli passati sul runtime della scheda, su archivi privati.
- Walkthrough PC 960×640: Base, Functional e Apple Calm; NEAT Pilota/Tentativi, PPO, impostazioni e dossier; zero warning QML. Qualifica → Gara con due riferimenti, giri effettivi, nessun certificato neurale artificiale. Vista Pilota circa 0,99× nelle finestre PC provate.
- Le finestre PC brevi hanno mostrato picchi di frame durante alcuni aggiornamenti. Non attestano il gate di fluidità del pannello; qualifica EGLFS, carico maturo e misure finali riportati nella ricevuta.
- Il successo dei controlli non dimostra che i sei piloti sappiano già completare un giro, sorpassare o gareggiare. Servono allenamenti e Qualifiche espliciti. Restano prove ottiche/input, uso lungo, confronti scientifici a budget uguali e taratura dei premi.

[Evidenze, manifest e ricevuta](evidence/v09-session-modes-implementation-2026-10-13/).

## Ricevuta finale

**Rc.14 installata**, 588 hash conformi, API 2.11/68 superfici. Servizio e GUI pronti, `NRestarts=0`, Base attivo conservato. Sei piloti, **1.808 artefatti**, pesi/checkpoint/contatori e preferenze invariati. Nessun allenamento originale avviato dalle prove, nessun reboot OS.

Sette casi EGLFS più supplemento di navigazione: NEAT 32 tentativi/Functional sul Tecnico, cinque modalità/Qualifica→Gara Apple Calm, checkpoint NEAT reale, gara 2/4 con inquadratura di tutte le auto, dossier e classifiche al tasto 5. Zero warning QML. Le qualifiche prodotte nelle prove appartengono esclusivamente agli archivi privati dei riferimenti dichiarati.

Sul checkpoint NEAT maturo, 20 s: **1,0016×**, clock **30,00 Hz**, 599 frame; p95 **45,13 ms**, p99 **60,07 ms**, massimo **83,27 ms**. Gate software del campione in movimento superato. Apple Calm, 16 s: 0,9977×, clock 30 Hz; 62 intervalli dei frame in movimento, p95 35,33 ms e massimo 38,88 ms. I gap grezzi dei frame Apple raggiungono un secondo quando il pilota principiante è fermo/in attesa di ripartenza: Qt non presenta nuovi frame se nulla cambia. Il clock resta regolare (massimo 52,07 ms). Non sono una misura di movimento a un FPS, né una verifica ottica generale.

Il primo controllo di conservazione ha rifiutato la consegna per la sola transizione della sessione originale da `paused` a `interrupted` al riavvio; rollback automatico a rc.13 e confronto diretto col backup. Corretto il controllo: ammette solo la chiusura prevista, con payload/tempi/pesi invariati. Consegna successiva e supplemento passati. Checkpoint NEAT preservato: 362.642 passi, 4.419,47 s, generazione 86; nessun reset del pilota.

Backup dati: `/var/backups/smartpc-before-sessions-20261013-224246`. Rollback rc.13: `/opt/smartpc/dashboard-rc13-before-sessions`; versione rc.14 prima del supplemento: `/opt/smartpc/dashboard-rc14-before-navigation`. [Ricevuta finale](evidence/v09-session-modes-implementation-2026-10-13/board/window-receipt.json) · [Manifest finale](evidence/v09-session-modes-implementation-2026-10-13/runtime-manifest.json).

Gli episodi/verifiche dei checkpoint precedenti riprendono fedelmente. Evo/NEAT adottano il compito di un giro al successivo rinnovo della popolazione; PPO/Clone alla chiusura del vecchio tentativo multigiro. Cambiare durata invalida la comparabilità della vecchia fitness, non i pesi o i certificati di Qualifica. Le prove ottiche/input e di lungo periodo restano aperte, come la competenza reale dei piloti.

**Supplemento finale sulle finestre:** tempo/credito/sensori persistono al taglio esterno PPO, con bootstrap sullo stesso stato. Il modello della dimostrazione continua viene aggiornato al confine della finestra, conservando posizione e revisione. Bot e maestro considerano anche traffico doppiato nella medesima zona fisica, usando il gap circolare solo nei mondi continui. Dieci controlli mirati passati su PC/ARM e tre modalità in Functional/EGLFS; tutti i dati originali conservati. Rollback precedente al supplemento: `/opt/smartpc/dashboard-rc14-before-windows`. Nessun cambiamento a DT, dimensioni o parametri dei piloti.
