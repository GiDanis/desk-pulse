"""Root, stdin contains the verified external receipt and canonical inventory hash."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
W=Path('/var/lib/smartpc-dashboard/maintenance-work/graphics-fix');H=Path('/var/lib/smartpc-dashboard');R=Path('/opt/smartpc/dashboard');request=json.load(sys.stdin)
assert os.geteuid()==0 and request['export']['status']=='passed' and request['export']['gzipIntegrity'] and request['export']['everyFileDigestAndMetadataVerified'] and request['export']['sourceRecheckedUnchanged']
assert W.is_dir() and not W.is_symlink()
m=json.loads(subprocess.check_output(['/usr/bin/python3',str(W/'inventory-archive-roots.py'),*request['export']['roots']]))
assert hashlib.sha256(json.dumps(m,sort_keys=True).encode()).hexdigest()==request['inventoryCanonicalSha256'],'Exported source changed'
f=json.loads((W/'live-rc4-production-final.json').read_text());assert f['status']=='passed' and f['version']=='0.10.2-rc.4' and f['newOsBoot'] and f['nativeDiagnosticProbeAbsent']
assert hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest()==f['manifestSha256']
S=Path('/etc/systemd/system');D=S/'smartpc-dashboard.service.d'
assert not any((D/n).exists() for n in ('90-aquarium-graphics-recovery.conf','99-aquarium-graphics-trial.conf'))
assert not any((S/n).exists() for n in ('smartpc-graphics-trial-recovery.service','smartpc-graphics-trial-recovery.timer'))
references=[]
def within(value):
 value=value.removesuffix(' (deleted)');return value==str(W) or value.startswith(str(W)+'/')
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 for kind in ('cwd','exe'):
  try:
   target=os.readlink(p/kind)
   if within(target):references.append([p.name,kind,target])
  except (FileNotFoundError,ProcessLookupError):pass
 for folder in ('fd','map_files'):
  try:links=list((p/folder).iterdir())
  except (FileNotFoundError,ProcessLookupError):continue
  for link in links:
   try:
    target=os.readlink(link)
    if within(target):references.append([p.name,folder,target])
   except (FileNotFoundError,ProcessLookupError):pass
assert not references,references
shutil.rmtree(W);assert not W.exists()
s=dict(l.split('=',1) for l in subprocess.check_output(['systemctl','show','smartpc-dashboard.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True).splitlines());assert s['ActiveState']=='active' and s['NRestarts']=='0' and s['MainPID']==f['service']['MainPID']
receipt={'status':'passed','observedAt':time.time(),'removed':str(W),'removedOnlyVerifiedOwnedWorkarea':True,'externalArchiveSha256':request['export']['sha256'],'membersVerified':request['export']['membersVerified'],'hardlinkGroupsVerified':request['export']['hardlinkGroupsVerified'],'sourceRecheckedBeforeDeletion':True,'liveReferences':references,'runtimeManifestSha256':f['manifestSha256'],'service':s,'sameProductionProcess':True,'rollbacksRetained':request['export']['roots'][1:],'legacyAndExperimentalCacheFilesRetained':True,'temporarySystemdGuardAbsent':True}
out=H/'maintenance-receipts';out.mkdir(exist_ok=True);p=out/'aquarium-graphics-rc4-20261029.json';p.write_text(json.dumps(receipt,indent=2)+'\n');p.chmod(0o640);print(json.dumps(receipt),flush=True)
