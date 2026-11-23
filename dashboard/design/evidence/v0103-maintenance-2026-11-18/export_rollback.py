"""Export and independently verify every backup member before activation."""
from pathlib import Path
import gzip,hashlib,json,os,subprocess,tarfile

W=Path(__file__).resolve().parent
PRIVATE=Path('/home/giuseppe/.local/share/smartpc-private-backups/20261118-continuous-rc1')
SSH=['ssh','-i','/home/giuseppe/.ssh/smartpc_ed25519','-o','BatchMode=yes','smartpc@192.168.1.179']
B='/var/backups/smartpc-dashboard/20261118-continuous-rc1'
os.umask(0o077)
PRIVATE.mkdir(parents=True,mode=0o700,exist_ok=False)
def fetch(remote,local):
    with local.open('wb') as output:subprocess.run([*SSH,'sudo -n cat '+remote],stdout=output,check=True)
fetch(B+'/backup-verification.json',PRIVATE/'backup-verification.json')
fetch(B+'/archive-inventory-private.json',PRIVATE/'archive-inventory-private.json')
info=json.loads((PRIVATE/'backup-verification.json').read_text())
fetch(info['archive'],PRIVATE/'before.tar.gz')
archive=PRIVATE/'before.tar.gz'
h=hashlib.sha256()
with archive.open('rb') as stream:
    for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
assert h.hexdigest()==info['archiveSha256']
inventory=json.loads((PRIVATE/'archive-inventory-private.json').read_text());nodes=inventory['nodes']
seen=set();hardlinks=0
with tarfile.open(archive,'r:gz') as t:
    for m in t:
        assert m.name in nodes and m.name not in seen;seen.add(m.name);n=nodes[m.name]
        assert (m.uid,m.gid,m.mode)==(n['uid'],n['gid'],n['mode'])
        assert abs(m.mtime-n['mtime'])<1e-6
        if n['kind']=='directory':assert m.isdir()
        elif n['kind']=='symlink':assert m.issym() and m.linkname==n['link']
        else:
            assert m.isfile() or m.islnk();h=hashlib.sha256();stream=t.extractfile(m)
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
            assert h.hexdigest()==n['sha256']
            if m.islnk():
                hardlinks+=1
                assert any(m.name in g and m.linkname in g for g in inventory['hardlinkGroups'])
assert seen==set(nodes)
assert hardlinks==sum(len(g)-1 for g in inventory['hardlinkGroups'])
with gzip.open(archive,'rb') as stream:
    while stream.read(1024*1024):pass
receipt={'status':'verified','archiveSha256':info['archiveSha256'],'members':len(nodes),
         'hardlinks':hardlinks,'metadataAndContentsVerified':True,'gzipCRCVerified':True,
         'privateArchive':str(archive)}
(W/'external-backup.json').write_text(json.dumps(receipt,indent=2)+'\n')
subprocess.run(['scp','-i','/home/giuseppe/.ssh/smartpc_ed25519','-o','BatchMode=yes',
                str(W/'external-backup.json'),'smartpc@192.168.1.179:/var/lib/smartpc-dashboard/maintenance-work/external-backup.json'],check=True)
print(json.dumps(receipt))
