# v0.9.3 — attuazione e verifica dell’intero sistema

**22 ottobre 2026 · candidata 0.9.3-rc.1 installata, 645 hash, tre reboot qualificati.** [Report](../../v093-implementation-report.md), [piano V0–V9](../../v093-systemwide-execution-plan.md), [studio e baseline](../v093-systemwide-analysis-2026-10-21/README.md). La cartella conserva la data di apertura dei lavori, 21 ottobre. Le ricevute descrivono gli esiti effettivi; un file di log incompleto non certifica un pass.

La ricevuta di installazione identifica **native-wire-final/receipt.json** come qualifica della versione effettivamente consegnata. I nomi delle altre cartelle conservano le prove intermedie, incluse le varianti scartate.

## Evidenze principali

| File o gruppo | Significato |
| --- | --- |
| [selected-implementation.json](selected-implementation.json), [final-health.json](final-health.json) | Identità della versione consegnata, scelta/rifiuto delle alternative e salute finale con PID/heartbeat corrente |
| `before/`, `implementation.patch` | Copie iniziali dei file toccati e differenza limitata a questo intervento. Il checkout conteneva già molti altri lavori: non usare il diff Git completo come diff della v0.9.3 |
| `boot-handoff-initial.json`, `dedicated-timer.json`, `resource-selection.json` | Causa del quit Plymouth senza privilegi, conclusione dei sette job bloccati, conservazione e disattivazione del timer estraneo, politica delle risorse scelta |
| `sport-cached-arm-candidate.json` | Getter sul calendario reale di 380 incontri, rete negata e stato stale: circa 0,058 ms di mediana, rispetto ai 17,3 ms della baseline |
| `final-pc-gates.json`, `*-qualified*` | Verifiche della candidata congelata e matrice Apple giorno/notte, Base, Functional; correttezza di servizi, notifiche, UI, lifecycle, API e disponibilità moduli |
| `native-wire-final/receipt.json`, `native-wire-final/*/report.json` | Qualifica EGLFS/OpenGL sulla board: confronto primo frame coerente, navigazione, tutte le 68 superfici, gara a cinque auto, SAC con replay pieno, metadati reali read-only |
| `native-final/governor-rollback.json` | Stop della policy → schedutil; Start → performance, con lettura del kernel. Nessuna affinità imposta o priorità real-time |
| `native-r4/receipt.json`, `native-final/receipt.json`, `native-abba-statistics.json` | Tre blocchi ABBA nice e tre governor, Base/Functional, PPO nominale, SAC/TD3/Tactic con replay pieno sintetico e Qualifica fino a completamento naturale. Le differenze di sorgente rispetto alla qualifica finale sono esplicite nella ricevuta |
| `installation-receipt.json`, `before-install.json`, `installed-final.json`, `rollback-rehearsal.json` | Installazione, manifest, backup completo, inversione atomica e prova reale del vecchio runtime, poi reinstallazione della candidata; verifiche di preferenze, tabelle e artefatti |
| `reboot-qualification.json` | Tre reboot effettivi con boot ID distinti, GUI corrente pronta, hash, tema, preferenze, thread di rendering, governor e boot senza job sospesi |
| `post-reboot-preservation.json`, `system-after-reboots.json`, `passive-observation-start.json` | Conservazione finale di 14 tabelle e 211 artefatti, osservazione OS e avvio del campionamento passivo di otto ore, ancora incompleto |
| `ruff-qualified.txt` | Controllo statico dei file Python modificati da questo intervento |

Il confronto ABBA del solo trasporto JSON/cache QML è nei quattro report `native-wire-final/first-response-A0/B0/B1/A1`. L’ulteriore separazione calendario/dettaglio di `native-selected-final/` è scartata per la regressione sulle riaperture, nonostante il miglioramento sugli incontri diversi. La variante QJSValue creata con evaluate, in `native-js-final/` e `pc-qjs-eval/`, è stata scartata per la crescita di memoria; patch e misure rimangono disponibili. Le copie PC precedenti al riuso sono in `pc-pre-js/`; non entrano nel conteggio della matrice finale.

Gli script `final_pc_qualification.py`, `native_wire_qualification.py`, `first_response_wire.py`, `mixed_native_wire.py`, `probe_metadata_reader.py`, `install_candidate.py` e `qualify_reboots.py` documentano le procedure. Il coordinator nativo ferma il kiosk per ottenere KMS esclusivo e lo riavvia in finally. I carichi UI/Gioco usano dati privati; la sonda metadati apre il database produttivo soltanto in mode=ro e query_only. Nessun learner produttivo viene avviato.

## Interpretazione e tentativi storici

`frameSwapped` e il primo frame con contesto coerente sono misure software: non latenza ottica, FPS fisici o USB-HID. La prova generale precedente forza un frame dopo readiness e resta conservata con quel limite. I percentili finali sono nearest-rank; freddo e caldo restano separati.

La prova distinta di navigazione inizialmente assumeva che il ritorno azzerasse l’indice: il prodotto conserva correttamente il match selezionato. L’oracolo è stato corretto, azzerando i bookmark privati solo prima del nuovo ciclo e verificando l’indice scelto sul ritorno; fallimento e tentativo riuscito sono conservati.

I log senza suffisso qualified, i giri nativi r1/r2/r3 e il primo giro mixed conservano i tentativi intermedi. Alcuni fallirono per renderer diagnostico omesso, fixture mutate in posto, isolamento XDG incompleto o oracolo Rete legacy; non entrano nei conteggi finali. Il primo mixed usava processEvents senza il normale drenaggio DeferredDelete di app.exec. La procedura finale usa un vero event loop. Il primo giro corretto, ancora precedente al riuso JavaScript, passa 287 casi/68 superfici in 600,6 s, con RSS 218→633 MB: include il riscaldamento di viste/stili diversi e non qualifica l’assestamento della memoria. Una sonda PC a rotta ripetuta mantiene dieci contesti/lease, con heap Python circa 5,8 MB fra il decimo e il trentesimo giro; il trim diagnostico del solo processo privato mostra anche memoria trattenuta dall’allocatore. Non viene introdotto un trim o GC periodico nel prodotto e non si ricava da questi campioni una prova di RAM stabile per ore.

`check_game.py` mantiene cinque failure e un error preesistenti, riprodotti sui sorgenti completi precedenti: assume piloti senza policy iniziali. I controlli delle ricette e della rosa correnti sono separati, e quel risultato non è presentato come superato.

L’uso misto prolungato 60 minuti/8–24 ore, le prove fisiche pannello/tastierino e gli eventi live dei provider rimangono gate distinti finché non esistono le rispettive ricevute. La candidata conserva rc; non si promettono 60 FPS costanti o benefici della NPU non misurati.
