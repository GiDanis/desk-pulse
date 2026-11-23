"""Read-only manifest for private export; preserve metadata and hardlink groups."""
from pathlib import Path
import hashlib,json,os,stat,sys
entries={};groups={};digests={}
for argument in sys.argv[1:]:
 root=Path(argument);assert root.is_absolute() and not root.is_symlink()
 assert str(root)=='/var/lib/smartpc-dashboard/maintenance-work/graphics-fix' or (root.parent==Path('/var/backups/smartpc-maintenance') and root.name.startswith('rollback-0.10.2-rc.'))
 selected=[root]
 for directory,dirs,files in os.walk(root,followlinks=False):selected.extend(Path(directory)/n for n in dirs+files)
 for p in sorted(selected):
  s=p.lstat();name=root.name+('/'+str(p.relative_to(root)) if p!=root else '')
  r={'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'mtime':int(s.st_mtime),'inode':[s.st_dev,s.st_ino]}
  if stat.S_ISDIR(s.st_mode):r['type']='directory'
  elif stat.S_ISLNK(s.st_mode):r.update(type='symlink',target=os.readlink(p))
  elif stat.S_ISREG(s.st_mode):
   key=(s.st_dev,s.st_ino)
   if key not in digests:
    h=hashlib.sha256()
    with p.open('rb') as f:
     for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    digests[key]=h.hexdigest()
   r.update(type='file',size=s.st_size,sha256=digests[key]);groups.setdefault(key,[]).append(name)
  else:raise ValueError('Unsupported special file: '+str(p))
  assert name not in entries;entries[name]=r
print(json.dumps({'entries':entries,'hardlinkGroups':sorted(sorted(g) for g in groups.values() if len(g)>1)},sort_keys=True))
