"""Real Main light/red-night palettes; canonical contrast and immutable author input."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
from theme_fixture_support import LegacyHarness, isolate_process


def main():
    private, base = isolate_process()
    harness = None
    try:
        from theme_core import ROOT, contrast
        from theme_bundle import BundleManager
        from theme_runtime import preflight
        from theme_semantics import graph
        harness = LegacyHarness(base, {'theme':'base','variant':'day','motion':'off'})
        project = base/'palette-project'; shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
        file = project/'theme.json'; pack=json.loads(file.read_text())
        pack['palettes']={
            'day':{'colors.background':'#ecebe4','colors.backgroundOverlay':'#e2e0d8','colors.surface':'#f3f1e9','colors.surfaceFocused':'#d5d3cb','colors.bannerSurface':'#e8e6dc','colors.textPrimary':'#181817','colors.textSecondary':'#3b3b36','colors.accent':'#ff5500'},
            'night':{'colors.background':'#170709','colors.backgroundOverlay':'#130407','colors.surface':'#280f15','colors.surfaceFocused':'#35131b','colors.bannerSurface':'#301117','colors.textPrimary':'#ffd2cd','colors.textSecondary':'#dcaaa3','colors.accent':'#ff8978'}}
        for mode in ('small','large','urgent','badge','inbox','detail'):
            pack['palettes']['day']['notifications.'+mode+'.accent']='#994400'
            pack['palettes']['day']['notifications.'+mode+'.borderColor']='#69685e'
        file.write_text(json.dumps(pack)); original=file.read_bytes()
        service=harness.service
        revision=BundleManager(service.store.parent).import_bundle(project,preflight=preflight,require_preflight=True)
        assert service.reloadCatalog(); assert service.selectDraft(revision['id']),service.lastError
        checks=[]
        for variant in ('day','night'):
            assert service.setSection('paletteMode',variant),service.lastError
            harness.wait_ready(); harness.pump(200)
            snapshot=service.resolvedAppearance; tokens=snapshot['tokens']; document=graph(str(ROOT))
            for usage in document['usages']:
                role=document['roles'].get(usage['foreground']); key=role['futureToken'] if role else usage['foreground']
                background=usage.get('backgroundFallbackFor') if usage.get('backgroundFallbackFor') in tokens else usage['backgroundToken']
                assert contrast(tokens[key],tokens[background])>=usage['minimum'],usage
            assert tokens['colors.accent']==pack['palettes'][variant]['colors.accent']
            assert file.read_bytes()==original
            assert service.draft['overrides']=={},'Derived foregrounds must not become user overrides'
            if variant=='day': assert snapshot['semanticDerivations'],'Light inherited foregrounds should be derived and reported'
            for route in ('menu','settings','info','alerts'):
                harness.root.setProperty('overlay',route); harness.pump(180)
                assert harness.root.property('overlay')==route
            harness.root.setProperty('overlay',''); harness.pump()
            if len(sys.argv)==2:
                output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
                assert harness.window.grabWindow().save(str(output/('palette-'+variant+'.png')))
            checks.append({'variant':variant,'contrastPairs':len(document['usages']),'derivedRoles':len(snapshot['semanticDerivations']),'status':'passed'})
        # Explicit invalid authored role is rejected, never silently repaired.
        before=deepcopy(service.draft)
        assert not service.setToken('semantic.accentTextOnCanvas',tokens['colors.background'])
        assert service.draft==before and service.lastError
        assert not harness.messages,harness.messages
        assert not harness.transport,harness.transport
        report={'status':'passed','checks':checks,'qmlWarnings':harness.messages,'scope':'Actual Main and public/legacy renderer colors; no optical panel readability or final concept acceptance claim'}
        print(json.dumps(report))
    finally:
        if harness:harness.close()
        private.cleanup()

if __name__=='__main__':main()
