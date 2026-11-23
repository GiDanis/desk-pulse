# Apple Calm v0.10.2 · seconda passata grafica

29 ottobre 2026 · revisione 2 · studio e tavole di proposta, senza attuazione sul runtime.

La dashboard può migliorare ancora lavorando su **gerarchia, composizione e nitidezza**. La proposta è mantenere l’identità Apple Calm e combinare card dove raggruppano informazioni con superfici aperte dove conta confrontare righe e numeri. Il risultato non richiede nuovi effetti permanenti o un cambio di palette.

Questo documento estende l’[analisi di leggibilità e notifiche](v0102-apple-calm-readability-analysis.md). Il formato confermato dall’utente è **3,5″ in orizzontale**: nelle tavole larghezza × altezza = **960 × 640 px**. La grandezza delle anteprime in chat non certifica la lettura sul pannello.

Il successivo [audit dei dati](v0102-apple-calm-data-audit.md) ha allineato la tavola Meteo al contratto effettivo: tre giorni datati, massima/minima e probabilità massima giornaliera. Il [piano completo](v0102-apple-calm-implementation-plan.md) fissa ora scelte, dipendenze e criteri di accettazione.

## 1. Altri interventi utili

| Intervento | Proposta concreta | Dove serve |
| --- | --- | --- |
| Ridurre la frammentazione | Una card per un gruppo semantico; separatori sottili nelle liste. Eliminare bordi ripetuti su ogni dato passivo. | Timing, menu, storico rete, finestre Account. |
| Dare priorità al dato | Numero principale, etichetta e fonte su tre livelli; dettagli secondari nella vista dedicata. | Meteo, quote, traffico e temperature. |
| Stabilizzare le colonne | Stesse posizioni per nomi, unità, tempi e distacchi; spazio riservato ai valori mancanti. | F1/MotoGP, Calcio e dispositivi. |
| Migliorare la tipografia | Stessa famiglia e pesi coerenti; cifre tabulari dove supportate; niente riduzione automatica del testo per riempire una riga. | Tutte le viste. |
| Ridurre la densità del Menu | Tre voci generose quando quattro diventano strette al 110%; selezione e accesso alle altre voci con i comandi esistenti. | Menu e sotto-menu. |
| Uniformare le icone | Dimensione ottica, peso e distanza dal testo comuni; simbolo di categoria e testo dello stato distinti. | Header, menu, Casa e notifiche. |
| Rendere leggibili i grafici | Più larghezza al tracciato, pochi riferimenti, unità esplicite e legenda stabile; niente curve che inventino valori intermedi. | Storico Rete e grafici Gioco pertinenti. |
| Migliorare la profondità | Superfici piene, distanza e sovrapposizione coerenti; ombra locale soltanto sul livello che si solleva. | Notifiche e pannelli temporanei. |
| Rendere chiari i dati parziali | Trattino e descrizione di indisponibilità; buchi visibili nelle serie; valore precedente etichettato. | Meteo, Rete, Casa, Account e timing. |
| Curare la risposta | Focus immediato e stabile, animazione breve facoltativa; stessa posizione finale dopo Ridotto/Off. | Liste, selezione e apertura dei pannelli. |

Queste sono opportunità progettuali, non difetti tutti dimostrati sulla board né benefici prestazionali già misurati.

## 2. Riscontri aggiuntivi nei sorgenti

- `Label.qml` arrotonda già la dimensione del font alla scala corrente. Non serve duplicare questa logica. La posizione finale dei singoli elementi e delle trasformazioni va invece verificata sulle viste interessate.
- `Rows.qml` prevede già capacità e scorrimento della selezione. Usa titolo 30–34 px, dettaglio 26 px e bordo anche sulle righe non selezionate: il primo intervento è rendere più coerente il componente, non ricostruire i controller di ogni lista.
- `NetworkHistoryChart.qml` rispetta già `breakBefore` e valori nulli, distingue le due serie e ridisegna su dati/palette/visibilità. Sono comportamenti da conservare. Migliorare la grafica non deve riportare il Canvas a un ridisegno continuo.
- `AccountPage.qml` separa già le finestre temporali e mostra il dato utilizzato. Il concept confronta una presentazione del residuo: è una scelta di prodotto da esplicitare, con etichetta coerente e conversione soltanto quando il dato è disponibile e valido.
- Il generatore delle icone usa celle di 48 px in un atlante locale. Prima di aumentare la risoluzione globale, confrontare le icone problematiche alla dimensione effettiva; un atlante più grande non assicura maggiore leggibilità.
- Il Menu corrente contiene Comandi, Impostazioni, Informazioni e Diagnostica, più voci contestuali. Le nuove tavole usano queste quattro funzioni e non introducono nuove destinazioni.

