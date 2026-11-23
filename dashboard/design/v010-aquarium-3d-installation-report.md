# Acquario 3D — consegna sulla board

**Aggiornamento finale 29 ottobre 2026: rc.4 installata, 3D attivo, riavvio app e reboot OS verificati con scanout corretto.** [Correzioni e limiti attuali](v010-aquarium-graphics-fix-report.md), [ricevuta](evidence/v010-aquarium-graphics-fix-2026-10-29/implementation-receipt.json). Pannello fisico confermato dall’utente sulla rc.4: «Sì, ora è corretto». Ottica, tasti fisici e durata estesa restano aperti. Le sezioni seguenti conservano la cronologia rc.2 e del recupero display.

La candidata conserva Apple Calm **1.6.5**, Theme API **2.14 / 71 superfici**, quattro tipi e sei pesci persistenti. Al termine della prima consegna il 3D era attivo, senza reboot OS; il successivo reboot richiesto dall’utente ha evidenziato un problema fisico del display. **Stato al recupero rc.2: renderer 2D**, schermata Home leggibile confermata dall’utente. Le prove software precedenti restano storiche e non qualificano il 3D sul pannello.

## Incidente display dopo reboot e recupero

Dopo il riavvio completo del sistema operativo, boot ID `b8c93440-c88c-4d6b-9fe0-df2d36e3283a`, l’utente ha segnalato glitch e assenza di contenuti leggibili. Servizio attivo, heartbeat pronto e connettore DRM abilitato non avevano rilevato il difetto fisico: queste verifiche non equivalgono all’accettazione del pannello.

Applicato e verificato il drop-in persistente `/etc/systemd/system/smartpc-dashboard.service.d/90-aquarium-graphics-recovery.conf`:

```ini
[Service]
Environment=SMARTPC_AQUARIUM_RENDERER=2d
```

Dopo `daemon-reload` e riavvio del solo servizio, il processo effettivo usa `2d`, senza `LD_PRELOAD`; la configurazione speciale del contesto 3D viene esclusa. **Conferma dell’utente: «Sì, ora è leggibile».** Home pronta, servizio attivo/NRestarts0 e **548 file conformi al manifest rc.2**. Non è stato necessario ripristinare il runtime precedente né modificare dati, archivio pesci o preferenze. L’override resta anche agli avvii successivi, ma non è stato eseguito un secondo reboot OS dopo il recupero.

Il recupero circoscrive il problema al percorso grafico attivato con il 3D; non isola ancora la responsabilità tra richiesta del contesto GLES, preload del produttore e interazione con il driver. La risoluzione definitiva richiede confronti controllati e verifica fisica, compresi avvio a freddo, navigazione e rientro dal 3D. Non riattivare automaticamente il 3D sulla sola base degli heartbeat o della media delle callback. Le funzioni 3D/gestione tornano disponibili soltanto dopo una nuova promozione verificata.

[Ricevuta del recupero](evidence/v010-aquarium-3d-install-2026-10-29/display-recovery/recovery-receipt.json). Cattura della memoria di scanout esportata e verificata nel backup privato PC; non è una fotografia del pannello. Area di lavoro sulla board verificata e rimossa, override e rollback conservati.

[Analisi successiva e piano di correzione G0–G5](v010-aquarium-graphics-recovery-analysis.md): controlli read-only sulla board e sorgenti Qt6.8.2; nessuna riattivazione 3D durante l’analisi.

**Seguito concluso:** la comunicazione è tornata disponibile; rc.3 installata e verificata, ma insufficiente a correggere il framebuffer vuoto con cache. La [rc.4](v010-aquarium-graphics-fix-report.md) aggiunge il bypass cache e supera restart/reboot con Home e Acquario corretti nella memoria di scanout. Il renderer corrente è3D;550 hash verificati,218 artefatti Gioco e sei identità/visite conservati. La leggibilità e l’assenza di glitch sul pannello sono state confermate dall’utente; gli FPS ottici e i tasti fisici restano distinti.

