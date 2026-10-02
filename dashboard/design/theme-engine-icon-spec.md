# v0.6.6 — Icone semantiche e renderer sostituibili

**Aggiornamento attuazione v0.6.6:** il piano è implementato nei sorgenti. Contratti effettivi, uso e limiti sono nella [guida del motore](theme-engine-implementation-guide.md); stato dei gate e prove sulla scheda nel [resoconto di migrazione](v066-migration-report.md). Gli snippet di analisi illustrano alternative; per il formato eseguibile usare schema, registry ed esempi distribuiti.
**Revisione 1.0 · 2 ottobre 2026 · proposta tecnica; nessuna icona runtime aggiunta.**

Completa [architettura](theme-engine-construction-spec.md), [risorse/font](theme-engine-risk-review.md), [presentazioni e compagno](theme-engine-presentation-spec.md) e [motion](theme-engine-motion-spec.md). La migrazione Base conserva inizialmente l'aspetto attuale: definire il contratto non impone di aggiungere icone a tutte le schermate.

## 1. Riscontro e decisione

Scansione dei 21 `dashboard/*.qml`: zero dichiarazioni di Image, AnimatedImage, AnimatedSprite, SpriteSequence, Shape e Canvas. Si tratta di un inventario testuale, non di una misura del scene graph. La dashboard usa già simboli testuali, per esempio la stella del preferito in SportTeamOverlay. L'assenza di Image oggi non è un vincolo del futuro renderer.

**Decisione proposta:** un componente `AppIcon` con ID semantico stabile e un catalogo di descrittori, separati dalla tecnologia di disegno. Per il prototipo, piccolo set monocromatico di geometrie QML semplici; icon-font è un backend alternativo supportabile e da confrontare. Immagini locali e atlanti restano ammessi per risorse che li richiedono. Il backend predefinito di un set viene scelto dopo prova di resa/costo sulla board, non dalla sola quantità di file.

Non stabilire la regola "niente SVG/PNG nell'engine": limiterebbe stemmi, illustrazioni, pixel art e skin del futuro compagno senza un vantaggio misurato. Allo stesso tempo, evitare una collezione di URL sparsi nelle viste: la risoluzione delle risorse è centralizzata e il caricamento avviene su necessità.

## 2. Significato e rappresentazione

```text
dato/stato/azione di prodotto → iconId semantico
iconId + icon set + variante + stile → descrittore validato
descrittore → AppIcon → renderer registrato + risorse condivise
```

La presentazione decide se e dove usare l'icona; il tema ne sceglie il set/stile. Il tema non ricava condizioni da titoli/localizzazioni, non cambia azioni e non inventa dati assenti.

| Famiglia di ID proposta | Significato | Regola |
| --- | --- | --- |
| `system.home`, `system.back`, `system.settings`, `system.alerts` | Azione della shell | La mappa tasti rimane quella del controller |
| `status.offline`, `status.stale`, `status.unavailable` | Provenienza/disponibilità | Stati distinti; icona accompagnata dal testo necessario |
| `weather.clear`, `weather.cloudy`, `weather.rain`, `weather.snow`, `weather.fog`, `weather.storm`, `weather.unknown` | Condizione normalizzata | Un adapter di dominio mappa codici verificati, non la stringa description |
| `sport.favourite`, `sport.football` | Simbolo generico di contenuto | Personalizzabile senza cambiare la selezione o la disciplina |
| `motorsport.tyre.*` | Mescola/stato disponibile dal dato strutturato | Etichetta e significato dei colori conservati; assente resta assente |
| Logo squadra/competizione | Identità di un'entità, con entity ID | Risorsa di dominio opzionale, nome/abbreviazione come fallback |

L'elenco è iniziale e ampliabile con namespace. Il validatore distingue ID ignoto richiesto per errore da un asset opzionale non disponibile: il primo genera diagnostica, il secondo usa il fallback dichiarato. Entrambi mantengono leggibilità e spazio coerente.

### Meteo: dati già disponibili e variante notte

[weather.py](../weather.py) conserva già `code` attuale e il `code` di ogni previsione: non serve riscrivere il provider per ottenere i simboli di base. Inserire il mapping codice → condizione/iconId nell'adapter di dominio e coprire tutti i codici supportati/unknown con fixture.

Il payload corrente non richiede/esporta `is_day`. Se una presentazione usa sole/luna, aggiungere una fonte temporale strutturata e gestire il valore sconosciuto; **palette notte e notte meteorologica non sono la stessa cosa**. Una previsione giornaliera non possiede automaticamente una fase giorno/notte. Dato stale mantiene la condizione salvata e la propria età: non mostrare una nuova condizione dedotta dall'ora attuale.

Gli indicatori gomme sono capacità future quando il provider espone il dato necessario. Il Theme Engine non aggiunge implicitamente una sorgente di mescole o un download di stemmi.

## 3. Confronto dei backend

