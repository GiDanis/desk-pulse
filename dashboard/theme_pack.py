"""Validated local data-pack import/export. No QML is executed from a theme pack."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
from theme_core import ThemeCatalog, ThemeError, contained, read_json


def import_pack(source, destination, *, root=None):
    source=Path(source).resolve(); destination=Path(destination).resolve()
    arguments={'root':root} if root else {}
    manifest=read_json(source/'theme.json')
    catalog=ThemeCatalog(destination,**arguments); catalog.validate_pack(manifest)
    identifier=manifest['id']
    if identifier in catalog.packs: raise ThemeError('id','pacchetto già presente; usare un nuovo ID/versione')
    destination.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.import-',dir=destination))
    try:
        output=staging/identifier; output.mkdir()
        for asset in manifest.get('assets',[]):
            path=contained(source,asset.get('path',''))
            target=contained(output,asset.get('path',''))
            if not path.is_file(): raise ThemeError('assets','risorsa mancante')
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)
        (output/'theme.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        # Validate against installed parents/registries before any visible mutation.
        catalog.packs[identifier]=manifest; catalog.directories[identifier]=output
        for variant in ('day','night'): catalog.resolve(identifier,variant=variant)
        output.rename(destination/identifier)
    finally: shutil.rmtree(staging,ignore_errors=True)
    return identifier


def export_pack(catalog, identifier, destination, *, new_id, overrides=None):
    destination=Path(destination)
    if destination.exists(): raise ThemeError('destination','cartella già esistente')
    day=catalog.resolve(identifier,overrides,variant='day'); night=catalog.resolve(identifier,overrides,variant='night')
    pack={'schemaVersion':1,'id':new_id,'name':'Personalizzazione '+new_id,'version':'1.0.0',
          'tokens':day['tokens'],'palettes':{'night':{k:v for k,v in night['tokens'].items() if day['tokens'][k]!=v}},
          'presentations':day['presentations'],'motion':day['motion'],'scene':day['scene'],
          'iconSetId':day['iconSetId'],'iconApiVersion':1,'iconOverrides':day['icons'],'assets':[]}
    catalog.validate_pack(pack)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.export-',dir=destination.parent))
    try:
        for asset in day['assets']:
            descriptor={k:v for k,v in asset.items() if k!='file'}
            descriptor['path']='assets/'+asset['id']+Path(asset['file']).suffix
            target=contained(temporary,descriptor['path']); target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(asset['file'],target); pack['assets'].append(descriptor)
        (temporary/'theme.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n')
        candidate=deepcopy(catalog.packs); catalog.packs[new_id]=pack; old_dir=catalog.directories.get(new_id);catalog.directories[new_id]=temporary
        try:
            for variant in ('day','night'):catalog.resolve(new_id,variant=variant)
        finally:
            catalog.packs=candidate
            if old_dir:catalog.directories[new_id]=old_dir
            else:catalog.directories.pop(new_id,None)
        temporary.rename(destination)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return pack


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',type=Path,required=True)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('list'); commands.add_parser('validate')
    install=commands.add_parser('import');install.add_argument('directory',type=Path)
    export=commands.add_parser('export');export.add_argument('theme');export.add_argument('directory',type=Path);export.add_argument('--id',required=True);export.add_argument('--overrides',type=Path)
    args=parser.parse_args()
    try:
        catalog=ThemeCatalog(args.store)
        if args.command=='import': print(import_pack(args.directory,args.store))
        elif args.command=='export': export_pack(catalog,args.theme,args.directory,new_id=args.id,overrides=read_json(args.overrides) if args.overrides else None);print(args.directory)
        else:
            print(json.dumps({'themes':list(catalog.packs),'errors':catalog.errors},ensure_ascii=False,indent=2))
            if args.command=='validate' and catalog.errors: return 1
    except (ThemeError,OSError) as error: parser.exit(1,str(error)+'\n')
    return 0

if __name__=='__main__':raise SystemExit(main())
