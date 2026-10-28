# v0.9.0-rc.13 · presentazione del Gioco a 30 Hz

**13 ottobre 2026 · implementata e installata; gate iniziale Evo/32 e integrazione nativa verificati.** Seguito dello [studio degli scatti Evo](game-frame-pacing-study.md). [Evidenze](evidence/v09-pacing-optimization-2026-10-13/). Theme API 2.10/68 superfici conservata.

## Modifiche

- **Dati:** la factory collega privatamente la sorgente del Gioco al solo campo pubblico `scene`. Ogni scena conserva validazione atomica e copie possedute; non attraversa più la normalizzazione del contesto completo e il ritorno JS → Python. Le impostazioni, il tema, la pista e il lifecycle seguono il percorso ordinario. Contesti nascosti conservano l’ultimo dato e ricevono quello corrente alla riattivazione; il collegamento viene rilasciato con il contesto. Preview/fixture senza sorgente usano il percorso precedente.
- **Presentazione:** clock con scadenze assolute monotone a 30 Hz, timer preciso e nessun recupero a raffica dei tick tardivi. Pubblicazione del worker a 30 Hz, polling preciso, senza cambiare DT=1/60 s o budget/ordine degli episodi.
- **Auto:** delegate conservati a parità di numero, campi individuali aggiornati solo quando cambiano, piccolo buffer di campioni reali. Interpolazione limitata ai campioni, angolo sul percorso breve, senza estrapolazione. Ritardo di presentazione 200 ms per la popolazione e 120 ms per Gara/preview con movimento normale, zero con movimento ridotto/disattivato; fino a 16 campioni per auto/sensori. Pausa, cambio identità/sessione/pista/generazione/prova, riavvio preview e movimento ridotto/disattivato azzerano l’interpolazione. I campioni del simulatore restano autorevoli e il buffer non entra in policy o checkpoint.
- **Camera/sensori:** stessa cadenza e pose interpolate delle auto; sensori interpolati dai propri campioni reali e resettati al cambio selezione. Rivale cercato solo per Duello, senza ordinamento; limiti del gruppo calcolati solo in Gara. Geometria della pista memorizzata. Tutte le auto di Gara rimangono visibili, anche in Sensori.
- **CPU fisica:** vertici e campioni di contatto preparati soltanto quando il corpo può toccare i bordi o esistono altre auto nello stesso mondo. Conservato il percorso dettagliato per fuori pista/contatti, gli stessi sottopassi e le stesse equazioni. Nessun cambio di versione fisica, reward, sensori, RNG, reti o formato dei salvataggi.

## Misure native e limiti

EGLFS 960×640, copie private, governor ordinari. Callback Qt e pose QML misurati sul dispositivo, **non FPS ottici o tempi GPU**.

Primo A/B sulla stessa sequenza reale della rc.12, 35 s: GUI principale da **66,7% a 58,5% di un core**, render thread da **35,1% a 23,0%**. Il primo veicolo passa da p95 di movimento 86,7 a 51,5 ms, con zero pause di posa >100 ms. Quel primo percorso manca ancora il gate dei frame (p95 64,7 ms); la materializzazione JS da sola non lo risolve (p95 65,1 ms). Non sono risultati di 30 fps garantiti.

Prova successiva con tutti i 32 tentativi inizialmente attivi, stessi pesi/profile Evo del checkpoint reale, episodi resettati **solo nella copia privata**: 35 s, 32 attivi in 882/985 pacchetti. Buffer 200 ms: **29,97 frame callback/s**, intervalli p95 **43,48 ms**, p99 **46,16 ms**, massimo **73,38 ms**. Peggiore p95 di movimento fra le auto **44,38 ms**, massimo **91,61 ms**; nessuna pausa di frame o posa >100 ms. Il gate iniziale dello studio è superato in questa finestra; il pacchetto finale è verificato separatamente sotto.

Una prima prova etichettata `live32` non aveva applicato il reset al checkpoint salvato della copia e partiva con 21 attivi: conservata, non usata come prova di 32 attivi. La prima misura con buffer 120 ms rendeva regolari i frame ma lasciava pause di posa >100 ms; per questo si è aumentato il buffer della Popolazione. Il ritardo aggiunto è esplicito.

