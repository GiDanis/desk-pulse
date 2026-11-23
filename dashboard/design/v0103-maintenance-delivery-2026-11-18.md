# Manutenzione 0.10.3-rc.1 — installata sulla Orange Pi

18 novembre 2026 · seguito autorizzato dell’[audit del 17 novembre](v0102-continuous-audit-2026-11-17.md).

**Installata e verificata nel servizio reale.** Runtime **551 file**, Apple Calm **1.7.0** conservato, GUI pronta, `NRestarts=0`. Le correzioni riguardano misure, conferme Acquario, memoria in inattività e conflitto della ventola. Nessun reboot OS, nessuna sostituzione del codice di ricerca Gioco o delle librerie native con quelle del checkout.

## Correzioni consegnate

| Ambito | Comportamento risultante |
| --- | --- |
| Soak | Identifica la GUI dal heartbeat, verifica discendenza dal supervisore e token di inizio processo. Rileva GUI assente, PID riutilizzato, cambio processo, readiness persa o heartbeat scaduto. Distingue GUI, supervisore, helper e memoria del cgroup; registra CPU, RSS/PSS, thread/FD, temperatura e vista. Campioni limitati agli ultimi 10.000. |
| Conferme Acquario | Le azioni pubbliche `prepared`, `shown` e `change` restano pendenti fino all’esito del worker, correlato al request ID. La conferma non deriva più dal solo accodamento. |
| Recupero Acquario | Le ricevute del renderer attendono `completed`, evitano invii duplicati mentre la richiesta è pendente e ritentano gli errori accettati con attesa, fino a tre tentativi. Un cambio di target azzera la vecchia ricevuta. Errori e istruzione di recupero restano visibili anche nella scena normalmente in movimento. Il commit di un candidato già applicato non duplica la visita. |
| Metadati Gioco | Il processo di sola lettura viene chiuso dopo 60 s senza richieste. La proiezione del menu resta nella GUI; una richiesta successiva riavvia il lettore. Nessun intervento sul processo del learner o sui modelli. |
| Persistenza Acquario | Una popolazione fissa senza candidati non scrive più `lastTime` a ogni riconciliazione. Il watermark rimane in memoria e viene persistito nei comandi e alla chiusura; le visite temporizzate conservano il checkpoint durevole precedente. La riconciliazione invariata non pubblica un aggiornamento UI. Anche `shown` già registrato evita una nuova scrittura. |
| Ventola/OS | Individuata la configurazione vendor: `orangepi-hardware-optimization`, ramo `orangepizero3w`, esporta GPIO101/PD5 e lo porta alto. Il nuovo servizio preserva **out/high** e scollega il controller PWM concorrente. Nessun cambiamento a kernel, device tree, governor, bootloader o recupero del display. |
| Ambiente PC | Creato un ambiente separato con interprete Python 3.12.13 copiato, PySide6 6.8.2.1/Qt 6.8.2, NumPy 2.2.6 e neat-python 1.1.0. Aggiunto controllo esplicito dell’ambiente prima della qualifica. La board conserva Python 3.13.5/Qt 6.8.2, verificati direttamente. |

La minore persistenza della popolazione fissa non costituisce un journal continuo dell’orologio: in caso di perdita improvvisa di alimentazione vale l’ultimo checkpoint durevole, non il watermark solo in RAM. Non vengono effettuate rotazioni finché non si riconciliano i dati; i comandi salvano il watermark e le popolazioni con calendario mantengono la persistenza precedente. Le prove coprono arretramento durante l’esecuzione e dopo chiusura/riapertura.

Il controllo ventola mantiene l’impostazione elettrica originaria. La lettura GPIO alta e l’assenza di errori PWM **non sono una verifica fisica della rotazione**. Il servizio è abilitato per l’avvio successivo; il prossimo boot non è stato provato in questa consegna.

## Provenienza dei byte

| Oggetto | Identità |
| --- | --- |
| Baseline installata rc.5, 550 file | `7b33780f75ce4496089365ae7ad9ab2d5178f5051c4be02cf18b938ff732d1cd` |
| Runtime rc.1, 551 file | `bc2cce895a4d0a9443ff60a5d8fe7d52ecdd00cf20cc9e7489c105ad3d501f6e` |
| Apple Calm 1.7.0 invariato | `daf0a7b1cc0bc19bd2931765b14714dc1dadf685025df337541a65fe9b78d376` |

