"""Paired, interruptible comparison before replacing an infinite local branch."""
from copy import deepcopy
import random
from game_academy import Episode
from game_learning import Policy,policy_snapshot
from game_observation_contract import bind,migrate


def candidate(checkpoint,profile):
    c=migrate(checkpoint);b=c['learner'];algorithm=profile['algorithm']
    if algorithm=='clone_ppo':
        from game_hybrid import ClonePPO
        result=ClonePPO(profile,b).policy()
    elif algorithm=='neat':
        # NEAT-Python owns a process-global RNG. Reading a donor must not advance it.
        state=random.getstate()
        try:
            from game_neat import NEAT
            result=NEAT(profile,b).candidate_policy()
        finally:random.setstate(state)
    else:
        key='actor' if algorithm in ('ppo','ppo_smooth') else 'weights' if algorithm=='imitation' else 'candidate'
        weights=b.get(key) or b.get('best')
        result=policy_snapshot(weights,profile['hidden'],algorithm)
    return bind(result,c['inputContract'])


class BranchCheck:
    def __init__(self,track,local,donor,saved=None):
        self.candidate=deepcopy(donor);self.local=deepcopy(local);self.cursor=0
        self.episodes=[];self.policies=[Policy(local),Policy(donor)]
        for _ in self.policies:
            for seed in (8201001,8201002):
                self.episodes.append(Episode(track,'launch',seed,protocol='driving-memory-1',launch_distance=20.))
                e=Episode(track,'control',seed,protocol='driving-memory-1',objective='impara_infinito')
                e.spec['limitSeconds']=120.;self.episodes.append(e)
        if saved:
            self.cursor=saved['cursor']
            self.episodes=[Episode(s['track_id'],s['phase'],s['seed'],saved=s) for s in saved['episodes']]
        for e in self.episodes:e.world.native_sensors=True

    def tick(self):
        for _ in self.episodes:
            index=self.cursor%len(self.episodes);self.cursor+=1;e=self.episodes[index]
            if not e.reason:
                p=self.policies[index//4]
                e.step(p.act(e.observations(),world=e.world,index=0));break
        return all(e.reason for e in self.episodes)

    def result(self):
        rows=[]
        for offset in (0,4):
            part=self.episodes[offset:offset+4];endurance=part[1::2]
            rows.append(dict(launches=sum(e.reason=='success' for e in part[::2]),
                cleanLaps=sum(int(e.world.clean_laps[0]) for e in endurance),
                meters=sum(e.valid_progress for e in endurance),
                survivalSeconds=min(e.age for e in endurance),
                trackLimits=sum(int(e.world.track_limits[0]) for e in endurance)))
        local,donor=rows
        key=lambda r:(r['launches'],r['cleanLaps'],-r['trackLimits'],r['meters'])
        adopt=donor['launches']==2 and donor['cleanLaps']>=2 and key(donor)>key(local)
        return dict(version='paired-branch-1',adopted=adopt,local=local,donor=donor,
                    trials=8,secondsPerEndurance=120.,seeds=[8201001,8201002])

    def snapshot(self):
        return dict(cursor=self.cursor,local=self.local,candidate=self.candidate,
                    episodes=[e.snapshot() for e in self.episodes])
