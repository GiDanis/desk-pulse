"""Frozen policies on the previously sealed final bank; no learning."""
import argparse,json,time,subprocess,os,sys,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
R=Path(__file__).resolve().parent
if len(sys.argv)>1 and sys.argv[1]=='--case':
    _,_,method,revision,seed,path=sys.argv
    sys.path.insert(0,str(R.parents[2]))
    from game_learning import Policy
    from game_academy import Episode
    from game_residual_trainer import reward_profile
    from game_rewards import specification
    bank=json.loads((R/'final-bank.json').read_text());data=json.loads(Path(path).read_text())
    policy=Policy(data['champion']);cases=[('pace',s) for s in bank['soloSeeds']]
    if method=='residual_tactic':cases += [(p,s) for p,seeds in bank['traffic'].items() for s in seeds]
    rows=[];started=time.monotonic()
    for phase,scenario_seed in cases:
        spec={**specification(reward_profile(data['champion'])),'evaluationRules':bank['rules']}
        e=Episode(bank['track'],phase,scenario_seed,protocol='driving-memory-1',single_lap=True,reward_spec=spec)
        for _ in range(24000):
            e.step(policy.act(None,world=e.world,index=0),return_observation=False)
            if e.reason:break
        rows.append(dict(phase=phase,seed=scenario_seed,reason=e.reason,success=e.reason=='success',seconds=e.age,
            contacts=e.contact_count,trackLimits=int(e.world.track_limits[0]),maxSpeedKmh=float(e.world.max_speed[0])*3.6,
            violations=getattr(e,'racecraft',{}).get('violations',0)))
    (R/f'final-{revision}-{method}-{seed}.json').write_text(json.dumps(dict(method=method,revision=revision,seed=int(seed),rows=rows,seconds=time.monotonic()-started,
        inputSha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),bankSha256=hashlib.sha256((R/'final-bank.json').read_bytes()).hexdigest()),indent=2)+'\n')
else:
    p=argparse.ArgumentParser();p.add_argument('--ppo',action='store_true');a=p.parse_args()
    methods=['residual_ppo'] if a.ppo else ['residual_sac','residual_td3','residual_tactic']
    jobs=[]
    for method in methods:
        for revision in ('old','new'):
            for seed in range(31,36):
                source=R/(f'dev-prior-{seed}.json' if a.ppo and revision=='new' else f'{revision}-{method}-{seed}.json')
                jobs.append((method,revision,seed,source))
    def run(job):
        m,r,s,path=job
        with (R/f'final-{r}-{m}-{s}.log').open('w') as out:
            subprocess.run(['nice','-n','10',sys.executable,str(__file__),'--case',m,r,str(s),str(path)],env=dict(os.environ,OPENBLAS_NUM_THREADS='1'),stdout=out,stderr=subprocess.STDOUT,check=True)
        print('Evaluated '+r+' '+m+' '+str(s),flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(run,jobs))
