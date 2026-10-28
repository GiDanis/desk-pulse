"""Compare optimized trajectories with the preserved rc.3 engine."""
import importlib.util
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
import numpy as np
from game_simulation import World
spec=importlib.util.spec_from_file_location('simulation_rc3',Path(__file__).with_name('simulation-rc3.py'))
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
rng=np.random.default_rng(812)
ticks=0
for count,shared in [(1,False),(32,False),(256,False),(4,True)]:
    a=old.World(count,seed=17,shared=shared);b=World(count,seed=17,shared=shared)
    for i in range(600):
        actions=rng.uniform([-.12,.1],[.12,1],(count,2))
        ao,ar,ad=a.step(actions,pace=.7)
        bo,br,bd=b.step(actions,pace=.7)
        np.testing.assert_array_equal(ao,bo)
        np.testing.assert_array_equal(ar,br)
        np.testing.assert_array_equal(ad,bd)
        assert a.snapshot()==b.snapshot()
        ticks+=1
        if not a.active.any():a.reset(varied=not shared);b.reset(varied=not shared)
result=dict(status='passed',comparedTicks=ticks,exactSnapshots=True,
            exactObservationsRewardsTermination=True,counts=[1,32,256,4],sharedRace=True)
Path(__file__).with_name('equivalence.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
