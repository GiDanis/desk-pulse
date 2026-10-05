# Theme Engine — implementazione A1–A6

**5 ottobre 2026 · v0.6.6 · collaudo finale in corso**

La dashboard ora importa temi con codice visuale QML/JS, animazioni e risorse proprie, usando una API pubblica versionata. Pagine, shell, overlay, dettagli e tutte le sei superfici Avvisi possono essere sostituiti; ogni superficie mantenuta con Base è dichiarata nel manifest. Il codice funzionale, i provider, le decisioni sugli eventi e il router dei nove tasti restano gestiti dall'applicazione.

Questa consegna implementa i blocchi A1–A5 e gli strumenti/prove di A6. Non assegna una nuova versione o tag. L'accettazione integrale dei gate dispositivo è distinta dalla presenza del codice: [matrice T01–T21](evidence/theme-engine-a1-a6-2026-10-05/acceptance-matrix.json). La baseline precedente è `d643cfb`; le prove iniziali sul dispositivo usano uno staging dichiarato dirty. Manifest e installazione finale sono registrati nelle evidenze finali.

## Funzioni consegnate

| Blocco | Implementazione |
| --- | --- |
| A1 · API e copertura | `SmartPC.ThemeApi 2.0`: 44 superfici, 16 contesti, 58 DTO, 30 modelli, 32 azioni. Adapter privati, proprietà pubbliche read-only, modelli con identità stabile; numeri/null preservati. Shell e overlay sostituibili, broker con guardie e completamento asincrono effettivo. |
| A2 · Bundle | Manifest e registri validati, namespace, compatibilità engine/API/Qt/capacità, cartelle/revisioni immutabili con digest di tutto il payload. ResourceRef per tutti gli host, preflight Qt separato anche per scene/icone/ricette e visuali inattivi. Import/export offline con codice e asset. |
| A3 · Recupero | Journal atomico, precedente/Base, quarantena, lease delle risorse e GC. Un candidato si salva solo dopo readiness e frame coerente reali. Supervisore fuori dalla GUI per crash, blocco, startup incompleto e readiness persa. Annullamento e salvataggio fallito conservano lo stato impegnato. |
| A4 · Authoring AI | Kit autonomo con contratto, tipi, template, fixture, SDK, brief e comandi per progetto, validazione/lint/preflight, preview, packaging, trasferimento ed export. Diagnostica strutturata; nessun modello AI obbligatorio sul dispositivo. |
| A5 · Impostazioni | Tema, revisione installata, palette, dimensione testo e movimento; anteprima/applica/annulla/import/export. Editor avanzato transitorio. Identificatori canonici e metadati delle opzioni permettono a un tema di ridisegnare anche questo percorso. |
| A6 · Verifica | Suite locale/Qt minimo, runtime Main reale, notifiche, scene e palette sul display EGLFS, stress e idle con evidenze. Backup, manifest e recupero controllato per l'installazione. Gate lunghi/fisici elencati separatamente. |

## Personalizzazione, notifiche e compagno

Il profilo schema 1 rimane compatibile; il bundle completo consente composizioni nuove e risorse locali senza aggiungere file dentro l'app installata. La copertura del registro è obbligatoria: own e fallback sono disgiunti e devono coprire tutte le 44 superfici. Gli esempi sono progetti di prova, non un elenco chiuso di stili possibili.

Piccolo, grande, urgente, badge, inbox e dettaglio Avvisi hanno visuali e stile indipendenti. Eventi, priorità, deadline, seen/dismiss e regole silenzio rimangono dell'app; il tema cambia la presentazione e richiede azioni validate. Una priorità urgente non dipende dalla fine dell'animazione. Il collaudo confronta identità/eventi/deadline attraverso anteprime, aggiornamenti e annullamenti.

