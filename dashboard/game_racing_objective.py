"""Frozen flying-lap selection and separate, policy-bound race retention."""
from copy import deepcopy
import numpy as np
from game_academy import Episode
from game_learning import Policy
from game_residual import key
from game_residual_trainer import reward_profile,verification_key
from game_rewards import specification,digest
from game_school_lessons import RaceProof,SKILLS

VERSION='flying-pace-and-race-1'


def school_ready(stats):
    return all(stats.get(skill,{}).get('valid',0)>=2 for skill in SKILLS)


def graduated(stats,previous=False):
    return bool(previous or school_ready(stats))


class RacingCheck:
    def __init__(self,candidate,champion,track,saved=None,cache=None,race_champion=None,race_due=True):
        self.candidate=deepcopy(candidate);self.champion=deepcopy(champion);self.track=track
        self.race_champion=deepcopy(race_champion or dict(policy=champion))
        self.race_due=(saved or {}).get('raceDue',race_due)
        self.cursor=0;self.race_cursor=0;self.reused=0
        self.cache=cache if cache is not None else {}
        self.cases=[('pace',s) for s in (91001,91002,91003)]
        self.attack_mode=candidate.get('recipe',{}).get('trafficLearning')=='attack-1'
        if self.attack_mode:
            self.cases += [(family,s) for family in ('complete','attack','corner','defend') for s in (973101,973102,973103)]
        elif candidate['algorithm']=='residual_tactic':
            self.cases += [('overtake',s) for s in (93101,93102)]+[('corner',s) for s in (93201,93202,93203,93204)]+[('defend',s) for s in (93301,93302)]
        reward={**specification(reward_profile(candidate)),'evaluationRules':'spatial-rules-2'}
        self.reward_digest=digest(reward)
        def episode(phase,seed):
            if self.attack_mode and phase!='pace':
                from game_overtaking import scenario
                e=scenario(track,phase,seed,reward_profile(candidate));e.reward_spec=deepcopy(reward);return e
            return Episode(track,phase,seed,protocol='driving-memory-1',single_lap=phase!='pace',reward_spec=reward,pace_pressure=1.)
        self.episodes=[episode(phase,seed) for phase,seed in self.cases*2]
        self.policies=[Policy(candidate),Policy(champion),Policy(self.race_champion['policy'])]
        self.races=None
        if saved:
            self.cursor=saved['cursor'];self.race_cursor=saved['raceCursor'];self.reused=saved['reused']
            self.episodes=[Episode(track,e['phase'],e['seed'],saved=e) for e in saved['episodes']]
            self.races=None if saved['races'] is None else [RaceProof(r['policy'],track,r['seed'],r['slot'],saved=r) for r in saved['races']]
        else:
            bank=self.cases+[('race-reference',key(self.race_champion['policy'])),('protocol',VERSION),('evaluation-reward',self.reward_digest)]
            cached=self.cache.get(verification_key(champion,track,bank))
            if cached:
                self.episodes[len(self.cases):]=[Episode(track,e['phase'],e['seed'],saved=e) for e in cached]
                self.reused=len(self.cases)

    def tick(self):
        self.last_steps_advanced=0
        if not all(e.reason for e in self.episodes):
            half=len(self.cases)
            for _ in self.episodes:
                i=self.cursor%len(self.episodes);self.cursor+=1;e=self.episodes[i]
                if e.reason:continue
                driver=self.policies[0 if i<half else 1 if i-half<3 else 2]
                e.step(driver.act(None,world=e.world,index=0),return_observation=False)
                self.last_steps_advanced=1
                break
            return False
        if self.races is None:
            summary=self.result()
            if self.track!='oval-1' or not summary['raceProposed'] or not summary['raceDue']:
                self.races=[];return True
            self.races=[RaceProof(policy,self.track,seed,slot) for policy in
                        (self.candidate,self.race_champion['policy']) for seed,slot in ((942002,2),(942004,4))]
        for _ in self.races:
            r=self.races[self.race_cursor%len(self.races)];self.race_cursor+=1
            if not r.reason:r.tick();self.last_steps_advanced=1;break
        return all(r.reason for r in self.races)

    def result(self):
        if not all(e.reason for e in self.episodes):raise ValueError('Verifica incompleta')
        half=len(self.cases)
        def collect(episodes):
            rows=[];times=[]
            for e in episodes[:3]:
                laps=e.world.lap_times[0]
                flying=[r['time'] for r in laps[1:] if r['clean']]
                valid=e.reason=='success' and not e.contact_count and not e.world.track_limits[0] and len(flying)==2
                seconds=float(np.median(flying)) if valid else None
                if valid:times.append(seconds)
                rows.append({**e.result(),'standingAndFlyingSeconds':e.age,'flyingMedian':seconds,'lapTimes':deepcopy(laps)})
            traffic=episodes[3:]
            return dict(valid=len(times),total=3,best=min(times) if times else None,
                median=float(np.median(times)) if len(times)==3 else None,results=rows,
                trafficValid=sum(e.reason=='success' for e in traffic),trafficResults=[e.result() for e in traffic])
        candidate=collect(self.episodes[:half]);champion=collect(self.episodes[half:])
        gain=max(.05,(champion['median'] or 0.)*.0015)
        accepted=candidate['valid']==3 and (champion['valid']<3 or candidate['median']<champion['median']-gain)
        reference=self.race_champion.get('flyingMedian')
        if reference is None and key(self.race_champion['policy'])==key(self.champion):reference=champion['median']
        race_proposed=candidate['valid']==3 and (reference is None and accepted or reference is not None and candidate['median']<reference-max(.05,reference*.0015))
        solo_proposed=race_proposed
        attack_accepted=False
        if self.attack_mode:
            def tactical(rows):
                valid=[e for e in rows if e.reason=='success' and not e.contact_count and not e.world.track_limits[0] and not getattr(e,'racecraft',{}).get('violations',0)]
                passing=[e.age for e in valid if e.phase!='defend']
                return dict(valid=len(valid),total=len(rows),median=float(np.median(passing)) if passing else None,
                    contacts=sum(e.contact_count for e in rows),limits=sum(int(e.world.track_limits[0]) for e in rows))
            a=tactical(self.episodes[3:half]);b=tactical(self.episodes[half+3:])
            candidate['attack']=a;champion['attack']=b
            retained=candidate['valid']==3 and (champion['median'] is None or candidate['median']<=champion['median']*1.01)
            better=(a['valid']>b['valid'] or a['valid']==b['valid'] and a['median'] is not None and b['median'] is not None and a['median']<b['median']-.1)
            attack_accepted=bool(retained and better and a['contacts']<=b['contacts'] and a['limits']<=b['limits'])
            race_proposed=bool(race_proposed or attack_accepted)
        due=self.race_due or bool(race_proposed and reference is not None and candidate['median']<reference*.97)
        regressions=[dict(phase=a.phase,seed=a.seed) for a,b in zip(self.episodes[3:half],self.episodes[half+3:])
            if (b.reason=='success' and a.reason!='success') or a.contact_count>b.contact_count or a.world.track_limits[0]>b.world.track_limits[0]]
        attack_accepted=bool(attack_accepted and not regressions)
        race_proposed=bool(solo_proposed or attack_accepted)
        comparisons=[dict(candidate=a.result(),champion=b.result()) for a,b in zip((self.races or [])[:2],(self.races or [])[2:])]
        race_accepted=bool(race_proposed and not regressions and len(comparisons)==2 and all(
            r['candidate']['reason']=='success' and r['candidate']['finished']==5
            and r['candidate']['contacts']<=r['champion']['contacts']
            and r['candidate']['limits']<=r['champion']['limits'] for r in comparisons))
        decision='improved' if accepted else 'solo_invalid' if candidate['valid']<3 else 'race_improved' if race_accepted else 'attack_improved' if attack_accepted else 'no_gain'
        labels=dict(improved='Giro lanciato migliorato',solo_invalid='Serie di giri puliti insufficiente',race_improved='Versione gara migliorata',attack_improved='Attacco migliorato · verifica gara separata',no_gain='Guida valida · tempo da migliorare')
        race_label='Pronto per la gara' if race_accepted else 'Verifica gara programmata' if race_proposed and not due else 'Da verificare nel traffico' if race_proposed and not comparisons else 'Gara precedente conservata'
        candidate['retained']=accepted
        bank=self.cases+[('race-reference',key(self.race_champion['policy'])),('protocol',VERSION),('evaluation-reward',self.reward_digest)]
        self.cache[verification_key(self.champion,self.track,bank)]=[e.snapshot() for e in self.episodes[half:]]
        # Solo candidate + old race traffic is the correct next mixed baseline.
        self.cache[verification_key(self.candidate,self.track,bank)]=[e.snapshot() for e in self.episodes[:3]+self.episodes[half+3:]]
        if race_accepted:
            next_bank=self.cases+[('race-reference',key(self.candidate)),('protocol',VERSION),('evaluation-reward',self.reward_digest)]
            self.cache[verification_key(self.candidate,self.track,next_bank)]=[e.snapshot() for e in self.episodes[:half]]
        while len(self.cache)>4:self.cache.pop(next(iter(self.cache)))
        return dict(rewardVersion=self.candidate['recipe']['reward'],evaluationVersion=VERSION,
            raceRulesVersion='spatial-rules-2',policyHash=key(self.candidate),accepted=bool(accepted),
            raceAccepted=race_accepted,attackAccepted=attack_accepted,raceProposed=bool(race_proposed),raceDue=bool(due),raceDecisionLabel=race_label,
            raceReferenceMedian=reference,raceReferenceHash=key(self.race_champion['policy']),
            decision=decision,decisionLabel=labels[decision],phase='pace',stageLabel='Giri lanciati · tempo e gara separati',
            candidate=candidate,champion=champion,regressions=regressions,gridRetention=comparisons,
            reusedChampionCases=self.reused)

    def snapshot(self):
        return dict(version=VERSION,candidate=self.candidate,champion=self.champion,track=self.track,
            raceChampion=self.race_champion,raceDue=self.race_due,cursor=self.cursor,raceCursor=self.race_cursor,reused=self.reused,
            episodes=[e.snapshot() for e in self.episodes],races=None if self.races is None else [r.snapshot() for r in self.races])
