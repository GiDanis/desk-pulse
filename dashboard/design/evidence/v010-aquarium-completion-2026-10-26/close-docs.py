"""Reconcile current release documentation only after successful real delivery."""
import json
from pathlib import Path
E=Path(__file__).resolve().parent;DESIGN=E.parents[1];ROOT=DESIGN.parents[1];B=E/'board'
def read(p):return json.loads(p.read_text())
f=read(B/'final-receipt.json');n=read(B/'native-receipt.json');r=read(B/'aquarium-ui/report.json');art=read(E/'artwork.json');kit=read(E/'kit-check.json')
assert f['status']=='passed' and f['version']=='0.10.0-rc.2' and f['activeTheme']['version']=='1.6.5'
assert f['gameDatabasePreserved'] and f['policyArtifactsPreserved'] and f['allOtherPreferencesPreserved'] and f['appearanceOptionsPreserved']
assert f['service']['NRestarts']=='0' and not f['manifestMismatches'] and not f['newOSReboot']
assert n['status']=='passed' and n['preferencesPreserved'] and r['near60SoftwareGate']
for name in ('base-ui','functional-ui','aquarium-ui'):
 c=read(B/name/'report.json');assert c['checks'].count('requestedThemeSurvivesReentry')==20 and not c['warnings'] and not c['networkAttempts']
