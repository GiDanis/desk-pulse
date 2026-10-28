# Evidenze rc.22 — studio e consegna

Avvio studio 16 ottobre; revisione/consegna 17 ottobre 2026, Europe/Rome. I file dei modelli reali non sono esportati qui.

**Consegna completata: rc.22 installata, 624 hash; gate software severo non superato e misura ottica aperta.**

## Decisioni

- `heldout-summary.json`: **banca finale v2**, cinque semi vecchio/candidato, 240 casi unici per policy. `reward-promotion-decision.json`: nuovo premio respinto, produzione mantiene ricetta 2.
- `heldout-summary-v1-rejected.json`, `bank-audit.json`: primo generatore con gruppi duplicati; risultati conservati, non validi per rivendicare abilità distinte.
- `selection-summary.json`: progressione a capacità respinta. La perdita di passo è indipendente dalla duplicazione dei gruppi di traffico.
- `methods-summary.json`: screening PPO/SAC/TD3 col premio candidato; non confronto abbinato dei due premi per ciascun metodo, non prova di generalizzazione.
- `research-receipt.json`: budget, semi e hash. Nessun modello importato; tempi di campagna PC sotto carico concorrente non usati per vantaggi di tempo reale.

## Verifiche

- `tests-release-pc.txt`, `tests-default-retained-final.txt`: prima matrice (39), poi controlli finali di compatibilità/diagnostica (11).
- `default-baseline-compatibility.json`: quattro riprese da checkpoint generati col codice precedente, stesso learner/replay/RNG/fisica/premio. Script `default_compatibility.py`, sorgente baseline congelata e directory temporanea privata richieste come argomenti/ambiente. I checkpoint diagnostici restano fuori dalle evidenze.
- `pc-functional-retained/report.json`: Main/Worker isolati, quattro allievi/save e cinque auto.
- `board/`: sonde ARM, A/B nativo, campioni prolungati, risorse, immagini 960×640, ricevuta e salute dopo l’installazione. Raccolta conclusa; ricevuta rc.22/624 file e salute finale presenti.
- `performance_summary.py --board board`: analisi locale degli intervalli grezzi, distinguendo callback, pose interpolate e freschezza. Conserva anche metriche totali incluse le pause volute della preview.

Sorgenti congelate: `frozen-baseline-rc21.tar.gz` e `frozen-reward-candidate.tar.gz`, con ricevuta `frozen-sources.json`. Sono copie per riprodurre gli esperimenti, non pacchetti da installare.

## Attribuzione delle sorgenti

La campagna scientifica usa il candidato congelato **prima** della decisione negativa. La distribuzione conserva il premio precedente. I ricevuti `*-refinement.json` della scheda dichiarano gli aggiustamenti successivi: preparazione fixture prima della finestra Qt, hash preview già congelato, ricetta precedente ripristinata, memoria writer prima dell’ACK, priorità dell’etichetta contatto, riuso delle letture GUI e identità completa della cache numerica. Nessun cambiamento del controllo/fisica della Gara durante il confronto.

Il valore `status=passed` dei runner GUI attesta completamento funzionale e assenza di warning QML: **non** certifica i gate prestazionali. Per quelli usare `performance-summary.json`, separato dalla ricevuta d’installazione. Nessuna misurazione ottica o manuale HID viene simulata.
