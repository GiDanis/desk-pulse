"""Real isolated learner lifecycle on private stores, never production data."""
from pathlib import Path
import json,os,queue,tempfile,time,unittest
from unittest.mock import patch
import torch
from game_store import GameStore
from game_lab.models import Actor
from game_lab.skills import initialize,export
from game_process import spawn_role
from game_reference_backend import selected


class ReferenceRuntimeChecks(unittest.TestCase):
    def test_retention_survives_short_sessions_and_keeps_certified_models(self):
        from game_lab.runtime_worker import maintain_checkpoints
        from game_catalog import configuration
        from game_store import canonical
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);driver=next(d for d in store.drivers() if d['name']=='Crono')
            actor=Actor('gru-skip',128);policy=actor.export();policy['origin']={'backend':'sb3-skill-1'}
            with store.connect() as db:db.execute('UPDATE drivers SET profile=? WHERE id=?',
                (canonical({**driver['profile'],'hidden':128,'learningBackend':'sb3-skill-1'}).decode(),driver['id']))
            checkpoints=[];policies=[];binaries=[]
            for n in range(4):
                policy['weights']['head.bias'][0]=n*.001
                binary=Path(root)/'reference-checkpoints'/driver['id']/str(n);binary.mkdir(parents=True)
                (binary/'manifest.json').write_text('{}');binaries.append(binary)
                checkpoint=dict(backend='sb3-skill-1',binary=str(binary.relative_to(root)),configuration=configuration('oval-1','race-68-v3'),task={})
                policies.append(store.save_training(driver['id'],checkpoint,policy,n,0.))
                checkpoints.append(store.driver(driver['id'])['checkpoint'])
            # A historical certified actor remains a portable race root;
            # its obsolete optimizer need not occupy disk indefinitely.
            with store.connect() as db:db.execute('INSERT INTO timed_qualifications VALUES(?,?,?,?)',
                (driver['id'],'fixture-scope',policies[0],canonical(dict(policy=policies[0],bestLap=30.)).decode()))
            old=time.time()-600
            for f in [*store.policies.glob('*.json'),*[d/'manifest.json' for d in binaries]]:os.utime(f,(old,old))
            self.assertFalse(maintain_checkpoints(store,now=old+1))
            reopened=GameStore(root,recover_sessions=False)
            self.assertTrue(maintain_checkpoints(reopened,now=old+302))
            self.assertTrue((store.policies/(policies[0]+'.json')).is_file())
            self.assertFalse((store.policies/(checkpoints[0]+'.json')).exists())
            self.assertFalse(binaries[0].exists());self.assertFalse(binaries[1].exists())
            for n in (2,3):
                self.assertTrue(binaries[n].is_dir());self.assertTrue(store.load(checkpoints[n]))
            self.assertFalse(maintain_checkpoints(reopened,now=old+303))

    def test_isolated_learning_pause_save_restart_and_stop(self):
        for method,mode,name in [('ppo','impara','Crono'),('sac','impara_infinito','Memoria'),('td3','impara_sorpasso','Linea'),('td3','impara_sorpasso','Tattico')]:
            with self.subTest(method=method,mode=mode,name=name):self.lifecycle(method,mode,name)

    def test_pause_during_startup_can_save_zero_steps_and_then_learn(self):
        self.lifecycle('ppo','impara','Crono',early=True)

    def lifecycle(self,method,mode,name,early=False):
        torch.set_num_threads(1);torch.manual_seed(721)
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,SMARTPC_GAME_REFERENCE_EXPERIMENT='1'):
            store=GameStore(root);driver=next(d for d in store.drivers() if d['name']==name)
            # Private synthetic fixture, not an installation or promotion.
            from game_store import canonical
            with store.connect() as db:db.execute('UPDATE drivers SET profile=? WHERE id=?',
                (canonical({**driver['profile'],'learningBackend':'sb3-skill-1'}).decode(),driver['id']))
            driver=store.driver(driver['id'])
            fixture=os.environ.get('SMARTPC_TEST_REFERENCE_POLICY')
            base=json.loads(Path(fixture).read_text()) if fixture else Actor('gru-skip',128).export()
            model,_=initialize(base,method,seed=91)
            policy=export(model);store.save_training(driver['id'],{},policy,0,0)
            store.select_objective(mode)
            request=dict(epoch=7,mode=mode,driver=driver['id'],track='oval-1',bots=2)
            self.assertTrue(selected(root,request));self.assertFalse(selected(root,{**request,'mode':'qualifica'}))
            def run_once(previous,pause_first=False):
                process,link,frames=spawn_role('reference',root,request);messages=[];scenes=[];arrivals={};started=time.monotonic()
                def wait(condition,seconds=20):
                    deadline=time.monotonic()+seconds
                    while time.monotonic()<deadline:
                        try:
                            while link.poll():
                                message=link.recv();messages.append(message)
                                if not message.get('automatic'):arrivals.setdefault(message['type'],time.monotonic())
                            while True:scenes.append(frames.get_nowait())
                        except (queue.Empty,EOFError):pass
                        self.assertFalse(any(m['type'] in ('error','save_failed') for m in messages),messages)
                        if condition():return
                        time.sleep(.005)
                    self.fail('Learner timeout '+str(messages))
                try:
                    if pause_first:pause_at=time.monotonic();link.send({'type':'pause'})
                    wait(lambda:any(m['type']=='ready' for m in messages))
                    session=next(m['run'] for m in messages if m['type']=='ready')
                    if not pause_first:
                        with store.connect() as db:self.assertEqual(db.execute('SELECT status FROM sessions WHERE id=?',(session,)).fetchone()[0],'running')
                    if Path('/proc').exists():
                        self.assertNotIn('libtorch',(Path('/proc')/str(process.pid)/'maps').read_text())
                        child_file=Path('/proc')/str(process.pid)/'task'/str(process.pid)/'children'
                        if child_file.is_file():children=child_file.read_text().split()
                        else:
                            # Some ARM kernels omit CONFIG_PROC_CHILDREN.
                            children=[]
                            for status in Path('/proc').glob('[0-9]*/status'):
                                try:
                                    if ('PPid:\t'+str(process.pid)+'\n') in status.read_text():children.append(status.parent.name)
                                except (FileNotFoundError,PermissionError,ProcessLookupError):pass
                        self.assertEqual(len(children),1)
                        args=(Path('/proc')/children[0]/'cmdline').read_bytes()
                        self.assertIn(b'reference-training',args)
                        self.assertNotIn(b'multiprocessing',args)
                    if not pause_first:
                        wait(lambda:any(s['meta']['learningStats']['decisions']>previous+128 for s in scenes))
                        hold=float(os.environ.get('SMARTPC_TEST_REFERENCE_HOLD','0'))
                        if hold and previous==0 and not early and name==os.environ.get('SMARTPC_TEST_REFERENCE_HOLD_PILOT','Crono'):
                            wait(lambda:time.monotonic()-arrivals['ready']>=hold,seconds=hold+20)
                            self.assertTrue(any(m['type']=='saved' and m.get('automatic') for m in messages))
                            self.assertEqual(scenes[-1]['meta']['phase'],'apprendimento')
                        self.assertTrue(scenes);pause_at=time.monotonic();link.send({'type':'pause'})
                    wait(lambda:any(m['type']=='saved' and not m.get('automatic') for m in messages))
                    kinds=[m['type'] for m in messages if not m.get('automatic')]
                    self.assertLess(kinds.index('pause_pending'),kinds.index('paused'));self.assertLess(kinds.index('paused'),kinds.index('saved'))
                    driver_now=store.driver(driver['id']);checkpoint=store.load(driver_now['checkpoint'])
                    self.assertEqual(checkpoint['backend'],'sb3-skill-1');self.assertTrue((Path(root)/checkpoint['binary']/'manifest.json').is_file())
                    from game_dossier import dossier
                    detail=dossier(store,driver['id']);self.assertTrue(detail)
                    self.assertGreaterEqual(checkpoint['decisions'],previous) if pause_first else self.assertGreater(checkpoint['decisions'],previous)
                    stop_at=time.monotonic();link.send({'type':'stop'})
                    wait(lambda:not process.is_alive())
                    self.assertEqual(store.driver(driver['id'])['checkpoint'],driver_now['checkpoint'],
                        'Stop after durable pause must reuse its exact checkpoint')
                    report_dir=os.environ.get('SMARTPC_TEST_REFERENCE_REPORT')
                    if report_dir and not early:
                        import statistics,math
                        stamps=sorted(set(s['timestamp'] for s in scenes));intervals=sorted(1000*(b-a) for a,b in zip(stamps,stamps[1:]))
                        rates=[s['meta']['simRate'] for s in scenes if s['meta'].get('simRate') is not None]
                        quantile=lambda q:intervals[min(len(intervals)-1,math.ceil(q*len(intervals))-1)] if intervals else None
                        active=sorted(set(s['timestamp'] for s in scenes if s['meta']['phase']=='apprendimento' and arrivals['ready']+1<s['timestamp']<pause_at))
                        gaps=sorted(1000*(b-a) for a,b in zip(active,active[1:]))
                        active_q=lambda q:gaps[min(len(gaps)-1,math.ceil(q*len(gaps))-1)] if gaps else None
                        report=dict(kind='private-lifecycle-software-timing',method=method,mode=mode,pilot=name,previousDecisions=previous,
                            decisions=checkpoint['decisions'],basePolicy=checkpoint['basePolicy'],frames=len(stamps),
                            producerIntervalMs=dict(p50=quantile(.5),p95=quantile(.95),p99=quantile(.99),maximum=max(intervals,default=None)),
                            activeFrameGapMs=dict(p50=active_q(.5),p95=active_q(.95),p99=active_q(.99),maximum=max(gaps,default=None)),
                            activeFrames=len(active),
                            automaticSaves=sum(m['type']=='saved' and bool(m.get('automatic')) for m in messages),
                            medianSimulationRate=statistics.median(rates) if rates else None,
                            pauseAckMs=1000*(arrivals['pause_pending']-pause_at),savedMs=1000*(arrivals['saved']-pause_at),
                            stopMs=1000*(time.monotonic()-stop_at),wallSeconds=time.monotonic()-started,
                            realModelFixture=bool(fixture),qualified=False,installed=False)
                        destination=Path(report_dir);destination.mkdir(parents=True,exist_ok=True)
                        (destination/(name+'-'+str(previous)+'.json')).write_text(json.dumps(report,indent=2)+'\n')
                    return checkpoint['decisions']
                finally:
                    if process.is_alive():process.kill();process.join(1)
                    process.close();link.close()
            steps=run_once(0,pause_first=early);run_once(steps)

if __name__=='__main__':unittest.main()
