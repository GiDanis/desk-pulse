# SmartPC: verifiche proporzionate

Per ridurre tempi e consumo di token:

- Cercare prima con `rg` e leggere solo le sezioni pertinenti. Non caricare
  interi MasterPlan, inventari o cartelle di evidenze per una modifica locale.
- Scegliere i controlli con `python3 scripts/check-dashboard.py --list`.
  Per modifiche circoscritte usare `--case NOME`; senza selezione il runner
  esegue cinque suite rapide. Scrivere i risultati in una directory dedicata.
- Usare `--suite core`, `ui` o `all` quando il perimetro lo richiede.
  Conservare i gate PC/ARM/EGLFS pertinenti per le consegne sulla board.
  Un rapido positivo non certifica l'intero sistema.
- Dopo un passaggio positivo non ripetere le stesse verifiche senza nuovi
  cambi, dipendenze diverse, errori o dubbi concreti. Le prove precedenti valgono
  solo per i sorgenti e l'ambiente effettivamente verificati.
- Preferire il riepilogo del runner; aprire i log dei soli fallimenti,
  iniziando dalle ultime righe. `--verbose` serve per diagnosticare il banco.
- Riportare in modo conciso risultato, verifiche e limiti effettivi.
  Non nascondere esclusioni o fallimenti storici.

Per pulizia e consegne seguire `os/maintenance-policy.md`: preservare dati,
preferenze, temi e rollback; verificare le copie prima di eliminare originali.
