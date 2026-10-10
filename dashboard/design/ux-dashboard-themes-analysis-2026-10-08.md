# SmartPC: dashboard e ottimizzazione dei temi

Analisi del 8 ottobre 2026. Riferimento principale: **Neo-Retro / Base**. Vincoli: display IPS 960×640 da 3,5″, consultazione a circa 50–60 cm, tastierino fisico, conservazione di colori, icone e identità dei temi.

## Decisione proposta

La preferenza per Base ha un riscontro concreto: Casa mostra già quattro preferiti in griglia, mentre Apple Calm usa righe che richiedono scorrimento. Il problema coinvolge però **sia il tema sia la struttura condivisa**. Base conserva una zona inferiore destinata alle guide; Apple Calm dispone di più altezza, ma alcune pagine mantengono schede alte 312 px e lasciano un grande vuoto sotto.

Propongo di ottimizzare prima Base e utilizzare le sue dashboard come riferimento funzionale. Apple Calm e Functional manterranno il proprio linguaggio grafico, rispettando gli stessi requisiti di contenuto, azioni, leggibilità e utilizzo degli spazi. Una scheda deve mostrare informazioni utili già nella panoramica; il dettaglio serve per approfondire.

Questo documento e il confronto interattivo sono **analisi e proposta**, senza modifiche al runtime, al tema installato o alla Orange Pi. Non attestano un risultato implementato né una validazione fisica.

## Evidenze e metodo

Ho acquisito 59 superfici per ciascuno dei tre temi, più una cattura Account con schema backend normalizzato per tema: **177 + 3 = 180 catture**. Qt 6.8.2, rendering software offscreen, finestra 960×640, palette notte, animazioni disattivate, trasporti dei provider bloccati. Le immagini sono rendering dei componenti attuali con fixture, non fotografie del dispositivo o dati live.

Le geometrie percorrono l'albero visuale `childItems`, comprendono i delegate e applicano clipping e visibilità. L'ultima scheda è un indicatore geometrico: non misura automaticamente la qualità di una schermata. Liste corte, viste senza schede, stati vuoti e notifiche richiedono valutazione semantica.

Artefatti riproducibili:

- [Script di analisi](evidence/dashboard-experience-audit-2026-10-08/audit_geometry.py), [sintesi geometrica](evidence/dashboard-experience-audit-2026-10-08/comparison-summary.json).
- [Base](evidence/dashboard-experience-audit-2026-10-08/base-night/audit.json), [Functional](evidence/dashboard-experience-audit-2026-10-08/functional-night/audit.json), [Apple Calm](evidence/dashboard-experience-audit-2026-10-08/apple-night/audit.json).
- Account normalizzato: [Base](evidence/dashboard-experience-audit-2026-10-08/base-night/audit-account-normalized.json), [Functional](evidence/dashboard-experience-audit-2026-10-08/functional-night/audit-account-normalized.json), [Apple Calm](evidence/dashboard-experience-audit-2026-10-08/apple-night/audit-account-normalized.json).
- [Confronto dei sorgenti](evidence/dashboard-experience-audit-2026-10-08/runtime-source-comparison.json): 499 file confrontati con il manifest della precedente installazione rc.2; 498 identici, solo `version.py` differente, ora 0.8.3. Apple Calm 1.3.1, digest `484b983f1622fbaccbfc09047d4c39641e5e1646bba04a2fd5cbc88f5aeb9a84`.

Nessun warning QML durante le acquisizioni e zero chiamate ai trasporti. Il primo giro Apple ha emesso due warning tardivi di asset durante la rimozione della directory temporanea, dopo le catture; lo script ora attende la distruzione del motore prima della pulizia. I tentativi iniziali sono conservati separatamente. La fixture Account canonica usa alias diversi dal backend legacy: i suoi testi `undefined` non sono prova di un difetto live. Il confronto Account qui riportato usa la fixture aggiuntiva normalizzata.

Non sono stati misurati prestazioni GPU, latenza del tastierino, leggibilità fisica o comportamento live dei provider. Le precedenti prove di installazione rimangono nel [rapporto rc.2](v083-space-optimization-report.md); questa analisi non le rinnova.

## Cosa causa lo spazio perso

