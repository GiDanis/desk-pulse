# Consegna Theme Engine A1–A6 · 6 ottobre 2026

Implementazione e installazione concluse; nessun tag/versione ulteriore assegnato.

- Runtime installato `bb4d76c`: 435 file SHA verificati, preferenze intatte, 16 eventi conservati, backup app/stato/cache, servizio EGLFS attivo, zero riavvii automatici dopo vero reboot.
- UI finale su `17db764`: sette verifiche mirate passate, viewport, domini, freschezza DTO, notte, scena, notifiche e overlay. Solo salvataggio e relativo test cambiano prima dell’installazione finale.
- Delta finale: 15 test recovery/salvataggio passati sulla board, attesa frame limitata e rollback.
- SDK: 433 file verificati, profilo di produzione, init/lint/preflight/pack/import/export da kit autonomo; archivio esportato byte-identico.

[Board e sorgenti delle prove](board/README.md), [matrice e decisione di consegna](acceptance-matrix.json), [SDK finale](sdk-delivery/theme-bb4d76c-sdk-delivery.json).

Le prove estese precedenti sono conservate per sorgente. La decisione esplicita sul dispositivo dedicato rende informativi i budget diagnostici storici e interrompe altre ripetizioni di stress. Non si convertono scostamenti in PASS. Tastierino fisico, power cut, soak 24/7 e qualificazione estetica dei nuovi temi rimangono aperti; il reboot reale ordinario è invece verificato.
