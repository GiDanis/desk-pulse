# Theme Engine — consegna B0: authoring AI schema 1

**3–4 ottobre 2026 · estensione della linea v0.6.6.** Implementato, collaudato in EGLFS e installato sulla Orange Pi, con pilota importato e preferenze correnti conservate. [Piano completo](theme-engine-ai-execution-plan.md), [specifica](theme-engine-ai-authoring-spec.md), [guida](theme-engine-implementation-guide.md).

## Risultato

`theme_pack.py` aggiunge `check`, `profile`, `kit`, `install`, conservando `list`, `validate`, `import`, `export` e la loro richiesta di `--store`. Il percorso del ponte è **brief AI → progetto JSON → check/correzione → inbox → Importa → selezione/anteprima → Applica e salva**. Il tema pilota `braun-rams` usa composizioni già distribuite: Home a sinistra, piccolo small-rail e grande large-split, più gli altri quattro ambiti Avvisi. Le varianti sono entrambe scure; la palette definitiva resta da progettare.

`check` non scrive nel catalogo e usa `ThemeCatalog` in memoria. Verifica varianti, ereditarietà, tipi/range, registri, asset/hash, contrasti e vincoli geometrici dei template. La diagnostica raccoglie token invalidi e coppie di contrasto indipendenti, indicando variante, file/JSON Pointer e provenienza ereditata. I suggerimenti sono `pairOnly`: non mutano il progetto e richiedono una nuova risoluzione. [Fixture invalida](evidence/theme-authoring-b0-2026-10-03/invalid-fixture-check.json), [correzione di una sola coppia ancora insufficiente](evidence/theme-authoring-b0-2026-10-03/pair-only-correction-check.json), [correzione coerente verificata](evidence/theme-authoring-b0-2026-10-03/corrected-fixture-check.json). La fixture è deliberatamente errata per dimostrare il ciclo di correzione.

Il checker rileva anche rischi G21 del runtime attuale: foreground semantici fissi e accenti effettivamente usati come testo/guide. Non migra `SemanticStyle` a una facade adattiva: quel lavoro resta in A1. Le verifiche supplementari di authoring possono rifiutare un candidato che il vecchio importatore schema 1 ammetterebbe; non modificano retroattivamente le preferenze salvate.

`profile` acquisisce Qt/font, display, registri effettivi, impronta di compatibilità e percorsi. Sulla board legge il processo del servizio per individuare root, HOME e store effettivi; il HOME SSH non è usato come HOME del kiosk. Il probe gira offscreen in un processo distinto e non costruisce ThemeService, QSettings o provider. `kit` genera prompt, schema con token anche di estensione, registri, Base e profilo; non introduce un secondo resolver. Il profilo è una fotografia con timestamp, non una certificazione permanente.

`install` valida anche la copia da consegnare, usa staging nascosto con `theme.json` dentro `payload/`, verifica digest, sincronizza e pubblica con rename sotto lock. Il discovery dell'importatore corrente ignora lo staging. Stesso contenuto ricevuto: idempotente; contenuto diverso: conflitto, senza overwrite. SFTP/SSH usa host key verificata e autenticazione esistente. Prima della pubblicazione sulla board, il destinatario ripete la risoluzione e il probe di font/immagini/glifi con il proprio Qt. Non vengono riavviati il servizio o applicate preferenze dal comando `install`.

## Uso per l'autore

Dal repository, con destinazione SSH del proprio dispositivo:

```bash
python3 dashboard/theme_pack.py profile --board smartpc@192.168.1.179 --output target-profile.json
python3 dashboard/theme_pack.py kit --profile target-profile.json --output ai-kit
python3 dashboard/theme_pack.py check cartella-tema --profile target-profile.json --format json
python3 dashboard/theme_pack.py install cartella-tema --board smartpc@192.168.1.179 --format json
```

Consegnare all'AI la cartella `ai-kit` con il brief. Il primo progetto estende Base e usa famiglie `""`; font aggiuntivi richiedono risorse reali o disponibilità nel profilo. Per un destinatario locale, `--store` può stare prima o dopo il nuovo sottocomando. `--qt` aggiunge un probe PC isolato; `--qt-python` seleziona l'interprete con PySide6. Il client dei controlli puri e del trasferimento usa la libreria standard Python e OpenSSH; non richiede PySide6 sul PC quando il probe è remoto.

L'applicazione ordinaria rimane `9 Menu → Impostazioni → Aspetto → Importa pacchetti → Tema (4/6) → Applica e salva (5)`. Non confondere ricevuto, importato e applicato. Per i nuovi comandi: uscita 0 nell'ambito richiesto, 1 per input/operazione fallita, 2 per uso errato o probe richiesto indisponibile. Errori di parsing CLI mantengono la diagnostica argparse su stderr. Non verificato non è PASS.

## Correzione emersa nel prototipo

La revisione visiva ha individuato un difetto reale delle ricette: NotificationHost preparava l'opacità iniziale per slide/fade, ma SlideRecipe animava soltanto la posizione. Il banner poteva restare a 0,35 anche dopo il passaggio a Off. Ora SlideRecipe porta posizione/opacità allo stato finale; exit e settle ripristinano correttamente il target. NotificationHost normalizza l'opacità del Loader al settlement. La prova del pilota controlla esplicitamente opacità 1 in Normale/Ridotto/Off e dopo annullamento della bozza, oltre al timer di consegna invariato.

