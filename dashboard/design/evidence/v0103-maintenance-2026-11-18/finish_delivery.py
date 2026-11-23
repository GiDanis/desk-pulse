"""Final health, complete work export, and receipt-bound temporary cleanup."""
from pathlib import Path
import gzip,hashlib,json,os,shutil,stat,subprocess,sys,tarfile,time
from prepare_delivery import W,H,R,B,verify,write,sha
sys.path.insert(0,str(R))
from soak import service_state,health_record,gui_identity

ARCHIVE=Path('/dev/shm/smartpc-20261118-work.tar.gz')
def nodes():
    result={}
    for p in [W,*W.rglob('*')]:
        s=p.lstat();n={'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode),'mtime':s.st_mtime}
        if p.is_symlink():n.update(kind='symlink',link=os.readlink(p))
        elif p.is_dir():n['kind']='directory'
        elif p.is_file():
            assert s.st_nlink==1,'Work hardlinks require explicit group verification'
            n.update(kind='file',sha256=sha(p),size=s.st_size)
        else:raise ValueError('Unsupported work node')
        result['work' if p==W else 'work/'+str(p.relative_to(W))]=n
    return result

def health():
    candidate=json.loads((W/'candidate.json').read_text());verify(R,candidate['runtimeManifestSha256'])
    state=service_state();pulse=health_record(int(state['MainPID']),H/'.local/share/SmartPC/SmartPC')
    gui=gui_identity(int(state['MainPID']),pulse)
    installation=json.loads((W/'installation.json').read_text())
    assert state['ActiveState']=='active' and state['NRestarts']=='0' and gui[0]==installation['guiPid']
    observation=json.loads((W/'installed-soak.json').read_text())
    assert observation['status']=='passed' and observation['samples']>=25
    fan=subprocess.check_output(['systemctl','show','smartpc-fan-ownership','-p','ActiveState','-p','ActiveEnterTimestampMonotonic'],text=True)
    f=dict(line.split('=',1) for line in fan.splitlines());assert f['ActiveState']=='active'
    kernel=subprocess.check_output(['journalctl','-b','-k','-n','2000','-o','json','--no-pager'],text=True)
    flags=('Cannot set pwm','pin PD5 already requested','enable pwm chan 5 failed')
    after=[json.loads(line) for line in kernel.splitlines() if int(json.loads(line).get('__MONOTONIC_TIMESTAMP',0))>int(f['ActiveEnterTimestampMonotonic'])]
    errors=[row['MESSAGE'] for row in after if any(s in str(row.get('MESSAGE','')) for s in flags)]
    assert not errors,'Fan ownership conflict still present'
    assert (Path('/sys/class/gpio/gpio101/value')).read_text().strip()=='1'
    assert not Path('/sys/bus/platform/drivers/pwm-fan/soc@3000000:pwm-fan').exists()
    spawn=[]
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:raw=path.read_bytes()
        except OSError:continue
        if b'spawn_main' in raw and path.parent.name in subprocess.check_output(['cat','/sys/fs/cgroup/system.slice/smartpc-dashboard.service/cgroup.procs'],text=True).split():spawn.append(int(path.parent.name))
    assert not spawn,'Metadata worker still resident after idle window'
    samples=observation['observations'];first,last=samples[0],samples[-1]
    helpers=lambda s:[p for p in s['processes'] if p['role']=='helper']
    gui_rows=[p for s in samples for p in s['processes'] if p['role']=='gui']
    cpu=[p['cpuPercentOneCore'] for p in gui_rows if p['cpuPercentOneCore'] is not None]
    report={'status':'passed','version':candidate['version'],'manifest':candidate['runtimeManifestSha256'],
        'service':state,'guiPid':gui[0],'sameGuiSinceInstall':True,'freshHeartbeat':True,
        'theme':pulse['selection'],'soakSeconds':observation['elapsed_s'],'soakSamples':observation['samples'],
        'guiRssMinKiB':min(p['rssKiB'] for p in gui_rows),'guiRssMaxKiB':max(p['rssKiB'] for p in gui_rows),
        'guiCpuMeanPercentOneCore':sum(cpu)/len(cpu) if cpu else None,
        'guiFdCounts':sorted({p['fds'] for p in gui_rows}),'guiThreadCounts':sorted({p['threads'] for p in gui_rows}),
        'helpersAtStart':helpers(first),'helpersAtEnd':helpers(last),'metadataWorkerReleased':True,
        'fanErrorsAfterHandoff':len(errors),'fanGpio101':'out/high retained','fanServiceEnabled':subprocess.check_output(['systemctl','is-enabled','smartpc-fan-ownership'],text=True).strip(),
        'temperaturesC':last['temperaturesC'],'freeBytes':shutil.disk_usage(H).free,
        'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'rebootPerformed':False,
        'scope':'Short passive installed-service check; no optical/HID/physical fan or long-term qualification.'}
    write(W/'final-health.json',report);write(B/'final-health.json',report)
    print(json.dumps(report),flush=True)

def archive():
    inventory=nodes();write(B/'work-export-inventory.json',{'nodes':inventory})
    with tarfile.open(ARCHIVE,'w:gz',compresslevel=3,dereference=False) as t:t.add(W,arcname='work')
    seen=set()
    with tarfile.open(ARCHIVE,'r:gz') as t:
        for m in t:
            assert m.name in inventory and m.name not in seen;seen.add(m.name);n=inventory[m.name]
            assert (m.uid,m.gid,m.mode)==(n['uid'],n['gid'],n['mode']) and abs(m.mtime-n['mtime'])<1e-6
            if n['kind']=='file':
                h=hashlib.sha256();f=t.extractfile(m)
                for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
                assert h.hexdigest()==n['sha256']
            elif n['kind']=='symlink':assert m.issym() and m.linkname==n['link']
            else:assert m.isdir()
    assert seen==set(inventory) and nodes()==inventory
    with gzip.open(ARCHIVE,'rb') as f:
        while f.read(1024*1024):pass
    report={'status':'verified','archive':str(ARCHIVE),'archiveSha256':sha(ARCHIVE),'members':len(inventory),'bytes':ARCHIVE.stat().st_size}
    write(B/'work-export-verification.json',report);print(json.dumps(report),flush=True)

def cleanup():
    external=json.loads((B/'work-external-verification.json').read_text());expected=json.loads((B/'work-export-verification.json').read_text())
    assert external['status']=='verified' and external['archiveSha256']==expected['archiveSha256']
    assert nodes()==json.loads((B/'work-export-inventory.json').read_text())['nodes'],'Work changed after verified export'
    ancestors=set();ancestor=os.getpid()
    while ancestor>1:
        ancestors.add(str(ancestor))
        ancestor=int((Path('/proc')/str(ancestor)/'stat').read_text().rsplit(')',1)[1].split()[1])
    for p in Path('/proc').glob('[0-9]*'):
        if p.name in ancestors:continue
        try:
            cwd=(p/'cwd').resolve();args=(p/'cmdline').read_bytes().split(b'\0')
            assert cwd!=W and W not in cwd.parents,'Live process cwd in maintenance work'
            assert not any(a.startswith(os.fsencode(str(W)) + b'/') for a in args),'Live process uses maintenance work'
            if (p/'maps').exists():assert str(W) not in (p/'maps').read_text(),'Live mapping in maintenance work'
        except OSError:continue
    backup=json.loads((B/'backup-verification.json').read_text())
    frozen=json.loads((B/'installation.json').read_text())
    assert frozen['externalBackupVerified'] and sha(backup['archive'])==backup['archiveSha256']
    shutil.rmtree(W)
    Path(backup['archive']).unlink();ARCHIVE.unlink()
    report={'status':'cleaned','workRemoved':str(W),'workArchiveVerifiedOnPC':True,'rollbackArchiveVerifiedOnPC':True,
        'rollbackRetained':str(B/'previous-runtime'),'snapshotRetained':str(B/'snapshot'),'freeBytes':shutil.disk_usage(H).free}
    write(B/'cleanup.json',report);print(json.dumps(report),flush=True)

if __name__=='__main__':
    assert os.geteuid()==0
    {'health':health,'archive':archive,'cleanup':cleanup}[sys.argv[1]]()
