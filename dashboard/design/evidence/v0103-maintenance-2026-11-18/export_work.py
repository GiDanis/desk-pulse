"""Verify complete temporary-work export, then permit only that exact cleanup."""
from pathlib import Path
import gzip,hashlib,json,subprocess,tarfile

W=Path(__file__).resolve().parent;B='/var/backups/smartpc-dashboard/20261118-continuous-rc1'
SSH=['ssh','-i','/home/giuseppe/.ssh/smartpc_ed25519','-o','BatchMode=yes','smartpc@192.168.1.179']
def fetch(remote,local):
    with local.open('wb') as f:subprocess.run([*SSH,'sudo -n cat '+remote],stdout=f,check=True)
fetch(B+'/work-export-verification.json',W/'work-export-verification.json')
fetch(B+'/work-export-inventory.json',W/'work-export-inventory.json')
receipt=json.loads((W/'work-export-verification.json').read_text())
archive=W/'board-work.tar.gz';fetch(receipt['archive'],archive)
h=hashlib.sha256()
with archive.open('rb') as f:
    for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
assert h.hexdigest()==receipt['archiveSha256']
nodes=json.loads((W/'work-export-inventory.json').read_text())['nodes'];seen=set();files=0
board=W/'board'
with tarfile.open(archive,'r:gz') as t:
    for m in t:
        assert m.name in nodes and m.name not in seen;seen.add(m.name);n=nodes[m.name]
        assert (m.uid,m.gid,m.mode)==(n['uid'],n['gid'],n['mode']) and abs(m.mtime-n['mtime'])<1e-6
        if n['kind']=='directory':assert m.isdir()
        elif n['kind']=='symlink':assert m.issym() and m.linkname==n['link']
        else:
            assert m.isfile() and not m.islnk();files+=1;f=t.extractfile(m);h=hashlib.sha256()
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
            assert h.hexdigest()==n['sha256']
            relative=Path(m.name).relative_to('work')
            if relative.parts[0]!='test-project' and relative.suffix in ('.json','.jsonl','.txt','.log','.png','.raw'):
                target=(board/relative).resolve();assert target.is_relative_to(board.resolve())
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('wb') as output:
                    f=t.extractfile(m)
                    for block in iter(lambda:f.read(1024*1024),b''):output.write(block)
assert seen==set(nodes)
with gzip.open(archive,'rb') as f:
    while f.read(1024*1024):pass
report={'status':'verified','archiveSha256':receipt['archiveSha256'],'members':len(nodes),'files':files,
        'metadataAndContentsVerified':True,'gzipCRCVerified':True,'hardlinks':0,'localArchive':str(archive)}
(W/'work-external-verification.json').write_text(json.dumps(report,indent=2)+'\n')
subprocess.run([*SSH,'sudo -n tee '+B+'/work-external-verification.json'],input=json.dumps(report).encode(),stdout=subprocess.DEVNULL,check=True)
print(json.dumps(report))
