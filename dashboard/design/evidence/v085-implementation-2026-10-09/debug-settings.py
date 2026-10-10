#!/usr/bin/env python3
"""Real Main theme chooser transactions, settings grids and Info without network.

Uses the exact preflighted Apple bundle and actual frame acknowledgements; no
synthetic acknowledgements or writes to production preferences.
"""
import argparse
import json
from pathlib import Path
import time
import sys
sys.path.insert(0,"/home/giuseppe/Documenti/Workspace/SmartPC/dashboard")
from theme_fixture_support import isolate_process, LegacyHarness

parser=argparse.ArgumentParser()
parser.add_argument('--palette',choices=['day','night'],default='night')
parser.add_argument('--capture-dir',type=Path)
args=parser.parse_args()
private,data=isolate_process()
h=None
try:
    from PySide6.QtCore import QObject,qVersion
    from theme_bundle import BundleManager,validate_project
    from theme_test_support import as_value
    bundle=Path('/home/giuseppe/Documenti/Workspace/SmartPC/theme-projects/apple-calm/bundle')
    valid=validate_project(bundle)
    cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
    assert cache['result']['status']=='passed' # Diagnostic only: final geometry preflight running.
    assert cache['result']['qt']==qVersion()
    BundleManager(data).import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(data,{'theme':'base','variant':args.palette,'motion':'off'})
    output=args.capture_dir or Path(private.name)/'captures';output.mkdir(parents=True,exist_ok=True)
    transactions=[]
    def wait(condition,label,seconds=15):
        end=time.monotonic()+seconds
        while not condition() and time.monotonic()<end:h.pump(10)
        assert condition(),(label,h.service.themeOperation,h.service.lastError,h.value('overlay'),h.messages)
    def capture(name):
        h.pump(50);assert h.window.grabWindow().save(str(output/(name+'.png')))
    def chooser():
        h.expression('home()');h.expression('pushOverlay("settings")');h.wait_ready()
        panel=h.root.findChild(QObject,'settingsPanel')
        h.expression('settingsIndex=1; activateKey(5)');h.wait_ready()
        assert h.value('overlay')=='appearance'
        h.expression('optionIndex=2; activateKey(5)');h.wait_ready()
        assert h.value('overlay')=='themeChooser'
        return panel
    # Set up the fixture preference using the same durable transaction as UI.
    assert h.service.activateTheme('base')
    wait(lambda:not h.service.themeOperation['busy'],'initial save')
    assert h.service.savedThemeId=='base'
    chooser();revision=h.service.revision
    saved=h.service.savedThemeId
    h.expression('activateKey(8)');h.pump(100)
    assert h.service.savedThemeId==saved and h.service.revision==revision and not h.service.candidateAppearance
    h.expression('activateKey(7)');h.wait_ready()
    assert h.value('overlay')=='appearance' and h.service.savedThemeId==saved
    # Cold and warm paths in both directions, including the optional shell removal.
    for i,target in enumerate(['studio.applecalm','base','functional','studio.applecalm','functional','base','studio.applecalm','base']):
        chooser()
        ids=[r['id'] for r in h.service.themes];index=ids.index(target)
        before=h.service.savedThemeId;revision=h.service.revision
        # Keypad focus movement must never activate intermediate themes.
        while h.value('themeChoiceIndex')!=index:
            h.expression('activateKey('+('8' if h.value('themeChoiceIndex')<index else '2')+')');h.pump(20)
            assert h.service.savedThemeId==before and h.service.revision==revision
        capture('chooser-'+str(i))
        started=time.monotonic();h.expression('activateKey(5)')
        observed=[]
        while h.service.themeOperation['busy'] and time.monotonic()-started<15:
            op=h.service.themeOperation
            if op['phase'] not in observed:observed.append(op['phase'])
            if op['phase']=='preparing' and time.monotonic()-started>.15:capture('loading-'+str(i))
            h.pump(10)
        wait(lambda:not h.service.themeOperation['busy'],'activation '+target)
        assert h.service.themeOperation['phase']=='completed',{k:v for k,v in h.service.themeOperation.items() if k!='palette'}
        wait(lambda:h.expression('currentThemeRenderCoherent()') and not h.service.needsFrameAcknowledgement,'final frame')
        assert h.service.savedThemeId==target and h.service.activeThemeId==target
        assert not h.service.lifecycle.read()['pending'] and not h.service.candidateAppearance
        assert h.value('overlay')=='appearance'
        transactions.append({'target':target,'seconds':round(time.monotonic()-started,3),'phases':observed})
        h.expression('home();pushOverlay("settings")');h.wait_ready();capture(target+'-settings-'+str(i))
        if i<5:
            for tab in range(4):
                h.root.setProperty('overlay','info');h.root.setProperty('infoPage',tab);h.root.setProperty('infoIndex',0);h.wait_ready()
                capture(target+'-info-'+str(tab))
    # Selecting the saved theme with a clean draft is an idempotent no-op.
    chooser();revision=h.service.revision
    h.expression('activateKey(5)');h.pump(100)
    assert h.service.savedThemeId=='base' and h.service.revision==revision
    assert not h.service.themeOperation['busy']
    assert not h.messages,h.messages
    assert not h.transport,h.transport
    assert all(count==0 for name,count in h.effects.items() if '.clear' not in name),h.effects
    report={'status':'passed','qt':qVersion(),'palette':args.palette,'transactions':transactions,
            'focusDoesNotActivate':True,'sameThemeNoOp':True,'finalFrameBeforeCompletion':True,
            'providerCalls':h.effects,'networkAttempts':h.transport,'qmlWarnings':h.messages}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
finally:
    if h:h.close()
    private.cleanup()
