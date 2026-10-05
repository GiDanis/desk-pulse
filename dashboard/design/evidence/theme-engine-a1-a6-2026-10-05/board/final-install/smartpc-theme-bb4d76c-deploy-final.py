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
manifest=verify(staged)
assert manifest['gitCommit'].startswith('bb4d76c')
backup.mkdir(parents=True,exist_ok=False);backup.chmod(0o700)
previous=json.loads((runtime/'release-manifest.json').read_text())
command('systemctl','stop',unit)
installed=False
try:
 before_prefs=digest(prefs);before_flags=flags()
 command('tar','-czf',str(backup/'dashboard.tar.gz'),'-C','/opt/smartpc','dashboard')
 command('tar','-czf',str(backup/'user-state.tar.gz'),'-C','/var','lib/smartpc-dashboard','cache/smartpc-dashboard')
 incoming=pathlib.Path('/opt/smartpc/theme-incoming-bb4d76c')
 assert not incoming.exists();shutil.copytree(staged,incoming)
 command('chown','-R','smartpc:smartpc',str(incoming));verify(incoming)
 runtime.rename(backup/'previous-runtime');incoming.rename(runtime);installed=True
 assert digest(prefs)==before_prefs
 command('systemctl','start',unit)
 initial=properties();pid=int(initial['MainPID']);assert pid>0
 started=time.time()
 while time.time()-started<15:
  time.sleep(1);current=properties()
  assert current['ActiveState']=='active' and int(current['MainPID'])==pid and current['NRestarts']=='0',current
 live=health(pid);verify(runtime)
 after_flags=flags()
 assert all(all(a>=b for a,b in zip(after_flags[key],values)) for key,values in before_flags.items() if key in after_flags)
 journal=command('journalctl','-u',unit,'--since','@'+str(int(started)),'--no-pager','-o','cat')
 (backup/'startup-journal.txt').write_text(journal+'\n')
 needles=['Binding loop detected','Unable to assign','ReferenceError:','TypeError:','Cannot assign to','failed to load component']
 assert not any(needle in journal for needle in needles),journal
 report={'status':'installed','sourceCommit':manifest['gitCommit'],'files':len(manifest['sha256']),
  'previousCommit':previous['gitCommit'],'backupDirectory':str(backup),'runtimeSha256Verified':True,
  'diagnosticRendererExcluded':True,'preferencesUnchangedBeforeStart':True,'preferencesUnchangedAfterStartup':digest(prefs)==before_prefs,
  'preferencesSha256Before':before_prefs,'preferencesSha256After':digest(prefs),
  'existingEventsStateNotReset':True,'eventRowsBefore':len(before_flags),'eventRowsRetained':len(set(before_flags)&set(after_flags)),
  'service':current,'stabilitySeconds':15,'bootId':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),**live,
  'backupSha256':{name:digest(backup/name) for name in ('dashboard.tar.gz','user-state.tar.gz')}}
 (backup/'deployment-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
except BaseException as error:
 command('systemctl','stop',unit)
 if installed:
  runtime.rename(backup/'failed-runtime');(backup/'previous-runtime').rename(runtime)
 (backup/'rollback-report.json').write_text(json.dumps({'status':'rolledBack','error':str(error)},indent=2)+'\n')
 raise
finally: command('systemctl','start',unit)
