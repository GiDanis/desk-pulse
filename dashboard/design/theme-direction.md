# Direzione grafica — concept v1

Questa tavola è una proposta esplorativa per allineare le schermate di SmartPC. Riprende la home QML già presente e prova a estenderne lo stesso linguaggio a Meteo, Eventi e Compagno. Non è ancora una specifica definitiva né un asset pronto per il runtime.

## Identità visiva

- **Base:** fondo navy scuro (`#101923` nell'interfaccia attuale), testo caldo chiaro e secondari blu-grigio.
- **Accento principale:** verde acqua (`#6de0be` nel QML attuale), usato per selezione, stato attivo, piccoli indicatori e dettagli del marchio.
- **Colori di stato:** giallo per sole/attenzione, azzurro per pioggia/freddo, rosso solo per urgenze. Il colore va accompagnato da testo o icona.
- **Struttura:** intestazione e regola superiore comuni, un contenuto dominante per schermata, righe sottili e navigazione in basso.
- **Tipografia:** orario e dato principale grandi; etichette brevi e leggibili a distanza; evitare microtesto sul pannello da 3,5″.
- **Movimento:** microtransizioni e animazioni 2D brevi. La scena deve restare leggibile anche quando è ferma.

## Schermate rappresentate

1. **Oggi:** orologio dominante, data, breve riepilogo meteo e spazio opzionale per una piccola presenza del Compagno.
2. **Meteo:** condizione attuale in primo piano, tre giorni sintetici e un riepilogo leggibile.
3. **Eventi:** un avviso prioritario con gerarchia chiara e una timeline essenziale.
4. **Compagno:** mascotte e ambiente ridotto a pochi elementi; scena separata dai dati funzionali.

## Regole di coerenza da provare

- Mantenere griglia, intestazione e navigazione comuni tra schermate.
- Dare a ogni schermata un solo elemento visivo dominante.
- Riutilizzare forme, spessori e stile icone; i moduli non devono sembrare applicazioni separate.
- Usare la pixel art per il cane solo se piace come direzione: è una proposta, non una decisione già presa.
- Tenere la mascotte piccola nella Home; riservare la scena illustrata alla pagina Compagno.
- Ridurre ulteriormente luminosità e saturazione in modalità notte senza perdere contrasto.

## Da decidere insieme

- Pixel art oppure illustrazione 2D più morbida per il cane.
- Presenza del cane nella Home o soltanto nella schermata Compagno.
- Navigazione sempre visibile oppure più compatta nelle pagine informative.
- Quanta informazione meteo/eventi mostrare nella Home.

La tavola usa testi e dati dimostrativi: colori, gerarchia e composizione sono il riferimento; contenuti e microcopy andranno sostituiti con dati reali. Ogni nuova scena animata andrà misurata sulla Orange Pi prima di fissare gli effetti definitivi.
