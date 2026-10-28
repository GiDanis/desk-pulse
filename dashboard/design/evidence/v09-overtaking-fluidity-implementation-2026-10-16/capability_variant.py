"""Research-only capability/decision-balanced curriculum. No product default."""
from game_residual_trainer import ResidualTrainer
from game_academy import Episode

class CapabilityTrainer(ResidualTrainer):
    def __init__(self,*a,**kw):
        self.skill_success={p:0 for p in ('pace','overtake','corner','defend')}
        self.skill_decisions={p:0 for p in self.skill_success}
        super().__init__(*a,**kw)
        self.spec={**self.spec,'curriculum':'capability-balanced-experiment-1'}
        self.state['effectiveParameters']=self.spec

    def new_episode(self,saved=None):
        phases=['pace']
        if self.skill_success['pace']>=3:phases+=['overtake']
        if self.skill_success['overtake']>=3:phases+=['corner']
        if self.skill_success['corner']>=3:phases+=['defend']
        # Compare physical decisions per skill, not unequal episode counts.
        phase=min(phases,key=lambda p:self.skill_decisions[p])
        seed=int(self.rng.integers(200000,300000));self.state['phase']=phase
        return Episode(self.track_id,phase,seed,self.opponents,protocol='driving-memory-1',objective=self.objective,
            bots=self.bots,single_lap=True,reward_spec=self.reward_spec,pace_pressure=1.)

    def tick(self):
        e=self.episode;before=self.decisions
        super().tick()
        if self.decisions>before:self.skill_decisions[e.phase]+=self.decisions-before
        if e is not self.episode and e.reason=='success':self.skill_success[e.phase]+=1
        self.state['capabilityExperiment']=dict(success=dict(self.skill_success),decisions=dict(self.skill_decisions))
