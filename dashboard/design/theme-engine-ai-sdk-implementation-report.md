# Theme Engine — SDK AI e fixture supplementari

**5 ottobre 2026 · implementazione A4; accettazione dell'intero engine distinta.**

Il kit permette di creare e controllare un progetto QML esterno usando contratti pubblici reali. L'esempio introduce Home, shell e due notifiche indipendenti; include anche una ricetta, un'icona procedurale e una skin di scena. Le altre **40 superfici** dichiarano fallback Base. Questo dimostra estensibilità e copertura funzionale dichiarata, non 44 visuali nuovi o la chiusura della matrice della board.

## Strumenti disponibili

`dashboard/smartpc-theme` e `theme_bundle_tools.py` espongono `init`, `validate`, `preview`, `pack`, `inspect`, `kit`, `transfer`, `export`. `theme_pack.py bundle ...` inoltra questi comandi; `theme_pack.py kit --bundle --output DESTINAZIONE` esporta l'SDK completo. I precedenti comandi schema 1 conservano il comportamento.

Il kit include:

- modulo `SmartPC.ThemeApi 2.0`, type information, sorgenti dello SDK e runner;
- contratti canonici, riferimento, schema dei token aggiornato e fingerprint;
- esempio esterno, 16 scheletri tipizzati intenzionalmente non ready finché completati, esempi scena/icona/motion;
- brief strutturato e prompt indipendente dal fornitore AI;
- fixture sintetiche, matrice T01–T21 inizialmente non verificata, manifest SHA dei sorgenti;
- strumenti utilizzabili senza il repository originale. Nessun account, database, cache di produzione o evidenza personale viene esportato.

Il progetto nasce con namespace nuovo. Le chiavi di registry e i riferimenti nel JSON vengono sostituiti coerentemente. Il builder produce ZIP deterministico e inventario dei file effettivi; export conserva la revisione esatta. Transfer usa staging nascosto, confronto SHA remoto e pubblicazione nell'inbox soltanto dopo il trasferimento integro. Import/apply restano azioni del dispositivo; transfer non applica un tema.

## Livelli di verifica

Il validator statico controlla manifest, registry, integrità, compatibilità, risoluzione e contrasti attraverso il resolver comune. `--lint` usa il vero qmllint con import path e type information: i report conservano file, linea, codice e suggerimento. Un tool assente produce `notVerified`.

La preview costruisce veri contesti pubblici e renderer Qt. Usa il catalogo del **bundle**, non la palette Base; un test controlla anche il pixel della superficie. Carica tutte le presentazioni e **tutte le famiglie ausiliarie**, anche quando non selezionate: scena, icona e ricetta. Verifica import dei moduli dichiarati, decodifica delle immagini e dei font dichiarati, readiness, geometria positiva, play/settle della ricetta e arresto delle animazioni dopo sospensione. Genera screenshot con fixture sintetiche, varianti giorno/notte e Normale/Ridotto/Off.

Le fixture precedono Qt con XDG/store privati. Connessioni socket/DNS vengono negate, con controllo positivo; non viene usato il DB reale. La preview di singoli renderer non certifica tutti i flussi di Main, il tastierino fisico, la GPU, il primo frame ottico o i budget prestazionali EGLFS.

## Prove PC

Con Python locale/PySide6 Qt **6.11.2**, backend offscreen/software:

- `check_theme_bundle_tools.py`: **7 prove passate**. SDK copiato indipendente, init/validate/pack senza repository, namespace/coverage, sorgenti conservati, packaging deterministico, export esatto, diagnostica e tool mancante.
- `check_theme_bundle_preview.py`: **4 prove passate**, comprendenti **72 casi primari e 18 ausiliari**; controllo della palette realmente disegnata; errore introdotto separatamente in scena/icona/ricetta respinto; font invalido dichiarato ma inutilizzato respinto.
- qmllint: **7 componenti senza diagnostica**. Una proprietà deliberatamente errata genera `missing-property` con linea e candidato; dopo correzione il lint passa.
- `check_theme_semantic_residuals.py`: **7 casi supplementari passati** su Main reale. Home senza/con evento e passaggio futuro→iniziato→scaduto; mezzanotte/cambio anno; forecast parziale che conserva snapshot/cache/fetchedAt precedenti; regione protetta che ferma la scena senza sostituire ActorState.

Queste fixture supplementari entrano nel runner di regressione A0.4; non aumentano artificiosamente le 108 richieste canoniche. Le prove della board devono essere registrate separatamente sulla versione Qt realmente installata.

[Evidenze locali](evidence/theme-ai-sdk-2026-10-05/local/preview-report.json), [lint](evidence/theme-ai-sdk-2026-10-05/local/lint.json), [prove del toolkit](evidence/theme-ai-sdk-2026-10-05/local/tool-tests.txt), [residui semantici](evidence/theme-ai-sdk-2026-10-05/local/semantic-residuals.json).

## Accettazione ancora distinta

Il kit non dichiara chiusi import/apply e tutte le superfici sul dispositivo, recovery da GUI bloccata, power cut, versioni/lease/GC, input fisico, stress/cold/idle/soak o leggibilità dell'intero runtime. Questi punti appartengono alle prove integrate A1/A2/A3/A5/A6. Le immagini sono prove di caricamento/layout sintetico; la validità estetica richiede una valutazione visiva del tema sul pannello.

Icona e ricetta usano il contratto storico API 1 del rispettivo host; pagine, shell, notifiche e scena usano contesti tipizzati pubblici API 2. Nessun esempio accede a Main o ai controller. Le risorse restano estendibili nei formati e moduli dichiarati dal profilo; il kit non fissa tutte le palette, i font, le animazioni o il formato futuro del compagno.
