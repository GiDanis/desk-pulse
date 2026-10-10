#!/usr/bin/env python3
"""Read-only production audit; real Main runs with private, offline fixture data."""
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from theme_fixture_support import isolate_process, LegacyHarness

private, data = isolate_process()
from PySide6.QtCore import qVersion
from theme_bundle import BundleManager, validate_project

project = ROOT.parent / 'theme-projects/apple-calm/bundle'
valid = validate_project(project)
cache = json.loads((project.parent / 'evidence/preflight-cache.json').read_text())
assert cache['digest'] == valid['digest']
assert cache['result']['status'] == 'passed' and cache['result']['qt'] == qVersion()
BundleManager(data).import_bundle(project, preflight=lambda *_: cache['result'], require_preflight=True)
h = None
result = {'scope': 'Isolated real Main; private preferences, offline fixtures, no board or supervisor',
          'qt': qVersion(), 'bundleDigest': valid['digest'], 'observations': []}
try:
    h = LegacyHarness(data, {'theme': 'base', 'variant': 'night', 'motion': 'off'})
    h.service.cancel()
    h.wait_ready()
    h.pump(1100)
    def sample(name):
        row = {'name': name, 'draft': h.service.draft.get('themeId'),
               'activeThemeId': h.service.activeThemeId,
               'status': h.service.status, 'candidate': bool(h.service.candidateAppearance),
               'coherent': h.expression('currentThemeRenderCoherent()'),
               'overlay': h.value('overlay'), 'optionIndex': h.value('optionIndex'),
               'error': h.service.lastError,
               'overrides': h.service.draft.get('overrides', {})}
        result['observations'].append(row)
        h.window.grabWindow().save(str(HERE / (name+'.png')))
    def transition(name, action):
        start = time.monotonic()
        accepted = action()
        incoherent = 0
        while time.monotonic()-start < 6:
            h.pump(10)
            if h.expression('currentThemeRenderCoherent()') and not h.service.candidateAppearance:
                break
            incoherent += 1
        elapsed = round(time.monotonic()-start, 3)
        sample(name)
        result['observations'][-1].update(elapsedSeconds=elapsed, incoherentSamples=incoherent, actionResult=accepted)
    h.expression('pushOverlay("settings")')
    h.wait_ready()
    sample('base-settings')
    h.expression('pushOverlay("appearance")')
    h.wait_ready()
    h.root.setProperty('optionIndex', 2)
    sample('base-appearance')
    result['themeOptions'] = h.service.themes
    transition('cycle-first', lambda: h.expression('activateKey(6)'))
    transition('cycle-second', lambda: h.expression('activateKey(6)'))
    if h.service.readyToApply:
        h.service.apply()
        until = time.monotonic()+6
        while (h.service.editing or h.service.status == 'saving') and time.monotonic() < until:
            h.pump(10)
        sample('after-save')
        h.pump(1200)
        sample('after-save-settled')
    h.service.beginEdit()
    transition('return-base', lambda: h.service.selectDraft('base'))
    h.service.apply()
    h.pump(300)
    h.service.beginEdit()
    transition('direct-apple-in-appearance', lambda: h.service.selectDraft('studio.applecalm'))
    h.service.cancel()
    h.wait_ready()
    h.expression('pushOverlay("info")')
    h.wait_ready()
    h.root.setProperty('infoPage', 0)
    h.pump(60)
    sample('info-device')
    h.root.setProperty('infoPage', 1)
    h.pump(60)
    sample('info-resources')
    result['qmlMessages'] = h.messages
    result['networkAttempts'] = h.transport
finally:
    if h:
        h.close()
    private.cleanup()
    (HERE / 'isolated-settings-diagnostic.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
