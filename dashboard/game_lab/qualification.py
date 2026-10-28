"""Fail-closed scientific promotion. A completed run is not a passed gate."""
from copy import deepcopy
import math,statistics
from game_residual import key

VERSION='independent-preparation-promotion-2'


def qualify(runs,*,solo_tolerance=.01,pass_margin=.1):
    failures=[]
    if len(runs)!=5:failures.append('Five completed independent preparations are required')
    seeds=[r.get('preparationSeed') for r in runs]
    if None in seeds or len(set(seeds))!=5:failures.append('Preparation seeds are missing or repeated')
    dataset_hashes=[r.get('datasetHash') for r in runs]
    if None in dataset_hashes or len(set(dataset_hashes))!=5:failures.append('Five distinct preparation datasets are required')
    gains=0;rows=[]
    for run in runs:
        seed=run.get('preparationSeed');base=run.get('baseEvaluation',{});candidate=run.get('candidateEvaluation',{})
        issues=[]
        if base.get('bank',{}).get('split')!='final' or candidate.get('bank',{}).get('split')!='final':issues.append('Final bank required')
        if not base.get('bank',{}).get('hash') or base.get('bank',{}).get('hash')!=candidate.get('bank',{}).get('hash'):issues.append('Unpaired bank')
        if candidate.get('policyHash')!=run.get('candidateHash'):issues.append('Candidate identity mismatch')
        if base.get('policyHash')!=run.get('baseHash'):issues.append('Imitation base identity mismatch')
        c=candidate.get('rows',[]);b=base.get('rows',[])
        if len(c)!=len(b) or not c:issues.append('Incomplete paired evaluation')
        identity=lambda r:(r.get('seed'),r.get('family'),r.get('bots'),r.get('duration'))
        for report in (base,candidate):
            if not report.get('bank',{}).get('cases') or list(map(identity,report.get('rows',[])))!=list(map(identity,report.get('bank',{}).get('cases',[]))):
                issues.append('Incomplete frozen bank')
        minimum_duration=min([r.get('duration',0) for r in c],default=0)
        if minimum_duration<180:issues.append('Sustained three-minute windows required')
        for family,minimum in (('attack',.9),('complete',.9),('corner',.75),('traffic',.75)):
            cases=[r for r in c if r.get('family')==family]
            if not cases or sum(bool(r.get('cleanPass')) for r in cases)/len(cases)<minimum:issues.append(family+' pass gate')
        for bots in (1,2,3):
            cases=[r for r in c if r.get('family')=='traffic' and r.get('bots')==bots]
            if not cases or not any(r.get('cleanPass') for r in cases):issues.append('Traffic family '+str(bots)+' empty/zero')
        for current,previous in zip(c,b):
            if identity(current)!=identity(previous):issues.append('Case order mismatch');continue
            x=current.get('result',{});y=previous.get('result',{})
            if x.get('contacts',float('inf'))>y.get('contacts',-1) or x.get('trackLimits',float('inf'))>y.get('trackLimits',-1):issues.append('Safety regression')
            if previous.get('cleanPass') and not current.get('cleanPass'):issues.append('Lost clean pass')
        solos=[r for r in c if r.get('family')=='solo'];old_solos=[r for r in b if r.get('family')=='solo']
        if not solos or any(not r.get('clean') or not r.get('windowComplete') or r.get('cleanLaps',0)<3 or r.get('flyingMedian') is None for r in solos):issues.append('Solo competence')
        for family in ('defend','recover'):
            cases=[r for r in c if r.get('family')==family]
            if not cases or any(not r.get('clean') or not r.get('windowComplete') for r in cases):issues.append(family+' competence')
        new_times=[r['flyingMedian'] for r in solos if r.get('flyingMedian') is not None]
        old_times=[r['flyingMedian'] for r in old_solos if r.get('flyingMedian') is not None]
        if not old_times or not new_times or statistics.median(new_times)>statistics.median(old_times)*(1+solo_tolerance):issues.append('Solo retention')
        reference=run.get('referenceSoloMedian')
        if not isinstance(reference,(int,float)) or not math.isfinite(reference) or reference<=0 or not new_times or statistics.median(new_times)>reference*(1+solo_tolerance):issues.append('Common solo reference')
        # Completion drills start already alongside: no new attack latency
        # exists there. Measure each offered approach, including unanswered
        # opportunities in the denominator, rather than mixing lap finish and
        # first-pass time with the decision to attack.
        attacks=[v for r in c if r.get('family')=='attack'
            for v in r.get('result',{}).get('attack',{}).get('opportunityEvents',[]) if v.get('kind')=='approach']
        timely=sum(v.get('latency') is not None and 0<=v['latency']<=3. for v in attacks)
        if not attacks or timely/len(attacks)<.8:issues.append('Attack latency')
        waiting=lambda rows:sum(r.get('result',{}).get('attack',{}).get('queueSeconds',0)+r.get('result',{}).get('attack',{}).get('idleAlongsideSeconds',0) for r in rows if r.get('family')=='traffic')
        old_wait=waiting(b);new_wait=waiting(c)
        if old_wait>1 and new_wait>old_wait*.5:issues.append('Waiting reduction')
        passing=lambda rows:[r['firstPass'] for r in rows if r.get('family') in ('attack','complete','corner','traffic') and r.get('cleanPass') and r.get('firstPass') is not None]
        old_pass=passing(b);new_pass=passing(c)
        improved=bool(old_pass and new_pass and statistics.median(new_pass)<statistics.median(old_pass)-pass_margin and not issues)
        gains+=int(improved)
        race=run.get('races',[])
        if {r.get('cars') for r in race}!={2,5} or any(not r.get('complete') or r.get('laps')!=3 or not r.get('allCarsVisible') for r in race):issues.append('Two/five-car race gate')
        issues=sorted(set(issues));rows.append(dict(seed=seed,passed=not issues,issues=issues,rlImproved=improved,
            candidateHash=run.get('candidateHash'),baseHash=run.get('baseHash'),datasetHash=run.get('datasetHash'),bankHash=candidate.get('bank',{}).get('hash')))
        failures.extend('Seed '+str(seed)+': '+s for s in issues)
    if gains<4:failures.append('RL improvement beyond own imitation base required in at least 4/5 seeds')
    return dict(version=VERSION,qualified=not failures,failures=failures,runs=rows,improvedSeeds=gains,
        gate=dict(soloTolerance=solo_tolerance,passMarginSeconds=pass_margin,preparations=5))


def package(policy,qualification,*,context,selected_seed):
    """Build a proposal only. Installation still needs ARM/runtime evidence."""
    if qualification.get('version')!=VERSION or not qualification.get('qualified'):
        raise ValueError('Scientific qualification failed; existing pilots must be preserved')
    if not any(r.get('seed')==selected_seed and r.get('passed') and r.get('candidateHash')==key(policy) for r in qualification['runs']):
        raise ValueError('Selected preparation not qualified')
    return dict(version=VERSION,status='scientifically-qualified-not-installed',policy=deepcopy(policy),
        policyHash=key(policy),selectedSeed=selected_seed,context=deepcopy(context),qualification=deepcopy(qualification))