Il pacchetto è costruito con `--baseline-manifest` da una copia della rc.5 con tutti gli hash verificati, aggiungendo esplicitamente il nuovo componente QML. Il delta ammesso è di dieci file: `Main.qml`, `aquarium.py`, `aquarium_population.py`, `aquarium_store.py`, `game_metadata.py`, i tre componenti `Aquarium3DVisual.qml`/`Fish3DActor.qml`/`AquariumAcknowledgement.qml`, `soak.py` e `version.py`. Tutti gli altri byte della baseline, comprese le due librerie native e il motore Gioco, sono conservati.

Il checkout contiene ancora ricerca Gioco preesistente diversa dalla baseline; **il numero di versione del checkout non rende distribuibile l’intero checkout**. I sorgenti effettivamente consegnati e il manifest sono nella [distribuzione verificata](evidence/v0103-maintenance-2026-11-18/runtime/release-manifest.json). Theme API resta 2.15, con 71 superfici e fingerprint invariato.

## Verifiche

**Sette casi selezionati positivi sul PC e sette sulla board**, eseguiti sulla baseline con il solo delta di manutenzione: ciclo di vita dell’app, Acquario, popolazione, nuove regressioni di continuità, commit asincrono reale Main/Theme API, azioni pubbliche e adapter API. Le nuove prove comprendono PID errato/riutilizzato/assente, heartbeat scaduto, rilascio e riapertura del lettore senza cambiare i piloti, assenza di scritture nella popolazione fissa, clock arretrato, ricevute pendenti/fallite/completate e retry limitato.

La prova Main con errore SQLite controllato verifica: risultato iniziale pendente, errore tardivo riportato, candidato ancora presente, retry con un solo incremento dello storico, replay senza seconda visita e rilascio della richiesta dal broker. I dati sono isolati. Il banco software PC forza il renderer 2D per il test del routing; il rendering 3D è verificato separatamente su EGLFS.

**Tre temi EGLFS 960×640**, 21 controlli ciascuno, zero warning QML nei report finali. Provati gestione, salvataggio, sostituzione di un pesce conservando gli altri cinque e lo storico, pausa/ripresa, urgenza e movimento ridotto/disattivato. Contesto driver e Qt RHI riconoscono GLES 3.2; ponte EGL e bypass shader cache restano quelli qualificati della baseline.

| Tema, finestra finale | Callback | Pose | p95 software |
| --- | ---: | ---: | ---: |
| Base, circa 8 s | 482 | 482 | 18,78 ms |
| Functional, circa 8 s | 479 | 480 | 17,81 ms |
| Apple Calm, circa 8 s | 480 | 480 | 17,96 ms |

Questi valori sono callback e avanzamenti software di una finestra sintetica; non FPS ottici, latenza di input o confronto controllato del consumo. Il primo campione Base, con backup ancora in corso, conteneva soltanto due callback ed è escluso dalla qualifica del movimento. Una successiva sonda diagnostica accedeva a una proprietà del wrapper errata: il banco è stato corretto e la finestra Base finale include stato `moving=true` all’inizio e alla fine. Le ricevute precedenti sono conservate. Non è dimostrata la causa della prima finestra statica.

I primi test UI PC erano privi dei renderer di fixture, esclusi correttamente dal runtime: sono stati aggiunti al solo staging diagnostico. Il primo controllo dell’ambiente ARM assumeva Python 3.11; la lettura live ha stabilito 3.13.5 e il controllo è stato corretto. La board non è stata aggiornata per soddisfare il banco. Restano nel rapporto lint due import inutilizzati **preesistenti** di `aquarium_population.py` (`time`, `Property`); non sono nascosti come lint positivo.

[Riepilogo delle qualifiche e limiti](evidence/v0103-maintenance-2026-11-18/qualification.json), [ARM](evidence/v0103-maintenance-2026-11-18/board/arm-checks/checks.json), [ambiente PC](evidence/v0103-maintenance-2026-11-18/environment.json), [ambiente ARM](evidence/v0103-maintenance-2026-11-18/board/arm-environment.json).

## Servizio reale dopo l’attivazione

Stesso boot, supervisore PID 122816 e GUI PID 122827. Profilo EGLFS/OpenGL, ponte EGL e shader cache verificati nel processo installato. **551/551 hash**, heartbeat pronto, Apple Calm originale e `NRestarts=0`. Nessun warning QML/grafico rilevato nel journal della nuova invocation; scanout effettivo acquisito senza sonde nel processo della GUI.

