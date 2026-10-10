"""Import exact native-preflighted revision while the production kiosk is stopped."""
import json,sys
from pathlib import Path
sys.path.insert(0,'/opt/smartpc/dashboard')
from theme_bundle import BundleManager,validate_project
H=Path('/var/lib/smartpc-dashboard');P=H/'v087-opening-proof';bundle=H/'smartpc-v087-opening-staging/project/theme-projects/apple-calm/bundle'
cache=json.loads((P/'native-theme-preflight.json').read_text());validation=validate_project(bundle)
assert validation['digest']==cache['digest'] and cache['result']['status']=='passed'
revision=BundleManager(H/'.local/share/SmartPC/SmartPC').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
assert revision['digest']==cache['digest'] and revision['version']=='1.6.2'
(P/'production-theme-import.json').write_text(json.dumps(revision,indent=2)+'\n')
