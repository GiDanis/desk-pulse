"""Latch the first coherent GUI state before synchronization, not a forced later frame."""
from pathlib import Path
import argparse
from copy import deepcopy
import json
import math
import statistics
import sys
import threading
import time


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    sys.path.insert(0,str(args.source))
    from theme_fixture_support import isolate_process,LegacyHarness
    private,base=isolate_process()
    from PySide6.QtCore import QObject,Qt,Signal
    from PySide6.QtQml import QQmlEngine,QQmlExpression
    from theme_bundle import BundleManager,validate_project
    valid=validate_project(args.bundle)
    cached=json.loads((args.bundle.parent/'evidence/preflight-cache.json').read_text())
    assert valid['digest']==cached['digest']
    BundleManager(base,app_root=args.source).import_bundle(args.bundle,preflight=lambda *_:cached['result'],require_preflight=True)
    h=None
    class Keypad(QObject):keyPressed=Signal(int)
    records=[]
    try:
        h=LegacyHarness(base,dict(theme='base',variant='day',motion='normal'))
        assert h.service.selectDraft('studio.applecalm')
        h.wait_ready()
        sample=deepcopy(h.sport._snapshot['fixtures'][0])
        fixtures=[]
        for index in range(380):
            row=deepcopy(sample)
            row.update(canonicalMatchId='response-'+str(index),round=str(index//10+1),
                       kickoffUtc=h.now+3600+index*7200,status='scheduled',homeScore=None,awayScore=None)
            fixtures.append(row)
        h.sport._snapshot=dict(h.sport._snapshot,fixtures=fixtures)
        h.sport.changed.emit()
        h.wait_ready()
        keypad=Keypad()
        h.root.setProperty('keypad',keypad)
        host=h.root.findChild(QObject,'overlayHost')
        status_expression=QQmlExpression(QQmlEngine.contextForObject(h.root),h.root,'sport.status')
        gui_thread=threading.get_ident()
        guard=threading.Lock()
        state=dict(serial=0,ready=0,synced=0,expected=None,error='')
        submitted={}
        def animated():
            if threading.get_ident()!=gui_thread:
                state['error']='GUI latch ran outside GUI thread'
                return
            expected=state['expected']
            if not expected:return
            state['gate']=dict(active=host.property('active'),ready=host.property('currentReady'),surface=host.property('contentId'),currentSurface=host.property('currentSurfaceId'),loaded=host.property('loadedRevision'),revision=h.service.revision)
            if not host.property('active') or not host.property('currentReady'):return
            if host.property('contentId')!=expected['surface'] or host.property('currentSurfaceId')!=expected['surface']:return
            if host.property('loadedRevision')!=h.service.revision:return
            contexts=[context for context,generation in h.service.apiFactory._contexts.values()
                      if context.contentId==expected['surface'] and context._snapshots.get('lifecycle',{}).get('active')]
            state['gate']['contexts']=len(contexts)
            if len(contexts)!=1:return
            snapshot=contexts[0]._snapshots
            if expected['surface']=='sport.fixtures':
                state['gate']['selectionIndex']=snapshot.get('selection',{}).get('index')
                if state['gate']['selectionIndex']!=expected['index']:return
            else:
                state['gate']['matchId']=snapshot.get('match',{}).get('id')
                if state['gate']['matchId']!=expected['match']:return
            status,error=status_expression.evaluate()
            if error:
                state['error']='Controller source status expression failed'
                return
            state['gate']['status']=[snapshot.get('source',{}).get('status'),status]
            if state['gate']['status'][0]!=status:return
            with guard:state['ready']=state['serial']
        def synchronize():
            with guard:state['synced']=state['ready']
        def swap():
            with guard:
                if state['synced']:submitted.setdefault(state['synced'],time.perf_counter_ns())
        h.window.afterAnimating.connect(animated,Qt.ConnectionType.DirectConnection)
        h.window.beforeSynchronizing.connect(synchronize,Qt.ConnectionType.DirectConnection)
        h.window.frameSwapped.connect(swap,Qt.ConnectionType.DirectConnection)
        def key(number,category,cycle,expected):
            with guard:
                state.update(serial=state['serial']+1,ready=0,synced=0,expected=expected)
                serial=state['serial']
            before=time.perf_counter_ns()
            keypad.keyPressed.emit(number)
            handler=time.perf_counter_ns()
            h.window.update()
            deadline=time.monotonic()+5
            while serial not in submitted and time.monotonic()<deadline:
                h.app.processEvents()
                time.sleep(.001)
            assert not state['error'],state['error']
            assert serial in submitted,(category,expected,state.get('gate'),h.messages)
            records.append(dict(category=category,cycle=cycle,handlerMs=(handler-before)/1e6,
                                firstCoherentSubmittedMs=(submitted[serial]-before)/1e6))
            state['expected']=None
        for cycle in range(6):
            h.root.setProperty('overlay','')
            h.root.setProperty('overlayStack',[])
            h.root.setProperty('familyId','sports')
            h.root.setProperty('sportHubSelectedId','sport')
            h.wait_ready()
            key(5,'openList',cycle,dict(surface='sport.fixtures',index=0))
            key(8,'listInput',cycle,dict(surface='sport.fixtures',index=1))
            key(2,'listInput',cycle,dict(surface='sport.fixtures',index=0))
            identity=h.value('sportRows')[0]['canonicalMatchId']
            key(5,'openDetail',cycle,dict(surface='sport.match.detail',match=identity))
            key(7,'backToList',cycle,dict(surface='sport.fixtures',index=0))
        assert not h.messages and not h.transport
        h.window.afterAnimating.disconnect(animated)
        h.window.beforeSynchronizing.disconnect(synchronize)
        h.window.frameSwapped.disconnect(swap)
        summaries={}
        for category in sorted({r['category'] for r in records}):
            values=sorted(r['firstCoherentSubmittedMs'] for r in records if r['category']==category and r['cycle']>0)
            summaries[category]=dict(n=len(values),p50Ms=statistics.median(values),
                p95Ms=values[math.ceil(.95*len(values))-1],maxMs=max(values))
        report=dict(status='passed',records=records,warm=summaries,qmlWarnings=h.messages,
            networkAttempts=h.transport,scope='GUI-thread coherence latch, render-thread primitive ticket, software submission; no optical/USB claim')
        args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(status='passed',warm=summaries)),flush=True)
    finally:
        if h:h.close()
        private.cleanup()


if __name__=='__main__':main()
