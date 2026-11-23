"""Archive this task's staging, then remove only after external verification."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,stat,tarfile
p=argparse.ArgumentParser();p.add_argument('operation',choices=['export','cleanup']);p.add_argument('--apply',action='store_true');a=p.parse_args()
assert os.getuid()==0
os.umask(0o077)
W=Path('/var/lib/smartpc-dashboard/maintenance-work/calm-20261030')
B=Path('/var/backups/smartpc-dashboard/20261030-calm-rc5-retry3')
ARCHIVE=Path('/dev/shm/smartpc-calm-rollback3/staging-evidence.tar.gz')
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def inventory():
 entries={}
 for q in [W,*W.rglob('*')]:
  s=q.lstat();entry={'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'mtimeNs':s.st_mtime_ns,'size':s.st_size,'inode':[s.st_dev,s.st_ino]}
  if q.is_symlink():entry['link']=os.readlink(q)
  elif q.is_file():entry['sha256']=sha(q)
  elif not q.is_dir():raise AssertionError('Unexpected special node')
  entries[str(q.relative_to(W))]=entry
 return entries
if a.operation=='export':
 assert json.loads((W/'installation.json').read_text())['status']=='installed'
 discovery=W/'preservation-discovery-private.json'
 if discovery.exists():discovery.rename(B/discovery.name)
 inv={'root':str(W),'entries':inventory()}
 (B/'staging-inventory.json').write_text(json.dumps(inv,indent=2)+'\n')
 with tarfile.open(ARCHIVE,'w:gz',compresslevel=3,dereference=False) as t:t.add(W,arcname=W.name)
 assert inv['entries']==inventory(),'Staging changed during export'
 result={'archiveSha256':sha(ARCHIVE),'inventorySha256':sha(B/'staging-inventory.json'),'entries':len(inv['entries'])}
 (B/'staging-export.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
else:
 assert a.apply,'Cleanup requires --apply'
 inv=json.loads((B/'staging-inventory.json').read_text());receipt=json.loads((B/'staging-export-verified.json').read_text())
 assert receipt['status']=='passed' and receipt['inventorySha256']==sha(B/'staging-inventory.json')
 assert receipt['archiveSha256']==sha(ARCHIVE)
 assert inv['root']==str(W) and inv['entries']==inventory(),'Staging differs from verified export'
 references=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  links=[proc/'cwd',proc/'exe']
  for sub in ['fd','map_files']:
   try:links+=list((proc/sub).iterdir())
   except (FileNotFoundError,PermissionError):pass
  for q in links:
   try:target=os.readlink(q)
   except (FileNotFoundError,PermissionError,OSError):continue
   if target==str(W) or target.startswith(str(W)+'/'):references.append([proc.name,str(q),target])
 assert not references,references
 assert W.parent==Path('/var/lib/smartpc-dashboard/maintenance-work') and not W.is_symlink()
 shutil.rmtree(W)
 (ARCHIVE).unlink()  # Exact verified archive remains on PC.
 result={'status':'passed','removedRoot':str(W),'verifiedEntries':len(inv['entries']),'archiveSha256':receipt['archiveSha256'],'activeProcessReferences':0,'privateBackupRetained':str(B)}
 (H:=Path('/var/lib/smartpc-dashboard/maintenance-receipts')).mkdir(exist_ok=True)
 (H/'calm-20261030-cleanup.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
