"""Run the real public-renderer preflight and bind its result to the payload."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--dashboard',type=Path,required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.dashboard.resolve()))
from theme_bundle import validate_project
from theme_runtime import preflight
checked=validate_project(a.project,app_root=a.dashboard.resolve())
result=preflight(a.project.resolve(),json.loads((a.project/'bundle.json').read_text()),json.loads((a.project/'visual-registry.json').read_text()))
report={'digest':checked['digest'],'identity':{k:checked[k] for k in ('id','version','digest')},'result':result}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'identity':report['identity'],'result':result}));assert result['status']=='passed',result
