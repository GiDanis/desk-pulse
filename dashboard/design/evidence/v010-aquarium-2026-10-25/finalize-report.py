"""Close documentation only after the real installation and frozen native proof."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
DESIGN=OUT.parents[1]
def read(path):return json.loads(path.read_text())
final=read(OUT/'board/final-receipt.json');native=read(OUT/'board/qualification-receipt.json');summary=read(OUT/'benchmark-summary.json')
assert final['status']=='passed' and final['version']=='0.10.0-rc.1' and final['files']==682
assert final['allPreferencesPreserved'] and final['gameDatabasePreserved'] and final['policyArtifactsPreserved']
assert final['service']['NRestarts']=='0' and not final['manifestMismatches'] and not final['newOSReboot']
assert native['sameSourceForAllCases'] and native['preferencesPreserved'] and len(native['results'])==15
assert summary['sourceTreeSha256']==native['sourceTreeSha256']
by={r['caseId']:r for r in summary['cases']}
for name in ('nominal-1','nominal-2','nominal-3','soak30'):assert by[name]['near60SoftwareGate']
soak=by['soak30'];assert soak['seconds']>=1800
receipt='evidence/v010-aquarium-2026-10-25/board/final-receipt.json'
report='v010-aquarium-implementation-report.md'
def fmt(value,places=2):return '—' if value is None else f'{value:.{places}f}'
headline=f"{fmt(soak['callbacksPerSecond'],3)} callback/s, p95 {fmt(soak['p95Ms'])} ms su 30 minuti"
# Report: retain design, exact test scopes and residuals; replace provisional state.
p=DESIGN/report;s=p.read_text();lines=s.splitlines()
lines=[f'**Stato corrente: implementata, verificata PC/ARM/EGLFS e installata come candidata 0.10.0-rc.1.** 682 hash conformi, Apple Calm 1.6.4 conservato, GUI pronta e NRestarts=0; preferenze, database e artefatti Gioco preservati. Nessun nuovo reboot OS. [Ricevuta]({receipt}).' if l.startswith('**Stato corrente:') else l for l in lines]
s='\n'.join(lines)+'\n';s=s.replace('Risultati finali ancora da acquisire.','Risultati finali acquisiti sulla stessa impronta dei sorgenti; nessuna soglia modificata dopo le prove.')
if '## Prestazioni native finali' in s:
 start=s.index('## Prestazioni native finali');end=s.index('## Distribuzione e conservazione',start)
 s=s[:start]+s[end:]
metrics=['## Prestazioni native finali','','Tutte le righe seguenti usano EGLFS/PowerVR e i sorgenti finali congelati. Tre repliche nominali distinte; gli stress e gli sprite restano campioni più brevi, con durata esplicita.','','| Caso | Pesci / renderer | Secondi | Callback/s | p95 ms | p99 ms | max ms | Slot stimati persi | Stalli >50ms |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
for r in summary['cases']:
 if r['caseId'].startswith(('nominal','scale','sprite','soak')):
  metrics.append(f"| {r['caseId']} | {r['population']} / {r['renderer']} | {fmt(r['seconds'],1)} | {fmt(r['callbacksPerSecond'],3)} | {fmt(r['p95Ms'])} | {fmt(r['p99Ms'])} | {fmt(r['maxMs'])} | {r['estimatedMissedSlots']} ({fmt(r['estimatedMissedSlotRatio']*100,3)}%) | {r['stallsOver50Ms']} |")
res=soak['resources'];w1=soak['windows']['1'];w10=soak['windows']['10']
metrics+=['',f"Durata: **{headline}**. Peggiore finestra completa da 1 s: {fmt(w1['worstCallbackRate']['callbacksPerSecond'],1)} callback/s; massimo p95 nelle finestre da 10 s: {fmt(w10['worstP95']['p95Ms'])}ms. Le code parziali sono esplicite e restano nel dataset grezzo e nel gate complessivo.",'',f"RSS {fmt(res['firstRssMiB'])}→{fmt(res['lastRssMiB'])}MiB, massimo {fmt(res['maxRssMiB'])}MiB; CPU media {fmt(res['cpuPercentOfOneCoreMean'])}% di un core; temperatura massima campionata {fmt(res['maxTemperatureC'],1)}°C. Thread {res['firstThreads']}→{res['lastThreads']}, FD {res['firstFds']}→{res['lastFds']}. L’RSS comprende il buffer dei timestamp del banco.",'',f"Impronta sorgenti: `{native['sourceTreeSha256']}`. [Riepilogo/finestre](evidence/v010-aquarium-2026-10-25/benchmark-summary.json), [CSV 1/10/120 s](evidence/v010-aquarium-2026-10-25/benchmark-windows.csv), [ricevuta di qualifica](evidence/v010-aquarium-2026-10-25/board/qualification-receipt.json). I callback e le pose non certificano 60 FPS ottici.",'']
s=s.replace('## Distribuzione e conservazione','\n'.join(metrics)+'\n## Distribuzione e conservazione',1)
s=s.replace('Percorsi di backup e rollback saranno nella ricevuta effettiva.',f"Backup quiescente: `{final['backup']}`. Runtime precedente: `{final['runtimeRollback']}`. {final['policyArtifactCount']} artefatti Gioco e tabelle conservati, tutte le preferenze confrontate uguali. Il rollback è disponibile e non è stato provocato un guasto per esercitarlo in questa consegna.")
p.write_text(s)
# MasterPlan: update every current-state surface, leaving historical releases intact.
p=DESIGN/'release-masterplan.md';s=p.read_text();lines=s.splitlines();new=[]
for line in lines:
 if line.startswith('| **v0.10.0-rc.1** |'):continue
 if line.startswith('**Baseline verificata:'):line='**Baseline verificata: core 0.10.0-rc.1 installata · manifest 682 file · Theme API 2.13 · 69 superfici · Apple Calm 1.6.4 attivo, incidente 1.6.2 conservato.**'
 elif line.startswith('**Revisione 3.24'):line=line.replace('3.24','3.25',1)
 elif line.startswith('**Acquario v0.10 — implementazione autorizzata'):line=f'**Acquario v0.10 — consegnata il 26 ottobre:** due specie/sei pesci, canvas 960×640, barra/HH:mm e avvisi conservati; API 2.13 e SDK aggiornati. Tre repliche native e durata 30 minuti passate: {headline}, misura software. 682 hash, GUI pronta/NRestarts=0; dati/preferenze e Apple Calm 1.6.4 conservati, backup disponibile, nessun reboot OS. Candidata, qualifica ottica/HID/live distinta. [Report]({report}), [ricevuta]({receipt}).'
 elif line.startswith('| Core |'):line=f'| Core | **0.10.0-rc.1 installata**, 682 file | [Acquario]({report}): scena/API/asset, prove PC/EGLFS, durata 30 minuti e manifest conformi; dati/preferenze conservati, GUI pronta e NRestarts=0. Candidata non promossa stabile. |'
 elif line.startswith('| Contratto dei temi |'):line=f'| Contratto dei temi | **SmartPC.ThemeApi 2.13**, 69 superfici | AquariumContext/DTO/azioni aggiunti, kit con asset e template; durata dei risultati pubblici corretta e verificata. [Report]({report}). Import precedenti e ShellContext.clock conservati. |'
 elif line.startswith('| Reboot |'):line='| Reboot | Tre reboot OS qualificati nella **0.9.3-rc.1** | 0.9.4-rc.1/rc.2/rc.3 e0.10.0-rc.1 riavviano il servizio e conservano il boot ID; nessun nuovo reboot OS. |'
 elif line.startswith('| Sport in corso |'):line='| Sport/live | Routing e consultazioni già consegnati; qualifica live distinta | La consegna Acquario conserva i provider e non riqualifica freschezza, reconnect o latenza delle fonti reali. |'
 elif line.startswith('| Gioco v0.9 |'):line='| Gioco v0.9 | **Fase funzionale chiusa / manutenzione**, conservata nella 0.10.0-rc.1 | Rosa, progressi e artefatti preservati; chiusura funzionale della rc.3 invariata. [P0–P9](game-reference-integration-plan.md) parzialmente completato: ricerca competitiva rinviata e nuovi modelli non qualificati. |'
 elif line.startswith('| **Acquario** |'):continue
 elif line.startswith('| **v0.10 — Acquario Calm** |'):line=f'| **v0.10 — Acquario Calm** | Argomento 2D fullscreen, due specie/sei pesci, asset locali Calm. | 0.10.0-rc.1 installata; tre repliche e durata 30 minuti passate, vicino a 60 software. [Report]({report}). Fisico/live ancora distinti. |'
 elif line.startswith('Il riferimento attuale è **API 2.11'):line=line.replace('API 2.11 / 68 superfici / Apple Calm 1.6.3','API 2.13 / 69 superfici / Apple Calm 1.6.4')
 elif line.startswith('| Acquario v0.10 |'):line=f'| Acquario v0.10 | Qualifica fisica/ottica/HID, concorrenza live e protocollo esteso A1/A2. | [Implementata/installata]({report}), tre repliche da 120 s e soak30min finali passati; scala1/4/8/16 e confronto sprite brevi. Nessuna promozione stabile o 60 FPS fisici dichiarati. |'
 elif line.startswith('| Identità distribuzione |'):line=f'| Identità distribuzione | Core 0.10.0-rc.1, API 2.13, Apple Calm 1.6.4 attivo. | [Ricevuta]({receipt}): 682 hash, tutte le preferenze e archivio Gioco conservati, GUI pronta/NRestarts=0. |'
 elif line.startswith('1. **Baseline:**'):line=f'1. **Baseline:** 0.10.0-rc.1 installata / API 2.13 / 69 superfici / Apple Calm 1.6.4 attivo. [Ricevuta]({receipt}), 682 file conformi. Distribuzione completa nelle evidenze Acquario. Il checkout conserva prototipi estranei: partire dalla distribuzione verificata e confrontare il delta prima della prossima consegna.'
 elif line.startswith('5. **In corso:** Acquario'):line=f'5. **Acquario consegnato, poi Compagno:** [candidata v0.10]({report}) installata, con gate fisici/live ancora distinti. Seguono Compagno v0.11, Memoria/AI v0.12 e Stabilità v1.1. Gioco resta in manutenzione; nuove ricerche scientifiche soltanto su richiesta, senza rinumerare le release successive. Hardware/Cyberdeck, Media/Spotify, camera/audio, altri giochi e generatore restano senza release obbligatoria assegnata.'
 if line.startswith('| **v0.9.4-rc.3** |'):new.append(f'| **v0.10.0-rc.1** | Acquario Calm, API 2.13 e asset animati locali; integrazione della shell e fix di durata ActionResult. | Installata 26 ottobre, 682 hash; tre temi, venti rientri per tema, tre repliche da 120 s e soak30min. Preferenze/archivio Gioco conservati, Apple Calm 1.6.4 attivo, NRestarts=0, nessun reboot OS. [Report/ricevuta]({report}). |')
 new.append(line)
 if line.startswith('| **Gioco** |'):new.append('| **Acquario** | Scena Calm a tutto schermo | Due specie/sei pesci, nuoto e virate locali; 5 pausa/ripresa e 9 Menu. Urgenze e overlay sospendono, Reduced/Off statici; barra e HH:mm conservati. |')
s='\n'.join(new)+'\n'
a=s.index('## 11. v0.10');b=s.index('## 12.',a);section=s[a:b]
section=section.replace('**Implementata come candidata 0.10.0-rc.1, qualifica finale in corso.**',f'**Implementata e installata come candidata 0.10.0-rc.1 il 26 ottobre.** [Ricevuta]({receipt}).')
start=section.index('**Prestazioni:**');section=section[:start]+f'**Prestazioni:** tre repliche nominali da 120 s / 60 s warm-up e durata 30 minuti passate sulla stessa impronta finale: {headline}. Scala 1/4/8/16 e sprite 1/6 come screening breve, senza cambiare soglie. Verifiche di alpha/clipping/ingombro e durata dei risultati pubblici passate. FPS ottici, input fisico, fonti live concorrenti e intera matrice estesa A1/A2 restano distinti. Compagno v0.11, Memoria/AI v0.12 e Stabilità v1.1 mantengono scopo e numerazione.\n\n'
s=s[:a]+section+s[b:];p.write_text(s)
# Point the earlier research/specification to the achieved candidate, not a stale promise.
for name in ['v010-aquarium-analysis.md','v010-aquarium-integration-study.md','v010-aquarium-online-research.md','v010-aquarium-implementation-plan.md']:
 p=DESIGN/name;s=p.read_text();s=s.replace('Aggiornamento esecutivo, 25 ottobre: implementazione autorizzata e candidata in verifica.','Aggiornamento esecutivo, 26 ottobre: candidata implementata, verificata e installata; perimetri software/fisico distinti.');s=s.replace('**Stato:','**Stato dello studio alla redazione:',1);p.write_text(s)
p=DESIGN.parent/'README.md';s=p.read_text();s=s.replace('**v0.9.4-rc.3 —','**Consegna precedente v0.9.4-rc.3 —',1)
if '**v0.10.0-rc.1 — Acquario Calm installata:**' not in s:
 s=s.replace('# DeskPulse / SmartPC Dashboard\n','# DeskPulse / SmartPC Dashboard\n\n**v0.10.0-rc.1 — Acquario Calm installata:** due specie/sei pesci animati, controlli e sospensioni integrati nella shell; API 2.13 e SDK aggiornati. Tre repliche native e durata di 30 minuti passate. Preferenze, dati del Gioco e Apple Calm 1.6.4 conservati. [Report, misure e ricevuta](design/v010-aquarium-implementation-report.md).\n',1)
p.write_text(s)
(OUT/'WORK-STATE.md').write_text(f'# Stato finale · 26 ottobre 2026\n\n0.10.0-rc.1 installata, 682 hash conformi. Apple Calm 1.6.4 e tutti i dati/preferenze conservati; GUI pronta/NRestarts=0, nessun reboot OS.\n\n{headline}. Tutti i 15 casi finali e i gate nominali/durata passati con sorgenti congelati.\n\nRicevute in board/, dettagli nel report e MasterPlan. Qualifica ottica/HID/live e matrice estesa restano separati.\n')
print(json.dumps({'status':'updated','version':final['version'],'files':final['files'],'soak':headline}))
