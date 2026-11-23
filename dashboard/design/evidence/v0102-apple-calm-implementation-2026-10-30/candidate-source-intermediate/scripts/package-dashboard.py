#!/usr/bin/env python3
"""Build/verify recursive, reproducible dashboard distributions (no user state)."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ALLOWED={'.fishmesh','.py','.qml','.qmltypes','.js','.json','.sh','.html','.base64','.ttf','.otf','.png','.svg','.webp','.jpg','.jpeg','.txt','.md'}

def diagnostic_only(relative):
    return (relative.parts[:3] == ('fixtures','theme-runtime','renderers') or
            len(relative.parts)==1 and relative.suffix=='.py' and
            relative.name.startswith(('check_','verify_')))

def files(root, diagnostics=False):
    # A declared data resource can use an engine-specific extension (rig, atlas,
    # shader, etc.). Packaging must not silently discard a validated asset.
    declared=set()
    for manifest_file in root.rglob('theme.json'):
        for asset in json.loads(manifest_file.read_text()).get('assets',[]):
            candidate=(manifest_file.parent/asset['path']).resolve()
            if not candidate.is_relative_to(manifest_file.parent.resolve()): raise ValueError('Asset outside its pack')
            declared.add(candidate)
    for manifest_file in root.rglob('bundle.json'):
        for resource in json.loads(manifest_file.read_text()).get('resources',[]):
            candidate=(manifest_file.parent/resource['path']).resolve()
            if not candidate.is_relative_to(manifest_file.parent.resolve()): raise ValueError('Resource outside its bundle')
            declared.add(candidate)
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if not path.is_file() or any(x in ('__pycache__','design','.git') or x.startswith('.') for x in relative.parts):continue
        if not diagnostics and diagnostic_only(relative):continue
        if path.name=='release-manifest.json' or path.name=='README.md' and len(relative.parts)==1 or path.suffix=='.pyc':continue
        if relative.as_posix() in ('resources/iliadbox-ca.pem','game_native.c','libsmartpc_game_native.so','egl_context_bridge.c','libsmartpc_egl_context_bridge.so') or path.suffix in ALLOWED or path.name in ('qmldir','LICENSE','smartpc-theme') or path.resolve() in declared:yield path,relative

def digest(file):return hashlib.sha256(file.read_bytes()).hexdigest()

def build(source,output,diagnostics=False,baseline_manifest=None,add_files=()):
    if output.exists():raise ValueError('Output già esistente')
    additions=set(add_files)
    if additions and baseline_manifest is None:raise ValueError('Le aggiunte esplicite richiedono una baseline')
    for name in additions:
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or path.as_posix()!=name or not (source/path).resolve().is_relative_to(source.resolve()):
            raise ValueError('Aggiunta fuori dalla sorgente: '+name)
    selected=list(files(source,diagnostics))
    baseline=None
    if baseline_manifest is not None:
        baseline=json.loads(baseline_manifest.read_text())
        expected=set(baseline['sha256'])
        if not diagnostics:expected={name for name in expected if not diagnostic_only(Path(name))}
        expected.update(additions)
        selected=[(path,relative) for path,relative in selected if relative.as_posix() in expected or
                  diagnostics and relative.parts[:3] == ('fixtures','theme-runtime','renderers')]
        missing=expected-{relative.as_posix() for _,relative in selected}
        if missing:raise ValueError('File della baseline mancanti: '+str(sorted(missing)))
    output.mkdir(parents=True)
    manifest={}
    for path,relative in selected:
        destination=output/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
        manifest[str(relative)]=digest(destination)
    version=next(ast.literal_eval(node.value) for node in ast.parse((source/'version.py').read_text()).body
                 if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='VERSION' for target in node.targets))
    checkout=Path(__file__).resolve().parents[1]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=checkout,text=True))
    metadata={'version':version,'gitCommit':commit,'dirty':dirty,'distributionKind':'diagnostic' if diagnostics else 'runtime','packagingVersion':2,'sha256':manifest}
    if baseline is not None:
        metadata['sourceBaseline']={'version':baseline['version'],'manifestSha256':digest(baseline_manifest)}
        if additions:metadata['explicitAddedFiles']=sorted(additions-set(baseline['sha256']))
    (output/'release-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (output/'run.sh').chmod(0o755)
    if (output/'smartpc-theme').exists(): (output/'smartpc-theme').chmod(0o755)
    verify(output)

def verify(root):
    manifest=json.loads((root/'release-manifest.json').read_text())
    if manifest.get('distributionKind') != 'diagnostic':
        unexpected=[str(path.relative_to(root)) for path in root.rglob('*') if path.is_file() and diagnostic_only(path.relative_to(root))]
        if unexpected:raise ValueError('File diagnostici nella distribuzione runtime: '+str(sorted(unexpected)))
    actual={str(rel):digest(path) for path,rel in files(root,manifest.get("distributionKind")=="diagnostic")}
    if actual!=manifest['sha256']:
        raise ValueError('Manifest differente: '+str(sorted(k for k in set(actual)|set(manifest['sha256']) if actual.get(k)!=manifest['sha256'].get(k))))
    print(json.dumps({'version':manifest['version'],'files':len(actual),'verified':True}))

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    a=commands.add_parser('build');a.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]/'dashboard');a.add_argument('--output',type=Path,required=True);a.add_argument('--diagnostics',action='store_true')
    a.add_argument('--baseline-manifest',type=Path,help='Limit a maintenance build to files from an installed release')
    a.add_argument('--add-file',action='append',default=[],help='Explicit relative addition to the baseline; repeat for each new runtime file')
    a=commands.add_parser('verify');a.add_argument('directory',type=Path)
    args=parser.parse_args()
    if args.command=='build':build(args.source.resolve(),args.output.resolve(),args.diagnostics,args.baseline_manifest,args.add_file)
    else:verify(args.directory.resolve())

if __name__=='__main__':main()
