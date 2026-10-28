"""Versioned Evo curriculum, stratified suites and independent stage checks.

No policy assistance. All candidates run the same scenarios, in sequence;
retention is part of the selection and never resets the main-task counters.
"""
from copy import deepcopy
from functools import lru_cache
import math
import numpy as np
from game_geometry import get_track,_bend_entries
from game_curriculum import summary

VERSION='evo-progressive-1'
CHECK_VERSION='evo-stage-check-1'
# phase, label, distance (None = lap), initial speed, start relative to bend entry
STAGES=(
 ('launch','Partenza · 1 m',1.,0.,None),
 ('launch','Partenza · 3 m',3.,0.,None),
 ('launch','Partenza · 8 m',8.,0.,None),
 ('launch','Partenza · 20 m',20.,0.,None),
 ('straight','Rettilineo · 40 m',40.,0.,None),
 ('bend','Arco lento · 20 m',20.,3.,35.),
 ('bend','Arco lento · 50 m',50.,4.5,35.),
 ('bend','Ingresso curva · 60 m',60.,6.,10.),
 ('bend','Curva completa · 140 m',140.,8.,0.),
 ('bend','Curva veloce · 140 m',140.,11.,0.),
 ('control','Un giro pulito',None,0.,None),
)


@lru_cache(maxsize=64)
def straight_start(track_id,distance):
    track=get_track(track_id)
    if track.oval:return 36.-distance-12.
    candidates=np.linspace(0,track.length,256,endpoint=False)
    angle=track.poses(candidates[:,None]+np.linspace(0,distance+8,16)[None,:])[:,:,2]
    turn=np.abs((np.diff(angle,axis=1)+math.pi)%(2*math.pi)-math.pi).sum(axis=1)
    return float(candidates[int(np.argmin(turn))])


def stage_scenario(track_id,level,seed,retention=False,retention_goal=20.):
    track=get_track(track_id)
    phase,label,distance,speed,shift=STAGES[min(level,len(STAGES)-1)]
    if retention:phase,label,distance,speed,shift='launch','Ripasso Partenza · '+str(int(retention_goal))+' m',retention_goal,0.,None
    if distance is None:distance=track.length
    start=0.
    if phase in ('launch','straight'):
        start=straight_start(track_id,distance)
    elif phase=='bend':
        entries=_bend_entries(track_id)
        # The bank alternates geometry; speed stays fixed until stage promotion.
        start=float(entries[int(seed)%len(entries)]+shift)
    return dict(phase=phase,label=label,distance=float(distance),start=start,speed=speed,
                limitSeconds=max(12.,distance/3+8) if phase!='control' else max(60.,track.length/3+15),
                stage=level,version=VERSION,role='retention' if retention else 'primary')


class EvoPlan:
    def __init__(self,state,profile,track,coverage=()):
        self.state=state;self.profile=profile;self.track=track
        self.coverage=sorted([deepcopy(c) for c in coverage if c['track']!=track],key=lambda c:(c['track'],c['phase']))
        self.data=state.setdefault('evoTraining',dict(version=VERSION,level=0,generations=0,
            stageGenerations=0,case=0,results=[],reliable=0,archives={},recent=[]))
        if self.data['version']!=VERSION:raise ValueError('Protocollo Evo incompatibile')
        self.sync()

    @property
    def graduated(self):return self.data['level']>=len(STAGES)

    def sync(self):
        if not self.graduated:
            phase,_,goal,_,_=STAGES[self.data['level']]
            self.state['phase']=phase
            if phase=='launch':self.state['launchGoal']=goal

    def cases(self,held=False):
        level=self.data['level'];count=4 if held else 2
        base=self.profile['seed']*100000+level*64+(7000000 if held else 1000000)
        cases=[]
        for i in range(count):
            seed=base+i
            scenario=None if self.graduated else stage_scenario(self.track,level,seed)
            cases.append(dict(seed=seed,phase=self.state['phase'],scenario=scenario))
        if self.state['phase']!='launch':
            for i in range(2 if held else 1):
                seed=base+32+i
                cases.append(dict(seed=seed,phase='launch',scenario=stage_scenario(self.track,level,seed,True)))
            if self.coverage:
                old=self.coverage[level%len(self.coverage)]
                cases.append(dict(seed=base+48,track=old['track'],phase=old['phase'],scenario=None,
                                  context=old.get('configuration')))
        return cases

    def context(self):
        # Stable bank, stage and objective, independent of the current retention case.
        return (VERSION,self.track,self.data['level'],self.state['phase'],self.state['pacePressure'])

    def take_results(self,episodes,scores):
        self.data['results'].append([dict(success=e.reason=='success',progress=min(1.,e.valid_progress/max(1,e.spec['distance'] or e.world.track.length)),
            reason=e.reason,score=float(s),time=e.age) for e,s in zip(episodes,scores)])
        if self.data['case']+1<len(self.cases()):
            self.data['case']+=1;return None
        results=self.data['results'];main=results[:2];retention=results[2:]
        mean=np.mean([[r['score'] for r in rows] for rows in results],axis=0)
        success=np.sum([[r['success'] for r in rows] for rows in main],axis=0)
        retained=np.sum([[r['success'] for r in rows] for rows in retention],axis=0) if retention else np.zeros(len(mean))
        # Retention is a separate objective, not an unreported episode reward.
        # Once both main cases are solved, a launch-capable policy ranks first.
        ranks=np.column_stack((success+retained,retained,success,mean))
        self.data['case']=0;self.data['results']=[]
        self.data['generations']+=1;self.data['stageGenerations']+=1
        self.data['recent']=(self.data['recent']+[dict(generation=self.data['generations'],
            primarySuccess=int(success.max()),primaryTotal=2,retained=bool(retained[np.lexsort(tuple(-ranks[:,i] for i in range(3,-1,-1)))[0]]),
            meanScore=float(np.max(mean)))])[-32:]
        return mean,ranks

    def save_archive(self,learner):
        key=str(self.data['level'])+':'+self.state['phase']
        self.data['archives'][key]=dict(policy=deepcopy(learner.candidate_policy()),
            quality=deepcopy(getattr(learner,'current_key',None)),generations=self.data['stageGenerations'])

    def should_check(self):return not self.graduated and (self.data['stageGenerations']==1 or self.data['stageGenerations']%4==0)

    def accept(self,result):
        self.data['reliable']=self.data['reliable']+1 if result['retained'] else 0
        if self.data['reliable']<2:return False
        self.data['level']+=1;self.data['stageGenerations']=0;self.data['reliable']=0
        if self.graduated:self.state.update(phase='pace',curveReady=True)
        self.sync();return True

    def meta(self):
        level=self.data['level'];case=min(self.data['case'],len(self.cases())-1)
        active=self.cases()[case];scenario=active['scenario'] or {}
        return dict(version=VERSION,level=level,stages=len(STAGES),generation=self.data['generations'],
            stageGeneration=self.data['stageGenerations'],scenario=case+1,scenarios=len(self.cases()),
            role='retention' if case>=2 else 'primary',label=STAGES[level][1] if not self.graduated else self.state['phase'],
            initialSpeedKmh=scenario.get('speed',0.)*3.6)