## Distribuzione e preservazione

La distribuzione deriva dai **533 file della 0.10.1-rc.1 realmente installata**, con un elenco esplicito del delta Acquario: **548 file**, 24 file aggiornati e 15 nuovi, nessuna rimozione. Tutti i file del Gioco e `libsmartpc_game_native.so` restano identici alla baseline; i lavori Gioco diversi presenti nel checkout non sono stati distribuiti.

Manifest rc.2: `8f210df92292890d1aac76a35ee3d60f3d53c28a8c9fa38188f8d9a043410dbc`. [Delta](evidence/v010-aquarium-3d-install-2026-10-29/release-delta.json), [manifest](evidence/v010-aquarium-3d-install-2026-10-29/release-manifest.json), [ricevuta installazione](evidence/v010-aquarium-3d-install-2026-10-29/board-rc2/installation-rc2-receipt.json).

Preferenze e configurazioni sono state confrontate nei byte; database Gioco e **215 artefatti** nei contenuti. Integrità SQLite/FK verificate. Il tema installato conserva la stessa identità/digest. Servizio attivo, **NRestarts=0**, heartbeat GUI pronto e processo corrente confermato. [Verifica finale](evidence/v010-aquarium-3d-install-2026-10-29/board-rc2/final-verification.json).

## Dipendenze installate

Sono stati installati soltanto sei pacchetti ARM64, dai deb esatti precedentemente verificati:

| Pacchetto | Versione |
| --- | --- |
| libqt6quick3d6 | 6.8.2-5 |
| libqt6quick3druntimerender6 | 6.8.2-5 |
| libqt6quick3dutils6 | 6.8.2-5 |
| libqt6shadertools6 | 6.8.2-3 |
| python3-pyside6.qtquick3d | 6.8.2.1-4 |
| qml6-module-qtquick3d | 6.8.2-5 |

Nessun pacchetto precedente è stato aggiornato/rimosso e gli hold sono invariati. Nessuna sostituzione di driver o modifica del governor. Il launcher applica il collegamento alla GLES del produttore prima di avviare Python; nel processo installato sono verificate le librerie PowerVR, GLES e Quick3D effettivamente mappate. [Anteprima apt](evidence/v010-aquarium-3d-install-2026-10-29/apt-preview.txt), [installazione apt](evidence/v010-aquarium-3d-install-2026-10-29/apt-install.txt).

## Prove della consegna

- **PC:** quattro suite mirate su archivio, contratto, runtime API e core temi; workflow grafico della candidata. Il primo banco grafico non aveva il renderer Canvas diagnostico richiesto dal suo harness: aggiunto soltanto al pacchetto di diagnosi, poi passaggio positivo. Non distribuito nel runtime.
- **ARM:** archivio14, contratto e core temi passati. API runtime: **39 test passati, uno skip esplicito per qmllint assente**; il controllo reale qmllint passa sul PC, dove i40 test sono eseguiti. Il primo invio ARM senza questa distinzione è conservato come3/4 suite, non trasformato retroattivamente in PASS. Nei contratti è inoltre dichiarato lo skip del validatore JSON Schema indipendente non installato.
- **EGLFS 960×640 sulla candidata rc.1:** 21 controlli per ciascuno di Base, Functional e Apple Calm; stato/salvataggio, gestione presentata, sostituzione, storico, pausa, urgenti e Reduced/Off. Navigazione Home/Meteo/Account/Sport/Casa/Rete/Acquario/Gioco e avvio/pausa/salvataggio del pilota Crono su archivio privato, senza training o modifica dei piloti reali.
- **Servizio installato:** apertura dell’Acquario e della gestione tramite eventi sintetici sul dispositivo evdev del tastierino dedicato. Sei individui/quattro specie nel database reale, tutti con ACK di presentazione. Identità e permanenze conservate dopo un ulteriore riavvio dell’applicazione. Nessuna pressione fisica dei tasti è dichiarata provata.

