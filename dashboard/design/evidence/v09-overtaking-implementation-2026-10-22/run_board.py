from pathlib import Path
import hashlib,json,shutil,sqlite3,subprocess,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-attack-proof';S=H/'smartpc-attack-project/dashboard'
PY=H/'game-runtime/bin/python';G=H/'.local/share/SmartPC/SmartPC/game'
m=json.loads((S/'release-manifest.json').read_text());assert m['version']=='0.9.3-rc.2'
assert all(hashlib.sha256((S/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
with sqlite3.connect('file:'+str(G/'game.sqlite')+'?mode=ro',uri=True) as db:
    assert not db.execute("SELECT 1 FROM sessions WHERE status='running'").fetchall(),'Pause required'
def artifacts():return {str(p.relative_to(G)):hashlib.sha256(p.read_bytes()).hexdigest() for p in G.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}
(P/'private/test-home').mkdir(exist_ok=True)
base=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
    'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);before=artifacts()
backup=H/'game-backups'/time.strftime('before-attack-native-%Y%m%d-%H%M%S');shutil.copytree(G,backup);backup.chmod(0o700)
try:
    env=base+['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
    for theme in ('base','functional','apple'):
        args=[str(PY),str(S/'check_game_menu_ui.py'),'--theme',theme,'--saved-root',str(P/'private/saved'),'--output',str(P/theme)]
        if theme=='apple':args+=['--all-modes','--full-race','--export-store',str(P/'private/reopen')]
        with (P/(theme+'.txt')).open('w') as out:
            subprocess.run(['runuser','-u','smartpc','--','env',*env,*args],cwd=S.parent,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=1200)
        d=json.loads((P/theme/'report.json').read_text());assert d['status']=='passed' and not d['qmlWarnings']
        assert len(d['sessions'])==(12 if theme=='apple' else 4) and all(r['updates']>r['previousUpdates'] and r['saved'] and r['menuUsed'] for r in d['sessions'])
        if theme=='apple':assert d['race']['completed'] and d['race']['fiveCarsVisible']
        print('Native menu '+theme+' passed',flush=True)
    args=[str(PY),str(S/'check_game_menu_ui.py'),'--theme','apple','--restore-store',str(P/'private/reopen'),'--output',str(P/'apple-reopen')]
    with (P/'apple-reopen.txt').open('w') as out:
        subprocess.run(['runuser','-u','smartpc','--','env',*env,*args],cwd=S.parent,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=600)
    d=json.loads((P/'apple-reopen/report.json').read_text());assert d['status']=='passed' and d['reopened'] and len(d['sessions'])==4
    (P/'source-checks.json').write_text(json.dumps(dict(status='passed',sourceHashes=m['sha256'],nativeCases=['base','functional','apple','apple-reopen'],
        allTwelveLearningCombinations=True,allFourReopened=True,fullRace=True),indent=2)+'\n')
    print('All four pilots reopened and saved through the menu',flush=True)
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    assert artifacts()==before,'Production policy artifacts changed'
    (P/'original-preservation.json').write_text(json.dumps(dict(status='passed',artifactCount=len(before),artifactsPreserved=True,
        rawBackup=str(backup),scope='Only private stores trained; production service restarted'),indent=2)+'\n')
