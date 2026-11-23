"""Freeze and verify a private rollback before any installed runtime is replaced."""
from pathlib import Path
import gzip,hashlib,json,os,shutil,sqlite3,stat,subprocess,tarfile,tempfile

W=Path(__file__).resolve().parent
H=Path('/var/lib/smartpc-dashboard');R=Path('/opt/smartpc/dashboard')
B=Path('/var/backups/smartpc-dashboard/20261118-continuous-rc1')
PY=H/'game-runtime/bin/python'
ARCHIVE=Path('/dev/shm/smartpc-20261118-rollback.tar.gz')

def run(*args,**kwargs):return subprocess.run(list(map(str,args)),check=True,**kwargs)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def inventory(path):
    p=run('sudo','-n','-u','smartpc','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),
          PY,W/'collect-preservation.py',capture_output=True,text=True)
    value=json.loads(p.stdout);write(path,value);return value
def verify(root,digest):
    assert sha(root/'release-manifest.json')==digest
    m=json.loads((root/'release-manifest.json').read_text())
    assert all(sha(root/n)==d for n,d in m['sha256'].items())
    return m

def main():
    assert os.geteuid()==0
    os.umask(0o077)
    c=json.loads((W/'candidate.json').read_text())
    old=verify(R,c['baselineManifestSha256']);new=verify(W/'runtime',c['runtimeManifestSha256'])
    assert len(new['sha256'])==c['runtimeFiles']
    assert {n for n,d in new['sha256'].items() if old['sha256'].get(n)!=d}==set(c['deltaFiles'])
    assert shutil.disk_usage(H).free>10*1024**3
    assert not B.exists() and not ARCHIVE.exists()
    B.mkdir(mode=0o700)
    run('systemctl','stop','smartpc-dashboard')
    try:
        before=inventory(B/'before-private.json')
        selected=[R,*[p for p in H.iterdir() if p.name not in {'game-runtime','pilot-learner-runtime','maintenance-work'}],Path('/var/cache/smartpc-dashboard')]
        selected=[p for p in selected if p.exists()]
        write(B/'selected-roots-private.json',[str(p) for p in selected])
        snapshot=B/'snapshot';snapshot.mkdir()
        run('rsync','-aH','--checksum','--relative',*selected,snapshot)
        source_groups={};copy_groups={};count=0
        for root in selected:
            for p in [root,*root.rglob('*')] if root.is_dir() else [root]:
                q=snapshot/str(p).lstrip('/');a=p.lstat();b=q.lstat()
                assert (a.st_mode,a.st_uid,a.st_gid,a.st_mtime_ns)==(b.st_mode,b.st_uid,b.st_gid,b.st_mtime_ns)
                if p.is_symlink():assert os.readlink(p)==os.readlink(q)
                elif p.is_file():
                    assert sha(p)==sha(q)
                    source_groups.setdefault((a.st_dev,a.st_ino),set()).add(str(p))
                    copy_groups.setdefault((b.st_dev,b.st_ino),set()).add(str(p));count+=1
        assert {frozenset(v) for v in source_groups.values()}=={frozenset(v) for v in copy_groups.values()}
        dbs=0
        for path in snapshot.rglob('*'):
            if path.suffix not in ('.sqlite','.sqlite3','.db') or not path.is_file():continue
            if path.read_bytes()[:16]!=b'SQLite format 3\x00':continue
            with tempfile.TemporaryDirectory(dir=B,prefix='verify-db-') as tmp:
                target=Path(tmp)/path.name
                for suffix in ('','-wal','-shm'):
                    source=Path(str(path)+suffix)
                    if source.exists():shutil.copy2(source,Path(str(target)+suffix))
                with sqlite3.connect(target.as_uri()+'?mode=ro',uri=True) as db:
                    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                    assert not db.execute('PRAGMA foreign_key_check').fetchall()
                dbs+=1
        nodes={};groups={}
        for p in [snapshot,*snapshot.rglob('*')]:
            s=p.lstat();name=str(p.relative_to(snapshot.parent))
            node={'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode),'mtime':s.st_mtime}
            if p.is_symlink():node.update(kind='symlink',link=os.readlink(p))
            elif p.is_dir():node['kind']='directory'
            elif p.is_file():
                node.update(kind='file',sha256=sha(p),size=s.st_size)
                groups.setdefault((s.st_dev,s.st_ino),[]).append(name)
            else:raise AssertionError('Unsupported snapshot node')
            nodes[name]=node
        write(B/'archive-inventory-private.json',{'nodes':nodes,'hardlinkGroups':[v for v in groups.values() if len(v)>1]})
        os.sync()
        with tarfile.open(ARCHIVE,'w:gz',compresslevel=3,dereference=False) as archive:archive.add(snapshot,arcname='snapshot')
        seen=set();hardlinks=0
        with tarfile.open(ARCHIVE,'r:gz') as archive:
            for m in archive:
                assert m.name in nodes and m.name not in seen;seen.add(m.name);n=nodes[m.name]
                assert (m.uid,m.gid,m.mode)==(n['uid'],n['gid'],n['mode'])
                assert abs(m.mtime-n['mtime'])<1e-6
                if n['kind']=='symlink':assert m.issym() and m.linkname==n['link']
                elif n['kind']=='directory':assert m.isdir()
                else:
                    assert m.isfile() or m.islnk();h=hashlib.sha256();f=archive.extractfile(m)
                    for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
                    assert h.hexdigest()==n['sha256'];hardlinks+=int(m.islnk())
                    if m.islnk():assert any(m.name in g and m.linkname in g for g in groups.values())
        assert seen==set(nodes)
        assert hardlinks==sum(len(g)-1 for g in groups.values())
        with gzip.open(ARCHIVE,'rb') as stream:
            while stream.read(1024*1024):pass
        report={'status':'verified','archiveSha256':sha(ARCHIVE),'archiveBytes':ARCHIVE.stat().st_size,
                'members':len(nodes),'originalFilesCompared':count,'hardlinks':hardlinks,'databasesChecked':dbs,
                'snapshot':str(snapshot),'archive':str(ARCHIVE),'backup':str(B),'baseline':c['baselineManifestSha256'],
                'metadataAndContentsVerified':True,'gzipCRCVerified':True}
        write(B/'backup-verification.json',report);write(W/'backup-public.json',report)
        print(json.dumps(report),flush=True)
    except BaseException:
        run('systemctl','start','smartpc-dashboard')
        raise

if __name__=='__main__':main()
