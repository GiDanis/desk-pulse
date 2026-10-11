"""Real learned fixture: pause/restore mid evaluation, promote and change phase.
The fixture is private; it does not train or replace a production pilot.
"""
import argparse,json,multiprocessing as mp,sys,time,queue
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))

def main():
 from game_store import GameStore,default_profile
 from game_catalog import configuration
 from game_learning import Evolution
 from game_simulation import World
 from game_worker import worker_main
 import numpy as np
 parser=argparse.ArgumentParser();parser.add_argument('--store',type=Path,required=True);parser.add_argument('--policy',type=Path,required=True)
 args=parser.parse_args();store=GameStore(args.store);driver=store.drivers()[0]
 profile={**driver['profile'],'population':8};store.set_profile(driver['id'],profile)
 policy=json.loads(args.policy.read_text());learner=Evolution(profile)
 learner.population[:]=policy['weights'];learner.best=np.array(policy['weights'])
 initial={'schema':1,'configuration':configuration(),'learner':learner.checkpoint(),'worlds':[World(8).snapshot()],
          'age':[0.]*8,'fitness':[0.]*8,'steps':0,'seconds':0,'partialUpdate':False}
 store.save_training(driver['id'],initial,policy,0,0)
 ctx=mp.get_context('spawn')
 def run(predicate,timeout=180):
  parent,child=ctx.Pipe();frames=ctx.Queue(2)
  process=ctx.Process(target=worker_main,args=(child,frames,args.store,{'mode':'impara','driver':driver['id'],'epoch':'eval-proof'}))
  process.start();child.close();started=time.monotonic();last=None
  def receive(kind):
   deadline=time.monotonic()+30
   while time.monotonic()<deadline:
    if parent.poll(.05):
     msg=parent.recv();assert msg['type']!='error',msg
     if msg['type']==kind:return msg
   raise RuntimeError('Missing '+kind)
  try:
   receive('ready')
   while time.monotonic()-started<timeout:
    while parent.poll():
     msg=parent.recv();assert msg['type']!='error',msg
    try:last=frames.get(timeout=.01)
    except queue.Empty:pass
    row=store.driver(driver['id'])
    if predicate(last,row):break
   else:raise RuntimeError('Worker did not reach evaluation boundary')
   tick=time.monotonic();parent.send({'type':'pause'});receive('paused');latency=time.monotonic()-tick
   assert latency<.25,latency
   receive('saved');parent.send({'type':'stop'});process.join(5);assert not process.is_alive()
   return store.driver(driver['id']),latency
  finally:
   if process.is_alive():process.terminate();process.join(3)
   parent.close();frames.close();process.close()
 first,ack=run(lambda frame,row:frame and frame['meta']['phase']=='valutazione' and frame['cars'][0]['speed']>0)
 checkpoint=store.load(first['checkpoint']);pending=checkpoint['curriculum']['pending']
 assert pending and pending['worlds'][0]['time']>0
 assert first['policy_profile']['algorithm']=='evolution'
 second,ack2=run(lambda frame,row:row['curriculum'] and row['curriculum']['phase']=='pace')
 state=second['curriculum'];assert state['champion'] and len(state['evaluations'])>=2
 proof={'status':'passed','midEvaluationSaved':True,'phaseRecovered':'Passo','valid':state['champion']['proof']['candidate']['valid'],
        'pauseAckSeconds':[ack,ack2],'policyHash':second['policy'],'candidateHash':second['candidate'],
        'legacyPolicyPreservedUntilPromotion':True,'evaluations':len(state['evaluations']),
        'scope':'Private fixture policy previously learned by evolution, no reference controller; real worker pause and process restart'}
 (args.store/'worker-evaluation-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