| Aspetto | Neo-Retro / Base | Apple Calm | Functional |
|---|---|---|---|
| Area ordinaria dei contenuti | x44, y90, 872×455; termina a y545 | x24, y72, 912×552; termina a y624 | Stessa area di Base |
| Guide inferiori | Divisore y558, guide y578 | Rimosse nella revisione precedente | Eredita la struttura comune |
| Casa, quattro preferiti | Quattro schede in griglia, visibili | Tre righe complete e parte della quarta | Quattro righe |
| Meteo attuale | Ultima scheda a y502 | Ultima scheda a y478; fonte da y589 | Come Base nel caso acquisito |
| Sport, ingresso discipline | Ultima scheda a y517 | Ultima scheda a y624 | Come Base |
| Account normalizzato | Finestre e crediti presenti | Finestre presenti, crediti assenti | Finestre e crediti presenti |
| Rete, traffico WAN della fixture | Valore non renderizzato nella panoramica strumenti | Valore renderizzato | Come Base |

Le coordinate sono della finestra, non del singolo componente. Le aree degli overlay Rete/Impostazioni sono differenti dalle pagine ordinarie: non vanno confrontate come se avessero lo stesso contenitore.

In Apple Calm, Giornata, Meteo attuale, Previsioni e Account hanno schede fisse alte **312 px**. Fra il loro bordo inferiore e la fonte rimangono **111 px**. Assumendo diagonale nominale 3,5″ e pixel quadrati, sono circa **8,55 mm**, coerenti con lo spazio percepito dall'utente. È una conversione nominale, non una misura con calibro. Il margine esterno inferiore di 16 px vale circa 1,23 mm: eliminarlo non risolverebbe quel vuoto.

In Base, il contenuto ordinario termina 95 px prima del fondo dello schermo perché la struttura conserva le guide. Recuperare quest'area richiede modificare il layout comune e adattare i componenti. Aumentare soltanto l'altezza del contenitore rischia di spostare o sovrapporre testi con coordinate fisse.

Casa e Sport Apple sono casi diversi: arrivano già vicino al fondo. Casa ha un problema di composizione e di quarta riga tagliata; Sport ha soprattutto approfondimenti ancora impostati come elenchi di accesso. Non tutte le schermate richiedono la stessa correzione.

## Problemi da correggere insieme ai margini

1. **Parità dei contenuti.** Con due finestre Account e 12 crediti, Apple Calm omette i crediti mostrati da Base. In Rete avviene il contrario: `NetworkOverview.qml` di Base mostra titolo e dettaglio degli strumenti, ma ignora il campo `value` che contiene il traffico WAN. Il tema deve poter cambiare la composizione mantenendo i fatti principali disponibili.
2. **Gerarchia ripetuta.** Titolo globale, titolo locale, sottotitolo, tab, riepilogo e guida consumano insieme molte righe. Conservare un titolo di argomento e un'identità di vista chiara; aggiungere sottotitoli solo quando portano contesto.
3. **Componente universale a righe.** La stessa presentazione viene usata per preferiti, dati, configurazioni e destinazioni. Servono quattro composizioni: panoramica dashboard, lista di record, dettaglio, regolazioni. Classifiche e inbox beneficiano delle liste; preferiti e metriche della griglia.
4. **Navigazione dipendente dal focus nascosto.** In Casa e Rete, 4/6 cambia argomento oppure vista secondo `casaTabsSelected` / `networkTabsSelected`. Dalla prima scheda occorre prima premere 2 per raggiungere la barra viste. Eliminare la guida senza rendere evidente questo focus non rende il percorso più semplice.
5. **Icona umidità Apple.** La pagina usa `drop`, mentre il catalogo contiene `droplet`. Si può riusare l'icona esistente, evitando il simbolo di ripiego. Le nuove icone andranno create solo per significati realmente scoperti.
6. **Informazioni dispositivo.** Nella revisione analizzata Dispositivo e Risorse cambiano contenuto: la precedente duplicazione non va riportata come bug ancora aperto. Rimangono una gerarchia troppo simile e colonne valore poco adatte a metriche brevi o testi lunghi.

## Dashboard per argomento

