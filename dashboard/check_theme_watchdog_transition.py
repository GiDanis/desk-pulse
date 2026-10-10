"""External watchdog protocol: fresh pulses, lost readiness and bounded transitions."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from theme_lifecycle import LifecycleManager

CHILD=r'''
import os,sys,time
from theme_lifecycle import LifecycleManager
from theme_bundle import atomic_json
from theme_lifecycle import process_token
manager=LifecycleManager(sys.argv[1]);mode=sys.argv[2];start=time.monotonic()
while time.monotonic()-start<4:
 elapsed=time.monotonic()-start
 if mode!='dead' or elapsed<.8:
  ready=elapsed<.5 or mode=='completed' and elapsed>1.6
  atomic_json(manager.health_path,{'pid':os.getpid(),'processStart':process_token(os.getpid()),'time':time.time(),'ready':ready,'transition':not ready,'generation':int(elapsed*100)})
 if mode=='completed' and elapsed>2:sys.exit(0)
 time.sleep(.04)
'''
with tempfile.TemporaryDirectory(prefix='smartpc-watchdog-transition-') as tmp:
    records=[]
    for mode in ('completed','stalled','dead'):
        root=Path(tmp)/mode
        launcher=[sys.executable,str(Path(__file__).with_name('theme_supervisor.py')),'--data-root',str(root),
                  '--startup-timeout','2','--heartbeat-timeout','.6','--transition-timeout','2','--',
                  sys.executable,'-c',CHILD,str(root),mode]
        started=time.monotonic();result=subprocess.run(launcher,capture_output=True,text=True,timeout=9,env={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parent)})
        assert result.returncode==75,(mode,result.returncode,result.stderr)
        recovered=LifecycleManager(root).read()['lastRecovery'];reason=recovered['reason']
        expected={'completed':'processo GUI terminato con codice 0','stalled':'GUI heartbeat scaduto/readiness persa','dead':'GUI heartbeat assente'}[mode]
        assert reason==expected,(mode,reason,result.stderr)
        assert recovered['selected']=={'kind':'base','id':'base'}
        records.append({'mode':mode,'elapsedSeconds':round(time.monotonic()-started,2),'reason':reason})
    print(json.dumps({'status':'passed','records':records,'scope':'real child pulses; accelerated private supervisor timeouts'}))
