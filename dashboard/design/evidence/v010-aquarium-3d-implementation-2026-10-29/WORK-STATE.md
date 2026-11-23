# Acquario 3D — indice di chiusura, 29 ottobre 2026

Implementazione nei sorgenti completata. [Report e limiti](../../v010-aquarium-3d-dynamic-implementation-report.md), [piano aggiornato](../../v010-aquarium-3d-dynamic-plan.md). Nessuna installazione della candidata; nessun subagente impiegato.

## Sorgenti e attribuzione

- `measured-source-manifest.json`: 737 file diagnostici, SHA256 `6faa8e29f789ed65deb2a1e77a00a341d6fad97a4795bdbab1ee92c9358f25c1`. È il sorgente della misura120s e dei primi workflow EGLFS nei tre temi.
- `final-source-manifest.json`: 737 file, SHA256 `bdde25a6a532bd59a6b2b30bbba71c1f449712ff272cfc38f6514954a13859d6`. Nomi mesh con digest, profilo per permanenza, diagnostica fixture, gestione senza righe tagliate e menu coerente con la disponibilità del 3D. Tutti i file del manifest corrispondono al checkout (`source-attribution.json`).
- Le quattro mesh finali sono identiche nei byte a quelle misurate; sono cambiati i nomi/riferimenti immutabili. La misura lunga non è dichiarata ripetuta dopo le modifiche successive.
- Versione del package diagnostico: etichetta del checkout0.10.1-rc.1, non una release nuova e non l'identità del runtime installato. Lavori precedenti Game/cleanup/README conservati; il checkout diagnostico non va installato integralmente.

## Prove positive pertinenti

| Evidenza | Perimetro |
| --- | --- |
| `pc-api-fixed/checks.json` | Contratto, adapter e core temi. |
| `pc-final-state-api/checks.json` | 40 test runtime API dopo rigenerazione dei qmltypes; test archivio allora disponibili. |
| `pc-profile-pinning/` | 14 test finali archivio/calendario/profili sul PC. |
| `board-final/arm-population/` | Gli stessi 14 test su ARM. |
| `pc-corpus-contract.json` | 171 scenari validati sul contratto dati, inclusi i tre contesti Acquario. |
| `pc-corpus-3d.json`, `pc-corpus-manage.json` | Un caso UI PC per ciascuna nuova superficie. Non matrice completa. |
| `pc-final-graphics/report.json` | Workflow reale Main, 20 controlli, llvmpipe funzionale. |
| `pc-legacy-final-direct/report.json` | Vecchio renderer2D Base: 76 controlli, inclusi venti rientri; nessun avviso. Solo regressione PC, non nuova qualifica ARM2D. |
| `board-measurement/results/{base,functional,apple}/` | Workflow EGLFS,20 controlli/tema; Apple120s dopo60s. |
| `performance-summary.json` | 59,955 callback/s, p95 18,15 / p99 20,52 ms, massimo45,74ms, zero stalli>50ms, sei draw call, CPU37,8% di un core, finestre10s. |
| `board-final/apple-final/` | Sorgente finale:21 controlli EGLFS, gestione realmente presentata, 59,97 callback/s nel breve controllo4s; nessun avviso/stallo>50ms. Non seconda misura nominale120s. |
| `board-final/board-final-receipt.json` | Manifest finale e preservazione runtime533file/preferenze/Gioco215artefatti/boot ID. |
| `board-final/final-health.json` | Dopo tutte le prove e la pulizia: versione installata0.10.1-rc.1, Apple1.6.5, servizio attivo/NRestarts0, heartbeat pronto. |
| `work-export-receipt.json`, `board-final/cleanup-receipt.json` | Archivio PC verificato su1058file/link; rimossa soltanto maintenance-work, ricontrollati533hash installati. |

Sintassi shell, indici/nomi Python e packaging controllati. Ambiente PC condiviso: `/home/giuseppe/.cache/smartpc-dev-qt682/bin/python`, PySide6 6.8.2.1. Nessun ambiente Python creato sulla board.

## Limiti e fallimenti conservati

- `board-short-cold/report.json`: in una prova4s dopo1s di riscaldamento, uno stallo308ms. Successivi passaggi brevi positivi non cancellano questa osservazione; cold start/transizioni da profilare.
- `native-dev-*`, `native-gdb.txt`, `pc-core`, `pc-state-runtime` e altre cartelle di sviluppo conservano i fallimenti precedenti: conteggi/mapping API, qmltypes, host dinamico, handler Python/cattura sincrona e contesto ES errato. L'archivio completo contiene anche il materiale della diagnostica.
- Apple inizialmente falliva perché il banco impostava un'anteprima della shell prima della creazione della Main; il banco finale parte da Base, seleziona e salva il tema con la GUI pronta.
- Il primo comando del runner generico su `check_aquarium_ui` ometteva `--output` (`pc-legacy-final/`): errore d'invocazione. L'esecuzione con gli argomenti propri dello script è in `pc-legacy-final-direct/` ed è passata. Un primo avvio ARM era fermato dai permessi della directory risultati prima di eseguire la suite; corretto e rieseguito.
- Non ripetuti: nuova matrice completa, tre repliche nominali finali, scala di popolazione, trenta rotazioni/venti rientri3D, soak30/60min, provider live concorrenti, pannello/tastierino fisici, GPU timing e FPS ottici. I venti rientri PC del vecchio2D non coprono il nuovo3D.

## Archivio e board

Archivio verificato: `/home/giuseppe/Documenti/SmartPC-backups/aquarium-3d-20261029/isolated-work.tar.gz`, SHA256 `98a71664a0bdc64aa50dd71009d7d0b5728b5643f62cdd35f26972b841f5ef6c`, 1058 voci confrontate per byte/hash o destinazione del link. `measured-source.tar.gz` conserva il sorgente della misura lunga. Le sei dipendenze ARM esatte, solo estratte e mai installate, sono nell'archivio con manifest dei contenuti. La cartella `/var/lib/smartpc-dashboard/maintenance-work` è stata rimossa dopo la verifica e il controllo dei processi; servizio originale ripristinato, nessun reboot.
