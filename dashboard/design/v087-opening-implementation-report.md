# 0.8.7-rc.2 — aperture e riaperture più leggere

10 ottobre 2026 · Theme API 2.7, 62 superfici · Apple Calm 1.6.2 · display 960×640.

Questa revisione interviene sul ritardo tra tasto e destinazione: conserva e riusa le viste chiuse, evita una doppia costruzione dei contesti pubblici e riduce i dati preparati per La mia squadra. Palette, font, icone, dimensioni delle card e informazioni consultabili restano quelli approvati. La navigazione Apple Calm e l'ingresso dei pannelli ricevono una dissolvenza breve di 100 ms, da opacità 0,88 a 1, rispettando Ridotto e Disattivo.

**Consegnata come candidata:** core 0.8.7-rc.2 / Apple Calm 1.6.2 installati e verificati dopo reboot reale. Servizio active/running, NRestarts=0, GUI fresca e pronta, nessuna attivazione pending o warning QML rilevato. Conservate 40 preferenze estranee all’aspetto, personalizzazioni e profili degli altri temi. Nessuna promozione stabile implicita. Questo rapporto accompagna lo [studio aperture/CPU/GPU](v087-heavy-opening-cpu-gpu-analysis.md) e prosegue la [prima ottimizzazione 0.8.7](v087-performance-implementation-report.md).

## Interventi applicati

- **Riaperture:** la chiusura di un overlay conserva il renderer validato in una cache di massimo sei elementi. Le viste nascoste sono sospese; alla riapertura ricevono i dati correnti prima della presentazione. Cambiare tema rilascia i renderer che non corrispondono alla presentazione effettivamente selezionata, anche quando la vecchia revisione resta nel catalogo.
- **Contesti:** `createLegacy` è un percorso privato che normalizza e valida lo snapshot completo prima di costruire una sola volta gli oggetti e i modelli Qt. Non pubblica identità o contesti quando lo snapshot è invalido. Il percorso pubblico precedente e il fallback dell'adapter restano disponibili; contratto e fingerprint non cambiano.
- **La mia squadra:** il renderer Apple `sport.team` richiede soltanto il dominio team, evitando il trasferimento di tutte le 380 partite sotto il selettore. Serie A mantiene calendario, turni e tutte le dieci partite; la squadra preferita conserva un percorso separato.
- **Apertura a freddo:** la costruzione viene accodata con controllo della generazione e della superficie richiesta. Un percorso già superato non costruisce un albero che dovrà essere distrutto subito. Il passaggio alla vista personale imposta la modalità prima dell'argomento, evitando una destinazione intermedia.
- **Movimento:** l'entrata avviene quando renderer e contesto sono pronti, una volta per presentazione. Spostare il focus nella stessa lista non riavvia la dissolvenza. Le ricette terminano con opacità 1; il movimento non sostituisce la riduzione del lavoro sincrono.

