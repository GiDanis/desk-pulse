"""Offline audit of frozen-source native reports, including worst 1/10/120s."""
import argparse,csv,json,math
from pathlib import Path

def percentile(values,q):
    values=sorted(values)
    return values[max(0,math.ceil(len(values)*q)-1)] if values else None

def windows(intervals,seconds):
    total=sum(intervals)/1000;count=int(total//seconds)
    rows=[{'fromFirstCallbackSeconds':i*seconds,'seconds':seconds,'callbacks':0,'intervals':[]} for i in range(count)]
    if rows:rows[0]['callbacks']=1
    elapsed=0
    for dt in intervals:
        elapsed+=dt/1000;index=int(elapsed//seconds)
        if index<count:
            rows[index]['callbacks']+=1;rows[index]['intervals'].append(dt)
    result=[]
    for row in rows:
        sample=row.pop('intervals');missed=sum(max(0,round(dt/(1000/60))-1) for dt in sample)
        result.append({**row,'callbacksPerSecond':row['callbacks']/seconds,'p95Ms':percentile(sample,.95),'maxMs':max(sample,default=None),'estimatedMissedSlots':missed,'stallsOver50Ms':sum(dt>50 for dt in sample)})
    return {'completeWindows':len(result),'partialTailSeconds':total-count*seconds,'worstCallbackRate':min(result,key=lambda r:r['callbacksPerSecond']) if result else None,'worstP95':max((r for r in result if r['p95Ms'] is not None),key=lambda r:r['p95Ms'],default=None),'rows':result}

def resources(samples):
    if not samples:return None
    weighted=duration=0
    for before,after in zip(samples,samples[1:]):
        if after['cpuPercent'] is not None:
            dt=after['elapsed']-before['elapsed'];weighted+=after['cpuPercent']*dt;duration+=dt
    return {'firstRssMiB':samples[0]['rssKiB']/1024,'lastRssMiB':samples[-1]['rssKiB']/1024,'maxRssMiB':max(s['rssKiB'] for s in samples)/1024,'cpuPercentOfOneCoreMean':weighted/duration if duration else None,'maxTemperatureC':max((t for s in samples for t in s['temperaturesC'].values()),default=None),'firstThreads':samples[0]['threads'],'lastThreads':samples[-1]['threads'],'firstFds':samples[0]['fds'],'lastFds':samples[-1]['fds']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    receipt=json.loads((a.board/'qualification-receipt.json').read_text())
    assert receipt['sameSourceForAllCases'] and receipt['preferencesPreserved']
    assert len(receipt['results'])==15,'Incomplete qualification'
    digest=receipt['sourceTreeSha256'];rows=[];window_csv=[]
    for case in receipt['results']:
        name=case['caseId'];r=json.loads((a.board/'qualification'/name/'report.json').read_text())
        assert r['sourceTreeSha256']==digest and r['caseId']==name
        assert r['status']=='passed' and not r['warnings'] and not r['networkAttempts']
        if 'rawIntervalsMs' not in r:continue
        raw=r['rawIntervalsMs'];assert r['callbacks']==len(raw)+1
        assert abs(percentile(raw,.95)-r['p95Ms'])<1e-9
        row={k:r[k] for k in ('caseId','population','renderer','seconds','callbacksPerSecond','p50Ms','p95Ms','p99Ms','maxMs','estimatedMissedSlots','estimatedMissedSlotRatio','stallsOver50Ms','poseTicks','discardedLongDeltas','near60SoftwareGate')}
        row['resources']=resources(r.get('resourceSamples',[]));row['windows']={}
        for seconds in (1,10,120):
            data=windows(raw,seconds);row['windows'][str(seconds)]={k:v for k,v in data.items() if k!='rows'}
            window_csv.extend({'caseId':name,**w} for w in data['rows'])
        rows.append(row)
    summary={'status':'passed','sourceTreeSha256':digest,'scope':'Queue callbacks/poses in isolated Main; windows relative to first callback, complete bins plus explicitly reported partial tail; not optical FPS/GPU time','cases':rows}
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'benchmark-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (a.output/'benchmark-windows.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(window_csv[0]));writer.writeheader();writer.writerows(window_csv)
    print(json.dumps({'status':'passed','cases':len(rows),'windows':len(window_csv)}))
if __name__=='__main__':main()
