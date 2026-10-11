"""Real worker checkpoints and completed race across a physical reboot, isolated store."""
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time
sys.path.insert(0,'/opt/smartpc/dashboard')
ROOT=Path('/var/lib/smartpc-dashboard/v09-game-install-rc3-proof/boot-game')

def run(request, training=False, expected_steps=None):
    from game_worker import worker_main
    context=mp.get_context('spawn');parent,child=context.Pipe();frames=context.Queue(2)
    process=context.Process(target=worker_main,args=(child,frames,ROOT,{**request,'epoch':'durability'}))
    process.start();child.close()
    def receive(kind):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if parent.poll(.05):
                message=parent.recv()
                assert message['type']!='error',message
                if message['type']==kind:return message
        raise RuntimeError('Ack mancante: '+kind)
    try:
        receive('ready')
        if training:
            if expected_steps is None:time.sleep(.2)
            else:
                import queue
                deadline=time.monotonic()+20
                while True:
                    try:
                        frame=frames.get(timeout=.05)
                        if frame.get('meta',{}).get('steps',0)>expected_steps:break
                    except queue.Empty:pass
                    if time.monotonic()>deadline:raise RuntimeError('Nessun nuovo passo dopo la ripresa')
            parent.send({'type':'pause'});receive('paused');saved=receive('saved')
        else:receive('finished');saved=None
        parent.send({'type':'stop'});process.join(5);assert not process.is_alive()
        return saved
    finally:
        if process.is_alive():process.terminate();process.join(2)
        parent.close();frames.close();process.close()

def main():
    from game_store import GameStore
    from game_learning import Evolution
    phase=sys.argv[1];store=GameStore(ROOT)
    proof=ROOT.parent/'boot-game-before.json'
    if phase=='before':
        training=[]
        for driver,method in zip(store.drivers(),('evolution','ppo','neat')):
            store.set_profile(driver['id'],{**driver['profile'],'algorithm':method,'population':8,'rollout':64})
            run({'mode':'impara','driver':driver['id']},True)
            training.append(store.driver(driver['id']))
        racers=[]
        for i in range(2):
            identity=store.create_driver('Fixture gara '+str(i+1));driver=store.driver(identity)
            learner=Evolution(driver['profile']);fixture=learner.policy()
            fixture['weights']=[0.0]*len(fixture['weights']);fixture['weights'][-2:]=[2+i*.01,2]
            store.save_training(identity,learner.checkpoint(),fixture,100,1);racers.append(identity)
        run({'mode':'gara','participants':racers})
        data={'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'drivers':training,'races':store.sessions('gara')}
        proof.write_text(json.dumps(data,indent=2)+'\n')
    else:
        before=json.loads(proof.read_text())
        assert before['bootId']!=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        assert store.sessions('gara')==before['races']
        resumed=[]
        for prior in before['drivers']:
            assert store.driver(prior['id'])==prior
        for prior in before['drivers']:
            current=store.driver(prior['id'])
            store.load(current['candidate'] or current['policy']);store.load(current['checkpoint'])
            assert run({'mode':'impara','driver':current['id']},True,current['steps'])['steps']>current['steps']
            resumed.append(current['profile']['algorithm'])
        assert not any(s['status'] in ('running','paused') for s in store.sessions(complete=False))
        data={'status':'passed','resumed':resumed,'racePreserved':True,'automaticStart':False,
              'scope':'Isolated qualification pilots; no production pilot training or fabricated driving competence'}
        (ROOT.parent/'boot-game-after.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'phase':phase,'status':'passed'}))

if __name__=='__main__':main()
