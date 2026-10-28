# Gioco — chiusura funzionale della fase v0.9

25 ottobre 2026 · consegna di manutenzione core **0.9.4-rc.3**.

## Decisione e perimetro

L'utente chiede di concludere il modulo Auto nel modo migliore e più semplice per passare a un nuovo modulo. La fase funzionale viene chiusa e il Gioco entra in manutenzione. Si conservano la rosa Maestro/Crono/Memoria/Linea/Tattico, i progressi personali e tutte le modalità già consegnate. Non si avviano altre campagne di apprendimento per questa chiusura.

La ricerca P0–P9 è archiviata come **parzialmente completata, seguito scientifico rinviato**: non equivale a promuovere le reti sperimentali o a dichiarare superati i gate. L'esito negativo delle nuove ricette rimane valido. Il successivo modulo può procedere senza dipendere da questi esperimenti; l'ordine ufficiale Acquario → Compagno → Memoria/AI è conservato.

## Ultima correzione inclusa

La produzione rc.2 chiudeva la gara al più tardi 30 secondi dopo il primo arrivo. Un pilota qualificato più lento poteva quindi essere fermato prima dei tre giri. La nuova finestra è:

`max(30 s, (giro qualificato più lento − più veloce) × giri gara + giro più lento)`.

Il limite complessivo della sessione rimane attivo. Esempio di regressione: qualifiche 23,5 e 35,7 s, gara di tre giri; il vecchio limite interrompe il secondo, la nuova finestra di 72,3 s lo comprende con margine di un giro. Il valore è salvato nelle regole della sessione e usato dal worker. Tempi di qualifica non finiti o non positivi sono rifiutati.

La distribuzione viene derivata dall'esatto manifest installato rc.2, **654 file**, con soli tre file modificati: `game_protocol.py`, `game_worker.py`, `version.py`. Le modifiche di ricerca presenti nel checkout non vengono trasferite in questa consegna. Modelli, premi, fisica, backend di apprendimento, grafica e preferenze conservano le versioni installate.

## Stato del piano P0–P9 alla chiusura

| Parte | Stato acquisito | Trattamento |
| --- | --- | --- |
| P0, menu/Start/pausa | Correzioni installate e prove tecniche documentate. | Manutenzione. |
| P1–P4, diagnosi/riferimenti/ambiente/dataset | Laboratorio e confronti implementati. | Conservati e riproducibili. |
| P5, nuove basi | Cinque preparazioni superano il prerequisito quantitativo di sviluppo; ricetta comune robusta non qualificata. | Ricerca rinviata, nessuna nuova base attivata. |
| P6, affinamento RL | Otto continuazioni e candidati intermedi valutati; primo guadagno sicuro insufficiente rispetto al gate d'attesa. | Ricerca rinviata, nessuna nuova ricompensa attivata. |
| P7, finale scientifico | Non eseguito; banca finale conservata. | Richiesto prima di una futura promozione. |
| P8–P9, nuove reti nella GUI/ARM | Prototipo verificato tecnicamente su copie. | Nessuna consegna dei pesi sperimentali. |
| Chiusura funzionale attuale | Ultima correzione gare e verifica del runtime esistente. | Manutenzione rc.3; distinta dalla release scientifica dei nuovi piloti. |

## Verifica e installazione

**Installata e verificata sulla Orange Pi: core 0.9.4-rc.3, 654 hash conformi.** [Ricevuta](evidence/v094-game-functional-closure-2026-10-25/board/final-receipt.json) · [audit successivo](evidence/v094-game-functional-closure-2026-10-25/board/post-delivery-audit.json) · [indice delle evidenze](evidence/v094-game-functional-closure-2026-10-25/README.md).

- **PC:** sei regressioni della finestra finale e tredici controlli di menu/Start/processi/heartbeat; sedici sessioni dei quattro learner nelle quattro modalità, più gara completa Apple Calm con quattro piloti qualificati, tre giri e quattro arrivi.
- **ARM/EGLFS 960×640:** gli stessi diciannove controlli automatici, quindici sessioni Main/QML complessive nei tre temi; Crono nelle quattro modalità per tema, gare nei tre temi e gara completa Apple Calm con quattro partecipanti, tre giri e tutti arrivati. Tutte le auto rappresentate durante la gara; nessun warning QML. Le prove Base/Functional e i controlli già riusciti sono riutilizzati solo dopo confronto dell'esatto manifest e dei sorgenti: nessuna somma dei tentativi ripetuti.
- **Risultati correnti verificati:** il test finale identifica la nuova sessione nella copia privata, controlla regole/tre giri e stato completo, attende che la classifica esponga lo stesso `raceId` e poi verifica gli arrivi. Una prima cattura leggeva la classifica storica: è conservata ed esclusa. La prima matrice estesa, interrotta manualmente per restringere il collaudo, è conservata separatamente.
- **Dati:** SQLite integro; tabelle, artefatti e preferenze identici al controllo precedente alla consegna. Anche il backup è stato ricontrollato dopo le prove. Nessun reset, training personale o cambio dei pesi.
- **Ripristino:** backup completo `/var/lib/smartpc-dashboard/p0p9-backups/reference-native-20261024-220928`; runtime precedente `/opt/smartpc/dashboard-before-v094-rc3-20261025-193013`.
- **Salute finale:** servizio active/running, `NRestarts=0`, heartbeat fresco del PID GUI corrente; boot ID conservato, nessun reboot OS. Rimossi soltanto i temporanei creati per queste prove, dopo controllo di assenza di file aperti.

Manifest installato: `3218f94083f6d41972bc971a99b75f2e8847f9df96fb1ace4f61b468d71104a3`. La fase funzionale è chiusa ed entra in manutenzione. La candidata core non viene rinominata stabile e i nuovi modelli restano non qualificati.

## Base di partenza per il prossimo modulo

La distribuzione completa con manifest rc.3 è conservata nelle evidenze come `game-maintenance-0.9.4-rc.3.tar.gz`. Questa è la base esatta della manutenzione, riproducibile senza includere i prototipi. Il checkout di lavoro conserva anche codice di ricerca non consegnato: una futura distribuzione deve confrontarsi con questo manifest e includere soltanto le modifiche autorizzate per il nuovo modulo. Il codice sperimentale non va attivato attraverso un packaging ricorsivo indiscriminato del checkout.

## Limiti conservati e criterio di riapertura

Le modalità esistenti restano disponibili, ma **miglioramento continuo, sorpassi competitivi e difesa generale dei learner non sono garantiti**. Nessuna nuova rete è scientificamente qualificata. I test di interfaccia e gli arrivi in gara non sostituiscono la misura dell'apprendimento. CPU per simulazione/apprendimento e GPU per Qt Quick; NPU non attivata. Target grafico 30 Hz; nessuna nuova certificazione di FPS ottici, tastierino fisico, power-cut o uso di ore.

Riaprire il modulo per un difetto riproducibile nell'uso normale o per una nuova richiesta esplicita di ricerca/contenuti. Un'eventuale nuova ricetta richiede ancora confronto con la propria base, sicurezza e sorpassi multigiro, cinque preparazioni della stessa ricetta, banca finale e gare con gli esatti pesi da consegnare. Il modulo successivo non attende questi lavori.
