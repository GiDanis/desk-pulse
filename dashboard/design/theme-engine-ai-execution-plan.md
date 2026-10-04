# Theme Engine — piano per avviare authoring AI e bundle completi

**Revisione 1.3 · 4 ottobre 2026 · Europe/Rome**

**Stato: B0 implementato e collaudato; percorso completo A0–A6 ancora aperto.** [Consegna del bridge e prove](theme-engine-authoring-b0-report.md). Questo piano traduce la [specifica di authoring](theme-engine-ai-authoring-spec.md) in consegne verificabili. Mantiene il [MasterPlan](release-masterplan.md), i cinque riferimenti dello [studio UX](themes-and-ux-analysis.md) e il [contratto notifiche](theme-engine-notification-spec.md). Le decisioni estetiche definitive restano nel prototipo.

**A0.1/A0.2 implementati:** [piano operativo](theme-engine-a0-a1-implementation-analysis.md), inventario di 44 superfici / 30 route, contratti pubblici canonici e tooling; normalizzazione dei dati, tracing e migrazione degli host mantengono la sequenza approvata. I [contratti canonici e il tooling](theme-engine-a0-contracts-report.md) sono consegnati. Tracing e fixture runtime A0.3/A0.4, modulo QML e host A1 restano aperti.

## 1. Baseline e valutazione delle aggiunte

La baseline di preparazione è v0.6.6 con migrazione delle sei superfici Avvisi già consegnata, runtime `b20ca334faac5b9b69c7802928a9dce59d0bacc4`; `c66d9c8` contiene le evidenze successive e `63828c2` l'analisi di authoring precedente. La revisione del piano del 3 ottobre era esclusivamente documentale: [inventario sorgenti](evidence/theme-ai-authoring-analysis-2026-10-03/source-audit.json), [verifiche della revisione](evidence/theme-ai-authoring-analysis-2026-10-03/plan-review.json). Le prove PC/board e la distribuzione B0 del 3–4 ottobre hanno un [resoconto separato](theme-engine-authoring-b0-report.md).

| Aggiunta / dubbio | Valutazione e decisione |
| --- | --- |
| Tool ponte `check` / `install` | Consegnato in B0. Conservare `list`, `validate`, `import`, `export` e la loro compatibilità durante A0/A1 |
| Diagnostica che aiuta l'AI a correggersi | Necessaria: codici stabili, variante e percorso del campo; suggerimenti verificabili, nessuna correzione cromatica silenziosa |
| Prompt singolo JSON | Adatto al profilo schema 1. I visuali nuovi richiedono un progetto di più file e il futuro kit completo |
| Cinque concept | Conservati come suite candidata, non come limite dell'engine. Prima prova con Braun scuro; font/palette finali dopo il prototipo |
| Trasferimento diretto sulla board | `install` consegna nell'inbox; importazione, anteprima e applicazione restano passi distinti. Non confermare «applicato» dopo una copia |
| Font e contrasto | Profilo reale del destinatario e risorse dichiarate. Inter/JetBrains non risultano installati sul PC della verifica; questo non prova la disponibilità sulla board |
| Palette chiare | Nuovo G21: colori warning/critical fissi e accenti usati come testo richiedono ruoli adattivi e controlli sulle superfici effettive |

L'esempio corretto è `#7a7a7a` su `#242424`: **3,616:1**. Il primo grigio più chiaro a 8 bit che supera 4,5 su quella sola superficie è `#8b8b8b`: **4,556:1**. Non è automaticamente una correzione valida sull'intero tema. Il riferimento Braun `#ff5500` su `#ecebe4` vale **2,682:1**; i warning/critical fissi hanno a loro volta contrasto insufficiente su tale superficie. Il checker B0 segnala i rischi conosciuti con una mappa degli usi; A1 sostituirà quella mappa con il grafo condiviso delle coppie realmente usate e migrerà i ruoli nel runtime.

## 2. Decisioni di partenza

- **Due profili:** schema 1 per generare temi con capacità già distribuite; bundle completo per composizioni QML/JS, animazioni, icone e asset nuovi. Il primo non sostituisce il secondo.
- **Stack:** Python/PySide6 per dati, catalogo, verifica e persistenza; Qt Quick/QML per visuali e animazioni. Facade tipizzate; nessun resolver a ogni frame. Nuovo codice nativo soltanto per un limite misurato.
- **Base condivisa:** provider, eventi, router/input e storage funzionale appartengono all'app. I renderer consumano contesti e azioni pubblici versionati. `SmartPC.ThemeApi 2` resta un nome proposto da realizzare.
- **Personalizzazione:** pagine, shell, overlay/dettagli, tutte le sei superfici Avvisi, motion, icone e scene hanno copertura esplicita. Un fallback Base va dichiarato; non si presenta un tema parziale come integralmente ridisegnato.
- **Creazione:** AI sul PC, kit indipendente dal servizio/modello, pacchetto usabile offline. Sul dispositivo: tema, anteprima/applica e pochi adattamenti di palette, testo e movimento.
- **Fiducia:** primo profilo completo per codice visuale dell'autore generato nel progetto locale. QML non è una sandbox. Nessun Python, installer o plugin nativo incluso nel tema.
- **Identità:** ID/versione/digest, revisioni immutabili, precedente disponibile. Il codice testato deve avere lo stesso digest del codice distribuito.
- **Compagno futuro:** attore/stato persistente posseduto dall'app, visuale/asset sostituibili e capacità evolvibili. G20 resta separato dal collaudo del compagno definitivo.

