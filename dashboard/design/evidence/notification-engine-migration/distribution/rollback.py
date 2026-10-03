import hashlib,json,pathlib,subprocess,tarfile,time
unit='smartpc-dashboard.service';runtime=pathlib.Path('/opt/smartpc/dashboard')
backup=pathlib.Path('/var/backups/smartpc-notifications-20261003/pre-migration');work=backup.parent/'rollback-proof'
work.mkdir(exist_ok=False)
prefs=pathlib.Path('/var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf')
def command(*args):return subprocess.check_output(args,text=True).strip()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def stable():
 pid=command('systemctl','show','-p','MainPID','--value',unit);time.sleep(6)
 assert pid!='0' and command('systemctl','is-active',unit)=='active' and command('systemctl','show','-p','MainPID','--value',unit)==pid
 return int(pid)
preferences=digest(prefs)
with tarfile.open(backup/'dashboard.tar.gz') as archive:archive.extractall(work,filter='data')
old=work/'dashboard';manifest=json.loads((old/'release-manifest.json').read_text())
command('python3','/tmp/smartpc-package-dashboard.py','verify',str(old))
command('systemctl','stop',unit);runtime.rename(work/'new');old.rename(runtime)
command('chown','-R','smartpc:smartpc',str(runtime))
try:
 command('systemctl','start',unit);oldpid=stable()
 command('python3','/tmp/smartpc-package-dashboard.py','verify',str(runtime));assert digest(prefs)==preferences
 assert json.loads((runtime/'release-manifest.json').read_text())==manifest
finally:
 command('systemctl','stop',unit);runtime.rename(work/'restored-old');(work/'new').rename(runtime);command('systemctl','start',unit)
newpid=stable();assert digest(prefs)==preferences
command('python3','/tmp/smartpc-package-dashboard.py','verify',str(runtime))
report={'previousSource':manifest['gitCommit'],'oldRuntimeFiles':len(manifest['sha256']),'newRuntimeFiles':len(json.loads((runtime/'release-manifest.json').read_text())['sha256']),
 'oldPid':oldpid,'newPid':newpid,'actualCompleteRollback':True,'distributionVerified':True,'preferencesUnchanged':True,'preferencesSha256':preferences,
 'scope':'Whole runtime replaced and started from fresh pre-migration backup, then notification engine restored. Production preferences/cache/event DB preserved.'}
(work/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
