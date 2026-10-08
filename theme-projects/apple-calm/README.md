# Apple Calm 1.3.1

Tema profondo per SmartPC a 960 × 640, con palette Giorno/Notte, orologio dedicato e copertura coerente di Casa, Sport, Meteo, Account, Motorsport e Rete. La revisione **1.3.1** è installata con **SmartPC 0.8.3-rc.2 / Theme API 2.5**, con reboot verificato: barra da 56 px, margini coerenti, Sport esteso al corpo disponibile, liste scorrevoli e metriche iliadbox in panoramica. Palette, font, icone e stile delle card della 1.3.0 sono conservati. Conserva gli import compatibili delle superfici precedenti. [Prove e limiti](../../dashboard/design/v083-space-optimization-report.md), [consegna precedente](../../dashboard/design/v083-implementation-report.md).

- `bundle/`: unico payload installabile corrente, con 59 superfici proprie e fallback Base per la scena.
- `design/icon-source.json`: unico sorgente modificabile dei 57 glifi vettoriali e delle loro associazioni semantiche.
- `tools/generate_icons.py`: genera metadati e un solo atlante PNG condiviso. QtSvg serve soltanto sul PC di authoring; il dispositivo legge PNG con la propria installazione Qt.
- `tools/blueprint/` e `tools/assemble.py`: rigenerano manifesti, registro ed entry point. Dopo una modifica alle icone eseguire il generatore, poi l'assemblatore per aggiornare l'inventario delle risorse.
- `tools/verify_optimization.py`: confronto con dati reali in cache e provider isolati; verifica nomi, identità, riuso dei dettagli e nuova vista Orologio.
- `tools/verify_main.py`: Main reale, corpus canonico, palette, ingrandimento testo, azioni, scroll, pallini, Normale/Ridotto/Disattivo.
- `tools/verify_board.sh`: collaudo EGLFS completo; usare uno stage persistente sotto `/var/lib/smartpc-dashboard`, con core diagnostico e copia della cache sportiva.
- `tools/install_board.sh`: aggiornamento verificato con backup della transazione e ripristino automatico in caso di errore.
- `evidence/`: risultati della consegna corrente e baseline di confronto. Consultare `CONSEGNA.md` per esito e limiti delle prove.

Il costo della stagione sportiva non viene ripetuto per selezionare una squadra. Le liste pubblicano soltanto i record pertinenti; il riepilogo Motorsport usa i metadati degli eventi e carica risultati, giri e soste nel dettaglio; i contesti nascosti si sospendono e si riallineano prima della presentazione. Gli overlay conservano al massimo sei renderer, distinti per superficie e identità del tema; un cambio revisione invalida la cache e rilascia le lease.

La pagina precedente resta presentata finché la destinazione è pronta. Le pagine pronte vengono presentate subito; il cambio viene accompagnato dal movimento dei pallini. Selezione, dati e schede non avviano dissolvenze della pagina. I pallini centrali seguono gli argomenti; quelli laterali seguono le viste della pagina o le schede del dettaglio aperto. Le macroaree sono sei; Sport ha un indice per Calcio, F1 e MotoGP. Nel cambio gruppo si riallineano senza attraversare posizioni inesistenti. Animazione: 140 ms Normale, 80 ms Ridotto, immediata Disattivo. Le urgenze hanno priorità e nascondono la shell.

La vista Oggi → Orologio usa numeri grandi e meteo compatto, senza riempire spazi con eventi inesistenti. Il tema non contiene leggende permanenti del tastierino; la guida rimane nel Menu.

Il manifesto usa `retention: latest`. La pulizia avviene solo dopo l'attivazione e tre heartbeat coerenti: conserva la revisione attiva, protegge eventuali lease ancora vive e usa Base per il recupero. Rimuove le revisioni precedenti di Apple Calm e i loro override, senza toccare i dati dei provider o gli altri temi.

Le misure azione → callback `frameSwapped` attestano il comportamento software osservato sul dispositivo. Non sono latenza ottica, tempo GPU o prova del tastierino fisico. I dati delle verifiche sono sintetici oppure cache reali isolate, con rete negata.

I sorgenti della consegna comprendono il core aggiornato e la patch relativa alla baseline Casa. I file hash e le prove native restano separati dalla misura dei provider live. Lo stage di installazione deve essere persistente: `/tmp` viene svuotato al reboot della scheda.
