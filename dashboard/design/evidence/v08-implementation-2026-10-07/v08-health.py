"""Read-only installed runtime, private inventory, readiness and reboot verifier."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
root=Path('/opt/smartpc/dashboard');sys.path.insert(0,str(root))
from iliadbox import load_config,IliadboxClient
from network_core import NetworkStore,display
from theme_lifecycle import process_token
manifest=json.loads((root/'release-manifest.json').read_text());receipt=json.loads(Path('/var/lib/smartpc-dashboard/v08-proof/install-receipt.json').read_text())
assert manifest['version']=='0.8.0-rc.1'
assert all(hashlib.sha256((root/k).read_bytes()).hexdigest()==v for k,v in manifest['sha256'].items())
service=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState','-p','SubState','-p','NRestarts','-p','MainPID'],text=True).splitlines())
main=int(service['MainPID']);processes=[tuple(row.split()) for row in subprocess.check_output(['ps','-eo','pid=,ppid='],text=True).splitlines()];pids=[str(main)]
for parent in pids:
    pids.extend(pid for pid,ppid in processes if ppid==parent and pid not in pids)
health=[]
for pid in pids:
    for file in Path(f'/proc/{pid}/root/tmp').glob('smartpc-theme-health-*/*.json'):
        d=json.loads(file.read_text());hp=d.get('pid',0)
        if str(hp) in pids and d.get('processStart')==process_token(hp) and 0<=time.time()-d.get('time',0)<6:health.append(d)
assert health,'No fresh GUI heartbeat'
ready=next(d for d in health if d['ready']);gui=ready['pid'];rss=int(next(row.split()[1] for row in Path(f'/proc/{gui}/status').read_text().splitlines() if row.startswith('VmRSS:')))
client=IliadboxClient(load_config(Path('/var/lib/smartpc-dashboard/.config/smartpc/iliadbox/app.json')))
store=NetworkStore('/var/lib/smartpc-dashboard/.local/state/smartpc/network',client.scope);snapshot=store.load();data=display(snapshot,'active',time.time())
conf=Path('/var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf');prefs=hashlib.sha256(conf.read_bytes()).hexdigest()==receipt['preferenceSha256']
logs=subprocess.check_output(['journalctl','-u','smartpc-dashboard','--since','@'+str(int(receipt['installedAt'])),'--no-pager','-o','cat'],text=True)
patterns=('Binding loop','ReferenceError','TypeError','Unable to assign','QQmlApplicationEngine failed','failed to load component','Cannot assign','Type NetworkOverview unavailable')
report={'version':manifest['version'],'files':len(manifest['sha256']),'manifestVerified':True,'service':service,'guiReady':ready['ready'],'guiRssKiB':rss,'theme':ready['selection'],'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'bootChanged':Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=receipt['bootIdBefore'],'preferencesPreserved':prefs,'inventory':data['knownCount'],'reachable':data['reachableText'],'coverage':data['coverage'],'favourites':len(data['favourites']),'lastCheckedAt':snapshot['checkedAt'],'currentCount':data['countCurrent'],'credentialPermissions':oct(Path('/var/lib/smartpc-dashboard/.config/smartpc/iliadbox/app.json').stat().st_mode&0o777),'cachePermissions':oct(store.path.stat().st_mode&0o777),'qmlWarningMatches':[p for p in patterns if p.lower() in logs.lower()],'checkedAt':time.time(),'scope':'Installed EGLFS service, fresh GUI heartbeat, persistent live inventory and boot identity; no physical presence claim.'}
print(json.dumps(report,ensure_ascii=False))
assert service['ActiveState']=='active' and service['SubState']=='running' and service['NRestarts']=='0'
assert prefs and not report['qmlWarningMatches'] and snapshot['checkedAt']>receipt['installedAt'] and data['countCurrent']
if '--after-reboot' in sys.argv:assert report['bootChanged']
