# SmartPC v0.10.1 — pulizia OS e distribuzione

28 ottobre 2026, Europe/Rome. Attuazione autorizzata dopo l'analisi della board.
**Stato: pulizia completata; candidata 0.10.1-rc.1 installata e verificata.**

## Perimetro

Baseline verificata `0.10.0-rc.2`, 682 file conformi, Apple Calm 1.6.5, servizio
attivo e `NRestarts=0`. SD da 29 GiB al 97%, circa 1 GiB disponibile. Il problema
principale è l'accumulo di backup e prove; il runtime occupa circa 14 MiB.

L'inventario privato comprende 349.933 voci in 422 radici, con SHA-256, inode,
metadati e hard link. Archiviazione sul PC in
`/home/giuseppe/Documenti/SmartPC-backups/v0101-20261028/` con accesso ristretto.
Verificati tutti i contenuti e metadati dell’archivio e il digest trasmesso.
Prima della rimozione, inventario e riferimenti dei processi ricontrollati;
validazione senza rimozione e applicazione entrambe passate.

## Modifiche applicate

- Runtime separato dagli script `check_*` / `verify_*`: 533 file; diagnostica
  separata con 683 file, compreso il renderer Canvas necessario al banco.
- Quattordici import inutilizzati rimossi in sette moduli e cinque strumenti
  locali. Nessuna modifica a fisica, premi, pesi, dati o grafica.
- Distribuzione costruita dai byte installati, con solo sette moduli ripuliti e
  `version.py` aggiornato a `0.10.1-rc.1`. Il codice di ricerca presente soltanto
  nel checkout non entra nella consegna. Libreria nativa ARM invariata.
- I sette pacchetti Chrome/Docker sono stati salvati nelle esatte versioni
  installate e verificati contro i SHA-256 di APT prima della rimozione.
- Introdotti filtro del manifest di baseline, controlli di integrità e guardie
  contro diagnostica presente nel runtime; quattro test del packaging passati.
- [Regole di conservazione](../../os/maintenance-policy.md): una sola cartella
  temporanea di manutenzione, esportazione delle prove, rollback recente,
  archivi storici sul PC e nessuna cancellazione automatica per sola anzianità.

## Test più leggeri

Il runner locale usa ora `quick` come default: cinque suite (impostazioni,
Aquarium, menu Game, avvio sessione, core temi), tutte passate in 11,13 secondi
sul checkout corrente. Le dipendenze di sviluppo includono ora le versioni
NumPy/NEAT già fissate per Game, usate nella verifica. Un solo riepilogo a
console; log completi e JSON su disco.
`--case` seleziona direttamente i casi pertinenti, `--list` li elenca senza
avviarli e `--verbose` abilita gli esiti intermedi. `core`, `ui` e `all` restano
disponibili; nessun test viene cancellato né riclassificato. Verificati anche
selezione, errori CLI e propagazione del timeout.

Le istruzioni `AGENTS.md` limitano letture dei file, output e ripetizioni ai
controlli necessari. Il rapido non sostituisce la qualifica di una consegna.
[Ricevuta rapido](evidence/v0101-cleanup-2026-10-28/quick-runner/checks.json),
[controlli CLI](evidence/v0101-cleanup-2026-10-28/runner-cli.json).

## Dati e dipendenze preservati

Conservare dati/preferenze, temi e quarantena, entrambi gli ambienti Python,
boot/kernel/driver e file di ripristino DP. `game-runtime` è il Python attivo;
`dp-kernel-fix/uImage.dpfix` e `boot.cmd.dpfix` servono all'updater. CopyTrade,
LightDM/desktop di recupero e hold dei pacchetti restano fuori dalla pulizia.

## Verifiche e limiti

Quattordici suite correnti PC e quattordici ARM passate; lint dei file modificati
passato. Le suite storiche `check_game.py` e `check_dashboard.py` falliscono anche
sulla baseline: la prima assume piloti inizialmente vuoti (cinque failure e un
error), la seconda una matrice di navigazione precedente all'Acquario. Gli esiti
iniziali sono conservati e non vengono riclassificati come successi.

Il banco UI iniziale richiedeva il renderer diagnostico assente dal pacchetto
installato e la corretta gestione del menu Gioco e del main guard per spawn.
Sono correzioni del banco privato; non modificano il runtime applicativo.
Le sei verifiche UI PC e le sei EGLFS nei tre temi sono poi passate. La candidata è installata con 533 hash conformi, GUI pronta e NRestarts=0; cinque piloti, 215 artefatti, contenuto logico del database e preferenze/configurazioni identici, senza reboot OS. [Ricevuta](evidence/v0101-cleanup-2026-10-28/installation-receipt.json). Archivio storico verificato e rimozione completata; [ricevuta finale](evidence/v0101-cleanup-2026-10-28/final-receipt.json).

Le prove software non certificano FPS ottici, eventi live, telecomando fisico,
soak prolungato o qualifica scientifica dei modelli. Nessun nuovo modello è
promosso e nessun reset personale è previsto.

[Evidenze](evidence/v0101-cleanup-2026-10-28/).

## Spazio e conservazione finali

- Spazio libero iniziale: **0,97 GiB**; finale: **20,87 GiB**.
- Rimozione storica: **19,76 GiB recuperati**, 422 radici / 349.933 voci.
- Archivio compresso sul PC: **8,39 GiB**, SHA-256 `0817ef0aa033fd5444eddfbbe203a9f34984d128aab0cc74b2a0e45d64ec1c79`.
- Copia iniziale interrotta: il recupero ha verificato l’intero prefisso già
  ricevuto prima di aggiungere la coda; poi digest completo e ogni voce sono
  stati verificati nuovamente. Nessuna rimozione durante il recupero.
- Resta il rollback completo
  `/var/backups/smartpc-maintenance/rollback-0.10.0-rc.2-20261028-200231`,
  con runtime precedente, configurazioni/dati e relativo manifest. Conservati
  anche i rollback recenti Aquarium e gli snapshot OS previsti dalla policy.
- Esportate e confrontate le prove di manutenzione; rimossa la cartella
  temporanea sulla board e rimossi inventari/script temporanei di questa operazione.
- Controllo finale: 533 hash conformi, GUI pronta, `NRestarts=0`, preferenze,
  dati Gioco e 215 artefatti conservati; sette file OS protetti, hold e insieme
  pacchetti successivo alla rimozione autorizzata invariati. Nessun reboot OS.

[Ricevuta archivio](evidence/v0101-cleanup-2026-10-28/archive-verification.json),
[rimozione](evidence/v0101-cleanup-2026-10-28/cleanup-receipt.json),
[salute finale](evidence/v0101-cleanup-2026-10-28/final-health.json).
