"""Read-only offline authority probes; no training, no production changes."""
import argparse,hashlib,json,time,math
from pathlib import Path
import numpy as np
from game_residual import snapshot,initial_weights,controls,key
from game_learning import Policy
from game_control import racing_actions
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_academy import Episode
from game_rewards import specification,reference_time


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();c=json.loads(args.checkpoint.read_text());board=json.loads(args.snapshot.read_text());p=board['profile']
    source=Path(__file__).resolve().parents[3]
    hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in board['sourceHashes']}
    assert hashes==board['sourceHashes'],'Local runtime differs from installed source'
    policies=dict(base=snapshot(p,initial_weights(p)),champion=c['curriculum']['champion']['policy'],candidate=snapshot(p,c['learner']['actor']))
    cases=[(name,Policy(data)) for name,data in policies.items()]
    cases += [(label,('fixed',lane)) for label,lane in (('upper-pace-center',0.),('upper-pace-left',.5),('upper-pace-right',-.5))]
    cases += [('private-base-speed-'+str(factor),('speed',factor)) for factor in (1.5,1.8)]
    def action(controller,w):
        if isinstance(controller,Policy):return controller.act(None,world=w,index=0)
        return controls(w,[[controller[1],1.]],[0])[0] if controller[0]=='fixed' else racing_actions(w,[0],speed_factor=controller[1])[0]
    results=[];started=time.monotonic()
    for name,controller in cases:
        w=World(1,71,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
        w.reset(varied=False);w.native_sensors=True;samples=[]
        for tick in range(12000):
            u=action(controller,w)
            if tick%6==0:
                offset,tangent,phase=w.coordinates();phase=float(phase[0])-36
                angles=w.track.poses(np.array([phase-1,phase+1]))[:,2]
                curve=abs(float((angles[1]-angles[0]+np.pi)%(2*np.pi)-np.pi)/2)>.005
                residual=getattr(w,'residual_previous',np.zeros((1,2)))[0]
                samples.append([w.time,float(w.state[0,3])*3.6,float(offset[0]),int(curve),float(u[0]),float(u[1]),*map(float,residual)])
            w.step(np.array([u]),return_observations=False)
            if not w.active.any():break
        a=np.asarray(samples);moving=a[a[:,0]>5]
        e=Episode('oval-1','pace',91001,protocol='driving-memory-1',single_lap=True,reward_spec=specification(p),pace_pressure=1.)
        e.world.native_sensors=True
        for tick in range(12000):
            e.step(action(controller,e.world),return_observation=False)
            if e.reason:break
        row=dict(case=name,kind='frozen-network' if isinstance(controller,Policy) else 'fixed-action-no-learning' if controller[0]=='fixed' else 'private-authority-probe-outside-production-action-range',
            laps=w.lap_times[0],completedLaps=int(w.lap_count[0]),cleanLaps=int(w.clean_laps[0]),retired=bool(w.retired[0]),trackLimits=int(w.track_limits[0]),
            maxSpeedKmh=float(a[:,1].max()),meanMovingSpeedKmh=float(moving[:,1].mean()),
            straightSpeedKmh=np.percentile(moving[moving[:,3]==0,1],[5,50,95]).tolist(),cornerSpeedKmh=np.percentile(moving[moving[:,3]==1,1],[5,50,95]).tolist(),
            offsetRangeMeters=[float(a[:,2].min()),float(a[:,2].max())],steerRange=[float(a[:,4].min()),float(a[:,4].max())],
            brakeFraction=float(np.mean(moving[:,5]<-.05)),gasFraction=float(np.mean(moving[:,5]>.05)),
            residualLineQuantiles=np.percentile(moving[:,6],[5,50,95]).tolist(),residualPaceQuantiles=np.percentile(moving[:,7],[5,50,95]).tolist(),
            trainingProbe=dict(seed=91001,reason=e.reason,seconds=e.age,returnTotal=e.return_total,terms=e.term_totals,referenceSeconds=reference_time(e.world,e.reward_spec)))
        if isinstance(controller,Policy):row['policyHash']=key(controller.snapshot)
        results.append(row);print(name,round(row['maxSpeedKmh'],2),row['completedLaps'],row['trackLimits'],flush=True)
    std=np.exp(np.asarray(c['learner']['logStd']));margin=12/2-1.8/2-.9
    out=dict(scope='Deterministic diagnostics on one saved Crono and one seed; not a learning comparison or a promoted preset',
        checkpoint=board['driver']['checkpoint'],sourceHashes=hashes,physicalStepsPerSecond=60,decisionHz=10,
        rawStd=std.tolist(),lateralTargetStdNearZeroMeters=float(margin*std[0]),paceFactorStdNearZero=float(.25*std[1]),
        gaeSeconds=1.6,rolloutSeconds=12.8,discountSeconds=40.,productionTargetSpeedUpperKmh=45.,results=results,wallSeconds=time.monotonic()-started)
    args.output.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':main()
