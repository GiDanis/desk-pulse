"""Publish measured feasibility only after final native proof and restored GUI."""
import json
from pathlib import Path
E=Path(__file__).resolve().parent;D=E.parents[1]
def read(p):return json.loads(p.read_text())
s=read(E/'comparison-summary.json');receipt=read(E/'board/measure-receipt.json');health=read(E/'board/final-health.json');deps=read(E/'dependency-overlay.json');a=s['nominalSixFish']['2d'];b=s['nominalSixFish']['3d'];delta=s['nominalSixFish']['delta3dMinus2d'];cases=s['cases']
assert s['status']=='completed_with_unsupported_option' and s['measuredCases']==10 and len(s['unsupportedCases'])==1
assert receipt['productionUnchanged'] and receipt['sourceUnchanged']
supplement=read(E/'board/supplement-receipt.json')
assert receipt['status']=='incomplete' and supplement['status']=='passed' and supplement['productionUnchanged'] and supplement['sourceUnchanged']
assert health['version']=='0.10.0-rc.2' and health['activeTheme']['version']=='1.6.5' and health['files']==682 and not health['manifestMismatches']
assert health['service']['ActiveState']=='active' and health['service']['NRestarts']=='0' and health['guiHeartbeat']['ready'] and health['guiHeartbeat']['ageSeconds']<5 and health['guiHeartbeat']['pid']==health['runtimePid']
ev='evidence/'+E.name;report='v010-aquarium-3d-cost-report.md'
headline='Il campione 3D supera il gate software vicino a 60 fps in tutte e tre le repliche nominali.' if b['allNear60Gates'] else 'Il campione 3D resta vicino a 60 callback/s di media, ma nessuna delle tre repliche nominali supera il gate di regolarità.'
lines=[f'''# Acquario — costo del vero 3D sulla Orange Pi

**Misurato 26–27 ottobre 2026 · esperimento isolato, nessuna consegna 3D.** Produzione ripristinata sulla **0.10.0-rc.2 / Apple Calm 1.6.5**, 682 hash conformi, GUI pronta/NRestarts=0. Manifest, preferenze, tabelle e artefatti Gioco e bootID invariati. Nessun aggiornamento/installazione di pacchetti nel sistema, nessun nuovo reboot OS. Dieci casi misurati; un’opzione non supportata nella configurazione provata. [Primo stadio interrotto su MSAA]({ev}/board/measure-receipt.json), [due prove residue completate]({ev}/board/supplement-receipt.json), [controllo finale]({ev}/board/final-health.json).

## Risultato principale

{headline} Rispetto al 2D, con sei pesci, la mediana delle tre prove comporta **{delta['cpuOneCorePercentagePoints']:+.2f} punti percentuali di un core CPU** e **{delta['rssMiB']:+.2f} MiB di RSS**. Rapporto di CPU {delta['cpuRatio']:.2f}×. È il costo di questo modello e di questo rig: non una misura universale del 3D né un’approvazione dei modelli artistici finali.

| Sei pesci · tre repliche per renderer | Callback/s mediana | p95 min–max ms | CPU mediana, % di un core | RSS mediano MiB | Gate superati |
| --- | --- | --- | --- | --- | --- |''']
for name,r in [('2D illustrato',a),('3D procedurale',b)]:lines.append(f"| {name} | {r['callbacksMedian']:.3f} | {r['p95MinMs']:.2f}–{r['p95MaxMs']:.2f} | {r['cpuOneCorePercentMedian']:.2f}% | {r['rssMiBMedian']:.2f} | {r['gatePassCount']}/3 |")
for mode in ('2d','3d'):
 rows=[r for r in cases if r['caseId'].startswith('nominal-'+mode+'-')]
 values=[r['resources']['cpuOneCorePercent'] for r in rows]
 lines+=['',f"CPU {mode.upper()}, intervallo tra repliche: **{min(values):.2f}–{max(values):.2f}% di un core**. La mediana riassume questi campioni; frequenze CPU/GPU e relativo margine non sono stati registrati durante le finestre."]
