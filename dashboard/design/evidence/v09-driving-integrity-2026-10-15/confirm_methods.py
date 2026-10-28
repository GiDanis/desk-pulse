"""Five-seed confirmation plus one-variable PPO screening; private only."""
import concurrent.futures
from screen_methods import run
if __name__=='__main__':
 jobs=[(m,s,v,250000) for m,v in [('ppo','baseline'),('ppo_smooth','fresh'),('ppo_smooth','warm'),('imitation','baseline')] for s in (4,5)]
 jobs += [('evolution',s,'baseline',250000) for s in (1,2,3,4,5)]
 jobs += [('ppo',s,v,250000) for v in ('lr-low','gae-short','batch-large') for s in (1,2,3)]
 with concurrent.futures.ProcessPoolExecutor(3) as e:list(e.map(run,jobs))
