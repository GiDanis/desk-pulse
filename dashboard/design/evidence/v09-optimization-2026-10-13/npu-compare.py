"""CPU and NPU complete inference on the same frozen 68-channel policy."""
import hashlib,json,os,statistics,subprocess,sys,time
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1';sys.path.insert(0,'/var/lib/smartpc-dashboard/smartpc-v09-rc10-project/dashboard')
import numpy as np
from game_learning import Policy
P=Path('/var/lib/smartpc-dashboard/v09-optimization-proof/npu');reports=[]
for batch in (1,4,32):
 root=P/str(batch);policy=Policy(json.loads((root/'policy.json').read_text()));vectors=np.random.default_rng(733).uniform(-1,1,(512*batch,68)).astype('<f4')
 vectors.tofile(root/'observations-full.f32');subprocess.run([str(P/'benchmark'),str(root/'network_binary.nb'),str(root/'observations-full.f32'),str(root/'actions-full.f32'),'68',str(batch)],stdout=(root/'times-full.txt').open('w'),stderr=(root/'stderr-full.txt').open('w'),check=True)
 result=np.fromfile(root/'actions-full.f32',dtype='<f4').reshape(-1,2);reference=policy.act(vectors)
 error=float(np.max(np.abs(result-reference)));assert np.isfinite(result).all() and error<.002
 npu=[float(x.split()[-1]) for x in (root/'times-full.txt').read_text().splitlines() if x.startswith('sample ')]
 assert len(npu)==512
 cpu=[]
 for _ in range(10):policy.act(vectors[:batch])
 for i in range(512):
  start=time.perf_counter();policy.act(vectors[i*batch:(i+1)*batch]);cpu.append(time.perf_counter()-start)
 row={'batch':batch,'samples':512,'vectors':len(vectors),'inputs':68,'hidden':policy.hidden,'maxActionError':error,
      'cpuMedianUs':statistics.median(cpu)*1e6,'cpuP95Us':sorted(cpu)[int(.95*(len(cpu)-1))]*1e6,
      'npuMedianUs':statistics.median(npu)*1e6,'npuP95Us':sorted(npu)[int(.95*(len(npu)-1))]*1e6,
      'cold':(root/'stderr-full.txt').read_text(),'compiledHash':hashlib.sha256((root/'network_binary.nb').read_bytes()).hexdigest(),
      'policyHash':hashlib.sha256((root/'policy.json').read_bytes()).hexdigest(),'precision':'CPU float64 policy from float32 vectors; NPU FP16 I/O/internal, conversion included'}
 reports.append(row);print(row,flush=True)
(P/'runtime-choice.json').write_text(json.dumps({'status':'passed','cases':reports,'selectedRuntime':'CPU','scope':'One frozen 68-16-2 policy; 512 batches each. Not closed-loop or multiple distinct models, not training or energy qualification.'},indent=2)+'\n')
