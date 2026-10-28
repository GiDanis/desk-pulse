# SmartPC v0.11 — Ricerca online per il Compagno A

> **Riallineamento roadmap · 13 ottobre 2026:** Compagno ora v0.11, memoria/scene AI v0.12; la nuova v0.10 è Acquario. Nomi dei file e asset conservati per mantenere i collegamenti. Baseline, fonti e proposte dell’11 ottobre restano storiche; per stato corrente e numerazione vale il [MasterPlan](release-masterplan.md), revisione 2.68. Nessuna nuova verifica sulla board.
**Revisione 1 · 11 ottobre 2026 · Europe/Rome**

**Stato: studio, senza implementazione o benchmark.** Integra [analisi](v010-companion-analysis.md) e [specifica](v010-companion-functional-spec.md). Conserva stile A, accudimento attivo, progressione, presenza ambientale, schermata dedicata e reazioni agli avvisi. Baseline locale: MasterPlan 2.56, core 0.9.0-rc.6, Theme API 2.9; nessuna nuova verifica della board.

## 1. Metodo e forza delle evidenze

Fonti consultate online l'**11 ottobre 2026**: due studi empirici originali, tre contributi di sviluppatori di Game AI Pro, documentazione Qt 6.8/SQLite, linee guida Google/W3C, produzione Disney/Spine, prodotto Bandai e ricerca originale sull'animazione generativa. Sono **14 riferimenti principali**, non 14 esperimenti scientifici.

Ogni scheda separa contenuto della fonte, applicazione proposta e limite. Studi su agenti umani o videogiochi non dimostrano che il nostro cane produrrà lo stesso risultato. Documentazione Qt della serie 6.8 può riflettere patch successive alla 6.8.2 della baseline: verificare le capacità del runtime effettivo nel prototipo. Nessuna fonte esterna certifica i 60 FPS su questa Orange Pi.

Riprendiamo meccaniche e principi, costruendo un personaggio originale con asset AI nostri. Non importiamo personaggi, immagini, codice o capitoli dei prodotti/studi citati.

## 2. Studi sul rapporto e sul gioco

### S1 · Continuità del rapporto — Bickmore e Picard, 2005

