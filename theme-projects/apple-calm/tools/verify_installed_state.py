#!/usr/bin/env python3
"""Read-only installed identity, preferences, service and GUI health proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

p=argparse.ArgumentParser()
p.add_argument('--manifest',type=Path,required=True)
p.add_argument('--backup',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--before-boot-id')
a=p.parse_args()
runtime=Path('/opt/smartpc/dashboard')
data=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC')
sys.path.insert(0,str(runtime))
from PySide6.QtCore import QCoreApplication,QSettings,qVersion
from theme_bundle import BundleManager
from theme_lifecycle import process_token,BASE
app=QCoreApplication([])
expected=json.loads(a.manifest.read_text())
identity={'id':'studio.applecalm','version':expected['themeVersion'],'digest':expected['bundleDigest']}
files={name:hashlib.sha256((runtime/name).read_bytes()).hexdigest() for name in expected['files']}
assert files==expected['files'],'installed source differs'
journal=json.loads((data/'theme-activation.json').read_text())
assert journal['active']==identity and journal['pending'] is None and journal['lastRecovery'] is None
assert not (data/'theme-quarantine'/(identity['digest']+'.json')).exists()
revision=BundleManager(data,app_root=runtime).verify_revision(identity)
assert revision['preflight']['status']=='passed'
assert journal['previous']==BASE,journal['previous']
installed=BundleManager(data,app_root=runtime).list_revisions(include_quarantined=True)
assert [r['version'] for r in installed if r['id']==identity['id']]==[identity['version']], 'old Apple Calm revision retained'
settings=QSettings('/var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf',QSettings.Format.IniFormat)
config=json.loads(settings.value('appearance/config'))
assert config['themeId']==identity['id'] and config['bundleRevision']==identity
def kept(s):return {k:s.value(k) for k in s.allKeys() if not k.startswith('appearance/') and k not in ('animationsEnabled','nightMode')}
original_bytes=subprocess.check_output(['sudo','-n','tar','-xOf',str(a.backup/'before.tar.gz'),'var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf'])
with tempfile.TemporaryDirectory(prefix='apple-calm-private-preferences-') as temporary:
 original=Path(temporary)/'Dashboard.conf';original.write_bytes(original_bytes);original.chmod(0o600)
 prior=kept(QSettings(str(original),QSettings.Format.IniFormat))
 assert kept(settings)==prior,'non-appearance preferences differ from original backup'
raw=subprocess.check_output(['systemctl','show','smartpc-dashboard.service','-p','ActiveState','-p','SubState','-p','NRestarts','-p','MainPID'],text=True)
service=dict(line.split('=',1) for line in raw.strip().splitlines())
assert service['ActiveState']=='active' and service['SubState']=='running' and service['NRestarts']=='0'
health_hash=hashlib.sha256(os.fsencode(str(data))).hexdigest()
health_path=f"/proc/{service['MainPID']}/root/tmp/smartpc-theme-health-{os.getuid()}/{health_hash}.json"
deadline=time.monotonic()+15
while True:
 try:health=json.loads(subprocess.check_output(['sudo','-n','cat',health_path],stderr=subprocess.DEVNULL))
 except subprocess.CalledProcessError:health={}
 if health.get('ready') is True and 0<=time.time()-health['time']<15:break
 if time.monotonic()>=deadline:break
 time.sleep(.25)
assert health.get('ready') is True and 0<=time.time()-health['time']<15,health
assert health['selection']==identity and health['pending'] is None
assert Path('/proc/'+str(health['pid'])).exists()
assert health['processStart']==process_token(health['pid'])
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
if a.before_boot_id:assert boot!=a.before_boot_id,'board did not reboot'
report={'status':'passed','qt':qVersion(),'revision':identity,'files':files,'resourceIntegrity':'passed','importPreflight':revision['preflight'],'service':service,'guiHeartbeatReady':True,'guiPid':health['pid'],'bootId':boot,'beforeBootId':a.before_boot_id,'osRebootVerified':bool(a.before_boot_id),'nonAppearancePreferencesPreservedFromOriginalBackup':True,'preservedPreferenceCount':len(prior),'paletteMode':config.get('paletteMode'),'motionMode':config.get('motionMode'),'pendingActivation':False,'latestAppleCalmOnly':True,'recoveryTarget':'Base','quarantined':False,'recovery':False}
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