Il tema può fornire icone geometriche, glifi, immagini o componenti verificati. Le animazioni possono usare ricette proprie e le scene hanno un contesto pubblico. Off, Ridotto, attività/visibilità e sospensione sono politiche comuni: il tema deve rispettarle. L'attore del futuro compagno ha identità e stato persistenti gestiti dall'app; pelle, pose e visuale possono evolvere. Rig/atlanti/shader e il compagno definitivo richiedono capacità e collaudo propri: non sono dichiarati già consegnati.

QML/JS del bundle è codice visuale fidato. Preflight, compatibilità e supervisione non costituiscono una sandbox. Il pacchetto non distribuisce Python, installer o plugin nativi.

## Prestazioni e scelte tecniche

QML consuma facade/proprietà Qt tipizzate. Il dizionario di token viene risolto ai confini dell'aggiornamento; non viene attraversato da Python per ogni frame. DTO annidati sono istanze dei tipi registrati ma i getter PySide usano `QObject*`, con tooling generato dal contratto: non si promettono puntatori C++ personalizzati né AOT per ogni role dinamico.

Il resolver mantiene cache limitate e lease dei font; non carica tutte le famiglie ipotizzate. Il database delle famiglie viene interrogato una volta per risoluzione. Gli adapter dell'API pubblica non preparano snapshot per i visuali legacy. Il factory applica gli aggiornamenti solo dopo la validazione atomica dei campi modificati e conserva la distinzione fra falso, zero e null. Queste ottimizzazioni mantengono il contratto e riducono lavoro misurato sul PC; i budget di prodotto sono valutati con misure sulla board.

Le prove preservano cold first-use, p95, intervalli lunghi, denominatori, run falliti e assestamenti non osservabili. La diagnostica è opt-in e non forza frame durante l'idle. Il timing `frameSwapped` non è una misura ottica del pannello o del tempo GPU; il ritardo GIL dei callback Python resta non quantificato.

## Evidenze locali

[Evidenze locali e comandi](evidence/theme-engine-a1-a6-2026-10-05/local/README.md). Suite API nativa/typeinfo, 44 adapter reali, bundle avversariali, ciclo di vita, service recovery e profili persistenti, SDK standalone e preview, ruoli semantici, font/icone e tracing. La matrice legacy contiene 136 scenari su otto profili: **1.088 esecuzioni**, 108 requisiti coperti, nessun warning QML. Le 14 regressioni UI isolate sono passate; i due harness modificati seguono le righe effettivamente visibili delle nuove impostazioni e conservano gli intenti funzionali.

[Prove integrative API/notifiche/scene](theme-engine-acceptance-supplement-report.md) e [SDK indipendente](theme-engine-ai-sdk-implementation-report.md) specificano i rispettivi ambiti. Il modulo runtime e i renderer esterni sono esercitati realmente; il metadata del checker statico rimane `contractOnly` e non viene promosso artificiosamente a prova runtime.

## Evidenze dispositivo e decisione

Le prove iniziali su Qt 6.8.2 / PySide 6.8.2.1 aarch64 e EGLFS sono archiviate in [board/initial](evidence/theme-engine-a1-a6-2026-10-05/board/initial). Import/apply/cancel/update, notifiche pubbliche, scene guaste/non pronte e palette Giorno chiaro/Notte rossa passano senza warning. Tre coppie off/on su due profili font conservano 1.200 cambi; l'idle passivo non genera frame. Queste prove precedono le ultime ottimizzazioni e non rappresentano i numeri prestazionali del sorgente finale.

La verifica finale, i numeri dopo ottimizzazione e l'installazione sono aggiunti qui alla conclusione del collaudo. Il confronto mantiene gli obiettivi originali **150 ms / 20 ms** e costo diagnostico **1 ms / 8 MiB**.

I casi T01–T21 richiedono più delle singole prove automatizzate. Restano separati il tastierino fisico, power-cut reale durante scrittura, reboot hardware, lettura ottica/contrasto del pannello, soak 24/7 e qualifica dei cinque concept estetici. Un tema nuovo che passa il preflight non è automaticamente qualificato per ogni budget o ogni variante di contenuto.
