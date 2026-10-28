"""Inference-only algebraic migration feasibility; never save transformed weights."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from game_learning import Evolution,Policy
s=json.loads(Path(sys.argv[1]).read_text());d=next(d for d in s['tables']['drivers'] if d['name']=='Evo');profile=json.loads(d['profile']);c=s['artifacts'][d['checkpoint']]['value']
policy=Evolution(profile,c['learner'],evo_v2=True).candidate_policy();weights=np.asarray(policy['weights']).copy();hidden=policy['hidden'];a=weights[:69*hidden].reshape(69,hidden)
cue=2/9;a[-1]+=a[67]*cue;a[67]=0.
folded=Policy({**policy,'weights':weights.tolist()});original=Policy(policy)
obs=np.random.default_rng(673).uniform(-1,1,(256,68));old=obs.copy();old[:,67]=cue;new=obs.copy();new[:,67]=0.
error=float(np.max(abs(original.act(old)-folded.act(new))));assert error<1e-12
result=dict(vectors=256,maxAbsoluteActionError=error,oldCue=cue,newCue=0.,scope='Diagnostic constant-feature folding in a private dense actor copy; no weights persisted, no NEAT/optimizer migration validated')
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(result)
