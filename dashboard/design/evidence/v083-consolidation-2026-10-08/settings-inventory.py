"""Read canonical row identities from real Main, including Casa/Network contexts."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from theme_fixture_support import LegacyHarness,isolate_process
from theme_api_contract import ThemeApiContract
private,base=isolate_process();h=None
try:
 h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'});contract=ThemeApiContract();rows=[]
 for sid,definition in contract.surfaces.items():
  if not sid.startswith('settings.'):continue
  h.root.setProperty('overlay',definition['legacyRoute']);h.wait_ready();h.pump(20)
  payload=h.expression('publicSurfacePayload('+json.dumps(sid)+')')
  rows.append({'surface':sid,'context':definition['context'],'route':definition['legacyRoute'],'rows':[{k:r.get(k) for k in ['id','title','control','actionId','targetId','enabled','reason']} for r in payload['rows']]})
 assert not h.messages,h.messages
 (Path(__file__).parent/'settings-map.json').write_text(json.dumps({'apiFingerprint':contract.fingerprint,'scope':'Real Main with isolated demo fixtures; enabled states are conditional, not production availability','surfaces':rows},ensure_ascii=False,indent=2)+'\n')
finally:
 if h:h.close()
 private.cleanup()
