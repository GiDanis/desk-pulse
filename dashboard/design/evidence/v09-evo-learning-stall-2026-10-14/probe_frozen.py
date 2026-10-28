"""Matched frozen populations/controls and mutation audit; production read-only.
Private weights are inputs only and are not written into the evidence output.
"""
import argparse,json,sys,time,math,hashlib
from pathlib import Path
from copy import deepcopy
import numpy as np
SOURCE=Path(__file__).resolve().parents[3];sys.path.insert(0,str(SOURCE))
from game_academy import Episode
from game_learning import Evolution,forward,random_weights
from game_batch import BatchPhysics
from game_rewards import specification,reference_time
from game_control import pursuit_actions


def score(e):
    charge=0.
    if e.reason not in ('success','window'):
        charge=.5*max(0.,e.spec['limitSeconds']-(e.age-e.window_started))/reference_time(e.world,e.reward_spec)
    return e.return_total-charge


def frozen(label,population,profile,seeds,controller=None):
    rows=[]
    for seed in seeds:
        episodes=[Episode('oval-1','bend',seed,protocol='driving-memory-1',reward_spec=specification()) for _ in range(len(population))]
        initial=float(episodes[0].world.state[0,3]);batch=BatchPhysics();obs=np.array([e.observations() for e in episodes]);pedals=np.zeros((len(episodes),3));steer=np.zeros(len(episodes));samples=np.zeros(len(episodes))
        first=None
        while any(not e.reason for e in episodes):
            actions=np.tanh(forward(population,obs,profile['hidden']))
            if controller:
                actions=np.array([pursuit_actions(e.world,[0])[0] for e in episodes])
                if controller=='brake':actions[:,1]=-1
                if controller=='gas':actions[:,1]=1
                if controller=='idle':actions[:]=0
            if first is None:first=actions.copy()
            prepared=batch.prepare(episodes,actions)
            for i,e in enumerate(episodes):
                if e.reason:continue
                if e.age<2:
                    steer[i]+=abs(actions[i,0]);samples[i]+=1
                pedals[i,0 if actions[i,1]>.05 else 1 if actions[i,1]<-.05 else 2]+=1
                obs[i],_,_,_=e.step(actions[i],physics=prepared[i])
        for i,e in enumerate(episodes):
            rows.append(dict(label=label,seed=seed,index=i,initialSpeedKmh=initial*3.6,
                reason=e.reason,age=e.age,validProgress=e.valid_progress,rawReturn=e.return_total,
                selectionScore=score(e),trackLimits=int(e.world.track_limits[0]),
                firstAction=first[i].tolist(),earlyMeanAbsSteer=steer[i]/max(1,samples[i]),
                pedalFractions=(pedals[i]/max(1,pedals[i].sum())).tolist(),rewardTerms=e.term_totals))
    return rows


def mutate_audit(profile,current,fresh):
    contexts=[]
    for seed in range(8):
        e=Episode('oval-1','bend',seed,protocol='driving-memory-1',reward_spec=specification());contexts.append(e.observations())
    x=np.array(contexts);n=len(current);split=(68+1)*profile['hidden'];scale=np.ones(current.shape[1]);scale[:split]/=math.sqrt(68);scale[split:]/=math.sqrt(profile['hidden'])
    rows=[]
    for label,p in (('current',current),('fresh',fresh)):
        parent=p[0];before=np.tanh(forward(parent,x,profile['hidden']));results={}
        for name,factor in (('absolute_sigma',np.ones_like(scale)),('fan_in_sigma',scale)):
            rng=np.random.default_rng(1107);noise=rng.normal(0,profile['mutation'],(64,len(parent)))*(rng.random((64,len(parent)))<.25)*factor
            mutated=np.tanh(forward((parent+noise)[:,None,:],x[None,:,:],profile['hidden']))
            results[name]=dict(meanWeightDeltaNorm=float(np.mean(np.linalg.norm(noise,axis=1))),parentNorm=float(np.linalg.norm(parent)),
                meanAbsActionChange=float(np.mean(abs(mutated-before))),
                meanAbsSteerChange=float(np.mean(abs(mutated[:,:,0]-before[:,0]))),
                fractionSteerOver08=float(np.mean(abs(mutated[:,:,0])>.8)))
        rows.append(dict(parent=label,result=results))
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--current',type=Path,required=True);p.add_argument('--before',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    wrapper=json.loads(a.current.read_text());c=wrapper['checkpoint'];profile=wrapper['profile'];old=json.loads(a.before.read_text())
    current=np.array(c['learner']['population']);fresh=Evolution(profile).population
    started=time.monotonic();rows=[]
    cases=[('current_population',current,None),('fresh_population',fresh,None),
           ('current_best',np.array([c['learner']['best']]),None),('current_candidate',np.array([c['learner']['candidate']]),None),
           ('previous_best',np.array([old['learner']['best']]),None)]
    if c.get('memory',{}).get('baseline',{}).get('weights'):cases.append(('memory_baseline',np.array([c['memory']['baseline']['weights']]),None))
    cases.extend((name,np.array([fresh[0]]),control) for name,control in (('reference','reference'),('reference_full_brake','brake'),('reference_full_gas','gas'),('coast','idle')))
    for label,pop,control in cases:
        data=frozen(label,pop,profile,range(8),control);rows.extend(data)
        print(json.dumps(dict(case=label,success=sum(r['reason']=='success' for r in data),total=len(data),medianProgress=float(np.median([r['validProgress'] for r in data])),seconds=round(time.monotonic()-started,1))),flush=True)
    report=dict(scope='PC frozen copies; no learning, production writes, restart or reset',checkpointHash=wrapper['hash'],sourceCheckpoint=c['sourceCheckpoint'],generation=c['learner']['generation'],phaseUpdates=c['curriculum']['phaseUpdates'],profile=profile,
        sourceHashes={name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in ('game_learning.py','game_academy_trainer.py','game_academy.py','game_rewards.py','game_simulation.py')},
        rows=rows,mutationAudit=mutate_audit(profile,current,fresh),wallSeconds=time.monotonic()-started)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
