from pathlib import Path
import json,time
from theme_fixture_support import isolate_process,LegacyHarness
private,base=isolate_process();h=None;provider=None
try:
    from casa import CasaService
    from PySide6.QtCore import QObject,qVersion
    from theme_test_support import as_value
    h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
    provider=CasaService(auto_refresh=False,
        config_path='/var/lib/smartpc-dashboard/.config/smartpc/tuya-cloud.json',
        state_dir='/var/lib/smartpc-dashboard/.local/state/smartpc/casa')
    before=provider.budget.data['requests']
    assert provider.moduleState['status']=='stale'
    h.state._casa=provider
    provider.changed.connect(h.state.casaChanged);provider.changed.connect(h.state.settingsChanged)
    h.state.casaChanged.emit();h.state.settingsChanged.emit()
    h.root.setProperty('familyId','casa');h.root.setProperty('viewIndex',[0]*7);h.root.setProperty('overlay','')
    h.wait_ready();h.pump(150)
    assert h.value('casaData')['configured'] and len(h.value('casaRows'))==4
    assert all(d['previous'] for d in h.value('casaRows'))
    assert h.window.width()==960 and h.window.height()==640
    assert h.window.grabWindow().save('/tmp/v07-real-cache-overview.png')
    h.root.setProperty('casaSelectedId',h.value('casaRows')[0]['id']);h.expression('activateKey(5)');h.wait_ready();h.pump(100)
    assert h.window.grabWindow().save('/tmp/v07-real-cache-detail.png')
    assert not h.messages,h.messages
    assert provider.budget.data['requests']==before
    print(json.dumps({'status':'passed','qt':qVersion(),'size':[960,640],'sourceStatus':'stale','actualInventory':len(provider._snapshot['devices']),'favourites':len(provider._snapshot['favourites']),'additionalCloudCalls':0,'qmlWarnings':h.messages,'scope':'Real production cloud cache, isolated Main/Base preferences, EGLFS on board. Saved data explicitly labelled previous.'}))
finally:
    if provider:provider.close()
    if h:h.close()
    private.cleanup()
