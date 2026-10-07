"""Installed Apple Calm immutable bundle with new Base network surfaces, real saved inventory."""
import hashlib,json,shutil,os
from pathlib import Path
from theme_fixture_support import isolate_process,LegacyHarness
private,base=isolate_process();h=None;provider=None
try:
    from PySide6.QtCore import QObject,qVersion
    from network import NetworkService
    original=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/theme-bundles')
    before={str(p.relative_to(original)):hashlib.sha256(p.read_bytes()).hexdigest() for p in original.rglob('*') if p.is_file()}
    shutil.copytree(original,base/'theme-bundles')
    h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
    assert h.service.selectDraft('studio.applecalm')
    h.wait_ready();h.pump(180)
    assert h.service.draft['themeId']=='studio.applecalm'
    assert h.service.resolvedAppearance['presentations']['network.overview']=='builtin.network.overview'
    provider=NetworkService(auto_refresh=False,config_path='/var/lib/smartpc-dashboard/.config/smartpc/iliadbox/app.json',state_dir='/var/lib/smartpc-dashboard/.local/state/smartpc/network')
    assert provider.moduleState['status']=='stale' and provider.moduleState['data']['hasInventory']
    h.state._network=provider;provider.changed.connect(h.state.networkChanged);provider.changed.connect(h.state.modulesChanged)
    h.state.networkChanged.emit();h.state.modulesChanged.emit();h.root.setProperty('familyId','network');h.pump(250)
    assert h.value('networkRows') and all(d['previous'] for d in h.value('networkRows'))
    proof=Path('/var/lib/smartpc-dashboard/v08-proof/private-captures');proof.mkdir(mode=0o700,exist_ok=True)
    assert h.window.grabWindow().save(str(proof/'apple-calm-real-cache-overview.png'))
    h.expression('openNetworkDevice(networkRows[0].id)');h.pump(250)
    assert h.window.grabWindow().save(str(proof/'apple-calm-real-cache-detail.png'))
    h.expression('back()');h.expression('pushOverlay("networkSettings")');h.pump(250)
    assert h.window.grabWindow().save(str(proof/'apple-calm-real-cache-settings.png'))
    assert not h.messages and not h.transport,(h.messages,h.transport)
    after={str(p.relative_to(original)):hashlib.sha256(p.read_bytes()).hexdigest() for p in original.rglob('*') if p.is_file()}
    assert before==after
    print(json.dumps({'status':'passed','qt':qVersion(),'backend':os.environ.get('QT_QPA_PLATFORM','Qt default'),'size':[h.window.width(),h.window.height()],'theme':'studio.applecalm@1.2.0','fallback':'Base Network surfaces using Apple Calm style','inventory':provider.moduleState['data']['knownCount'],'sourceStatus':'stale','qmlWarnings':h.messages,'immutableOriginalPreserved':True,'routerRequests':0,'scope':'Board rendering and cached real inventory; backend stated separately; no physical keypad/presence test.'},ensure_ascii=False))
finally:
    if provider:provider.close()
    if h:h.close()
    private.cleanup()