| Argomento | Prima vista utile | Viste successive e approfondimenti |
|---|---|---|
| Oggi | Ora/data e meteo essenziale, con pannelli allineati; preservare il carattere quieto | Giornata: eventi realmente disponibili; pannello principale più ampio quando ci sono pochi elementi |
| Meteo | Condizione, temperatura/percepita, vento/raffiche, umidità/pioggia | Previsioni come schede temporali confrontabili; ulteriori dati nel dettaglio |
| Account | Finestre d'uso, reset, crediti e relativa disponibilità | Stato della sincronizzazione e opzioni degli avvisi; numero di finestre variabile senza perdita di dati |
| Sport | Conservare l'ingresso semplice per discipline | Ogni disciplina apre una panoramica con prossimo evento, stato/risultato e informazioni pertinenti; classifiche e partecipanti restano liste |
| Casa | Quattro preferiti completi, stato leggibile, temperatura/umidità quando disponibili | Dispositivi organizzati in pagine; dettaglio con tutte le misure. Una scheda offline mostra stato precedente e orario |
| Rete / iliadbox | Traffico WAN ↓/↑, temperature disponibili e osservazioni sui dispositivi | Collegamenti Wi-Fi/Ethernet, stato Internet e storico; dettagli tecnici raggiungibili dal contesto |
| Informazioni | Dispositivo: identità/versione e stato essenziale | Risorse: CPU, RAM, temperatura e spazio, con disponibilità esplicita; fonti e diagnostica approfondita in lista |
| Impostazioni | Categorie riconoscibili e accessi immediati alle regolazioni comuni | Categoria con controlli effettivi, descrizione breve e salvataggio/annullamento coerenti |
| Avvisi | Inbox leggibile per priorità e data | Dettaglio e ritorno alla stessa posizione; notifiche sovrapposte senza coprire valori o focus |

Le schede devono rispondere a domande, per esempio «quanto traffico passa?» o «la presa è online?». Un rettangolo con soltanto «Apri Wi-Fi» rimane un menu. Con uno o due dati si amplia il pannello utile; non si inventano valori o indicatori per raggiungere quattro schede.

Per Rete, distinguere **traffico rilevato, capacità del collegamento e speed test**. I record del router non provano presenza o copertura complete. Ogni metrica conserva il proprio orario e stato: un aggiornamento della WAN non rende attuali temperature o Wi-Fi. La panoramica estesa richiede proiezioni DTO e interessi del broker adeguati, mantenendo TTL, single flight e persistenza; nessuna chiamata I/O nei renderer o polling generalizzato delle viste nascoste.

Nelle Impostazioni separare consultazione e regolazione: temperature e velocità sono contenuti di Rete; la categoria Rete configura collegamento e comportamento. Un accesso contestuale «Opzioni» deve usare la stessa destinazione e lo stesso proprietario delle preferenze. Le conferme già necessarie per operazioni distruttive e il modello bozza/salvataggio restano parte del flusso.

## Regole comuni, identità dei temi

Obiettivo iniziale di geometria: barra superiore circa 56 px, contenuto da y72 fino a y624, margini laterali 24 px e inferiore 16 px. Sono **dimensioni da validare**, non risultati già implementati. La fonte occupa una riga compatta solo quando necessaria, senza prenotare una fascia per guide e contatori `1–2/3`.

Usare dimensioni derivate dall'area disponibile: griglia 2×2 per quattro elementi, 2+1 per tre, pannelli più ampi per uno o due. Valutare anche lo spazio interno: ingrandire il bordo di una scheda lasciando i testi tutti in alto non basta. Titoli, valori e stato devono mantenere una distribuzione leggibile.

Base conserva palette, contrasti e carattere Neo-Retro; Apple Calm conserva superfici, colori e icone; Functional conserva la propria sobrietà. Il requisito condiviso riguarda ordine delle informazioni, disponibilità, azioni, focus e margini. Non impone renderer identici.

Introdurre primitive comuni per area pagina, griglia adattiva, riepilogo, qualità della fonte, lista e dettaglio. I renderer esterni continuano a negoziare il layout tramite Theme API; eventuali estensioni devono essere additive e documentate nell'SDK. Non imporre nuove coordinate ai temi esterni senza compatibilità verificata.

## Navigazione: lavoro separato dal restyling

Prima fase: preservare i comandi esistenti, rendere visibile la barra viste e il focus, togliere guide persistenti e contatori. Non usare lo spazio recuperato per una nuova legenda permanente.

Seconda fase: prototipare una convenzione comune. Una possibilità è 4/6 per argomenti alla radice, 2/8 per viste quando la barra viste è selezionata, 5 per entrare nelle schede; nelle schede 2/8 seleziona, 5 apre e 7 risale di un livello conservando selezione e posizione. Home, Avvisi e Menu mantengono gli accessi globali. I casi Sport e gli overlay richiedono una tabella completa delle transizioni prima di cambiare il controller.

È una proposta da confrontare con il sistema attuale mediante compiti reali. Può migliorare prevedibilità senza ridurre ogni sequenza di pressioni. Il confronto interattivo illustra composizione e cambio vista; non simula il contratto definitivo del tastierino.

