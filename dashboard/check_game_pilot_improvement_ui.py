"""Actual Main/Worker checks of immutable recipes and readable effective settings."""
import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')


def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    from theme_bundle import BundleManager,validate_project
    from PySide6.QtCore import qVersion
    p=argparse.ArgumentParser();p.add_argument('--theme',choices=('base','functional','apple'),default='base')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    private,base=isolate_process();root=Path(__file__).resolve().parents[1]
    if a.theme=='apple':
        bundle=root/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
        cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
        BundleManager(base,app_root=root/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
    h=LegacyHarness(base,dict(theme=a.theme if a.theme!='apple' else 'base',variant='day',motion='normal',game=True))
    captures=[]
    def wait(f):
        end=time.monotonic()+35
        while not f() and time.monotonic()<end:h.pump(10)
        assert f(),h.game.snapshot.get('message')
    def capture(label):
        a.output.mkdir(parents=True,exist_ok=True);h.pump(80)
        assert h.window.grabWindow().save(str(a.output/(label+'.png')));captures.append(label)
    try:
        if a.theme=='apple':assert h.service.selectDraft('studio.applecalm');h.wait_ready()
        assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
        original=h.game._store.drivers()
        h.expression('familyId="game"');h.wait_ready();h.expression('activateKey(9)');h.wait_ready()
        h.game.settingsAction('section:management',1);h.game.settingsAction('create',1)
        ids={r['id'] for r in h.game.snapshot['settings']['rows']}
        assert {'preset:clone_ppo','preset.variants'}<=ids
        assert 'preset:neat64' not in ids
        capture('recipes')
        h.game.settingsAction('preset.variants',1)
        ids={r['id'] for r in h.game.snapshot['settings']['rows']}
        assert {'preset:neat64','preset:neat_response','preset:regular','preset:attacker','preset:versatile'}<=ids
        capture('variants')
        h.game.settingsAction('preset:neat_response',1)
        assert h.game.snapshot['profile']['variant']=='neat_response'
        assert not h.game.configure({'population':64})
        h.expression('popOverlay()');h.wait_ready()
        h.game._training_view='attempts';h.game._refresh()
        assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and len(h.game.scene.get('cars',[]))==32)
        capture('neat-population')
        assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved' and not h.game.captured)
        d=h.game._store.driver(h.game._selected)
        assert d['curriculum']['effectiveParameters']['network']['responseInit']==.4
        h.expression('openPilotDetails('+json.dumps(d['id'])+')');h.wait_ready()
        h.expression('activateKey(6)');h.pump(60);capture('neat-effective')
        assert any(r['title']=='NEAT · risposta iniziale' and r['value']=='0.4' for r in h.game.snapshot['dossier']['parameters'])
        h.expression('activateKey(9)');h.wait_ready()
        assert h.game.createDriverPreset('neat64')
        h.expression('popOverlay()');h.wait_ready()
        assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and len(h.game.scene.get('cars',[]))==64)
        capture('neat64-population')
        assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved' and not h.game.captured)
        h.expression('pushOverlay("gameMenu")');h.wait_ready()
        assert h.game.createDriverPreset('clone_ppo')
        h.expression('popOverlay()');h.wait_ready()
        assert h.game.start();wait(lambda:h.game.snapshot['runState']=='running' and h.game.scene.get('meta',{}).get('steps',0)>=128)
        capture('hybrid-learning')
        assert len(h.game.scene['cars'])==1
        assert h.game.pause();wait(lambda:h.game.snapshot['saveState']=='saved' and not h.game.captured)
        d=h.game._store.driver(h.game._selected);c=h.game._store.load(d['checkpoint'])
        assert c['learner']['hybrid']['phase']=='imitation'
        assert c['learner']['buffer']==[]
        h.expression('openPilotDetails('+json.dumps(d['id'])+')');h.wait_ready()
        h.expression('activateKey(6)');h.pump(60);capture('hybrid-effective')
        assert any(r['title']=='Ricetta ibrida' and r['value']=='Imitazione' for r in h.game.snapshot['dossier']['parameters'])
        for old in original:assert h.game._store.driver(old['id'])==old
        assert not h.messages,h.messages
        report=dict(status='passed',theme=a.theme,window=[h.window.width(),h.window.height()],
            textScale=1.1,recipesVisible=True,profilesFixed=True,neatResponse=.4,neat64Visible=True,
            realHybridWorker=True,originalsPreserved=True,captures=captures,qmlWarnings=h.messages,
            scope='Isolated Main/Worker; no trained-competence or optical-FPS claim')
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    finally:h.close();private.cleanup()


if __name__=='__main__':main()
