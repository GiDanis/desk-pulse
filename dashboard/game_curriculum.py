"""Versioned driving curriculum and interruptible, paired policy evaluation.

The GUI can import the metadata functions without loading NumPy. Evaluation
uses separate frozen policies/worlds, never the training RNG or a controller
for the learner. Checkpoints include the entire in-flight evaluation.
"""
from copy import deepcopy
import hashlib
import json
import statistics

REWARD_VERSION = 'control-pace-1'
EVALUATION_VERSION = 'paired-10-v1'
PHASE_LABELS = {'control':'Controllo', 'pace':'Passo', 'traffic':'Traffico', 'legacy':'Precedente'}
MIN_VALID = 9
TIME_TOLERANCE = 0.05
REFERENCE_SECONDS = 60.0


def digest(policy):
    return hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def initial_state(traffic=False):
    return {'version':1, 'rewardVersion':REWARD_VERSION, 'evaluationVersion':EVALUATION_VERSION,
            'phase':'traffic' if traffic else 'control', 'phaseUpdates':0,
            'updates':0, 'round':0, 'reliableWindows':0, 'champion':None,
            'baseline':None, 'evaluations':[], 'pending':None}


def pace_weight(state):
    if state['phase']=='control':return 0.0
    return min(1.0, state['phaseUpdates']/8)


def summary(results):
    times=[row['time'] for row in results if row['status']=='arrivato' and row['time'] is not None]
    return {'valid':len(times), 'total':len(results),
            'median':statistics.median(times) if times else None,
            'best':min(times) if times else None,
            'spread':max(times)-min(times) if times else None,
            'contacts':sum(row['status']=='ritirato' for row in results),
            'results':results}


def consider(state, candidate, candidate_result, champion_result, scenarios, scope, profile=None):
    """Only promote against the old champion on the very same scenarios."""
    old=state['champion']
    reliable=candidate_result['valid']>=MIN_VALID
    promotion=reliable and (old is None or (
        candidate_result['valid']>=champion_result['valid'] and
        (champion_result['valid']<MIN_VALID or
         candidate_result['median'] < champion_result['median']-TIME_TOLERANCE)))
    evidence={'round':state['round'], 'phase':state['phase'], 'rewardVersion':REWARD_VERSION,
              'evaluationVersion':EVALUATION_VERSION, 'scope':scope, 'scenarios':scenarios,
              'candidateHash':digest(candidate), 'candidate':candidate_result,
              'championHash':digest(old['policy']) if old else '',
              'champion':champion_result, 'promoted':promotion}
    if promotion:
        state['champion']={'policy':deepcopy(candidate), 'proof':deepcopy(evidence), 'profile':deepcopy(profile)}
        if state['baseline'] is None:state['baseline']=deepcopy(candidate_result)
    state['evaluations']=(state['evaluations']+[evidence])[-40:]
    state['reliableWindows']=state['reliableWindows']+1 if reliable else 0
    phase_changed=state['phase']=='control' and state['reliableWindows']>=2
    if phase_changed:state['phase']='pace';state['phaseUpdates']=0
    state['pending']=None
    return promotion, phase_changed, evidence


class Evaluation:
    def __init__(self, candidate, champion=None, round_number=0, traffic=False, saved=None):
        from game_simulation import World
        from game_learning import Policy
        self.candidate=deepcopy(candidate)
        self.champion=deepcopy(champion)
        self.traffic=traffic
        # Each window is distinct; separate seeds >=1,000,000 are reserved for
        # qualification. Both contestants use exactly the same start perturbation.
        self.scenarios=[1001+round_number*10+i for i in range(10)]
        self.policies=[Policy(candidate)] + ([Policy(champion)] if champion else [])
        self.worlds=[]
        for _ in self.policies:
            if not traffic:
                import numpy as np
                world=World(10,1)
                for i,seed in enumerate(self.scenarios):
                    rng=np.random.default_rng(seed)
                    world.state[i,1]+=rng.uniform(-0.7,0.7)
                    world.state[i,2]=rng.uniform(-0.08,0.08)
                self.worlds.append(world)
                continue
            for seed in self.scenarios:
                world=World(2 if traffic else 1,seed,shared=traffic)
                world.reset(varied=not traffic)
                if traffic:
                    world.state[0,1]+=world.rng.uniform(-0.6,0.6)
                    world.state[0,2]=world.rng.uniform(-0.06,0.06)
                self.worlds.append(world)
        if saved:
            if saved['version']!=EVALUATION_VERSION or saved['scenarios']!=self.scenarios:
                raise ValueError('Valutazione salvata incompatibile')
            for world,snapshot in zip(self.worlds,saved['worlds'],strict=True):world.restore(snapshot)

    def snapshot(self):
        return {'version':EVALUATION_VERSION, 'candidate':self.candidate, 'champion':self.champion,
                'traffic':self.traffic,'scenarios':self.scenarios,
                'worlds':[world.snapshot() for world in self.worlds]}

    def step(self):
        import numpy as np
        from game_simulation import reference_actions
        for i,world in enumerate(self.worlds):
            if not (world.active[0] if self.traffic else world.active.any()) or world.time>=REFERENCE_SECONDS:continue
            if not self.traffic:
                world.step(self.policies[i].act(world.observations()))
                continue
            policy=self.policies[i//10]
            action=policy.act(world.observations()[0])
            if self.traffic:
                bot=reference_actions(world)[1]
                bot[1]=np.clip((7-world.state[1,3])*0.3,-1,1)
                world.step(np.array([action,bot]))
            else:world.step(np.array([action]))
        return all(not (w.active[0] if self.traffic else w.active.any()) or w.time>=REFERENCE_SECONDS for w in self.worlds)

    def results(self):
        groups=[]
        for index in range(len(self.policies)):
            rows=[]
            if not self.traffic:
                world=self.worlds[index]
                for i,(seed,row) in enumerate(zip(self.scenarios,world.rows())):
                    rows.append({'seed':seed,'time':row['finishTime'],'progress':row['progress'],
                                 'status':'tempo scaduto' if world.active[i] else row['status']})
                groups.append(summary(rows))
                continue
            for seed,world in zip(self.scenarios,self.worlds[index*10:(index+1)*10]):
                row=world.rows()[0]
                rows.append({'seed':seed,'time':row['finishTime'],'progress':row['progress'],
                             'status':'tempo scaduto' if world.active[0] else row['status']})
            groups.append(summary(rows))
        return groups[0],groups[1] if len(groups)>1 else None
