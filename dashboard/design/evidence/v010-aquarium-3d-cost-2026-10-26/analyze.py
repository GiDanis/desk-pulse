"""Audit paired native raw data, preserving gates, worst windows and resource units."""
import argparse,csv,json,math,statistics
from pathlib import Path

def percentile(values,q):
    ordered=sorted(values);return ordered[max(0,math.ceil(len(ordered)*q)-1)] if ordered else None
def resources(samples):
    weighted=duration=0
    for before,after in zip(samples,samples[1:]):
        dt=after['elapsed']-before['elapsed']
        if after['cpuPercent'] is not None:weighted+=after['cpuPercent']*dt;duration+=dt
    return {'cpuOneCorePercent':weighted/duration,'rssMedianMiB':statistics.median(x['rssKiB']/1024 for x in samples),'rssFirstMiB':samples[0]['rssKiB']/1024,'rssLastMiB':samples[-1]['rssKiB']/1024,'rssPeakMiB':max(x['rssKiB']/1024 for x in samples),'threadsFirst':samples[0]['threads'],'threadsLast':samples[-1]['threads'],'fdsFirst':samples[0]['fds'],'fdsLast':samples[-1]['fds'],'temperatureMaxC':max(t for x in samples for t in x['temperaturesC'].values())}
def windows(raw,size):
    span=sum(raw)/1000;n=int(span//size);rows=[{'offsetSeconds':i*size,'seconds':size,'callbacks':0,'intervals':[]} for i in range(n)]
    if rows:rows[0]['callbacks']=1
    elapsed=0
    for dt in raw:
        elapsed+=dt/1000;index=int(elapsed//size)
        if index<n:rows[index]['callbacks']+=1;rows[index]['intervals'].append(dt)
    for row in rows:
        data=row.pop('intervals');row.update(callbacksPerSecond=row['callbacks']/size,p95Ms=percentile(data,.95),maxMs=max(data,default=None),stallsOver50Ms=sum(t>50 for t in data))
    return {'completeWindows':n,'partialTailSeconds':span-n*size,'worstCallbackRate':min(rows,key=lambda x:x['callbacksPerSecond']),'worstP95':max((x for x in rows if x['p95Ms'] is not None),key=lambda x:x['p95Ms'],default=None)},rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();receipt=json.loads((a.board/'measure-receipt.json').read_text());protocol=json.loads((a.board/'measure-protocol.json').read_text())
    # Preserve the aborted MSAA stage as incomplete: Qt disabled the requested
    # feature. The two unchanged remaining probes have their own receipt.
    supplement=json.loads((a.board/'supplement-receipt.json').read_text())
    extra_protocol=json.loads((a.board/'supplement-protocol.json').read_text())
    assert receipt['status']=='incomplete' and receipt['cases']==8 and receipt['expectedCases']==11
    assert supplement['status']=='passed' and supplement['cases']==supplement['expectedCases']==2
    assert all(r['productionUnchanged'] and r['sourceUnchanged'] and r['sameBoot'] for r in (receipt,supplement))
    assert receipt['sourceHashes']==protocol['sourceHashes']
    assert receipt['sourceHashes']==supplement['sourceHashes']==extra_protocol['sourceHashes']
    warning='Multisample renderbuffers are not supported, disabling MSAA for Offscreen View3D'
    aa_log=a.board/'measure/aa4-3d/run.log'
    assert warning in aa_log.read_text() and not (aa_log.parent/'report.json').exists()
    unsupported=[{'caseId':'aa4-3d','requestedMsaaSamples':4,'status':'unsupportedInTestedConfiguration','reason':warning,'performanceQualified':False,'log':'board/measure/aa4-3d/run.log'}]
    result=[];csvrows=[]
    recorded=[('measure',r) for r in receipt['results']]+[('supplement',r) for r in supplement['results']]
    assert {r['caseId'] for _,r in recorded}|{r['caseId'] for r in unsupported}=={r[0] for r in protocol['cases']}
    for phase,case in recorded:
        r=json.loads((a.board/phase/case['caseId']/'report.json').read_text());raw=r['rawIntervalsMs']
        assert r['callbacks']==len(raw)+1 and abs(percentile(raw,.95)-r['p95Ms'])<1e-9
        assert not r['qmlWarnings'] and not r['networkAttempts']
        assert all(w=='Particles not supported due to missing RGBA32F and RGBA16F texture format support' for w in r['capabilityWarnings'])
        assert r['actualGlContext']['renderer'] and 'llvmpipe' not in r['actualGlContext']['renderer'].lower()
        row={k:v for k,v in r.items() if k not in ('rawIntervalsMs','resourceSamples')};row['phase']=phase;row['resources']=resources(r['resourceSamples']);row['windows']={}
        for size in (1,10):
            summary,rows=windows(raw,size);row['windows'][str(size)]=summary;csvrows.extend({'caseId':r['caseId'],**w} for w in rows)
        if r['mode']=='3d':
            assert r['renderTarget']=={'width':960,'height':640}
            geom=r['meshes'];row['trianglesPerFish']=geom['body']['triangles']+4*geom['eye']['triangles']+geom['tail']['triangles']+3*geom['fin']['triangles']
            assert r['postMeasurement3dStats']['drawCallCount']>0
        result.append(row)
    groups={}
    for mode in ('2d','3d'):
        rows=[r for r in result if r['caseId'].startswith('nominal-'+mode+'-')];assert len(rows)==3
        groups[mode]={'runs':3,'callbacksMedian':statistics.median(r['callbacksPerSecond'] for r in rows),'p95MinMs':min(r['p95Ms'] for r in rows),'p95MaxMs':max(r['p95Ms'] for r in rows),'p99MaxMs':max(r['p99Ms'] for r in rows),'maxIntervalMs':max(r['maxMs'] for r in rows),'cpuOneCorePercentMedian':statistics.median(r['resources']['cpuOneCorePercent'] for r in rows),'rssMiBMedian':statistics.median(r['resources']['rssMedianMiB'] for r in rows),'rssPeakMiB':max(r['resources']['rssPeakMiB'] for r in rows),'gatePassCount':sum(r['near60SoftwareGate'] for r in rows),'allNear60Gates':all(r['near60SoftwareGate'] for r in rows),'stallsOver50MsTotal':sum(r['stallsOver50Ms'] for r in rows),'missedSlotRatioMax':max(r['estimatedMissedSlotRatio'] for r in rows),'poseHzMin':min(r['poseTicksPerSecond'] for r in rows),'temperatureMaxC':max(r['resources']['temperatureMaxC'] for r in rows)}
    groups['delta3dMinus2d']={'cpuOneCorePercentagePoints':groups['3d']['cpuOneCorePercentMedian']-groups['2d']['cpuOneCorePercentMedian'],'rssMiB':groups['3d']['rssMiBMedian']-groups['2d']['rssMiBMedian'],'cpuRatio':groups['3d']['cpuOneCorePercentMedian']/groups['2d']['cpuOneCorePercentMedian']}
    summary={'status':'completed_with_unsupported_option','plannedCases':11,'measuredCases':len(result),'unsupportedCases':unsupported,'productionUnchanged':True,'sourceUnchanged':True,'nominalSixFish':groups,'cases':result,'scope':'Actual Main private fixture workload. CPU percent of one core, process RSS not GPU VRAM; queue and pose timing not optical FPS. Render counters sampled after measurement. Software gates may fail. MSAA disabled by Qt is an unsupported option, not a passed AA performance test; original incomplete receipt retained.'}
    a.output.mkdir(exist_ok=True,parents=True);(a.output/'comparison-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (a.output/'worst-windows.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    print(json.dumps({'status':summary['status'],'measuredCases':len(result),'unsupportedCases':unsupported,'nominal':groups}))
if __name__=='__main__':main()