## Piano di consegna e verifiche

| Passaggio | Risultato concreto | Verifica prima di proseguire |
|---|---|---|
| D1 — Spazio e completezza | Base come riferimento; area comune adattiva; eliminazione delle guide; schede Apple senza altezza fissa; WAN/crediti e icona umidità | Confronto geometrico e contenuti sugli stessi dati, margini e focus senza sovrapposizioni |
| D2 — Casa e Rete | Preferiti 2×2; panoramica iliadbox con informazioni immediatamente visibili; viste successive coerenti | Quattro preferiti completi; traffico e temperatura consultabili senza entrare nelle Impostazioni; dati precedenti riconoscibili |
| D3 — Informazioni e regolazioni | Dispositivo/Risorse distinguibili; categorie e controlli comuni più immediati | Percorsi, salvataggio/annullamento, nomi lunghi e assenza di duplicazioni |
| D4 — Parità e navigazione | Stessi fatti e azioni nei tre temi; eventuale nuovo flusso dopo prova del prototipo | Matrice tastierino e ritorni, stati limite, entrambi i colori e scale testo |

Distribuzione proposta: **0.8.4** per D1 e D2, con Base come prima superficie di verifica e correzione contestuale della parità Apple/Functional; **0.8.5** per D3 e D4, completando Informazioni, Impostazioni e coerenza dei percorsi. Il nuovo contratto di navigazione entra in 0.8.5 solo dopo prova del prototipo; altrimenti si consegnano i miglioramenti di chiarezza compatibili con i comandi attuali. Sono numeri e contenuti proposti, non release già approvate, implementate o installate.

Criteri di accettazione da applicare alla futura implementazione:

- Nelle dashboard popolate, nessun vuoto finale ingiustificato oltre 24 px prima della fonte o del margine utile. Eccezioni motivate per orologio, stati vuoti e liste corte; nessun obiettivo di riempimento percentuale artificiale.
- Quattro preferiti interamente visibili alla scala testo 1,0 e 1,1; scheda selezionata sempre completamente visibile, nomi lunghi leggibili senza coprire il valore.
- Stessi dati chiave e azioni nei tre temi: WAN, crediti, reset e qualità. Nessun `undefined`, simbolo di ripiego o dato mancante convertito in zero.
- Prove con zero/uno/molti elementi, valori realmente pari a zero, testi lunghi, dati precedenti/offline, metriche mancanti, notifiche e aggiornamenti mentre il focus è attivo.
- Scala iniziale indicativa: titoli 28–34 px, valori principali 48–70 px, stato essenziale circa 26 px; verifica fisica a 50–60 cm prima di fissare la scala definitiva.
- Cinque compiti sul dispositivo: leggere condizioni meteo; distinguere stato attuale/precedente di un preferito; leggere traffico e temperatura iliadbox; trovare consumo/reset/crediti; modificare una regolazione e tornare alla vista iniziale. Registrare errori, passaggi e leggibilità, senza assegnare tempi non misurati.
- Dopo i controlli locali pertinenti: verifica EGLFS 960×640, assenza di warning runtime, servizio stabile, preferenze conservate, manifest e rollback. Riavvio solo quando richiesto dalla consegna; le catture di questa analisi non sostituiscono queste prove.

## Studi e fonti: cosa trasferire a SmartPC

Le fonti rafforzano il criterio «informazioni importanti subito, approfondimenti accessibili», ma non dimostrano che una griglia specifica o una dimensione di testo siano perfette sul nostro display. Distinguo linee guida, studi empirici e raccolte descrittive.

