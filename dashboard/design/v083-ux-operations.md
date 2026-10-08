# v0.8.3 · Sport e impostazioni

La candidata **0.8.3-rc.2** organizza il carosello in **Oggi, Meteo, Account, Sport, Casa e Rete**. I gruppi nascosti vengono saltati. Sport mantiene separati dati, aggiornamenti e preferenze di Calcio, F1 e MotoGP. Apple Calm **1.3.1** conserva la grafica della revisione precedente e adatta gli spazi: barra più sottile, margini uniformi e liste scorrevoli; le guide dei tasti restano nel Menu Comandi.

## Entrare in Sport e ritrovare la selezione

Con **4/6** scegli Sport. Nell'indice, **2/8** sceglie la disciplina e **5** la apre. Dentro una disciplina, **4/6** sceglie la vista e **2/8** la selezione disponibile; **5** apre il dettaglio. **7** risale al contesto precedente e poi all'indice Sport. Le viste e le selezioni di F1 e MotoGP sono indipendenti; tornare in una lista conserva il record, se ancora disponibile. Un record rimosso non viene sostituito silenziosamente nel dettaglio.

I comandi globali restano **1 Home, 3 Avvisi, 9 Menu**. Il Menu mostra la guida adatta al contesto. I pallini indicano la posizione; titoli e icone identificano l'argomento. I riepiloghi dell'indice indicano disponibilità e stato della fonte: i dati precedenti conservano l'ora originale.

## Impostazioni per compito

Apri **9 → Impostazioni**, scegli con **2/8** e conferma con **5**. **4/6** regola i valori, **7** torna al livello precedente conservando la selezione.

| Gruppo | Contenuto |
| --- | --- |
| **Schermo** | Luminosità automatica/manuale, orari, intensità giorno/notte, dimensione testo. |
| **Aspetto** | Tema, palette, movimento, regolazioni ed editor; **Gestione temi** raccoglie importazione, esportazione, revisioni e rilettura. |
| **Moduli e Home** | Visibilità delle macroaree; **Sport e Home** contiene discipline, riepiloghi Home e accesso alle configurazioni sportive. |
| **Avvisi** | Fascia silenzio, interruzioni per categoria e soglie Account. Gli eventi rimangono consultabili nella casella. |
| **Servizi collegati** | Stato e opzioni di Account, Casa e Rete, anche quando manca una configurazione. |
| **Dati e aggiornamenti** | Rilettura e refresh manuali delle fonti, con accettazione, avanzamento ed esito effettivo. |

**Luminosità:** la regolazione si applica subito. **Dimensione testo e aspetto:** l'anteprima mostra «non salvata»; usa **Salva** per confermare o **Annulla** per ripristinare. Trasferire o importare un tema non costituisce una conferma di attivazione: le schermate distinguono selezione, anteprima, operazione e risultato.

Nascondere la macroarea Sport conserva le scelte delle discipline. Alla prima migrazione il gruppo compare soltanto se almeno una disciplina era visibile. Non si attivano discipline precedentemente nascoste. Le chiavi provider e le cache esistenti rimangono valide.

## Rete e dati precedenti

Panoramica, dispositivi, router, Wi-Fi e porte seguono gli stessi titoli, stati e regole di selezione. In Apple Calm le liste scorrono e portano la selezione interamente in vista, senza contatori di pagina sul fondo. La panoramica apre su **Metriche**, con traffico WAN e temperature iliadbox nel primo riepilogo; **Dispositivi** rende visibile l’altro elenco. Il traffico rilevato non è uno speed test. I grafici distinguono le serie anche attraverso tratto continuo/tratteggiato e legenda; conservano buchi, risoluzione RRD e timestamp. Le etichette degli assi usano il font QML del tema anche in EGLFS. Base e Functional conservano i propri layout.

«Precedente» non significa attuale; «Non disponibile» non significa zero. La presenza nei record del router non dimostra presenza fisica o copertura Wi-Fi. La rilettura Account non avvia una sincronizzazione cloud dal dispositivo. I limiti delle fonti rimangono quelli dei [moduli Rete](v081-network-operations.md) e della [manutenzione 0.8.2](v082-maintenance-operations.md).

## Recupero e limiti

Manifest, ricevuta, test e prove di reboot della rc.2 sono conservati in **`/var/lib/smartpc-dashboard/v083-space-proof/`**. La ricevuta `install-receipt.json` identifica il backup completo **`/var/backups/smartpc-before-v083-space-20261008T130632Z`**, comprendente core rc.1 e tema 1.3.0; la versione effettiva è nel manifest di `/opt/smartpc/dashboard`. Le prove della rc.1 restano in `/var/lib/smartpc-dashboard/v083-proof/`.

Per un rollback del solo core, arresta il servizio, ripristina la cartella `dashboard` del backup e riavvia; verifica manifest, identità del tema e heartbeat GUI fresco. Per tornare anche all'aspetto precedente usa la revisione Apple Calm **1.3.0** e la selezione conservate nel backup: la policy del tema può aver rimosso la revisione precedente dallo store attivo. Un ripristino completo di configurazione, dati e cache riporta le preferenze al backup e va effettuato soltanto quando necessario, con servizio fermo. **Conserva sempre i ledger Casa più recenti**, prima di sostituire `.local`: il consumo successivo al backup non deve diminuire. L'installer applica questa regola anche nel rollback automatico.

La qualifica software e il reboot ordinato non certificano leggibilità fisica a **50–60 cm**, tastierino reale, perdita di alimentazione, scollegamento di rete o funzionamento prolungato. [Ottimizzazione e prove rc.2](v083-space-optimization-report.md), [consolidamento rc.1](v083-implementation-report.md).
