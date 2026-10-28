# v0.9.0-rc.9 · Accademia di guida e fisica gara

**13 ottobre 2026 · implementata e installata; perimetro PC/EGLFS verificato.** Theme API 2.10, 68 superfici; distribuzione da 572 file. [Evidenze](evidence/v09-academy-2026-10-13/), [studio dello stallo](game-idle-learning-study.md), [studio fisica/sensori](game-racing-space-physics-sensors-study.md).

## 1. Percorso del pilota

Start di Impara attiva un percorso `academy-1`. Aprire la vista, installare il software o riavviare la dashboard non avvia apprendimento o migrazione dei piloti. Nome, identità, algoritmo, seme, popolazione, dimensione della rete e parametri propri del metodo restano fissati. Un solo pilota si allena; i rivali restano congelati.

| Esercizio | Compito | Condizione |
| --- | --- | --- |
| Partenza | 1 → 3 → 8 → 20 m | Si alza il traguardo dopo almeno 20 successi negli ultimi 32 tentativi, al confine di un aggiornamento. La valutazione richiede sempre 20 m. |
| Controllo | Un giro solitario | Cancellate uscite di pista e contatti. |
| Passo | Tre giri solitari | Premio al progresso e costo del tempo; confronto con un campione congelato. |
| Inseguimento | 100 m dietro un rivale | Distanza 5–35 m per almeno il 65% del tempo. |
| Sorpasso | 200 m | Passaggio da dietro ad avanti con margine maggiore della lunghezza vettura + 1 m; nessun contatto o track limit. |
| Affiancamento | 160 m su una curva moderata | Sorpasso pulito; settore scelto dalla geometria, non dalla curva più stretta. |
| Difesa | 120 m con rivale dietro | Rivale ancora dietro con margine al termine. |
| Gara 2 | Tre giri con un rivale | Prova condivisa, senza reset in corsa. |
| Partenza in gruppo | 200 m, quattro vetture | Griglia sfalsata da 6 m; completamento pulito. |
| Gara 4 | Tre giri, quattro vetture | Prova condivisa e conservazione delle abilità precedenti. |

L'avanzamento di fase richiede due finestre affidabili su scenari diversi. PPO/Clone ripassano esercizi precedenti tra ambienti indipendenti; Evoluzione/NEAT ripetono una generazione di un compito precedente ogni cinque aggiornamenti. La valutazione controlla anche le abilità già acquisite. È un curriculum implementato, non una promessa che ogni algoritmo o seme completi tutte le fasi.

## 2. Stallo e ricompense

Due secondi di grazia; un metro di nuovo progresso rinnova il credito. Una velocità sotto 0,5 m/s, almeno tre secondi senza credito e altri quattro secondi lenti termina il tentativo. Il limite generale è 15 secondi senza nuovo avanzamento. Una sosta dietro un rivale fermo vicino viene riconosciuta separatamente e conserva il normale deadline. Nessun controllo dei comandi di gas, nessun minimo di velocità imposto.

Stallo, incidente e completamento sono terminali. Deadline e traffico bloccato sono troncamenti: PPO conserva l'ultima osservazione fisica e il bootstrap; l'osservazione dopo reset non viene usata come successore. Il reset è del tentativo in Impara. Gara, Prova e Campione usano modelli congelati e non ricreano vetture durante una corsa.

La Partenza normalizza il premio del progresso rispetto al traguardo breve: a 20 m coincide con `progresso/10`. Il bonus viene pagato soltanto dopo il completamento valido. I termini progresso/tempo/contatto/fuori pista/arrivo/controllo/compito/stallo vengono registrati separatamente. Non si tratta di shaping dichiarato invariante: i compiti iniziali hanno un obiettivo diverso, esplicito e versionato.

Nel nuovo percorso PPO usa `gamma=exp(-DT/40)`, circa 0,999583 a 60 Hz. Il valore precedente 0,995 rimane nel percorso archiviato. Critic, memorie ed optimizer incompatibili vengono ricreati; l'attore resta conservato. GAE λ=0,95 e rollout/epoche restano quelli del pilota; ulteriori confronti separati rimangono aperti.

## 3. Fisica f2-1 e scala

- Vettura standard **4,4 × 1,8 m**, passo 2,65 m, massa 1.200 kg e potenza 85 kW. Varano e Mallory mantengono strada simulata 12 m; i circuiti compatti mantengono 10 m.
- Posizione e altezza del baricentro, carichi per asse con trasferimento longitudinale, ripartizione trazione/frenata, budget di aderenza combinato e saturazione laterale continua. Resistenza aerodinamica e rotolamento sono esterni al budget dei pneumatici.
- Accelerazioni nel riferimento della vettura, incluse le componenti dovute alla rotazione. Passo fisico 60 Hz e sottopassi adattivi conservati.
- Urto tra corpi orientati: normale, profondità, impulso e imbardata; ritiro per velocità relativa d'impatto ≥12 m/s. Soglia di gioco sperimentale, senza modello di danno o attribuzione di colpa. La risposta d'impulso normale è verificata per quantità di moto e dissipazione nel caso controllato.
- Uscita lieve: fondo meno aderente e con maggiore rotolamento, limite sportivo registrato, niente premio di progresso fuori strada. Barriera a 6 m oltre il bordo; i cancelli e la validità del giro restano autorevoli.
- Le vetture ritirate sono sagome trasparenti, con `×`, escluse da contatti e sensori. La convenzione è descritta nel dossier.