| Fonte consultata | Evidenza e applicazione | Limite |
|---|---|---|
| [Apple HIG — Layout](https://developer.apple.com/design/human-interface-guidelines/layout) | Gerarchia, raggruppamento e adattamento degli spazi | Le aree sicure e gli effetti delle piattaforme Apple non sono requisiti del kiosk |
| [Material — Metrics and keylines](https://m1.material.io/layout/metrics-keylines.html) | Ritmo e allineamento su griglia | I dp non sono automaticamente pixel del nostro IPS |
| [NN/g — Dashboard e percezione](https://www.nngroup.com/articles/dashboards-preattentive/) | Poche informazioni critiche leggibili con interazione minima; numeri e barre semplici | Linee guida, non prova specifica sul tastierino |
| [NN/g — Progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | Contenuti frequenti nella panoramica, avanzati nel dettaglio | Troppi livelli vanificano la semplificazione |
| [NN/g — Information scent](https://www.nngroup.com/articles/information-scent/) | Etichette e contesto rendono prevedibile il dettaglio | Un'etichetta chiara non sostituisce il valore nella panoramica |
| [NN/g — Cards](https://www.nngroup.com/articles/cards-component/) | Schede per elementi eterogenei; lista per record confrontabili | Non trasformare tutte le classifiche in tessere |
| [NN/g — Grids](https://www.nngroup.com/articles/using-grids-in-interface-designs/) | Allineamenti coerenti e composizione adattiva | La densità va verificata sullo schermo reale |
| [NN/g — Recognition and recall](https://www.nngroup.com/articles/recognition-and-recall/) | Vista e focus riconoscibili riducono memoria dei comandi | Rimuovere le guide richiede segnali alternativi verificabili |
| [NN/g — Complex applications](https://www.nngroup.com/articles/complex-application-design/) | Continuità tra panoramica e dettaglio | Applicazioni più grandi del nostro contesto |
| [Carbon — Dashboards](https://www.carbondesignsystem.com/building-blocks/data-visualization/dashboards) | Priorità dei KPI e consistenza delle rappresentazioni | Non copiare la densità di una dashboard desktop |
| [Bach et al. — Dashboard Design Patterns, 2022](https://arxiv.org/abs/2205.00757), [catalogo degli autori](https://dashboarddesignpatterns.github.io/patterns.html) | Revisione di 144 dashboard e workshop di due settimane con 23 partecipanti; pattern di pagine, panoramiche e dettagli | Non è un esperimento che dimostra la superiorità universale di quattro schede |
| [Shneiderman — The Eyes Have It, 1996](https://www.cs.umd.edu/users/ben/papers/Shneiderman1996eyes.pdf) | Panoramica, selezione e dettagli mantenendo contesto | Principio progettuale, non validazione SmartPC |
| [Blascheck et al. — Glanceable Visualization, 2018](https://www.microsoft.com/en-us/research/uploads/prod/2018/08/GlanceableVis-InfoVis2018.pdf) | Due studi, 18 partecipanti ciascuno, confronto tra barre, donut e grafici radiali su smartwatch | Display circa 28,73×28,73 mm e distanza circa 28 cm: risultati e tempi non trasferibili direttamente a 50–60 cm |
| [Matthews, Forlizzi, Rohrbach — Glanceable Peripheral Displays, 2006](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2006/EECS-2006-113.html) | Interviste, letteratura e caso applicativo: informazione periferica con limitata interruzione | Consultata la descrizione del rapporto; non prova una scala tipografica specifica |
| [A Census of Visualization Dashboards, 2023](https://arxiv.org/abs/2306.16513) | Raccolta descrittiva di 25.620 dashboard Tableau Public; utile per metodo di inventario | Consultato l'abstract; frequenza di un pattern non equivale a efficacia sul nostro IPS |

Il confronto allegato contiene catture attuali Base/Apple e una proposta Neo-Retro per Casa, Rete, Meteo e Account. I valori sono fixture o indisponibilità esplicite. Le icone schematiche del prototipo illustrano i significati: l'implementazione dovrà riutilizzare gli asset originali dei temi. La versione stretta del confronto si adatta al browser; soltanto le catture QML sono prove della geometria attuale 960×640.

La [verifica del confronto](evidence/dashboard-experience-audit-2026-10-08/preview-review.json) comprende le otto viste a due larghezze di browser, caricamento delle immagini e cambio argomento/vista/variante. Le schede non hanno overflow nella revisione finale. Due errori di una prima revisione sono rimasti nel log del browser; il riferimento alle immagini è stato corretto prima della verifica finale.

## Esito successivo · 9 ottobre 2026

Dopo l’autorizzazione all’implementazione, D1/D2 sono consegnati nella candidata **0.8.4-rc.1**, con Base conservato e Apple Calm 1.4.0 disponibile. D3/D4 rimangono pianificati per la 0.8.5. Le proposte e le catture precedenti restano la baseline di questa analisi; gli esiti attuali sono nel [resoconto di implementazione e installazione](v084-dashboard-optimization-report.md).

Il 9 ottobre la [nuova analisi 0.8.5](v085-settings-theme-analysis.md) aggiunge cambio tema tramite lista, caricamento per fasi, recupero GUI come priorità P0 e revisione mirata di Impostazioni/Informazioni. Contiene la lettura non invasiva del journal reale, un percorso Main isolato con difetti riprodotti e 14 riferimenti mirati. Questi risultati non attestano un fix già implementato o una nuova installazione.
