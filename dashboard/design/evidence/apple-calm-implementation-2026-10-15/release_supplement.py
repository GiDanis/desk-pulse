"""Native acceptance of the final empty-chart clear delta; no production edits."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

H=Path('/var/lib/smartpc-dashboard');PY=H/'game-runtime/bin/python'
W=Path('/tmp/smartpc-apple-candidate');E=Path('/tmp/smartpc-apple-final-proof')
release=Path('/tmp/smartpc-apple-release');game=H/'.local/share/SmartPC/SmartPC/game'
def fingerprint():
    with sqlite3.connect((game/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        tables={r[0]:db.execute('SELECT * FROM "'+r[0]+'" ORDER BY rowid').fetchall()
                for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not any(r[2]=='running' for r in tables.get('sessions',[]))
    return {'db':hashlib.sha256(json.dumps(tables,sort_keys=True,default=str).encode()).hexdigest(),
            'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (game/'policies').glob('*.json')},
            'config':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'.config/SmartPC').glob('*') if p.is_file()}}
assert json.loads((release/'preview/preview-report.json').read_text())['status']=='passed'
before=fingerprint();subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    stable=fingerprint();assert before==stable
    env=['HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms',
         'QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1',
         'QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
    reports=[]
    def run(label,script,args):
        print('START '+label,flush=True)
        with (E/(label+'.txt')).open('w') as out:
            subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(script),*map(str,args)],
                cwd=W,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)
        report=json.loads((E/'native'/label/'report.json').read_text())
        reports.append((label,report));print('PASS '+label,flush=True)
    for i in range(3):
        for label,bundle in [('release-original',Path('/tmp/smartpc-apple-work/theme-projects/apple-calm/bundle')),
                             ('release-final',release/'bundle')]:
            name=label+'-'+str(i)
            run(name,W/'benchmark_charts.py',['--bundle',bundle,'--output',E/'native'/name])
    for i in range(3):
        old=dict(reports)['release-original-'+str(i)];new=dict(reports)['release-final-'+str(i)]
        assert all(x['visibleSha256']==y['visibleSha256'] for x,y in zip(old['rows'],new['rows']))
        assert new['rows'][0]['missingChartCleared'] is True
        assert all(row['hiddenPointReads']==0 and row['resumePixelParity'] and not row['qmlWarnings'] for row in new['rows'])
    run('release-main-native',W/'qualify_apple.py',[
        '--dashboard',W/'dashboard','--bundle',release/'bundle','--cache',release/'cache.json',
        '--seconds',30,'--warmup',10,'--output',E/'native/release-main-native'])
    last=reports[-1][1]
    assert last['status']=='passed' and not last['qmlWarnings'] and not last['transportAttempts']
    assert last['appearancePublicationsDuringNavigation']==0
    assert fingerprint()==stable
    receipt={'status':'passed','bundle':last['bundle'],'nativeCases':[label for label,_ in reports],
             'missingChartCleared':True,'visiblePixelsMatchOriginal':True,
             'privateDataOnly':True,'productionDataAndSettingsUnchanged':True,
             'scope':'Final payload native delta acceptance. The 30-minute core soak uses the explicitly recorded earlier graph digest.'}
    (E/'release-supplement.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