| Backend | Vantaggio | Costo/limite da qualificare | Uso proposto |
| --- | --- | --- | --- |
| Icon-font TTF/OTF outline | Set coerente, un asset, tinta tramite Text, pipeline dei glifi Qt | Nuova famiglia/cache, primo uso dei glifi, metriche e fallback; stile del contorno incorporato nel font | Simboli monocromatici statici; trasformazioni o crossfade |
| Rectangle/Shape/Path QML | Parametri di tinta/spessore/parti; adatto ad animazioni locali e meteo stilizzato | Nodi, geometria/triangolazione e antialiasing; animare il path può aumentare il lavoro | Primo piccolo set semplice; renderer animati e componibili |
| SVG tramite Image | Asset vettoriale editabile con strumenti comuni, più colori | Rasterizzazione alla sourceSize, texture/cache; decoder disponibile da verificare | Icone/illustrazioni statiche più articolate |
| PNG/atlante | Resa controllata, pixel art e multicolore | Decodifica, dimensioni/texture, versioni per scala; atlante può caricare anche regioni inutilizzate | Stemmi, illustrazioni e clip raster |
| Render adapter aggiuntivo | Formati/animazioni future | Modulo, toolchain e budget da qualificare | Estensione del registry, non requisito implementato della v0.6.6 |

