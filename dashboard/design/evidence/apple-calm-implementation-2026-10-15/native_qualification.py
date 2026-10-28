"""Run as root on the dedicated board; always restore the installed service.

Only private fixtures run on the panel. Production game data/preferences are
fingerprinted before and after. No installation is performed by this script.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import argparse

parser=argparse.ArgumentParser();parser.add_argument('--proof-root',type=Path,default=Path('/tmp/smartpc-apple-evidence'))
parser.add_argument('--loop-only',action='store_true');options=parser.parse_args()

H=Path('/var/lib/smartpc-dashboard');W=Path('/tmp/smartpc-apple-candidate')
E=options.proof_root;E.mkdir(parents=True,exist_ok=True);PY=H/'game-runtime/bin/python'
DATA=H/'.local/share/SmartPC/SmartPC';GAME=DATA/'game'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def game_snapshot():
    with sqlite3.connect((GAME/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        tables={r[0]:db.execute('SELECT * FROM "'+r[0]+'" ORDER BY rowid').fetchall()
                for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return {'tables':{name:hashlib.sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest() for name,rows in tables.items()},
            'artifacts':{p.name:digest(p) for p in (GAME/'policies').glob('*.json')},
            'runningSessions':[r[0] for r in tables.get('sessions',[]) if r[2]=='running']}
def preferences():return {str(p.relative_to(H/'.config')):digest(p) for p in (H/'.config/SmartPC').rglob('*') if p.is_file()}
def write(name,value):(E/name).write_text(json.dumps(value,indent=2)+'\n')
initial=game_snapshot();assert not initial['runningSessions'],'Production training running; do not interrupt'
prefs=preferences();write('before-native-game.json',initial)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    stable=game_snapshot();write('stable-game.json',stable)
    assert stable['artifacts']==initial['artifacts']
    assert preferences()==prefs
    (E/'native').mkdir(exist_ok=True)
    subprocess.run(['chown','-R','smartpc:smartpc',str(E)],check=True)
    env=['HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms',
         'QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1',
         'QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
    def run(label,script,args,timeout):
        print('START '+label,flush=True)
        with (E/(label+'.txt')).open('w') as out:
            subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(script),*map(str,args)],
                            cwd=W,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=timeout)
        print('PASS '+label,flush=True)
    def dashboard(label,bundle,theme='apple',variant='day',motion='normal',seconds=60,warmup=30):
        dashboard_root=Path('/tmp/smartpc-cancel-before/dashboard') if label.startswith('original-') and options.loop_only else W/'dashboard'
        args=['--dashboard',dashboard_root,'--theme',theme,'--variant',variant,'--motion',motion,
              '--seconds',seconds,'--warmup',warmup,'--output',E/'native'/label]
        if theme=='apple':args+=['--bundle',bundle,'--cache',E/('candidate-cache.json' if 'candidate' in label or 'soak' in label or 'night' in label else 'original-cache.json')]
        run(label,W/'qualify_apple.py',args,seconds+warmup+150)
    run('readmission-native',W/'dashboard/check_theme_readmission_ui.py',
        ['--output',E/'native/readmission'],240)
    for i in range(0 if options.loop_only else 3):
        for label,bundle in [('original',Path('/tmp/smartpc-apple-work/theme-projects/apple-calm/bundle')),
                             ('candidate',W/'theme-projects/apple-calm/bundle')]:
            run('charts-'+label+'-'+str(i),W/'benchmark_charts.py',
                ['--bundle',bundle,'--output',E/'native'/('charts-'+label+'-'+str(i))],60)
    original=Path('/tmp/smartpc-apple-work/theme-projects/apple-calm/bundle')
    candidate=W/'theme-projects/apple-calm/bundle'
    if not options.loop_only:
        dashboard('base-control',None,theme='base')
        dashboard('functional-control',None,theme='functional',seconds=20,warmup=5)
    for i in range(3):
        pair=[('original-'+str(i),original),('candidate-'+str(i),candidate)]
        if i%2:pair.reverse()
        for label,bundle in pair:dashboard(label,bundle)
    if not options.loop_only:
        dashboard('night-reduced',candidate,variant='night',motion='reduced',seconds=30,warmup=5)
        dashboard('night-off',candidate,variant='night',motion='off',seconds=30,warmup=5)
        run('game-settings-native',W/'dashboard/check_game_settings_ui.py',
            ['--theme','apple','--capture-dir',E/'native/game-settings'],360)
    dashboard('soak-30min',candidate,seconds=1800,warmup=30)
    after=game_snapshot();assert after==stable,'Private tests changed production game'
    assert preferences()==prefs,'Private tests changed production settings'
    write('native-receipt.json',{'status':'passed','privateNativeTests':True,
          'productionGameUnchanged':True,'preferencesUnchanged':True,
          'artifactCount':len(after['artifacts']),'newOSReboot':False})
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
