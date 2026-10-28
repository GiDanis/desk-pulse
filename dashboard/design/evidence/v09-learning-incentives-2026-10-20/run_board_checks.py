from pathlib import Path
import subprocess,json,hashlib,sqlite3
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-incentives-proof';S=H/'smartpc-incentives-project/dashboard';PY=H/'game-runtime/bin/python'
m=json.loads((S/'release-manifest.json').read_text())
assert all(hashlib.sha256((S/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
assert not any('spawn_main' in x or 'multiprocessing.spawn' in x for x in subprocess.check_output(['ps','-eo','args='],text=True).splitlines()),'Active training'
base=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
G=H/'.local/share/SmartPC/SmartPC/game'
def original_state():
    with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN');tables={}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            rows=db.execute('SELECT * FROM '+name+' ORDER BY rowid').fetchall()
            if name=='sessions':rows=[tuple('interrupted' if i==2 and v=='paused' else v for i,v in enumerate(row)) for row in rows]
            tables[name]=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    artifacts={str(p.relative_to(G)):hashlib.sha256(p.read_bytes()).hexdigest() for p in G.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}
    return dict(tables=tables,artifacts=artifacts)
before=original_state()
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    with (P/'arm-tests.txt').open('w') as out:
        subprocess.run(['runuser','-u','smartpc','--','env',*base,'QT_QPA_PLATFORM=offscreen','PYTHONPATH='+str(S),str(PY),'-m','unittest','check_game_incentives',
            'check_game_residual.ResidualTests.test_trainer_json_resume','check_game_residual.ResidualTests.test_offpolicy_resume_and_real_updates',
            'check_game_residual.ResidualTests.test_mode_change_preserves_learner_not_old_episode','-v'],cwd=S,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=300)
    print('ARM tests passed',flush=True)
    env=base+['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
    for theme in ('base','functional','apple'):
        with (P/(theme+'.txt')).open('w') as out:
            subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(S/'check_game_residual_ui.py'),'--theme',theme,'--saved-root',str(P/'private'),'--race-seconds','8','--output',str(P/theme)],cwd=S.parent,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=500)
        r=json.loads((P/theme/'report.json').read_text());assert r['status']=='passed' and not r['qmlWarnings'] and r['fiveCarsVisible']
        print('Native '+theme+' passed',flush=True)
    (P/'source-checks.json').write_text(json.dumps(dict(status='passed',sourceHashes=m['sha256'],manifestSha256=hashlib.sha256((S/'release-manifest.json').read_bytes()).hexdigest(),nativeCases=['base','functional','apple'],privateOriginalCheckpoints=4),indent=2)+'\n')
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    after=original_state();assert after==before,'Original game changed during private native checks'
    (P/'original-preservation.json').write_text(json.dumps(dict(status='passed',tablesPreserved=True,artifactsPreserved=True,artifactCount=len(before['artifacts']),allowedChange='paused session status to interrupted on kiosk restart'),indent=2)+'\n')
