"""Authorized delivery: consolidate each pilot, preserve original artifacts/history."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,shutil,sqlite3,subprocess,sys,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-racing-objective-proof'
R=H/'smartpc-racing-final-runtime/dashboard';T=Path('/opt/smartpc/dashboard')
PY=H/'game-runtime/bin/python';G=H/'.local/share/SmartPC/SmartPC/game'
m=json.loads((R/'release-manifest.json').read_text())
assert m['version']=='0.9.0-rc.27' and len(m['sha256'])==640
assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
c=json.loads((P/'source-checks.json').read_text());assert c['status']=='passed'
assert all(c['sourceHashes'].get(n)==h for n,h in m['sha256'].items())
for theme in ('base','functional','apple'):
    d=json.loads((P/theme/'report.json').read_text())
    assert d['status']=='passed' and not d['qmlWarnings'] and d['window']==[960,640] and d['fiveCarsVisible']
    assert len(d['learners'])==4 and all(x['control']=='direct' and x['policyKind']=='direct' for x in d['learners'])
    if theme=='apple':assert d['completedRace'] and d['actualGuiQualification']
assert json.loads((P/'original-preservation.json').read_text())['status']=='passed'
assert json.loads((P/'scientific-receipt.json').read_text())['completeCohorts']
sys.path.insert(0,str(R))
from game_store import GameStore
from game_residual_migration import exchange,inventory
from game_direct_trainer import DirectTrainer
from game_neural_mixture import EXPERT_SIZE
import numpy as np

def health(label):
    path=P/(label+'.json');path.touch();subprocess.run(['chown','smartpc:smartpc',str(path)],check=True)
    subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),
        'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard',
        'QT_QPA_PLATFORM=offscreen',str(PY),str(H/'v086-source-proof/board-health.py'),'--output',str(path)],check=True,stdout=subprocess.DEVNULL)
    return json.loads(path.read_text())

def db_state(root):
    with closing(sqlite3.connect((root/'game.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
        assert not db.execute("SELECT 1 FROM sessions WHERE status='running'").fetchall(),'Pause required'
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {n:[dict(r) for r in db.execute('SELECT * FROM "'+n+'" ORDER BY rowid')] for n in names}

def qualify(stage,prior):
    store=GameStore(stage);rows=[]
    for d in store.drivers():
        if d['name']=='Maestro':continue
        payload=store.load(d['checkpoint']);payload['migrationSource']=d['checkpoint']
        original=np.asarray(payload['learner']['actor']);stable=payload['curriculum']['champion']['policy']
        t=DirectTrainer(d['profile'],'oval-1',payload)
        assert t.steps==d['steps'] and t.learner.update_index==0
        assert t.state['migration']['version']=='direct-racing-1'
        np.testing.assert_array_equal(t.learner.actor[:EXPERT_SIZE],original[:EXPERT_SIZE])
        np.testing.assert_array_equal(t.learner.actor[EXPERT_SIZE:],np.asarray(stable['weights'])[EXPERT_SIZE:])
        store.save_training(d['id'],t.checkpoint(d['seconds']),t.learner.policy(),d['steps'],d['seconds'],t.metric,t.state)
        rows.append(dict(id=d['id'],name=d['name'],steps=d['steps'],seconds=d['seconds'],sourceCheckpoint=d['checkpoint'],
            recipe=t.spec['version'],reward=t.reward_spec['version'],migration=t.state['migration'],epochUpdates=0))
    after=db_state(stage)
    for table in prior:
        if table not in ('drivers','history','driving_contexts'):assert after[table]==prior[table],table
    assert after['history'][:len(prior['history'])]==prior['history']
    added=after['history'][len(prior['history']):]
    assert len(added)==8 and sum(r['kind']=='racing_migration' for r in added)==4 and sum(r['kind']=='checkpoint' for r in added)==4
    contexts={(r['id'],r['context_hash']):r for r in after['driving_contexts']}
    assert len(contexts)==len(prior['driving_contexts'])
    migrated={r['id'] for r in rows};drivers={r['id']:r for r in after['drivers']}
    for previous in prior['driving_contexts']:
        current=contexts[(previous['id'],previous['context_hash'])]
        assert current['configuration']==previous['configuration']
        if previous['id'] in migrated:
            assert json.loads(current['state'])==drivers[previous['id']]
            old_state=json.loads(previous['state']);new_state=json.loads(current['state'])
            assert all(old_state[k]==new_state[k] for k in old_state if k not in ('candidate','checkpoint','curriculum','profile'))
        else:assert current==previous
    for before,now in zip(prior['drivers'],after['drivers']):
        assert all(before[k]==now[k] for k in ('id','name','number','policy','steps','seconds'))
        if before['name']=='Maestro':assert before==now
    return rows,after

before=health('before-install');assert before['version']=='0.9.0-rc.26' and not before['manifestMismatches']
stamp=time.strftime('%Y%m%d-%H%M%S');stage=T.with_name('dashboard-racing-stage-'+stamp)
old=T.with_name('dashboard-rc26-before-racing-'+stamp);gs=G.with_name('game-racing-stage-'+stamp)
backup=H/'game-backups'/('before-racing-objective-'+stamp);backup.parent.mkdir(exist_ok=True)
config=inventory(H/'.config/SmartPC');stage.mkdir()
for n,h in m['sha256'].items():
    dest=stage/n;assert dest.resolve().is_relative_to(stage.resolve());dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(R/n,dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==h
shutil.copy2(R/'release-manifest.json',stage/'release-manifest.json')
db_state(G)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);switched=False;swapped=False
try:
    original=inventory(G);prior=db_state(G);shutil.copytree(G,gs);gs.chmod(0o700)
    rows,expected=qualify(gs,prior)
    staged=inventory(gs)
    assert all(staged.get(n)==h for n,h in original.items() if not n.startswith('game.sqlite'))
    subprocess.run(['chown','-R','smartpc:smartpc',str(gs)],check=True)
    shutil.copytree(H/'.config/SmartPC',backup.with_name(backup.name+'-config'));os.sync()
    T.rename(old);switched=True;stage.rename(T)
    exchange(G,gs);swapped=True;gs.rename(backup);backup.chmod(0o700);os.sync()
    assert inventory(backup)==original and db_state(G)==expected
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True);deadline=time.monotonic()+90
    while True:
        time.sleep(3);after=health('installed');gui=after.get('guiHeartbeat') or {}
        if after['service']['ActiveState']=='active' and gui.get('ready') and gui.get('ageSeconds',999)<5 and not gui.get('pending') and gui.get('pid')==after['runtimePid'] and after['runtimePid']!=before['runtimePid']:break
        assert time.monotonic()<deadline,'GUI not ready'
    assert after['version']==m['version'] and not after['manifestMismatches'] and after['service']['NRestarts']=='0'
    assert before['allPreferenceHashes']==after['allPreferenceHashes'] and before['activeTheme']==after['activeTheme'] and before['bootId']==after['bootId']
    assert inventory(H/'.config/SmartPC')==config and db_state(G)==expected
    receipt=dict(status='passed',version=after['version'],files=len(m['sha256']),operation='racing-objective-preserved-pilots-new-critic-epoch',
        authorization='User authorized applying study and completing implementation',runtimeRollback=str(old),dataBackup=str(backup),backupFiles=len(original),
        backupHashesPreserved=True,drivers=rows,identitiesPreserved=True,lifetimeTotalsPreserved=True,historyPreserved=True,
        originalPolicyArtifactsPreserved=True,exactRacePoliciesAndQualificationsPreserved=True,preferencesPreserved=True,
        activeTheme=after['activeTheme'],liveGuiPidVerified=True,guiHeartbeat=gui,service=after['service'],
        manifestMismatches=after['manifestMismatches'],finalManifestSha256=hashlib.sha256((T/'release-manifest.json').read_bytes()).hexdigest(),
        newOSReboot=False,nativeCases=['base','functional','apple'],noStudyChampionsImported=True,noProductionTrainingStarted=True)
    (P/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
except BaseException:
    subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
    if swapped:exchange(G,backup if backup.exists() else gs)
    if switched:
        if T.exists():T.rename(T.with_name('dashboard-rc27-failed-'+stamp))
        old.rename(T)
    os.sync();raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