**Fisica:** parità esatta di snapshot/reward/osservazioni per 16 combinazioni (quattro piste, uno/quattro veicoli, f1-2/f2-1), 180 passi con stati dentro pista, al bordo/fuori pista e contatti. Tre repliche da 256 chiamate trainer per caso sulla scheda: Controllo ovale **309,9 → 321,2 transizioni/s (+3,6%)**, Controllo Varano **272,6 → 289,6 (+6,2%)**; Sorpasso Varano **196,5 → 199,2 (+1,4%)**, beneficio piccolo, non una conclusione generale. Nessuna qualifica della convergenza da questi campioni.

## Verifica e consegna

- 94 test PC, un’esclusione preesistente; altri 19 controlli di fisica/circuiti/record. Walkthrough PC Base/Evo, Functional/PPO, Apple/NEAT con movimento ridotto, Apple/Gara Varano.
- Primo avvio dei test ARM fermato da strumenti diagnostici assenti (`QtTest`, `qmllint`): timer testato col loop Qt già disponibile; lint reale superato sul PC e distinto dai controlli ARM. Log iniziale conservato; nessuna dipendenza installata sulla scheda.
- **41 controlli ARM** superati; lint escluso solo sulla scheda perché lo strumento è assente, già superato nel giro PC.
- **Sette walkthrough nativi finali:** Functional/NEAT sul tecnico, Apple/PPO su Varano a scala 1,1, gare reali 2/4 auto nei tre temi, record/classifica Apple e Evo finale. Gare: due finestre di 10 s per tema, tutte le auto contenute nell’arena e Sensori attivo. P95 dei frame 35,6–43,3 ms, nessun blocco >100 ms; i massimi di ogni caso restano nei JSON. Non sono nuovi test di tre giri completi: quelli della rc.12 restano storici.
- **Evo finale, 35 s:** 32 attivi in 877/1.008 pacchetti, **30,00 callback/s**, p95 **43,73 ms**, p99 **46,59 ms**, massimo **91,26 ms**. Peggiore p95 delle pose **44,17 ms**, massimo **87,43 ms**, zero pause >100 ms. GUI principale mediana **34,6% di un core**, render thread **19,5%**; campione live distinto dal replay A/B. Scene p95 45,45 ms/massimo 128,50 ms: il buffer assorbe questa irregolarità nel campione, non la elimina nel simulatore.
- **Movimento ridotto:** supplemento nativo Functional/tecnico, gare 2/4 con buffer a zero e tutte le auto contenute; posizioni e sensori seguono entrambi i dati correnti. La sola condizione sul movimento normale conserva i valori 200/120 ms del campione precedente. [Ricevuta supplemento e hash finali](evidence/v09-pacing-optimization-2026-10-13/board/motion-policy-receipt.json).
- **Consegna:** [ricevuta](evidence/v09-pacing-optimization-2026-10-13/board/final-receipt.json), 584 hash conformi, sei piloti/tutte le tabelle/**1.325 artefatti** e preferenze conservati; Base attivo, servizio e GUI pronti, NRestarts=0. Nessun nuovo reboot OS. Backup `/var/backups/smartpc-before-pacing-20261013-183044`; rollback `/opt/smartpc/dashboard-rc12-before-pacing`.

## Seguito aperto

Il target iniziale è 30 regolari con il carico verificato. Restano uso prolungato, optimizer/topologie maturi, cambi generazione/ripasso/salvataggi/notifiche concorrenti e verifica ottica/input dell’utente. Non si certificano 30 fissi per ogni futura popolazione/pista né 60 fps. F3 completo, con batch di mondi compatibili, richiede ancora prototipo e parità di episodi/RNG/checkpoint prima della scelta; il collector multiprocesso precedente e la NPU restano non selezionati per questo carico. Il piccolo intervento sui contatti evita lavoro inutile senza alterare il percorso autorevole.
