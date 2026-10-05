#!/usr/bin/env python3
"""Build/verify recursive, reproducible dashboard distributions (no user state)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ALLOWED={'.py','.qml','.qmltypes','.js','.json','.sh','.html','.base64','.ttf','.otf','.png','.svg','.webp','.jpg','.jpeg','.txt','.md'}

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
        if not diagnostics and relative.parts[:3] == ('fixtures','theme-runtime','renderers'):continue
        if path.name=='release-manifest.json' or path.name=='README.md' and len(relative.parts)==1 or path.suffix=='.pyc':continue
        if path.suffix in ALLOWED or path.name in ('qmldir','LICENSE','smartpc-theme') or path.resolve() in declared:yield path,relative

def digest(file):return hashlib.sha256(file.read_bytes()).hexdigest()

def build(source,output,diagnostics=False):
    if output.exists():raise ValueError('Output già esistente')
    output.mkdir(parents=True)
    manifest={}
    for path,relative in files(source,diagnostics):
        destination=output/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
        manifest[str(relative)]=digest(destination)
    sys.path.insert(0,str(source));from version import VERSION
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True))
    (output/'release-manifest.json').write_text(json.dumps({'version':VERSION,'gitCommit':commit,'dirty':dirty,'distributionKind':'diagnostic' if diagnostics else 'runtime','sha256':manifest},indent=2)+'\n')
    (output/'run.sh').chmod(0o755)
    if (output/'smartpc-theme').exists(): (output/'smartpc-theme').chmod(0o755)
    verify(output)

def verify(root):
    manifest=json.loads((root/'release-manifest.json').read_text())
    if manifest.get('distributionKind') != 'diagnostic' and (root/'fixtures/theme-runtime/renderers').exists():
        raise ValueError('Diagnostic renderers present in runtime distribution')
    actual={str(rel):digest(path) for path,rel in files(root,manifest.get("distributionKind")=="diagnostic")}
    if actual!=manifest['sha256']:
        raise ValueError('Manifest differente: '+str(sorted(k for k in set(actual)|set(manifest['sha256']) if actual.get(k)!=manifest['sha256'].get(k))))
    print(json.dumps({'version':manifest['version'],'files':len(actual),'verified':True}))

parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
a=commands.add_parser('build');a.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]/'dashboard');a.add_argument('--output',type=Path,required=True);a.add_argument('--diagnostics',action='store_true')
a=commands.add_parser('verify');a.add_argument('directory',type=Path)
args=parser.parse_args()
if args.command=='build':build(args.source.resolve(),args.output.resolve(),args.diagnostics)
else:verify(args.directory.resolve())
