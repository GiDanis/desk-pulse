import hashlib,json,pathlib,sqlite3,subprocess,time,os,shutil
unit='smartpc-dashboard.service'
runtime=pathlib.Path('/opt/smartpc/dashboard')
staged=pathlib.Path('/var/tmp/smartpc-theme-bb4d76c-runtime')
backup=pathlib.Path('/var/backups/smartpc-theme-a1a6-20261006-bb4d76c-final')
prefs=pathlib.Path('/var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf')
database=pathlib.Path('/var/lib/smartpc-dashboard/events.sqlite3')
def command(*args): return subprocess.check_output(args,text=True).strip()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def verify(root):
 m=json.loads((root/'release-manifest.json').read_text())
 assert not m['dirty'] and m['distributionKind']=='runtime'
 assert all(digest(root/p)==v for p,v in m['sha256'].items())
 assert not (root/'fixtures/theme-runtime/renderers').exists()
 return m
def flags():
 if not database.exists():return {}
 with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as db:
  return {row[0]:list(row[1:]) for row in db.execute('SELECT id,notified_level,dismissed_level,seen FROM events')}
def properties():
 return dict(line.split('=',1) for line in command('systemctl','show','-p','ActiveState','-p','MainPID','-p','NRestarts',unit).splitlines())
def health(pid):
 argv=pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
 assert any(v.endswith('/theme_supervisor.py') for v in argv),argv
 root=pathlib.Path(argv[argv.index('--data-root')+1])
 procroot=pathlib.Path(f'/proc/{pid}/root')
 records=list((procroot/'tmp').glob('smartpc-theme-health-*/*.json'))
 key=hashlib.sha256(os.fsencode(str(root))).hexdigest()+'.json'
 record=json.loads(next(path for path in records if path.name==key).read_text())
 child=record['pid']
 stat=pathlib.Path(f'/proc/{child}/stat').read_text().split(') ',1)[1].split()
 assert int(stat[1])==pid and str(stat[19])==str(record['processStart'])
 assert record['ready'] and record['pending'] is None and time.time()-record['time']<5
 journal_path=root/'theme-activation.json'
 journal=json.loads(journal_path.read_text()) if journal_path.exists() else None
 # Base without an activation has no durable journal yet; health is canonical.
 assert journal is not None or record.get('pending') is None
 return {'health':record,'dataRoot':str(root),'journal':journal,'journalExists':journal_path.exists()}

report_path=pathlib.Path('/var/backups/smartpc-theme-a1a6-20261006-bb4d76c-final/deployment-report.json')
before=json.loads(report_path.read_text())
initial=properties();pid=int(initial['MainPID']);started=time.time()
while time.time()-started<15:
 time.sleep(1);current=properties()
 assert current['ActiveState']=='active' and int(current['MainPID'])==pid and current['NRestarts']=='0',current
health_deadline=time.monotonic()+5
while True:
 try: live=health(pid);break
 except AssertionError:
  if time.monotonic()>=health_deadline:raise
  time.sleep(.25)
manifest=verify(runtime)
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot!=before['bootId']
journal=command('journalctl','-u',unit,'-b','--no-pager','-o','cat')
assert not any(v in journal for v in ['Binding loop detected','Unable to assign','ReferenceError:','TypeError:','Cannot assign to','failed to load component'])
result={'status':'passed','physicalRebootObserved':True,'bootIdBefore':before['bootId'],'bootIdAfter':boot,'service':current,'stabilitySeconds':15,'runtimeSourceCommit':manifest['gitCommit'],'runtimeFilesVerified':len(manifest['sha256']),'qmlWarnings':[],**live,'scope':'Real software-requested device reboot and production EGLFS startup; no power cut, physical keypad or long soak claim'}
out=pathlib.Path('/var/tmp/smartpc-theme-bb4d76c-final');(out/'post-reboot.json').write_text(json.dumps(result,indent=2)+'\n');(out/'post-reboot-journal.txt').write_text(journal+'\n');print(json.dumps(result))
