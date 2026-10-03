"""OpenSSH/SFTP transport for the schema-1 authoring bridge."""
from pathlib import Path
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import uuid

from theme_core import ThemeError,contained,read_json
from theme_probe import payload_digest,receiver


class ProbeUnavailable(RuntimeError):
    pass


def local_probe(request,python):
    try:
        result=subprocess.run([python,str(Path(__file__).with_name('theme_probe.py'))],
                              input=json.dumps(request),capture_output=True,text=True,timeout=45)
    except (OSError,subprocess.TimeoutExpired) as error:
        raise ProbeUnavailable('probe Qt indisponibile: '+str(error)) from error
    return _response(result)


def _response(result):
    try:response=json.loads(result.stdout)
    except ValueError as error:raise ProbeUnavailable('nessun report valido dal probe: '+result.stderr.strip()[-600:]) from error
    if not response.get('ok'):
        if response.get('errorType') in ('ModuleNotFoundError','ImportError'):raise ProbeUnavailable(response['error'])
        raise ThemeError('probe',response.get('error','probe fallito'))
    if result.returncode:raise ProbeUnavailable('probe terminato con errore')
    return response['result']


class BoardTransport:
    def __init__(self,destination,identity=None):
        if not isinstance(destination,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@:-]*',destination):
            raise ThemeError('board','destinazione SSH non valida')
        self.destination=destination
        self.options=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=8']
        if identity:self.options+=['-i',str(Path(identity).expanduser())]

    def request(self,request):
        # Code is the author's checked-in helper, never Python taken from a pack.
        script="_REQUEST = "+repr(request)+"\n__file__ = '/opt/smartpc/dashboard/theme_probe.py'\n"
        script+=Path(__file__).with_name('theme_probe.py').read_text()
        command='python3 -c '+shlex.quote('import sys; exec(compile(sys.stdin.read(), "<SmartPC authoring probe>", "exec"))')
        try:
            result=subprocess.run(['ssh',*self.options,'--',self.destination,command],
                                  input=script,capture_output=True,text=True,timeout=60)
        except (OSError,subprocess.TimeoutExpired) as error:
            raise ProbeUnavailable('collegamento SSH indisponibile: '+str(error)) from error
        return _response(result)

    def profile(self):
        try:return self.request({'operation':'profile','service':True})
        except ThemeError as error:raise ProbeUnavailable('profilo board indisponibile: '+str(error)) from error

    def upload(self,payload,remote):
        def quote(path):
            value=str(path)
            if any(c in value for c in ('\n','\r','\0')):raise ThemeError('assets.path','nome non supportato dal trasporto SFTP')
            return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'
        commands=[]
        for path in sorted(payload.rglob('*')):
            if path.is_file():commands.append('put '+quote(path)+' '+quote(remote+'/'+path.relative_to(payload).as_posix()))
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.sftp') as batch:
            batch.write('\n'.join(commands)+'\n');batch.flush()
            try:
                result=subprocess.run(['sftp',*self.options,'-b',batch.name,'--',self.destination],
                                      capture_output=True,text=True,timeout=120)
            except (OSError,subprocess.TimeoutExpired) as error:raise ProbeUnavailable('trasferimento SFTP interrotto: '+str(error)) from error
        if result.returncode:raise ThemeError('transfer','SFTP fallito: '+result.stderr.strip()[-600:])


def snapshot_payload(source,destination):
    """Copy only declared data resources, validating the exact copied manifest."""
    source=Path(source).resolve();manifest=read_json(source/'theme.json')
    if (source/'theme.json').is_symlink():raise ThemeError('theme.json','manifest link non supportato')
    destination.mkdir()
    files={'theme.json':source/'theme.json'}
    for asset in manifest.get('assets',[]):
        relative=asset['path']
        if relative=='theme.json':raise ThemeError('assets.path','theme.json è riservato')
        path=contained(source,relative)
        # Reject links throughout the source path rather than copying a target
        # whose identity might change while validation is running.
        if any(p.is_symlink() for p in [source/relative,*list((source/relative).parents)[:len(Path(relative).parts)-1]]):
            raise ThemeError('assets.path','link non supportato')
        if any(c in relative for c in ('\n','\r','\0')):raise ThemeError('assets.path','nome non supportato dal trasporto')
        files[relative]=path
    for relative,path in files.items():
        target=contained(destination,relative);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    return manifest,files


def install_local(source,store,root,*,verify_qt=False,verify=None):
    inbox=store.parent/'theme-imports';inbox.mkdir(parents=True,exist_ok=True)
    ticket='.receive-'+uuid.uuid4().hex
    staging=inbox/ticket;staging.mkdir(mode=0o700)
    try:
        payload=staging/'payload';snapshot_payload(source,payload)
        if verify:verify(payload)
        digest=payload_digest(payload)
        return receiver({'operation':'receive.publish','ticket':ticket,'digest':digest,'verifyQt':verify_qt},root,store)
    finally:
        if staging.exists():shutil.rmtree(staging)


def install_board(source,transport,profile,*,verify=None):
    ticket='.receive-'+uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='smartpc-authoring-transfer-') as temporary:
        payload=Path(temporary)/'payload';snapshot_payload(source,payload)
        if verify:verify(payload)
        digest=payload_digest(payload)
        files=[p.relative_to(payload).as_posix() for p in sorted(payload.rglob('*')) if p.is_file()]
        common={'service':True,'ticket':ticket,'store':profile['store']}
        try:
            started=transport.request({**common,'operation':'receive.begin','files':files,
                                       'bytes':sum(p.stat().st_size for p in payload.rglob('*') if p.is_file())})
            transport.upload(payload,started['path'])
            return transport.request({**common,'operation':'receive.publish','digest':digest,'verifyQt':True})
        finally:
            try:transport.request({**common,'operation':'receive.abort'})
            except (ThemeError,ProbeUnavailable):pass  # A lost connection leaves hidden staging; never a visible partial pack.
