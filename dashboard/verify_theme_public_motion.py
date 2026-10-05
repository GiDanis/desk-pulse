#!/usr/bin/env python3
"""Passive frame observations for a real API2 SDK prototype in isolated Main.

Studio's own breathing animation, Qt keypad navigation and one provider-style
synthetic notification create the work. The observer never requests frames or
adds an animation. This is one prototype workload, not universal qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import time

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentile(values, quantile):
    if not values: return None
    values=sorted(values)
    return values[math.floor((len(values)-1)*quantile)]


def statistics(values):
    return {'count':len(values),'p50':percentile(values,.5),'p95':percentile(values,.95),
            'max':max(values) if values else None,'over33ms':sum(value>33 for value in values),
            'over50ms':sum(value>50 for value in values)}


def memory():
    result={'cpuTimeNs':time.process_time_ns()}
    path=Path('/proc/self/smaps_rollup')
    if path.exists():
        for line in path.read_text().splitlines():
            if line.startswith(('Rss:','Pss:')):
                name,value,*_=line.split();result[name[:-1]+'MiB']=int(value)/1024
    return result


def verify(output, capture_dir=None):
    from theme_fixture_support import isolate_process
    private,base=isolate_process()
    harness=None; recording=False; frames=[]
    result={'reportVersion':1,'status':'failed','operation':'publicPrototypeMotion'}
    try:
        from PySide6.QtCore import QCoreApplication,QEvent,QObject,Qt,qVersion
        from PySide6.QtGui import QKeyEvent
        from theme_fixture_support import LegacyHarness
        from theme_test_support import as_value,wait_save
        from theme_runtime import preflight
        from theme_api_contract import ThemeApiContract
        harness=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal'})
        service=harness.service
        project=base/'studio-public-motion'
        shutil.copytree(ROOT/'examples/bundles/studio-ambient',project)
        theme=json.loads((project/'theme.json').read_text());theme['scene']['enabled']=True
        (project/'theme.json').write_text(json.dumps(theme,ensure_ascii=False,indent=2)+'\n')
        # The active auxiliary scene must be owned explicitly, including older kits.
        manifest=json.loads((project/'bundle.json').read_text())
        if 'scene.main' not in manifest['coverage']['surfaces']:
            manifest['coverage']['surfaces'].append('scene.main')
            manifest['coverage']['fallbacks'].remove('scene.main')
            (project/'bundle.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        revision=service.bundles.import_bundle(project,preflight=preflight)
        assert service.reloadCatalog(),service.lastError
        service.beginEdit();assert service.selectDraft(revision['id']),service.lastError
        assert service.setSection('paletteMode','day'),service.lastError
        assert service.setSection('motionMode','normal'),service.lastError
        harness.wait_ready()
        deadline=time.monotonic()+8
        while not service.readyToApply and time.monotonic()<deadline: harness.pump(5)
        assert service.readyToApply,'No coherent real frame acknowledged'
        assert service.apply(),service.lastError
        wait_save(harness.app,service,timeout=8)
        assert service.status=='ready',service.lastError
        scene=harness.root.findChild(QObject,'sceneHost')
        assert scene is not None and scene.property('currentReady') and scene.property('visible')
        public_hosts=[child for child in scene.findChildren(QObject)
                      if child.metaObject().indexOfProperty('currentItem')>=0
                      and child.property('contentId')=='scene.main']
        assert len(public_hosts)==1,'Public scene host not uniquely loaded'
        scene_item=as_value(public_hosts[0].property('currentItem'))
        assert scene_item is not None
        animations=[child for child in scene_item.findChildren(QObject)
                    if 'Animation' in child.metaObject().className()
                    and child.metaObject().indexOfProperty('running')>=0]
        assert any(child.property('running') for child in animations),'Prototype breathing is not active'
        actor=as_value(scene.property('actorState'))
        assert actor is not None and not actor.property('paused')
        actor_id=actor.property('actorId')
        companion=next(child for child in scene_item.findChildren(QObject)
                       if child.metaObject().indexOfProperty('scale')>=0
                       and child.property('width')==26)
        captures=[]
        if capture_dir:
            capture_dir.mkdir(parents=True,exist_ok=True)
            path=capture_dir/'public-prototype-before.png'
            image=harness.window.grabWindow()
            assert not image.isNull() and image.save(str(path)),'Initial screenshot failed'
            captures.append(str(path.resolve()))
        harness.pump(120)
        warnings_before=list(harness.messages)
        assert not warnings_before,warnings_before

        def on_frame():
            # Queued to GUI: no scene reads, cross-thread state or requested update.
            if recording: frames.append(time.perf_counter_ns())
        harness.window.frameSwapped.connect(on_frame,Qt.ConnectionType.QueuedConnection)
        cpu_before=memory();start=time.perf_counter_ns();recording=True
        actions=[];samples=[];notification={};seen_routes={'home.now'}
        plan=[(1.2,6),(2.4,8),(3.6,2),(4.8,1),(6.0,6),(7.2,4),(8.4,6),(9.6,1)]
        next_action=0;next_sample=0.0;duration=12.0
        while (elapsed:=(time.perf_counter_ns()-start)/1e9)<duration:
            if next_action<len(plan) and elapsed>=plan[next_action][0]:
                key=plan[next_action][1];at=time.perf_counter_ns()
                before=harness.value('activeContentId')
                for kind in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
                    QCoreApplication.sendEvent(harness.window,QKeyEvent(kind,Qt.Key_0+key,Qt.KeyboardModifier.NoModifier))
                after=harness.value('activeContentId')
                cold=after not in seen_routes;seen_routes.add(after)
                actions.append({'kind':'navigation','key':key,'atNs':at-start,'before':before,'after':after,
                                'coldFirstUse':cold,'windowNs':400_000_000})
                next_action+=1
            if not notification and elapsed>=5.4:
                at=time.perf_counter_ns();now=harness.now
                event={'version':1,'id':'public-motion:notice','source':'public-motion-fixture',
                       'sourceLabel':'Fixture isolata','category':'demo','priority':2,'notificationRank':2,
                       'bannerSize':'small','title':'Animazione e notifica del tema',
                       'detail':'Evento sintetico pubblicato dal normale engine; nessun dato di produzione.',
                       'issuedAt':now,'startsAt':now-1,'expiresAt':now+3600,'revision':'1',
                       'sourceUrl':'','showOnHome':False}
                assert harness.events.publish_snapshot(event['source'],[event])
                notification={'id':event['id'],'atNs':at-start,'published':True}
                actions.append({'kind':'notification','atNs':at-start,'coldFirstUse':True,'windowNs':500_000_000})
            if elapsed>=next_sample:
                samples.append({'atNs':time.perf_counter_ns()-start,'family':harness.value('familyId'),
                                'view':harness.value('activeContentId'),'actorId':actor.property('actorId'),
                                'actorPaused':actor.property('paused'),'companionScale':companion.property('scale')})
                next_sample+=.5
            harness.pump(4)
        end=time.perf_counter_ns();recording=False
        harness.window.frameSwapped.disconnect(on_frame)
        cpu_after=memory()
        notification['deliveryAcknowledged']=not harness.events.eventState.get('bannerPending',True)
        notification['displayedId']=harness.value('bannerEvent').get('id','')
        notification['deadline']=harness.events._banner_until
        assert notification['displayedId']==notification['id'] and notification['deliveryAcknowledged'],notification
        assert len(frames)>20,'No representative active-animation frame samples'
        assert len({round(sample['companionScale'],3) for sample in samples if not sample['actorPaused']})>2,'Breathing did not progress'
        assert all(sample['actorId']==actor_id for sample in samples),'Actor identity changed during navigation'
        assert next_action==len(plan),'Navigation plan incomplete'
        assert any(action['after']=='weather.now' for action in actions if action['kind']=='navigation'),actions
        assert any(action['after']=='home.now' for action in actions if action['kind']=='navigation'),actions
        if capture_dir:
            path=capture_dir/'public-prototype-after.png';image=harness.window.grabWindow()
            assert not image.isNull() and image.save(str(path)),'Final screenshot failed'
            captures.append(str(path.resolve()))
        raw=[]
        for earlier,later in zip(frames,frames[1:]):
            first=earlier-start;last=later-start
            overlaps=[action for action in actions if last>=action['atNs'] and first<=action['atNs']+action['windowNs']]
            if overlaps:
                action=overlaps[-1];kind=action['kind'];cold=action['coldFirstUse']
            else:kind='sceneOnly';cold=last<1_000_000_000
            raw.append({'fromNs':first,'toNs':last,'ms':(later-earlier)/1e6,'kind':kind,'coldFirstUse':cold})
        categories={name:statistics([row['ms'] for row in raw if row['kind']==kind and (warm is None or row['coldFirstUse'] is not warm)])
                    for name,kind,warm in [('sceneCold','sceneOnly',False),('sceneWarm','sceneOnly',True),
                        ('navigationCold','navigation',False),('navigationWarm','navigation',True),('notification','notification',None)]}
        source_files=['Main.qml','theme_service.py','theme_runtime.py','theme_fixture_support.py',
                      'theme_api.py','theme_contexts.py','components/PublicContextAdapter.qml',
                      'components/SceneHost.qml','components/ViewHost.qml','components/MotionController.qml',
                      'examples/bundles/studio-ambient/qml/Scene.qml','verify_theme_public_motion.py']
        source_manifest=ROOT/'release-manifest.json'
        all_stats=statistics([row['ms'] for row in raw]);ordinary=categories['sceneWarm']['p95']
        result={'reportVersion':1,'status':'passed','operation':'publicPrototypeMotion','qt':qVersion(),
                'backend':os.environ['QT_QPA_PLATFORM'],'machine':platform.machine(),'durationSeconds':(end-start)/1e9,
                'statisticsMethod':'sorted[floor((n-1)*q)], no interpolation','frameCallbacks':len(frames),
                'intervalMs':all_stats,'categories':categories,'rawIntervals':raw,'frameCallbackNs':[stamp-start for stamp in frames],
                'actions':actions,'actorSamples':samples,'notification':notification,'captures':captures,
                'memoryBefore':cpu_before,'memoryAfter':cpu_after,
                'cpuPercentOneCore':100*(cpu_after['cpuTimeNs']-cpu_before['cpuTimeNs'])/(end-start),
                'bundleRevision':{key:revision[key] for key in ('id','version','digest')},
                'apiFingerprint':ThemeApiContract().fingerprint,'sourceSha256':{name:digest(ROOT/name) for name in source_files},
                'sourceManifestSha256':digest(source_manifest) if source_manifest.exists() else None,
                'sourceManifest':json.loads(source_manifest.read_text()) if source_manifest.exists() else None,
                'qmlWarnings':list(harness.messages),'transportAttempts':list(harness.transport),
                'isolation':{'privatePreferences':True,'privateEventsDb':True,'privateProviderFixtures':True,
                             'networkDenied':True,'realBundlePreflight':True,'realCoherentFrameApply':True},
                'informationalTarget':{'ordinaryP95Ms':20,'sceneWarmWithinTarget':ordinary is not None and ordinary<=20,
                                       'navigationWarmWithinTarget':categories['navigationWarm']['p95'] is not None and categories['navigationWarm']['p95']<=20,
                                       'notificationWithinTarget':categories['notification']['p95'] is not None and categories['notification']['p95']<=20,
                                       'functionalPassIsNotPerformanceQualification':True,
                                       'universalThemeQualification':False},
                'observer':{'requestedFrames':False,'addedAnimation':False,'clockTimerStopped':True,
                            'timestampQuality':'Queued GUI callback entry; includes unknown render signal/GIL/event-loop delay'},
                'scope':'One real API2 SDK prototype actor + eight numeric Qt navigation actions + one synthetic production-engine notification. Passive Qt submission callbacks, not GPU/optical timing, physical HID, memory-graphics accounting, 100 theme swaps or endurance.'}
        assert not result['qmlWarnings'],result['qmlWarnings']
        assert not result['transportAttempts'],result['transportAttempts']
        return result
    except Exception as error:
        result.update(error=str(error),qmlWarnings=list(harness.messages) if harness else [],frameCallbacks=len(frames),
                      scope='Failed verification retained; does not establish a performance PASS.')
        return result
    finally:
        recording=False
        if harness: harness.close()
        private.cleanup()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--capture-dir',type=Path)
    args=parser.parse_args()
    result=verify(args.output,args.capture_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    compact={key:value for key,value in result.items() if key not in ('rawIntervals','frameCallbackNs','actorSamples','sourceManifest')}
    print(json.dumps(compact,ensure_ascii=False))
    return 0 if result['status']=='passed' else 1


if __name__=='__main__': raise SystemExit(main())
