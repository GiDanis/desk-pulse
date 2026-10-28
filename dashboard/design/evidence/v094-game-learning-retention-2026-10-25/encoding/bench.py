from pathlib import Path
import importlib.util,json,time,hashlib,sys,statistics
import numpy as np
import game_temporal
from game_temporal import TemporalPolicy as Original
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('optimized_temporal',root/'optimized_temporal.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);Optimized=module.TemporalPolicy
base=json.loads((root/'policy.json').read_text());raw=np.load(root/'raw.npz',allow_pickle=False)['x']

def encode(cls,compact,optimized=False,actor=None):
 actor=actor or cls(base);state=None;rows=[]
 for x in raw:
  if optimized:
   _,state=actor.forward(x,state,encode_only=True)
   value=actor.maneuver_inputs(x,state) if compact else actor.readout_features(x,state)
  else:
   _,state=actor.forward(x,state);value=actor.readout_features(x,state)
   if compact:value=value[-92:]
  rows.append(value.astype(np.float32))
 return np.asarray(rows),state

rows=[]
for compact in (True,False):
 before,state=encode(Original,compact);after,new_state=encode(Optimized,compact,True)
 assert np.array_equal(before,after) and state==new_state,'Encoding changed'
 actor_old=Original(base);actor_new=Optimized(base);a=b=None
 for x in raw:
  command,a=actor_old.forward(x,a);other,b=actor_new.forward(x,b)
  assert np.array_equal(command,other) and a==b,'Runtime command changed'
 blocks={'old':[],'new':[]}
 for name in ('old','new','new','old','new','old','old','new'):
  actor=(Optimized if name=='new' else Original)(base)
  start=time.perf_counter()
  for repeat in range(2):encode(Optimized if name=='new' else Original,compact,name=='new',actor)
  blocks[name].append((time.perf_counter()-start)*1000/(2*len(raw)))
 medians={name:statistics.median(values) for name,values in blocks.items()}
 rows.append(dict(features=92 if compact else 348,exactFeatures=True,exactMemory=True,exactRuntimeCommands=True,
  millisecondsPerDecision=medians,blockMillisecondsPerDecision=blocks,reduction=1-medians['new']/medians['old']))
report=dict(version='causal-encoding-abba-2',rows=rows,samples=len(raw),oldSourceHash=hashlib.sha256(Path(game_temporal.__file__).read_bytes()).hexdigest(),optimizedSourceHash=hashlib.sha256((root/'optimized_temporal.py').read_bytes()).hexdigest(),
 inputHash=hashlib.sha256((root/'raw.npz').read_bytes()).hexdigest(),scope='Encoder calculation excluding construction; not training throughput, frame rate, optical or scientific qualification',qualified=False)
(root/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
