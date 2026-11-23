"""Evaluate candidate/tactical/race separately on an explicit PRIVATE store."""
from pathlib import Path
import argparse,json,time
import numpy as np
from game_store import GameStore
from game_direct import snapshot,features
from game_learning import Policy
from game_residual import key
from game_lab.environment import make_episode


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=60.)
    p.add_argument('--seeds',type=int,nargs='+',default=[981001]);a=p.parse_args()
    # Refuse the production directory. This tool can initialize store paths.
    if str(a.root.resolve()).startswith('/var/lib/'):raise ValueError('Use an isolated snapshot')
    store=GameStore(a.root);rows=[];started=time.monotonic()
    report=dict(scope='Private store, deterministic policy roles, no training',rows=rows)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for driver in store.drivers():
        if driver['profile']['algorithm']=='race_master':continue
        c=store.load(driver['checkpoint']) if driver.get('checkpoint') else None
        if not c:continue
        state=c['curriculum'];profile=state.get('trainingProfile',driver['profile'])
        roles={'candidate':snapshot(profile,c['learner']['actor']),
            'tactical':(state.get('attackChampion') or state['champion'])['policy'],
            'race':(state.get('raceChampion') or state['champion'])['policy']}
        for role,data in roles.items():
            for bots in (1,2,3):
                for seed in a.seeds:
                    e=make_episode(seed,bots=bots,duration=a.seconds,profile=profile);policy=Policy(data)
                    gates=[];pedals=[];slots=[];trace=[];failure=None
                    while not e.reason:
                        if round(e.world.time*60)%6==0:
                            z=features(e.world)
                            if data.get('architecture')=='neural-experts-2x64-v1':
                                _,cache=__import__('game_neural_mixture').forward(np.asarray(data['weights']),z,True)
                                gates.append(float(cache['gate']))
                            pos=e.world.state;delta=pos[1:,:2]-pos[0,:2]
                            slot=tuple((np.argsort(np.linalg.norm(delta,axis=1))[:3]+1).tolist())
                            if slots and slot!=slots[-1]:trace.append(dict(time=e.age,rivals=list(slot)))
                            slots.append(slot)
                        command=policy.act(None,world=e.world,index=0)
                        if round(e.world.time*60)%6==0:pedals.append(float(command[1]))
                        before=(e.contact_count,int(e.world.track_limits[0]))
                        e.step(command,return_observation=False)
                        if failure is None and before!=(e.contact_count,int(e.world.track_limits[0])):
                            failure=dict(time=e.age,command=command.tolist(),speed=float(e.world.state[0,3]),
                                progress=float(e.world.progress[0]),rivalGaps=(e.world.progress[1:]-e.world.progress[0]).tolist())
                    rows.append(dict(pilot=driver['name'],role=role,policyHash=key(data),bots=bots,seed=seed,
                        result=e.result(),firstFailure=failure,rivalSlotChanges=trace[:32],
                        gateMean=float(np.mean(gates)) if gates else None,
                        gateSaturatedFraction=float(np.mean((np.array(gates)<.02)|(np.array(gates)>.98))) if gates else None,
                        meanPedal=float(np.mean(pedals)),updates=c['learner'].get('update'),steps=c['steps']))
                    report['wallSeconds']=time.monotonic()-started
                    a.output.write_text(json.dumps(report,indent=2)+'\n')
                    print(driver['name'],role,bots,e.passes,e.contact_count,int(e.world.track_limits[0]),flush=True)


if __name__=='__main__':main()
