from pathlib import Path
import hashlib,json,sqlite3,subprocess,shutil,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-menu-proof';S=H/'smartpc-menu-project/dashboard';PY=H/'game-runtime/bin/python'
G=H/'.local/share/SmartPC/SmartPC/game';m=json.loads((S/'release-manifest.json').read_text())
assert all(hashlib.sha256((S/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
for old in ('source-before-diagnostic-fix.json','source-before-resume-budget.json'):
    before=json.loads((P/old).read_text())
    assert {n for n,h in m['sha256'].items() if before['sha256'].get(n)!=h}=={'check_game_menu_ui.py'}
for theme in ('base','functional','apple'):
    d=json.loads((P/theme/'report.json').read_text());assert d['status']=='passed' and not d['qmlWarnings']
    assert len(d['sessions'])==(12 if theme=='apple' else 4)
assert d['race']['completed'] and d['race']['fiveCarsVisible']
with sqlite3.connect('file:'+str(G/'game.sqlite')+'?mode=ro',uri=True) as db:
    assert not db.execute("SELECT 1 FROM sessions WHERE status='running'").fetchall()
def artifacts():return {str(f.relative_to(G)):hashlib.sha256(f.read_bytes()).hexdigest() for f in G.rglob('*') if f.is_file() and not f.name.startswith('game.sqlite')}
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard',
    'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms',
    'QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);original=artifacts()
backup=H/'game-backups'/time.strftime('before-menu-resume-%Y%m%d-%H%M%S');shutil.copytree(G,backup);backup.chmod(0o700)
try:
    args=[str(PY),str(S/'check_game_menu_ui.py'),'--theme','apple','--restore-store',str(P/'private/reopen'),'--output',str(P/'apple-reopen')]
    with (P/'apple-reopen.txt').open('w') as out:
        subprocess.run(['runuser','-u','smartpc','--','env',*env,*args],cwd=S.parent,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=600)
    d=json.loads((P/'apple-reopen/report.json').read_text());assert d['status']=='passed' and d['reopened'] and len(d['sessions'])==4
    assert all(r['updates']>r['previousUpdates'] and r['steps']>r['previousSteps'] and r['saved'] for r in d['sessions'])
    (P/'source-checks.json').write_text(json.dumps(dict(status='passed',sourceHashes=m['sha256'],nativeCases=['base','functional','apple','apple-reopen'],
        allTwelveLearningCombinations=True,allFourReopened=True,fullRace=True,productionSourceUnchangedAcrossRetries=True,
        caseSourceManifests=dict(base='source-before-diagnostic-fix.json',functional='source-before-diagnostic-fix.json',apple='source-before-resume-budget.json',reopen='final'),
        diagnosticDeltas=['Stop after finished instead of pause','Short off-policy resume before an expensive verification, still requiring actual new updates and save']),indent=2)+'\n')
    print('Final four-pilot reopen passed; previous unchanged product evidence retained',flush=True)
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True);assert artifacts()==original
    (P/'original-preservation.json').write_text(json.dumps(dict(status='passed',artifactsPreserved=True,artifactCount=len(original),rawBackup=str(backup),scope='Only private stores trained; production restarted'),indent=2)+'\n')
