"""Native Qt preflight of the exact staged immutable theme, no production state."""
import json
from pathlib import Path
import sys
project=Path('/var/lib/smartpc-dashboard/v083-staging/smartpc-v083-project')
sys.path.insert(0,str(project/'dashboard'))
from theme_bundle import validate_project
from theme_runtime import preflight
bundle=project/'theme-projects/apple-calm/bundle'
valid=validate_project(bundle)
result=preflight(bundle,valid['manifest'],valid['registry'])
assert result['status']=='passed',result
cache={'digest':valid['digest'],'result':result}
for path in [project/'theme-projects/apple-calm/evidence/preflight-cache.json',Path('/var/lib/smartpc-dashboard/v083-proof/native-theme-preflight.json')]:
 path.write_text(json.dumps(cache,indent=2)+'\n')
print(json.dumps(cache),flush=True)