Il rendering usa le dimensioni pubblicate dal veicolo. Ruote, vetri, bordi e selezione sono proporzionali; nessun minimo in pixel ingrandisce la carrozzeria. Segui/Duello restano le camere per leggere traiettorie e distanze; la minimappa usa simboli. Display nativo invariato: **960 × 640 orizzontale**.

Non sono introdotti ABS/TCS, slip longitudinale delle ruote, cambio, trasferimento laterale, usura, banking o fondi avanzati. Richiedono stati e verifiche ulteriori. Cataloghi di pista/vettura/gomme/fondo/condizione restano separati; nuovi contenuti richiederanno un nuovo ambito e qualifiche proprie.

## 4. Sensori e guida nel traffico

`race-68-v3`: 68 canali normalizzati, inclusi cinque raggi frontali fino a 150 m, velocità/sterzo/assetto/offset e punti anticipati, tre rivali anche dietro, quattro raggi laterali/posteriori, margini del corpo orientato, accelerazioni e slip laterale, curvatura anticipata, spazio tra ingombri e rischio TTC, timer e fase del compito. Le reti precedenti 32/42 mantengono schema e normalizzazione originali.

Il riferimento `traffic-pursuit-2` sceglie corridoi, controlla un rivale in avvicinamento da dietro, mantiene distanza quando segue e limita la velocità per la curva e lo spazio libero. È il maestro esplicito di Clone e un avversario di esercizio. Il comando delle reti autonome non viene corretto da questo controllore. I modelli Gara 4 disponibili all'avvio possono diventare avversari congelati; i pesi e la selezione sono salvati nel checkpoint della sessione.

Allenamento, stato RNG, ambienti, timer, dataset, optimizer, minibatch e valutazione pendenti sono ripristinabili. La preview del pilota resta indipendente dalla raccolta accelerata; la GUI mostra poche vetture e metadati compatti. Le valutazioni impossibili da qualificare si interrompono presto: scenari non eseguiti sono espliciti e non contano come validi.

## 5. Qualifica, gara e conservazione

Solitario, Gara 2 e Gara 4 sono distinti. Le qualifiche richiedono almeno **18/20 scenari validi su tre giri**, stessa policy congelata, stesso circuito/fisica/sensori. Dieci scenari sono nella fascia di valutazione e dieci nella fascia indipendente oltre il milione, separate dai semi di training. Per Gara 2 serve la prova condivisa Gara 2 e la conservazione di solo/sorpasso; Gara 4 richiede anche la prova a quattro e le abilità precedenti. Partenza o sorpasso breve da soli non assegnano una qualifica da gara.

Un hash diverso invalida la qualifica. Le prove selezionano/promuovono il modello: non sono una certificazione esterna né un benchmark universale mai usato per decisioni. Gare e Prove precedenti hanno ambiti distinti; la classifica mostra la fisica della sessione, il grafico confronta soltanto lo stesso esercizio. Fitness private di metodi diversi non sono confrontate.

Start archivia l'intero percorso precedente e crea un percorso v2. I nuovi ingressi densi partono con pesi zero; attore, popolazione/geni e RNG utili sono conservati. Le memorie legate all'obiettivo precedente ripartono. La parità algebrica dei pesi espansi non implica identica guida con nuova fisica/normalizzazione. La policy da gara precedente resta disponibile finché viene verificato un nuovo campione solitario. La prova del campione precedente resta associata al suo esatto hash anche sui circuiti nuovi durante il cambio percorso; non qualifica il nuovo candidato. I checkpoint originali restano artefatti immutabili e lo storico indica il cambio percorso. I contatori del nuovo percorso partono da zero; lo storico complessivo include il precedente.

Modelli neurali di fisiche differenti non vengono schierati insieme. Il riferimento geometrico può usare la versione esplicita coerente con la gara: la sessione registra artefatto e origine, senza addestrarlo o riscrivere il pilota. Le gare vecchie restano compatibili con f1-2.

Nel dossier: metodo/parametri, fase, partenze complete e microesercizi distinti, stalli, tempo fermo simulato, tempi mediani al primo/decimo metro, sorpassi validi e qualifiche per hash. Reset continua a riguardare il solo percorso selezionato, con conferma e storico conservato.

## 6. Prove e limiti

