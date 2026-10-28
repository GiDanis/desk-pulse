"""Physical readiness protocol with a declared geometric reference, no training."""
from pathlib import Path
import json
import os
import sys
import time
os.environ['OPENBLAS_NUM_THREADS']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from game_hybrid import HybridGate
from game_profiles import reference_policy

start=time.monotonic();gate=HybridGate(reference_policy('oval-1',academy=True),'oval-1')
while not gate.tick():pass
result=gate.result()
result.update(controller='traffic-pursuit-2',neuralPilot=False,trainingSteps=0,
    wallSeconds=time.monotonic()-start,
    meaning='Checks the physical gate, not the learning or competence of Clone-PPO')
Path(__file__).with_name('hybrid-gate-reference.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
assert result['passed']
