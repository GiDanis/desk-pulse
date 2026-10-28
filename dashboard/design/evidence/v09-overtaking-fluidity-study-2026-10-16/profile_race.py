"""PC hotspot locator, not a live frame-rate or board benchmark."""
from pathlib import Path
import cProfile,pstats,json,platform,sys,time,pickle
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'dashboard'))
from game_simulation import World
from game_residual import profile,snapshot,initial_weights
from game_catalog import RACE_PHYSICS_VERSION
from game_learning import Policy
from game_control import frozen_actions
from game_native import available


def main():
    policies=[]
    for i,m in enumerate(('race_master','residual_ppo','residual_sac','residual_td3','residual_tactic')):
        p=profile(i+1,m);policies.append(Policy(snapshot(p,None if m=='race_master' else initial_weights(p))))
    w=World(5,47,shared=True,laps=5,physics=RACE_PHYSICS_VERSION,telemetry=True);w.reset(varied=False);w.native_sensors=True;w.enable_timing('gara')
    def tick(n):
        for k in range(n):
            w.step(frozen_actions(w,policies),return_observations=False)
            if k%2==0:
                rows=w.rows();obs=w.observations(version='race-68-v3')[0]
                pickle.dumps(dict(cars=rows,sensors=obs[:5].tolist(),time=w.time))
    tick(120);pr=cProfile.Profile();start=time.monotonic();pr.enable();tick(1000);pr.disable();seconds=time.monotonic()-start
    stats=pstats.Stats(pr);rows=[]
    for (file,line,fn),(primitive,calls,selftime,cumtime,callers) in stats.stats.items():
        if file.startswith(str(ROOT/'dashboard')):rows.append(dict(file=Path(file).name,line=line,function=fn,calls=calls,selfSeconds=selftime,cumulativeSeconds=cumtime))
    rows.sort(key=lambda x:x['cumulativeSeconds'],reverse=True)
    result=dict(scope='instrumented PC, 1000 physics ticks, actual five frozen policies and 30Hz row/sensor/pickle cadence; excludes Qt/IPC feeder/GUI/disk',python=platform.python_version(),machine=platform.machine(),nativeSensorsAvailable=available(),secondsWithProfiler=seconds,simulatedSeconds=1000/60,hotspots=rows[:32])
    Path(__file__).with_name('profile-race.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