La direzione è coerente con le indicazioni ufficiali Qt: ridurre lavoro e allocazioni nella GUI, creare soltanto ciò che serve e misurare prima di cambiare architettura. `Loader.asynchronous` non sposta in un worker la preparazione Python precedente. [Prestazioni Qt Quick](https://doc.qt.io/qt-6.8/qtquick-performance.html), [Loader](https://doc.qt.io/qt-6.8/qml-qtquick-loader.html).

## Metodo di misura

Baseline congelata 0.8.7-rc.1 / Apple Calm 1.6.1 contro pacchetto candidato 0.8.7-rc.2 / 1.6.2. Main reale sulla stessa board EGLFS/KMS, stesso verificatore byte per byte, rete negata, 380 partite sintetiche e piccoli inventari dimostrativi. Ogni profilo comprende 30 aperture e 30 ritorni per cinque percorsi, 36 cambi argomento, 30 dashboard Sport e 30 movimenti del focus: 396 azioni. Le 30 aperture comprendono un primo ingresso e 29 riaperture: non costituiscono 30 avvii a freddo indipendenti.

Il tempo va dal segnale sintetico al `frameSwapped` di un frame richiesto dopo la readiness della destinazione. I riferimenti agli host e l'espressione di coerenza sono stabili; non si scandiscono tutti i DTO durante ogni attesa. Si registrano separatamente handler e readiness. È una misura software di invio del frame coerente: **non** misura primo pixel, latenza USB, tempo GPU o completamento della dissolvenza. Il confronto con i circa 0,7 s del precedente harness non è valido, perché il protocollo è diverso.

I primi tentativi con un event loop manuale trattenevano le cancellazioni differite Qt e producevano un accumulo artificiale di oggetti. Quei tentativi sono stati scartati. Il verificatore finale svuota `DeferredDelete` durante l'attesa, riproducendo il ciclo di vita dell'event loop ordinario, in modo identico per baseline e candidato. Questa correzione riguarda il test; non aggiunge `processEvents` al prodotto. Nessun outlier viene escluso dalle prove valide.

## Risultati nativi

Apple Calm, movimento disattivato; mediana / p95 empirico / massimo, millisecondi. Tutti i campioni inclusi.

| Percorso | Mediana prima → ora | p95 prima → ora | Massimo prima → ora |
| --- | ---: | ---: | ---: |
| Serie A · elenco | 465.9 → 138.5 | 507.1 → 152.6 | 877.6 → 827.1 |
| Squadra · selettore senza preferita | 603.3 → 300.4 | 856.0 → 382.0 | 13017.4 → 760.7 |
| Casa · elenco | 153.0 → 70.9 | 169.5 → 77.8 | 186.3 → 165.8 |
| Rete · elenco | 249.1 → 110.5 | 273.9 → 138.8 | 316.1 → 264.5 |
| Impostazioni | 230.4 → 222.4 | 236.3 → 236.1 | 623.0 → 545.9 |
| Cambio argomento | 67.7 → 79.6 | 286.7 → 293.9 | 572.8 → 580.6 |
| Cambio dashboard Sport | 48.2 → 48.6 | 49.8 → 49.8 | 95.4 → 105.6 |
| Focus elenco Serie A | 23.3 → 24.6 | 25.5 → 25.3 | 35.0 → 37.8 |

Mediana Serie A −70,3%, Casa −53,7%, Rete −55,6%. Impostazioni −3,5%: beneficio piccolo, p95 sostanzialmente invariato. Cambio argomento 67,7 → 79,6 ms: in questa raccolta la mediana peggiora di 11,9 ms; p95 286,7 → 293,9 ms. Non è un miglioramento generale della navigazione. Il primo ingresso Serie A arriva ancora a 827 ms e il selettore a 761 ms: il gate del freddo rimane aperto. Il massimo precedente di 13 s riguarda un singolo primo ingresso nel selettore con la fixture senza preferita, non il tempo ordinario del club configurato.

Base, movimento disattivato:

| Percorso | Mediana prima → ora, ms | p95 prima → ora, ms |
| --- | ---: | ---: |
| Serie A · elenco | 82.3 → 82.6 | 83.8 → 83.2 |
| Squadra · selettore senza preferita | 82.5 → 82.2 | 83.5 → 98.3 |
| Casa · elenco | 132.5 → 82.4 | 133.7 → 83.4 |
| Rete · elenco | 216.8 → 114.2 | 250.7 → 116.3 |
| Impostazioni | 70.5 → 82.6 | 85.5 → 84.9 |
| Cambio argomento | 58.2 → 59.3 | 179.4 → 168.8 |
| Cambio dashboard Sport | 16.6 → 16.6 | 20.1 → 19.6 |
| Focus elenco Serie A | 15.0 → 15.3 | 16.7 → 16.1 |

Base migliora negli elenchi Casa/Rete; Serie A, Sport e focus restano vicini alla baseline. La mediana Impostazioni cresce da 70,5 a 82,6 ms, con p95 praticamente invariato: nessuna riduzione rivendicata su quel percorso. Sono raccolte sequenziali sullo stesso dispositivo, con governor invariati, non intervalli di confidenza o prove di causalità per ogni singolo intervento.

Apple Calm con **movimento Normale**, stessa candidata (nessun confronto A/B con Normale precedente):

| Percorso | Mediana, ms | p95, ms | Massimo, ms |
| --- | ---: | ---: | ---: |
| Serie A · elenco | 185.3 | 204.9 | 851.5 |
| Squadra · selettore senza preferita | 510.6 | 519.2 | 776.1 |
| Casa · elenco | 119.5 | 137.8 | 187.9 |
| Rete · elenco | 157.9 | 165.4 | 262.5 |
| Impostazioni | 226.8 | 235.6 | 578.7 |
| Cambio argomento | 129.4 | 347.9 | 599.0 |
| Cambio dashboard Sport | 80.3 | 109.3 | 112.3 |
| Focus elenco Serie A | 43.2 | 43.5 | 43.7 |

Il selettore con Normale conserva una mediana di 511 ms e p95 di 519 ms: richiede un seguito mirato. La dissolvenza è configurata a 100 ms, ma questi tempi non ne misurano il completamento. Il movimento resta opzionale; Ridotto limita la durata a 80 ms, Disattivo evita la ricetta. Il p95 usa il quantile empirico inferiore `floor((n−1)×0,95)`; con campioni piccoli si pubblica sempre anche il massimo.

[Confronto completo, tempi handler e riaperture separate](evidence/v087-opening-implementation-2026-10-10/native-comparison.json), [396 azioni Apple Normale](evidence/v087-opening-implementation-2026-10-10/board-proof/candidate-apple-normal.json), [qualifica dell’esatto manifest](evidence/v087-opening-implementation-2026-10-10/board-proof/qualification.json).

## Verifica funzionale e distribuzione

I controlli PC comprendono 39 test runtime dell'API, equivalenza canonica dei contesti iniziali per tutte le 62 superfici, proprietà dei modelli e identità, rifiuto delle righe duplicate senza pubblicazione, lint QML e 1.098 combinazioni Apple Calm. Le regressioni mirate coprono contratto/adapters/domini, recovery, trace/watchdog, riepiloghi e percorsi Sport/Casa/Rete.

Main verifica tre temi e palette giorno/notte, impostazioni e cambio tema, loading e annullamenti. La regressione della cache prova cinque riaperture con la stessa istanza, dati cambiati mentre la vista è nascosta, otto percorsi con limite sei e rilascio completo dei vecchi renderer al passaggio a Base. I percorsi Serie A verificano tutte le dieci partite e la separazione della preferita. La qualifica finale EGLFS dell’esatto manifest comprende quattro profili Main (Base giorno, Functional notte, Apple giorno/notte), otto transazioni di tema, la regressione cache e tre sequenze prestazionali di 396 azioni. Nessun warning QML o tentativo di rete nelle prove isolate. [Cache nativa](evidence/v087-opening-implementation-2026-10-10/board-proof/native-cache.json), [impostazioni](evidence/v087-opening-implementation-2026-10-10/board-proof/native-settings/report.json).

Il pacchetto runtime contiene 515 file, senza rimozioni rispetto al precedente: sette file modificati e il verificatore aggiunto. Il kit autonomo è aggiornato con lo stesso contratto; il suo manifest viene controllato anche dentro lo ZIP. Il bundle cambia soltanto tre manifest JSON: nessun asset grafico o layout QML modificato. [Delta e hash](evidence/v087-opening-implementation-2026-10-10/delta-scope.json), [manifest runtime](evidence/v087-opening-implementation-2026-10-10/release-manifest.json), [export SDK](evidence/v087-opening-implementation-2026-10-10/sdk-export.json).

## Installazione e riavvio

- Manifest runtime: **515 file**, SHA-256 `9a4242aa65c3c687ec4dbb79793a9ff34eaf01bc91fd0997f4f3a46f1c449d67`; nessuna discrepanza.
- Apple Calm: **1.6.2**, digest `29f17b2dcf54ae37024426b1f3a9d6177f62d7c930ab26308d2381b8cc8cd8d4`; identità GUI, journal e configurazione coincidono.
- Backup protetto: `/var/backups/smartpc-before-v087-opening-20261010T123037Z`. L’installer dispone di rollback in caso di errore, conservando i budget Casa maturati; non è stato necessario attivarlo in questa consegna.
- Boot ID: `f1a01e32-4c81-4ddd-a26f-b14b15f2e781` → `7bd9a338-6d9a-42ae-a7eb-84c58b2e5733`. Dopo reboot servizio active/running con NRestarts=0, GUI PID 1253, heartbeat fresco, pending nullo e nessun warning QML rilevato.
- Tutte le preferenze post-attivazione sopravvivono al reboot; le 40 chiavi estranee all’aspetto e le personalizzazioni coincidono con il backup. Gli altri profili tema sono preservati.
- Campione passivo post-reboot: 20 s, stesso processo e servizio senza restart. È un controllo breve di salute, non un soak o una misura comparativa di consumo.

Il primo verificatore post-reboot è stato avviato come `smartpc`, che non può leggere il backup root con permessi 0700: QSettings restituiva valori predefiniti e il confronto falliva. Non era una modifica delle preferenze. Verificatore corretto con controllo dello stato QSettings ed eseguito con accesso al backup; confronto completo superato sullo stesso boot, senza un ulteriore reboot. Il tentativo originale resta in `reboot-run.txt` e la prova corretta in `reboot-verify-run.txt`.

[Installazione](evidence/v087-opening-implementation-2026-10-10/board-proof/install-receipt.json), [reboot e preferenze](evidence/v087-opening-implementation-2026-10-10/board-proof/reboot-verification.json), [salute passiva](evidence/v087-opening-implementation-2026-10-10/board-proof/installed-passive-sample.json), [SDK verificato](evidence/v087-opening-implementation-2026-10-10/sdk-verification.json), [kit autonomo](../../smartpc-theme-sdk-v087-rc2.zip). Le prove originali persistono in `/var/lib/smartpc-dashboard/v087-opening-proof/`; credenziali, cache e configurazione privata non entrano nel pacchetto o nell’archivio delle prove.

## CPU, GPU e residui

La verifica precedente ha confermato otto core online disponibili ai thread, assenza di quota CPU restrittiva, acquisizioni già in pool di worker e rendering OpenGL hardware PowerVR. La [lettura dopo reboot](evidence/v087-opening-implementation-2026-10-10/board-proof/installed-hardware.json) conferma otto core, librerie PowerVR effettivamente caricate, descrittori DRM e QSGRenderThread nella GUI installata. È una fotografia di driver/thread/affinità, senza prova di speedup parallelo o saturazione GPU. Il pool Rete serializzato protegge client e persistenza. Python conserva il GIL: moltiplicare i thread non parallelizza automaticamente la normalizzazione CPU e gli oggetti Qt rimangono nel thread proprietario.

Questa revisione non cambia linguaggio, backend grafico, governor, affinità o numero di worker. Le evidenze giustificano ridurre le ricostruzioni prima di introdurre C++ o processi. Il monitoraggio GPU passivo non dimostra saturazione né efficienza sotto carico; non rivendichiamo distribuzione ottimale su tutti i core, 60 FPS costanti o una RAM fissa per tutte le viste.

Rimangono il collaudo con tastierino e pannello reali a 50–60 cm, misure del primo feedback visibile, refresh reali simultanei e uso prolungato della build fissa. I primi ingressi, il selettore senza preferita e le Impostazioni richiedono ancora attenzione; i risultati sintetici non qualificano feed live, presenza dei dispositivi o quota dei provider.
