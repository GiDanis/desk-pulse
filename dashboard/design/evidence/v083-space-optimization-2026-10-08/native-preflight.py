"""Full native renderer preflight of the exact final immutable theme."""
import json,sys
from pathlib import Path
project=Path('/var/lib/smartpc-dashboard/v083-space-staging/smartpc-space-project')
sys.path.insert(0,str(project/'dashboard'))
from theme_bundle import validate_project
from theme_runtime import preflight
bundle=project/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
result=preflight(bundle,valid['manifest'],valid['registry'])
assert result['status']=='passed',result
cache={'digest':valid['digest'],'result':result}
for p in [project/'theme-projects/apple-calm/evidence/preflight-cache.json',Path('/var/lib/smartpc-dashboard/v083-space-proof/native-theme-preflight.json')]:
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(cache,indent=2)+'\n')
print(json.dumps(cache),flush=True)
