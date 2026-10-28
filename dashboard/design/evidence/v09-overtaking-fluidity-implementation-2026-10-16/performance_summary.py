"""Report raw intervals by run; software callbacks never imply optical FPS."""
from pathlib import Path
import json,math,bisect,argparse
p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);a=p.parse_args();root=a.board

def percentile(values,p):
 s=sorted(values);return s[min(len(s)-1,math.ceil(p*len(s))-1)] if s else None

def statistics(values):return dict(samples=len(values),p95Ms=percentile(values,.95),p99Ms=percentile(values,.99),maxMs=max(values) if values else None,over100=sum(x>100 for x in values))

results=[]
for directory in sorted([*root.glob('long-*'),*root.glob('mature-ppo-final-supplement')]):
 path=directory/'report.json'
 if not path.exists():continue
 report=json.loads(path.read_text());runs=[]
 for index,record in enumerate(report['runs']):
  raw=json.loads((directory/f'raw-{index}.json').read_text());frames=raw['frames'];poses=raw['poses'];packets=raw['packets'];stamps=[p['received'] for p in packets]
  def packet(at):
   pos=bisect.bisect_right(stamps,at)-1
   return packets[max(0,pos)] if packets else {}
  def moving(at):
   sample=packet(at);return sample.get('previewState','running') in ('running','window') and sample.get('speed',1)>.5
  all_spans=[(y-x)*1000 for x,y in zip(frames,frames[1:])]
  moving_spans=[(y-x)*1000 for x,y in zip(frames,frames[1:]) if moving(x) and moving(y) and packet(x).get('resetKey')==packet(y).get('resetKey')]
  presentation=[y['presentedMs']-x['presentedMs'] for x,y in zip(poses,poses[1:]) if moving(x['presentedMs']/1000) and moving(y['presentedMs']/1000) and x['resetKey']==y['resetKey']]
  ages=[v['presentedMs']-v['poseSampleMs'] for v in poses if v.get('poseSampleMs',0)>0 and moving(v['presentedMs']/1000)]
  changes=0;repeated=0;repeat_start=None;max_repeat=0.
  for x,y in zip(poses,poses[1:]):
   if x['resetKey']!=y['resetKey'] or not moving(y['presentedMs']/1000):repeat_start=None;continue
   if math.hypot(x['presentedX']-y['presentedX'],x['presentedY']-y['presentedY'])>1e-7:changes+=1;repeat_start=None
   else:
    repeated+=1
    if repeat_start is None:repeat_start=x['presentedMs']
    max_repeat=max(max_repeat,y['presentedMs']-repeat_start)
  simulated=0.;simulation_wall=0.;phase_seconds={};captures=[]
  for x,y in zip(packets,packets[1:]):
   wall=y['timestamp']-x['timestamp']
   phase_seconds[x.get('phase') or 'unknown']=phase_seconds.get(x.get('phase') or 'unknown',0.)+max(0.,wall)
   if wall>0 and x.get('resetKey')==y.get('resetKey') and x.get('previewState','running') in ('running','window') and y['simTime']>=x['simTime']:
    simulated+=y['simTime']-x['simTime'];simulation_wall+=wall
  for packet_sample in packets:
   checkpoint=packet_sample.get('checkpoint') or {}
   if checkpoint.get('captureMs') is not None:captures.append(checkpoint['captureMs'])
  pstats=statistics(presentation);sstats=statistics(moving_spans)
  gate=bool(sstats['samples'] and sstats['p95Ms']<=50 and sstats['p99Ms']<=66.67 and sstats['over100']==0 and pstats['samples'] and pstats['over100']==0 and percentile(ages,.95)<=200 and max(ages)<=300)
  saving_stalls=[dict(ms=(y-x)*1000,start=x,end=y,checkpointBefore=packet(x).get('checkpoint'),checkpointAfter=packet(y).get('checkpoint')) for x,y in zip(frames,frames[1:]) if (y-x)>.1 and moving(x) and moving(y)]
  runs.append(dict(**record,allSwaps=statistics(all_spans),movingSwaps=sstats,movingPresentation=pstats,poseAge=statistics(ages),
   changedPoses=changes,repeatedMovingPoses=repeated,maxRepeatedPoseMs=max_repeat,simulationWallRate=simulated/simulation_wall if simulation_wall else None,simulationRateWallSeconds=simulation_wall,phaseWallSeconds=phase_seconds,maxCheckpointCaptureMs=max(captures) if captures else None,strictSoftwareGate=gate,stalls=saving_stalls))
 results.append(dict(case=directory.name,theme=report['theme'],load=report['load'],mature=report['mature'],syntheticReplay=report['syntheticOffPolicyReplay'],elapsed=sum(r['elapsed'] for r in runs),runs=runs))
summary=dict(cases=results,strictSoftwareGate=all(r['strictSoftwareGate'] for c in results for r in c['runs']) if results else False,
 opticalFPSCertified=False,meaning='Separate callback cadence, actual interpolated poses and packet freshness; thresholds per run, no averaging away tails. Static preview holds/reset boundaries excluded only from moving metrics, all metrics retained.')
(root/'performance-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(dict(cases=len(results),strictSoftwareGate=summary['strictSoftwareGate'])))
