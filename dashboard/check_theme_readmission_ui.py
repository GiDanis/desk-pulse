"""Real chooser, cancellable isolated verification and explicit activation.

The initial example import declares a test-only preflight; the readmission uses
the real subprocess matrix. All provider state and Qt preferences are private.
"""
import argparse
import json
from pathlib import Path
import time

from theme_fixture_support import isolate_process
private,base=isolate_process()
from theme_bundle import ROOT, BundleManager, atomic_json
from theme_fixture_support import LegacyHarness
from PySide6.QtCore import QObject

p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
manager=BundleManager(base)
revision=manager.import_bundle(ROOT/'examples/bundles/studio-ambient',
                              preflight=lambda *_:{'status':'passed','testOnly':True})
marker=base/'theme-quarantine'/(revision['digest']+'.json')
atomic_json(marker,{'revision':{k:revision[k] for k in ('id','version','digest')},
                    'reason':'GUI interrotta (-11), causa da verificare','failures':1})
h=LegacyHarness(base,dict(theme='base',variant='day',motion='normal'))

def until(predicate,seconds=120):
    end=time.monotonic()+seconds
    while not predicate() and time.monotonic()<end:h.pump(10)
    assert predicate(),(h.service.lastError,h.messages)

try:
    h.expression('openThemeChooser()');h.pump(100)
    rows=h.service.themeInventory
    index=next(i for i,r in enumerate(rows) if r['id']==revision['id'])
    assert rows[index]['state']=='blocked' and not rows[index]['selectable']
    assert all(r['id']!=revision['id'] for r in h.service.themes)
    assert not h.service.activateTheme(revision['id'])
    h.expression('themeChoiceIndex='+str(index));h.pump(100)
    assert h.window.grabWindow().save(str(args.output/'blocked.png'))
    assert h.expression('activateThemeChoice('+str(index)+')')
    assert not h.service.verifyTheme(revision['id']),'duplicate accepted'
    h.expression('activateKey(1)')
    until(lambda:not h.service.themeOperation['busy'],15)
    assert marker.exists() and h.service.activeThemeId=='base'
    assert h.value('overlay')=='','Home must complete after verification cancellation'
    h.expression('openThemeChooser();themeChoiceIndex='+str(index))
    assert h.service.verifyTheme(revision['id'])
    h.pump(250)
    h.events.set_demo_scenario('urgente');h.pump(150)
    assert h.service.themeOperation['busy'] and h.value('urgentEvent').get('id')
    loading=h.root.findChild(QObject,'themeLoading')
    assert not loading.property('visible'),'verification hid the urgent alert'
    h.expression('activateKey(7)');h.pump(80)
    assert not h.value('urgentEvent') and h.service.themeOperation['busy']
    until(lambda:not h.service.themeOperation['busy'])
    assert not marker.exists(),h.service.lastError
    assert h.service.activeThemeId=='base','verification must not activate'
    assert h.value('themeChoiceIndex')==index,'focus lost after readmission'
    assert next(r for r in h.service.themeInventory if r['id']==revision['id'])['selectable']
    assert h.expression('activateThemeChoice('+str(index)+')')
    until(lambda:not h.service.themeOperation['busy'])
    assert h.service.savedThemeId==revision['id'],h.service.lastError
    h.wait_ready()
    h.events.set_demo_scenario('urgente');h.pump(250)
    assert h.value('urgentEvent')['id'];h.expression('activateKey(7)');h.pump(100)
    assert not h.value('urgentEvent')
    assert h.service.activateTheme('base');until(lambda:not h.service.themeOperation['busy'])
    assert not h.messages,h.messages
    report={'status':'passed','backend':__import__('os').environ['QT_QPA_PLATFORM'],
            'checks':['blocked-visible-not-executable','legacy-missing-date','duplicate-rejected',
                      'home-cancel-keeps-quarantine','urgent-preempts-verification',
                      'real-isolated-matrix','verification-does-not-activate',
                      'focus-preserved','explicit-activation-saved','urgent-and-fallback'],
            'qmlWarnings':h.messages}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
finally:
    h.close();private.cleanup()