Osservazione passiva **150 s / 30 campioni** su `home.now`: RSS GUI 301.952–303.600 KiB, CPU media circa **1,16% di un core**. Thread 15–18 e FD 47–55 durante l’assestamento. Il lettore metadati passa da **110.896 KiB PSS** a processo terminato, circa **108,3 MiB liberati**; rimane il piccolo resource tracker. Il confronto della RSS GUI con i quattro giorni della rc.5 non è controllato e non dimostra un risparmio globale o assenza di leak.

**Zero nuovi errori del conflitto fan/PWM dopo il passaggio**, GPIO101 ancora out/high, servizio abilitato. Sensori nell’ultima lettura circa 57,6–59,3 °C. Restano i meccanismi di raffreddamento CPU del kernel; viene scollegato soltanto il controller PWM in conflitto con il GPIO già posseduto dalla configurazione vendor.

[Ricevuta di installazione](evidence/v0103-maintenance-2026-11-18/board/installation.json), [salute finale](evidence/v0103-maintenance-2026-11-18/board/final-health.json), [30 campioni effettivi](evidence/v0103-maintenance-2026-11-18/board/installed-soak.json), [scanout Home convertito senza modifiche](evidence/v0103-maintenance-2026-11-18/board/scanout/installed-home.png). Lo scanout mostra la GUI installata in modalità notturna con luminosità originale, non una fotografia del pannello.

## Conservazione, rollback e pulizia

Servizio arrestato ordinatamente prima della copia. Verificati originali e snapshot su **2.577 file**, contenuti, uid/gid, permessi, timestamp, symlink e gruppi hardlink; sette database controllati su copie disposable con i rispettivi WAL/SHM. Archivio completo **2.766 membri**, SHA-256 `31af9c6adb436aeec64978942b97d76d26a18a0cfa0b050994e40998b5f6d450`, gzip consumato fino a CRC/trailer. Copia PC verificata membro per membro **prima** di sostituire il runtime.

Preservati esattamente il database Gioco e i **218 artefatti**, il database Acquario con **sei identità e sei visite**, **44 preferenze** e la selezione Apple Calm 1.7.0. Nessun reset, migrazione dei piloti, apprendimento implicito o modifica a CopyTrade, agli ambienti Python della board e alle politiche di aggiornamento.

Rollback e snapshot durevole: `/var/backups/smartpc-dashboard/20261118-continuous-rc1/`, con `previous-runtime` e `snapshot`. Archivio privato PC: `/home/giuseppe/.local/share/smartpc-private-backups/20261118-continuous-rc1/before.tar.gz`. L’installatore contiene il ripristino coordinato di runtime, dati e proprietà in caso di fallimento; non è stato necessario attivarlo. Un ripristino futuro deve tenere conto dei dati maturati dopo questa consegna.

Esportato anche tutto il lavoro temporaneo: **922 voci / 866 file**, contenuti e metadati verificati sul PC e gzip completo, nessun hardlink. Solo dopo la verifica e l’assenza di processi che lo usassero è stato rimosso `maintenance-work`, insieme ai due archivi RAM. Restano rollback, snapshot, dati e preferenze. Spazio libero dopo la pulizia: **16.803.303.424 byte**, circa **15,65 GiB**.

[Backup esterno verificato](evidence/v0103-maintenance-2026-11-18/external-backup.json), [lavoro esportato e verificato](evidence/v0103-maintenance-2026-11-18/work-external-verification.json), [pulizia](evidence/v0103-maintenance-2026-11-18/cleanup.json).

## Uso e limiti residui

Ambiente PC creato: `/home/giuseppe/.local/share/smartpc-maintenance-py312-qt682/bin/python`. Usarlo con `scripts/check-dashboard-environment.py` prima delle verifiche; il venv precedente non è stato sovrascritto. La preparazione portabile è aggiornata nel README, con `--copies` e controllo delle versioni.

Il nuovo `soak.py` è installato e può essere eseguito in sola osservazione, per esempio `sudo python3 /opt/smartpc/dashboard/soak.py 1800 --interval 10 --output /tmp/smartpc-soak.json`. Non è stato creato alcun monitor ricorrente.

La release rimane una candidata: non sono stati eseguiti un nuovo reboot OS, una qualifica prolungata 24 h/7 giorni, Gara/apprendimento concorrenti alle fonti, verifica ottica del pannello/FPS, tastierino fisico, conferma fisica della ventola o prove live goal/VAR e motorsport. Le verifiche mirate e il campione di 150 s non sostituiscono questi gate né la matrice estesa.
