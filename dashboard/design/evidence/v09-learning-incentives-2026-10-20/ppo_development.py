"""Small explicitly private ablations; never choose defaults from one seed."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import subprocess,sys,os,json,time,math
R=Path(__file__).resolve().parent
variants={'short':dict(std=.08,tau=1.6,entropy=0.,potential=True),
          'narrow':dict(std=.04,tau=1.6,entropy=.0001,potential=True),
          'old-noise':dict(std=.01,tau=1.6,entropy=0.,potential=True),
          'no-potential':dict(std=.04,tau=1.6,entropy=.0001,potential=False),
          'wide':dict(std=.06,pace=.45,tau=4.,entropy=.0002,potential=True,rate=.0003,criticRate=.001),
          'wide-short':dict(std=.06,pace=.45,tau=1.6,entropy=.0002,potential=True,rate=.0003,criticRate=.001),
          'prior':dict(std=.04,pace=.15,tau=1.6,entropy=.0001,potential=True,prior=True)}
if len(sys.argv)>1 and sys.argv[1] not in ('--wide','--prior'):
    variant,seed=sys.argv[1],int(sys.argv[2]);v=variants[variant]
    sys.path.insert(0,'/tmp/smartpc-incentives-ppo-prior/dashboard' if v.get('prior') else '/tmp/smartpc-incentives-ppo-b/dashboard' if 'rate' in v else '/tmp/smartpc-incentives-candidate')
    import game_residual
    original=game_residual.recipe
    def recipe(p):
        r=original(p);r.update(exploration=[v['std'],v.get('pace',.15)],gaeLambda=math.exp(-.1/v['tau']),ppoEntropy=v['entropy'])
        if 'rate' in v:r.update(minStd=[.03,.15],maxStd=[.25,.8],ppoLearningRate=v['rate'],criticRate=v['criticRate'])
        if v.get('prior'):r['potentialPrior']=True
        return r
    game_residual.recipe=recipe
    import game_residual_trainer
    if 'rate' in v:
        original_init=game_residual_trainer.ResidualPPO.__init__
        def init(self,*a,**kw):
            original_init(self,*a,**kw);self.profile['learningRate']=v['rate'];self.tuning['criticRate']=v['criticRate']
        game_residual_trainer.ResidualPPO.__init__=init
    if not v['potential']:game_residual_trainer.learning_potential=lambda e:0.
    t=game_residual_trainer.ResidualTrainer(game_residual.profile(seed,'residual_ppo'),'oval-1');started=time.monotonic()
    budget=int(sys.argv[3]) if len(sys.argv)>3 else 24576
    while t.steps<budget or t.check or t.iterator:t.tick()
    data=dict(variant=variant,parameters=v,seed=seed,steps=t.steps,decisions=t.decisions,recipe=t.spec,stats=t.state['stats'],
        evaluations=t.state['evaluations'],champion=t.state['champion']['policy'],candidate=t.learner.policy(),seconds=time.monotonic()-started)
    (R/f'dev-{variant}-{seed}.json').write_text(json.dumps(data,indent=2)+'\n')
else:
    def run(j):
        v,s=j
        with (R/f'dev-{v}-{s}.log').open('w') as out:
            subprocess.run(['nice','-n','12',sys.executable,str(__file__),v,str(s),'49152' if '--prior' in sys.argv else '24576'],env=dict(os.environ,OPENBLAS_NUM_THREADS='1'),stdout=out,stderr=subprocess.STDOUT,check=True)
        print('Completed '+v+' '+str(s),flush=True)
    selected=('prior',) if '--prior' in sys.argv else ('wide','wide-short') if len(sys.argv)>1 else ('short','narrow','old-noise','no-potential')
    seeds=range(31,36) if '--prior' in sys.argv else (41,42)
    with ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(run,[(v,s) for s in seeds for v in selected]))
