# Studio UX e navigazione — proposta v1

> Superata dalla [proposta v2](./ux-navigation-v2.md), che riduce le famiglie e definisce tutti i tasti e gli stati di navigazione.

## Premessa

La testata fissa `SMARTPC / COMPANION` e `MODALITÀ NOTTE` usa circa 84 px verticali prima ancora del contenuto. Il marchio non aiuta a capire dove ci si trova e la modalità notte è deducibile dall’aspetto dello schermo. Per un display da 3,5″ conviene recuperare quello spazio e mostrare solo contesto e controlli utili alla schermata corrente.

## Riferimenti di prodotto

| Prodotto | Schema osservato | Cosa prendiamo | Cosa non copiamo |
|---|---|---|---|
| **LaMetric TIME** | Display informativo a colpo d’occhio, app autonome, pulsante d’azione e tasti sinistra/destra sul dispositivo. La guida descrive pressioni brevi/lunghe e uso dei tasti direzionali durante la modifica. | Poche azioni fisiche coerenti; navigazione visibile e locale al dispositivo; distinzione fra lettura e modifica. | I display e le funzioni sono diversi; la nostra tastiera 3×3 ha più tasti e può supportare una gerarchia più ricca. |
| **Home Assistant** | Dashboard organizzate in viste; le viste contengono sezioni e schede raggruppate per funzione. | Separare destinazioni principali e schermate correlate; raggruppare per ridurre la scansione; usare una vista di dettaglio per un contenuto alla volta. | La griglia flessibile e le molte schede sono pensate per touch e schermi più grandi. |
| **Tidbyt** | Display pixel ambientale che alterna app e informazioni; gestione soprattutto da telefono/voce. | Una Home passiva leggibile a distanza e contenuti brevi; la schermata può restare utile senza interazione. | Non adottare la rotazione automatica come navigazione principale: con tastierino vogliamo controllo prevedibile e nessun cambio pagina inatteso. |
| **DAKboard** | Schermo sempre acceso che combina calendario, foto, meteo e agenda in layout configurabili. | Informazioni quotidiane scelte e ordinate secondo la routine dell’utente. | La densità e il layout da TV/tablet non sono adatti al nostro piccolo pannello; non trasformare ogni pagina in un mosaico di widget. |

### Fonti ufficiali

