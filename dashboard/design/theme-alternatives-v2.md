# Alternative di layout — concept v2

Tre modi di organizzare la Home mantenendo palette e stile neo-retro della dashboard: A Orologio, B Moduli, C Compagno. La tavola è esplorativa: testi e dati sono dimostrativi e alcuni dettagli vanno ricondotti alla mappatura reale del tastierino.

## Vincoli d’uso

- Display 960×640 su diagonale 3,5″: pochi elementi, testo ad alto contrasto e gerarchia leggibile a distanza.
- Interazione tramite tastierino 3×3; niente gesture o controlli che sembrano richiedere touch.
- Mappatura presente nel progetto: 1 Orologio, 2 Moduli, 3 Sistema, 4 Meteo, 5 Sport, 6 Casa, 7 pagina precedente, 8 pagina successiva, 9 diagnostica.
- Le schermate devono mostrare sempre dove ci si trova e dare riscontro visivo breve dopo la pressione di un tasto.

## Valutazione delle alternative

### A — Orologio dominante

**Punto forte:** ottima Home da dispositivo sempre acceso; l’ora si legge subito e resta il centro visivo. Il meteo può stare in una riga compatta.

**Rischio:** nella proposta illustrata il riepilogo di tre giorni e la mascotte sottraggono spazio. Sul display reale ridurrei la Home a ora, data e una sola riga meteo; niente previsioni estese.

**Valutazione:** scelta migliore come schermata iniziale/idle.

### B — Moduli a schede

**Punto forte:** rende esplicito il rapporto tra moduli e tasti 4, 5 e 6. Lo stato di selezione può usare bordo e colore, mentre il numero grande ricorda il comando diretto.

**Rischio:** tre schede con icona, nome, descrizione e badge diventano strette su 3,5″. Ogni scheda dovrebbe avere solo nome, stato essenziale e numero; i dettagli stanno nella pagina del modulo. Le card devono restare indicatori di selezione da tastierino, non fingere pulsanti touch.

**Valutazione:** buona pagina Moduli, secondaria rispetto alla Home.

### C — Compagno in primo piano

**Punto forte:** dà personalità al prodotto e offre un luogo dedicato alle animazioni del cane.

**Rischio:** la scena illustrata compete con ora, meteo e avvisi e può rendere più faticosa la lettura. Anche la versione quieta dovrebbe mantenere i dati essenziali nella fascia superiore e limitare la mascotte a un’area definita.

**Valutazione:** adatta alla pagina Compagno, non alla Home predefinita.

## Direzione consigliata

Combinare le tre proposte per ruolo: **A come Home**, **B come pagina Moduli**, **C come schermata Compagno**. In questo modo il prodotto conserva un’identità visiva unica senza chiedere a una sola schermata di fare tutto.

Usare un focus evidente ma non lampeggiante per il comando appena ricevuto. Lasciare 7/8 alla navigazione sequenziale. Il tasto 9 oggi è Diagnostica: la tavola lo mostra genericamente come “Info”, quindi nella UI va etichettato correttamente oppure la funzione andrà ridefinita in una successiva revisione della mappatura. Evitare che un tasto di debug occupi permanentemente una posizione primaria nella UI finale.

## Regole pratiche da portare nel prossimo mockup

- Home: ora grande, data e un solo stato secondario (meteo oppure prossimo evento).
- Pagina Moduli: tre voci in elenco ampio, attivazione diretta con 4/5/6; selezione mostrata con bordo, accento e nome, non solo colore.
- Pagina Compagno: animazione confinata a un’area; evitare sfondi animati o particelle.
- Footer: mostrare la pagina attiva e suggerimenti dei tasti davvero utili in quel contesto. Evitare di stampare l’intera mappatura in piccolo lungo il bordo.
- Non basare la navigazione su più livelli: un tasto numerico deve portare direttamente alla pagina corrispondente.
