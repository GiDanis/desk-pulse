"""Private integration of immutable bundle storage with the existing catalog."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from theme_core import ThemeCatalog, ThemeError
from theme_bundle import BundleManager, semver

def make_catalog(store, root, selected=None, trace=None):
    catalog=ThemeCatalog(store,root=root,trace=trace)
    manager=BundleManager(Path(store).parent,app_root=root)
    latest={}
    verified=manager.list_revisions()
    # The editor consumes this immutable identity index. Resource verification
    # stays at catalog reload/selection; reading a QML property does no file I/O.
    catalog.installed_bundle_revisions=[{key:revision[key] for key in ('id','version','digest')} for revision in verified]
    for revision in verified:
        latest[revision['id']]=revision
    if selected:
        if (Path(store).parent/'theme-quarantine'/(selected['digest']+'.json')).exists():
            raise ThemeError('bundleRevision','revisione in quarantena')
        latest[selected['id']]=manager.verify_revision(selected)
    for revision in latest.values():
        try:
            manager.register_catalog(catalog,revision)
            catalog.validate_pack(catalog.packs[revision['id']])
            for variant in ('day','night'): catalog.resolve(revision['id'],variant=variant)
        except (ThemeError,OSError) as error:
            catalog.packs.pop(revision['id'],None)
            catalog.errors.append(str(error))
    return catalog

def preflight(payload, manifest, registry):
    """Separate process: a blocked visual cannot block import or the kiosk GUI."""
    from PySide6.QtCore import qVersion
    if semver(qVersion())<semver(manifest['qtMinimum']):
        return {'status':'failed','error':'Versione Qt inferiore al minimo del tema'}
    with tempfile.TemporaryDirectory(prefix='smartpc-theme-preflight-') as temporary:
        env=dict(os.environ,QT_QPA_PLATFORM='offscreen')
        command=[sys.executable,str(Path(__file__).with_name('theme_bundle_preview.py')),str(payload),'--output',str(Path(temporary)/'preview'),'--matrix']
        try:
            # The matrix exercises every covered surface 18 times. A complete
            # theme must not hit the five-surface starter's fixed time budget.
            timeout=max(90,min(600,12*len(manifest['coverage']['surfaces'])))
            result=subprocess.run(command,capture_output=True,text=True,env=env,timeout=timeout)
            report=json.loads(result.stdout)
            if result.returncode or report.get('status')!='passed':
                return {'status':'failed','error':'Preflight Qt fallito','diagnostics':report,'stderr':result.stderr[-6000:]}
            return {'status':'passed','qt':qVersion(),'backend':'offscreen','scope':'isolatedPublicRenderers',
                    'renderers':len(report.get('renderers',[])),'boardEglfs':'notVerified'}
        except (OSError,ValueError,subprocess.TimeoutExpired) as error:
            return {'status':'failed','error':str(error)}
