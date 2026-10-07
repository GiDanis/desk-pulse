# v0.7 Casa / Smart Life · consegna della candidata

**6 ottobre 2026 · versione 0.7.0-rc.1.** Il modulo Casa è implementato e installato sulla Orange Pi. Si usa Tuya Cloud direttamente nello stesso processo della dashboard, con un worker asincrono. Nessun Home Assistant, server aggiuntivo o comando ai dispositivi.

La candidata permette la consultazione reale e gli aggiornamenti manuali. **Il polling continuativo resta disattivato finché non sono noti quota effettiva, consumo condiviso e scadenza del progetto.** I collaudi fisici e la latenza rispetto a Smart Life rimangono criteri di uscita dalla candidata; non sono dichiarati superati.

## Comportamento consegnato

- Casa nel carosello quando esistono collegamento e preferiti: quattro grandi tessere in Base, quattro righe in Functional; testo e icona oltre al colore.
- Inventario completo paginato, dettaglio di ogni dispositivo e preferiti modificabili/ordinabili dalle impostazioni. I quattro iniziali sono proposte modificabili.
- Lettura cumulativa inventario/stati, token riutilizzato, specifiche soltanto per i preferiti nuovi/modificati o dopo un giorno. Paginazione completa prima di pubblicare il risultato.
- Disponibilità dichiarata dal cloud distinta dall'ultimo valore riportato. Un dispositivo offline può avere un vecchio interruttore acceso; il display mostra entrambe le informazioni. Cache e campi mancanti non diventano dati attuali, zero o falso.
- Cache privata atomica, associata a progetto/account, e contatore persistente prima dell'invio. Scrittori serializzati con lock/rilettura, file e directory sincronizzati su disco. Preferiti, nomi e ordine seguono l'identità del dispositivo.
- Aggiunte scoperte dal successivo aggiornamento, rinomina senza perdita del preferito; rimozione dopo due inventari completi. Un preferito rimosso resta riconoscibile fino alla deselezione. Errori o pagine incomplete conservano l'ultimo inventario completo.
- Scheduler pronto: 5 minuti ordinari, fino a 1 minuto durante la consultazione, massimo 2 ore/giorno UTC, margine del 20%, backoff e sospensione per autorizzazione/quota/scadenza. Senza policy effettiva: una discovery iniziale in assenza di cache, poi refresh manuali con limite persistente di 100 richieste aggiuntive.
- Conferma del refresh solo dopo risposta completa e cache salvata: il broker pubblico mantiene l'azione in attesa e la conclude con esito reale. Un errore di rete o disco non viene confermato come successo.

