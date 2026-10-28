"""Reconcile every current-state section only after a verified installation."""
import json
from pathlib import Path

evidence=Path(__file__).resolve().parent
receipt=json.loads((evidence/'board-install/final-receipt.json').read_text())
assert receipt['status']=='passed' and receipt['version']=='0.9.0-rc.7'
assert receipt['allDriverColumnsPreserved'] and receipt['preferencesPreserved']
assert receipt['newOSReboot']
path=evidence.parents[1]/'release-masterplan.md'
s=path.read_text()
s=s.replace('Revisione 2.57','Revisione 2.58')
s=s.replace('Baseline corrente documentata: core 0.9.0-rc.6 · Theme API 2.9','Baseline corrente documentata: core 0.9.0-rc.7 · Theme API 2.10')
start=s.index("L'aggiornamento registra")
end=s.index('## 1.',start)
s=s[:start]+'''L'aggiornamento registra **0.9.0-rc.7 installata e riavviata**: impostazioni Sessione/Allenamento/Gestione, bozza confermata, focus stabile, Circuito Tecnico e percorsi per circuito/configurazione. PPO usa il tempo episodio corretto e distingue timeout/termine. [Consegna e limiti](v09-settings-circuits-report.md). Conservati dossier, Gara/Guida PPO, Controllo/Passo, piloti e artefatti precedenti.

**Studio A → B → C implementato:** geometria comune a fisica/sensori/render, trasferimento esplicito e classifiche per circuito, griglia sfalsata e reti congelate. Cinque semi a budget uguale: 50/50 completamenti tecnici dal trasferimento, 39/50 da zero; beneficio non uniforme e ritenzione separata. Tre temi EGLFS, gara a due/tre giri e quattro/cinque giri, PPO 30 minuti; qualifica traffico, PPO/NEAT, carichi ampliati, lettura/input fisici e FPS ottici restano aperti. Compagno v0.10 e Memoria v0.11 conservano la sequenza.

''' +s[end:]
lines=[]
for line in s.splitlines():
    if line.startswith('| Core |'):
        line='| Core | **0.9.0-rc.7**, checkout e installazione | [Impostazioni/circuiti](v09-settings-circuits-report.md): manifest '+str(receipt['files'])+' file, backup, archivi/artefatti/preferenze conservati e reboot attribuito alla candidata. Qualifica completa ancora aperta. |'
    elif line.startswith('| Tema attivo documentato |'):
        line='| Tema attivo documentato | **Apple Calm 1.6.2** | Conservato nella rc.7 anche dopo reboot; colori, font, icone e personalizzazioni mantenuti. Base/Functional e Apple Calm verificati in EGLFS. |'
    elif line.startswith('| Contratto dei temi |'):
        line='| Contratto dei temi | **SmartPC.ThemeApi 2.10**, 68 superfici | Mappe additive di impostazioni/pista, azioni app-owned, contratto e kit aggiornati; import precedenti compatibili. [Report](v09-settings-circuits-report.md). |'
    elif line.startswith('| Reboot |'):
        line='| Reboot | Ultimo reboot OS qualificato **0.9.0-rc.7** | [Ricevuta corrente](evidence/v09-settings-circuits-2026-10-11/board-install/final-receipt.json): manifest, GUI fresca/pronta, servizio e conservazione dopo cambio boot ID. |'
    elif line.startswith('| Gioco v0.9 |'):
        line='| Gioco v0.9 | **Candidata implementata/installata; qualifica parziale** | [Rc.7](v09-settings-circuits-report.md): A/B/C consegnati, geometria/percorsi, gara tecnica 2/4 e PPO 30 minuti su EGLFS. 50/50 prove tecniche da trasferimento, 39/50 da zero; ovali originali 49/50. Robustezza, traffico, competenza PPO/NEAT, carichi ampliati e gate fisici aperti. |'
    elif line.startswith('| **Gioco** |'):
        line='| **Gioco** | Pista / Classifica / Progressi / Pilota | Ovale e Circuito Tecnico; Impara individuale, Gara 2–4/3–5–10 giri e modelli congelati. Menu Sessione/Allenamento/Gestione, bozza e avanzate; percorsi, dossier e reset mirato. |'
    elif line.startswith('| **v0.9 — Gioco'):
        line='| **v0.9 — Gioco / Piloti che imparano** | Ovale e Circuito Tecnico, vettura standard/F1 candidata, piloti e percorsi persistenti, Impara/Gara, quattro viste e Start/Pausa. | **0.9.0-rc.7 installata**: A impostazioni → B geometria/ambiti → C pista tecnica consegnati. [Report](v09-settings-circuits-report.md), qualifica residua aperta; poi Compagno v0.10. |'
    elif line.startswith('| Gioco |'):
        line='| Gioco | Robustezza, traffico/Gara, competenza PPO/NEAT, carichi ampliati e gate fisici/frame pacing. | **Rc.7 installata**: nuove impostazioni, geometria, ambiti e Circuito Tecnico consegnati; 50/50 contro 39/50, gare native 2/4 e PPO 30 minuti. [Report](v09-settings-circuits-report.md). Nessuna qualifica universale o 60 FPS ottici dichiarati. |'
    elif line.startswith('| Identità distribuzione |'):
        line='| Identità distribuzione | Conservare ricevuta 0.9.0-rc.7, manifest '+str(receipt['files'])+' file, API 2.10 e tema 1.6.2. | Archivi, hash/preferenze, heartbeat e reboot verificati nella [ricevuta](evidence/v09-settings-circuits-2026-10-11/board-install/final-receipt.json); nuove distribuzioni richiedono nuova evidenza. |'
    lines.append(line)
