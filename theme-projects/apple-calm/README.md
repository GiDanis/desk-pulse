# Apple Calm 1.6.5

**Installata con core0.10.0-rc.2 / API2.13:** icona Acquario dedicata, glifi precedenti identici, geometria/font/palette conservati. [Chiusura e ricevuta](../../dashboard/design/v010-aquarium-completion-report.md).

**1.6.4 / core 0.9.4-rc.1:** orario persistente nella barra, tramite `ShellContext.clock` (Theme API 2.12); gli stati Quiete/Ripristino usano una seconda riga nello stesso spazio. [Verifiche e consegna](../../dashboard/design/v094-header-clock-report.md).

Tema per SmartPC a 960 × 640, palette Giorno/Notte, 61 superfici proprie più scena Base. Consegna storica: revisione **1.6.3 installata e selezionabile** sulla Orange Pi con **SmartPC 0.9.0-rc.19 / Theme API 2.11**; Base resta attivo. Grafici nascosti sospesi e ripresa/assenza dei dati corrette, senza modificare font, palette, icone e layout approvati. Il core rende visibili i temi bloccati con diagnostica e verifica isolata. Matrici PC/ARM da 1.098 casi e prove EGLFS superate; soak del core finale e supplemento del bundle finale hanno perimetri distinti. [Consegna corrente e limiti](../../dashboard/design/apple-calm-recovery-performance-report.md), [storico delle revisioni](CONSEGNA.md).

- `bundle/`: unico payload installabile corrente, con 61 superfici proprie e fallback Base per la scena.
- `design/icon-source.json`: unico sorgente modificabile dei 61 glifi vettoriali e delle loro associazioni semantiche.
- `tools/generate_icons.py`: genera metadati e un solo atlante PNG condiviso. QtSvg serve soltanto sul PC di authoring; il dispositivo legge PNG con la propria installazione Qt.
- `tools/blueprint/` e `tools/assemble.py`: strumenti storici con blueprint1.6.1, da riallineare prima di rigenerare l’intero bundle corrente. Per la1.6.5 sono stati rigenerati soltanto i due asset iconici esistenti e aggiornate le versioni dei manifesti; nessun nuovo percorso richiede modifica dell’inventario. Il bundle corrente e il delta verificato sono il riferimento.
- `tools/verify_optimization.py`: confronto con dati reali in cache e provider isolati; verifica nomi, identità, riuso dei dettagli e nuova vista Orologio.
- `tools/verify_main.py`: Main reale, corpus canonico, palette, ingrandimento testo, azioni, scroll, pallini, Normale/Ridotto/Disattivo.
- `tools/verify_board.sh`: collaudo EGLFS completo; usare uno stage persistente sotto `/var/lib/smartpc-dashboard`, con core diagnostico e copia della cache sportiva.
- `tools/install_board.sh`: aggiornamento verificato con backup della transazione e ripristino automatico in caso di errore.
- `evidence/`: risultati della consegna corrente e baseline di confronto. Consultare `CONSEGNA.md` per esito e limiti delle prove.

Il costo della stagione sportiva non viene ripetuto per selezionare una squadra. Le liste pubblicano soltanto i record pertinenti; il riepilogo Motorsport usa i metadati degli eventi e carica risultati, giri e soste nel dettaglio; i contesti nascosti si sospendono e si riallineano prima della presentazione. Gli overlay conservano al massimo sei renderer, distinti per superficie e identità del tema; un cambio revisione invalida la cache e rilascia le lease.

La pagina precedente resta presentata finché la destinazione è pronta. Le pagine pronte vengono presentate subito; il cambio viene accompagnato dal movimento dei pallini. Selezione, dati e schede non avviano dissolvenze della pagina. I pallini centrali seguono gli argomenti; quelli laterali seguono le viste della pagina o le schede del dettaglio aperto. Le macroaree sono sei; Sport alterna Serie A, La mia squadra, F1 e MotoGP; 5 apre l’elenco della giornata, il club o il GP; calendari e classifiche rimangono nel Menu contestuale. Nel cambio gruppo si riallineano senza attraversare posizioni inesistenti. Le transizioni di navigazione/ingresso usano fade da 100 ms e rispettano Movimento ridotto/Disattivo secondo la policy comune. Le urgenze hanno priorità e nascondono la shell.

La vista Oggi → Orologio usa numeri grandi e meteo compatto, senza riempire spazi con eventi inesistenti. Il tema non contiene leggende permanenti del tastierino; la guida rimane nel Menu.

Il manifesto usa `retention: latest`. La pulizia avviene solo dopo l'attivazione e tre heartbeat coerenti: conserva la revisione attiva, protegge eventuali lease ancora vive e usa Base per il recupero. Rimuove le revisioni precedenti di Apple Calm e i loro override, senza toccare i dati dei provider o gli altri temi.

Le misure azione → callback `frameSwapped` attestano il comportamento software osservato sul dispositivo. Non sono latenza ottica, tempo GPU o prova del tastierino fisico. I dati delle verifiche sono sintetici oppure cache reali isolate, con rete negata.

I sorgenti della consegna comprendono il core aggiornato e la patch relativa alla baseline Casa. I file hash e le prove native restano separati dalla misura dei provider live. Lo stage di installazione deve essere persistente: `/tmp` viene svuotato al reboot della scheda.