[Guida d'uso e configurazione quota](v07-casa-operations.md). Il telefono continua ad associare dispositivi da Smart Life; il progetto conserva il collegamento Automatic Link. Il display non sostituisce l'hub Zigbee e non promette rilevamento istantaneo di movimento.

## Evidenze

| Livello | Risultato | Limite della prova |
| --- | --- | --- |
| Client Tuya | 22 test passati su PC e board | Risposte simulate: firma, autenticazione/rinnovo, tipi e cache. |
| Core Casa | 19 test passati su PC e board | Paginazione, campi falsi/zero/non verificati, cambi inventario, clock, quota, cache e scrittori concorrenti. |
| Qt e Main | 8 scenari su PC; 8 sulla board Qt 6.8.2 | Worker, single flight, cache offline/nuovo provider, disco non scrivibile, scheduler/limite accelerazione/scadenza, preferiti/navigazione e broker pending→failed. I/O simulato. |
| Display reale | EGLFS/KMS 960×640, Base giorno e Functional notte; nessun avviso QML | Scenari sintetici sul display; niente benchmark GPU o tastiera fisica. |
| Cache reale nel display | 16 dispositivi, 4 preferiti; overview/dettaglio EGLFS, dati marcati precedenti; nessun avviso | Harness diagnostico con stessi file runtime, preferenze isolate e cache reale; nessuna ulteriore chiamata cloud. |
| Cloud dalla board | 6 GET del primo avvio + 2 del probe successivo; 16 dispositivi, 7 online e 9 offline secondo Tuya | Nessun cambio fisico provocato. Il consumo precedente dell'analisi e altri client non sono inclusi nel contatore locale. |
| Theme API | 31 test contratto, 31 runtime PC con qmllint; 48 adapter/17 contesti su PC e board | Estensione additiva 2.1; import 2.0 conservato. Nessuna certificazione di bundle autori arbitrari. |
| Temi e impostazioni | 26 test bundle, 5 profili; regressioni Dashboard/Settings e broker impostazioni passate | Payload dei vecchi bundle immutabile; fallback effettivo Base per le quattro superfici Casa. |
| Corpus | 140 scenari strutturali / 112 requisiti; 4 superfici Casa × 2 profili UI | Non è stata ripetuta l'intera matrice UI storica dei temi. |
| Distribuzione | 453 file verificati per hash, credenziali 600 fuori dal pacchetto, preferenze conservate | Checkout di lavoro con modifiche preesistenti; nessun tag Git di rilascio. |
| Riavvio reale | Boot ID cambiato; servizio active/running e NRestarts=0; 16 dispositivi, 4 preferiti e 8 chiamate conservati; hash/preferenze invariati, nessun avviso QML | Rete disponibile durante il reboot: non è una prova di avvio con rete fisicamente assente. |

[JSON, manifest e schermate delle verifiche](evidence/v07-implementation-2026-10-06/README.md). La verifica precedentemente documentata del 6 ottobre consumava altre 8 chiamate sul PC: resta distinta dalle 8 chiamate del provider installato sulla board.

Nel campione reale il sensore T & H riporta **26,5 °C, 54% umidità e 25% batteria**. Presa Zigbee, lampada e sensore di movimento risultano offline; i valori salvati sono presentati come precedenti. Questa è una fotografia della risposta cloud, non una prova che i dispositivi fisici abbiano quello stato.

## Installazione, attribuzione e recupero

Runtime: `/opt/smartpc/dashboard`, servizio `smartpc-dashboard`. Versione esplicita in `version.py`; manifest ricorsivo con commit di riferimento `df4d7c15bbb3f98b4d9e5963c0a966a3137ad5b2` e `dirty=true`. I file installati corrispondono al manifest consegnato.

Backup della v0.6.6 precedente: `/var/backups/smartpc-before-v07-20261006T105223Z`. Backup prima dell'ultimo aggiornamento del contatore: `/var/backups/smartpc-before-v07-20261006T105853Z`. Directory private, con runtime, stato e cache. Il file preferenze `Dashboard.conf` conserva lo stesso hash prima/dopo l'installazione. Credenziali trasferite nel percorso privato del servizio, proprietario smartpc e permessi 600; non entrano nel pacchetto, nelle schermate o nei report.

Il checkout aveva già modifiche Theme a Main, NotificationHost, adapter/test e strumenti/runtime dei bundle; inoltre `theme-projects/` era già presente. Sono state preservate. Il build usa il checkout corrente e include quelle modifiche precedenti dei file dashboard: non vengono attribuite a Casa. La patch precedente è conservata fra le evidenze per distinguere le responsabilità; `theme-projects/` non fa parte della distribuzione dashboard. Non sono stati creati commit o tag.

Per rollback, fermare il servizio e ripristinare soltanto il runtime dal backup della v0.6.6, poi riavviare. Conservare credenziali, preferiti e soprattutto il ledger attuale: non azzerare consumo o stato per cambiare versione. La baseline non usa il provider Casa.

## Decisione e prove ancora necessarie

**Implementazione consegnata come candidata utilizzabile in consultazione manuale.** Per la v0.7 finale servono:

1. Quota/consumo/scadenza effettivi dalla console Tuya e attivazione controllata del polling; nessun riferimento di listino sostituisce questi valori.
2. Per ogni preferito, confronto app/dispositivo/display con cambi reali, misura della latenza, spegnimento del dispositivo e del gateway pertinente.
3. Aggiunta/rinomina/rimozione reale da Smart Life, rinnovo/revoca account e recupero dopo interruzione fisica della rete, compreso avvio senza rete.

Riconnessione, errori e riavvio del provider sono verificati con trasporti simulati; i dispositivi fisici non sono stati accesi/spenti. Le azioni sul display restano scelte dell'interfaccia e della configurazione; eventuali comandi ai dispositivi richiedono una versione successiva con azioni nominate e provate.