s='\n'.join(lines)+'\n'
anchor='\nLe promozioni/tag storici'
s=s.replace(anchor,'\n| **v0.9.0-rc.7** | Sessione/Allenamento/Gestione, bozza/focus, geometria condivisa, percorsi, trasferimento e Circuito Tecnico; correzioni PPO. | Installata e reboot; API 2.10/68, '+str(receipt['files'])+' file, archivi conservati. Tre temi EGLFS, gara 2/4 multigiro, PPO 30 minuti, confronto a cinque semi. [Report](v09-settings-circuits-report.md), residui dichiarati. |\n'+anchor)
s=s.replace('Il riferimento attuale è **API 2.9 / 68 superfici / Apple Calm 1.6.2**','Il riferimento attuale è **API 2.10 / 68 superfici / Apple Calm 1.6.2**')
start=s.index('**Stato:** candidata **0.9.0-rc.6')
end=s.index('\n\n',start)
s=s[:start]+'''**Stato:** candidata **0.9.0-rc.7 implementata e installata**, con [impostazioni/percorsi/Circuito Tecnico](v09-settings-circuits-report.md), dossier e Gara/Guida PPO conservati. A/B/C consegnati, S0–S5 non globalmente chiusi: robustezza, traffico, competenza PPO/NEAT, profili ampliati e input/lettura fisici restano da qualificare. Soak PPO di 30 minuti sulla pista tecnica e reboot attuali verificati; non sono certificazione ottica di 60 FPS. Ricompensa sperimentale: confronto storico misto conservato.''' +s[end:]
s=s.replace('4/6 sceglie Sintesi/Metodo/Storico/Risultati/Reset, 2/8 scorre e pagina, 5 cambia pilota sulla riga Pilota o apre i parametri della sessione.', '4/6 sceglie Sintesi/Metodo/Storico/Risultati, 2/8 scorre e pagina, 5 sulla riga Pilota apre il selettore o i parametri della sessione. Dalla rc.7 il reset si apre da Gestione e nomina pilota/circuito; non è una quinta scheda di consultazione.')
start=s.index('### Approfondimento impostazioni e circuito tecnico')
end=s.index('**RAM,',start)
s=s[:start]+'''### Impostazioni e Circuito Tecnico — consegna rc.7

[Studio originario e fonti](game-settings-circuits-ux-study.md), [implementazione e prove](v09-settings-circuits-report.md). Tre sezioni, avanzate per metodo, descrizioni e unità, selettori espliciti e bozza applicata una volta. 7 annulla/torna, focus per ID; dossier e Comandi coerenti. Pista tecnica curata da 272,052 m/10 m, vettura 4,4×1,8 m e rendering statico con gli stessi bordi del simulatore.

| Passo | Stato acquisito | Residui |
| --- | --- | --- |
| **A · Impostazioni** | Implementato; PC e tre temi EGLFS 960×640 a scala 1/1,1. Bozza senza scritture, focus, reset e selettori verificati. | Keypad/lettura fisici e valutazione del costo percepito dei passaggi. |
| **B · Geometria e ambiti** | TrackRuntime, indice/raggi equivalenti, cancelli direzionali, sagome, percorsi per pista/profilo e reset mirato. Migrazione reale senza modifiche ai piloti/artefatti. | Altri contenuti e prove di generalizzazione; rotazione discretizzata dichiarata. |
| **C · Circuito tecnico** | Cinque semi e budget uguale: 50/50 da trasferimento, 39/50 da zero. Gare native 2/3 giri e 4/5 giri, dieci giri selezionabili; una rete congelata per auto, griglia sfalsata e rosa qualificata per ambito/hash. PPO corretto e soak 30 minuti; pacchetto/backup/reboot. | Beneficio non uniforme, ritenzione della rete non universale; traiettorie nel traffico, competenza PPO/NEAT, profili ampliati e FPS/input fisici. |

Fisica/training/inferenza CPU. Trasferimento di pesi densi soltanto su percorso vuoto compatibile, con nuova qualifica; il modello originale dell'ovale rimane disponibile. NEAT richiede compatibilità di topologia specifica. Gli sviluppi futuri usano cataloghi e ambiti, senza rendere selezionabili fondi o vetture non implementati.

''' +s[end:]
start=s.index('**Prossimi passi:** approfondimento richiesto')
end=s.index('\n\n',start)
s=s[:start]+'''**Prossimi passi:** conservare A/B/C consegnati nella rc.7 e gli originali ovali; migliorare robustezza sui semi/scenari difficili, competenza traffico/Gara/PPO/NEAT, profili ampliati e uso fisico. Nuove piste/vetture/fondi e preset adattivi richiedono contenuti e confronti propri. Il carico prolungato rc.7 è verificato per PPO standard sulla pista tecnica, non per tutte le combinazioni esposte.''' +s[end:]
s=s.replace('1. **Baseline:** partire da 0.9.0-rc.6 / API 2.9 / Apple Calm 1.6.2;', '1. **Baseline:** partire da 0.9.0-rc.7 / API 2.10 / Apple Calm 1.6.2;')
start=s.index('3. **Gioco v0.9:**')
end=s.index('\n4.',start)
s=s[:start]+'''3. **Gioco v0.9:** usare la rc.7 con impostazioni/percorsi/Circuito Tecnico, dossier e Gara/Guida PPO. A/B/C sono implementati e installati; [report](v09-settings-circuits-report.md). Conservare confronti a budget uguale e campioni ovali originali. Restano taratura/robustezza, guida nel traffico, competenza PPO/NEAT, profili ampliati e input/lettura/FPS fisici. Non ripetere indiscriminatamente le prove acquisite; nuovi test risolvono rischi concreti.''' +s[end:]
s=s.replace('Circuito tecnico proposto nella famiglia v0.9.x con A/B/C, senza versione/data obbligatoria.', 'Circuito Tecnico consegnato nella rc.7; ulteriori contenuti della famiglia v0.9.x dopo gate propri.')
path.write_text(s)

