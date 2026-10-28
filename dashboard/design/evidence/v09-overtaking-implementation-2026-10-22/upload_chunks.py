"""Bounded transfers over the unstable board WLAN, verify complete SHA256."""
from pathlib import Path
import subprocess,hashlib,time,os
source=Path('/tmp/smartpc-attack-delta.tar.gz');data=source.read_bytes();names=[]
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','-i','/home/giuseppe/.ssh/smartpc_ed25519','smartpc@192.168.1.179']
for i,start in enumerate(range(0,len(data),24576)):
 name='/tmp/smartpc-attack-part-'+str(i);names.append(name)
 if i<int(os.environ.get('START_PART','0')):continue
 for attempt in range(5):
  try:
   r=subprocess.run(ssh+['cat > '+name],input=data[start:start+24576],timeout=25)
   if r.returncode==0:break
  except subprocess.TimeoutExpired:pass
  print('retry',i,attempt,flush=True)
 else:raise RuntimeError('part failed '+str(i))
 print('uploaded',i,flush=True)
command='cat '+' '.join(names)+' > /tmp/smartpc-attack-delta.tar.gz && sha256sum /tmp/smartpc-attack-delta.tar.gz'
result=subprocess.check_output(ssh+[command],text=True,timeout=25);assert result.split()[0]==hashlib.sha256(data).hexdigest();print(result,flush=True)
