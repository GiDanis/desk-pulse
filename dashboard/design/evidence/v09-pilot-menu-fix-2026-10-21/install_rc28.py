"""Menu-only delivery: exact preservation of the complete production game DB."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,shutil,sqlite3,subprocess,sys,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-menu-proof';R=H/'smartpc-menu-runtime/dashboard'
T=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python';G=H/'.local/share/SmartPC/SmartPC/game'
m=json.loads((R/'release-manifest.json').read_text());assert m['version']=='0.9.0-rc.28' and len(m['sha256'])==642
assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
checks=json.loads((P/'source-checks.json').read_text());assert checks['status']=='passed'
assert all(checks['sourceHashes'].get(n)==h for n,h in m['sha256'].items())
assert checks['allTwelveLearningCombinations'] and checks['allFourReopened'] and checks['fullRace']
assert json.loads((P/'original-preservation.json').read_text())['status']=='passed'
assert json.loads((P/'pc-checks.json').read_text())['status']=='passed'
numeric=json.loads((P/'native-learning-proof.json').read_text());assert numeric['status']=='passed' and len(numeric['rows'])==12
for theme in ('base','functional','apple','apple-reopen'):
    d=json.loads((P/theme/'report.json').read_text())
    assert d['status']=='passed' and d['window']==[960,640] and not d['qmlWarnings']
    assert all(r['saved'] and r['menuUsed'] and r['updates']>r['previousUpdates'] for r in d['sessions'])
    if theme=='apple':assert d['race']['completed'] and d['race']['fiveCarsVisible']
sys.path.insert(0,str(R))
from game_residual_migration import inventory,exchange

def health(label):
    p=P/(label+'.json');p.touch();subprocess.run(['chown','smartpc:smartpc',str(p)],check=True)
    subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),
        'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',
        str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(p)],stdout=subprocess.DEVNULL,check=True)
    return json.loads(p.read_text())

def db_state(root):
    with closing(sqlite3.connect((root/'game.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
        assert not db.execute("SELECT 1 FROM sessions WHERE status='running'").fetchall(),'Pause required'
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {t:[dict(r) for r in db.execute('SELECT * FROM "'+t+'" ORDER BY rowid')] for t in tables}

before=health('before-install');assert before['version']=='0.9.0-rc.27' and not before['manifestMismatches']
stamp=time.strftime('%Y%m%d-%H%M%S');stage=T.with_name('dashboard-menu-stage-'+stamp)
old=T.with_name('dashboard-rc27-before-menu-'+stamp);backup=H/'game-backups'/('before-menu-fix-'+stamp)
stage.mkdir();config=inventory(H/'.config/SmartPC')
for name,digest in m['sha256'].items():
    target=stage/name;assert target.resolve().is_relative_to(stage.resolve());target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(R/name,target);assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
shutil.copy2(R/'release-manifest.json',stage/'release-manifest.json');db_state(G)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);switched=False
try:
    original=inventory(G);prior=db_state(G);shutil.copytree(G,backup);backup.chmod(0o700)
    assert inventory(backup)==original
    shutil.copytree(H/'.config/SmartPC',backup.with_name(backup.name+'-config'))
    os.sync();T.rename(old);switched=True;stage.rename(T)
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True);deadline=time.monotonic()+90
    while True:
        time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
        if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending') and gui.get('pid')==after['runtimePid'] and after['runtimePid']!=before['runtimePid']:break
        assert time.monotonic()<deadline,'GUI not ready'
    assert after['version']==m['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
    assert before['allPreferenceHashes']==after['allPreferenceHashes'] and before['activeTheme']==after['activeTheme'] and before['bootId']==after['bootId']
    assert inventory(H/'.config/SmartPC')==config and db_state(G)==prior
    current=inventory(G)
    assert all(current.get(n)==h for n,h in original.items() if not n.startswith('game.sqlite'))
    receipt=dict(status='passed',version=after['version'],files=len(m['sha256']),operation='menu-profile-validation-fix',
        authorization='User authorized implementation and confirmed pause',runtimeRollback=str(old),dataBackup=str(backup),
        backupFiles=len(original),backupHashesPreserved=True,entireGameDatabaseRowsPreserved=True,
        originalPolicyArtifactsPreserved=True,noModelReset=True,noRecipeMigration=True,noProductionTrainingStarted=True,
        preferencesPreserved=True,activeTheme=after['activeTheme'],liveGuiPidVerified=True,guiHeartbeat=gui,
        service=after['service'],manifestMismatches=after['manifestMismatches'],newOSReboot=False,
        finalManifestSha256=hashlib.sha256((T/'release-manifest.json').read_bytes()).hexdigest(),
        nativeCases=['base','functional','apple','apple-reopen'],allTwelveLearningCombinations=True,
        allFourReopened=True,fullRace=True)
    (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
    subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
    if switched:
        if T.exists():T.rename(T.with_name('dashboard-rc28-failed-'+stamp))
        old.rename(T)
    # This delivery never writes game data. Preserve the original backup for recovery.
    os.sync();raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
