"""Publish every completed seed; never select from an incomplete cohort."""
from pathlib import Path
import json,statistics,hashlib
P=Path(__file__).parent
groups=('baseline','reward-only','routed','multi-step','circuit-fixed','retained','episode-noise',
    'episode-retained','ppo-horizon','production','extended/baseline','extended/production','saved-continuations')
all_rows=[]
for group in groups:
    for path in sorted((P/group).glob('*.json')):
        d=json.loads(path.read_text())
        if 'method' not in d:continue
        def summary(cases):
            valid=[r['flyingMedian'] for r in cases if r.get('flyingMedian') is not None and r['reason']=='success' and not r['contacts'] and not r['limits']]
            return dict(valid=len(valid),total=len(cases),median=statistics.median(valid) if len(valid)==len(cases) else None)
        initial=summary(d['results']['initial']);champion=summary(d['results']['champion'])
        gain=100*(1-champion['median']/initial['median']) if champion['median'] and initial['median'] else None
        all_rows.append(dict(group=group,name=path.stem,method=d['method'],seed=d['seed'],
            physicalSteps=d['physicalSteps'],decisions=d.get('collectedDecisions',d['decisions']),updates=d['updates'],
            learningWallSeconds=d['learningSeconds'],evaluationWallSeconds=d['evaluationSeconds'],
            totalWallSeconds=d['totalWallSeconds'],processCpuSeconds=d.get('processCpuSeconds'),
            initial=initial,champion=champion,gainPercent=gain,raceReadyMedian=d['state'].get('raceChampion',{}).get('flyingMedian'),
            trainingStats=d['stats'],teacherOverridesEgo=d['teacherOverridesEgo'],teacherLabelsInRL=d['teacherLabelsInRL'],
            sourceHashes=d['sourceHashes']))
cohorts=[]
for group in groups:
    for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
        rows=[r for r in all_rows if r['group']==group and r['method']==method]
        if not rows:continue
        values=[r['champion']['median'] for r in rows if r['champion']['median']]
        cohorts.append(dict(group=group,method=method,seeds=[r['seed'] for r in rows],count=len(rows),
            median=statistics.median(values) if len(values)==len(rows) else None,
            improved=sum((r['gainPercent'] or 0)>0 for r in rows),atLeast3Percent=sum((r['gainPercent'] or 0)>=3 for r in rows),
            clean=sum(r['champion']['valid'] for r in rows),total=sum(r['champion']['total'] for r in rows)))
required=[('production',m,5) for m in ('residual_ppo','residual_sac','residual_td3','residual_tactic')]
required += [('extended/'+v,'residual_ppo',5) for v in ('baseline','production')]
complete=all(next((c['count'] for c in cohorts if c['group']==g and c['method']==m),0)==n for g,m,n in required)
source=Path(__import__('game_direct').__file__).parent
frozen=Path('/home/giuseppe/.cache/smartpc-racing-production-reference')
delta={p.name:dict(frozen=hashlib.sha256((frozen/p.name).read_bytes()).hexdigest(),final=hashlib.sha256(p.read_bytes()).hexdigest())
    for p in source.glob('game_*.py') if (frozen/p.name).exists() and p.read_bytes()!=(frozen/p.name).read_bytes()}
out=dict(status='complete' if complete else 'pending',completeCohorts=complete,rows=all_rows,cohorts=cohorts,
    sourceDeltaFromConfirmation=delta,rejectedGroups=['routed','multi-step'],notSelected=['circuit-fixed','episode-noise','ppo-horizon'],
    scope='Fixed collected physics budgets; evaluation separate; concurrent host load prevents wall-speed claims; personal models private')
(P/'scientific-receipt.json').write_text(json.dumps(out,indent=2)+'\n')
for c in cohorts:
    if c['group'] in ('production','extended/production','extended/baseline','saved-continuations'):print(c)
print('Required cohorts complete:',complete)