[Establishing and Maintaining Long-Term Human-Computer Relationships, copia degli autori](https://www.ccs.neu.edu/home/bickmore/publications/toCHI.pdf), ACM TOCHI; abstract e sezioni introduttive. Esperimento controllato con **101 utenti per un mese**, agente conversazionale per attività fisica: l'agente dotato di comportamenti relazionali ottenne valutazioni superiori su gradimento, rispetto e fiducia rispetto al confronto orientato al compito.

**Applicazione proposta:** identità e saluti riconoscibili fra sessioni; il legame sblocca modi di rispondere, oltre a numeri. **Limite:** agente umano parlante e contesto diverso; nessuna prova diretta per cane silenzioso, accudimento o effetti di benessere. Non serve introdurre un LLM nella v0.11 per sperimentare continuità comportamentale.

### S2 · Scelta e padronanza — Ryan, Rigby e Przybylski, 2006

[The Motivational Pull of Video Games: A Self-Determination Theory Approach](https://selfdeterminationtheory.org/wp-content/uploads/2020/10/2006_RyanRigbyPrzybylski_MandE.pdf), DOI 10.1007/s11031-006-9051-8. Quattro studi esaminano autonomia, competenza, relazione e comandi intuitivi; riportano associazioni fra autonomia/competenza percepite e gradimento del gioco.

**Applicazione proposta:** scelta reale di direzione/distanza nella palla, effetti comprensibili, uscita libera, traguardi che aggiungono un gesto/possibilità. **Limite:** non stabilisce frequenze ottimali di cura, premi o tempi delle nostre azioni; non giustifica massimizzare il tempo trascorso nella dashboard. I bisogni psicologici dello studio sono distinti dalle tre quantità simulate del cane.

### S3 · Personalità visibile e oggetti — Bandai, Tamagotchi Uni

[How to play, sito ufficiale](https://tamagotchi-official.com/us/series/uni/howtoplay/). Il prodotto presenta personalità attraverso azioni/reazioni e oggetti con cui il personaggio interagisce.

**Applicazione proposta:** un temperamento iniziale affettuoso e curioso, espresso in pochi gesti; una palla o cuccia sbloccata deve aggiungere una risposta osservabile. **Limite:** riferimento di prodotto, non studio di efficacia. Non trasferiamo automaticamente evoluzioni, economia online, castighi o coefficienti di cura; aspetto stabile e tre bisogni restano il perimetro candidato.

## 3. Come scegliere il comportamento

### S4 · Utility e inerzia — David “Rez” Graham, Game AI Pro, 2013

[An Introduction to Utility Theory](https://www.gameaipro.com/GameAIPro/GameAIPro_Chapter09_An_Introduction_to_Utility_Theory.pdf), soprattutto §§9.6–9.7. Confronta azioni tramite punteggi; discute scelta fra candidati migliori e inerzia/cooldown per evitare oscillazioni.

**Applicazione proposta:** prima filtri e priorità rigide, poi piccolo selettore dei gesti ambientali. Una richiesta di cibo può dominare uno sguardo curioso; varietà solo fra gesti compatibili, impegno minimo e pausa dopo la ripetizione. **Limite:** non randomizzare urgenti, input, premi o regole di cura; le durate candidate di SmartPC non vengono dal libro.

### S5 · Intenzione, esecuzione e adattamento — Michael Ramsey, 2013

[A Control-Based Architecture for Animal Behavior](https://www.gameaipro.com/GameAIPro/GameAIPro_Chapter44_A_Control-Based_Architecture_for_Animal_Behavior.pdf). Tratta animali virtuali con obiettivi e comportamento adattato a un ambiente variabile, usando World of Zoo come esempio.

**Applicazione proposta:** “vuole raggiungere la cuccia” deve diventare un percorso consentito dalla geometria attuale. Se lo spazio cambia, interrompere/raccordare in modo coerente. **Limite:** la nostra scena iniziale non richiede una simulazione animale generale, un sistema di controllo biologico o un planner spaziale complesso.

### S6 · Separare decisioni e animazione — Bobby Anguelov, 2015

[Separation of Concerns Architecture for AI and Animation](https://www.gameaipro.com/GameAIPro2/GameAIPro2_Chapter12_Separation_of_Concerns_Architecture_for_AI_and_Animation.pdf), §§12.4–12.6. Distingue logica di gioco, controller d'animazione e animazione; le loro transizioni e durate non coincidono necessariamente.

**Applicazione proposta:** comando semantico → adattatore visuale → rig/clip, con esito identificato. Compatibilità dei piccoli gesti dichiarata; nuova clip/tema non cambia i premi. **Limite:** riprendiamo la separazione, non la complessità dell'architettura di un gioco AAA.

## 4. Input, attenzione e movimento

### S7 · Focus e ritorno prevedibile — Google, Android TV

[TV navigation](https://developer.android.com/training/tv/get-started/navigation), sezioni D-pad, focus e Back. Raccomanda controlli raggiungibili, focus chiaramente percepibile e ritorno prevedibile.

**Applicazione proposta:** modalità Azioni evidente, selezionato distinto da “in corso”, focus ripristinato dopo uscita/avviso. **Limite:** SmartPC usa la propria shell e il tastierino 3×3; non adottiamo il routing Android né modifichiamo i tasti globali.

### S8 · Ridurre il movimento senza perdere la funzione — W3C

[Understanding WCAG 2.2, SC 2.3.3 Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html). Il criterio AAA distingue animazione non essenziale e funzionalità/informazione essenziale.

**Applicazione proposta:** in Reduced/Off restano cura, scelte della palla ed esiti comprensibili; pose e testo possono sostituire gesti decorativi. **Limite:** riferimento di progettazione dal web, non dichiarazione di conformità WCAG della dashboard nativa. Non basta nascondere il cane lasciando andare timer e azioni.

## 5. Disegno, animazione e produzione AI

### S9 · Recitazione leggibile — Walt Disney Animation Studios

[Animation, processo ufficiale](https://www.disneyanimation.com/process/animation/). Descrive timing, messa in scena, anticipazione, movimento successivo e azioni secondarie nella costruzione della personalità.

**Applicazione proposta:** ogni risposta ha preparazione, gesto principale e assestamento; nella presenza compatta occhi/testa/coda comunicano prima dei dettagli. **Limite:** principi artistici, non prova prestazionale. Le durate e il grado di deformazione vanno scelti per stile A e dimensione reale.

### S10 · Parti e deformazioni 2D — Esoteric Software, Spine

[Mesh attachments](https://esotericsoftware.com/spine-meshes). Spiega immagini deformabili mediante mesh/ossa e compromessi di vertici, pesi e area trasparente.

**Applicazione proposta:** parti sovrapposte con pivot puliti per i gesti piccoli; deformazione limitata solo dove serve, evitando grandi immagini quasi vuote. **Limite:** non scegliamo Spine come dipendenza. La sua documentazione non dimostra che una mesh generata dall'AI sia pronta, né che ogni calcolo del rig venga eseguito dalla GPU.

### S11 · Interpolazione generativa — Xing et al., ToonCrafter, 2024

[Paper originale](https://arxiv.org/abs/2405.17933) e [pagina degli autori](https://doubiiu.github.io/projects/ToonCrafter/). La ricerca affronta interpolazione cartoon, movimenti non lineari e occlusioni; usa informazioni oltre alla semplice fusione di due immagini.

**Applicazione proposta:** per le clip AI progettare pose chiave, percorso e parti che diventano visibili; verificare identità/appoggio lungo tutta la clip. **Limite:** ToonCrafter non è uno strumento assunto disponibile in questa chat e non è selezionato per produzione. Il paper non qualifica il generatore che useremo. Generazione in chat e riproduzione locale restano fasi distinte; nessuna generazione video sul dispositivo durante l'uso.

## 6. Rendering e salvataggio

### S12 · Budget del frame e caricamento — Qt Quick 6.8

[Performance Considerations](https://doc.qt.io/qt-6.8/qtquick-performance.html), Timing/Profiling/Images; [Scene Graph](https://doc.qt.io/qt-6.8/qtquick-visualcanvas-scenegraph.html), render loop. Qt descrive il budget di circa 16 ms a 60 FPS, lavoro asincrono, profiling, caricamento immagini e rendering separato dalla GUI dove supportato.

**Applicazione proposta:** texture dimensionate/preparate, I/O fuori GUI, snapshot discreti, backend/render loop verificati sul dispositivo. **Limite:** né C++ né un thread separato certificano fluidità o assenza di blocchi; non impostare variabili del renderer senza prova.

### S13 · Animator e sprite — Qt Quick 6.8

[Animator](https://doc.qt.io/qt-6.8/qml-qtquick-animator.html): può animare il scene graph sul thread di rendering; la proprietà QML viene aggiornata alla fine. [AnimatedSprite](https://doc.qt.io/qt-6.8/qml-qtquick-animatedsprite.html): riproduce frame preparati; l'interpolazione è fusione tra immagini; `frameSync` lega l'avanzamento ai frame disegnati; `finished` non arriva semplicemente impostando `running=false`.

**Applicazione proposta:** Animator per trasformazioni decorative indipendenti; separare coordinate semantiche e visuali. Per le clip preferire timing temporale, annullamento esplicito e controllare eventuale immagine doppia con blending. **Limite:** 60 frame presentati non equivalgono a 60 pose disegnate diverse; blending non genera nuovi appoggi delle zampe.

### S14 · Atomicità e durata dei dati — SQLite

[Atomic Commit in SQLite](https://www.sqlite.org/atomiccommit.html). Descrive commit atomico, costo dell'I/O e assunzioni su filesystem/flush/hardware.

**Applicazione proposta:** stato, premio ed esito in una transazione; un writer fuori GUI; checkpoint radi e recupero esplicito. **Limite:** non disattivare sincronizzazione per ottenere FPS; “commit confermato” e “resiste a un taglio di alimentazione reale” sono verifiche diverse.

## 7. Integrazioni concrete della proposta SmartPC

Le righe seguenti sono **nostre scelte progettuali proposte**, ispirate alle fonti; non risultati misurati o comportamenti già approvati.

| Area | Aggiunta alla base | Riferimenti | Dove si specifica |
| --- | --- | --- | --- |
| Personalità | Temperamento stabile, umore variabile; saluto e risposta alla cura riconoscibili. | S1, S3, S9 | Specifica §7 e §11. |
| Cura | Frase/gesto che spiegano il bisogno; simulare anche assenza e sessioni brevi. | S2, S3 | Specifica §4 e §12. |
| Autonomia | Selezione leggera di gesti leciti; pause, inerzia e varietà controllata. Non si nutre da solo. | S4, S5 | Specifica §9.1. |
| Progressione | Sblocchi osservabili e catalogo piccolo; nessun premio da permanenza/pressioni ripetute. | S1, S2, S3 | Specifica §7. |
| Input e avvisi | Focus conservato; reazioni brevi, compatibili con il contesto, nessun movimento per urgente. | S6, S7, S8 | Specifica §3 e §8. |
| Animazione | Partitura dei gesti, combinazioni consentite, pose/raccordi e contatti verificabili. | S6, S9, S10 | Specifica §11. |
| Asset AI | Master + parti + clip; controlli su identità, giunture, occlusioni e loop. | S10, S11 | Specifica §11. |
| CPU/GPU | QML/Qt per visuale, Python per stato lento, C++ mirato dopo profiling; niente controller Python per frame. | S12, S13 | Specifica §9.2. |
| Recupero | Esiti idempotenti, watchdog per callback mancante, salvataggi fuori GUI. | S6, S13, S14 | Specifica §10. |

## 8. Studi da fare sul nostro prodotto

| Studio futuro | Confronto / osservazione | Decisione da prendere |
| --- | --- | --- |
| Giornata di cura | Parametri attuali contro profilo più lento; due/tre visite brevi, gioco ripetuto, una cura saltata, assenza di 24 h. | Frequenza desiderata e tempo reale da dedicare, senza assumere che “attivo” significhi visite ogni pochi minuti. |
| Espressività | Stessi bisogni con sola posa contro posa + breve anticipazione/risposta; dimensioni ambientali e dedicate. | Quali gesti si capiscono davvero; nessuna statistica generalizzata da una preferenza personale. |
| Gesti autonomi | Durata/intervalli e due bisogni quasi uguali; seed ripetibile. | Nessuna oscillazione, nessuna fame nascosta da una festa casuale, nessuna interruzione continua. |
| Palla/focus | Sequenza completa col tastierino, urgente a metà, ritorno e Reduced/Off. | Chiarezza della selezione, uscita e rapporto fra scelta ed effetto. |
| Produzione AI | Un master, un gesto a parti e una clip di passo/recupero. | Giunture, identità e zampe credibili prima di produrre tutto il catalogo. |
| Prestazioni | Idle trasformato, passo a clip, cambio vista/asset a freddo, banner e carichi consentiti. | Distribuzione intervalli/scatti e ritardo input; distinguere frame software e risposta fisica. |
| Robustezza | Timeout visuale, callback duplicata/tardiva, crash durante scrittura, errore storage, orologio e reboot. | Effetti una sola volta, uscita sempre possibile, recupero senza azzeramenti silenziosi. |

La ricerca **rafforza il 2D ibrido** come prima ipotesi coerente con gli asset AI e con Qt già presente; è una valutazione progettuale, non un confronto sperimentale vinto. Restano da concordare ritmo, assenza/riposo, sblocchi, nome/master e collocazione. La prima prova tecnica dovrà decidere se bastano parti Qt o se una deformazione nativa mirata migliora abbastanza il risultato da giustificarne il costo.

## 9. Cosa questa ricerca non chiude

Nessuna frequenza “scientificamente corretta” per alimentare il cane, nessun 60 FPS garantito, nessuna garanzia di coerenza degli asset AI. Non introduce dialogo, voce, riconoscimento dell'utente, inferenza NPU o apprendimento del carattere nella v0.11. La continuità locale di identità/legame resta distinta dalla memoria narrativa e dal planner della v0.12.
