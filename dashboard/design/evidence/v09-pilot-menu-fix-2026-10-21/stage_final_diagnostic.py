from pathlib import Path
import hashlib,json,shutil
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-menu-proof'
S=H/'smartpc-menu-project/dashboard';R=H/'smartpc-menu-runtime/dashboard'
shutil.copy2(S/'release-manifest.json',P/'source-before-resume-budget.json')
for root in (S,R):
    m=json.loads((root/'release-manifest.json').read_text())
    assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
    f=root/'check_game_menu_ui.py';shutil.copy2('/tmp/check_game_menu_ui.py',f)
    m['sha256'][f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
    (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
for name in ('apple-reopen','apple-reopen.txt','run-board.log'):
    f=P/name
    if f.exists():f.rename(P/(name+'-before-resume-budget'))
print('Only final diagnostic resume budget updated',flush=True)
