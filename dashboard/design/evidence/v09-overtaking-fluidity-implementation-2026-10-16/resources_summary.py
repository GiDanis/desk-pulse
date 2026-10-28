"""Domain resource diagnostics aligned to measured windows; no GPU/NPU inference."""
from pathlib import Path
import argparse,json,math
p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);a=p.parse_args();root=a.board
samples=[json.loads(line) for line in (root/'resources-resumed.jsonl').read_text().splitlines() if line.strip()]
def percentile(values,p):
 s=sorted(values);return s[min(len(s)-1,math.ceil(p*len(s))-1)] if s else None
out=[]
for directory in sorted([*root.glob('long-*'),*root.glob('mature-ppo-final-supplement')]):
 path=directory/'report.json'
 if not path.exists():continue
 report=json.loads(path.read_text());records=[]
 for i,r in enumerate(report['runs']):
  raw=json.loads((directory/f'raw-{i}.json').read_text());frames=raw['frames']
  if not frames:continue
  subset=[s for s in samples if frames[0]<=s['monotonic']<=frames[-1]]
  if not subset:records.append(dict(segment=i,samples=0,coverage='missing'));continue
  cpu={role:[sum(p.get('cpuPercent') or 0 for p in s['processes'] if p['role']==role) for s in subset] for role in ('gui','worker','helper')}
  rss=[sum(p['rssMiB'] for p in s['processes']) for s in subset]
  thermal=[v for s in subset for k,v in s['thermal'].items() if k.startswith('cpu')]
  records.append(dict(segment=i,samples=len(subset),approximateCoverageFraction=min(1.,len(subset)*2/r['elapsed']),cpuPercentOneCore100={role:dict(p95=percentile(values,.95),maximum=max(values)) for role,values in cpu.items()},maxDomainRssMiB=max(rss),minAvailableMiB=min(s['availableMiB'] for s in subset),maxCpuThermalC=max(thermal) if thermal else None))
 out.append(dict(case=directory.name,runs=records))
result=dict(cases=out,meaning='CPU 100% means one logical core; worker role aggregates learner and writer. RSS includes diagnostic buffers. Resource samples may cover only part of a segment; raw resource file retained. Thermal labels do not measure GPU/NPU work; no GPU/NPU utilization or power claim.',opticalFPS=False)
(root/'resources-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(cases=len(out))))
