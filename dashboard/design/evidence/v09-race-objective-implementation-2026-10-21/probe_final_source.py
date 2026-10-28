"""Exact fresh-run equivalence across the migration-only epoch correction."""
from pathlib import Path
import hashlib,json,sys
from game_direct_bootstrap import direct_profile
from game_direct_trainer import DirectTrainer
from game_school_lessons import SKILLS

rows=[]
for seed,method in enumerate(('residual_ppo','residual_sac','residual_td3','residual_tactic'),41):
    t=DirectTrainer(direct_profile(seed,method),'oval-1')
    for _ in range(4000):t.tick()
    def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    row=dict(method=method,learner=digest(t.learner.checkpoint()),world=digest(t.episode.world.snapshot()),steps=t.steps,decisions=t.decisions)
    t.state['schoolStats']={s:dict(total=2,valid=2) for s in SKILLS};phases=[]
    for decisions in (0,8191,8192,90000):
        t.decisions=decisions
        for number in range(16):
            t.state['stats']['episodes']=number;e=t.new_episode()
            phases.append(dict(decisions=decisions,episode=number,phase=e.phase,seed=e.seed,world=digest(e.world.snapshot()),spec=e.spec))
    row['phases']=digest(phases);rows.append(row)
Path(sys.argv[1]).write_text(json.dumps(rows,indent=2)+'\n')
