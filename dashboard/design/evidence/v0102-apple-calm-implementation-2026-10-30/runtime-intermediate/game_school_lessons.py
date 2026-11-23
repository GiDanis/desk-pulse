"""Physical lessons and independent skill gates; no actuator assistance."""
from copy import deepcopy
import numpy as np
from game_academy import Episode
from game_rewards import specification
from game_direct_bootstrap import physical_context

SKILLS=('accelerazione','frenata','traiettoria','aderenza')


class Lesson(Episode):
    def __init__(self,track,skill,seed,profile=None,saved=None):
        self.lesson=deepcopy((saved or {}).get('lesson')) or dict(fullGas=0,brake=0,minTurnSpeed=100.,offsetMin=100.,offsetMax=-100.)
        rng=np.random.default_rng(seed)
        start,speed,distance={
            'accelerazione':(-24.,float(seed%3)*3.,165.),
            'frenata':(5.,18.+seed%3,160.),
            'traiettoria':(32.,12.+seed%3,145.),
            'aderenza':(-18.,12.,190.)}[skill]
        if track!='oval-1':start=0.;distance=None
        context=physical_context(rng,True) if skill=='aderenza' and track=='oval-1' else None
        scenario=dict(start=start,speed=speed,distance=distance,label=skill.capitalize()+' · scuola guida',limitSeconds=55.) if distance else None
        super().__init__(track,'pace',seed,protocol='driving-memory-1',single_lap=True,
            reward_spec=specification(profile or dict(algorithm='residual_ppo',controlMode='direct')),
            pace_pressure=1.,scenario=scenario,context=context,saved=saved)
        self.spec.update(schoolSkill=skill,schoolStartSpeed=speed)

    def step(self,action,*args,**kwargs):
        result=super().step(action,*args,**kwargs);w=self.world;offset,_,_=w.coordinates()
        self.lesson['fullGas']+=int(action[1]>.90 and abs(w.state[0,5])<.1)
        self.lesson['brake']+=int(action[1]<-.10)
        self.lesson['offsetMin']=min(self.lesson['offsetMin'],float(offset[0]))
        self.lesson['offsetMax']=max(self.lesson['offsetMax'],float(offset[0]))
        if abs(w.state[0,5])>.20:self.lesson['minTurnSpeed']=min(self.lesson['minTurnSpeed'],float(w.state[0,3]))
        if self.reason=='success' and not self.demonstrated():
            self.reason='skill_failed';self.terminated=True
            return result[0],result[1],True,True
        return result

    def demonstrated(self):
        skill=self.spec['schoolSkill']
        if self.track_id!='oval-1':return True
        if skill=='accelerazione':return self.lesson['fullGas']>=12
        if skill=='frenata':return self.lesson['brake']>=6 and self.lesson['minTurnSpeed']<self.spec['schoolStartSpeed']*.97
        if skill=='traiettoria':return self.lesson['offsetMax']-self.lesson['offsetMin']>.4
        return True

    def skill_valid(self):
        # These are measured segments ending after the corner exit. A full
        # lap is a separate mandatory gate, not a fabricated segment lap.
        return bool(not self.world.retired[0] and not self.contact_count
            and self.world.track_limits[0]==0 and not getattr(self,'racecraft',{}).get('violations',0)
            and self.demonstrated())

    def snapshot(self):return {**super().snapshot(),'lesson':deepcopy(self.lesson)}

    def result(self):return {**super().result(),'schoolSkill':self.spec['schoolSkill'],'lesson':deepcopy(self.lesson),'demonstrated':self.reason=='success' and self.demonstrated()}