for name in ('pc-preflight.json','arm-preflight.json'):assert read(E/name)['result']['status']=='passed' and read(E/name)['result']['renderers']==1098
assert art['identicalPixelCells']==1080 and kit['sdkFiles']==673 and not kit['manifestMismatches'] and kit['standaloneSavedThemeReentries']==20
report='v010-aquarium-completion-report.md';receipt='evidence/'+E.name+'/board/final-receipt.json';ev='evidence/'+E.name
metric=f"{r['callbacksPerSecond']:.3f} callback/s, p95 {r['p95Ms']:.2f} ms"
text=f'''# v0.10 — chiusura dell’implementazione Acquario

26 ottobre 2026 · **core 0.10.0-rc.2 installata · Theme API 2.13 / 69 superfici · Apple Calm 1.6.5 attivo**.

Implementazione software completata e installata. [Ricevuta]({receipt}): 682 hash conformi, GUI pronta con PID corrente, NRestarts=0, backup disponibile e nessun nuovo reboot OS. Database e {f['policyArtifactCount']} artefatti Gioco conservati. Le preferenze mantengono i valori: cambiano soltanto l’identità del bundle attivo e il registro degli override per la nuova identità, con override correnti copiati e profili degli altri temi conservati.

## Che cosa completa questa consegna

La shell Apple mostrava il simbolo generico per Acquario. Il nuovo glifo a pesce segue lo stesso tratto, inset, palette e atlante PNG del tema. Le associazioni coprono la barra e le righe del modulo nelle impostazioni. È una revisione immutabile nuova; la precedente è recuperabile dal backup.

I 60 glifi precedenti restano identici pixel per pixel in tutti i 18 colori: **1.080 celle confrontate**, alias preesistenti conservati. Il delta del payload contiene soltanto versioni dei due manifesti, Format.js, IconPaths.js e l’atlante rigenerato. Nessun cambiamento a font, geometria, palette, movimento o contenuti delle altre viste. [Verifica artistica]({ev}/artwork.json), [bundle installabile]({ev}/apple-calm-1.6.5.smartpc-theme).

È corretto anche il banco dei rientri: prima manteneva il tema in anteprima, che Home annulla intenzionalmente. Per questo i vecchi venti cicli non dimostravano la permanenza del tema richiesto. Il banco ora salva la selezione **soltanto nelle preferenze private del test** e controlla l’identità dopo ciascun rientro. Nessuna modifica al comportamento di Home nell’applicazione. Il delta core rispetto alla rc.1 riguarda solo `check_aquarium_ui.py` e `version.py`; controller, asset, algoritmi e renderer Acquario sono byte per byte invariati. [Delta]({ev}/runtime-delta.json).

## Verifiche finali

- Preflight reale di tutti i renderer pubblici: **1.098 combinazioni PC e 1.098 ARM**, sul digest Apple Calm 1.6.5 finale.
- Main reale PC/EGLFS: immagine del pesce pronta, giorno/notte, movimento Ridotto/Disattivo, menu e ritorno a Home con l’icona dell’orologio.
- **20 rientri con Base, 20 con Functional e 20 con Apple Calm**, sia PC sia EGLFS; tema salvato controllato ogni volta, un solo clock e sei attori, pausa/menu/urgenze/Reduced/Off e orario verificati. Nessun warning QML inatteso o tentativo di rete nelle fixture.
- SDK esportato API 2.13, fingerprint invariato, **673 file con hash conformi** e prova autonoma di venti rientri con tema salvato. [Kit]({ev}/SmartPC-Theme-API-2.13-rc2.zip), [ricevuta]({ev}/kit-check.json).

[Ricevuta nativa]({ev}/board/native-receipt.json), [preflight PC]({ev}/pc-preflight.json), [preflight ARM]({ev}/arm-preflight.json), [icona/Main]({ev}/board/icon-ui/report.json).

## Prestazioni e attribuzione

Nuova misura EGLFS/PowerVR, sei pesci con rig, **60 s di riscaldamento + {r['seconds']:.2f} s registrati**, dopo i controlli di navigazione e con il tema salvato: **{metric}**; p99 {r['p99Ms']:.2f} ms, massimo {r['maxMs']:.2f} ms, {r['stallsOver50Ms']} stalli oltre 50 ms, slot mancati stimati {r['estimatedMissedSlotRatio']*100:.3f}%. Gate software vicino a 60 superato, con le soglie precedenti invariate. [Report grezzo completo]({ev}/board/aquarium-ui/report.json).

Le tre repliche nominali e la prova da **30 minuti / 59,971 callback/s / p95 18,03 ms** appartengono alla precedente **rc.1 con Apple Calm 1.6.4** e restano attribuite a quella combinazione. Non diventano un nuovo soak della 1.6.5. Le prove `--benchmark-only` precedenti non attraversavano Home e mantengono la loro validità; la correzione riguarda l’attribuzione dei cicli di navigazione. [Report iniziale e dati] (v010-aquarium-implementation-report.md).

Queste sono misure software della presentazione e delle pose, non FPS ottici, tempo GPU o latenza del tastierino fisico. La nuova misura è un supplemento da 120 s: non sostituisce il protocollo esteso A1/A2 con tre repliche per ogni carico/renderer.

Cattura nativa del test con il tema nuovo; non è lo schermo corrente della produzione:

![Acquario con icona dedicata]({ev}/board/icon-ui/day.png)

## Stato P0–P7

| Lotto | Implementazione e riscontro |
| --- | --- |
| P0 · Contratto/fixture | Completato nella rc.1: API 2.13, DTO/azioni, nove varianti e compatibilità additiva; invariato. |
| P1 · Lifecycle/controller | Completato: caricamento pigro, sospensione/ripresa/urgenze, epoch/close, senza timer Python di animazione. |
| P2 · Shell | Completato: routing/safeArea/barra/orario/dimming/menu, icona dedicata nella 1.6.5; tre temi verificati. |
| P3 · Pesce e movimento | Completato: rig e sprite locali, curve/clock/virate e test del JavaScript reale. |
| P4 · Scena | Completato: due specie/sei istanze, asset originali e profili giorno/notte/statici. |
| P5 · Capacità/strumenti | Implementati: banco, screening 1/4/8/16 e confronto rig/sprite acquisiti. Matrice prestazionale estesa ancora distinta. |
| P6 · Packaging/qualifica | Pacchetti/SDK/manifest e backup completati; 30 min precedenti e nuovo supplemento EGLFS attribuiti alle rispettive versioni. Fisico/live/uso lungo aperti. |
| P7 · Consegna | Rc.2 e Apple 1.6.5 installati con ricevuta, controllo GUI e conservazione dei dati; nessun reboot OS. |

## Conservazione e limiti

Backup quiescente: `{f['backup']}`. Runtime precedente: `{f['runtimeRollback']}`. La transazione conserva anche configurazioni e intero stato dei temi; ripristino automatico in caso di errore. Il percorso di rollback è disponibile, senza simulare un guasto durante questa consegna.

Non restano segnaposto funzionali per il perimetro Acquario richiesto. Restano qualifica fisica di pannello/HID e qualità visiva umana, FPS ottici/tempi GPU, carichi concorrenti delle fonti reali, intera matrice A1/A2 e uso 24/7. Le fixture isolate non provano il carico live. La candidata non è promossa stabile. Compagno v0.11, Memoria/AI v0.12 e Stabilità v1.1 conservano sequenza e scopo; Gioco resta in manutenzione e nessun training/reset è eseguito.
'''.replace('[Report iniziale e dati] (','[Report iniziale e dati](')
(DESIGN/report).write_text(text)
# All current MasterPlan surfaces, preserving historic measurements/version identities.
p=DESIGN/'release-masterplan.md';s=p.read_text();lines=[]
for line in s.splitlines():
 if line.startswith('**Revisione '):line='**Revisione 3.26 · 26 ottobre 2026 · Europe/Rome**'
 elif line.startswith('**Baseline verificata:'):line='**Baseline verificata: core 0.10.0-rc.2 installata · manifest 682 file · Theme API 2.13 · 69 superfici · Apple Calm 1.6.5 attivo, incidente 1.6.2 conservato.**'
 elif line.startswith('**Acquario v0.10 — consegnata'):line=f'**Acquario v0.10 — implementazione completata e rc.2 installata:** scena a due specie/sei pesci, icona dedicata Apple Calm 1.6.5 e banco corretto con tema salvato: venti rientri per ciascuno dei tre temi PC/EGLFS. Nuovo supplemento120s: {metric}. Le precedenti tre repliche e durata30min restano attribuite a rc.1/Apple1.6.4. 682 hash, GUI pronta/NRestarts=0, preferenze e archivio Gioco conservati. Nessun reboot OS; fisico/live e matrice estesa distinti. [Chiusura]({report}), [ricevuta]({receipt}).'
 elif line.startswith('| Core |'):line=f'| Core | **0.10.0-rc.2 installata**, 682 file | [Chiusura Acquario]({report}): icona e banco dei rientri corretti, controlli PC/EGLFS e manifest conformi. Dati/preferenze conservati, GUI pronta/NRestarts=0; candidata non stabile. |'
 elif line.startswith('| Tema attivo corrente |'):line=f'| Tema attivo corrente | **Apple Calm 1.6.5 attivo**; Base e Functional verificati | [Consegna]({report}): aggiunta icona Acquario, 60 glifi ×18 colori preesistenti identici. Palette/font/layout conservati; revisioni precedenti e incidente1.6.2 restano storici. |'
 elif line.startswith('| Reboot |'):line=line.replace('e0.10.0-rc.1','e 0.10.0-rc.1/rc.2')
 elif line.startswith('| Gioco v0.9 |'):line=line.replace('0.10.0-rc.1','0.10.0-rc.2')
 elif line.startswith('| **v0.10.0-rc.1** |'):
  lines.append(f'| **v0.10.0-rc.2** | Chiusura Acquario: icona Apple1.6.5, prova dei rientri con tema salvato e SDK aggiornato. | Installata, 682 hash; 20 rientri per tema PC/EGLFS, nuovo supplemento120s vicino60, dati/preferenze conservati e NRestarts=0. [Report/ricevuta]({report}). |')
  line=line.replace('venti rientri per tema, ','cicli in anteprima poi ricontrollati nella rc.2, ')
 elif line.startswith('Il riferimento attuale è **API'):line=line.replace('Apple Calm 1.6.4','Apple Calm 1.6.5')
 elif line.startswith('| **v0.10 — Acquario Calm** |'):line=f'| **v0.10 — Acquario Calm** | Argomento2D fullscreen, due specie/sei pesci e asset Calm locali. | Implementazione completata, rc.2/Apple1.6.5 installati. [Chiusura]({report}); fisico/live e qualifica estesa distinti. |'
 elif line.startswith('**Implementata e installata come candidata0.10') or line.startswith('**Implementata e installata come candidata 0.10'):
  line=line.replace('0.10.0-rc.1','0.10.0-rc.2').replace('Apple Calm **1.6.4**','Apple Calm **1.6.5**');line=line.replace('Apple Calm **1.6.5** conserva identità e payload.','Apple Calm **1.6.5** aggiunge l’icona Acquario con una nuova identità immutabile, conservando palette, font, geometria e gli altri file grafici.');line+=f' [Chiusura esecutiva]({report}), icona e rientri con tema salvato completati.'
 elif line.startswith('**Prestazioni:** tre repliche nominali'):
  line=f'**Prestazioni:** nuovo supplemento120s rc.2/Apple1.6.5: {metric}, dopo venti rientri con il tema salvato. Tre repliche120s e durata30min della rc.1/Apple1.6.4 restano conservate nella loro versione. Scala1/4/8/16 e rig/sprite sono screening brevi; matrice A1/A2 completa, FPS ottici, HID e carichi live restano distinti. Compagno v0.11, Memoria/AI v0.12 e Stabilità v1.1 invariati. [Report]({report}).'
 elif line.startswith('| Acquario v0.10 |'):line=f'| Acquario v0.10 | Qualifica fisica/ottica/HID, fonti live concorrenti e protocollo esteso A1/A2. | [Implementazione completata e rc.2 installata]({report}). Rientri corretti nei tre temi e nuovo supplemento120s passati; durata30min precedente attribuita a rc.1/Apple1.6.4. |'
 elif line.startswith('| Identità distribuzione |'):line=f'| Identità distribuzione | Core0.10.0-rc.2 / API2.13 / Apple Calm1.6.5 attivo. | [Ricevuta]({receipt}): 682 hash, GUI pronta/NRestarts=0, dati e opzioni conservati. Solo identità del tema e registro override aggiornati. |'
 elif line.startswith('1. **Baseline:**'):line=f'1. **Baseline:** 0.10.0-rc.2 / API2.13 /69 superfici /Apple Calm1.6.5 installati. [Ricevuta]({receipt}), 682 hash conformi. Pacchetto esatto nelle evidenze della chiusura; conservare l’esclusione dei prototipi estranei del checkout dalla prossima consegna.'
 lines.append(line)
