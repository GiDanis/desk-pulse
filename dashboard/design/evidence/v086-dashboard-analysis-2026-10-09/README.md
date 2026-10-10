# Analisi dashboard Apple Calm · 9 ottobre 2026

Baseline: core 0.8.5-rc.1 / Apple Calm 1.5.0 / Theme API 2.6. Solo analisi, documentazione e concept HTML; nessuna modifica al runtime o operazione sulla board/provider.

- [Analisi, 13 fonti e piano](../../v086-dashboard-first-analysis.md).
- [Source audit](source-audit.json): hash dei 19 sorgenti letti e riferimento alle prove storiche 0.8.5.
- [Verifica del concept](concept-review.json): nove dashboard simulate, apertura/ritorno; geometria di Rete a viewport 960/736/320 in due varianti, senza clipping negli elementi esaminati. Le misure sono del browser, non del display SmartPC.
- [Integrità della consegna](analysis-integrity.json): link locali, hash runtime conservati e sintassi dello script.

Concept inline: /home/giuseppe/.codex/visualizations/2026/10/07/01a1188a-5f59-71e1-a6fc-37604b0cb0f4/smartpc-dashboard-first.html. Il wrapper in /tmp e il server 127.0.0.1 servono soltanto alla verifica e vengono chiusi; non sono una distribuzione dell'applicazione.

Non è stato effettuato un test statistico di usabilità, un rendering QML dei nuovi layout, un confronto prestazionale sulla board o una certificazione dei feed live. I gate di implementazione e accettazione restano nel piano.
