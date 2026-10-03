import hashlib,json,pathlib,sqlite3,subprocess,time
unit='smartpc-dashboard.service';runtime=pathlib.Path('/opt/smartpc/dashboard')
backup=pathlib.Path('/var/backups/smartpc-notifications-20261003/pre-migration')
prefs=pathlib.Path('/var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf')
database=pathlib.Path('/var/lib/smartpc-dashboard/events.sqlite3')
def command(*args):return subprocess.check_output(args,text=True).strip()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def flags():
 if not database.exists():return {}
 with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as db:
  return {row[0]:list(row[1:]) for row in db.execute('SELECT id,notified_level,dismissed_level,seen FROM events WHERE cancelled=0')}
def protected(before,after):
 for identifier,values in before.items():
  if identifier in after:
   assert all(a>=b for a,b in zip(after[identifier],values)), 'Existing event state was reset'
 return True
backup.mkdir(parents=True,exist_ok=False);backup.chmod(0o700);backup.parent.chmod(0o700)
preferences=digest(prefs);before_manifest=json.loads((runtime/'release-manifest.json').read_text())
command('systemctl','stop',unit)
try:
 before=flags()
 command('tar','-czf',str(backup/'dashboard.tar.gz'),'-C','/opt/smartpc','dashboard')
 command('tar','-czf',str(backup/'user-state.tar.gz'),'-C','/var','lib/smartpc-dashboard','cache/smartpc-dashboard')
 command('bash','/tmp/smartpc-v066-install.sh')
 assert digest(prefs)==preferences,'Preferences changed during install'
 after=flags();assert protected(before,after)
 report={'backupDirectory':str(backup),'previousGitCommit':before_manifest['gitCommit'],'previousRuntimeFiles':len(before_manifest['sha256']),
  'newRuntimeFiles':len(json.loads((runtime/'release-manifest.json').read_text())['sha256']),
  'preferencesUnchanged':True,'preferencesSha256':preferences,'existingEventStateNotReset':True,'existingActiveEventRows':len(before),
  'backupSha256':{name:digest(backup/name) for name in ('dashboard.tar.gz','user-state.tar.gz')},
  'service':dict(line.split('=',1) for line in command('systemctl','show','-p','ActiveState','-p','MainPID','-p','NRestarts',unit).splitlines())}
 (backup/'deployment-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
 command('systemctl','start',unit)
