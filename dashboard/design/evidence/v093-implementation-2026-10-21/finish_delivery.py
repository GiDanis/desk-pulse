"""Wait for exact native proof, then ARM gates, preserving install and three boots."""
from pathlib import Path
import json
import subprocess
import time

OUT=Path(__file__).resolve().parent
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-i','/home/giuseppe/.ssh/smartpc_ed25519','smartpc@192.168.1.179']
REMOTE=r'''
from pathlib import Path
import json
receipt=Path('/var/lib/smartpc-dashboard/v093-proof/native-wire-final/receipt.json')
running=False
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:args=(p/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 if len(args)>1 and args[1]==b'/var/lib/smartpc-dashboard/v093-proof/native_wire_qualification.py':running=True
passed=receipt.exists() and json.loads(receipt.read_text()).get('status')=='passed'
print(json.dumps(dict(ready=passed and not running,failed=not passed and not running)))
'''
deadline=time.monotonic()+2000
while True:
 result=subprocess.run(SSH+['sudo -n python3 -'],input=REMOTE,capture_output=True,text=True,check=True)
 status=json.loads(result.stdout)
 if status['ready']:break
 assert not status['failed'],'Native qualification ended without a passing receipt'
 assert time.monotonic()<deadline,'Native qualification timed out'
 time.sleep(15)
print('Exact native artifact qualified',flush=True)
assert json.loads((OUT/'final-pc-gates.json').read_text())['status']=='passed'
files=['final-pc-gates.json','final_board_gates.py','install_candidate.py','observe_candidate.py']
subprocess.run(['scp','-q','-i','/home/giuseppe/.ssh/smartpc_ed25519',*[str(OUT/n) for n in files],'smartpc@192.168.1.179:/tmp/'],check=True)
subprocess.run(SSH+['sudo -n install -m 644 '+' '.join('/tmp/'+n for n in files)+' /var/lib/smartpc-dashboard/v093-proof/'],check=True)
with (OUT/'arm-final.txt').open('w') as log:
 subprocess.run(SSH+['sudo -n python3 /var/lib/smartpc-dashboard/v093-proof/final_board_gates.py'],stdout=log,stderr=subprocess.STDOUT,check=True)
print('Final ARM gates passed',flush=True)
with (OUT/'domains-arm-final.json').open('w') as log,(OUT/'domains-arm-final.stderr').open('w') as error:
 subprocess.run(SSH+['sudo -n runuser -u smartpc -- env PYTHONDONTWRITEBYTECODE=1 /var/lib/smartpc-dashboard/game-runtime/bin/python /var/lib/smartpc-dashboard/v093-proof/probe_domains.py --source /var/lib/smartpc-dashboard/v093-stage/dashboard'],stdout=log,stderr=error,check=True)
with (OUT/'installation.txt').open('w') as log:
 subprocess.run(SSH+['sudo -n python3 /var/lib/smartpc-dashboard/v093-proof/install_candidate.py'],stdout=log,stderr=subprocess.STDOUT,check=True)
print('Candidate installed; actual runtime rollback/reinstall rehearsed',flush=True)
for directory in ('native-selected-final','native-wire-final','arm-final'):
 subprocess.run(['rsync','-rtz','--rsync-path=sudo -n rsync','-e','ssh -i /home/giuseppe/.ssh/smartpc_ed25519','smartpc@192.168.1.179:/var/lib/smartpc-dashboard/v093-proof/'+directory+'/',str(OUT/directory)+'/'],check=True)
for name in ('installation-receipt.json','before-install.json','installed-first.json','installed-final.json','rollback-rehearsal.json'):
 with (OUT/name).open('w') as log:subprocess.run(SSH+['sudo -n cat /var/lib/smartpc-dashboard/v093-proof/'+name],stdout=log,check=True)
subprocess.run(['python3',str(OUT/'qualify_reboots.py')],check=True)
print('Three candidate OS reboots qualified',flush=True)
