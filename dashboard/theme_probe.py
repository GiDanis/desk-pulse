"""Isolated authoring probe and receiver. Never constructs application services."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys


def payload_digest(directory):
    rows=[]
    for path in sorted(Path(directory).rglob('*')):
        if path.is_symlink(): raise ValueError('link nel payload')
        if path.is_file():
            rows.append([path.relative_to(directory).as_posix(),hashlib.sha256(path.read_bytes()).hexdigest()])
    return hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def service_context():
    """Use the running kiosk's paths, not the SSH login's HOME or Qt backend."""
    result=subprocess.run(['systemctl','show','smartpc-dashboard.service','-p','MainPID','-p','User'],
                          capture_output=True,text=True,check=True,timeout=10)
    properties=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    pid=int(properties.get('MainPID','0'))
    if pid<=0: raise ValueError('servizio non attivo: profilo del destinatario indisponibile')
    environ=dict(item.split(b'=',1) for item in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in item)
    for key in ('HOME','XDG_DATA_HOME','XDG_CONFIG_HOME','SMARTPC_THEME_STORE'):
        value=environ.get(key.encode())
        if value is not None: os.environ[key]=value.decode()
        else: os.environ.pop(key,None)
    arguments=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0')
    script=next((Path(value) for value in arguments if value.endswith('/app.py')),None)
    if not script: raise ValueError('root dashboard non individuabile dal servizio')
    return script.parent,properties.get('User'),pid


def qt_application():
    os.environ['QT_QPA_PLATFORM']='offscreen'
    from PySide6.QtGui import QGuiApplication
    app=QGuiApplication.instance() or QGuiApplication([])
    app.setOrganizationName('SmartPC');app.setApplicationName('SmartPC')
    return app


def store_path(explicit=None):
    if explicit or os.environ.get('SMARTPC_THEME_STORE'):
        return Path(explicit or os.environ['SMARTPC_THEME_STORE']).expanduser().resolve()
    # Same fixed organization/application as app.py, without requiring Qt for
    # pure Linux checks. Qt profile verifies this default independently.
    data=os.environ.get('XDG_DATA_HOME','')
    base=Path(data) if data and Path(data).is_absolute() else Path.home()/'.local/share'
    return (base/'SmartPC/SmartPC/themes').resolve()


def profile(root,store,service=None):
    sys.path.insert(0,str(root))
    from theme_core import ThemeCatalog
    from PySide6.QtCore import QStandardPaths,qVersion
    from PySide6.QtGui import QFontDatabase
    import PySide6
    app=qt_application()
    catalog=ThemeCatalog(store,root=root)
    registries={name:getattr(catalog,name) for name in ('contract','presentations','recipes','icon_sets','icon_renderers','scene_renderers')}
    fingerprint=hashlib.sha256(json.dumps(registries,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    from datetime import datetime,timezone
    import platform
    api = {'availability': 'unavailable', 'apiFingerprint': None, 'runtimeModuleVerified': False}
    if (Path(root) / 'theme-api').exists():
        from theme_api_contract import api_metadata
        api = api_metadata(root)
    return {'profileVersion':1,'profileKind':'schema1','capturedAt':datetime.now(timezone.utc).isoformat(),
            'architecture':platform.machine(),'root':str(root),'store':str(store),
            'inbox':str(store.parent/'theme-imports'),'service':service,
            'display':{'width':960,'height':640},'qtVersion':qVersion(),'pysideVersion':PySide6.__version__,
            'probeBackend':'offscreen','productionBackendVerified':False,
            'appDataLocation':QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation),
            'defaultFont':app.font().family(),'fontFamilies':sorted(QFontDatabase.families()),
            'registryFingerprint':fingerprint,'registries':registries,
            'apiFingerprint':api['apiFingerprint'],'themeApiContract':api,
            'installedThemes':[{'id':p['id'],'version':p['version']} for p in catalog.packs.values()],
            'limitations':['QML layouts/input/frames and EGLFS performance not verified by this probe',
                            'G21: adaptive semantic colors for light palettes pending'],
            'verification':{'qtProfile':'verified','boardRuntime':'notVerified'}}


def resource_probe(snapshots):
    from PySide6.QtCore import qVersion
    from PySide6.QtGui import QFontDatabase,QFont,QRawFont,QImageReader
    app=qt_application();registered={};issues=[]
    try:
        for snapshot in snapshots:
            variant=snapshot['variant'];replacements={};image_bytes=0
            assets={a['id']:a for a in snapshot['assets']}
            for asset in assets.values():
                if asset['type']=='image':
                    reader=QImageReader(asset['file']);size=reader.size()
                    estimated=size.width()*size.height()*4 if size.isValid() else 0
                    image_bytes+=estimated
                    if not reader.canRead() or not size.isValid() or image_bytes>24*1024*1024:
                        issues.append({'code':'resource.image','path':'assets.'+asset['id'],'variant':variant,'message':'immagine non leggibile o budget texture superato'})
                    elif reader.read().isNull():
                        issues.append({'code':'resource.image','path':'assets.'+asset['id'],'variant':variant,'message':'decodifica immagine fallita'})
            refs={value for key,value in snapshot['tokens'].items() if key.endswith('Family')}
            refs.update(icon['family'] for icon in snapshot['icons'].values() if isinstance(icon,dict) and icon.get('backend')=='glyph')
            for ref in refs:
                if not ref.startswith('asset:'):continue
                asset=assets.get(ref[6:])
                if not asset or asset['type']!='font':
                    issues.append({'code':'resource.font','path':ref,'variant':variant,'message':'asset font mancante'});continue
                digest=asset['sha256']
                if digest not in registered:
                    number=QFontDatabase.addApplicationFont(asset['file'])
                    registered[digest]=(number,QFontDatabase.applicationFontFamilies(number) if number>=0 else [])
                names=registered[digest][1]
                if not names:issues.append({'code':'resource.font','path':ref,'variant':variant,'message':'font non caricabile'})
                else:replacements[ref]=names[0]
            families=set(QFontDatabase.families())
            for key,value in snapshot['tokens'].items():
                if key.endswith('Family') and value and value not in replacements and value not in families:
                    issues.append({'code':'resource.font','path':key,'variant':variant,'message':'famiglia font non disponibile: '+value})
            for key,icon in snapshot['icons'].items():
                if not isinstance(icon,dict) or icon.get('backend')!='glyph':continue
                family=replacements.get(icon['family'],icon['family'])
                if family not in families or not QRawFont.fromFont(QFont(family)).supportsCharacter(ord(icon['glyph'])):
                    issues.append({'code':'resource.glyph','path':'icons.'+key,'variant':variant,'message':'famiglia o glifo non disponibile'})
        return {'status':'invalid' if issues else 'valid','issues':issues,'qtResources':'failed' if issues else 'verified',
                'qtProbe':{'qtVersion':qVersion(),'backend':'offscreen','scope':'resource decode/fonts/glyphs; no QML rendering or board frame/performance proof'}}
    finally:
        for number,_ in registered.values():
            if number>=0:QFontDatabase.removeApplicationFont(number)


def receiver(request,root,store):
    """Only stage verified data packs. No import, preferences, restart or apply."""
    import fcntl
    sys.path.insert(0,str(root))
    from theme_core import ThemeCatalog,ID,contained,read_json
    inbox=store.parent/'theme-imports'
    ticket=request['ticket']
    if not ticket.startswith('.receive-') or not all(c in 'abcdefghijklmnopqrstuvwxyz0123456789.-' for c in ticket):
        raise ValueError('ticket non valido')
    staging=inbox/ticket;payload=staging/'payload'
    if request['operation']=='receive.abort':
        if staging.is_dir() and not staging.is_symlink():shutil.rmtree(staging)
        return {'status':'aborted'}
    if request['operation']=='receive.begin':
        inbox.mkdir(parents=True,exist_ok=True)
        if inbox.is_symlink():raise ValueError('inbox link non supportata')
        staging.mkdir(mode=0o700);payload.mkdir()
        for relative in request['files']:
            if '\n' in relative or '\r' in relative:raise ValueError('nome file non supportato dal trasporto')
            contained(payload,relative).parent.mkdir(parents=True,exist_ok=True)
        if shutil.disk_usage(inbox).free < request['bytes']+1024*1024:raise ValueError('spazio inbox insufficiente')
        return {'status':'staging','path':str(payload)}
    manifest=read_json(payload/'theme.json');identifier=manifest['id']
    if not isinstance(identifier,str) or not ID.fullmatch(identifier):raise ValueError('ID non valido')
    if payload_digest(payload)!=request['digest']:raise ValueError('hash payload diverso dal progetto verificato')
    catalog=ThemeCatalog(store,root=root);catalog.validate_pack(manifest)
    if identifier in catalog.packs:raise ValueError('ID già installato: aggiornamenti schema 1 non supportati')
    catalog.packs[identifier]=manifest;catalog.directories[identifier]=payload
    snapshots=[catalog.resolve(identifier,variant=variant) for variant in ('day','night')]
    qt=resource_probe(snapshots) if request.get('verifyQt',True) else {'issues':[],'qtResources':'notVerified'}
    if qt['issues']:raise ValueError(json.dumps(qt['issues'],ensure_ascii=False))
    destination=inbox/identifier
    with (inbox/'.theme-transfer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or not destination.is_dir() or payload_digest(destination)!=request['digest']:
                raise ValueError('conflitto inbox: contenuto esistente diverso')
            idempotent=True
        else:
            for path in payload.rglob('*'):
                if path.is_file():
                    with path.open('rb') as stream:os.fsync(stream.fileno())
            for folder in [*sorted((p for p in payload.rglob('*') if p.is_dir()),reverse=True),payload]:
                fd=os.open(folder,os.O_RDONLY|os.O_DIRECTORY)
                try:os.fsync(fd)
                finally:os.close(fd)
            payload.rename(destination);idempotent=False
            fd=os.open(inbox,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
    shutil.rmtree(staging)
    return {'status':'received','id':identifier,'digest':request['digest'],'destination':str(destination),
            'idempotent':idempotent,'qtProbe':qt.get('qtProbe'),
            'verification':{'resolvedTheme':'verified','qtResources':qt['qtResources'],'boardRuntime':'notVerified'}}


def run_request(request):
    root=Path(request.get('root',Path(__file__).parent)).resolve();service=None
    if request.get('service'):
        root,user,pid=service_context();service={'user':user,'pid':pid,'root':str(root)}
    store=store_path(request.get('store'))
    operation=request['operation']
    if operation=='profile':return profile(root,store,service)
    if operation=='resources':return resource_probe(request['snapshots'])
    if operation.startswith('receive.'):return receiver(request,root,store)
    raise ValueError('operazione probe sconosciuta')


if __name__=='__main__':
    try:
        request=globals().get('_REQUEST') or json.load(sys.stdin)
        print(json.dumps({'ok':True,'result':run_request(request)},ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error),'errorType':type(error).__name__},ensure_ascii=False))
        sys.exit(1)
