# v0.7 Casa · proposta di polling entro la quota Trial

> Aggiornamento 6 ottobre: il modulo è implementato nella candidata v0.7.0-rc.1. [Consegna e verifiche attuali](v07-implementation-report.md), [uso e quota](v07-casa-operations.md). Il testo sotto conserva l’analisi e le evidenze antecedenti.

**1 ottobre 2026. Stato: proposta, scheduling non implementato.** La prova API resta manuale. Non usare il probe periodicamente come provider: riacquisisce il token e rilegge le specifiche a ogni avvio.

**Ricontrollo 6 ottobre:** risposta cumulativa e parametri pagina ancora funzionanti; [evidenze](evidence/v07-readiness-2026-10-06/README.md). La [revisione prima dell'implementazione](v07-implementation-readiness.md) precisa contatore prima dell'invio, persistenza attraverso reboot/clock, esito asincrono del refresh e budget per pagine aggiuntive. Polling continuativo subordinato a quota assegnata, consumo e scadenza della console; 26.000 non viene assunto come saldo disponibile.

## Dato verificato per ridurre le chiamate

Provata sul cloud reale `GET /v1.0/users/{uid}/devices?page_no=1&page_size=50`: 16 dispositivi, tutti con disponibilità booleana; 10 con un elenco di stati, 83 campi complessivi. Sensore movimento, temperatura/umidità, presa e le due lampade hanno stati nella risposta. Sei dispositivi non espongono un elenco di stati: non vanno trasformati in spenti o zeri. Due richieste per questa verifica, inclusa l'autenticazione iniziale.

Questa API può aggiornare insieme elenco, nomi, disponibilità e stati, con una chiamata per pagina. Per i 16 dispositivi attuali una pagina basta. La freschezza delle variazioni rispetto all'app/pulsante va ancora misurata: il risultato resta l'ultimo stato riportato dal cloud. [API Smart Home](https://developer.tuya.com/en/docs/cloud/ad2823ae46?id=Kconjtzq1vk1q).

## Budget di riferimento

La documentazione Tuya indica circa 26.000 chiamate/mese per Trial, con una ripartizione esemplificativa della risorsa tra API e messaggi. Quota, allocazione e scadenza effettive devono essere lette dalla console dell'account; l'accesso API riuscito non prova un servizio gratuito permanente. Trial non permette eccedenze: esaurita la risorsa, il servizio viene sospeso fino al rinnovo mensile della quota. [Pricing ufficiale](https://developer.tuya.com/en/docs/iot/membership-service?id=K9m8k45jwvg9j).

Stime aritmetiche su 30 giorni, una pagina per ciclo; escluse autenticazione, specifiche, retry e aggiornamenti manuali:

| Strategia | GET/mese |
| --- | ---: |
| Quattro letture di stato separate ogni minuto, 24/7 | 172.800 |
| Una lettura cumulativa ogni minuto, 24/7 | 43.200 |
| Una lettura cumulativa ogni due minuti, 24/7 | 21.600 |
| Una lettura cumulativa ogni tre minuti, 24/7 | 14.400 |
| Una lettura cumulativa ogni cinque minuti, 24/7 | 8.640 |
| Un minuto per due ore/giorno, cinque minuti nelle altre 22 ore | 11.520 |

Lanciare il probe attuale da 10 chiamate ogni cinque minuti consumerebbe 86.400 richieste/mese. Il futuro provider deve vivere nel backend già presente, riutilizzare il token e mantenere le specifiche in cache.

## Policy proposta

- **Base:** una lettura cumulativa ogni cinque minuti, anche con Casa nascosta. La stessa lettura scopre aggiunte/rinomine: nessun polling distinto dell'inventario.
- **Consultazione:** aggiornamento all'ingresso in Casa se il dato non è già recente; poi ogni minuto. Per il budget di riferimento, limitare l'accelerazione a due ore cumulative/giorno, quindi tornare ai cinque minuti. La frequenza deve adattarsi alla quota effettiva.
- **Specifiche:** cache persistente per i dispositivi selezionati, rilettura al cambio di identità/modello o di codici e al massimo una verifica giornaliera ordinaria. Niente GET delle specifiche per ogni aggiornamento di stato. Le richieste fallite non innescano nuove letture senza limite.
- **Token:** mantenuto in memoria e rinnovato alla scadenza dichiarata dall'API. Non avviare un processo nuovo per ogni polling. Conteggiare conservativamente anche autenticazioni/retry nel budget locale.
- **Aggiornamento manuale:** debounce, nessuna richiesta parallela o timer duplicato; condivide il budget del polling.
- **Quota:** pianificare sul massimo dell'80% del budget effettivo, lasciando il 20% a prove, retry e altri client/progetti cloud. Contatore persistente e confronto con le statistiche Tuya: il contatore locale non misura il consumo degli altri client.
- **Errori:** backoff progressivo; quota/servizio scaduto non diventano tentativi rapidi continui. Cache precedente con ora del dato, stato cloud e disponibilità dispositivo separati. Nessuna conferma fisica derivata dalla GET.

Nello scenario da 11.520 GET, autenticazioni, quattro verifiche giornaliere delle specifiche e qualche aggiornamento manuale portano indicativamente a circa 12–14 mila richieste mensili, assumendo un processo stabile e pochi errori. Non è una misura della quota realmente addebitata. Un mese di 31 giorni aumenta il polling di circa il 3,3%; più pagine aumentano il costo dei cicli proporzionalmente.

## Implicazioni per l'integrazione

Il client attuale usa l'inventario generale con cursore e GET degli stati per dispositivo. Il percorso cumulativo Smart Home richiede un adapter distinto con paginazione a numero di pagina, filtro/normalizzazione degli stati prima della persistenza e riuso delle specifiche per tipo/scala/unità. Non basta cambiare il percorso conservando il parser corrente. Conservare solo campi autorizzati nella cache, senza local key, IP, coordinate o UID.

Il risultato di prodotto sarà una vista informativa con ritardo possibile di uno/cinque minuti, non un rilevatore istantaneo di presenza/movimento. Sensori usati per automazioni o allarmi rapidi richiederebbero un percorso a eventi separato e verificato.