La prima variante notte ereditava colori Base: il pilota ora dichiara anche i ruoli notturni necessari a conservare il grigio/arancio. La prima copia di prova nell'inbox è stata preservata durante il test di conflitto e poi rimossa controllando il suo digest esatto; nessun tema installato è stato eliminato. [Prima ricezione](evidence/theme-authoring-b0-2026-10-03/first-transfer.json), [conflitto respinto](evidence/theme-authoring-b0-2026-10-03/conflict.json), [ricezione finale](evidence/theme-authoring-b0-2026-10-03/final-transfer.json).

## Verifiche

Otto harness PC passati, comprendendo 20 test del nuovo bridge, 17 del core e le regressioni font/persistenza/motion/UI/notifiche. [Esiti](evidence/theme-authoring-b0-2026-10-03/local/checks.json). Probe aggiuntivo con TTF reale e rifiuto della famiglia glyph vuota, conforme al runtime: [risorse](evidence/theme-authoring-b0-2026-10-03/local/resource-probes.json). Il PC usa Qt 6.11.2; le risorse locali verificate non vengono attribuite al Qt del destinatario.

Sulla board Qt 6.8.2/PySide6 6.8.2.1: bridge/core/font/persistenza offscreen, motion e notifiche in EGLFS, prova verticale del pilota in EGLFS. Import/selezione/salvataggio attraverso il menu reale con QKeyEvent, preferenze inalterate all'import, nuova ThemeService che rilegge la selezione salvata, sei host pronti in Day/Night × Normale/Ridotto/Off, focus e deadline del banner preservati. Dati/provider/SQLite/preferenze delle fixture sono isolati. [Report del pilota](evidence/theme-authoring-b0-2026-10-03/board/pilot-ui/report.json), [notifiche](evidence/theme-authoring-b0-2026-10-03/board/notifications/report.json). Nessun warning QML inatteso. Non è una pressione umana sul tastierino.

Smoke EGLFS di 20 secondi, Base e stessa sequenza dello strumento precedente: frame p95 **17,731 ms**, input→frame p95 **33,834 ms**, nessun warning. [Dati integrali](evidence/theme-authoring-b0-2026-10-03/board/motion-smoke/report.json). Misura FrameSwapped nelle finestre di animazione, non tempo GPU o risposta ottica. Non sostituisce lo stress di cambio tema, soak o misure dei futuri bundle; il precedente residuo p95 155,921 ms sul cambio tema resta aperto.

## Distribuzione e dati reali

Backup fresco privato prima delle prove: `/var/backups/smartpc-authoring-b0-20261003/pre-implementation`, con runtime, stato utente e prova dei flag evento. [Metadati del backup](evidence/theme-authoring-b0-2026-10-03/board/backup-report.json). La dashboard è stata riavviata dal trap dopo i test EGLFS.

Distribuzione finale verificata: **183 file**, manifest `dirty=false`, commit `a7fd705ca0078e02c38f1b18c94b3a42ee342955`; implementazione nel commit `83e473e`. Runtime precedente conservato in `/var/backups/smartpc-authoring-b0-20261003/previous-runtime`, con ripristino automatico del software previsto nel deploy in caso di errore. Il rollback software non è stato nuovamente eseguito in questa consegna. Il pilota è importato nel catalogo e selezionabile in **Impostazioni → Aspetto → Tema**, senza applicarlo. Preferenze con SHA invariato, stato dei nove eventi preesistenti non azzerato, servizio `active`, PID 30559, `NRestarts=0` e zero warning QML nel controllo successivo al riavvio. [Report di installazione](evidence/theme-authoring-b0-2026-10-03/deployment-report.json). [Trasferimento identico ripetuto](evidence/theme-authoring-b0-2026-10-03/idempotent-transfer.json). Nessun nuovo tag o cambio del tag v0.6.6, nessun push. Riavvio del servizio verificato; reboot fisico e soak non ripetuti.

[Manifest finale](evidence/theme-authoring-b0-2026-10-03/final-manifest.json) e [verifica conclusiva](evidence/theme-authoring-b0-2026-10-03/final-verification.json): SHA di tutti i file installati identici al workspace e al pacchetto; 20 test del bridge ripetuti sul runtime definitivo. Le revisioni documentali successive non richiedono una nuova distribuzione.

## Confine della consegna

B0 permette all'AI di progettare un tema dichiarativo e correggerlo tramite gli strumenti reali. Non importa QML/JS nuovi, non aggiorna lo stesso ID installato, non contiene l'API pubblica 2, il nuovo catalogo semplificato, lifecycle/versioni/GC o supervisor dei bundle. Il kit completo A4 resta distinto dal kit schema 1. L'uso di genitori personali sul destinatario richiede lo stesso catalogo disponibile al checker; per il ponte PC→board il percorso raccomandato estende Base. `qtResources` verifica decode/font/glifi; layout/input/prestazioni richiedono le fixture e la board. A0/A1 è il prossimo blocco; A2–A6 e il compagno definitivo restano nel piano.
