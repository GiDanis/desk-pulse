"""Exact solo/shared dynamics parity; native throughput with normal kiosk alive."""
import importlib.util,json,statistics,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,sys.argv[1]);old_path=Path(sys.argv[2]);out=Path(sys.argv[3])
from game_simulation import World
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset
import game_academy
spec=importlib.util.spec_from_file_location('pacing_original_world',old_path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
rng=np.random.default_rng(608);rows=[]
for track in ('oval-1','technical-1','varano-short-1','mallory-oval-1'):
 for count,shared in ((1,False),(4,True)):
  for physics in ('f1-2','f2-1'):
   a=old.World(count,71,shared=shared,track_id=track,physics=physics);b=World(count,71,shared=shared,track_id=track,physics=physics)
   for step in range(180):
    # On-road, boundary, recovery and contact states.
    if step in (0,60,120):
     for i in range(count):
      x,y,yaw=a.track.pose(a.track.length*(step/180),0 if step==0 else a.track.width/2+.2)
      for w in (a,b):w.state[i,:4]=[x,y,yaw,15+i];w.active[i]=True
    command=rng.uniform(-1,1,(count,2));ra=a.step(command);rb=b.step(command)
    for x,y in zip(ra,rb):np.testing.assert_array_equal(x,y)
    assert a.snapshot()==b.snapshot(),(track,count,physics,step)
   rows.append(dict(track=track,count=count,shared=shared,physics=physics,steps=180,exact=True))
perf=[]
for track,phase in (('oval-1','control'),('varano-short-1','control'),('varano-short-1','overtake')):
 values={}
 for label,klass in (('original',old.World),('optimized',World)):
  game_academy.World=klass
  rates=[]
  for _ in range(3):
   t=AcademyTrainer(academy_profile(preset(3,'evolution')),track);t.state['phase']=phase;t.reset_episodes()
   started=time.perf_counter();before=t.steps
   for i in range(256):t.tick()
   elapsed=time.perf_counter()-started;rates.append((t.steps-before)/elapsed)
  values[label]=dict(transitionsPerSecondMedian=statistics.median(rates),samples=rates)
 perf.append(dict(track=track,phase=phase,**values))
result=dict(status='passed',scope='Exact snapshots/rewards/observations and 3x256 trainer calls per native throughput case; not convergence or displayed FPS',parity=rows,throughput=perf)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