Non occorre decidere adesso tutti i font, le palette o le animazioni. Schemi esatti, API e budget sono risultati dei blocchi tecnici, non decisioni estetiche demandate all'utente.

## 3. Primo blocco B0 — strumenti schema 1 e diagnosi

**Obiettivo:** un'AI genera un tema compatibile con il runtime attuale, riceve errori utili, li corregge e trasferisce i file integri nell'inbox. Il toolkit completo di nuovi visuali viene dopo A1/A2.

### Interfacce ora disponibili per B0

```text
python3 dashboard/theme_pack.py check <cartella_tema_o_theme.json> [--store <catalogo>] [--profile <profilo.json>] [--format text|json]
python3 dashboard/theme_pack.py install <cartella_tema> [--store <catalogo_locale> | --board <destinazione_ssh>] [--format text|json]
```

Per i nuovi comandi, opzioni globali documentate e testate anche dopo il sottocomando; conservare l'invocazione legacy con `--store` globale. Il valore di default locale va derivato con lo stesso metodo del runtime. `--store` e `--board` sono alternativi. I comandi legacy mantengono comportamento e codici di uscita esistenti.

| Unità | Interventi e risultato | Verifica necessaria |
| --- | --- | --- |
| B0.1 · Verifica del progetto | Parser CLI e staging temporaneo in `theme_pack.py`; riuso di `ThemeCatalog`/schema in `theme_core.py`, senza un secondo resolver | File o cartella, ereditarietà, Day/Night, registri, range, chiavi sconosciute/duplicate, asset e hash; store originale intatto anche su errore |
| B0.2 · Diagnostica | Report testuale/JSON con fase, variante, file, JSON Pointer, ruolo, valore e soglia; aggregare errori indipendenti | Errori multipli riproducibili; niente suggerimenti su dati dipendenti invalidi; proposta cromatica rivalidata prima di dichiararla valida |
| B0.3 · Profilo e prompt | Export del contratto e dei registri effettivi; profilo Qt/display/font/capacità del destinatario; prompt schema 1 derivato dagli stessi dati | Nessuna proprietà o presentazione inventata, motion con quattro campi obbligatori, ID/range reali; probe Qt separato dai provider e dalle preferenze |
| B0.4 · Trasferimento | Helper locale/SFTP, directory temporanea, verifica digest, pubblicazione atomica nell'inbox e ricevuta | Transfer interrotto, assenza spazio, conflitto e credenziali errate lasciano corrente/inbox pubblicata integri; niente restart o apply implicito |
| B0.5 · Prova verticale | Un progetto candidato Braun scuro con visuali già disponibili e copertura dichiarata | AI corregge almeno un errore reale; check, trasferimento, import e preview sul destinatario; prove Qt/board distinte dalle verifiche pure |

Nel profilo schema 1, `check` riusa tutti i vincoli attuali: colori `#RRGGBB`, raggi Card/Row/Pill/Button 0–24, `listRows` 3 o 4, scala testo 0,85–1,10. Le ricette motion hanno `recipe`, `durationMs`, `distancePx`, `easing`, entro i limiti del registro; urgente immediato. Il prompt allega il contratto completo anziché copiare una sua versione abbreviata da mantenere a mano.

### Risultati e verifiche mancanti

Formato report proposto, da congelare con B0.2:

```json
{
  "reportVersion": 1,
  "operation": "check",
  "status": "invalid",
  "verification": {
    "schema": "verified",
    "resolvedTheme": "failed",
    "qtResources": "notVerified",
    "boardRuntime": "notVerified"
  },
  "issues": [{
    "code": "contrast.minimum",
    "phase": "resolve",
    "variant": "day",
    "file": "theme.json",
    "pointer": "/palettes/day/colors.textSecondary",
    "foreground": "#7a7a7a",
    "background": "#242424",
    "ratio": 3.616,
    "minimum": 4.5,
    "suggestion": {"value": "#8b8b8b", "scope": "pairOnly", "requiresRevalidation": true}
  }]
}
```