lines+=['',f"CPU indica user+system di tutti i thread, rapportati a **un solo core**, non all’intera CPU a otto core. RSS è memoria fisica del processo, non memoria GPU. Temperatura massima campionata nelle repliche: 2D {a['temperatureMaxC']:.1f} °C, 3D {b['temperatureMaxC']:.1f} °C. Nessun dato sui watt assorbiti.",'','## Campione e confronto controllato','',
'''Il prototipo è volumetrico: mesh con posizioni/normali/indici, prospettiva, occlusione e orientamento tridimensionale; coda e pinne sono parti solide animate con trasformazioni. Nove Model per pesce: corpo, coda, tre pinne, due occhi e due pupille. Geometrie condivise: **900 triangoli per pesce** nel profilo leggero, **3.492** nel profilo più fitto. Due luci direzionali, materiali Principled opachi; niente texture sui pesci, skinning dei vertici, ombre, caustiche, particelle, riflessi o postprocessing.

Sono copie private della stessa Main e degli stessi provider/contesti isolati. Il 2D usa il renderer illustrato installato; il 3D sostituisce soltanto il visuale. Controller, seed, traiettorie Bézier, velocità/fase, popolazione, geometria nominale, fondale, barra, orario e tema salvato sono conservati. La prospettiva è compensata per mantenere una taglia comparabile in pixel; la sagoma resta diversa, soprattutto nelle virate. La qualità artistica dei due campioni non è equivalente: il modello 3D è una sonda geometrica, senza i dettagli delle illustrazioni.

La scena 3D usa View3D Offscreen a **960×640 effettivi**, integrato sotto la stessa shell. La texture intermedia comporta un costo possibile, documentato da [Qt](https://doc.qt.io/qt-6.8/qml-qtquick3d-view3d.html). Non sono state usate riduzioni di risoluzione, modifiche del governor, priorità o driver per far passare il 3D.''','',
f'''Le sei dipendenze compatibili sono state **scaricate ed estratte in una cartella separata**: {deps['compressedBytes']/1048576:.2f} MiB compressi, {deps['extractedBytes']/1048576:.2f} MiB di file estratti. Qt Quick 3D 6.8.2 e binding PySide6 6.8.2.1. LD_LIBRARY_PATH, QML_IMPORT_PATH e percorso del modulo Python valgono soltanto per i processi di prova. [Inventario e hash]({ev}/dependency-overlay.json).''','',
'## Tutte le misure native','',
'| Caso | Secondi | Callback/s | Pose/s | p95 ms | p99 ms | max ms | CPU % di un core | RSS MiB | Stalli >50 ms | Gate |',
'| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
for r in cases:
 q=r['resources'];lines.append(f"| {r['caseId']} | {r['seconds']:.1f} | {r['callbacksPerSecond']:.3f} | {r['poseTicksPerSecond']:.3f} | {r['p95Ms']:.2f} | {r['p99Ms']:.2f} | {r['maxMs']:.2f} | {q['cpuOneCorePercent']:.2f} | {q['rssMedianMiB']:.2f} | {r['stallsOver50Ms']} | {'passa' if r['near60SoftwareGate'] else 'non passa'} |")
lines.append('| aa4-3d | n/d | n/d | n/d | n/d | n/d | n/d | n/d | n/d | n/d | MSAA disabilitato da Qt: non qualificato |')
lines+=['',
'''Un pesce: 30 s di riscaldamento + 60 s registrati per renderer. Nominale: **60 s + 120 s, tre processi per renderer**, ordine 2D→3D→3D→2D→2D→3D. Mesh più fitta: 30 s + 60 s; stress a 16 pesci: 15 s + 30 s. Questi ultimi due sono screening brevi, non repliche nominali né durata prolungata.

**MSAA 4× non qualificato:** alla richiesta `MSAA / High`, Qt segnala `Multisample renderbuffers are not supported, disabling MSAA for Offscreen View3D`. Il banco rifiuta il ripiego e conserva il primo stadio come incompleto. Nessuna prestazione senza antialiasing viene attribuita a MSAA. Le due prove residue usano lo stesso codice e gli stessi hash in un protocollo separato, senza antialiasing. Non è una diagnosi dell’intera capacità hardware: riguarda questa integrazione EGLFS/Offscreen.

Soglie congelate prima della misura: callback medi ≥59/s, p95 ≤18,5 ms, slot mancati stimati ≤1%, meno di 2 stalli >50 ms, almeno 58 pose/s. Un esperimento completato può contenere configurazioni che falliscono il gate: non si eliminano righe o picchi e non si modificano le soglie. Percentili nearest-rank; risorse ogni 10 s; catture e contatori di rendering estesi raccolti dopo la finestra. Il tempo di apertura parte dall’inizializzazione della Main, esclude l’import Python e non equivale al boot/cold-start della dashboard.''','',
f'[Protocollo congelato]({ev}/board/measure-protocol.json), [protocollo residuo]({ev}/board/supplement-protocol.json), [log MSAA]({ev}/board/measure/aa4-3d/run.log), [riepilogo verificato]({ev}/comparison-summary.json), [finestre di 1/10 s]({ev}/worst-windows.csv). I dati grezzi sono sotto `{ev}/board/measure/` e `{ev}/board/supplement/`. Le code parziali delle finestre restano nei raw e nel gate complessivo.','',
'## Driver, contatori e limiti','']
ctx=next(r['actualGlContext'] for r in cases if r['mode']=='3d')
lines.append(f"Contesto ottenuto durante il rendering: **{ctx['vendor']} / {ctx['renderer']} / {ctx['version']}**. Il formato Qt espone {ctx['formatMajor']}.{ctx['formatMinor']}; non va confuso con la stringa di versione del driver. Nessuna deduzione della GPU dal solo nome del pacchetto.")
lines+=['',
'''Il runtime segnala che nel backend provato non sono abilitate le texture RGBA32F/RGBA16F per le particelle. Il messaggio esatto è registrato in capabilityWarnings; ogni altro warning QML viene rifiutato. Il controllo è eseguito anche creando una scena priva di particelle nel [codice Qt 6.8.2](https://github.com/qt/qtquick3d/blob/v6.8.2/src/runtimerender/rendererimpl/qssglayerrenderdata.cpp). È un limite della configurazione provata: non dimostra l’assenza della capacità nell’hardware e non qualifica future particelle/HDR.

I contatori Qt Quick 3D riportano draw call, vertici emessi, buffer mesh e passaggi della scena; sono conservati nei report, con raccolta estesa fuori dalla finestra. `renderTime` è preparazione/registrazione CPU, non durata GPU. `lastCompletedGpuTime=0` è marcato non misurato; i timestamp non sono raccolti e Qt 6.8 non li supporta su OpenGL ES. `vmemUsedBytes=0` non prova assenza di consumo VRAM. [RenderStats](https://doc.qt.io/qt-6.8/qml-qtquick3d-renderstats.html), [timestamp Qt Quick](https://doc.qt.io/qt-6.8/qquickgraphicsconfiguration.html#setTimestamps).

Callback frameSwapped e tick delle pose restano **misure software**, non fotogrammi ottici o latenza del tastierino. Le fixture negano la rete e non qualificano fonti live concorrenti. Non sono provati uso 24/7, consumo energetico, intero acquario 3D, materiali testurizzati, rig scheletrico o effetti avanzati.''','',
'## Catture della prova','',
f'Campione 2D nativo, stessa Main e popolazione nominale:\n\n![Campione 2D]({ev}/board/measure/nominal-2d-3/capture.png)\n\nCampione 3D nativo di costo, grafica procedurale di prova:\n\n![Campione 3D]({ev}/board/measure/nominal-3d-3/capture.png)','',
'## Decisione e seguito','',
'''La media rimane vicina a 60 anche con la mesh più fitta e con 16 pesci; in nessun caso registrato compaiono intervalli oltre 50 ms. Nel nominale, tutti gli altri criteri passano: è il p95 a superare la soglia di 18,5 ms. Questo non certifica scatti visibili: callback e pose sono osservati dal banco software, con la stessa modalità di campionamento per i due renderer.

Con la mesh più fitta, i triangoli per pesce crescono di 3,88 volte e le draw call restano 54. Nello stress salgono a 144 draw call. Questi screening non isolano il collo di bottiglia: la variabilità CPU e l’assenza di tempi GPU/frequenze impediscono di attribuire il risultato ai soli poligoni, alla GPU o alle chiamate di disegno.

Il primo seguito utile sarebbe profilare i thread e verificare la regolarità nell’event loop della dashboard con carichi reali; poi confrontare un rig con meno parti/materiali o instancing esplicito. Qt consente di disegnare copie di un Model con una sola chiamata, ma non trasforma automaticamente Repeater3D in instancing: vanno gestite anche le animazioni indipendenti delle parti. È una direzione da misurare, senza un guadagno garantito. [Documentazione Qt sull’instancing](https://doc.qt.io/qt-6.8/quick3d-instancing.html).

Un’eventuale versione 3D richiede il modello artistico Calm definitivo, rig/materiali scelti e ripetizione del confronto con quel modello; ombre, antialiasing e complessità vanno trattati come budget espliciti. La release installata resta il 2D, il Compagno resta alla v0.11. La scelta di integrare il 3D è successiva a questa prova.''']
(D/report).write_text('\n'.join(lines)+'\n')
p=D/'release-masterplan.md';text=p.read_text();text=text.replace('**Revisione 3.26 · 26 ottobre 2026 · Europe/Rome**','**Revisione 3.27 · 27 ottobre 2026 · Europe/Rome**',1)
text='\n\n'.join(part for part in text.split('\n\n') if not part.startswith('**Prova 3D del 27 ottobre — solo esperimento:**'))
marker='## 12. v0.11';pos=text.index(marker);text=text[:pos]+f'**Prova 3D del 27 ottobre — solo esperimento:** [costo misurato]({report}), copie private della Main e dipendenze estratte senza installazione nel sistema. {headline} Sei pesci: CPU {delta["cpuOneCorePercentagePoints"]:+.2f} punti percentuali di un core e RSS {delta["rssMiB"]:+.2f} MiB rispetto al 2D. Produzione 2D rc.2 / Apple Calm 1.6.5 ripristinata, dati/opzioni e 682 hash invariati, GUI pronta/NRestarts=0. Modello artistico finale, skinning, effetti, fonti live e ottica non qualificati; nessuna implementazione 3D di produzione autorizzata da questa sola misura.\n\n'+text[pos:];p.write_text(text)
(E/'WORK-STATE.md').write_text(f'# Prova 3D completata · 27 ottobre 2026\n\n{headline}\n\nDelta nominale sei pesci: CPU {delta["cpuOneCorePercentagePoints"]:+.2f} punti percentuali di un core, RSS {delta["rssMiB"]:+.2f} MiB. Dieci casi misurati, MSAA non supportato nella configurazione provata: primo stadio incompleto conservato e due prove residue con ricevuta separata. Raw conservati, nessun gate nascosto.\n\nProduzione 2D rc.2 / Apple Calm 1.6.5 ripristinata e verificata, 682 hash, GUI pronta/NRestarts=0; game/preferenze/bootID invariati, nessun pacchetto installato o upgrade OS. Prototipo confinato allo stage, nessun nuovo deploy. Dettagli nel report.\n')
print(json.dumps({'report':str(D/report),'headline':headline,'cost':delta}))
