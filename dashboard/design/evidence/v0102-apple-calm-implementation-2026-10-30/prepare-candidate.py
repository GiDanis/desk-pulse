"""Derive the candidate from the verified board bytes, not the dirty checkout."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
E=Path(__file__).resolve().parent;ROOT=E.parents[3];S=E/'candidate-source';D=S/'dashboard'
assert not S.exists(), 'Use a fresh candidate directory after any new source changes'
S.mkdir();D.mkdir()
with tarfile.open(E/'before/board-runtime.tar.gz','r:gz') as archive:archive.extractall(D,filter='data')
before=json.loads((E/'before/source-hashes.json').read_text());baseline=json.loads((E/'before/board-manifest.json').read_text());delta=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for key,old in before.items():
 if not key.startswith('dashboard/'):continue
 p=ROOT/key;name=key.removeprefix('dashboard/')
 if not p.is_file() or digest(p)==old:continue
 if p.name.startswith(('check_','verify_')):continue
 assert name in baseline['sha256'], 'Explicit review required for runtime addition: '+name
 target=D/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);delta.append(name)
# Diagnostic-only sources remain outside the production package.
for p in (ROOT/'dashboard').glob('check_*.py'):shutil.copy2(p,D/p.name)
for p in (ROOT/'dashboard').glob('verify_*.py'):shutil.copy2(p,D/p.name)
shutil.copytree(ROOT/'dashboard/fixtures/theme-runtime/renderers',D/'fixtures/theme-runtime/renderers',dirs_exist_ok=True)
shutil.copytree(ROOT/'theme-projects/apple-calm',S/'theme-projects/apple-calm',ignore=shutil.ignore_patterns('evidence','__pycache__'))
shutil.copytree(ROOT/'scripts',S/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
(S/'theme-projects/apple-calm/evidence').mkdir()
# Only an exact digest+Qt receipt may be reused locally. ARM deletes this cache
# and performs its own native preflight before any EGLFS acceptance.
cache=ROOT/'theme-projects/apple-calm/evidence/preflight-cache.json'
if cache.exists():shutil.copy2(cache,S/'theme-projects/apple-calm/evidence/preflight-cache.json')
subprocess.run(['python3',str(ROOT/'scripts/package-dashboard.py'),'build','--source',str(D),'--output',str(E/'runtime'),'--baseline-manifest',str(E/'before/board-manifest.json')],check=True)
new=json.loads((E/'runtime/release-manifest.json').read_text())
for name,h in baseline['sha256'].items():
 if name not in delta:assert new['sha256'][name]==h,name
assert all(new['sha256'][name]==h for name,h in baseline['sha256'].items() if name.startswith('game') or name.endswith('.so'))
shutil.copy2(E/'runtime/release-manifest.json',D/'release-manifest.json')
receipt={'status':'prepared','version':new['version'],'baselineVersion':baseline['version'],'baselineManifestSha256':digest(E/'before/board-manifest.json'),'runtimeManifestSha256':digest(E/'runtime/release-manifest.json'),'changedRuntimeFiles':sorted(delta),'runtimeFiles':len(new['sha256']),'gameAndNativeLibrariesPreserved':True}
(E/'candidate.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