Il report reale usa il percorso del campo presente nel file o la sua provenienza ereditata; non assume che il campo sia necessariamente definito nella palette. Una verifica pura riuscita può essere `valid` nel suo ambito, con risorse/runtime ancora `notVerified`. Stampare gli ambiti anche in modalità testo. Se un livello è richiesto esplicitamente e non eseguibile, il risultato complessivo è `notVerified`, non un PASS.

Per i **nuovi** comandi: uscita 0 per successo nell'ambito richiesto, 1 per input invalido/operazione fallita, 2 per uso errato o verifica richiesta indisponibile, con codice strutturato che distingue i due casi. La ricevuta di install descrive `received`, destinazione canonica, ID/hash e verifica effettuata; non produce `applied` o `saved`.

### Percorsi, accesso e atomicità

Il runtime usa `SMARTPC_THEME_STORE` oppure `QStandardPaths.AppDataLocation/themes`; l'inbox attuale è il fratello `theme-imports`, non una cartella arbitraria nella home SSH. Default riscontrato sul PC: `~/.local/share/SmartPC/SmartPC/theme-imports/`. Il percorso del servizio documentato è `/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/theme-imports/`. Entrambi sono esempi: leggere configurazione e profilo del destinatario, inclusi utente/proprietario, prima della copia. [Qt: QStandardPaths](https://doc.qt.io/qt-6.8/qstandardpaths.html).

Usare destinazioni SSH configurate e autenticazione già disponibile; non registrare password/token, non disabilitare la verifica della host key. L'utente di trasferimento deve avere permessi coerenti con il servizio; un accesso riuscito alla home SSH non prova la scrivibilità dell'inbox del kiosk. Nessun ampliamento implicito dei permessi di `/opt`.

Copia in staging sullo stesso filesystem, verifica file/hash e rename soltanto a progetto completo. Stesso ID e contenuto già ricevuto: esito idempotente; stesso ID e contenuto diverso: conflitto esplicito, senza sovrascrittura. Non pretendere update versionati dal ponte schema 1: saranno introdotti dal lifecycle dei bundle. Gestire contemporaneità con l'importatore e ignorare directory temporanee nel discovery. Il contenuto ricevuto è verificato nuovamente dall'importatore, perché può cambiare dopo il trasferimento.

## 4. Percorso completo dopo il ponte

Il dettaglio eseguibile dei primi due blocchi è nell'[analisi A0/A1](theme-engine-a0-a1-implementation-analysis.md): 44 superfici logiche, 30 route overlay, 16 famiglie di contesti proposte, azioni versionate e adattatori privati. Il profilo board del 4 ottobre riconferma Qt 6.8.2 mediante probe offscreen; non è una nuova verifica EGLFS. Il confronto dei 183 SHA descrive la baseline precedente allo sviluppo. A0.1/A0.2 sono ora consegnati nel [resoconto](theme-engine-a0-contracts-report.md); il prossimo incremento è tracing A0.3 e fixture runtime A0.4, prima del modulo A1.