Un icon-font evita il decoder di PNG/SVG, **non tutto il costo di preparazione**: font/shaping, generazione dei glifi e cache del renderer restano. Usa la stessa pipeline dei testi, ma una famiglia diversa non riusa magicamente la texture dei caratteri UI. [Qt Text](https://doc.qt.io/qt-6.8/qml-qtquick-text.html#renderType-prop).

Con Shape il backend geometrico può triangolare sulla CPU e ripetere il lavoro quando cambia il path. Per la prima prova preferire geometrie ferme e animazioni su rotazione/traslazione/opacità dei gruppi; morphing vero è una capacità da profilare. Un PathSvg descrive dati di percorso, non interpreta automaticamente un documento SVG completo con tutti i suoi elementi. [Shape Qt 6.8](https://doc.qt.io/qt-6.8/qml-qtquick-shapes-shape.html), [PathSvg](https://doc.qt.io/qt-6.8/qml-qtquick-pathsvg.html).

Image possiede cache e condivisione delle risorse; file diversi non implicano decodifica a ogni frame. Definire sourceSize finita e stabile, preparare prima dell'uso e gestire Ready/Error. Non legare sourceSize a una dimensione animata: la sua variazione può ricaricare/rasterizzare la sorgente. Cache Qt non equivale a un limite di memoria imposto dall'app. [Qt Image](https://doc.qt.io/qt-6.8/qml-qtquick-image.html).

## 4. Contratto AppIcon e catalogo

API pubblica proposta, da implementare:

| Campo | Tipo/semantica |
| --- | --- |
| `iconId` | string, ID semantico |
| `style` | StyleFacade tipizzata live/preview/staging |
| `size` | real in pixel QML, box quadrato riservato indipendente dal caricamento |
| `semanticRole` | Ruolo validato per tinta/contrasto: neutral, action o stato di dominio |
| `active`, `motionEnabled` | Visibilità/autorizzazione della presentazione e policy motion effettiva |
| `accessibleLabel`, `decorative` | Nome di prodotto o esclusione accessibile quando ridondante col testo |
| `status`, `effectiveRendererId`, `revision` | Readiness/esito osservabile; il renderer è diagnostica, non scelta della singola vista |

Icone ordinarie non prendono focus e non gestiscono input: l'azione appartiene al controllo che le contiene. Il nome accessibile viene dal dominio/azione, mai dal carattere PUA o dal nome del file. Un'icona di stato non è l'unica indicazione di offline/urgenza.

Il catalogo descrive per risorsa: iconId/set/versione, rendererId, assetId o componentId, box/area ottica, baseline/inset, policy di tinta, fallback e costo dichiarato. Famiglia/codice del glifo e URL sono dettagli del descrittore; non compaiono nei 21 consumatori. Parametri estesi vengono validati contro il renderer registrato e convertiti in proprietà tipizzate nel suo adapter.

Risoluzione al cambio di iconId, set, variante o revisione: niente slot Python per frame o getter che aprono file. Risorse preparate dall'Appearance transaction; lo snapshot `resolvedAppearance` include anche la scelta delle icone nella stessa revisione logica. Preview riceve il proprio catalogo/stile risolto, senza modificare quello live.

### Personalizzazione nei pacchetti

Campi facoltativi con default `builtin.plain`, all'interno del contratto dell'aspetto:

```json
{
  "iconApiVersion": 1,
  "iconSetId": "builtin.plain",
  "iconOverrides": {
    "weather.rain": "personal.rainOutline"
  }
}
```

`personal.rainOutline` deve essere una risorsa dichiarata e compatibile nel catalogo del pacchetto. Nuovi ID di risorsa/set si scoprono dai manifest; nuovo renderer QML entra attraverso una estensione applicativa verificata. JSON non carica una classe QML arbitraria da URL. Il set può cambiare forma, riempimento, spessore, scala ottica e ricetta per i simboli che supportano quei parametri; non è vincolato a una sola font-family per tutto il sistema.

Fallback: override valido → set selezionato con eventuali genitori → set Base distribuito → fallback semplice/text del controllo. La catena è finita e senza cicli. Un asset indispensabile errato blocca il commit candidato; un asset opzionale assente usa il fallback senza far sparire il dato. L'errore rimane osservabile.

Tinta `theme` per simboli ordinari, `semantic` per stati con significato e `original` per risorse identitarie/multicolore. La classificazione semantica appartiene al contratto: il tema non può riclassificare un'allerta come decorazione. Image non espone una tinta universale per SVG/PNG: l'adapter dichiara varianti preparate, shader qualificato o colori originali; non aggiungere un effetto grafico per ogni icona come automatismo.

## 5. Icon-font: regole specifiche

- Un font dedicato con file/versione/licenza e tabella iconId → codepoint; nessun carattere PUA literal sparso nel QML. Codice del glifo stabile solo all'interno della versione del set.
- Registrazione su necessità attraverso il font registry condiviso; verificare famiglia effettiva e presenza dei glifi richiesti, senza accettare tofu o un simbolo estraneo di un fallback di sistema.
- Metriche ottiche controllate: advance/baseline del Text non sono automaticamente il box visibile. Testare centratura, padding, clipping e bordi sottili sul display reale.
- Glifo monocromatico come caso iniziale; multicolore o varianti di contorno non sono proprietà universali di un TTF. Font variabile/color-font richiede capacità e prova specifiche su Qt board.
- Animazione del glifo come oggetto è possibile; per parti indipendenti o morphing tra forme serve un renderer capace. Cambiare codepoint non realizza automaticamente un morph vettoriale.
- Rigenerazione/subset di un set sul PC durante authoring/build, mai nel percorso di animazione del kiosk. Rispetto della licenza del set e degli asset derivati.

## 6. Immagini, identità e compagno

Stemmi e illustrazioni preservano i colori propri quando necessari. Il nome della squadra resta disponibile con logo assente/offline. Un eventuale modulo di acquisizione/cache delle immagini è lavoro separato: Theme non avvia fetch in onCompleted e non introduce dipendenze di rete per le icone di base.

Il compagno non viene ridotto a un AppIcon. SceneHost conserva identità/azione/checkpoint; CompanionRenderer visualizza la skin e può usare parti QML, atlante o altri adapter. AppIcon può mostrare un simbolo statico del compagno nei menu, senza possedere la macchina comportamentale.

AnimatedSprite visualizza frame di una stessa immagine e SpriteSequence gestisce sequenze: evitare un URL diverso per ogni fotogramma. Gli atlanti hanno comunque memoria e limiti di dimensione, da qualificare sulla GPU; un unico file enorme non è automaticamente migliore di più asset preparati. [AnimatedSprite](https://doc.qt.io/qt-6.8/qml-qtquick-animatedsprite.html).

Set/icona animata dichiara posa statica, Reduced/Off, interrupt e fallback. Nessuna ricetta impone un loop continuo: in idle l'icona resta ferma salvo scelta ambientale esplicita, si sospende quando non visibile e non compete con un urgente. Clock/policy QML, nessun Python per frame.

## 7. Migrazione e gate

1. **T0:** confermare inventario; Base conserva testo/geometrie/font attuali e non guadagna nuove icone implicitamente.
2. **T1:** definire catalogo/API/fallback, un simbolo sistema e una condizione meteo, usati nel prototipo/preview. Confrontare geometria QML e glifo equivalente per resa/costo, usando asset licenziati; qualificare disponibilità dei moduli necessari sulla Qt board.
3. **T2/T3:** usare AppIcon dove la presentazione lo richiede; mapping da code meteo e stati di prodotto. Set alternativi non cambiano provider, input o semantica. Provare almeno una sostituzione di backend senza modificare la vista.
4. **T4/T5:** import/override, preview isolata, errori e swap ripetuti, fallback offline e memoria di picco/plateau.

| Prova | Risultato richiesto |
| --- | --- |
| IconId ignoto/glifo mancante/asset errato | Diagnostica e fallback leggibile; nessun crash/tofu silenzioso |
| Meteo code sconosciuto, stale e giorno/notte ignoto | Nessuna condizione inventata, età e testo coerenti |
| Palette giorno/notte e luminosità | Contrasto e riconoscibilità fisici, box senza clipping |
| Backend/tema cambia durante motion | Stato finale corretto; nessuna variazione di input/selezione |
| Preview e cancel | Catalogo/stile live invariati; risorse obsolete rilasciate quando non usate |
| Cold/warm e ripetizioni dello stesso simbolo | Separare creazione, glyph/geometry/decoding, upload e cache condivisa |
| 100 swap e contenuto rappresentativo | Picco e plateau entro budget misurato; scene comprese |
| Immagine non disponibile o renderer non supportato | Dato testuale leggibile; commit/fallback secondo indispensabilità |

Misure prestazionali su EGLFS/A733: carico identico, numero/dimensioni dei simboli dichiarati, animazioni reali e risorse osservabili. Il conteggio dei file e l'assenza di decoder immagini non certificano i 60 fps. Nessun asset definitivo deve essere scelto per poter iniziare T0.