def make_check(candidate,champion,track,saved=None,cache=None):
    from game_residual_trainer import ResidualCheck,verification_key
    class SchoolCheck(ResidualCheck):
        def __init__(self):
            super().__init__(candidate,champion,track,saved=saved,cache=cache)
            self.races=None;self.race_cursor=0
            if saved and saved.get('races') is not None:
                self.races=[RaceProof(x['policy'],track,x['seed'],x['slot'],saved=x) for x in saved['races']]
                self.race_cursor=saved.get('raceCursor',0)
            if saved:
                self.episodes=[Lesson(track,s['spec']['schoolSkill'],s['seed'],saved=s) if s.get('spec',{}).get('schoolSkill') else Episode(track,s['phase'],s['seed'],saved=s) for s in saved['episodes']]
                self.cases=[(e.spec.get('schoolSkill',e.phase),e.seed) for e in self.episodes[:len(self.episodes)//2]]
                return
            half=len(self.episodes)//2;lessons=[(s,941001+i) for i,s in enumerate(SKILLS)]
            self.episodes=self.episodes[:half]+[Lesson(track,s,n) for s,n in lessons]+self.episodes[half:]+[Lesson(track,s,n) for s,n in lessons]
            self.cases+=lessons
            cached=self.cache.get(verification_key(champion,track,self.cases))
            if cached and len(cached)==len(self.cases):
                self.episodes[len(self.cases):]=[Lesson(track,s['spec']['schoolSkill'],s['seed'],saved=s) if s.get('spec',{}).get('schoolSkill') else Episode(track,s['phase'],s['seed'],saved=s) for s in cached]
                self.reused=len(self.cases)

        def tick(self):
            if not all(e.reason for e in self.episodes):
                if not super().tick():return False
            if self.races is None:
                # Expensive traffic retention runs only after the cheap gates
                # propose a promotion; failed exploratory attempts stop here.
                if track!='oval-1' or not self.result()['accepted']:self.races=[];return True
                self.races=[]
                for policy in (candidate,champion):
                    cases=[('race-proof',942002,2),('race-proof',942004,4)]
                    saved_races=self.cache.get(verification_key(policy,track,cases))
                    for i,(_,seed,slot) in enumerate(cases):
                        self.races.append(RaceProof(policy,track,seed,slot,saved=saved_races[i] if saved_races else None))
            for _ in self.races:
                i=self.race_cursor%len(self.races);self.race_cursor+=1
                if not self.races[i].reason:self.races[i].tick();break
            return all(r.reason for r in self.races)

        def result(self):
            result=super().result();half=len(self.episodes)//2
            skill_rows=[]
            for a,b in zip(self.episodes[:half],self.episodes[half:]):
                if not a.spec.get('schoolSkill'):continue
                skill_rows.append(dict(skill=a.spec['schoolSkill'],candidate=a.result(),champion=b.result()))
            result['school']=skill_rows
            # Skill preservation is mandatory. A new personal best must improve
            # the repeated full-lap median, not just one isolated exercise.
            result['accepted']=bool(result['accepted'] and all(x['candidate']['demonstrated'] for x in skill_rows)
                and (result['champion']['valid']<3 or result['candidate']['median']<result['champion']['median']*.999))
            if not all(x['candidate']['demonstrated'] for x in skill_rows):
                result.update(decision='school_regression',decisionLabel='Fondamenti da ripassare')
            elif not result['accepted'] and result['decision']=='improved':
                result.update(decision='no_gain',decisionLabel='Abilità conservate · tempo da migliorare')
            if self.races:
                comparisons=[dict(candidate=a.result(),champion=b.result()) for a,b in zip(self.races[:2],self.races[2:])]
                result['gridRetention']=comparisons
                safe=all(x['candidate']['reason']=='success' and x['candidate']['finished']==5
                    and x['candidate']['limits']<=x['champion']['limits'] for x in comparisons)
                if not safe:
                    result.update(accepted=False,decision='grid_regression',decisionLabel='Da migliorare nella gara a cinque auto')
                    result['regressions'].append(dict(phase='five-car-race',seed=942002))
                if all(r.reason for r in self.races):
                    for policy,rs in ((candidate,self.races[:2]),(champion,self.races[2:])):
                        self.cache[verification_key(policy,track,[('race-proof',942002,2),('race-proof',942004,4)])]=[r.snapshot() for r in rs]
            result['candidate']['retained']=result['accepted'];result['evaluationVersion']='school-gates-2'
            result['stageLabel']='Giro e fondamenti · confronto col campione'
            for name,episodes in (('candidate',self.episodes[:half]),('champion',self.episodes[half:])):
                traffic=[e for e in episodes[3:] if not e.spec.get('schoolSkill')]
                result[name]['trafficValid']=sum(e.reason=='success' for e in traffic)
                result[name]['trafficResults']=[e.result() for e in traffic]
                result[name]['schoolSkills']={e.spec['schoolSkill']:dict(valid=int(e.reason=='success'),total=1) for e in episodes if e.spec.get('schoolSkill')}
            return result

        def snapshot(self):return {**super().snapshot(),'version':'school-gates-2','races':None if self.races is None else [r.snapshot() for r in self.races],'raceCursor':self.race_cursor}
    return SchoolCheck()


class RaceProof:
    """Frozen five-car retention trial, separate from collected RL experience."""
    def __init__(self,policy,track,seed,slot,saved=None):
        from game_direct_bootstrap import base_asset
        from game_learning import Policy
        from game_residual import profile,snapshot
        from game_simulation import World
        from game_catalog import RACE_PHYSICS_VERSION
        self.policy=deepcopy(policy);self.track=track;self.seed=seed;self.slot=slot
        a=base_asset('driving')['policy'];b=base_asset('traffic')['policy']
        opponents=[a,a,a if policy['algorithm']=='residual_tactic' else b,snapshot(profile(1,'race_master'))]
        opponents.insert(slot,policy);self.policies=list(map(Policy,opponents))
        self.world=World(5,seed,shared=True,laps=3,track_id=track,physics=RACE_PHYSICS_VERSION,telemetry=True)
        self.world.native_sensors=True;self.world.race_lap_target=True
        self.contacts=0;self.contact_events=set();self.reason=''
        if saved:
            self.world.restore(saved['world']);self.contacts=saved['contacts'];self.reason=saved['reason']
            self.contact_events={(x[0],tuple(x[1])) for x in saved.get('contactEvents',[])}

    def tick(self):
        from game_control import frozen_actions
        w=self.world;w.step(frozen_actions(w,self.policies),return_observations=False)
        self.contact_events.update((e['time'],tuple(e['cars'])) for e in w.events if e.get('type')=='contact')
        self.contacts=len(self.contact_events)
        if w.retired.any():self.reason='retirement'
        elif not w.active.any():self.reason='success'
        elif w.time>=150.:self.reason='timeout'
        return bool(self.reason)

    def result(self):
        return dict(seed=self.seed,slot=self.slot,reason=self.reason,seconds=self.world.time,
            finished=int(np.isfinite(self.world.finish).sum()),contacts=self.contacts,limits=int(self.world.track_limits.sum()))

    def snapshot(self):
        return dict(policy=self.policy,track=self.track,seed=self.seed,slot=self.slot,world=self.world.snapshot(),contacts=self.contacts,reason=self.reason,contactEvents=[[t,list(c)] for t,c in sorted(self.contact_events)])
