import json,sys
from pathlib import Path
sys.path.insert(0,"/opt/smartpc/dashboard")
from theme_bundle import BundleManager
proof=Path("/var/lib/smartpc-dashboard/v083-space-proof")
cache=json.loads((proof/"native-theme-preflight.json").read_text())
revision=BundleManager(Path("/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC")).import_bundle(Path("/var/lib/smartpc-dashboard/v083-space-staging/smartpc-apple-calm-1.3.1.smartpc-theme"),preflight=lambda *_:cache["result"],require_preflight=True)
assert revision["digest"]==cache["digest"] and revision["version"]=="1.3.1"
(proof/"production-theme-import.json").write_text(json.dumps(revision,indent=2)+"\n")
