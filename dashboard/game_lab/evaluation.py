"""Frozen, policy-bound evaluation; development and final banks never overlap."""
from pathlib import Path
import hashlib,json,time,statistics
from game_lab.environment import make_episode
from game_learning import Policy
from game_lab.teacher import Teacher
from game_residual import key


def bank(split='development',*,duration=180.,cases=3,feature_version=None):
    if split not in ('development','final'):raise ValueError('Evaluation split')
    base=982000 if split=='development' else 1982000
    rows=[]
    for n,family in enumerate(('solo','attack','complete','corner','defend','traffic','recover')):
        for bots in ((1,2,3) if family=='traffic' else (1,)):
            for i in range(cases):rows.append(dict(family=family,bots=bots,seed=base+n*1000+bots*100+i,duration=duration))
    from game_catalog import configuration
    from game_direct import ACTION,FEATURES
    root=Path(__file__).resolve().parents[1]
    sources=('game_simulation.py','game_academy.py','game_direct.py','game_temporal.py','game_control.py',
        'game_driving_school.py','game_rewards.py','game_catalog.py','game_racecraft.py','game_geometry.py','game_contacts.py',
        'game_overtaking.py','game_protocol.py','game_direct_bootstrap.py','game_racing_presets.py',
        'game_lab/environment.py','game_lab/evaluation.py','game_lab/teacher.py')
    hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources}
    result=dict(version='sustained-overtaking-bank-3',split=split,cases=rows,configuration=configuration('oval-1','race-68-v3'),
        action=ACTION,features=feature_version or FEATURES,sourceHashes=hashes)
    result['hash']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result


def evaluate(policy=None,*,split='development',duration=180.,cases=3,output=None):
    plan=bank(split,duration=duration,cases=cases,feature_version=policy['features'] if policy else None);rows=[];start=time.monotonic()
    report=dict(bank=plan,policyHash=key(policy) if policy else 'physical-teacher-utilization-055',
        controller='network' if policy else 'named-offline-teacher',rows=rows,qualified=False)
    for case in plan['cases']:
        e=make_episode(**case);driver=Policy(policy) if policy else None;teacher=Teacher() if policy is None else None
        first_pass=None;first_failure=None;command=None;global_contacts=0
        while not e.reason:
            if driver is not None:command=driver.act(None,world=e.world,index=0)
            elif round(e.world.time*60)%6==0:
                from game_direct import controls
                command=teacher.label(e.world);controls(e.world,command,[0])
            before_time=e.world.time
            previous=e.passes;e.step(command,return_observation=False)
            global_contacts+=sum(v.get('type')=='contact' and v['time']>before_time for v in e.world.events)
            if first_pass is None and e.passes>previous:first_pass=e.age
            if first_failure is None and (e.contact_count or int(e.world.track_limits[0])>(1 if case['family']=='recover' else 0)):
                first_failure=dict(time=e.age,steer=float(command[0]),pedal=float(command[1]),speed=float(e.world.state[0,3]))
        result=e.result();flying=[lap['time'] for lap in e.world.lap_times[0][1:] if lap['clean']]
        clean=not result['contacts'] and result['trackLimits']<=(1 if case['family']=='recover' else 0) and not result.get('racecraft',{}).get('violations',0)
        complete=e.age>=duration-.1 and not e.world.retired[0]
        rows.append(dict(**case,result=result,clean=bool(clean),windowComplete=bool(complete),
            cleanPass=bool(clean and complete and e.passes>0),firstPass=first_pass,firstFailure=first_failure,
            globalContacts=global_contacts,rivalContacts=max(0,global_contacts-result['contacts']),
            globalTrackLimits=int(e.world.track_limits.sum()),retirements=e.world.retired.tolist(),
            cleanLaps=int(e.world.clean_laps[0]),flyingMedian=statistics.median(flying) if flying else None))
        report['wallSeconds']=time.monotonic()-start
        if output:Path(output).write_text(json.dumps(report,indent=2)+'\n')
        print('evaluate',report['controller'],case['family'],case['bots'],case['seed'],e.passes,result['contacts'],result['trackLimits'],flush=True)
    report['summary']=summarize(rows)
    if output:Path(output).write_text(json.dumps(report,indent=2)+'\n')
    return report


def summarize(rows):
    groups={}
    for family in ('solo','attack','complete','corner','defend','traffic','recover'):
        cases=[r for r in rows if r['family']==family]
        passing=family in ('attack','complete','corner','traffic')
        valid=[r for r in cases if r['cleanPass']] if passing else [r for r in cases if r['clean'] and r['windowComplete']]
        groups[family]=dict(total=len(cases),valid=len(valid),rate=len(valid)/len(cases) if cases else 0.,
            contacts=sum(r['result']['contacts'] for r in cases),limits=sum(r['result']['trackLimits'] for r in cases),
            medianPass=statistics.median([r['firstPass'] for r in valid if r['firstPass'] is not None]) if passing and valid else None)
    return groups