La preparazione A0 può iniziare mentre si completa B0. Prima di allargare `theme_pack.py`, separare parsing/diagnostica, trasporto e storage per non concentrare ogni responsabilità nella CLI. La [mappa completa dei file](theme-engine-ai-authoring-spec.md#15-mappa-degli-interventi-sul-codice) resta il riferimento.

| Blocco | Modifiche principali | Prova che sblocca il successivo |
| --- | --- | --- |
| A0 · Contratti e profilo | Inventario di tutte le superfici/azioni; schemi e matrice di compatibilità; profilo board; tracing del cambio tema; mappa G01–G21 | Baseline riproducibile, API/capacità richieste determinate, residuo prestazionale dichiarato |
| A1 · API pubblica e copertura | Modulo QML pubblico, contesti senza controller, host shell/overlay e adapter legacy; ruoli semantici adattivi G21 | Renderer nuovo usa solo API pubbliche; focus/router/dati invariati; palette chiare abilitate soltanto dopo T21 |
| A2 · Bundle e risorse | Schemi manifest/registry, builder, namespace, ResourceRef, import/export, digest e preflight dei quattro tipi di host | Un solo pacchetto porta nuova Home + piccola + grande su installazione pulita, offline, senza aggiungere file nell'app |
| A3 · Revisioni e recupero | Update/downgrade, journal atomico, lease/GC, migrazione override, supervisore esterno e quarantena | Interruzione, crash e blocco GUI recuperano precedente/Base; eventi e preferenze funzionali restano coerenti |
| A4 · Kit AI completo | Brief, contratti generati, fixture, lint/preview, packaging e report; renderer di tutte le superfici mancanti | Tema creato usando solo il kit e corretto dall'AI dopo diagnosi; tutti i file testati inclusi nel bundle |
| A5 · Dispositivo semplice | Catalogo/import/preview/apply/versioni, pochi adattamenti; editor corrente transitorio; migrazione preferenze | Percorso completo con nove tasti, urgente reale prioritario, annullamento e salvataggio fallito senza falsa conferma |
| A6 · Board e consegna | Stress, primi usi, idle, offline, reboot, export/reimport, servizio e manifest; cinque concept valutati progressivamente | Matrice T01–T21 eseguita con esiti/residui espliciti; versione/tag soltanto dopo decisione di consegna |

La nuova Home + piccola + grande è la prima prova del bundle. Per dichiarare completo l'engine vanno poi coperti pagina/shell/menu/impostazioni/Info/dettagli e gli altri quattro visuali Avvisi. I cinque concept si sviluppano progressivamente; una libreria di cinque temi si pubblica solo quando ciascuno passa la matrice comune. Non è necessario completare cinque estetiche per dimostrare l'architettura con un primo tema completo.

### Notifiche: invarianti e prove obbligatorie

I sei contratti sono `alerts.banner.small`, `alerts.banner.large`, `alerts.urgent`, `alerts.inbox`, `alerts.detail`, `alerts.badge`. Un tema può ridisegnare geometria, font, colori, iconografia e motion entro il contratto di ciascun host, o dichiarare un fallback Base. Piccola e grande restano indipendenti. Non riscrive tempi, deduplicazione, lettura, priorità o azioni.

Verificare tutti e sei con testi lunghi, selezione per ID durante refresh/scadenza, frame acknowledgement, timer unico, Off/Ridotto, errori di renderer/asset, cambio tema, urgente durante preview e rollback. La semantica dei dati mancanti/offline/stale e della fonte deriva dall'evento: non riutilizzare lo stato meteo per una notifica di altra categoria. I test osservano contratti/host stabili e readiness, senza pretendere figli specifici del visuale precedente. Focus ripristinato esplicitamente dopo il commit; callback di vecchie generation ignorate.

### Risorse e prestazioni

Il profilo board rimane distinto dal PC: Qt 6.8.2 e backend EGLFS delle prove acquisite vanno riconfermati al deploy, senza assumere che il Qt di sviluppo sia equivalente. Registrare font disponibili o `asset:<id>`, inventario/licenze/hash, moduli/import, dimensioni decodificate e primo uso. Un icon font è una possibilità, non il solo formato: icone procedurali, SVG/raster e atlanti devono evolvere tramite il medesimo contratto risorse con profili misurati.

Conservare gli obiettivi della specifica: frame ordinario animato p95 ≤20 ms, input→frame p95 ≤100 ms, cambio completo p95 ≤150 ms. La misura pregressa senza font aggiuntivi è 155,921 ms: residuo reale da profilare, non soglia da aumentare per comodità. Misurare cold/warm, primo glifo/asset, cambio da/verso Base, sei notifiche, CPU idle, RSS/PSS e plateau. FrameSwapped non è tempo GPU, PSS non è tutta la memoria grafica. Nessuna animazione diagnostica per fabbricare frame; scene/compagno ricchi avranno collaudo proprio.

## 5. Preparazione repository e consegna del primo blocco

All'avvio dell'implementazione:

1. Verificare branch, stato di lavoro e istruzioni del repository; conservare modifiche dell'utente. Registrare commit/hash della baseline effettiva. Non confondere la revisione documentale con il codice installato.
2. Realizzare B0.1/B0.2 e relative prove pure prima del trasferimento. Usare fixture isolate, senza QSettings/provider/DB reali. Poi B0.3/B0.4 e prova verticale B0.5.
3. Ogni consegna descrive codice, comandi realmente disponibili, ambiti verificati, limiti e prossimo gate. Non marcare A2–A6 chiusi sulla base di un `check` JSON.
4. Prima della prova/deploy sulla board: profilare destinatario, backup e rollback, verificare che trasferimento/import non modifichino dati dei provider. Dopo: manifest/hash, servizio attivo, riavvii inattesi, warning QML, persistenza e input reale.

**Definizione di completamento B0:** comandi utilizzabili e documentati, prompt/contratti coerenti, diagnostica correggibile dall'AI, progetto trasferito integro e importato con la selezione ordinaria del dispositivo. La prova sul PC e quella sulla board sono riportate separatamente. Nessun requisito di visuali nuovi viene dichiarato chiuso da questa consegna.

**B0 consegnato:** checker, diagnostica, profilo/kit schema 1 e trasferimento nell'inbox, con prova del menu e delle sei superfici del pilota. Restano API/bundle/lifecycle e kit completo A0–A6. Il prossimo blocco è A0/A1, ora [preparato con sequenza e verifiche](theme-engine-a0-a1-implementation-analysis.md#7-file-e-sequenza-di-implementazione); la possibilità di importare composizioni QML completamente nuove si dichiara consegnata solo dopo A6.