- LaMetric, [TIME user guide — uso delle app e navigazione](https://lametric.com/sites/default/files/techspecs/2019-12/user_guide.pdf)
- Home Assistant, [Dashboard views](https://www.home-assistant.io/dashboards/views/) e [Dashboard cards](https://www.home-assistant.io/dashboards/cards)
- Tidbyt, [How Tidbyt Works](https://help.tidbyt.com/getting-started-with-your-tidbyt) e [product overview](https://tidbyt.com/)
- DAKboard, [product and display overview](https://dakboard.com/site)

## Modello di navigazione proposto

La UI è organizzata su due assi distinti:

- **Orizzontale = famiglia di funzioni.** Oggi, Meteo, Sport, Casa, PC, Compagno, Sistema.
- **Verticale = viste simili dentro la famiglia selezionata.** Per esempio Meteo: Adesso ↕ Previsioni ↕ Allerte; Sport: Prossimo evento ↕ Live ↕ Calendario; Casa: Panoramica ↕ Stanze ↕ Dispositivi.

Una famiglia con una sola vista non finge di avere pagine vuote. Le destinazioni principali devono restare direttamente raggiungibili; lo scorrimento è un modo di esplorare, non un passaggio obbligatorio attraverso menu annidati.

### Composizione della schermata

1. **Barra di contesto compatta:** famiglia selezionata e vista corrente, con indicatore discreto per elementi vicini. Niente wordmark persistente e niente etichetta “modalità notte”. Altezza indicativa 44–52 px.
2. **Area principale:** un contenuto dominante, con spaziatura generosa. La Home conserva orologio, data e al massimo una o due informazioni utili.
3. **Indicatore di posizione:** per esempio `METEO · 1/3 ADESSO`; mostra il livello e quante viste correlate esistono.
4. **Aiuto tasti contestuale:** in basso mostra solo le azioni disponibili in quel momento, con i numeri del tastierino. Niente legenda completa in corpo piccolo su ogni pagina.
5. **Riscontro all’input:** bordo/riquadro di focus e breve animazione dopo la pressione. Nessuna dipendenza da touch, hover o colore da solo.

Questo recupera spazio dalla testata attuale senza lasciare l’utente disorientato: il nome della famiglia e della vista resta visibile in forma compatta.

## Mappatura tastierino da prototipare

Per rendere i due assi reali, una convenzione classica 3×3 è facile da imparare:

| Tasto | Azione proposta |
|---|---|
| 2 / 8 | Vista precedente / successiva nella famiglia (verticale) |
| 4 / 6 | Famiglia precedente / successiva (orizzontale) |
| 5 | Apri / conferma / seleziona |
| 1 | Vai a Oggi/Home |
| 3 | Indietro o chiudi dettaglio |
| 7 | Avvisi/favorito rapido, da definire |
| 9 | Sistema/impostazioni; diagnostica fuori dal percorso normale |

È una proposta d’interazione, non una rimappatura già applicata. Il progetto oggi usa 1–6 per pagine dirette, 7/8 per pagina precedente/successiva e 9 per diagnostica; prima di cambiare il comportamento va provato un prototipo con tutti i nove tasti. In particolare, va deciso cosa fare con 7 e 9 nell’uso quotidiano e come mantenere il debug accessibile senza renderlo un’azione primaria.

### Regole per evitare disorientamento

- 4/6 cambiano sempre famiglia; 2/8 cambiano sempre vista nella famiglia corrente.
- 1 riporta sempre alla Home; 3 torna al contesto precedente senza perdere la famiglia corrente.
- 5 conferma solo quando esiste un elemento selezionato; non deve attivare azioni irreversibili per errore.
- Ogni pagina indica gli assi con frecce e numeri, per esempio `4 ← METEO → 6` e `2 ↑ ADESSO ↓ 8 PREVISIONI`.
- Per i comandi di casa, richiedere conferma solo alle azioni con effetto fisico rilevante; mostrare uno stato chiaro dopo il comando.
- Gli avvisi prioritari possono comparire come overlay temporaneo; alla chiusura si torna esattamente alla schermata precedente.
- Il display non cambia schermata da solo mentre l’utente sta navigando. Solo la Home può alternare lentamente un riepilogo non interattivo, se attivato.

## Architettura delle famiglie

- **Oggi:** orologio e riepilogo essenziale; Home predefinita dopo inattività.
- **Meteo:** Adesso, Previsioni, Allerte locali.
- **Sport:** Prossimo evento, Live, Calendario/risultati.
- **Casa:** Panoramica, Stanze, Dispositivi. I comandi vanno separati dalla sola consultazione.
- **PC:** stato, attività, eventuali notifiche.
- **Compagno:** scena/stato della mascotte, con contenuto animato confinato e dati funzionali non coperti.
- **Sistema:** connettività, risorse, diagnostica solo quando richiesta.

Le viste non ancora implementate non vanno inserite nel flusso finché non hanno contenuti reali; possono apparire come destinazioni future solo nella schermata Moduli di sviluppo.

## Prossimo ciclo di design

1. Disegnare tre schermate con la barra compatta: Oggi, Meteo/Adesso, Meteo/Previsioni.
2. Provare 4/6 e 2/8 da tastiera desktop, mostrando sempre il focus e l’aiuto contestuale.
3. Provare la stessa navigazione sul tastierino fisico e misurare leggibilità alla distanza d’uso normale.
4. Verificare che ogni destinazione frequente si raggiunga in una pressione o al massimo un passaggio prevedibile.
5. Solo dopo fissare la mappatura fisica e aggiornare QML/keypad.