class EvoStageCheck:
    def __init__(self,plan,policy,saved=None):
        from game_academy import Episode
        self.plan=plan;self.candidate=deepcopy(policy);self.champion=None;self.protocol='driving-memory-1'
        self.phase=plan.state['phase'];self.scenarios=plan.cases(True);self.cursor=0
        self.episodes=[Episode(c.get('track',plan.track),c['phase'],c['seed'],protocol=self.protocol,
            scenario=c['scenario'],single_lap=True,context=c.get('context'),
            launch_distance=20. if c['phase']=='launch' and c['scenario'] is None else None) for c in self.scenarios]
        if saved:
            self.cursor=saved['cursor']
            self.episodes=[Episode(s['track_id'],s['phase'],s['seed'],saved=s) for s in saved['episodes']]

    def tick(self):
        from game_learning import Policy
        if not hasattr(self,'policy'):self.policy=Policy(self.candidate)
        for _ in self.episodes:
            e=self.episodes[self.cursor%len(self.episodes)];self.cursor+=1
            if not e.reason:
                e.step(self.policy.act(e.observations(),world=e.world,index=0))
                self.plan.data['evaluationSteps']=self.plan.data.get('evaluationSteps',0)+1
                break
        return all(e.reason for e in self.episodes)

    def results(self):
        main=summary([e.result() for e in self.episodes[:4]])
        retention=summary([e.result() for e in self.episodes[4:]]) if len(self.episodes)>4 else None
        main.update(tested=4,retained=main['valid']==4 and (retention is None or retention['valid']==retention['total']),
            skills={self.phase:{**main,'tested':4}})
        if retention:
            keys={('launch' if c['phase']=='launch' and not c.get('track') else 'Memoria '+c.get('track','')) for c in self.scenarios[4:]}
            for key in keys:
                rows=[e.result() for c,e in zip(self.scenarios[4:],self.episodes[4:]) if key==('launch' if c['phase']=='launch' and not c.get('track') else 'Memoria '+c.get('track',''))]
                main['skills'][key]={**summary(rows),'tested':len(rows)}
        return main,None

    def snapshot(self):
        return dict(kind=CHECK_VERSION,candidate=self.candidate,phase=self.phase,
                    cursor=self.cursor,episodes=[e.snapshot() for e in self.episodes])


def record_epoch(state,e,row):
    epoch=state['epochStats'];epoch.setdefault('byTask',{})
    key=e.track_id+':'+e.spec['label']
    targets=[epoch,epoch['byTask'].setdefault(key,dict(label=e.spec['label'],phase=e.phase,track=e.track_id,episodes=0))]
    delta_progress=max(0.,e.valid_progress-getattr(e,'reported_epoch_progress',0.))
    for target in targets:
        target['episodes']+=1
        target[e.reason]=target.get(e.reason,0)+1
        target['progressMeters']=target.get('progressMeters',0.)+delta_progress
        target['understeerSeconds']=target.get('understeerSeconds',0.)+row['understeerSeconds']-getattr(e,'reported_understeer',0.)
        target['initialSpeedKmh']=getattr(e,'initial_speed',0.)*3.6
        pedals=target.setdefault('pedalCounts',dict(gas=0,coast=0,brake=0))
        for pedal,value in row['pedalCounts'].items():pedals[pedal]+=value-getattr(e,'reported_pedals',{}).get(pedal,0)
        target['recentProgress']=(target.get('recentProgress',[])+[delta_progress])[-64:]
    e.reported_epoch_progress=e.valid_progress


def progress_meta(state,task,track,steps):
    epoch=state.get('epochStats',{});detail=epoch.get('byTask',{}).get(track+':'+task['label'],{})
    return dict(version=epoch.get('version'),steps=steps-epoch.get('startedSteps',steps),
        task=task['label'],episodes=detail.get('episodes',0),success=detail.get('success',0),
        retired=detail.get('contact',0),stalls=detail.get('no_progress',0),
        medianProgress=float(np.median(detail.get('recentProgress',[0.]))),
        initialSpeedKmh=detail.get('initialSpeedKmh',0.))
