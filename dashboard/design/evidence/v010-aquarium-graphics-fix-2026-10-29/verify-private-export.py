"""Run on PC: export only selected roots, verify every member, metadata and links."""
from pathlib import Path
import gzip,hashlib,json,shlex,subprocess,tarfile,time
E=Path(__file__).resolve().parent;W='/var/lib/smartpc-dashboard/maintenance-work/graphics-fix'
P=Path('/home/giuseppe/Documenti/SmartPC-backups/aquarium-3d-install-20261029/graphics-fix');P.mkdir(parents=True,exist_ok=True,mode=0o700)
SSH=['ssh','-T','-i','/home/giuseppe/.ssh/smartpc_ed25519','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','smartpc@192.168.1.179']
roots=[W,'/var/backups/smartpc-maintenance/rollback-0.10.2-rc.2-graphics-fix-20261029-134638','/var/backups/smartpc-maintenance/rollback-0.10.2-rc.3-graphics-fix-20261029-210619']
remote=W+'/inventory-archive-roots.py'
def inventory():
 r=subprocess.run(SSH+['sudo python3 '+shlex.quote(remote)+' '+' '.join(map(shlex.quote,roots))],check=True,capture_output=True,timeout=180)
 return json.loads(r.stdout)
m=json.loads((P/'export-inventory.json').read_text());archive=P/'graphics-fix-work-and-rollbacks.tar.gz';assert archive.is_file()
print('VERIFY_GZIP',archive.stat().st_size,flush=True)
with gzip.open(archive,'rb') as f:
 for _ in iter(lambda:f.read(1024*1024),b''):pass
print('VERIFY_MEMBERS',flush=True)
with tarfile.open(archive,'r|gz') as t:
 actual={};digest_cache={}
 def target(n):
  seen=set()
  while actual[n].islnk():
   assert n not in seen;seen.add(n);n=actual[n].linkname
  return n
 for x in t:
  name=x.name.rstrip('/');assert name in m['entries'] and name not in actual;actual[name]=x;row=m['entries'][name]
  assert (x.mode,x.uid,x.gid,int(x.mtime))==(row['mode'],row['uid'],row['gid'],row['mtime']),(name,'metadata')
  if row['type']=='directory':assert x.isdir()
  elif row['type']=='symlink':assert x.issym() and x.linkname==row['target']
  else:
   assert x.isfile() or x.islnk();canonical=target(name)
   if canonical not in digest_cache:
    assert x.isfile()
    h=hashlib.sha256();length=0
    with t.extractfile(x) as f:
     for b in iter(lambda:f.read(1024*1024),b''):h.update(b);length+=len(b)
    digest_cache[canonical]=(length,h.hexdigest())
   assert digest_cache[canonical]==(row['size'],row['sha256']),(name,'content')
 assert set(actual)==set(m['entries'])
 for g in m['hardlinkGroups']:assert len({target(n) for n in g})==1,('hardlinks',g)
print('RECHECK_SOURCE',flush=True);assert inventory()==m,'Source changed during export; refuse deletion'
h=hashlib.sha256()
with archive.open('rb') as f:
 for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
receipt={'status':'passed','archive':str(archive),'bytes':archive.stat().st_size,'sha256':h.hexdigest(),'roots':roots,'membersVerified':len(m['entries']),'hardlinkGroupsVerified':len(m['hardlinkGroups']),'gzipIntegrity':True,'everyFileDigestAndMetadataVerified':True,'sourceRecheckedUnchanged':True,'containsPrivateData':True,'boardBackupsRetained':True}
(P/'export-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');(P/'export-verification.json').chmod(0o600)
(E/'private-export-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
