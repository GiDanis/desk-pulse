from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
E=Path(__file__).resolve().parent;ROOT=E.parents[3];S=E/'candidate-source';D=S/'dashboard';before=json.loads((E/'before/source-hashes.json').read_text());base=json.loads((E/'before/board-manifest.json').read_text());delta=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
changed_source=[]
for key,old in before.items():
 if not key.startswith('dashboard/'):continue
 p=ROOT/key;name=key.removeprefix('dashboard/')
 if not p.is_file() or sha(p)==old or p.name.startswith(('check_','verify_')):continue
 assert name in base['sha256'],name
 shutil.copy2(p,D/name);delta.append(name);changed_source.append(Path('candidate-source/dashboard')/name)
for name in ['verify_main.py','verify_readability.py']:
 rel=Path('theme-projects/apple-calm/tools')/name;shutil.copy2(ROOT/rel,S/rel);changed_source.append(Path('candidate-source')/rel)
for name in ['check-dashboard.py','benchmark-calm-motion.py']:
 shutil.copy2(ROOT/'scripts'/name,S/'scripts'/name);changed_source.append(Path('candidate-source/scripts')/name)
(E/'runtime').rename(E/'runtime-generation1')
subprocess.run(['python3',str(ROOT/'scripts/package-dashboard.py'),'build','--source',str(D),'--output',str(E/'runtime'),'--baseline-manifest',str(E/'before/board-manifest.json')],check=True)
new=json.loads((E/'runtime/release-manifest.json').read_text())
assert all(new['sha256'][n]==h for n,h in base['sha256'].items() if n.startswith('game') or n.endswith('.so'))
assert all(new['sha256'][n]==h for n,h in base['sha256'].items() if n not in delta)
shutil.copy2(E/'runtime/release-manifest.json',D/'release-manifest.json');changed_source.append(Path('candidate-source/dashboard/release-manifest.json'))
shutil.copy2(E/'candidate.json',E/'candidate-generation1.json')
receipt={'status':'prepared','generation':2,'version':new['version'],'baselineVersion':base['version'],'baselineManifestSha256':sha(E/'before/board-manifest.json'),'runtimeManifestSha256':sha(E/'runtime/release-manifest.json'),'changedRuntimeFiles':sorted(delta),'runtimeFiles':len(new['sha256']),'gameAndNativeLibrariesPreserved':True}
(E/'candidate.json').write_text(json.dumps(receipt,indent=2)+'\n')
with tarfile.open(E/'candidate-refresh.tar.gz','w:gz') as archive:
 for p in changed_source:archive.add(E/p,arcname=str(p))
 for name in ['runtime','candidate.json']:archive.add(E/name,arcname=name)
print(json.dumps({'candidate':receipt,'archiveSha256':sha(E/'candidate-refresh.tar.gz')}))