p.write_text('\n'.join(lines)+'\n')
# Initial report: keep historical raw proof and correct the overbroad navigation claim.
p=DESIGN/'v010-aquarium-implementation-report.md';s=p.read_text();s=s.replace('**Stato corrente: implementata, verificata PC/ARM/EGLFS e installata come candidata 0.10.0-rc.1.**',f'**Consegna iniziale rc.1: superata dalla [chiusura rc.2 / Apple1.6.5]({report}).** Le misure di questo documento restano attribuite alla rc.1 / Apple1.6.4.')
s=s.replace('La sua shell precedente usa l’icona generica per la nuova famiglia; un’icona Acquario dedicata richiederebbe una nuova revisione del bundle, separata da questa consegna core.',f'La shell della consegna iniziale usava l’icona generica; l’icona dedicata è consegnata nella [Apple1.6.5]({report}).')
s=s.replace('venti cicli di uscita/rientro per tema e Home.',f'venti cicli di uscita/rientro e Home. Il tema era in anteprima e Home la annullava: questi cicli non qualificano la permanenza del tema richiesto. La prova corretta, con selezione salvata e identità verificata a ogni rientro nei tre temi, è nella [rc.2]({report}).')
p.write_text(s)
# User-facing and authoring entry points.
p=ROOT/'dashboard/README.md';s=p.read_text();ls=s.splitlines();ls=[f'**v0.10.0-rc.2 — Acquario Calm installata:** scena a due specie/sei pesci, icona Apple1.6.5, rientri verificati con il tema salvato e SDK API2.13 aggiornato. Dati/preferenze conservati. [Chiusura, prove e ricevuta](design/{report}).' if line.startswith('**v0.10.0-rc.1 — Acquario Calm installata:**') else line for line in ls];p.write_text('\n'.join(ls)+'\n')
apple=ROOT/'theme-projects/apple-calm';p=apple/'README.md';s=p.read_text();s=s.replace('# Apple Calm 1.6.3',f'# Apple Calm 1.6.5\n\n**Installata con core0.10.0-rc.2 / API2.13:** icona Acquario dedicata, glifi precedenti identici, geometria/font/palette conservati. [Chiusura e ricevuta](../../dashboard/design/{report}).',1)
s=s.replace('Revisione **1.6.3 installata e selezionabile**','Consegna storica: revisione **1.6.3 installata e selezionabile**').replace('sorgente modificabile dei 60 glifi','sorgente modificabile dei 61 glifi')
s=s.replace('- `tools/blueprint/` e `tools/assemble.py`: rigenerano manifesti, registro ed entry point. Dopo una modifica alle icone eseguire il generatore, poi l\'assemblatore per aggiornare l\'inventario delle risorse.','- `tools/blueprint/` e `tools/assemble.py`: strumenti storici con blueprint1.6.1, da riallineare prima di rigenerare l’intero bundle corrente. Per la1.6.5 sono stati rigenerati soltanto i due asset iconici esistenti e aggiornate le versioni dei manifesti; nessun nuovo percorso richiede modifica dell’inventario. Il bundle corrente e il delta verificato sono il riferimento.')
p.write_text(s)
p=apple/'CONSEGNA.md';s=p.read_text();pos=s.index('## Revisione 1.6.4');s=s[:pos]+f'''## Revisione 1.6.5 · 26 ottobre 2026

Installata con core0.10.0-rc.2. Glifo Acquario per barra e impostazioni; 1.080 celle dei60 glifi precedenti identiche. Preflight1.098 combinazioni PC/ARM, Main/EGLFS e rientri con il tema salvato passati. Nuovo supplemento120s: {metric}. 682 hash core, dati/opzioni e profili degli altri temi conservati, GUI pronta/NRestarts=0 e nessun reboot OS. [Chiusura e ricevuta](../../dashboard/design/{report}). La durata30min precedente resta attribuita alla1.6.4; candidata non promossa stabile.

'''+s[pos:];p.write_text(s)
for name in ('v010-aquarium-analysis.md','v010-aquarium-integration-study.md','v010-aquarium-online-research.md','v010-aquarium-implementation-plan.md'):
 p=DESIGN/name;s=p.read_text();marker='> Aggiornamento esecutivo, 26 ottobre:';ls=s.splitlines();ls=[f'> Aggiornamento esecutivo, 26 ottobre: implementazione completata e rc.2/Apple1.6.5 installati. Questo documento conserva lo studio precedente; [chiusura, stato P0–P7 e limiti]({report}).' if line.startswith(marker) else line for line in ls];p.write_text('\n'.join(ls)+'\n')
(E/'WORK-STATE.md').write_text(f'# Chiusura effettiva ·26 ottobre2026\n\nRc.2/Apple1.6.5 installati. 682 hash, NRestarts=0 e dati/opzioni/profili conservati. 20 rientri per tema PC/EGLFS con tema salvato; {metric} nel supplemento120s. SDK673file aggiornato e verificato.\n\nTutta implementazione Acquario conclusa; fisico/live/esteso/24h separati. Le misure30min precedenti restano attribuite a rc.1/Apple1.6.4. Dettagli e backup nel report/ricevuta.\n')
print(json.dumps({'documentation':'closed','version':f['version'],'theme':f['activeTheme'],'native120s':metric}))
