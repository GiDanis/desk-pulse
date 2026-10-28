"""Development-only prerequisite; never substitutes for the final RL gate."""
from game_lab.evaluation import summarize
import math,statistics


def base_readiness(runs):
    failures=[];rows=[]
    if len(runs)!=5 or len({r['preparationSeed'] for r in runs})!=5:
        failures.append('Five independent complete preparations required')
    if len({r.get('datasetHash') for r in runs})!=5:failures.append('Distinct preparation datasets required')
    banks={r['evaluation'].get('bank',{}).get('hash') for r in runs}
    if len(banks)!=1 or None in banks:failures.append('A common frozen development bank is required')
    for r in runs:
        d=r['evaluation'];issues=[];cases=d.get('rows',[]);plan=d.get('bank',{})
        if plan.get('split')!='development':issues.append('Development evidence required')
        identity=lambda x:(x.get('family'),x.get('bots'),x.get('seed'),x.get('duration'))
        if not cases or list(map(identity,cases))!=list(map(identity,plan.get('cases',[]))):issues.append('Incomplete bank')
        summary=summarize(cases)
        for family,minimum in [('solo',1.),('attack',.9),('complete',.9),('corner',.75),('traffic',.75),('defend',1.),('recover',1.)]:
            if summary[family]['rate']<minimum:issues.append(family+' competence')
        for n in (1,2,3):
            selected=[c for c in cases if c.get('family')=='traffic' and c.get('bots')==n]
            if not selected or not any(c.get('cleanPass') for c in selected):issues.append('No sustained clean pass with '+str(n)+' bots')
        solos=[c for c in cases if c.get('family')=='solo']
        if not solos or any(c.get('cleanLaps',0)<3 for c in solos):issues.append('Three clean solo laps')
        reference=r.get('referenceSoloMedian');times=[c.get('flyingMedian') for c in solos]
        if (not isinstance(reference,(int,float)) or not math.isfinite(reference) or reference<=0
            or not times or any(t is None for t in times) or statistics.median(times)>reference*1.01):issues.append('Common solo reference')
        rows.append(dict(seed=r['preparationSeed'],policyHash=d.get('policyHash'),datasetHash=r.get('datasetHash'),
            ready=not issues,issues=issues,summary=summary))
        failures.extend('Seed '+str(r['preparationSeed'])+': '+s for s in issues)
    return dict(version='development-base-readiness-2',readyForFinal=not failures,qualified=False,
        finalBankUsed=False,rows=rows,failures=failures)
