"""Verify all staging archive bytes and metadata on PC before board cleanup."""
from pathlib import Path,PurePosixPath
import argparse,gzip,hashlib,json,stat,tarfile
p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True);p.add_argument('--public',type=Path,required=True);a=p.parse_args()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
invpath=a.private/'staging-inventory.json';inv=json.loads(invpath.read_text());entries=inv['entries']
export=json.loads((a.private/'staging-export.json').read_text());archive=a.private/'staging-evidence.tar.gz'
assert sha(archive)==export['archiveSha256'] and sha(invpath)==export['inventorySha256']
prefix=Path(inv['root']).name;seen=set();files=0;hardlinks=0;groups={}
with tarfile.open(archive,'r:gz') as t:
 for m in t:
  parts=PurePosixPath(m.name).parts
  assert parts[0]==prefix and '..' not in parts,m.name
  name=str(PurePosixPath(*parts[1:])) if len(parts)>1 else '.'
  e=entries[name];seen.add(name)
  assert (m.mode,m.uid,m.gid)==(stat.S_IMODE(e['mode']),e['uid'],e['gid']),name
  assert abs(m.mtime-e['mtimeNs']/1e9)<1e-5,name
  if stat.S_ISDIR(e['mode']):assert m.isdir()
  elif stat.S_ISLNK(e['mode']):assert m.issym() and m.linkname==e['link']
  else:
   assert m.isfile() or m.islnk(),name
   f=t.extractfile(m);h=hashlib.sha256();size=0
   for c in iter(lambda:f.read(1024*1024),b''):h.update(c);size+=len(c)
   assert h.hexdigest()==e['sha256'] and size==e['size'],name
   groups.setdefault(tuple(e['inode']),[]).append(name);files+=1
   if m.islnk():
    target=str(PurePosixPath(*PurePosixPath(m.linkname).parts[1:]))
    assert entries[target]['inode']==e['inode'],name
    hardlinks+=1
  # Publish only qualification artifacts, never private data inventories.
  public=(name.startswith(('eglfs/','final-native-preflight/','arm-data/','arm-runtime-lint-optional/','arm-final-adapter/','arm-final-data/')) or name in {'post-install-check.json','resources-baseline.json','resources-installed.json','candidate.json','installation.json','backup-public.json','activation/report.json','cold-verify/report.json','activation/installed-home-demo.png','scanout/scanout.raw','scanout/scanout.json','scanout/drm-state.txt'})
  if public and m.isfile():
   target=a.public/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(t.extractfile(m).read())
  if name=='candidate-source/theme-projects/apple-calm/evidence/preflight-cache.json':
   a.public.mkdir(parents=True,exist_ok=True);(a.public/'preflight-cache-native.json').write_bytes(t.extractfile(m).read())
assert seen==set(entries) and hardlinks==sum(len(v)-1 for v in groups.values())
with gzip.open(archive,'rb') as f:
 while f.read(1024*1024):pass
receipt={'status':'passed','archiveSha256':export['archiveSha256'],'inventorySha256':export['inventorySha256'],'root':inv['root'],'entries':len(seen),'files':files,'hardlinks':hardlinks,'contentMetadataAndGzip':'verified on PC'}
(a.private/'staging-export-verified.json').write_text(json.dumps(receipt,indent=2)+'\n')
(a.public/'staging-export-verified.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
