# Evidenze dell'analisi 0.8.5

Questa cartella documenta la baseline, non una 0.8.5 implementata.

- `board-theme-state.json`: lettura del journal di attivazione, delle revisioni, della quarantena e dello stato del servizio; preferenze rappresentate soltanto dal loro hash.
- `board-theme-followup.json`: timestamp del riavvio, data della quarantena e record supervisor da journal systemd, letto con privilegi di sola consultazione.
- `isolated-settings-diagnostic.json` e `.log`: real Main su PC, Qt 6.8.2, backend offscreen/software, store temporaneo, dati sintetici e connessioni negate. Supervisore esterno non eseguito.
- `diagnose_settings.py`: percorso riproducibile. Usa il bundle Apple Calm corrente e verifica il digest del preflight cache prima di importarlo nello store privato.
- PNG: catture delle singole osservazioni. Il tema realmente visibile è `activeThemeId` nel JSON; `draft` può differire quando la transizione fallisce. In particolare `return-base.png` mostra l'errore del ritorno a Base con Apple ancora visibile.

Esecuzione dalla radice del repository:

```bash
/tmp/smartpc-maintenance-qt68/bin/python dashboard/design/evidence/v085-settings-analysis-2026-10-09/diagnose_settings.py
```

Il Main isolato ha inizialmente attraversato Base → Functional → Apple Calm dal tasto 6 in Aspetto, quindi salvato. Il campione immediatamente dopo il salvataggio è incoerente, ma dopo ulteriori 1,2 s recupera: è una stabilizzazione transitoria. Nel successivo ritorno a Base resta invece incoerente per l'intera finestra di 6 s, con errore `Presentazione non registrata: undefined` e un binding loop QML nel percorso. Le 6 s sono un limite di osservazione del probe, non il timeout di produzione.

Le osservazioni `direct-apple-in-appearance` e Info seguono il fallimento del ritorno a Base: **non rappresentano un nuovo passaggio riuscito da Base**. Il salvataggio e l'annullamento successivi operano solo sullo stato temporaneo del probe. Le immagini Info rappresentano Apple Calm e distinguono i contenuti Dispositivo/Risorse; diversi valori sono intenzionalmente N/D nelle fixture.

I tempi sono software locali; i colori seguono anche la palette automatica dell'app. Le catture non sono un confronto ottico a parità di luminosità e non certificano il display fisico. Il probe non riproduce il recupero del supervisore sulla board e non ne prova la causa completa.

Letture remote soltanto: nessuna installazione, attivazione, rimozione di quarantena o modifica alle preferenze di produzione. Ricerca, conclusioni e piano sono in [v085-settings-theme-analysis.md](../../v085-settings-theme-analysis.md).
