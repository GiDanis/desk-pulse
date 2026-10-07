# Manutenzione v0.7 · 0.7.0-rc.2

6 ottobre 2026. Revisione di pulizia, ordine e correzioni della candidata Casa, installata sulla Orange Pi. La baseline stabile resta la v0.6.6; quota effettiva, latenza e collaudi dei dispositivi fisici conservano i gate della [consegna iniziale](v07-implementation-report.md).

## Interventi

- Acquisizione Casa: salvataggio atomico, flush e fsync eseguiti nel worker. L'interfaccia continua a elaborare eventi mentre il disco scrive. L'esito pubblico arriva soltanto dopo il salvataggio; un errore conserva la snapshot precedente e conclude l'azione come fallita. La chiusura prima del salvataggio interrompe l'acquisizione.
- Scheduler: il rifiuto del ledger blocca davvero il ciclo accelerato; il suo ritorno non viene più ignorato. La scadenza della quota produce una notifica di cambio, senza invalidare l'interfaccia ogni cinque secondi a stato invariato. Una lettura manuale riuscita riabilita il polling precedentemente fermato da un errore, se quota e preferenza lo consentono. Il provider chiuso rifiuta il cambio di polling.
- Cache: validazione esplicita di dispositivi, preferiti e codici osservati, prima di normalizzazioni e operazioni su insiemi. Una stringa al posto della lista di codici non viene interpretata come una sequenza di singoli caratteri. Cache malformate sono scartate; dati assenti non diventano valori correnti.
- Riepilogo Casa: un dato secondario precedente, per esempio l'umidità non più restituita, rende visibile l'indicazione di dato precedente anche se la temperatura primaria è attuale. Il dettaglio conserva la qualità indipendente delle singole metriche.
- Launcher: i servizi sono chiusi anche quando Main.qml non riesce a inizializzarsi, passando attraverso lo stesso finally dell'uscita normale.
- Pulizia: rimossi 57 import inutilizzati e assegnazioni/stato privato senza letture; conservati i riferimenti necessari a mantenere vivi gli oggetti Qt. Formattati provider/core Casa e relativi controlli. Nessuna rimozione di documentazione, fixture, cache o progetto tema.
- Verifiche storiche: tolti conteggi di presentazioni/superfici anteriori a Casa; il confronto usa il registro/contratto corrente. Il test dei risultati F1 sceglie la gara registrata anziché l'ultimo evento relativo alla data di esecuzione. L'attesa fissa del candidato è sostituita dalla verifica effettiva di readiness. Il gate qmllint usa un livello supportato da Qt 6.8, mantenendo zero warning ammessi e il controllo positivo della proprietà errata.

Il checkout conteneva già Casa e modifiche Theme non committate. Sono preservate: `baseline.json` registra stato e hash iniziali; `maintenance-files.json` distingue i 47 file Python modificati durante questa revisione. Nessun commit o tag è stato creato.

## Verifiche

| Prova | Esito e perimetro |
| --- | --- |
| Statico | Ruff: 66 segnalazioni iniziali, zero finali; sintassi di 136 file Python verificata. |
| PC coerente con board | 64 casi/suite superati con Python 3.12.14 e PySide6 6.8.2.1 / Qt 6.8.2. Il primo giro di questo ambiente rilevava un flag qmllint incompatibile; il gate corretto passa nel rerun conservato separatamente. |
| Core Casa / Tuya | 21 e 22 test, rispettivamente, sul PC e sulla board. Risposte simulate; cache, contatori e concorrenza reali su file temporanei. |
| Board offscreen | 21 controlli mirati superati, comprendenti launcher, provider/UI Casa, Dashboard/Settings, adapter pubblici, bundle, caricamento, layout, contesti pending e corpus strutturale. Qt 6.8.2. |
| Display EGLFS/KMS | Casa Base giorno e Functional notte a 960×640: 11 scenari ciascuno, zero avvisi QML. I dati e la quota di questi scenari sono sintetici. |
| Cache di produzione sul display | Inventario reale salvato: 16 dispositivi e 4 preferiti, overview e dettaglio EGLFS; dati esplicitamente precedenti e nessuna nuova richiesta cloud. |
| Installazione | 454 file runtime verificati per SHA-256; nessun renderer diagnostico nella distribuzione. |
| Stato conservato | Hash delle preferenze e del ledger invariati, contatore ancora 8, inventario e preferiti conservati; zero chiamate Casa aggiuntive. |
| Servizio | Dopo riavvio del servizio: active/running, NRestarts=0 e nessun errore QML/Python nel journal controllato. Nessun reboot del sistema operativo in questa revisione. |

[Evidenze, manifest, esiti iniziali e finali](evidence/v07-maintenance-2026-10-06/README.md).

La prima suite sul PC usava Python 3.14 e Qt 6.10.3: alcune prove dei bundle esterni andavano in timeout, mentre gli stessi controlli passano nel runtime Qt 6.8.2. Quella esecuzione fallita rimane nelle evidenze e **non certifica Qt 6.10**. Le dipendenze di sviluppo sono ora fissate in `requirements-dev.txt` sul target effettivamente verificato. Questa revisione non misura GPU/FPS né ripete tutta la matrice storica di temi, motion e varianti.

## Uso delle verifiche e recupero

Dalla radice del repository, dopo aver creato l'ambiente Python 3.12 e installato `requirements-dev.txt`:

```bash
.venv/bin/ruff check dashboard scripts
.venv/bin/python scripts/check-dashboard.py --suite all --output-dir /tmp/smartpc-checks
```

Il runner isola ogni processo e il suo stato, registra output ed esito, applica un timeout e restituisce errore se almeno una verifica fallisce. `--suite core`, `--suite ui` e `--case` consentono controlli mirati. Il probe Casa che consuma quota è escluso.

Backup privato: `/var/backups/smartpc-before-v07-maintenance-20261006T123131Z`, con runtime precedente, stato e cache. Per tornare alla rc.1, fermare il servizio, ripristinare il solo runtime dal backup e riavviare. Conservare il ledger e lo stato attuali: il rollback del software non deve azzerare il consumo o sovrascrivere preferenze più recenti.

La rc.2 mantiene Casa utilizzabile in consultazione manuale. L'attivazione continuativa del polling resta subordinata alla policy reale; nessun nuovo collaudo fisico, comando ai dispositivi o interruzione della rete domestica è stato eseguito.
