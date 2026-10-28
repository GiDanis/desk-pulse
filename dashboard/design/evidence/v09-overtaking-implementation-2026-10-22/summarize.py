"""Complete paired cohort report; no ranking of unfinished seed groups."""
from pathlib import Path
import json,statistics,hashlib
P=Path(__file__).parent
methods=('residual_ppo','residual_sac','residual_td3','residual_tactic');seeds=range(741,746)
names=[f'{m}-{s}-{v}' for m in methods for s in seeds for v in ('candidate','baseline')]
assert all((P/'final-cohorts'/(n+'.json')).exists() and (P/'heldout'/(n+'.json')).exists() and (P/'supplement'/(n+'.json')).exists() for n in names),'Cohort incomplete'
def clean(r):return not r['contacts'] and not r['trackLimits'] and not r.get('racecraft',{}).get('violations',0)
def describe(d):
 result={}
 for family in ('complete','attack','corner','defend','traffic-1','traffic-2','traffic-3','solo'):
  rows=[x for x in d['rows'] if x['family']==family];rs=[x['result'] for x in rows]
  ok=[r for r in rs if clean(r) and (r['reason']=='success' if not family.startswith('traffic') else r['reason']=='window' and r['passes']>0)]
  times=[r['time'] for r in ok if r['time'] is not None]
  result[family]=dict(total=len(rs),cleanSuccesses=len(ok),passes=sum(r['passes'] for r in rs),contacts=sum(r['contacts'] for r in rs),limits=sum(r['trackLimits'] for r in rs),
   medianSeconds=statistics.median(times) if times else None,queueSeconds=sum(r.get('attack',{}).get('queueSeconds',0) for r in rs),
   idleAlongsideSeconds=sum(r.get('attack',{}).get('idleAlongsideSeconds',0) for r in rs),
   flyingMedian=statistics.median([x['flyingMedian'] for x in rows if x.get('flyingMedian') is not None]) if family=='solo' and all(x.get('flyingMedian') is not None for x in rows) else None)
 result['races']=dict(total=len(d['races']),allArrived=sum(r['reason']=='success' and r['finished']==5 for r in d['races']),contacts=sum(r['contacts'] for r in d['races']),limits=sum(r['limits'] for r in d['races']))
 return result
pairs=[];total_steps=total_decisions=total_updates=0
for method in methods:
 for seed in seeds:
  data={v:json.loads((P/'heldout'/f'{method}-{seed}-{v}.json').read_text()) for v in ('candidate','baseline')}
  summaries={v:describe(d) for v,d in data.items()};a=summaries['candidate'];b=summaries['baseline']
  for v in data:
   c=json.loads((P/'final-cohorts'/f'{method}-{seed}-{v}.json').read_text());assert c['physicalSteps']==196608
   total_steps+=c['physicalSteps'];total_decisions+=c['decisions'];total_updates+=c['updates']
  safety=all(a[f]['contacts']<=b[f]['contacts'] and a[f]['limits']<=b[f]['limits'] for f in a)
  solo=a['solo']['flyingMedian'] is not None and b['solo']['flyingMedian'] is not None and a['solo']['flyingMedian']<=b['solo']['flyingMedian']*1.01
  easy=all(a[f]['cleanSuccesses']/a[f]['total']>=.9 for f in ('complete','attack'))
  complex_ok=all(a[f]['cleanSuccesses']/a[f]['total']>=.75 for f in ('corner','traffic-2','traffic-3'))
  queue_a=sum(a[f]['queueSeconds']+a[f]['idleAlongsideSeconds'] for f in a if f!='races');queue_b=sum(b[f]['queueSeconds']+b[f]['idleAlongsideSeconds'] for f in b if f!='races')
  queue=queue_a<=queue_b*.5 if queue_b else queue_a==0
  extras={v:json.loads((P/'supplement'/f'{method}-{seed}-{v}.json').read_text()) for v in ('candidate','baseline')}
  offered=sum(r.get('attack',{}).get('opportunities',0) for r in extras['candidate']['rows'])
  prompt=sum(t<=3. for r in extras['candidate']['rows'] for t in r.get('attack',{}).get('attackLatencies',[]))
  latency=offered>0 and prompt/offered>=.8
  two=all(r['reason']=='success' and r['finished']==2 for r in extras['candidate']['races'])
  two_safety=all(a['egoContacts']<=b['egoContacts'] and a['egoLimits']<=b['egoLimits'] for a,b in zip(extras['candidate']['races'],extras['baseline']['races']))
  gates=dict(easy90=easy,complex75=complex_ok,safetyRetention=safety,soloWithinOnePercent=solo,waitingReducedHalf=queue,allFiveFinishBothGrids=a['races']['allArrived']==2,
   attackLatency80=latency,twoCarThreeLapRetention=two and two_safety)
  pairs.append(dict(method=method,seed=seed,summary=summaries,gates=gates,readyForDefault=all(v is True for v in gates.values()),policyHashes={v:d['policyHash'] for v,d in data.items()},supplementaryTwoCarGrids={v:d['races'] for v,d in extras.items()},promptAttacks=prompt,offeredAttacks=offered))
report=dict(status='complete',trainingRuns=len(names),trainingSeeds=list(seeds),methods=list(methods),commonPreparedBase=True,
 retainedPhysicalSteps=total_steps,decisions=total_decisions,updates=total_updates,heldoutEpisodes=58*len(names),heldoutFiveCarGrids=2*len(names),supplementaryTwoCarGrids=2*len(names),supplementaryLatencyEpisodes=10*len(names),
 perRunBudget=196608,independentTeacherPreparations=False,teacherCallsDuringLearning=0,productionChanges=False,
 fullWallClockComparisonAvailable=False,wallClockLimit='Quota recovery resumed exact checkpoints; timings of resumed processes exclude earlier CPU and re-executed work.',
 measuredScope='Exact policy selected for racing; exploratory raw candidates reported separately in final-cohorts.',
 gaps=['Latency and two-car bank added after primary bank, no model tuning from outcomes','Global five-car grid contacts and limits include frozen rivals; two-car grids also report ego','Complex collision/contact attribution unchanged'],
 promotedDefault=False,pairs=pairs)
(P/'final-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print('Complete',len(names),'runs',total_steps,'retained steps; promoted:',report['promotedDefault'])
for method in methods:
 rows=[x for x in pairs if x['method']==method]
 print(method,{g:sum(r['gates'][g] is True for r in rows) for g in rows[0]['gates']})
