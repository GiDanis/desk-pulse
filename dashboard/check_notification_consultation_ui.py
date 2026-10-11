"""Real Main: notification delivery above consultation on three themes, offline."""
import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':
    os.environ.setdefault('QT_QUICK_BACKEND','software')
from theme_fixture_support import isolate_process, LegacyHarness
from theme_test_support import as_value
from theme_bundle import BundleManager, validate_project
from PySide6.QtCore import QObject, qVersion

parser=argparse.ArgumentParser()
parser.add_argument('--theme',choices=('base','functional','apple'),default='base')
parser.add_argument('--capture-dir',type=Path)
args=parser.parse_args()
private,base=isolate_process()
root=Path(__file__).resolve().parents[1]
if args.theme=='apple':
    bundle=root/'theme-projects/apple-calm/bundle'
    valid=validate_project(bundle)
    cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
    assert cache['digest']==valid['digest'] and cache['result']['status']=='passed' and cache['result']['qt']==qVersion()
    BundleManager(base,app_root=root/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
h=LegacyHarness(base,{'theme':'functional' if args.theme=='functional' else 'base','variant':'day','motion':'off'})
try:
    if args.theme=='apple':
        assert h.service.selectDraft('studio.applecalm');h.wait_ready()
    h.events.set_quiet(False,0,1)
    h.expression('pushOverlay("info")');h.wait_ready()
    item=dict(version=1,id='consultation-demo',source='notification-test',sourceLabel='Demo · nessuna fonte esterna',
              category='demo',priority=2,bannerSize='large',title='Serie A · Gol segnalato dalla fonte',
              detail='Inter – Roma · 1–0 · evento simulato',issuedAt=h.now,startsAt=h.now,
              expiresAt=h.now+3600,bannerUntil=h.now+180,revision='1')
    h.events.publish_snapshot('notification-test',[item])
    deadline=time.monotonic()+5
    while h.events.eventState['bannerPending'] and time.monotonic()<deadline:h.pump(10)
    assert not h.events.eventState['bannerPending'] and h.events.eventState['visibleBanner']['id']==item['id']
    assert h.value('overlay')=='info'
    host=h.root.findChild(QObject,'eventLargeBanner')
    assert host.property('show') and as_value(host.property('currentItem'))
    assert h.window.activeFocusItem().objectName()=='inputOwner'
    if args.capture_dir:
        args.capture_dir.mkdir(parents=True,exist_ok=True)
        h.pump(160);assert h.window.grabWindow().save(str(args.capture_dir/'consultation-banner.png'))
    h.expression('activateKey(3)');h.wait_ready()
    assert h.value('overlay')=='alerts' and not h.events.eventState['visibleBanner']
    h.events.publish_snapshot('notification-test',[])
    h.expression('activateKey(6)');h.pump(50)
    assert h.events.eventState['historyMode'] and any(v['cancelled'] for v in h.events.eventState['inbox'])
    assert h.events._engine.lookup(item['id'],h.now)=={}
    h.expression('activateKey(4)');h.pump(30)
    assert not h.events.eventState['historyMode']
    h.expression('popOverlay()');h.expression('popOverlay()');h.expression('pushOverlay("appearance")');h.wait_ready()
    item=dict(item,id='deferred-demo')
    h.events.publish_snapshot('notification-test',[item]);h.pump(50)
    assert not h.events.eventState['visibleBanner']
    h.expression('popOverlay()');h.wait_ready()
    deadline=time.monotonic()+5
    while h.events.eventState['bannerPending'] and time.monotonic()<deadline:h.pump(10)
    assert h.events.eventState['visibleBanner']['id']==item['id'] and not h.events.eventState['bannerPending']
    assert not h.messages,h.messages
    assert not h.transport,h.transport
    report={'status':'passed','theme':args.theme,'platform':os.environ['QT_QPA_PLATFORM'],'windowSize':[h.window.width(),h.window.height()],
            'qt':qVersion(),'checks':['consultation banner frame acknowledged','route and input focus preserved','history retains revoked event',
                                    'editing defers presentation','closing editor resumes timely event'],
            'qmlWarnings':h.messages,'transportCalls':len(h.transport),'scope':'Synthetic events in real Main; no claim of real goal or optical latency'}
    if args.capture_dir:(args.capture_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
finally:h.close();private.cleanup()
