"""Native Qt preflight in a private store; production selection is untouched."""
import json
from pathlib import Path
import sys

project = Path("/var/lib/smartpc-dashboard/v082-staging/smartpc-v082-project")
sys.path.insert(0, str(project / "dashboard"))
from theme_bundle import BundleManager, validate_project
from theme_runtime import preflight
proof = Path("/var/lib/smartpc-dashboard/v082-proof")
theme = project / "theme-projects/apple-calm/bundle"
checked = validate_project(theme)
revision = BundleManager(proof / "private-theme-import", app_root=project / "dashboard").import_bundle(
    theme, preflight=preflight, require_preflight=True)
report = {"digest": checked["digest"], "result": revision["preflight"]}
assert revision["digest"] == report["digest"]
(project / "theme-projects/apple-calm/evidence/preflight-cache.json").write_text(json.dumps(report, indent=2) + "\n")
(proof / "native-theme-preflight.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
