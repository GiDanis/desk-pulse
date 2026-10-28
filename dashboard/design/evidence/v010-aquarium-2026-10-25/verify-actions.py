"""Real AquariumContext broker/router integration, with isolated fixture services."""
import argparse,json,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.source.resolve()))
from theme_fixture_support import isolate_process,LegacyHarness
private,base=isolate_process();h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal'});checks=[]
def wait(predicate):
 end=time.monotonic()+8
 while not predicate() and time.monotonic()<end:h.pump(5)
 assert predicate(),h.aquarium.snapshot

def action(name,args=None):
 print('ACTION',name,flush=True)
 return h.expression('(function(){const r=aquariumPage.currentItem.ctx.requestAction('+json.dumps(name)+',"",'+json.dumps(args or {})+'); return {accepted:r.accepted,status:r.status,errorCode:r.errorCode}})()')
def check(name,condition):
 print('CHECK',name,condition,flush=True)
 assert condition,name;checks.append(name)
try:
 h.expression('familyId="aquarium"');wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running');h.pump(100)
 check('publicPauseAccepted',action('aquarium.pause')['accepted']);wait(lambda:h.aquarium.snapshot['requestedPlayback']=='paused')
 check('publicPauseApplied',h.aquarium.snapshot['requestedPlayback']=='paused')
 check('publicResumeAccepted',action('aquarium.resume')['accepted']);wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running')
 check('publicResumeApplied',h.aquarium.snapshot['effectivePlayback']=='running')
 check('unknownArgumentsRejected',not action('aquarium.pause',{'unexpected':1})['accepted'])
 check('otherSurfaceActionRejected',not action('game.pause')['accepted'])
 h.expression('activateKey(9)');h.pump(100)
 check('overlayContextCannotResume',not action('aquarium.resume')['accepted'])
 h.expression('activateKey(7)');h.pump(100)
 h.events.set_demo_scenario('urgente');h.pump(150)
 check('urgentContextCannotResume',not action('aquarium.resume')['accepted'])
 h.events.set_demo_scenario('nessuno');h.pump(150)
 check('urgentPauseRetained',h.aquarium.snapshot['requestedPlayback']=='paused')
 check('resumeAfterUrgentExplicit',action('aquarium.resume')['accepted']);wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running')
 assert h.service.setSection('motionMode','off');h.wait_ready();h.pump(150)
 check('resumeCannotOverrideMotionPolicy',not action('aquarium.resume')['accepted'] and h.aquarium.snapshot['effectivePlayback']=='static')
 h.expression('activateKey(1)');h.pump(150)
 check('retainedHiddenContextCannotPause',not action('aquarium.pause')['accepted'])
 assert not h.messages and not h.transport,(h.messages,h.transport)
 report={'status':'passed','checks':checks,'warnings':h.messages,'networkAttempts':h.transport,'scope':'Actual public context requestAction, broker and Main router; isolated QSettings/store/providers, not physical input timing'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
finally:h.close();private.cleanup()
