# v0.10.1 — manutenzione completata

28 ottobre 2026. Nessuna attività di questa pulizia rimane aperta.

- Candidata installata: 0.10.1-rc.1, 533 hash conformi; Apple Calm 1.6.5.
- Servizio attivo, GUI pronta, NRestarts=0; nessun reboot OS.
- Archivio privato PC verificato: 349.933 voci, 8,39 GiB compressi,
  SHA-256 0817ef0aa033fd5444eddfbbe203a9f34984d128aab0cc74b2a0e45d64ec1c79.
- Rimosse 422 radici storiche dopo verifica e controllo dei processi;
  recuperati 19,76 GiB, spazio libero finale 20,87 GiB.
- Dati Gioco, cinque piloti, 215 artefatti, configurazioni e preferenze conservati.
  Kernel/driver/file DP, hold, ambienti Python e CopyTrade preservati.
- Esportazione della cartella di manutenzione confrontata con checksum;
  cartella e file temporanei di questa operazione rimossi dalla board.
- Test di default: cinque suite rapide passate in 11,13 s, output unico.
  CLI/selezione/timeout verificati. Suite estese e gate di consegna mantenuti.
- Le due suite storiche check_game.py/check_dashboard.py falliscono anche sulla
  baseline; non sono dichiarate passate. Le matrici correnti PC/ARM/EGLFS
  sono passate e non sono state ripetute dopo modifiche solo agli strumenti.

Ricevuta principale: final-receipt.json. Dettagli: installation-receipt.json,
archive-verification.json, cleanup-receipt.json, final-preservation.json,
final-os.json, final-health.json, work-export.json e temporary-cleanup.json.
Le prove del rapido sono in quick-runner/checks.json; quelle CLI in runner-cli.json.

Backup PC fuori Git: /home/giuseppe/Documenti/SmartPC-backups/v0101-20261028/.
Rollback board: /var/backups/smartpc-maintenance/rollback-0.10.0-rc.2-20261028-200231.
Report: ../../v0101-cleanup-report.md; MasterPlan revisione 3.29.

La nuova analisi/piano Aquarium 3D di un'altra chat non è stata modificata
né consegnata con questa manutenzione.
