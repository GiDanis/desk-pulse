from pathlib import Path
import json,statistics,hashlib
r=Path(__file__).resolve().parent
phases=('pace','overtake','corner','defend')
def summary(path):
 d=json.loads(path.read_text());out={}
 for phase in phases:
  rows=[x for x in d['rows'] if x['case']['phase']==phase];times=[x['seconds'] for x in rows if x['reason']=='success']
  out[phase]=dict(valid=sum(x['reason']=='success' for x in rows),total=len(rows),median=statistics.median(times) if times else None,
    contacts=sum(x['contacts'] for x in rows),limits=sum(x['trackLimits'] for x in rows),rules=sum(x['rules'] for x in rows))
 return out
selection={v:{str(s):summary(r/f'eval-selection-{v}-{s}.json') for s in range(21,26)} for v in ('old','new','capability')}
comparisons=[]
for seed in range(21,26):
 a=json.loads((r/f'eval-selection-new-{seed}.json').read_text())['rows'];b=json.loads((r/f'eval-selection-capability-{seed}.json').read_text())['rows']
 regressions=[];gains=[]
 for x,y in zip(a,b):
  assert x['case']==y['case']
  if x['reason']=='success' and y['reason']!='success' or any(y[k]>x[k] for k in ('contacts','trackLimits','rules')):regressions.append(dict(phase=x['case']['phase'],seed=x['case']['seed'],old=x['reason'],new=y['reason']))
  if x['case']['phase']!='pace' and x['reason']!='success' and y['reason']=='success':gains.append(dict(phase=x['case']['phase'],seed=x['case']['seed']))
 old=selection['new'][str(seed)]['pace']['median'];new=selection['capability'][str(seed)]['pace']['median']
 pace=bool(old and new and new<=old*1.005)
 comparisons.append(dict(seed=seed,retainsSoloPace=pace,paceRatio=new/old if old and new else None,regressions=regressions,gains=gains,passes=pace and not regressions))
promote=all(c['passes'] for c in comparisons) and any(c['gains'] for c in comparisons)
selection_result=dict(bankHash=hashlib.sha256((r/'bank-selection.json').read_bytes()).hexdigest(),perSeed=selection,base=summary(r/'eval-selection-base-0.json'),
 capabilityComparison=comparisons,promoteCapability=promote,decision='Capability eligible for independent final test' if promote else 'Keep fixed curriculum; capability does not retain all paired abilities and pace',finalBankUsedForSelection=False)
(r/'selection-summary.json').write_text(json.dumps(selection_result,indent=2)+'\n')
print(json.dumps(dict(promote=promote,paired=[dict(seed=c['seed'],paceRatio=c['paceRatio'],regressions=len(c['regressions']),gains=len(c['gains'])) for c in comparisons])))
final={v:{str(s):summary(r/f'eval-final-v2-{v}-{s}.json') for s in range(21,26)} for v in ('old','new')}
aggregate={}
for v in final:
 aggregate[v]={}
 for phase in phases:
  records=[final[v][str(s)][phase] for s in range(21,26)];valid=[x['valid'] for x in records];times=[x['median'] for x in records if x['median'] is not None]
  aggregate[v][phase]=dict(meanValid=statistics.mean(valid),medianValid=statistics.median(valid),worstValid=min(valid),totalPerSeed=60,
    meanSeedMedianSeconds=statistics.mean(times) if times else None,contacts=sum(x['contacts'] for x in records),limits=sum(x['limits'] for x in records),rules=sum(x['rules'] for x in records))
final_result=dict(bankVersion='overtaking-structured-2',audit='bank-audit.json; v1 excluded from final family claims',bankHash=hashlib.sha256((r/'bank-final-v2.json').read_bytes()).hexdigest(),perSeed=final,aggregate=aggregate,base=summary(r/'eval-final-v2-base-0.json'),
 noTuningOnFinal=True,note='Same new environment for all frozen champions; longer drills are not neural learning gain. No study model imported.')
(r/'heldout-summary.json').write_text(json.dumps(final_result,indent=2)+'\n')
print(json.dumps(dict(final=aggregate,base=final_result['base'])))
methods={}
for m in ('residual_ppo','residual_sac','residual_td3'):
 methods[m]=[]
 for seed in range(21,26):
  d=json.loads((r/f'method-{m}-{seed}.json').read_text());accepted=[x for x in d['evaluations'] if x['accepted']]
  latest=accepted[-1] if accepted else None
  methods[m].append(dict(seed=seed,steps=d['physicalSteps'],decisions=d['decisions'],seconds=d['seconds'],stats=d['stats'],accepted=len(accepted),
    median=latest['candidate']['median'] if latest else None,baseMedian=d['evaluations'][0]['champion']['median'] if d['evaluations'] else None))
(r/'methods-summary.json').write_text(json.dumps(methods,indent=2)+'\n')
