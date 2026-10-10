"""Board-native Qt preflight of the exact staged Apple Calm revision."""
import json
from pathlib import Path
import subprocess
import sys
import time

project = Path('/var/lib/smartpc-dashboard/v086-dashboard-staging/project')
sys.path.insert(0, str(project / 'dashboard'))
from theme_bundle import validate_project
from theme_runtime import preflight
bundle = project / 'theme-projects/apple-calm/bundle'
validation = validate_project(bundle)
result = preflight(bundle, validation['manifest'], validation['registry'])
assert result['status'] == 'passed', result
report = {'digest': validation['digest'], 'result': result,
          'origin': {'hostname': subprocess.check_output(['hostname'], text=True).strip(), 'checkedAt': time.time()}}
serialized = json.dumps(report, indent=2) + '\n'
(project / 'theme-projects/apple-calm/evidence/preflight-cache.json').write_text(serialized)
Path('/var/lib/smartpc-dashboard/v086-dashboard-proof/native-theme-preflight.json').write_text(serialized)
print(json.dumps(report), flush=True)