- Regressione PC: 57 controlli di gioco superati; 16 controlli mirati dell'Accademia e ulteriori contratti dei temi. [Log](evidence/v09-academy-2026-10-13/pc/).
- UI reale su PC: Base, Functional, Apple Calm a 960×640, descrizioni, selettori, dossier, reset, Start/Pausa/ripresa. Warning QML assenti nei casi verificati.
- Gare complete PC con riferimenti congelati: 2 e 4 vetture, tre giri, tutti arrivati e nessun respawn. Sono prove del motore/UI, **non piloti neurali qualificati**. [Risultati](evidence/v09-academy-2026-10-13/pc/new-races-final/report.json).
- Prove preliminari isolate da 90 s PC, un seme per metodo e cinque scenari nuovi di Partenza: Evoluzione, NEAT e PPO da 0/5 a 5/5; Clone 5/5 iniziale e finale; PPO-Smooth resta 0/5. [Dati](evidence/v09-academy-2026-10-13/pc/learning-probes.json). Il protocollo iniziale non aveva microesercizi normalizzati.
- Dopo il riscontro su PPO-Smooth: con microesercizi a risultato e progresso normalizzato, seme 6, 120 s PC, **5/5 partenze complete nuove**; 151/198 microesercizi riusciti. [Dati](evidence/v09-academy-2026-10-13/pc/smooth-progressive-normalised.json). Budget diverso e un solo seme: prova del meccanismo, non superiorità generale o qualifica gara.

Qualifica estesa su cinque semi per ogni metodo, ablation dei sensori, taratura fisica quantitativa e resistenza prolungata rimangono esperimenti aperti. I piloti reali non sono stati riaddestrati dalle prove: devono ancora acquisire le qualifiche nel nuovo percorso. Fisica, sensori, training e inferenza restano su CPU. La NPU non viene presentata come usata o necessaria.

## 7. Scheda e consegna

Baseline osservata rc.8/567 file; candidata rc.9 installata con **572 hash conformi**, Qt 6.8.2, Base attivo, servizio active e `NRestarts=0`. [Ricevuta finale](evidence/v09-academy-2026-10-13/board/final-receipt.json), [manifest](evidence/v09-academy-2026-10-13/release-manifest.json).

Prima delle prove, un journal di rollback orfano impediva la lettura in sola lettura dell'archivio gioco. Il backup completo da 809 MiB conserva runtime, dati/configurazione e journal originale in `/var/backups/smartpc-before-academy-20261013-044418`. Recupero SQLite con `integrity_check=ok`; la sola sessione rimasta in pausa il 12 ottobre è stata marcata `interrupted`. Il dump recuperato prima e dopo questa correzione è registrato. **Tutte le colonne dei sei piloti e i 1.218 artefatti sono conservati; tutte le tabelle sono uguali al baseline dopo il recupero e la chiusura della vecchia pausa.** Non si dichiara parità del solo stato sessione rispetto alla pausa orfana. Il runtime rc.8 resta disponibile come rollback.

Prove native EGLFS 960×640: Base/NEAT, Functional/Clone, Apple/PPO-Smooth, impostazioni notturne, dossier e quattro camere su Varano senza warning QML o traceback Python nei casi verificati. Il primo tentativo Base si è fermato perché il banco richiedeva il renderer diagnostico escluso dal pacchetto produzione: aggiunto soltanto alla cartella di prova, senza includerlo nell'installazione. [Qualifica nativa](evidence/v09-academy-2026-10-13/board/native-qualification.json).

Le Gare 2/4 native completano tre giri sul circuito tecnico: tutti arrivati, zero respawn, piloti congelati invariati. Sono riferimenti geometrici, non una certificazione dei sei piloti neurali reali. [Risultati](evidence/v09-academy-2026-10-13/board/new-races/report.json).

La correzione finale della prova del campione archiviato passa il controllo mirato ARM e il walkthrough Base aggiornato. Tutti e sei i checkpoint di produzione si riprendono nelle **copie temporanee**: parametri immutabili, percorso originale archiviato, contatori complessivi conservati, Pausa/Salvato/ripresa. Gli originali non vengono allenati. Ack del worker nella prova finale: valori nel [report delle copie](evidence/v09-academy-2026-10-13/board/production-checkpoints-copy.json); sono tempi IPC, non latenza fisica del tastierino.

Misure software native: riferimento mobile su Varano, mediana `frameSwapped` **16,71 ms**, p95 **34,72 ms**, massimo **41,05 ms** in 12 s; progresso **210,90 m**. Walkthrough Apple/PPO-Smooth: mediana **17,20 ms**, p95 **37,05 ms**, massimo **821 ms** sull'intero protocollo comprendente navigazione e salvataggi. Non sono misure ottiche/GPU, né prova di 60 FPS costanti. Carico/uso prolungato restano un gate separato.

Avvio completo dell'app installata con servizi e dati reali sotto manutenzione, cattura nativa e ritorno al servizio normale: GUI pronta verificata sul PID corrente dopo composizione (la prima cattura precoce è conservata come tentativo non valido), nessun Start implicito del gioco, preferenze/tema/dump/artefatti ancora conformi. [Avvio](evidence/v09-academy-2026-10-13/board/full-startup.json), [immagine](evidence/v09-academy-2026-10-13/board/full-startup-screen.png), [stato finale](evidence/v09-academy-2026-10-13/board/final-health.json). Stesso boot ID; **nessun nuovo reboot OS**. La cattura è dell'app completa lanciata durante manutenzione, non una fotografia del pannello o della successiva istanza systemd.