Riferimenti: [Label.qml](../../theme-projects/apple-calm/bundle/qml/Label.qml), [Rows.qml](../../theme-projects/apple-calm/bundle/qml/Rows.qml), [grafico](../../theme-projects/apple-calm/bundle/qml/NetworkHistoryChart.qml), [Account](../../theme-projects/apple-calm/bundle/qml/AccountPage.qml), [generatore icone](../../theme-projects/apple-calm/tools/generate_icons.py), [Main.qml](../Main.qml).

## 3. Ricerca applicata

| Fonte primaria | Indicazione pertinente | Decisione per questa proposta |
| --- | --- | --- |
| [Apple HIG · Layout](https://developer.apple.com/design/human-interface-guidelines/layout) | Raggruppare elementi collegati, allineare e lasciare spazio alle informazioni essenziali. | Usare allineamento e spazio prima di aggiungere contenitori; dimensioni locali per SmartPC, senza copiare le misure tvOS riportate nella stessa pagina. |
| [Apple HIG · Charts](https://developer.apple.com/design/human-interface-guidelines/charts) | Il dato deve prevalere su assi e struttura; in ambienti compatti sfruttare la larghezza del grafico. | Grafico Rete ampio con poche linee guida e unità vicino al titolo. |
| [Apple HIG · Color](https://developer.apple.com/design/human-interface-guidelines/color) | Significato del colore coerente; informazione essenziale accompagnata da simbolo o testo. | Blu per interazione, colore di attenzione per dato precedente o avviso; testo esplicito per gli stati. |
| [Heer e Bostock · CHI 2010](https://homes.cs.washington.edu/~jheer/files/2010-MTurk-CHI.pdf) | Gli esperimenti confrontano codifiche spaziali, dimensioni e griglie. La posizione su scala comune risultava più accurata di angolo/area nei compiti esaminati. | Per quote e confronto di valori: numeri e barre allineate, anziché aggiungere anelli decorativi. È un’inferenza progettuale; lo studio non certifica queste viste o la misura ottimale sul nostro display. |
| [Qt 6.8 · Text](https://doc.qt.io/qt-6.8/qml-qtquick-text.html#renderType-prop) | `QtRendering` e `CurveRendering` sono accelerati; qualità, costo e memoria differiscono. `NativeRendering` usa il percorso della piattaforma. L’hinting documentato si applica al percorso nativo. | Confronto locale di testo piccolo e orologio grande prima di cambiare renderer. Nessun interruttore globale sulla fiducia. |
| [Qt 6.8 · Shape](https://doc.qt.io/qt-6.8/qml-qtquick-shapes-shape.html) | Esistono renderer diversi per i path; la rappresentazione richiesta e quella effettiva possono differire secondo il backend. | Possibile banco per grafici o simboli specifici. La richiesta di un renderer non prova qualità o velocità sulla PowerVR. |
| [Qt 6.8 · Performance, immagini](https://doc.qt.io/qt-6.8/qtquick-performance.html#images) | Dimensioni delle risorse, caricamento e composizione a runtime incidono su memoria e reattività. | Asset locali adeguati alla misura; ombre precomposte dove convengono; niente caricamenti o rigenerazioni per frame. |

Le fonti sostengono i principi. La scelta fra le due composizioni, il numero di righe e il beneficio sulla board richiedono prove del nostro prodotto.

## 4. Due composizioni, da combinare secondo la vista

### Card raggruppate

Mantiene gruppi su superfici piene con raggio coerente e spaziatura. Aiuta a distinguere insiemi diversi: meteo attuale/previsioni, dispositivi e finestre Account. La selezione ha un bordo evidente; i gruppi passivi non hanno bisogno di ombre o cornici forti.

### Superfici aperte

Riduce i riquadri attorno a informazioni già organizzate in colonne. Il focus rimane una superficie distinta, le altre righe usano separatori sottili. Favorisce la continuità visiva di timing, storico e menu.

**Scelta consigliata:** card per Meteo/Casa e pannelli temporanei; superfici aperte per F1/MotoGP, grafici e liste omogenee. Per Account il piano consolidato sceglie due finestre confrontabili con il residuo come dato principale e barra coerente. Le notifiche restano nella direzione Calm essenziale della prima analisi.

Non occorre scegliere una composizione unica per tutte le viste né creare un nuovo tema: sono regole complementari di Apple Calm.

## 5. Sette viste nuove

| Vista | Cosa cambia | Vincolo del dato |
| --- | --- | --- |
| Storico Rete | Grafico ampio, valori principali allineati, legenda continua/tratteggiata, scelta 1 h/24 h. | Le linee si interrompono sui campioni assenti; l’ultimo valore mancante resta «—». Il traffico non è la capacità massima della linea. |
| Meteo/previsioni | Stima attuale dominante, poche grandezze a fianco, tre giorni datati con simbolo, massima/minima e probabilità massima. | Il contratto offre tre previsioni giornaliere, non quattro temperature orarie. Probabilità % e precipitazioni mm restano distinte. I simboli non sono una nuova sorgente; sole/luna richiedono dati appropriati. |
| F1/timing | Tre piloti leggibili con posizione/nome/tempo in colonne; selezione riconoscibile. | Tempi e nomi sono demo; «Salvato» non diventa «Live». Per MotoGP usare la stessa struttura quando lo schema del dato lo consente. |
| Casa | Dispositivo, lettura e stato separati; valore precedente con età e testo visibile. | Consultazione: nessun comando domotico viene simulato come eseguito. |
| Account | Due finestre confrontabili, percentuale e barra semplice; stato dello snapshot evidente. | I numeri sono inventati per la tavola. Una percentuale salvata non prova la disponibilità attuale; dato mancante non equivale a zero. |
| Menu | Tre voci grandi con icona e descrizione; le altre raggiungibili tramite scorrimento. | Destinazioni e comandi esistenti, selezione per ID. Nel concept cambia il focus, senza eseguire azioni sul sistema. |
| Icone/stati | Tavola di dimensioni, distanza dal testo e simboli associati allo stato. | È una tavola componenti, non una nuova vista runtime. I simboli Lucide sono riferimenti; la produzione usa il catalogo Apple Calm. |

Il concept esplora la struttura e non fissa una riduzione dei font produttivi. Le dimensioni esistenti di `Rows.qml` vanno preservate quando offrono maggiore leggibilità; se il testo non entra si riduce il numero di righe. I valori esatti si consolidano nella successiva prova QML a 960×640.

## 6. Nitidezza e uso della GPU: banchi da preparare nell’attuazione

| Banco circoscritto | Confronto | Cosa decide |
| --- | --- | --- |
| Testo UI | Cantarell a 22/24/26/30/34 px, scala 1 e 1,1; QtRendering e NativeRendering, con hinting applicabile. | Leggibilità dei caratteri, interlinea, layout e costo dei testi che cambiano. |
| Orologio | Liberation Sans a 120–140 px; QtRendering normale/qualità superiore e CurveRendering se supportato. | Qualità dei bordi e memoria dei glifi; un percorso GPU diverso non è automaticamente più veloce. |
| Icone | Stessi simboli a 28/32/36 px, atlante corrente contro risorsa mirata a risoluzione diversa. | Peso visivo, margini, aloni e nitidezza. Confrontare risorse equivalenti, senza variare il disegno insieme alla risoluzione. |
| Grafico | Canvas corrente contro path/scene graph soltanto se un costo misurato lo giustifica. | Qualità del tratto e costo di un aggiornamento; conservare buchi, unità e risoluzione della fonte. |
| Focus/rilievo | Bordo/riempimento statici, contro una singola ombra locale precomposta. | Separazione percepibile senza ridisegno permanente. |

I banchi vanno eseguiti su copie isolate con il target Qt/PowerVR pertinente. Le tavole browser non confrontano i renderer Qt, il consumo GPU o la risposta del display. Non si modificano driver, ponte EGL, bypass cache shader o renderer Acquario per ottenere un confronto estetico.

Per il testo, `renderTypeQuality` elevata può consumare più memoria e non è una correzione generale per ogni etichetta. Per le immagini, ingrandire l’atlante in entrambe le dimensioni aumenta l’area dei pixel: scegliere solo le risorse per cui il confronto mostra un beneficio. Non applicare MSAA o layer offscreen a ogni riga della dashboard.

## 7. Priorità pratica

1. **Composizione e liste:** allineamenti, gruppi, unità, font e capacità delle righe. Beneficio grafico valutabile prima di cambiare tecnologia.
2. **Icone e stati:** stesso peso, spaziature e descrizioni; nessun simbolo aggiunto senza significato.
3. **Grafici e timing:** leggenda, griglia, gap, colonne e numeri stabili.
4. **Rilievo e movimento:** un accento locale; mantenere Ridotto/Off e la priorità degli urgenti.
5. **Qualità dei renderer:** solo A/B circoscritti dopo avere una composizione approvata; adozione quando il confronto dimostra il vantaggio.

Le modifiche soltanto visuali possono stare nel bundle; dati mancanti, nuovi stati, raggruppamento e campana globale richiedono i contratti descritti nella prima analisi. Nessuna schermata di proposta aggiunge da sola acquisizione, polling o funzioni di provider.

## 8. Tavole e verifica

Le schermate sono nella [cartella delle tavole](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/). Esempi:

- [Rete aperta](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/network-open-day-100-complete.png) e [card](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/network-grouped-day-100-complete.png).
- [Meteo](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/weather-grouped-day-100-complete.png).
- [F1](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/racing-open-day-100-complete.png).
- [Casa](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/casa-grouped-day-100-complete.png).
- [Account](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/account-open-day-100-complete.png) e [dato mancante](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/account-open-day-100-partial.png).
- [Menu](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/menu-grouped-day-100-complete.png).
- [Icone e stati](evidence/v0102-apple-calm-readability-2026-10-29/refinement/screens/icons-grouped-day-100-complete.png).

La verifica browser, registrata in [review.json](evidence/v0102-apple-calm-readability-2026-10-29/refinement/review.json), copre due composizioni, sette viste, due condizioni dei dati e quattro larghezze al 110%: **112 combinazioni senza sconfinamenti o collisioni rilevate**. Passate **sei interazioni**, inclusi scorrimento del Menu e discontinuità del grafico. Nessun errore JavaScript; **22 nuove catture, tutte 960×640**, comprendenti notte, testo ingrandito e dati parziali. Hash e collegamenti sono registrati nella [ricevuta degli artefatti](evidence/v0102-apple-calm-readability-2026-10-29/refinement/artifact-checks.json). Sono controlli del concept, non della board o del rendering QML.

La ricevuta precedente descrive la prima revisione del concept. Dopo la correzione Meteo sono state riprovate soltanto le **16 geometrie della vista modificata**, aggiungendo il controllo di collisione con il footer e dei contenuti nelle card: tutte passate, senza errori JavaScript. Sei catture Meteo aggiornate, giorno/notte e 110% parziale, portano a **26 PNG complessivi** nella cartella; gli altri contenuti restano invariati. Evidenza: [review-weather-correction.json](evidence/v0102-apple-calm-readability-2026-10-29/refinement/review-weather-correction.json). I primi tentativi del nuovo layout hanno evidenziato collisioni del footer, risolte intervenendo sugli spazi senza ridurre il corpo del testo.

Le precedenti 15 tavole mantengono il proprio perimetro verificato. Le suite runtime dell’audit dati hanno ricevute distinte; non sono state ripetute per la correzione di questo concept. Restano necessari, prima della consegna, i controlli QML pertinenti e la lettura sul pannello fisico indicati nel piano completo.
