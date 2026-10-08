Crea un tema SmartPC originale usando esclusivamente questo SDK e il brief allegato.

Leggi contracts/contexts.json, surfaces.json, actions.json, semantic-roles.json e il riferimento generato. I nomi esportati sono reali nel modulo SmartPC.ThemeApi 2.0. Non inventare metodi, proprietà o dati; il sistema conserva provider, router, tempi di notifica, priorità e stato del compagno.

Genera un progetto bundle, non soltanto palette: manifest, visual-registry, theme.json, renderer QML/JS, risorse e licenze. Inizia con `init`, poi crea una grammatica visiva coerente per Home e tutte le sei superfici notifiche, pagine, liste, dettagli, shell, impostazioni e scena. Puoi dichiarare fallback Base per una superficie; rendilo esplicito e non chiamarlo nuovo visuale. Piccola e grande devono avere composizioni indipendenti.

Usa contesti tipizzati con `required property PageContext context` o il tipo previsto dalla superficie. Non accedere a Main, controller, DashboardState o provider. Le azioni passano dal broker del contesto e sono validate dal sistema; la preview non le esegue. Dati assenti restano assenti: zero e false sono valori validi, offline/stale devono rimanere comprensibili, Home senza evento non riserva una scheda vuota.

Animazioni: usa la policy del contesto. Normale consente movimento, Ridotto limita decorazioni, Off mostra subito lo stato utile. Inattività/sospensione/uscita ferma Timer, sprite, shader e media: `visible=false` da solo non basta. Implementa settleMotion e readiness del contenuto, con errori e aree dei ruoli obbligatori; urgent deve comparire subito sopra ogni decorazione.

Progetta per 960×640 con gerarchia leggibile, focus evidente e nove tasti. Icone, font, immagini, sprite e altri asset sono risorse dichiarate, con licenze/hash e fallback. Nessun formato estetico è imposto; verifica gli asset sul profilo della board. Il compagno mantiene identità e stato fuori dalle schermate, rispetta ingombri e z-order del sistema.

Esegui validate --lint --runtime, leggi gli errori JSON, correggi i file e ripeti. Esegui preview --matrix e guarda gli screenshot. Non stimare contrasto a vista, non ignorare warning e non dichiarare eseguiti test mancanti. Compatta soltanto i file verificati con pack, conserva digest/report e trasferisci nell'inbox; il dispositivo valida nuovamente prima di applicare.

BRIEF: [vedi BRIEF.json]
DIAGNOSTICA: [report strutturato da correggere]
