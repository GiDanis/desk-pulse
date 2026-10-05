"""Real provider invalidation must hold readiness until the public DTO is fresh."""
import json
from pathlib import Path
import shutil
import sys
import time
from theme_fixture_support import isolate_process, LegacyHarness

private,base=isolate_process();harness=None
try:
    from PySide6.QtCore import QObject, qVersion
    from theme_runtime import preflight
    from theme_test_support import as_value,wait_save
    harness=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
    service=harness.service
    project=base/'project';shutil.copytree(Path(__file__).parent/'examples/bundles/studio-ambient',project)
    revision=service.bundles.import_bundle(project,preflight=preflight)
    assert service.reloadCatalog();service.beginEdit();assert service.selectDraft(revision['id'])
    harness.wait_ready()
    deadline=time.monotonic()+5
    while not service.readyToApply and time.monotonic()<deadline:harness.pump(5)
    assert service.readyToApply;assert service.apply();wait_save(harness.app,service)
    home=harness.root.findChild(QObject,'homeNow');loader=as_value(home.property('currentLoader'))
    adapter=loader.findChild(QObject,'publicContextAdapter');context=as_value(adapter.property('publicContext'))
    assert home.property('currentReady') and context.weather.temperature.value==0
    weather=context.weather
    harness.weather.value['data']['numeric']['temperature']=2
    harness.weather.value['data']['temperature']='2°'
    harness.weather.changed.emit()
    assert adapter.property('refreshScheduled'),'Positive control: invalidation was not deferred'
    assert not home.property('currentContextReady') and not home.property('currentReady')
    assert not harness.expression('currentThemeRenderCoherent()')
    assert context.weather.temperature.value==0,'Old DTO should remain owned until publication'
    deadline=time.monotonic()+3
    while time.monotonic()<deadline and (adapter.property('refreshScheduled') or context.weather.temperature.value!=2):harness.pump(5)
    assert not adapter.property('refreshScheduled') and adapter.property('valid')
    assert home.property('currentContextReady') and home.property('currentReady')
    assert context.weather is weather and context.weather.temperature.value==2
    assert not harness.messages,harness.messages
    result={'status':'passed','qt':qVersion(),'checks':['real-provider-invalidation','deferred-context-positive-control',
        'readiness-held-until-dto-publication','coherent-theme-guard','fresh-public-weather','dto-identity-retained'],
        'qmlWarnings':harness.messages,'scope':'Actual isolated Main and provider; readiness guard, not an invented frame acknowledgement.'}
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:
    if harness:harness.close()
    private.cleanup()