[Ricevuta EGLFS rc.1](evidence/v010-aquarium-3d-install-2026-10-29/board/qualification-receipt.json), [controllo vivo rc.2](evidence/v010-aquarium-3d-install-2026-10-29/board-rc2/live-receipt.json), [persistenza rc.2](evidence/v010-aquarium-3d-install-2026-10-29/board-rc2/persistence-rc2-receipt.json).

La verifica del riavvio reale della rc.1 ha trovato sei avvisi `mesh.valid` durante la distruzione degli attori. La **rc.2** aggiunge il controllo del riferimento nullo, mantenendo lo stesso risultato durante il rendering normale. È stata nuovamente verificata con21 controlli EGLFS brevi, poi installata e ricontrollata nel servizio e dopo il riavvio: **zero problemi QML/grafici nel journal dei processi rc.2**.

Il journal conserva anche eccezioni di chiusura dei semafori `multiprocessing` (`sem_unlink` / FileNotFoundError), già riscontrate numerose volte nei processi della baseline0.10.1 prima della consegna. Non sono state nascoste né corrette modificando il Gioco fuori perimetro: la verifica finale distingue questi eventi noti dagli errori QML/grafici e dalle eccezioni non classificate.

## Prestazioni e attribuzione

Una nuova misura sulla distribuzione selezionata **rc.1**, Apple Calm, sei pesci e clock attivo, usa **120 secondi dopo60 di riscaldamento**: **59,967 callback/s**, p95 **18,07 ms**. Dati grezzi, p99/massimo/stalli e risorse sono nel [report nominale](evidence/v010-aquarium-3d-install-2026-10-29/board/qualification/apple/report.json).

La correzione rc.2 riguarda soltanto il caso in cui la mesh è già distrutta. Il campione120s resta attribuito alla rc.1; la rc.2 dispone della [prova EGLFS breve](evidence/v010-aquarium-3d-install-2026-10-29/board-rc2/apple/report.json), **59,91 callback/s / p95 18,25 ms**, e della verifica del processo realmente installato. Non viene inventata una nuova misura120s sui byte rc.2.

Le misure sono callback/pose software in un banco con provider privati: non FPS ottici o tempi GPU. Restano aperti ripetibilità estesa, test30/60min e24/7, carichi live concorrenti, valutazione artistica sul pannello e analisi dei caricamenti/transizioni a freddo. Il precedente stallo308ms nel banco breve resta nel report di implementazione. La candidata è installata; non è promossa a stabile.

## Backup e rollback

Rollback completo verificato sulla board:

`/var/backups/smartpc-maintenance/rollback-0.10.1-rc.1-aquarium3d-20261029-121954`

Contiene runtime0.10.1, configurazioni, dati applicativi e runtime Python con proprietari/permessi preservati. Copia PC privata verificata su **3270 file e4 link**, archivio SHA256 `95fed0ca695ad0be73d6a27cd73076a88d045015401b33fff473bca1a64b3b06`: [ricevuta di esportazione](evidence/v010-aquarium-3d-install-2026-10-29/rollback-export-receipt.json).

Per ripristinare il solo runtime precedente, conservando dati/preferenze correnti e il nuovo archivio Acquario:

```sh
sudo python3 /var/backups/smartpc-maintenance/restore-aquarium3d-0.10.2.py
```

Il comando è preparato e controlla versione/hash; non è stato eseguito come prova di rollback. Le dipendenze Qt aggiunte restano installate durante questo recupero. Il vecchio runtime riapre l’Acquario2D; l’archivio3D resta conservato per una successiva riattivazione.

L’area temporanea `maintenance-work` è stata esportata fuori da Git, verificata su2407 file/link e rimossa dopo un secondo confronto dei contenuti, secondo la policy. [Ricevuta di pulizia](evidence/v010-aquarium-3d-install-2026-10-29/cleanup-receipt.json). Gli archivi privati includono configurazioni: non sono allegati alle evidenze pubbliche del progetto.

Compagno **0.11**, Memoria/AI **0.12**, Stabilità **1.1** invariati.
