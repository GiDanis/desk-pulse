"""Read-only schema-1 authoring, structured diagnostics and generated AI kit."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
import sys

from theme_core import ROOT,FIELDS,ThemeCatalog,ThemeError,contrast,read_json
from theme_transfer import ProbeUnavailable,local_probe


def pointer(*parts):
    return ''.join('/'+str(part).replace('~','~0').replace('/','~1') for part in parts)


def registries(catalog):
    return {name:getattr(catalog,name) for name in ('contract','presentations','recipes','icon_sets','icon_renderers','scene_renderers')}


def registry_fingerprint(catalog):
    return hashlib.sha256(json.dumps(registries(catalog),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def read_profile(path):
    path=Path(path)
    if path.stat().st_size>2*1024*1024:raise ThemeError('profile','profilo troppo grande')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('chiave duplicata')
            result[key]=value
        return result
    result=json.loads(path.read_text(),object_pairs_hook=unique)
    if not isinstance(result,dict) or type(result.get('profileVersion')) is not int or result.get('profileVersion')!=1 or result.get('profileKind')!='schema1':
        raise ThemeError('profile','versione/profilo non supportato')
    if not isinstance(result.get('fontFamilies'),list) or not all(isinstance(v,str) for v in result['fontFamilies']):
        raise ThemeError('profile.fontFamilies','lista di famiglie richiesta')
    return result


def error_issue(error,*,file='theme.json',variant=None,phase='resolve',where=None):
    result={'code':'theme.validation','phase':phase,'file':str(file),'pointer':where or pointer(error.path),
            'path':error.path,'message':error.message}
    if variant is not None:result['variant']=variant
    return result


def token_origin(catalog,identifier,variant,role):
    chain=catalog.chain(identifier)
    for pack in reversed(chain):
        if role in pack.get('palettes',{}).get(variant,{}):
            return str(catalog.directories[pack['id']]/'theme.json'),pointer('palettes',variant,role)
        if role in pack.get('tokens',{}):return str(catalog.directories[pack['id']]/'theme.json'),pointer('tokens',role)
    inherited=catalog.contract.get(role,{}).get('inherit')
    if inherited:return token_origin(catalog,identifier,variant,inherited)
    return str(catalog.root/'themes/token-contract.json'),pointer('tokens',role,'default')


def contrast_suggestion(foreground,background,minimum):
    rgb=[int(foreground[i:i+2],16) for i in (1,3,5)];choices=[]
    for endpoint in (0,255):
        for amount in range(1,256):
            candidate='#'+''.join(f'{round(value+(endpoint-value)*amount/255):02x}' for value in rgb)
            if contrast(candidate,background)>=minimum:
                distance=sum((int(candidate[i:i+2],16)-value)**2 for i,value in zip((1,3,5),rgb))
                choices.append((distance,candidate));break
    if not choices:return None
    value=min(choices)[1]
    return {'value':value,'ratio':contrast(value,background),'scope':'pairOnly','requiresRevalidation':True}


def semantic_colors(root):
    file=Path(root)/'themes/SemanticStyle.qml'
    if not file.is_file():return {}
    return dict(re.findall(r'readonly property color (\w+): "(#[0-9a-fA-F]{6})"',file.read_text()))


def check_project(source,*,store=None,root=ROOT,profile=None,qt=False,qt_python=None):
    source=Path(source).expanduser()
    file=source/'theme.json' if source.is_dir() else source
    report={'reportVersion':1,'operation':'check','profile':'schema1','status':'valid',
            'verification':{'schema':'notVerified','resolvedTheme':'notVerified','qtResources':'notVerified','boardRuntime':'notVerified'},
            'issues':[],'warnings':[],'source':str(file.resolve())}
    issues=report['issues'];snapshots=[]
    try:
        if file.is_symlink():raise ThemeError('theme.json','manifest link non supportato')
        pack=read_json(file);catalog=ThemeCatalog(store,root=root)
        if not isinstance(pack,dict):raise ThemeError('theme.json','oggetto richiesto')
        if profile is not None and profile.get('registryFingerprint')!=registry_fingerprint(catalog):
            raise ThemeError('profile','registri destinatario differenti: usare lo stesso runtime per il check')
        meta=deepcopy(pack)
        for field in sorted(set(pack)-FIELDS):
            issues.append(error_issue(ThemeError(field,'campo sconosciuto'),file=file,phase='schema',where=pointer(field)))
            meta.pop(field)
        if isinstance(meta.get('tokens',{}),dict):meta['tokens']={}
        if isinstance(meta.get('palettes',{}),dict):
            meta['palettes']={v:{} if isinstance(values,dict) else values for v,values in meta.get('palettes',{}).items()}
        try:catalog.validate_pack(meta)
        except ThemeError as error:issues.append(error_issue(error,file=file,phase='schema'))
        layers=[('tokens',pack.get('tokens',{}))]
        if isinstance(pack.get('palettes',{}),dict):layers += [('palettes/'+v,values) for v,values in pack.get('palettes',{}).items()]
        for layer,values in layers:
            if not isinstance(values,dict):continue
            for role,value in values.items():
                try:catalog.validate_tokens({role:value})
                except ThemeError as error:
                    issues.append(error_issue(error,file=file,phase='schema',where=pointer(*layer.split('/'),role)))
        motion_required=read_json(catalog.root/'themes/theme-pack.schema.json')['properties']['motion']['additionalProperties']['required']
        for event,recipe in pack.get('motion',{}).items() if isinstance(pack.get('motion',{}),dict) else []:
            if isinstance(recipe,dict):
                for field in motion_required:
                    if field not in recipe:
                        issues.append({'code':'motion.required','phase':'schema','file':str(file),'pointer':pointer('motion',event,field),'message':'campo motion obbligatorio mancante'})
        for index,asset in enumerate(pack.get('assets',[])) if isinstance(pack.get('assets',[]),list) else []:
            if isinstance(asset,dict) and isinstance(asset.get('path'),str) and Path(asset['path']).is_absolute():
                issues.append({'code':'asset.relativePath','phase':'schema','file':str(file),'pointer':pointer('assets',index,'path'),'message':'percorso risorsa relativo richiesto'})
        if issues:
            report['verification']['schema']='failed'
        else:
            report['verification']['schema']='verified'
            identifier=pack['id'];report['id']=identifier;report['version']=pack['version']
            if identifier in catalog.packs and catalog.directories[identifier].resolve()!=file.parent.resolve():
                raise ThemeError('id','ID già presente nel destinatario; usare un nuovo ID schema 1')
            catalog.packs[identifier]=pack;catalog.directories[identifier]=file.parent.resolve()
            for variant in ('day','night'):
                try:
                    snapshot=catalog.resolve(identifier,variant=variant)
                    snapshots.append(snapshot)
                except ThemeError as error:
                    if getattr(error,'issues',None):
                        for detail in error.issues:
                            origin,location=token_origin(catalog,identifier,variant,detail['foregroundRole'])
                            background_file,background_pointer=token_origin(catalog,identifier,variant,detail['backgroundRole'])
                            suggestion=contrast_suggestion(detail['foreground'],detail['background'],detail['minimum'])
                            issues.append({**detail,'phase':'resolve','file':origin,'pointer':location,
                                           'variant':variant,'suggestion':suggestion,
                                           'backgroundSource':{'file':background_file,'pointer':background_pointer},
                                           'projectOverride':{'file':str(file),'pointer':pointer('palettes',variant,detail['foregroundRole'])}})
                    else:
                        where=None
                        if error.path in catalog.contract:
                            origin,where=token_origin(catalog,identifier,variant,error.path)
                        else:
                            origin=str(file)
                            for section in ('presentations','motion','scene','iconOverrides'):
                                for key in pack.get(section,{}) if isinstance(pack.get(section,{}),dict) else []:
                                    if error.path==section+'.'+key or error.path.startswith(section+'.'+key+'.'):
                                        where=pointer(section,key);break
                        issues.append(error_issue(error,file=origin,variant=variant,where=where))
            report['verification']['resolvedTheme']='failed' if issues else 'verified'
            report['coverage']=[{'variant':s['variant'],'presentations':s['presentations'],
                                  'newQmlIncluded':False,'scene':s['scene']} for s in snapshots]
            if profile:
                report['target']={'qtVersion':profile['qtVersion'],'registryFingerprint':profile['registryFingerprint'],
                                  'profileBackend':profile.get('probeBackend'),'runtimeVerified':False}
                families=set(profile['fontFamilies'])
                for snapshot in snapshots:
                    refs=[(key,value) for key,value in snapshot['tokens'].items() if key.endswith('Family')]
                    refs += [('icons.'+key,icon['family']) for key,icon in snapshot['icons'].items() if isinstance(icon,dict) and icon.get('backend')=='glyph']
                    for key,value in refs:
                        if value and not value.startswith('asset:') and value not in families:
                            issues.append(error_issue(ThemeError(key,'famiglia assente nel profilo destinatario: '+value),file=file,variant=snapshot['variant'],phase='profile'))
            # Detect known baseline light-palette risks without pretending the
            # semantic facade itself has been migrated (A1/G21).
            fixed=semantic_colors(root)
            usage={'warning':(('colors.background',4.5),('colors.backgroundOverlay',4.5),('colors.surface',4.5),('notifications.urgent.surface',3)),
                   'accountCritical':(('colors.background',4.5),('colors.surface',4.5)),
                   'critical':(('notifications.urgent.surface',3),),
                   'accentText':(('colors.background',4.5),('colors.backgroundOverlay',4.5),('colors.surface',4.5),('colors.surfaceFocused',4.5))}
            for snapshot in snapshots:
                colors={**fixed,'accentText':snapshot['tokens']['colors.accent']}
                for mode in ('small','large','urgent','badge','inbox','detail'):
                    role='notifications.'+mode+'.accent';colors[role]=snapshot['tokens'][role]
                    usage[role]=(('notifications.'+mode+'.surface',4.5),)
                for role,color in colors.items():
                    for surface,minimum in usage.get(role,()):
                        ratio=contrast(color,snapshot['tokens'][surface])
                        if ratio<minimum:
                            origin,location=(str(Path(root)/'themes/SemanticStyle.qml'),pointer(role)) if role in fixed else token_origin(catalog,identifier,snapshot['variant'],'colors.accent' if role=='accentText' else role)
                            issues.append({'code':'semantic.contrast','phase':'profile','file':origin,
                                           'pointer':location,'variant':snapshot['variant'],'foreground':color,
                                           'background':snapshot['tokens'][surface],'backgroundRole':surface,'ratio':ratio,'minimum':minimum,
                                           'message':'G21: ruolo informativo non leggibile sulla superficie effettiva; correggere il tema o usare variante supportata'})
            report['verification']['readability']='failed' if any(i['code']=='semantic.contrast' for i in issues) else 'verified'
            if qt and not issues:
                try:
                    checked=local_probe({'operation':'resources','snapshots':snapshots},qt_python or sys.executable)
                    report['verification']['qtResources']=checked['qtResources']
                    report['qtProbe']=checked['qtProbe']
                    issues += [error_issue(ThemeError(issue['path'],issue['message']),file=file,variant=issue['variant'],phase='qt') | {'code':issue['code']} for issue in checked['issues']]
                except ProbeUnavailable as error:
                    report['status']='notVerified'
                    report['warnings'].append({'code':'probe.unavailable','message':str(error)})
            report['warnings'].append({'code':'scope.runtime','message':'Layout QML, input, EGLFS e prestazioni richiedono fixture/runtime; il check non li certifica.'})
    except (ThemeError,OSError,ValueError,KeyError,TypeError) as error:
        issue=error if isinstance(error,ThemeError) else ThemeError('source',str(error))
        issues.append(error_issue(issue,file=file,phase='read' if report['verification']['schema']=='notVerified' else 'resolve'))
    if issues:report['status']='invalid'
    return report


def generated_schema(catalog):
    schema=read_json(catalog.root/'themes/theme-pack.schema.json')
    kinds={'color':'string','string':'string','bool':'boolean','int':'integer','real':'number'}
    properties={}
    for key,spec in catalog.contract.items():
        row={'type':kinds[spec['type']]}
        for name in ('default','minimum','maximum','enum'):
            if name in spec:row[name]=spec[name]
        if spec['type']=='color':row['pattern']='^#[0-9a-fA-F]{6}$'
        if spec['type']=='string':row['maxLength']=120
        properties[key]=row
    tokens={'type':'object','properties':properties,'additionalProperties':False}
    schema['properties']['tokens']=tokens
    schema['properties']['palettes']={'type':'object','properties':{'day':deepcopy(tokens),'night':deepcopy(tokens)},'additionalProperties':False}
    return schema


def write_kit(destination,*,store=None,root=ROOT,profile=None):
    destination=Path(destination)
    if destination.exists():raise ThemeError('output','cartella kit già esistente')
    catalog=ThemeCatalog(store,root=root)
    if profile and profile.get('registryFingerprint')!=registry_fingerprint(catalog):raise ThemeError('profile','registri destinatario differenti')
    destination.mkdir(parents=True)
    try:
        data={'token-contract.json':{'tokens':catalog.contract},'theme-pack.schema.json':generated_schema(catalog),
              'registries.json':registries(catalog),'base.theme.json':catalog.packs['base']}
        if profile:data['target-profile.json']=profile
        else:data['target-profile.json']={'status':'notVerified','registryFingerprint':registry_fingerprint(catalog),'reason':'profilo Qt destinatario non acquisito'}
        for name,value in data.items():(destination/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        prompt='''Crea un tema SmartPC originale dal brief, usando gli allegati di questa cartella.
Profilo: schema 1 dichiarativo, stesso runtime Python/Qt Quick, display 960×640.
Restituisci un solo JSON valido. Non generare QML per questo profilo.
Usa chiavi piatte con punto in tokens e palettes.day/night, extends="base",
un nuovo id e version x.y.z. Non inventare campi, token o ID: usa il contratto
e i registry effettivi allegati. Mantieni stati dei dati, fonti e azioni invariati.
Progetta separatamente piccolo e grande e considera tutte le sei superfici alerts.
La prima prova usa famiglie "" e assets []; altrimenti font/asset devono essere
presenti e verificati nel profilo o dichiarati con hash e licenza nel progetto.
Motion: recipe, durationMs, distancePx, easing obbligatori, ricette/eventi compatibili;
urgent.present immediato builtin.cut, durationMs=0, distancePx=0.
Mantieni Home dinamica senza scheda evento vuota. Nessuna telemetria inventata.
Usa varianti leggibili: le palette chiare sono limitate da G21 nel runtime attuale.
Nessuna attribuzione biologica alla palette notte. I cinque concept sono spunti.
Esegui theme_pack.py check --format json, correggi gli errori riportati e ripeti.
Non stimare i contrasti a vista e non dichiarare verificato ciò che il report non prova.
Trasferisci solo dopo check: install riceve nella inbox, non applica il tema.
Visuali nuovi, bundle e API 2 appartengono al percorso successivo e non sono disponibili.

BRIEF: [direzione estetica e preferenze della persona]
DIAGNOSTICA: [report da correggere, se presente]
'''
        (destination/'PROMPT.md').write_text(prompt)
        (destination/'README.md').write_text('Kit AI schema 1 generato dai registri effettivi.\n\n'
            'Il resolver è autoritativo: lo schema JSON non verifica contrasti, risorse o layout.\n'
            'Usare check --profile target-profile.json soltanto con un profilo Qt acquisito.\n'
            'Install prepara theme-imports; scegliere Importa e Applica dalle impostazioni.\n'
            'Controlli PC/offscreen e runtime EGLFS sono livelli distinti. Nessun nuovo QML incluso.\n')
    except Exception:
        import shutil
        shutil.rmtree(destination);raise
    return {'reportVersion':1,'operation':'kit','status':'created','destination':str(destination.resolve()),
            'profile':'schema1','registryFingerprint':registry_fingerprint(catalog),'targetProfileVerified':profile is not None}
