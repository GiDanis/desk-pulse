"""Assemble Aquarium-only delta on verified installed0.10.1 runtime."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
P=Path('/home/giuseppe/.cache/smartpc-aquarium3d-install-20261029');S=Path('dashboard');B=P/'baseline/dashboard';A=P/'assembly/dashboard';E=Path('dashboard/design/evidence/v010-aquarium-3d-install-2026-10-29')
m=json.loads((B/'release-manifest.json').read_text());assert all(hashlib.sha256((B/f).read_bytes()).hexdigest()==v for f,v in m['sha256'].items())
existing=['Main.qml','aquarium.py','aquarium_catalog.py','presentations/registry.json','qml/SmartPC/ThemeApi/runtime.qmltypes','run.sh','theme_bundle.py','theme_fixture_support.py','themes/packs/base/theme.json','themes/packs/functional/theme.json','fixtures/theme-runtime/README.md','fixtures/theme-runtime/catalog.json','fixtures/theme-runtime/domains/context-structural.json']
existing += [str(f.relative_to(S)) for f in (S/'theme-api').rglob('*') if f.is_file() and str(f.relative_to(S)) in m['sha256']]
new=['aquarium_geometry.py','aquarium_population.py','aquarium_rotation.py','aquarium_store.py','presentations/aquarium-3d.qml','presentations/aquarium-manage.qml','presentations/aquarium/Aquarium3DVisual.qml','presentations/aquarium/Fish3DActor.qml','fixtures/theme-runtime/scenarios/aquarium.3d--normal.json','fixtures/theme-runtime/scenarios/aquarium.manage--normal.json']
new += [str(f.relative_to(S)) for f in (S/'assets/aquarium/calm-3d-v1').iterdir() if f.is_file()]
assert not A.exists();shutil.copytree(B,A)
for name in existing+new:
 out=A/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(S/name,out)
(S/'version.py').write_text((S/'version.py').read_text().replace("0.10.1-rc.1","0.10.2-rc.1"));shutil.copy2(S/'version.py',A/'version.py')
selection=dict(m);selection['sha256']={**m['sha256'],**{f:hashlib.sha256((A/f).read_bytes()).hexdigest() for f in new}};(P/'selection-manifest.json').write_text(json.dumps(selection,indent=2)+'\n')
subprocess.run(['python3','scripts/package-dashboard.py','build','--source',str(A),'--output',str(P/'runtime'),'--baseline-manifest',str(P/'selection-manifest.json')],check=True)
r=P/'runtime';final=json.loads((r/'release-manifest.json').read_text());final['sourceBaseline']={'version':m['version'],'manifestSha256':hashlib.sha256((B/'release-manifest.json').read_bytes()).hexdigest()};(r/'release-manifest.json').write_text(json.dumps(final,indent=2)+'\n')
changed=sorted(f for f,v in final['sha256'].items() if f in m['sha256'] and v!=m['sha256'][f]);added=sorted(set(final['sha256'])-set(m['sha256']));removed=sorted(set(m['sha256'])-set(final['sha256']))
assert set(changed)<=set(existing+['version.py']) and set(added)==set(new) and not removed
assert all(final['sha256'][f]==v for f,v in m['sha256'].items() if f.startswith('game') or f=='libsmartpc_game_native.so')
report={'version':final['version'],'baselineVersion':m['version'],'baselineManifestSha256':final['sourceBaseline']['manifestSha256'],'runtimeManifestSha256':hashlib.sha256((r/'release-manifest.json').read_bytes()).hexdigest(),'runtimeFiles':len(final['sha256']),'changed':changed,'added':added,'removed':removed,'gameCodeAndNativeLibraryUnchanged':True}
(E/'release-delta.json').write_text(json.dumps(report,indent=2)+'\n');(E/'release-manifest.json').write_bytes((r/'release-manifest.json').read_bytes())
for name in ['check_aquarium_population.py','check_theme_api_contract.py','check_theme_api_adapters.py','check_theme_api_runtime.py','check_theme_core.py','check_theme_runtime_fixtures.py']:
 shutil.copy2(S/name,A/name)
subprocess.run(['python3','scripts/package-dashboard.py','build','--source',str(A),'--output',str(P/'source/dashboard'),'--diagnostics'],check=True)
print(json.dumps(report,indent=2))
