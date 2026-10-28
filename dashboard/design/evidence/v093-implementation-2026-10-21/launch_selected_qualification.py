from pathlib import Path
import json,subprocess,time
OUT=Path(__file__).resolve().parent
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-i','/home/giuseppe/.ssh/smartpc_ed25519','smartpc@192.168.1.179']
REMOTE=r"""
from pathlib import Path
import json,subprocess
receipt=Path('/var/lib/smartpc-dashboard/v093-proof/native-wire-final/receipt.json')
running=False
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:args=(p/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 if len(args)>1 and args[1]==b'/var/lib/smartpc-dashboard/v093-proof/native_wire_qualification.py':running=True
ready=receipt.exists() and json.loads(receipt.read_text()).get('status')=='passed' and not running
print(json.dumps(dict(ready=ready)))
"""
deadline=time.monotonic()+600
while True:
 r=subprocess.run(SSH+['sudo -n python3 -'],input=REMOTE,capture_output=True,text=True,check=True)
 if json.loads(r.stdout)['ready']:break
 assert time.monotonic()<deadline,'Previous qualification did not complete'
 time.sleep(15)
subprocess.run(SSH+["sudo -n cp -a /var/lib/smartpc-dashboard/v093-stage /var/lib/smartpc-dashboard/v093-before-selected"],check=True)
for local,remote in [('/tmp/smartpc-v093-selected-diagnostic/','/var/lib/smartpc-dashboard/v093-stage/dashboard/'),('/tmp/smartpc-v093-selected-runtime/','/var/lib/smartpc-dashboard/v093-runtime/dashboard/')]:
 subprocess.run(['rsync','-a','--delete','--rsync-path=sudo -n rsync','-e','ssh -i /home/giuseppe/.ssh/smartpc_ed25519',local,'smartpc@192.168.1.179:'+remote],check=True)
files=['native_selected_qualification.py','first_response_wire.py','mixed_native_wire.py','final_board_gates.py','install_candidate.py']
subprocess.run(['scp','-q','-i','/home/giuseppe/.ssh/smartpc_ed25519',*[str(OUT/n) for n in files],'smartpc@192.168.1.179:/tmp/'],check=True)
subprocess.run(SSH+['sudo -n install -m 644 '+' '.join('/tmp/'+n for n in files)+' /var/lib/smartpc-dashboard/v093-proof/'],check=True)
subprocess.run(SSH+['sudo -n python3 /var/lib/smartpc-dashboard/v093-proof/native_selected_qualification.py'],check=True)
