"""Private Main navigation/alerts benchmark and mixed stability run on EGLFS.

Same fixed fixture inputs and actions for Base/Apple before/after. Callback and
coherent-host timing is software evidence, not optical FPS or direct GPU time.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

p=argparse.ArgumentParser();p.add_argument('--dashboard',type=Path,required=True)
p.add_argument('--bundle',type=Path);p.add_argument('--cache',type=Path)
p.add_argument('--theme',choices=('base','functional','apple'),default='apple')
p.add_argument('--variant',choices=('day','night'),default='day')
p.add_argument('--motion',choices=('normal','reduced','off'),default='normal')
p.add_argument('--seconds',type=int,default=60);p.add_argument('--warmup',type=int,default=30)
p.add_argument('--legacy-pump',action='store_true',help='Diagnostic negative control: do not drain DeferredDelete')
p.add_argument('--output',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.dashboard.resolve()))
from theme_fixture_support import isolate_process
private,base=isolate_process()
from theme_fixture_support import LegacyHarness
from theme_bundle import BundleManager,validate_project
from PySide6.QtCore import QObject,qVersion,QCoreApplication,QEvent

identity=None
if a.theme=='apple':
    valid=validate_project(a.bundle)
    cache=json.loads(a.cache.read_text())
    assert cache['digest']==valid['digest'] and cache['result']['qt']==qVersion()
    identity=BundleManager(base,app_root=a.dashboard).import_bundle(a.bundle,
                    preflight=lambda *_:cache['result'],require_preflight=True)
h=LegacyHarness(base,dict(theme='functional' if a.theme=='functional' else 'base',
                         variant=a.variant,motion=a.motion))
if not a.legacy_pump:
    original_pump=h.pump
    def pump(ms=30):
        original_pump(ms)
        # Unlike app.exec(), repeated processEvents() does not handle deferred
        # deletion on its own. Simulate the normal event-loop boundary so the
        # benchmark does not retain retired QML renderers indefinitely.
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    h.pump=pump
a.output.mkdir(parents=True,exist_ok=True)
intervals=[];ready=[];memory=[];cpu=[];captures=[];window_until=0;last=None
def frame():
    global last
    now=time.perf_counter()
    if now<=window_until:
        if last is not None:intervals.append((now-last)*1000)
        last=now
h.window.frameSwapped.connect(frame)

def sample():
    vals={}
    for line in Path('/proc/self/smaps_rollup').read_text().splitlines():
        if line.startswith(('Rss:','Pss:','Swap:')):
            k,v,*_=line.split();vals[k[:-1]]=int(v)
    def number(path):
        try:return int(path.read_text().strip())
        except (OSError,ValueError):return None
    platform={
        'temperaturesMilliC':{z.name:number(z/'temp') for z in Path('/sys/class/thermal').glob('thermal_zone*')},
        'devfreqHz':{d.name:number(d/'cur_freq') for d in Path('/sys/class/devfreq').glob('*')},
        'cpuFrequencyKHz':{d.name:number(d/'scaling_cur_freq') for d in Path('/sys/devices/system/cpu/cpufreq').glob('policy*')}}
    memory.append(dict(at=time.monotonic(),contexts=len(h.service.apiFactory._contexts),
                       leases=len(h.service._leases),qmlObjects=len(h.root.findChildren(QObject)),platform=platform,**vals))
    threads={}
    for td in Path('/proc/self/task').iterdir():
        try:
            stat=(td/'stat').read_text().rsplit(')',1)[1].split()
            threads[td.name]={'name':(td/'comm').read_text().strip(),'ticks':int(stat[11])+int(stat[12])}
        except OSError:pass
    cpu.append(dict(at=time.monotonic(),threads=threads))

def capture(name):
    assert h.window.grabWindow().save(str(a.output/(name+'.png')));captures.append(name)

routes=[('home','familyId="oggi";viewIndex=[0,0,0,0,0,0,0,0,0]'),
        ('clock','viewIndex=[1,0,0,0,0,0,0,0,0]'),('weather','familyId="meteo"'),
        ('account','familyId="account"'),('sport','familyId="sport"'),
        ('casa','familyId="casa"'),('network','familyId="network"'),
        ('menu','pushOverlay("menu")'),('settings','popOverlay();pushOverlay("settings")'),
        ('appearance','popOverlay();pushOverlay("appearance")'),
        ('chooser','openThemeChooser()'),('return','home()')]
try:
    if identity:
        assert h.service.selectDraft(identity['id']);h.wait_ready()
    assert h.service.setToken('typography.textScale',1.1);h.wait_ready()
    # Explicit full activation and save, so restart semantics are exercised in
    # an isolated store rather than editing production preferences.
    h.window.update()
    deadline=time.monotonic()+10
    while not h.service.readyToApply and time.monotonic()<deadline:h.pump(10)
    assert h.service.apply(),h.service.lastError
    from theme_test_support import wait_save
    wait_save(h.app,h.service,timeout=10);h.wait_ready()
    capture('home-'+a.variant)
    h.pump(a.warmup*1000)
    start=time.monotonic();count=0;sample()
    while time.monotonic()-start<a.seconds:
        name,code=routes[count%len(routes)]
        window_until=time.perf_counter()+.35;last=None;t=time.perf_counter()
        previous_revision=h.service.revision
        h.expression(code);h.wait_ready();ready.append(dict(route=name,ms=(time.perf_counter()-t)*1000,
                    revisionBefore=previous_revision,revisionAfter=h.service.revision))
        h.pump(500)
        if count%len(routes)==len(routes)-1:
            h.events.set_demo_scenario('urgente');h.pump(120)
            assert h.value('urgentEvent').get('id');h.expression('activateKey(7)');h.pump(100)
            assert not h.value('urgentEvent')
            assert h.service.activeThemeId==('studio.applecalm' if identity else a.theme)
        if count%10==0:sample()
        if count and count%100==0:
            print(json.dumps({'progressSeconds':round(time.monotonic()-start,1),
                              'actions':count,'qmlWarnings':len(h.messages),'memoryKiB':memory[-1]}),flush=True)
        if count in (7,10):capture(name)
        assert not h.messages,h.messages
        count+=1
    sample();elapsed=time.monotonic()-start
    def stats(vals):
        vals=sorted(vals)
        return {k:vals[int((len(vals)-1)*q)] if vals else None for k,q in
                [('median',.5),('p95',.95),('p99',.99),('max',1)]}
    first,lastcpu=cpu[0],cpu[-1];hz=os.sysconf('SC_CLK_TCK');usage={}
    for tid,r in lastcpu['threads'].items():
        if tid in first['threads']:
            usage[tid]={'name':r['name'],'percentOneCore':100*(r['ticks']-first['threads'][tid]['ticks'])/hz/(lastcpu['at']-first['at'])}
    capture('final')
    report=dict(status='passed',qt=qVersion(),backend=os.environ['QT_QPA_PLATFORM'],
        theme=a.theme,bundle={k:identity[k] for k in ('id','version','digest')} if identity else None,
        variant=a.variant,motion=a.motion,textScale=1.1,seconds=elapsed,warmup=a.warmup,
        actions=count,readyMs=stats([r['ms'] for r in ready]),routes=ready,
        frameMs=stats(intervals),frames=len(intervals),stallsOver100ms=sum(x>100 for x in intervals),
        memoryKiB=memory,cpu=usage,captures=captures,qmlWarnings=h.messages,
        transportAttempts=h.transport,scope=__doc__)
    report['deferredDeletesDrained']=not a.legacy_pump
    report['appearancePublicationsDuringNavigation']=sum(max(0,r['revisionAfter']-r['revisionBefore']) for r in ready)
    assert not h.transport,h.transport
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('routes','memoryKiB')}),flush=True)
finally:
    h.close();private.cleanup()
