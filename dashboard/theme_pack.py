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
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'bundle':
        from theme_bundle_tools import main as bundle_main
        return bundle_main(sys.argv[2:])
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',type=Path)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('list'); commands.add_parser('validate')
    install=commands.add_parser('import');install.add_argument('directory',type=Path)
    export=commands.add_parser('export');export.add_argument('theme');export.add_argument('directory',type=Path);export.add_argument('--id',required=True);export.add_argument('--overrides',type=Path)
    for name in ('check','install','profile','kit'):
        command=commands.add_parser(name)
        command.add_argument('--store',type=Path,default=argparse.SUPPRESS)
        command.add_argument('--format',choices=('text','json'),default='text')
        command.add_argument('--qt-python',default=__import__('sys').executable)
        if name in ('check','install'):command.add_argument('source',type=Path)
        if name in ('check','install','kit'):command.add_argument('--profile',type=Path)
        if name in ('check','install'):command.add_argument('--qt',action='store_true')
        if name in ('install','profile','kit'):
            command.add_argument('--board');command.add_argument('--identity',type=Path)
        if name in ('profile','kit'):command.add_argument('--output',type=Path,required=name=='kit')
        if name=='kit':command.add_argument('--bundle',action='store_true',help='Esporta SDK completo API2 e bundle; schema1 resta il default')
    args=parser.parse_args()
    if args.command in ('check','install','profile','kit'):
        if getattr(args,'board',None) and (args.store or getattr(args,'profile',None)):
            parser.error('--board non può essere combinato con --store o --profile')
        return authoring_command(args)
    if args.store is None:parser.error('--store è obbligatorio per list/validate/import/export')
    try:
        catalog=ThemeCatalog(args.store)
        if args.command=='import': print(import_pack(args.directory,args.store))
        elif args.command=='export': export_pack(catalog,args.theme,args.directory,new_id=args.id,overrides=read_json(args.overrides) if args.overrides else None);print(args.directory)
        else:
            print(json.dumps({'themes':list(catalog.packs),'errors':catalog.errors},ensure_ascii=False,indent=2))
            if args.command=='validate' and catalog.errors: return 1
    except (ThemeError,OSError) as error: parser.exit(1,str(error)+'\n')
    return 0


def authoring_command(args):
    import sys
    from theme_authoring import check_project,read_profile,write_kit
    from theme_core import ROOT
    from theme_probe import store_path
    from theme_transfer import BoardTransport,ProbeUnavailable,install_board,install_local,local_probe
    try:
        store=store_path(args.store)
        profile=read_profile(args.profile) if getattr(args,'profile',None) else None
        transport=None
        if getattr(args,'board',None):
            transport=BoardTransport(args.board,args.identity);profile=transport.profile()
        if args.command=='profile':
            profile=profile or local_probe({'operation':'profile','root':str(ROOT),'store':str(store)},args.qt_python)
            report={'reportVersion':1,'operation':'profile','status':'created','profile':profile}
            if args.output:
                if args.output.exists():raise ThemeError('output','profilo già esistente; scegliere un nuovo file')
                args.output.parent.mkdir(parents=True,exist_ok=True)
                with args.output.open('x') as output:output.write(json.dumps(profile,ensure_ascii=False,indent=2)+'\n')
                report={'reportVersion':1,'operation':'profile','status':'created','destination':str(args.output.resolve()),
                        'qtVersion':profile['qtVersion'],'verification':profile['verification']}
        elif args.command=='kit':
            if args.bundle:
                from theme_bundle_tools import write_full_kit
                args.output.parent.mkdir(parents=True,exist_ok=True)
                report=write_full_kit(args.output,profile=profile)
            else:report=write_kit(args.output,store=None if transport else store,profile=profile)
        else:
            report=check_project(args.source,store=None if transport else store,profile=profile,qt=args.qt,qt_python=args.qt_python)
            if args.command=='install' and report['status']=='valid':
                if not args.source.is_dir():raise ThemeError('source','install richiede una cartella contenente theme.json')
                qt_details={}
                def verify_payload(path):
                    checked=check_project(path,store=None if transport else store,profile=profile,qt=args.qt,qt_python=args.qt_python)
                    if checked['status']!='valid':raise ThemeError('staging',json.dumps(checked['issues'],ensure_ascii=False))
                    qt_details.update(checked.get('qtProbe',{}))
                receipt=install_board(args.source,transport,profile,verify=verify_payload) if transport else install_local(args.source,store,ROOT,verify_qt=False,verify=verify_payload)
                report={'reportVersion':1,'operation':'install',**receipt}
                if not transport and args.qt:
                    report['verification']['qtResources']='verified';report['qtProbe']=qt_details
            elif args.command=='install':report['operation']='install'
    except ProbeUnavailable as error:
        report={'reportVersion':1,'operation':args.command,'status':'failed' if args.command=='install' else 'notVerified',
                'issues':[{'code':'probe.unavailable','phase':'probe','message':str(error)}]}
    except (ThemeError,OSError,ValueError,KeyError,TypeError) as error:
        report={'reportVersion':1,'operation':args.command,'status':'invalid',
                'issues':[{'code':'operation.failed','phase':'operation','message':str(error)}]}
    if args.format=='json':print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    else:
        print(args.command+': '+report['status'])
        if report.get('destination'):print('Destinazione: '+report['destination'])
        if report.get('id'):print('Tema: '+report['id'])
        if report.get('digest'):print('SHA payload: '+report['digest'])
        for scope,result in report.get('verification',{}).items():print(scope+': '+result)
        if args.command=='profile' and 'profile' in report:print(json.dumps(report['profile'],ensure_ascii=False,indent=2))
        for issue in report.get('issues',[])+report.get('warnings',[]):
            print('['+issue.get('code','error')+'] '+issue.get('variant','')+' '+issue.get('file','')+' '+issue.get('pointer','')+' '+issue['message'])
            if 'ratio' in issue:print(f"  Contrasto {issue['ratio']:.3f}:1; minimo {issue['minimum']}:1")
            if issue.get('suggestion'):print('  Candidato (coppia soltanto, rivalidare): '+issue['suggestion']['value'])
    return 1 if report['status'] in ('invalid','failed') else 2 if report['status']=='notVerified' else 0


if __name__=='__main__':raise SystemExit(main())
