"""Real-time demonstration of the current PPO policy, outside its rollouts."""
from game_simulation import World,DT


class PracticePreview:
    def __init__(self,seed=1,track_id='oval-1'):
        self.world=World(1,seed,laps=3,track_id=track_id)
        self.remaining=0.
        self.hold=0.
        self.status='running'

    def advance(self,elapsed,policy):
        # Discard long UI/pause gaps instead of racing through unseen attempts.
        elapsed=max(0.,min(float(elapsed),.1))
        if self.hold>0:
            self.hold=max(0.,self.hold-elapsed)
            if self.hold==0:
                self.world.reset(varied=True)
                self.status='running'
            return
        self.remaining+=elapsed
        while self.remaining+1e-12>=DT:
            self.world.step(policy.act(self.world.observations(),world=self.world),return_observations=False)
            self.remaining=max(0.,self.remaining-DT)
            if not self.world.active.any():
                self.remaining=0.;self.hold=1.
                self.status='3 giri completati' if not self.world.retired.any() else 'Ripartenza'
                break
