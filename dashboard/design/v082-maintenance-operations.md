# v0.8.2 · Aggiornamenti e recupero

**0.8.2-rc.1**, candidata di manutenzione; navigazione e collocazione delle preferenze restano quelle della v0.8.1. Per router, Wi-Fi e porte consultare le [operazioni Rete](v081-network-operations.md).

## Aggiornare i dati

Apri **Menu → Impostazioni → Dati e aggiornamenti**, scegli la fonte con 2/8 e premi 5. Una richiesta accettata mostra «Aggiornamento in corso»; solo il completamento mostra l'esito. Se è già in corso, oppure il cooldown non è terminato, non parte una seconda acquisizione. Rete può accodare il refresh dell'inventario al batch dello storico già in corso.

**Account ChatGPT** rilegge il file arrivato dal PC. Non avvia la sincronizzazione dell'account online: la schermata dichiara questa distinzione. Dati precedenti mantengono l'ora originale. File assente o invalido conserva l'ultima lettura utilizzabile, senza presentarla come attuale.

**Meteo** può mostrare dati appena acquisiti insieme a «cache non salvata». In quel caso il dato in memoria è valido, ma il ripristino offline al prossimo avvio non è garantito: il refresh non riceve una falsa conferma di successo. Le fonti irraggiungibili conservano i dati precedenti con il loro stato.

La panoramica Sport può alternare le pagine finché non premi un tasto. Dopo il primo input la pagina resta ferma anche aprendo e chiudendo un dettaglio. La rotazione può riprendere dopo uscita e rientro nella famiglia.

## Evidenze e backup

Ricevuta, salute prima/dopo reboot, test e verifier: **`/var/lib/smartpc-dashboard/v082-proof/`**. Non dipendono dalla sopravvivenza di `/tmp`. Il manifest installato è `/opt/smartpc/dashboard/release-manifest.json`.

Backup della consegna: **`/var/backups/smartpc-before-v082-20261008T072838Z`**. Contiene `dashboard`, `config`, `local` e `cache`; quest'ultimo stato include preferenze, temi immutabili e contatori del provider. Il manifest del backup identifica la versione precedente.

Per un rollback ordinario del core, ferma `smartpc-dashboard`, sostituisci `/opt/smartpc/dashboard` con la cartella `dashboard` del backup e riavvia il servizio. Apple Calm 1.2.1 resta compatibile con il contratto precedente. Verifica servizio, manifest e heartbeat prima di dichiarare riuscito il recupero.

Per il recupero completo della transazione è disponibile anche il precedente stato di configurazione/temi/cache. Ripristinalo soltanto se serve e con il servizio fermo: riporta le preferenze e i dati al momento del backup. **Il contatore Casa deve conservare il consumo più recente**; dopo nuove richieste non ripristinare un vecchio ledger come se fosse corrente. Il rollback automatico della prima transazione è stato verificato prima di ulteriori richieste Casa.

[Resoconto, misure e limiti](v082-implementation-report.md). La qualifica software non sostituisce l'uso fisico a 50–60 cm, una prova prolungata o una perdita reale di rete/alimentazione.