readme=evidence.parents[2]/'README.md'
r=readme.read_text();start=r.index('**Candidata installata:');end=r.index('\n\n',start)
r=r[:start]+'''**Candidata installata: 0.9.0-rc.7 · 11 ottobre 2026.** Impostazioni Gioco Sessione/Allenamento/Gestione, bozza confermata, focus stabile e Circuito Tecnico. Percorsi per circuito/profilo, trasferimento esplicito, dossier e reset mirato; PPO con tempo episodio/bootstrap corretti. API 2.10 / 68 superfici / Apple Calm 1.6.2; archivi/preferenze preservati, tre temi EGLFS 960×640, gare 2/4 multigiro, PPO 30 minuti e reboot qualificato. [Consegna e limiti](design/v09-settings-circuits-report.md) · [MasterPlan 2.58](design/release-masterplan.md).''' +r[end:]
r=r.replace('Pista / Classifica / Progressi, ovale asfaltato asciutto e vettura standard.', 'Pista / Classifica / Progressi / Pilota, Ovale o Circuito Tecnico asfaltato asciutto e vettura standard. Sessione/Allenamento/Gestione con descrizioni, avanzate e bozza confermata; percorsi e classifiche distinti per circuito.');readme.write_text(r)
print('MasterPlan 2.58 / README reconciled from the verified rc.7 receipt')
